"""Print the prose tail of each plate chapter, so it can be replaced surgically.

The LaTeX figure blocks are verified geometry; the prose around them is what
changes when the guide is re-aimed at human experience. This prints everything
after each `\\end{figure}` so the replacement text can be matched exactly.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOOK = HERE.parent

for i in range(1, 12):
    for p in sorted(BOOK.glob(f"{i:02d}_*.md")):
        text = p.read_text(encoding="utf-8")
        if "\\end{figure}" in text:
            tail = text.split("\\end{figure}", 1)[1]
            print(f"\n===== {p.name} =====")
            print(tail.strip()[:1400])
