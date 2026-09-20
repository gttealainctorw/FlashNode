"""Custom-painted checkbox so it matches the design tokens exactly."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton

from app.ui.theme import Colors


class Checkbox(QAbstractButton):
    """18px checkable box. Emits `toggled(bool)` like any QAbstractButton."""

    SIZE = 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setFixedSize(self.SIZE, self.SIZE)
        self._hover = False

    def sizeHint(self) -> QSize:
        return QSize(self.SIZE, self.SIZE)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0.75, 0.75, self.SIZE - 1.5, self.SIZE - 1.5)
        checked = self.isChecked()
        enabled = self.isEnabled()

        if not enabled:
            fill = QColor(Colors.SURFACE_ACTIVE)
            border = QColor(Colors.BORDER)
            mark = QColor(Colors.TEXT_DISABLED)
        elif checked:
            fill = QColor(Colors.PRIMARY_HOVER if self._hover else Colors.PRIMARY)
            border = fill
            mark = QColor(Colors.TEXT_ON_PRIMARY)
        else:
            fill = QColor(Colors.SURFACE_HOVER if self._hover else Colors.SURFACE)
            border = QColor(Colors.PRIMARY if self._hover else Colors.BORDER_STRONG)
            mark = None

        painter.setPen(QPen(border, 1.5))
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, 4, 4)

        if self.hasFocus():
            painter.setPen(QPen(QColor(Colors.PRIMARY_BORDER), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-0.5, -0.5, 0.5, 0.5), 5, 5)

        if checked or (not enabled and self.isChecked()):
            path = QPainterPath()
            s = self.SIZE
            path.moveTo(s * 0.27, s * 0.52)
            path.lineTo(s * 0.44, s * 0.69)
            path.lineTo(s * 0.74, s * 0.34)
            pen = QPen(mark or QColor(Colors.TEXT_DISABLED), 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
