# CAS PCBA Engineer — Changelog

## 2026-09-21 — logic gates are separated from Noetic involution (owner decision OD-A)

The book described Boolean logic gates in Noetic vocabulary. Two defects followed from that, and both are
corrected here. This changes what a board checker must enforce, so it is recorded as its own entry.

- **`XOR` was called a both-active detector.** It is not. `XOR` fires when its inputs *differ*, so it never
  fires when both are active. **`AND`** is the both-active detector. Corrected in `Chapter_10` (the gate
  table, the worked examples and the bench note), `Appendix_B` (the truth-rule table and its failure row)
  and `Appendix_E` exercise 10.4, whose listing now reads `gate conflict: AND< attract, averse >;`.
- **`NOT` was called the involution operator made discrete**, with `NOT< ^2^E >` yielding `^3^E`. A gate
  acts on a true/false firing flag; a Noetic involution acts on a cognitive state. `NOT` is now a Boolean
  complement that maps to a Noetic involution only for a licensed pair. The same correction is applied to
  the op-amp inverting configuration (an arithmetic inversion around a reference, with no automatic Noetic
  flip) and to the Breakdown rule (the flip happens only when it is declared).

Also in this entry:

- **`XNOR` added** as an equivalence detector, in the gate production, the reserved type-name list, the
  component prefix list, the `Chapter_10` and `Appendix_B` tables and the `Appendix_A` quick reference.
- **The Capacitor state literal** is now described as the `^5` composition whose persistence is modeled,
  which ties the datasheet to the authoritative `^5` Female definition.

Known and deliberate: `gate` is both a component prefix and a statement leader. That was already true of
the grammar's two reserved lists (`Appendix_C` §C.2 and §C.12); exercise 10.4 now makes it visible in a
listing. A reader resolves it with one token of lookahead past the colon — a type name followed by `<` is a
component declaration, anything else is the `gate` statement, which always carries `requires`.

## 2026-09-09 — v0.9 (print-quality rebuild; the component library moves out to its own book)

The illustrated component library — the symbol plates, the cognitive schematics and
the printable card deck — is **no longer part of this volume**. It is published as a
separate short book, *The Component Companion*, under
`book/CAS_Component_Companion/`. Its changelog is `book/CAS_Component_Companion/CHANGELOG.md`.

It was Appendix J here for one draft, and that was the wrong shape: a reference you keep
open beside the main volume is a book, not an appendix, and calling it one buried a
40-page illustrated component library at the back of a design text. The appendix is gone;
`build_book.py` no longer lists it, and the only trace left in this volume is a
cross-reference in Appendix C that now names the companion by title.

**One thing is deliberately shared between the two books.**
`build/figures_preamble.tex` — the TikZ symbol and block library — stays here, because this
volume's own schematics use it. The companion copies it at build time rather than keeping
its own version, so `pics/cas*` glyphs have exactly one definition. `build_companion.py`
runs this volume's `patch_overflows.py` against the companion's `body.tex` for the same
reason. Fix a glyph or a layout pass once, and both books get it.

### This volume's own fixes

- **The printed index was missing.** `body.tex` contained zero `\index{}` marks because
  `publishing/build_indexes.py` was not in the build path. The new `build/build_full_book.py`
  runs the whole pipeline in the one order that works (assemble → pandoc → postprocess →
  patch → index marks → xelatex → makeindex → xelatex ×2) and fails on any log line
  beginning with `! `, because `nonstopmode` still writes a PDF after an error. The index is
  back: 181 lines.
- **39 wrapped running heads are gone.** A two-line running head overflows memoir's 13.6 pt
  head slot and raised `Overfull \vbox (13.59999pt too high)` on that recto page. Pass 5 of
  `patch_overflows.py` now shortens the running-head mark for the 76 over-long section titles
  using memoir's three-argument `\section[TOC][head]{printed}` form, so the printed heading,
  TOC entry, PDF bookmark and every page break are untouched. The mark is built from pandoc's
  plain-text `\texorpdfstring` argument and re-escaped for text mode — without that escape
  step, titles containing `^` or `_` compile *with* two silent errors. Result:
  `Overfull \vbox` 39 → **0**, wrapped heads 39 → **0**.
