#!/usr/bin/env python3
r"""
Build print-ready full-wrap covers and Kindle front covers for all three
Noetic Compass Press titles.

Geometry is exact KDP for a 6x9 black-and-white paperback on WHITE stock:

    spine width = pages x 0.002252 in
    wrap width  = 0.125 bleed + 6 + spine + 6 + 0.125 bleed
    wrap height = 0.125 bleed + 9 + 0.125 bleed = 9.25 in

The barcode clear zone (2.0 x 1.2 in, back-cover bottom-right, inset 0.25 in
from trim) is left empty and white, which is what KDP requires.

Design is deliberately typographic. These are technical and framework titles;
in those categories a confident type-and-rule cover reads as more credible than
stock illustration, and it survives being shrunk to a thumbnail, which is where
most buying decisions actually happen. Each front carries one geometric mark
drawn from that book's own content, not decoration.

Outputs per book:
    <slug>_wrap.pdf   full-wrap print cover, 300 DPI vector
    <slug>_kindle.jpg front only, 2560 x 1600 px

Run: python build_covers.py
"""
import io
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "cover_template.tex"

SPINE_PER_PAGE = 0.002252   # white stock
BLEED = 0.125
TRIM_W, TRIM_H = 6.0, 9.0


def tex_escape(s):
    for a, b in [("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_")]:
        s = s.replace(a, b)
    return s


# --- geometric marks, each derived from the book it sits on ---------------

MARK_PCBA = r"""\begin{tikzpicture}[x=1.45mm,y=1.45mm]
  % A Cognitive Junction Transistor: cause in, bias controlling, effect out.
  \draw[accent, line width=0.9pt] (0,6) -- (11,6);
  \draw[ink!55, line width=0.9pt] (11,0) -- (11,12);
  \draw[accent, line width=0.9pt] (11,9.4) -- (22,13.6);
  \draw[accent, line width=0.9pt] (11,2.6) -- (22,-1.6);
  \fill[accent] (22,13.6) circle (0.85mm);
  \fill[accent] (22,-1.6) circle (0.85mm);
  \fill[ink!55] (0,6) circle (0.85mm);
\end{tikzpicture}"""

MARK_TICA = r"""\begin{tikzpicture}[x=1.45mm,y=1.45mm]
  % The 40 Cognitive States: 10 Noetics across, 4 Processing Domains down.
  \foreach \r in {0,1,2,3} {
    \foreach \c in {0,...,9} {
      \pgfmathsetmacro\op{0.30 + 0.70*(\r==0) + 0.22*\c/9}
      \fill[accent, opacity=\op] (\c*3.0, -\r*3.0) circle (0.78mm);
    }
  }
\end{tikzpicture}"""

MARK_TKS = r"""\begin{tikzpicture}[x=1.45mm,y=1.45mm]
  % The Four Worlds: one descent, Atziluth down to Deha, each denser.
  \foreach \r/\n/\o in {0/3/0.95, 1/5/0.78, 2/7/0.60, 3/10/0.42} {
    \foreach \c in {1,...,\n} {
      \pgfmathsetmacro\x{(\c-1)*(27.0/(\n-1))}
      \fill[accent, opacity=\o] (\x, -\r*3.4) circle (0.80mm);
    }
  }
  \draw[accent, opacity=0.30, line width=0.5pt] (-1.6,1.9) -- (28.6,1.9);
\end{tikzpicture}"""


