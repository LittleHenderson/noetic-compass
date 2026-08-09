# Noetic Topos 2.0 — 17-point audit report

**Subject:** `docs/whitepapers/monograph/noetic_topos2/` (12 chapters + 4 appendices), rendered to
`docs/whitepapers/pdf/MONOGRAPH_NOETIC_TOPOS_2_0_v0.3.pdf`.
**Checklist:** the 17 defect classes characteristic of AI-assisted academic writing.
**Compiled:** 2026-08-09.

Three passes ran against this volume. **181 findings total**, all triaged and resolved.

| Pass | Agents | Findings | Critical | Major | Minor |
|---|---|---|---|---|---|
| 1 — initial audit | 11 | 128 | 11 | 60 | 57 |
| 2 — adversarial verification *of the corrections* | 3 | 19 | 1 | 4 | 14 |
| 3 — confirmatory audit *of the corrected text* | 6 | 34 | 1 | 5 | 28 |
| repair agents | 11 | — | — | — | — |
| **total** | **31** | **181** | **13** | **69** | **99** |

Final build: 5/5 volumes compile, **0 undefined references, 0 undefined citations**, Noetic Topos
overfull boxes reduced 83 → 55.

---

## Coverage by checklist item

Each pass-1 auditor was scoped to explicit issue numbers; pass 3 re-swept all 17 against the
corrected text.

| # | Issue | Swept by | Found | Representative defect |
|---|---|---|---|---|
| 1 | Hallucinated citations | cite-claim-A/B, citations auditor | **0 fabricated** | All 17 bibliography entries web-verified as real, with correct authors/venue/year/volume/pages |
| 2 | Citation-claim mismatch | cite-claim-A/B, citations auditor | 20 | Čech cohomological obstruction credited to Abramsky–Brandenburger 2011, which contains none |
| 3 | Fabricated / too-clean data | data-consistency, math-verification | 39 | "Both sides count 2 by a direct check" — a fabricated verification of a false equality |
| 4 | Stale literature | stale-literature | 3 | Cohomology/contextual-fraction line of work post-2011 unrepresented |
| 5 | Confident vagueness | substance ×3 | 7 | Claims lacking conditions where the subject demands them |
| 6 | No genuine contribution | substance ×3 | 0 | Primer chapters attribute rather than appropriate |
| 7 | Shallow methodology | substance ×3 | 9 | "One verifies" with no computation present or cited |
| 8 | Missing negative space | substance ×3 | 6 | Counted-but-never-named open obligations |
| 9 | Long-range inconsistency | long-range-consistency | 27 | Mac Lane–Moerdijk pinpoint; glossary vs defining chapter |
| 10 | Formulaic structure | style-tells | 4 | Repeated chapter-opener templates |
| 11 | Signature vocabulary | style-tells | 31 | The worth/deserves metadiscourse family |
| 12 | Uniform rhythm | style-tells | 1 | One genuinely monotone paragraph |
| 13 | Empty filler | style-tells | 2 | Announce-then-say constructions |
| 14 | Undisclosed AI use | scholarly-practice | 1 | No disclosure existed; added to `\thanks` |
| 15 | Plagiarism-adjacent paraphrase | scholarly-practice | 3 | Standard definitions tracking source wording unquoted |
| 16 | Wrong disciplinary register | scholarly-practice | 5 | QED tombstones on non-proof design arguments |
| 17 | Figure/equation/table weakness | math-verification, issues-3+17 | 23 | A table's entire result column printing off the page |

---

## The four defects that mattered most

### 1. A false mathematical result, corroborated by five independent auditors
`ch09_finite_theorems.tex` claimed the ACBE witness presheaf separates the two topologies at
**"three of the sixteen contexts"**, supported by a *"direct check"* that *"both sides count 2"* at
triples. Both claims are false.

Recomputed exhaustively in Python: because no RPM piece of any context contains a complete ACBE block,
the matching-family set is a **singleton at all sixteen contexts** — never 2. Gluing therefore fails
wherever α(V) ≥ 1: at **seven** contexts (the two ACBE blocks and four triples at 2-to-1, Ω at 4-to-1).

