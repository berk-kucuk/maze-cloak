"""Shared Maze visual language.

The palette is Maze Guard's, on purpose: the two apps sit next to each other in
the tray and a user should not be able to tell which codebase drew the chrome.

Two things here are corrections rather than copies, and both were failures of
legibility rather than taste:

**`label`.** Maze Guard's `text_dim` (#3a3a3a) is used for small-caps section
labels. On the #111111 card surface that is roughly 1.6:1 — the labels are
functionally invisible. `text_dim` is kept for what it is actually suited to,
disabled controls, and a `label` token carries real labels at ≥4.5:1.

**Control glyphs.** A Qt stylesheet can only *fill* `::indicator:checked`, so a
checked and an unchecked box differ by shade alone — you have to already know
which shade means yes. The tick and the radio dot are painted in `icons.py` and
referenced here.
"""
from __future__ import annotations

from mazecloak.gui.icons import ensure_control_glyphs

_BASE = """
QWidget {{
    font-size: 13px;
    font-family: "Inter", "Segoe UI", "SF Pro Display", sans-serif;
    color: {text};
}}

/* ── tabs ─────────────────────────────────────────────────────────────── */
/* The pane draws the rule under the bar; the tab's own bottom border sits on
   top of it. Giving both a visible edge double-draws the line. */
QTabWidget::pane {{
    border: none;
    background-color: {bg};
}}

QTabWidget > QWidget {{
    background-color: {bg};
}}

QTabBar {{
    background-color: {bg};
    qproperty-drawBase: 0;
}}

QTabBar::tab {{
    background-color: {bg};
    color: {text_mid};
    padding: 11px 24px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 4px;
    font-size: 13px;
}}

QTabBar::tab:selected {{
    color: {text};
    border-bottom: 2px solid {accent};
    font-weight: bold;
}}

QTabBar::tab:hover:!selected {{
    color: {text};
}}

/* ── tables ───────────────────────────────────────────────────────────── */
QTableWidget {{
    background-color: {bg};
    alternate-background-color: {surface};
    border: none;
    gridline-color: transparent;
    color: {text};
    selection-background-color: {elevated};
    selection-color: {text};
    outline: none;
}}

QTableWidget::item {{
    padding: 9px 14px;
    border: none;
}}

QHeaderView {{
    background-color: {bg};
}}

QHeaderView::section {{
    background-color: {bg};
    color: {label};
    padding: 9px 14px;
    border: none;
    border-bottom: 1px solid {border};
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 1.5px;
}}

/* ── inputs ───────────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border2};
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 130px;
}}

QComboBox:hover {{ border-color: {focus}; }}
QComboBox:focus {{ border-color: {accent}; }}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 22px;
    border: none;
}}

QComboBox QAbstractItemView {{
    background-color: {elevated};
    color: {text};
    border: 1px solid {border2};
    border-radius: 6px;
    selection-background-color: {accent};
    selection-color: {accent_text};
    outline: none;
    padding: 4px;
}}

QSpinBox {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border2};
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 14px;
    font-weight: bold;
}}

QSpinBox:hover {{ border-color: {focus}; }}
QSpinBox:focus {{ border-color: {accent}; }}
QSpinBox:disabled {{ color: {text_dim}; border-color: {border}; }}

/* ── checkboxes and radios ────────────────────────────────────────────── */
QCheckBox, QRadioButton {{
    color: {text};
    spacing: 10px;
    background: transparent;
    padding: 2px 0;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {border2};
    background-color: {surface};
}}

QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 9px; }}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {focus};
}}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
}}
{glyph_rules}

QCheckBox:disabled, QRadioButton:disabled {{ color: {text_dim}; }}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
    border-color: {border};
    background-color: {bg};
}}

/* ── buttons ──────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border2};
    border-radius: 6px;
    padding: 7px 16px;
    min-width: 38px;
}}

QPushButton:hover {{
    background-color: {elevated};
    border-color: {focus};
}}

QPushButton:pressed {{ background-color: {bg}; }}

QPushButton:disabled {{
    color: {text_dim};
    border-color: {border};
    background-color: transparent;
}}

QPushButton[active="true"] {{
    background-color: {accent};
    color: {accent_text};
    border-color: {accent};
    font-weight: bold;
}}

QPushButton[active="true"]:hover {{
    background-color: {accent_hover};
    border-color: {accent_hover};
}}

/* ── scrollbars ───────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent; width: 6px; border: none; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {scrollbar}; border-radius: 3px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {focus}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0; background: none;
}}
QScrollBar:horizontal {{
    background: transparent; height: 6px; border: none;
}}
QScrollBar::handle:horizontal {{
    background: {scrollbar}; border-radius: 3px; min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0; background: none;
}}

/* ── structure ────────────────────────────────────────────────────────── */
QLabel {{ background: transparent; }}

QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {border}; background: {border};
}}

QMainWindow {{ background-color: {bg}; }}

QWidget#header {{
    background-color: {bg};
    border-bottom: 1px solid {border};
}}

QLabel#logo {{
    color: {text};
    font-size: 16px;
    font-weight: bold;
    letter-spacing: 4px;
    background: transparent;
}}

QScrollArea {{ background-color: {bg}; border: none; }}
QScrollArea > QWidget > QWidget {{ background-color: {bg}; }}

QFrame#card {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 10px;
}}

/* The one surface allowed to sit above the others: it carries the answer the
   window exists to give. */
QFrame#hero {{
    background-color: {surface};
    border: 1px solid {border2};
    border-radius: 12px;
}}

QLabel#hero_status {{
    font-size: 30px;
    font-weight: bold;
    letter-spacing: -0.5px;
    background: transparent;
}}

QLabel#hero_mac {{
    font-family: "JetBrains Mono", "DejaVu Sans Mono", "Monospace", monospace;
    font-size: 27px;
    font-weight: bold;
    letter-spacing: 1px;
    color: {text};
    background: transparent;
}}

QLabel#hero_meta {{
    color: {text_mid};
    font-size: 12px;
    background: transparent;
}}

/* Small-caps labels. `label`, not `text_dim`: these are content, and at 10px
   they need contrast more than body text does, not less. */
QLabel#label {{
    color: {label};
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 2px;
    background: transparent;
}}

QLabel#card_key {{
    color: {text_mid};
    font-size: 12px;
    background: transparent;
}}

QLabel#card_value {{
    color: {text};
    font-size: 13px;
    background: transparent;
}}

QLabel#stat {{
    color: {text};
    font-size: 19px;
    font-weight: bold;
    background: transparent;
}}

QLabel#mono {{
    font-family: "JetBrains Mono", "DejaVu Sans Mono", "Monospace", monospace;
    color: {text};
    font-size: 13px;
    background: transparent;
}}

QLabel#hint {{
    color: {text_mid};
    font-size: 11px;
    background: transparent;
}}

QGroupBox {{
    border: 1px solid {border};
    border-radius: 10px;
    background-color: {surface};
    margin-top: 15px;
    padding: 18px 16px 14px 16px;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 2px;
    color: {label};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 7px;
    background-color: {bg};
}}

/* ── window chrome ────────────────────────────────────────────────────── */
QPushButton#primary_switch {{
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 1.2px;
    padding: 13px 30px;
    border-radius: 8px;
}}

QPushButton#win_btn, QPushButton#win_close {{
    background: transparent;
    border: none;
    border-radius: 0;
    color: {text_mid};
    font-size: 14px;
    padding: 0;
    min-width: 44px;
    min-height: 44px;
}}

QPushButton#win_btn:hover {{
    background-color: {elevated};
    color: {text};
}}

QPushButton#win_close:hover {{
    background-color: #c42b1c;
    color: #ffffff;
}}

QToolTip {{
    background-color: {elevated};
    color: {text};
    border: 1px solid {border2};
    padding: 6px 9px;
    border-radius: 6px;
}}
"""

