from decimal import Decimal
import re
from uuid import uuid4

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QImageReader, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit,
    QTableWidgetItem, QTextEdit, QVBoxLayout,
)

from logic_units.catalog import CATEGORIES, COLLECTIONS
from logic_units.paths import IMAGES
from ui_units.widgets import FormDialog, Photo, Table, action, combo, divider, label, surface


def price_value(text):
    value = text.replace(" ", "").replace(",", ".")
    if not re.fullmatch(r"[0-9]{1,7}(?:\.[0-9]{1,2})?", value):
        raise ValueError("Цену указывай в рублях, до двух знаков после запятой.")
    return int(Decimal(value) * 100)


class ProductEditor(FormDialog):
    def __init__(self, parent, db, product=None):
        title = "Редактировать товар" if product else "Новый товар"
        super().__init__(parent, title, 790)
        self.resize(930, 679)
        self.db = db
        self.product_id = product["id"] if product else None
        self.file = None
        product = product or {}
        self.image_path = product.get("image", "")

        overview = QHBoxLayout()
        overview.setSpacing(17)
        form = QFormLayout()
        form.setVerticalSpacing(7)
        self.fields = {}
        for key, field_title, max_length in (
            ("sku", "Артикул", 30),
            ("name", "Название", 80),
            ("material", "Материал", 64),
            ("style", "Стиль", 64),
            ("photo_color", "Цвет на фото", 48),
        ):
            field = QLineEdit(product.get(key, ""))
            field.setMaxLength(max_length)
            self.fields[key] = field
            form.addRow(field_title, field)
        self.category = combo({key: item[0] for key, item in CATEGORIES.items()}, product.get("category_id"))
        self.subcategory = combo([])
        self.reload_subcategories()
        if product:
            self.subcategory.setCurrentText(product["subcategory"])
        self.category.currentIndexChanged.connect(self.reload_subcategories)
        form.insertRow(2, "Раздел", self.category)
        form.insertRow(3, "Подкатегория", self.subcategory)
        self.description = QTextEdit(product.get("description", ""))
        self.description.setAcceptRichText(False)
        self.description.setFixedHeight(66)
        form.addRow("Описание", self.description)
        overview.addLayout(form, 1)

        right = surface()
        right.setFixedWidth(293)
        visual = QVBoxLayout(right)
        visual.setContentsMargins(12, 12, 12, 12)
        visual.setSpacing(7)
        self.preview = Photo(self.image_path, description="Фото товара")
        self.preview.setMinimumHeight(139)
        visual.addWidget(self.preview, 1)
        file_buttons = QHBoxLayout()
        file_buttons.addWidget(action("Выбрать фото", self.browse, "secondary"))
        file_buttons.addWidget(action("Убрать", self.remove_photo, "link"))
        visual.addLayout(file_buttons)
        visual.addWidget(label("Коллекции", "strong"))
        self.collections = {}
        chosen = db.product_collections(self.product_id) if product else set()
        for key, title in COLLECTIONS.items():
            check = QCheckBox(title)
            check.setChecked(key in chosen)
            self.collections[key] = check
            visual.addWidget(check)
        overview.addWidget(right)
        self.body.addLayout(overview)
        self.body.addWidget(divider())

        rows = QHBoxLayout()
        rows.addWidget(label("Варианты", "strong"))
        rows.addWidget(label("Двойной щелчок для правки", "small"))
        rows.addStretch()
        rows.addWidget(action("Добавить строку", self.add_variant, "secondary"))
        rows.addWidget(action("Удалить строку", self.remove_variant, "link"))
        self.body.addLayout(rows)
        self.variants = Table(
            ("Размер", "Цвет", "Цена, ₽", "Старая цена, ₽", "Остаток"), (100, 190, 120, 134)
        )
        self.variants.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.variants.setMinimumHeight(123)
        self.variants.verticalHeader().setDefaultSectionSize(34)
        self.body.addWidget(self.variants, 1)
        if self.product_id:
            data = db.variants(self.product_id)
            self.variants.fill([
                (v["size"], v["color"], f"{Decimal(v['price']) / 100:f}",
                 f"{Decimal(v['previous_price']) / 100:f}" if v["previous_price"] else "",
                 v["stock"])
                for v in data
            ])
            for row in range(self.variants.rowCount()):
                if data[row]["previous_price"] is None:
                    self.variants.item(row, 3).setText("")
        else:
            self.append_variant(("Единый", "", "", "", "0"))
        self.set_actions("Сохранить товар", self.save)

    def reload_subcategories(self):
        key = self.category.currentData()
        self.subcategory.clear()
        self.subcategory.addItems(CATEGORIES[key][1])

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Фотография товара", "", "Изображения (*.jpg *.jpeg *.png *.webp *.bmp)"
        )
        if not path:
            return
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        size = reader.size()
        if size.isValid() and max(size.width(), size.height()) > 1200:
            size.scale(QSize(1200, 1200), Qt.AspectRatioMode.KeepAspectRatio)
            reader.setScaledSize(size)
        image = reader.read()
        if image.isNull():
            self.show_error("Не удалось открыть изображение.")
            return
        self.file = image
        self.preview.pixmap = QPixmap.fromImage(image)
        self.preview.update()
        self.show_error("")

    def remove_photo(self):
        self.image_path = ""
        self.file = None
        self.preview.set_image("")

    def append_variant(self, values):
        row = self.variants.rowCount()
        self.variants.insertRow(row)
        for column, value in enumerate(values):
            self.variants.setItem(row, column, QTableWidgetItem(value))
        return row

    def add_variant(self):
        row = self.append_variant(("", "", "", "", "0"))
        self.variants.setCurrentCell(row, 0)
        self.variants.editItem(self.variants.item(row, 0))

    def remove_variant(self):
        row = self.variants.currentRow()
        if row >= 0:
            self.variants.removeRow(row)

    def variant_rows(self):
        rows = []
        for index in range(self.variants.rowCount()):
            size, color, price, previous, stock = (
                self.variants.item(index, column).text().strip() for column in range(5)
            )
            if not stock.isdecimal() or len(stock) > 6:
                raise ValueError(f"Строка {index + 1}. Укажи остаток целым числом от 0 до 999999.")
            rows.append((size, color, price_value(price), price_value(previous) if previous else None, int(stock)))
        return rows

    def save(self):
        new_file = None
        try:
            variants = self.variant_rows()
            product = {key: field.text().strip() for key, field in self.fields.items()}
            product["sku"] = product["sku"].upper()
            product.update(
                category_id=self.category.currentData(),
                subcategory=self.subcategory.currentText(),
                description=self.description.toPlainText().strip(),
                image=self.image_path,
            )
            if self.file is not None:
                path = f"custom/{uuid4().hex}.jpg"
                new_file = IMAGES / path
                new_file.parent.mkdir(parents=True, exist_ok=True)
                if not self.file.save(str(new_file), "JPEG", 91):
                    raise ValueError("Не удалось сохранить файл фотографии.")
                product["image"] = path
            self.db.save_product(
                product, variants, [key for key, box in self.collections.items() if box.isChecked()],
                self.product_id,
            )
        except (ValueError, OSError) as error:
            if new_file is not None:
                try:
                    new_file.unlink(missing_ok=True)
                except OSError:
                    pass
            self.show_error(error)
            return
        self.accept()
