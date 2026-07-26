#!/usr/bin/env python3
r"""
Preprocess FULL_MANUSCRIPT_v2.md into a pandoc-friendly markdown file for
LaTeX conversion.

Does NOT modify manuscript semantics. Only translates the manuscript's
structural conventions into proper markdown headings pandoc recognizes:

  - ' PART N: TITLE' (single-leading-space lines) -> raw LaTeX \part{TITLE}
  - ' Chapter N: TITLE'                           -> '# Chapter N: TITLE'
  - ' Appendix X: TITLE' (first one triggers \appendix) -> '# Appendix X: TITLE'
  - ' J.N Title' (Appendix J subsections)         -> '## J.N Title'
  - Every OTHER heading-shaped single-leading-space line -> '## Title'.
    These are the manuscript's section headings (439 of them). Previously they
    fell through and were typeset as ordinary body text, which left the printed
    book and the EPUB with no navigation below chapter level.

IMPORTANT: single-leading-space lines inside fenced ``` blocks are CAS-language
code comments, not headings. They are tracked and left untouched.

Section numbering is suppressed (secnumdepth 0, re-asserted after \mainmatter
because memoir's \mainmatter resets it). The manuscript supplies its own
ordinals where it wants them ('1. The Principled Domain', 'J.1 Purpose'), so
auto-numbering on top would print 'J.1 J.1 Purpose'.

Also:
  - Strips the placeholder '[Front Matter]' and 'Back Matter' top-level
    markers — we replace these with explicit \frontmatter / \mainmatter /
    \backmatter LaTeX commands injected at known boundaries.
  - Strips/rewrites the existing '## Title Page', '## Copyright',
    '## Dedication' sections from the markdown front matter — we use a
    hand-crafted LaTeX title/copyright/dedication page instead.
"""

import re
import sys
from pathlib import Path

SRC = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\manuscript\FULL_MANUSCRIPT_v2.md")
DST = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\publishing\latex\manuscript_preprocessed.md")

sys.path.insert(0, str(Path(__file__).parent))
from figures import FIGURES  # noqa: E402

# anchor text -> (tikz body, label, caption). Figures are emitted immediately
# before their anchor heading.
FIG_BY_ANCHOR = {a: (b, lbl, cap) for a, b, lbl, cap in FIGURES}

# Acronyms that str.title() would mangle ("AI SYSTEMS" -> "Ai Systems").
ACRONYMS = {"AI", "CAS", "RPM", "NCCS", "CO", "LLM", "API", "EPUB", "PDF", "US"}

# Editorial notes that must not reach the printed page.
EDITORIAL = re.compile(r"^\s*\[(PREFACE SUPPLEMENT|PLACEHOLDER|AUTHOR REVIEW)[^\]]*\]\s*$", re.I)
HTML_NOTE = re.compile(r"^\s*<!--\s*(AUTHOR REVIEW|TODO|NOTE TO SELF)", re.I)


def smart_title(s: str) -> str:
    """Title-case a shouted heading without destroying acronyms."""
    return " ".join(
        w if w.upper() in ACRONYMS else w.title()
        for w in s.split(" ")
    )


