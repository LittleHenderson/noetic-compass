# tksCAS — Changelog

Monorepo-level log. Subprojects keep their own changelogs
(`cas-forex/CHANGELOG.md`, `noetic-compass-scaffold/noetic-compass/CHANGELOG.md`,
`book/CAS_PCBA_Engineer/CHANGELOG.md`). This file records cross-cutting campaign milestones.

## 2026-08-28 (evaluation round) — CAS-RR capability criterion, ladder test, and R3 verdict

- Developed the executable reasoning-capability criterion (docs/cas_rr/REASONING_CAPABILITY_CRITERION.md): seven quantified difficulty axes (D proof depth, B branching, C constraints, N negations, U uncertainty, M memory, R recursion), a L0-L6 ladder, R0-R4 tiers, and the scoring principle that a typed refusal is the CORRECT answer when an operator does not exist - and that honesty never raises the tier.
- Tested the machine against the ladder (python run.py report): core 9/9 passed (L0 recall through L5 recursive planning), frontier 4/5 refused honestly (native arithmetic, induction, probabilistic, hypothetical). Verdict: capability tier R3 (recursive planner); R4 not attained.
- The test exposed and we fixed the biggest engine gap: FLAT recursion. Subgoals could halt but not descend. Now scans report the exact missing prerequisite token, subgoals carry their resolving action's prerequisites, and any goal may descend - depth-2 nested planning (capability -> knowledge) passes: 7 ticks, full ascend/descend trace, in cas-rr/tasks/battery.py (task_recursive_nested).
- Capability report with the honest GPT-scale mapping (docs/cas_rr/CAPABILITY_REPORT_V0_1.md): proof-grade symbolic core with GPT-0-era breadth; guaranteed deduction/provenance/typed-refusal where GPT-1/2/3 confabulate, and zero language/learning/probability where GPT has all three. Prioritized fixes: hypothesis autonomy, backtracking, arithmetic peripheral, induction operator, uncertainty degrees, procedural learning, encoders, CCDL emit/parse, breakdown semantics, memory ranking.
- Suite now 43 passed; CLI determinism check green on all 12 battery tasks (including the new nested one).

## 2026-08-28 (later) — CAS-RR interaction layer: CLI, reporter, determinism checker, authored-problem example

- CLI: python run.py list / run <task> [--trace] [--full] [--json out.json] / demo / check / repl — the machine is now drivable from the command line; bench reports show status, output, the RPM recursion story (descend/resolve, scans with cached flags showing fresh re-measurement), deduped lacunae, tournament elimination, commitment gates, and the winning proof path.
- cas_rr/report.py (summarize / battery_table / trace_compact / determinism_check) + run.py CLI; INTERACTION.md covers the packet anatomy, a problem-authoring template, and safe poke experiments (eval-gain boot rejection, memory seeding, budget starvation, typed halts).
- examples/custom_kinship.py: a grandparent syllogism the battery has never seen, authored from scratch and solved by the generic machine (CONCLUDED -> grandparent(ada,cy), proof via r_grandparent) — live proof of the encoder boundary and of "one machine, encoded problems".
- 12 new interaction tests; suite now 37 passed. CLI determinism check green for all 11 battery tasks (traces, status, output identical across double runs).

## 2026-08-28 — CAS-RR v0.1: a native CAS reasoning machine (not a harness)

- Built the first executable CAS-native reasoner from the three PCBA sources (CAS PCBA Engineer book, CAS-Ohm 1.0 v0.2 paper, CAS-Ohm Quantification Guide): CJTs with all four regions (cutoff/active/saturation/breakdown), typed biases, gain regimes (candidate 1.5 / evaluation 1.0 constitution-locked / commit 2.0 / learn 0.05), 7 Foundation engines x 28 sub-foundation channels with the Foundation-to-Drive adapter, CMB 40-cell memory with typed lacunae, ^8/^6/^9 reasoning spine (association ≠ deduction), CDAB shared-bias tournament, RPM D→W→P recursion stack (section-retraction; re-measure from scratch after every subgoal), Schmitt commitment with 7 typed halt states, P→C→E→O sequencing with O-last boot ("no action without principle"), low-gain episodic learning (procedural/constitutional layers disabled in v0.1), append-only reasoning provenance packets.
- 25 pytest tests green in cas-rr/: the six-task native battery (transitive inference, constraint satisfaction, fault walk-down, missing-information, recursive planning, memory-dependent) plus negative variants covering all seven halt states, the five load-bearing laws, determinism, candidate invariant, boot order, and both rumination stop gates.
- Source grounding done first: 16/17 load-bearing claims CONFIRMED, 1 PARTIAL (the 7/28/22 ontology lives in the TKS side, not the three PCBA sources; root label is A0/A1 — "A22" appears nowhere; 4 CJT regions, not 3). Honest boundary: deterministic symbolic reasoning with no LLM in the loop; no empirical-generality claim; CAS-Ohm used only as authored design quantities per the paper's own restrictions.
- Artifacts: cas-rr/ (package + tests), docs/cas_rr/CAS_RR_V0_1_SPEC.md (18-chapter operational semantics), docs/cas_rr/CCB_R1_BOARD_SPEC.md (the motherboard), docs/cas_rr/SOURCE_GROUNDING_NOTES.md (verbatim citations).