# `label` and `focus` are the additions to Maze Guard's palette; every other
# value is shared with it so the two windows stay indistinguishable.
_DARK = {
    "bg":           "#0a0a0a",
    "surface":      "#111111",
    "elevated":     "#1a1a1a",
    "border":       "#1e1e1e",
    "border2":      "#2e2e2e",
    "focus":        "#4a4a4a",
    "text":         "#f0f0f0",
    "text_mid":     "#9a9a9a",   # 6.4:1 on bg
    "label":        "#8a8a8a",   # 5.4:1 on surface — labels are content
    "text_dim":     "#4a4a4a",   # disabled only
    "scrollbar":    "#2a2a2a",
    "accent":       "#f0f0f0",
    "accent_text":  "#0a0a0a",
    "accent_hover": "#ffffff",
}

_LIGHT = {
    "bg":           "#f5f5f5",
    "surface":      "#ffffff",
    "elevated":     "#ebebeb",
    "border":       "#e2e2e2",
    "border2":      "#d0d0d0",
    "focus":        "#9a9a9a",
    "text":         "#0a0a0a",
    "text_mid":     "#5f5f5f",   # 6.9:1 on bg
    "label":        "#6b6b6b",   # 5.3:1 on surface
    "text_dim":     "#b0b0b0",
    "scrollbar":    "#c8c8c8",
    "accent":       "#0a0a0a",
    "accent_text":  "#f5f5f5",
    "accent_hover": "#282828",
}


def _glyph_rules(theme: str, palette: dict) -> str:
    """Point the checked indicators at the painted tick and dot.

    Returns "" when the glyphs could not be written (a read-only cache), which
    leaves the plain accent fill — degraded, but never a broken image box.
    """
    glyphs = ensure_control_glyphs(theme, palette["accent_text"])
    rules = []
    if glyphs.get("check"):
        rules.append(
            "QCheckBox::indicator:checked {\n"
            f"    image: url({glyphs['check']});\n"
            "}")
    if glyphs.get("dot"):
        rules.append(
            "QRadioButton::indicator:checked {\n"
            f"    image: url({glyphs['dot']});\n"
            "}")
    return "\n".join(rules)


def get_stylesheet(theme: str) -> str:
    palette = dict(_DARK if theme == "dark" else _LIGHT)
    palette["glyph_rules"] = _glyph_rules(theme, palette)
    return _BASE.format(**palette)


# The same three signal colours Maze Guard uses for threat levels, so green,
# amber and red mean the same thing in both windows.
STATE_COLORS = {
    "on":      "#00e676",   # cloaked and rotating
    "partial": "#ffab00",   # enabled but held back (VPN, no schedule)
    "off":     "#ff3d00",   # not cloaked
    "idle":    "#6a6a6a",   # unknown / daemon not running
}
