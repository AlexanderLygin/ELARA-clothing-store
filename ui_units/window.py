from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QStackedWidget, QVBoxLayout, QWidget,
)

from logic_units.accounts import Session
from logic_units.catalog import CATEGORIES
from ui_units.accounts import AccountPage, LoginDialog
from ui_units.catalog import CatalogPage, HomePage
from ui_units.icons import icon
from ui_units.orders import CartPage
from ui_units.product import ProductDialog
from ui_units.staff import StaffPage
from ui_units.widgets import action, tell


class StoreWindow(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.session = Session()
        self.favorite_ids = set()
        self.staff = None
        self.extra_page = None
        self.setWindowTitle("ELARA")
        self.setMinimumSize(970, 640)
        self.layers = QStackedWidget()
        self.setCentralWidget(self.layers)
        self.front = QWidget()
        self.front.setObjectName("storefront")
        self.layers.addWidget(self.front)
        layout = QVBoxLayout(self.front)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header())
        layout.addWidget(self.navigation())
        self.pages = QStackedWidget()
        layout.addWidget(self.pages, 1)
        self.home = HomePage(self.db, self)
        self.catalog = CatalogPage(self.db, self)
        self.pages.addWidget(self.home)
        self.pages.addWidget(self.catalog)
        self.toast_label = QLabel(self)
        self.toast_label.setStyleSheet("background: #392129; color: #fff4e6; padding: 11px 17px;")
        self.toast_label.hide()
        self.toast_timer = QTimer(self)
        self.toast_timer.setSingleShot(True)
        self.toast_timer.timeout.connect(self.toast_label.hide)
        shortcut = QShortcut(QKeySequence.StandardKey.Find, self.front)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(self.focus_search)
        self.refresh_identity()
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1270, screen.width() - 30), min(900, screen.height() - 70))

    def header(self):
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(70)
        layout = QGridLayout(bar)
        layout.setContentsMargins(33, 5, 32, 5)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(2, 1)

        self.search = QLineEdit()
        self.search.setObjectName("storeSearch")
        self.search.setPlaceholderText("Поиск по каталогу")
        self.search.setAccessibleName("Поиск по каталогу")
        self.search.setMaxLength(90)
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(238)
        search_action = self.search.addAction(icon("search"), QLineEdit.ActionPosition.LeadingPosition)
        search_action.triggered.connect(self.find)
        self.search.returnPressed.connect(self.find)
        layout.addWidget(self.search, 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(action("ELARA", self.open_home, "brand", tip="Главная"), 0, 1)

        tools = QHBoxLayout()
        tools.setSpacing(1)
        tools.addStretch()
        self.staff_button = action("Управление", self.open_staff, "link")
        tools.addWidget(self.staff_button)
        tools.addWidget(action("", self.open_favorites, "utility", "heart", tip="Избранное"))
        self.bag = action("0", self.open_cart, "utility", "bag", tip="Корзина")
        tools.addWidget(self.bag)
        self.account_button = action("Войти", self.open_account, "utility", "user", tip="Аккаунт")
        tools.addWidget(self.account_button)
        layout.addLayout(tools, 0, 2)
        return bar

    def navigation(self):
        bar = QFrame()
        bar.setObjectName("storeNav")
        bar.setFixedHeight(47)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(12)
        layout.addStretch()
        self.categories = {}
        titles = {"new": "Новинки"} | {key: values[0] for key, values in CATEGORIES.items()} | {"all": "Весь каталог"}
        for key, title in titles.items():
            if key == "new":
                callback = lambda: self.open_catalog(collection="new")
            elif key == "all":
                callback = self.open_catalog
            else:
                callback = lambda _, category=key: self.open_catalog(category=category)
            button = action(title, callback, "nav")
            button.setCheckable(True)
            layout.addWidget(button)
            self.categories[key] = button
        layout.addStretch()
        return bar

    def focus_search(self):
        self.search.setFocus()
        self.search.selectAll()

    def find(self):
        self.open_catalog(query=self.search.text().strip())

    def set_page(self, page, selected=None):
        self.pages.setCurrentWidget(page)
        if self.extra_page is not None and self.extra_page is not page:
            self.pages.removeWidget(self.extra_page)
            self.extra_page.deleteLater()
            self.extra_page = None
        for key, button in self.categories.items():
            button.setChecked(key == selected)

    def open_home(self):
        self.search.clear()
        self.set_page(self.home)

    def open_catalog(self, *, category="", collection="", query="", saved=False):
        self.search.setText(query)
        self.catalog.open(category, collection, query, saved)
        selected = category or ("new" if collection else None if query or saved else "all")
        self.set_page(self.catalog, selected)

    def login(self, parent=None):
        dialog = LoginDialog(parent or self, self.db)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.session.person = dialog.person
            self.refresh_identity()
            return True
        return False

    def ensure_client(self, parent=None):
        if self.session.role is None and not self.login(parent):
            return False
        if self.session.client_id is None:
            tell(parent or self, "Аккаунт покупателя", "Для этого действия войди как покупатель.")
            return False
        return True

    def refresh_identity(self):
        self.favorite_ids = self.db.favorites(self.session.client_id)
        self.home.grid.refresh_hearts()
        self.catalog.grid.refresh_hearts()
        count = self.db.cart_quantity(self.session.client_id)
        self.bag.setText(str(count))
        self.bag.setToolTip(f"Корзина · {count}")
        self.account_button.setText("Профиль" if self.session.person else "Войти")
        self.staff_button.setVisible(self.session.is_staff)

    def open_product(self, product_id):
        product = self.db.product(product_id)
        if product:
            ProductDialog(self, product).exec()
        else:
            tell(self, "Каталог", "Товар уже удалён.")
            self.home.refresh()
            self.catalog.refresh()

    def toggle_favorite(self, product_id, parent=None):
        if not self.ensure_client(parent):
            return
        try:
            saved = self.db.toggle_favorite(self.session.client_id, product_id)
        except ValueError as error:
            tell(parent or self, "Избранное", str(error))
            return
        self.refresh_identity()
        if self.pages.currentWidget() is self.catalog and self.catalog.saved_only:
            self.catalog.refresh()
        self.toast("Сохранено в избранное" if saved else "Убрано из избранного")

    def open_favorites(self):
        if self.ensure_client():
            self.open_catalog(saved=True)

    def show_extra(self, page):
        self.pages.addWidget(page)
        self.set_page(page)
        self.extra_page = page

    def open_cart(self):
        if self.ensure_client():
            self.show_extra(CartPage(self))

    def open_account(self, *, history=False):
        if not self.session.person and not self.login():
            return
        if self.session.is_staff:
            self.open_staff()
        else:
            self.show_extra(AccountPage(self, history))

    def open_staff(self):
        if not self.session.is_staff:
            return
        if self.staff is None:
            self.staff = StaffPage(self)
            self.layers.addWidget(self.staff)
        self.layers.setCurrentWidget(self.staff)
        self.setWindowTitle("ELARA — Панель сотрудников")

    def open_store(self):
        self.home.refresh()
        if self.pages.currentWidget() is self.catalog:
            self.catalog.refresh()
        self.layers.setCurrentWidget(self.front)
        self.setWindowTitle("ELARA")

    def logout(self):
        self.session.person = None
        self.open_home()
        self.catalog.open()
        self.refresh_identity()
        self.open_store()
        if self.staff is not None:
            self.layers.removeWidget(self.staff)
            self.staff.deleteLater()
            self.staff = None
        self.toast("Выход выполнен")

    def position_toast(self):
        self.toast_label.move(self.width() - self.toast_label.width() - 34,
                              self.height() - self.toast_label.height() - 24)

    def toast(self, message):
        self.toast_label.setText(message)
        self.toast_label.adjustSize()
        self.position_toast()
        self.toast_label.raise_()
        self.toast_label.show()
        self.toast_timer.start(2500)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "toast_label"):
            self.position_toast()
