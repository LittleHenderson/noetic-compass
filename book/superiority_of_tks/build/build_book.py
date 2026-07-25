#!/usr/bin/env python3
r"""
Build The Superiority of TKS into a 6x9 trade-paperback PDF.

Pipeline:
  SOURCE_ORIGINAL.md  --repair_manuscript.py-->  MANUSCRIPT.md
  MANUSCRIPT.md       --pandoc-->                body.tex
  body.tex + frontmatter_tks.tex + preamble_tks.tex --xelatex x2--> PDF

The preamble is derived from the shared Noetic Compass Press preamble so all
three books share one typographic system, one margin geometry, and one Unicode
fallback table. Unlike the CAS titles this book needs no notation machinery,
but it inherits the same page setup and glyph coverage.
"""
import re
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
BOOK = BUILD.parent
SHARED_PREAMBLE = BOOK.parent / "publishing" / "latex" / "preamble.tex"


def patch_preamble() -> None:
    p = SHARED_PREAMBLE.read_text(encoding="utf-8")
    p = p.replace("Thinking in Cognitive Architecture",
                  "Reality Engineering: The Tootra Kabbalistic System")
    p = p.replace(
        "A Universal Framework for Humans, AI, and Biological Minds",
        "A Complete Operating Manual for Manifestation",
    )
    p = p.replace(
        "cognitive architecture, CAS, AI alignment, topos theory, Noetic Compass",
        "TKS, Tootra, Kabbalah, reality engineering, manifestation, esoteric practice",
    )
    # This book has many short sections; number chapters and parts only.
    p = p.replace(r"\setcounter{secnumdepth}{1}", r"\setcounter{secnumdepth}{0}")
    p = p.replace(r"\setcounter{tocdepth}{1}", r"\setcounter{tocdepth}{0}")

    # ASCII box-drawing diagrams live in fenced blocks; Consolas lacks many of
    # those glyphs, DejaVu Sans Mono has the full set.
    p = p.replace(r"\setmonofont{Consolas}[Scale=0.92]",
                  r"\setmonofont{DejaVu Sans Mono}[Scale=0.84]")

    # Zodiac signs appear in running prose (166 lines of card/sign
    # correspondences) and Palatino has no glyphs for them. Route them, and the
    # remaining stray symbols, through DejaVu Sans.
    zodiac = {
        "2648": "aries", "2649": "taurus", "264A": "gemini", "264B": "cancer",
        "264C": "leo", "264D": "virgo", "264E": "libra", "264F": "scorpio",
        "2650": "sagittarius", "2651": "capricorn", "2652": "aquarius",
        "2653": "pisces",
    }
    extra = ["\n% --- Superiority of TKS: symbol fallback font ---",
             r"\newfontfamily\symbolfont{DejaVu Sans}"]
    for cp in zodiac:
        extra.append(rf'\newunicodechar{{^^^^{cp.lower()}}}'
                     rf'{{{{\symbolfont\symbol{{"{cp}}}}}}}')
    # arrows and misc marks the body font also lacks
    for cp, cmd in (("2191", r"\uparrow"), ("2193", r"\downarrow"),
                    ("2195", r"\updownarrow")):
        extra.append(rf'\newunicodechar{{^^^^{cp.lower()}}}{{\ensuremath{{{cmd}}}}}')
    extra.append(r'\newunicodechar{^^^^25cc}{{\symbolfont\symbol{"25CC}}}')
    extra.append(r'\newunicodechar{^^^^1d62}{\textsubscript{i}}')
    extra.append(r'\newunicodechar{^^^^2099}{\textsubscript{n}}')
    extra.append(r'\newunicodechar{^^^^2098}{\textsubscript{m}}')
    # misc operators Palatino lacks
    for cp, cmd in (("25c7", r"\diamond"), ("2299", r"\odot"),
                    ("224b", r"\approx"), ("21c4", r"\rightleftarrows"),
                    ("21ba", r"\circlearrowleft"), ("25cb", r"\circ"),
                    ("27f9", r"\Longrightarrow")):
        extra.append(rf'\newunicodechar{{^^^^{cp}}}{{\ensuremath{{{cmd}}}}}')
    # The Golem chapter quotes Hebrew (emet / met). Palatino has no Hebrew.
    extra.append(r"\newfontfamily\hebrewfont{Times New Roman}")
    for cp in ("05d0", "05de", "05ea", "05d5", "05d1", "05d2", "05d3"):
        extra.append(rf'\newunicodechar{{^^^^{cp}}}'
                     rf'{{{{\hebrewfont\symbol{{"{cp.upper()}}}}}}}')

    # Page-count control. At 11pt/1.20 leading this book ran 851 pages, over
    # KDP's 828-page ceiling for a black-and-white paperback on white stock.
    # Tightening the leading brings it inside the limit without dropping to
    # 10pt, which would hurt readability across 178,000 words.
    p = p.replace(r"\setSingleSpace{1.20}", r"\setSingleSpace{1.13}")

    p += "\n".join(extra) + "\n"
    # Long unbroken prose with em-dashes and wide tables; let it stretch.
    # fvextra lets the ASCII flow diagrams wrap instead of running off the
    # trimmed page edge -- several are wider than the 6x9 measure.
    p = p.replace(r"\usepackage{fancyvrb}",
                  "\\usepackage{fancyvrb}\n\\usepackage{fvextra}\n"
                  "\\fvset{breaklines=true,breakanywhere=true,"
                  "fontsize=\\footnotesize}")
    p += (
        "\n% --- Superiority of TKS build: overfull-box mitigation ---\n"
        "\\usepackage{etoolbox}\n"
        "\\setlength{\\emergencystretch}{3em}\n"
        "\\AtBeginEnvironment{longtable}{\\footnotesize}\n"
        "\\AtBeginEnvironment{tabular}{\\small}\n"
    )
    (BUILD / "preamble_tks.tex").write_text(p, encoding="utf-8")
    print("patched preamble -> preamble_tks.tex")


