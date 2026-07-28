#!/usr/bin/env python3
"""
Post-process pandoc body.tex for the CAS PCBA Engineer build.

Converts pandoc's plain `verbatim` environments (used for CAS/CCDL code blocks
and ASCII schematics) into fvextra `Verbatim` with line-breaking enabled, so
long CCDL statements and block diagrams fit the 6x9 measure instead of running
into the margin. No `commandchars` are set, so literal braces/backslashes in
code remain literal.
"""
import re
from pathlib import Path

BODY = Path(__file__).with_name("body.tex")

OPEN_SRC = r"\begin{verbatim}"
OPEN_DST = r"\begin{Verbatim}[breaklines=true,breakanywhere=true,fontsize=\footnotesize]"
CLOSE_SRC = r"\end{verbatim}"
CLOSE_DST = r"\end{Verbatim}"

# Register notation (|T, |A, |f, |E) must be written "\|" in the Markdown so the
# pipe does not split a table cell. Pandoc faithfully renders that escape as a
# literal backslash, so the printed book showed "\|A" instead of "|A" — including
# in the Appendix A quick-reference card that teaches the notation. Strip the
# backslash here, after pandoc, so the Markdown tables stay valid.
PIPE_LEAK = re.compile(r"\\textbackslash\{\}(?=\\textbar\{\})")


def main() -> None:
    text = BODY.read_text(encoding="utf-8")
    n_open = text.count(OPEN_SRC)
    text = text.replace(OPEN_SRC, OPEN_DST).replace(CLOSE_SRC, CLOSE_DST)

    text, n_pipes = PIPE_LEAK.subn("", text)

    BODY.write_text(text, encoding="utf-8")
    print(f"postprocess: converted {n_open} verbatim block(s) to breakable Verbatim")
    print(f"postprocess: removed {n_pipes} leaked register-pipe backslash(es)")

    remaining = len(re.findall(r"\\textbackslash\{\}\\textbar\{\}", text))
    if remaining:
        raise SystemExit(f"postprocess: FAILED — {remaining} leaked '\\|' remain in body.tex")


if __name__ == "__main__":
    main()