## 2026-08-22 — Frontier #1 lever RUN (pre-registered, $0): domain axis vs matched Tinbergen taxonomy — INCONCLUSIVE BY DESIGN

- Pre-registered before capture: `PREREG_DOMAIN_VS_TINBERGEN_20260822.md` (sha256 `14ace6dd…`).
- Executed the spec sheet's single most available lever for CAS-specificity: the v4 domain fixture (8 topics × 4 domains) on `pythia-160m-reserialized` (attested engine, CPU, $0), two label arms on the SAME vectors — CAS P/C/E/O vs Tinbergen's four questions (abstractness-aligned primary, positional sensitivity).
- Result: `INCONCLUSIVE BY DESIGN` — nearest-centroid accuracy is invariant under bijective class relabeling, so the arms tie by construction (layer-mean 0.875 = 0.875, best 1.0 = 1.0 at layer 2, identical at all 12 layers, McNemar p = 1.0). The prereg's literal verdict word (`DOMAIN_DOES_NOT_BEAT_GENERIC_ABSTRACTNESS`) is not citable.
- Standing positive: the CAS arm reproduces v4's cross-topic domain decodability (layer-mean 0.875, best 1.0, shuffle 0.259, random-subspace 0.25).
- Frontier #1 remains OPEN; the lever requires the Condition-3 blind-rater instrument or independently-annotated rival labels.
- Artifacts: `docs/working/gate2_closure/cas_specificity/domain_vs_tinbergen_20260822/` (results sha256 `d6b0787d…`). No claim upgraded; no negative hidden.

## 2026-08-19 — WELD v2: a CAS diagnose→correct loop that can actually FAIL (one axis, two criteria)

The Gate-5 WELD build was reviewed at `2be60327` and failed its own review: all four success
criteria were true by construction. `docs/working/gate5_weld/cas_weld_loop_v2.py` +
`WELD_SPEC_V2.md` supersede it (the v1 files are left on disk as the failure record).

- **Scope narrowed on purpose to ONE axis** — `A` (Pathway/RPM chain) on the numeric plane,
  the single detection the review found genuine. Axes N/W/F/E/S/P are declared out of scope.
  J1, J2, the epsilon realizers, the PCBA vocabulary and stage 5 are **absent**, not stubbed.
  v1's criteria (c)/(d1)/(d2) were **deleted**, not repaired — they lived on a lossy
  projection and could not be made falsifiable.
- **Blindness is structural.** `diagnose_blind(obj)` and `localize_blind(obj)` take exactly
  one parameter, asserted via `inspect.signature`; there is no parameter through which an
  axis name, a pre-injection object or a fault record could be passed. No concatenation
  anywhere. Ground truth is read once per case, only to score localization, and every read
  is logged.
- **The chain is proved load-bearing, not asserted.** `repair(obj, targets)` is called with
  `targets is localization.indices`. A built-in tamper check reproduces the v1 defect once:
  driven by the localizer NEG-3 reports `axis A cleared = False`; driven by ground truth it
  reports `True`. The v1 wiring **manufactures a success where v2 reports a failure**, and
  the `PREREGISTRATION_VIOLATED` / exit-1 branch is reachable.
- **The control can match, and its null is stated with its derivation.** Exhaustive sweep of
  all `C(7,k)` same-size interventions with the localized subset **in** the pool. Chance rate
  **1/7 = 0.142857** (k=1) and **1/21 = 0.047619** (k=2), cross-checked empirically over 2000
  seeded random draws (0.1490, 0.0435; all |z| < 1.5). In NEG-3 the same control reports
  `positive_control = False`.