- **Tables that ran into the gutter now wrap.** pandoc emits `@{}llll@{}` for a pipe table and
  an `l` column never wraps, so sentence-length cells made the table wider than the measure;
  separately, pandoc wraps grid-table cells in `\begin{minipage}[b]{\linewidth}`, which inside
  a longtable means the *table* width. Both are fixed in `patch_overflows.py` (proportional
  `p{}` columns for all-`l` tables with long cells; redundant minipage wrappers removed).
- **One cell token was widened into a phrase.** The CSB test-point table carried
  `safety_decision=PASS` as an unbreakable token in a quarter-width column, which pushed a
  line 15.6 pt past the fore-edge line. It is now prose.
- **`build/verify_print_margins.py` is new** — it measures the finished PDF's ink against each
  trim edge, per page, with the gutter side chosen by page parity. This changelog has claimed
  "0 margin violations" since v0.8.1, but **no script that measures margins existed**; the claim
  rested on a KDP previewer run. Measured before the table fixes: gutter **0.513 in** where the
  layout promises 0.9375 in — sentence-length cells in non-wrapping columns were pushing tables
  into the spine. After: **0.9001 in on page 356**, and the narrowest outside margin 0.283 in →
  **0.381 in**. KDP requires 0.875 in inside at this page count. The claim is now measured
  rather than asserted.

### Interior

**781 pages**, 0 LaTeX errors, 0 overfull vboxes, 0 missing characters, index restored, 41
overfull hboxes remaining — all pre-existing, all in Chapters 3/9/18/19/21/23 and Appendices
C/D/E, and none of them crosses a KDP limit. The page count fell from 804 (and 809 with the
appendix) because the component library is no longer in this volume.

### Covers

`book/covers/build_covers.py` had been hard-coding 743 pages while the published paperback was
783, so the cover on file was a whole revision narrow. It now reads the page count from the
built interior (`interior_pdf`), gained a `SPINE_TEXT_MIN_PAGES` rule (KDP prints no spine type
below 100 pages), and gained a checker, `book/covers/verify_cover.py`, which measures the
finished wrap for text collisions, barcode-zone intrusion and trim overflow. PCBA wrap
regenerated at 781 pages: spine **1.7588 in**, wrap 14.0088 × 9.25 in. Confirm the spine in
KDP's cover calculator against the uploaded interior before publishing.

## 2026-08-14 — v0.8.1 (KDP print-compliance rebuild; published)

Published on Amazon KDP: Kindle eBook (from the existing v0.8 EPUB, $9.99, DRM on)
and 6×9 paperback (ISBN 9798192600276, $34.99, worldwide, matte). Both in KDP review.

The paperback interior is a print-compliance rebuild of v0.8 (`CAS_PCBA_Engineer_print.pdf`,
783 pages vs 787). KDP's Print Previewer rejected the v0.8 PDF: insufficient gutter
(787 pages require 0.875" inside margin; the build's memoir layout produced ~0.868"),
chapter numbers hanging into the gutter (`hangnum` style), and ~20 pages of unbreakable
inline-code tokens and wide tables/TikZ protruding past the text block. Fixes, all in
`build/` (content unchanged — layout only):

- Gutter 0.875" → 0.9375", fore-edge 0.625" → 0.5" (`preamble_pcba.tex`).
- `\chapterstyle{hangnum}` → `\chapterstyle{default}` (numbers inside the block).
- `build/patch_texttt.py` + `build/patch_overflows.py`: insert `\allowbreak{}` after
  delimiters (`= | , ; → / › ( ·` and `\_`) inside long `\texttt` args and after `→`
  in prose/table cells (Verbatim and TikZ excluded); ten natural-width longtables set
  `\footnotesize`; the tp_lock capture table given wrapping p-columns; the
  domain-layers TikZ figure wrapped in `\resizebox{\linewidth}{!}`.
- Gotcha for future rebuilds: longtable caches column widths in the `.aux` and never
  shrinks them — delete `manuscript_pcba.aux` when narrowing a table.

