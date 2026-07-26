#!/usr/bin/env python3
r"""
Render every book figure to PNG so the EPUB editions carry them.

All three books embed figures as raw LaTeX (TikZ / pgfplots) for the print
build. Pandoc's EPUB writer drops raw LaTeX, so without this the ebooks ship
with no figures -- which, for a set of books whose most-cited weakness was
"no figures", would be the same defect wearing a different file extension.

Each figure is compiled standalone against its own book's figure preamble,
because the three books have different style vocabularies (PCBA has a domain
palette plus pgfplots; TKS has its own World colours; TiCA has a third set).

Output: <book>/figures/fig-<label>.png at 300 DPI.
build_epubs.py already swaps \begin{figure}...\label{fig:X}...\end{figure}
for ![caption](figures/fig-X.png), so nothing else has to change.
"""
import io
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent          # .../book

FIGURE = re.compile(
    r"\\begin\{figure\}(?:\[[^\]]*\])?\s*(?P<body>.*?)"
    r"\\caption\{(?P<cap>.*?)\}\\label\{fig:(?P<lab>[^}]+)\}\s*\\end\{figure\}",
    re.S)

DOC = r"""\documentclass[border=8pt]{standalone}
\usepackage{fontspec}
\defaultfontfeatures{Ligatures=TeX}
\setmainfont{Palatino Linotype}
\setsansfont{Arial}
\usepackage{amsmath,amssymb}
%(styles)s
\begin{document}
%(body)s
\end{document}
"""


def styles_for(book):
    """Preamble-safe style block for one book."""
    if book == "pcba":
        src = ROOT / "CAS_PCBA_Engineer" / "build" / "figures_preamble.tex"
        return src.read_text(encoding="utf-8")
    if book == "tks":
        # colours are injected into the generated preamble by build_book.py
        gen = ROOT / "superiority_of_tks" / "build" / "preamble_tks.tex"
        t = gen.read_text(encoding="utf-8") if gen.exists() else ""
        keep = [l for l in t.splitlines()
                if l.startswith("\\definecolor{tks")
                or l.startswith("\\usetikzlibrary")]
        return "\\usepackage{tikz}\n" + "\n".join(keep)
    raise ValueError(book)


SOURCES = {
    "pcba": (ROOT / "CAS_PCBA_Engineer",
             sorted(list((ROOT / "CAS_PCBA_Engineer").glob("Chapter_*.md"))
                    + list((ROOT / "CAS_PCBA_Engineer").glob("Appendix_*.md")))),
    "tks": (ROOT / "superiority_of_tks",
            [ROOT / "superiority_of_tks" / "MANUSCRIPT.md"]),
}


def render(book, outdir, work, styles, label, body):
    tex = DOC % {"styles": styles, "body": body}
    src = work / f"{label}.tex"
    src.write_text(tex, encoding="utf-8")
    subprocess.run(["xelatex", "-interaction=nonstopmode",
                    f"-output-directory={work}", str(src)],
                   capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
    pdf = work / f"{label}.pdf"
    if not pdf.exists():
        return None
    png = outdir / f"fig-{label}"
    subprocess.run(["pdftoppm", "-png", "-r", "300", "-singlefile",
                    str(pdf), str(png)],
                   capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
    final = png.with_suffix(".png")
    return final if final.exists() else None


def main():
    if not shutil.which("xelatex"):
        sys.exit("xelatex not found")
    grand = 0
    for book, (bookdir, files) in SOURCES.items():
        outdir = bookdir / "figures"
        work = bookdir / "_figbuild"
        outdir.mkdir(exist_ok=True)
        work.mkdir(exist_ok=True)
        styles = styles_for(book)
        print(f"=== {book} ===")
        seen, ok = set(), 0
        for f in files:
            text = f.read_text(encoding="utf-8", errors="replace")
            for m in FIGURE.finditer(text):
                lab = m.group("lab")
                if lab in seen:
                    continue
                seen.add(lab)
                out = render(book, outdir, work, styles, lab,
                             m.group("body").strip())
                if out:
                    ok += 1
                    print(f"  OK   fig-{lab}.png  ({out.stat().st_size//1024} KB)")
                else:
                    print(f"  FAIL fig-{lab}")
        print(f"  {ok}/{len(seen)} rendered\n")
        grand += ok
    print(f"{grand} figures rendered in total")


if __name__ == "__main__":
    main()
