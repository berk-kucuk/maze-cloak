<div align="center">

# MAZE CLOAK

**MAC Address Randomisation**

*Scheduled rotation · NetworkManager integration · VPN-aware · Maze suite status reporting*

---

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)](https://python.org)
[![PyQt6](https://img.shields.io/badge/UI-PyQt6-green?style=flat-square)](https://pypi.org/project/PyQt6/)
[![Platform](https://img.shields.io/badge/Platform-Linux-orange?style=flat-square&logo=linux)](https://kernel.org)
[![License](https://img.shields.io/badge/License-GPL3-lightgrey?style=flat-square)](LICENSE)

</div>

---

## What is Maze Cloak?

Your network adapter's MAC address is a permanent, globally unique serial number that every access point you pass sees — whether or not you connect to it. Maze Cloak replaces it with a randomised one and, optionally, keeps changing it on a schedule.

It is the companion to [Maze Guard](https://github.com/berk-kucuk/maze-guard): Guard defends the connection, Cloak hides who is making it.

The window runs as your normal user and never asks for a password. A small daemon runs as root under systemd and performs the actual change.

---

## Three layers of randomisation

They cover different moments, and the tool turns on all three by default because a gap in any one of them re-links you.

| Layer | Covers | Handled by |
|---|---|---|
| **Scan randomisation** | The address broadcast while looking for networks — leaked to every AP in range, connected or not | NetworkManager drop-in |
| **Connection randomisation** | The address used once associated with a network | NetworkManager drop-in |
| **Scheduled rotation** | The address while you stay connected — the case NetworkManager does not cover | Maze Cloak daemon (`ip link`) |

---

## Features

### Rotation
- **Timer-based rotation** — every 1 minute to 1 week; the daemon keeps rotating whether or not the window is open
- **Rotate immediately on enable**, and on demand from the window or the tray menu
- **VPN-aware pause** — changing an address bounces the link a tunnel runs over, which drops the VPN. Rotation is suspended while a tunnel is up, and the interval clock is held rather than banked, so a rotation does not fire the instant the tunnel closes
- **Restore on stop** — the burned-in address is put back when the cloak is turned off, when the daemon stops, and when the package is removed

### Address style
| Strategy | What it does | Trade-off |
|---|---|---|
| **Fully random** | Every byte random | Maximum unlinkability; stands out on a network of recognisable vendors |
| **Keep my vendor prefix** | Keeps your real OUI, randomises the rest | Blends in; leaks your adapter's make |
| **Random vendor prefix** | Borrows the shape of a common consumer OUI | Blends in without revealing your hardware |

Every generated address has the locally-administered bit set and the multicast bit clear, so it never impersonates a genuine factory address and is never an invalid source address.

### Interface control
- Per-interface opt-in; virtual devices (bridges, tunnels, VPN, docker, `lo`) are refused outright
- Live table of current address, hardware address, vendor, type and link state
- The hardware address is recorded **before** the first rotation and persisted, so a daemon restarted mid-cloak never adopts a random address as the one to restore to

### Integration with the Maze suite
Maze Cloak writes `/etc/NetworkManager/conf.d/99-maze-cloak.conf`. **Maze Control Center reads exactly that file** to decide whether to report *MAC randomisation: Enabled*, so turning the cloak on here shows up there, and turning it off removes the claim. The Overview tab reports what the rest of the suite currently sees, including the case where a *different* tool enabled randomisation first.

### Interface
- Frameless window in the shared Maze visual language, dark and light
- **Tray-first**: autostarts hidden; toggle the cloak and rotate on demand from the tray menu
- English + Turkish with live switching
- `maze-cloak --status` for the same picture in a terminal, over SSH

---

## Requirements

- **OS:** Linux, systemd
- **Python:** 3.11+
- **Required:** `iproute2`, `polkit`
- **Optional:** `ethtool` (read the burned-in address exactly), `networkmanager` (scan/connection layers and suite status reporting)

---

## Installation

### From the Maze repository

**On Maze Linux** the repository is already configured:

```bash
sudo pacman -S maze-cloak
```

**On Arch Linux and Arch-based distributions**, add the repository once:

1. Import and trust the Maze signing key:

   ```bash
   curl -O https://mazerepo.berkkucukk.com.tr/packages/mazelinux.gpg
   gpg --show-keys --with-fingerprint mazelinux.gpg
   sudo pacman-key --add mazelinux.gpg
   sudo pacman-key --lsign-key 7C4D515A6B930CB04794CEF6147C8159B3E2EE5F
   ```

   The fingerprint `gpg` prints must be `7C4D 515A 6B93 0CB0 4794  CEF6 147C 8159 B3E2 EE5F`.

2. Add the repository to the end of `/etc/pacman.conf`:

   ```ini
   [mazelinux]
   SigLevel = Required DatabaseOptional
   Server = https://mazerepo.berkkucukk.com.tr/packages
   ```

3. Sync and install:

   ```bash
   sudo pacman -Syu maze-cloak
   ```

Optionally install `mazelinux-keyring` as well; it keeps the signing key up to date through pacman.

Remove with `sudo pacman -Rns maze-cloak`.

### Build from source

```bash
sudo pacman -S --needed base-devel git imagemagick
git clone https://github.com/berk-kucuk/maze-cloak.git
cd maze-cloak
./build-pkg.sh
sudo pacman -U dist-pkg/maze-cloak-*-x86_64.pkg.tar.zst
```

The script runs the test suite, builds the package into `./dist-pkg/`, and stops. It never installs and never asks for a password; `pacman -U` pulls in the runtime dependencies.

`maze-python` (the shared Python runtime) comes from the Maze repository, so add the repository first (steps 1–2 above).

### After installing

**Log out and back in once** so your new `maze` group membership applies, then start the daemon — from the app's Overview tab, or:

```bash
sudo systemctl enable --now maze-cloak.service
```

The package deliberately does not enable the daemon for you: turning on randomisation changes how your machine appears on every network it joins, which is your decision to make, not the installer's.

### Running from a source checkout

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Without the daemon installed the window runs read-only and says so. To point the app at a scratch directory instead of `/etc` — useful when developing:

```bash
export MAZE_CLOAK_ETC=/tmp/mc/etc MAZE_CLOAK_RUN=/tmp/mc/run \
       MAZE_CLOAK_VAR=/tmp/mc/var MAZE_CLOAK_NM=/tmp/mc/99-maze-cloak.conf
```

---

## Architecture

```
┌──────────────────────────────────────────────┐
│  GUI  (your user, no password, tray-first)   │
│                                              │
│  PyQt6 ──► CloakController                   │
│               │ writes            │ reads    │
└───────────────┼───────────────────┼──────────┘
                ▼                   ▲
   /etc/maze-cloak/config.json   /run/maze-cloak/state.json
        root:maze 0664                  0644
                ▼                   ▲
┌───────────────┼───────────────────┼──────────┐
│  Daemon (root, systemd)                      │
│    ip link set … address    (the MAC change) │
│    /etc/NetworkManager/conf.d/99-maze-cloak  │
│    /var/lib/maze-cloak/originals.json        │
└──────────────────────────────────────────────┘
```

There is no socket and no protocol. The GUI writes a config file; the daemon polls it and publishes a state file. One direction each way, and nothing to get wrong in between.

---

## Security model

- **No password for day-to-day use, and no sudo anywhere.** The config file is `root:maze` mode `0664`, so a member of the `maze` group — the same group Maze Guard uses — changes settings by writing a file. The daemon picks the change up on its next tick.
- **`pkexec` is not used.** Starting and stopping the daemon calls `systemctl` directly, which raises systemd's own narrow polkit actions carrying the unit name. The shipped rule (`49-maze-cloak.rules`) grants those to the `maze` group **for `maze-cloak.service` only**. A `pkexec` rule broad enough to be silent would have authorised running *any* program as root.
- **The GUI never touches an interface.** Every privileged operation lives in the daemon. The window's most dangerous power is writing a JSON file it is already permitted to write.
- **A rotation that did not happen is reported as a failure.** After every change the kernel is re-read; if NetworkManager reasserted the old address, that is surfaced as an error rather than counted as a rotation. Silent no-ops are the failure mode this kind of tool actually has.
- **Privileged calls are guarded at the source.** `nmcli general reload` is a polkit-authorised operation, so it refuses to run unless the caller is already root — a user-context call returns quietly instead of raising a password dialog on a timer.
- **The suite-wide status flag cannot outlive the daemon.** The NetworkManager drop-in is removed on shutdown and on package removal, so no other Maze tool reports "Enabled" for something that stopped running.
- **Virtual interfaces are refused.** Bridges, tunnels, VPN and container interfaces are never touched: their address is not visible to the network you are trying to be anonymous on, and changing it breaks what it carries.

---

## Configuration

`/etc/maze-cloak/config.json`, written by the app and read by the daemon.

| Key | Description |
|---|---|
| `enabled` | Master switch; everything else is inert while false |
| `strategy` | `full_random` \| `keep_vendor` \| `random_vendor` |
| `interfaces` | Interfaces to rotate; empty means every physical one |
| `rotate_enabled` / `rotate_minutes` | Timer rotation and its interval |
| `rotate_on_start` | Rotate the moment the cloak is enabled |
| `pause_on_vpn` | Suspend rotation while a tunnel is up |
| `restore_on_stop` | Put the hardware address back when stopping |
| `nm_integration` | Write the NetworkManager drop-in (also the suite status flag) |
| `nm_wifi_scan_rand` | Randomise the scan-time address |
| `nm_cloned_mode` | `random` (per connection) \| `stable` (per network) |

`stable` is worth knowing about: it keeps captive portals and MAC-based Wi-Fi allowlists working, at the cost of being linkable across visits to the same network.

---

## Testing

```bash
python3 tests/test_core.py
```

The suite blocks `subprocess` outright, so no test can shell out, touch an interface, or raise an authentication prompt. Coverage is aimed at the failures that are otherwise silent: reverted rotations, restoring to a previously-randomised address, VPN pauses banking an overdue rotation, stale state files, and the two i18n tables drifting apart.

---

## License

Copyright © 2026 Berk Küçük

GPL3 — see [LICENSE](LICENSE).

---

<div align="center">
<sub>Part of the Maze suite · Built for Linux · Tested on Arch Linux</sub>
</div>