Verified programmatically: 0 margin violations across all 783 pages; KDP previewer
passed with no errors. Cover wraps regenerated at exact spine widths (paperback spine
1.7633" = 783 × 0.002252"). Hardcover is NOT possible on KDP at this length (hardcover
maximum is 550 pages for B&W at every trim size); IngramSpark is the route if a
hardcover edition is wanted.

## 2026-08-08 — v0.8 (external-audit corrections: the CSB safety chain, the CCDL grammar)

An external audit — the five-volume *Project Coherence* monograph set, working from the
published build `src-pcba-engineer-20260726` — found real defects in this book, most of
them on the Cognitive Safety Board, the one artifact built across the whole volume. They
are fixed here. Findings, verdicts, and page anchors:
`docs/reference/PCBA_BOOK_DEFECTS_FROM_MONOGRAPHS.md`.

**The CSB safety chain (Ch 18 and Appendix D, plus the tables and prose that quote them).**
- **The red fuse could not trip.** The red output stage carries `sat = 0.1`, which bounds
  its output unconditionally, and nothing on the clamp-to-fuse path amplifies — yet the
  fuse in series with it was published at `threshold = 0.9`. The protective crossing was
  unreachable on every possible input. The threshold moves to **0.05**, below the clamp,
  so a saturated red path actually crosses it. The contradictory pair was printed twice —
  chapter listing and reference appendix — so the typo defence was never available; both
  listings are corrected, along with the Ch 18 walk-through prose, the BOM table, the
  verification step, the board datasheet summary, and the matching Appendix D table and
  footnotes.
- **`beta = infinity` becomes `beta = 10`.** A non-finite parameter in a language whose
  validator requires finite ones. The comparator idealization that the infinite-gain limit
  was teaching is kept — it is the right way to think about a hard-decision stage — but the
  listing is now buildable. The value is the book's own: the Ch 18 red-path Bench Note
  already observed that with `sat = 0.1`, anything above about β = 10 is indistinguishable.
  Appendix D no longer asks the reader to repair the listing before using it.
- **The fuse now has a fail-closed latch specification.** The book asserted a latch and
  defined no state machine for one — no states, no transitions, no behaviour on a retry or
  on an unreadable input. Specified now, and specified fail-closed.
- **Fuse polarity is stated.** The book never said which way the fuse cuts. Tripping severs
  the *output* path; it must never sever the refusal path it exists to protect.
- **Saturation does not latch — corrected.** The red stage's saturation clamp is a
  memoryless plateau: it holds while the input holds and releases when the input drops, so
  a maximal alarm can de-assert under oscillation. The latch is the fuse, and only the fuse.
  Sentences that credited saturation with latching the decision are rewritten.

The last three are independent of the arithmetic — they were defects at any threshold — and
the unreachable fuse was hiding all of them. A board whose fuse never fires tests
*vacuously* safe.

**CCDL (Appendix C).**
- **Nineteen statement leaders had no production anywhere in the published grammar**, while
  the book's own five-board reference corpus used all of them: the CSB body items, the
  CMB's `charge` / `select` / `discharge` / `refresh` / `scan`, and the CPMB's fourteen
  power-management forms. The corpus was using more statement vocabulary outside the printed
  EBNF than inside it. All nineteen now have productions.
- **The `board` / `circuit` fork is decided, and recorded as a decision.** The audit was
  right that the book had never settled whether a `board` block may carry circuit content or
  whether the CSB listing should have said `circuit` — two repairs that produce *different
  languages*, which is why no implementer should have been left to choose. Settled in favour
  of the corpus: the board-level statements are `circuit_item`s, because that is how the
  book's own boards are written.
- **The mirror expression syntax is grammatical.** `mirror bias_mirror:
  replicate(shared_bias) -> [cjt_l, cjt_r]` failed three ways at once against an RHS that
  had to be `type_name<arg_list>`: call-shaped syntax, an arrow, and a bracketed target
  list. The expression grammar now produces all three.
- **A construct coverage matrix is published**, mapping every construct the reference boards
  use to the production that produces it. This is the artifact whose absence let the
  divergence ship: the appendix and the corpus had evolved on different schedules, and
  nothing was checking them against each other. Its claim is deliberately narrow — surface
  syntax only. It says each printed construct is produced by the printed grammar. It says
  nothing about semantic validity, and it is not a substitute for the compiler.

