from collections import Counter

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from logic_units.accounts import MANAGERS, ROLES, full_name
from logic_units.formatting import display_date, rubles
from ui_units.analytics import AnalyticsPage
from ui_units.management import OrdersPage, PeoplePage, ProductsPage
from ui_units.orders import OrderDialog
from ui_units.widgets import Table, action, label, surface, tell


class Overview(QWidget):
    def __init__(self, staff):
        super().__init__()
        self.staff = staff
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 21, 26, 25)
        layout.setSpacing(16)
        layout.addWidget(label("Обзор магазина", "title"))

        orders = staff.db.orders()
        counts = Counter(order["status"] for order in orders)
        delivered = ("Доставлены", counts["Доставлен"], "Доставлен")
        if staff.role in MANAGERS:
            paid = sum(
                order["total"] for order in orders
                if order["payment_status"] == "Оплачен" and order["status"] != "Отменён"
            )
            delivered = ("Оплаченная выручка", rubles(paid), "analytics")
        metrics = (
            ("Новые заказы", counts["Новый"], "Новый"),
            ("В обработке", counts["В обработке"], "В обработке"),
            ("В доставке", counts["Передан курьеру"], "Передан курьеру"),
            delivered,
        )
        tiles = QGridLayout()
        tiles.setHorizontalSpacing(12)
        for index, (caption, value, target) in enumerate(metrics):
            tile = surface()
            box = QVBoxLayout(tile)
            box.setContentsMargins(14, 11, 14, 9)
            box.setSpacing(2)
            box.addWidget(label(caption, "muted", True))
            box.addWidget(label(value, "metric"))
            if target == "analytics":
                callback = staff.open_analytics
            else:
                callback = lambda _, status=target: staff.open_orders(status=status)
            box.addWidget(action("Открыть →", callback, "link"), alignment=Qt.AlignmentFlag.AlignLeft)
            tiles.addWidget(tile, 0, index)
            tiles.setColumnStretch(index, 1)
        layout.addLayout(tiles)

        header = QHBoxLayout()
        header.addWidget(label("Последние заказы", "section"))
        header.addStretch()
        header.addWidget(action("Все заказы →", staff.open_orders, "link"))
        layout.addLayout(header)
        self.recent = orders[:9]
        self.table = Table(("№", "Дата", "Покупатель", "Сумма", "Статус"), (58, 143, 218, 112, 165))
        self.table.fill([
            (f"{order['id']:04}", display_date(order["created_at"], with_time=True),
             order["customer"], rubles(order["total"]), order["status"])
            for order in self.recent
        ])
        self.table.doubleClicked.connect(self.details)
        layout.addWidget(self.table, 1)

    def details(self):
        index = self.table.currentRow()
        if index >= 0:
            order = self.staff.db.order(self.recent[index]["id"])
            if order:
                OrderDialog(self, self.staff.db, order).exec()


class StaffPage(QWidget):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.db = store.db
        self.role = store.session.role
        self.setObjectName("staffBody")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        side = QFrame()
        side.setObjectName("staffSide")
        side.setFixedWidth(194)
        navigation = QVBoxLayout(side)
        navigation.setContentsMargins(17, 21, 13, 16)
        navigation.setSpacing(5)
        navigation.addWidget(label("ELARA", "sideBrand"))
        navigation.addWidget(label("Панель сотрудников", "sideText"))
        navigation.addSpacing(21)
        links = [("overview", "Обзор", self.open_overview)]
        if self.role == "admin":
            links.append(("products", "Товары", self.open_products))
        links.extend((
            ("orders", "Заказы", self.open_orders),
            ("clients", "Клиенты", self.open_clients),
        ))
        if self.role in MANAGERS:
            links.extend((
                ("employees", "Сотрудники", self.open_people),
                ("analytics", "Аналитика", self.open_analytics),
            ))
        if self.role == "picker":
            links.extend((
                ("new", "Новые заказы", lambda: self.open_orders(status="Новый")),
                ("processing", "В обработке", lambda: self.open_orders(status="В обработке")),
            ))
        if self.role == "courier":
            links.extend((
                ("packed", "Готовые к доставке", lambda: self.open_orders(status="Собран")),
                ("delivery", "В доставке", lambda: self.open_orders(status="Передан курьеру")),
            ))
        self.links = {}
        for key, title, callback in links:
            item = action(title, callback, "side")
            item.setCheckable(True)
            navigation.addWidget(item)
            self.links[key] = item
        navigation.addStretch()
        navigation.addWidget(action("Выйти из аккаунта", store.logout, "side"))
        outer.addWidget(side)

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        head = QFrame()
        head.setObjectName("staffTop")
        head.setFixedHeight(64)
        toolbar = QHBoxLayout(head)
        toolbar.setContentsMargins(25, 8, 23, 8)
        toolbar.addWidget(action("← К витрине", store.open_store, "secondary"))
        toolbar.addStretch()
        self.identity = label("", "muted")
        toolbar.addWidget(self.identity)
        toolbar.addWidget(action("Профиль", self.profile, "utility", "user"))
        main_layout.addWidget(head)
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)
        outer.addWidget(main, 1)
        self.refresh_identity()
        self.open_overview()

    def refresh_identity(self):
        person = self.store.session.person
        self.identity.setText(f"{person['name']} {person['surname']}  ·  {ROLES[self.role]}")

    def show_page(self, key, page):
        previous = self.stack.currentWidget()
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        if previous is not None:
            self.stack.removeWidget(previous)
            previous.deleteLater()
        for name, button in self.links.items():
            button.setChecked(name == key)

    def open_overview(self):
        self.show_page("overview", Overview(self))

    def open_products(self):
        if self.role == "admin":
            self.show_page("products", ProductsPage(self))

    def open_orders(self, *, status=""):
        filters = {"Новый": "new", "В обработке": "processing", "Собран": "packed", "Передан курьеру": "delivery"}
        key = filters.get(status)
        self.show_page(key if key in self.links else "orders", OrdersPage(self, status))

    def open_clients(self):
        self.show_page("clients", PeoplePage(self))

    def open_people(self):
        if self.role in MANAGERS:
            self.show_page("employees", PeoplePage(self, employees=True))

    def open_analytics(self):
        if self.role in MANAGERS:
            self.show_page("analytics", AnalyticsPage(self.db))

    def profile(self):
        person = self.store.session.person
        tell(self, "Профиль сотрудника", "\n".join(
            (full_name(person), ROLES[person["role"]], person["phone"], person["email"])
        ))
