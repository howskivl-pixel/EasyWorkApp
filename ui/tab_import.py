from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.dxf_core import DXFAnalysisResult, analyze_dxf

from .widgets import DxfPreviewWidget


class DxfImportTab(QWidget):
    """Tab that lets the user load a DXF file and view calculated metrics."""

    dxf_loaded = Signal(object)  # emits DXFAnalysisResult

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result: DXFAnalysisResult | None = None
        self._path_label = QLabel("Файл не выбран")
        self._path_label.setWordWrap(True)

        self._preview = DxfPreviewWidget()

        self._area_label = QLabel("-")
        self._length_label = QLabel("-")
        self._width_label = QLabel("-")
        self._height_label = QLabel("-")
        self._scale_label = QLabel("-")

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        select_btn = QPushButton("Выбрать DXF файл…")
        select_btn.clicked.connect(self._handle_select_clicked)
        layout.addWidget(select_btn)

        layout.addWidget(self._path_label)

        preview_group = QGroupBox("Предпросмотр")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.addWidget(self._preview)
        layout.addWidget(preview_group)

        metrics_group = QGroupBox("Результаты расчёта")
        metrics_form = QFormLayout(metrics_group)
        metrics_form.addRow("Масштаб (1 unit → мм):", self._scale_label)
        metrics_form.addRow("Чистая площадь (см²):", self._area_label)
        metrics_form.addRow("Длина кривой (м):", self._length_label)
        metrics_form.addRow("Габаритная ширина (мм):", self._width_label)
        metrics_form.addRow("Габаритная высота (мм):", self._height_label)
        layout.addWidget(metrics_group)

        layout.addStretch(1)

    def _handle_select_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите DXF файл",
            "",
            "DXF файлы (*.dxf);;Все файлы (*.*)",
        )
        if not file_path:
            return

        path_obj = Path(file_path)
        try:
            result = analyze_dxf(path_obj)
        except Exception as exc:  # pylint: disable=broad-except
            QMessageBox.critical(
                self,
                "Ошибка анализа",
                f"Не удалось обработать файл:\n{exc}",
            )
            return

        self._result = result
        self._update_metrics(result)
        self.dxf_loaded.emit(result)

    def _update_metrics(self, result: DXFAnalysisResult) -> None:
        self._path_label.setText(
            f"Загружен файл: {result.source_path.name} (путь: {result.source_path})"
        )
        self._preview.set_result(result)
        self._scale_label.setText(f"{result.scale_factor:.3f}")
        self._area_label.setText(f"{result.area_cm2:.2f}")
        self._length_label.setText(f"{result.length_m:.3f}")
        self._width_label.setText(f"{result.width_mm:.2f}")
        self._height_label.setText(f"{result.height_mm:.2f}")

    @property
    def result(self) -> DXFAnalysisResult | None:
        """Return the last successful DXF analysis."""

        return self._result
