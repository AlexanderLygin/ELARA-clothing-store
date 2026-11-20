from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from logic_units.accounts import MANAGERS, ROLES, full_name
from logic_units.catalog import CATEGORIES, CatalogFilter
from logic_units.formatting import counted, display_date, rubles
from logic_units.orders import PAYMENT_STATUSES, STATUSES, STATUS_BY_ROLE
from ui_units.accounts import EditAccountDialog
from ui_units.orders import OrderDialog
from ui_units.product_editor import ProductEditor
from ui_units.widgets import FormDialog, Table, action, combo, confirm, divider, label, tell


class RecordSearch(FormDialog):
    def __init__(self, parent, spec, old):
        super().__init__(parent, "Расширенный поиск")
        form = QFormLayout()
        form.setVerticalSpacing(9)
        self.fields = {}
        for key, title, choices in spec:
            if choices:
                field = combo({"": "Любой вариант"} | choices, old.get(key, ""))
            else:
                field = QLineEdit(old.get(key, ""))
                field.setMaxLength(120)
            self.fields[key] = field
            form.addRow(title, field)
        self.body.addLayout(form)
        self.set_actions("Найти", self.accept)

    def values(self):
        return {
            key: field.text().strip() if isinstance(field, QLineEdit) else field.currentData()
            for key, field in self.fields.items()
        }