BOOKS = [
    {
        "slug": "cas_pcba_engineer",
        "pages": 722,
        "title_lines": r"CAS\\PCBA\\Engineer",
        "spine_title": "CAS PCBA Engineer",
        "subtitle": "Designing Cognitive Circuits with the "
                    "Cognitive Architecture System",
        "title_drop": 4.35,
        "blurb_drop": 2.35,
        "ink": "16202B", "accent": "1F5C73", "paper": "F2EFE9",
        "mark": MARK_PCBA,
        "hook": "We would never accept from a bridge, a pacemaker, or a power "
                "supply what we routinely accept from an AI system.",
        "blurb": r"""This is the circuit-design discipline for cognition. It begins with a
single discovery: the transistor has an exact structural twin in thought. A bias
controls the path from a cause to an effect the same way a base current controls
collector-to-emitter flow.\par\medskip
From that Cognitive Junction Transistor the book builds a complete component
library --- resistors, capacitors, inductors, diodes, amplifiers, filters,
oscillators, power management --- and then five full Cognitive Circuit Boards,
including a Cognitive Safety Board you design, test, and sign off.\par\medskip
A bench book. Every component has a datasheet. Every board has a schematic, a
bill of materials, test points, and a failure-mode table. All 105 exercises are
answered in full. No electronics background assumed; none in CAS either. Both
are taught from first principles, exactly where you need them.""",
        "category": "COMPUTERS / Artificial Intelligence",
    },
    {
        "slug": "thinking_in_cognitive_architecture",
        "pages": 790,
        "title_lines": r"Thinking in\\Cognitive\\Architecture",
        "spine_title": "Thinking in Cognitive Architecture",
        "subtitle": "A Universal Framework for Humans, AI, "
                    "and Biological Minds",
        "title_drop": 4.35,
        "blurb_drop": 2.55,
        "ink": "1A1A22", "accent": "6B3F8C", "paper": "F4F1EC",
        "mark": MARK_TICA,
        "hook": "What if the same structural laws that govern how a person turns "
                "intention into action also govern how an AI turns a prompt into "
                "a response?",
        "blurb": r"""The Cognitive Architecture System is a formal framework that maps the
structure of thought across any substrate, human or artificial. Ten Noetics
describe what a mind is doing. Four Processing Domains describe at what level.
Seven Core Drives describe why.\par\medskip
Together they give you what a vocabulary of ``bias'' and ``heuristic'' never
did: a notation precise enough to write a mind down, compare two of them, and
say exactly where one is failing.\par\medskip
The book moves from the ten primitives to the forty cognitive states, through
the prerequisite chains that make capability possible, and into the inversions
that make sophisticated minds fail in predictable ways. Then it turns the
instrument on artificial minds --- assessment, adversarial resilience, and what
it takes to build an AI that is architecturally sound rather than merely
well-behaved.\par\medskip
Twenty-eight chapters. Ten appendices. A complete formal system, taught from
nothing.""",
        "category": "COMPUTERS / Artificial Intelligence",
    },
    {
        "slug": "reality_engineering",
        "pages": 817,
        "title_lines": r"Reality\\Engineering",
        "spine_title": "Reality Engineering",
        "subtitle": "The Tootra Kabbalistic System --- A Complete Operating "
                    "Manual for Manifestation",
        "title_drop": 3.75,
        "blurb_drop": 2.75,
        "ink": "1C1A16", "accent": "8C5A1F", "paper": "F5F0E6",
        "mark": MARK_TKS,
        "hook": "You have manifested before. And then it stopped working, and "
                "nobody could tell you why.",
        "blurb": r"""Every system hands you fragments. Kabbalah gives you cosmic backstory
and no mechanism. Law of Attraction gives you a frequency and no engine. Chaos
magick gets results it cannot explain. None of them can tell you what went wrong
on the attempt that failed.\par\medskip
The Tootra Kabbalistic System is built to answer exactly that question. Ten
Noetics, four Worlds, forty Elements, seven Foundations, and a Recursive
Prerequisite Model that finds the specific unmet condition blocking a specific
outcome. Not ``raise your vibration'' --- a diagnosis, with a name, and an
operation that addresses it.\par\medskip
Twenty-seven chapters, five full workshops covering money, love, health,
protection, and career, and twelve appendices of reference tables, templates,
and troubleshooting.\par\medskip
Stop describing reality. Start engineering it.""",
        "category": "BODY, MIND \\& SPIRIT / Magick Studies",
    },
]

BIO = ("Little Henderson is the creator of the Cognitive Architecture System "
       "and the Noetic Compass assessment framework, and the author of the "
       "Noetic Compass Press series.")

AUTHOR = "Little Henderson"


