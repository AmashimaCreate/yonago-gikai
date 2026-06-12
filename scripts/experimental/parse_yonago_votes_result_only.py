#!/usr/bin/env python3
"""Prototype parser for Yonago City Council result-only vote PDFs.

The official PDFs contain bill-level outcomes, not member-level votes. This
script discovers the latest regular-session PDFs from the official listing,
extracts text with poppler's pdftotext, and emits a result_only votes.json-like
sample for research verification.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


LISTING_URL = "https://www.city.yonago.lg.jp/13764.htm"
COUNCIL_ID = "yonago-city"
PARSED_SECTIONS = {"市長提出議案", "議員提出議案", "諮問", "請願", "陳情"}
ALL_SECTIONS = PARSED_SECTIONS | {"報告"}
SECTION_ORDER = ["市長提出議案", "議員提出議案", "諮問", "報告", "請願", "陳情"]

SECTION_RE = re.compile(
    r"^(市長提出議案|議員提出議案|諮問|報告|請願|陳情)\s*：\s*([0-9０-９]+)\s*件"
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


def normalize_digits(value: str) -> str:
    return unicodedata.normalize("NFKC", value)


def parse_count(value: str) -> int:
    return int(normalize_digits(value))


def normalize_number(value: str) -> str:
    return re.sub(r"\s+", "", normalize_digits(value))


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_reiwa_date(value: str) -> str:
    match = re.fullmatch(r"令和([0-9０-９]+)年([0-9０-９]+)月([0-9０-９]+)日", value)
    if not match:
        raise ValueError(f"unsupported date: {value}")
    year = 2018 + parse_count(match.group(1))
    month = parse_count(match.group(2))
    day = parse_count(match.group(3))
    return dt.date(year, month, day).isoformat()


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "yonago-gikai-research/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    return raw.decode("utf-8", errors="replace")


def discover_regular_sessions(limit: int) -> list[dict[str, str]]:
    body = fetch_text(LISTING_URL)
    anchor_re = re.compile(
        r'<a\b[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<label>令和[^<]+定例会)</a>',
        re.IGNORECASE,
    )
    sessions: list[dict[str, str]] = []
    for match in anchor_re.finditer(body):
        label = html.unescape(match.group("label")).strip()
        href = html.unescape(match.group("href")).strip()
        sessions.append(
            {
                "session": label,
                "source_url": urllib.parse.urljoin(LISTING_URL, href),
            }
        )
        if len(sessions) >= limit:
            break
    return sessions


def download_pdf(url: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "yonago-gikai-research/0.1"})
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

        bill_number = normalize_number(item_match.group(1))
        date_raw = date_match.group(1)
        result = normalize_digits(date_match.group(2))
        title = joined
        title = ITEM_RE.sub(" ", title, count=1)
        title = DATE_RESULT_RE.sub(" ", title, count=1)
        title = normalize_spaces(title)
        section_record_counts[current_section] += 1
        seq = section_record_counts[current_section]
        vote_id = f"{COUNCIL_ID}--{session}--{bill_number}"
        vote_id = re.sub(r"[^0-9A-Za-z一-龥ぁ-んァ-ンー]+", "-", vote_id)

        records.append(
            {
                "id": vote_id,
                "council_id": COUNCIL_ID,
                "session": session,
                "category": current_section,
                "bill_number": bill_number,
                "bill_title": title,
                "date": parse_reiwa_date(date_raw),
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
            section_counts[current_section] = parse_count(section_match.group(2))
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
    checks = {
        "summary_total_count": total_summary,
        "summary_report_count": summary_counts.get("報告", 0),
        "summary_result_only_expected": result_summary,
        "section_result_only_expected": expected_result_only,
        "parsed_count": len(records),
        "section_counts_match": {
            section: section_record_counts.get(section, 0) == section_counts.get(section, 0)
            for section in SECTION_ORDER
            if section in PARSED_SECTIONS
        },
        "result_only_count_match": len(records) == expected_result_only == result_summary,
    }
    diagnostics = {
        "is_text_pdf": len(text.strip()) > 1000 and "議決結果" in text,
        "text_characters": len(text),
        "summary_counts": {section: summary_counts.get(section, 0) for section in SECTION_ORDER},
        "section_counts": {section: section_counts.get(section, 0) for section in SECTION_ORDER},
        "checks": checks,
    }
    return records, diagnostics


def build_payload(limit: int) -> dict[str, Any]:
    sessions = discover_regular_sessions(limit)
    all_votes: list[dict[str, Any]] = []
    source_checks: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="yonago-votes-") as tmpdir:
        tmp = Path(tmpdir)
        for i, session_info in enumerate(sessions, start=1):
            pdf_path = tmp / f"session_{i}.pdf"
            download_pdf(session_info["source_url"], pdf_path)
            text = pdftotext(pdf_path)
            votes, diagnostics = parse_pdf_text(
                text,
                session=session_info["session"],
                source_url=session_info["source_url"],
            )
            all_votes.extend(votes)
            source_checks.append({**session_info, **diagnostics})

    return {
        "council_id": COUNCIL_ID,
        "updated_at": dt.date.today().isoformat(),
        "acquisition": "manual_download",
        "granularity": "result_only",
        "source_url": LISTING_URL,
        "source_checks": source_checks,
        "votes": all_votes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-sessions", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_payload(args.limit_sessions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for check in payload["source_checks"]:
        summary = check["checks"]
        print(
            f"{check['session']}: parsed={summary['parsed_count']} "
            f"expected={summary['section_result_only_expected']} "
            f"text_pdf={check['is_text_pdf']} match={summary['result_only_count_match']}"
        )


if __name__ == "__main__":
    main()
