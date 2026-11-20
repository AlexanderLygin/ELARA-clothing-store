from dataclasses import replace

from PyQt6.QtCore import QSignalBlocker, QSize, Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from logic_units.catalog import CATEGORIES, COLLECTIONS, COLORS, SORTS, CatalogFilter
from logic_units.formatting import counted, rubles
from ui_units.icons import icon
from ui_units.widgets import Photo, FormDialog, action, combo, divider, empty_state, label, scroll_page


class ProductCard(QFrame):
    def __init__(self, product, store):
        super().__init__()
        self.product_id = product["id"]
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        show = lambda: store.open_product(self.product_id)
        self.photo = Photo(product["image"], show, product["name"])
        self.photo.setFixedHeight(220)
        overlay = QHBoxLayout(self.photo)
        overlay.setContentsMargins(11, 11, 11, 11)
        if product["previous_price"]:
            badge = label("Скидка", "status")
            overlay.addWidget(badge, alignment=Qt.AlignmentFlag.AlignTop)
        overlay.addStretch()
        self.heart = action("", lambda: store.toggle_favorite(self.product_id), "heart", "heart")
        self.heart.setFixedSize(34, 34)
        self.heart.setIconSize(QSize(18, 18))
        overlay.addWidget(self.heart, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.photo)

        info = QVBoxLayout()
        info.setContentsMargins(13, 10, 13, 12)
        info.setSpacing(2)
        info.addWidget(label(product["subcategory"], "small"))
        self.name = product["name"]
        self.name_button = action(self.name, show, "itemName", tip=self.name)
        self.name_button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        info.addWidget(self.name_button)
        row = QHBoxLayout()
        price_prefix = "От " if product["price"] != product["maximum_price"] else ""
        row.addWidget(label(price_prefix + rubles(product["price"]), "strong"))
        if product["previous_price"]:
            row.addWidget(label(rubles(product["previous_price"]), "oldPrice"))
        row.addStretch()
        for color in product["colors"][:4]:
            dot = QFrame()
            dot.setFixedSize(11, 11)
            dot.setToolTip(color)
            dot.setStyleSheet(
                f"background: {COLORS.get(color, '#bdaba1')}; border: 1px solid #9f8e82; border-radius: 5px;"
            )
            row.addWidget(dot)
        info.addLayout(row)
        layout.addLayout(info)
        self.set_favorite(self.product_id in store.favorite_ids)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        visible_name = self.name_button.fontMetrics().elidedText(
            self.name, Qt.TextElideMode.ElideRight, max(1, event.size().width() - 29)
        )
        self.name_button.setText(visible_name)

    def set_favorite(self, saved):
        text = "Убрать из избранного" if saved else "В избранное"
        self.heart.setToolTip(text)
        self.heart.setAccessibleName(text)
        self.heart.setIcon(icon("heart_on" if saved else "heart", "#73283c" if saved else "#332729"))


