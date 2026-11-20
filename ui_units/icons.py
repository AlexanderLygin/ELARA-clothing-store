from functools import lru_cache

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


@lru_cache(maxsize=24)
def icon(name, color="#332729"):
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(2, 2)
    pen = QPen(QColor(color), 1.45, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    path = QPainterPath()
    if name == "search":
        painter.drawEllipse(QRectF(4, 4, 11, 11))
        painter.drawLine(QPointF(13.5, 13.5), QPointF(19.7, 19.7))
    elif name in ("heart", "heart_on"):
        path.moveTo(12, 20)
        path.cubicTo(8, 17, 3.1, 13, 3.1, 8.7)
        path.cubicTo(3.1, 4, 9, 3.2, 12, 7.2)
        path.cubicTo(15, 3.2, 20.9, 4, 20.9, 8.7)
        path.cubicTo(20.9, 13, 16, 17, 12, 20)
        path.closeSubpath()
        if name == "heart_on":
            painter.setBrush(QColor(color))
        painter.drawPath(path)
    elif name == "bag":
        painter.drawRoundedRect(QRectF(4.3, 8, 15.4, 12.5), 0.8, 0.8)
        painter.drawArc(QRectF(8.4, 3.4, 7.2, 9), 0, 180 * 16)
    elif name == "user":
        painter.drawEllipse(QRectF(8, 3.6, 8, 8))
        path.moveTo(4.3, 20)
        path.cubicTo(4.3, 12.8, 19.7, 12.8, 19.7, 20)
        painter.drawPath(path)
    elif name == "filter":
        for y, x in ((7.0, 9.0), (12.0, 15.0), (17.0, 10.0)):
            painter.drawLine(QPointF(4.0, y), QPointF(20.0, y))
            painter.setBrush(QColor("#fcf9f3"))
            painter.drawEllipse(QPointF(x, y), 2.0, 2.0)
    elif name == "photo":
        painter.drawRoundedRect(QRectF(3.5, 4.3, 17, 15.4), 1, 1)
        painter.drawEllipse(QRectF(7, 7, 3, 3))
        path.moveTo(4, 18)
        path.lineTo(10, 13)
        path.lineTo(13.5, 15.4)
        path.lineTo(17.2, 11.3)
        path.lineTo(20, 14)
        painter.drawPath(path)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)
