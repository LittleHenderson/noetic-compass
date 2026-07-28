"""Verify the chapter skeleton and safety banners required by BOOK_SPEC.md."""

from __future__ import annotations

import re
from pathlib import Path


BOOK = Path(__file__).resolve().parent.parent
MS = BOOK / "manuscript"
EXERCISE_RE = re.compile(r"(?m)^\*\*(\d+\.\d+)(?:\s|\*\*)")
FIGURE_RE = re.compile(r"\[\[FIGURE\s+\d+-[A-Z]:")


def main() -> int:
    problems: list[str] = []
    chapters: dict[int, Path] = {}
    for path in sorted(MS.glob("ch[0-2][0-9]_*.md")):
        chapter = int(path.name[2:4])
        if 1 <= chapter <= 24:
            if chapter in chapters:
                problems.append(
                    f"chapter {chapter}: duplicate canonical source "
                    f"{chapters[chapter].name}, {path.name}"
                )
            chapters[chapter] = path

    missing = sorted(set(range(1, 25)) - set(chapters))
    if missing:
        problems.append("missing canonical chapters: " + ", ".join(map(str, missing)))

    for chapter, path in sorted(chapters.items()):
        text = path.read_text(encoding="utf-8")
        bench_notes = len(re.findall(r"\bBench Note\b", text, re.I))
        figures = len(FIGURE_RE.findall(text))
        exercises = [
            item for item in EXERCISE_RE.findall(text)
            if int(item.split(".")[0]) == chapter
        ]

        if bench_notes < 2:
            problems.append(f"{path.name}: {bench_notes} Bench Notes; requires at least 2")
        if not 4 <= len(exercises) <= 8:
            problems.append(
                f"{path.name}: {len(exercises)} exercises; requires 4 through 8"
            )
        if not re.search(r"What This Chapter Established", text, re.I):
            problems.append(f"{path.name}: missing What This Chapter Established")
        if not re.search(r"\bFailure Modes?\b", text, re.I):
            problems.append(f"{path.name}: missing Failure Modes")
        if not re.search(r"\bTest Points?\b|\bTP1\b", text, re.I):
            problems.append(f"{path.name}: missing test-point coverage")

        if 6 <= chapter <= 11:
            if figures < 2:
                problems.append(
                    f"{path.name}: {figures} figures; Part II requires at least 2"
                )
            if not re.search(
                r"(?:Component|Parameter).{0,24}Table|^### .*Parameters",
                text,
                re.I | re.M,
            ):
                problems.append(f"{path.name}: missing component/parameter table")

        if 12 <= chapter <= 20:
            if figures < 3:
                problems.append(
                    f"{path.name}: {figures} figures; Part III requires at least 3"
                )
            if not re.search(r"(?m)^board\s+\w+\s*\{", text):
                problems.append(f"{path.name}: missing full CCDL board listing")
            if not re.search(r"\bWorked Example\b", text, re.I):
                problems.append(f"{path.name}: missing worked example")
            if not (
                re.search(r"(?:Component|Parameter).{0,24}Table", text, re.I)
                or re.search(r"(?m)^\|\s*Ref\s*\|", text)
            ):
                problems.append(f"{path.name}: missing component/parameter table")

        if chapter in {15, 16, 17, 18, 19}:
            if not (
                "DETECTION-ONLY" in text
                and ("DO NOT BUILD" in text or "NOT A BUILD LISTING" in text)
            ):
                problems.append(f"{path.name}: missing required detection-only banner")

    print(f"canonical chapters : {len(chapters)}/24")
    print(f"structure problems : {len(problems)}")
    for problem in problems:
        print(f"  {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