The volume's own **Appendix C already stated the correct seven-context result**. The book contradicted
itself, and the appendix was the side that was right.

### 2. A table whose entire result column printed off the page
`appC_witness_tables.tex` — the Ω-gluing table overflowed the text block by **320.6pt**, pushing its
final column (the four sheaf verdicts) off the printed sheet. The table exists to report those
verdicts. Source correct, deliverable broken. Fixed to **0.00pt**, confirmed by rasterizing the page.

Three further identifiers were clipped off-page: the formal specification's SHA-256 (ch01), the
theorem-ledger filename (ch09), and the registered certificate check names (ch11) — each an identifier
a reviewer must *read* to verify anything.

### 3. A drafting artifact shipped in the PDF
`ch04_sheaves_modalities.tex` contained a visible mid-sentence self-correction —
*"…is not constantly 1? No: s **is** constantly 1…"* — attached to an unretracted false claim that a
non-presheaf was "separated". The most legible AI-drafting tell found anywhere in the five volumes.

### 4. An exercise asking readers to disprove a chapter's own theorem
`ch05_legacy_collapse.tex` asked for a counterexample to an invariant proved two pages earlier, with a
self-contradicting hint ("include the top as a proper-looking member" — including the top makes it
non-proper). The requested object does not exist.

---

## Defects the correction pass itself introduced

Recorded because they bear on how much to trust automated correction:

- **appD's glossary table went 85pt → 433pt overfull**, pushing the "Where" column — the chapter
  attributions ~30 of the fixes were correcting — off the page. The fix made its own subject invisible.
- **26 double-numbered cross-references** left in ch09 (`Theorem 7.\ref{...}` → "Theorem 7.7.12") after
  a sibling agent normalized the identical pattern in ch08. Produces no LaTeX warning, so a clean build
  never catches it.
- **Three de-tic-ing rewrites damaged the prose**: a verbless fragment, a false apposition, an
  unidiomatic passive. A fourth rewrote three chapter openers into the *same* construction —
  manufacturing the formulaic symmetry (issue 10) the edit was meant to reduce.
- **Two corrections introduced new errors**: ch05 called the countermodel "finite" while ch06 (same
  pass) says it is infinite; appA's "ten → nine contexts" fixed a count to match a list that was itself
  incomplete.

All were caught by the later passes and repaired.

---

## What was checked and found clean

Stated so the absence of findings is legible as coverage, not as a gap:

- **No fabricated references.** All 17 bibliography entries exist and are accurately described. All
  four Stacks Project tags were fetched and confirmed to say what they are cited for.
- **Citation/bibliography set equality** verified in both directions across 90 citation sites — no cite
  without an entry, no entry without a cite, no duplicates. (A 46-entry shared list of which 34 were
  never cited was replaced by a 17-entry per-volume bibliography.)
- **No stale current-state claims.** Every literature-state sentence is a dated, self-scoped epistemic
  label rather than a survey claim.
- **No epistemic regression.** Every hedge, status label, claim boundary and ledger qualifier was
  preserved or strengthened; the corrections *withdrew* two overclaims (ch10's "executable layer
  discharges every quantifier", ch11's Lean rerunnability).
- **No canonical text altered.** TKS/CAS definitional texts and quoted material untouched throughout.

---

## Limits of this audit

- Pass 3 was scoped to survivors and newly-introduced defects, not a from-scratch re-derivation of
  every pass-1 finding.
- Style judgments (issues 10–13) are inherently editorial; the counts above reflect one reading.
- Overfull-box comparison across builds matched on exact point values, which cannot always distinguish
  "new box" from "same box, shifted size". One such misattribution was caught and corrected during
  pass 2; others may remain.
- Three pre-existing overfull boxes outside the finding list were flagged and deliberately not edited.
- No independent human review has been performed. This is machine audit only.

---

*Underlying data: `nt2_audit_findings.md` (128), `nt2_verify.md` (19), `nt2_confirm.md` (34) in the
session scratchpad. Commits: `f427084a` (pass 1 + 2), and the confirmatory pass in this revision.*
