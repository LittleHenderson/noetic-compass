"""Assemble the three reviewed answer-key parts into Appendix H."""

from __future__ import annotations

import re
from pathlib import Path


BOOK = Path(__file__).resolve().parent.parent
BUILD = BOOK / "build"
OUT = BOOK / "manuscript" / "appendix_h_exercise_answers.md"
PARTS = [
    BUILD / "appendix_h_ch01_08.md",
    BUILD / "appendix_h_ch09_16.md",
    BUILD / "appendix_h_ch17_24.md",
]


INTRO = """# APPENDIX H
## Worked Exercise Answers
*One auditable solution path for every numbered exercise*

These are worked solutions, not answer-only results. For numerical problems,
the governing equation and substitutions are shown. For diagnosis and design
problems, the answer names the invariant, the evidence, and the capability
given up by the repair.

Open-ended design exercises can admit more than one sound board. The listing
shown here is a reference solution: it must satisfy the stated constraints and
canonical CAS notation, but a different parameterization can also be correct if
its arithmetic, safety posture, and trade-offs are explicit.

Detection-only exercises remain detection-only. No answer in this appendix
turns a structural analysis of coercion into a protocol against a person.

---
"""


def main() -> int:
    missing = [path for path in PARTS if not path.exists()]
    if missing:
        for path in missing:
            print(f"MISSING ANSWER PART: {path}")
        return 1

    bodies = []
    for path in PARTS:
        text = path.read_text(encoding="utf-8").strip()
        match = re.search(r"(?m)^## Chapter \d+\s*$", text)
        if not match:
            print(f"MISSING CHAPTER HEADING IN ANSWER PART: {path}")
            return 1
        bodies.append(text[match.start():].strip())
    OUT.write_text(INTRO.rstrip() + "\n\n" + "\n\n".join(bodies) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT} from {len(PARTS)} reviewed parts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
