#!/usr/bin/env python3
r"""
Repoint every in-text reference to STYLE_GUIDE.md at something the reader has.

STYLE_GUIDE.md says of itself "It is an internal authoring reference, not a
chapter of the book. Do not ship it." It is correctly excluded from the build --
and sixteen lines then sent the reader to it anyway, two of them to numbered
sections (§4, §5) that no shipped page contains.

Targets, chosen by what each site actually needs:
  notation and anti-drift naming rules  -> Chapter 2 / Appendix A
  component and CCDL syntax (§5)        -> Appendix C
  the Fisher-Rao gain metric (§4)       -> Chapter 9
  self-references inside Appendix C     -> that appendix's own forms
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BOOK = Path(__file__).resolve().parent.parent

# ordered: most specific first
SUBS = [
    (r"\(style guide §4\)", "(Chapter 9)"),
    (r"\(style guide §5\)", "(Appendix C)"),
    (r"§5 of the style guide", "Appendix C"),
    (r"§4 of the style guide", "Chapter 9"),
    (r"the style guide's", "Appendix C's"),
    (r"Chapter 2 and the style guide", "Chapter 2 and Appendix A"),
    (r"Chapter 3 and the style reference", "Chapter 3 and Appendix A"),
    (r"the naming rule from the style guide", "the naming rule from Chapter 2"),
    (r"The style guide flags", "Appendix A flags"),
    (r"the style reference", "Appendix A"),
    (r"the style guide", "Appendix A"),
    (r"style guide", "Appendix A"),
]


def main() -> None:
    total = 0
    for p in sorted(BOOK.glob("*.md")):
        if p.name == "STYLE_GUIDE.md":
            continue
        text = p.read_text(encoding="utf-8")
        before = text
        n = 0
        for pat, rep in SUBS:
            text, k = re.subn(pat, rep, text)
            n += k
        if text != before:
            p.write_text(text, encoding="utf-8")
            print(f"  {p.name[:46]:48s} {n} retargeted")
            total += n
    print(f"\n{total} references repointed")

    left = 0
    for p in BOOK.glob("*.md"):
        if p.name == "STYLE_GUIDE.md":
            continue
        left += len(re.findall(r"style guide|style reference",
                               p.read_text(encoding="utf-8"), re.I))
    print(f"remaining references to the unshipped style guide: {left}")
    if left:
        raise SystemExit("fix_styleguide_refs: some references remain")


if __name__ == "__main__":
    main()
