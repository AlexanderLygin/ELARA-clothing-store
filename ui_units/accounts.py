from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLineEdit, QTabWidget, QVBoxLayout, QWidget

from logic_units.accounts import ROLES, full_name
from logic_units.formatting import display_date, rubles
from ui_units.widgets import (
    FormDialog, Table, action, clear_layout, combo, day_edit, empty_state, iso_date, label,
    password_entry, scroll_page, surface,
)


class AccountForm(QWidget):
    def __init__(self, person=None, staff=False, allow_role_change=True):
        super().__init__()
        person = person or {}
        self.staff = staff
        self.fields = {}
        self.role = None
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(7)
        for key, title, placeholder in (
            ("surname", "Фамилия", ""),
            ("name", "Имя", ""),
            ("patronymic", "Отчество", "Если есть"),
            ("phone", "Телефон", "+7 900 123-45-67"),
            ("email", "Эл. почта", "name@example.com"),
        ):
            field = QLineEdit(person.get(key, ""))
            field.setPlaceholderText(placeholder)
            field.setMaxLength(120)
            self.fields[key] = field
            form.addRow(title, field)

        born = QDate.fromString(person.get("birthday", ""), "yyyy-MM-dd")
        self.birthday = day_edit(born if born.isValid() else QDate.currentDate().addYears(-21))
        self.birthday.setMaximumDate(QDate.currentDate())
        form.insertRow(3, "Дата рождения", self.birthday)
        if staff:
            self.role = combo({key: name for key, name in ROLES.items() if key != "client"},
                              person.get("role", "operator"))
            self.role.setEnabled(allow_role_change)
            form.addRow("Должность", self.role)
            passport = QLineEdit(person.get("passport", ""))
            passport.setMaxLength(60)
            self.fields["passport"] = passport
            form.addRow("Паспорт", passport)

        pw, self.password = password_entry("Оставь пустым, чтобы сохранить" if person else "От 8 символов")
        repeat, self.repeat = password_entry()
        form.addRow("Новый пароль" if person else "Пароль", pw)
        form.addRow("Повтори пароль", repeat)

    def values(self):
        if self.password.text() != self.repeat.text():
            raise ValueError("Пароли не совпадают.")
        data = {key: field.text() for key, field in self.fields.items()}
        data.update(birthday=iso_date(self.birthday), password=self.password.text())
        return data

    def selected_role(self):
        return self.role.currentData() if self.staff else "client"


class LoginDialog(FormDialog):
    def __init__(self, parent, db):
        super().__init__(parent, "Вход в ELARA")
        self.db = db
        self.person = None
        self.show_login()

    def change_form(self, title):
        self.setWindowTitle(title)
        self.heading.setText(title)
        clear_layout(self.body)
        clear_layout(self.footer)
        self.footer.addStretch()
        self.show_error("")

    def fit_form(self):
        self.layout.activate()
        self.resize(self.width(), self.minimumSizeHint().height())

    def show_login(self):
        self.change_form("Вход в ELARA")
        self.body.addWidget(label("Войти могут покупатели и сотрудники.", "muted"))
        form = QFormLayout()
        form.setVerticalSpacing(9)
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("+7 900 123-45-67")
        self.phone.setMaxLength(25)
        panel, self.password = password_entry()
        form.addRow("Телефон", self.phone)
        form.addRow("Пароль", panel)
        self.body.addLayout(form)
        self.body.addWidget(action("Создать аккаунт", self.show_registration, "link"),
                            alignment=Qt.AlignmentFlag.AlignLeft)
        self.set_actions("Войти", self.login)
        self.phone.setFocus()
        self.fit_form()

    def login(self):
        person = self.db.authenticate(self.phone.text(), self.password.text())
        if person is None:
            self.show_error("Телефон или пароль введён неверно.")
            return
        self.person = person
        self.accept()

    def show_registration(self):
        self.change_form("Регистрация")
        self.registration = AccountForm()
        self.body.addWidget(self.registration)
        self.footer.insertWidget(0, action("Уже есть аккаунт", self.show_login, "link"))
        self.set_actions("Зарегистрироваться", self.register)
        self.fit_form()

    def register(self):
        try:
            self.person = self.db.save_person(self.registration.values())
        except ValueError as error:
            self.show_error(error)
            return
        self.accept()


