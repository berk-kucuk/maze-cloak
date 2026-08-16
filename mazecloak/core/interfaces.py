"""Network interface discovery and MAC read/write.

Everything here reads sysfs where it can and shells out to `ip` only for the
write, which keeps the common path (the GUI refreshing four times a minute)
free of subprocess spawns.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

_SYS_NET = Path("/sys/class/net")

# Linux caps interface names at IFNAMSIZ-1 = 15 bytes and forbids '/' and
# whitespace; this is deliberately no broader than that.
#
# The first character is restricted further, to exclude '-': a name reaching
# `ip link set <name> address <mac>` with a leading hyphen would be parsed as an
# option rather than an interface. No real interface starts with one.
_IFNAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.:@-]{0,14}$")

# Interface name prefixes that must never be touched. Randomising a bridge, a
# tunnel or a VPN interface breaks the link it carries and buys nothing: the
# address is not visible to the network the user is trying to be anonymous on.
_VIRTUAL_PREFIXES = (
    "lo", "docker", "veth", "br-", "virbr", "tun", "tap", "wg", "dummy",
    "bond", "team", "vmnet", "vboxnet", "xenbr", "ovs-", "flannel", "cni",
    "calico", "cilium", "zt", "tailscale", "ppp", "sit", "gre",
)


@dataclass
class Interface:
    name: str
    mac: str = ""
    permanent: str = ""     # burned-in address, "" when the driver won't say
    state: str = "unknown"  # up | down | unknown
    wireless: bool = False
    has_ip: bool = False
    vendor: str = ""
    connection: str = ""    # NetworkManager connection name, "" when unknown
    rotating: bool = field(default=False)  # filled in by the daemon's state

    @property
    def is_up(self) -> bool:
        return self.state == "up"


def _read(path: Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def is_virtual(name: str) -> bool:
    if any(name.startswith(p) for p in _VIRTUAL_PREFIXES):
        return True
    # A device with no `device` symlink has no hardware behind it. This catches
    # virtual interfaces whose names don't match any prefix above.
    return not (_SYS_NET / name / "device").exists()


def is_wireless(name: str) -> bool:
    return (_SYS_NET / name / "wireless").exists() or (
        _SYS_NET / name / "phy80211").exists()


def current_mac(name: str) -> str:
    return _read(_SYS_NET / name / "address").lower()


def permanent_mac(name: str) -> str:
    """The burned-in address.

    Tried in two places because neither is universally available: sysfs does not
    expose it on every driver, and ethtool is an optional dependency. Returns ""
    when both fail, which callers must treat as "unknown" rather than "none" —
    restoring to "" would brick the interface.
    """
    perm = _read(_SYS_NET / name / "phys_switch_id")
    from mazecloak.core.mac import is_valid
    if is_valid(perm):
        return perm.lower()
    try:
        r = subprocess.run(["ethtool", "-P", name],
                           capture_output=True, text=True, timeout=5)
        token = r.stdout.strip().split()[-1].lower()
        if is_valid(token) and token != "00:00:00:00:00:00":
            return token
    except (OSError, subprocess.SubprocessError, IndexError):
        pass
    return ""


def has_ip(name: str) -> bool:
    try:
        r = subprocess.run(["ip", "-o", "addr", "show", name],
                           capture_output=True, text=True, timeout=5)
        return "inet " in r.stdout or "inet6 " in r.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def _nm_connection(name: str) -> str:
    try:
        r = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,CONNECTION", "device", "status"],
            capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            dev, _, conn = line.partition(":")
            if dev == name and conn not in ("--", ""):
                return conn
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def describe(name: str, with_nm: bool = True) -> Interface:
    from mazecloak.core.mac import vendor_of
    mac = current_mac(name)
    return Interface(
        name=name,
        mac=mac,
        permanent=permanent_mac(name),
        state=_read(_SYS_NET / name / "operstate") or "unknown",
        wireless=is_wireless(name),
        has_ip=has_ip(name),
        vendor=vendor_of(mac),
        connection=_nm_connection(name) if with_nm else "",
    )


def list_names(include_virtual: bool = False) -> list[str]:
    try:
        names = sorted(p.name for p in _SYS_NET.iterdir())
    except OSError:
        return []
    if include_virtual:
        return names
    return [n for n in names if not is_virtual(n)]


def list_interfaces(include_virtual: bool = False,
                    with_nm: bool = True) -> list[Interface]:
    return [describe(n, with_nm=with_nm)
            for n in list_names(include_virtual)]


def set_mac(name: str, mac: str) -> tuple[bool, str]:
    """Apply `mac` to `name`. Returns (ok, error).

    Tries the change without downing the link first. That ordering matters:
    bringing an interface down makes NetworkManager notice a carrier loss and,
    on a managed device, re-apply its own address — so the down/up path is the
    fallback for drivers that reject a live change, not the default.

    Requires root; the daemon is the only caller.
    """
    from mazecloak.core.mac import is_valid
    if not is_valid(mac):
        return False, f"invalid MAC: {mac}"
    # The interface name reaches this function from a config file that is
    # group-writable by design, so it is validated here rather than trusted from
    # the caller. Callers already intersect it with /sys/class/net, but this is
    # the function that builds an argv as root and it should not depend on that
    # having happened. Kernel interface names are IFNAMSIZ-1 at most and this
    # character set is a superset of what `ip link` will accept.
    if not _IFNAME_RE.match(name or ""):
        return False, f"invalid interface name: {name!r}"
    if is_virtual(name):
        return False, f"refusing to touch virtual interface {name}"

    def _run(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(args, capture_output=True, text=True, timeout=15)

    try:
        r = _run(["ip", "link", "set", name, "address", mac])
        if r.returncode != 0:
            _run(["ip", "link", "set", name, "down"])
            r = _run(["ip", "link", "set", name, "address", mac])
            _run(["ip", "link", "set", name, "up"])
            if r.returncode != 0:
                return False, r.stderr.strip() or "ip link set address failed"
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)

    # Report what the kernel actually holds, not what we asked for. A managed
    # device can accept the command and still end up back on its old address,
    # and a rotation that silently did nothing is the failure this tool exists
    # to avoid.
    actual = current_mac(name)
    if actual != mac:
        return False, f"address reverted to {actual or 'unknown'} (NetworkManager may be managing {name})"
    return True, ""
