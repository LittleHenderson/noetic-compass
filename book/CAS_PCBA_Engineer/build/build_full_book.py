#!/usr/bin/env python3
"""One deterministic build of the full 6x9 CAS PCBA Engineer trade paperback.

Order matters and is the reason this script exists:

  1. build_book.py        assemble front_prose.md + main_body.md from the sources
  2. pandoc               markdown -> LaTeX (front_prose.tex, body.tex)
  3. postprocess_pcba.py  verbatim -> fvextra Verbatim, so long CCDL lines wrap
  4. patch_overflows.py   texttt/arrow breaking, longtable sizing, running heads
  5. build_indexes.py     insert \\index marks (needs body.tex, not the markdown)
  6. xelatex              first pass, writes manuscript_pcba.idx
  7. makeindex            .idx -> .ind  (between the passes; \\printindex needs it)
  8. xelatex  x2          resolve TOC, cross-references and index page numbers
  9. copy                 manuscript_pcba.pdf -> CAS_PCBA_Engineer[_print].pdf

Run:  python build_full_book.py [--no-index]
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
BOOK = BUILD.parent
PUBLISHING = BOOK.parent / "publishing"


def run(cmd: list[str], **kw) -> None:
    print("+", " ".join(cmd), flush=True)
    done = subprocess.run(cmd, cwd=BUILD, text=True, encoding="utf-8",
                          errors="replace", stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, **kw)
    tail = done.stdout[-2500:] if done.stdout else ""
    if done.returncode != 0:
        print(tail)
        raise SystemExit(f"failed: {' '.join(cmd)} (exit {done.returncode})")
    return done


def check_log(path: Path) -> None:
    """Fail on real LaTeX errors.

    `-interaction=nonstopmode` still writes a PDF after an error, so a green
    exit code or an existing output file proves nothing. The marker is a line
    beginning with `! `.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    errors = [ln for ln in text.splitlines() if ln.startswith("! ")]
    if errors:
        for ln in errors[:20]:
            print("  " + ln)
        raise SystemExit(f"{path.name}: {len(errors)} LaTeX error(s)")


def main() -> int:
    no_index = "--no-index" in sys.argv

    run([sys.executable, "build_book.py"])
    run(["pandoc", "front_prose.md", "-o", "front_prose.tex", "-t", "latex",
         "--top-level-division=chapter", "-f", "markdown-superscript-subscript",
         "--syntax-highlighting=none"])
    run(["pandoc", "main_body.md", "-o", "body.tex", "-t", "latex",
         "--top-level-division=chapter", "-f", "markdown-superscript-subscript",
         "--syntax-highlighting=none"])
    run([sys.executable, "postprocess_pcba.py"])
    run([sys.executable, "patch_overflows.py"])
    if not no_index:
        run([sys.executable, str(PUBLISHING / "build_indexes.py"), "pcba"])

    # longtable caches its column widths in the .aux and never shrinks them, so
    # a stale .aux keeps a narrowed table at its old width and reports
    # "Overfull \hbox ... in alignment". body.tex was just regenerated, so the
    # cache is meaningless: drop it and let pass 1 recompute.
    (BUILD / "manuscript_pcba.aux").unlink(missing_ok=True)

    run(["xelatex", "-interaction=nonstopmode", "manuscript_pcba.tex"])
    if not no_index:
        run(["makeindex", "-q", "manuscript_pcba.idx"])
    run(["xelatex", "-interaction=nonstopmode", "manuscript_pcba.tex"])
    run(["xelatex", "-interaction=nonstopmode", "manuscript_pcba.tex"])
    check_log(BUILD / "manuscript_pcba.log")

    pdf = BUILD / "manuscript_pcba.pdf"
    if not pdf.exists():
        raise SystemExit("manuscript_pcba.pdf was not produced")
    for target in ("CAS_PCBA_Engineer.pdf", "CAS_PCBA_Engineer_print.pdf"):
        shutil.copy2(pdf, BOOK / target)
        print(f"WROTE {BOOK / target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
