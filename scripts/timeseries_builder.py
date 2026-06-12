#!/usr/bin/env python3
"""Build council-level SSDS timeseries data files.

Reads ESTAT_APP_ID from the environment or a local .env file. The appId is
only used for API requests and is never written to generated JSON.
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


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "docs" / "data"
ESTAT_ENDPOINT = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
INDICATOR_COUNT = 10

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

INDICATORS: dict[str, dict[str, Any]] = {
    "population_total": {
        "label": "住民基本台帳人口（総数）",
        "unit": "persons",
        "value_type": "integer",
        "stats_data_id": {
            "prefecture": "0000010101",
            "municipality": "0000020101",
        },
        "ssds_item": {
            "prefecture": "A2301",
            "municipality": "A2301",
        },
    },
    "births": {
        "label": "出生数",
        "unit": "persons",
        "value_type": "integer",
        "stats_data_id": {
            "prefecture": "0000010101",
            "municipality": "0000020101",
        },
        "ssds_item": {
            "prefecture": "A4101",
            "municipality": "A4101",
        },
    },
    "fiscal_index": {
        "label": "財政力指数",
        "unit": "index",
        "value_type": "decimal",
        "stats_data_id": {
            "prefecture": "0000010104",
            "municipality": "0000020104",
        },
        "ssds_item": {
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


def request_stats(
    app_id: str, stats_data_id: str, area_code: str, item_code: str
) -> dict[str, Any]:
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
    request = urllib.request.Request(
        url, headers={"User-Agent": "yonago-gikai-timeseries-builder/1.0"}
    )
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


def extract_series(
    payload: dict[str, Any],
    value_type: str,
    stats_data_id: str,
    area_code: str,
    item_code: str,
) -> dict[int, int | float]:
    root = payload.get("GET_STATS_DATA", {})
    result = root.get("RESULT", {})
    if str(result.get("STATUS")) != "0":
        raise RuntimeError(
            f"e-Stat API error for {stats_data_id}/{item_code}/{area_code}: {result}"
        )

    values = as_list(root.get("STATISTICAL_DATA", {}).get("DATA_INF", {}).get("VALUE"))
    by_year: dict[int, int | float] = {}
    for item in values:
        time_code = str(item.get("@time", ""))
        if len(time_code) < 4 or not time_code[:4].isdigit():
            continue
        parsed = parse_number(str(item.get("$", "")), value_type)
        if parsed is not None:
            by_year[int(time_code[:4])] = parsed
    return by_year


def fetch_all_series(app_id: str) -> dict[str, dict[str, dict[int, int | float]]]:
    fetched: dict[str, dict[str, dict[int, int | float]]] = {}
    for indicator_key, indicator in INDICATORS.items():
        fetched[indicator_key] = {}
        for area in AREAS:
            level = area["area_level"]
            stats_data_id = indicator["stats_data_id"][level]
            item_code = indicator["ssds_item"][level]
            payload = request_stats(
                app_id, stats_data_id, area["estat_area_code"], item_code
            )
            fetched[indicator_key][area["council_id"]] = extract_series(
                payload,
                indicator["value_type"],
                stats_data_id,
                area["estat_area_code"],
                item_code,
            )
    return fetched


def latest_common_years(
    fetched: dict[str, dict[str, dict[int, int | float]]]
) -> dict[str, list[int]]:
    years_by_indicator: dict[str, list[int]] = {}
    for indicator_key, area_series in fetched.items():
        common_years: set[int] | None = None
        for area in AREAS:
            years = set(area_series[area["council_id"]])
            common_years = years if common_years is None else common_years & years
        if common_years is None or len(common_years) < INDICATOR_COUNT:
            raise RuntimeError(
                f"{indicator_key}: fewer than {INDICATOR_COUNT} common years are available"
            )
        years_by_indicator[indicator_key] = sorted(common_years)[-INDICATOR_COUNT:]
    return years_by_indicator


def indicator_payload(
    indicator_key: str,
    area: dict[str, str],
    series: dict[int, int | float],
    years: list[int],
) -> dict[str, Any]:
    indicator = INDICATORS[indicator_key]
    level = area["area_level"]
    values = [{"year": year, "value": series[year]} for year in years]
    return {
        "label": indicator["label"],
        "unit": indicator["unit"],
        "ssds_item": indicator["ssds_item"][level],
        "year_start": years[0],
        "year_end": years[-1],
        "values": values,
    }


def build_council_payloads(
    fetched: dict[str, dict[str, dict[int, int | float]]],
    years_by_indicator: dict[str, list[int]],
) -> dict[str, dict[str, Any]]:
    retrieved_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    payloads: dict[str, dict[str, Any]] = {}
    for area in AREAS:
        indicators: dict[str, Any] = {}
        stats_data_ids: dict[str, str] = {}
        for indicator_key, indicator in INDICATORS.items():
            level = area["area_level"]
            stats_data_ids[indicator_key] = indicator["stats_data_id"][level]
            indicators[indicator_key] = indicator_payload(
                indicator_key,
                area,
                fetched[indicator_key][area["council_id"]],
                years_by_indicator[indicator_key],
            )

        payloads[area["council_id"]] = {
            "council_id": area["council_id"],
            "updated_at": retrieved_at,
            "source": {
                "provider": "e-Stat 社会・人口統計体系（SSDS）",
                "api": "getStatsData",
                "retrieved_at": retrieved_at,
                "area_code": area["estat_area_code"],
                "statsDataIds": stats_data_ids,
                "note": "SSDSは確定統計のため最新年が1〜3年遅れる。profileの最新公表値とは出典・年次が異なる。",
            },
            "indicators": indicators,
        }
    return payloads


def write_payloads(payloads: dict[str, dict[str, Any]], output_dir: Path) -> None:
    for council_id, payload in payloads.items():
        target_dir = output_dir / council_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "timeseries.json"
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def profile_year(profile_item: dict[str, Any], profile_key: str) -> int | None:
    if profile_key == "population":
        as_of = profile_item.get("as_of")
        if isinstance(as_of, str) and len(as_of) >= 4 and as_of[:4].isdigit():
            return int(as_of[:4])
    if profile_key == "fiscal_index":
        year = profile_item.get("fiscal_year")
        if isinstance(year, int):
            return year
    return None


def spot_checks(output_dir: Path) -> list[str]:
    checks: list[str] = []
    for council_id in ("kurayoshi-city", "tottori-pref"):
        timeseries_path = output_dir / council_id / "timeseries.json"
        profile_path = output_dir / council_id / "profile.json"
        if not timeseries_path.exists() or not profile_path.exists():
            continue
        timeseries = load_json(timeseries_path)
        profile = load_json(profile_path)
        population_values = timeseries["indicators"]["population_total"]["values"]
        latest = population_values[-1]
        profile_population = profile.get("population")
        if not isinstance(profile_population, dict):
            continue
        profile_value = profile_population.get("value")
        ssds_value = latest["value"]
        diff = profile_value - ssds_value if isinstance(profile_value, int) else None
        checks.append(
            "{} population: SSDS {}={} profile {}={} diff={}".format(
                council_id,
                latest["year"],
                ssds_value,
                profile_year(profile_population, "population"),
                profile_value,
                diff,
            )
        )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()

    app_id = load_app_id()
    fetched = fetch_all_series(app_id)
    years_by_indicator = latest_common_years(fetched)
    payloads = build_council_payloads(fetched, years_by_indicator)
    write_payloads(payloads, args.output_dir)

    print("generated {}".format(", ".join(sorted(payloads))))
    for indicator_key, years in years_by_indicator.items():
        print(f"{indicator_key}: {years[0]}-{years[-1]} ({len(years)} points)")
    for check in spot_checks(args.output_dir):
        print(check)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
