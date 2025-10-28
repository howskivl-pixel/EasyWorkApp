import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import ezdxf
import numpy as np
from shapely.geometry import LinearRing, LineString, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

Point = Tuple[float, float]
PointList = Tuple[bool, List[Point], str]


@dataclass
class DXFAnalysisResult:
    """Aggregated metrics extracted from a DXF file."""

    source_path: Path
    scale_factor: float
    area_cm2: float
    length_m: float
    width_mm: float
    height_mm: float
    geometry: Optional[BaseGeometry]
    polygons: List[Polygon]
    open_lines: List[LineString]


def units_to_mm_factor(insunits: Optional[int]) -> Optional[float]:
    mapping = {1: 25.4, 2: 304.8, 4: 1.0, 5: 10.0, 6: 1000.0}
    return mapping.get(insunits)


def approx_arc(cx: float, cy: float, r: float, start_angle: float, end_angle: float, pts: int = 120) -> List[Point]:
    sa = math.radians(start_angle)
    ea = math.radians(end_angle)
    if ea < sa:
        ea += 2 * math.pi
    angles = np.linspace(sa, ea, max(4, int(pts * abs(ea - sa) / (2 * math.pi))))
    return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in angles]


def approx_spline(spline, tol: float = 0.5) -> List[Point]:
    try:
        return [(p.x, p.y) for p in spline.flattening(tolerance=tol)]
    except Exception:
        try:
            cps = spline.control_points
            return [(float(p[0]), float(p[1])) for p in cps]
        except Exception:
            return []


def entity_to_pointlists(entity, scale: float = 1.0) -> List[PointList]:
    et = entity.dxftype()
    out: List[PointList] = []
    if et in ("LWPOLYLINE", "POLYLINE"):
        pts: List[Point] = []
        try:
            for v in entity.get_points():
                x = float(v[0]) * scale
                y = float(v[1]) * scale
                pts.append((x, y))
        except Exception:
            try:
                for v in entity.vertices():
                    x = float(v.dxf.location.x) * scale
                    y = float(v.dxf.location.y) * scale
                    pts.append((x, y))
            except Exception:
                pass
        closed = bool(getattr(entity, "closed", False) or (getattr(entity.dxf, "flag", 0) & 1))
        if pts:
            out.append((closed, pts, "poly"))
    elif et == "LINE":
        x1, y1 = entity.dxf.start.x * scale, entity.dxf.start.y * scale
        x2, y2 = entity.dxf.end.x * scale, entity.dxf.end.y * scale
        out.append((False, [(x1, y1), (x2, y2)], "line"))
    elif et == "CIRCLE":
        cx, cy, r = entity.dxf.center.x * scale, entity.dxf.center.y * scale, entity.dxf.radius * scale
        pts = approx_arc(cx, cy, r, 0, 360, pts=120)
        out.append((True, pts, "circle"))
    elif et == "ARC":
        cx, cy, r = entity.dxf.center.x * scale, entity.dxf.center.y * scale, entity.dxf.radius * scale
        sa, ea = entity.dxf.start_angle, entity.dxf.end_angle
        pts = approx_arc(cx, cy, r, sa, ea, pts=120)
        out.append((False, pts, "arc"))
    elif et == "SPLINE":
        pts = approx_spline(entity)
        pts = [(x * scale, y * scale) for x, y in pts]
        if pts:
            closed = bool(len(pts) >= 3 and abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][1] - pts[-1][1]) < 1e-6)
            out.append((closed, pts, "spline"))
    return out


def parse_dxf(path: Path | str) -> Tuple[List[PointList], float]:
    path = Path(path)
    doc = ezdxf.readfile(str(path))
    header = doc.header
    ins = header.get("$INSUNITS", None)
    factor = units_to_mm_factor(ins) or 1.0
    model = doc.modelspace()
    pointlists: List[PointList] = []
    for entity in model:
        try:
            chunk = entity_to_pointlists(entity, scale=factor)
            for closed, pts, etype in chunk:
                ptsf = [(float(x), float(y)) for x, y in pts if not (math.isnan(x) or math.isnan(y))]
                if len(ptsf) >= 2:
                    pointlists.append((closed, ptsf, etype))
        except Exception:
            continue
    return pointlists, factor


