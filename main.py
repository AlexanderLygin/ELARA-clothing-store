import sys

from PyQt6.QtCore import QLocale, Qt
from PyQt6.QtWidgets import QApplication

from db_units.db import Database
from ui_units.theme import apply_theme
from ui_units.window import StoreWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ELARA")
    app.setApplicationDisplayName("ELARA")
    app.setStyle("Fusion")
    QLocale.setDefault(QLocale(QLocale.Language.Russian, QLocale.Country.Russia))
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus)
    apply_theme(app)
    window = StoreWindow(Database())
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
