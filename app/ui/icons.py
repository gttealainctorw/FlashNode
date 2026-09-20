"""Inline SVG icon set.

A small, consistent set of stroke icons (24px grid, 1.75px stroke, round caps),
rendered on demand with QtSvg in whatever color the component needs. No image
files, no extra dependencies, crisp at any DPI.
"""

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from app.ui.theme import Colors

# Paths only; the wrapper <svg> element (with stroke/fill) is added at render time.
_PATHS = {
    "bolt": '<path d="M13 3 4.5 13.5H11L10 21l8.5-10.5H12L13 3z"/>',
    "refresh": ('<path d="M20 12a8 8 0 1 1-2.34-5.66"/>'
                '<path d="M20 4v5h-5"/>'),
    "trash": ('<path d="M4 7h16"/>'
              '<path d="M10 11v6M14 11v6"/>'
              '<path d="M6 7l1 13h10l1-13"/>'
              '<path d="M9 7V4h6v3"/>'),
    "cpu": ('<rect x="6" y="6" width="12" height="12" rx="2"/>'
            '<rect x="10" y="10" width="4" height="4" rx="0.5"/>'
            '<path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>'),
    "check": '<path d="M5 12.5 9.5 17 19 7.5"/>',
    "alert": ('<circle cx="12" cy="12" r="9"/>'
              '<path d="M12 8v5"/>'
              '<path d="M12 16h.01"/>'),
    "terminal": ('<path d="M5 8l4 4-4 4"/>'
                 '<path d="M12 16h7"/>'),
}


def _svg(name: str, color: str, stroke_width: float = 1.75) -> QByteArray:
    body = _PATHS[name]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )
    return QByteArray(svg.encode("utf-8"))


def _device_pixel_ratio() -> float:
    app = QApplication.instance()
    if app is None:
        return 1.0
    screen = app.primaryScreen()
    return screen.devicePixelRatio() if screen else 1.0


def pixmap(name: str, color: str = Colors.TEXT_SECONDARY, size: int = 16,
           stroke_width: float = 1.75) -> QPixmap:
    """Render an icon to a pixmap sized for the current screen DPI."""
    dpr = _device_pixel_ratio()
    px = int(round(size * dpr))
    pm = QPixmap(QSize(px, px))
    pm.fill(QColor(0, 0, 0, 0))
    renderer = QSvgRenderer(_svg(name, color, stroke_width))
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, px, px))
    painter.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def icon(name: str, color: str = Colors.TEXT_SECONDARY, size: int = 16,
         disabled_color: str = Colors.TEXT_DISABLED) -> QIcon:
    """Build a QIcon with normal and disabled renderings."""
    ic = QIcon()
    ic.addPixmap(pixmap(name, color, size), QIcon.Mode.Normal)
    ic.addPixmap(pixmap(name, disabled_color, size), QIcon.Mode.Disabled)
    return ic


def logo_pixmap(size: int = 28) -> QPixmap:
    """The FlashNode mark: a bolt on a rounded primary tile."""
    dpr = _device_pixel_ratio()
    px = int(round(size * dpr))
    pm = QPixmap(QSize(px, px))
    pm.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(Colors.PRIMARY))
    radius = px * 0.26
    painter.drawRoundedRect(QRectF(0, 0, px, px), radius, radius)

    # Bolt, scaled from the 24px grid into the tile with some padding.
    bolt = QPainterPath()
    pts = [(13, 3), (4.5, 13.5), (11, 13.5), (10, 21), (18.5, 10.5), (12, 10.5)]
    scale = px / 24 * 0.72
    offset = px * 0.14
    bolt.moveTo(pts[0][0] * scale + offset, pts[0][1] * scale + offset)
    for x, y in pts[1:]:
        bolt.lineTo(x * scale + offset, y * scale + offset)
    bolt.closeSubpath()
    painter.setBrush(QColor(Colors.TEXT_ON_PRIMARY))
    painter.drawPath(bolt)
    painter.end()

    pm.setDevicePixelRatio(dpr)
    return pm


def app_icon() -> QIcon:
    ic = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        ic.addPixmap(logo_pixmap(size))
    return ic