class RecordsPage(QWidget):
    def __init__(self, staff, title, columns, widths, hint, spec):
        super().__init__()
        self.staff = staff
        self.db = staff.db
        self.role = staff.role
        self.spec = spec
        self.criteria = {}
        self.records = []
        self.row_actions = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 25)
        layout.setSpacing(13)
        header = QHBoxLayout()
        header.addWidget(label(title, "title"))
        header.addStretch()
        self.count = label("", "muted")
        header.addWidget(self.count, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(header)

        self.toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.setPlaceholderText(hint)
        self.search.setMaxLength(120)
        self.search.setMinimumWidth(200)
        self.search.textChanged.connect(self.refresh)
        self.toolbar.addWidget(self.search, 1)
        self.filter_button = action("Поиск по полям", self.advanced, "secondary")
        self.toolbar.addWidget(self.filter_button)
        self.toolbar.addWidget(action("Сбросить", self.reset, "link"))
        layout.addLayout(self.toolbar)
        layout.addWidget(divider())
        self.table = Table(columns, widths)
        self.table.itemSelectionChanged.connect(self.enable_row_actions)
        layout.addWidget(self.table, 1)
        self.bottom = QHBoxLayout()
        self.bottom.addStretch()
        layout.addLayout(self.bottom)

    def enable_row_actions(self):
        enabled = self.table.currentRow() >= 0 and bool(self.table.selectionModel().selectedRows())
        for button in self.row_actions:
            button.setEnabled(enabled)

    def selected(self):
        if self.table.selectionModel().selectedRows():
            return self.records[self.table.currentRow()]
        return None

    def row_action(self, title, callback, role="secondary"):
        button = action(title, callback, role)
        self.bottom.addWidget(button)
        self.row_actions.append(button)
        button.setEnabled(False)

    def advanced(self):
        dialog = RecordSearch(self, self.spec, self.criteria)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.criteria = dialog.values()
            self.refresh()

    def reset(self):
        self.criteria = {}
        self.search.clear()
        self.refresh()

    def refresh(self):
        self.table.clearSelection()
        self.records, display = self.data(self.search.text(), self.criteria)
        self.table.fill(display)
        self.count.setText(counted(len(self.records), "запись", "записи", "записей"))
        self.filter_button.setText("Поиск по полям •" if any(self.criteria.values()) else "Поиск по полям")
        self.enable_row_actions()


class ProductsPage(RecordsPage):
    def __init__(self, staff):
        spec = (
            ("sku", "Артикул", None), ("name", "Название", None), ("material", "Материал", None),
            ("style", "Стиль", None), ("category", "Раздел", {k: c[0] for k, c in CATEGORIES.items()}),
            ("subcategory", "Подкатегория", {name: name for c in CATEGORIES.values() for name in c[1]}),
        )
        super().__init__(
            staff, "Товары", ("Артикул", "Модель", "Раздел", "Подкатегория", "Цена от", "Остаток"),
            (91, 220, 133, 125, 105, 75), "Артикул, модель, материал", spec,
        )
        self.bottom.insertWidget(0, action("Добавить товар", self.add, "primary"))
        self.row_action("Редактировать", self.edit)
        self.row_action("Удалить", self.remove, "link")
        self.table.doubleClicked.connect(self.edit)
        self.refresh()

    def data(self, query, fields):
        filters = CatalogFilter(query=query, category=fields.get("category", ""),
                                subcategory=fields.get("subcategory", ""))
        rows = self.db.products(filters, fields=fields)
        return rows, [
            (p["sku"], p["name"], p["category"], p["subcategory"], rubles(p["price"]), p["stock"])
            for p in rows
        ]

    def add(self):
        if ProductEditor(self, self.db).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def edit(self):
        product = self.selected()
        if product and ProductEditor(self, self.db, product).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def remove(self):
        product = self.selected()
        if product and confirm(self, "Удалить товар", f"Удалить «{product['name']}» из каталога?"):
            self.db.delete_product(product["id"])
            self.refresh()


class PeoplePage(RecordsPage):
    def __init__(self, staff, employees=False):
        self.employees = employees
        spec = [
            ("id", "Номер записи", None), ("surname", "Фамилия", None), ("name", "Имя", None),
            ("patronymic", "Отчество", None), ("phone", "Телефон", None), ("email", "Почта", None),
        ]
        columns = ("№", "ФИО", "Телефон", "Эл. почта", "Дата рождения")
        widths = (47, 197, 132, 155, 117)
        if employees:
            columns += ("Должность", "Паспорт")
            widths += (134, 103)
            spec.append(("role", "Должность", {key: value for key, value in ROLES.items() if key != "client"}))
        super().__init__(
            staff, "Сотрудники" if employees else "Клиенты", columns, widths,
            "Фамилия, телефон, почта", spec,
        )
        editable = self.role == "admin" if employees else self.role in MANAGERS
        if editable:
            if employees:
                self.bottom.insertWidget(0, action("Добавить сотрудника", self.add, "primary"))
            self.row_action("Редактировать", self.edit)
            self.row_action("Удалить", self.remove, "link")
            self.table.doubleClicked.connect(self.edit)
        else:
            self.row_action("Сведения", self.details)
            self.table.doubleClicked.connect(self.details)
        self.refresh()

    def data(self, query, fields):
        rows = self.db.people(staff=self.employees, query=query, fields=fields)
        display = []
        for person in rows:
            line = (person["id"], full_name(person), person["phone"], person["email"], display_date(person["birthday"]))
            if self.employees:
                line += (ROLES[person["role"]], person["passport"])
            display.append(line)
        return rows, display

    def details(self):
        person = self.selected()
        if person:
            texts = (full_name(person), person["phone"], person["email"], display_date(person["birthday"]))
            tell(self, "Данные аккаунта", "\n".join(texts))

    def add(self):
        if EditAccountDialog(self, self.db, staff=True).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def edit(self):
        person = self.selected()
        if not person:
            return
        editing_self = person["id"] == self.staff.store.session.person["id"]
        dialog = EditAccountDialog(self, self.db, person, self.employees, allow_role_change=not editing_self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if editing_self:
                self.staff.store.session.person = dialog.person
                self.staff.refresh_identity()
            self.refresh()

    def remove(self):
        person = self.selected()
        if not person:
            return
        if person["id"] == self.staff.store.session.person["id"]:
            tell(self, "Сотрудники", "Текущий аккаунт можно удалить из другого аккаунта администратора.")
            return
        if confirm(self, "Удалить аккаунт", f"Удалить аккаунт «{full_name(person)}»?"):
            try:
                self.db.delete_person(person["id"])
            except ValueError as error:
                tell(self, "Аккаунт", str(error))
            self.refresh()


class ChangeOrderDialog(FormDialog):
    def __init__(self, parent, db, order, role):
        super().__init__(parent, f"Статус заказа № {order['id']:04}")
        self.db = db
        self.order = order
        self.role = role
        form = QFormLayout()
        choices = list(dict.fromkeys((*STATUS_BY_ROLE[role], order["status"])))
        self.status = combo(choices, order["status"])
        form.addRow("Статус", self.status)
        self.payment = None
        if role in MANAGERS:
            self.payment = combo(PAYMENT_STATUSES, order["payment_status"])
            form.addRow("Оплата", self.payment)
        self.body.addLayout(form)
        self.set_actions("Сохранить статус", self.save)

    def save(self):
        try:
            self.db.change_order(
                self.order["id"], self.role, self.status.currentData(),
                self.payment.currentData() if self.payment else None,
            )
        except ValueError as error:
            self.show_error(error)
            return
        self.accept()


class OrdersPage(RecordsPage):
    def __init__(self, staff, status=""):
        spec = (
            ("id", "Номер заказа", None), ("customer", "Покупатель", None), ("phone", "Телефон", None),
            ("status", "Статус", {key: key for key in STATUSES}),
            ("payment_status", "Оплата", {key: key for key in PAYMENT_STATUSES}),
        )
        super().__init__(
            staff, "Заказы", ("№", "Дата", "Покупатель", "Телефон", "Сумма", "Оплата", "Статус", "Адрес"),
            (55, 132, 165, 128, 104, 111, 135, 220), "Номер, получатель, телефон, адрес", spec,
        )
        self.criteria["status"] = status
        self.row_action("Состав заказа", self.details)
        if self.role in STATUS_BY_ROLE:
            self.row_action("Изменить статус", self.change, "primary")
        if self.role in MANAGERS:
            self.row_action("Удалить", self.remove, "link")
        self.table.doubleClicked.connect(self.details)
        self.refresh()

    def data(self, query, fields):
        rows = self.db.orders(query=query, fields=fields)
        return rows, [
            (f"{order['id']:04}", display_date(order["created_at"], with_time=True), order["customer"],
             order["phone"], rubles(order["total"]), order["payment_status"], order["status"], order["address"])
            for order in rows
        ]

    def details(self):
        order = self.selected()
        if order:
            current = self.db.order(order["id"])
            if current:
                OrderDialog(self, self.db, current).exec()

    def change(self):
        order = self.selected()
        if order and ChangeOrderDialog(self, self.db, order, self.role).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def remove(self):
        order = self.selected()
        if order and confirm(self, "Удалить заказ", f"Удалить заказ № {order['id']:04}?"):
            self.db.delete_order(order["id"])
            self.refresh()
