# Building *The Superiority of TKS*

Produces the designed 6×9 trade-paperback PDF from the repaired manuscript.

## Toolchain
- **pandoc** ≥ 3 (Markdown → LaTeX)
- **XeLaTeX** (MiKTeX / TeX Live) — Unicode + fontspec
- **Python** 3 (repair + assembly)
- Fonts: **Palatino Linotype** (body), **DejaVu Sans Mono** (ASCII diagrams —
  it has the box-drawing glyphs Consolas lacks), **DejaVu Sans** (zodiac signs,
  which appear in 166 lines of running prose), **Times New Roman** (the Hebrew
  in the Golem chapter).

## Files

| File | Role |
|---|---|
| `../SOURCE_ORIGINAL.md` | Untouched input, sha256 `cac21411…4806`. Never edit. |
| `repair_manuscript.py` | Reorders, renumbers and de-scaffolds → `../MANUSCRIPT.md` |
| `build_book.py` | Patches the shared preamble, runs pandoc + XeLaTeX twice |
| `frontmatter_tks.tex` | Half-title, title, copyright, dedication, TOC (hand-written) |
| `manuscript_tks.tex` | Master document (memoir, 11pt, 6×9, twoside) |
| `../MANUSCRIPT.md`, `preamble_tks.tex`, `body.tex`, `*.aux/log/toc/pdf` | Generated |

## Build

```bash
python build_book.py
```

That runs the repair, patches the preamble, converts, and typesets. Output
lands at `../The_Superiority_of_TKS.pdf`.

## What the repair does, and why

The source is three draft layers concatenated in the wrong order. Forensic
analysis hashed 2,716 paragraphs and found **zero** duplicates; cross-region
5-gram Jaccard is 0.0000. Almost nothing is redundant — the book was
structurally disordered and cosmetically unfinished. Under 2% of the prose is
removed.

- **Order.** Layer 1's own appendices and its terminal conclusion sat at PDF
  262–283, so a reader hit "Now Go Build Something" a third of the way in and
  then found 263 more pages. Appendices move to the back; the conclusion folds
  into the Epilogue.
- **Numbering.** Five chapters carried no number. Chapter 20 (a thin 1,309-word
  workshop set, superseded 15× by Part VI) is dropped and everything after
  renumbers. Result: Chapters 1–27, each appearing exactly once.
- **Appendices.** Two colliding A–E series plus a stray F–G, relabelled to a
  single A–L run. Appendix B's heading had been lost entirely — its content
  survived headless between A and C — and is restored.
- **Parts.** Parts II and III were never declared in the body and two different
  sections both called themselves "PART V". Now I–VII, no collisions.
- **Scaffolding.** 25 drafting stamps, the page-break comments and the terminal
  production-statistics block are removed, along with ~20 decorative emoji that
  would print as blobs in a black-and-white interior.
- **Headings.** Like the CAS manuscripts, this source marks headings with a
  single leading space rather than `#`. 426 are promoted so the book has real
  navigation. Fenced blocks are tracked and left verbatim.

### One correction worth recording

An early pass deleted all 516 code-fence lines on the assumption they wrapped
nothing — the previous PDF printed them literally, which looked like stray
markup. That was wrong. They are **258 correctly paired blocks**, all with
content, 33 of them holding ASCII box-drawing diagrams. The old PDF printed
them literally because that build never ran the Markdown through a renderer.
The fences are load-bearing and are now preserved.

## Known constraints

- **817 pages.** KDP's ceiling for a black-and-white paperback on white stock
  is 828, so this fits with ~11 pages of headroom. Leading is set to 1.13 to
  achieve that; do not loosen it without re-checking the page count. Hardcover
  is not available at this length.
- **The index has no page numbers.** It lists topics rather than locations and
  must be rebuilt against final pagination before release.
- Section numbering is on (memoir's `\mainmatter` resets `secnumdepth`). For an
  800-page operating manual this is useful — it gives the index something to
  point at.
