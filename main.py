#!/usr/bin/env python3
import sys


def _usage() -> None:
    print(
        "Maze Cloak — MAC address randomisation for the Maze suite\n"
        "\n"
        "  maze-cloak                 start the interface\n"
        "  maze-cloak --background    start hidden in the system tray\n"
        "  maze-cloak --status        print the current state and exit\n"
        "  maze-cloak --version       print the version\n"
        "\n"
        "The rotation itself is performed by maze-cloak.service, which runs as\n"
        "root under systemd. This window only reads and writes its settings.\n"
    )


def _status() -> int:
    """A terminal-sized version of the Overview tab.

    Exists so the daemon can be sanity-checked over SSH, and so a packaging
    script can assert the thing actually came up without launching a GUI.
    """
    from mazecloak.core import nm, service
    from mazecloak.core.config import load_config
    from mazecloak.core.interfaces import list_interfaces
    from mazecloak.core.state import read_state

    cfg = load_config()
    state = read_state()

    print(f"cloak       : {'enabled' if cfg.enabled else 'disabled'}")
    print(f"daemon      : "
          f"{'running' if state and state.running else 'not running'}"
          f"{'' if service.available() else '  (unit not installed)'}")
    if cfg.rotate_enabled:
        print(f"rotation    : every {cfg.rotate_minutes} min  ({cfg.strategy})")
    else:
        print(f"rotation    : manual only  ({cfg.strategy})")
    if state and state.paused:
        print(f"paused      : {state.paused}")
    print(f"nm drop-in  : {'present' if nm.is_active() else 'absent'}"
          f"{'  (another tool enables randomisation)' if nm.detected_elsewhere() else ''}")

    print("\ninterfaces:")
    selected = set(cfg.interfaces)
    # A one-shot print can afford the ethtool call the GUI's timer cannot.
    for iface in list_interfaces(with_permanent=True):
        rotating = (not selected) or (iface.name in selected)
        original = ""
        if state and iface.name in state.interfaces:
            original = state.interfaces[iface.name].original
        print(f"  {'*' if rotating else ' '} {iface.name:<12} {iface.mac or '—':<18}"
              f" hw={original or iface.permanent or '—':<18}"
              f" {'wifi' if iface.wireless else 'wired'}  {iface.state}")
    return 0


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        _usage()
    elif "--version" in sys.argv:
        from mazecloak import __version__
        print(f"maze-cloak {__version__}")
    elif "--status" in sys.argv:
        sys.exit(_status())
    else:
        from mazecloak.gui.app import run
        sys.exit(run())
