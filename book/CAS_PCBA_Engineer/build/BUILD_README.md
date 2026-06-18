# Building the CAS PCBA Engineer PDF

This directory builds the designed 6×9 trade-paperback PDF of *CAS PCBA Engineer*
from the chapter/appendix Markdown in the parent folder.

## Toolchain
- **pandoc** ≥ 3 (Markdown → LaTeX)
- **XeLaTeX** (MiKTeX/TeX Live) — Unicode + fontspec
- **Python** 3 (assembly + post-processing)
- Fonts: **Palatino Linotype** (body), **Arial** (sans), **DejaVu Sans Mono** (code).
  DejaVu Sans Mono is used for code blocks because it covers the CAS notation
  glyphs (Greek β/Θ/Ω, arrows, operators, subscript digits).

## Hand-written source files (checked in)
- `build_book.py` — assembles the book: patches the proven CAS LaTeX preamble
  (`../../publishing/latex/preamble.tex`), slices the Preface + How-to from
  `../00_Front_Matter.md`, and stitches the 26 chapters into 5 `\part`s plus the
  8 lettered appendices. Strips redundant "Chapter N:" / "Appendix X —" prefixes
  from H1s (memoir already prints the label).
- `postprocess_pcba.py` — converts pandoc's plain `verbatim` blocks to
  line-breaking `fvextra` `Verbatim` so long CCDL/ASCII lines fit the measure.
- `manuscript_pcba.tex` — master document (memoir, 11pt, 6×9, twoside).
- `frontmatter_pcba.tex` — half-title, title, copyright, epigraph, TOC.

## Generated files (gitignored)
`preamble_pcba.tex`, `front_prose.{md,tex}`, `main_body.md`, `body.tex`,
and all `*.aux/*.log/*.toc/*.pdf`, plus `preview/`.

## Build
```bash
python build_book.py
pandoc front_prose.md -o front_prose.tex -t latex --top-level-division=chapter \
       -f markdown-superscript-subscript --syntax-highlighting=none
pandoc main_body.md   -o body.tex        -t latex --top-level-division=chapter \
       -f markdown-superscript-subscript --syntax-highlighting=none
python postprocess_pcba.py
xelatex -interaction=nonstopmode manuscript_pcba.tex   # run twice for TOC/refs
xelatex -interaction=nonstopmode manuscript_pcba.tex
cp manuscript_pcba.pdf ../CAS_PCBA_Engineer.pdf
```

Notes:
- Sections are auto-numbered by memoir (e.g. 5.8, 24.4); the TOC is kept at
  chapter level. `\mainmatter` resets memoir's secnumdepth, which is why sections
  number regardless of the `secnumdepth` counter in the preamble.
- The MiKTeX "unsupported version of Windows" line is a harmless warning; the PDF
  still builds.
