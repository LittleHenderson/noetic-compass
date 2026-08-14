# Thinking in Cognitive Architecture — print compliance notes

## 2026-08-14 — KDP print-compliance rebuild

`latex/manuscript.pdf` rebuilt at 800 pages (was 798): gutter 0.9375", default
chapter style, `\emergencystretch` and global `vset{breaklines,breakanywhere}`
added (source preamble had neither), memoir TOC `\setpnumwidth`/`\setrmarg` fix,
two TikZ labels given `text width`, five overflowing display equations wrapped in
`esizebox`, appendix J code-comment lines split. Verified 0 margin violations
across all 800 pages. Note: `latex/preamble.tex` is the shared CAS preamble —
these fixes benefit future builds of all three books.
Cover: user's cinematic wrap re-composited for the 800-page spine
(spine band resampled 127.45pt -> 129.72pt) -> Downloads/
thinking_in_cognitive_architecture_cinematic_wrap_print.pdf.