- **No involution identity.** The injector overwrites a stage with a seeded `U(0.05,0.45)`
  draw; the corrector is a constraint solver that never learns the original. `repaired ==
  pre-injection original` is **measured** and comes out False every run (L1 0.10 / 0.20 / 2.25).
- **6 cases, 3 designed to fail, all matched preregistration** → `LOOP_FALSIFIABLE_AND_HELD`,
  exit 0, 18,154 scanner calls, zero GPU/API cost, stable across 5 seeds. NEG-1 surfaces a
  live gap: `detect_pathway_inversion` misses every prerequisite inversion whose unsatisfied
  stage stays above 0.5. ROBUST shows the loop reporting a partial repair as partial
  (`axes ['W'] still fired — OUT OF SCOPE, NOT CORRECTED`).
- **Honest limit, stated in §9 of the spec:** the detector is a transparent hand-written rule
  over disjoint input slices, so every value the loop measures is derivable from the Rust
  source. The gate has **no** chance null and is not scored as identification. The claim is
  only that the chain reports failure when the diagnosis is wrong, never falls back to ground
  truth, never manufactures a correction, and beats a non-zero chance rate a random
  intervention can and does hit. **Nothing here bears on efficacy; no model is loaded.**
- Separate finding, committed on its own: `inversion_gate._DOMAIN_RE` used `` after
  `[PCEO]`, which `_` defeats, so **axis W could never fire on any drive-tagged expression
  in the repo**. Fixed; 7 regression tests (4 fail against the old regex); belief suite
  135 → 142 passing.

## 2026-08-19 — Gate 4 board-CHANGE: 16-conversation pilot RUN. Both claims VACUOUS; kill statistic fires but is not citable.

The pilot spend gate of `PREREG_BOARD_CHANGE_V1.md` was executed under AMENDMENT A1
(generation budget 800 → 4000). Prereg and runner sha256 verified unchanged across data
collection (`immutability_sha256.match = true`). ~429 provider calls; call counts landed
on §15 (224 main-pass labelling + 160 corpus turns + repairs/retries).

- **A1 works.** All four frozen generators now produce usable turns: per-generator median
  chars deepseek 6188 / gemini 4906 / glm 4898 / qwen 14935; zero turns under
  `MIN_TURN_CHARS=200`; zero kept-but-truncated conversations. But
  `GENERATOR_LENGTH_IMBALANCE_FLAG = true` (max/min median ratio **3.0494** > 3.0), driven
  by qwen saturating the new 4000 budget — 14 of 40 qwen turns end without terminal
  punctuation. The length confound flipped direction rather than disappearing.
- **`r̂ = 0.1884`** on 138 analysable pairs / 26 model-initiated changes. Above the `< 0.10`
  hard stop, so the preregistered STOP does not fire. `K_neutral = clamp(ceil(40/(2.98·r̂)),
  60, 120) = 72`.
- **GATE 0 = FAIL** (6 failed, 1 null) → **CLAIM 1 VACUOUS, CLAIM 2 VACUOUS**. Two failures
  are pilot-size arithmetic (analysable pairs 138 < 240; T-USER positive control NULL for
  want of Stratum S). Three are **not**: T-CHANGE Fleiss κ **0.2853** < 0.35 on 142 complete
  cases (inside the preregistered VACUOUS band, above the 0.20 instrument kill);
  B0 share of consensus board labels **0.7325** vs a 0.40 ceiling; T-USER κ **−0.0410**,
  degenerate because Stratum N is continuers-only (P_e = 0.9244).
- **Kill statistic fires:** `surface_change_f1` 0.4000 (S3 length) ≥ `board_change_f1`
  0.2647 → `KILLED = true`. Under §10.1 this is **not evidence and may not be cited**,
  because Gate 0 failed; and §15 forbids reading a pilot VACUOUS as a stop signal.
  Recorded, not claimed.
- Instrument health is good: complete-case coverage 0.981 / 0.986 / 1.000, consensus
  coverage 0.981 / 1.000 / 1.000, residual same-conversation batch collisions **0**,
  CONTROL 4 generator≠labeller violations **0** (computed, not asserted).
- Operational finding for any full run: glm-4.6 as a board reader returned
  `finish_reason=length` on **13 of 40** calls even at `max_tokens=20000`; two repair rounds
  recovered all but 3 items. Two glm conversations initially fell below `MIN_TURNS=6` and
  were re-attempted via the runner's own checkpoint-restart path (no labels existed yet).

Evidence backed up to `D:\tksCAS-archive\gate4_board_change_pilot_20260819\`.
No gate was moved, no threshold relaxed, no prereg file edited.

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
