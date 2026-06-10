"""Generate a simplified Tottori municipality SVG from MLIT N03 data.

Input zip:
  https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2024/N03-20240101_31_GML.zip
"""

from __future__ import annotations

import argparse
import html
import json
import math
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ZIP = Path("/private/tmp/N03-20240101_31_GML.zip")
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "assets" / "maps" / "tottori-municipalities.svg"
DEFAULT_TOLERANCE = 0.0015
DEFAULT_MIN_AREA = 0.04
SOURCE_URL = "https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2024/N03-20240101_31_GML.zip"
SOURCE_ACQUIRED_DATE = "2026-06-11"
ACTIVE_COUNCILS = {
    "312011": "tottori-city",
    "312029": "yonago-city",
    "312037": "kurayoshi-city",
    "312045": "sakaiminato-city",
}


Point = tuple[float, float]
Ring = list[Point]


def point_line_distance(point: Point, start: Point, end: Point) -> float:
    x, y = point
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / math.hypot(dx, dy)


def rdp(points: Ring, tolerance: float) -> Ring:
    if len(points) <= 2:
        return points

    start = points[0]
    end = points[-1]
    max_distance = -1.0
    index = 0
    for i, point in enumerate(points[1:-1], start=1):
        distance = point_line_distance(point, start, end)
        if distance > max_distance:
            index = i
            max_distance = distance

    if max_distance > tolerance:
        left = rdp(points[: index + 1], tolerance)
        right = rdp(points[index:], tolerance)
        return left[:-1] + right
    return [start, end]


def simplify_ring(ring: Ring, tolerance: float) -> Ring:
    if len(ring) < 4:
        return ring
    points = ring[:-1] if ring[0] == ring[-1] else ring[:]
    simplified = rdp(points, tolerance)
    if len(simplified) < 3:
        simplified = points[:3]
    simplified.append(simplified[0])
    return simplified


def lg_code_from_jis5(jis5: str) -> str:
    weights = [6, 5, 4, 3, 2]
    remainder = sum(int(digit) * weight for digit, weight in zip(jis5, weights)) % 11
    check = 11 - remainder
    if check == 10:
        check = 0
    elif check == 11:
        check = 1
    return f"{jis5}{check}"


def extract_polygons(geometry: dict[str, Any]) -> list[list[Ring]]:
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geom_type == "Polygon":
        return [[[(float(lon), float(lat)) for lon, lat in ring] for ring in coordinates]]
    if geom_type == "MultiPolygon":
        return [
            [[(float(lon), float(lat)) for lon, lat in ring] for ring in polygon]
            for polygon in coordinates
        ]
    raise ValueError(f"Unsupported geometry type: {geom_type}")


def load_municipalities(source_zip: Path) -> dict[str, dict[str, Any]]:
    with zipfile.ZipFile(source_zip) as archive:
        geojson_name = next(
            name for name in archive.namelist() if name.endswith(".geojson")
        )
        data = json.loads(archive.read(geojson_name))

    municipalities: dict[str, dict[str, Any]] = {}
    for feature in data["features"]:
        props = feature["properties"]
        jis5 = props["N03_007"]
        lg_code = lg_code_from_jis5(jis5)
        if lg_code not in municipalities:
            municipalities[lg_code] = {
                "jis5": jis5,
                "lg_code": lg_code,
                "name": props["N03_004"],
                "polygons": [],
            }
        municipalities[lg_code]["polygons"].extend(
            extract_polygons(feature["geometry"])
        )
    return municipalities


def collect_bounds(
    municipalities: dict[str, dict[str, Any]],
) -> tuple[float, float, float, float]:
    lon_values: list[float] = []
    lat_values: list[float] = []
    for municipality in municipalities.values():
        for polygon in municipality["polygons"]:
            for ring in polygon:
                for lon, lat in ring:
                    lon_values.append(lon)
                    lat_values.append(lat)
    return min(lon_values), min(lat_values), max(lon_values), max(lat_values)


def projected_area(points: Ring) -> float:
    if len(points) < 4:
        return 0.0
    area = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        area += x1 * y2 - x2 * y1
    return abs(area) / 2


def path_for_polygon(
    polygon: list[Ring],
    tolerance: float,
    project,
    min_area: float,
) -> str | None:
    segments: list[str] = []
    for ring in polygon:
        simplified = simplify_ring(ring, tolerance)
        projected = [project(lon, lat) for lon, lat in simplified]
        if projected_area(projected) < min_area:
            continue
        commands = [
            f"M{projected[0][0]:.1f},{projected[0][1]:.1f}",
            *[f"L{x:.1f},{y:.1f}" for x, y in projected[1:]],
            "Z",
        ]
        segments.append(" ".join(commands))
    if not segments:
        return None
    return " ".join(segments)


def build_svg(
    municipalities: dict[str, dict[str, Any]],
    tolerance: float,
    min_area: float,
) -> str:
    min_lon, min_lat, max_lon, max_lat = collect_bounds(municipalities)
    mid_lat = (min_lat + max_lat) / 2
    x_scale = math.cos(math.radians(mid_lat)) * 1000
    y_scale = 1000
    padding = 12
    width = (max_lon - min_lon) * x_scale + padding * 2
    height = (max_lat - min_lat) * y_scale + padding * 2

    def project(lon: float, lat: float) -> Point:
        x = (lon - min_lon) * x_scale + padding
        y = (max_lat - lat) * y_scale + padding
        return x, y

    groups: list[str] = []
    for lg_code, municipality in sorted(municipalities.items()):
        paths: list[str] = []
        for polygon in municipality["polygons"]:
            path = path_for_polygon(polygon, tolerance, project, min_area)
            if path:
                paths.append(path)
        if not paths:
            continue

        name = html.escape(municipality["name"])
        active = lg_code in ACTIVE_COUNCILS
        classes = "municipality is-active" if active else "municipality is-inactive"
        council_attr = (
            f' data-council-id="{ACTIVE_COUNCILS[lg_code]}"' if active else ""
        )
        path_elements = "\n".join(
            f'    <path d="{path}" fill-rule="evenodd"/>'
            for path in paths
        )
        groups.append(
            "\n".join(
                [
                    (
                        f'  <g class="{classes}" data-lg-code="{lg_code}" '
                        f'data-jis-code="{municipality["jis5"]}" '
                        f'data-name="{name}"{council_attr}>'
                    ),
                    f"    <title>{name}</title>",
                    path_elements,
                    "  </g>",
                ]
            )
        )

    groups_text = "\n".join(groups)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg class="tottori-municipality-map" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.1f} {height:.1f}" role="img" aria-label="鳥取県の市町村地図">
  <title>鳥取県市町村地図</title>
  <desc>国土数値情報 N03 行政区域データ 2024年版から生成。簡略化 tolerance={tolerance}、取得日 {SOURCE_ACQUIRED_DATE}。</desc>
{groups_text}
</svg>
'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-zip", type=Path, default=DEFAULT_SOURCE_ZIP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    parser.add_argument("--min-area", type=float, default=DEFAULT_MIN_AREA)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.source_zip.exists():
        raise SystemExit(
            f"Source zip not found: {args.source_zip}\nDownload: {SOURCE_URL}"
        )
    municipalities = load_municipalities(args.source_zip)
    svg = build_svg(municipalities, args.tolerance, args.min_area)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8")
    print(
        f"Wrote {args.output} ({len(svg.encode('utf-8')):,} bytes, "
        f"{len(municipalities)} municipalities)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
