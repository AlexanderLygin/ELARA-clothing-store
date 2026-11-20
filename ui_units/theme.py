from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPalette

from logic_units.paths import RESOURCES


def apply_theme(app):
    for font in ("Cormorant-Garamond.ttf", "Golos-Text.ttf"):
        QFontDatabase.addApplicationFont(str(RESOURCES / "fonts" / font))

    font = QFont("Golos Text")
    font.setPixelSize(13)
    app.setFont(font)

    palette = app.palette()
    for role, color in (
        (QPalette.ColorRole.Window, "#f7f4ee"),
        (QPalette.ColorRole.WindowText, "#272222"),
        (QPalette.ColorRole.Base, "#fffdf8"),
        (QPalette.ColorRole.Text, "#272222"),
        (QPalette.ColorRole.ButtonText, "#272222"),
        (QPalette.ColorRole.Highlight, "#78384a"),
        (QPalette.ColorRole.HighlightedText, "#fffdf8"),
        (QPalette.ColorRole.PlaceholderText, "#786b64"),
    ):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    stylesheet = (RESOURCES / "styles" / "elara.qss").read_text(encoding="utf-8")
    app.setStyleSheet(stylesheet.replace("@RESOURCES@", RESOURCES.as_posix()))
