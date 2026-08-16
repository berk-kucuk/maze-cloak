"""Small display helpers shared by the views.

Durations are rendered as coarse units (`3m`, `2h 10m`) rather than clock
times: the numbers here are all "how long until" or "how long since", and a
wall-clock timestamp makes the reader do the subtraction themselves.
"""
from __future__ import annotations

import time


def _units(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    hours, rem = divmod(seconds, 3600)
    minutes = rem // 60
    return f"{hours}h {minutes}m" if minutes else f"{hours}h"


def until(ts: float, never: str, due: str) -> str:
    """A future timestamp as "in 12m", or `due` once it has passed."""
    if not ts:
        return never
    delta = int(ts - time.time())
    return _units(delta) if delta > 0 else due


def since(ts: float, never: str) -> str:
    """A past timestamp as an age: "12m"."""
    if not ts:
        return never
    return _units(max(0, int(time.time() - ts)))


def mac_or_dash(mac: str) -> str:
    return mac.upper() if mac else "—"
