"""Core tests. No root, no real NIC — `ip link` is stubbed at the seam.

The cases worth having here are the ones where a bug is silent: a rotation that
reports success while the kernel kept the old address, a restore that puts back
a previously-randomised address, and a VPN pause that quietly banks up an
overdue rotation for the moment the tunnel drops.
"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Point every path at a scratch dir before importing anything that reads them.
_TMP = tempfile.mkdtemp(prefix="maze-cloak-test-")
os.environ["MAZE_CLOAK_ETC"] = f"{_TMP}/etc"
os.environ["MAZE_CLOAK_RUN"] = f"{_TMP}/run"
os.environ["MAZE_CLOAK_VAR"] = f"{_TMP}/var"
os.environ["MAZE_CLOAK_NM"] = f"{_TMP}/nm/99-maze-cloak.conf"

import subprocess  # noqa: E402

# ── no test may shell out ────────────────────────────────────────────────────
# This suite exercises code that, in production, runs `ip link set` and
# `nmcli general reload` as root. `nmcli general reload` is a privileged D-Bus
# call: reached from an ordinary user account it raises a polkit password
# dialog, and sync_nm() is called on every daemon tick — so a single careless
# test turns `python tests/test_core.py` into a stream of authentication
# prompts on the developer's desktop.
#
# Rather than trusting each test to stub the right seam, the door is locked
# here: any subprocess launched from anywhere under test fails the run with a
# clear message instead of touching the machine.
def _no_subprocess(*args, **kwargs):
    raise AssertionError(
        f"a test tried to run an external command: {args[0] if args else kwargs}. "
        "Stub the seam in mazecloak.core instead — see the note in tests/test_core.py.")


subprocess.run = _no_subprocess
subprocess.Popen = _no_subprocess
subprocess.call = _no_subprocess
subprocess.check_output = _no_subprocess

from mazecloak.core import interfaces as ifaces  # noqa: E402
from mazecloak.core import mac as macgen         # noqa: E402
from mazecloak.core import nm, paths, vpn        # noqa: E402
from mazecloak.core.config import CloakConfig, load_config, save_config  # noqa: E402
from mazecloak.core.rotator import Rotator       # noqa: E402
from mazecloak.core.state import (               # noqa: E402
    DaemonState, IfaceState, read_state, write_state,
)


class FakeNic:
    """A pretend interface whose address only changes when `set_mac` succeeds."""

    def __init__(self, name="wlan0", permanent="aa:bb:cc:11:22:33"):
        self.name = name
        self.permanent = permanent
        self.mac = permanent
        self.accept = True
        self.reverts_to = None   # simulates NetworkManager reasserting itself


class RotatorTestCase(unittest.TestCase):
    def setUp(self):
        self.nic = FakeNic()
        for p in (paths.ORIGINALS_PATH, paths.STATE_PATH):
            try:
                p.unlink()
            except OSError:
                pass

        self._saved = (ifaces.list_names, ifaces.current_mac,
                       ifaces.permanent_mac, ifaces.set_mac, vpn.is_up)

        ifaces.list_names = lambda include_virtual=False: [self.nic.name]
        ifaces.current_mac = lambda n: self.nic.mac if n == self.nic.name else ""
        ifaces.permanent_mac = lambda n: self.nic.permanent if n == self.nic.name else ""
        ifaces.set_mac = self._set_mac
        vpn.is_up = lambda: False

    def tearDown(self):
        (ifaces.list_names, ifaces.current_mac, ifaces.permanent_mac,
         ifaces.set_mac, vpn.is_up) = self._saved

    def _set_mac(self, name, mac):
        if not self.nic.accept:
            return False, "driver refused"
        self.nic.mac = self.nic.reverts_to or mac
        if self.nic.mac != mac:
            return False, f"address reverted to {self.nic.mac}"
        return True, ""

    def _rotator(self, **kw):
        cfg = CloakConfig(enabled=True, **kw)
        return Rotator(cfg, log=lambda _m: None)

    # ── rotation ──────────────────────────────────────────────────────────

    def test_rotation_changes_the_address(self):
        r = self._rotator()
        self.assertEqual(r.rotate_all(), 1)
        self.assertNotEqual(self.nic.mac, self.nic.permanent)
        self.assertTrue(macgen.is_locally_administered(self.nic.mac))

    def test_a_reverted_change_is_reported_as_failure(self):
        """The kernel keeping the old address must not count as a rotation."""
        r = self._rotator()
        self.nic.reverts_to = self.nic.permanent
        ok, err = r.rotate_one(self.nic.name)
        self.assertFalse(ok)
        self.assertIn("reverted", err)
        self.assertEqual(r.state.interfaces[self.nic.name].rotations, 0)

    def test_driver_refusal_is_recorded(self):
        r = self._rotator()
        self.nic.accept = False
        ok, _ = r.rotate_one(self.nic.name)
        self.assertFalse(ok)
        self.assertTrue(r.state.interfaces[self.nic.name].last_error)

    # ── restore ───────────────────────────────────────────────────────────

    def test_restore_returns_the_hardware_address(self):
        r = self._rotator()
        r.rotate_all()
        self.assertNotEqual(self.nic.mac, self.nic.permanent)
        r.restore_all()
        self.assertEqual(self.nic.mac, self.nic.permanent)

    def test_original_survives_a_restart_while_randomised(self):
        """A daemon restarted mid-cloak must not adopt the random address as
        the one to restore to."""
        r1 = self._rotator()
        r1.rotate_all()
        randomised = self.nic.mac

        # Restart: a fresh Rotator, and the driver has stopped reporting the
        # permanent address (the common ethtool-less case).
        ifaces.permanent_mac = lambda n: ""
        r2 = self._rotator()
        self.assertEqual(r2.original_of(self.nic.name), self.nic.permanent)

        r2.restore_all()
        self.assertEqual(self.nic.mac, self.nic.permanent)
        self.assertNotEqual(self.nic.mac, randomised)

    def test_unknown_hardware_address_is_not_invented(self):
        """With no permanent address and an already-random current one, there is
        nothing safe to record — better no original than a random one."""
        self.nic.mac = "02:11:22:33:44:55"
        ifaces.permanent_mac = lambda n: ""
        r = self._rotator()
        r._remember_original(self.nic.name)
        self.assertEqual(r.original_of(self.nic.name), "")

    # ── scheduling ────────────────────────────────────────────────────────

    def test_the_first_tick_rotates(self):
        """A daemon that has never rotated is due.

        Worth its own case because the interval test below passes vacuously if
        nothing ever rotates: it only asserts the address stopped changing.
        """
        r = self._rotator(rotate_minutes=30)
        r.tick()
        self.assertNotEqual(self.nic.mac, self.nic.permanent,
                            "the schedule never fired at all")

    def test_tick_respects_the_interval(self):
        r = self._rotator(rotate_minutes=30)
        r.tick()
        first = self.nic.mac
        self.assertNotEqual(first, self.nic.permanent)
        r.tick()
        self.assertEqual(self.nic.mac, first, "rotated twice inside one interval")

    def test_rotate_on_start_off_defers_rather_than_skips(self):
        """Declining the startup rotation must not leave the clock unstarted:
        the next tick would then treat it as overdue and rotate anyway."""
        r = self._rotator(rotate_minutes=30, rotate_on_start=False)
        r.first_run()
        r.tick()
        self.assertEqual(self.nic.mac, self.nic.permanent,
                         "rotated despite rotate_on_start=False")

    def test_tick_rotates_once_due(self):
        r = self._rotator(rotate_minutes=1)
        r.tick()
        first = self.nic.mac
        r._last_rotation = time.time() - 120
        r.tick()
        self.assertNotEqual(self.nic.mac, first)

    def test_a_failing_rotation_does_not_retry_every_tick(self):
        """The one that takes the machine down with it.

        set_mac's fallback drops the link and brings it back up, so a rotation
        that fails on every interface must still consume its interval. Retrying
        on the next tick means the network goes down and up every two seconds
        for as long as the daemon runs.
        """
        r = self._rotator(rotate_minutes=30)
        self.nic.accept = False
        calls = []
        inner = ifaces.set_mac
        ifaces.set_mac = lambda n, m: (calls.append(n), inner(n, m))[1]
        try:
            r.tick()
            self.assertEqual(len(calls), 1, "the first tick should try once")
            r.tick()
            r.tick()
            self.assertEqual(len(calls), 1,
                             "retried a failed rotation before the interval was up")
        finally:
            ifaces.set_mac = inner

    def test_vpn_pauses_rotation(self):
        vpn.is_up = lambda: True
        r = self._rotator(rotate_minutes=1, pause_on_vpn=True)
        r.tick()
        self.assertEqual(self.nic.mac, self.nic.permanent)
        self.assertEqual(r.state.paused, "vpn")

    def test_vpn_pause_does_not_bank_an_overdue_rotation(self):
        """The clock must not keep running under the tunnel: otherwise the tick
        after a long VPN session fires immediately, whatever the interval."""
        r = self._rotator(rotate_minutes=60, pause_on_vpn=True)
        vpn.is_up = lambda: True
        r.tick()
        vpn.is_up = lambda: False
        r.tick()
        self.assertEqual(self.nic.mac, self.nic.permanent,
                         "rotated the instant the VPN dropped")

    def test_disabled_config_does_nothing(self):
        r = Rotator(CloakConfig(enabled=False), log=lambda _m: None)
        r.tick()
        self.assertEqual(self.nic.mac, self.nic.permanent)
        self.assertEqual(r.state.paused, "disabled")

    def test_manual_mode_reports_itself(self):
        r = self._rotator(rotate_enabled=False)
        r.tick()
        self.assertEqual(r.state.paused, "no-schedule")
        self.assertEqual(self.nic.mac, self.nic.permanent)

    # ── interface selection ───────────────────────────────────────────────

    def test_empty_selection_means_every_interface(self):
        r = self._rotator()
        self.assertEqual(r.targets(), [self.nic.name])

    def test_selection_ignores_interfaces_that_are_gone(self):
        r = self._rotator(interfaces=["wlan0", "eth9"])
        self.assertEqual(r.targets(), ["wlan0"])

    # ── NetworkManager drop-in ────────────────────────────────────────────

    def test_enabling_writes_the_dropin_other_maze_tools_read(self):
        r = self._rotator(nm_integration=True)
        r.sync_nm()
        self.assertTrue(nm.is_active())
        text = paths.NM_DROPIN.read_text()
        # The exact strings maze_status.mac_randomization_enabled() greps for.
        self.assertIn("wifi.scan-rand-mac-address", text)
        self.assertIn("cloned-mac-address=random", text)

    def test_disabling_removes_the_dropin(self):
        r = self._rotator(nm_integration=True)
        r.sync_nm()
        r.cfg.enabled = False
        r.sync_nm()
        self.assertFalse(nm.is_active())


class ConfigTestCase(unittest.TestCase):
    def test_roundtrip(self):
        cfg = CloakConfig(enabled=True, rotate_minutes=15,
                          strategy=macgen.RANDOM_VENDOR)
        save_config(cfg)
        self.assertEqual(load_config().rotate_minutes, 15)

    def test_hand_edited_nonsense_is_clamped(self):
        cfg = CloakConfig.from_dict(
            {"rotate_minutes": 10 ** 9, "strategy": "wat", "nm_cloned_mode": "wat"})
        self.assertEqual(cfg.strategy, macgen.FULL_RANDOM)
        self.assertEqual(cfg.nm_cloned_mode, "random")
        self.assertLessEqual(cfg.rotate_minutes, 10080)

    def test_unknown_keys_from_a_newer_version_are_dropped(self):
        cfg = CloakConfig.from_dict({"enabled": True, "invented_later": 1})
        self.assertTrue(cfg.enabled)

    def test_corrupt_file_falls_back_to_safe_defaults(self):
        paths.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        paths.CONFIG_PATH.write_text("{not json")
        self.assertFalse(load_config().enabled)


class StateTestCase(unittest.TestCase):
    def test_roundtrip(self):
        write_state(DaemonState(running=True,
                                interfaces={"wlan0": IfaceState(rotations=2)}))
        got = read_state()
        self.assertTrue(got.running)
        self.assertEqual(got.interfaces["wlan0"].rotations, 2)

    def test_a_stale_file_is_not_reported_as_running(self):
        """A daemon killed with SIGKILL leaves running=true behind; the GUI must
        not show a live schedule for a process that is gone."""
        write_state(DaemonState(running=True))
        old = time.time() - 600
        os.utime(paths.STATE_PATH, (old, old))
        got = read_state()
        self.assertFalse(got.running)
        self.assertEqual(got.paused, "stale")

    def test_missing_file_means_not_running(self):
        try:
            paths.STATE_PATH.unlink()
        except OSError:
            pass
        self.assertIsNone(read_state())


class MacTestCase(unittest.TestCase):
    def test_every_strategy_yields_a_local_unicast_address(self):
        for strategy in macgen.STRATEGIES:
            for _ in range(100):
                m = macgen.random_mac(strategy, current="00:1a:11:22:33:44")
                self.assertTrue(macgen.is_valid(m), m)
                first = int(m.split(":")[0], 16)
                self.assertTrue(first & 0x02, f"{strategy}: {m} not local")
                self.assertFalse(first & 0x01, f"{strategy}: {m} is multicast")

    def test_keep_vendor_preserves_the_prefix(self):
        m = macgen.random_mac(macgen.KEEP_VENDOR, current="aa:bb:cc:11:22:33")
        self.assertTrue(m.startswith("aa:bb:cc:"))
        self.assertNotEqual(m, "aa:bb:cc:11:22:33")

    def test_keep_vendor_falls_back_when_there_is_no_current_address(self):
        self.assertTrue(macgen.is_valid(
            macgen.random_mac(macgen.KEEP_VENDOR, current=None)))

    def test_a_borrowed_oui_is_never_passed_off_as_genuine(self):
        for _ in range(100):
            m = macgen.random_mac(macgen.RANDOM_VENDOR)
            self.assertEqual(macgen.vendor_of(m), "locally administered")

    def test_virtual_interfaces_are_refused(self):
        ok, err = ifaces.set_mac("lo", "02:11:22:33:44:55")
        self.assertFalse(ok)
        self.assertIn("virtual", err)


class SecurityTestCase(unittest.TestCase):
    """The config file is group-writable and a root daemon reads it. These are
    the checks that keep that boundary from being more than it is meant to be."""

    def test_interface_names_are_validated_before_becoming_argv(self):
        """set_mac builds an argv as root. It must not depend on its caller
        having filtered the name against /sys/class/net first."""
        for bad in ("../../etc/passwd", "eth0 extra", "a" * 32, "", "eth0;reboot",
                    "eth/0", "-rf"):
            ok, err = ifaces.set_mac(bad, "02:11:22:33:44:55")
            self.assertFalse(ok, f"accepted {bad!r}")
            self.assertIn("invalid interface name", err, f"for {bad!r}")

    def test_a_malformed_mac_is_refused(self):
        for bad in ("", "zz:11:22:33:44:55", "02:11:22:33:44",
                    "02:11:22:33:44:55:66", "02-11-22-33-44-55"):
            ok, _ = ifaces.set_mac("wlan0", bad)
            self.assertFalse(ok, f"accepted {bad!r}")

    def test_the_daemon_refuses_to_read_config_through_a_symlink(self):
        """A maze-group member can write the config — that is the trust model —
        but must not be able to aim the root daemon at another path."""
        from mazecloak.core.config import load_config as raw_load
        target = Path(_TMP) / "elsewhere.json"
        target.write_text(json.dumps({"enabled": True, "rotate_minutes": 5}))

        link = Path(_TMP) / "linked-config.json"
        link.unlink(missing_ok=True)
        link.symlink_to(target)

        # Untrusted read follows it; the daemon's trusted read must not.
        self.assertTrue(raw_load(link).enabled)
        self.assertFalse(raw_load(link, trusted=True).enabled,
                         "the daemon followed a symlink")

    def test_an_oversized_config_cannot_exhaust_the_daemon(self):
        from mazecloak.core.config import load_config as raw_load
        huge = Path(_TMP) / "huge.json"
        huge.write_text('{"enabled": true, "pad": "' + "x" * (256 * 1024) + '"}')
        self.assertFalse(raw_load(huge, trusted=True).enabled)

    def test_virtual_and_tunnel_interfaces_are_never_touched(self):
        for name in ("lo", "docker0", "wg0", "tun0", "virbr0", "veth1234"):
            ok, err = ifaces.set_mac(name, "02:11:22:33:44:55")
            self.assertFalse(ok, f"would have touched {name}")

    def test_the_nm_reload_never_runs_unprivileged(self):
        """`nmcli general reload` is polkit-authorised: reached as a normal user
        it raises a password dialog, and sync_nm() runs on every daemon tick."""
        self.assertNotEqual(os.geteuid(), 0, "run the suite as a normal user")
        # subprocess is blocked suite-wide, so reaching nmcli would raise
        # AssertionError rather than return False.
        self.assertFalse(nm.reload_networkmanager())


class AutostartTestCase(unittest.TestCase):
    def setUp(self):
        from mazecloak.core import autostart
        self.autostart = autostart
        self._home = tempfile.mkdtemp(prefix="maze-cloak-autostart-")
        os.environ["XDG_CONFIG_HOME"] = self._home

    def tearDown(self):
        os.environ.pop("XDG_CONFIG_HOME", None)

    def test_disabling_writes_a_user_override_not_a_deletion(self):
        """Turning autostart off must not require touching /etc."""
        ok, _ = self.autostart.set_enabled(False)
        self.assertTrue(ok)
        self.assertTrue(self.autostart.user_entry().exists())
        self.assertIn("Hidden=true", self.autostart.user_entry().read_text())
        self.assertFalse(self.autostart.is_enabled())

    def test_reenabling_removes_the_override(self):
        """Rather than writing Hidden=false, which would pin a stale Exec line."""
        self.autostart.set_enabled(False)
        self.autostart.set_enabled(True)
        self.assertFalse(self.autostart.user_entry().exists())


class I18nTestCase(unittest.TestCase):
    def test_the_two_languages_have_the_same_keys(self):
        from mazecloak.gui.i18n import STRINGS
        missing_tr = set(STRINGS["en"]) - set(STRINGS["tr"])
        missing_en = set(STRINGS["tr"]) - set(STRINGS["en"])
        self.assertFalse(missing_tr, f"missing Turkish: {sorted(missing_tr)}")
        self.assertFalse(missing_en, f"missing English: {sorted(missing_en)}")

    def test_placeholders_match_across_languages(self):
        """A {path} that exists in one language and not the other is a crash at
        .format() time, in whichever locale nobody tested."""
        import re
        from mazecloak.gui.i18n import STRINGS
        for key, en in STRINGS["en"].items():
            tr = STRINGS["tr"][key]
            self.assertEqual(set(re.findall(r"{(\w+)}", en)),
                             set(re.findall(r"{(\w+)}", tr)),
                             f"placeholder mismatch in '{key}'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