**Components (Appendix B).**
- **The `Fuse` datasheet gains a design rule: *Reachability*.** A trip threshold means
  nothing on its own; it is meaningful only against what drives it. `threshold < min(sat,
  clamp, …)` over every upstream stage on the input path — otherwise the fuse is decoration.
  Gain does not rescue it, because `sat` bounds the stage output *after* β. The Zener
  datasheet now carries the same rule for `breakdown`. This is what would have caught the CSB
  defect at design time, and the reason nothing did is worth naming: the validators check
  values one at a time, so a 0.1 clamp and a 0.9 threshold each pass on their own, and the
  contradiction between them is invisible to a per-value check.

**Gain: two definitions, unbridged (Appendix I).** This book defines β as a ratio of
Fisher-Rao displacements (Ch 3, Ch 9); the CAS-Ohm operationalization addendum computes gain
as a Jacobian. They are not two notations for one quantity — no chain rule composes the
Fisher-Rao ratios along a cascade, and identifying them requires assumptions nobody has
stated. Rather than quietly pick one, Appendix I now sets the two profiles side by side,
lists what a bridge between them would have to assume, and requires any reported β to name
the method that produced it. Until that bridge exists, figures computed under the two
definitions are not comparable. Registered as `OHM-CONFLICT-GAIN-DEFINITION`, still open.

**Front matter.** New section, *What This Book Is — and What It Is Not*, closing the Preface
and standing before *How to Use This Book*. It states positively what the book is (a design
text and a teaching reference), what it is not (a certification, a measurement authority, a
validated safety standard), and — the part that matters at the bench — that the worked
listings are pedagogical examples a real build must validate, not drop-in designs. The
unreachable fuse is cited there by name. A book that has just found a dead protective element
in its own flagship listing has the strongest possible argument for checking listings, and a
weaker one for any disclaimer. The copyright block points forward to it, and the conventions
list in *How to Use This Book* points back.

Two build-side follow-ups, neither of them content: the build slices front prose from
`## Preface` onward, so this is the earliest position from which the section reaches the
printed page without a build change — promoting it to a front-matter chapter of its own,
which it deserves, is one line in `build/build_book.py` beside the two promotions already
there. And the typeset copyright page lives in `build/frontmatter_pcba.tex`, which still
wants the same forward pointer the source copyright block now carries.

**Changelog hygiene.** The audit also recorded that this file's most recent label predated
the build it shipped with: the audited PDF carried v0.6 / 2026-06-18 as its latest entry
while itself dating from 2026-07-26. That revision now has the entry below, reconstructed
from the repository history. The audited build is identified as:

    src-pcba-engineer-20260726 — 743 pp, 6×9
    SHA-256 294320B39FA521EAC086E99E2D9DB913E2B6CFF0754FF82DB1EF966424566274

recorded here so that external page anchors resolve against the right bytes. Hashing the
book identifies it; it does not endorse it.

Source revision only — **rebuild the PDF and EPUB from `build/` before redistribution.** The
shipped artifacts predate every correction above.

## 2026-07-26 — v0.7 (published build — entry written retroactively)

*This revision shipped with no changelog entry, which is itself one of the audit findings.
Reconstructed from the repository history (`8f1c8309`, `99044f60`, `29eafed7`, `0923146b`)
rather than from notes taken at the time, so it is a summary and not a full record.*

Defects surfaced by a four-eval run over the manuscript and a reference-board eval:
- **Ch 21 / Appendix D** — the `nearest()` example published a ranking no reader could
  reproduce: under one-cell-per-state addressing every pairwise Fisher-Rao distance is
  identical, which the book's own open-simplex constraint (`p_k > 0`) already implies.
  Replaced with computed values from a worked composition, plus a Bench Note on why
  similarity reads as proximity only when addresses are full distributions.
- **Ch 22 / Appendix D** — two of four regulators dropped out on the wrong rail (`e_reg`
  targeting F6 on an F5 spec, `o_reg` targeting F5 on an F3 spec), against the rule Ch 22
  itself states. Duplicated verbatim in the appendix, so not a typo. All four now agree.
