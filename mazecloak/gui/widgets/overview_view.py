"""The Overview tab — the answer to "what is this machine showing the network?".

That question has a literal answer, and it is an address, so the address is the
headline: set in mono at display size, with the hardware address it is standing
in for underneath. Monospace is earned here — this is data being compared
digit by digit, not decoration.

The supporting facts sit in one dense strip rather than a row of equal cards.
Three same-sized cards, each a label over a short value, is the layout that made
this window read as empty: it spreads four facts across the full width and still
leaves each container two-thirds hollow.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from mazecloak.core.mac import LOCAL_VENDOR
from mazecloak.gui import format as fmt
from mazecloak.gui.controller import (
    ST_DAEMON_OFF, ST_MANUAL, ST_NO_DAEMON, ST_OFF, ST_ON, ST_VPN,
)
from mazecloak.gui.theme import STATE_COLORS
from mazecloak.gui.widgets.cards import dot

_STATUS_TEXT = {
    ST_ON:         ("state_on", "on"),
    ST_MANUAL:     ("state_no_schedule", "partial"),
    ST_VPN:        ("state_paused_vpn", "partial"),
    ST_OFF:        ("state_off", "off"),
    ST_DAEMON_OFF: ("state_daemon_off", "idle"),
    ST_NO_DAEMON:  ("state_daemon_off", "idle"),
}

_STRATEGY_KEY = {
    "full_random": "strategy_full_random",
    "keep_vendor": "strategy_keep_vendor",
    "random_vendor": "strategy_random_vendor",
}


def _label(text: str = "") -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("label")
    return lbl


class OverviewView(QWidget):
    def __init__(self, state, controller):
        super().__init__()
        self._s = state
        self._c = controller
        self._iface_rows: list[tuple[QLabel, QLabel, QLabel, QLabel]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        self._body = QVBoxLayout(inner)
        self._body.setContentsMargins(24, 20, 24, 24)
        self._body.setSpacing(16)
        scroll.setWidget(inner)
        root.addWidget(scroll)

        self._build_hero()
        self._build_stats()
        self._build_interfaces()
        self._build_footer()
        self._body.addStretch()

        state.language_changed.connect(self.retranslate)
        self.refresh()

    # ── hero ──────────────────────────────────────────────────────────────

    def _build_hero(self) -> None:
        hero = QFrame()
        hero.setObjectName("hero")
        outer = QVBoxLayout(hero)
        outer.setContentsMargins(26, 22, 26, 24)
        outer.setSpacing(18)

        # Top line: state, and the controls that change it.
        top = QHBoxLayout()
        top.setSpacing(12)
        self._dot = dot(STATE_COLORS["idle"], 13)
        top.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)

        self._status_lbl = QLabel()
        self._status_lbl.setObjectName("hero_status")
        top.addWidget(self._status_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addStretch()

        self._rotate_btn = QPushButton()
        self._rotate_btn.clicked.connect(self._on_rotate)
        top.addWidget(self._rotate_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self._switch = QPushButton()
        self._switch.setObjectName("primary_switch")
        self._switch.clicked.connect(self._on_switch)
        top.addWidget(self._switch, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addLayout(top)

        # The address itself.
        addr = QVBoxLayout()
        addr.setSpacing(6)
        self._showing_lbl = _label()
        addr.addWidget(self._showing_lbl)

        self._mac_lbl = QLabel("—")
        self._mac_lbl.setObjectName("hero_mac")
        self._mac_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        addr.addWidget(self._mac_lbl)

        self._mac_meta = QLabel()
        self._mac_meta.setObjectName("hero_meta")
        self._mac_meta.setWordWrap(True)
        addr.addWidget(self._mac_meta)
        outer.addLayout(addr)

        self._body.addWidget(hero)

    # ── stat strip ────────────────────────────────────────────────────────

    def _build_stats(self) -> None:
        card = QFrame()
        card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setContentsMargins(26, 18, 26, 18)
        grid.setHorizontalSpacing(30)
        grid.setVerticalSpacing(5)

        self._stats: dict[str, tuple[QLabel, QLabel]] = {}
        for col, key in enumerate(("next", "interval", "count", "style")):
            key_lbl = _label()
            val_lbl = QLabel("—")
            val_lbl.setObjectName("stat")
            grid.addWidget(key_lbl, 0, col)
            grid.addWidget(val_lbl, 1, col)
            grid.setColumnStretch(col, 1)
            self._stats[key] = (key_lbl, val_lbl)

        self._body.addWidget(card)

    # ── interfaces ────────────────────────────────────────────────────────

    def _build_interfaces(self) -> None:
        self._iface_label = _label()
        self._body.addWidget(self._iface_label)

        self._iface_card = QFrame()
        self._iface_card.setObjectName("card")
        self._iface_layout = QVBoxLayout(self._iface_card)
        self._iface_layout.setContentsMargins(26, 8, 26, 8)
        self._iface_layout.setSpacing(0)
        self._body.addWidget(self._iface_card)

    def _iface_row(self) -> tuple[QLabel, QLabel, QLabel, QLabel]:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 11, 0, 11)
        lay.setSpacing(16)

        name = QLabel()
        name.setStyleSheet("font-weight: bold; background: transparent;")
        name.setFixedWidth(110)

        mac = QLabel()
        mac.setObjectName("mono")
        mac.setFixedWidth(180)

        meta = QLabel()
        meta.setObjectName("hint")

        state = QLabel()
        state.setObjectName("hint")
        state.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        lay.addWidget(name)
        lay.addWidget(mac)
        lay.addWidget(meta, 1)
        lay.addWidget(state)

        self._iface_layout.addWidget(row)
        return name, mac, meta, state

    # ── footer ────────────────────────────────────────────────────────────

    def _build_footer(self) -> None:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(4, 2, 4, 0)
        lay.setSpacing(10)

        self._nm_dot = dot(STATE_COLORS["idle"], 8)
        self._nm_lbl = QLabel()
        self._nm_lbl.setObjectName("hint")
        self._nm_lbl.setWordWrap(True)

        lay.addWidget(self._nm_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._nm_lbl, 1)
        self._body.addWidget(row)

    # ── actions ───────────────────────────────────────────────────────────

    def _on_switch(self) -> None:
        status = self._c.status()
        if status == ST_NO_DAEMON:
            return
        if status == ST_DAEMON_OFF:
            self._c.start_daemon()
        else:
            self._c.set_enabled(not self._c.cfg.enabled)
        self.refresh()

    def _on_rotate(self) -> None:
        self._c.request_rotation()
        self.refresh()

    # ── refresh ───────────────────────────────────────────────────────────

    def _primary(self, ifaces):
        """The interface the hero speaks for: the live one being cloaked."""
        rotating = [i for i in ifaces if i.rotating]
        for candidate in (rotating, ifaces):
            up = [i for i in candidate if i.is_up]
            if up:
                return up[0]
            if candidate:
                return candidate[0]
        return None

    def refresh(self) -> None:
        t = self._s.t
        status = self._c.status()
        key, colour = _STATUS_TEXT.get(status, ("state_off", "off"))

        self._dot.setStyleSheet(
            f"color: {STATE_COLORS[colour]}; font-size: 13px; background: transparent;")
        self._status_lbl.setText(t(key))

        cloaked = status in (ST_ON, ST_MANUAL, ST_VPN)

        if status == ST_NO_DAEMON:
            self._switch.setText(t("btn_daemon_start"))
            self._switch.setEnabled(False)
        elif status == ST_DAEMON_OFF:
            self._switch.setText(t("btn_daemon_start"))
            self._switch.setEnabled(True)
        else:
            self._switch.setText(
                t("btn_disable") if self._c.cfg.enabled else t("btn_enable"))
            self._switch.setEnabled(self._c.writable)

        self._switch.setProperty("active", self._c.cfg.enabled)
        self._switch.style().unpolish(self._switch)
        self._switch.style().polish(self._switch)

        self._rotate_btn.setText(t("btn_rotate_now"))
        self._rotate_btn.setVisible(cloaked)
        self._rotate_btn.setEnabled(self._c.writable and status != ST_VPN)

        self._refresh_address(cloaked, status)
        self._refresh_stats()
        self._refresh_interfaces()
        self._refresh_footer()

    def _refresh_address(self, cloaked: bool, status: str) -> None:
        t = self._s.t
        ifaces = self._c.interfaces()
        primary = self._primary(ifaces)

        if primary is None:
            self._showing_lbl.setText(t("hero_showing"))
            self._mac_lbl.setText("—")
            self._mac_meta.setText(t("iface_empty"))
            return

        self._showing_lbl.setText(t("hero_showing"))
        self._mac_lbl.setText(fmt.mac_or_dash(primary.mac))

        hardware = self._c.original_of(primary.name)
        bits = [primary.name]
        if primary.vendor == LOCAL_VENDOR:
            # "appears as locally administered" is not something a network sees;
            # what it sees is an address with no vendor behind it.
            bits.append(t("hero_no_vendor"))
        elif primary.vendor:
            bits.append(f"{t('hero_appears_as')} {primary.vendor}")
        if hardware and hardware != primary.mac:
            bits.append(f"{t('hero_hardware')} {fmt.mac_or_dash(hardware)}")

        # When nothing is cloaking it, the address on screen *is* the permanent
        # one — say so plainly rather than leaving the reader to infer it.
        if not cloaked:
            bits.append(t("hero_exposed"))
        self._mac_meta.setText("  ·  ".join(bits))

    def _refresh_stats(self) -> None:
        t = self._s.t
        st, cfg = self._c.state, self._c.cfg

        labels = {"next": "lbl_next", "interval": "lbl_interval",
                  "count": "lbl_count", "style": "lbl_strategy"}
        for key, i18n_key in labels.items():
            self._stats[key][0].setText(t(i18n_key))

        never, due = t("lbl_never"), t("lbl_due")
        self._stats["next"][1].setText(
            fmt.until(st.next_rotation if st else 0.0, never, due))
        self._stats["interval"][1].setText(
            f"{cfg.rotate_minutes} {t('sched_minutes')}" if cfg.rotate_enabled
            else t("lbl_none"))
        total = sum(i.rotations for i in st.interfaces.values()) if st else 0
        self._stats["count"][1].setText(str(total))
        self._stats["style"][1].setText(
            t(_STRATEGY_KEY.get(cfg.strategy, "strategy_full_random")))

    def _refresh_interfaces(self) -> None:
        t = self._s.t
        self._iface_label.setText(t("sec_cloaked_interfaces"))

        ifaces = [i for i in self._c.interfaces() if i.rotating]
        while len(self._iface_rows) < len(ifaces):
            self._iface_rows.append(self._iface_row())

        for widgets, iface in zip(self._iface_rows, ifaces):
            name, mac, meta, state = widgets
            for w in widgets:
                w.parentWidget().setVisible(True)
            name.setText(iface.name)
            mac.setText(fmt.mac_or_dash(iface.mac))
            meta.setText(t("type_wireless") if iface.wireless else t("type_wired"))
            up = iface.is_up
            state.setText(t("state_up") if up else t("state_down"))
            state.setStyleSheet(
                f"color: {STATE_COLORS['on'] if up else STATE_COLORS['idle']};"
                "font-size: 11px; background: transparent;")

        for widgets in self._iface_rows[len(ifaces):]:
            widgets[0].parentWidget().setVisible(False)

        self._iface_card.setVisible(bool(ifaces))
        self._iface_label.setVisible(bool(ifaces))

    def _refresh_footer(self) -> None:
        t = self._s.t
        nm_state = self._c.nm_status()
        if nm_state == "ours":
            self._nm_dot.setStyleSheet(
                f"color: {STATE_COLORS['on']}; font-size: 8px; background: transparent;")
            self._nm_lbl.setText(f"{t('nm_active')} — {t('nm_hint')}")
        elif nm_state == "elsewhere":
            self._nm_dot.setStyleSheet(
                f"color: {STATE_COLORS['partial']}; font-size: 8px; background: transparent;")
            self._nm_lbl.setText(f"{t('nm_elsewhere')} — {t('nm_hint')}")
        else:
            self._nm_dot.setStyleSheet(
                f"color: {STATE_COLORS['idle']}; font-size: 8px; background: transparent;")
            self._nm_lbl.setText(f"{t('nm_inactive')} — {t('nm_hint')}")

    def retranslate(self) -> None:
        self.refresh()
