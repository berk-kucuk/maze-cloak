"""The Interfaces tab — which adapters get a new identity, and what they show now.

The tick box writes to `cfg.interfaces`, which the daemon reads as an allowlist.
Empty means "all physical interfaces", so the table starts fully ticked and
un-ticking the last box does not silently mean "all" again: the view keeps an
explicit list once the user has touched it.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from mazecloak.gui import format as fmt
from mazecloak.gui.theme import STATE_COLORS

_COLUMNS = ("col_cloak", "col_interface", "col_current", "col_hardware",
            "col_vendor", "col_type", "col_state")


class InterfacesView(QWidget):
    def __init__(self, state, controller):
        super().__init__()
        self._s = state
        self._c = controller
        self._suppress = False   # guards the checkbox handler during a rebuild

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)

        self._hint = QLabel()
        self._hint.setObjectName("hint")
        self._hint.setWordWrap(True)
        root.addWidget(self._hint)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self._table, 1)

        self._empty = QLabel()
        self._empty.setObjectName("hint")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setVisible(False)
        root.addWidget(self._empty)

        state.language_changed.connect(self.retranslate)
        self.refresh()

    # ── build ─────────────────────────────────────────────────────────────

    def _mono(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        font = item.font()
        font.setFamily("JetBrains Mono, Monospace, Courier New")
        item.setFont(font)
        return item

    def refresh(self) -> None:
        t = self._s.t
        self._hint.setText(t("iface_hint"))
        self._table.setHorizontalHeaderLabels([t(c) for c in _COLUMNS])

        ifaces = self._c.interfaces()
        self._empty.setText(t("iface_empty"))
        self._empty.setVisible(not ifaces)
        self._table.setVisible(bool(ifaces))

        self._suppress = True
        self._table.setRowCount(len(ifaces))
        for row, iface in enumerate(ifaces):
            box = QCheckBox()
            box.setChecked(iface.rotating)
            box.setEnabled(self._c.writable)
            box.toggled.connect(
                lambda checked, name=iface.name: self._on_toggle(name, checked))
            wrapper = QWidget()
            lay = QHBoxLayout(wrapper)
            lay.setContentsMargins(14, 0, 0, 0)
            lay.addWidget(box)
            lay.addStretch()
            self._table.setCellWidget(row, 0, wrapper)

            self._table.setItem(row, 1, QTableWidgetItem(iface.name))
            self._table.setItem(row, 2, self._mono(fmt.mac_or_dash(iface.mac)))

            original = self._c.original_of(iface.name)
            self._table.setItem(row, 3, self._mono(fmt.mac_or_dash(original)))

            self._table.setItem(row, 4, QTableWidgetItem(iface.vendor or "—"))
            self._table.setItem(row, 5, QTableWidgetItem(
                t("type_wireless") if iface.wireless else t("type_wired")))

            state_item = QTableWidgetItem(
                t("state_up") if iface.is_up else t("state_down"))
            state_item.setForeground(
                _colour(STATE_COLORS["on"] if iface.is_up else STATE_COLORS["idle"]))
            self._table.setItem(row, 6, state_item)
        self._suppress = False

    # ── actions ───────────────────────────────────────────────────────────

    def _on_toggle(self, name: str, checked: bool) -> None:
        if self._suppress:
            return
        # Materialise the implicit "all" into a real list before removing from
        # it, so unticking one adapter does not read back as "rotate everything".
        current = set(self._c.cfg.interfaces) or {
            i.name for i in self._c.interfaces()}
        if checked:
            current.add(name)
        else:
            current.discard(name)
        self._c.cfg.interfaces = sorted(current)
        self._c.save()

    def retranslate(self) -> None:
        self.refresh()


def _colour(hex_code: str):
    from PyQt6.QtGui import QColor
    return QColor(hex_code)