class EditAccountDialog(FormDialog):
    def __init__(self, parent, db, person=None, staff=False, allow_role_change=True):
        title = "Данные сотрудника" if staff else "Личные данные"
        if not person and staff:
            title = "Новый сотрудник"
        super().__init__(parent, title, 560)
        self.db = db
        self.person = person
        self.form = AccountForm(person, staff, allow_role_change)
        self.body.addWidget(self.form)
        self.set_actions("Сохранить", self.save)

    def save(self):
        try:
            self.person = self.db.save_person(
                self.form.values(), self.form.selected_role(),
                self.person["id"] if self.person else None,
            )
        except ValueError as error:
            self.show_error(error)
            return
        self.accept()


class AccountPage(QWidget):
    def __init__(self, store, history=False):
        super().__init__()
        self.store = store
        self.person = store.session.person
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        area, layout = scroll_page()
        outer.addWidget(area)
        layout.addWidget(label("ELARA  /  АККАУНТ", "eyebrow"))
        titlebar = QHBoxLayout()
        titlebar.addWidget(label("Личный кабинет", "title"))
        titlebar.addStretch()
        titlebar.addWidget(action("Выйти", store.logout, "secondary"))
        layout.addLayout(titlebar)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.profile(), "Профиль")
        self.tabs.addTab(self.history(), "История заказов")
        self.tabs.setCurrentIndex(1 if history else 0)
        layout.addWidget(self.tabs)

    def profile(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(23, 19, 23, 22)
        panel = surface()
        form = QFormLayout(panel)
        form.setContentsMargins(22, 18, 22, 19)
        form.setVerticalSpacing(12)
        for title, value in (
            ("Имя", full_name(self.person)),
            ("Дата рождения", display_date(self.person["birthday"])),
            ("Телефон", self.person["phone"]),
            ("Эл. почта", self.person["email"]),
        ):
            form.addRow(label(title, "muted"), label(value, "strong", True))
        layout.addWidget(panel)
        layout.addWidget(action("Редактировать профиль", self.edit, "primary"),
                         alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        return page

    def history(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(23, 19, 23, 22)
        self.orders = self.store.db.orders(client_id=self.person["id"])
        if not self.orders:
            layout.addWidget(empty_state(
                "Заказов пока нет", "После покупки здесь появится статус заказа.",
                action("Открыть каталог", self.store.open_catalog, "link"),
            ))
            return page

        self.table = Table(("Заказ", "Дата", "Сумма", "Оплата", "Статус"), (105, 165, 135, 153, 180))
        self.table.fill([
            (f"№ {order['id']:04}", display_date(order["created_at"], with_time=True),
             rubles(order["total"]), order["payment_status"], order["status"])
            for order in self.orders
        ])
        self.table.setMinimumHeight(300)
        self.table.doubleClicked.connect(self.show_order)
        details = action("Открыть заказ", self.show_order, "secondary")
        details.setEnabled(False)
        self.table.itemSelectionChanged.connect(
            lambda: details.setEnabled(bool(self.table.selectionModel().selectedRows()))
        )
        layout.addWidget(self.table, 1)
        layout.addWidget(details, alignment=Qt.AlignmentFlag.AlignLeft)
        return page

    def show_order(self):
        from ui_units.orders import OrderDialog

        index = self.table.currentRow()
        if index >= 0:
            order = self.store.db.order(self.orders[index]["id"])
            if order and order["client_id"] == self.store.session.client_id:
                OrderDialog(self, self.store.db, order).exec()

    def edit(self):
        dialog = EditAccountDialog(self, self.store.db, self.person)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.store.session.person = dialog.person
            self.store.open_account()
            self.store.toast("Профиль обновлён")
