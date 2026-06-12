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
    "prefecture",
    "prefecture_name",
    "lg_code",
    "minutes_system",
    "vote_granularity",
    "status",
}
COUNCIL_TYPES = {"prefecture", "city"}
MINUTES_SYSTEMS = {"dbsr", "kensakusystem", "kensakusystem_legacy", "unknown"}
VOTE_GRANULARITIES = {"member", "faction", "result_only", "unknown"}
STATUSES = {"active", "planned"}

MEMBERS_ROOT_KEYS = {
    "council_id",
    "updated_at",
    "source_url",
    "acquisition",
    "members",
}
MEMBER_ACQUISITIONS = {"scraping", "manual_transcription"}
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
PROFILE_ROOT_KEYS = {
    "council_id",
    "population",
    "households",
    "budget_general_yen",
    "fiscal_index",
    "aging_rate_pct",
    "local_debt_yen",
    "member_salary_monthly_yen",
    "per_capita",
    "updated_at",
}
PROFILE_INPUT_FIELDS = {
    "population",
    "households",
    "budget_general_yen",
    "fiscal_index",
    "aging_rate_pct",
    "local_debt_yen",
    "member_salary_monthly_yen",
}
PER_CAPITA_KEYS = {
    "population_per_member",
    "budget_per_capita_yen",
    "debt_per_capita_yen",
}
VOTES_ROOT_KEYS = {
    "council_id",
    "updated_at",
    "votes",
}
VOTE_ACQUISITIONS = {"scraping", "manual_transcription", "manual_download"}
VOTE_KEYS = {
    "id",
    "council_id",
    "session",
    "bill_title",
    "date",
    "result",
    "granularity",
    "votes_by_member",
    "votes_by_faction",
    "source_url",
}
VOTE_GRANULARITY_VALUES = {"member", "faction", "result_only"}
VOTE_VALUES = {"賛成", "反対", "退席", "欠席", "議長", "除斥", "継続審査"}


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
        if not isinstance(council.get("prefecture"), str) or not council.get(
            "prefecture"
        ):
            errors.append(f"{label}: prefecture must be a non-empty string")
        if not isinstance(council.get("prefecture_name"), str) or not council.get(
            "prefecture_name"
        ):
            errors.append(f"{label}: prefecture_name must be a non-empty string")
        lg_code = council.get("lg_code")
        if (
            not isinstance(lg_code, str)
            or len(lg_code) != 6
            or not lg_code.isdigit()
        ):
            errors.append(f"{label}: lg_code must be a 6-digit string")
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
        votes_official_url = council.get("votes_official_url")
        if votes_official_url is not None and (
            not isinstance(votes_official_url, str)
            or not votes_official_url.startswith("https://")
        ):
            errors.append(
                f"{label}: votes_official_url must start with 'https://' or be null"
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
    if data.get("acquisition") not in MEMBER_ACQUISITIONS:
        errors.append(
            f"{path}: invalid acquisition '{data.get('acquisition')}'"
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
        profile_url = member.get("official_profile_url")
        if "official_profile_url" in member and (
            profile_url is not None
            and (
                not isinstance(profile_url, str)
                or not profile_url.startswith("https://")
            )
        ):
            errors.append(
                f"{label}: official_profile_url must be https URL or null"
            )

    return errors


def validate_profile_item(path: Path, field: str, item: Any) -> list[str]:
    errors: list[str] = []
    label = f"{path}: {field}"
    if item is None:
        return errors
    if not isinstance(item, dict):
        return [f"{label}: must be an object or null"]
    if "value" not in item:
        errors.append(f"{label}: missing key 'value'")
    source_url = item.get("source_url")
    if source_url is None:
        errors.append(f"{label}: missing key 'source_url'")
    elif not isinstance(source_url, str) or not source_url.startswith("https://"):
        errors.append(f"{label}: source_url must start with 'https://'")
    return errors


def validate_profile_file(council_id: str, path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"{path}: file not found for council '{council_id}'"]

    data = load_json(path)
    if not isinstance(data, dict):
        return [f"{path}: root must be an object"]
    add_missing_key_errors(errors, data, PROFILE_ROOT_KEYS, str(path))

    if data.get("council_id") != council_id:
        errors.append(
            f"{path}: council_id '{data.get('council_id')}' "
            f"does not match '{council_id}'"
        )

    for field in PROFILE_INPUT_FIELDS:
        errors.extend(validate_profile_item(path, field, data.get(field)))

    per_capita = data.get("per_capita")
    if not isinstance(per_capita, dict):
        errors.append(f"{path}: per_capita must be an object")
    else:
        add_missing_key_errors(
            errors, per_capita, PER_CAPITA_KEYS, f"{path}: per_capita"
        )

    return errors


def validate_votes_file(council_id: str, path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return errors

    data = load_json(path)
    if not isinstance(data, dict):
        return [f"{path}: root must be an object"]
    add_missing_key_errors(errors, data, VOTES_ROOT_KEYS, str(path))

    if data.get("council_id") != council_id:
        errors.append(
            f"{path}: council_id '{data.get('council_id')}' "
            f"does not match '{council_id}'"
        )
    if "acquisition" in data and data.get("acquisition") not in VOTE_ACQUISITIONS:
        errors.append(f"{path}: invalid acquisition '{data.get('acquisition')}'")

    known_member_ids = load_member_ids(council_id)
    votes = data.get("votes")
    if not isinstance(votes, list):
        errors.append(f"{path}: votes must be a list")
        return errors

    seen: set[str] = set()
    prefix = f"{council_id}--"
    for i, vote in enumerate(votes):
        label = f"{path}: votes[{i}]"
        if not isinstance(vote, dict):
            errors.append(f"{label}: must be an object")
            continue
        add_missing_key_errors(errors, vote, VOTE_KEYS, label)

        vote_id = vote.get("id")
        if not isinstance(vote_id, str) or not vote_id.startswith(prefix):
            errors.append(f"{label}: id '{vote_id}' must start with '{prefix}'")
        elif vote_id in seen:
            errors.append(f"{label}: duplicate vote id '{vote_id}'")
        else:
            seen.add(vote_id)

        if vote.get("council_id") != council_id:
            errors.append(
                f"{label}: council_id '{vote.get('council_id')}' "
                f"does not match '{council_id}'"
            )
        for key in ("session", "bill_title", "source_url"):
            if not isinstance(vote.get(key), str) or not vote.get(key):
                errors.append(f"{label}: {key} must be a non-empty string")
        source_url = vote.get("source_url")
        if isinstance(source_url, str) and not source_url.startswith("https://"):
            errors.append(f"{label}: source_url must start with 'https://'")
        committee_report = vote.get("committee_report")
        if committee_report is not None and not isinstance(committee_report, str):
            errors.append(f"{label}: committee_report must be a string or null")
        date_value = vote.get("date")
        if date_value is not None and (
            not isinstance(date_value, str) or not is_iso_date(date_value)
        ):
            errors.append(f"{label}: date must be YYYY-MM-DD or null")
        if vote.get("granularity") not in VOTE_GRANULARITY_VALUES:
            errors.append(
                f"{label}: invalid granularity '{vote.get('granularity')}'"
            )

        granularity = vote.get("granularity")
        if granularity == "result_only":
            bill_no = vote.get("bill_no")
            if not isinstance(bill_no, str) or not bill_no:
                errors.append(f"{label}: bill_no must be a non-empty string for result_only")
        votes_by_member = vote.get("votes_by_member")
        if granularity == "member":
            errors.extend(
                validate_votes_by_member(
                    label, votes_by_member, known_member_ids, council_id
                )
            )
        elif votes_by_member is not None:
            errors.append(f"{label}: votes_by_member must be null unless member")

        votes_by_faction = vote.get("votes_by_faction")
        if granularity == "result_only" and votes_by_faction is not None:
            errors.append(f"{label}: votes_by_faction must be null for result_only")
        if votes_by_faction is not None and not isinstance(votes_by_faction, list):
            errors.append(f"{label}: votes_by_faction must be a list or null")

    return errors


def validate_votes_by_member(
    label: str, value: Any, known_member_ids: set[str], council_id: str
) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return [f"{label}: votes_by_member must be a list for member granularity"]
    if not value:
        errors.append(f"{label}: votes_by_member must not be empty")

    prefix = f"{council_id}--"
    for j, item in enumerate(value):
        item_label = f"{label}: votes_by_member[{j}]"
        if not isinstance(item, dict):
            errors.append(f"{item_label}: must be an object")
            continue
        member_id = item.get("member_id")
        member_name = item.get("member_name")
        if member_id is not None:
            if not isinstance(member_id, str) or not member_id.startswith(prefix):
                errors.append(
                    f"{item_label}: member_id must start with '{prefix}' or be null"
                )
            elif known_member_ids and member_id not in known_member_ids:
                errors.append(f"{item_label}: unknown member_id '{member_id}'")
        elif not isinstance(member_name, str) or not member_name:
            errors.append(
                f"{item_label}: member_name must be kept when member_id is null"
            )
        vote_value = item.get("vote")
        if not isinstance(vote_value, str) or not vote_value:
            errors.append(f"{item_label}: vote must be a non-empty string")
        elif vote_value not in VOTE_VALUES:
            errors.append(
                f"{item_label}: invalid vote '{vote_value}' "
                f"(expected one of {sorted(VOTE_VALUES)})"
            )
    return errors


def load_member_ids(council_id: str) -> set[str]:
    path = DATA_DIR / council_id / "members.json"
    if not path.exists():
        return set()
    data = load_json(path)
    members = data.get("members", []) if isinstance(data, dict) else []
    if not isinstance(members, list):
        return set()
    return {m["id"] for m in members if isinstance(m, dict) and isinstance(m.get("id"), str)}


def is_iso_date(value: str) -> bool:
    parts = value.split("-")
    if len(parts) != 3:
        return False
    year, month, day = parts
    return (
        len(year) == 4
        and len(month) == 2
        and len(day) == 2
        and year.isdigit()
        and month.isdigit()
        and day.isdigit()
    )


def main() -> int:
    councils, errors = validate_councils()
    warnings: list[str] = []

    for council in councils:
        if council.get("status") != "active":
            continue
        council_id = council.get("id")
        if not isinstance(council_id, str):
            continue
        members_path = DATA_DIR / council_id / "members.json"
        errors.extend(validate_members_file(council_id, members_path))
        profile_path = DATA_DIR / council_id / "profile.json"
        if profile_path.exists():
            errors.extend(validate_profile_file(council_id, profile_path))
        else:
            warnings.append(
                f"{profile_path}: profile.json is recommended for active "
                f"council '{council_id}'"
            )
        votes_path = DATA_DIR / council_id / "votes.json"
        errors.extend(validate_votes_file(council_id, votes_path))

    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if warnings:
        print("Validation warnings:", file=sys.stderr)
        for warning in warnings:
            print(f"- {warning}", file=sys.stderr)

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
