"""One source of truth for every view.

The widgets never touch the config file, the state file or systemd directly.
They read properties here and call methods here, which means the "did the save
actually work" question is answered in exactly one place — and the read-only
case (no `maze` group membership) cannot be forgotten by a view that happens to
write its own setting.
"""
from __future__ import annotations

import time

from PyQt6.QtCore import QObject, pyqtSignal

from mazecloak.core import nm, paths, service
from mazecloak.core import interfaces as ifaces
from mazecloak.core.config import (
    CloakConfig, UiConfig, config_writable, load_config, load_ui,
    save_config, save_ui,
)
from mazecloak.core.state import DaemonState, read_state

# Overall status, in the order the Overview tab tests them.
ST_NO_DAEMON = "no_daemon"     # unit not installed
ST_DAEMON_OFF = "daemon_off"   # installed, not running
ST_OFF = "off"                 # running, cloak disabled
ST_VPN = "vpn"                 # enabled but held back by a tunnel
ST_MANUAL = "manual"           # enabled, no timer
ST_ON = "on"                   # enabled and rotating


class CloakController(QObject):
    config_changed = pyqtSignal()
    state_changed = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.cfg: CloakConfig = load_config()
        self.ui: UiConfig = load_ui()
        self.state: DaemonState | None = read_state()
        self._service_available = service.available()

    # ── refresh ───────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Re-read everything the daemon owns. Driven by the window's timer."""
        before = (self.state.to_dict() if self.state else None)
        self.state = read_state()
        # Reload the config too: the daemon does not write it, but a second
        # Maze Cloak window or a hand edit might have.
        self.cfg = load_config()
        if (self.state.to_dict() if self.state else None) != before:
            self.state_changed.emit()

    # ── status ────────────────────────────────────────────────────────────

    @property
    def daemon_installed(self) -> bool:
        return self._service_available

    @property
    def daemon_running(self) -> bool:
        return bool(self.state and self.state.running)

    @property
    def writable(self) -> bool:
        return config_writable()

    def status(self) -> str:
        if not self._service_available:
            return ST_NO_DAEMON
        if not self.daemon_running:
            return ST_DAEMON_OFF
        if not self.cfg.enabled:
            return ST_OFF
        paused = self.state.paused if self.state else ""
        if paused == "vpn":
            return ST_VPN
        if not self.cfg.rotate_enabled:
            return ST_MANUAL
        return ST_ON

    def nm_status(self) -> str:
        """"ours" | "elsewhere" | "off" — what the other Maze tools will report."""
        if nm.is_active():
            return "ours"
        if nm.detected_elsewhere():
            return "elsewhere"
        return "off"

    def interfaces(self) -> list[ifaces.Interface]:
        """Live interface list, annotated with what the daemon is rotating."""
        selected = set(self.cfg.interfaces)
        out = []
        for iface in ifaces.list_interfaces():
            iface.rotating = (not selected) or (iface.name in selected)
            out.append(iface)
        return out

    def original_of(self, name: str) -> str:
        """The hardware address the daemon recorded, falling back to the driver's."""
        if self.state and name in self.state.interfaces:
            original = self.state.interfaces[name].original
            if original:
                return original
        return ifaces.permanent_mac(name)

    # ── mutations ─────────────────────────────────────────────────────────

    def save(self) -> bool:
        """Persist the daemon config. Emits `error` and returns False on failure."""
        try:
            save_config(self.cfg)
        except PermissionError:
            self.error.emit("readonly")
            return False
        except OSError as e:
            self.error.emit(str(e))
            return False
        self.config_changed.emit()
        return True

    def set_enabled(self, enabled: bool) -> bool:
        self.cfg.enabled = enabled
        return self.save()

    def request_rotation(self) -> bool:
        """Ask the daemon to rotate now.

        Only meaningful while the cloak is on; the daemon ignores the request
        otherwise, and the Overview tab disables the button to match.
        """
        self.cfg.rotate_request = time.time()
        return self.save()

    def save_ui_prefs(self) -> None:
        save_ui(self.ui)

    # ── daemon control (pkexec) ───────────────────────────────────────────

    def start_daemon(self) -> bool:
        ok, err = service.enable()
        if not ok and err != "cancelled":
            self.error.emit(err)
        self._service_available = service.available()
        return ok

    def stop_daemon(self) -> bool:
        ok, err = service.disable()
        if not ok and err != "cancelled":
            self.error.emit(err)
        return ok

    @property
    def config_path_str(self) -> str:
        return str(paths.CONFIG_PATH)
