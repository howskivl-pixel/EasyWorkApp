from __future__ import annotations

from typing import Iterable, Optional, Tuple

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from core.dxf_core import DXFAnalysisResult

Bounds = Tuple[float, float, float, float]


class DxfPreviewWidget(QWidget):
    """Simple canvas that renders the outline of the analysed DXF file."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._result: Optional[DXFAnalysisResult] = None
        self._bounds: Optional[Bounds] = None
        self.setMinimumHeight(260)

    def set_result(self, result: Optional[DXFAnalysisResult]) -> None:
        self._result = result
        self._bounds = self._compute_bounds(result)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), Qt.white)

        if not self._result or not self._bounds:
            painter.setPen(Qt.gray)
            painter.drawText(self.rect(), Qt.AlignCenter, "Предпросмотр недоступен")
            return

        minx, miny, maxx, maxy = self._bounds
        width = maxx - minx or 1.0
        height = maxy - miny or 1.0

        margin = 12.0
        available_width = max(1.0, self.width() - 2 * margin)
        available_height = max(1.0, self.height() - 2 * margin)
        scale = min(available_width / width, available_height / height)

        painter.translate(margin, margin)
        painter.scale(scale, scale)
        painter.translate(-minx, -miny)
        painter.scale(1, -1)
        painter.translate(0, -(miny + maxy))

        self._draw_polygons(painter)
        self._draw_open_lines(painter)

    def _draw_polygons(self, painter: QPainter) -> None:
        painter.setPen(QPen(Qt.black, 0))
        fill_brush = QColor("#87CEFA")

        for polygon in self._result.polygons:  # type: ignore[union-attr]
            exterior_path = self._coords_to_path(polygon.exterior.coords)
            painter.fillPath(exterior_path, fill_brush)
            painter.drawPath(exterior_path)

            for interior in polygon.interiors:
                hole_path = self._coords_to_path(interior.coords)
                painter.fillPath(hole_path, Qt.white)
                painter.drawPath(hole_path)

    def _draw_open_lines(self, painter: QPainter) -> None:
        line_pen = QPen(Qt.darkGray, 0)
        painter.setPen(line_pen)

        for line in self._result.open_lines:  # type: ignore[union-attr]
            polyline = QPolygonF([QPointF(x, y) for x, y in line.coords])
            painter.drawPolyline(polyline)

    @staticmethod
    def _coords_to_path(coords: Iterable[Tuple[float, float]]) -> QPainterPath:
        path = QPainterPath()
        iterator = iter(coords)
        try:
            first = next(iterator)
        except StopIteration:
            return path
        path.moveTo(*first)
        for x, y in iterator:
            path.lineTo(x, y)
        path.closeSubpath()
        return path

    @staticmethod
    def _compute_bounds(result: Optional[DXFAnalysisResult]) -> Optional[Bounds]:
        if result is None:
            return None

        if result.geometry is not None:
            return result.geometry.bounds

        xs = []
        ys = []
        for line in result.open_lines:
            for x, y in line.coords:
                xs.append(x)
                ys.append(y)

        if xs and ys:
            return min(xs), min(ys), max(xs), max(ys)

        return None
