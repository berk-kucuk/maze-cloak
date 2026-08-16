"""The Schedule tab — how often the address changes, and what it changes to.

Each strategy carries its own trade-off line rather than a tooltip: "fully
random" versus "keep my vendor prefix" is a privacy decision with a real cost
on either side, and a user picking blind will pick wrong.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QButtonGroup, QCheckBox, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QRadioButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from mazecloak.core.config import MAX_INTERVAL, MIN_INTERVAL
from mazecloak.core.mac import FULL_RANDOM, KEEP_VENDOR, RANDOM_VENDOR

_STRATEGIES = (
    (FULL_RANDOM,   "strategy_full_random",   "strategy_full_random_desc"),
    (KEEP_VENDOR,   "strategy_keep_vendor",   "strategy_keep_vendor_desc"),
    (RANDOM_VENDOR, "strategy_random_vendor", "strategy_random_vendor_desc"),
)


class ScheduleView(QWidget):
    def __init__(self, state, controller):
        super().__init__()
        self._s = state
        self._c = controller
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        self._body = QVBoxLayout(inner)
        self._body.setContentsMargins(24, 18, 24, 24)
        self._body.setSpacing(18)
        scroll.setWidget(inner)
        root.addWidget(scroll)

        self._rotation_group = self._build_rotation()
        self._strategy_group = self._build_strategy()
        self._body.addWidget(self._rotation_group)
        self._body.addWidget(self._strategy_group)
        self._body.addStretch()

        state.language_changed.connect(self.retranslate)
        self.load()

    # ── rotation ──────────────────────────────────────────────────────────

    def _build_rotation(self) -> QGroupBox:
        grp = QGroupBox()
        lay = QVBoxLayout(grp)
        lay.setSpacing(12)

        self._cb_rotate = QCheckBox()
        self._cb_rotate.toggled.connect(self._on_change)
        lay.addWidget(self._cb_rotate)

        row = QHBoxLayout()
        self._lbl_interval = QLabel()
        self._spin = QSpinBox()
        self._spin.setRange(MIN_INTERVAL, MAX_INTERVAL)
        self._spin.setFixedWidth(110)
        self._spin.valueChanged.connect(self._on_change)
        self._lbl_minutes = QLabel()
        self._lbl_minutes.setObjectName("hint")
        row.addSpacing(26)
        row.addWidget(self._lbl_interval)
        row.addWidget(self._spin)
        row.addWidget(self._lbl_minutes)
        row.addStretch()
        lay.addLayout(row)

        self._cb_on_start = QCheckBox()
        self._cb_on_start.toggled.connect(self._on_change)
        lay.addWidget(self._cb_on_start)

        self._cb_vpn = QCheckBox()
        self._cb_vpn.toggled.connect(self._on_change)
        lay.addWidget(self._cb_vpn)
        self._hint_vpn = QLabel()
        self._hint_vpn.setObjectName("hint")
        self._hint_vpn.setWordWrap(True)
        self._hint_vpn.setContentsMargins(26, 0, 0, 6)
        lay.addWidget(self._hint_vpn)

        self._cb_restore = QCheckBox()
        self._cb_restore.toggled.connect(self._on_change)
        lay.addWidget(self._cb_restore)

        return grp

    # ── strategy ──────────────────────────────────────────────────────────

    def _build_strategy(self) -> QGroupBox:
        grp = QGroupBox()
        lay = QVBoxLayout(grp)
        lay.setSpacing(10)

        self._radios: dict[str, QRadioButton] = {}
        self._descs: dict[str, QLabel] = {}
        self._group = QButtonGroup(self)

        for value, _label_key, _desc_key in _STRATEGIES:
            radio = QRadioButton()
            radio.toggled.connect(self._on_change)
            self._group.addButton(radio)
            self._radios[value] = radio
            lay.addWidget(radio)

            desc = QLabel()
            desc.setObjectName("hint")
            desc.setWordWrap(True)
            desc.setContentsMargins(26, 0, 0, 8)
            self._descs[value] = desc
            lay.addWidget(desc)

        return grp

    # ── binding ───────────────────────────────────────────────────────────

    def load(self) -> None:
        """Push config into the widgets without triggering a save."""
        self._loading = True
        cfg = self._c.cfg
        self._cb_rotate.setChecked(cfg.rotate_enabled)
        self._spin.setValue(cfg.rotate_minutes)
        self._cb_on_start.setChecked(cfg.rotate_on_start)
        self._cb_vpn.setChecked(cfg.pause_on_vpn)
        self._cb_restore.setChecked(cfg.restore_on_stop)
        radio = self._radios.get(cfg.strategy) or self._radios[FULL_RANDOM]
        radio.setChecked(True)
        self._loading = False
        self.retranslate()
        self._apply_enabled()

    def _on_change(self, *_args) -> None:
        if self._loading:
            return
        cfg = self._c.cfg
        cfg.rotate_enabled = self._cb_rotate.isChecked()
        cfg.rotate_minutes = self._spin.value()
        cfg.rotate_on_start = self._cb_on_start.isChecked()
        cfg.pause_on_vpn = self._cb_vpn.isChecked()
        cfg.restore_on_stop = self._cb_restore.isChecked()
        for value, radio in self._radios.items():
            if radio.isChecked():
                cfg.strategy = value
                break
        self._c.save()
        self._apply_enabled()

    def _apply_enabled(self) -> None:
        writable = self._c.writable
        for w in (self._cb_rotate, self._cb_on_start, self._cb_vpn,
                  self._cb_restore, *self._radios.values()):
            w.setEnabled(writable)
        # The interval only means anything while the timer is on.
        on = writable and self._cb_rotate.isChecked()
        self._spin.setEnabled(on)
        self._lbl_interval.setEnabled(on)

    # ── text ──────────────────────────────────────────────────────────────

    def retranslate(self) -> None:
        t = self._s.t
        self._rotation_group.setTitle(t("sched_group"))
        self._cb_rotate.setText(t("sched_enable"))
        self._lbl_interval.setText(t("sched_interval"))
        self._lbl_minutes.setText(t("sched_minutes"))
        self._cb_on_start.setText(t("sched_on_start"))
        self._cb_vpn.setText(t("sched_pause_vpn"))
        self._hint_vpn.setText(t("sched_pause_vpn_hint"))
        self._cb_restore.setText(t("sched_restore"))

        self._strategy_group.setTitle(t("strategy_group"))
        for value, label_key, desc_key in _STRATEGIES:
            self._radios[value].setText(t(label_key))
            self._descs[value].setText(t(desc_key))

    def refresh(self) -> None:
        # Re-sync only when something else changed the file underneath us;
        # otherwise typing in the spin box would fight the timer.
        if not self.isVisible():
            self.load()
