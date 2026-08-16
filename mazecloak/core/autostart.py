"""Autostart, per user, on top of the system-wide default.

The package installs `/etc/xdg/autostart/maze-cloak.desktop`, so autostart is
**on by default** for every account on the machine — the app is tray-first and
is not much use if it only runs when you remember to open it.

Turning it off is therefore a per-user override rather than a deletion: a user
cannot remove a file from /etc, and should not need root to stop an app from
starting in their own session. The XDG autostart spec covers this — a file of
the same name in `~/.config/autostart` shadows the system one, and `Hidden=true`
means "do not start". That is what the toggle writes.

Re-enabling deletes the override rather than writing `Hidden=false`, so the
user file does not linger and silently pin a stale Exec line after an upgrade.
"""
from __future__ import annotations

import os
from pathlib import Path

_ENTRY = "maze-cloak.desktop"

_SYSTEM_DIRS = (
    Path("/etc/xdg/autostart"),
    Path("/usr/share/applications/autostart"),
)


def _user_dir() -> Path:
    return Path(os.environ.get(
        "XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "autostart"


def user_entry() -> Path:
    return _user_dir() / _ENTRY


def system_entry() -> Path | None:
    for directory in _SYSTEM_DIRS:
        candidate = directory / _ENTRY
        if candidate.exists():
            return candidate
    return None


def available() -> bool:
    """Whether autostart can be controlled at all — false from a checkout."""
    return system_entry() is not None or user_entry().exists()


def _is_hidden(path: Path) -> bool:
    try:
        for line in path.read_text(errors="ignore").splitlines():
            key, _, value = line.partition("=")
            if key.strip().lower() == "hidden":
                return value.strip().lower() == "true"
    except OSError:
        pass
    return False


def is_enabled() -> bool:
    override = user_entry()
    if override.exists():
        return not _is_hidden(override)
    return system_entry() is not None


def _override_text() -> str:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Maze Cloak\n"
        "Exec=/usr/bin/maze-cloak --background\n"
        "Icon=maze-cloak\n"
        "Terminal=false\n"
        "Hidden=true\n"
        "X-GNOME-Autostart-enabled=false\n"
    )


def set_enabled(enabled: bool) -> tuple[bool, str]:
    """Turn autostart on or off for this user only. Never needs root."""
    override = user_entry()
    try:
        if enabled:
            # Drop the override and fall back to the system entry.
            override.unlink(missing_ok=True)
            if system_entry() is None:
                return False, "no system autostart entry is installed"
            return True, ""
        override.parent.mkdir(parents=True, exist_ok=True)
        override.write_text(_override_text())
        return True, ""
    except OSError as e:
        return False, str(e)