def run(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, cwd=BUILD, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", **kw)
    if r.returncode != 0 and cmd[0] != "xelatex":
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        sys.exit(f"FAILED: {cmd[0]}")
    return r


def main() -> None:
    run([sys.executable, str(BUILD / "repair_manuscript.py")])
    patch_preamble()
    run(["pandoc", str(BOOK / "MANUSCRIPT.md"),
         "-o", "body.tex", "-t", "latex",
         "--top-level-division=chapter",
         "-f", "markdown-superscript-subscript",
         "--syntax-highlighting=none"])

    # Convert pandoc's plain verbatim to fvextra's Verbatim so the ASCII
    # diagrams wrap at the measure instead of running into the margin.
    body = BUILD / "body.tex"
    t = body.read_text(encoding="utf-8")
    n = t.count(r"\begin{verbatim}")
    t = t.replace(r"\begin{verbatim}",
                  r"\begin{Verbatim}[breaklines=true,breakanywhere=true,"
                  r"fontsize=\footnotesize]")
    t = t.replace(r"\end{verbatim}", r"\end{Verbatim}")
    body.write_text(t, encoding="utf-8")
    print(f"  converted {n} verbatim block(s) to breakable Verbatim")
    for i in (1, 2):
        run(["xelatex", "-interaction=nonstopmode", "manuscript_tks.tex"])
        print(f"  xelatex pass {i} done")

    pdf = BUILD / "manuscript_tks.pdf"
    if pdf.exists():
        import pypdf
        n = len(pypdf.PdfReader(str(pdf)).pages)
        target = BOOK / "Reality_Engineering.pdf"
        target.write_bytes(pdf.read_bytes())
        log = (BUILD / "manuscript_tks.log").read_text(encoding="utf-8",
                                                       errors="replace")
        print(f"\nOK: {target}  ({n} pages)")
        print(f"    missing glyphs: {len(re.findall('Missing character', log))}")
    else:
        sys.exit("no PDF produced")


if __name__ == "__main__":
    main()
