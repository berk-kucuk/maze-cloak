"""Icons: the app mark, and the glyphs Qt cannot draw for itself.

Two problems are solved here.

**The mark ships with 10% transparent padding on every side** — the artwork
occupies about 80% of its canvas. A system tray adds its own margin on top of
that, so the untouched PNG renders visibly smaller than every neighbouring icon
in the panel. `_content_pixmap()` trims the empty border once and caches it, so
the mark fills the slot it is given.

**Qt stylesheets cannot put a checkmark inside a checkbox.** Styling
`::indicator:checked` can only fill it, which makes checked and unchecked two
similarly-sized squares that differ by shade — unreadable at a glance and
invisible to anyone who does not already know which shade means yes. The
glyphs are painted here to PNGs the stylesheet can reference by path.
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import (
    QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap,
)

_LOGO_PATH = Path(__file__).parent.parent.parent / "MAZE-CLOAK.png"

# Sizes a panel, task switcher or notification may ask for. Supplying real
# pixmaps at each one lets Qt pick rather than smooth-scaling from a single size.
_ICON_SIZES = (16, 22, 24, 32, 48, 64, 128, 256)

_cache_dir = Path(
    os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "maze-cloak"

_trimmed: QPixmap | None = None


def _content_pixmap() -> QPixmap | None:
    """The mark with its transparent border removed. Computed once."""
    global _trimmed
    if _trimmed is not None:
        return _trimmed if not _trimmed.isNull() else None
    if not _LOGO_PATH.exists():
        return None

    image = QImage(str(_LOGO_PATH))
    if image.isNull():
        return None
    if not image.hasAlphaChannel():
        _trimmed = QPixmap.fromImage(image)
        return _trimmed

    width, height = image.width(), image.height()
    min_x, min_y, max_x, max_y = width, height, -1, -1
    # A coarse scan is plenty: the border is hundreds of pixels wide, and this
    # runs once per process.
    step = max(1, min(width, height) // 256)
    for y in range(0, height, step):
        for x in range(0, width, step):
            if image.pixelColor(x, y).alpha() > 12:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if max_x <= min_x or max_y <= min_y:
        _trimmed = QPixmap.fromImage(image)
        return _trimmed

    # Step back one sample so the coarse scan cannot clip an edge, and keep the
    # crop square so the artwork is not stretched.
    min_x = max(0, min_x - step)
    min_y = max(0, min_y - step)
    max_x = min(width - 1, max_x + step)
    max_y = min(height - 1, max_y + step)
    side = max(max_x - min_x, max_y - min_y) + 1
    cx, cy = (min_x + max_x) // 2, (min_y + max_y) // 2
    left = max(0, min(width - side, cx - side // 2))
    top = max(0, min(height - side, cy - side // 2))

    _trimmed = QPixmap.fromImage(image.copy(left, top, side, side))
    return _trimmed


def logo_pixmap(size: int = 64) -> QPixmap | None:
    source = _content_pixmap()
    if source is None:
        return None
    return source.scaled(size, size,
                         Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)


def _fallback_icon(size: int) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("#0a0a0a"))
    painter = QPainter(pixmap)
    painter.setPen(QColor("#f0f0f0"))
    from PyQt6.QtGui import QFont
    painter.setFont(QFont("sans-serif", max(6, size // 5), QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "M")
    painter.end()
    return QIcon(pixmap)


def create_app_icon(size: int = 64) -> QIcon:
    """The app mark at every size a desktop might ask for."""
    source = _content_pixmap()
    if source is None:
        return _fallback_icon(size)

    icon = QIcon()
    for edge in _ICON_SIZES:
        icon.addPixmap(source.scaled(
            edge, edge,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
    return icon


def tray_icon() -> QIcon:
    """The mark for the system tray.

    Prefers the installed themed icon, which lets the panel scale from hicolor
    at whatever size and DPI it actually uses; falls back to the trimmed
    in-tree pixmap when running from a checkout.
    """
    themed = QIcon.fromTheme("maze-cloak")
    if not themed.isNull():
        return themed
    return create_app_icon(128)


# ── control glyphs ───────────────────────────────────────────────────────────

def _glyph_path(name: str, theme: str) -> Path:
    return _cache_dir / f"{name}-{theme}.png"


def _paint_check(path: Path, colour: str, size: int = 16) -> None:
    # Painted at 3x and scaled down: Qt renders stylesheet images at their
    # natural size, so the extra resolution is what keeps the stroke clean on a
    # HiDPI panel.
    scale = 3
    image = QImage(size * scale, size * scale, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(colour))
    pen.setWidthF(2.0 * scale)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    stroke = QPainterPath()
    unit = size * scale
    stroke.moveTo(unit * 0.24, unit * 0.52)
    stroke.lineTo(unit * 0.42, unit * 0.70)
    stroke.lineTo(unit * 0.77, unit * 0.31)
    painter.drawPath(stroke)
    painter.end()

    image.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio,
                 Qt.TransformationMode.SmoothTransformation).save(str(path))


def _paint_dot(path: Path, colour: str, size: int = 15) -> None:
    scale = 3
    image = QImage(size * scale, size * scale, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(colour))
    unit = size * scale
    inset = unit * 0.30
    painter.drawEllipse(QRectF(inset, inset, unit - 2 * inset, unit - 2 * inset))
    painter.end()

    image.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio,
                 Qt.TransformationMode.SmoothTransformation).save(str(path))


def ensure_control_glyphs(theme: str, on_accent: str) -> dict[str, str]:
    """Paint the checkbox tick and radio dot for `theme`, returning their paths.

    `on_accent` is the colour that reads on top of the accent fill — dark in the
    dark theme, light in the light one — so the tick is legible in both.
    Regenerated whenever missing, which also repairs a cleared cache.
    """
    paths = {"check": _glyph_path("check", theme), "dot": _glyph_path("dot", theme)}
    try:
        _cache_dir.mkdir(parents=True, exist_ok=True)
        if not paths["check"].exists():
            _paint_check(paths["check"], on_accent)
        if not paths["dot"].exists():
            _paint_dot(paths["dot"], on_accent)
    except OSError:
        # A read-only cache costs the tick, not the app: the stylesheet falls
        # back to the plain accent fill.
        return {"check": "", "dot": ""}
    return {k: v.as_posix() for k, v in paths.items()}
