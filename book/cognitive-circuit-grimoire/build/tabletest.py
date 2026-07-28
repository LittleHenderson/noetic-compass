#!/usr/bin/env python3
"""Compile every generated longtable against the 6x9 text measure."""

from __future__ import annotations

import io
import re
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BUILD = Path(__file__).resolve().parent
BODY = BUILD / "body.tex"
OUT = BUILD / "figtest" / "table_focus"

TABLE = re.compile(
    r"(?P<marker>% grimoire-wide-table:.*?\n\\setlength\{\\tabcolsep\}\{2pt\}\n"
    r"\\renewcommand\{\\grimoiretablefont\}\{\\scriptsize\}\n)?"
    r"(?P<env>\\begin\{longtable\}\[\]\{@\{\}.*?\\end\{longtable\})",
    re.DOTALL,
)

def main() -> int:
    body = BODY.read_text(encoding="utf-8")
    tables = list(TABLE.finditer(body))
    expected = body.count(r"\begin{longtable}")
    if len(tables) != expected:
        raise SystemExit(
            f"tabletest: parsed {len(tables)} of {expected} generated longtables"
        )
    selected = [match.group(0) for match in tables]

    OUT.mkdir(parents=True, exist_ok=True)
    tex = OUT / "table_focus.tex"
    document = [
        r"\documentclass[11pt,openright,twoside]{memoir}",
        r"\makeatletter\def\input@path{{../../}}\makeatother",
        r"\input{../../preamble_grimoire.tex}",
        r"\begin{document}",
        r"\makeatletter\scriptsize\typeout{TABLETEST-SCRIPTSIZE=\f@size pt}\makeatother",
    ]
    for table in selected:
        document.extend(("{", table, r"\par\clearpage", "}"))
    document.append(r"\end{document}")
    tex.write_text("\n".join(document) + "\n", encoding="utf-8")

    for suffix in (".aux", ".log", ".out", ".pdf", ".toc"):
        tex.with_suffix(suffix).unlink(missing_ok=True)

    result = None
    for _ in range(2):
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=OUT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode:
            break
    assert result is not None
    log_path = OUT / "table_focus.log"
    log = log_path.read_text(encoding="utf-8", errors="replace")
    material = [
        float(value)
        for value in re.findall(r"Overfull \\hbox \(([0-9.]+)pt too wide\)", log)
        if float(value) > 2.0
    ]
    size = re.search(r"TABLETEST-SCRIPTSIZE=([0-9.]+)pt", log)
    print(
        f"tabletest: {len(selected)} generated longtables; "
        f"material overfull hboxes={len(material)}; "
        f"scriptsize={size.group(1) if size else 'unknown'}pt"
    )
    if result.returncode:
        print(result.stdout[-2500:])
        return result.returncode
    if material:
        print(f"tabletest: FAILED material widths={material}")
        return 1
    if not size or float(size.group(1)) < 8.0:
        print("tabletest: FAILED scriptsize is below the 8pt readability floor")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
