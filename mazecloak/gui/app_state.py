from PyQt6.QtCore import QObject, pyqtSignal

from mazecloak.gui.i18n import t as _t


class AppState(QObject):
    theme_changed = pyqtSignal(str)     # "dark" | "light"
    language_changed = pyqtSignal(str)  # "en" | "tr"

    def __init__(self, theme: str = "dark", language: str = "en"):
        super().__init__()
        self.theme = theme
        self.language = language

    def set_theme(self, theme: str) -> None:
        if theme != self.theme:
            self.theme = theme
            self.theme_changed.emit(theme)

    def set_language(self, lang: str) -> None:
        if lang != self.language:
            self.language = lang
            self.language_changed.emit(lang)

    def toggle_theme(self) -> None:
        self.set_theme("light" if self.theme == "dark" else "dark")

    def t(self, key: str) -> str:
        return _t(key, self.language)
