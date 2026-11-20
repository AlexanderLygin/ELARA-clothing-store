from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from logic_units.formatting import counted, display_date, rubles
from logic_units.orders import PAYMENT_METHODS
from ui_units.widgets import (
    FormDialog, Photo, Table, action, clear_layout, combo, divider, empty_state, label,
    scroll_page, surface, tell,
)


class OrderDialog(FormDialog):
    def __init__(self, parent, db, order):
        super().__init__(parent, f"Заказ № {order['id']:04}", 760)
        self.resize(800, 525)
        overview = QFormLayout()
        overview.setVerticalSpacing(6)
        for title, value in (
            ("Дата", display_date(order["created_at"], with_time=True)),
            ("Покупатель", order["customer"]),
            ("Телефон", order["phone"]),
            ("Доставка", order["address"]),
            ("Оплата", f"{order['payment_status']} · {order['payment_method']}"),
            ("Статус", order["status"]),
        ):
            overview.addRow(label(title, "muted"), label(value, wrap=True))
        self.body.addLayout(overview)
        table = Table(("Модель", "Размер", "Цвет", "Кол-во", "Цена", "Сумма"), (225, 65, 126, 65, 96))
        table.fill([
            (item["name"], item["size"], item["color"], item["quantity"],
             rubles(item["price"]), rubles(item["quantity"] * item["price"]))
            for item in db.order_items(order["id"])
        ])
        self.body.addWidget(table, 1)
        self.footer.insertWidget(0, label(f"Итого   {rubles(order['total'])}", "strong"))
        self.set_actions("Закрыть", self.accept, cancel="")


class CheckoutDialog(FormDialog):
    def __init__(self, store, items):
        super().__init__(store, "Оформление заказа", 575)
        self.store = store
        self.items = items
        self.order_id = None
        form = QFormLayout()
        form.setVerticalSpacing(11)
        self.address = QLineEdit()
        self.address.setPlaceholderText("Город, улица, дом, квартира")
        self.address.setMaxLength(220)
        self.payment = combo(PAYMENT_METHODS)
        form.addRow("Адрес доставки", self.address)
        form.addRow("Способ оплаты", self.payment)
        self.body.addLayout(form)
        self.body.addWidget(label("Демо-оплата. Деньги не списываются.", "muted", True))
        total = sum(item["price"] * item["quantity"] for item in items)
        self.body.addWidget(divider())
        self.body.addWidget(label(f"К оплате   {rubles(total)}", "priceHero"))
        self.set_actions("Подтвердить заказ", self.submit)

    def submit(self):
        try:
            self.order_id = self.store.db.checkout(
                self.store.session.client_id, self.address.text(),
                self.payment.currentData(), self.items,
            )
        except ValueError as error:
            self.show_error(error)
            return
        self.accept()


class CartPage(QWidget):
    def __init__(self, store):
        super().__init__()
        self.store = store
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        area, layout = scroll_page()
        outer.addWidget(area)
        layout.addWidget(label("ELARA  /  КОРЗИНА", "eyebrow"))
        layout.addWidget(label("Корзина", "title"))
        self.content = QVBoxLayout()
        self.content.setSpacing(15)
        layout.addLayout(self.content)
        layout.addStretch()
        self.refresh()

    def refresh(self):
        clear_layout(self.content)
        self.items = self.store.db.cart(self.store.session.client_id)
        if not self.items:
            self.content.addWidget(empty_state(
                "Корзина пуста", "Выбери размер и цвет в карточке товара.",
                action("Смотреть каталог", self.store.open_catalog, "link"),
            ))
            return

        total_items = sum(item["quantity"] for item in self.items)
        total = sum(item["price"] * item["quantity"] for item in self.items)
        self.content.addWidget(label(counted(total_items, "вещь", "вещи", "вещей"), "muted"))
        row = QHBoxLayout()
        row.setSpacing(22)
        items = QVBoxLayout()
        items.setSpacing(10)
        for item in self.items:
            items.addWidget(self.cart_card(item))
        row.addLayout(items, 1)
        summary = surface()
        summary.setFixedWidth(305)
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(19, 16, 19, 19)
        summary_layout.setSpacing(13)
        summary_layout.addWidget(label("К оплате", "muted"))
        summary_layout.addWidget(label(rubles(total), "priceHero"))
        summary_layout.addWidget(divider())
        checkout = action("Оформить заказ", self.checkout, "primary")
        if any(item["quantity"] > item["stock"] for item in self.items):
            summary_layout.addWidget(label("Измени количество товаров с ограниченным остатком.", "error", True))
            checkout.setEnabled(False)
        summary_layout.addWidget(checkout)
        row.addWidget(summary, alignment=Qt.AlignmentFlag.AlignTop)
        self.content.addLayout(row)

    def cart_card(self, item):
        panel = surface()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(15)
        photo = Photo(
            item["image"], lambda: self.store.open_product(item["product_id"]), item["name"]
        )
        photo.setFixedSize(96, 96)
        layout.addWidget(photo)
        info = QVBoxLayout()
        info.addWidget(label(item["name"], "strong", True))
        info.addWidget(label(f"{item['color']}  /  {item['size']}", "muted"))
        if item["quantity"] > item["stock"]:
            info.addWidget(label(f"В наличии {item['stock']} шт.", "error"))
        info.addWidget(action("Убрать", lambda: self.set_quantity(item, 0), "link"),
                       alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(info, 1)

        controls = QHBoxLayout()
        controls.setSpacing(3)
        decrease = action("−", lambda: self.set_quantity(item, item["quantity"] - 1), "secondary",
                          tip="Уменьшить количество")
        decrease.setEnabled(item["quantity"] > 1)
        increase = action("+", lambda: self.set_quantity(item, item["quantity"] + 1), "secondary",
                          tip="Увеличить количество")
        increase.setEnabled(item["stock"] > item["quantity"])
        controls.addWidget(decrease)
        controls.addWidget(label(item["quantity"]))
        controls.addWidget(increase)
        layout.addLayout(controls)
        price = label(rubles(item["quantity"] * item["price"]), "strong")
        price.setMinimumWidth(89)
        price.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(price)
        return panel

    def set_quantity(self, item, quantity):
        try:
            self.store.db.set_cart_quantity(self.store.session.client_id, item["variant_id"], quantity)
        except ValueError as error:
            tell(self, "Корзина", str(error))
        self.store.refresh_identity()
        self.refresh()

    def checkout(self):
        dialog = CheckoutDialog(self.store, self.items)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.store.refresh_identity()
            self.store.open_account(history=True)
            self.store.toast(f"Заказ № {dialog.order_id:04} оформлен")
            order = self.store.db.order(dialog.order_id)
            OrderDialog(self.store, self.store.db, order).exec()
        else:
            self.refresh()
