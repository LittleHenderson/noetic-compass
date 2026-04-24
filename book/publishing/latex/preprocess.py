#!/usr/bin/env python3
"""
Preprocess FULL_MANUSCRIPT_v2.md into a pandoc-friendly markdown file for
LaTeX conversion.

Does NOT modify manuscript semantics. Only translates the manuscript's
structural conventions into proper markdown headings pandoc recognizes:

  - ' PART N: TITLE' (single-leading-space lines) -> raw LaTeX \part{TITLE}
  - ' Chapter N: TITLE'                           -> '# Chapter N: TITLE'
  - ' Appendix X: TITLE' (first one triggers \appendix) -> '# Appendix X: TITLE'
  - ' J.N Title' (Appendix J subsections)         -> '## J.N Title'
  - Other single-leading-space short lines are left unchanged (bold inline
    rendering will be handled in LaTeX via paragraph styling if required).

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


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    lines = text.splitlines()
    out = []

    # Strip [Front Matter] marker and Back Matter marker — handled by LaTeX
    # frontmatter/mainmatter/backmatter directives below.
    appendix_mode = False

    i = 0
    # Collect all structural-marker line numbers for boundary logic
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()

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
            part_title = m.group(2).strip().title()
            out.append("")
            out.append(r"```{=latex}")
            # Start main matter at Part I
            if part_label == "Part I":
                out.append(r"\mainmatter")
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
        if stripped in ("## Glossary", "## Bibliography and Further Reading",
                        "## About the Author", "## Contact and Community",
                        "## Colophon", "## Index"):
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

        out.append(line)
        i += 1

    DST.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {DST}  ({len(out)} lines)")


if __name__ == "__main__":
    main()
