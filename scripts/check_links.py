#!/usr/bin/env python3
"""Check official council links used by the public site."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
COUNCILS_PATH = REPO_ROOT / "councils.json"
USER_AGENT = "Mozilla/5.0 (compatible; tottori-mieru-link-check/1.0)"
TIMEOUT = 20


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_links(councils: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    links: list[tuple[str, str, str]] = []
    for council in councils:
        council_id = str(council.get("id") or "unknown")
        for key in ("votes_official_url", "minutes_base_url"):
            url = council.get(key)
            if isinstance(url, str) and url.startswith("https://"):
                links.append((council_id, key, url))
        for i, link in enumerate(council.get("official_links") or []):
            if not isinstance(link, dict):
                continue
            url = link.get("url")
            label = link.get("label") or f"official_links[{i}]"
            if isinstance(url, str) and url.startswith("https://"):
                links.append((council_id, str(label), url))
    return links


def request_status(url: str, method: str) -> int:
    request = urllib.request.Request(
        url,
        method=method,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return int(response.status)


def check_link(url: str) -> tuple[bool, str]:
    try:
        status = request_status(url, "HEAD")
    except urllib.error.HTTPError as exc:
        if exc.code in {403, 405, 501}:
            try:
                status = request_status(url, "GET")
            except Exception as get_exc:  # noqa: BLE001
                return False, f"GET failed after HEAD {exc.code}: {get_exc}"
        else:
            status = exc.code
    except Exception as exc:  # noqa: BLE001
        try:
            status = request_status(url, "GET")
        except Exception as get_exc:  # noqa: BLE001
            return False, f"HEAD/GET failed: {exc}; {get_exc}"

    if 400 <= status:
        return False, f"HTTP {status}"
    return True, f"HTTP {status}"


def main() -> int:
    councils = load_json(COUNCILS_PATH).get("councils", [])
    if not isinstance(councils, list):
        print("councils.json: councils must be a list", file=sys.stderr)
        return 1

    failures: list[str] = []
    for council_id, label, url in collect_links(councils):
        ok, message = check_link(url)
        print(f"{council_id} {label}: {message} {url}")
        if not ok:
            failures.append(f"{council_id} {label}: {message} {url}")

    if failures:
        print("Link check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