- **Ch 14 / Ch 22** — the brownout thresholds did not survive the conversion between the
  normalized presentation and the +12 V one. Ch 22 moved to 4.2 V / 5.4 V so the
  multiplication is reproducible on the page.
- **Appendix E** — the Ex 22.2 answer key gave a flat sequencer gate where Ch 22 uses
  per-domain tolerances. An answer key that disagrees with its chapter teaches the wrong
  thing.
- **Appendix C** — 53 of the 64 statement keywords the book uses were undocumented, and
  `comp_kind` was referenced in the EBNF but never enumerated. Keyword coverage brought to
  64/64. (That closed the *keyword* gap; the *grammar* gap it left behind is A1 above, fixed
  in v0.8.)
- **Ch 18** — the red-path `beta=infinity` was flagged as a comparator idealization with a
  Bench Note directing a large finite gain, and the unconstrained `Fuse` action (a board
  with `action=warn` compiles clean and still calls itself a CSB) was written up as a manual
  verification step. Both are partial repairs; v0.8 finishes them.
- **`build/check_invariants.py`** — 32 mechanical checks added across the three titles, each
  one corresponding to a defect that was actually present in a manuscript. Cheap
  string-and-arithmetic checking, no substitute for reading the book, but the specific
  mistakes already made cannot come back unnoticed.

Interior rebuilt: 743 pp, 6×9, fonts embedded, zero missing glyphs; cover spine and EPUB
rebuilt to match.

## 2026-06-18 — v0.6 (recipe coverage complete: CMB + CPMB)

Added the final two board recipe views, so all five reference boards now carry a
worked production-semantics analysis:
- **Ch 21 (CMB)** — "Recipe View: What Produces a Recall": `Ω_recall =
  1·^1^C + 2·^5^E + 1·^7^C`. Tip-of-the-tongue worked case where faded stored
  charge (`^5`) is the limiting reagent (`Y_T=0.30`) despite a perfect address;
  fix = rehearse (feed `^7^C`) or store deep. False recall via near-neighbor
  addressing named as the leakage (`Λ`) path, vs lacunarity (empty cell) and
  inversion.
- **Ch 22 (CPMB)** — "Recipe View: What Caps a Session": `Ω_session =
  2·F3 + 1·F6 + 1·F7`, with F3 Vitality the limiting reagent (`Y_T=1.50`) — the
  reason F3 is the master rail with the dedicated brownout detector. Thermal load
  framed as inhibitor `ι`, sequencing as a hard gate, efficiency as catalyst `κ`.
  Closes the loop back to Chapter 14, where recipes first appeared beside the
  power budget.

All five boards (CSB, COB, CDAB, CMB, CPMB) now have a recipe view. Rebuilt PDF
(6×9). Canonical Noetic names preserved; CCDL listings unchanged.

## 2026-06-18 — v0.5 (two more worked recipes: COB + CDAB)

Extended the recipe/limiting-reagent tooling (Ch 14) onto two more boards:
- **Ch 19 (COB)** — new "Recipe View: What Produces Entrainment": the PLL
  outcome `Ω_entrainment` as `Θ = 1·^1^C + 1·^4^E + 2·^3^O`. Worked case shows a
  high-insight, high-Q compulsion where behavioral plasticity (`^3^O`, the VCO)
  is the limiting reagent (`Y_T=0.30`) — the structural form of "I understand it
  and still can't stop." Therapy = feeding the bottleneck (lower L widens the
  lock range = raises effective `^3^O`); lock-range = the η-preserving operating
  condition; steady reference = catalyst, chaos = inhibitor.
- **Ch 20 (CDAB)** — new "Recipe View: What Produces a Synthesis": `Ω_synthesis`
  (a `×` fusion) as `Θ = 1·^1^C + 2·^4^P + 1·^6^C`. Worked stalemate case where
  the integrative drive (`^4^P|T`, will-to-unify) is the limiting reagent
  (`Y_T=0.25`) — the well-characterized disagreement that never resolves. Names
  the **leakage** path too: poor CMRR contaminates the difference signal (present
  but wrong = `Λ`), so good CMRR is a precondition for sound synthesis.

