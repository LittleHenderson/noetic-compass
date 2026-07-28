"""Catch stale chapter numbers and mis-lettered appendix section headings."""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


BOOK = Path(__file__).resolve().parent.parent
MS = BOOK / "manuscript"
NUMBERED_REF_LIST = re.compile(
    r"\b(?:Chapters?|Chs?\.?|Sections?)\s+"
    r"(\d+(?:\.\d+)?(?:"
    r"(?:[ \t]*,[ \t]*(?:and[ \t]+)?|[ \t]+and[ \t]+|[–—-])"
    r"\d+(?:\.\d+)?"
    r")*)",
    re.I,
)
STALE_REF_NEAR_PREFIX = re.compile(
    r"\b(?:Chapters?|Chs?\.?|Sections?)\b[^\n]{0,180}"
    r"\b(?:25|26)\.\d+\b",
    re.I,
)
SECTION_SIGN_REF = re.compile(r"§\s*(\d+)(?:\.(\d+))?")
BARE_STALE_REF = re.compile(r"\((?:2[5-9]|[3-9]\d)\.\d+\)")
APPENDIX_HEADING = re.compile(r"(?m)^#{2,3}\s+([A-M])\.(\d+)")
APPENDIX_REF = re.compile(
    r"\b(?:Appendix|App\.)\s+([A-M])(?:,)?"
    r"(?:\s+§\s*([A-M])\.(\d+))?"
)
APPENDIX_SIGN_REF = re.compile(r"§\s*([A-M])\.(\d+)")
EDITORIAL_MARKER = re.compile(r"\[\[(?!FIGURE\b)")
STALE_PART_REF = re.compile(r"\bPart\s+V\b", re.I)


def source_paths() -> list[Path]:
    paths = set(MS.glob("ch[0-2][0-9]_*.md"))
    paths.update(MS.glob("appendix_*.md"))
    for name in (
        "00_title_page.md",
        "01_table_of_contents.md",
        "02_preface.md",
        "03_how_to_use.md",
        "04_quickstart.md",
        "about_the_author.md",
    ):
        path = MS / name
        if path.exists():
            paths.add(path)
    return sorted(paths)


def main() -> int:
    problems: list[str] = []
    paths = source_paths()
    chapter_sections: set[str] = set()
    appendix_sections: set[str] = set()
    for path in paths:
        text = path.read_text(encoding="utf-8")
        chapter_sections.update(re.findall(
            r"(?m)^#{2,4}\s+(\d+\.\d+)\b", text
        ))
        appendix_sections.update(
            f"{letter}.{number}"
            for letter, number in APPENDIX_HEADING.findall(text)
        )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in EDITORIAL_MARKER.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            problems.append(
                f"{path.name}:{line}: unresolved editorial marker"
            )

        for match in STALE_PART_REF.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            problems.append(
                f"{path.name}:{line}: stale Part V reference; the book has four parts"
            )

        for match in NUMBERED_REF_LIST.finditer(text):
            numbers = re.findall(r"\d+(?:\.\d+)?", match.group(1))
            if any(int(number.split(".")[0]) > 24 for number in numbers):
                line = text.count("\n", 0, match.start()) + 1
                problems.append(
                    f"{path.name}:{line}: out-of-range chapter reference "
                    f"{match.group(0)!r}"
                )
            for number in numbers:
                if "." in number and number not in chapter_sections:
                    line = text.count("\n", 0, match.start()) + 1
                    problems.append(
                        f"{path.name}:{line}: unresolved chapter section "
                        f"{number!r} in {match.group(0)!r}"
                    )

        for pattern in (STALE_REF_NEAR_PREFIX, BARE_STALE_REF):
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                problems.append(
                    f"{path.name}:{line}: stale numbered reference "
                    f"{match.group(0)!r}"
                )

        for match in SECTION_SIGN_REF.finditer(text):
            chapter = int(match.group(1))
            if chapter > 24:
                line = text.count("\n", 0, match.start()) + 1
                problems.append(
                    f"{path.name}:{line}: stale numbered reference "
                    f"{match.group(0)!r}"
                )
                continue
            section = (f"{match.group(1)}.{match.group(2)}"
                       if match.group(2) else None)
            if section and section not in chapter_sections:
                line = text.count("\n", 0, match.start()) + 1
                problems.append(
                    f"{path.name}:{line}: unresolved chapter section {section!r}"
                )

        for match in APPENDIX_REF.finditer(text):
            appendix, section_letter, number = match.groups()
            if section_letter and appendix != section_letter:
                line = text.count("\n", 0, match.start()) + 1
                problems.append(
                    f"{path.name}:{line}: appendix/section mismatch "
                    f"{match.group(0)!r}"
                )
            if section_letter and f"{section_letter}.{number}" not in appendix_sections:
                line = text.count("\n", 0, match.start()) + 1
                problems.append(
                    f"{path.name}:{line}: unresolved appendix section "
                    f"{section_letter}.{number}"
                )

        for match in APPENDIX_SIGN_REF.finditer(text):
            section = f"{match.group(1)}.{match.group(2)}"
            if section not in appendix_sections:
                line = text.count("\n", 0, match.start()) + 1
                problems.append(
                    f"{path.name}:{line}: unresolved appendix section {section!r}"
                )

        if path.name.startswith("appendix_"):
            expected = path.name[len("appendix_")].upper()
            for match in APPENDIX_HEADING.finditer(text):
                if match.group(1) != expected:
                    line = text.count("\n", 0, match.start()) + 1
                    problems.append(
                        f"{path.name}:{line}: section {match.group(0)!r} "
                        f"should use prefix {expected}."
                    )

    print(f"cross-reference problems: {len(problems)}")
    for problem in problems:
        print(f"  {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
