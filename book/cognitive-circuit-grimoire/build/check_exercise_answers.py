"""Verify that Appendix H answers every numbered chapter exercise exactly once."""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path


BOOK = Path(__file__).resolve().parent.parent
MS = BOOK / "manuscript"
ANSWER_FILE = MS / "appendix_h_exercise_answers.md"

QUESTION_RE = re.compile(r"(?m)^\*\*(\d+\.\d+)(?:\s|\*\*)")
ANSWER_RE = re.compile(r"(?m)^###\s+H\.(\d+\.\d+)\b")
CHAPTER_RE = re.compile(r"(?m)^##\s+Chapter\s+(\d+)\s*$")
FENCE_RE = re.compile(r"(?m)^```")
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|TBD|FIXME|PLACEHOLDER)\b|left to (?:the )?reader",
    re.I,
)
MIN_ANSWER_CHARS = 120


def numeric_key(item: str) -> tuple[int, int]:
    chapter, exercise = item.split(".")
    return int(chapter), int(exercise)


def main() -> int:
    expected: list[str] = []
    for path in sorted(MS.glob("ch[0-2][0-9]_*.md")):
        chapter = int(path.name[2:4])
        ids = QUESTION_RE.findall(path.read_text(encoding="utf-8"))
        expected.extend(item for item in ids if int(item.split(".")[0]) == chapter)

    if not ANSWER_FILE.exists():
        print(f"MISSING: {ANSWER_FILE}")
        print(f"expected answer count: {len(expected)}")
        return 1

    answer_text = ANSWER_FILE.read_text(encoding="utf-8")
    answer_matches = list(ANSWER_RE.finditer(answer_text))
    found = [match.group(1) for match in answer_matches]
    counts = Counter(found)
    missing = sorted(set(expected) - set(found), key=numeric_key)
    extra = sorted(set(found) - set(expected), key=numeric_key)
    duplicate = sorted((key for key, count in counts.items() if count > 1),
                       key=numeric_key)
    out_of_order = found != expected

    short: list[tuple[str, int]] = []
    placeholder: list[str] = []
    for index, match in enumerate(answer_matches):
        end = (answer_matches[index + 1].start()
               if index + 1 < len(answer_matches) else len(answer_text))
        body = answer_text[match.end():end].strip()
        answer_id = match.group(1)
        if len(body) < MIN_ANSWER_CHARS:
            short.append((answer_id, len(body)))
        if PLACEHOLDER_RE.search(body):
            placeholder.append(answer_id)

    chapters = [int(value) for value in CHAPTER_RE.findall(answer_text)]
    missing_chapters = sorted(set(range(1, 25)) - set(chapters))
    duplicate_chapters = sorted(
        chapter for chapter, count in Counter(chapters).items() if count > 1
    )
    odd_fence_count = len(FENCE_RE.findall(answer_text)) % 2

    print(f"chapter exercises : {len(expected)}")
    print(f"answer headings   : {len(found)}")
    print(f"missing           : {len(missing)}")
    print(f"extra             : {len(extra)}")
    print(f"duplicate         : {len(duplicate)}")
    print(f"out of order      : {int(out_of_order)}")
    print(f"short answers     : {len(short)} (< {MIN_ANSWER_CHARS} chars)")
    print(f"placeholder text  : {len(placeholder)}")
    print(f"chapter headings  : {len(chapters)}")
    print(f"unclosed fences   : {odd_fence_count}")

    for label, values in (
        ("MISSING", missing),
        ("EXTRA", extra),
        ("DUPLICATE", duplicate),
        ("PLACEHOLDER", placeholder),
    ):
        if values:
            print(f"{label}: {', '.join(values)}")

    if short:
        print("SHORT: " + ", ".join(
            f"{answer_id} ({size})" for answer_id, size in short
        ))
    if missing_chapters:
        print("MISSING CHAPTER HEADINGS: " + ", ".join(map(str, missing_chapters)))
    if duplicate_chapters:
        print("DUPLICATE CHAPTER HEADINGS: " + ", ".join(map(str, duplicate_chapters)))

    problems = (
        missing
        or extra
        or duplicate
        or out_of_order
        or short
        or placeholder
        or missing_chapters
        or duplicate_chapters
        or chapters != list(range(1, 25))
        or odd_fence_count
        or len(found) != len(expected)
    )
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