Rebuilt PDF (6×9). Canonical Noetic names preserved; CCDL listings unchanged.

## 2026-06-18 — v0.4 (recipes / production semantics developed)

Paid off the Chapter 2 recipe forward-promise and made recipes a first-class
circuit-design tool:
- **Ch 14** — new section *"Recipes and the Limiting Reagent: What Caps the
  Outcome"* developing the full v7.6 production semantics as circuit analysis:
  recipe `Θ`, state vector `S`, **theoretical yield** `Y_T = minᵢ(xᵢ/aᵢ)`,
  **limiting reagent** `L`, **actual yield** `Y_A`, **efficiency** `η`, **excess
  capacity** `ε`, **leakage/side-reaction** `Λ` (vs lacunarity vs inversion), and
  **catalyst/inhibitor** `κ/ι` — tied to the chapter's power-budget/efficiency
  material. Includes a worked **CSB refusal recipe** showing that the Chapter 18
  starvation attack is exactly a limiting-reagent failure (principled aversion
  starved below the saturation-lock threshold), with the redundant-register fix
  reframed as raising the floor on the limiting reagent.
- **Ch 2** — the recipe forward-reference now points concretely to Chapter 14
  and names the limiting reagent.
- **Ch 14 exercises** — added the long-promised power-dissipation exercise (14.4,
  which Appendix E already answered but the chapter had never listed — a
  pre-existing phantom-answer gap, now closed) and a new limiting-reagent
  exercise (14.5); Appendix E gains the 14.5 worked answer.
- **Appendix G** — the Recipe (Θ) glossary entry expanded to define the whole
  production-semantics family.

Rebuilt PDF (6×9). CCDL code listings unchanged; canonical Noetic names preserved.

## 2026-06-18 — v0.3 (vector charts + multilayer-board diagram)

Added five more vector figures, replacing ASCII sketches / filling gaps where
the text described a chart but had none. Charts use `pgfplots` (added to
`build/figures_preamble.tex`); all are grayscale-legible (color + line style):
- **Ch 9** — CJT characteristic-curve family: effect-vs-cause traces at bias
  {0.2, 0.4, 0.6, 0.8}, with the load line (`R=30`) and the labelled Q-point
  (0.43, 0.45), cutoff/active-region/saturation-knee annotations.
- **Ch 16** — two-panel Bode plot: magnitude roll-off to the 0 dB crossover and
  phase to −180°, with gain margin (~20 dB) and phase margin (~30°) marked.
- **Ch 12** — four filter frequency responses (low-pass / high-pass / band-pass
  / notch) on one log-frequency axis, with the −3 dB line and fc/f0 markers.
- **Ch 6** — forgetting curve: stored charge vs time under the chapter's
  `(1−leakage)^t` model, a deep memory (leakage 0.001) vs a leaky one (0.05),
  half-life marked.
- **Ch 17** — multilayer cognitive-board illustration (TikZ): the four Domain
  layers (P/C/E/O) with descent vias v1–v3 and the distinct upward feedback
  via v4 (`^9^O→^0^P`). The CCDL `board { … }` listing was left as code.

Book now carries **12 vector figures**. Rebuilt PDF: 699-page 6×9, zero TeX
errors, zero missing glyphs.

## 2026-06-18 — v0.2 polish (consistency, answer key, vector schematics)

Three review/upgrade passes over the v0.1 draft:

**1. Cross-chapter consistency audit + fixes.** A full audit confirmed the CSB,
the five boards, the Drive rails, the Dials, and the running amplifier are
consistent across chapters and Appendix D. Five surgical fixes applied:
- Ch 21: address-decoder block no longer glosses `^1^C` as "differentiation"
  (now canonical "Mind") — the lone Noetic-naming drift in the book.
- Ch 5: voltage-divider worked build — corrected `V_expand` to 0.40 so the
  formula matches the "expansion is the minority partner" prose.
