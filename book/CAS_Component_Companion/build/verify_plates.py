#!/usr/bin/env python3
"""Compile every inline plate and schematic figure as a standalone XeLaTeX artifact.

Reads `figures_preamble.tex` from this directory -- `companion_build.py` copies
it from the main volume's build directory so the symbol library has exactly one
source of truth.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import plates

BUILD = Path(__file__).resolve().parent
COMPANION = BUILD.parent
OUT = BUILD / "plates_verify"

TEMPLATE = r"""\documentclass[border=8pt]{standalone}
\usepackage{fontspec}
\defaultfontfeatures{Ligatures=TeX}
\setmainfont{Palatino Linotype}
\setsansfont{Arial}
\usepackage{amsmath,amssymb}
%s
\begin{document}
%s
\end{document}
"""


def main() -> int:
    styles = plates.STYLES.read_text(encoding="utf-8")
    found = plates.figures()
    labels = [m.group("label") for _, m in found]
    duplicates = sorted({l for l in labels if labels.count(l) > 1})
    if duplicates:
        print("FAIL duplicate labels:", ", ".join(duplicates))
        return 1
    OUT.mkdir(exist_ok=True)
    failed: list[str] = []
    for _, match in found:
        label = match.group("label")
        tex = OUT / f"{label}.tex"
        tex.write_text(TEMPLATE % (styles, match.group("body").strip()), encoding="utf-8")
        done = subprocess.run(
            ["xelatex", "-halt-on-error", "-interaction=nonstopmode",
             f"-output-directory={OUT}", str(tex)],
            cwd=COMPANION, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace")
        pdf = OUT / f"{label}.pdf"
        if done.returncode != 0 or not pdf.exists():
            failed.append(label)
            (OUT / f"{label}.command.log").write_text(done.stdout, encoding="utf-8")
            print(f"FAIL {label}")
        else:
            print(f"OK   {label}")
    print(f"compiled={len(found) - len(failed)} total={len(found)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