class ProductGrid(QWidget):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(16)
        self.grid.setVerticalSpacing(20)
        self.cards = []

    def set_products(self, products):
        for card in self.cards:
            self.grid.removeWidget(card)
            card.hide()
            card.deleteLater()
        self.cards = [ProductCard(product, self.store) for product in products]
        self.reflow()

    def refresh_hearts(self):
        for card in self.cards:
            card.set_favorite(card.product_id in self.store.favorite_ids)

    def reflow(self):
        columns = 4 if self.width() >= 1030 else 3 if self.width() >= 660 else 2
        width = max(1, (self.width() - (columns - 1) * self.grid.horizontalSpacing()) // columns)
        for index in range(4):
            self.grid.setColumnStretch(index, int(index < columns))
        for index, card in enumerate(self.cards):
            card.photo.setFixedHeight(max(150, min(320, width)))
            self.grid.addWidget(card, index // columns, index % columns)
            card.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow()


class HomePage(QWidget):
    def __init__(self, db, store):
        super().__init__()
        self.store = store
        self.db = db
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        area, layout = scroll_page((34, 25, 34, 32))
        layout.setSpacing(20)
        root.addWidget(area)

        hero = QWidget()
        hero.setFixedHeight(390)
        split = QHBoxLayout(hero)
        split.setContentsMargins(0, 0, 0, 0)
        split.setSpacing(0)
        copy = QFrame()
        copy.setObjectName("heroCopy")
        copy_layout = QVBoxLayout(copy)
        copy_layout.setContentsMargins(38, 22, 20, 24)
        copy_layout.setSpacing(10)
        copy_layout.addStretch()
        copy_layout.addWidget(label("КОЛЛЕКЦИЯ ОСЕНЬ / ЗИМА", "heroEyebrow"))
        title = label("Форма\nи фактура", "heroTitle")
        copy_layout.addWidget(title)
        copy_layout.addWidget(label("Шерсть, кожа и шёлк.", "heroNote"))
        copy_layout.addSpacing(13)
        cta = action("Смотреть коллекцию   →", lambda: store.open_catalog(collection="new"), "hero")
        copy_layout.addWidget(cta, alignment=Qt.AlignmentFlag.AlignLeft)
        copy_layout.addStretch()
        split.addWidget(copy, 42)
        split.addWidget(Photo("campaign/autumn-winter.jpg", description="Коллекция осень-зима", fit="hero"), 58)
        layout.addWidget(hero)

        featured = QHBoxLayout()
        featured.addWidget(label("Новая коллекция", "section"))
        featured.addStretch()
        featured.addWidget(action("Весь каталог  →", store.open_catalog, "link"))
        layout.addLayout(featured)
        self.grid = ProductGrid(store)
        layout.addWidget(self.grid)
        layout.addWidget(divider())
        layout.addStretch()
        self.refresh()

    def refresh(self):
        products = self.db.products(CatalogFilter(collection="new"))
        preferred = ("EL-W01", "EL-A01", "EL-M01", "EL-J01")
        items = {product["sku"]: product for product in products}
        picks = [items[sku] for sku in preferred if sku in items]
        picks.extend(product for product in products if product not in picks)
        self.grid.set_products(picks[:4])


class FilterDialog(FormDialog):
    def __init__(self, parent, filters, scope):
        super().__init__(parent, "Фильтры")
        self.filters = filters
        form = QFormLayout()
        form.setVerticalSpacing(11)
        self.minimum = QSpinBox()
        self.minimum.setRange(0, 9_999_999)
        self.minimum.setSuffix(" ₽")
        self.minimum.setValue(filters.minimum // 100)
        self.maximum = QSpinBox()
        self.maximum.setRange(0, 9_999_999)
        self.maximum.setSuffix(" ₽")
        self.maximum.setSpecialValueText("Без ограничения")
        self.maximum.setValue(filters.maximum // 100 if filters.maximum is not None else 0)
        self.material = combo(
            {"": "Любой материал"} | {p: p for p in sorted({item["material"] for item in scope})},
            filters.material,
        )
        self.style = combo(
            {"": "Любой стиль"} | {p: p for p in sorted({item["style"] for item in scope})},
            filters.style,
        )
        self.in_stock = QCheckBox("Только в наличии")
        self.in_stock.setChecked(filters.in_stock)
        for title, field in (
            ("Цена от", self.minimum), ("Цена до", self.maximum),
            ("Материал", self.material), ("Стиль", self.style),
        ):
            form.addRow(title, field)
        form.addRow(self.in_stock)
        self.body.addLayout(form)
        self.footer.insertWidget(0, action("Сбросить", self.reset, "link"))
        self.set_actions("Применить", self.save)

    def reset(self):
        self.minimum.setValue(0)
        self.maximum.setValue(0)
        self.material.setCurrentIndex(0)
        self.style.setCurrentIndex(0)
        self.in_stock.setChecked(False)
        self.show_error("")

    def save(self):
        low, high = self.minimum.value(), self.maximum.value()
        if high and high < low:
            self.show_error("Верхняя граница цены должна быть не ниже нижней.")
            return
        self.filters = replace(
            self.filters, minimum=low * 100, maximum=high * 100 if high else None,
            material=self.material.currentData(), style=self.style.currentData(),
            in_stock=self.in_stock.isChecked(),
        )
        self.accept()


class CatalogPage(QWidget):
    def __init__(self, db, store):
        super().__init__()
        self.db = db
        self.store = store
        self.filters = CatalogFilter()
        self.saved_only = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.area, layout = scroll_page()
        outer.addWidget(self.area)
        self.breadcrumb = label("ELARA  /  КАТАЛОГ", "eyebrow")
        layout.addWidget(self.breadcrumb)
        self.title = label("Каталог", "title")
        layout.addWidget(self.title)
        toolbar = QHBoxLayout()
        self.count = label("", "muted")
        self.section = combo({"": "Все подкатегории"})
        self.sort = combo(SORTS)
        self.section.setMinimumWidth(180)
        self.sort.setMinimumWidth(166)
        self.sort.setAccessibleName("Сортировка")
        self.filter_button = action("Фильтры", self.open_filters, "secondary", "filter")
        toolbar.addWidget(self.count)
        toolbar.addStretch()
        toolbar.addWidget(self.section)
        toolbar.addWidget(self.sort)
        toolbar.addWidget(self.filter_button)
        self.section.currentIndexChanged.connect(self.change_section)
        self.sort.currentIndexChanged.connect(self.change_sort)
        layout.addLayout(toolbar)
        layout.addWidget(divider())
        self.grid = ProductGrid(store)
        layout.addWidget(self.grid)
        self.empty = empty_state(
            "Товаров пока нет", "Попробуй изменить запрос или фильтры.",
            action("Открыть весь каталог", store.open_catalog, "link"),
        )
        layout.addWidget(self.empty)
        self.empty_saved = empty_state(
            "Избранное пока пусто", "Сохраняй понравившиеся модели кнопкой с сердцем.",
            action("Открыть весь каталог", store.open_catalog, "link"),
        )
        layout.addWidget(self.empty_saved)
        layout.addStretch()

    def open(self, category="", collection="", query="", saved=False):
        self.saved_only = saved
        self.filters = CatalogFilter(category=category, collection=collection, query=query)
        with QSignalBlocker(self.section), QSignalBlocker(self.sort):
            self.section.clear()
            if category:
                self.section.addItem("Все подкатегории", "")
                for name in CATEGORIES[category][1]:
                    self.section.addItem(name, name)
            elif collection:
                for key, name in COLLECTIONS.items():
                    self.section.addItem(name, key)
                self.section.setCurrentIndex(self.section.findData(collection))
            self.section.setVisible(bool(category or collection))
            self.sort.setCurrentIndex(0)
        self.refresh()
        self.area.verticalScrollBar().setValue(0)

    def change_section(self):
        if self.filters.category:
            self.filters.subcategory = self.section.currentData()
        else:
            self.filters.collection = self.section.currentData()
        self.refresh()

    def change_sort(self):
        self.filters.sort = self.sort.currentData()
        self.refresh()

    def open_filters(self):
        scope = replace(self.filters, material="", style="", minimum=0, maximum=None, in_stock=False)
        dialog = FilterDialog(self, self.filters, self.db.products(
            scope, favorites_of=self.store.session.client_id if self.saved_only else None
        ))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.filters = dialog.filters
            self.refresh()

    def refresh(self):
        category, collection = self.filters.category, self.filters.collection
        title = "Весь каталог"
        if self.saved_only:
            title = "Избранное"
        elif self.filters.query:
            title = f"Поиск по запросу «{self.filters.query}»"
        elif category:
            title = self.filters.subcategory or CATEGORIES[category][0]
        elif collection:
            title = COLLECTIONS[collection]
        self.title.setText(title)
        self.title.setWordWrap(True)
        self.breadcrumb.setText("ELARA  /  ИЗБРАННОЕ" if self.saved_only else "ELARA  /  КАТАЛОГ")
        favorites = self.store.session.client_id if self.saved_only else None
        products = self.db.products(self.filters, favorites_of=favorites)
        self.count.setText(counted(len(products), "модель", "модели", "моделей"))
        self.filter_button.setText("Фильтры •" if self.filters.is_filtered() else "Фильтры")
        self.grid.set_products(products)
        self.grid.setVisible(bool(products))
        missing_favorites = self.saved_only and not self.filters.is_filtered()
        self.empty.setVisible(not products and not missing_favorites)
        self.empty_saved.setVisible(not products and missing_favorites)
