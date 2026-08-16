"""The card primitive every view is built from.

Same shape as Maze Guard's InfoCard — a small-caps title over key/value rows,
optionally with a status dot — so the two apps' dashboards read as one product.
Rows are addressed by a stable key so a refresh updates text in place instead
of rebuilding the layout, which is what keeps the window from flickering on a
two-second timer.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QLabel, QSizePolicy, QVBoxLayout,
)


def dot(color: str, size: int = 9) -> QLabel:
    lbl = QLabel("●")
    lbl.setStyleSheet(f"color: {color}; font-size: {size}px; background: transparent;")
    return lbl


class InfoCard(QFrame):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(10)

        self._title = QLabel(title.upper())
        self._title.setObjectName("card_title")
        outer.addWidget(self._title)

        self._grid = QGridLayout()
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(14)
        self._grid.setVerticalSpacing(6)
        self._grid.setColumnStretch(1, 1)
        outer.addLayout(self._grid)
        outer.addStretch()

        self._row = 0
        self._values: dict[str, QLabel] = {}
        self._keys: dict[str, QLabel] = {}
        self._dots: dict[str, QLabel] = {}

    def set_title(self, text: str) -> None:
        self._title.setText(text.upper())

    def add_row(self, key: str, key_text: str, value_text: str = "",
                mono: bool = False) -> None:
        k = QLabel(key_text)
        k.setObjectName("card_key")
        v = QLabel(value_text)
        v.setObjectName("mono" if mono else "card_value")
        v.setWordWrap(not mono)
        self._keys[key] = k
        self._values[key] = v
        self._grid.addWidget(k, self._row, 0, Qt.AlignmentFlag.AlignTop)
        self._grid.addWidget(v, self._row, 1)
        self._row += 1

    def add_status_row(self, key: str, color: str, value_text: str) -> None:
        d = dot(color)
        v = QLabel(value_text)
        v.setObjectName("card_value")
        v.setStyleSheet("font-size: 15px; font-weight: bold; background: transparent;")
        self._dots[key] = d
        self._values[key] = v
        self._grid.addWidget(d, self._row, 0, Qt.AlignmentFlag.AlignVCenter)
        self._grid.addWidget(v, self._row, 1, Qt.AlignmentFlag.AlignVCenter)
        self._row += 1

    def set_value(self, key: str, text: str) -> None:
        if key in self._values:
            self._values[key].setText(text)

    def set_key_text(self, key: str, text: str) -> None:
        if key in self._keys:
            self._keys[key].setText(text)

    def set_dot(self, key: str, color: str) -> None:
        if key in self._dots:
            self._dots[key].setStyleSheet(
                f"color: {color}; font-size: 9px; background: transparent;")
