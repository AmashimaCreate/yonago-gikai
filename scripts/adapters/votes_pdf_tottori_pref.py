"""Build Tottori Prefectural Assembly member vote data from official PDFs."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "docs" / "data"
COUNCIL_ID = "tottori-pref"
INDEX_URL = "https://www.pref.tottori.lg.jp/87621.htm"
OUT_PATH = DATA_DIR / COUNCIL_ID / "votes.json"

USER_AGENT = "Mozilla/5.0 (compatible; tottori-mieru/1.0)"
SLEEP_SECONDS = 2.0
REQUEST_TIMEOUT = 30
EXPECTED_MEMBER_COLUMNS = 35
MIN_MEMBER_COLUMNS = 30
PDF_TEXT_MIN_CHARS = 200

SYMBOL_CHARS = "○〇×✕議副棄除欠－-△※"
VOTE_MAP = {
    "○": "賛成",
    "〇": "賛成",
    "×": "反対",
    "✕": "反対",
    "議": "議長",
    "副": "議長",
    "-": "退席",
    "－": "退席",
    "棄": "退席",
    "※": "欠席",
    "欠": "欠席",
    "除": "除斥",
    "△": "継続審査",
}
NAME_VARIANTS = str.maketrans(
    {
        "髙": "高",
        "﨑": "崎",
        "神": "神",
        "隆": "隆",
        "𠮷": "吉",
        "邊": "辺",
        "邉": "辺",
        "濵": "浜",
        "塚": "塚",
    }
)
SKIP_LINES = {
    "知",
    "事",
    "提",
    "案",
    "議",
    "員",
    "請",
    "願",
    "陳",
    "情",
    "議案等",
    "番 号",
    "自由民主党 民主とっとり 公明党",
    "件 名 議決結果",
    "表決",
    "方法",
    "表",
    "決",
    "者",
    "数",
    "賛",
    "成",
    "反",
    "対",
    "無所属",
    "【議案】 議案に対する賛否",
    "【請願・陳情】 委員長報告",
}


@dataclass(frozen=True)
class VotePdfLink:
    session: str
    session_month: date
    session_url: str
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


class TottoriPrefVotesPdfAdapter:
    def __init__(self, start: date, end: date) -> None:
        self.start = start
        self.end = end
        self.members = load_members()
        self.stats = ParseStats()
        self.omitted_pdfs: list[dict[str, str]] = []
        self.rejected_bills: list[dict[str, str]] = []
        self.table_warnings: list[dict[str, str]] = []
        self.quality_checks: dict[str, Any] = {
            "header_full_column_check": None,
            "split_vote_check": None,
        }

    def scrape_votes(self) -> dict[str, Any]:
        ensure_pdftotext()
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
        self.print_summary(len(votes))
        return {
            "council_id": COUNCIL_ID,
            "updated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "acquisition": "scraping",
            "coverage": {
                "source": "鳥取県議会 定例会・臨時会の概要",
                "source_url": INDEX_URL,
                "scope": "直近2年分の定例会・臨時会に掲載された議員別賛否PDF",
                "start_date": self.start.isoformat(),
                "end_date": self.end.isoformat(),
                "quality_policy": "PDFの議員ヘッダ列を名簿へ全列照合し、賛成・反対・表決者数の検算が一致した議決のみ収録。35列PDFはquality_checksに全列対応を保存",
                "note": "PDF上の縦書きヘッダと横長マトリクスを機械抽出しているため、議案名は公式PDFへのリンクで必ず確認する",
            },
            "omitted_pdfs": self.omitted_pdfs,
            "rejected_bills": self.rejected_bills,
            "table_warnings": self.table_warnings,
            "quality_checks": self.quality_checks,
            "votes": votes,
        }

    def discover_pdf_links(self) -> list[VotePdfLink]:
        overview = fetch_text(INDEX_URL)
        sessions = discover_session_links(overview)
        links: list[VotePdfLink] = []
        for session in sessions:
            if not (self.start <= session.session_month <= self.end):
                continue
            session_html = fetch_text(session.url)
            pdf = find_vote_pdf_link(session_html, session.url)
            if pdf is None:
                result_page = find_result_page_link(session_html, session.url)
                if result_page is not None:
                    session_html = fetch_text(result_page)
                    pdf = find_vote_pdf_link(session_html, result_page)
            if pdf is None:
                self.omitted_pdfs.append(
                    {
                        "session": session.session,
                        "url": session.url,
                        "reason": "議員別賛否PDFリンクを検出できない",
                    }
                )
                continue
            links.append(
                VotePdfLink(
                    session=session.session,
                    session_month=session.session_month,
                    session_url=session.url,
                    url=pdf["url"],
                    label=pdf["label"],
                )
            )
        links.sort(key=lambda link: link.session_month)
        print(f"{COUNCIL_ID}: discovered {len(links)} vote PDFs")
        return links

    def download_pdf(self, link: VotePdfLink) -> Path:
        content = fetch_bytes(link.url)
        path = Path(tempfile.gettempdir()) / (
            "tottori-pref-votes-"
            + hashlib.sha1(link.url.encode("utf-8")).hexdigest()[:12]
        )
        path = path.with_suffix(".pdf")
        path.write_bytes(content)
        return path

    def parse_pdf(self, link: VotePdfLink, pdf_path: Path) -> list[dict[str, Any]]:
        try:
            raw_text = pdftotext(pdf_path, "-raw")
            if len(raw_text.strip()) < PDF_TEXT_MIN_CHARS:
                self.mark_unreadable(link, "機械可読テキストが不足")
                return []
            layout_text = pdftotext(pdf_path, "-layout")
            layout_records = extract_layout_records(layout_text)
            raw_records = self.extract_raw_records(link, raw_text)
            merge_layout_titles(raw_records, layout_records)
            votes = [self.build_vote_record(link, record) for record in raw_records]
            self.stats.pdfs_parsed += 1
            return [vote for vote in votes if vote is not None]
        except Exception as exc:
            self.mark_unreadable(link, f"PDF解析エラー: {exc}")
            return []

    def extract_raw_records(
        self, link: VotePdfLink, raw_text: str
    ) -> list[dict[str, Any]]:
        vote_date = parse_vote_date(raw_text)
        records: list[dict[str, Any]] = []
        member_columns: list[dict[str, Any]] | None = None
        for page_index, page_text in enumerate(raw_text.split("\f"), start=1):
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            if not lines:
                continue

            header = self.extract_member_columns(link, lines, page_index)
            if header is not None:
                member_columns = header
            if member_columns is None:
                self.table_warnings.append(
                    {
                        "session": link.session,
                        "location": f"page {page_index}",
                        "reason": "議員ヘッダをまだ検出できないページをスキップ",
                        "source_url": link.url,
                    }
                )
                continue

            data_start = find_data_start(lines)
            if data_start is None:
                continue
            buffer: list[str] = []
            for line in lines[data_start:]:
                if line.startswith("※") or line == "【凡例】":
                    break
                if line in SKIP_LINES:
                    continue
                if not buffer and not is_bill_start(line):
                    continue
                buffer.append(line)
                parsed = parse_vote_buffer(buffer, len(member_columns))
                if parsed is None:
                    continue
                parsed["date"] = vote_date
                parsed["member_columns"] = member_columns
                parsed["page"] = page_index
                records.append(parsed)
                buffer = []
        return records

    def extract_member_columns(
        self, link: VotePdfLink, lines: list[str], page_index: int
    ) -> list[dict[str, Any]] | None:
        labels: list[str] = []
        buffer: list[str] = []
        for line in lines:
            if "【議案】" in line or line == "議案等":
                break
            if line == "員" and buffer and buffer[-1] == "議":
                label = "".join(buffer[:-1])
                buffer = []
                if label:
                    labels.append(label)
                continue
            if re.fullmatch(r"[一-龯々ぁ-んァ-ンー]{1,3}", line):
                buffer.append(line)
            else:
                buffer = []

        if not labels:
            return None

        columns: list[dict[str, Any]] = []
        unmatched: list[str] = []
        for index, label in enumerate(labels, start=1):
            member = match_header_label(label, self.members)
            if member is None:
                unmatched.append(label)
                columns.append(
                    {
                        "column": index,
                        "header_label": label,
                        "member_id": None,
                        "member_name": label,
                    }
                )
                continue
            columns.append(
                {
                    "column": index,
                    "header_label": label,
                    "member_id": member["id"],
                    "member_name": member["name"],
                }
            )

        if len(columns) < MIN_MEMBER_COLUMNS:
            self.table_warnings.append(
                {
                    "session": link.session,
                    "location": f"page {page_index}",
                    "reason": f"議員ヘッダ照合 {len(columns)}件で少なすぎる",
                    "source_url": link.url,
                }
            )
            return None

        if len(columns) == EXPECTED_MEMBER_COLUMNS and not unmatched:
            self.set_header_quality_check(link, columns)
        return columns

    def set_header_quality_check(
        self, link: VotePdfLink, columns: list[dict[str, Any]]
    ) -> None:
        if self.quality_checks["header_full_column_check"] is not None:
            return
        self.quality_checks["header_full_column_check"] = {
            "source_url": link.url,
            "session": link.session,
            "expected_columns": EXPECTED_MEMBER_COLUMNS,
            "matched_columns": len(columns),
            "unmatched": [],
            "checked_scope": "PDFヘッダ35列すべてを現職members.jsonへ順番どおり照合",
            "columns": [
                {
                    "column": column["column"],
                    "header_label": column["header_label"],
                    "member_id": column["member_id"],
                    "member_name": column["member_name"],
                }
                for column in columns
            ],
        }

    def build_vote_record(
        self, link: VotePdfLink, record: dict[str, Any]
    ) -> dict[str, Any] | None:
        votes_by_member: list[dict[str, Any]] = []
        yes = no = 0
        for column, raw_symbol in zip(record["member_columns"], record["symbols"]):
            vote_value = normalize_vote(raw_symbol)
            if vote_value == "賛成":
                yes += 1
            elif vote_value == "反対":
                no += 1
            member_id = column["member_id"]
            member_name = column["member_name"]
            self.stats.member_cells += 1
            if member_id is not None:
                self.stats.linked_member_cells += 1
            votes_by_member.append(
                {
                    "member_id": member_id,
                    "member_name": member_name,
                    "vote": vote_value,
                }
            )

        problems: list[str] = []
        if len(record["symbols"]) != len(record["member_columns"]):
            problems.append(
                f"投票セル数 {len(record['symbols'])} が議員ヘッダ列数 {len(record['member_columns'])} と不一致"
            )
        if yes != record["yes"]:
            problems.append(f"賛成数 {yes} がPDF記載 {record['yes']} と不一致")
        if no != record["no"]:
            problems.append(f"反対数 {no} がPDF記載 {record['no']} と不一致")
        if yes + no != record["total"]:
            problems.append(
                f"表決者数 {yes + no} がPDF記載 {record['total']} と不一致"
            )

        bill_title = record["title"] or f"{link.session} page {record['page']}"
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

        vote_date = record["date"]
        result = record["result"] or None
        self.stats.bills_kept += 1
        if (
            self.quality_checks["split_vote_check"] is None
            and record["yes"] > 0
            and record["no"] > 0
        ):
            self.quality_checks["split_vote_check"] = {
                "source_url": link.url,
                "session": link.session,
                "bill_title": bill_title,
                "expected_yes": record["yes"],
                "expected_no": record["no"],
                "calculated_yes": yes,
                "calculated_no": no,
                "note": "割れた議決で賛成・反対数がPDF記載と一致することを確認",
            }
        return {
            "id": build_vote_id(link.session, vote_date, bill_title, result),
            "council_id": COUNCIL_ID,
            "session": link.session,
            "bill_title": bill_title,
            "date": vote_date.isoformat() if vote_date else None,
            "result": result,
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
            OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with OUT_PATH.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
        return data

    def print_summary(self, vote_count: int) -> None:
        print(
            f"{COUNCIL_ID}: pdfs_seen={self.stats.pdfs_seen}, "
            f"pdfs_parsed={self.stats.pdfs_parsed}, "
            f"unreadable_pdfs={self.stats.unreadable_pdfs}, "
            f"votes={vote_count}, rejected={self.stats.bills_rejected}"
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


@dataclass(frozen=True)
class SessionLink:
    session: str
    session_month: date
    url: str


def fetch_text(url: str) -> str:
    data = fetch_bytes(url)
    return data.decode("utf-8", errors="replace")


def fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            data = response.read()
    except URLError as exc:
        raise RuntimeError(f"{url}: fetch failed: {exc}") from exc
    time.sleep(SLEEP_SECONDS)
    return data


def discover_session_links(overview_html: str) -> list[SessionLink]:
    sessions: list[SessionLink] = []
    current_year: int | None = None
    for line in overview_html.splitlines():
        year_match = re.search(r"◆\s*令和\s*([0-9０-９]+)\s*年", line)
        if year_match:
            current_year = 2018 + int(to_ascii_digits(year_match.group(1)))
        if current_year is None:
            continue
        for href, raw_label in re.findall(
            r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
            line,
            flags=re.I,
        ):
            label = normalize_text(strip_tags(html.unescape(raw_label)))
            month_match = re.search(r"([0-9０-９]+)\s*月", label)
            if not month_match or "会" not in label:
                continue
            month = int(to_ascii_digits(month_match.group(1)))
            sessions.append(
                SessionLink(
                    session=f"令和{current_year - 2018}年{month}月{label.split('月', 1)[1]}",
                    session_month=date(current_year, month, 1),
                    url=urljoin(INDEX_URL, href),
                )
            )
    sessions.sort(key=lambda item: item.session_month)
    return sessions


def find_vote_pdf_link(page_html: str, base_url: str) -> dict[str, str] | None:
    for href, raw_label in re.findall(
        r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
        page_html,
        flags=re.I | re.S,
    ):
        label = normalize_text(strip_tags(html.unescape(raw_label)))
        if "議員別" not in label or "賛否" not in label:
            continue
        if ".pdf" not in href.lower():
            continue
        return {"url": urljoin(base_url, href), "label": label}
    return None


def find_result_page_link(page_html: str, base_url: str) -> str | None:
    for href, raw_label in re.findall(
        r"<a\b[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
        page_html,
        flags=re.I | re.S,
    ):
        label = normalize_text(strip_tags(html.unescape(raw_label)))
        if "議案等の議決結果" in label:
            return urljoin(base_url, href)
    return None


def ensure_pdftotext() -> None:
    if shutil.which("pdftotext") is None:
        raise SystemExit("pdftotext command not found. Install poppler to parse PDFs.")


def pdftotext(pdf_path: Path, mode: str) -> str:
    output_path = pdf_path.with_suffix(f".{mode.removeprefix('-')}.txt")
    subprocess.run(
        ["pdftotext", mode, str(pdf_path), str(output_path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return output_path.read_text(encoding="utf-8", errors="replace")


def extract_layout_records(layout_text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    buffer: list[str] = []
    for line in layout_text.splitlines():
        clean_line = line.rstrip()
        stripped = clean_line.strip()
        if not stripped or stripped in SKIP_LINES:
            continue
        if "自由民主党" in stripped or "議案等" in stripped:
            continue
        if "件" in stripped and "名" in stripped and "議決結果" in stripped:
            continue
        if not buffer and not is_bill_start(stripped):
            continue
        buffer.append(clean_line)
        parsed = parse_vote_buffer(buffer, EXPECTED_MEMBER_COLUMNS)
        if parsed is None:
            parsed = parse_vote_buffer(buffer, EXPECTED_MEMBER_COLUMNS - 1)
        if parsed is not None:
            records.append(parsed)
            buffer = []
    return records


def merge_layout_titles(
    raw_records: list[dict[str, Any]], layout_records: list[dict[str, Any]]
) -> None:
    for raw, layout in zip(raw_records, layout_records, strict=False):
        if (
            raw["yes"] == layout["yes"]
            and raw["no"] == layout["no"]
            and raw["total"] == layout["total"]
            and len(layout["title"]) > len(raw["title"])
        ):
            raw["title"] = layout["title"]


def find_data_start(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        if "【議案】" in line or line == "議案等":
            return i + 1
    return None


def build_vote_row_re(member_column_count: int) -> re.Pattern[str]:
    return re.compile(
        rf"(?P<votes>(?:[{re.escape(SYMBOL_CHARS)}]\s+)"
        rf"{{{member_column_count - 1}}}[{re.escape(SYMBOL_CHARS)}])\s+"
        r"(?P<yes>\d+)\s+(?P<no>\d+)\s+(?P<total>\d+)\s+"
        r"(?P<result>.+?)(?:\s+(?P<method>起立|簡易採決|簡易|採決|記名|無記名))?\s*$"
    )


def parse_vote_buffer(
    buffer: list[str], member_column_count: int
) -> dict[str, Any] | None:
    text = " ".join(buffer)
    match = build_vote_row_re(member_column_count).search(text)
    if match is None:
        return None
    return {
        "title": normalize_japanese_spacing(text[: match.start()]),
        "symbols": match.group("votes").split(),
        "yes": int(match.group("yes")),
        "no": int(match.group("no")),
        "total": int(match.group("total")),
        "result": normalize_japanese_spacing(match.group("result")),
        "method": match.group("method"),
    }


def is_bill_start(line: str) -> bool:
    return bool(
        re.match(
            r"^(第[０-９0-9一二三四五六七八九十百]+号|附帯意見|[0-9０-９]+年[－-][0-9０-９]+)",
            line.strip(),
        )
    )


def parse_vote_date(text: str) -> date | None:
    match = re.search(
        r"令和\s*([0-9０-９]+)年\s*([0-9０-９]+)月\s*([0-9０-９]+)日\s*議決分",
        text,
    )
    if not match:
        return None
    year = 2018 + int(to_ascii_digits(match.group(1)))
    month = int(to_ascii_digits(match.group(2)))
    day = int(to_ascii_digits(match.group(3)))
    return date(year, month, day)


def normalize_vote(value: str) -> str:
    compact = re.sub(r"\s+", "", value)
    return VOTE_MAP.get(compact, compact)


def normalize_name(value: str) -> str:
    value = value.translate(NAME_VARIANTS)
    value = re.sub(r"[\s\u3000]", "", value)
    value = re.sub(r"(議員|君|氏|さん)$", "", value)
    return value


def match_header_label(
    header_label: str, members: list[dict[str, Any]]
) -> dict[str, Any] | None:
    normalized_label = normalize_name(header_label)
    matches = [
        member
        for member in members
        if isinstance(member.get("name"), str)
        and normalize_name(member["name"]).startswith(normalized_label)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_japanese_spacing(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(
        r"(?<=[一-龯々ぁ-んァ-ンー])\s+(?=[一-龯々ぁ-んァ-ンー])", "", value
    )
    value = re.sub(r"(?<=第)\s+", "", value)
    value = re.sub(r"\s+(?=号)", "", value)
    value = re.sub(r"\s+([）)])", r"\1", value)
    value = re.sub(r"([（(])\s+", r"\1", value)
    return value.strip()


def strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value)


def to_ascii_digits(value: str) -> str:
    return value.translate(str.maketrans("０１２３４５６７８９", "0123456789"))


def build_vote_id(
    session: str, vote_date: date | None, bill_title: str, result: str | None
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

    adapter = TottoriPrefVotesPdfAdapter(start=args.start, end=args.end)
    adapter.save_votes(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
