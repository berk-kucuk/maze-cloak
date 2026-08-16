"""Maze Cloak privileged daemon.

Runs as root under systemd. It is the only component that touches an interface,
and it never listens on anything: it reads the config file the GUI writes and
publishes a state file the GUI reads. No socket means no protocol to get wrong
and no listening surface to harden.

The config is polled by mtime rather than watched with inotify because the file
is replaced (os.replace) rather than edited in place, which is the case inotify
watches handle worst, and a one-second poll of a single stat() costs nothing.
"""
from __future__ import annotations

import os
import signal
import sys
import time

from mazecloak import __version__
from mazecloak.core import nm, paths
from mazecloak.core.config import CloakConfig, load_config as _load_config


def load_config() -> CloakConfig:
    """Config as the daemon reads it: never through a symlink. See core/config."""
    return _load_config(trusted=True)
from mazecloak.core.rotator import Rotator
from mazecloak.core.state import clear_state, write_state

# How often to look for config changes and re-evaluate the schedule. Rotation
# intervals are minutes at the shortest, so this only bounds how quickly the
# daemon reacts to the GUI, not rotation accuracy.
_TICK = 2.0


def _log(msg: str) -> None:
    print(msg, flush=True)


class Daemon:
    def __init__(self) -> None:
        self.cfg: CloakConfig = load_config()
        self.rotator = Rotator(self.cfg, log=_log)
        self._config_mtime = self._mtime()
        self._stop = False

    def _mtime(self) -> float:
        try:
            return paths.CONFIG_PATH.stat().st_mtime
        except OSError:
            return 0.0

    def _reload_if_changed(self) -> None:
        mtime = self._mtime()
        if mtime == self._config_mtime:
            return
        self._config_mtime = mtime
        old = self.cfg
        self.cfg = load_config()
        self.rotator.cfg = self.cfg
        _log(f"[config] reloaded (enabled={self.cfg.enabled}, "
             f"strategy={self.cfg.strategy}, "
             f"every={self.cfg.rotate_minutes}m)")

        # Turning the master switch on should act now, not at the next interval
        # — the user just asked for it and is watching the window.
        if self.cfg.enabled and not old.enabled:
            self.rotator.first_run()
        # Turning it off should hand the interfaces back immediately.
        elif old.enabled and not self.cfg.enabled and self.cfg.restore_on_stop:
            self.rotator.restore_all()

        # An explicit "rotate now" from the GUI. Checked after the on/off
        # handling above so that enabling the cloak and asking for a rotation in
        # the same write does not rotate twice.
        elif self.cfg.rotate_request > old.rotate_request and self.cfg.enabled:
            _log("[request] immediate rotation")
            self.rotator.rotate_all()

    def _publish(self) -> None:
        state = self.rotator.refresh_state()
        state.running = True
        state.version = __version__
        state.pid = os.getpid()
        write_state(state)

    def run(self) -> int:
        if os.geteuid() != 0:
            _log("maze-cloak daemon must run as root")
            return 1

        _log(f"Maze Cloak daemon {__version__} starting "
             f"(config={paths.CONFIG_PATH})")

        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._on_signal)

        self.rotator.state.started_at = time.time()
        self.rotator.sync_nm()
        self.rotator.first_run()

        while not self._stop:
            try:
                self._reload_if_changed()
                self.rotator.tick()
                self._publish()
            except Exception as e:  # noqa: BLE001 — a bad tick must not be fatal
                _log(f"[error] tick failed: {e}")
            # Sleep in slices so a SIGTERM is answered promptly rather than
            # after the remainder of the tick.
            deadline = time.time() + _TICK
            while not self._stop and time.time() < deadline:
                time.sleep(0.2)

        return self._shutdown()

    def _on_signal(self, _signum, _frame) -> None:
        self._stop = True

    def _shutdown(self) -> int:
        _log("Maze Cloak daemon stopping")
        if self.cfg.restore_on_stop:
            restored = self.rotator.restore_all()
            _log(f"[restore] {restored} interface(s) returned to their hardware address")
        # The drop-in is a claim that randomisation is active, so it must not
        # outlive the daemon that makes it true.
        if nm.is_active():
            nm.remove()
            nm.reload_networkmanager()
        clear_state()
        return 0


def main() -> int:
    if "--version" in sys.argv:
        print(f"maze-cloak-daemon {__version__}")
        return 0
    return Daemon().run()


if __name__ == "__main__":
    sys.exit(main())