def build_polygons_with_holes(pointlists: Sequence[PointList]) -> Tuple[List[Polygon], List[LineString]]:
    closed_polys: List[dict] = []
    open_lines: List[LineString] = []
    for closed, pts, _ in pointlists:
        if closed:
            if pts[0] != pts[-1]:
                pts = list(pts) + [pts[0]]
            try:
                ring = LinearRing(pts)
                if not ring.is_valid:
                    continue
                poly = Polygon(ring)
                if poly.area > 1e-6:
                    closed_polys.append({"poly": poly, "pts": pts, "area": poly.area})
            except Exception:
                continue
        else:
            try:
                open_lines.append(LineString(pts))
            except Exception:
                pass
    closed_polys.sort(key=lambda x: x["area"])
    n = len(closed_polys)
    parent: List[Optional[int]] = [None] * n
    for i in range(n):
        pi = closed_polys[i]["poly"]
        for j in range(i + 1, n):
            pj = closed_polys[j]["poly"]
            if pj.contains(pi):
                parent[i] = j
                break
    outers: dict[int, dict[str, object]] = {}
    for i in range(n):
        if parent[i] is None:
            outers[i] = {"outer": closed_polys[i]["poly"], "holes": []}
    for i in range(n):
        par = parent[i]
        if par is None:
            continue
        anc = par
        while parent[anc] is not None:
            anc = parent[anc]
        record = outers.setdefault(anc, {"outer": closed_polys[anc]["poly"], "holes": []})
        record["holes"].append(list(closed_polys[i]["poly"].exterior.coords))
    polygons_out: List[Polygon] = []
    for idx, rec in outers.items():
        outer_poly = rec["outer"]  # type: ignore[assignment]
        holes = [list(coords) for coords in rec["holes"]]  # type: ignore[assignment]
        try:
            polygons_out.append(Polygon(list(outer_poly.exterior.coords), holes=holes))
        except Exception:
            polygons_out.append(outer_poly)
    return polygons_out, open_lines


def compute_metrics(polygons_out: Iterable[Polygon], open_lines: Iterable[LineString]) -> Tuple[float, float, float, float, Optional[BaseGeometry]]:
    polygons_out = list(polygons_out)
    open_lines = list(open_lines)
    geom: Optional[BaseGeometry] = unary_union(polygons_out) if polygons_out else None
    total_length_mm = geom.length if geom is not None else 0.0
    for ln in open_lines:
        try:
            total_length_mm += ln.length
        except Exception:
            pass
    area_mm2 = geom.area if geom is not None else 0.0
    if geom is not None:
        minx, miny, maxx, maxy = geom.bounds
    else:
        xs = [x for ln in open_lines for x, _ in ln.coords]
        ys = [y for ln in open_lines for _, y in ln.coords]
        if xs and ys:
            minx, maxx = min(xs), max(xs)
            miny, maxy = min(ys), max(ys)
        else:
            minx = miny = maxx = maxy = 0.0
    area_cm2 = area_mm2 / 100.0
    length_m = total_length_mm / 1000.0
    width_mm = maxx - minx
    height_mm = maxy - miny
    return area_cm2, length_m, width_mm, height_mm, geom


def analyze_dxf(path: Path | str) -> DXFAnalysisResult:
    """Process a DXF file and return geometry metrics."""

    path = Path(path)
    pointlists, factor = parse_dxf(path)
    polygons_out, open_lines = build_polygons_with_holes(pointlists)
    area_cm2, length_m, w_mm, h_mm, geom = compute_metrics(polygons_out, open_lines)
    return DXFAnalysisResult(
        source_path=path,
        scale_factor=factor,
        area_cm2=area_cm2,
        length_m=length_m,
        width_mm=w_mm,
        height_mm=h_mm,
        geometry=geom,
        polygons=list(polygons_out),
        open_lines=list(open_lines),
    )


__all__ = [
    "DXFAnalysisResult",
    "analyze_dxf",
    "build_polygons_with_holes",
    "compute_metrics",
    "entity_to_pointlists",
    "parse_dxf",
]