def build(book):
    pages = book["pages"]
    spine = pages * SPINE_PER_PAGE
    wrap_w = 2 * BLEED + 2 * TRIM_W + spine
    wrap_h = 2 * BLEED + TRIM_H

    spine_x = BLEED + TRIM_W
    spine_x_end = spine_x + spine
    front_x = spine_x_end
    spine_mid = spine_x + spine / 2.0

    # Spine type must fit the spine width with margin; scale to it.
    spine_pt = max(9.0, min(15.0, (spine - 0.30) * 72.0 * 0.42))

    subs = {
        r"\WRAPWIDTH": f"{wrap_w:.4f}in",
        r"\WRAPHEIGHT": f"{wrap_h:.4f}in",
        r"\WRAPW": f"{wrap_w:.4f}",
        r"\WRAPH": f"{wrap_h:.4f}",
        r"\SPINEXEND": f"{spine_x_end:.4f}",
        r"\SPINEX": f"{spine_x:.4f}",
        r"\SPINEMID": f"{spine_mid:.4f}",
        r"\FRONTX": f"{front_x:.4f}",
        r"\INKCOLOR": book["ink"],
        r"\ACCENTCOLOR": book["accent"],
        r"\PAPERCOLOR": book["paper"],
        r"\TITLELINEA": book["title_lines"],
        r"\SUBTITLE": tex_escape(book["subtitle"]),
        r"\SPINETITLE": tex_escape(book["spine_title"]),
        r"\SPINESIZE": f"{spine_pt:.1f}",
        r"\TITLEDROP": f"{book['title_drop']:.2f}",
        r"\BLURBDROP": f"{book['blurb_drop']:.2f}",
        r"\AUTHOR": AUTHOR,
        r"\HOOK": tex_escape(book["hook"]),
        r"\BLURB": book["blurb"],
        r"\BIO": tex_escape(BIO),
        r"\CATEGORY": book["category"],
        r"\MARK": book["mark"],
    }

    tex = TEMPLATE.read_text(encoding="utf-8")
    # longest token first so \SPINEX does not clip \SPINEXEND
    for k in sorted(subs, key=len, reverse=True):
        tex = tex.replace(k, subs[k])

    work = HERE / "_build"
    work.mkdir(exist_ok=True)
    src = work / f"{book['slug']}.tex"
    src.write_text(tex, encoding="utf-8")

    r = subprocess.run(["xelatex", "-interaction=nonstopmode",
                        f"-output-directory={work}", str(src)],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    pdf = work / f"{book['slug']}.pdf"
    if not pdf.exists():
        print(f"  FAIL {book['slug']}")
        print(r.stdout[-2500:])
        return None

    out_pdf = HERE / f"{book['slug']}_wrap.pdf"
    shutil.copyfile(pdf, out_pdf)

    # Kindle front: crop the front panel out of the wrap. KDP wants 2560 px on
    # the LONGEST side, so scale to height, not width. At a 6x9 trim that gives
    # 1707 x 2560, which is inside KDP's accepted range (their ideal 1.6:1 is
    # 1600x2560; a 1.5:1 trim cannot hit that exactly without distorting).
    dpi = 2560 / TRIM_H                     # 284.44 -> 2560 px down 9in
    front_png = work / f"{book['slug']}_front"
    subprocess.run(
        ["pdftoppm", "-png", "-r", f"{dpi:.4f}",
         "-x", str(int(front_x * dpi)), "-y", str(int(BLEED * dpi)),
         "-W", str(int(TRIM_W * dpi)), "-H", str(int(TRIM_H * dpi)),
         "-singlefile", str(out_pdf), str(front_png)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")

    png = front_png.with_suffix(".png")
    kindle = HERE / f"{book['slug']}_kindle.png"
    if png.exists():
        shutil.copyfile(png, kindle)

    return out_pdf, kindle, spine, wrap_w, wrap_h


def main():
    if not shutil.which("xelatex"):
        sys.exit("xelatex not found")
    print("Building covers\n")
    for b in BOOKS:
        res = build(b)
        if not res:
            continue
        pdf, kindle, spine, w, h = res
        print(f"  OK  {b['spine_title']}")
        print(f"        wrap   {pdf.name}  {w:.4f} x {h:.2f} in "
              f"(spine {spine:.4f} in @ {b['pages']}pp)")
        print(f"        kindle {kindle.name}")
    print("\nCheck the spine width against KDP's Cover Calculator before "
          "uploading; page counts must match the final interiors exactly.")


if __name__ == "__main__":
    main()