- Ch 14: reconciled the brownout thresholds with Ch 22/App D (normalized 0–1
  here vs +12V / 2.5V trip on the CPMB, with an explicit note); rewrote the
  thermal response from two stages to the canonical three tiers (Warning −25% β
  / Critical force `^0^P` rest ~5min / Emergency all-CJT cutoff); pinned the
  brownout β-derate to 0.5; updated the datasheet and Key Takeaways to match.

**2. Appendix E answer-key verification + fixes.** Every chapter's exercises
were checked against the answer key (104 answers, 4/chapter — no gaps, no
phantoms). Three corrections: Ch 22 Ex 22.1 named the wrong +12V rails (F3/F7,
not F3/F5) and carried a self-contradicting note; Ch 2 Ex 2.4 mis-described a
forward E→P move as the sanctioned O→P feedback path.

**3. Vector schematics.** Replaced the main ASCII block diagrams with
professional TikZ figures (true vector, native to the LaTeX pipeline), domain-
colored (P gold / C blue / E red / O green): the CJT terminal diagram (Ch 3),
the five board signal-flow diagrams (CSB Ch 18, COB Ch 19, CDAB Ch 20, CMB
Ch 21, CPMB Ch 22), and the deployment ladder (Ch 25). Styles live in
`build/figures_preamble.tex`; CCDL code listings were left as code.

Rebuilt PDF: 695-page 6×9 paperback, zero TeX errors, zero missing glyphs.

## 2026-06-18 — v0.1 full draft + designed PDF

Wrote the complete first draft of *CAS PCBA Engineer: Designing Cognitive
Circuits with the Cognitive Architecture System*, following `CAS_PCBA_Engineer_BOOK_PLAN.md`
and the `docs/working/CJT_PCBA_IMPLEMENTATION_BLUEPRINT.md` reference designs.

**Content (~169k words across 36 Markdown files):**
- Front matter (`00_Front_Matter.md`): title, copyright, preface, how-to-use.
- 26 chapters in 5 parts:
  - Part I — Foundations (Ch 1–4): why circuits, CAS notation in one chapter,
    the transistor → CJT, first cognitive circuit.
  - Part II — The Component Library (Ch 5–10): resistors, capacitors, inductors,
    diodes, the CJT deep dive, special-purpose components.
  - Part III — Circuit Design (Ch 11–16): amplifiers, filters, oscillators,
    power management, mixed-signal, feedback systems.
  - Part IV — Cognitive Circuit Boards (Ch 17–22): the CCB design process and
    the five reference boards — CSB, COB, CDAB, CMB, CPMB.
  - Part V — Deployment & Governance (Ch 23–26): testing, debugging, production
    deployment, certification/governance.
- 8 appendices (A–H): notation quick-reference, component datasheets, CCDL
  language reference, consolidated CCB reference designs, exercise answers, lab
  setup guide, glossary, further reading.
- `STYLE_GUIDE.md`: internal authoring contract (canonical Noetic notation,
  voice, chapter template, anti-drift rules) — not part of the shipped book.

**Design conventions held throughout:**
- Canonical Noetic names only (Idea, Mind, Positive, Negative, Vibration,
  Female, Male, Rhythm, Above/Cause, Below/Effect) — no Scheme-A/B/C drift.
- v7.7 operator discipline (`+` / `×`-with-named-Ω / `|⟨…⟩`).
- Honesty: CCDL/compiler presented as a specified design (per the implementation
  blueprint roadmap); all parameters are design choices, no fabricated run or
  benchmark results; USPTO Provisional #64/037,173 stated as real.
- Running spine: the Cognitive Safety Board (CSB) is built across the book.

**Designed PDF:** `CAS_PCBA_Engineer.pdf` — 695-page 6×9 trade paperback,
memoir/XeLaTeX, Palatino body, DejaVu Sans Mono code, clean TOC, numbered
chapters/sections, part dividers. Reproducible via `build/` (see
`build/BUILD_README.md`). Compiles with zero TeX errors and zero missing glyphs.

**Status:** v0.1 complete draft. Suggested next passes — technical review of
worked CCDL builds for cross-chapter parameter consistency; verify all
Appendix E answers against final exercise text; integrate any figures/diagrams
beyond the ASCII schematics; copyedit pass.
