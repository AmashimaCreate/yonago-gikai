"""Scrape speech indexes from legacy kensakusystem.jp minutes sites.

The legacy kensakusystem UI is Shift_JIS/CP932 based. Search POST bodies must
also be CP932 URL-encoded, otherwise Japanese speaker names are garbled by the
CGI and searches silently return zero results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urljoin

import requests
from bs4 import BeautifulSoup

if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from scripts.base import CouncilScraperBase  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
COUNCILS_PATH = REPO_ROOT / "councils.json"
DATA_DIR = REPO_ROOT / "docs" / "data"

COVERAGE = {
    "scope": "本会議・議員発言者(speaker1)のみ",
    "excluded": [
        "議長の議事進行発言",
        "市長・執行部の発言(member_id: null扱い)",
    ],
    "note": "議長は慣例により一般質問を行わないため発言数が少なく/ゼロに見える場合がある",
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


@dataclass(frozen=True)
class MemberMatch:
    speaker_label: str
    member_id: str | None
    mode: str


@dataclass(frozen=True)
class SearchScope:
    from_year: str
    from_date: str
    till_year: str
    till_date: str
    start_date: date
    end_date: date


class NameMatcher:
    """Match kensakusystem speaker labels to members.json IDs."""

    def __init__(self, members: list[dict[str, Any]]) -> None:
        self.full_name_to_id: dict[str, str] = {}
        family_to_ids: dict[str, list[str]] = {}
        for member in members:
            member_id = member.get("id")
            name = member.get("name")
            if not isinstance(member_id, str) or not isinstance(name, str):
                continue

            full_name = normalize_name(name)
            self.full_name_to_id[full_name] = member_id

            family = normalize_name(name.split()[0].split("　")[0])
            family_to_ids.setdefault(family, []).append(member_id)

        self.unique_family_to_id = {
            family: ids[0] for family, ids in family_to_ids.items() if len(ids) == 1
        }

    def match(self, speaker_label: str) -> MemberMatch:
        normalized = normalize_name(speaker_label)
        if normalized in self.full_name_to_id:
            return MemberMatch(speaker_label, self.full_name_to_id[normalized], "full")
        if normalized in self.unique_family_to_id:
            return MemberMatch(
                speaker_label, self.unique_family_to_id[normalized], "family_unique"
            )
        return MemberMatch(speaker_label, None, "unmatched")


class KensakuSystemLegacyMinutesAdapter(CouncilScraperBase):
    """Common adapter for legacy ``www.kensakusystem.jp/{tenant}/`` sites."""

    def __init__(
        self,
        council_id: str,
        fiscal_start_year: int = 2024,
        fiscal_years: int = 2,
    ) -> None:
        super().__init__()
        self.council_id = council_id
        self.fiscal_start_year = fiscal_start_year
        self.fiscal_years = fiscal_years
        self.council = self.load_council(council_id)
        self.base_url = self.council["minutes_base_url"].rstrip("/") + "/"
        self.search_url = urljoin(self.base_url, "cgi-bin3/Search2.exe")
        self.search_top_url: str | None = None
        self.code: str | None = None
        self.resultframe_is_durable: bool | None = None

    def load_council(self, council_id: str) -> dict[str, Any]:
        with COUNCILS_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        for council in data.get("councils", []):
            if council.get("id") == council_id:
                if not council.get("minutes_base_url"):
                    raise SystemExit(f"{council_id}: minutes_base_url is not set")
                return council
        raise SystemExit(f"{council_id}: not found in councils.json")

    def fetch_legacy_text(
        self, url: str, data: list[tuple[str, str]] | None = None
    ) -> str:
        if data is None:
            resp = self.session.get(url, timeout=self.request_timeout)
        else:
            body = urlencode(data, encoding="cp932").encode("ascii")
            resp = self.session.post(
                url,
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.request_timeout,
            )
        resp.raise_for_status()
        time.sleep(self.sleep_seconds)
        return resp.content.decode("cp932", errors="replace")

    def extract_code(self) -> str:
        top_html = self.fetch_legacy_text(urljoin(self.base_url, "index.html"))
        matches = re.findall(r"Search2\.exe\?Code=([^&\"']+)", top_html)
        if not matches:
            raise SystemExit(f"{self.council_id}: could not extract Code")
        self.code = matches[0]
        self.search_top_url = f"{self.search_url}?Code={quote(self.code)}&sTarget=2"
        return self.code

    def fetch_search_form(self, from_year: str, till_year: str) -> str:
        code = self.require_code()
        return self.fetch_legacy_text(
            self.search_url,
            [
                ("Code", code),
                ("dMode", "0"),
                ("fromYear", from_year),
                ("tillYear", till_year),
                ("eTarget", "1"),
            ],
        )

    def build_scope(self) -> tuple[SearchScope, str]:
        start = date(self.fiscal_start_year, 4, 1)
        end = date(self.fiscal_start_year + self.fiscal_years, 3, 31)
        from_year = to_reiwa_label(start.year)
        till_year = to_reiwa_label(end.year)
        form_html = self.fetch_search_form(from_year, till_year)

        from_dates = extract_select_options(form_html, "fromDate")
        till_dates = extract_select_options(form_html, "tillDate")
        from_date = first_meeting_on_or_after(from_dates, start)
        till_date = last_meeting_on_or_before(till_dates, end)
        if from_date is None or till_date is None:
            raise SystemExit(
                f"{self.council_id}: could not determine search date range "
                f"for {start.isoformat()}..{end.isoformat()}"
            )

        return (
            SearchScope(
                from_year=from_year,
                from_date=from_date,
                till_year=till_year,
                till_date=till_date,
                start_date=start,
                end_date=end,
            ),
            form_html,
        )

    def scrape_speeches(self) -> dict[str, Any]:
        self.extract_code()
        scope, form_html = self.build_scope()
        speakers = extract_speaker1_options(form_html)
        matcher = NameMatcher(load_members(self.council_id))
        matches = [matcher.match(speaker) for speaker in speakers]

        rows: list[dict[str, Any]] = []
        unmatched = [match.speaker_label for match in matches if match.member_id is None]
        fallback_matches = [
            match.speaker_label for match in matches if match.mode == "family_unique"
        ]

        for match in matches:
            result_html = self.search_speaker(match.speaker_label, scope)
            rows.extend(self.parse_result_rows(result_html, match, scope))
            year_tabs = extract_result_years(result_html)
            for year_label in year_tabs[1:]:
                year_html = self.search_speaker_year(
                    match.speaker_label, year_label, scope
                )
                rows.extend(self.parse_result_rows(year_html, match, scope))

        source_url = self.choose_source_url(rows)
        speeches = self.build_speeches(rows, source_url)

        print(
            f"{self.council_id}: speaker1={len(speakers)}, "
            f"speeches={len(speeches)}, "
            f"member_id_linked={sum(1 for s in speeches if s['member_id'])}"
        )
        if fallback_matches:
            print(
                "family-name fallback matches: " + ", ".join(sorted(fallback_matches))
            )
        if unmatched:
            print("unmatched speaker1 names: " + ", ".join(sorted(unmatched)))
        else:
            print("unmatched speaker1 names: none")
        if self.resultframe_is_durable:
            print("source_url mode: ResultFrame.exe direct URL")
        else:
            print("source_url mode: search top fallback")

        return {
            "council_id": self.council_id,
            "coverage": COVERAGE,
            "speeches": speeches,
        }

    def search_speaker(self, speaker_label: str, scope: SearchScope) -> str:
        code = self.require_code()
        return self.fetch_legacy_text(
            self.search_url,
            [
                ("Code", code),
                ("dMode", "0"),
                ("KeyWord", ""),
                ("searchMode", "1"),
                ("keyMode", "10"),
                ("fromYear", scope.from_year),
                ("fromDate", scope.from_date),
                ("tillYear", scope.till_year),
                ("tillDate", scope.till_date),
                ("speaker", speaker_label),
                ("speaker1", speaker_label),
                ("speaker2", ""),
                ("speaker3", ""),
                ("eTarget", "1"),
                ("AhitResult", "検索"),
            ],
        )

    def search_speaker_year(
        self, speaker_label: str, year_label: str, scope: SearchScope
    ) -> str:
        code = self.require_code()
        return self.fetch_legacy_text(
            self.search_url,
            [
                ("Code", code),
                ("dMode", "0"),
                ("fromDate", scope.from_date),
                ("tillDate", scope.till_date),
                ("sTarget", "2:0"),
                ("searchMode", "1"),
                ("keyMode", "10"),
                ("speaker", speaker_label),
                ("treedepth", year_label),
                ("FUNC", ""),
                ("sort", ""),
            ],
        )

    def parse_result_rows(
        self, html: str, match: MemberMatch, scope: SearchScope
    ) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[dict[str, Any]] = []
        for link in soup.find_all("a", href=True):
            context = extract_go_context(link["href"])
            if context is None:
                continue
            tr = link.find_parent("tr")
            if tr is None:
                continue
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all("td")]
            if len(cells) < 5:
                continue
            meeting_base = cells[0]
            meeting_issue = link.get_text(" ", strip=True)
            meeting_date = parse_meeting_date(f"{meeting_base} {meeting_issue}")
            if meeting_date is None:
                continue
            if not (scope.start_date <= meeting_date <= scope.end_date):
                continue
            rows.append(
                {
                    "member_id": match.member_id,
                    "speaker_label": match.speaker_label,
                    "meeting_name": f"{meeting_base}{meeting_issue} 本会議",
                    "date": meeting_date.isoformat(),
                    "context": context,
                }
            )
        return rows

    def choose_source_url(self, rows: list[dict[str, Any]]) -> str:
        if not rows:
            self.resultframe_is_durable = False
            return self.require_search_top_url()

        sample = rows[0]
        resultframe_url = self.build_resultframe_url(
            sample["speaker_label"], sample["context"]
        )
        html = self.fetch_legacy_text(resultframe_url)
        body_is_direct = "<FRAMESET" not in html.upper() and sample["speaker_label"] in html
        self.resultframe_is_durable = body_is_direct
        if body_is_direct:
            return "{resultframe}"
        return self.require_search_top_url()

    def build_speeches(
        self, rows: list[dict[str, Any]], source_url: str
    ) -> list[dict[str, Any]]:
        deduped: dict[tuple[str | None, str, str, str], dict[str, Any]] = {}
        for row in rows:
            key = (
                row["member_id"],
                row["speaker_label"],
                row["meeting_name"],
                row["context"],
            )
            deduped[key] = row

        speeches: list[dict[str, Any]] = []
        sorted_rows = sorted(
            deduped.values(),
            key=lambda row: (
                row["date"],
                row["meeting_name"],
                row["speaker_label"],
                row["context"],
            ),
        )
        for row in sorted_rows:
            row_source_url = (
                self.build_resultframe_url(row["speaker_label"], row["context"])
                if source_url == "{resultframe}"
                else source_url
            )
            speeches.append(
                {
                    "id": self.build_speech_id(row),
                    "member_id": row["member_id"],
                    "meeting_name": row["meeting_name"],
                    "date": row["date"],
                    "kind": "本会議",
                    "summary": None,
                    "source_url": row_source_url,
                }
            )
        return speeches

    def build_speech_id(self, row: dict[str, Any]) -> str:
        if row["member_id"]:
            speaker_slug = row["member_id"].split("--", 1)[1]
        else:
            speaker_slug = hashlib.sha1(
                row["speaker_label"].encode("utf-8")
            ).hexdigest()[:10]
        context_slug = re.sub(r"[^0-9A-Za-z]+", "-", row["context"]).strip("-").lower()
        return f"{self.council_id}--{row['date']}--{speaker_slug}--{context_slug}"

    def build_resultframe_url(self, speaker_label: str, context: str) -> str:
        code = self.require_code()
        query = urlencode(
            [
                ("Code", code),
                ("dMode", "0"),
                ("searchMode", "1"),
                ("keyMode", "10"),
                ("speaker", speaker_label),
                ("speaker1", speaker_label),
                ("eTarget", "1"),
                ("speakerMode", "1"),
                ("context", context),
            ],
            encoding="cp932",
        )
        return f"{urljoin(self.base_url, 'cgi-bin3/ResultFrame.exe')}?{query}"

    def require_code(self) -> str:
        if self.code is None:
            raise RuntimeError("Code has not been extracted")
        return self.code

    def require_search_top_url(self) -> str:
        if self.search_top_url is None:
            raise RuntimeError("search_top_url has not been built")
        return self.search_top_url

    def save_speeches(self, dry_run: bool = False) -> dict[str, Any]:
        data = self.scrape_speeches()
        if not dry_run:
            self.save_json(DATA_DIR / self.council_id / "speeches.json", data)
        return data


def normalize_name(value: str) -> str:
    value = value.translate(NAME_VARIANTS)
    value = re.sub(r"[\s\u3000]", "", value)
    value = re.sub(r"(議員|君|氏|さん)$", "", value)
    return value


def load_members(council_id: str) -> list[dict[str, Any]]:
    path = DATA_DIR / council_id / "members.json"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    members = data.get("members", [])
    if isinstance(members, list):
        return members
    return []


def extract_select_options(html: str, name: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", attrs={"name": name})
    if select is None:
        return []
    options: list[str] = []
    for option in select.find_all("option"):
        value = option.get("value")
        if isinstance(value, str) and value:
            options.append(value)
    return options


def extract_speaker1_options(html: str) -> list[str]:
    return extract_select_options(html, "speaker1")


def extract_go_context(href: str) -> str | None:
    match = re.search(r"go\('([^']+)'\)", href)
    if match:
        return match.group(1)
    return None


def extract_result_years(html: str) -> list[str]:
    years: list[str] = []
    for year in re.findall(r"changeyear\('([^']+)'\)", html):
        if year not in years:
            years.append(year)
    return years


def to_reiwa_label(year: int) -> str:
    reiwa_year = year - 2018
    if reiwa_year <= 0:
        raise ValueError(f"{year} is before the Reiwa era")
    if reiwa_year == 1:
        return "令和元年"
    return f"令和 {reiwa_year}年"


def first_meeting_on_or_after(values: list[str], target: date) -> str | None:
    dated = [(value, parse_meeting_date(value)) for value in values]
    candidates = [
        (value, meeting_date)
        for value, meeting_date in dated
        if meeting_date is not None and meeting_date >= target
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[1])[0]


def last_meeting_on_or_before(values: list[str], target: date) -> str | None:
    dated = [(value, parse_meeting_date(value)) for value in values]
    candidates = [
        (value, meeting_date)
        for value, meeting_date in dated
        if meeting_date is not None and meeting_date <= target
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1])[0]


def parse_meeting_date(value: str) -> date | None:
    year_match = re.search(r"令和\s*(元|\d+)\s*年", value)
    if year_match is None:
        return None
    year_text = year_match.group(1)
    year = 2019 if year_text == "元" else 2018 + int(year_text)
    month_day_matches = re.findall(r"(\d{1,2})月\s*(\d{1,2})日", value)
    if not month_day_matches:
        return None
    month_text, day_text = month_day_matches[-1]
    return date(year, int(month_text), int(day_text))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("council_id")
    parser.add_argument("--fiscal-start-year", type=int, default=2024)
    parser.add_argument("--fiscal-years", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    adapter = KensakuSystemLegacyMinutesAdapter(
        council_id=args.council_id,
        fiscal_start_year=args.fiscal_start_year,
        fiscal_years=args.fiscal_years,
    )
    adapter.save_speeches(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
