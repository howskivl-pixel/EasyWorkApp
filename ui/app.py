import sys
from typing import Any

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from .state import app_state
from .tab_estimate import EstimateTab
from .tab_import import DxfImportTab


class EasyWorkWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("EasyWork")
        self.resize(900, 600)

        tabs = QTabWidget()

        self.import_tab = DxfImportTab()
        self.import_tab.dxf_loaded.connect(self._handle_dxf_loaded)
        tabs.addTab(self.import_tab, "Загрузить файл для расчёта")

        self.estimate_tab = EstimateTab()
        tabs.addTab(self.estimate_tab, "Смета")

        self.nomenclature_tab = self._make_placeholder("Номенклатура")
        tabs.addTab(self.nomenclature_tab, "Номенклатура")

        self.setCentralWidget(tabs)

    def _make_placeholder(self, title: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(f"Вкладка «{title}» пока в разработке."))
        layout.addStretch(1)
        return widget

    def _handle_dxf_loaded(self, result: Any) -> None:
        """Receive DXF analysis and propagate it to other tabs."""

        app_state.dxf_result = result
        self.estimate_tab.refresh()


def main() -> int:
    app = QApplication(sys.argv)
    window = EasyWorkWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
