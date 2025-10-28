import sys

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from .tab_import import DxfImportTab


class EasyWorkWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EasyWork")
        self.resize(900, 600)

        self._dxf_result = None

        tabs = QTabWidget()

        self.import_tab = DxfImportTab()
        self.import_tab.dxf_loaded.connect(self._handle_dxf_loaded)
        tabs.addTab(self.import_tab, "Загрузить файл для расчёта")

        self.estimate_tab = self._make_placeholder("Смета")
        tabs.addTab(self.estimate_tab, "Смета")

        self.nomenclature_tab = self._make_placeholder("Номенклатура")
        tabs.addTab(self.nomenclature_tab, "Номенклатура")

        self.setCentralWidget(tabs)

    def _make_placeholder(self, title: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(f"Вкладка «{title}» пока в разработке."))
        return widget

    def _handle_dxf_loaded(self, result):
        """Receive DXF analysis and keep it available for other tabs."""

        self._dxf_result = result
        # TODO: notify estimate tab once it is implemented


def main():
    app = QApplication(sys.argv)
    window = EasyWorkWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
