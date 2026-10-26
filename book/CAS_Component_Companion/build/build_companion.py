#!/usr/bin/env python3
"""One deterministic build of *The Component Companion* (6x9 trade paperback).

Order matters and is the reason this script exists:

  1. companion_build.py   copy the symbol library, write the preamble,
                          assemble front_prose.md + main_body.md
  2. pandoc               markdown -> LaTeX (front_prose.tex, body.tex)
  3. postprocess          verbatim -> fvextra Verbatim, so long lines wrap
  4. patch_overflows.py   running heads, table columns, texttt breaking
                          (the main volume's pass, run against this body.tex)
  5. xelatex  x2          resolve TOC and cross-references
  6. verify               fail on any log line beginning with "! "
  7. copy                 companion.pdf -> ../CAS_Component_Companion.pdf

Run:  python build_companion.py [--no-cards]
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import plates

BUILD = plates.BUILD
BOOK = plates.COMPANION
PCBA_BUILD = plates.STYLES_SOURCE.parent

OPEN_SRC = r"\begin{verbatim}"
OPEN_DST = r"\begin{Verbatim}[breaklines=true,breakanywhere=true,fontsize=\footnotesize]"
CLOSE_SRC = r"\end{verbatim}"
CLOSE_DST = r"\end{Verbatim}"
PIPE_LEAK = re.compile(r"\\textbackslash\{\}(?=\\textbar\{\})")


def run(cmd: list[str], **kw) -> None:
    print("+", " ".join(cmd), flush=True)
    done = subprocess.run(cmd, cwd=BUILD, text=True, encoding="utf-8",
                          errors="replace", stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, **kw)
    if done.returncode != 0:
        print((done.stdout or "")[-2500:])
        raise SystemExit(f"failed: {' '.join(cmd)} (exit {done.returncode})")


def postprocess() -> None:
    """cwd-relative equivalent of the main volume's postprocess step.

    The main volume's copy of this resolves body.tex next to *itself*, so it
    cannot be reused here without editing the other book's body.
    """
    body = BUILD / "body.tex"
    text = body.read_text(encoding="utf-8")
    n_open = text.count(OPEN_SRC)
    text = text.replace(OPEN_SRC, OPEN_DST).replace(CLOSE_SRC, CLOSE_DST)
    text, n_pipes = PIPE_LEAK.subn("", text)
    body.write_text(text, encoding="utf-8")
    print(f"postprocess: {n_open} verbatim block(s), {n_pipes} leaked pipe(s)")


def check_log(path: Path) -> None:
    """Fail on real LaTeX errors.

    `-interaction=nonstopmode` still writes a PDF after an error, so a green
    exit code or an existing output file proves nothing. The marker is a line
    beginning with `! `.
    """
    errors = [ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
              if ln.startswith("! ")]
    if errors:
        for ln in errors[:20]:
            print("  " + ln)
        raise SystemExit(f"{path.name}: {len(errors)} LaTeX error(s)")


def main() -> int:
    run([sys.executable, "companion_build.py"])
    run(["pandoc", "front_prose.md", "-o", "front_prose.tex", "-t", "latex",
         "--top-level-division=chapter", "-f", "markdown-superscript-subscript",
         "--syntax-highlighting=none"])
    run(["pandoc", "main_body.md", "-o", "body.tex", "-t", "latex",
         "--top-level-division=chapter", "-f", "markdown-superscript-subscript",
         "--syntax-highlighting=none"])
    postprocess()
    # The main volume's layout pass is cwd-relative, so it edits THIS body.tex.
    run([sys.executable, str(PCBA_BUILD / "patch_overflows.py")])

    (BUILD / "companion.aux").unlink(missing_ok=True)
    run(["xelatex", "-interaction=nonstopmode", "companion.tex"])
    run(["xelatex", "-interaction=nonstopmode", "companion.tex"])
    check_log(BUILD / "companion.log")

    pdf = BUILD / "companion.pdf"
    if not pdf.exists():
        raise SystemExit("companion.pdf was not produced")
    shutil.copy2(pdf, BOOK / "CAS_Component_Companion.pdf")
    print(f"WROTE {BOOK / 'CAS_Component_Companion.pdf'}")

    if "--no-cards" not in sys.argv:
        run([sys.executable, "build_cards.py"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
