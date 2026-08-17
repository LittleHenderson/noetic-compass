# tksCAS — Changelog

Monorepo-level log. Subprojects keep their own changelogs
(`cas-forex/CHANGELOG.md`, `noetic-compass-scaffold/noetic-compass/CHANGELOG.md`,
`book/CAS_PCBA_Engineer/CHANGELOG.md`). This file records cross-cutting campaign milestones.

## 2026-08-17 — Gate 5 AWS package: durable backup + version-controlled regression guard

Two receipts landed for the Gate 5 staging package, both offline and $0.00.

- **Durable backup of the triple-audited GO package.** The frozen one-hour-session
  package `aws_cloudshell_unarmed_20260818` (identity `525365c4…`, archive 89,510 B /
  `a843f37e…`) previously existed only in the Codex build dir plus a volatile Temp
  scratchpad. It is now backed up to `D:\tksCAS-archive\project_coherence_gate5_one_hour_package_20260818\`
  with a `BACKUP_RECEIPT.md` and 3-way sha256 confirms — including a round-trip that
  re-extracts the D: archive and re-verifies all 18 member rows byte-exact.
- **Regression guard brought into git.** New `tools/aws_gate5/known_live_failure_lint.sh`
  encodes the three defect classes that each killed a package generation *live* after
  all static audits passed: C1 PowerShell `Test-Path` bound to a bare `-or` (20260815),
  C2 a script that both requires/pins root and calls `sts assume-role` (20260816, live),
  C3 an STS/role duration knob >3600s illegal for role-chained CloudShell creds
  (20260817, live). Positive-control calibrated: the verdict grid is strictly monotone
  and matches the real failure history — 20260815/16/17 each FAIL on their live class,
  the GO package PASSes all three. It is a floor to run before the full triple audit,
  not a substitute. Transcript committed at `tools/aws_gate5/CALIBRATION_EVIDENCE.txt`.

Statuses unchanged: Gate 5 OPEN / KEEP_OPEN; Stage C DESIGN_ONLY / UNAUTHORIZED;
corpus 0/960. Staging still awaits the owner's fresh `stage AWS now` bound to
`525365c4…`, with paid compute and final deletion as separate confirmations.

## 2026-08-08 — Noetic Topos 2.0 monograph: audit + corrections + adversarial verification (final volume)

Completes the five-volume audit campaign. 11 auditors → 128 findings (11 critical,
60 major, 57 minor); corrections applied by 4 parallel agents; then a 3-agent
ADVERSARIAL VERIFICATION pass over the corrections themselves, which found 19
residual defects, repaired by 3 further agents. 21 agents total on this volume.

Critical mathematical corrections (all independently recomputed in Python before
applying, and again during verification):

- **ch09 RPM-gluing failure count — wrong, found by 5 independent auditors.**
  Remark ch09:rem-other-failures claimed the ACBE witness presheaf separates the
  two topologies at "three of the sixteen contexts", citing a "direct check" that
  "both sides count 2" at triples. Both false. Because no RPM piece of any context
  contains a complete ACBE block, the matching-family set is a SINGLETON at all 16
  contexts; gluing fails wherever alpha(V) >= 1, i.e. at SEVEN contexts (A_0, A_1,
  the four triples at 2-to-1, and Omega at 4-to-1). The volume's own Appendix C
  already stated the correct seven-context result — the book contradicted itself.
- **appB block-completeness table — all four triple rows wrong.** Listed "none" as
  the complete RPM block of every triple; each triple contains exactly one
  (alpha = rho = 1). Contradicted ch07 Table 7.5, Appendix A, and Appendix C.
- **ch04 drafting artifact shipped in the PDF.** Example ch04:ex:bounded contained a
  visible mid-sentence self-correction ("...is not constantly 1? No: s *is*
  constantly 1...") attached to an unretracted false claim that a non-presheaf was
  "separated". Replaced with a correct, verified example.
- **ch05 impossible exercise.** Asked the reader to exhibit a counterexample to an
  invariant the same chapter proves, with a self-contradicting hint. Replaced.

Citation and scholarship: Cech cohomological-obstruction machinery re-attributed
from Abramsky-Brandenburger 2011 (which contains none) to Abramsky-Mansfield-Barbosa
2012, plus the CSL 2015 paradox paper and the 2017 contextual-fraction measure;
Mac Lane-Moerdijk pinpoint corrected (Ch. VII has no associated-sheaf theorem —
it is Ch. III sec. 5-6); canonical topology corrected to *universally*
effective-epimorphic sieves; sieve-axioms definition re-pointed from Stacks Tag
00ZC to 00Z4; per-volume bibliography created (17 cited entries, replacing a
46-entry shared list of which 34 were never cited); AI-assistance disclosure added
to the \thanks block, matching the four sibling volumes.

Defects the verification pass caught in the corrections themselves:

- appD glossary longtable went 85pt -> 433pt overfull, pushing the entire "Where"
  column (the chapter attributions ~30 fixes were correcting) off the printed page.
  Non-wrapping `lll` spec replaced with wrapping `p{}` columns; 433pt -> 0pt,
  confirmed by rendering the page. Same fix applied to ch11's table (420pt -> 0pt).
- 26 double-numbered cross-references left in ch09 ("Theorem 7.\ref{...}" renders
  "Theorem 7.7.12") after a sibling agent normalized the identical pattern in ch08.
  Produces no LaTeX warning, so a clean build does not catch it. Now zero volume-wide.
- Two corrections that introduced new errors: ch05 called the countermodel "finite"
  while ch06 (same pass) says it is infinite; appA's "ten -> nine contexts" change
  fixed a count to match a list that was itself incomplete. Both reverted correctly.

All five volumes rebuild with zero undefined-reference and zero undefined-citation
warnings. PDFs in docs/whitepapers/pdf/ refreshed.

## 2026-08-08 — CAS PCBA 8 monograph: 17-failure-mode audit + corrections (11-agent workflow)

- Same audit protocol as the two sibling volumes, run over
  docs/whitepapers/monograph/cas_pcba8/ (15 files). 117 raw findings,
  ~100 corrections applied.
- Fabricated specificity caught and corrected against the actual source PDF:
  ch11 claimed the CSB's clamp and fuse threshold are "declared thirty lines
  apart" — in the hash-verified book they are on ADJACENT lines (verified on
  PDF pp. 342/608); the unreachability proof's no-amplifier premise is now
  anchored to that fact. ch10's "sixteen reference-listing pages" corrected
  to the fourteen its own page ranges sum to.
- Worked examples reconciled with the volume's own closed enumerations:
  Appendix B's "clean pass" board used units (alpha, fraction) and a signal
  kind (constraint) that do not exist in ch04's closed vocabulary — its clean
  pass would actually fail DRC; ch08's worked run used an illegal
  (activation, dimensionless) pair; ch05's "legal junction" example
  deterministically fires PCBA8-BIAS-001 (E-rank bias under C-rank cause);
  ch04's simplex-rejection example used weights summing to exactly 1 (vacuous);
  ch07's NET-006 scenario was unrealizable under the admissibility table.
- Appendix/glossary reconciliation: appA's check-class table invented a sixth
  class and misassigned BIAS-001/SAF-002/TKS-001 vs ch07's normative five;
  adapter-certificate and trace tables gained their omitted citation-identity
  digest fields; appC's CJT entry imported CAS-Ohm content ch06 never delivers;
  glossary alphabetization fixed; doubled \bottomrule in four longtables.
- Math/notation: "no section of pi exists" corrected (the proposition proves
  no LEFT inverse; sections exist and its own proof exhibits one); machine
  epsilon vs unit roundoff distinguished; 0.25/1e-12 is eleven orders not
  twelve; omega definition unified on d; four "Chapter~\ref{section}" broken
  cross-references fixed; ch10's 28-vs-7 out-of-grammar arithmetic corrected
  to the taxonomy-consistent 19+9+1 accounting.
- Citations: Rao-1945 "was the first" priority claim corrected (Hotelling 1930
  anticipated both ideas); shrinking no longer implicitly attributed to the
  QuickCheck 2000 paper (\cite{claessen} added); "adversarial generation"
  de-attributed from QuickCheck; IEEE 754 flag list completed (division-by-zero);
  PROV-O glosses and Harel's statechart formula properly quoted; targeted/
  coverage-guided PBT (FuzzChick, Hypothesis) added to the stale PBT survey;
  Merkle cited for the hash-chain construction; Mars Climate Orbiter report
  cited for the unit-mixing claim; per-volume 17-entry bibliography replaces
  the padded 46-entry shared list.
- Substance: three sources-silent gaps marked as open documentation items
  (Phase-0 authority matrix digest, Gate-5 spec digest, TKS kernel approved
  constant, SAF-003 cycle cap, the 20 open review criteria's identities);
  ch12's "pinned environment" recomputation step now states the environment
  is NOT bound (hermetic reproduction is open obligation 5); baseline
  disclaimer anchored to its actual copyright-page text (verified in the book
  PDF); warn-fuse post-trip semantics gap declared; gain-bound "declared
  exceptions" phantom mechanism removed (FBK-003 has no exception path);
  conservative-direction misstatements fixed (ch05 reachable-resolution,
  ch06 clamp under-reporting); rival host formalisms (Statecharts, block
  diagrams, Petri nets) named with rejection reasons; F1-F7 drive names
  glossed; SARIF prior art acknowledged for the record format.
- Scholarly practice: AI-assistance disclosure added to \thanks; two QED
  tombstones on design arguments (ch08 determinism, ch05 digest) converted
  to the shared designargument environment.
- Style: ~45 fixes — fivefold "deserve(s) emphasis" cluster, sixfold "deserves
  its own X" template, the worth/deserves family (~48 occurrences), three
  "Every ... of this monograph" openers varied. Classic AI vocabulary clean.
- All five volumes rebuild with zero undefined references/citations; corrected
  PDF copied to docs/whitepapers/pdf/ and Downloads.

## 2026-08-08 — CAS-Ohm 1.0 monograph: 17-failure-mode audit + corrections (11-agent workflow)

- Same audit protocol as CAS Core 8, run over docs/whitepapers/monograph/cas_ohm1/
  (16 chapter files). 122 raw findings, ~110 corrections applied.
- Systematic censoring-rule misstatement fixed at 10 sites: text keyed censoring
  to "zero-compatible predicted response" and/or claimed the residual is
  suppressed, contradicting the defining ch10 rule (observed-side trigger,
  marker OBSERVED_INTERVAL_INCLUDES_ZERO; residual retained, only ratio
  quantities censored). Fixed in ch01, ch03 x2, ch04, ch11, ch12, ch14, appA, appB.
- Arithmetic/count fixes: ch07 ASOM cross-table caption+remark miscounted the
  printed table (6/14/8 -> 3/14/11; 22 -> 25 of 28 cells); "five literatures"
  -> seven (matching ch02's own count); "three sources" -> four (the PCBA book
  is the audit's registered fourth source); "four reasons" -> five; "twice the
  minimum" -> three times; ch10's synthetic fault-mode enumeration reconciled
  with the seven-board catalog used everywhere else incl. the governing v0.2
  paper; a dangling "item eight of the closure experiment list" citation fixed.
- Citation fixes: five Kennedy-O'Hagan over-attributions (preregistration,
  validation trichotomy, split discipline, "the receipt", decorative replay
  cite) corrected or re-attributed; three Zou et al. over-attributions (control
  inventory, sign flips, sweep phenomenology) re-scoped; two Ritz
  over-attributions reworded; VIM wording credited to VIM not GUM; decorative
  Buckingham cite anchored to dimensional homogeneity.
- Close paraphrase: four VIM3 definitions (quantity, measurand, uncertainty,
  traceability) now properly quoted against jcgm.bipm.org wording.
- Stale literature: 2024-2026 steering-reliability results added (Tan et al.
  NeurIPS 2024; Da Silva et al. ACL 2025), SAE feature-steering family +
  AxBench added as fourth construction family, Brynjarsdottir & O'Hagan 2014
  discrepancy-prior result added; preregistration section now cites
  Simmons/Gelman-Loken/Chambers/ICMJE instead of gesturing at "the literature".
- Substance: unexecutable "best memoryless model" evidentiary bar (ch13) made
  executable via frozen baseline family; "preregistered margin" constants
  re-scoped to per-run Gate-5 freeze (ch10 x6); anti-conservative min-confidence
  convention honestly characterized as an upper bound on joint coverage with
  Bonferroni revision flagged (ch08+ch09); gain-composition replay gap declared;
  caller-trust status of component region/linearity declared; five "declared
  X never declared" constants marked sources-silent/open (drift cadence,
  decimal context, resource limits, unit-norm rule, region aggregation);
  provenance-enum gap vs ch02's four families acknowledged; Q10 floor
  divergence marked as candidate choice; half-open-bin "only way" uniqueness
  claim replaced with the real Guide-display argument.
- Appendix/glossary reconciliation: appA scope honestly narrowed, no-diagnosis
  list completed (3 -> 6 regions), profile field table gains splits/instruments/
  dependency-lock/fit-receipt/full-scale rows; glossary calibration-profile,
  censoring, Q4-banding, status-vector, link entries corrected.
- Scholarly practice: AI-assistance disclosure added to \thanks (series-standard
  sentence); three QED tombstones on design arguments converted to the shared
  designargument environment; per-volume bibliography created (was printing ~35
  never-cited shared entries; now 20 entries, all cited).
- Style: 37 fixes — sevenfold verbatim "deserves emphasis" scaffold, ~30-strong
  worth/deserves family, five "Every ..." chapter openers varied. Classic AI
  vocabulary scan clean (delve/tapestry/landscape/paradigm = 0).
- All five volumes rebuilt: zero undefined references, zero undefined citations.
  Corrected PDF copied to docs/whitepapers/pdf/ and Downloads.

## 2026-08-08 — Monograph cross-reference repair (tks_v8, cas_pcba8, cas_ohm1)

- Fixed all 14 pre-existing undefined `\ref` targets that rendered as "??"
  in three volumes: tks_v8 used a `chNN:main` label convention that was
  never defined (`ch01/ch03/ch07:main` → `chNN:chap`, `ch10:main` →
  `ch10:testing`; 9 sites in ch04/ch05/ch06); cas_pcba8's ch05 intro
  pointed at a nonexistent `ch05:sec:boundary` (→ `ch05:sec:invariants`,
  the "Invariants and boundary" closing section); cas_ohm1 referenced
  `ch12:hypotheses`/`ch11:eligibility` where the chapters are labeled
  `hyp:chapter`/`elig:chapter` (4 sites in ch04/ch05).
- All five volumes now build with zero undefined-reference and zero
  undefined-citation warnings; PDFs in `docs/whitepapers/pdf/` refreshed.

## 2026-08-08 — CAS Core 8 monograph: 17-failure-mode audit + corrections (11-agent workflow)

- Ran an 11-agent audit workflow over `docs/whitepapers/monograph/cas_core8/`
  covering the 17 standard AI-writing failure modes (hallucinated citations,
  citation-claim mismatch, data fabrication/reconciliation, stale literature,
  substance, long-range consistency, style tells, scholarly practice,
  figure/equation defects). 98 raw findings; ~60 distinct corrections applied.
- Critical fix: ch04 invalid-boundary table had three arithmetically impossible
  family counts (16/8/2 corrected to 8/12/6; wrong values coincidentally summed
  to the correct 33, masking the error — verified by exhaustive enumeration).
- Appendix A + glossary reconciled to the normative chapters: namespace enum
  7→9 members, link-kind enum 3→4 (IDENTITY exists, guarded to self-links —
  "omission is the mechanism" was factually wrong), digest case lowercase→
  uppercase, phantom "review state" link field replaced with the real
  crosswalk fields (crosswalk_id, source_artifact_sha256, note, boundary),
  decision-model enums replaced with the actual three-member sets, glossary
  "eight-step" list fixed to eight items, wrong chapter title corrected.
- Citation integrity: ch12 claim that RFC 8785 handles "the full JSON value
  space" corrected to I-JSON (contradicted the RFC and the monograph's own
  ch02); per-volume bibliography created (the shared 46-entry list printed 41
  never-cited references against ch02's own "why these five citations"
  argument); bibitem keys `turnertrojans`→`zourepe` and `opre`→`vaswani`
  fixed in the shared bibliography (+ 8 cite updates in cas_ohm1); Buckingham
  title completed; three decorative/misattributed cites fixed or removed.
- Stale literature: in-toto / SLSA / Sigstore added to ch02's supply-chain
  survey and ch12's "against supply-chain attestation practice" contrast —
  the one materially stale area (2021-2025 attestation standardization).
- Substance: ch09's property-based-testing overclaim corrected to match
  ch12's own "no fuzzing campaign" account; ch01 "all five drift mechanisms
  observed" overclaim corrected to the two documented ones; ch11 "(and does)"
  uncertified companion assertion re-scoped; ch12 rejection-coverage claim now
  names its silent third family; ch05 declares uppercase digests, the JCS
  sort-order rationale (as reconstruction), and the bounds' underived status.
- Scholarly practice: AI-assistance disclosure added to the \thanks block;
  Reproducible Builds definition and PROV-O glosses now properly quoted;
  PROV model/ontology conflation fixed; five "Design argument" blocks moved
  off the amsthm proof environment (no more QED tombstone on non-proofs) via
  a new additive `designargument` environment in the shared preamble.
- Style: 19 fixes — the "it is worth X-ing / deserves" metadiscourse tic
  (66 corpus occurrences, worst cluster in ch09) reduced at its 16 worst
  sites; two identical chapter-opening and chapter-closing templates varied.
  Signature-vocabulary scan otherwise clean (delve/tapestry/pivotal etc. = 0).
- All five monograph PDFs rebuilt (shared preamble/bibliography changed);
  corrected `MONOGRAPH_CAS_CORE_8_v0.3.pdf` copied to `docs/whitepapers/pdf/`
  and the user's Downloads copy.

## 2026-08-08 — Project Coherence monographs v0.3 (book-length, ~934 pp total)

- Expanded the five v0.2 research papers into full `amsbook` monographs under
  `docs/whitepapers/monograph/`, each 184-188 pages: Noetic Topos 2.0 (188pp,
  12 chapters + 4 appendices), TKS v8.0 (184pp, 12ch + 3app), CAS Core 8
  (187pp, 12ch + 2app), CAS PCBA 8 (188pp, 12ch + 3app), CAS-Ohm 1.0 (187pp,
  14ch + 2app). PDFs in `pdf/MONOGRAPH_*_v0.3.pdf`.
- Authored via a 20-agent parallel fleet writing body-only chapter sources
  against a shared preamble/bibliography and a strict LaTeX + Ring-4 claim
  contract; ~425,000 words delivered before the fleet hit the session limit,
  with the 4 remaining appendix gaps (NT2 sieve census; PCBA catalogs, worked
  board, glossary) written directly. All 76 chapter files pass the
  `sanitize_chapters.py` ASCII/environment/balance checker.
- Depth added over v0.2: tutorial preliminaries (category theory, sheaves,
  finite-function/spectral math, metrology, dose-response, information
  geometry, hardware-description and verification background); complete proofs
  with the seed papers' ledger proof-statuses preserved; per-item treatment of
  every diagnostic code, source conflict, threat, and registered hypothesis;
  implementation documentation of the src modules; worked examples, exercises,
  and reference appendices. Claim discipline unchanged: Ring 4 / NOT LICENSED
  headers, conjectures labeled, bounded-receipt framing, full open-obligation
  sets, and the 64/037,173 new-matter boundary.

## 2026-08-07 — Project Coherence research papers v0.2 (full-length)

- Superseded the five v0.1 white-paper summaries with full-length amsart
  research papers (`docs/whitepapers/tex/RESEARCH_PAPER_*_v0.2.tex`, builds in
  `pdf/`): TKS v8.0 (10pp), Noetic Topos 2.0 (14pp), CAS Core 8 (8pp),
  CAS PCBA 8 (9pp), CAS-Ohm 1.0 (9pp).
- Depth added from the deep sources: NT2 now carries the complete finite-context
  theory — legacy collapse and subcanonicity countermodel proofs, coverage-basis
  lemma, NT2-1..4 with full proofs, explicit reflector construction with the
  universal-property proof, the commuting modality-composition theorem
  (Lemmas 3.1/3.2/4.1, Theorem 5.1 of the registered proof), and the 23-check
  finite certificate (298 sieves / 168 covering / 3,012 restriction squares).
  TKS v8.0 adds full proofs (norm theorem via fiber-block Gram decomposition,
  factorial idempotence, shortlex pruning soundness) and the 11-row obligation
  ledger. PCBA 8 reproduces the per-board EBNF counterexample table with page
  anchors and formalizes CSB fuse unreachability. CAS-Ohm reproduces all eight
  conflicts at evidence-record granularity with source locators and the
  implemented enum catalogs. Core 8 adds a threat-by-threat analysis mapping
  each historical failure class to its blocking mechanism.
- Claim discipline retained everywhere: ledger proof statuses on theorems,
  conjectures labeled as conjectures, Ring 4 / NOT LICENSED headers,
  bounded-receipt framing, and full open-obligation sets.

## 2026-08-07 — Project Coherence white paper series v0.1 drafted

- Drafted five academic-rigor white papers into `docs/whitepapers/` from the
  Project Coherence Gate 1 / Gate 4 sources in the 2026-08-05 Codex snapshot
  (`project_coherence_model_smoke`): TKS v8.0 (typed finite-function kernel),
  Noetic Topos 2.0 (marked/modal successor site), CAS Core 8 (compatibility and
  evidence kernel), CAS PCBA 8 (adaptive cognitive circuit engineering), and
  CAS-Ohm 1.0 (profile-specific experimental response and calibration model).
- Every paper preserves its source's governing status
  (`DRAFT / OPEN / Ring 4 / NOT LICENSED`), exact SHA-256 source identities,
  bounded-evidence receipts (test/exhaustive-case counts, Lean scope), adverse
  findings (legacy topology collapse, CCDL grammar gap, CSB unreachable fuse,
  eight CAS-Ohm source conflicts), and full open-obligation ledgers. Drafting
  promotes no claim; papers note the 64/037,173 new-matter boundary.
- Index with shared conventions at `docs/whitepapers/README.md`.

## 2026-07-28 — Cognitive Circuit Grimoire accepted digital master

- Built and accepted the canonical 6 × 9 inch, 908-page
  `book/cognitive-circuit-grimoire/Cognitive_Circuit_Grimoire.pdf` digital
  master (2,672,454 bytes; SHA-256
  `99AC4170929C48F82C3D2FA81AABA3798C181EF32B3CDCC4C5E7E2D7C52F923D`).
- Completed the split 24-chapter manuscript, 13 appendices, 112 authored
  figures, and 164 worked exercise answers. Added fail-closed structure,
  cross-reference, answer, figure-inventory, standalone-figure, longtable,
  index, glyph, citation, reference, and layout gates to the publishing path.
- The accepted build reports 0 material layout errors, unresolved references,
  unresolved citations, missing glyphs, or rerun warnings. All fonts are
  embedded/subset, and independent text/front-matter inspection found no stale
  markers or orphaned contents entry.
- Marked the pre-existing HTML, EPUB, cover HTML, and monolithic manuscript as
  legacy previews rather than release artifacts.
- Print-production status remains `OPEN`: 908 pages exceeds KDP's current
  828-page 6 × 9 black-ink, white-paper paperback maximum. Closure requires a
  publishing decision between a validated 10-point single-volume reflow and a
  multi-volume split, followed by cover/spine regeneration.

## 2026-07-27 — Gate 2 campaign: root cause found, instrument rebuilt, S3-1 ALL_ROWS_PASS

- **Judge positive control** (`d755665b`): sixteen nulls explained — harness sound (`T0 28/28`),
  authored scenarios carried NO signal (`T2 p = 0.3011`). The owner's 27-section spec repaired it:
  `0.0429 → 0.9167` on the SAME author model (`59e9044c`), with the `56%` World-name leak
  disclosed post-hoc and the drive axis clean (`84/84`).
- **Small-model runs** (`pythia-160m`): `NOT_LICENSED_LEXICAL` twice (`c599273a`, `db948bf1`) —
  above chance, did not beat char n-grams; `world = 0.0000` fold defect fixed by the owner's
  Latin square; both leakage controls (`C-PERM`, `C-BODY`) passed for the first time.
- **Governance:** `CAS_HARNESS_CURRENT_STATE.json` continuation pointer + HISTORICAL SNAPSHOT
  banners (`bed3fc94`); Gate-2 closure contract frozen before any successor number (`17159fce`);
  84-item lane closed against benchmark fitting.
- **Track A:** `PHASE_A_IDENTIFIABILITY_PASS` (`4714fa1a`) — a registered direction works on
  untouched groups (`+1.2500` vs `0.4167` control envelope); effective `n = 6` and the non-zero
  sham floor disclosed. CJT/J-space Phase B unlocked.
- **Track B pilots:** corpora v1/v2 failed authoring yield (World-label leak `18–56%`; cohort
  confound avoided by full regeneration); realization-grammar pilot v1
  `VOID_APPARATUS_PROMPT_CONTAMINATION` (the prompt printed the forbidden word); S2 silent
  enforcement + E-arm universal target-blind instruction → `0.0094`; confirmatory `R1–R6` with
  full byte-replayability logging — low leakage replicates cross-family (`claude-haiku 0.0063`).
- **Attribution chain, one variable at a time:** thin judge key `joint 0.2222` → full canon on
  identical texts `0.6181` (`S3-0`, `536f6a89`) → motive repair with the rejected close rival
  `0.7569`, the campaign's first joint pass; `P74` (generative vs companionship)
  `0.5833 → 0.9375`. **All 13 mechanical rows green**, including `R6` arms regenerated under the
  repaired prompt (`0.0125` / `0.0187`).
- **v3 budget** from the frozen rule (worst-cell Wilson LCB `0.6990`, rule-of-three family
  rejection, sibling dependence): `13` plans/cell → `P(all 28 cells reach 8 families) = 0.9987`,
  `2,912` candidates.
- **Gate 2 remains OPEN at `0.38`.** Next: `TKS_672_V3` lock under the motive-repaired
  instrument, then the small-model readout ladder on the frozen corpus under
  `GATE_2_SUCCESSOR_CLOSURE_CONTRACT` — final equivalence decision is the owner's.
