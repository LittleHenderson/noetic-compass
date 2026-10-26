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
- `build_full_book.py` — **the build driver.** Runs the pipeline in order and
  fails on a LaTeX error. Use this rather than the manual steps below.
- `build_book.py` — assembles the book: patches the proven CAS LaTeX preamble
  (`../../publishing/latex/preamble.tex`), slices the Preface + How-to from
  `../00_Front_Matter.md`, and stitches the 26 chapters into 5 `\part`s plus the
  lettered appendices. Strips redundant "Chapter N:" / "Appendix X —" prefixes
  from H1s (memoir already prints the label).
- `postprocess_pcba.py` — converts pandoc's plain `verbatim` blocks to
  line-breaking `fvextra` `Verbatim` so long CCDL/ASCII lines fit the measure.
- `patch_overflows.py` — the layout pass. `\allowbreak{}` inside long `\texttt`
  arguments, `\footnotesize` on natural-width longtables, and three passes added
  in v0.9: shortened running heads, proportional `p{}` columns for wide tables,
  and removal of pandoc's full-width table-cell minipages.
- `manuscript_pcba.tex` — master document (memoir, 11pt, 6×9, twoside).
- `frontmatter_pcba.tex` — half-title, title, copyright, epigraph, TOC.
- `figures_preamble.tex` — the shared TikZ symbol and block library for every
  figure in the book, including the `pics/cas*` component glyphs. **This file is
  the single source of truth for the symbol library**: the companion volume
  *The Component Companion* (`book/CAS_Component_Companion/`) copies it at build
  time rather than keeping its own, so one fix here reaches both books.

## Generated files (gitignored)
`preamble_pcba.tex`, `front_prose.{md,tex}`, `main_body.md`, `body.tex`, and all
`*.aux/*.log/*.toc/*.pdf`, plus `preview/`.

## Build

**Use the driver.** `build_full_book.py` runs the whole pipeline in the one order
that works and refuses to finish on a LaTeX error:

```bash
python build_full_book.py            # -> ../CAS_PCBA_Engineer.pdf
                                     #    ../CAS_PCBA_Engineer_print.pdf
python build_full_book.py --no-index # skip the index marks and makeindex
```

It performs: `build_book.py` → pandoc (`front_prose.tex`, `body.tex`) →
`postprocess_pcba.py` → `patch_overflows.py` →
`publishing/build_indexes.py pcba` → delete the stale `.aux` → `xelatex` →
`makeindex` → `xelatex` ×2 → `verify` the log has no `! ` errors → copy.

Why the order matters, and why each step is there:

- **`postprocess_pcba.py` before `patch_overflows.py`.** The overflow patch
  recognises `\begin{Verbatim}` blocks to skip them; postprocess is what creates
  them.
- **`build_indexes.py` after pandoc, not before.** Index marks go into `body.tex`
  and the markdown sources stay clean.
- **`makeindex` between the xelatex passes.** `\printindex` prints page numbers,
  so the `.idx` must be compiled before the last pass.
- **The `.aux` is deleted every build.** longtable caches column widths there and
  never shrinks them, so a stale cache keeps a narrowed table at its old width.
- **The log is checked for `! `.** `-interaction=nonstopmode` still writes a PDF
  after an error, so a green exit code and an existing output file prove nothing.

## Manual equivalent

```bash
python build_book.py
pandoc front_prose.md -o front_prose.tex -t latex --top-level-division=chapter \
       -f markdown-superscript-subscript --syntax-highlighting=none
pandoc main_body.md   -o body.tex        -t latex --top-level-division=chapter \
       -f markdown-superscript-subscript --syntax-highlighting=none
python postprocess_pcba.py
python patch_overflows.py
python ../publishing/build_indexes.py pcba
xelatex -interaction=nonstopmode manuscript_pcba.tex
makeindex -q manuscript_pcba.idx
xelatex -interaction=nonstopmode manuscript_pcba.tex
xelatex -interaction=nonstopmode manuscript_pcba.tex
cp manuscript_pcba.pdf ../CAS_PCBA_Engineer.pdf
```

## Verification

```bash
python verify_print_margins.py ../CAS_PCBA_Engineer_print.pdf
python ../publishing/check_invariants.py
```

`verify_print_margins.py` measures the finished PDF: for every page it takes the
union of all text spans and vector drawing rectangles and reports the distance
from that ink to each trim edge, with the gutter side chosen by page parity.
`check_invariants.py` runs the cross-title mechanical checks (43 of them) over
all four books.

The plate and schematic figures are audited by the companion volume's own suite
— 17 figures, three audits and a negative control for each. See
`book/CAS_Component_Companion/build/BUILD_README.md`.

## Other artifacts

```bash
cd ../covers && python build_covers.py    # cover wraps (reads each interior's page count)
cd ../covers && python verify_cover.py cas_pcba_engineer_wrap.pdf --pages=809
```

## The companion volume

*The Component Companion* — the illustrated symbol plates, the ten cognitive
schematics and the printable card deck — is a **separate book** at
`book/CAS_Component_Companion/`. It was Appendix J in an earlier draft of this
volume; that framing is gone. Build it with its own driver:

```bash
cd ../CAS_Component_Companion/build && python build_companion.py
```

Notes:
- Sections are auto-numbered by memoir (e.g. 5.8, 24.4); the TOC is kept at
  chapter level. `\mainmatter` resets memoir's secnumdepth, which is why sections
  number regardless of the `secnumdepth` counter in the preamble.
- `patch_overflows.py` pass 5 shortens over-long running heads via memoir's
  `\section[TOC][head]{printed}` form. This changes only the running head: the
  printed heading, TOC entry, PDF bookmark and every page break are untouched, so
  the pass cannot repaginate the book. `build_companion.py` runs the same pass
  against the companion's `body.tex`, so the two books cannot drift apart on
  layout handling.
- The MiKTeX "unsupported version of Windows" line is a harmless warning; the PDF
  still builds.
