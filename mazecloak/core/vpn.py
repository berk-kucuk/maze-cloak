"""VPN tunnel detection.

Used for one decision: whether it is safe to rotate right now. Changing a
physical interface's address bounces the link the tunnel is built on, which
drops the VPN — so a rotation timed badly turns a privacy feature into a leak.

Detection is by interface naming and type, which covers WireGuard, OpenVPN and
the tun/tap-based commercial clients. It intentionally does not try to be
exhaustive: a false positive costs one skipped rotation, a false negative costs
a dropped tunnel, so the check leans towards "yes, a tunnel is up".
"""
from __future__ import annotations

from pathlib import Path

_SYS_NET = Path("/sys/class/net")

_VPN_PREFIXES = ("tun", "tap", "wg", "ppp", "nordlynx", "proton", "mullvad",
                 "tailscale", "zt", "ipsec", "vpn")


def _operstate(name: str) -> str:
    try:
        return (_SYS_NET / name / "operstate").read_text().strip()
    except OSError:
        return "unknown"


def active_vpn_interfaces() -> list[str]:
    try:
        names = sorted(p.name for p in _SYS_NET.iterdir())
    except OSError:
        return []

    active: list[str] = []
    for name in names:
        if not any(name.startswith(p) for p in _VPN_PREFIXES):
            continue
        # WireGuard interfaces frequently report "unknown" rather than "up"
        # because they are pointtopoint and carry no carrier signal; treating
        # that as down would defeat the whole check.
        if _operstate(name) in ("up", "unknown"):
            active.append(name)
    return active


def is_up() -> bool:
    return bool(active_vpn_interfaces())
