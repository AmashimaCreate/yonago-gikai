"""鳥取市議会 議員一覧スクレイパー.

ソース: https://www.city.tottori.lg.jp/site/shigikai/6355.html
出力: docs/data/tottori-city/members.json
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urljoin

from bs4 import Tag

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.base import CouncilScraperBase  # noqa: E402
from scripts.councils.tottori_pref import make_slug, normalize_text  # noqa: E402

COUNCIL_ID = "tottori-city"
SOURCE_URL = "https://www.city.tottori.lg.jp/site/shigikai/6355.html"
OUT_PATH = REPO_ROOT / "docs" / "data" / COUNCIL_ID / "members.json"


def split_name_kana(text: str) -> tuple[str, str]:
    m = re.match(r"^(.+?)[（(](.+?)[）)]$", normalize_text(text))
    if not m:
        return normalize_text(text), ""
    return normalize_text(m.group(1)), normalize_text(m.group(2))


def parse_elected_count(text: str) -> int | None:
    m = re.search(r"(\d+)\s*回", text)
    return int(m.group(1)) if m else None


def cell_lines(cell: Tag) -> list[str]:
    lines = [
        normalize_text(line)
        for line in cell.get_text("\n", strip=True).split("\n")
    ]
    return [line for line in lines if line]


def photo_url(cell: Tag) -> str | None:
    img = cell.find("img")
    if not img or not img.get("src"):
        return None
    return urljoin(SOURCE_URL, img["src"])


def parse_row(tr: Tag) -> dict | None:
    cells = tr.find_all(["td", "th"])
    if len(cells) < 7 or cells[0].name == "th":
        return None

    name, name_kana = split_name_kana(cells[2].get_text(" ", strip=True))
    if not name:
        return None

    committees = cell_lines(cells[5])
    slug = make_slug(name_kana)
    return {
        "id": f"{COUNCIL_ID}--{slug}",
        "council_id": COUNCIL_ID,
        "name": name,
        "name_kana": name_kana,
        "faction": normalize_text(cells[6].get_text(" ", strip=True)),
        "elected_count": parse_elected_count(cells[4].get_text(" ", strip=True)),
        "positions": [],
        "committees": committees,
        "photo_url": photo_url(cells[1]),
    }


def assign_unique_ids(members: list[dict]) -> None:
    counts: dict[str, int] = {}
    for member in members:
        base = member.get("id", "")
        n = counts.get(base, 0) + 1
        counts[base] = n
        if n > 1:
            member["id"] = f"{base}-{n}"


class TottoriCityScraper(CouncilScraperBase):
    def scrape_members(self) -> list[dict]:
        print(f"fetching {SOURCE_URL} ...")
        soup = self.fetch(SOURCE_URL)
        table = soup.find("table")
        if not table:
            raise RuntimeError("議員名簿テーブルが見つかりません")

        members = [
            member
            for tr in table.find_all("tr")
            if (member := parse_row(tr)) is not None
        ]
        assign_unique_ids(members)
        return members


def main() -> int:
    scraper = TottoriCityScraper()
    members = scraper.scrape_members()
    print(f"parsed {len(members)} members")
    scraper.assert_min_count(members, 25, "members")
    if not 25 <= len(members) <= 40:
        print(
            f"WARNING: expected 25-40 members, got {len(members)}",
            file=sys.stderr,
        )

    scraper.save_json(
        OUT_PATH,
        {
            "council_id": COUNCIL_ID,
            "source_url": SOURCE_URL,
            "acquisition": "scraping",
            "members": members,
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
