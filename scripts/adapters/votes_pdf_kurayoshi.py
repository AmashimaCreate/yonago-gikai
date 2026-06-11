"""Build Kurayoshi City Council member vote data from official PDF matrices."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import pdfplumber
import requests
from bs4 import BeautifulSoup

if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from scripts.adapters.minutes_kensakusystem_legacy import (  # noqa: E402
    normalize_name,
)
from scripts.base import CouncilScraperBase  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "docs" / "data"
COUNCIL_ID = "kurayoshi-city"
INDEX_URL = "https://www.city.kurayoshi.lg.jp/4235.htm"
OUT_PATH = DATA_DIR / COUNCIL_ID / "votes.json"

MEMBER_START_COL = 10
MACHINE_READABLE_MIN_CHARS = 200

VOTE_MAP = {
    "○": "賛成",
    "〇": "賛成",
    "×": "反対",
    "✕": "反対",
    "※": "欠席",
    "議長": "議長",
}


@dataclass(frozen=True)
class VotePdfLink:
    session: str
    session_month: date
    url: str
    label: str


@dataclass
class ParseStats:
    pdfs_seen: int = 0
    pdfs_parsed: int = 0
    unreadable_pdfs: int = 0
    bills_kept: int = 0
    bills_rejected: int = 0
    member_cells: int = 0
    linked_member_cells: int = 0


class KurayoshiVotesPdfAdapter(CouncilScraperBase):
    def __init__(self, start: date, end: date) -> None:
        super().__init__()
        self.start = start
        self.end = end
        self.members = load_members()
        self.member_count = len(self.members)
        self.name_to_id = {
            normalize_name(member["name"]): member["id"]
            for member in self.members
            if isinstance(member.get("name"), str)
            and isinstance(member.get("id"), str)
        }
        self.name_to_official_name = {
            normalize_name(member["name"]): member["name"]
            for member in self.members
            if isinstance(member.get("name"), str)
        }
        self.stats = ParseStats()
        self.omitted_pdfs: list[dict[str, str]] = []
        self.rejected_bills: list[dict[str, str]] = []
        self.table_warnings: list[dict[str, str]] = []

    def scrape_votes(self) -> dict[str, Any]:
        links = self.discover_pdf_links()
        votes: list[dict[str, Any]] = []
        for link in links:
            self.stats.pdfs_seen += 1
            pdf_path = self.download_pdf(link)
            votes.extend(self.parse_pdf(link, pdf_path))

        votes.sort(
            key=lambda item: (
                item["date"] or "",
                item["session"],
                item["bill_title"],
                item["id"],
            )
        )
        print(
            f"{COUNCIL_ID}: pdfs_seen={self.stats.pdfs_seen}, "
            f"pdfs_parsed={self.stats.pdfs_parsed}, "
            f"unreadable_pdfs={self.stats.unreadable_pdfs}, "
            f"votes={len(votes)}, rejected={self.stats.bills_rejected}"
        )
        if self.stats.member_cells:
            rate = self.stats.linked_member_cells / self.stats.member_cells * 100
            print(
                f"{COUNCIL_ID}: member_id_linked="
                f"{self.stats.linked_member_cells}/{self.stats.member_cells} "
                f"({rate:.1f}%)"
            )
        if self.omitted_pdfs:
            print("omitted PDFs:")
            for item in self.omitted_pdfs:
                print(f"- {item['session']}: {item['reason']} {item['url']}")
        if self.rejected_bills:
            print("rejected bills:")
            for item in self.rejected_bills:
                print(f"- {item['session']} {item['bill_title']}: {item['reason']}")
        if self.table_warnings:
            print("table warnings:")
            for item in self.table_warnings:
                print(f"- {item['session']} {item['location']}: {item['reason']}")

        return {
            "council_id": COUNCIL_ID,
            "coverage": {
                "source": "倉吉市議会 令和2年以降 議決結果",
                "source_url": INDEX_URL,
                "scope": "直近2年分の定例会・議員別議決結果PDF",
                "start_date": self.start.isoformat(),
                "end_date": self.end.isoformat(),
                "quality_policy": "検算不一致または機械可読でないPDFは未収録",
            },
            "omitted_pdfs": self.omitted_pdfs,
            "rejected_bills": self.rejected_bills,
            "table_warnings": self.table_warnings,
            "votes": votes,
        }

    def discover_pdf_links(self) -> list[VotePdfLink]:
        soup = self.fetch(INDEX_URL)
        links: list[VotePdfLink] = []
        for heading in soup.find_all("h2"):
            session = normalize_text(heading.get_text(" ", strip=True))
            if "令和" not in session or "定例会" not in session:
                continue
            session_month = parse_session_month(session)
            if session_month is None or not (self.start <= session_month <= self.end):
                continue

            node = heading
            while True:
                node = node.find_next_sibling()
                if node is None or getattr(node, "name", None) == "h2":
                    break
                for anchor in node.find_all("a", href=True):
                    label = normalize_text(anchor.get_text(" ", strip=True))
                    if "議員別" not in label or ".pdf" not in anchor["href"].lower():
                        continue
                    links.append(
                        VotePdfLink(
                            session=session.replace(" 議決結果", ""),
                            session_month=session_month,
                            url=urljoin(INDEX_URL, anchor["href"]),
                            label=label,
                        )
                    )
        links.sort(key=lambda link: link.session_month)
        print(f"{COUNCIL_ID}: discovered {len(links)} regular-session vote PDFs")
        return links

    def download_pdf(self, link: VotePdfLink) -> Path:
        resp = self.session.get(link.url, timeout=self.request_timeout)
        resp.raise_for_status()
        time.sleep(self.sleep_seconds)
        path = Path(tempfile.gettempdir()) / (
            "kurayoshi-votes-" + hashlib.sha1(link.url.encode("utf-8")).hexdigest()[:12]
        )
        path = path.with_suffix(".pdf")
        path.write_bytes(resp.content)
        return path

    def parse_pdf(self, link: VotePdfLink, pdf_path: Path) -> list[dict[str, Any]]:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                if len(text.strip()) < MACHINE_READABLE_MIN_CHARS:
                    self.mark_unreadable(link, "機械可読テキストが不足")
                    return []
                parsed: list[dict[str, Any]] = []
                for page_index, page in enumerate(pdf.pages, start=1):
                    parsed.extend(self.parse_page(link, page, page_index))
                self.stats.pdfs_parsed += 1
                return parsed
        except Exception as exc:
            self.mark_unreadable(link, f"PDF解析エラー: {exc}")
            return []

    def parse_page(
        self, link: VotePdfLink, page: pdfplumber.page.Page, page_index: int
    ) -> list[dict[str, Any]]:
        tables = page.extract_tables()
        if not tables:
            self.mark_unreadable(link, f"{page_index}ページ目に表を検出できない")
            return []

        votes: list[dict[str, Any]] = []
        for table in tables:
            member_names = extract_member_names(table)
            if len(member_names) < 10:
                self.table_warnings.append(
                    {
                        "session": link.session,
                        "location": f"page {page_index}",
                        "reason": f"議員列が{len(member_names)}件で少なすぎる",
                        "source_url": link.url,
                    }
                )
                continue
            for row_index, row in enumerate(table):
                if not is_bill_row(row):
                    continue
                vote = self.build_vote_record(link, member_names, row, row_index)
                if vote is not None:
                    votes.append(vote)
        return votes

    def build_vote_record(
        self,
        link: VotePdfLink,
        member_names: list[str],
        row: list[str | None],
        row_index: int,
    ) -> dict[str, Any] | None:
        bill_number = build_bill_number(row)
        bill_name = clean_cell(row[3]) if len(row) > 3 else ""
        bill_title = normalize_japanese_spacing(f"{bill_number} {bill_name}")
        if not bill_title:
            bill_title = f"{link.session} row {row_index}"

        date_text = clean_cell(row[6]) if len(row) > 6 else ""
        vote_date = parse_reiwa_date(date_text)
        result_col = len(row) - 1
        result = clean_cell(row[result_col]) if result_col >= 0 else ""
        expected_yes = parse_int_cell(row[8] if len(row) > 8 else None)
        expected_no = parse_int_cell(row[9] if len(row) > 9 else None)

        votes_by_member: list[dict[str, Any]] = []
        yes = no = other = 0
        for member_name, cell in zip(member_names, row[MEMBER_START_COL:result_col]):
            raw_vote = clean_cell(cell)
            vote_value = normalize_vote(raw_vote)
            if vote_value == "賛成":
                yes += 1
            elif vote_value == "反対":
                no += 1
            else:
                other += 1

            normalized_member_name = normalize_name(member_name)
            member_id = self.name_to_id.get(normalized_member_name)
            public_member_name = self.name_to_official_name.get(
                normalized_member_name, normalized_member_name
            )
            self.stats.member_cells += 1
            if member_id is not None:
                self.stats.linked_member_cells += 1
            votes_by_member.append(
                {
                    "member_id": member_id,
                    "member_name": public_member_name,
                    "vote": vote_value,
                }
            )

        problems: list[str] = []
        in_session_member_count = len(member_names)
        if yes + no + other != in_session_member_count:
            problems.append(
                f"投票セル数 {yes + no + other} がPDF上の在籍議員数 {in_session_member_count} と不一致"
            )
        if expected_yes is not None and yes != expected_yes:
            problems.append(f"賛成数 {yes} がPDF記載 {expected_yes} と不一致")
        if expected_no is not None and no != expected_no:
            problems.append(f"反対数 {no} がPDF記載 {expected_no} と不一致")

        if problems:
            self.stats.bills_rejected += 1
            self.rejected_bills.append(
                {
                    "session": link.session,
                    "bill_title": bill_title,
                    "reason": " / ".join(problems),
                    "source_url": link.url,
                }
            )
            return None

        self.stats.bills_kept += 1
        return {
            "id": build_vote_id(link.session, vote_date, bill_title, result),
            "council_id": COUNCIL_ID,
            "session": link.session,
            "bill_title": bill_title,
            "date": vote_date.isoformat() if vote_date else None,
            "result": result or None,
            "granularity": "member",
            "votes_by_member": votes_by_member,
            "votes_by_faction": None,
            "source_url": link.url,
        }

    def mark_unreadable(self, link: VotePdfLink, reason: str) -> None:
        self.stats.unreadable_pdfs += 1
        self.omitted_pdfs.append(
            {
                "session": link.session,
                "url": link.url,
                "reason": reason,
            }
        )

    def save_votes(self, dry_run: bool = False) -> dict[str, Any]:
        data = self.scrape_votes()
        if not dry_run:
            self.save_json(OUT_PATH, data)
        return data


def extract_member_names(table: list[list[str | None]]) -> list[str]:
    if len(table) < 2:
        return []
    names: list[str] = []
    result_col = len(table[1]) - 1
    for cell in table[1][MEMBER_START_COL:result_col]:
        name = normalize_name(clean_cell(cell))
        if name:
            names.append(name)
    return names


def is_bill_row(row: list[str | None]) -> bool:
    if len(row) < 12:
        return False
    bill_name = clean_cell(row[3])
    result = clean_cell(row[-1])
    yes = parse_int_cell(row[8])
    no = parse_int_cell(row[9])
    return bool(bill_name and result and yes is not None and no is not None)


def build_bill_number(row: list[str | None]) -> str:
    cells = [clean_cell(row[i]) if i < len(row) else "" for i in range(3)]
    if cells[0] and not cells[1] and not cells[2]:
        return normalize_japanese_spacing(cells[0])
    return normalize_japanese_spacing(" ".join(cell for cell in cells if cell))


def clean_cell(value: str | None) -> str:
    if value is None:
        return ""
    return normalize_text(value.replace("\n", " "))


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_japanese_spacing(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(
        r"(?<=[一-龯々ぁ-んァ-ンー])\s+(?=[一-龯々ぁ-んァ-ンー])", "", value
    )
    value = re.sub(r"\s+(?=号)", "", value)
    value = re.sub(r"(?<=第)\s+", "", value)
    return value.strip()


def normalize_vote(value: str) -> str:
    compact = re.sub(r"\s+", "", value)
    if compact in VOTE_MAP:
        return VOTE_MAP[compact]
    if not compact:
        return "欠席"
    return compact


def parse_int_cell(value: str | None) -> int | None:
    text = clean_cell(value)
    if not text:
        return None
    match = re.search(r"\d+", text)
    if not match:
        return None
    return int(match.group(0))


def parse_session_month(value: str) -> date | None:
    match = re.search(r"令和\s*(\d+)年\s*(\d+)月", value)
    if not match:
        return None
    year = 2018 + int(match.group(1))
    month = int(match.group(2))
    return date(year, month, 1)


def parse_reiwa_date(value: str) -> date | None:
    match = re.search(r"R\s*(\d+)\.(\d+)\.(\d+)", value, re.I)
    if not match:
        return None
    year = 2018 + int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))
    return date(year, month, day)


def build_vote_id(
    session: str, vote_date: date | None, bill_title: str, result: str
) -> str:
    digest = hashlib.sha1(
        f"{session}|{vote_date}|{bill_title}|{result}".encode("utf-8")
    ).hexdigest()
    date_part = vote_date.isoformat() if vote_date else "date-unknown"
    return f"{COUNCIL_ID}--{date_part}--{digest[:12]}"


def load_members() -> list[dict[str, Any]]:
    path = DATA_DIR / COUNCIL_ID / "members.json"
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    members = data.get("members", [])
    if not isinstance(members, list):
        raise SystemExit(f"{path}: members must be a list")
    return members


def parse_date_arg(value: str) -> date:
    return date.fromisoformat(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2024-04-01", type=parse_date_arg)
    parser.add_argument("--end", default="2026-03-31", type=parse_date_arg)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    adapter = KurayoshiVotesPdfAdapter(start=args.start, end=args.end)
    adapter.save_votes(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
