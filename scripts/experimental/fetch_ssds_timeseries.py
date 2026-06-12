#!/usr/bin/env python3
"""Fetch a small SSDS timeseries pilot from the e-Stat API.

This experimental script intentionally reads ESTAT_APP_ID from the environment
or a local .env file, and never writes the appId into generated artifacts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
ESTAT_ENDPOINT = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
DEFAULT_YEARS_BY_METRIC = {
    "population_total": list(range(2014, 2024)),
    "births": list(range(2013, 2023)),
    "fiscal_index": list(range(2012, 2022)),
}

AREAS = [
    {
        "council_id": "tottori-pref",
        "name": "鳥取県",
        "lg_code": "310000",
        "estat_area_code": "31000",
        "area_level": "prefecture",
    },
    {
        "council_id": "tottori-city",
        "name": "鳥取市",
        "lg_code": "312011",
        "estat_area_code": "31201",
        "area_level": "municipality",
    },
    {
        "council_id": "yonago-city",
        "name": "米子市",
        "lg_code": "312029",
        "estat_area_code": "31202",
        "area_level": "municipality",
    },
    {
        "council_id": "kurayoshi-city",
        "name": "倉吉市",
        "lg_code": "312037",
        "estat_area_code": "31203",
        "area_level": "municipality",
    },
    {
        "council_id": "sakaiminato-city",
        "name": "境港市",
        "lg_code": "312045",
        "estat_area_code": "31204",
        "area_level": "municipality",
    },
]

METRICS: dict[str, dict[str, Any]] = {
    "population_total": {
        "label": "住民基本台帳人口（総数）",
        "unit": "persons",
        "value_type": "integer",
        "period_type": "as_of_date",
        "notes": "SSDSの人口総数パイロットは、既存profileとの突合を優先してA2301を採用する。",
        "stats_data_id": {
            "prefecture": "0000010101",
            "municipality": "0000020101",
        },
        "item_code": {
            "prefecture": "A2301",
            "municipality": "A2301",
        },
    },
    "births": {
        "label": "出生数",
        "unit": "persons",
        "value_type": "integer",
        "period_type": "calendar_year",
        "notes": "人口動態統計由来の暦年値。SSDSでは年度ラベルで提供されるためsource_period_labelを保持する。",
        "stats_data_id": {
            "prefecture": "0000010101",
            "municipality": "0000020101",
        },
        "item_code": {
            "prefecture": "A4101",
            "municipality": "A4101",
        },
    },
    "fiscal_index": {
        "label": "財政力指数",
        "unit": "index",
        "value_type": "decimal",
        "period_type": "fiscal_year",
        "notes": "県と市でSSDS item codeが異なる。",
        "stats_data_id": {
            "prefecture": "0000010104",
            "municipality": "0000020104",
        },
        "item_code": {
            "prefecture": "D2101",
            "municipality": "D2201",
        },
    },
}


def load_app_id() -> str:
    env_value = os.environ.get("ESTAT_APP_ID")
    if env_value:
        return env_value.strip()

    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key == "ESTAT_APP_ID" and value.strip():
                return value.strip()

    raise RuntimeError("ESTAT_APP_ID is not set in environment or .env")


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def parse_number(raw: str, value_type: str) -> int | float | None:
    cleaned = raw.replace(",", "").strip()
    if cleaned in {"", "-", "***", "X", "x"}:
        return None
    if value_type == "integer":
        return int(float(cleaned))
    return float(cleaned)


def request_stats(app_id: str, stats_data_id: str, area_code: str, item_code: str) -> dict[str, Any]:
    params = {
        "appId": app_id,
        "lang": "J",
        "statsDataId": stats_data_id,
        "cdArea": area_code,
        "cdCat01": item_code,
        "metaGetFlg": "Y",
        "cntGetFlg": "N",
    }
    url = ESTAT_ENDPOINT + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "yonago-gikai-ssds-pilot/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def class_maps(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    class_objs = as_list(
        payload.get("GET_STATS_DATA", {})
        .get("STATISTICAL_DATA", {})
        .get("CLASS_INF", {})
        .get("CLASS_OBJ")
    )
    maps: dict[str, dict[str, str]] = {}
    for obj in class_objs:
        obj_id = obj.get("@id")
        classes = as_list(obj.get("CLASS"))
        maps[obj_id] = {
            str(item.get("@code")): str(item.get("@name"))
            for item in classes
            if item.get("@code") is not None
        }
    return maps


def extract_values(
    payload: dict[str, Any],
    metric_id: str,
    metric: dict[str, Any],
    area: dict[str, str],
    stats_data_id: str,
    item_code: str,
    years: list[int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = payload.get("GET_STATS_DATA", {})
    result = root.get("RESULT", {})
    if str(result.get("STATUS")) != "0":
        raise RuntimeError(f"e-Stat API error for {stats_data_id}/{item_code}/{area['estat_area_code']}: {result}")

    maps = class_maps(payload)
    time_map = maps.get("time", {})
    cat_map = maps.get("cat01", {})
    values = as_list(root.get("STATISTICAL_DATA", {}).get("DATA_INF", {}).get("VALUE"))
    by_year: dict[int, dict[str, Any]] = {}
    for item in values:
        time_code = str(item.get("@time", ""))
        if len(time_code) < 4 or not time_code[:4].isdigit():
            continue
        year = int(time_code[:4])
        if year not in years:
            continue
        raw = str(item.get("$", ""))
        value = parse_number(raw, str(metric["value_type"]))
        by_year[year] = {
            "year": year,
            "source_time_code": time_code,
            "source_period_label": time_map.get(time_code, f"{year}年度"),
            "value": value,
            "unit": item.get("@unit") or metric["unit"],
            "provenance": {
                "route": "ssds_api",
                "provider": "e-stat",
                "statsDataId": stats_data_id,
                "item_code": item_code,
                "item_label": cat_map.get(item_code, metric["label"]),
            },
        }

    rows: list[dict[str, Any]] = []
    for year in years:
        base = {
            "metric": metric_id,
            "label": metric["label"],
            "period_type": metric["period_type"],
            "council_id": area["council_id"],
            "name": area["name"],
            "lg_code": area["lg_code"],
            "estat_area_code": area["estat_area_code"],
            "area_level": area["area_level"],
        }
        value_row = by_year.get(year)
        if value_row is None:
            rows.append({**base, "year": year, "value": None, "missing": True})
        else:
            rows.append({**base, **value_row, "missing": False})

    diagnostics = {
        "statsDataId": stats_data_id,
        "item_code": item_code,
        "item_label": cat_map.get(item_code, metric["label"]),
        "area_code": area["estat_area_code"],
        "available_value_count": len(values),
        "selected_years": years,
        "missing_years": [row["year"] for row in rows if row["missing"]],
    }
    return rows, diagnostics


def load_profiles(profiles_dir: Path) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    if not profiles_dir.exists():
        return profiles
    for path in profiles_dir.glob("*/profile.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        council_id = data.get("council_id")
        if isinstance(council_id, str):
            profiles[council_id] = data
    return profiles


def profile_year(profile_item: dict[str, Any], key: str) -> int | None:
    if key == "population":
        as_of = profile_item.get("as_of")
        if isinstance(as_of, str) and len(as_of) >= 4 and as_of[:4].isdigit():
            return int(as_of[:4])
    if key == "fiscal_index":
        year = profile_item.get("fiscal_year")
        if isinstance(year, int):
            return year
    return None


def build_profile_checks(rows: list[dict[str, Any]], profiles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for metric_id, profile_key in (
        ("population_total", "population"),
        ("fiscal_index", "fiscal_index"),
    ):
        for area in AREAS:
            profile = profiles.get(area["council_id"], {})
            profile_item = profile.get(profile_key)
            if not isinstance(profile_item, dict) or "value" not in profile_item:
                continue
            metric_rows = [
                row for row in rows
                if row["metric"] == metric_id and row["council_id"] == area["council_id"] and not row.get("missing")
            ]
            if not metric_rows:
                continue
            latest = max(metric_rows, key=lambda row: row["year"])
            profile_value = profile_item["value"]
            ssds_value = latest["value"]
            diff = None
            pct_diff = None
            if isinstance(profile_value, (int, float)) and isinstance(ssds_value, (int, float)):
                diff = profile_value - ssds_value
                if ssds_value:
                    pct_diff = diff / ssds_value
            p_year = profile_year(profile_item, profile_key)
            if p_year == latest["year"]:
                status = "same_year_match" if diff is not None and abs(diff) <= (0.01 if metric_id == "fiscal_index" else max(1, abs(ssds_value) * 0.005)) else "same_year_diff"
            else:
                status = "year_or_definition_diff"
            checks.append(
                {
                    "metric": metric_id,
                    "council_id": area["council_id"],
                    "name": area["name"],
                    "ssds_year": latest["year"],
                    "ssds_value": ssds_value,
                    "profile_year": p_year,
                    "profile_value": profile_value,
                    "difference_profile_minus_ssds": diff,
                    "relative_difference": pct_diff,
                    "status": status,
                    "profile_source": profile_item.get("source_name"),
                }
            )
    return checks


def fetch_pilot(metric_ids: list[str], years_by_metric: dict[str, list[int]], profiles_dir: Path) -> dict[str, Any]:
    app_id = load_app_id()
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for metric_id in metric_ids:
        metric = METRICS[metric_id]
        years = years_by_metric[metric_id]
        for area in AREAS:
            level = area["area_level"]
            stats_data_id = metric["stats_data_id"][level]
            item_code = metric["item_code"][level]
            payload = request_stats(app_id, stats_data_id, area["estat_area_code"], item_code)
            extracted, diag = extract_values(payload, metric_id, metric, area, stats_data_id, item_code, years)
            rows.extend(extracted)
            diagnostics.append({"metric": metric_id, "council_id": area["council_id"], **diag})

    expected_points = sum(len(AREAS) * len(years_by_metric[metric_id]) for metric_id in metric_ids)
    missing = [row for row in rows if row.get("missing")]
    profiles = load_profiles(profiles_dir)
    profile_checks = build_profile_checks(rows, profiles)
    return {
        "schema_version": "0.1-pilot",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": {
            "provider": "e-stat",
            "api": "getStatsData",
            "endpoint": ESTAT_ENDPOINT,
            "appId_included": False,
        },
        "years_by_metric": years_by_metric,
        "areas": AREAS,
        "metrics": {metric_id: METRICS[metric_id] for metric_id in metric_ids},
        "summary": {
            "requested_metrics": metric_ids,
            "expected_points": expected_points,
            "actual_points": len([row for row in rows if not row.get("missing")]),
            "missing_points": len(missing),
            "complete": len(missing) == 0,
        },
        "diagnostics": diagnostics,
        "profile_checks": profile_checks,
        "values": rows,
    }


def parse_metrics(value: str) -> list[str]:
    if value == "all":
        return list(METRICS)
    metric_ids = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(metric_ids) - set(METRICS))
    if unknown:
        raise SystemExit(f"unknown metrics: {', '.join(unknown)}")
    return metric_ids


def parse_years(value: str) -> list[int]:
    if ":" in value:
        start_raw, end_raw = value.split(":", 1)
        start = int(start_raw)
        end = int(end_raw)
        return list(range(start, end + 1))
    years = [int(item.strip()) for item in value.split(",") if item.strip()]
    if len(years) != len(set(years)):
        raise SystemExit("duplicate years are not allowed")
    return sorted(years)


def build_years_by_metric(metric_ids: list[str], years_arg: str) -> dict[str, list[int]]:
    if years_arg == "auto":
        return {metric_id: DEFAULT_YEARS_BY_METRIC[metric_id] for metric_id in metric_ids}
    years = parse_years(years_arg)
    return {metric_id: years for metric_id in metric_ids}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", default="all", help="all or comma-separated metric ids")
    parser.add_argument("--years", default="auto", help="auto, YYYY:YYYY, or comma-separated years")
    parser.add_argument("--profiles-dir", type=Path, default=REPO_ROOT / "docs" / "data")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "research" / "ssds_timeseries_pilot.json")
    args = parser.parse_args()

    metric_ids = parse_metrics(args.metrics)
    years_by_metric = build_years_by_metric(metric_ids, args.years)
    payload = fetch_pilot(metric_ids, years_by_metric, args.profiles_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "metrics={} years={}-{} points={}/{} missing={}".format(
            ",".join(metric_ids),
            min(min(years) for years in years_by_metric.values()),
            max(max(years) for years in years_by_metric.values()),
            payload["summary"]["actual_points"],
            payload["summary"]["expected_points"],
            payload["summary"]["missing_points"],
        )
    )
    by_metric: dict[str, int] = {}
    for row in payload["values"]:
        if not row.get("missing"):
            by_metric[row["metric"]] = by_metric.get(row["metric"], 0) + 1
    for metric_id in metric_ids:
        print(f"{metric_id}: {by_metric.get(metric_id, 0)} values")
    for check in payload["profile_checks"]:
        if check["metric"] in {"population_total", "fiscal_index"}:
            print(
                "{metric} {name}: ssds={ssds_value}({ssds_year}) profile={profile_value}({profile_year}) {status}".format(
                    **check
                )
            )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
