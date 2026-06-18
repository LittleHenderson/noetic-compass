#!/usr/bin/env python3
"""
Post-process pandoc body.tex for the CAS PCBA Engineer build.

Converts pandoc's plain `verbatim` environments (used for CAS/CCDL code blocks
and ASCII schematics) into fvextra `Verbatim` with line-breaking enabled, so
long CCDL statements and block diagrams fit the 6x9 measure instead of running
into the margin. No `commandchars` are set, so literal braces/backslashes in
code remain literal.
"""
from pathlib import Path

BODY = Path(__file__).with_name("body.tex")

OPEN_SRC = r"\begin{verbatim}"
OPEN_DST = r"\begin{Verbatim}[breaklines=true,breakanywhere=true,fontsize=\footnotesize]"
CLOSE_SRC = r"\end{verbatim}"
CLOSE_DST = r"\end{Verbatim}"


def main() -> None:
    text = BODY.read_text(encoding="utf-8")
    n_open = text.count(OPEN_SRC)
    text = text.replace(OPEN_SRC, OPEN_DST).replace(CLOSE_SRC, CLOSE_DST)
    BODY.write_text(text, encoding="utf-8")
    print(f"postprocess: converted {n_open} verbatim block(s) to breakable Verbatim")


if __name__ == "__main__":
    main()
