"""MAC address generation, parsing and vendor lookup.

Every address this module invents has the locally-administered bit set and the
multicast bit clear. That is not cosmetic: a multicast-bit address is not a
valid source address and switches may drop the frames, and an address without
the locally-administered bit claims to be a real burned-in address belonging to
whoever owns that OUI, which is exactly the collision this tool should not
cause.
"""
from __future__ import annotations

import random
import re

_MAC_RE = re.compile(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")

# Generation strategies, in the order they appear in the UI.
FULL_RANDOM = "full_random"
KEEP_VENDOR = "keep_vendor"
RANDOM_VENDOR = "random_vendor"

STRATEGIES = (FULL_RANDOM, KEEP_VENDOR, RANDOM_VENDOR)

# Real, widely-deployed OUIs used by RANDOM_VENDOR. Blending in with common
# consumer hardware is the point: a fully random prefix is itself distinctive on
# a network where every other device reports a recognisable vendor.
#
# NOTE: the locally-administered bit is still forced on after the prefix is
# applied, so these never impersonate a genuine factory address — they only
# borrow the shape of one.
VENDOR_OUIS: tuple[tuple[str, str], ...] = (
    ("00:1a:11", "Google"),
    ("3c:5a:b4", "Google"),
    ("00:03:93", "Apple"),
    ("a4:83:e7", "Apple"),
    ("f0:18:98", "Apple"),
    ("00:16:6c", "Samsung"),
    ("5c:0a:5b", "Samsung"),
    ("00:1d:0f", "TP-Link"),
    ("50:c7:bf", "TP-Link"),
    ("00:1f:3f", "ASUSTek"),
    ("2c:56:dc", "ASUSTek"),
    ("00:0c:29", "VMware"),
    ("00:15:5d", "Microsoft"),
    ("b8:27:eb", "Raspberry Pi"),
    ("dc:a6:32", "Raspberry Pi"),
    ("00:e0:4c", "Realtek"),
    ("00:1b:63", "Intel"),
    ("94:65:9c", "Intel"),
    ("00:26:b9", "Dell"),
    ("00:21:5a", "HP"),
    ("00:24:d7", "Lenovo"),
    ("f4:8e:38", "Xiaomi"),
    ("64:09:80", "Xiaomi"),
    ("00:9a:cd", "Huawei"),
)


def is_valid(mac: str) -> bool:
    return bool(_MAC_RE.match(mac or ""))


def is_locally_administered(mac: str) -> bool:
    """True when the address is one that was assigned rather than burned in."""
    try:
        return bool(int(mac.split(":")[0], 16) & 0x02)
    except (ValueError, IndexError, AttributeError):
        return False


def normalise(mac: str) -> str:
    return (mac or "").strip().lower()


def _local_unicast(first_byte: int) -> int:
    """Set the locally-administered bit, clear the multicast bit."""
    return (first_byte & 0xFE) | 0x02


# Returned by vendor_of() for any assigned address. A sentinel rather than a
# free string so the UI can branch on it instead of matching prose.
LOCAL_VENDOR = "locally administered"


def vendor_of(mac: str) -> str:
    """Best-effort vendor name from the OUI, or "" when it is not one we know.

    A locally-administered address is reported as such rather than matched
    against the table: after the bit is forced on the prefix no longer belongs
    to the vendor it was copied from, and saying otherwise would be a lie the
    rest of the UI then repeats.
    """
    if not is_valid(mac):
        return ""
    if is_locally_administered(mac):
        return LOCAL_VENDOR
    prefix = normalise(mac)[:8]
    for oui, name in VENDOR_OUIS:
        if oui == prefix:
            return name
    return ""


def random_mac(strategy: str = FULL_RANDOM, current: str | None = None) -> str:
    """Generate an address according to `strategy`.

    KEEP_VENDOR falls back to FULL_RANDOM when `current` is missing or
    unparseable rather than raising: the caller is a rotation timer, and a
    failed rotation is worse than a differently-shaped address.
    """
    tail = [random.randint(0, 255) for _ in range(3)]

    if strategy == KEEP_VENDOR and is_valid(current or ""):
        head = [int(p, 16) for p in normalise(current).split(":")[:3]]
    elif strategy == RANDOM_VENDOR:
        oui, _name = random.choice(VENDOR_OUIS)
        head = [int(p, 16) for p in oui.split(":")]
    else:
        head = [random.randint(0, 255) for _ in range(3)]

    head[0] = _local_unicast(head[0])
    return ":".join(f"{b:02x}" for b in head + tail)
