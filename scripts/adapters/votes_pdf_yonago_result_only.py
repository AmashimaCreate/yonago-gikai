#!/usr/bin/env python3
"""Build Yonago City Council result-only vote data from official PDFs.

The official PDFs contain bill-level outcomes, not member-level votes. This
adapter discovers regular and special session PDFs from the official listing,
extracts text with poppler's pdftotext, and writes a result_only votes.json.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.lib.json_output import write_json_if_entity_changed  # noqa: E402

DATA_DIR = REPO_ROOT / "docs" / "data"
LISTING_URL = "https://www.city.yonago.lg.jp/13764.htm"
COUNCIL_ID = "yonago-city"
OUT_PATH = DATA_DIR / COUNCIL_ID / "votes.json"
USER_AGENT = "Mozilla/5.0 (compatible; tottori-mieru/1.0)"
SLEEP_SECONDS = 2.0
PARSED_SECTIONS = {"市長提出議案", "議員提出議案", "諮問", "請願", "陳情"}
ALL_SECTIONS = PARSED_SECTIONS | {"報告"}
SECTION_ORDER = ["市長提出議案", "議員提出議案", "諮問", "報告", "請願", "陳情"]

SECTION_RE = re.compile(
    r"^(市長提出議案|議員提出議案|諮問|報告|請願|陳情)\s*：\s*([0-9０-９]*)\s*件"
)
SUMMARY_RE = re.compile(
    r"^\s*(市長提出議案|議員提出議案|諮問|報告|請願|陳情)\s+([0-9０-９]+)\s*件"
)
DATE_RESULT_RE = re.compile(
    r"(令和[0-9０-９]+年[0-9０-９]+月[0-9０-９]+日)\s+([^\s]+)"
)
ITEM_RE = re.compile(
    r"(議\s*案\s*第\s*[0-9０-９]+\s*号|諮問第\s*[0-9０-９]+\s*号|"
    r"請\s*願\s*第\s*[0-9０-９]+\s*号|請願第\s*[0-9０-９]+\s*号|"
    r"陳\s*情\s*第\s*[0-9０-９]+\s*号|陳情第\s*[0-9０-９]+\s*号)"
)
SESSION_RE = re.compile(
    r"令和(?P<year>[0-9０-９]+)年(?P<month>[0-9０-９]+)月(?P<kind>定例会|臨時会)"
)


def normalize_digits(value: str) -> str:
    return unicodedata.normalize("NFKC", value)


def parse_count(value: str) -> int:
    return int(normalize_digits(value))


def normalize_number(value: str) -> str:
    return re.sub(r"\s+", "", normalize_digits(value))


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def default_start_date(today: dt.date | None = None) -> dt.date:
    today = today or dt.date.today()
    return dt.date(today.year - 2, today.month, 1)


def parse_reiwa_date(value: str) -> str:
    match = re.fullmatch(r"令和([0-9０-９]+)年([0-9０-９]+)月([0-9０-９]+)日", value)
    if not match:
        raise ValueError(f"unsupported date: {value}")
    year = 2018 + parse_count(match.group(1))
    month = parse_count(match.group(2))
    day = parse_count(match.group(3))
    return dt.date(year, month, day).isoformat()


def parse_session_month(label: str) -> dt.date | None:
    match = SESSION_RE.search(label)
    if not match:
        return None
    year = 2018 + parse_count(match.group("year"))
    month = parse_count(match.group("month"))
    return dt.date(year, month, 1)


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    return raw.decode("utf-8", errors="replace")


def discover_sessions(start: dt.date, end: dt.date) -> list[dict[str, str]]:
    body = fetch_text(LISTING_URL)
    anchor_re = re.compile(
        r'<a\b[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<label>令和[^<]+(?:定例会|臨時会))</a>',
        re.IGNORECASE,
    )
    sessions: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in anchor_re.finditer(body):
        label = html.unescape(match.group("label")).strip()
        href = html.unescape(match.group("href")).strip()
        session_month = parse_session_month(label)
        if session_month is None or session_month < start or session_month > end:
            continue
        source_url = urllib.parse.urljoin(LISTING_URL, href)
        if source_url in seen:
            continue
        seen.add(source_url)
        sessions.append(
            {
                "session": label,
                "session_month": session_month.isoformat(),
                "source_url": source_url,
            }
        )
    return sorted(sessions, key=lambda item: item["session_month"], reverse=True)


def download_pdf(url: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        dest.write_bytes(response.read())


def pdftotext(pdf_path: Path) -> str:
    if shutil.which("pdftotext") is None:
        raise RuntimeError("pdftotext is not available")
    proc = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout


def build_vote_id(session: str, bill_no: str, date_value: str, result: str) -> str:
    digest = hashlib.sha1(
        f"{session}|{bill_no}|{date_value}|{result}".encode("utf-8")
    ).hexdigest()[:10]
    slug = re.sub(r"[^0-9A-Za-z一-龥ぁ-んァ-ンー]+", "-", f"{session}-{bill_no}")
    slug = slug.strip("-")[:80]
    return f"{COUNCIL_ID}--{slug}-{digest}"


def parse_pdf_text(text: str, session: str, source_url: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    summary_counts: dict[str, int] = {}
    section_counts: dict[str, int] = {}
    records: list[dict[str, Any]] = []
    section_record_counts = {section: 0 for section in PARSED_SECTIONS}

    current_section: str | None = None
    buffer: list[str] = []
    in_summary = True

    def flush_buffer() -> None:
        nonlocal buffer
        if not buffer or current_section not in PARSED_SECTIONS:
            buffer = []
            return
        joined = normalize_spaces(" ".join(buffer))
        date_match = DATE_RESULT_RE.search(joined)
        item_match = ITEM_RE.search(joined)
        if not date_match or not item_match:
            buffer = []
            return

        bill_no = normalize_number(item_match.group(1))
        date_raw = date_match.group(1)
        date_value = parse_reiwa_date(date_raw)
        result = normalize_digits(date_match.group(2))
        title = joined
        title = ITEM_RE.sub(" ", title, count=1)
        title = DATE_RESULT_RE.sub(" ", title, count=1)
        title = normalize_spaces(title)
        section_record_counts[current_section] += 1
        seq = section_record_counts[current_section]

        records.append(
            {
                "id": build_vote_id(session, bill_no, date_value, result),
                "council_id": COUNCIL_ID,
                "session": session,
                "category": current_section,
                "bill_no": bill_no,
                "bill_title": title,
                "date": date_value,
                "result": result,
                "granularity": "result_only",
                "votes_by_member": None,
                "votes_by_faction": None,
                "source_url": source_url,
                "source_row_index": seq,
            }
        )
        buffer = []

    for raw_line in text.splitlines():
        line = raw_line.replace("\f", "").strip()
        if not line or re.fullmatch(r"[0-9０-９]+", normalize_digits(line)):
            continue

        if in_summary:
            summary_match = SUMMARY_RE.match(line)
            if summary_match:
                summary_counts[summary_match.group(1)] = parse_count(summary_match.group(2))

        section_match = SECTION_RE.match(line)
        if section_match:
            flush_buffer()
            current_section = section_match.group(1)
            count_text = section_match.group(2)
            section_counts[current_section] = (
                parse_count(count_text)
                if count_text
                else summary_counts.get(current_section, 0)
            )
            in_summary = False
            continue

        if current_section is None or current_section not in PARSED_SECTIONS:
            continue
        if any(header in line for header in ("議案番号", "諮問番号", "請願番号", "陳情番号", "件 名", "議決年月日")):
            continue

        buffer.append(line)
        if DATE_RESULT_RE.search(line):
            flush_buffer()

    flush_buffer()

    expected_result_only = sum(section_counts.get(section, 0) for section in PARSED_SECTIONS)
    total_summary = sum(summary_counts.get(section, 0) for section in ALL_SECTIONS)
    result_summary = sum(summary_counts.get(section, 0) for section in PARSED_SECTIONS)
    count_formula_match = total_summary - summary_counts.get("報告", 0) == len(records)
    has_extractable_text = len(text.strip()) > 100 and bool(summary_counts)
    checks = {
        "summary_total_count": total_summary,
        "summary_report_count": summary_counts.get("報告", 0),
        "summary_total_minus_reports": total_summary - summary_counts.get("報告", 0),
        "summary_result_only_expected": result_summary,
        "section_result_only_expected": expected_result_only,
        "parsed_count": len(records),
        "section_counts_match": {
            section: section_record_counts.get(section, 0) == section_counts.get(section, 0)
            for section in SECTION_ORDER
            if section in PARSED_SECTIONS
        },
        "result_only_count_match": len(records) == expected_result_only == result_summary,
        "summary_total_minus_reports_match": count_formula_match,
    }
    accepted = (
        has_extractable_text
        and checks["summary_total_minus_reports_match"]
    )
    diagnostics = {
        "accepted": accepted,
        "is_text_pdf": has_extractable_text,
        "text_characters": len(text),
        "summary_counts": {section: summary_counts.get(section, 0) for section in SECTION_ORDER},
        "section_counts": {section: section_counts.get(section, 0) for section in SECTION_ORDER},
        "checks": checks,
    }
    return records, diagnostics


def build_payload(start: dt.date, end: dt.date) -> dict[str, Any]:
    sessions = discover_sessions(start, end)
    all_votes: list[dict[str, Any]] = []
    source_checks: list[dict[str, Any]] = []
    omitted_sessions: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="yonago-votes-") as tmpdir:
        tmp = Path(tmpdir)
        for i, session_info in enumerate(sessions, start=1):
            pdf_path = tmp / f"session_{i}.pdf"
            download_pdf(session_info["source_url"], pdf_path)
            time.sleep(SLEEP_SECONDS)
            text = pdftotext(pdf_path)
            votes, diagnostics = parse_pdf_text(
                text,
                session=session_info["session"],
                source_url=session_info["source_url"],
            )
            source_checks.append({**session_info, **diagnostics})
            if diagnostics["accepted"]:
                all_votes.extend(votes)
            else:
                omitted_sessions.append(
                    {
                        "session": session_info["session"],
                        "source_url": session_info["source_url"],
                        "reason": "検算不一致またはテキスト抽出不可のため未収録",
                        "checks": diagnostics["checks"],
                    }
                )

    all_votes.sort(
        key=lambda item: (
            item["date"] or "",
            item["session"],
            item["bill_no"],
            item["id"],
        )
    )

    return {
        "council_id": COUNCIL_ID,
        "updated_at": dt.datetime.now(dt.UTC).isoformat(),
        "acquisition": "scraping",
        "granularity": "result_only",
        "source_url": LISTING_URL,
        "coverage": {
            "scope": "直近2年分の定例会・臨時会の議決結果PDF",
            "note": "議員別の賛否は公式に公開されていないため、議案ごとの議決結果のみを収録する。",
        },
        "source_checks": source_checks,
        "omitted_sessions": omitted_sessions,
        "votes": all_votes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=dt.date.fromisoformat, default=default_start_date())
    parser.add_argument("--end", type=dt.date.fromisoformat, default=dt.date.today())
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args.start, args.end)
    if not args.dry_run:
        write_json_if_entity_changed(args.output, payload)

    for check in payload["source_checks"]:
        summary = check["checks"]
        print(
            f"{check['session']}: parsed={summary['parsed_count']} "
            f"expected={summary['summary_total_minus_reports']} "
            f"text_pdf={check['is_text_pdf']} accepted={check['accepted']}"
        )
    if payload["omitted_sessions"]:
        print(f"{COUNCIL_ID}: omitted_sessions={len(payload['omitted_sessions'])}")
        for item in payload["omitted_sessions"]:
            print(f"- {item['session']}: {item['reason']}")
    print(
        f"{COUNCIL_ID}: sessions_seen={len(payload['source_checks'])}, "
        f"votes={len(payload['votes'])}, output={args.output}"
    )


if __name__ == "__main__":
    main()
