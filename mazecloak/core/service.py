"""systemd control for the daemon, from the unprivileged GUI.

Everything here calls `systemctl` directly — never `pkexec`, never `sudo`.

That distinction matters. `pkexec systemctl …` asks polkit for
`org.freedesktop.policykit.exec`, which means "let this user run an arbitrary
program as root": it prompts by default, and the only way to make it quiet is a
rule broad enough to cover every pkexec call on the system. Calling systemctl
directly instead lets systemd raise its own, far narrower actions
(`manage-units`, `manage-unit-files`, carrying the unit name), which the rule
shipped in packaging/49-maze-cloak.rules grants to the `maze` group for
`maze-cloak.service` and nothing else.

So on a properly installed system these are silent. On one where the rule is
missing or the user is not in `maze`, polkit prompts once per action — which is
the correct outcome for a button labelled "Start daemon", and never happens on
a timer or a refresh.

Read-only queries below need no authorisation at all.
"""
from __future__ import annotations

import shutil
import subprocess

from mazecloak.core.paths import SERVICE_UNIT


def _systemctl(*args: str, timeout: float = 10.0) -> subprocess.CompletedProcess:
    return subprocess.run(["systemctl", *args],
                          capture_output=True, text=True, timeout=timeout)


# ── queries (no authorisation) ───────────────────────────────────────────────

def available() -> bool:
    """Whether the unit is installed at all — drives the GUI's setup banner."""
    if not shutil.which("systemctl"):
        return False
    try:
        r = _systemctl("list-unit-files", SERVICE_UNIT)
        return SERVICE_UNIT in r.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def is_active() -> bool:
    try:
        return _systemctl("is-active", "--quiet", SERVICE_UNIT).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def is_enabled() -> bool:
    try:
        return _systemctl("is-enabled", "--quiet", SERVICE_UNIT).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


# ── state changes (polkit-mediated) ──────────────────────────────────────────

def _manage(*args: str) -> tuple[bool, str]:
    try:
        r = _systemctl(*args, timeout=120.0)
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    if r.returncode == 0:
        return True, ""

    err = (r.stderr or "").strip()
    lowered = err.lower()
    # Distinguish "you said no" from "it broke": the first is not an error the
    # user needs shown back to them in red.
    if "authentication required" in lowered or "not authorized" in lowered:
        return False, "cancelled"
    return False, err or f"systemctl {' '.join(args)} failed"


def start() -> tuple[bool, str]:
    return _manage("start", SERVICE_UNIT)


def stop() -> tuple[bool, str]:
    return _manage("stop", SERVICE_UNIT)


def enable() -> tuple[bool, str]:
    """Start now, and on every boot."""
    return _manage("enable", "--now", SERVICE_UNIT)


def disable() -> tuple[bool, str]:
    return _manage("disable", "--now", SERVICE_UNIT)
