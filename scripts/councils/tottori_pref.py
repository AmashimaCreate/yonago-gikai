"""鳥取県議会 議員一覧スクレイパー.

ソース: https://www.pref.tottori.lg.jp/75928.htm
出力: docs/data/tottori-pref/members.json
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import Tag

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.base import CouncilScraperBase  # noqa: E402

COUNCIL_ID = "tottori-pref"
SOURCE_URL = "https://www.pref.tottori.lg.jp/75928.htm"
OUT_PATH = REPO_ROOT / "docs" / "data" / COUNCIL_ID / "members.json"

FACTIONS = {"自由民主党", "民主とっとり", "公明党", "無所属"}

HIRAGANA_TO_ROMAJI: dict[str, str] = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "を": "wo", "ん": "n",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
}
COMPOUND_HIRAGANA: dict[str, str] = {
    "きゃ": "kya", "きゅ": "kyu", "きょ": "kyo",
    "ぎゃ": "gya", "ぎゅ": "gyu", "ぎょ": "gyo",
    "しゃ": "sha", "しゅ": "shu", "しょ": "sho",
    "じゃ": "ja", "じゅ": "ju", "じょ": "jo",
    "ちゃ": "cha", "ちゅ": "chu", "ちょ": "cho",
    "にゃ": "nya", "にゅ": "nyu", "にょ": "nyo",
    "ひゃ": "hya", "ひゅ": "hyu", "ひょ": "hyo",
    "びゃ": "bya", "びゅ": "byu", "びょ": "byo",
    "ぴゃ": "pya", "ぴゅ": "pyu", "ぴょ": "pyo",
    "みゃ": "mya", "みゅ": "myu", "みょ": "myo",
    "りゃ": "rya", "りゅ": "ryu", "りょ": "ryo",
}


def normalize_text(s: str | None) -> str:
    if s is None:
        return ""
    s = s.replace(" ", " ").replace("　", " ")
    return re.sub(r"\s+", " ", s).strip()


def make_slug(kana: str) -> str:
    if not kana:
        return ""
    s = kana.strip()
    out: list[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in (" ", "　"):
            out.append("-")
            i += 1
            continue
        if i + 1 < len(s) and s[i : i + 2] in COMPOUND_HIRAGANA:
            out.append(COMPOUND_HIRAGANA[s[i : i + 2]])
            i += 2
            continue
        if ch in HIRAGANA_TO_ROMAJI:
            out.append(HIRAGANA_TO_ROMAJI[ch])
        i += 1
    return "".join(out).strip("-")


def split_name_kana(text: str) -> tuple[str, str]:
    m = re.match(r"^(.+?)（(.+?)）$", normalize_text(text))
    if not m:
        return normalize_text(text), ""
    return normalize_text(m.group(1)), normalize_text(m.group(2))


def append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def parse_member(title: Tag, status: Tag | None) -> dict:
    link = title.find("a")
    name, name_kana = split_name_kana(link.get_text(" ", strip=True) if link else "")
    faction = ""
    committees: list[str] = []

    if status:
        for a in status.find_all("a"):
            category = normalize_text(a.get_text(" ", strip=True))
            if category.endswith("選挙区"):
                continue
            if category in FACTIONS:
                faction = category
                continue
            if "委員会" in category:
                append_unique(committees, category)

    slug = make_slug(name_kana)
    return {
        "id": f"{COUNCIL_ID}--{slug}",
        "council_id": COUNCIL_ID,
        "name": name,
        "name_kana": name_kana,
        "faction": faction,
        "elected_count": None,
        "positions": [],
        "committees": committees,
        "photo_url": None,
    }


def assign_unique_ids(members: list[dict]) -> None:
    counts: dict[str, int] = {}
    for member in members:
        base = member.get("id", "")
        n = counts.get(base, 0) + 1
        counts[base] = n
        if n > 1:
            member["id"] = f"{base}-{n}"


class TottoriPrefScraper(CouncilScraperBase):
    def scrape_members(self) -> list[dict]:
        print(f"fetching {SOURCE_URL} ...")
        soup = self.fetch(SOURCE_URL)
        blog = soup.find(id="moduleid155189")
        if not blog:
            raise RuntimeError("議員名簿ブログ領域が見つかりません")

        members: list[dict] = []
        for title in soup.find_all("h2", class_="Title"):
            status = title.find_next_sibling("p", class_="Status")
            member = parse_member(title, status)
            if member["name"]:
                members.append(member)

        assign_unique_ids(members)
        return members


def main() -> int:
    scraper = TottoriPrefScraper()
    members = scraper.scrape_members()
    print(f"parsed {len(members)} members")
    scraper.assert_min_count(members, 30, "members")
    if not 30 <= len(members) <= 40:
        print(
            f"WARNING: expected 30-40 members, got {len(members)}",
            file=sys.stderr,
        )

    scraper.save_json(
        OUT_PATH,
        {
            "council_id": COUNCIL_ID,
            "source_url": SOURCE_URL,
            "members": members,
        },
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
