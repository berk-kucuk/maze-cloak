"""The line Maze Cloak publishes into the Maze suite status contract.

Maze Guard reads /run/maze/status/maze-cloak.json when it files an attack, so
that an incident report can say whether the attacker saw the adapter's real
address. That makes this file part of another package's input, and the cases
that matter are the ones where a wrong answer would be believed: a stale claim
outliving the daemon, and a pause that still reports randomisation.
"""
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

_TMP = tempfile.mkdtemp(prefix="maze-cloak-status-test-")
os.environ["MAZE_CLOAK_ETC"] = f"{_TMP}/etc"
os.environ["MAZE_CLOAK_RUN"] = f"{_TMP}/run"
os.environ["MAZE_CLOAK_VAR"] = f"{_TMP}/var"
os.environ["MAZE_CLOAK_NM"] = f"{_TMP}/nm/99-maze-cloak.conf"

from mazecloak.core import paths, state                    # noqa: E402

# paths.py resolves its environment once, at import. Another test module in the
# same run may well have imported it first, so the scratch location is pinned
# here by patching the attribute rather than by setting an env var that would
# already have been read.
_STATUS_PATH = Path(_TMP) / "status" / "maze-cloak.json"


def _state(**kw):
    ifaces = kw.pop("ifaces", {})
    return state.DaemonState(
        interfaces={n: state.IfaceState(**v) for n, v in ifaces.items()}, **kw)


def _published() -> dict:
    return json.loads(_STATUS_PATH.read_text())


class TestSuiteStatus(unittest.TestCase):

    def setUp(self):
        self._patch = unittest.mock.patch.object(paths, "STATUS_PATH",
                                                 _STATUS_PATH)
        self._patch.start()

    def tearDown(self):
        state.clear_state()
        self._patch.stop()

    def test_rotated_address_is_reported_as_randomised(self):
        state.write_state(_state(running=True, paused="", ifaces={
            "wlan0": {"mac": "aa:bb:cc:dd:ee:ff",
                      "original": "00:11:22:33:44:55", "rotations": 2}}))
        self.assertTrue(_published()["mac_randomised"])

    def test_case_differences_are_not_a_rotation(self):
        state.write_state(_state(running=True, paused="", ifaces={
            "wlan0": {"mac": "AA:BB:CC:DD:EE:FF",
                      "original": "aa:bb:cc:dd:ee:ff", "rotations": 0}}))
        self.assertFalse(_published()["mac_randomised"])

    def test_paused_daemon_claims_nothing(self):
        state.write_state(_state(running=True, paused="vpn", ifaces={
            "wlan0": {"mac": "aa:bb:cc:dd:ee:ff",
                      "original": "00:11:22:33:44:55", "rotations": 2}}))
        self.assertFalse(_published()["mac_randomised"])

    def test_stopped_daemon_claims_nothing(self):
        state.write_state(_state(running=False, ifaces={
            "wlan0": {"mac": "aa:bb:cc:dd:ee:ff",
                      "original": "00:11:22:33:44:55", "rotations": 2}}))
        self.assertFalse(_published()["mac_randomised"])

    def test_clear_state_removes_the_claim(self):
        """A status file outliving the daemon would be believed."""
        state.write_state(_state(running=True, paused="", ifaces={
            "wlan0": {"mac": "aa:bb", "original": "cc:dd", "rotations": 1}}))
        self.assertTrue(_STATUS_PATH.exists())
        state.clear_state()
        self.assertFalse(_STATUS_PATH.exists())

    def test_report_is_world_readable(self):
        """Maze Guard's GUI reads it as the normal user; the daemon is root."""
        state.write_state(_state(running=True, ifaces={}))
        self.assertEqual(_STATUS_PATH.stat().st_mode & 0o777, 0o644)

    def test_schema_keys_are_stable(self):
        """Another package parses this; adding keys is fine, losing them is not."""
        state.write_state(_state(running=True, ifaces={}))
        self.assertLessEqual(
            {"app", "at", "running", "paused", "mac_randomised"},
            set(_published()))


class TestConfigOwnership(unittest.TestCase):
    """Saving must not quietly take the config away from the `maze` group.

    tmpfiles.d declares /etc/maze-cloak/config.json root:maze 0664 so every
    member of the group can change the settings. `os.replace` keeps the temp
    file's inode, so a save used to hand the file to the saving user and their
    personal group — permissions still looked right, and on a one-user machine
    nothing broke, but a second `maze` member silently lost the ability to save.
    """

    def setUp(self):
        import grp
        try:
            self.maze_gid = grp.getgrnam("maze").gr_gid
        except KeyError:
            self.skipTest("no 'maze' group on this machine")
        if self.maze_gid not in os.getgroups() and os.geteuid() != 0:
            self.skipTest("not a member of the 'maze' group")
        self._dir = tempfile.mkdtemp(prefix="maze-cloak-own-")
        self.path = Path(self._dir) / "config.json"

    def test_saved_config_belongs_to_the_maze_group(self):
        from mazecloak.core import config as cfgmod
        cfgmod.save_config(cfgmod.CloakConfig(), self.path)
        self.assertEqual(self.path.stat().st_gid, self.maze_gid)

    def test_saved_config_stays_group_writable(self):
        from mazecloak.core import config as cfgmod
        cfgmod.save_config(cfgmod.CloakConfig(), self.path)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o664)

    def test_a_second_save_keeps_both(self):
        """The re-save path is the one that used to drift."""
        from mazecloak.core import config as cfgmod
        cfgmod.save_config(cfgmod.CloakConfig(), self.path)
        cfgmod.save_config(cfgmod.CloakConfig(enabled=True), self.path)
        st = self.path.stat()
        self.assertEqual(st.st_gid, self.maze_gid)
        self.assertEqual(st.st_mode & 0o777, 0o664)


if __name__ == "__main__":
    unittest.main()
