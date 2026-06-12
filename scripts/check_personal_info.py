#!/usr/bin/env python3
"""Check generated JSON for accidental personal/contact information.

The project intentionally avoids collecting individual contact details or
private profile fields. This checker focuses on actual contact-info shapes
instead of broad words such as "メール", which can appear in bill titles.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


FORM_PATTERNS = [
    ("email address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    (
        "phone number",
        re.compile(r"0\d{1,4}[-−(（]\d{1,4}[-−)）]\d{3,4}"),
    ),
    ("postal code", re.compile(r"〒?\d{3}[-−]\d{4}")),
]

KEY_PATTERN = re.compile(
    r"(?:^|_)(?:tel|telephone|phone|fax|email|e[-_]?mail|mail_address|address|birth|birthday|date_of_birth)(?:$|_)",
    re.IGNORECASE,
)

VALUE_WORD_PATTERN = re.compile(
    r"生年月日|自宅住所|住所氏名|電話番号|メールアドレス|ファクシミリ番号|FAX番号",
    re.IGNORECASE,
)


def json_pointer(parts: list[str]) -> str:
    if not parts:
        return "/"
    escaped = [part.replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(escaped)


def iter_json_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def scan_value(value: str, path: Path, pointer: str) -> list[str]:
    findings = []
    for label, pattern in FORM_PATTERNS:
        match = pattern.search(value)
        if match:
            findings.append(f"{path}:{pointer}: {label}: {match.group(0)}")
    match = VALUE_WORD_PATTERN.search(value)
    if match:
        findings.append(f"{path}:{pointer}: restricted word: {match.group(0)}")
    return findings


def scan_node(node: Any, path: Path, pointer_parts: list[str]) -> list[str]:
    findings: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            child_parts = [*pointer_parts, str(key)]
            if KEY_PATTERN.search(str(key)):
                findings.append(f"{path}:{json_pointer(child_parts)}: restricted key: {key}")
            findings.extend(scan_node(value, path, child_parts))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            findings.extend(scan_node(value, path, [*pointer_parts, str(index)]))
    elif isinstance(node, str):
        findings.extend(scan_value(node, path, json_pointer(pointer_parts)))
    return findings


def scan_file(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]
    return scan_node(data, path, [])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", default=["docs/data"])
    args = parser.parse_args()

    findings: list[str] = []
    for target in args.paths:
        for path in iter_json_files(Path(target)):
            findings.extend(scan_file(path))

    if findings:
        print("Personal/contact info check failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
