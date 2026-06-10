"""Common scraper utilities for council data sources."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


class CouncilScraperBase:
    """Base class for per-council scrapers.

    Subclasses should implement methods such as ``scrape_members`` and use
    ``fetch`` / ``save_json`` for consistent request and output behavior.
    """

    user_agent = (
        "tottori-mieru-scraper/0.1 "
        "(+https://github.com/amashimacreate/yonago-gikai; civic-tech)"
    )
    request_timeout = 30
    sleep_seconds = 2

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def fetch(self, url: str) -> BeautifulSoup:
        """Fetch a URL and return a BeautifulSoup document."""
        resp = self.session.get(url, timeout=self.request_timeout)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        time.sleep(self.sleep_seconds)
        return BeautifulSoup(resp.text, "html.parser")

    def assert_min_count(self, items: list[Any], n: int, label: str) -> None:
        """Abort when a parsed list is too small to be trusted."""
        if len(items) < n:
            print(
                f"ERROR: parsed only {len(items)} {label}; expected at least {n}",
                file=sys.stderr,
            )
            raise SystemExit(1)

    def save_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON with a UTC updated_at timestamp."""
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(data)
        payload["updated_at"] = datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        )
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"wrote {path}")
