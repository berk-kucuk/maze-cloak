"""Configuration, split by who owns it.

`CloakConfig` is the daemon's contract and lives in /etc — the GUI writes it,
the daemon obeys it. `UiConfig` is theme and language, which the daemon has no
opinion about, so it stays in the user's own ~/.config where a second user on
the same machine gets their own.

Unknown keys are dropped on load rather than rejected, so a config written by a
newer version downgrades cleanly instead of refusing to start.
"""
from __future__ import annotations

import grp
import json
import os
from dataclasses import dataclass, asdict, field, fields
from pathlib import Path

from mazecloak.core import paths
from mazecloak.core.mac import FULL_RANDOM, STRATEGIES

UI_CONFIG_PATH = Path(
    os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
) / "maze-cloak" / "ui.json"

# Rotation intervals offered in the UI, in minutes.
INTERVAL_CHOICES = (5, 10, 15, 30, 60, 120, 360, 720, 1440)

MIN_INTERVAL = 1
MAX_INTERVAL = 10080  # one week


@dataclass
class CloakConfig:
    """What the daemon does. Written by the GUI, read by the daemon."""

    # Master switch. Everything below is inert while this is False.
    enabled: bool = False

    strategy: str = FULL_RANDOM

    # Which interfaces to rotate. Empty means "every physical interface",
    # which is what a user who has never opened the Interfaces tab expects.
    interfaces: list[str] = field(default_factory=list)

    # ── scheduling ────────────────────────────────────────────────────────
    rotate_enabled: bool = True
    rotate_minutes: int = 30
    rotate_on_start: bool = True

    # Rotating mid-tunnel tears down the link the VPN runs over, which drops
    # the tunnel and briefly exposes traffic the user believed was covered —
    # the opposite of what someone enabling this tool wants.
    pause_on_vpn: bool = True

    # Put the burned-in address back when the daemon stops. Off means a
    # randomised address outlives the tool, which is occasionally what someone
    # wants and always surprising, so it is a visible switch.
    restore_on_stop: bool = True

    # ── NetworkManager integration ────────────────────────────────────────
    # Also this tool's status flag: Maze Control Center reads the drop-in to
    # decide whether MAC randomisation is on. See core/nm.py.
    nm_integration: bool = True
    nm_wifi_scan_rand: bool = True
    nm_cloned_mode: str = "random"   # "random" (per connect) | "stable" (per network)

    # ── one-shot request ──────────────────────────────────────────────────
    # Set to time.time() by the GUI to ask for an immediate rotation. The daemon
    # acts whenever the value increases, which is what lets an unprivileged
    # window trigger a privileged action without a socket or a password: it is
    # a request written to a file the daemon already watches, not a command.
    rotate_request: float = 0.0

    def sanitised(self) -> "CloakConfig":
        """Clamp anything a hand-edited file could get wrong."""
        if self.strategy not in STRATEGIES:
            self.strategy = FULL_RANDOM
        if self.nm_cloned_mode not in ("random", "stable"):
            self.nm_cloned_mode = "random"
        self.rotate_minutes = max(MIN_INTERVAL,
                                  min(MAX_INTERVAL, int(self.rotate_minutes or 30)))
        self.interfaces = [str(i) for i in (self.interfaces or []) if str(i).strip()]
        return self

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CloakConfig":
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in valid}).sanitised()


def load_config(path: Path | None = None, trusted: bool = False) -> CloakConfig:
    """Read the daemon config.

    `trusted=True` is used by the root daemon and adds a refusal to follow a
    symlink at the config path. /etc/maze-cloak is group-writable by design, so
    a `maze` member can replace config.json — which is the intended trust model,
    they can write its contents anyway — but they should not be able to aim a
    root process at an arbitrary path and have it opened. O_NOFOLLOW is the
    cheap way to keep the daemon reading the file it thinks it is reading.

    Every failure returns defaults rather than raising: the defaults are "do
    nothing", which is the safe direction for a config error to fail in.
    """
    p = path or paths.CONFIG_PATH
    try:
        if trusted:
            # O_NOFOLLOW fails with ELOOP on a symlink rather than opening the
            # target. Checked with lstat first so the reason can be logged.
            if p.is_symlink():
                raise PermissionError(f"{p} is a symlink; refusing to read it")
            fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                raw = os.read(fd, _MAX_CONFIG_BYTES).decode("utf-8")
            finally:
                os.close(fd)
        else:
            raw = p.read_text()
        return CloakConfig.from_dict(json.loads(raw))
    except FileNotFoundError:
        return CloakConfig()
    except (OSError, ValueError, TypeError, UnicodeDecodeError):
        return CloakConfig()


# A config file is a few hundred bytes. Capping the read stops a group-writable
# path from being used to make the daemon allocate without bound.
_MAX_CONFIG_BYTES = 64 * 1024


def save_config(cfg: CloakConfig, path: Path | None = None) -> None:
    """Persist the daemon's config.

    Raises PermissionError when the caller is neither root nor in the `maze`
    group — the GUI catches that and says so rather than pretending it saved.
    """
    p = path or paths.CONFIG_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg.sanitised().to_dict(), indent=2))
    # os.replace keeps the temp file's inode, so the destination inherits the
    # temp file's mode AND its ownership — both have to be set here, not just
    # the mode.
    #
    # Ownership is the half that used to be missed. tmpfiles.d declares this
    # file root:maze 0664 so that every member of the `maze` group can change
    # the settings, but a GUI save replaced it with one owned by the saving
    # user and their personal group. The permissions still looked right, and on
    # a single-user machine nothing broke — but a second `maze` member silently
    # lost the ability to save, and the file only returned to root:maze at the
    # next boot, when systemd-tmpfiles runs. Put the group back explicitly.
    try:
        os.chmod(tmp, 0o664)
    except OSError:
        pass
    try:
        maze_gid = grp.getgrnam("maze").gr_gid
        # -1 leaves the owner alone: a non-root saver cannot give the file to
        # root, but it can set the group to one it belongs to, which is the
        # part that matters for shared access.
        os.chown(tmp, 0 if os.geteuid() == 0 else -1, maze_gid)
    except (KeyError, OSError, PermissionError):
        # No `maze` group, or not a member. The save still succeeds; only the
        # shared-access property is lost, and tmpfiles restores it at boot.
        pass
    os.replace(tmp, p)


def config_writable(path: Path | None = None) -> bool:
    """Whether this process can save. Drives the GUI's limited-mode banner."""
    p = path or paths.CONFIG_PATH
    if p.exists():
        return os.access(p, os.W_OK)
    return p.parent.exists() and os.access(p.parent, os.W_OK)


# ── UI preferences (per user) ────────────────────────────────────────────────

@dataclass
class UiConfig:
    theme: str = "dark"
    language: str = "en"
    start_hidden: bool = True
    notify: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def load_ui() -> UiConfig:
    try:
        d = json.loads(UI_CONFIG_PATH.read_text())
        valid = {f.name for f in fields(UiConfig)}
        return UiConfig(**{k: v for k, v in d.items() if k in valid})
    except (OSError, ValueError, TypeError):
        return UiConfig()


def save_ui(cfg: UiConfig) -> None:
    try:
        UI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        UI_CONFIG_PATH.write_text(json.dumps(cfg.to_dict(), indent=2))
    except OSError:
        pass  # a lost theme preference is not worth an error dialog
