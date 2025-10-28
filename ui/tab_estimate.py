from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .state import app_state


class EstimateTab(QWidget):
    """Displays summary info based on the loaded DXF file."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._info_label = QLabel("Нет данных DXF")
        self._info_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self._info_label)
        layout.addStretch(1)

    def refresh(self) -> None:
        result = app_state.dxf_result
        if result is None:
            self._info_label.setText("Нет данных DXF")
            return

        self._info_label.setText(
            (
                f"Площадь: {result.area_cm2:.2f} см²\n"
                f"Периметр: {result.length_m:.2f} м\n"
                f"Габариты: {result.width_mm:.2f} × {result.height_mm:.2f} мм"
            )
        )
