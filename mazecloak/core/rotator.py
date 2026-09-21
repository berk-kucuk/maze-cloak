"""The rotation engine — all of the daemon's decision-making, minus the loop.

Kept free of signals, sleeping and systemd so it can be driven directly from a
test or a one-shot CLI run. `Rotator.tick()` is the whole contract: call it
often, it decides whether anything is due and does it.
"""
from __future__ import annotations

import time
from typing import Callable

from mazecloak.core import interfaces as ifaces
from mazecloak.core import mac as macgen
from mazecloak.core import nm, vpn
from mazecloak.core.config import CloakConfig
from mazecloak.core.state import (
    DaemonState, IfaceState, load_originals, save_originals,
)


def _log(msg: str) -> None:
    print(msg, flush=True)


class Rotator:
    def __init__(self, cfg: CloakConfig, log: Callable[[str], None] = _log):
        self.cfg = cfg
        self._log = log
        self.state = DaemonState()
        self._originals: dict[str, str] = load_originals()
        self._last_rotation = 0.0
        self._applied_nm: tuple[bool, bool, str] | None = None

    # ── interface selection ───────────────────────────────────────────────

    def targets(self) -> list[str]:
        """Interfaces to rotate: the configured set, or every physical one.

        Names are filtered against what actually exists on each call rather than
        cached, so unplugging a USB adapter stops producing errors on the next
        tick instead of every tick forever.
        """
        present = set(ifaces.list_names())
        if self.cfg.interfaces:
            return [n for n in self.cfg.interfaces if n in present]
        return sorted(present)

    # ── original addresses ────────────────────────────────────────────────

    def _remember_original(self, name: str) -> None:
        """Record the burned-in address once, before the first rotation.

        Prefers the driver's permanent address over whatever is live: if the
        daemon is restarted while an interface is already randomised, the live
        address is a random one and recording it would make "restore" a no-op
        forever.
        """
        if name in self._originals:
            return
        perm = ifaces.permanent_mac(name)
        current = ifaces.current_mac(name)
        original = perm or current
        if not original:
            return
        if not perm and macgen.is_locally_administered(current):
            # No permanent address available and the live one is already
            # randomised — recording it would lock in a random "original".
            self._log(f"[warn] {name}: cannot determine the hardware address; "
                      f"restore-on-stop will not be able to undo this")
            return
        self._originals[name] = original
        save_originals(self._originals)

    def original_of(self, name: str) -> str:
        return self._originals.get(name, "")

    # ── rotation ──────────────────────────────────────────────────────────

    def rotate_one(self, name: str) -> tuple[bool, str]:
        self._remember_original(name)
        current = ifaces.current_mac(name)
        new_mac = macgen.random_mac(self.cfg.strategy, current=self._originals.get(name) or current)
        ok, err = ifaces.set_mac(name, new_mac)

        st = self.state.interfaces.setdefault(name, IfaceState())
        st.original = self._originals.get(name, "")
        st.mac = ifaces.current_mac(name)
        if ok:
            st.rotations += 1
            st.last_rotation = time.time()
            st.last_error = ""
            self._log(f"[ok] {name}: {current or '?'} -> {new_mac}")
        else:
            st.last_error = err
            self._log(f"[fail] {name}: {err}")
        return ok, err

    def rotate_all(self) -> int:
        rotated = 0
        for name in self.targets():
            ok, _ = self.rotate_one(name)
            rotated += int(ok)

        # The clock is reset whether or not anything actually changed, and that
        # is the important half. Advancing it only on success reads as the
        # careful choice and is the opposite: an interface that refuses every
        # rotation — a managed device that reasserts its own address, a driver
        # that rejects the change — leaves _last_rotation at 0, next_due() then
        # answers "now" forever, and tick() re-enters this method on every pass
        # of a two-second loop. Each of those passes runs set_mac(), whose
        # fallback takes the link down and back up. A failing rotation would
        # bring the machine's network down and up every two seconds, for as long
        # as the daemon runs.
        #
        # Only the *reported* last rotation stays conditional: the GUI shows it
        # to the user, and a failure is not a rotation.
        self._last_rotation = time.time()
        if rotated:
            self.state.last_rotation = self._last_rotation
        return rotated

    def restore_all(self) -> int:
        """Put the burned-in addresses back. Called on shutdown."""
        restored = 0
        for name, original in list(self._originals.items()):
            if name not in set(ifaces.list_names()):
                continue
            if ifaces.current_mac(name) == original:
                continue
            ok, err = ifaces.set_mac(name, original)
            if ok:
                restored += 1
                self._log(f"[restore] {name} -> {original}")
            else:
                self._log(f"[restore-fail] {name}: {err}")
        return restored

    # ── NetworkManager drop-in ────────────────────────────────────────────

    def sync_nm(self) -> None:
        """Bring the drop-in in line with the config.

        Also this tool's status flag for the rest of the Maze suite, so it is
        kept in step on every tick rather than only when settings change — a
        drop-in deleted by hand is restored on the next pass.
        """
        want = (self.cfg.enabled and self.cfg.nm_integration)
        desired = (want, self.cfg.nm_wifi_scan_rand, self.cfg.nm_cloned_mode)
        present = nm.is_active()

        if desired == self._applied_nm and present == want:
            return

        if want:
            ok, err = nm.apply(self.cfg.nm_wifi_scan_rand, self.cfg.nm_cloned_mode)
            self._log(f"[nm] drop-in written "
                      f"(scan-rand={self.cfg.nm_wifi_scan_rand}, "
                      f"cloned={self.cfg.nm_cloned_mode})" if ok
                      else f"[nm-fail] {err}")
        else:
            ok, err = nm.remove()
            if present:
                self._log("[nm] drop-in removed" if ok else f"[nm-fail] {err}")

        if ok:
            nm.reload_networkmanager()
            self._applied_nm = desired

    # ── scheduling ────────────────────────────────────────────────────────

    @property
    def interval(self) -> float:
        return max(1, int(self.cfg.rotate_minutes)) * 60.0

    def next_due(self) -> float:
        """When the next rotation is due, for display. 0.0 means "no schedule"."""
        if not (self.cfg.enabled and self.cfg.rotate_enabled):
            return 0.0
        if not self._last_rotation:
            return time.time()
        return self._last_rotation + self.interval

    def is_due(self) -> bool:
        """Whether to rotate on this tick.

        Separate from next_due() because the two cannot share the "never
        rotated" answer. next_due() returns *now* for the display, and asking
        `time.time() >= self.next_due()` evaluates the left side first — so the
        deadline is always a few microseconds newer than the clock it is
        compared against, the branch is never taken, and a daemon that has not
        yet rotated stays that way for as long as it runs.
        """
        if not self._last_rotation:
            return True
        return time.time() >= self._last_rotation + self.interval

    def tick(self) -> None:
        """Do whatever is due. Safe to call as often as you like."""
        self.sync_nm()

        if not self.cfg.enabled:
            self.state.paused = "disabled"
            self.state.next_rotation = 0.0
            return

        if not self.cfg.rotate_enabled:
            self.state.paused = "no-schedule"
            self.state.next_rotation = 0.0
            return

        if self.cfg.pause_on_vpn and vpn.is_up():
            self.state.paused = "vpn"
            # Hold the clock rather than letting the interval elapse under the
            # tunnel: otherwise every tick after the VPN drops fires a rotation
            # that is "overdue" by however long the tunnel was up.
            self._last_rotation = self._last_rotation or time.time()
            self.state.next_rotation = 0.0
            return

        self.state.paused = ""

        if self.is_due():
            self.rotate_all()

        self.state.next_rotation = self.next_due()

    def first_run(self) -> None:
        """Rotate immediately at startup when the config asks for it.

        Every path out of here starts the schedule's clock, including the ones
        that decline to rotate. Leaving it unset would make the next tick treat
        the rotation as overdue and do immediately what this method just decided
        not to do.
        """
        if not self.cfg.enabled:
            return
        if not self.cfg.rotate_on_start:
            self._start_clock()
            return
        if self.cfg.pause_on_vpn and vpn.is_up():
            self._log("[skip] VPN is up — not rotating at startup")
            self._start_clock()
            return
        self.rotate_all()

    def _start_clock(self) -> None:
        """Begin the interval now, without disturbing a real earlier rotation."""
        self._last_rotation = self._last_rotation or time.time()

    # ── state ─────────────────────────────────────────────────────────────

    def refresh_state(self) -> DaemonState:
        for name in self.targets():
            st = self.state.interfaces.setdefault(name, IfaceState())
            st.mac = ifaces.current_mac(name)
            st.original = self._originals.get(name, "")
        # Drop interfaces that have gone away so the GUI stops listing them.
        for name in list(self.state.interfaces):
            if name not in set(ifaces.list_names()):
                del self.state.interfaces[name]
        return self.state
