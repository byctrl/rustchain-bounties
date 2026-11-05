#!/usr/bin/env python3
"""Sanity-check a BoTTube 3-replies bounty claim file.

Validates the claim markdown against the issue rules:
  - 3 replies, each on a different video
  - each reply body is 10+ words
  - each reply has a reply URL filled in

Usage:
    python3 claims/bottube-comments-3-replies-check.py claims/<claim>.md

Exit code 0 = pass, 1 = rule violation found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MIN_WORDS = 10
EXPECTED_REPLIES = 3

REPLY_HEADING = re.compile(r"^###\s+Reply\s+(\d+)\b", re.MULTILINE)
VIDEO_LINE = re.compile(r"^-\s*Video:\s*(\S+)\s*$", re.MULTILINE)
URL_LINE = re.compile(r"^-\s*Reply URL:\s*(.+?)\s*$", re.MULTILINE)
QUOTE_BLOCK = re.compile(r"^>\s?(.*)$", re.MULTILINE)
PLACEHOLDER = re.compile(r"<[^>\n]*>")


def split_replies(text: str) -> list[str]:
    starts = [m.start() for m in REPLY_HEADING.finditer(text)]
    blocks = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        blocks.append(text[start:end])
    return blocks


def reply_body(block: str) -> str:
    lines = [line.strip() for line in QUOTE_BLOCK.findall(block)]
    return " ".join(part for part in lines if part)


def check(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    blocks = split_replies(text)

    if len(blocks) != EXPECTED_REPLIES:
        errors.append(
            f"expected {EXPECTED_REPLIES} reply sections, found {len(blocks)}"
        )

    videos: list[str] = []
    for index, block in enumerate(blocks, start=1):
        video_match = VIDEO_LINE.search(block)
        if not video_match:
            errors.append(f"reply {index}: missing '- Video:' line")
        else:
            videos.append(video_match.group(1))

        url_match = URL_LINE.search(block)
        raw_url = url_match.group(1) if url_match else ""
        if not url_match or not raw_url or PLACEHOLDER.search(raw_url):
            errors.append(f"reply {index}: reply URL not filled in")
        elif not raw_url.startswith("http"):
            errors.append(f"reply {index}: reply URL is not an http(s) link")

        body = reply_body(block)
        words = [w for w in body.split() if any(c.isalnum() for c in w)]
        if not words:
            errors.append(f"reply {index}: empty reply body")
        elif len(words) < MIN_WORDS:
            errors.append(
                f"reply {index}: reply body has {len(words)} words, "
                f"needs {MIN_WORDS}+"
            )

    if len(videos) == EXPECTED_REPLIES and len(set(videos)) != EXPECTED_REPLIES:
        errors.append("replies must target 3 different videos, found duplicates")

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip())
        return 1

    path = Path(argv[1])
    if not path.is_file():
        print(f"not a file: {path}")
        return 1

    errors = check(path)
    if errors:
        print(f"FAIL {path}")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"PASS {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
