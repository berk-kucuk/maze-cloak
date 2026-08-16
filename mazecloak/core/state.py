"""The daemon's runtime report.

One direction only: the daemon writes, the GUI reads. Keeping it one-way is why
there is no socket protocol here — the GUI never asks the daemon a question, it
reads the answer the daemon already published.

Lives on tmpfs, so its absence is the honest signal that the daemon is not
running.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict, field, fields
from pathlib import Path

from mazecloak.core import paths


@dataclass
class IfaceState:
    mac: str = ""
    original: str = ""      # what to restore to; "" when never captured
    rotations: int = 0
    last_rotation: float = 0.0
    last_error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DaemonState:
    running: bool = False
    version: str = ""
    pid: int = 0
    started_at: float = 0.0
    last_rotation: float = 0.0
    next_rotation: float = 0.0
    # "" when rotating normally; otherwise why it is not — "vpn", "disabled",
    # "no-schedule". The GUI shows this verbatim-ish, so the set is small.
    paused: str = ""
    interfaces: dict[str, IfaceState] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["interfaces"] = {k: v.to_dict() if hasattr(v, "to_dict") else v
                           for k, v in self.interfaces.items()}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "DaemonState":
        valid = {f.name for f in fields(cls)}
        clean = {k: v for k, v in (d or {}).items() if k in valid}
        raw = clean.pop("interfaces", {}) or {}
        ifaces: dict[str, IfaceState] = {}
        ivalid = {f.name for f in fields(IfaceState)}
        for name, s in raw.items():
            if isinstance(s, dict):
                ifaces[name] = IfaceState(
                    **{k: v for k, v in s.items() if k in ivalid})
        return cls(interfaces=ifaces, **clean)


def write_state(state: DaemonState, path: Path | None = None) -> None:
    p = path or paths.STATE_PATH
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state.to_dict(), indent=2))
        os.chmod(tmp, 0o644)   # every local user may read the report
        os.replace(tmp, p)
    except OSError:
        pass  # never let a failed status write take the daemon down


def read_state(path: Path | None = None) -> DaemonState | None:
    """The daemon's last report, or None when it is not running.

    A state file whose mtime is far in the past means the daemon died without
    clearing it — SIGKILL, or the box lost power with /run on disk. Treating
    that as "not running" keeps the GUI from showing a rotation schedule that
    nothing is executing.
    """
    p = path or paths.STATE_PATH
    try:
        raw = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    state = DaemonState.from_dict(raw)
    if state.running and time.time() - p.stat().st_mtime > _STALE_AFTER:
        state.running = False
        state.paused = "stale"
    return state


def clear_state(path: Path | None = None) -> None:
    try:
        (path or paths.STATE_PATH).unlink()
    except OSError:
        pass


# The daemon rewrites state every tick; three missed ticks is dead, not slow.
_STALE_AFTER = 90.0


# ── original addresses, across restarts ──────────────────────────────────────

def load_originals(path: Path | None = None) -> dict[str, str]:
    """Burned-in addresses captured before the first rotation.

    Persisted because the alternative — reading the current address at startup
    — records an already-randomised address as the "original" whenever the
    daemon is restarted while active, and restore-on-stop then puts back a
    random address forever.
    """
    p = path or paths.ORIGINALS_PATH
    try:
        d = json.loads(p.read_text())
        return {str(k): str(v) for k, v in d.items() if isinstance(v, str)}
    except (OSError, ValueError, AttributeError):
        return {}


def save_originals(originals: dict[str, str], path: Path | None = None) -> None:
    p = path or paths.ORIGINALS_PATH
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(originals, indent=2))
        os.replace(tmp, p)
    except OSError:
        pass
