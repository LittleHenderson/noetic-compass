# Reality Engineering — Changelog

## 2026-08-14 — KDP print-compliance rebuild (v-print1)

Interior rebuilt for KDP paperback publication (`build/manuscript_tks.pdf`, 793 pages
vs 801): gutter 0.875"->0.9375", fore-edge 0.625"->0.5", `hangnum`->`default` chapter
style, all 245 lowercase `verbatim` blocks converted to breaking fvextra `Verbatim`,
texttt/underscore-run/em-dash break-point insertion, four `\sloppy` spot fixes.
Verified 0 margin violations across all 793 pages. eBook (EPUB, unchanged content)
and paperback staged for KDP publication. See patch scripts in `build/`.


