"""Build public profile.json files from reviewed profile source inputs."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.lib.json_output import write_json_if_entity_changed  # noqa: E402

COUNCILS_PATH = REPO_ROOT / "councils.json"
INPUT_DIR = REPO_ROOT / "data_sources" / "profiles"
OUTPUT_DIR = REPO_ROOT / "docs" / "data"

PROFILE_FIELDS = [
    "population",
    "households",
    "budget_general_yen",
    "fiscal_index",
    "aging_rate_pct",
    "local_debt_yen",
    "member_salary_monthly_yen",
]
INTEGER_FIELDS = {
    "population",
    "households",
    "budget_general_yen",
    "local_debt_yen",
    "member_salary_monthly_yen",
}
NUMBER_FIELDS = {"fiscal_index", "aging_rate_pct"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict[str, Any]) -> bool:
    return write_json_if_entity_changed(path, data)


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def council_ids() -> set[str]:
    data = load_json(COUNCILS_PATH)
    councils = data.get("councils", [])
    return {
        council["id"]
        for council in councils
        if isinstance(council, dict) and isinstance(council.get("id"), str)
    }


def member_count(council_id: str) -> int | None:
    path = OUTPUT_DIR / council_id / "members.json"
    if not path.exists():
        return None
    data = load_json(path)
    members = data.get("members")
    if not isinstance(members, list):
        return None
    return len(members)


def validate_profile_item(
    field: str,
    item: Any,
    label: str,
    errors: list[str],
) -> None:
    if item is None:
        return
    if not isinstance(item, dict):
        errors.append(f"{label}: must be an object or null")
        return

    value = item.get("value")
    source_url = item.get("source_url")
    if "value" not in item:
        errors.append(f"{label}: missing key 'value'")
    if "source_url" not in item:
        errors.append(f"{label}: missing key 'source_url'")
    elif not isinstance(source_url, str) or not source_url.startswith("https://"):
        errors.append(f"{label}: source_url must start with 'https://'")

    if field in INTEGER_FIELDS and not is_int(value):
        errors.append(f"{label}: value must be an integer")
    if field in NUMBER_FIELDS and not is_number(value):
        errors.append(f"{label}: value must be a number")

    if field == "population" and is_number(value) and value <= 0:
        errors.append(f"{label}: value must be greater than 0")
    if field in {
        "households",
        "budget_general_yen",
        "local_debt_yen",
        "member_salary_monthly_yen",
    } and is_number(value) and value < 0:
        errors.append(f"{label}: value must not be negative")
    if field == "aging_rate_pct" and is_number(value) and not 0 <= value <= 100:
        errors.append(f"{label}: value must be between 0 and 100")

    as_of = item.get("as_of")
    if as_of is not None and (
        not isinstance(as_of, str) or DATE_RE.fullmatch(as_of) is None
    ):
        errors.append(f"{label}: as_of must be YYYY-MM-DD")

    fiscal_year = item.get("fiscal_year")
    if fiscal_year is not None and not is_int(fiscal_year):
        errors.append(f"{label}: fiscal_year must be an integer")

    source_name = item.get("source_name")
    if source_name is not None and not isinstance(source_name, str):
        errors.append(f"{label}: source_name must be a string")


def validate_source(
    path: Path,
    data: Any,
    known_council_ids: set[str],
) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    label = str(path)
    if not isinstance(data, dict):
        return None, [f"{label}: root must be an object"]

    council_id = data.get("council_id")
    if not isinstance(council_id, str):
        errors.append(f"{label}: council_id must be a string")
    elif council_id not in known_council_ids:
        errors.append(f"{label}: council_id '{council_id}' is not in councils.json")
    elif path.stem != council_id:
        errors.append(f"{label}: filename must match council_id '{council_id}'")

    for field in PROFILE_FIELDS:
        if field not in data:
            errors.append(f"{label}: missing key '{field}'")
            continue
        validate_profile_item(field, data[field], f"{label}: {field}", errors)

    return council_id if isinstance(council_id, str) else None, errors


def value_of(item: Any) -> int | float | None:
    if isinstance(item, dict):
        value = item.get("value")
        if is_number(value):
            return value
    return None


def divide(
    numerator: int | float | None,
    denominator: int | float | None,
) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def build_profile(council_id: str, source: dict[str, Any]) -> dict[str, Any]:
    population = value_of(source.get("population"))
    budget = value_of(source.get("budget_general_yen"))
    debt = value_of(source.get("local_debt_yen"))
    members = member_count(council_id)

    population_per_member = divide(population, members)
    budget_per_capita = divide(budget, population)
    debt_per_capita = divide(debt, population)

    profile = {"council_id": council_id}
    profile.update({field: source.get(field) for field in PROFILE_FIELDS})
    profile["per_capita"] = {
        "population_per_member": (
            round(population_per_member, 1)
            if population_per_member is not None
            else None
        ),
        "budget_per_capita_yen": (
            round(budget_per_capita) if budget_per_capita is not None else None
        ),
        "debt_per_capita_yen": (
            round(debt_per_capita) if debt_per_capita is not None else None
        ),
    }
    profile["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return profile


def main() -> int:
    if not INPUT_DIR.exists():
        print(f"{INPUT_DIR}: directory not found", file=sys.stderr)
        return 1

    known_council_ids = council_ids()
    input_paths = sorted(INPUT_DIR.glob("*.json"))
    if not input_paths:
        print(f"{INPUT_DIR}: no profile source files found", file=sys.stderr)
        return 1

    errors: list[str] = []
    sources: list[tuple[str, dict[str, Any]]] = []
    for path in input_paths:
        try:
            data = load_json(path)
        except json.JSONDecodeError as err:
            errors.append(f"{path}: invalid JSON: {err}")
            continue
        council_id, path_errors = validate_source(path, data, known_council_ids)
        errors.extend(path_errors)
        if council_id and isinstance(data, dict) and not path_errors:
            sources.append((council_id, data))

    if errors:
        print("Profile build failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    for council_id, source in sources:
        profile = build_profile(council_id, source)
        output_path = OUTPUT_DIR / council_id / "profile.json"
        action = "wrote" if write_json(output_path, profile) else "unchanged"
        print(f"{action} {output_path.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
