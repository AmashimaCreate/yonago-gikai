"""Validate registry and generated council data files."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
COUNCILS_PATH = REPO_ROOT / "councils.json"
DATA_DIR = REPO_ROOT / "docs" / "data"

COUNCIL_REQUIRED_KEYS = {
    "id",
    "name",
    "type",
    "minutes_system",
    "vote_granularity",
    "status",
}
COUNCIL_TYPES = {"prefecture", "city"}
MINUTES_SYSTEMS = {"dbsr", "kensakusystem", "unknown"}
VOTE_GRANULARITIES = {"member", "faction", "result_only", "unknown"}
STATUSES = {"active", "planned"}

MEMBERS_ROOT_KEYS = {"council_id", "updated_at", "source_url", "members"}
MEMBER_KEYS = {
    "id",
    "council_id",
    "name",
    "name_kana",
    "faction",
    "elected_count",
    "positions",
    "committees",
    "photo_url",
}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def add_missing_key_errors(
    errors: list[str], obj: dict[str, Any], required: set[str], label: str
) -> None:
    missing = sorted(required - set(obj))
    for key in missing:
        errors.append(f"{label}: missing key '{key}'")


def validate_councils() -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    if not COUNCILS_PATH.exists():
        return [], [f"{COUNCILS_PATH}: file not found"]

    data = load_json(COUNCILS_PATH)
    councils = data.get("councils")
    if not isinstance(councils, list):
        return [], ["councils.json: 'councils' must be a list"]

    ids: set[str] = set()
    for i, council in enumerate(councils):
        label = f"councils[{i}]"
        if not isinstance(council, dict):
            errors.append(f"{label}: must be an object")
            continue
        add_missing_key_errors(errors, council, COUNCIL_REQUIRED_KEYS, label)
        council_id = council.get("id")
        if isinstance(council_id, str):
            if council_id in ids:
                errors.append(f"{label}: duplicate id '{council_id}'")
            ids.add(council_id)
        if council.get("type") not in COUNCIL_TYPES:
            errors.append(f"{label}: invalid type '{council.get('type')}'")
        if council.get("minutes_system") not in MINUTES_SYSTEMS:
            errors.append(
                f"{label}: invalid minutes_system "
                f"'{council.get('minutes_system')}'"
            )
        if council.get("vote_granularity") not in VOTE_GRANULARITIES:
            errors.append(
                f"{label}: invalid vote_granularity "
                f"'{council.get('vote_granularity')}'"
            )
        if council.get("status") not in STATUSES:
            errors.append(f"{label}: invalid status '{council.get('status')}'")

    return councils, errors


def validate_members_file(council_id: str, path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"{path}: file not found for active council '{council_id}'"]

    data = load_json(path)
    if not isinstance(data, dict):
        return [f"{path}: root must be an object"]
    add_missing_key_errors(errors, data, MEMBERS_ROOT_KEYS, str(path))

    if data.get("council_id") != council_id:
        errors.append(
            f"{path}: council_id '{data.get('council_id')}' "
            f"does not match '{council_id}'"
        )

    members = data.get("members")
    if not isinstance(members, list):
        errors.append(f"{path}: 'members' must be a list")
        return errors
    if len(members) == 0:
        errors.append(f"{path}: members must not be empty")

    seen: set[str] = set()
    prefix = f"{council_id}--"
    for i, member in enumerate(members):
        label = f"{path}: members[{i}]"
        if not isinstance(member, dict):
            errors.append(f"{label}: must be an object")
            continue
        add_missing_key_errors(errors, member, MEMBER_KEYS, label)
        member_id = member.get("id")
        if not isinstance(member_id, str) or not member_id.startswith(prefix):
            errors.append(
                f"{label}: id '{member_id}' must start with '{prefix}'"
            )
        elif member_id in seen:
            errors.append(f"{label}: duplicate member id '{member_id}'")
        else:
            seen.add(member_id)
        if member.get("council_id") != council_id:
            errors.append(
                f"{label}: council_id '{member.get('council_id')}' "
                f"does not match '{council_id}'"
            )
        if not isinstance(member.get("positions"), list):
            errors.append(f"{label}: positions must be a list")
        if not isinstance(member.get("committees"), list):
            errors.append(f"{label}: committees must be a list")
        elected_count = member.get("elected_count")
        if elected_count is not None and not isinstance(elected_count, int):
            errors.append(f"{label}: elected_count must be int or null")

    return errors


def main() -> int:
    councils, errors = validate_councils()

    for council in councils:
        if council.get("status") != "active":
            continue
        council_id = council.get("id")
        if not isinstance(council_id, str):
            continue
        members_path = DATA_DIR / council_id / "members.json"
        errors.extend(validate_members_file(council_id, members_path))

    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
