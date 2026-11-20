from collections.abc import Mapping

from PyQt6.QtCore import QDate, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractButton, QAbstractItemView, QComboBox, QDateEdit, QDialog,
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from logic_units.paths import IMAGES
from ui_units.icons import icon


def label(text="", role="", wrap=False):
    widget = QLabel(str(text))
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    widget.setProperty("role", role)
    if role in ("eyebrow", "heroEyebrow", "sideBrand"):
        font = widget.font()
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.9 if role == "sideBrand" else 1.35)
        widget.setFont(font)
    return widget


def action(text, callback=None, role="", symbol=None, tip=None):
    button = QPushButton(text)
    button.setProperty("role", role)
    if role == "brand":
        font = button.font()
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 5)
        button.setFont(font)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if symbol:
        button.setIcon(icon(symbol))
        button.setIconSize(QSize(21, 21))
    if tip:
        button.setToolTip(tip)
        button.setAccessibleName(tip)
    if callback:
        button.clicked.connect(callback)
    return button


def combo(choices, value=None):
    box = QComboBox()
    pairs = choices.items() if isinstance(choices, Mapping) else ((choice, choice) for choice in choices)
    for key, text in pairs:
        box.addItem(text, key)
    if value is not None:
        index = box.findData(value)
        if index >= 0:
            box.setCurrentIndex(index)
    return box


def day_edit(day=None):
    field = QDateEdit(day or QDate.currentDate())
    field.setDisplayFormat("dd.MM.yyyy")
    field.setCalendarPopup(True)
    return field


def iso_date(field):
    return field.date().toString("yyyy-MM-dd")


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().hide()
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())
            item.layout().deleteLater()


def surface():
    panel = QFrame()
    panel.setProperty("surface", True)
    return panel


def divider():
    line = QFrame()
    line.setObjectName("divider")
    line.setFixedHeight(1)
    return line


def scroll_page(margins=(36, 28, 36, 36)):
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    content = QWidget()
    content.setObjectName("page")
    layout = QVBoxLayout(content)
    layout.setContentsMargins(*margins)
    layout.setSpacing(16)
    area.setWidget(content)
    return area, layout


def empty_state(title, detail="", button=None):
    panel = surface()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(24, 44, 24, 44)
    layout.setSpacing(10)
    caption = label(title, "section", True)
    caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(caption)
    if detail:
        note = label(detail, "muted", True)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(note)
    if button is not None:
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignHCenter)
    return panel


def password_entry(placeholder=""):
    panel = QWidget()
    layout = QHBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(5)
    entry = QLineEdit()
    entry.setPlaceholderText(placeholder)
    entry.setEchoMode(QLineEdit.EchoMode.Password)
    entry.setMaxLength(128)
    show = action("Показать", role="secondary")
    show.setCheckable(True)

    def reveal(checked):
        entry.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)
        show.setText("Скрыть" if checked else "Показать")

    show.toggled.connect(reveal)
    layout.addWidget(entry, 1)
    layout.addWidget(show)
    return panel, entry


class FormDialog(QDialog):
    def __init__(self, parent, title, width=510):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(width)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(26, 19, 26, 22)
        self.layout.setSpacing(15)
        self.heading = label(title, "section", True)
        self.layout.addWidget(self.heading)
        self.body = QVBoxLayout()
        self.body.setSpacing(13)
        self.layout.addLayout(self.body, 1)
        self.error = label("", "error", True)
        self.error.hide()
        self.layout.addWidget(self.error)
        self.footer = QHBoxLayout()
        self.footer.addStretch()
        self.layout.addLayout(self.footer)

    def set_actions(self, title, callback, cancel="Отмена"):
        if cancel:
            self.footer.addWidget(action(cancel, self.reject, "secondary"))
        accept = action(title, callback, "primary")
        accept.setDefault(True)
        self.footer.addWidget(accept)
        return accept

    def show_error(self, message):
        self.error.setText(str(message))
        self.error.setVisible(bool(message))


def tell(parent, title, message):
    dialog = QMessageBox(parent)
    dialog.setWindowTitle(title)
    dialog.setTextFormat(Qt.TextFormat.PlainText)
    dialog.setText(message)
    dialog.addButton("Закрыть", QMessageBox.ButtonRole.AcceptRole)
    dialog.exec()


def confirm(parent, title, message):
    dialog = FormDialog(parent, title)
    dialog.body.addWidget(label(message, wrap=True))
    dialog.set_actions("Удалить", dialog.accept)
    return dialog.exec() == QDialog.DialogCode.Accepted


class Photo(QAbstractButton):
    def __init__(self, path, callback=None, description="", fit="cover"):
        super().__init__()
        self.fit = fit
        self.pixmap = QPixmap()
        self.set_image(path)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.interactive = callback is not None
        self.setAccessibleName(description or "Фото товара")
        if self.interactive:
            self.clicked.connect(callback)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        else:
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_image(self, path):
        self.pixmap = QPixmap(str(IMAGES / path)) if path else QPixmap()
        self.update()

    def sizeHint(self):
        return QSize(200, 200)

    def minimumSizeHint(self):
        return QSize(0, 0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if self.fit != "contain" or self.pixmap.isNull():
            painter.fillRect(self.rect(), QColor("#eae1d7"))
        if self.pixmap.isNull():
            center = QRectF(self.rect()).center()
            icon("photo", "#9b847a").paint(
                painter, int(center.x() - 15), int(center.y() - 15), 30, 30
            )
        else:
            iw, ih = self.pixmap.width(), self.pixmap.height()
            sx, sy = self.width() / iw, self.height() / ih
            factor = min(sx, sy) if self.fit == "contain" else max(sx, sy)
            width, height = iw * factor, ih * factor
            offset_y = 0.28 if self.fit == "hero" else 0.5
            target = QRectF((self.width() - width) / 2, (self.height() - height) * offset_y, width, height)
            painter.drawPixmap(target, self.pixmap, QRectF(0, 0, iw, ih))
        if self.interactive and self.hasFocus():
            painter.setPen(QColor("#874556"))
            painter.drawRect(self.rect().adjusted(1, 1, -2, -2))


class Table(QTableWidget):
    def __init__(self, columns, widths=()):
        super().__init__(0, len(columns))
        self.setHorizontalHeaderLabels(columns)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.setShowGrid(False)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(42)
        self.horizontalHeader().setStretchLastSection(True)
        for index, width in enumerate(widths):
            self.setColumnWidth(index, width)

    def fill(self, rows):
        self.clearContents()
        self.setRowCount(len(rows))
        for index, values in enumerate(rows):
            for column, value in enumerate(values):
                text = str(value) if value is not None and value != "" else "—"
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                self.setItem(index, column, item)
