# Journal Submission Package

This directory contains a journal-style LaTeX package derived from
`peer_review/TKS_v7_4_REFEREE_DEFENSIBLE_PEER_REVIEW.md`.

## Venue Assumption

The working venue assumption is **Applied Categorical Structures**. That choice
fits the present version of the manuscript because the paper is framed as a
strictly mathematical note centered on:

- a finite concrete category,
- a Grothendieck topology and sheaf topos, and
- a narrowly stated information-geometric layer.

The paper is intentionally conservative. It avoids speculative claims, treats
the axioms as proposed assumptions, and states that empirical validation of any
assessment use would be future work.

The source uses a portable `amsart` setup so it can be built immediately on a
standard TeX installation. If a journal class is later required, the current
structure should transfer with mechanical formatting edits.

## Files

- `main.tex` - manuscript source
- `references.bib` - BibTeX database for the cited standard references

## Build

Recommended manual sequence:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

If `latexmk` is configured locally, this also works:

```bash
latexmk -pdf main.tex
```
