"""Every path Maze Cloak reads or writes, in one place.

Two processes share these files and they do not run as the same user:

    daemon (root)  writes  state.json,  reads   config.json
    GUI    (user)  writes  config.json, reads   state.json

so the ownership is deliberate rather than incidental. `config.json` is
``root:maze`` mode 0664 — group-writable, which is what lets the GUI change a
setting without a password prompt, the same trust boundary Maze Guard draws
around its helper socket. `state.json` lives on tmpfs and is world-readable
because it is only ever a report.

The MAZE_CLOAK_ETC / MAZE_CLOAK_RUN overrides exist so the app can be run from
a source checkout without touching /etc — see README, "Running from source".
"""
import os
from pathlib import Path

_ETC = Path(os.environ.get("MAZE_CLOAK_ETC", "/etc/maze-cloak"))
_RUN = Path(os.environ.get("MAZE_CLOAK_RUN", "/run/maze-cloak"))

CONFIG_DIR = _ETC
CONFIG_PATH = _ETC / "config.json"

RUN_DIR = _RUN
STATE_PATH = _RUN / "state.json"

# Restored on daemon shutdown, so it has to outlive a reboot-less crash but not
# a reboot: /var/lib, not /run.
ORIGINALS_PATH = Path(
    os.environ.get("MAZE_CLOAK_VAR", "/var/lib/maze-cloak")) / "originals.json"

# The NetworkManager drop-in. Maze Control Center greps
# /etc/NetworkManager/conf.d/*.conf for the randomization keys to decide
# whether to show "MAC randomisation: Enabled", so this file is both a real
# setting and this tool's public status flag — see core/nm.py.
NM_DROPIN = Path(os.environ.get(
    "MAZE_CLOAK_NM",
    "/etc/NetworkManager/conf.d/99-maze-cloak.conf"))

SERVICE_UNIT = "maze-cloak.service"

# Shared with Maze Guard: a member of this group may change Maze settings
# without authenticating.
GROUP = "maze"
