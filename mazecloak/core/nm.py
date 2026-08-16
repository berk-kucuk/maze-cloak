"""The NetworkManager drop-in — a real setting that doubles as a status flag.

Maze Control Center decides whether to report "MAC randomisation: Enabled" by
grepping /etc/NetworkManager/conf.d/*.conf for these keys:

    wifi.scan-rand-mac-address
    cloned-mac-address=random
    cloned-mac-address=stable
    mac-address=random

(see maze-tools, ``maze_status.mac_randomization_enabled``). Writing this file
is therefore how Maze Cloak announces itself to the rest of the Maze tools, and
removing it is how it stands down. The keys are not written to satisfy a grep —
each one does what it says — but the file is kept in the shape that detector
recognises on purpose, and that is the coupling to preserve if either side
changes.

The two layers this file configures are complementary, not redundant:

  scan-rand-mac-address  randomises the address used while *scanning* for
                         networks, which is what leaks to every AP in range
                         whether or not the user ever associates.
  cloned-mac-address     randomises the address used once *associated*.

Timer-based rotation (core/rotator.py) is a third, independent layer for the
already-connected case, which NetworkManager does not cover.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from mazecloak.core import paths

_HEADER = """# Managed by Maze Cloak — do not edit.
#
# This file is rewritten whenever Maze Cloak's settings change and removed when
# MAC randomisation is turned off. Other Maze tools read it to report whether
# randomisation is active, so deleting it by hand will make them say "Disabled"
# while the daemon is still running.
"""


def render(wifi_scan_rand: bool = True, cloned_mode: str = "random") -> str:
    if cloned_mode not in ("random", "stable"):
        cloned_mode = "random"
    return (
        f"{_HEADER}\n"
        "[device-mac-randomization]\n"
        f"wifi.scan-rand-mac-address={'yes' if wifi_scan_rand else 'no'}\n"
        "\n"
        "[connection-mac-randomization]\n"
        f"ethernet.cloned-mac-address={cloned_mode}\n"
        f"wifi.cloned-mac-address={cloned_mode}\n"
    )


def is_active(path: Path | None = None) -> bool:
    """Whether *our* drop-in is in place.

    Deliberately narrower than the ecosystem-wide check in `detected_elsewhere`:
    this answers "did Maze Cloak write it", which is what the tool may safely
    remove.
    """
    return (path or paths.NM_DROPIN).exists()


def detected_elsewhere() -> bool:
    """Whether some *other* conf.d file already enables randomisation.

    Mirrors the detector in maze-tools so the GUI can explain a confusing case:
    Maze Control Center says "Enabled" while Maze Cloak is off, because a
    different tool — or a hand-written conf — got there first.
    """
    needles = (
        "wifi.scan-rand-mac-address",
        "cloned-mac-address=random",
        "cloned-mac-address=stable",
        "mac-address=random",
    )
    ours = paths.NM_DROPIN.name
    try:
        for f in Path("/etc/NetworkManager/conf.d").glob("*.conf"):
            if f.name == ours:
                continue
            text = f.read_text(errors="ignore")
            if any(n in text for n in needles):
                return True
    except OSError:
        pass
    return False


def apply(wifi_scan_rand: bool = True, cloned_mode: str = "random",
          path: Path | None = None) -> tuple[bool, str]:
    """Write the drop-in. Root only. Returns (ok, error)."""
    p = path or paths.NM_DROPIN
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render(wifi_scan_rand, cloned_mode))
        return True, ""
    except OSError as e:
        return False, str(e)


def remove(path: Path | None = None) -> tuple[bool, str]:
    p = path or paths.NM_DROPIN
    try:
        p.unlink()
        return True, ""
    except FileNotFoundError:
        return True, ""
    except OSError as e:
        return False, str(e)


def reload_networkmanager() -> bool:
    """Ask NetworkManager to re-read conf.d. Root only — never prompts.

    `nmcli general reload` is a privileged D-Bus call: run as an ordinary user
    it raises a polkit password dialog. Since this is called from `sync_nm()`,
    which runs on every daemon tick, letting a non-root caller reach it turns a
    background loop into a stream of authentication prompts — so the euid check
    below is load-bearing, not a nicety. Anything that imports this module in a
    user context (the GUI, the test suite) gets a silent no-op.

    Best-effort even as root: the drop-in also takes effect on the next NM
    restart or reboot, so a machine without nmcli is not an error worth
    surfacing.
    """
    if os.geteuid() != 0:
        return False
    try:
        r = subprocess.run(["nmcli", "general", "reload", "conf"],
                           capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