def is_heading(stripped: str) -> bool:
    """Heading-shaped: short, not a sentence, not a wrapped continuation."""
    return (
        0 < len(stripped) <= 85
        and not stripped.endswith(".")
        and not stripped[:1].islower()
    )


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    lines = text.splitlines()
    out = []

    # Strip [Front Matter] marker and Back Matter marker — handled by LaTeX
    # frontmatter/mainmatter/backmatter directives below.
    appendix_mode = False
    in_code = False
    in_html_note = False
    n_promoted = 0
    n_dropped = 0
    n_figures = 0

    i = 0
    # Collect all structural-marker line numbers for boundary logic
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()

        # --- fenced code blocks: pass through verbatim ---------------------
        if stripped.lstrip().startswith("```"):
            in_code = not in_code
            out.append(line)
            i += 1
            continue
        if in_code:
            out.append(line)
            i += 1
            continue

        # --- multi-line HTML editorial notes -------------------------------
        if in_html_note:
            if "-->" in stripped:
                in_html_note = False
            i += 1
            n_dropped += 1
            continue
        if HTML_NOTE.match(stripped):
            if "-->" not in stripped:
                in_html_note = True
            i += 1
            n_dropped += 1
            continue

        # --- bracketed editorial placeholders ------------------------------
        if EDITORIAL.match(stripped):
            i += 1
            n_dropped += 1
            continue

        # Skip '# [Front Matter]' marker entirely
        if stripped == "# [Front Matter]":
            i += 1
            continue

        # Mark main-matter / back-matter transitions
        if stripped == "# Back Matter":
            out.append("")
            out.append(r"```{=latex}")
            out.append(r"\backmatter")
            out.append(r"```")
            out.append("")
            i += 1
            continue

        # Strip the redundant '## Title Page', '## Copyright', '## Dedication'
        # sections from the original front matter. The LaTeX preamble supplies
        # these via \maketitle, custom title/copyright/dedication pages.
        if stripped in ("## Title Page", "## Copyright", "## Dedication",
                        "## Acknowledgments", "## Table of Contents"):
            # Skip through the next '## ' or '---' separator
            i += 1
            while i < len(lines):
                nxt = lines[i].rstrip()
                if nxt.startswith("## ") or nxt == "# Back Matter":
                    break
                i += 1
            continue

        # Preface heading — keep as unnumbered chapter via raw LaTeX
        if stripped.startswith("## Preface:"):
            out.append("")
            out.append(r"```{=latex}")
            out.append(r"\chapter*{Preface: The Map and the Territory}")
            out.append(r"\addcontentsline{toc}{chapter}{Preface: The Map and the Territory}")
            out.append(r"\markboth{PREFACE}{PREFACE}")
            out.append(r"```")
            out.append("")
            i += 1
            continue

        # 'How to Read This Book' — unnumbered chapter
        if stripped == "## How to Read This Book":
            out.append("")
            out.append(r"```{=latex}")
            out.append(r"\chapter*{How to Read This Book}")
            out.append(r"\addcontentsline{toc}{chapter}{How to Read This Book}")
            out.append(r"\markboth{HOW TO READ THIS BOOK}{HOW TO READ THIS BOOK}")
            out.append(r"```")
            out.append("")
            i += 1
            continue

        # PART I: THE FOUNDATIONS  (single leading space)
        m = re.match(r"^ (PART [IVX]+):\s*(.+)$", line)
        if m:
            part_label = m.group(1).title()  # "Part I"
            part_title = smart_title(m.group(2).strip())
            out.append("")
            out.append(r"```{=latex}")
            # Start main matter at Part I
            if part_label == "Part I":
                out.append(r"\mainmatter")
                # memoir's \mainmatter resets secnumdepth, which would number
                # sections on top of the manuscript's own ordinals. Re-suppress.
                out.append(r"\setcounter{secnumdepth}{0}")
                out.append(r"\setcounter{tocdepth}{0}")
            out.append(fr"\part{{{part_title}}}")
            out.append(r"```")
            out.append("")
            i += 1
            continue

        # Chapter N: Title — memoir auto-prefixes "Chapter N", so emit bare title
        m = re.match(r"^ Chapter ([0-9.]+):\s*(.+)$", line)
        if m:
            chnum = m.group(1)
            chtitle = m.group(2).strip()
            # For Chapter 26.5 (non-integer), we keep the full label since
            # memoir auto-numbering would assign 27 — handle specially below.
            if chnum == "26.5":
                out.append("")
                out.append(r"```{=latex}")
                out.append(r"\chapter*{Chapter 26.5: " + chtitle + "}")
                out.append(r"\addcontentsline{toc}{chapter}{Chapter 26.5: " + chtitle + "}")
                out.append(r"\markboth{" + chtitle.upper() + "}{" + chtitle.upper() + "}")
                out.append(r"```")
                out.append("")
            else:
                out.append("")
                out.append(f"# {chtitle}")
                out.append("")
            i += 1
            continue

        # Appendix X: Title — first one triggers \appendix; memoir prefixes "Appendix X"
        m = re.match(r"^ Appendix ([A-Z]):\s*(.+)$", line)
        if m:
            if not appendix_mode:
                appendix_mode = True
                out.append("")
                out.append(r"```{=latex}")
                out.append(r"\appendix")
                out.append(r"```")
                out.append("")
            app_title = m.group(2).strip()
            out.append("")
            out.append(f"# {app_title}")
            out.append("")
            i += 1
            continue

        # Appendix J subsection: ' J.N Title'
        m = re.match(r"^ (J\.[0-9]+)\s+(.+)$", line)
        if m:
            sub_label = m.group(1)
            sub_title = m.group(2).strip()
            out.append("")
            out.append(f"## {sub_label} {sub_title}")
            out.append("")
            i += 1
            continue

        # Back-matter subsections like '## Glossary', '## Bibliography' — keep
        # as unnumbered chapter
        # The manuscript's "Index" section is a note explaining how an index
        # would be produced, not an index. Replace it with the real one, built
        # from the \index marks that build_indexes.py inserts into body.tex.
        if stripped == "## Index":
            out.append("")
            out.append(r"```{=latex}")
            out.append(r"\printindex")
            out.append(r"```")
            out.append("")
            i += 1
            while i < len(lines):
                nxt = lines[i].rstrip()
                if nxt.startswith("## ") or nxt == "# Back Matter":
                    break
                i += 1
            continue

        if stripped in ("## Glossary", "## Bibliography and Further Reading",
                        "## About the Author", "## Contact and Community",
                        "## Colophon"):
            title = stripped[3:]
            out.append("")
            out.append(r"```{=latex}")
            out.append(fr"\chapter*{{{title}}}")
            out.append(fr"\addcontentsline{{toc}}{{chapter}}{{{title}}}")
            out.append(fr"\markboth{{{title.upper()}}}{{{title.upper()}}}")
            out.append(r"```")
            out.append("")
            i += 1
            continue

        # --- figures ---------------------------------------------------------
        # Emitted before the heading they illustrate.
        if stripped.rstrip() in FIG_BY_ANCHOR:
            body, label, caption = FIG_BY_ANCHOR.pop(stripped.rstrip())
            out.append("")
            out.append(r"```{=latex}")
            out.append(r"\begin{figure}[htbp]")
            out.append(r"\centering")
            out.append(body.strip())
            out.append(rf"\caption{{{caption}}}\label{{fig:{label}}}")
            out.append(r"\end{figure}")
            out.append(r"```")
            out.append("")
            n_figures += 1

        # --- section headings ----------------------------------------------
        # Any remaining single-leading-space, heading-shaped line is one of the
        # manuscript's section headings. Promote it so it typesets as a heading
        # and appears in PDF bookmarks and EPUB navigation.
        if (
            line.startswith(" ")
            and not line.startswith("  ")
            and is_heading(stripped.strip())
        ):
            out.append("")
            out.append(f"## {stripped.strip()}")
            out.append("")
            n_promoted += 1
            i += 1
            continue

        out.append(line)
        i += 1

    DST.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {DST}  ({len(out)} lines)")
    print(f"  promoted {n_promoted} section heading(s) to '##'")
    print(f"  dropped  {n_dropped} editorial note line(s)")
    print(f"  inserted {n_figures} figure(s)")
    if FIG_BY_ANCHOR:
        raise SystemExit(
            "preprocess: FAILED - these figure anchors no longer match the "
            "manuscript: " + "; ".join(repr(a) for a in FIG_BY_ANCHOR))


if __name__ == "__main__":
    main()
