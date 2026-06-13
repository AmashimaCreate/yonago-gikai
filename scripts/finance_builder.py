"""Build municipal finance JSON files from Digital Agency/Soumu CSV bundle."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "data"

FISCAL_YEAR = 2024
SOURCE_UPDATED_AT = "2026-04-24T00:00:00+09:00"
SOURCE_DIR = "20260424_resources_municipal-finance"
FLOW_CSV = f"{SOURCE_DIR}/finance_local_finance_data_table_flow.csv"
MASTER_CSV = f"{SOURCE_DIR}/finance_data_table_master.csv"
GROUPS_CSV = f"{SOURCE_DIR}/finance_data_table_groups.csv"

TARGETS = {
    "tottori-city": {"municipal_code": "31201", "name": "鳥取市"},
    "yonago-city": {"municipal_code": "31202", "name": "米子市"},
    "kurayoshi-city": {"municipal_code": "31203", "name": "倉吉市"},
    "sakaiminato-city": {"municipal_code": "31204", "name": "境港市"},
}

PURPOSE_ORDER = [
    "議会費",
    "総務費",
    "民生費",
    "衛生費",
    "労働費",
    "農林水産業費",
    "土木費",
    "教育費",
    "公債費",
    "その他",
]

NATURE_ORDER = [
    "人件費",
    "扶助費",
    "公債費",
    "普通建設事業費",
    "物件費",
    "補助費等",
    "その他",
]

SOURCE_INFO = {
    "name": "総務省「地方財政状況調査」/ デジタル庁 地方財政データ",
    "dataset": "20260424_resources_municipal-finance",
    "fiscal_year": FISCAL_YEAR,
    "license": "CC BY 4.0相当",
    "note": "手元の配布ZIPから生成。金額の生値は千円。",
    "files": {
        "flow": FLOW_CSV,
        "master": MASTER_CSV,
        "groups": GROUPS_CSV,
    },
}


def read_csv(zip_file: ZipFile, name: str) -> list[dict[str, str]]:
    with zip_file.open(name) as f:
        return list(csv.DictReader((line.decode("utf-8-sig") for line in f)))


def load_councils() -> dict[str, dict[str, Any]]:
    with (REPO_ROOT / "councils.json").open(encoding="utf-8") as f:
        data = json.load(f)
    return {council["id"]: council for council in data["councils"]}


def parse_int(value: str) -> int:
    if value == "":
        return 0
    return int(float(value))


def sum_by_major(
    flow_totals: dict[str, dict[str, dict[str, int]]],
    municipal_code: str,
    category: str,
) -> dict[str, int]:
    return dict(flow_totals.get(municipal_code, {}).get(category, {}))


def aggregate_flow(
    flow_rows: list[dict[str, str]],
) -> dict[str, dict[str, dict[str, int]]]:
    totals: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    for row in flow_rows:
        if row["年度"] != str(FISCAL_YEAR):
            continue
        totals[row["市区町村コード"]][row["分類"]][row["大項目"]] += parse_int(
            row["値_千円"]
        )
    return {
        code: {
            category: dict(items)
            for category, items in categories.items()
        }
        for code, categories in totals.items()
    }


def category_rows(
    totals_thousand_yen: dict[str, int],
    order: list[str],
    population: int,
    peer_averages: dict[str, dict[str, float | int] | None],
) -> list[dict[str, Any]]:
    total = sum(totals_thousand_yen.values())
    rows = []
    labels = [label for label in order if label in totals_thousand_yen]
    labels.extend(sorted(set(totals_thousand_yen) - set(labels)))
    for label in labels:
        thousand_yen = totals_thousand_yen.get(label, 0)
        yen = thousand_yen * 1000
        peer = peer_averages.get(label) if peer_averages else None
        rows.append({
            "label": label,
            "amount_thousand_yen": thousand_yen,
            "amount_yen": yen,
            "amount_oku_yen": round(thousand_yen / 100000, 3),
            "share_pct": round((thousand_yen / total) * 100, 3) if total else 0,
            "per_capita_yen": round(yen / population) if population else None,
            "similar_group_average_per_capita_yen": (
                round(peer["average_per_capita_yen"])
                if isinstance(peer, dict) and peer.get("average_per_capita_yen") is not None
                else None
            ),
            "similar_group_average_n": (
                int(peer["n"])
                if isinstance(peer, dict) and isinstance(peer.get("n"), int)
                else None
            ),
        })
    rows.sort(key=lambda item: item["amount_thousand_yen"], reverse=True)
    return rows


def build_peer_averages(
    flow_totals: dict[str, dict[str, dict[str, int]]],
    master_by_code: dict[str, dict[str, str]],
    classification: str,
) -> dict[str, dict[str, dict[str, float | int]]]:
    values: dict[tuple[str, str], list[float]] = defaultdict(list)
    for code, master in master_by_code.items():
        if master["年度"] != str(FISCAL_YEAR):
            continue
        population = parse_int(master["人口数_人"])
        if population <= 0:
            continue
        totals = sum_by_major(flow_totals, code, classification)
        for label, thousand_yen in totals.items():
            values[(master["類似団体区分"], label)].append((thousand_yen * 1000) / population)
    averages: dict[str, dict[str, dict[str, float | int]]] = defaultdict(dict)
    for (group, label), items in values.items():
        if items:
            averages[group][label] = {
                "average_per_capita_yen": mean(items),
                "n": len(items),
            }
    return {group: dict(items) for group, items in averages.items()}


def read_group_indicators(group_rows: list[dict[str, str]], similar_group: str) -> dict[str, Any]:
    indicators: dict[str, Any] = {}
    for row in group_rows:
        if row["年度"] == str(FISCAL_YEAR) and row["類似団体名"] == similar_group:
            try:
                value: float | None = float(row["値"])
            except ValueError:
                value = None
            indicators[row["指標名"]] = {
                "value": value,
                "unit": row["単位"],
            }
    return indicators


def validate_code_mapping(council_id: str, lg_code: str, municipal_code: str) -> str | None:
    if not (isinstance(lg_code, str) and len(lg_code) == 6 and lg_code.isdigit()):
        return f"{council_id}: lg_code must be a 6-digit string"
    if lg_code[:5] != municipal_code:
        return (
            f"{council_id}: lg_code {lg_code} does not match "
            f"municipal code {municipal_code}"
        )
    return None


def write_json_if_changed(path: Path, data: dict[str, Any]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == rendered:
        return False
    path.write_text(rendered, encoding="utf-8")
    return True


def build(zip_path: Path, output_dir: Path) -> list[dict[str, Any]]:
    councils = load_councils()
    results: list[dict[str, Any]] = []
    with ZipFile(zip_path) as z:
        flow_rows = read_csv(z, FLOW_CSV)
        master_rows = read_csv(z, MASTER_CSV)
        group_rows = read_csv(z, GROUPS_CSV)

    master_by_code = {
        row["市区町村コード"]: row
        for row in master_rows
        if row["年度"] == str(FISCAL_YEAR)
    }
    flow_totals = aggregate_flow(flow_rows)
    purpose_peer = build_peer_averages(flow_totals, master_by_code, "歳出 (目的)")
    nature_peer = build_peer_averages(flow_totals, master_by_code, "歳出 (性質)")
    for council_id, target in TARGETS.items():
        municipal_code = target["municipal_code"]
        council = councils.get(council_id)
        if not council:
            raise ValueError(f"{council_id}: not found in councils.json")
        code_error = validate_code_mapping(council_id, council["lg_code"], municipal_code)
        if code_error:
            raise ValueError(code_error)
        master = master_by_code.get(municipal_code)
        if not master:
            raise ValueError(f"{council_id}: municipal code {municipal_code} not found")

        population = parse_int(master["人口数_人"])
        similar_group = master["類似団体区分"]
        purpose_totals = sum_by_major(flow_totals, municipal_code, "歳出 (目的)")
        nature_totals = sum_by_major(flow_totals, municipal_code, "歳出 (性質)")
        purpose_total = sum(purpose_totals.values())
        nature_total = sum(nature_totals.values())

        data = {
            "council_id": council_id,
            "updated_at": SOURCE_UPDATED_AT,
            "fiscal_year": FISCAL_YEAR,
            "municipal_code": municipal_code,
            "lg_code": council["lg_code"],
            "municipality_name": master["市区町村名"],
            "similar_group": similar_group,
            "population": {
                "value": population,
                "source": "finance_data_table_master.csv 人口数_人",
            },
            "source": SOURCE_INFO,
            "checks": {
                "lg_code_first_5_digits_match_municipal_code": True,
                "purpose_total_thousand_yen": purpose_total,
                "nature_total_thousand_yen": nature_total,
                "purpose_minus_nature_thousand_yen": purpose_total - nature_total,
                "purpose_share_sum_pct": round(sum(
                    (value / purpose_total) * 100 for value in purpose_totals.values()
                ), 6) if purpose_total else 0,
                "nature_share_sum_pct": round(sum(
                    (value / nature_total) * 100 for value in nature_totals.values()
                ), 6) if nature_total else 0,
            },
            "similar_group_indicators": read_group_indicators(group_rows, similar_group),
            "expenditure": {
                "purpose": {
                    "classification": "歳出 (目的)",
                    "total_thousand_yen": purpose_total,
                    "total_yen": purpose_total * 1000,
                    "items": category_rows(
                        purpose_totals,
                        PURPOSE_ORDER,
                        population,
                        purpose_peer.get(similar_group, {}),
                    ),
                },
                "nature": {
                    "classification": "歳出 (性質)",
                    "total_thousand_yen": nature_total,
                    "total_yen": nature_total * 1000,
                    "items": category_rows(
                        nature_totals,
                        NATURE_ORDER,
                        population,
                        nature_peer.get(similar_group, {}),
                    ),
                },
            },
        }

        output_path = output_dir / council_id / "finance.json"
        changed = write_json_if_changed(output_path, data)
        results.append({
            "council_id": council_id,
            "municipal_code": municipal_code,
            "lg_code": council["lg_code"],
            "similar_group": similar_group,
            "population": population,
            "purpose_total_thousand_yen": purpose_total,
            "nature_total_thousand_yen": nature_total,
            "changed": changed,
            "output": str(output_path.relative_to(REPO_ROOT)),
        })
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", type=Path, help="Path to municipal finance ZIP")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    results = build(args.zip_path, args.output_dir)
    for result in results:
        print(
            f"{result['council_id']}: {result['municipal_code']} <- "
            f"{result['lg_code']} / {result['similar_group']} / "
            f"目的別 {result['purpose_total_thousand_yen']:,}千円 / "
            f"性質別 {result['nature_total_thousand_yen']:,}千円 / "
            f"{'updated' if result['changed'] else 'unchanged'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
