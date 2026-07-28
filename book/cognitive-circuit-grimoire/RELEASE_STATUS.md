# Cognitive Circuit Grimoire — Release Status

## Accepted artifact

The canonical release artifact is the 6 × 9 inch digital PDF master:

- File: `Cognitive_Circuit_Grimoire.pdf`
- Title: *The Cognitive Circuit Grimoire*
- Subject: *Designing Cognitive Circuits with the Cognitive Architecture System*
- Author: Little Henderson
- Pages: 908
- Size: 2,672,454 bytes
- SHA-256: `99AC4170929C48F82C3D2FA81AABA3798C181EF32B3CDCC4C5E7E2D7C52F923D`
- Built: 2026-07-28
- Page geometry: 432 × 648 points (exactly 6 × 9 inches)
- PDF version: 1.5
- Producer: XeLaTeX (memoir, Palatino Linotype)
- Fonts: embedded and subset

This is an accepted visual digital master. It is not a tagged accessible PDF.

## Acceptance evidence

The canonical command is:

```powershell
python book/publishing/build_all.py grimoire
```

The accepted build completed every required stage and copied the PDF only
after its gates passed:

- 24 of 24 canonical chapters present.
- 164 exercises matched to 164 worked answers, with no missing, extra,
  duplicate, reordered, placeholder, or short answers.
- 112 authored figure markers matched to 112 unique figure assets, with no
  missing, orphaned, or duplicate assets.
- All 112 standalone figures compiled.
- All 249 generated longtables passed the two-pass regression suite, with no
  material overfull boxes and an 8-point minimum table type size.
- CJT lint: 57 checked, 8 deliberate counterexamples skipped, 2 documented
  exceptions, and 0 violations.
- Cross-reference validation: 0 problems.
- Index: 82 entries after 24 TeX control-word-space normalizations.
- Final log: 0 missing glyphs, unresolved references, unresolved citations,
  rerun warnings, material overfull boxes, oversized floats, empty plots, or
  running-header warnings.
- Final layout: 10 overfull hboxes total, none over 2 points; maximum
  1.88060 points. No overfull vboxes.
- Exact authored List of Figures order and labels verified.
- Independent text extraction found 164 worked-answer headings, 112 figure
  captions, and no stale-part, stale-chapter, TODO, TBD, FIXME, or placeholder
  markers.
- The final front-matter render keeps both `About the Author 859` and
  `Index 861` together on contents page xxiv; the List of Figures begins on
  page xxv without an orphaned contents leaf.

The split Markdown manuscript, generated assembly files, TeX templates, figure
sources, validators, and publishing scripts in this directory and
`book/publishing/` are the canonical source chain.

## Excluded legacy previews

`Cognitive_Circuit_Grimoire.html`, `manuscript.html`,
`Cognitive_Circuit_Grimoire.epub`, and the existing cover HTML files predate
the accepted PDF build. They are legacy previews and are not release artifacts.
The monolithic `COGNITIVE_CIRCUIT_GRIMOIRE_COMPLETE.md` is archived and
superseded by the split manuscript.

## Open print-production gate

Status: `OPEN`.

At 908 pages, this 6 × 9 inch interior exceeds Amazon KDP's current 828-page
maximum for a black-ink, white-paper paperback and the lower limits for the
other relevant print options. It must not be described as KDP print-ready.
See the official [KDP paperback submission guidelines](https://kdp.amazon.com/en_US/help/topic/G201857950).

Closure requires an explicit publishing choice:

1. Reflow a single volume at 10-point body type and rebuild it through the full
   validation and visual-QA pipeline; or
2. Split the book into multiple volumes, preserving the present readable type
   size.

The split-volume option is recommended for readability. Cover and spine files
must be regenerated only after the final page plan is selected.
