#!/usr/bin/env python3
r"""
Render each TikZ figure standalone to PNG for the EPUB edition.

The print build embeds the figures as live TikZ. Pandoc's EPUB writer drops raw
LaTeX, so without this step the ebook would ship with no figures at all --
which for a book whose whole complaint was "zero figures in 786 pages" would be
a poor joke.

Output: figures/fig-<label>.png at 300 DPI, plus a manifest the EPUB builder
uses to swap each raw-LaTeX figure block for an image reference.
"""
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from figures import FIGURES  # noqa: E402

OUT = HERE / "figures"
WORK = HERE / "_figbuild"

PREAMBLE = (HERE / "figures_preamble.tex").read_text(encoding="utf-8")
# Take the style block from its first line onward. Splitting on
# \usetikzlibrary does NOT work: that command wraps onto a second line, and the
# orphaned tail gets injected as stray braces, which silently produces eight
# identical blank pages instead of eight figures.
MARK = "\\definecolor{casink}"
if MARK not in PREAMBLE:
    sys.exit(f"render_figures: style marker {MARK!r} not found in preamble")
STYLES = PREAMBLE[PREAMBLE.index(MARK):]

DOC = r"""\documentclass[border=6pt]{standalone}
\usepackage{fontspec}
\defaultfontfeatures{Ligatures=TeX}
\setmainfont{Palatino Linotype}
\usepackage{tikz}
\usetikzlibrary{arrows.meta, positioning, calc, shapes.geometric, fit,
                backgrounds, decorations.pathmorphing}
%(styles)s
\begin{document}
%(body)s
\end{document}
"""


def main():
    if not shutil.which("xelatex"):
        sys.exit("xelatex not found")
    OUT.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)

    manifest = {}
    for anchor, body, label, caption in FIGURES:
        tex = DOC % {"styles": STYLES, "body": body}
        src = WORK / f"{label}.tex"
        src.write_text(tex, encoding="utf-8")

        r = subprocess.run(
            ["xelatex", "-interaction=nonstopmode",
             f"-output-directory={WORK}", str(src)],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        pdf = WORK / f"{label}.pdf"
        if not pdf.exists():
            print(f"  FAIL {label}")
            print(r.stdout[-1800:])
            continue

        png = OUT / f"fig-{label}"
        subprocess.run(["pdftoppm", "-png", "-r", "300", "-singlefile",
                        str(pdf), str(png)],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
        final = png.with_suffix(".png")
        if final.exists():
            kb = final.stat().st_size // 1024
            manifest[label] = {"file": f"figures/fig-{label}.png",
                               "caption": caption}
            print(f"  OK  fig-{label}.png  ({kb} KB)")

    (HERE / "figures_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n{len(manifest)}/{len(FIGURES)} figures rendered "
          f"-> {HERE / 'figures_manifest.json'}")


if __name__ == "__main__":
    main()
