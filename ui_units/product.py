from PyQt6.QtCore import QSignalBlocker, QSize, Qt
from PyQt6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QSpinBox, QVBoxLayout

from logic_units.formatting import rubles
from ui_units.icons import icon
from ui_units.widgets import Photo, action, combo, divider, label


class ProductDialog(QDialog):
    def __init__(self, store, product):
        super().__init__(store)
        self.store = store
        self.product = product
        self.variants = store.db.variants(product["id"])
        self.setWindowTitle(product["name"])
        self.resize(860, 565)
        self.setMinimumSize(770, 540)
        outer = QHBoxLayout(self)
        outer.setSpacing(23)
        outer.setContentsMargins(18, 18, 21, 18)

        image_column = QVBoxLayout()
        self.image = Photo(product["image"], description=product["name"], fit="contain")
        image_column.addWidget(self.image, 1)
        if product["image"] and product["photo_color"]:
            image_column.addWidget(label(f"На фото · {product['photo_color'].lower()}", "small"))
        outer.addLayout(image_column, 47)

        info = QVBoxLayout()
        info.setSpacing(10)
        top = QHBoxLayout()
        top.addWidget(label(f"{product['subcategory'].upper()}   /   {product['sku']}", "eyebrow"))
        top.addStretch()
        top.addWidget(action("✕", self.reject, "utility", tip="Закрыть карточку"))
        info.addLayout(top)
        info.addWidget(label(product["name"], "section", True))
        prices = QHBoxLayout()
        self.price = label("", "priceHero")
        self.old_price = label("", "oldPrice")
        prices.addWidget(self.price)
        prices.addWidget(self.old_price)
        prices.addStretch()
        info.addLayout(prices)
        info.addWidget(label(product["description"], wrap=True))
        info.addWidget(label(f"{product['material']}   /   {product['style']}", "muted", True))
        info.addWidget(divider())
        form = QFormLayout()
        form.setVerticalSpacing(6)
        colors = list(dict.fromkeys(v["color"] for v in self.variants))
        self.color = combo(colors, product["photo_color"])
        self.color.setAccessibleName("Цвет")
        self.size = combo([])
        self.size.setAccessibleName("Размер")
        self.quantity = QSpinBox()
        self.quantity.setMinimum(1)
        self.quantity.setAccessibleName("Количество")
        form.addRow("Цвет", self.color)
        form.addRow("Размер", self.size)
        form.addRow("Количество", self.quantity)
        info.addLayout(form)
        self.stock = label("", "muted")
        info.addWidget(self.stock)
        self.notice = label("", "error", True)
        self.notice.hide()
        info.addWidget(self.notice)
        info.addStretch()

        actions = QHBoxLayout()
        self.buy = action("Добавить в корзину", self.add_to_cart, "primary", tip="Добавить в корзину")
        actions.addWidget(self.buy, 1)
        self.heart = action("", self.toggle_favorite, "secondary", "heart", tip="В избранное")
        actions.addWidget(self.heart)
        info.addLayout(actions)
        outer.addLayout(info, 53)
        self.color.currentIndexChanged.connect(self.update_sizes)
        self.size.currentIndexChanged.connect(self.update_variant)
        self.update_sizes()
        self.refresh_heart()

    def update_sizes(self):
        active_size = self.size.currentText()
        with QSignalBlocker(self.size):
            self.size.clear()
            for variant in self.variants:
                if variant["color"] == self.color.currentData():
                    self.size.addItem(variant["size"], variant)
            index = self.size.findText(active_size)
            if index < 0:
                index = next(
                    (i for i in range(self.size.count()) if self.size.itemData(i)["stock"]), 0
                )
            self.size.setCurrentIndex(index)
        self.update_variant()

    def update_variant(self):
        self.notice.hide()
        variant = self.size.currentData()
        if variant is None:
            self.buy.setEnabled(False)
            return
        stock = variant["stock"]
        self.price.setText(rubles(variant["price"]))
        self.old_price.setVisible(bool(variant["previous_price"]))
        if variant["previous_price"]:
            self.old_price.setText(rubles(variant["previous_price"]))
        self.stock.setText(f"В наличии · {stock} шт." if stock else "Этого варианта пока нет в наличии")
        self.quantity.setMaximum(max(1, stock))
        self.quantity.setEnabled(bool(stock))
        self.buy.setEnabled(bool(stock) and not self.store.session.is_staff)
        self.buy.setText("Временно нет в наличии" if not stock else "Добавить в корзину")

    def refresh_heart(self):
        saved = self.product["id"] in self.store.favorite_ids
        self.heart.setIcon(icon("heart_on" if saved else "heart", "#73283c"))
        self.heart.setIconSize(QSize(19, 19))
        tip = "Убрать из избранного" if saved else "В избранное"
        self.heart.setToolTip(tip)
        self.heart.setAccessibleName(tip)

    def add_to_cart(self):
        variant = self.size.currentData()
        if self.store.ensure_client(self):
            try:
                self.store.db.set_cart_quantity(
                    self.store.session.client_id, variant["id"], self.quantity.value(), add=True
                )
            except ValueError as error:
                self.notice.setText(str(error))
                self.notice.show()
                return
            self.store.refresh_identity()
            self.store.toast("Товар добавлен в корзину")
            self.accept()

    def toggle_favorite(self):
        self.store.toggle_favorite(self.product["id"], self)
        self.refresh_heart()
        self.update_variant()
