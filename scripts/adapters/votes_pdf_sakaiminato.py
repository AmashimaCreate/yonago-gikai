"""Build Sakaiminato City Council member vote data from locally downloaded PDFs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pdfplumber

if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from scripts.adapters.minutes_kensakusystem_legacy import (  # noqa: E402
    normalize_name,
)
from scripts.base import CouncilScraperBase  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "docs" / "data"
COUNCIL_ID = "sakaiminato-city"
SOURCE_DIR = REPO_ROOT / "data_sources" / "votes_pdf" / COUNCIL_ID
SOURCES_PATH = SOURCE_DIR / "sources.json"
OUT_PATH = DATA_DIR / COUNCIL_ID / "votes.json"

MACHINE_READABLE_MIN_CHARS = 200

VOTE_MAP = {
    "○": "賛成",
    "〇": "賛成",
    "×": "反対",
    "✕": "反対",
    "-": "退席",
    "－": "退席",
    "ー": "退席",
    "※": "欠席",
    "議長": "議長",
    "除斥": "除斥",
    "△": "継続審査",
}


@dataclass(frozen=True)
class LocalVotePdf:
    session: str
    title: str
    filename: str
    path: Path
    source_url: str


@dataclass
class ParseStats:
    pdfs_seen: int = 0
    pdfs_parsed: int = 0
    unreadable_pdfs: int = 0
    bills_kept: int = 0
    bills_rejected: int = 0
    member_cells: int = 0
    linked_member_cells: int = 0


class SakaiminatoVotesPdfAdapter(CouncilScraperBase):
    def __init__(self) -> None:
        super().__init__()
        self.sources = load_sources()
        self.members = load_members()
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
        pdfs = self.load_pdf_list()
        votes: list[dict[str, Any]] = []
        for link in pdfs:
            self.stats.pdfs_seen += 1
            votes.extend(self.parse_pdf(link))

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
                print(f"- {item['session']}: {item['reason']} {item['filename']}")
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
            "acquisition": "manual_download",
            "coverage": {
                "source": "境港市議会 議決結果PDF",
                "source_url": self.sources["source_url"],
                "downloaded_at": self.sources["downloaded_at"],
                "downloaded_by": self.sources["downloaded_by"],
                "scope": "KTが手動ダウンロードした令和6年1月から令和8年6月までの議決結果PDF",
                "missing_note": "令和6年6月〜12月の定例会分は公式サイト上で確認できず未収録",
                "source_note": self.sources["note"],
                "quality_policy": "検算不一致または機械可読でないPDFは未収録",
            },
            "omitted_pdfs": self.omitted_pdfs,
            "rejected_bills": self.rejected_bills,
            "table_warnings": self.table_warnings,
            "votes": votes,
        }

    def load_pdf_list(self) -> list[LocalVotePdf]:
        items: list[LocalVotePdf] = []
        files = self.sources.get("files")
        if not isinstance(files, list):
            raise SystemExit(f"{SOURCES_PATH}: files must be a list")
        for item in files:
            if not isinstance(item, dict):
                raise SystemExit(f"{SOURCES_PATH}: file entry must be an object")
            filename = item.get("filename")
            session = item.get("session")
            title = item.get("title")
            source_url = item.get("source_url", self.sources.get("source_url"))
            if not all(isinstance(value, str) for value in (filename, session, title, source_url)):
                raise SystemExit(f"{SOURCES_PATH}: invalid file entry {item!r}")
            path = SOURCE_DIR / filename
            if not path.exists():
                raise SystemExit(f"{path}: file not found")
            items.append(
                LocalVotePdf(
                    session=session,
                    title=title,
                    filename=filename,
                    path=path,
                    source_url=source_url,
                )
            )
        return items

    def parse_pdf(self, link: LocalVotePdf) -> list[dict[str, Any]]:
        try:
            with pdfplumber.open(link.path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                if len(text.strip()) < MACHINE_READABLE_MIN_CHARS:
                    self.mark_unreadable(link, "機械可読テキストが不足")
                    return []
                parsed: list[dict[str, Any]] = []
                member_names: list[str] = []
                for page_index, page in enumerate(pdf.pages, start=1):
                    page_votes, member_names = self.parse_page(
                        link, page, page_index, member_names
                    )
                    parsed.extend(page_votes)
                self.stats.pdfs_parsed += 1
                return parsed
        except Exception as exc:
            self.mark_unreadable(link, f"PDF解析エラー: {exc}")
            return []

    def parse_page(
        self,
        link: LocalVotePdf,
        page: pdfplumber.page.Page,
        page_index: int,
        current_member_names: list[str],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        tables = page.extract_tables()
        if not tables:
            self.table_warnings.append(
                {
                    "session": link.session,
                    "location": f"page {page_index}",
                    "reason": "表を検出できないページをスキップ",
                    "filename": link.filename,
                }
            )
            return [], current_member_names

        votes: list[dict[str, Any]] = []
        member_names = current_member_names
        for table_index, table in enumerate(tables, start=1):
            header = find_member_header(table)
            data_start_row = 0
            if header is not None:
                member_names = header["member_names"]
                data_start_row = header["row_index"] + 1
            if len(member_names) < 10:
                self.table_warnings.append(
                    {
                        "session": link.session,
                        "location": f"page {page_index} table {table_index}",
                        "reason": f"議員列が{len(member_names)}件で少なすぎる",
                        "filename": link.filename,
                    }
                )
                continue
            member_start_col = infer_member_start_col(table, member_names)
            if member_start_col is None:
                self.table_warnings.append(
                    {
                        "session": link.session,
                        "location": f"page {page_index} table {table_index}",
                        "reason": "議員列の開始位置を推定できない",
                        "filename": link.filename,
                    }
                )
                continue
            for row_index, row in enumerate(table[data_start_row:], start=data_start_row):
                if not is_bill_row(row, member_start_col, len(member_names)):
                    continue
                vote = self.build_vote_record(
                    link, member_names, row, row_index, page_index, member_start_col
                )
                if vote is not None:
                    votes.append(vote)
        return votes, member_names

    def build_vote_record(
        self,
        link: LocalVotePdf,
        member_names: list[str],
        row: list[str | None],
        row_index: int,
        page_index: int,
        member_start_col: int,
    ) -> dict[str, Any] | None:
        base = [clean_cell(cell) for cell in row[:member_start_col]]
        bill_number = build_bill_number(base)
        bill_name = infer_bill_name(base)
        bill_title = normalize_japanese_spacing(f"{bill_number} {bill_name}")
        if not bill_title:
            bill_title = f"{link.session} page {page_index} row {row_index}"

        date_text = find_date_text(base)
        vote_date = parse_reiwa_date(date_text)
        result = infer_result(base)

        vote_cells = row[member_start_col : member_start_col + len(member_names)]
        votes_by_member: list[dict[str, Any]] = []
        counts = {
            "賛成": 0,
            "反対": 0,
            "退席": 0,
            "欠席": 0,
            "議長": 0,
            "除斥": 0,
            "継続審査": 0,
        }
        for member_name, cell in zip(member_names, vote_cells):
            raw_vote = clean_cell(cell)
            vote_value = normalize_vote(raw_vote)
            counts.setdefault(vote_value, 0)
            counts[vote_value] += 1

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

        total = sum(counts.values())
        problems: list[str] = []
        if total != len(member_names):
            problems.append(
                f"投票セル数 {total} がPDFヘッダの議員数 {len(member_names)} と不一致"
            )

        if problems:
            self.stats.bills_rejected += 1
            self.rejected_bills.append(
                {
                    "session": link.session,
                    "bill_title": bill_title,
                    "reason": " / ".join(problems),
                    "filename": link.filename,
                    "source_url": link.source_url,
                }
            )
            return None

        self.stats.bills_kept += 1
        return {
            "id": build_vote_id(
                link.session, vote_date, bill_title, result, link.filename, page_index, row_index
            ),
            "council_id": COUNCIL_ID,
            "session": link.session,
            "bill_title": bill_title,
            "date": vote_date.isoformat() if vote_date else None,
            "result": result or None,
            "granularity": "member",
            "votes_by_member": votes_by_member,
            "votes_by_faction": None,
            "source_url": link.source_url,
        }

    def mark_unreadable(self, link: LocalVotePdf, reason: str) -> None:
        self.stats.unreadable_pdfs += 1
        self.omitted_pdfs.append(
            {
                "session": link.session,
                "filename": link.filename,
                "reason": reason,
            }
        )

    def save_votes(self, dry_run: bool = False) -> dict[str, Any]:
        data = self.scrape_votes()
        if not dry_run:
            self.save_json(OUT_PATH, data)
        return data


def find_member_header(table: list[list[str | None]]) -> dict[str, Any] | None:
    for row_index, row in enumerate(table[:5]):
        cleaned = [clean_cell(cell) for cell in row]
        for start in range(max(0, len(cleaned) - 18), min(len(cleaned), 8)):
            names = [normalize_name(cell) for cell in cleaned[start:] if normalize_name(cell)]
            if len(names) >= 10 and looks_like_member_names(names):
                return {
                    "row_index": row_index,
                    "start_col": start,
                    "member_names": names,
                }
    return None


def looks_like_member_names(values: list[str]) -> bool:
    return sum(1 for value in values if 2 <= len(value) <= 6) >= 10


def infer_member_start_col(
    table: list[list[str | None]], member_names: list[str]
) -> int | None:
    for row in table[:5]:
        normalized_row = [normalize_name(clean_cell(cell)) for cell in row]
        for start in range(0, len(normalized_row)):
            window = normalized_row[start : start + len(member_names)]
            if window == member_names:
                return start
    if not table:
        return None
    widths = [len(row) for row in table if row]
    if not widths:
        return None
    return max(widths) - len(member_names)


def is_bill_row(row: list[str | None], member_start_col: int, member_count: int) -> bool:
    if len(row) < member_start_col + member_count:
        return False
    base = [clean_cell(cell) for cell in row[:member_start_col]]
    if not find_date_text(base):
        return False
    if not infer_result(base):
        return False
    vote_cells = row[member_start_col : member_start_col + member_count]
    normalized_votes = [normalize_vote(clean_cell(cell)) for cell in vote_cells]
    return sum(1 for vote in normalized_votes if vote) >= max(10, member_count - 1)


def build_bill_number(base: list[str]) -> str:
    cells, _ = split_bill_parts(base)
    return normalize_japanese_spacing(" ".join(cell for cell in cells if cell))


def infer_bill_name(base: list[str]) -> str:
    _, name = split_bill_parts(base)
    return name


def split_bill_parts(base: list[str]) -> tuple[list[str], str]:
    date_index = find_date_index(base)
    if date_index is None:
        return base[:2], ""
    candidates = base[:date_index]
    last_text_index = None
    for index in range(len(candidates) - 1, -1, -1):
        if candidates[index]:
            last_text_index = index
            break
    if last_text_index is None:
        return [], ""
    return candidates[:last_text_index], candidates[last_text_index]


def find_date_text(base: list[str]) -> str:
    for cell in base:
        if parse_reiwa_date(cell):
            return cell
    return ""


def find_date_index(base: list[str]) -> int | None:
    for index, cell in enumerate(base):
        if parse_reiwa_date(cell):
            return index
    return None


def infer_result(base: list[str]) -> str:
    date_index = find_date_index(base)
    if date_index is None:
        return ""
    for cell in base[date_index + 1 :]:
        if cell:
            return normalize_japanese_spacing(cell)
    return ""


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
    if "議長裁決" in compact:
        if "×" in compact or "✕" in compact:
            return "反対"
        if "○" in compact or "〇" in compact:
            return "賛成"
    if compact in VOTE_MAP:
        return VOTE_MAP[compact]
    if not compact:
        return "欠席"
    return compact


def parse_reiwa_date(value: str) -> date | None:
    match = re.search(r"R\s*(\d+)\.(\d+)\.(\d+)", value, re.I)
    if not match:
        return None
    year = 2018 + int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))
    return date(year, month, day)


def build_vote_id(
    session: str,
    vote_date: date | None,
    bill_title: str,
    result: str,
    filename: str,
    page_index: int,
    row_index: int,
) -> str:
    digest = hashlib.sha1(
        f"{session}|{vote_date}|{bill_title}|{result}|{filename}|{page_index}|{row_index}".encode(
            "utf-8"
        )
    ).hexdigest()
    date_part = vote_date.isoformat() if vote_date else "date-unknown"
    return f"{COUNCIL_ID}--{date_part}--{digest[:12]}"


def load_sources() -> dict[str, Any]:
    with SOURCES_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"{SOURCES_PATH}: root must be an object")
    if data.get("council_id") != COUNCIL_ID:
        raise SystemExit(f"{SOURCES_PATH}: council_id must be {COUNCIL_ID}")
    return data


def load_members() -> list[dict[str, Any]]:
    path = DATA_DIR / COUNCIL_ID / "members.json"
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    members = data.get("members", [])
    if not isinstance(members, list):
        raise SystemExit(f"{path}: members must be a list")
    return members


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    adapter = SakaiminatoVotesPdfAdapter()
    adapter.save_votes(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
