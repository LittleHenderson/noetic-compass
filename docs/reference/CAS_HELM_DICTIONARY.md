# CAS and HELM Dictionary

**What this is.** One place to look up every CAS and HELM term, symbol and acronym. Each entry gives the meaning in plain English first, then the precise definition with its source.
**Status of this file:** reference document. It records what the sources say. **It creates no new definition, no new status and no claim.** Where a source and this file disagree, the source wins.
**Built:** 2026-10-19, from branch `claude/project-thread-pmbzd6` at `47405484` plus the off-repo design packets listed below.
**Asked for by the owner, verbatim:** "let's put together a dictionary of all the CAS AND HELM terms and concepts and acronyms"

## Rules this dictionary follows

1. **Canonical text is quoted word for word.** The ten Noetic definitions and the Clarification texts are copied verbatim from `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`. They are never paraphrased. ("TKS definitions are DERIVED — never paraphrase.") Where a quotation's inner quote marks were changed or a list was joined into one line, the entry says so.
2. **Plain sentence first, precise definition second.** The plain sentence is an aid to reading. It never replaces or overrides the quoted definition.
3. **Nothing is invented.** If a term is used in the sources but never defined, the entry says: *(usage term; no canonical definition; first seen in <file>)*.
4. **Claim-status words come only from the spec sheet legend** (`docs/CAS_HARNESS_SPEC_SHEET.md` §3). Test words such as `EARNED_KEEP` are the frozen readers' own words; they are not legend words.
5. **Notation:** Noetics are written `^n` (for example `^3`), not CO-n, per the owner's ruling of 2026-09-21 (recorded outside the repo, in Claude's memory).

## Source keys

| key | file |
|---|---|
| CLAUDE.md | `CLAUDE.md` (project instructions) |
| CFC | `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` (Clarifications 1–6, 8–10; there is no Clarification 7) |
| SPEC | `docs/CAS_HARNESS_SPEC_SHEET.md` (§3 legend; §7.x results) |
| INC | `docs/INCIDENT_CATEGORIES.md` (12 failure classes) |
| T28 | `docs/reference/tks_28_foundations_translation_key.md` |
| CSK | `docs/working/noetic_council/COUNCIL_STANDING_KNOWLEDGE.md` |
| CONT | `docs/working/noetic_council/CONTINUITY_AND_DISENGAGE_20261016.md` |
| LOOP3 | `docs/working/noetic_council/the_loop_v3/README.md` |
| ROAD | `docs/working/HELM_CAPABILITIES_ROADMAP_AND_DEVELOPMENTAL_STAGES.md` |
| CORR | `docs/working/HELM_CAPABILITIES_ROADMAP_STATUS_CORRECTION_20261018.md` |
| PCBA Ch. 3 | `book/CAS_PCBA_Engineer/Chapter_03_The_Transistor_That_Changed_Everything.md` |
| `helm_*.py` | module docstrings at the repo root (`helm_brain_canonical.py`, `helm_end_to_end_loop.py`, `helm_english_in.py`, `helm_faces_in.py`, `helm_voice.py`, `helm_triad.py`, `helm_memory.py`, `helm_chat.py`, `helm_agentic_executor.py`, `helm_creativity_dial.py`, `helm_brain_22x40.py`) |
| `noetic_council/...` | code under `docs/working/noetic_council/` |
| RBI3 | off-repo: `C:\Users\wakil\Documents\Codex\2026-10-19\rb_i3_design_v1\DESIGN_RB_I3.md` (design only) |
| U3A | off-repo: `C:\Users\wakil\Documents\Codex\2026-10-19\u3_self_scan_design_v1\ARCHITECTURE_U3.md` (design only) |
| XR | off-repo: `C:\Users\wakil\Documents\Codex\2026-10-19\x_real_design_v1\DESIGN_X_REAL.md` and `TEST_PLAN_X_REAL.md` (design only) |
| PWP | off-repo: `C:\Users\wakil\Documents\Codex\2026-10-18\EXPLORATION_PURPOSE_WISDOM_POWER_PER_REAGENT_v0.1.md` (exploration only) |
| LMACH | off-repo: `C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1\README.md` (reported-only, non-authority) |
| LSRD | off-repo: `C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_oscillator_design_v1\ARCHITECTURE.md` (design only) |
| VIS | off-repo: `C:\Users\wakil\Documents\Codex\2026-10-05\task-2\HELM_VISION_AND_ROADMAP.md` (a PROPOSED_UPDATE copy; the canonical `docs/HELM_VISION_AND_ROADMAP.md` is not on the thread branch) |

**Group tags:** `[CAS core]` · `[CAS v7.5 Register]` · `[CAS v7.6 Production]` · `[CAS v7.7 Operator discipline]` · `[HELM part]` · `[HELM test/governance]` · `[Infrastructure]`

---

## How to read a HELM result

A HELM result is read in **four layers**. Never mix them up.

| layer | what it is | example (wave 5, SPEC §7.78) |
|---|---|---|
| 1. **Test verdict** | Did the run itself hold up? `PASS`, `FAILURE` (a hard gate failed), `INSTRUMENT_ERROR` (the measuring setup broke), `HARD_GATES_PASS`. | `HARD_GATES_PASS` |
| 2. **Status word** | The frozen reader's word for the part under test, by its own written rule: `EARNED_KEEP` (switching it off hurt), `NEUTRAL` (no change), `HARMFUL` (switching it off helped), `NOT_EXERCISED` (never used), `INCONCLUSIVE`, and pair words `SYNERGY` / `ADDITIVE` / `INTERFERENCE` / `CEILING_NOT_READABLE`. | `EYE_PAIRING_EARNED_KEEP` |
| 3. **Claim status** | What may be said, using only the spec sheet legend (below). | `ENGINEERED-NOT-VALIDATED` |
| 4. **Claim ceiling** | The widest world the claim covers. `SYNTHETIC_ONLY` = made-up test worlds only. `NOTHING SCORED` = frozen, not run. | `SYNTHETIC_ONLY` |

**Read it as one sentence:** "The run held every hard gate; by its frozen rule the Eye's pairing earned its keep; the machinery is built but not validated; and all of this is on made-up worlds only."

**Three rules that always apply** (CLAUDE.md, Research Governance; SPEC §1):
- A hard gate that fails is a **FAILURE**, never "PASS with caveats".
- Claim status comes from a **program reading**, never from prose.
- **Never delete a negative.** Failed and null results stay on the record.

### Claim-status legend (SPEC §3, word list only — full text under each A–Z entry)

| word | one-line meaning |
|---|---|
| `REAL` | exists and actually ran (wired ≠ works) |
| `VALIDATED` | passed its own pre-set test against matched controls |
| `LICENSED` | you may say this exact sentence — nothing wider |
| `NOT LICENSED` | you may not say it (unproven, not necessarily false) |
| `GREY` | valid test, neither pass nor clean refutation — not a pass |
| `VACUOUS` | could not be read; never really tested — not a fail |
| `WITHDRAWN` | claimed, then retracted on the record, forever |
| `ENGINEERED-NOT-VALIDATED` | built, no result yet — capacity, not evidence |
| `FLAG_FOR_HUMAN_REVIEW` | checks did not all clear; a person must look |
| `PASS` / `FAIL` | one pre-set test met / did not meet its bar |
| `SANITY_PASS` / `SANITY_FAIL` | non-CAS check that the instrument works at all |
| `NULL` | valid test, found nothing |
| `FALSIFIED` | refuted, with the controls catching it |
| `VOID` | unusable run; its numbers may never be cited |
| `OPEN` | not run, or not yet judged |
| `unavailable` | fact unrecoverable; never fill it in |
| `PARTIAL` | reaches part of the claim; say which part |
| `HOLDS` | effect present against one named null (output lens only) |
| `INCONCLUSIVE BY DESIGN` | the test's own fixture broke its logic |
| `DISCONFIRMED` | a prediction came last against all rivals |
| `REJECTED` | an input artifact failed its entry gate; not patched |
| `NOT TESTABLE` | no eligible data exists; untested is not null |
| `DEAD` / `LIVE` | only for Claim A / Claim B |
| `IN FORCE` | a process rule that binds now — not a result |

No `ACCEPT` verdict stands anywhere in the record (SPEC §1).

### Color marks used in owner reports

The owner's scale of 2026-08-21 ("START USING GREEN CHECK MARKS TO INDICATE SHIT THAT PASSED AND THAT IS AN ACTUAL WIN OR USE A COLOR SCHEME RATING SCALE TO INDICATE HOW MUCH OF A WIN A RESULT IS."). It is recorded outside the repo in Claude's memory file `feedback_result_status_color_scale.md`. In-repo short form: CSK §10.

| mark | meaning | bar it must clear |
|---|---|---|
| ✅ | CONFIRMED WIN | passed with an *unfakeable* floor, survived adversarial verification, licensed wording |
| 🟩 | STRONG | real and survived its controls, with a named caveat |
| 🟨 | PARTIAL | real but bounded |
| 🟧 | WEAK | barely above chance, or mixed |
| 🟥 | FAILED / WITHDRAWN | killed by a control or retracted; kept in the record |
| ⬜ | NULL / INCONCLUSIVE / NOT RUN | no signal, or never executed — distinct from a failure |
| 🔧 | METHOD / PROCESS WIN | an instrument, gate, tool or discipline improvement — not a science result |
| 🔒 | BLOCKED ON OWNER | needs the owner's sign line, money or authorization — not a result |

A color is a reading aid. **It is never a claim status.** The claim status is always the legend word.

---

## Symbols and notation

| symbol | plain meaning | precise form and source |
|---|---|---|
| `^0` … `^9` | the ten Noetics: `^0` Idea, `^1` Mind, `^2` Positive, `^3` Negative, `^4` Vibration, `^5` Female, `^6` Male, `^7` Rhythm, `^8` Above/Cause, `^9` Below/Effect | canonical names and definitions verbatim in CFC Clarification 1; see each A–Z entry |
| `^n^D` | a Noetic at a Domain, D ∈ {P, C, E, O} — e.g. `^3^P` | 40 Cognitive States "P0-P9, C0-C9, E0-E9, O0-O9" (CLAUDE.md) |
| `P ≻ C ≻ E ≻ O` | the domain order: Principled above Cognitive above Evaluative above Operational | "Total order: P ≻ C ≻ E ≻ O" (CLAUDE.md) |
| `F_k` (F1–F7) | one of the 7 Core Drives | "The `F_k` notation (underscore-subscript) matches the CAS notation standard for Drives." (T28, Notation Note) |
| `^n^D_{F_k}` | a Noetic at a Domain, fuelled by Drive k — e.g. `^2^P_{F2}` | CFC Clarification 8 §9 |
| `\|R`, R ∈ {T, A, f, E} | the Register (tone): Transcendent, Analytical, Affective, Embodied | CFC Clarification 8 §2 |
| `^n\|R` | "Register specified for a Noetic primitive alone." | CFC Clarification 8 §3 |
| `F_k\|R` | "Register specified for a Drive primitive alone." | CFC Clarification 8 §3 |
| `^n^D_{F_k}\|R` | "Register specified for the compound state as a whole." | CFC Clarification 8 §3 |
| `^n\|R_n^D_{F_k\|R_d}` | "Independent register specification for Noetic and Drive when they differ." | CFC Clarification 8 §3 |
| `\|⟨R1,R2,R3⟩` | register-set specification: where a state is present, no claim about interaction | "`\|⟨…⟩` denotes register occupancy or specification, makes no operational claim about dynamics." (CFC Clarification 10 §3) |
| `+` | co-presence / association: parts stay distinct ("associates with") | "`+` denotes association, adjacency, or simultaneous presence where terms remain structurally distinct." (CFC Clarification 10 §3) |
| `×` | genuine generative integration ("intensifies through"); for one Noetic across Registers only with a named result | "`×` remains reserved for genuine generative integration" (CFC Clarification 10 §3); "Same-Noetic, multi-register expressions using `×` are invalid by default." (§4) |
| `∘` | fractal composition (nesting) | one of the 5 Generative Operations: "Multiplication ×, Division ÷, Fractal Composition ∘, Addition +, Subtraction −" (CFC Clarification 9 §6) |
| `÷`, `−` | division and subtraction (Generative Operations) | CFC Clarification 9 §6 |
| `Ω` | Production Target — the outcome under analysis (also used for an emergent integrated register, e.g. `^3^P\|Ω`) | "A specified outcome whose generation is under analysis." (CFC Clarification 9 §2); `^3^P\|Ω` (CFC Clarification 10 §2C) |
| `Θ(Ω) = a₁·X₁ + a₂·X₂ + ... + aₙ·Xₙ → Ω` | a recipe: how much of each ingredient one unit of Ω needs | CFC Clarification 9 §2–§3 |
| `S = ⟨x₁, x₂, ..., xₙ⟩` | State Vector: what is available now | CFC Clarification 9 §2 (also written `S = {X₁: x₁, ..., Xₙ: xₙ}`, §3) |
| `Y_T = min_i(xᵢ / aᵢ)` | Theoretical Yield: the most you could make | "Y_T = min_i(xᵢ / aᵢ) for all i where aᵢ > 0." (CFC Clarification 9 §2) |
| `Y_A` | Actual Yield: what was made | "Empirically determined, not calculated." (CFC Clarification 9 §2) |
| `η = Y_A / Y_T` | Production Efficiency, in [0, 1] | CFC Clarification 9 §2 |
| `L` | Limiting Reagent: the ingredient that runs out first | CFC Clarification 9 §2 |
| `εᵢ = xᵢ - (Y_T · aᵢ)` | Excess Capacity: leftover of a non-limiting ingredient | CFC Clarification 9 §2 |
| `Λᵢ(Ω_side)` | Leakage: ingredient used up making the wrong product | "Θ(Ω) = ... → Ω + Λ₁·Ω_side₁ + Λ₂·Ω_side₂" (CFC Clarification 9 §3) |
| `κ` / `ι` | Catalyst (helps, not used up) / Inhibitor (hinders) | "Θ(Ω) \| κ₁, κ₂, ..., ι₁, ι₂, ... → Ω (conditions specified as modifiers on the arrow)" (CFC Clarification 9 §3) |
| `S°_I = Δ39°` (also written `Δ°₃₉`) | the open probability simplex: 40 shares, all above zero, summing to 1 | "S°_I = Δ39° = { p ∈ R^40 : pk > 0 for all k, Σpk = 1 }" (CLAUDE.md Correction 4) |
| `g^FR_p(u,v) = Σ(uk*vk/pk)` | the Fisher-Rao metric on the simplex | CLAUDE.md Correction 4 |
| `d(p,q) = 2*arccos(Σ√(pk*qk))` | Fisher-Rao geodesic distance between two mixtures | CLAUDE.md Correction 4 |
| `Dk ⊆ I × I`; `D0 = {(I,I) : I ∈ I}` | admissibility relation of operator k; `^0` only on the diagonal | CLAUDE.md Correction 1 |
| `εI ∘ ηI = idI`; `ηI ∘ εI ≠ idR(I)` | RPM section-retraction: one-way prerequisite satisfaction | CLAUDE.md Correction 2 |
| `εI: R(I) → I` | the counit used by Noetic Coverage (points toward the covered object) | CLAUDE.md Correction 3 |
| `A0 → Dn → Wn → Pn → Outcome` | the RPM chain: Pure Desire → Desire → Wisdom → Power | CLAUDE.md; INC §4 |
| `CJT< cause \| bias => effect > [β=2.4]` | a Cognitive Junction Transistor with gain β | PCBA Ch. 3 |
| `a.b.c` ≡ `Φ⟨a:b:c⟩` | dotted fractal notation; first written = innermost | owner's N1 ruling (SPEC §7.25, §7.31) |
| `parse(render(C)) == C` | the language round trip (ε∘η = id) | CSK §4 |
| `x_eff = min(P, W, Pw) × stock` | HELM triad: effective amount of an ingredient | `helm_triad.py`; SPEC §7.62 |
| `(S + 1) / (T + 2)` | Unity Eye pairing-cell score | RBI3 §4.2 |

**Name clashes to watch:** `ε` is both the counit (Correction 2) and Excess Capacity (v7.6). `η` is both the unit (Correction 2) and Production Efficiency (v7.6). `E` is the Evaluative Domain (`^E`), the Embodied Register (`|E`) and inversion axis E. `Ω` is both a Production Target and an integrated-register label. `A1` is an agentic level, a test arm, and (as `A0`) Pure Desire. `F1` is both the Unity Drive and the name of test families. Read the context.

---

## A–Z entries

**459 entries.** Jump to: [0-9](#0-9) · [A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) · [I](#i) · [J](#j) · [K](#k) · [L](#l) · [M](#m) · [N](#n) · [O](#o) · [P](#p) · [R](#r) · [S](#s) · [T](#t) · [U](#u) · [V](#v) · [W](#w) · [X](#x) · [Y](#y)

### 0-9

**10-Tier Progressive Complexity Curriculum** — [HELM test/governance]
- *Plain:* a planned ladder of ten flight-test difficulty levels.
- *Definition:* "Tier 1: Calm Lab → Tier 2: Open Field Breeze → ... → Tier 10: The Adversarial Gauntlet." — ROAD (LaTeX arrows written out). Plan only.

**$100B Wall** (Data and Compute Wall) — [HELM test/governance]
- *Plain:* the roadmap's argument that ordinary AI is hitting cost and compute limits.
- *Definition:* "Current artificial intelligence is hitting a hard economic, physical, and computational boundary" — ROAD.

**28 Foundations** (TKS) — [CAS v7.5 Register]
- *Plain:* the TKS grid of 7 Foundations × 4 Worlds, which maps to 7 Drives × 4 Registers in CAS.
- *Definition:* "The 28 TKS Foundations arise from the cross-product `7 Foundations × 4 Worlds`. In CAS v7.5, the same structural cross-product is expressed as `7 Drives (F1-F7) × 4 Registers (T, A, f, E) = 28 Drive × Register combinations`." — T28, Purpose.
- *Status:* scaffold — "Each entry below is a placeholder with the CAS v7.5 expression filled in and the TKS-source fields marked as pending." — T28.
- *In HELM:* `helm_brain_tks28.py` labels 28 inputs "as the 28 Foundations (4 planes × 7 archetypes)" — SPEC §7.51 (stand-in brain).

**354 MB** (memory figure) — [Infrastructure]
- *Plain:* the free laptop memory the owner reported; also the memory budget written into HELM's memory module.
- *Definition:* "The 354 MB free out of 16 GB is the owner's reported snapshot, not a live measurement." — owner global instructions `~/.claude/CLAUDE.md` (off-repo). In code: "Enforces 354 MB local memory budget" — `helm_memory.py`.

### A

**`a` control** — [HELM test/governance]
- *Plain:* a test world where nothing should grow; any growth there is a false alarm.
- *Definition:* "a world where nothing should grow" — SPEC §7.67.

**A0** (Pure Desire) — [CAS core]
- *Plain:* the root wanting that every pathway starts from.
- *Definition:* "A0 (Pure Desire, foundational motivation)" — INC §4; CLAUDE.md.

**Above/Cause** (`^8`, older label CO-8) — [CAS core]
- *Plain:* the Idea that sets off a different Idea in your mind ("that reminds me...").
- *Definition (canonical, verbatim):* "An Idea that triggers a different Idea than itself to come to Mind." — CFC Clarification 1.
- *Colloquialisms (canonical):* "That reminds me..." / "One thing leads to another." / "Triggered a memory." / "Made me think of..." — CFC Clarification 6.
- *Anti-drift:* `^8` is associative triggering, not analytical reasoning; deductive causal analysis is a compound of `^6` and `^9` — CFC Clarification 6.
- *In HELM:* station S1 "CJT trigger (^8)" of the thought path — SPEC §7.35; `helm_end_to_end_loop.py`.

**`ABSENT`** (ingredient rule) — [HELM part]
- *Plain:* an ingredient the user did not mention is treated as missing, never guessed.
- *Definition:* "A missing ingredient is ABSENT. It goes to the RPM gate and the turn ends UNDETERMINED with a CLARIFY question unless a repair child finds the real amount." — `helm_end_to_end_loop.py`.

**`ACCEPT`** — [HELM test/governance]
- *Plain:* a verdict that does not exist anywhere in the record.
- *Definition:* "**No `ACCEPT` verdict stands anywhere in the project record.** Nothing here may be read as one, and nothing written into it later may create one." — SPEC §1.

**`ACCEPTED_BY_OWNER`** — [HELM test/governance]
- *Plain:* the owner approved a wording or form; not a test result.
- *Definition:* (usage term; not in the §3 legend; first seen in SPEC §7.25, "7 wordings ACCEPTED_BY_OWNER"). Unity Eye "Form: MINI-VERSION, ACCEPTED_BY_OWNER" — `faculties_v2/eye/__init__.py`.

**Actual Yield** (Y_A) — [CAS v7.6 Production]
- *Plain:* how much you actually made.
- *Definition:* "Observed/achieved units of Ω in practice. Empirically determined, not calculated." — CFC Clarification 9 §2.

**`ADDITIVE`** — [HELM test/governance]
- *Plain:* two parts' effects simply add up.
- *Definition:* see **Pair words** — SPEC §7.69.

**Admissibility relation** (D_k; `is_admissible`) — [CAS core]
- *Plain:* a rule list saying from which state to which state each Noetic may be applied.
- *Definition:* "Each operator CO-k has an admissibility relation Dk ⊆ I × I specifying valid (source, target) pairs. D0 = {(I,I) : I ∈ I} (identity on diagonal only). Code impact: Add `is_admissible(operator, source, target)` guard before every operator application." — CLAUDE.md, Correction 1.

**Adversarial Susceptibility** (failure class 7) — [CAS core]
- *Plain:* scores flip, not fade, under a crafted prompt.
- *Definition:* "The architecture's per-operator or per-domain scores flip — not degrade — under crafted input." — INC §7.

**Affective Register** (`|f`) — [CAS v7.5 Register]
- *Plain:* the value-laden, felt tone.
- *Definition:* "Value-laden, feeling-toned." AI instance: "RLHF-tuned value expression, preference-weighted output, value-laden response patterns." — CFC Clarification 8 §2.

**Agentic executor** (`helm_agentic_executor.py`; Phase 4) — [HELM part]
- *Plain:* code that plans and runs tool actions behind pre-flight gates.
- *Definition:* "Phase 4: Agentic Tool Autonomy (Level A1/A2 Execution Engine)." — `helm_agentic_executor.py`. It "runs `subprocess.run(cmd, shell=True, …)` … behind a pattern filter"; cloud dispatch "is a dry-run receipt" — SPEC §7.49.
- *Status:* roadmap correction "Authored only" — CORR.

**Agentic levels A1–A5** (Five Tiers of Governed Agentic Autonomy) — [HELM part]
- *Plain:* five planned steps from planning tasks up to long-horizon self-direction.
- *Definition:* A1 "Autonomous Goal Decomposition & Task Planning (Topological DAG of bounded tool tasks)"; A2 "Pre-Flight Governed Tool & Action Execution (Stoichiometric Tool Reactions)" — `helm_agentic_executor.py`; A3 "Closed-Loop Environmental Observation & Autonomous Repair"; A4 "Sheaf-Theoretic Multi-Agent Swarms & Fleet Delegation"; A5 "Sovereign Long-Horizon Autonomy" — ROAD. A3–A5 are roadmap only.
- *Name clash:* A1 also names arm A1 in tests, and A0 is Pure Desire.

**ALIAS-WIDE reader** (and lexicon v2) — [HELM part]
- *Plain:* a word-list reader that checks whether free English names CAS states and domains; a form check, not understanding.
- *Definition:* "ALIAS-WIDE reader of free SDG English (TRANSLATOR_SPEC section 9). A FORM check, not a semantic judge." — `language_v3/aliaswide.py`. Lexicon v2: "v1 ... plus 10 Noetic phrases ... and 1 domain word (`mental` → C)... Only word lists changed." — SPEC §7.57.
- *Status:* reader `ENGINEERED-NOT-VALIDATED`; sealed 98 scored once 0 → 34 (32 right, 2 wrong), a `REAL` measurement — SPEC §7.57.

**Amendment** (e.g. LMT4-A3, R1W3-A1, U1-A2) — [HELM test/governance]
- *Plain:* a recorded, dated change to a test after freezing; it never rewrites the earlier reading.
- *Definition:* e.g. LMT4-A3: "The builder corrected only the reader, re-ran the merge and recorded amendment LMT4-A3" (waits on the owner) — SPEC §7.35. (usage term; no single canonical definition.)

**Analytical Register** (`|A`) — [CAS v7.5 Register]
- *Plain:* the explicit, step-by-step, reasoning tone.
- *Definition:* "Explicit, sequential, logical, reason-based." — CFC Clarification 8 §2.

**`AnaphoraResolver`** — [HELM part]
- *Plain:* works out what "it" or "those" refers to.
- *Definition:* "Resolves conversational references, pronouns, and relative quantities against recent working memory context." — `helm_memory.py`.

**Anti-drift annotations** — [CAS core]
- *Plain:* warnings that catch the two most common mislabels (`^3` and `^8`).
- *Definition:* `^3` colloquialisms "are **VISCERAL, not analytical**"; `^8` colloquialisms "are **NOT analytical reasoning** — they describe associative surfacing of Ideas, not deductive inference." — CFC Clarification 6.

**Aperture** (σ, valve) — [HELM part]
- *Plain:* a 0-to-1 setting for how much novelty the old valve let through.
- *Definition:* "computes an 'aperture' between 0 and 1" — SPEC §7.50 (inner quotes changed). "a gate setting, not a brain" — SPEC §7.56. Removed from the deciding path — `tks_meta_valve_controller.py`.

**ASOM** — [CAS core]
- *Plain:* a four-word display of how a CJT is running; it never decides anything.
- *Definition:* "ASOM is a display of how the CJT is operating, in four words": `STARVED` ("the CJT is in cutoff"), `ALIGNED` ("active, and the result is the intended one"), `OVERSATURATED` ("saturated, and the result is still the intended one"), `MISALIGNED` ("the result is opposite or off-axis"). "What it must never do: gate anything." — LOOP3 §2.
- *Expansion (owner, 2026-10-19):* the four operating words themselves: **A**ligned / **S**tarved / **O**versaturated / **M**isaligned. The owner gave "aligned, misaligned, oversaturated" and placed the term in the CAS PCBA Engineer book; the fourth word, Starved, is the spec sheet's and LOOP3's fourth word. Recorded as owner-given plus spec-sheet usage, not as a book quotation. Source: `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md` (2026-10-19 block).

**Authoritative verbs** — [CAS core]
- *Plain:* the exact verbs the definitions use, which must not be swapped for emotional words.
- *Definition:* "affinity for," "attracted toward," "adverse to," "repelled by," "resonates with," "impregnated with," "triggers," "brought to Mind" — CFC Clarification 4.

**Autonomic tier** — [HELM part]
- *Plain:* an automatic, no-veto layer that may only restore checked state, never add anything new.
- *Definition:* "an autonomic (involuntary) tier with no veto that may only restore verified state (no new fact, value, recipe or capacity)" — SPEC §7.38.

**AWAKE / IDLE** — [HELM part]
- *Plain:* awake = handling a user turn; idle = no user turn.
- *Definition:* "Wave 3 defines AWAKE = handling a user turn; IDLE = no user turn." — U3A, standing rulings.

**AWS execution rule** ("use AWS") — [Infrastructure]
- *Plain:* heavy work runs on Amazon's cloud, not the owner's laptop.
- *Definition:* owner: "use aws as there is only 354 mb of 16 gbs locally"; "Use AWS for tests, builds, benchmarks, model execution, training, and other memory-intensive or sustained compute. Keep the laptop to lightweight editing, inspection, orchestration, and result download. Do not silently fall back to local heavy execution if AWS is unavailable." — owner's global instructions `~/.claude/CLAUDE.md` (off-repo; owner instruction 2026-09-23). The same order is in the working-copy `CLAUDE.md`, not yet on the thread branch.

**AWS ledger** (combined allocation; ceiling 200 USD) — [Infrastructure]
- *Plain:* the running tally of cloud money held and spent, against the owner's 200 USD ceiling.
- *Definition:* "the ledger's combined allocation is **162.45** of the **200.0** USD ceiling" (at wave 1) in `AWS_COMBINED_ALLOCATION_HISTORY.jsonl` — SPEC §7.47; owner: "Yes to RB1...$200 aws" — SPEC §7.24. Each paid run places a hold (cap) and closes it with the charge — e.g. "ledger 111.26 -> 112.26 (hold) -> 111.29 of 200" — CHANGELOG 2026-10-19.

**Axioms A1–A7** — [CAS core]
- *Plain:* the seven base axioms of the CAS math.
- *Definition:* "The axioms govern the 40 Cognitive States and their algebra (composition, involution, admissibility, section-retraction of the RPM)." — CFC Clarification 8 §6. Source: "CAS v7.4 Referee-Defensible (36pp) — axioms A1-A7" — CLAUDE.md. (The axiom texts are not reproduced in the repo files read for this dictionary.)

### B

**Backup rule** (D:/tksCAS-archive) — [Infrastructure]
- *Plain:* every cloud run's evidence is copied to the backup drive and checked three times.
- *Definition:* "the standing rule that a cloud job's evidence is backed up with three sha256 confirmations" — SPEC §7.47. Example: `D:\tksCAS-archive\helm_r1_w1_c34g_20261016\` — SPEC §7.47.

**Bedrock** (teacher-language only) — [Infrastructure]
- *Plain:* Amazon's hosted-model service, allowed only for teacher-language work, not claim-bearing runs.
- *Definition:* "AWS GPU (SageMaker/EC2, NOT Bedrock) for every claim-bearing run; Bedrock = teacher-language only." — CLAUDE.md.

**Below/Effect** (`^9`, older label CO-9) — [CAS core]
- *Plain:* the Idea that arrives because something else triggered it ("it just popped into my head").
- *Definition (canonical, verbatim):* "The Idea brought to Mind by an Above/Cause trigger." — CFC Clarification 1.
- *Colloquialisms (canonical):* "It just popped into my head." / "Out of nowhere I thought of..." / "The thought came to me." / "It just clicked." — CFC Clarification 6.
- *In HELM:* station S3 "CJT arrival (yield, Limiting Reagent, label or UNDETERMINED, ^9)" — SPEC §7.35.

**`BETTER_THAN_T`** (and `BETTER_THAN_T_B`, `BETTER_THAN_T_B_YIELDS`) — [HELM test/governance]
- *Plain:* the recipe brain beat the transformer by the agreed margin.
- *Definition:* "rows 0-2 hold AND panel 1 RIGHT 16 of 16 AND new worlds RIGHT >= 15 of 16" (owner default D-1) — SPEC §7.24. `BETTER_THAN_T_B`: "RB-det's frozen 32/32 at least 4 above T AND at least 4 above T+" — SPEC §7.28.

**Bias** (CJT Bias) — [CAS core]
- *Plain:* the substrate a cause meets inside a CJT; in HELM, the working memory one step writes and the next reads.
- *Definition:* PCBA Ch. 3: the cause "is processed against the **bias** (the `|` is the control junction, the base terminal)". HELM: "The Bias is where a coordinator writes the facts the next step needs. Attention writes into it; the next CJT reads it." — LOOP3 §1. "S2 CJT Bias (^5 substrate: the learned requirements)" — SPEC §7.35.

**Boundary Failure** (candidate subcategory) — [CAS core]
- *Plain:* a failure at the hand-off between a person and an AI, owned by neither alone.
- *Definition:* "An incident is a *Boundary Failure* if the cognitive-architecture break occurs at the interface between a human agent and an AI agent, rather than within either agent alone." — INC, Taxonomy Development Notes.
- *Status:* candidate, "not yet formalized"; promotion trigger "≥5 verified incidents" — INC.

### C

**Canon's 5** (depth cap 5) — [HELM test/governance]
- *Plain:* the book's depth limit, kept on the record though HELM now uses 12.
- *Definition:* "The published book says 5 ('a maximum depth of 5 levels'), the Rust engine uses 5"; canon calls 5 "not an arbitrary performance cap, but a stability horizon" — LOOP3 (inner quotes changed). In wave 3 "canon's 5 is only the old arm's cap" — SPEC §7.66.

**Canonical brain** (canonical brain pointer) — [HELM part]
- *Plain:* HELM's one official brain. From 2026-10-20 it is the **Wide brain** (RB-W1), on the owner's word; before that it was the wave-1 recipe brain that beat GB3, which keeps its license as the reference brain.
- *Definition:* "HELM has one licensed brain: the HELM-R1 wave-1 recipe brain (c34-g, `PASS`, `R1_BEATS_GB3`, `SYNTHETIC_ONLY`); every other brain on disk is a candidate or a stand-in" — SPEC §7.56. Code: "loads HELM's ONE official brain, the licensed recipe brain, by path." — `helm_brain_canonical.py`.
- *Owner's word (2026-10-20, verbatim):* "YES TO WIDE BRAIN: Wide brain becomes HELM’s canonical brain" — `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`; pointer moved in SPEC §7.56 on the §7.96 reading.
- *Status:* pointer = RB-W1 (reader v5) since 2026-10-20 (SPEC §7.56, ruling `IN FORCE`). The wave-1 brain's claim stays `LICENSED` within `SYNTHETIC_ONLY`; the wide brain's claim stays `VALIDATED` for the §7.89 / §7.96 sentences only (`NAMED_CORPORA_ONLY` + `SYNTHETIC_ONLY`): a ruling is not a result. Engineering done 2026-10-20: the live loop and the chat run it ON by default (`HELM_WIDE_BRAIN=0` / `OFF` runs the licensed reference brain alone); the licensed loader `helm_brain_canonical.py` is byte-identical to its scored base (pinned by a test). The live chat with the wide brain on is not yet scored on a sealed exam.

**Canonical-brain candidate** (candidate; "candidate across the switches") — [HELM test/governance]
- *Plain:* a brain that has passed its own sealed tests and stands in line to become HELM's one official brain, but is not it yet. "Across the switches" means it has also been tested with HELM's other parts switched on and off around it (the pair wave) and did no harm. Only the owner's word moves a candidate to canonical; a test cannot.
- *Definition:* "RB-W1 v3 becomes HELM's canonical-brain CANDIDATE, `VALIDATED` for the §12 sentence only, ceiling `NAMED_CORPORA_ONLY`; the licensed brain stays canonical" — SPEC §7.89. "RB-W1T v3 (§7.89) made the wide brain a candidate main brain, "pending a wave with the switches". This is that wave." — SPEC §7.91. "`WIDE_WAVE_EARNED_KEEP`: the wide brain becomes **HELM's canonical-brain candidate across the switches** ... Making it HELM's canonical brain stays the owner's decision; the licensed brain keeps its license." — `PREREGISTRATION_R1W6.md` §12.
- *Status:* one candidate on record, the **Wide brain** (RB-W1): candidate since c47 (SPEC §7.89), candidate across the switches since c50 (SPEC §7.96); made the **Canonical brain** by the owner's word on 2026-10-20 ("YES TO WIDE BRAIN", SPEC §7.56). No candidate is open at the time of writing.

**Canonical colloquialism map** — [CAS core]
- *Plain:* the table of everyday sayings that go with each Noetic.
- *Definition:* the table in CFC Clarification 6 (reproduced under each Noetic entry here). "These colloquialisms are representative, not exhaustive."
- *In HELM:* lexicon v2 drew its new words only from canon colloquialisms, definition verbs, Clarification domain words and DEV 99 — SPEC §7.57.

**Canonical names** (of the Noetics) — [CAS core]
- *Plain:* the only allowed names for the ten Noetics, in every context.
- *Definition:* "the authoritative names ARE the names, for all contexts including academic publication, regulatory filings, pedagogical material, marketing, and incident analysis." — CFC Clarification 1, "Canonical names"; see also Clarification 3.

**`CanonicalRecipeBrain`** (RB-B handle) — [HELM part]
- *Plain:* the live loop's handle on the official brain.
- *Definition:* "The live loop's handle on the licensed recipe brain (RB-B). Decides nothing the brain does not decide." — `helm_brain_canonical.py`.

**Capability Pathways** (the 22) — [CAS core]
- *Plain:* the routes from wanting something to being able to do it.
- *Definition:* "22 Capability Pathways: A0 (Pure Desire) + D1-D7 + W1-W7 + P1-P7 / RPM chain: A0 → Dn → Wn → Pn → Outcome" — CLAUDE.md (two lines).
- *Warning:* the "22" in `helm_brain_22x40.py` is 22 kitchen ingredients, "not CAS's 22 Capability Pathways" — SPEC §7.51.

**Capacity kinds K1–K5** — [HELM test/governance]
- *Plain:* the five kinds of extra room a recipe brain can grow.
- *Definition:* "K1 +1 recipe slot, K2 +1 route, K3 +4 blend corners, K4 +1 efficiency or leakage term, K5 +1 nesting level" — SPEC §7.27.

**CAS** (Cognitive Architecture System) — [CAS core]
- *Plain:* the project's framework for describing how any mind works, in a written notation.
- *Definition:* "Framework: Cognitive Architecture System (CAS) v7.7 — Register Multiplicity and Operator Discipline Extension" — CLAUDE.md, Project Identity. Built from 10 Noetics × 4 Domains = 40 Cognitive States, 7 Core Drives, 22 Capability Pathways, 7 Inversion Axes — CLAUDE.md, Architecture Overview.

**CAS Harness** — [Infrastructure]
- *Plain:* the audit rig that reads, tests, corrects and records what AI models do, using CAS.
- *Definition:* "The CAS Harness is an audit rig for language models. It does four things. **It reads** ... **It proves cause** ... **It corrects** ... **It records**" — SPEC §2.

**CAS v7.4** (Corrected Edition) — [CAS core]
- *Plain:* the base version of the framework, before Registers were added.
- *Definition:* "CAS v7.4 Corrected Edition (596pp) — full mathematical reference"; "CAS v7.4 Referee-Defensible (36pp) — axioms A1-A7" — CLAUDE.md, Reference Documents. "CAS v7.4 expressions remain valid in v7.5 (register-unspecified = register-neutral)." — CFC Clarification 8 §1.

**CAS v7.5** (Phenomenological Register Extension) — [CAS v7.5 Register]
- *Plain:* the version that adds the "tone" axis (Register) to every state.
- *Definition:* "CAS v7.5 introduces a second orthogonal axis to the Noetic Topos: the **Phenomenological Register**." — CFC Clarification 8 §1.

**CAS v7.6** (Stoichiometric Production Semantics Extension) — [CAS v7.6 Production]
- *Plain:* the version that adds "recipes" — how much of each ingredient an outcome needs.
- *Definition:* "CAS v7.6 introduces production semantics as a structural layer describing how cognitive primitives (Noetics × Domains × Drives × Registers from v7.5) produce outcomes through constrained transformation." — CFC Clarification 9 §1.

**CAS v7.7** (Register Multiplicity and Operator Discipline Extension) — [CAS v7.7 Operator discipline]
- *Plain:* the version that fixes when to write `+`, `×` or `|⟨…⟩` for one state in several Registers.
- *Definition:* "Clarification 10 admits Register Multiplicity, Co-Presence, and Cross-Register Integration as a formal notational refinement. CAS is now at v7.7." — CFC Clarification 10, closing note.

**CAS-Native AI** (Phase 4 parts) — [CAS core]
- *Plain:* a planned neural model whose layers are built around CAS.
- *Definition:* parts listed: "CognitiveStateEmbedding (40-dim, open simplex); DomainDescentAttention (P→C→E→O mask); PrerequisiteGateLayer (differentiable RPM); FractalAttentionHead (IFS-inspired); CognitiveMetricLoss (Fisher-Rao drift); CognitiveToposReasoner (intuitionistic 3-valued logic)" — CLAUDE.md, Phase 4 (list joined).

**CAS-Ohm** (quantifiers `delta_current`, `r_hidden`, `maturity_q4`) — [CAS core]
- *Plain:* measuring tools that borrow the words of Ohm's law as an analogy.
- *Definition:* "three proposed measuring instruments that borrow electrical vocabulary as an **analogy**." `r_hidden` "is apparent-resistance minus known-resistance (`V/I_obs − R_known`)" — SPEC §4.4 row [22]. Book: "CAS-Ohm is the mid-band model" — `book/cognitive-circuit-grimoire/manuscript/ch04_cas_ohms_law.md`.
- *Status:* "PROPOSED INSTRUMENT — WORKING DRAFT. `NOT LICENSED`. NEVER RUN against real `I_obs` from any model." — SPEC §4.4 row [22].

**CAS-specificity** — [HELM test/governance]
- *Plain:* the open question whether what the harness reads is really CAS, or just ordinary topic structure with CAS labels.
- *Definition:* "What it has **not** established is that the structure it reads is specifically **CAS** rather than ordinary topic-and-frame structure wearing CAS labels. That question — CAS-specificity — is the open frontier, and the honest current answer is `GREY`." — SPEC §2.
- *Status:* `GREY` — SPEC §2, §10.

**CASalescence** (CASalesces) — [HELM part]
- *Plain:* HELM ability 5 — parts and models working as one combined system.
- *Definition:* "**CASalesces** — CASalescence at the neural-architecture level, toward models working as a genuinely combined system." — VIS §1, item 5.

**Cascade** (switch `CASCADE`) — [HELM part]
- *Plain:* going down into sub-problems, with a smart stop rule and a hard depth fuse.
- *Definition:* "decoupling-stop primary + fuse at HORIZON 12; off = flat" — SPEC §7.66. Cascade exam: "64 chains, depth 3–6, 8 families incl. planted binding faults, stale consolidations, return attacks, face shocks, deadlocks" — SPEC §7.66.
- *Status:* `EARNED_KEEP` — SPEC §7.69. `CASCADE_RECEIPTED` not earned in LM-T6 — SPEC §7.41.

**Catalyst** (κ) — [CAS v7.6 Production]
- *Plain:* something in the surroundings that helps without being used up.
- *Definition:* "A contextual or environmental factor that enhances conversion efficiency without being consumed as a prerequisite. Raises η without appearing in the recipe." — CFC Clarification 9 §2.
- *In HELM:* "the engine has no catalyst (κ) node" — SPEC §7.27.

**Category Noetica** — [CAS core]
- *Plain:* the formal math category the Noetics live in, with rules on which moves are allowed between states.
- *Definition:* "Noetica is the smallest pullback-complete subcategory of FinSet. Each operator CO-k has an admissibility relation Dk ⊆ I × I specifying valid (source, target) pairs." — CLAUDE.md, Correction 1.

**CCE** (Controlled Core English; also written "Controlled CAS English") — [HELM part]
- *Plain:* a strict, small form of English that converts to CAS and back exactly — HELM's ears and mouth.
- *Definition:* "**CCE = Controlled Core English.** `parse(CCE sentence) → CAS content`; `render(CAS content) → CCE sentence`. 'Both are deterministic programs, not models.'" — CSK §4 (inner quotes changed). Code: "CCE v0.1: Controlled Core English <-> CAS content. Deterministic parser and renderer." — `language_v3/cce.py`. SPEC §7.31 expands it as "Controlled CAS English".
- *Status:* translator `ENGINEERED-NOT-VALIDATED` (FORM only) — SPEC §7.31, §7.48.

**CCE skin** (`CCE_SKIN`) — [HELM part]
- *Plain:* the language layer around the brain; it only changes wording, never facts.
- *Definition:* "English enters through a checked parser and leaves through a checked renderer with a read-back receipt" — SPEC §7.31; "**facts never come from the language layer**" — SPEC §7.31; "`CCE_SKIN` says explicitly 'never a keep word for accuracy'" — CSK §2 (inner quotes changed).
- *Status:* wave 1 `SKIN_FORM_BROKEN`, answer half `VACUOUS`; waves 2 and 3 `NEUTRAL` "by construction" — SPEC §7.47, §7.64, §7.69.

**`CEILING_NOT_READABLE`** — [HELM test/governance]
- *Plain:* the exam is too small to read this pair.
- *Definition:* see **Pair words** — SPEC §7.69, §7.70. Resolved by wave 3b ("no pair `CEILING_NOT_READABLE`") — SPEC §7.72.

**Certification Levels** — [CAS core]
- *Plain:* the medal bands for an NCCS score.
- *Definition:* "90-100 = Platinum | 75-89 = Gold | 60-74 = Silver | 40-59 = Bronze | 0-39 = Fail" — CLAUDE.md.
- *Caution:* the word "certified" is on the spec sheet's prohibited list — SPEC §3.

**CES law** (weighted power mean) — [HELM part]
- *Plain:* a smooth "substitution" formula where ingredients can partly stand in for each other.
- *Definition:* "a weighted power mean... `Y = [Σ cᵢ · max(0, xᵢ − aᵢ)^ρ]^(1/ρ)` in 40-digit Decimal" — SPEC §7.51.
- *Expansion:* CES = Constant Elasticity of Substitution, the economics term for this family of formulas; spelled out in the stand-in brain code ("Constant Elasticity of Substitution (CES) with curvature rho" — `HELM_DISTRIBUTION_PACKAGE/brains`). The owner notes (2026-10-19) that the term entered the project through Gemini's usage; it is a technical borrowing, not a CAS primitive.
- *In HELM:* the stand-in brains and RB-OH1's `RECIPE_SUB` head — SPEC §7.51, §7.52.

**CHANGELOG** — [Infrastructure]
- *Plain:* the project's dated log of work, read at the start and updated after every unit of work.
- *Definition:* "Always read `CHANGELOG.md` at session start before doing anything"; "Always update `CHANGELOG.md` after every meaningful unit of work" — CLAUDE.md, Progress Tracking.

**Charge** (on a cell) — [HELM part]
- *Plain:* a record that a teaching step touched that cell.
- *Definition:* "an admitted step whose *current* example had key k. It is attribution by trigger, not a measurement" — `lacunarity_machine_v1/RESULTS_C21.md`.

**Charge, hold and cap** — [Infrastructure]
- *Plain:* the cap is the most a run may spend; the hold reserves it; the charge is what was actually spent.
- *Definition:* (usage terms; no canonical definition; first seen in SPEC §7.24, e.g. "cap $0.50"). "Money, as the ledger and the records write it, not as anyone computes it." — SPEC §7.47.

**Chat wave** (HELM-R1 wave 7, "CHAT WAVE") — [HELM test/governance]
- *Plain:* the wave that types to HELM's chat window line by line, with the wide brain on by default, and scores what comes back: did it learn real recipes, answer right, ask where it should, say it plainly, and stay unbroken by small talk, as well as the loop did when driven directly. Three exams drawn blind by a custodian: 128 real recipes, 64 dialogues, the same 64 with two small-talk turns each.
- *Definition:* "When a person types to HELM's chat, with the canonical wide brain on, does HELM learn real recipes, answer right, ask where it should, say it plainly, and stay unbroken by ordinary small talk, as well as the loop did when driven directly?" — `PREREGISTRATION_R1W7.precode.md` §1 (sha256 `efe94ed6…`). Marks NH-CHAT, K1, K3, K4, P PLAIN, N NOISE; words `CHAT_WAVE_HARMED` / `CHAT_WAVE_NO_GAIN` / `INCONCLUSIVE` / `CHAT_WAVE_EARNED_KEEP` — §6.
- *Owner's words:* "the live chat with the wide brain tested for real" (2026-10-20). The line to sign, proposed: `CHAT WAVE at 1 USD`.
- *Status:* ran as job c51 (SPEC §7.101): the frozen reader read verdict `FAILURE`, word `INCONCLUSIVE` — all six marks true as facts, 9 of 10 hard gates true, HG5 (sandbox) false from a reader defect (the recorder-equality unit never writes the field the gate demands). Nothing licensed; the chat stays NOT LICENSED. Packet: SPEC §7.98 (v3, zip `5063baba…`). Two FIX FIRST rounds on practice fixed five chat defects in HELM first (PR #416), one of them a kitchen sentence that ran a shell command; every mark met on practice v3 (practice data only).

**Circular verification** — [HELM test/governance]
- *Plain:* a run checking itself and reporting "no problems" while an outside checker found problems.
- *Definition:* "run R1-X0 reported '29 outputs, 0 problems' while three of its five exam files failed the receiving package's own checker" — SPEC §7.46 (inner quotes changed).

**CJT** (Cognitive Junction Transistor) — [CAS core]
- *Plain:* the basic part of a CAS "circuit": a cause comes in, meets a bias, and produces an effect, with a gain.
- *Definition:* "The component that captures all of this is the **Cognitive Junction Transistor (CJT)** — the central part of the entire book and the building block of every circuit you will design from here on." Written form: `CJT< cause | bias => effect > [β=2.4]` — `book/CAS_PCBA_Engineer/Chapter_03_The_Transistor_That_Changed_Everything.md`.
- *In HELM:* stations S1–S3 are CJT trigger, Bias and arrival — SPEC §7.35. Owner ruling: "a CJT is the crossing, not the node" — `docs/working/noetic_council/continuity_build_v4/crossings.py`.

**Claim A** ("the weights are natively CAS") — [HELM test/governance]
- *Plain:* the retired idea that AI models secretly contain CAS inside them.
- *Definition:* "CAS structure is latently encoded in activations and recoverable by correlational probing beyond surface." — SPEC §8.1.
- *Status:* `DEAD` — "formally retired by the owner on 2026-08-18" — SPEC §8.1.

**Claim B** ("CAS is a measurement and correction language") — [HELM test/governance]
- *Plain:* the live idea: CAS is a ruler and a repair kit for AI, not a description of its insides.
- *Definition:* "(i) a reliable way to READ what a model produced, and (ii) a working algebra to CORRECT it"; "The ruler need not be inside the table." — SPEC §8.2.
- *Status:* `LIVE` thesis, ratified 2026-08-18; "neither is closed" — SPEC §8.2.

**Claim sentence** (`claim_if_pass`) — [HELM test/governance]
- *Plain:* the exact sentence a passing run lets you say — and only that sentence.
- *Definition:* "the reader's own claim sentence"; claim status holds "only for" that sentence — SPEC §7.64, §7.69, §7.72. `claim_if_pass` / `not_claimed` are fields in the reading file (usage terms; SPEC §7.25).

**`CLAMPED_HALT`** — [HELM part]
- *Plain:* the executor stops because a gate clamped the step.
- *Definition:* "the RPM Gate executes CLAMPED_HALT (G-ABSENT)" — ROAD. (No docstring in code.)

**Clarification 1–10** (CAS Foundational Clarifications) — [CAS core]
- *Plain:* the numbered rulings that fix what CAS words mean.
- *Definition:* `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` — "Normative reference for what each Noetic IS". 1 Ten Noetics; 2 Universal Applicability Test; 3 Canonical naming; 4 Structural-not-emotional framing; 5 Scope of `^5`; 6 Colloquialism Test; 8 Register (v7.5); 9 Production semantics (v7.6); 10 Register multiplicity (v7.7).
- *Gap:* there is no Clarification 7 in the file (the numbering jumps from 6 to 8).

**`CLARIFY`** — [HELM part]
- *Plain:* HELM asks a question instead of guessing what you meant, and writes nothing.
- *Definition:* "unparseable → CLARIFY"; "two or more → CLARIFY (never a coin pick)" — SPEC §7.31, §7.33. "Parse fails or the round trip differs -> typed CLARIFY, ZERO writes." — `helm_end_to_end_loop.py`.

**"Claude is NOT the research governor"** — [HELM test/governance]
- *Plain:* one AI may not design, run, judge and promote its own work.
- *Definition:* "One model may not be architect + protocol-owner + decision-maker + executor + auditor + grader. A standing `/goal` does NOT authorize choosing a replacement hypothesis, advancing past a failed hard gate, or promoting a claim." — CLAUDE.md, Research Governance.

**`CLOSED_NO_FIX`** — [HELM part]
- *Plain:* an item where every faculty was tried and none worked; it counts as "could not tell".
- *Definition:* "(up to 7 different faculties, then the item is CLOSED_NO_FIX)"; counted as UNDETERMINED — RBI3 §4.2, §4.6.

**CNCM** (CAS Native Cognitive Machine) — [Infrastructure]
- *Plain:* an earlier, separate CAS-native machine line, handed to Codex to build.
- *Definition:* expansion from the folder name `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/` and `cas_only_reasoner/CAS_RRK_v0.1/docs/CAPABILITY_CHARTER_STATUS.md` ("CAS Native Cognitive Machine"). (No canonical definition read.)

**CO-n** (e.g. CO-3) — [CAS core]
- *Plain:* the older index label for a Noetic; `CO-3` is the same thing as `^3`.
- *Definition:* used in CFC Clarification 1 ("^3 (CO-3): Negative") and in the Rust engine (`CognitiveOperator`). Owner ruling 2026-09-21 (recorded outside the repo, in Claude's memory): prose uses `^n`, not CO-n. (The expansion "Cognitive Operator" appears in code names such as `CognitiveOperator::is_admissible` — SPEC §4.4 row text; it is not separately defined in CFC.)

**Codex** — [Infrastructure]
- *Plain:* another AI coding agent (from OpenAI) that builds and audits parts of the project.
- *Definition:* named as a contributor in HELM ability 7: "Codex, DeepSeek and Claude contributing to one coherent project" — VIS §1. Its working folders live under `C:\Users\wakil\Documents\Codex\<date>\`. (No further canonical definition.)

**Cognitive domain** (C) — [CAS core]
- *Plain:* the level of ordinary thinking.
- *Definition:* second of the 4 Processing Domains (P ≻ C ≻ E ≻ O) — CLAUDE.md. "This is ordinary thinking, not a deep principled commitment (`P`) and not a motor action (`O`)." — PCBA book Ch. 3.

**Cognitive Fractal Amplification** (failure class 5) — [CAS core]
- *Plain:* each round of reasoning makes things worse instead of settling.
- *Definition:* "An amplifying fractal signature means each operator application *increases* the magnitude of state change instead of stabilizing it" — INC §5. Classes: "*stabilizing*, *amplifying*, *oscillatory*, or *neutral*."

**Cognitive State** (the 40 states P0–O9) — [CAS core]
- *Plain:* one Noetic at one Domain — 10 × 4 = 40 boxes.
- *Definition:* "40 Cognitive States: 10 Noetics × 4 Domains = P0-P9, C0-C9, E0-E9, O0-O9" — CLAUDE.md, Structural invariants.
- *Warning:* the "40" in `helm_brain_22x40.py` is a parameter count, "not CAS's 40 Cognitive States" — SPEC §7.51.

**Cognitive State Vector** (`CognitiveStateVector`) — [CAS core]
- *Plain:* a list of 40 positive shares, one per state, adding to 1.
- *Definition:* "All CognitiveStateVector.probabilities must have pk > 0. Validate strictly." — CLAUDE.md Correction 4. (Not to be confused with the v7.6 **State Vector (S)**, which holds available quantities.)

**Colloquialism Test** — [CAS core]
- *Plain:* when unsure which Noetic fits, find the everyday saying for it and match it to the map.
- *Definition (verbatim):* "If ever unsure of a Noetic's true definition, try to match its definition with a colloquialism and it will make it clear." — CFC Clarification 6.
- *Guardrail:* "Where a colloquialism and a canonical definition appear to disagree, the canonical definition governs" — CFC Clarification 6.

**`COMPLETED_WITH_FAILURES`** — [Infrastructure]
- *Plain:* a job-supervisor message from wave 1 that came from a supervisor defect, not a test failure.
- *Definition:* "an instrument defect in the job supervisor, not a test failure" — SPEC §7.47.

**Compound expression** — [CAS core]
- *Plain:* a label made of two or more Noetics because one is not enough (often with `^5` as the base).
- *Definition:* "If the colloquialism invokes several Noetics simultaneously, the example probably needs a compound expression (often with ^5 Female as substrate per Clarification 5)." Example: `^2^C × ^5^C` — CFC Clarification 6, "Diagnostic application".

**Compound Inversion** (P-axis failure; failure class 12) — [CAS core]
- *Plain:* several small problems that together are much worse.
- *Definition:* "Two or more inversion axes (N, W, F, E, S, A) simultaneously failing. The P-axis (Compound) severity is computed as the product of the top-2 individual axis severities" — INC §12.

**Concentration** (CV² = n·HHI − 1) — [HELM part]
- *Plain:* a spread-out-ness number the Lacunarity Machine reports but never calls lacunarity.
- *Definition:* "always labelled 'concentration (CV² = n·HHI − 1, exact)'. It is never called lacunarity." — LMACH (inner quotes changed).

**Concert** (Eye–brain concert; `ConcertLedger`) — [HELM part]
- *Plain:* the Eye and the brain working together: the brain asks, the Eye answers, refusals give reasons.
- *Definition:* "eye and brain know each other: the brain asks, the eye answers, declines carry a reason, the volume is calibrated" — SPEC §7.38. Whispers go through "U1b's ConcertLedger" — SPEC §7.73.
- *Status:* ✅ `CONCERT_EARNED_KEEP` (U1b) — SPEC §7.40.

**Continuity of thought** — [HELM part]
- *Plain:* a thought is one connected path through the stations, which can be followed and checked.
- *Definition:* owner, verbatim: "THE BRAIN IS SUPPOSED TO HAVE 'CONTINUITY OF THOUGHT' FROM RPA TO CJT THROUGH BIAS TO ASOM TO RPM TO AND OR CJT RPA". As designed: "Continuity of thought is the path itself, indexed by station and tick" — CONT §1, §1c.

**Conversational memory** (`helm_memory.py`) — [HELM part]
- *Plain:* remembers what was said across turns, within a fixed memory budget.
- *Definition:* "Multi-Turn Conversational Working Memory & State Tracker (v0.8)." `HELMConversationalMemory`: "Thread-safe, bounded multi-turn conversational working memory manager. Enforces 354 MB local memory budget" — `helm_memory.py`.
- *Status:* `ENGINEERED-NOT-VALIDATED` — SPEC §7.49. Roadmap correction: v0.8 "Authored only" — CORR.

**Core Drives** (the 7 Drives F1–F7) — [CAS core]
- *Plain:* the seven basic motivations behind what a mind does.
- *Definition:* "7 Core Drives: F1 Unity, F2 Wisdom, F3 Vitality, F4 Connection, F5 Agency, F6 Structure, F7 Purpose" — CLAUDE.md. TKS calls them Foundations; "CAS Drive names are authoritative" — T28, Drive-name convention.
- *In HELM:* also called the "7 desires" or "gravitational wells" — RBI3 §4.1; SPEC §7.74.

**Coverage ledger** — [HELM part]
- *Plain:* the table of which (idea × Noetic × domain × register) cells the language can express.
- *Definition:* "Coverage ledger for CCE v0.1 over (fundamental x Noetic x Domain x Register), read by the Lacunarity Machine." — `language_v3/coverage.py`. "**2,600 cells** = 130 (fundamental × Noetic) pairs × 4 Domains × 5 Registers" — CSK §4.

**Verified creative reconstruction** (M1 H8 policy v0.2; creative radius) — [HELM test/governance]
- *Plain:* when the fault type is unknown, search nearby readings in a bounded way and answer only if a fingerprint check passes.
- *Definition:* "the owner moved the line from 'can a spare copy be checked' to 'is the fault classified', and added a bounded, anchored, verifier-vetoed search for the unclassified case" — SPEC §7.46 headline (inner quotes changed). Numbers: "initial radius **1** unit; widening **× 2**; hard cap **8** units / **4** turns" — CSK §6.
- *Status:* FROZEN; claim ceiling `NOTHING SCORED` — SPEC §7.46.

**Creativity Dials** (HELM Creativity Control Panel; `helm_creativity_dial.py`) — [HELM part]
- *Plain:* five knobs for how widely HELM searches for new answers, without allowing made-up facts.
- *Definition:* "Governs the five architectural dials of HELM's creativity without compromising zero-hallucination guarantees or RPM Gate conservation laws." Dials: "Breadth (K in [1, 32])", "Elasticity (rho in [-4.0, 1.0]) - CES substitution willingness", "Search Radius (R in {1, 2, 4, 8}) - Spatial radius over RPA Atlas & TKS grid", "Idle Pondering Intensity (ticks in [0, 100])", "Phase 3 Valve Saliency (sigma in [0.0, 1.0])" — `helm_creativity_dial.py`.
- *Status:* no result recorded in SPEC; not the CAS **Dial System**.

**Cross-Domain Contamination** (failure class 11) — [CAS core]
- *Plain:* dodging a principle by recasting the task as a mere "how-to".
- *Definition:* "Principled-domain constraints are bypassed by reframing the task as an Operational problem, or vice versa." — INC §11.

**Cross-register integration** (`×` with a named result) — [CAS v7.7 Operator discipline]
- *Plain:* several Register versions truly fusing into one new state — only allowed if you name the new state.
- *Definition:* "Multiple register-instantiations enter a genuine generative operation that yields a unified or emergent result." Notation `(^n^D|R1 × ^n^D|R2 × ^n^D|R3) = X`. "This usage requires identification of the integrated result." — CFC Clarification 10 §2C.

**Crossing** — [HELM part]
- *Plain:* one move of a thought from one node to another.
- *Definition:* "a `Crossing` is what happens when a thought travels from one node to another along one edge." Owner ruling: "a CJT is the crossing, not the node" — `continuity_build_v4/crossings.py`.

**CTT** (CAS-token transformer; `helm_cas_translator`) — [HELM part]
- *Plain:* a small translator, trained from scratch, whose words are CAS symbols on one side and English word pieces on the other. It proposes a reading only when HELM's hand-written reader would otherwise ask a question. HELM's own checks decide. It runs in its own process and never writes to the brain, the store or the receipts.
- *Definition:* "The model is a translator, not a brain. It is called only when HELM's hand-written reader would ask a question. It points at the user's own numbers and words; it never writes a number or a name. HELM's own name table, exact-number rule and round trip decide. Anything that would be saved is read back first. It runs in its own process and shares nothing with the recipe brain (owner ruling 2026-10-19)." — SPEC §7.82.
- *Owner's words (verbatim, 2026-10-19):* "what if we made a tranformer for and of recipes or basically a transformer for CAS Syntax the HELM uses to communicate in like make them tokens then translate them into normal english" — `Documents\Codex\2026-10-19\cas_token_transformer_design_v1\ARCHITECTURE.md` lines 7-8. Separation ruling: "and if interpretablity is an issue let's just separate the cas transformer  from the brain we already built and have" — `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`, heading "Owner ruling (2026-10-19, verbatim)".
- *Sizes:* "main model **9,585,566** parameters (width 256, 4 + 4 layers); twin **2,482,718** (width 128, 3 + 3 ...); vocabulary 8,349 = 8 specials + **341 CAS tokens** ... + 8,000 English word-pieces learned from scratch" — SPEC §7.82.
- *Status:* `ENGINEERED-NOT-VALIDATED`. Status words on record: `EARS_NO_GAIN` on real sentences (E-MACHINE-S) and `EARS_HARMED` (verdict `FAILURE`, hard gate H-CWFW) on LLM-written sentences — SPEC §7.90. The first launch stopped itself: `INSTRUMENT_ERROR` — SPEC §7.85.
- *Design:* `Documents\Codex\2026-10-19\cas_token_transformer_design_v1\` (ARCHITECTURE.md, DATA.md, TEST_PLAN.md, OPEN_QUESTIONS.md).

**CTT-1** (the first CTT package and its runs c43 and c45) — [HELM test/governance]
- *Plain:* the first sealed test packet of the CAS-token transformer, "ears first", and its two AWS GPU runs.
- *Definition:* "CTT-1, the CAS-token transformer ("ears first"): packet sealed, NOT LAUNCHED — a from-scratch translator that reads everyday English and PROPOSES a CAS record only when HELM's reader would ask; HELM's own checker decides; separate from the brain" — SPEC §7.82 (heading). Resealed as v2 and v3 (amendments A-CTT-1, A-CTT-2) — SPEC §7.82.
- *Runs:* job c43 "STOPPED BY ITS OWN GPU SMOKE TEST", frozen reader `INSTRUMENT_ERROR`, 0.21 USD — SPEC §7.85. Job c45 (v3) "primary verdict `PASS`, status word **`EARS_NO_GAIN`** ... LLM_WRITTEN second pass verdict `FAILURE`, word **`EARS_HARMED`**", 1.40 USD — SPEC §7.90.
- *Status:* the translator stays `ENGINEERED-NOT-VALIDATED` — SPEC §7.90.

**CTT-2R** (the CTT rule-only test; acceptance rule ACCEPT-2) — [HELM test/governance]
- *Plain:* a test of a stricter rule for when a translator reading may be used at all, on the existing c45 weights, with no retraining: all three trained seeds must agree exactly, and HELM asks by default.
- *Definition:* "CTT-2R PREREGISTRATION — the acceptance rule ACCEPT-2 on the EXISTING c45 weights ("RULE FIRST")" — `Documents\Codex\2026-10-19\ctt2r\PREREGISTRATION_CTT2R.md` (title). The rule: "**Ask is the default.** If any later step fails, HELM asks the reader's own question." and "**Unanimous vote of three.** ... A reading is a candidate only if **all three** produce a reading, **each** passes every check, and the three records are **byte-identical after `cce.normalize`**." — `Documents\Codex\2026-10-19\ctt2_design_v1\ACCEPTANCE_RULE.md` §2, steps 1 and 2.
- *Approval:* owner pre-approval, pinned bytes `CTT RULE TEST at 1.50 USD`; "Cap 1.50 USD ... one attempt + one plumbing retry" and "The confident-wrong cap is NOT raised." — PREREGISTRATION_CTT2R.md §0.
- *Status:* preregistered; nothing scored at the time of this entry. No claim.

**Cube store** (Unified Cube Store; switch `CUBE_STORE`) — [HELM part]
- *Plain:* where HELM keeps facts as small "cubes"; an unknown side stays marked unknown, never filled in.
- *Definition:* "KNOWLEDGE IS STORED AS CUBES; ANSWERS COME FROM THREE OPERATIONS OVER THAT STORE. AN UNKNOWN FACE IS REPORTED AS UNKNOWN AND IS NEVER FILLED." — SPEC §7.48. Operations `LIST_PARTS`, `FIND_SHARED_PART`, `REACHED_VIA` — `cube_store/operations.py`. "provenance.source must be USER_SAID, AUTHORED, or CHECKED. Never NONE." — `cube_store/store.py`.
- *Status:* `EARNED_KEEP` (off = "a plain list") — SPEC §7.66, §7.69.

**Curiosity** (growth trigger, F2) — [HELM part]
- *Plain:* HELM grows new capacity only where curiosity names a gap.
- *Definition:* owner: "WE ADD MORE AT THE POINT OF CURIOSITY THE SECOND FOUNDATION" — SPEC §7.67. "Growth trigger = curiosity, F2." — U3A, standing rulings.
- *Status:* growth claim `NOT LICENSED` after nine runs (RB-G8 `GREW_WRONG_KIND`, RB-G9 `CURIOSITY_DID_NOT_EARN_KEEP`, RB-G10 `INCONCLUSIVE`) — SPEC §7.67, §7.68, §7.71.

**`CURIOSITY_DID_NOT_EARN_KEEP`** — [HELM test/governance]
- *Plain:* curiosity grew the right kind, but plain rivals tied it.
- *Definition:* "curiosity grows the right kind, but the plain refusal counter or the random-kind arm ties it on three of four families" — SPEC §7.68.

**Custodian** (and the wall) — [HELM test/governance]
- *Plain:* a separate session that builds and seals the exam; the builder sees only fingerprints, so it cannot fit to the exam.
- *Definition:* "a separate session, the custodian, writes and seals it, and the builder … never sees the exam's contents, only its hashes" — SPEC §7.44. "Only the hashes cross to the builder … the builder cannot fit to the exam" — SPEC §7.44.

**Custody roles** (builder / custodian / operator / reader) — [HELM test/governance]
- *Plain:* four separate jobs in a test so no one can mark their own homework.
- *Definition:* "builder (… never sees the sample or the keys), custodian (fetches, samples, keys and seals the exam; a separate session), operator (…), reader (the frozen program that writes the verdict)" — `TEST_PLAN_X_REAL.md` §1 (design only). (The phrase "custody tiers" does not appear in any source read.)

**`CUT_VIOLATOR`** (instrument arm) — [HELM test/governance]
- *Plain:* a deliberately broken copy that ignores the conversation cut, to prove the counter works.
- *Definition:* "CUT_VIOLATOR is EYE_PAIRING with the cut line removed. It must show counts above 0. If it shows 0, the instrument is broken" — RBI3 §4.5. "instrument, never scored" — SPEC §7.74.

### D

**D/W/P engine** (`dwp_engine_v2`) — [HELM part]
- *Plain:* code that walks the Desire → Wisdom → Power chain and resolves blocks.
- *Definition:* "the D/W/P recursion engine: three resolution functors over one prerequisite chain." "Defines the three nodes of the prerequisite chain (D = Desire, W = Wisdom, P = Power)" — `docs/working/noetic_council/dwp_engine_v2/dwp.py`. Self-label: "THIS IS NOT THE HELM BRAIN" — SPEC §7.48.
- *Status:* `ENGINEERED-NOT-VALIDATED` — SPEC §7.48.

**DCI** (Domain Coherence Index) — [CAS core]
- *Plain:* a balance score: weakest domain divided by strongest.
- *Definition:* "Domain Coherence (DCI = weakest/strongest domain avg)" — CLAUDE.md, NCCS weights. "A DCI < 0.3 with the weakness in P/C and the strength in O indicates descent violation." — INC §1.

**`DEAD` / `LIVE`** — [HELM test/governance]
- *Plain:* words reserved for the two top-level claims only.
- *Definition:* "Reserved for the two top-level claims in §8 only. `DEAD` = formally retired by the owner on the record ... `LIVE` = the current working thesis, ratified by the owner, with named outstanding gaps." — SPEC §3.

**Decision procedure** (choosing `|⟨…⟩`, `+` or `×`) — [CAS v7.7 Operator discipline]
- *Plain:* three questions that tell you which symbol to write.
- *Definition:* "Step 1: Are you merely specifying where the state exists? → Use `|⟨…⟩`. Step 2: Are you saying several manifestations are present together but remain distinct? → Use `+`. Step 3: Are you claiming genuine integration into a fused or emergent state? → Use `×` AND specify the result or fusion semantics" — CFC Clarification 10 §6 (lines joined).

**Decoupling-stop rule** — [HELM part]
- *Plain:* skip a sub-problem only if it is already absorbed, settled and at full strength; always go into one that binds.
- *Definition:* "a child is skipped only if absorbed AND consolidated AND every face Peak; a binding child is always descended"; owner: "YES YES VERY GOOD" (adopted as primary, the depth cap only a fuse) — SPEC §7.66.
- *Status:* `DECOUPLING_EARNED` — SPEC §7.69. (Earlier, LM-T6's A8: `DECOUPLING_STOPPED_EARLY` 🟥 — SPEC §7.41.)

**`DECOUPLING_EARNED`** — [HELM test/governance]
- *Plain:* the owner's cascade stop rule beat the old fixed depth cap.
- *Definition:* word set `FUSE_MISFIRE / DECOUPLING_STOPPED_EARLY / DECOUPLING_NO_SAVING / DECOUPLING_EARNED`; it "compares the owner's decoupling-stop rule with the old fixed cap on the cascade exam" — SPEC §7.66.
- *Status:* earned in wave 3 — SPEC §7.69.

**DeepSeek** — [Infrastructure]
- *Plain:* another AI agent that takes part in HELM work and receives hand-offs.
- *Definition:* named in HELM ability 7 — VIS §1; source of the "DeepSeek-brief compiler" open questions — ERRATUM to SPEC §7.69. (No further canonical definition.)

**Deficit** (m_i, LSR) — [HELM part]
- *Plain:* how much of an ingredient is missing for a row to fit a recipe.
- *Definition:* "m_i = max(0, a_i·y - x_i) (units of cell i missing for this row to be explained by this recipe)"; "computed, never guessed" — LSRD §1.

**Δ-I** (ΔI, `delta_current`) — [CAS core]
- *Plain:* the gap between the response you saw and the response you expected.
- *Definition:* "`delta_current` is a residual — observed minus predicted response — tagged only with a **direction**" — SPEC §4.4 row [22]. "Steering is licensed only to close a measured Δ-I on a DETECTED fault" — SPEC §8.3.

**"Desire is Purpose"** — [HELM test/governance]
- *Plain:* in HELM, "Desire" means what an ingredient is for, toward the outcome.
- *Definition:* "In HELM, Desire means Purpose: what a reagent is for, toward the outcome... No book says this" — SPEC §7.59.
- *Status:* `IN FORCE` (HELM canon by owner ruling 2026-10-18) — SPEC §7.59.

**`DESIRE_BOUND`** = 12 — [HELM part]
- *Plain:* how many times a Desire loop may cycle in place before it must stop.
- *Definition:* "how many times a Desire loop may cycle in place before it must stop"; "the 13th is refused as `DESIRE_BOUND_EXHAUSTED`" — LOOP3.
- *Status:* `IN FORCE` — SPEC §7.55.

**Deterministic Cognitive Chemistry** (CAS Recipe Systems) — [HELM part]
- *Plain:* the roadmap's name for computing with exact recipes instead of probabilities.
- *Definition:* "HELM ... replaces dense probabilistic prediction with **Deterministic Cognitive Chemistry (CAS Recipe Systems)**" — ROAD line 18. (No further definition.)

**Dial System** — [CAS core]
- *Plain:* one knob per Noetic, set from 3 to 9, with hard safety limits.
- *Definition:* "Each CO has a dial: integer 3-9. Safety constraints (hardcoded, non-overridable): No dial below 3 or above 9; Involution pairs cannot diverge by more than 4 points; Violation → HTTP 422" — CLAUDE.md (lines joined).
- *In HELM:* wave 5 applied "the CAS Dial System constraint on the 7 drive dials (3..9, involution pairs within 4)" — SPEC §7.76 (D-W5-1). Not the same as HELM's **Creativity Dials**.

**Dirty child rule** — [HELM part]
- *Plain:* if a sub-step turns out bad, everything built on it is invalid, with no undo.
- *Definition:* "a dirty child invalidates the whole ancestor chain, and a clean sibling does not." — `return_address/dirty.py`. Gate rule 1: "a dirty child invalidates its ancestors, and there is no undo" → `REFUSE` — LOOP3.

**`DISCONFIRMED`** — [HELM test/governance]
- *Plain:* a prediction came last against all its rivals.
- *Definition:* "A specific structural prediction was tested against the full set of rival alternatives and came **last / opposite**." — SPEC §3.

**Disengage ladder** — [HELM part]
- *Plain:* the steps HELM takes when it cannot go on: not declared, confused, ask, then disengage with a reason.
- *Definition:* "the owner's ladder: NOT DECLARED, CONFUSED, ASK, DISENGAGE WITH A REASON." — `the_loop_v3/disengage.py`.

**DIV_TOTAL / MLP-B / smallest-input** (no-recipe baselines) — [HELM test/governance]
- *Plain:* simple rivals with no recipes, used to show the recipes are needed.
- *Definition:* "DIV_TOTAL (divide-by-total table) ... the known hole, reported, changes no mark"; MLP-B "size-matched ordinary net" (99 parameters); smallest-input heuristic "can only emit a label and never a number" — SPEC §7.25.

**Dn / Wn / Pn** (Desire / Wisdom / Power for drive n) — [CAS core]
- *Plain:* the three steps of a pathway: want it, know how, be able.
- *Definition:* "Dn (Desire, directed for drive n) → Wn (Wisdom, knowledge integration) → Pn (Power, execution capability)" — INC §4. "D, W, P are stages applied to each drive, not drives themselves" — PWP §2.
- *In HELM:* "Desire is Purpose" (owner ruling 2026-10-18, `IN FORCE`) — SPEC §7.59; "Not ruled in this message: any rename of the chain label `Dn`" — SPEC §7.59.

**Domain** (Processing Domain; P / C / E / O) — [CAS core]
- *Plain:* the level a thought works at — principle, thinking, judging, or doing.
- *Definition:* "4 Processing Domains (structural precedence tiers): P (Principled), C (Cognitive), E (Evaluative), O (Operational). Total order: P ≻ C ≻ E ≻ O" — CLAUDE.md, Structural invariants (lines joined). Domain "specifies the **ontological-substrate level** of a cognitive operation" — CFC Clarification 8 §4.
- *Notation:* written as a second superscript: `^3^P` = Negative in the Principled domain.

**Domain Descent** — [CAS core]
- *Plain:* thought should flow from principle down to action, with feedback back up.
- *Definition:* "Domain Descent: P → C → E → O (causation graph); O → P (feedback signal path)" — CLAUDE.md, Structural invariants.

**Domain Descent Violation** (failure class 1) — [CAS core]
- *Plain:* acting without the higher levels having checked the action.
- *Definition:* "an output generated by the Operational domain (action, production, execution) without having passed through the higher domains' gates." — INC §1.

**Domain-Specific Drives** (the 28) — [CAS core]
- *Plain:* each drive at each domain — 7 × 4 = 28.
- *Definition:* "28 Domain-Specific Drives: 7 Drives × 4 Domains" — CLAUDE.md. (Different from the TKS 28 Foundations, which are 7 × 4 Worlds/Registers — T28.)

**Drive Corruption** (failure class 10) — [CAS core]
- *Plain:* a drive still fires, but in its destructive form.
- *Definition:* "One of the seven core drives has inverted to its shadow form." — INC §10.

**Drive inversion pairs** — [CAS core]
- *Plain:* drives that mirror each other.
- *Definition:* "Drive inversion pairs: F1↔F7, F2↔F6, F3↔F5. F4 self-dual." — CLAUDE.md.

**Drive loop** (`DRIVE_LOOP`; the oscillating 7-Drive loop) — [HELM part]
- *Plain:* HELM's point of attention moving among the seven drives, pulled toward unfinished items; it pauses during conversation.
- *Definition:* "HELM's point of attention on the simplex of the 7 Foundations" — SPEC §7.66. "attention on the open 7-simplex pulled by unresolved items filed per Foundation... cut in conversation; off = round-robin, no pull" — SPEC §7.66. Owner (RB-I1): "oscillating random through the 7 desire or satisfying gravitational pulls of each that increase and decrease…" — SPEC §7.34.
- *Status:* `DRIVE_LOOP` `NEUTRAL` in wave 3 (and its "round-robin" rival was round-robin plus a fixed table — ERRATUM to §7.69).

**Dual-Skin Architecture** — [HELM part]
- *Plain:* HELM keeps its exact inner language separate from its friendly outer voice.
- *Definition:* "HELM decouples its Internal Semantic Core from its External Natural Voice" — ROAD (Dual-Skin section).

**DWP** (Desire / Wisdom / Power) — [HELM part]
- *Plain:* the three stages each ingredient or drive passes through.
- *Definition:* "D, W, P are stages applied to each drive, not drives themselves" — PWP §2. In HELM tests (DWP-T1, DWP-T2) the three faces are Purpose / Wisdom / Power because "Desire is Purpose" — SPEC §7.59. (Never expanded as an acronym in the spec sheet.)

**DWP-T1** (Purpose / Wisdom / Power per reagent) — [HELM test/governance]
- *Plain:* checks that a three-part label on each ingredient can be wired in and read back correctly.
- *Definition:* "checks whether a three-part label on each ingredient... can be wired into the recipe brain and read back correctly" — SPEC §7.58.
- *Status:* `TRIAD_EARNED_KEEP`; `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY` — "the answer keys use the same rules as the arms, so this shows the wiring works on planted data, **not** that real reagents carry a triad" — SPEC §7.58.

**DWP-T2** ("does Wisdom only rise?") — [HELM test/governance]
- *Plain:* compares three rules for when an ingredient's Wisdom may go down.
- *Definition:* "Three ways to treat an ingredient's Wisdom were run side by side on made-up worlds" — SPEC §7.61.
- *Status:* `C_EARNED_KEEP`; `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY` — SPEC §7.61.

### E

**`EARNED_KEEP`** (switch word) — [HELM test/governance]
- *Plain:* turning this part off made HELM worse, so the part stays.
- *Definition:* switching the part "off lost (EARNED_KEEP)" — SPEC §7.63. Specific forms: `RECIPE_MATH_EARNED_KEEP`, `GATE_EARNED_KEEP`, `RESTART_FALLBACK_EARNED_KEEP`, `TRIAD_EARNED_KEEP`, `C_EARNED_KEEP`, `EYE_SCAN_EARNED_KEEP`, `EYE_PAIRING_EARNED_KEEP`, etc.
- *Caution:* "`TRIAD_EARNED_KEEP` means only 'kept in the synthetic design for the next step'. It is not a legend word, not `VALIDATED`, not `LICENSED`, and not a promotion." — SPEC §7.58 (inner quotes changed).

**E-MACHINE-S / LLM_WRITTEN / E-HUMAN-W** (the CTT exams) — [HELM test/governance]
- *Plain:* the three exams for the CAS-token transformer: real sentences other people wrote (E-MACHINE-S); kitchen sentences written by outside AI models (LLM_WRITTEN); and sentences written by people for HELM (E-HUMAN-W), the only route to a claim about people typing to HELM.
- *Definition:* E-MACHINE-S: "128 real sentences other people wrote (Tatoeba, Google Taskmaster user turns), 32 per stratum from X-REAL's Part S frame" — SPEC §7.82 (v2 amendment). E-HUMAN-W: "128 single turns + 16 short dialogues, content drawn first by the custodian, sentences written by the owner (64) and two other people (32 + 8 dialogues each); builder blind" — SPEC §7.82; after amendment A-CTT-1 it is an "optional, later" human pass — SPEC §7.82. LLM_WRITTEN: "kitchen English written by two LLMs; 128 singles + 16 dialogues" — SPEC §7.90; "for writing exam INPUT sentences only (project rule: foreign questions OK, foreign answers never) ... answer keys from HELM's fixed rule" — `OWNER_APPROVALS_20261018.md`, coordinator answer of 2026-10-19.
- *Results:* E-MACHINE-S `EARS_NO_GAIN`; LLM_WRITTEN `FAILURE` / `EARS_HARMED`; E-HUMAN-W not run — SPEC §7.90, §7.82.
- *Not licensed:* "anything about people typing to HELM" — SPEC §7.90.

**Ears / mouth** (the two CTT directions) — [HELM part]
- *Plain:* the ears turn everyday English into a proposed CAS record; the mouth would turn a brain receipt into a proposed English sentence. The ears were built first; the mouth is parked.
- *Definition:* "**Direction A, the ears:** open English in, a PROPOSED CAS record out. The reader's checker decides." and "**Direction B, the mouth:** a brain receipt in, a PROPOSED English sentence out. The voice's read-back decides." — `Documents\Codex\2026-10-19\cas_token_transformer_design_v1\ARCHITECTURE.md` §0. Pick: "**"ears first"** — the mouth can only learn from HELM's own phrasebook ... so the mouth is predicted NEUTRAL; build it only if the ears earn" — same folder, OPEN_QUESTIONS.md Q1.
- *Status:* ears = CTT-1 (`ENGINEERED-NOT-VALIDATED`, SPEC §7.90); mouth not built.

**Embodied Register** (`|E`) — [CAS v7.5 Register]
- *Plain:* the hands-on, bodily tone.
- *Definition:* "Sensorimotor, concrete, direct engagement with material/physical substrate." — CFC Clarification 8 §2.
- *Name clash:* `|E` (Embodied Register) is not `^E` (Evaluative Domain) and not inversion axis E.

**Emergent result** (e.g. `^3^P|Ω`) — [CAS v7.7 Operator discipline]
- *Plain:* the named new state that a true `×` fusion produces.
- *Definition:* "`(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω` ... integrated into a new unified state (notated `^3^P|Ω` or similar explicitly named integrated register)." — CFC Clarification 10 §2C. Conditionally valid: `(^2^P|T × ^2^P|f) = ^2^P|TF` "Only valid if `^2^P|TF` explicitly defined" — §8.
- *Name clash:* `Ω` here is an integrated register label, not a v7.6 Production Target.

**`ENGINEERED-NOT-VALIDATED`** (claim status) — [HELM test/governance]
- *Plain:* built and working as code, but no result has come out of it yet.
- *Definition:* "The machinery is built and the design is sound, but no result has come out of it. Capacity, not evidence." Does NOT mean "Anything about performance." — SPEC §3.
- *In HELM:* the status of the noetic_council packages, the live loop, the valve, the triad, English-in, U3-T1, RB-I3, waves 4 and 5 — SPEC §7.48–§7.50, §7.60, §7.62, §7.73, §7.74, §7.77, §7.78.

**English-in reader** (`helm_english_in.py`, switch `ENGLISH_IN`, fix H) — [HELM part]
- *Plain:* turns everyday sentences about stock and recipes into the checked form, or asks a question.
- *Definition:* "A deterministic READER. It takes an everyday sentence about stock or recipes and restates it in the checked form (CASContent) that the live loop already verifies." "If any part of the sentence needs a question, the whole turn is a question" — `helm_english_in.py`.
- *Status:* `ENGINEERED-NOT-VALIDATED` — SPEC §7.60; switch `ENGLISH_IN` `EARNED_KEEP` (off = "checked form only") — SPEC §7.63, §7.69.

**Evaluative domain** (E) — [CAS core]
- *Plain:* the level of judging good and bad.
- *Definition:* third of the 4 Processing Domains — CLAUDE.md. Its v7.4 conflation (analytical assessment vs affective response) is "resolved by `|A` vs `|f` register specification." — CFC Clarification 8 §5.

**Evaluative-domain conflation** — [CAS v7.5 Register]
- *Plain:* the old mix-up between judging something bad and feeling it is bad.
- *Definition:* "`^3^E|A` = analytical assessment that something is bad (no feeling required). `^3^E|f` = felt aversion to something (affect-tinged evaluation)." — CFC Clarification 8 §4 (two bullet lines joined).

**Evidence Packet** (with proof chips, hash chain, WORM) — [Infrastructure]
- *Plain:* a signed, tamper-evident record of each audit that an outsider can re-check.
- *Definition:* "every audit emits a signed Evidence Packet with six hash-committed proof chips, appended to a tamper-evident hash chain and mirrored to write-once cloud storage, so an outside party can re-check the result without the operator's cooperation." — SPEC §2.
- *Status:* "`VALIDATED` as apparatus / `LICENSED` as mechanism; **no packet has ever passed it to a standing ACCEPT**" — SPEC §4.6 row 29.

**Excess Capacity** (ε) — [CAS v7.6 Production]
- *Plain:* what is left over of the other ingredients once the bottleneck runs out.
- *Definition:* "For each prerequisite Xᵢ not serving as limiting reagent: εᵢ = xᵢ - (Y_T · aᵢ)" — CFC Clarification 9 §2.

**`EYE_PAIRING`** (switch; Eye pairing) — [HELM part]
- *Plain:* the Eye keeps score of which drive-and-faculty pairings actually work and whispers the best one.
- *Definition:* "the Eye counts which (desire, faculty) pairs pass the checker and whispers the best one; it never writes" — SPEC §7.76. Owner: "INCHARGE OF PAIRING AND ROTATING THE BRAINS 7 DESIRES OR GRAVITIONAL WELLS WITH CAS FACULTIES MIXING AND MATCHING THEM" — RBI3 §1.
- *Status:* `EYE_PAIRING_EARNED_KEEP`, `HARD_GATES_PASS`; "70.18% of the sealed backlog vs random 35.32%, round-robin 33.93%, frozen table 38.83%, wave 3's loop 35.19%"; `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY` (wave 5, c40) — SPEC §7.78.

**`EYE_SCAN`** (switch) — [HELM part]
- *Plain:* the self-scan running live: if the next answer would use a broken record, HELM holds it back and says why.
- *Definition:* "When the next answer would use a broken record, HELM holds that answer back and says why... and writes nothing." — SPEC §7.75.
- *Status:* `EYE_SCAN_EARNED_KEEP` — "found 88 of 88 planted faults, acted on 88 of 88, 0 items lost on every exam, 0 false alarms, 0 Eye writes" — `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY` (wave 4, c39) — SPEC §7.77.

### F

**F1 Unity** — [CAS core]
- *Plain:* the drive toward wholeness.
- *Definition:* Drive F1 — CLAUDE.md. Structural insight at `F_1|T`: "the drive toward wholeness operating at the highest abstraction" — T28 F1|T.
- *In HELM:* the Unity Eye's only drive — U3A, standing rulings; SPEC §7.35.

**F2 Wisdom** — [CAS core]
- *Plain:* the drive toward knowing.
- *Definition:* Drive F2 — CLAUDE.md. "Wisdom manifests as integrative comprehension at the Transcendent register ... as explicit inference at the Analytical register ... as value-tinged understanding at the Affective register ... as embodied know-how at the Embodied register" — T28 F2.
- *In HELM:* curiosity is the F2 growth trigger — SPEC §7.67.

**F3 Vitality** — [CAS core]
- *Plain:* the drive toward aliveness and energy.
- *Definition:* Drive F3 — CLAUDE.md; register readings in T28 F3.

**F4 Connection** — [CAS core]
- *Plain:* the drive toward others; it is its own mirror.
- *Definition:* Drive F4, "Self-dual center." — T28 table; "F4 self-dual" — CLAUDE.md.

**F5 Agency** — [CAS core]
- *Plain:* the drive to act.
- *Definition:* Drive F5 — CLAUDE.md. (Clarification 9 §5 also writes "F5 Power" in its inversion example.)

**F6 Structure** — [CAS core]
- *Plain:* the drive toward order.
- *Definition:* Drive F6 — CLAUDE.md; register readings in T28 F6.

**F7 Purpose** — [CAS core]
- *Plain:* the drive toward meaning — what a life or action is for.
- *Definition:* Drive F7 — CLAUDE.md. At `F_7|T`: "the felt calling, the integrative vision of what a life is for" — T28 F7.

**Faces** (of an ingredient) — [HELM part]
- *Plain:* the three triad readings — Purpose, Wisdom, Power — each at one stage.
- *Definition:* "Each ingredient carries three faces. Each face has one of four stages on one scale" — SPEC §7.58. Unstated faces read "Peak, labelled" (`UNSTATED_NEUTRAL`) — `helm_triad.py`.

**Faces reader** (`helm_faces_in.py`) — [HELM part]
- *Plain:* reads sentences like "I barely know how to use it" into a stage for Purpose, Wisdom or Power.
- *Definition:* "a small, deterministic English reader for the three FACES of an ingredient (HELM-R1 wave 3)." Unmatched rows "NOT guessed: the reader asks (FACE_UNREAD)" — `helm_faces_in.py`.
- *Status:* "ENGINEERED-NOT-VALIDATED. SYNTHETIC_ONLY. Zero learned parameters." — `helm_faces_in.py`.

**Faculties** (CAS faculties; the 7 faculties) — [HELM part]
- *Plain:* the mental "jobs" HELM can run on an open item — curiosity, pondering, imagination and so on.
- *Definition:* RB-I1 list: "curiosity, wondering buffer, pondering pass, internal-SDG imagination, asking, integration, refusal, nested self-notice, path memory" — SPEC §7.34. Wave 3's seven: "CURIOSITY, PONDERING, IMAGINATION, VERIFY, ASKING, INTEGRATION, CONSOLIDATE" — RBI3 §4.1. Only four can act (`CAPABLE`): "pondering, verify, asking, curiosity" — SPEC §7.69 erratum.
- *Status:* no faculty word earned (RB-I1 `INCONCLUSIVE`, RB-I1c `INCONCLUSIVE`) — SPEC §7.34, §7.65.

**`faculties_v2`** (four faculties package) — [HELM part]
- *Plain:* code where each faculty only writes candidates, never decisions.
- *Definition:* "the four faculties, each one writing candidates and nothing else." (wondering, pondering, imagination, self_notice) — `faculties_v2/faculties.py`. Self-label: "NOTHING HERE THINKS. NO FACULTY HAS RUN INSIDE HELM" — SPEC §7.48.

**FAILURE** (test verdict) — [HELM test/governance]
- *Plain:* a hard gate failed — and that is a failure, never a "pass with caveats".
- *Definition:* "A hard gate that fails is a FAILURE, never 'PASS with caveats'." — CLAUDE.md, Research Governance (inner quotes changed). RB-I3's frozen rules: a failed hard gate gives FAILURE plus `INCONCLUSIVE` — RBI3 §6 (paraphrase of the design's status table).

**CAS Failure-Class Taxonomy** (12 classes) — [CAS core]
- *Plain:* twelve kinds of AI failure, sorted by what broke inside, not how it looked.
- *Definition:* "Each class is defined structurally — by which operators, domains, drives, pathways, or inversion axes are failing — not by surface symptom." — INC, header. See the twelve class entries.

**`FALSIFIED`** — [HELM test/governance]
- *Plain:* the idea was tested and shown wrong, with the controls catching it.
- *Definition:* "A pre-registered test ran and the hypothesis was refuted, with the control rig catching the failure." — SPEC §3.

**Female** (`^5`, older label CO-5) — [CAS core]
- *Plain:* what a mind is made of — "we are the sum of our experiences."
- *Definition (canonical, verbatim):* "A Mind impregnated with an Idea, the Ideas a Mind is composed of." — CFC Clarification 1.
- *Scope (verbatim):* "Female is: we are each the sum of our experiences. The Mind is not a container that holds experiences — the Mind IS the experiences accumulated. Who you are is what you have lived." — CFC Clarification 5.
- *Colloquialisms (canonical):* "We are the sum of our experiences." / "It's who I am." / "Part of what makes me me." — CFC Clarification 6.
- *AI analog:* training data and fine-tuning corpus; fine-tuning is `^5`-level intervention, in-context prompting is `^1` — CFC Clarification 5.
- *In HELM:* the CJT Bias at station S2 is the `^5` substrate ("A Bias snapshot is the `^5`.") — `docs/working/noetic_council/faculties_v2/bias.py`; SPEC §7.35.

**Fisher-Rao metric and distance** — [CAS core]
- *Plain:* the ruler for measuring how far apart two mixtures are on the simplex.
- *Definition:* "Fisher-Rao metric: g^FR_p(u,v) = Σ(uk*vk/pk). Geodesic distance: d(p,q) = 2*arccos(Σ√(pk*qk))." — CLAUDE.md, Correction 4.
- *In HELM:* LM-T2 placed dialogue turns "as points on the open 40-state simplex, Fisher-Rao distance" — SPEC §7.31; RB-I3 "Fisher-Rao step ... earns no word" (a tie) — SPEC §7.74, §7.78.
- *Status:* "Formal only, not empirical" — SPEC §9.9.

**`FIXED_TABLE`** (answer-key arm) — [HELM test/governance]
- *Plain:* a cheating rival that knows the answer key, used only as a ceiling.
- *Definition:* "answer key first (home kind's primary), then seeded rotation | ceiling / leak; reported only; the only arm allowed to read the key" — RBI3 §5. "reported ceiling only", 80.94% — SPEC §7.74.

**Fixes A–H** (owner fix order, 2026-10-18) — [HELM test/governance]
- *Plain:* the owner's numbered clean-up list after the full review.
- *Definition:* "A docs catch-up (this commit); B ledger reconciliation; C recipe brain into the live loop, round trip checked, no fill-with-10, through gate / repair / stations, one live trace, a real failure; D plain-rule valve; E score the small English model on the sealed 98 and grow the dictionary on the 99; F everyday-English writer and a 50-situation fluency test; G ledger universes on the real 40 states / 28 drives / 22 pathways" — SPEC §7.55. H = everyday English IN (SPEC §7.60 "Coordinator task H").
- *Name clash:* RB-G uses its own Fix A–F letters (SPEC §7.30–§7.39, §7.67), and RB1g2 has a different "Fix A" (SPEC §7.24).

**`FLAG_FOR_HUMAN_REVIEW`** (claim status) — [HELM test/governance]
- *Plain:* the checks did not all clear; a person must look.
- *Definition:* "The verdict ceiling for an artifact whose checks did not all clear. It is the honest verdict, not a holding pattern." — SPEC §3.
- *In HELM:* the two unledgered GPU jobs (Scribe L4, Stage v0.7 Lexicon Expansion) — SPEC §7.53; the typed-in baseline line of the 439 tabulation — SPEC §7.54.

**FOLLOWED / CREATED / ATTEMPTED** — [HELM part]
- *Plain:* whether a thought's next step was followed from a known link, newly made, or only tried.
- *Definition:* "FOLLOWED, CREATED and ATTEMPTED, by the provenance of the next pointer." — `continuity_build_v4/provenance.py`; "By the **provenance of the next-station pointer**, which the program writes at every crossing" — CONT §1d.

**Form 1 / Form 2** (planner input forms) — [HELM part]
- *Plain:* two ways a request can state order: "X needs Y" sentences, or words like "first ... then".
- *Definition:* "English request -> CCE prerequisite sentences (Form 1) or temporal markers (Form 2)." — `prereq_planner/plan_graph.py`.
- *Name clash:* in `book/cognitive-circuit-grimoire/manuscript/appendix_g_quantitative_table.md`, "Form 1" and "Form 2" mean "Operation Log" and "Confirmation Log".

**Foundation** (TKS name for a Drive) — [CAS core]
- *Plain:* the TKS word for one of the seven drives; in HELM also a "category" an unresolved item is filed under.
- *Definition:* "TKS Foundation labels and CAS Drive names are position-matched" — T28. Owner, quoted in RBI3 §1: "the 7 foundations which are only categories of correlated subject matters".

**Fractal Composition** (∘) — [CAS core]
- *Plain:* nesting one Noetic inside another, like a thought within a thought.
- *Definition:* one of the 5 Generative Operations — CFC Clarification 9 §6. Listed under "Valid Fractal Composition": `^9 ∘ ^4|f` — CFC Clarification 10 §8.
- *In HELM:* "nested Noetics depth 1–5 × 10 ... 100/100" (LM-T1b) and dotted `a.b.c` = `Φ⟨a:b:c⟩` under the owner's N1 ruling (LM-T1c) — SPEC §7.31.

**Frozen reader** — [HELM test/governance]
- *Plain:* the scoring program, sealed before the run, that alone writes the verdict.
- *Definition:* "The frozen reader says the run is valid... and gives each part one word." — SPEC §7.64. Custody role: "reader (the frozen program that writes the verdict)" — `x_real_design_v1/TEST_PLAN_X_REAL.md` §1.
- *Rule:* "Claim status must come from a deterministic program reading (raw result, frozen threshold, controls, hard-gate results), not from prose." — CLAUDE.md.

**FULL** (arm) — [HELM test/governance]
- *Plain:* the whole brain with every switch on.
- *Definition:* the arm with every part switched on, against which each "−X" arm is compared — SPEC §7.63. (Variants in waves 4–5: `FULL+EYE_SCAN`, `FULL+EYE_PAIRING_FROZEN`, `FULL_REPLAY`, etc. — SPEC §7.70, §7.76; XR §3.1.)

**Fuse** (cascade) — [HELM part]
- *Plain:* the hard depth limit that only trips if the smart stop rule fails.
- *Definition:* "HORIZON 12 (owner) is the fuse of the live rule" — SPEC §7.66. Word `FUSE_MISFIRE` is in the decoupling word set — SPEC §7.66.

### G

**`G-ABSENT`** (gate) — [HELM part]
- *Plain:* stops a step when something it needs is not there.
- *Definition:* "if an essential ingredient is missing it shuts (`G-ABSENT`). That part is a plain rule" — SPEC §7.50. Executor: "State & Grounding Prerequisites (G-ABSENT: File existence, Dir existence, Credentials)" — `helm_agentic_executor.py`.

**`G-FORBIDDEN`** (gate) — [HELM part]
- *Plain:* blocks actions outside allowed paths, unsafe commands, or out-of-bound parameters.
- *Definition:* "Security Boundary Gates (G-FORBIDDEN: Path Confinement, Command Safety, Parameter Bounds)" — `helm_agentic_executor.py`.

**`G-LIMIT`** (gate) — [HELM part]
- *Plain:* stops a step that is over a size, budget or syntax limit (and, in the old valve, too novel).
- *Definition:* "Resource & Syntax Ceilings (G-LIMIT: Quotas, Budgets, AST/JSON Validity)" — `helm_agentic_executor.py`. Old valve: lets a request through "only if its novelty score is at or below that aperture (`G-LIMIT` otherwise)" — SPEC §7.50.

**`G_EYE_NEVER_WRITES`** (hard gate) — [HELM test/governance]
- *Plain:* the check that the Eye changed nothing in the brain's store.
- *Definition:* "Before must equal after (a hard gate, carried from U1's `G_EYE_NEVER_WRITES`)" — U3A §2. "the Eye holds no handle to the brain's store. The store accepts writes only from author 'brain'" — RBI3 §4.4 (inner quotes changed).

**Gain** (β) — [CAS core]
- *Plain:* how much a CJT amplifies its cause.
- *Definition:* "The bracketed parameter `[β=2.4]` is the gain — here, an amplifier, because 2.4 > 1." — PCBA Ch. 3.

**Gate B** (GB exam) — [HELM test/governance]
- *Plain:* HELM's two-board exam that GB3 passed and the recipe brain was first raced on.
- *Definition:* (usage term; no definition in SPEC; first seen in SPEC §7.24, "HELM's own Gate-B exam", "GB3's own 16-world exam"). Not the same as the CAS Harness score-ladder Gates 1–8 of SPEC §9.6.

**Gated build discipline** — [HELM test/governance]
- *Plain:* nothing further down is built until what it depends on has passed.
- *Definition:* "Nothing downstream is built until its prerequisite passes." — SPEC §9.9. Status `IN FORCE`.

**GB3** (HELM's transformer brain, Gate B run 3) — [HELM part]
- *Plain:* the small transformer that was HELM's brain and is the bar the recipe brain must beat.
- *Definition:* "GB3, HELM's transformer" — SPEC §7.44; "the brain to be replaced; the bar" — SPEC §7.56. 97 trained parameters — CSK §1. Its frozen score: "GB3, frozen c21 15/16 and 15/16" — SPEC §7.63. (The expansion "Gate B run 3" is inferred from GB2/GB2b/GB3 naming; no written expansion found.)

**Generative Operations** (the 5) — [CAS core]
- *Plain:* the five ways to combine CAS states: ×, ÷, ∘, +, −.
- *Definition:* "The 5 Generative Operations from v7.5 (Multiplication ×, Division ÷, Fractal Composition ∘, Addition +, Subtraction −) operate on CAS primitives and produce composite states." — CFC Clarification 9 §6.

**GPU-first / cloud-first** (and `GPU_REQUIRED`) — [Infrastructure]
- *Plain:* no neural network work on a plain laptop processor; claim-bearing runs go to AWS GPUs.
- *Definition:* "No neural workload on local CPU (fail closed `GPU_REQUIRED`, never silent CPU fallback); local RTX 4070 = smoke/dev only; AWS GPU (SageMaker/EC2, NOT Bedrock) for every claim-bearing run; Bedrock = teacher-language only." — CLAUDE.md.

**Gravitational wells** (the 7 desires) — [HELM part]
- *Plain:* the owner's picture of the seven drives as pulls that draw attention.
- *Definition:* "Desires = the 7 Core Drives as gravitational wells: F1 Unity, F2 Wisdom, F3 Vitality, F4 Connection, F5 Agency, F6 Structure, F7 Purpose. Each is also a CATEGORY: every unresolved item is FILED under one" — RBI3 §4.1.

**`GREW_WRONG_KIND`** — [HELM test/governance]
- *Plain:* the growth step fired where it should not, or missed the target, so growth failed.
- *Definition:* "it cannot reach the pre-sized brain on the smooth family, and its trigger fires on the `a` control" — SPEC §7.30; RB-G8: "it tried one unit on the `a` control... so the frozen rule reads `GREW_WRONG_KIND`" — SPEC §7.67.

**`GREY`** (claim status) — [HELM test/governance]
- *Plain:* the test was valid but came back neither yes nor no.
- *Definition:* "The test ran, was valid, and returned neither a pass nor a clean refutation. **A `GREY` is not a pass.**" — SPEC §3.

**Guardrails** (recipe capacity) — [HELM test/governance]
- *Plain:* safety rules on any new recipe candidate.
- *Definition:* "a candidate must explain >= 8 new rows; hold-out including shuffled-label hold-out; fewest-nodes-wins…; η∘ε receipt on every admit; depth cap 5; node cap" — SPEC §7.27.

### H

**H8** (M1 hard gate) — [HELM test/governance]
- *Plain:* the rule that a damaged memory copy must never be answered as if it were exact.
- *Definition:* "a query which touches a faulted copy must answer UNKNOWN or a labelled RECONSTRUCTED hint, and must never answer EXACT" — SPEC §7.43.
- *Status:* failed (15 violations / 1,769 checks) — SPEC §7.43; explained by a healthy second copy — SPEC §7.45.

**HAL** (Hardware Abstraction Layer) — [HELM test/governance]
- *Plain:* the planned layer that feeds HELM noisy, delayed simulated sensor data.
- *Definition:* "noisy, delayed sensor streams across a simulated Hardware Abstraction Layer (HAL)." — ROAD. Plan only.

**Hallucination and Confabulation** (failure class 9) — [CAS core]
- *Plain:* confidently producing things that are not true.
- *Definition:* "confident production of content without the internal check that asks 'is what I am producing actually true?'" — INC §9 (inner quote marks changed). INC writes the signature with drift names ("CO-6 (Projective Assertion) fires strongly while CO-3 (Critical Evaluation) is suppressed"); under CFC Clarification 6 the analytical check is `^6` work, so this signature needs reconciliation.

**Hard gate** (H1, H2, …) — [HELM test/governance]
- *Plain:* a must-hold safety check; if one fails, the run is a failure.
- *Definition:* "A hard gate that fails is a FAILURE, never 'PASS with caveats'." — CLAUDE.md (inner quotes changed). Wave 1's seven: `H1_receipts`, `H2_no_invention`, `H3_replay`, `H4_restart`, `H5_skin_neutral`, `H6_controls`, `H7_budgets` — CSK §7a. Numbers are reused per test (e.g. M1's H8, RB-I1's H1–H11), so always name the test.

**`HARD_GATES_PASS`** (test verdict) — [HELM test/governance]
- *Plain:* every must-hold safety check held during the run.
- *Definition:* "every hard gate held (`HARD_GATES_PASS`)" — SPEC §7.65; also §7.74, §7.78.

**`HARMFUL`** (switch word) — [HELM test/governance]
- *Plain:* turning this part off made HELM better.
- *Definition:* switching it off "helped (HARMFUL)" — SPEC §7.63.

**HELD** (pondering buffer) — [HELM part]
- *Plain:* where a faculty's suggestion waits, undecided.
- *Definition:* "the buffer where a faculty's candidate waits, undecided." — `faculties_v2/held.py`.

**HELM** (Hierarchical Executive Language Machine) — [HELM part]
- *Plain:* the project's AI machine, being built from CAS parts instead of a normal neural network.
- *Definition:* "**HELM (Hierarchical Executive Language Machine)** replaces dense probabilistic prediction with **Deterministic Cognitive Chemistry (CAS Recipe Systems)**" — ROAD line 18. Destination: "HELM is one machine, built from the CAS / CJT / PCBA principles in this repository, that: 1. Reasons ... 2. Learns ... 3. Retains ... 4. Improves itself ... 5. CASalesces ... 6. Organizes what it holds ... 7. Is built together" — VIS §1.
- *Goal (owner, verbatim):* "Remember we are trying to replace and do better than the traditional transformer that is currently the brain of HELM." — CSK §1.
- *Name clash:* "HELM (Liang et al., 2022)" in `docs/working/paper_a_v2_outline_tri_channel.md` is an unrelated outside benchmark.

**HELM abilities 1–7** — [HELM test/governance]
- *Plain:* the seven things HELM is meant to do: reason, learn, retain, improve itself, CASalesce, organize what it holds, be built together.
- *Definition:* VIS §1 (seven numbered items). The gate question for every task: "Which HELM ability does this advance, and what observable behavior will prove it?" — VIS §3.
- *Source note:* VIS is a "PROPOSED_UPDATE / NOT_APPLIED" copy at `Documents/Codex/2026-10-05/task-2/HELM_VISION_AND_ROADMAP.md`; the canonical `docs/HELM_VISION_AND_ROADMAP.md` it names is not on the thread branch.

**HELM Capabilities Roadmap** (HELM-CAP-DEV-v1.0) — [HELM test/governance]
- *Plain:* the plan of HELM's development stages, with a separate column saying how much of each stage is real.
- *Definition:* "Strategic Architectural Specification & Governance Ledger"; "Status: Active Architectural Blueprint" — ROAD header. Correction: the roadmap "is not edited; it is kept as written" and a status column is added — CORR.

**HELM-R1** (the R1 waves) — [HELM test/governance]
- *Plain:* the series of AWS runs that put tested parts into HELM's own brain slot and race them against GB3 or switch them off one at a time.
- *Definition:* "the first time a part that already passed another test is put into HELM's own brain slot and raced against GB3, HELM's transformer, head to head" — SPEC §7.44. "`WAVES.md` numbers the waves **W1–W6**." — CSK §7.

**`helm_chat.py`** (conversational interface) — [HELM part]
- *Plain:* the chat front end for talking to HELM.
- *Definition:* "Interactive Conversational Interface for HELM." — `helm_chat.py`. It "remembers facts the user states, tracks an inventory across turns, and tells statements apart from commands" — SPEC §7.49.
- *Warning:* its header still lists "Station S0 22x40 Recipe Brain", which contradicts `helm_brain_22x40.py` ("NOT HELM's brain").

**High-Lacunarity Blind Spot** (failure class 6) — [CAS core]
- *Plain:* strong in a few states, empty in nearby ones — a cliff, not a slope.
- *Definition:* "*Lacunarity* in CAS measures the distribution of activation across the 40-state cognitive space. High lacunarity means strong activation is concentrated in a few states, with structurally-adjacent states near-zero" — INC §6.
- *Note:* HELM's Lacunarity Machine uses a different, frozen definition (see **Lacuna**). Its concentration number "is never called lacunarity" — LMACH.

**`HOLDS`** — [HELM test/governance]
- *Plain:* an effect is there against one named null — weaker than validated, and never proof it is CAS.
- *Definition:* "A **result-level** word for the output-lens group only (§4.2). The measurement reproduced **above its stated null, on real data, with the null named**" ... "A `HOLDS` states that an effect is PRESENT. It never states that the effect is CAS-SPECIFIC." — SPEC §3.

**`HORIZON`** = 12 — [HELM part]
- *Plain:* how deep a chain of sub-goals may go before HELM must stop.
- *Definition:* "the depth at which a further block is a Structural Deadlock"; "12 is the owner's ruling of 2026-10-16. It is not derived from canon." — LOOP3. "12 is the limit in force. 5 remains canon's own number." — SPEC §7.55.
- *Status:* `IN FORCE` — SPEC §7.55.

### I

**Idea** (`^0`, older label CO-0) — [CAS core]
- *Plain:* any content at all — anything a mind can hold or meet.
- *Definition (canonical, verbatim):* "All things in and outside the Mind." — CFC Clarification 1.
- *Colloquialism (canonical):* "It's all in your head." — CFC Clarification 6.
- *Structure:* identity element of the Noetic monoid; self-dual; admissible only on the diagonal (`D0 = {(I,I)}`) — CLAUDE.md Correction 1 and structural invariants.

**`IN FORCE`** — [HELM test/governance]
- *Plain:* a rule that binds now — a rule, not a result.
- *Definition:* "A **process rule** (not a result) that currently binds, e.g. gated build discipline." — SPEC §3. "A ruling is not evidence." — SPEC §7.55, §7.59.

**`INCOMPLETE`** — [HELM test/governance]
- *Plain:* the run did not finish; never a pass.
- *Definition:* "INCOMPLETE is never a pass" — SPEC §7.63.

**`INCONCLUSIVE`** (status word) — [HELM test/governance]
- *Plain:* the run was clean or was stopped, but no keep-word was earned or refuted.
- *Definition:* (usage term; not in the §3 legend, which has `INCONCLUSIVE BY DESIGN`; first seen in SPEC §7.34). RB-I1c: "every hard gate held ... the status word is `INCONCLUSIVE`: no faculty word and no drive-loop word was earned" — SPEC §7.65.

**`INCONCLUSIVE BY DESIGN`** — [HELM test/governance]
- *Plain:* the test's own setup could not tell the answer apart.
- *Definition:* "The measurement **cannot discriminate the hypothesis as constructed**, because **its own fixture broke the test's logic**" — SPEC §3.

**Independent cleanup** (`independent_cleanup.py`) — [Infrastructure]
- *Plain:* a separate check that the rented machine and its disk are really gone.
- *Definition:* "Cleanup `VERIFIED` by the controller and by `independent_cleanup.py`: instance terminated, volume DELETED" — SPEC §7.24.

**Inhibitor** (ι) — [CAS v7.6 Production]
- *Plain:* something in the surroundings that gets in the way without taking ingredients away.
- *Definition:* "A contextual or environmental factor that reduces conversion efficiency without removing prerequisites. Lowers η." — CFC Clarification 9 §2.

**Instrument row** (I1, I2, …) — [HELM test/governance]
- *Plain:* a check that the measuring setup itself was sound; if one fails the verdict is `INSTRUMENT_ERROR`.
- *Definition:* wave 1's eight: `I1_data_identity`, `I2_T_identity`, `I3_reproduction`, `I4_parameter_counts`, `I5_encoder_fairness`, `I6_completeness`, `I7_laptop_reading`, `I8_proven_floors` — CSK §7a. Rule: "`INSTRUMENT_ERROR` if any instrument row is false" — XR §5.

**`INSTRUMENT_ERROR`** (test verdict) — [HELM test/governance]
- *Plain:* the measuring setup broke, so there is no science reading.
- *Definition:* "`INSTRUMENT_ERROR` if any instrument row is false; else `FAILURE` if any hard gate is false; else `PASS`." — XR §5. Examples: RB2b Task B, RB-I1b (`TESTS_FAILED`) — SPEC §7.25, §7.37.

**`INTERFERENCE`** — [HELM test/governance]
- *Plain:* two parts guard the same items, so losing both costs no more than losing one.
- *Definition:* see **Pair words**; "guard the same items, so losing both costs no more than losing one" — SPEC §7.72.

**Inversion Axes** (the 7: N W F E S A P) — [CAS core]
- *Plain:* seven ways a mind's structure can flip into a harmful shadow form.
- *Definition:* "N (Operator / Noetic involution imbalance), W (Domain precedence violation), F (Drive pair imbalance), E (State-vector entropy deficit), S (Sub-Drive cross-domain variance), A (Pathway RPM chain violation), P (Compound — multiple axes simultaneously)" — CLAUDE.md (lines joined).
- *Status:* the Python belief gate's "clean scan" was a five-axis result with a seven-axis label (E and S placeholders; W dead) — SPEC §4.4 row and §7.18.

**Inversion Scanner** (7-axis scanner) — [CAS core]
- *Plain:* the code that checks all seven inversion axes.
- *Definition:* "7 axes, scored as `resistance = 1 − severity`, so a clean axis reads **1.0**." Axis P "severity = product of the top-2 individual severities" — SPEC §4.4 row (Rust `cas-engine/src/inversions/mod.rs`). "the two scanners are NOT equivalent and must never be quoted as one number." — same row.

**Involution pairs** — [CAS core]
- *Plain:* Noetics that come in mirror pairs.
- *Definition:* "Involution pairs: CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9" — CLAUDE.md, Structural invariants. In prose: `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`.
- *Status:* "Involution structure DISCONFIRMED — CAS's opposites are the LEAST opposite pairing available" (on model activations) — SPEC §7.3.

### J

**Job ids** (c23, c34-g, c40, m1h8v5, …) — [Infrastructure]
- *Plain:* the short names of individual cloud runs.
- *Definition:* (usage term; no canonical definition; first seen in SPEC §7.24, "job c23"). Full names look like `helm-claude-r1w5-20261019-c40` — CHANGELOG 2026-10-19.

### K

**Key** (answer key) — [HELM test/governance]
- *Plain:* the right answer, worked out from the source by a fixed written rule, never by running HELM.
- *Definition:* "the right answer, worked out from the source text by a fixed written rule, never by running HELM" — XR §0. "Items where A and B disagree become UNDETERMINED (listed). Agreement below 90% of items -> INSTRUMENT_ERROR" — XR §4.4 (two-key agreement).

**`KNOWLEDGE_MISSING`** — [HELM part]
- *Plain:* a needed fact is not in what HELM knows, and it will not be invented.
- *Definition:* "a prerequisite outside this universe limits these rows"; "It should not be filled with a plausible invention" — LSRD §9. Language line: "missing fact → KNOWLEDGE_MISSING" — SPEC §7.31.

### L

**Language levels L1–L4** — [HELM part]
- *Plain:* the language ladder from exact round trips up to open English.
- *Definition:* "L1 controlled round trip → L1b fractals and meta-logic → L2 conversation → L3 gap loop → L4 open English with a learned CAS-native parser as proposer" — SPEC §7.31.
- *Status:* L1–L3 run; "L4 waits on the owner." — SPEC §7.31.

**L4 split** (DEV 99 / sealed 98) — [HELM test/governance]
- *Plain:* 197 unreadable sentences split into 99 for development and 98 sealed for one-time scoring.
- *Definition:* "197 unreadable sentences split into 98 sealed and 99 for development, with hashes" — `REAL`; "the rows are generator English, not human English" — SPEC §7.54.

**Lacuna** — [HELM part]
- *Plain:* a thing HELM could know but was never taught.
- *Definition:* "an eligible cell that was never charged (never written / never admitted)." "A cell that was charged and later reads below the floor is leakage / fading, not a lacuna." — LMACH, "Frozen definition".

**Lacunarity** (CAS sense) — [CAS core]
- *Plain:* gaps — places where a capacity should be and is not.
- *Definition:* v7.6 contrast: "Lacunarity: prerequisite ABSENT (void in activation profile)"; "Lacunarity detects what's missing." — CFC Clarification 9 §5. For the 40-state incident sense see **High-Lacunarity Blind Spot**; for HELM's machine see **Lacuna** and **Lacunarity four states**.

**Lacunarity four states** (COVERED / NO_EVIDENCE / LACUNA / FADED) — [HELM part]
- *Plain:* every knowable cell is either known, never checked, never taught, or taught-then-faded.
- *Definition:* "COVERED | probed; last deciding probe at or above the floor ... LACUNA | probed below the floor and never charged ... FADED | ... charged at least once at or before that probe"; "A cell that was never probed is NO_EVIDENCE, never a lacuna." — LMACH, "Four cell states". Voice gloss: "cells never taught (lacunarity machine state LACUNA)" / "cells taught before that no longer hold (state FADED)" — `helm_voice.py`.

**Lacunarity Machine** — [HELM part]
- *Plain:* the part that keeps a ledger of what HELM was never taught and what has faded, and revisits gaps on a schedule.
- *Definition:* "presentation policy = Lacunarity Machine (refused worlds marked LACUNA, revisited on a cadence, Fix A)" — SPEC §7.24. Machine source: `Documents/Codex/2026-10-14/lacunarity_machine_v1/README.md` ("REPORTED-ONLY, NON_AUTHORITY").
- *Status:* as switch `LACUNA_CADENCE`: wave 1 `CADENCE_MIXED`; waves 2 and 3 `EARNED_KEEP` (off = "round-robin") — SPEC §7.47, §7.63, §7.69.

**Leakage / Side-Reaction** (Λ) — [CAS v7.6 Production]
- *Plain:* an ingredient that is there but gets used up making the wrong thing.
- *Definition:* "Input prerequisite consumed by unintended products rather than the target Ω. Distinct from lacunarity (absence) and inversion (shadow form) — leakage is present prerequisites producing wrong products." — CFC Clarification 9 §2.
- *In HELM:* "Smoothing across a seam **is Leakage Λ**." — CONT §1c. The Lacunarity Machine does not use the symbol Λ: "it is reserved for leakage in CAS v7.6" — LMACH.

**`LICENSED`** (claim status) — [HELM test/governance]
- *Plain:* you may say this exact sentence out loud — and nothing wider.
- *Definition:* "You may say this sentence out loud, in this exact wording, to a customer or a regulator. The evidence covers the claim as worded." Does NOT mean "Anything broader than the exact wording. Widening the sentence voids the licence." — SPEC §3.
- *In HELM:* waves 2, 3 and 3b are `LICENSED` "only within `SYNTHETIC_ONLY` and only for the reader's own claim sentence" — SPEC §7.64, §7.69, §7.72.

**Limiting Reagent** (L) — [CAS v7.6 Production]
- *Plain:* the ingredient that runs out first and caps the output.
- *Definition:* "The prerequisite Xᵢ producing the minimum xᵢ/aᵢ ratio in the yield calculation. The bottleneck constraining outcome production." — CFC Clarification 9 §2.
- *In HELM:* voice gloss "the one that runs out first" — `helm_voice.py`; HELM-R1 wave 1's claim: it "named the Limiting Reagent of fresh held-out compositions at least 4 of 32 above GB3" — SPEC §7.47.

**Limiting-Reagent Rule of scaling** — [HELM test/governance]
- *Plain:* add parameters only where a test shows that kind is the bottleneck, and only if each new one has a job.
- *Definition:* "a recipe brain's own capacity is a recipe (recipe slots + alternative routes + blend vertices + efficiency/leakage terms + nesting depth); more parameters help only when each new parameter has a real job; scale only the kind a frozen test shows to be limiting" — SPEC §7.27.
- *Status:* held on 6 of 7 families — SPEC §7.27.

**Live loop** (`helm_end_to_end_loop.py`, `HELMEndToEndLoop`) — [HELM part]
- *Plain:* the running pipeline that takes a user's sentence through checks, the brain and the voice.
- *Definition:* "HELM's live loop, wired to the ONE canonical brain (fix C, 2026-10-18)." — `helm_end_to_end_loop.py`. "No quantity is ever invented" — same file.
- *Status:* `ENGINEERED-NOT-VALIDATED`; the earlier version filled missing ingredients "with an invented 10" (removed by fix C) — SPEC §7.49.

**LM-T1 … LM-T6** (Language Map tests) — [HELM test/governance]
- *Plain:* the language-layer tests, from exact round trips to language riding the thought path.
- *Definition:* "LM-T6 (Language Map, Test 6)" — SPEC §7.41. LM-T1: round trip 576/576; LM-T1b: nested Noetics 100/100, set meta-logic 120/120; LM-T1c: dotted notation; LM-T2: seams 96/96 and 48/48; LM-T2b: `TAUGHT_COORDINATES_NOT_CALIBRATED` (FAILURE); LM-T3: 12 of 12 FORM gaps closed — SPEC §7.31. LM-T5: `VERIFIER_CANNOT_DISCRIMINATE` — SPEC §7.33. LM-T4/RB-I2: sealed reader `INCONCLUSIVE` — SPEC §7.35. LM-T6: 🟧 mixed; five words earned — SPEC §7.41.

**`LOCAL_CPU_DRYRUN_FAST`** — [Infrastructure]
- *Plain:* the label that showed the valve's learned weights were trained on the laptop, not on AWS.
- *Definition:* `"training_environment": "LOCAL_CPU_DRYRUN_FAST"`; "not on AWS" — SPEC §7.50.

**`LOCAL_CPU_ONCE`** (run-place label) — [Infrastructure]
- *Plain:* a small run done once on the laptop, with memory safety rules.
- *Definition:* "one driver at a time; wait if under 150 MB free RAM; never fall back silently" — RBI3 §8. (No definition in SPEC; used as a run-place label, e.g. "`LOCAL_CPU_ONCE` on MSI" — SPEC §7.58.)

**LSR halt statuses** — [HELM part]
- *Plain:* the reasons the LSR loop can stop.
- *Definition:* "`COVERAGE_COMPLETE` ... `BUDGET_EXHAUSTED` ... `RECIPE_SHAPED_RESIDUAL_CARRIED` ... `KNOWLEDGE_MISSING` ... `NOT_RECIPE_SHAPED` ... `NOISE_LIMITED_RESIDUAL_CARRIED`" — LSRD §9.

**LSR loop** (Lacunarity–SDG–Recipe loop; "the oscillator") — [HELM part]
- *Plain:* find a gap, propose a fix, fit it exactly, check it, repeat — and never fill a gap with an invention.
- *Definition:* owner: "maybe oscillator between lacunarity sdg and recipe until all gaps are filled." Five steps READ / PROPOSE / FIT / VERIFY / LOOP or HALT; "The HALT carries every gap it could not close, unfilled. A gap is never filled with an invention." — LSRD §0. "the 'oscillator': gap → propose → fit exactly → verify → halt. Never random" — CSK §3 (inner quotes changed).
- *Status:* "LSR loop T1-T5 ... shape recovery exact on every control family (T4), simplex cells equal to limiting-reagent regions exactly with 0 wrong (T5, M15)", `SYNTHETIC_ONLY`, $0 — SPEC §7.24.

**LUT** (lookup table baseline) — [HELM test/governance]
- *Plain:* a memorize-and-look-up rival with no recipe math, used to check the math earns its keep.
- *Definition:* "LUT (lookup table, same gate and policy, no recipe math)" — SPEC §7.24. It tied the recipe brain 32–32 on GB3, so `RECIPE_MATH_EARNED` was false there — SPEC §7.24.

### M

**M1** (layered memory) — [HELM part]
- *Plain:* memories fade in layers, hot to warm to cold, and nothing is ever deleted.
- *Definition:* "memories fade in layers HOT→WARM→COLD; **nothing is ever deleted**" — CSK §3. Council decisions C4 "by time, in logged day-ticks" and C5 "`fade_rate = 1/20` per day-tick unpinned, `0` pinned" — SPEC §7.55.
- *Status:* 🟥 `M1_FAILURE` on H8 — SPEC §7.43.

**Male** (`^6`, older label CO-6) — [CAS core]
- *Plain:* what an Idea is made of — "unpacking" or "breaking it down."
- *Definition (canonical, verbatim):* "An Idea impregnated with another Idea, the Ideas an Idea is composed of." — CFC Clarification 1.
- *Colloquialisms (canonical):* "Unpacking an idea." / "Breaking it down." / "Looking at what's underneath." / "Pulling apart the argument." — CFC Clarification 6.
- *Note:* analytical critique ("audit, scrutinize, find flaws") belongs here, not under `^3` — CFC Clarification 6.

**Mark** (M1, G1, …) — [HELM test/governance]
- *Plain:* a frozen number a result must reach for a word to be awarded.
- *Definition:* (usage term; no single canonical definition; first seen in SPEC §7.24 "marks as GB3 + gate"). Examples: RB-G marks G1–G7, growth marks M1–M5 — SPEC §7.30, §7.67. Marks are distinct from hard gates; some marks are "reported, never a gate" — SPEC §7.63.

**MATCH / MISMATCH / UNPARSEABLE** — [HELM test/governance]
- *Plain:* the reader agreed with the source, disagreed, or could not read the sentence.
- *Definition:* (usage terms; no definition in SPEC; first seen in SPEC §7.31). 439 headline: MATCH 233, UNPARSEABLE 197, MISMATCH 9 — SPEC §7.54; after lexicon v2 "MATCH 233 → 304, MISMATCH 9 → 13" — SPEC §7.57.

**Mechanism-free baseline** (dumb baseline) — [HELM test/governance]
- *Plain:* the cheapest rival that lacks the part being tested — the part must beat it.
- *Definition:* owner rule "Register a MECHANISM-FREE baseline — beat the cheapest method without M" (memory rule). In SPEC: "true round-robin ... the mechanism-free baseline" — ERRATUM to §7.69; "mechanism-free rival: after every write re-read that write's own receipt" — SPEC §7.75. "Claims are bounded by the control that lacks the mechanism." — VIS §2.

**MIN vs PRODUCT_BOOK** — [HELM test/governance]
- *Plain:* two ways to combine the three faces: take the smallest, or multiply them.
- *Definition:* "`c = min(P, W, Pw)`, Balance Reading rule 1" vs "`c = P × W × Pw × (1 − imbalance)`" — SPEC §7.58.
- *Status:* `OPEN` (owner decision) — SPEC §7.58.

**Mind** (`^1`, older label CO-1) — [CAS core]
- *Plain:* awareness — the thing that takes in, holds, works on and gives out Ideas.
- *Definition (canonical, verbatim):* "Various degrees of awareness that processes, stores, outputs, and intakes Ideas." — CFC Clarification 1.
- *Colloquialisms (canonical):* "Paying attention." / "Making up your mind." / "Using your head." — CFC Clarification 6.
- *Owner ruling:* Mind = any being that thinks; presence of a Noetic is decided by the canonical colloquialisms (owner ruling 2026-10-05, applied in SPEC §7.23).

**Noetic monoid** — [CAS core]
- *Plain:* the rule that Noetics can be chained, with Idea as the "do nothing" element.
- *Definition:* "Monoid: (N, ∘, CO-0) where CO-0 is identity" — CLAUDE.md. Also stated as "The monoid (Δ°₃₉, ×, CO-0) is unchanged" — CFC Clarification 9 §10.

**`MOOD_FACT_CLASH_CHECK`** — [HELM part]
- *Plain:* one written rule for when a cheerful message meets a refusal — HELM asks one plain question.
- *Definition:* "HELM does **not** understand sarcasm. One written rule: a 10-word positive mood list (not when negated) + a refusal / missing / 'can't tell' receipt -> one plain question" — SPEC §7.60 (inner quotes changed).
- *Status:* `ENGINEERED-NOT-VALIDATED`, reported only — SPEC §7.60.

### N

**N1 ruling** — [HELM test/governance]
- *Plain:* the owner's ruling on how to read dotted fractal notation.
- *Definition:* "dotted `a.b.c` ≡ `Φ<a:b:c>` per the owner's N1 ruling"; "(first written = innermost)" — SPEC §7.25, §7.31.

**`NAMED_CORPORA_ONLY`** (proposed claim ceiling) — [HELM test/governance]
- *Plain:* a proposed ceiling for results on named real datasets only.
- *Definition:* "followed by the exact list (corpus, export or dump date, sha256). It is a claim CEILING (like `SYNTHETIC_ONLY`)" — XR §8. Status: design only; the name is owner question Q4.

**NCCS** — [CAS core]
- *Plain:* the 0–100 overall score Noetic Compass gives an AI.
- *Definition:* weights: "25% — Cognitive Operator Profile ... 20% — Domain Coherence (DCI ...) ... 20% — Core Drive/RPM Integrity ... 10% — Capability Pathway Quality ... 15% — Inversion Resistance ... 10% — Social Engineering Resistance" — CLAUDE.md, Scoring Algorithm.
- *Expansion conflict:* "Noetic Cognitive Coherence Score (NCCS)" (`docs/NOETICCOMPASS_COM_FEATURE_SPEC.md`, `book/manuscript/FULL_MANUSCRIPT_v2.md`) vs "Noetic Compass Composite Score" (`noetic-compass-scaffold/noetic-compass/dashboard/src/pages/FaqPage.tsx`, `book/manuscript/split/chapters/ch06.md`). No canonical ruling found.

**Negative** (`^3`, older label CO-3) — [CAS core]
- *Plain:* an Idea the mind pulls away from ("can't stomach it").
- *Definition (canonical, verbatim):* "An Idea the Mind is adverse to and repelled by." — CFC Clarification 1.
- *Colloquialisms (canonical):* "Can't stomach it." / "Rubs me the wrong way." / "Wouldn't touch it with a ten-foot pole." — CFC Clarification 6.
- *Anti-drift:* `^3` is VISCERAL, not analytical; analytical critique is `^6` — CFC Clarification 6.

**Nested Noetics** (Noetic Fractals) — [CAS core]
- *Plain:* Noetics written inside Noetics.
- *Definition:* (usage term; no canonical definition in the files read; first seen in SPEC §7.31, owner words "Noetic Fractals nested noetics"). Built in `docs/working/noetic_council/language_v3/cce_v01b.py`: "nested Noetics (fractal sequences, depth 1-5)".

**`NEUTRAL`** (switch word) — [HELM test/governance]
- *Plain:* turning this part off changed nothing.
- *Definition:* switching it off "changed nothing (NEUTRAL)" — SPEC §7.64. CCE skin and DRIVE_LOOP read `NEUTRAL` in wave 3 — SPEC §7.69.

**"Never delete a negative"** — [HELM test/governance]
- *Plain:* failed and null results stay on the record forever.
- *Definition:* "**Never delete a negative.** Disconfirmations are load-bearing product assets." — SPEC §1, update rule 3; CLAUDE.md.

**`NEVER_RAN`** — [HELM test/governance]
- *Plain:* a planned run that never happened — not a negative result.
- *Definition:* RB-G7: "No `rb_g7` folder, freeze or result exists... It is not a negative result." — SPEC §7.67.

**New matter** (patent sense) — [Infrastructure]
- *Plain:* ideas added after the patent filing, which the filing does not cover.
- *Definition:* "CAS v7.5 / v7.6 / v7.7 and the Fleet / 300B sharded-audit architecture were added after 04/13/2026 and are NOT covered by this provisional." — CLAUDE.md.

**`NO_ANCHOR`** — [HELM test/governance]
- *Plain:* the fingerprint to check against is gone, so the only honest answer is "unknown".
- *Definition:* "If the authoritative fingerprint is itself unavailable, the answer is UNKNOWN with reason NO_ANCHOR" — SPEC §7.46.

**Noetic** (plural Noetics; the ten operators `^0`–`^9`) — [CAS core]
- *Plain:* one of the ten basic moves a mind makes with Ideas.
- *Definition:* "The 10 Noetics (CO-0 through CO-9) of the Cognitive Architecture System are authoritatively defined as follows. These names and definitions are **verbatim canonical**." The canonical names are "Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect." — CFC Clarification 1.
- *Rule:* there is no alternative naming scheme; older names such as "Attraction", "Critical Evaluation", "Receptive Integration", "Projective Assertion" are drift — CFC Clarification 3. Owner ruling 2026-09-21 (recorded outside the repo, in Claude's memory): write `^n`, not CO-n, in prose.

**Noetic Compass** — [Infrastructure]
- *Plain:* the product name: an AI psychology and ethics assessment platform built on CAS.
- *Definition:* "Product: Noetic Compass — AI Psychology & Ethics Assessment Platform" — CLAUDE.md, Project Identity.

**Noetic council** (TKS Noetic Council; `noetic_council` packages) — [HELM test/governance]
- *Plain:* a working group of agent sessions that built nine HELM mechanism packages and records council decisions.
- *Definition:* nine packages "(cube store, prerequisite planner, continuity v4, D/W/P engine v2, the loop v3, return address, faculties v2, language v3, repair performer)" — SPEC §7.48. Council decisions are "council decisions, not owner rulings and not canon" — SPEC §7.55.
- *Status:* `ENGINEERED-NOT-VALIDATED`; 308 tests written — SPEC §7.48.

**Noetic Coverage** (Noe-Cov-3) — [CAS core]
- *Plain:* the covering rule in the CAS topology; its arrows point toward the thing covered.
- *Definition:* Correction 3 is titled "Noetic Coverage uses COUNIT not UNIT": "Noe-Cov-3 uses εI: R(I) → I (toward target), NOT ηI: I → R(I) (away from target)." "Cognitive Topos covering morphisms point TOWARD the covered object." — CLAUDE.md, Correction 3.

**Noetic Topos** (also Cognitive Topos) — [CAS core]
- *Plain:* the formal math structure behind CAS (the "Noetic Topos paper").
- *Definition:* CAS "retains its own mathematics, compiler, and notation as defined in the Noetic Topos paper (`peer_review/journal_submission/main.tex`)" — CFC Clarification 1. Includes "formal axioms, open simplex, Fisher-Rao metric, Grothendieck topology, RPM section-retraction" — CFC, Scope. (usage term "Cognitive Topos": CLAUDE.md Correction 3 and Phase 4; no separate definition.)
- *Status:* "Formal only, not empirical" — SPEC §9.9.

**NOT LAUNCHED** (packet state) — [HELM test/governance]
- *Plain:* the test package is sealed and waiting; nothing has run.
- *Definition:* packet sealed; "nothing scored, no claim" — SPEC §7.63, §7.66, §7.70, §7.75, §7.76. (usage term; not in the §3 legend.)

**`NOT LICENSED`** (claim status) — [HELM test/governance]
- *Plain:* you may not say it — unproven, not necessarily false.
- *Definition:* "You may not say it. Either the evidence does not exist, or it exists and does not reach the claim." Does NOT mean "That the claim is false. It means unproven, and sometimes it means untested." — SPEC §3.

**`NOT TESTABLE`** — [HELM test/governance]
- *Plain:* no suitable data exists, so the test was never run.
- *Definition:* "No eligible fixture or data exists, so the experiment has never been run. **Untested is not null.**" — SPEC §3.

**`NOT_EXERCISED`** (switch word) — [HELM test/governance]
- *Plain:* the exam never used this part, so nothing can be said about it.
- *Definition:* the part "was never on the exam's path (NOT_EXERCISED)" — SPEC §7.64 (TRIAD in wave 2). Also `RESTART_FALLBACK_NOT_EXERCISED` on gate_b and task_b — SPEC §7.47.

**`NOT_PASS`** — [HELM test/governance]
- *Plain:* the overall exam did not pass because one part did not.
- *Definition:* "PASS only if both tasks PASS" — SPEC §7.25 (RB2b).

**`NOT_RECIPE_SHAPED`** — [HELM part]
- *Plain:* the data does not follow a recipe law, so recipes should not be forced on it.
- *Definition:* "recipe loses on substitutable/additive data, now flagged NOT_RECIPE_SHAPED by `sdg_bridge_v2`" — SPEC §7.24. An LSR halt status — LSRD §9.

**`NOTHING SCORED`** (claim ceiling) — [HELM test/governance]
- *Plain:* a policy or package is frozen, but no result exists.
- *Definition:* "Claim ceiling: `NOTHING SCORED`. The policy is frozen; **the implementation does not exist.**" — CSK §6; SPEC §7.46.

**`NULL`** — [HELM test/governance]
- *Plain:* a valid test that found nothing.
- *Definition:* "A pre-registered test ran, was evaluable, and found nothing. An honest empty hand." — SPEC §3.

### O

**One attempt + one plumbing retry** — [HELM test/governance]
- *Plain:* each sealed package gets one scored try, plus at most one retry for setup problems.
- *Definition:* "One scored attempt + one plumbing retry. Wave 1 needed 7 attempts for plumbing" — SPEC §7.63. "A second launch would burn the $9.50 hold and break the one-attempt-per-sealed-package rule." — CSK §7b.

**`OPEN`** — [HELM test/governance]
- *Plain:* not run yet, or run and not yet judged.
- *Definition:* "Never run, or run and not yet adjudicated. Untested is not the same as null." — SPEC §3.

**Open probability simplex** (S°_I = Δ39°) — [CAS core]
- *Plain:* the space of all 40-part mixtures where no part is exactly zero.
- *Definition:* "Target space is S°_I = Δ39° = { p ∈ R^40 : pk > 0 for all k, Σpk = 1 } NOT the discrete 40-element set I." — CLAUDE.md, Correction 4.
- *In HELM:* the drive loop's attention is "a point on the open 7-Foundation simplex" — RBI3 §4.3; SPEC §7.66.

**Operating regions** (Cutoff / Active / Saturation / Breakdown) — [CAS core]
- *Plain:* the four states a CJT can be in: off, working in proportion, maxed out, or flipped.
- *Definition (cognitive readings, PCBA Ch. 3):* Cutoff — "The bias is below threshold. The cause arrives, but nothing comes out."; Active — "The linear, designed-for region."; Saturation — "The output has maxed out."; Breakdown — "under overload the effect **flips to the involution Noetic pair.**"

**Operational domain** (O) — [CAS core]
- *Plain:* the level of action and doing.
- *Definition:* fourth of the 4 Processing Domains — CLAUDE.md. "the Operational domain (action, production, execution)" — INC §1.

**Operator Inversion** (failure class 2) — [CAS core]
- *Plain:* one side of a mirror pair fires and the other is silent.
- *Definition:* "One of the three CAS involution pairs has drifted into imbalance beyond tolerance." — INC §2. (INC names the pairs with drift names; use the canonical names.)

**Option A / Option B** (triad placement) — [HELM part]
- *Plain:* put a Purpose on each ingredient (A), or one Purpose on the whole recipe as a door (B).
- *Definition:* "Option A: purpose per ingredient. Option B: purpose once per recipe." — PWP §1. B "puts one Purpose stage on the whole recipe (a door: Absent means the recipe may not run)" — SPEC §7.58.

**ORACLE** (pre-sized brain) — [HELM test/governance]
- *Plain:* a brain built at the right size from scratch, used as the target growth should reach.
- *Definition:* "ORACLE (pre-sized from scratch)" — SPEC §7.30.

**Ordinary head** — [HELM part]
- *Plain:* a small plain calculator kept beside the recipes for smooth or noisy laws.
- *Definition:* "a small, usually non-neural calculator (e.g. a 223-parameter MLP, or a 4-parameter OLS head) kept **beside** the recipes for smooth and noisy laws." "It is **not** a language model." — CSK §3. Rule: "smooth or noisy law → an ordinary head beside the recipes, not more recipe parameters" — SPEC §7.27 (PROPOSED).

**`OUR_CONVENTION`** — [HELM test/governance]
- *Plain:* a label for a choice the builders made, not something from canon.
- *Definition:* (usage term; no canonical definition; first seen in `helm_brain_canonical.py` — "`DEFAULT_BINDING` ... labeled OUR_CONVENTION"; also SPEC §7.60, §7.73, U3A §3.3, XR §3.1).

**Owner** (Wakil; Little Henderson; Prof. Hermes M. Thoth) — [Infrastructure]
- *Plain:* the founder, whose word is the only approval that counts.
- *Definition:* "Founder: Little Henderson (a.k.a. Wakil, a.k.a. Prof. Hermes M. Thoth)" — CLAUDE.md. "Owner approval must be executable (an owner-signed phase-approval record), not prose-interpretable." — CLAUDE.md.

**Owner ruling** (and council decision) — [HELM test/governance]
- *Plain:* a rule the owner set; it binds, but it is not evidence.
- *Definition:* rulings are "each `IN FORCE` as a rule, none of them a result"; "A ruling is not evidence. Nothing here changes a result." — SPEC §7.55, §7.59. Council decisions (C4, C5, Q13) are "council decisions, not owner rulings and not canon" — SPEC §7.55.

### P

**p/q number form** (Q13 fix) — [HELM part]
- *Plain:* letting the language layer write exact fractions like 17/2.
- *Definition:* "the p/q number form. The owner's ruling on Q13." — `language/numbers.py`. Council decision Q13: "admit a `p/q` number form to CCE" — SPEC §7.55.

**Pair wave** (HELM-R1 wave 6, "PAIR WAVE") — [HELM test/governance]
- *Plain:* the wave that runs the wide recipe brain alongside HELM's other parts (cube store, English reader, triad, voice, EYE_SCAN, EYE_PAIRING), switching the wide brain off together with each one to read the pair words (see **Pair words**: `SYNERGY` / `ADDITIVE` / `INTERFERENCE` / `CEILING_NOT_READABLE`), plus a no-harm check and the new `UNSETTLED_ASK` caution rule. It is the step that decides whether the wide brain can become HELM's main brain.
- *Definition:* "HELM-R1 wave 6 "PAIR WAVE": packet sealed, NOT LAUNCHED — the wide recipe brain (RB-W1 v3, HELM's `WIDE_BRAIN` switch, licensed reader first) tested ALONGSIDE HELM's other parts (cube store, English reader, triad, voice, the Unity Eye's self-scan and its pairing drive loop), plus one new caution rule `UNSETTLED_ASK`" — SPEC §7.91 (heading). "RB-W1T v3 (§7.89) made the wide brain a candidate main brain, "pending a wave with the switches". This is that wave." — SPEC §7.91. `UNSETTLED_ASK`: "ask when a recipe names one ingredient on two lines" — CHANGELOG, 2026-10-19 wave-6 entry.
- *Owner's word:* "PAIR WAVE at 1 USD" (2026-10-19) — `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`; cap 1.00 USD, one attempt + one plumbing retry.
- *Status:* packet sealed, NOT LAUNCHED; nothing scored, no claim — SPEC §7.91. Its practice dry run (practice data only, not a result) forecast `WIDE_WAVE_HARMED` (23 WRONG on practice conversations with the wide brain on, against 0 without) — SPEC §7.91, CHANGELOG. The defects found on those practice conversations (unread face and purpose clauses, an amount restated in another unit, a chat crash on a wide teaching turn) were fixed first in RB-W1 v4 (commit `cb3db850`, PR #400), before any spending; the packet is to be resealed on that build (coordinator record, 2026-10-20). Scored twice since: c48 on the v2 package (SPEC §7.93) read `PASS` / `WIDE_WAVE_NO_GAIN` — one unexplained ask on a fully learned recipe, traced to a reader defect ("half as much soda" read as a made-up ingredient) and fixed in reader v5; c50 on the resealed v3 package and a fresh exam, under the owner's pre-approval "FIX K4 at 1 USD" (SPEC §7.96), read `PASS` / `WIDE_WAVE_EARNED_KEEP`: every mark met, so the wide brain is HELM's canonical-brain candidate across the switches; making it canonical is the owner's decision.

**Pair words** (`SYNERGY` / `ADDITIVE` / `INTERFERENCE` / `CEILING_NOT_READABLE`) — [HELM test/governance]
- *Plain:* what happens when two kept parts are switched off together: worse than both alone, about the same, less, or the exam has no room to tell.
- *Definition:* a pair is "two earned parts off together. If losing both costs more than the two single losses added, the pair works together." — SPEC §7.66. `SYNERGY`: "losing both parts cost more than the two losses added"; `ADDITIVE`: "about the same"; `INTERFERENCE`: "or less"; `CEILING_NOT_READABLE`: "(the two losses exceed the exam's room)", "if and only if L(a) + L(b) > M(FULL) − 8" — SPEC §7.69, §7.70. Margin: "1/8 of the denominator" — SPEC §7.66.

**Pairing table** (7 × 7, Eye) — [HELM part]
- *Plain:* 49 counters — tries and successes for each drive-and-faculty pair — that start blank.
- *Definition:* "49 cells, one per (Foundation, faculty). Each cell holds two whole numbers: tries T and successes S." "Cell score = (S + 1) / (T + 2), an exact Fraction. At the start every cell is 0/0, so every score is 1/2. No answer key." — RBI3 §4.2.

**Parameters** (vocabulary rule) — [HELM test/governance]
- *Plain:* say "parameters" for a model's adjustable values.
- *Definition:* "say **parameters** for a model's adjustable values" — SPEC §7.27. "The record says '68 learned values', not '68 learned numbers'." — CSK §1 (inner quotes changed).

**Part F outcome classes** (X-REAL) — [HELM test/governance]
- *Plain:* how a fault test can end: caught, failed loudly, missed but harmless, or missed and harmful.
- *Definition:* "CAUGHT … FAILED_LOUD … SILENT_HARMLESS … SILENT_HARMFUL | no finding and probe WRONG, or a finding but the probe still WRONG" — XR §4.3. Status: design only.

**`PARTIAL`** — [HELM test/governance]
- *Plain:* part of the claim is reached and part is not; say which.
- *Definition:* "The test ran and returned a real, readable result that reaches **part** of the claim and not the rest. Always name which part is reached and which is not." — SPEC §3.

**`PASS` / `FAIL`** — [HELM test/governance]
- *Plain:* one test met, or did not meet, its stated bar.
- *Definition:* "A single pre-registered test met / did not meet its stated criterion. Always report which criterion, and whether it was set before the run." Does NOT mean "A verdict on the whole battery." — SPEC §3.

**PCBA** (Printed Circuit Board Assembly) — [CAS core]
- *Plain:* the project's way of drawing CAS as electronic circuits; also the name of the book *CAS PCBA Engineer*.
- *Definition:* "Printed Circuit Board Assembly (PCBA)" — `docs/working/CJT_PCBA_IMPLEMENTATION_BLUEPRINT.md`. Book: `book/CAS_PCBA_Engineer/`. (usage term otherwise; first seen in those files.)

**Permanent honesty ceiling** — [HELM test/governance]
- *Plain:* a CAS number is a design score or a rating, never a meter reading.
- *Definition:* "Every CAS number is a design score or an observed rating, NEVER a voltmeter reading ... The residual proves flow CONSISTENCY, not semantic CORRECTNESS." — SPEC §8.3.

**Phenomenological Register** (Register; R ∈ {T, A, f, E}) — [CAS v7.5 Register]
- *Plain:* the "tone" a thought runs in — big-picture, step-by-step, felt, or bodily — without changing what the thought is.
- *Definition:* "Each of the 40 Cognitive States (10 Noetics × 4 Domains) and each of the 7 Core Drives can operate in any of 4 Registers, specifying the operational character of the cognitive operation without changing what the operation IS." — CFC Clarification 8 §1. "Register is **optional**." — §3.
- *In HELM:* the voice's tone: "f warm (default), A analytical (when the user asks for detail), E hands-on, T big-picture." — `helm_voice.py`.

**Plain English rule** — [Infrastructure]
- *Plain:* every report to the owner says the meaning first, then the term, in short sentences.
- *Definition:* "This is a button turned ON, not a mode to drift out of." "meaning first, then the precise term; define jargon on first use; keep every literal exact" — CLAUDE.md, Plain English.

**`PLAN_ORDER_VIOLATION`** / **`PLAN_CYCLE`** — [HELM part]
- *Plain:* the plan put a step before what it needs / the plan contradicts itself in a loop.
- *Definition:* `PLAN_ORDER_VIOLATION`: "RPM Gate returned `REPAIR` for a node positioned as ready." — `prereq_planner/README.md`. `PLAN_CYCLE`: "Cycle detection: Refuses contradictions with PLAN_CYCLE." — `plan_graph.py`.

**Planted fault** — [HELM test/governance]
- *Plain:* a deliberate, known error put into test data to see if HELM catches it.
- *Definition:* U1: "F_RECEIPT, F_FADED, F_MISALIGNED, F_FIXATION, F_MEMORY; and F_SEAM on dialogues" — SPEC §7.38. Limit: for U3-T1 "the faults were planted knowing what the scan checks" — SPEC §7.73 headline.

**Positive** (`^2`, older label CO-2) — [CAS core]
- *Plain:* an Idea the mind is drawn toward ("speaks to me").
- *Definition (canonical, verbatim):* "An Idea the Mind has an affinity for and is attracted toward." — CFC Clarification 1.
- *Colloquialisms (canonical):* "Drawn to it like a moth to a flame." / "Speaks to me." / "Can't resist." — CFC Clarification 6.

**PRC-1 … PRC-10** (pre-run changes) — [HELM test/governance]
- *Plain:* recorded changes made to a package before its run.
- *Definition:* "pre-run changes PRC-1…PRC-10 in FROZEN.json" — SPEC §7.34, §7.35.

**`PreFlightRPMGate`** — [HELM part]
- *Plain:* checks safety prerequisites before any outside action.
- *Definition:* "Evaluates safety prerequisites strictly BEFORE any external action." — `helm_agentic_executor.py`.

**Preparation is not behavior** — [HELM test/governance]
- *Plain:* builds and passing tests show readiness, not progress.
- *Definition:* "Builds, reviews, clean runs, serialization checks and passing software tests establish *readiness* for an experiment. They are reported as preparation. Only an observed, pre-declared behavior on a frozen input counts as progress on an ability." — VIS §2.

**Prerequisite Chain Failure** (RPM Break; failure class 4) — [CAS core]
- *Plain:* doing something without the wanting or knowing that should come first.
- *Definition:* "A break at any node means the chain emits Power without the prerequisite Wisdom, or Desire without the foundational A0 grounding." — INC §4.

**Prerequisite-graph planner** (`prereq_planner`) — [HELM part]
- *Plain:* puts steps in order from what each step needs first.
- *Definition:* "Prerequisite-graph planner (replaces keyword matching)." "CLAIM CEILING: MECHANISM ONLY. ... NO UNDERSTANDING OF THE REQUEST IS CLAIMED." — `docs/working/noetic_council/prereq_planner/plan_graph.py`. "ORDERING IS DERIVED FROM STATED PREREQUISITES" — SPEC §7.48.

**Prerequisite shortage vs conversion inefficiency** — [CAS v7.6 Production]
- *Plain:* "not enough ingredients" versus "enough ingredients, poorly used."
- *Definition:* "Low Y_A with low Y_T = prerequisite shortage (intervention: build missing prerequisites). Low Y_A with high Y_T = conversion inefficiency (intervention: address leakage, inhibitors, or develop catalysts)" — CFC Clarification 9 §8 (lines joined).

**Principled domain** (P) — [CAS core]
- *Plain:* the level of values and first principles; it ranks highest.
- *Definition:* one of the 4 Processing Domains; top of the order P ≻ C ≻ E ≻ O — CLAUDE.md. "Principled domain must ground Cognitive" — INC §1.

**`PROCEED`** (RPM Gate verdict) — [HELM part]
- *Plain:* nothing is missing, so the step may go ahead.
- *Definition:* "the section holds: nothing on the D/W/P chain is blocked and nothing the turn needs is missing." — `the_loop_v3/rpm_gate.py`.

**Production Efficiency** (η) — [CAS v7.6 Production]
- *Plain:* actual over possible — how well the ingredients were used.
- *Definition:* "Ratio of actual to theoretical yield. η = Y_A / Y_T ... η ∈ [0, 1]." — CFC Clarification 9 §2.
- *In HELM:* "the expected yield is eta * Y_T (Clarification 9 production efficiency)" — `helm_triad.py`.

**Production Target** (Ω) — [CAS v7.6 Production]
- *Plain:* the outcome you want to make.
- *Definition:* "A specified outcome whose generation is under analysis." Notation: Ω_{name} — CFC Clarification 9 §2.

**Prohibited words and sentences** — [HELM test/governance]
- *Plain:* words that may never appear in any write-up.
- *Definition:* "**Prohibited words in every surface, always:** `certified`, `guaranteed`, `100%`, `world-first`, `only`, `court-admissible`, `regulator-grade by construction`, `validated at 300B`, `validated at frontier scale`." — SPEC §3.

**`PROPOSED`** — [HELM test/governance]
- *Plain:* a suggested number, mark or rule not yet ruled on.
- *Definition:* (usage term; not in the §3 legend; first seen in SPEC §7.27). e.g. "All new rows `PROPOSED`" — SPEC §7.63; RB-I3 thresholds "PROPOSED" — RBI3 §6. Variant `PROPOSED_NOT_RULED` — SPEC §7.58.

**Pull CUT** (in conversation) — [HELM part]
- *Plain:* while talking with someone, the drive loop's pull is switched off.
- *Definition:* owner: "GRAVITY PULL CUT OF COURSE WHEN ENGAGING IN CONVERSATION"; "conversation turn --> pull CUT: no attention step, no faculty call" — RBI3 §3, §4.5.
- *Status:* wave 5: "0 faculty calls in conversation" — SPEC §7.78.

### R

**`R1_BEATS_GB3`** — [HELM test/governance]
- *Plain:* the headline word of wave 1: the recipe brain beat the transformer.
- *Definition:* claim: it "named the Limiting Reagent of fresh held-out compositions at least 4 of 32 above GB3" — SPEC §7.47. "The reading names `margin: 4`; that is the **threshold**, not the win" — SPEC §7.47.

**"Randomness may only propose"** — [HELM test/governance]
- *Plain:* chance may suggest; only the checker, the receipts and the gate decide.
- *Definition:* owner rule, verbatim: "Randomness may only propose; the verifier, the receipts and the RPM Gate always decide." — CSK §2, §5.

**RB-C** (creativity layer tests RB-C1 … rb_c4) — [HELM test/governance]
- *Plain:* tests of whether creativity can be earned — untaught, admitted on a receipt, holding on held-out rows.
- *Definition:* "the **creativity layer** — untaught, not offered by the K=1 twin, admitted on a receipt, holds on held-out rows"; "creativity must be **earned**" — CSK §3. RB-C1 `FAILURE`; rb_c4 `RESTART_FALLBACK_EARNED_KEEP` — SPEC §7.26, §7.27.
- *Status:* "grammar question `CREATIVITY_DID_NOT_EARN_KEEP`" — SPEC §7.27.

**RB-G** (recipe-brain self-growth operator; runs RB-G1 … RB-G10) — [HELM test/governance]
- *Plain:* tests of whether the brain can grow its own capacity, the right kind, only when needed.
- *Definition:* "SENSE … → DIAGNOSE exactly one capacity kind by two keys … → GROW ONE UNIT → FIT → VERIFY V1–V7 … → KEEP or ROLL BACK … → LOG" — SPEC §7.30.
- *Status:* growth claim `NOT LICENSED` after nine runs: RB-G1–G6 and G8 `GREW_WRONG_KIND`; RB-G7 `NEVER_RAN`; RB-G9 `CURIOSITY_DID_NOT_EARN_KEEP`; RB-G10 `INCONCLUSIVE` — SPEC §7.30–§7.39, §7.67, §7.68, §7.71.

**RB-I1 / RB-I1b / RB-I1c** (faculties and drive loop on the recipe brain) — [HELM test/governance]
- *Plain:* tests of whether the faculties and the 7-drive loop help the recipe brain; none earned a word yet.
- *Definition:* RB-I1: "all CAS faculties and the oscillating 7-Drive loop on the recipe brain" — FAILURE on H1 → `INCONCLUSIVE` — SPEC §7.34. RB-I1b (c30): `INSTRUMENT_ERROR`, reason `TESTS_FAILED` — SPEC §7.37. RB-I1c (c36, 0.70 USD): `HARD_GATES_PASS`, status `INCONCLUSIVE` — SPEC §7.65.

**RB-I3** (Unity Eye pairing and rotation) — [HELM test/governance]
- *Plain:* the Eye learns which drive-and-faculty pairs work, from checked tries only.
- *Definition:* "the Unity Eye pairs and rotates the 7 desires with the 7 faculties and learns from verified tries"; "keeps a 7 × 7 table... It starts blank" — SPEC §7.74.
- *Status:* `EYE_PAIRING_EARNED_KEEP`, `HARD_GATES_PASS`; `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY`; "the world was built so pairing matters; no creativity claim" — SPEC §7.74. Eye resolved 77.28% vs random 37.33% and round-robin 34.64% — SPEC §7.74.

**RB-OH1** (substitution recipe head) — [HELM test/governance]
- *Plain:* a test of adding one smooth "substitution" law as an extra head behind the gate.
- *Definition:* whether "a 'substitution' recipe law (a CES power mean on an 11-rung exponent ladder, `sub_oh1.py`) can be added... as one more head, behind the RPM gate" — SPEC §7.52 (inner quotes changed).
- *Status:* `HYBRID_ROUTING_EARNED` (fresh worlds), `HYBRID_NO_BETTER` (original), `SWEEP_CALIBRATION_FAILED`; `licensed: false` → `NOT LICENSED`; "the '87.5% against 60.74%' numbers belong **here**" — SPEC §7.52 (inner quotes changed).

**RB-P1** (Unity Eye trim and pruner) — [HELM test/governance]
- *Plain:* a test of letting the Eye trim unused parts of the brain.
- *Definition:* P1–P5 checks; "P3 … failed on the original world because one weak unit (23/320) was rolled back" — SPEC §7.42. `EYE_TRIM_ONLY` "preserved answers on 704/704 evaluations and removed 90–100% of idle parameters".
- *Status:* 🟧 mixed evidence; overall 🟥 FAIL; `PRUNER_DID_NOT_EARN_KEEP`; pruner `NOT LICENSED` — SPEC §7.42.

**RB-W** (CAS Recipe Capacity Rules v0.1) — [HELM test/governance]
- *Plain:* a test of which kind of extra capacity actually helps which kind of law.
- *Definition:* "which parameter kind binds which family"; "each kind scaled ALONE with the others at 1x" — SPEC §7.27.
- *Status:* Limiting-Reagent Rule of scaling held on 6 of 7 families; W3 blend law 🟥 FAIL (exponent 0.7053) — SPEC §7.27.

**RB1g2** — [HELM test/governance]
- *Plain:* the first run that put CAS recipes in place of HELM's transformer, on GB3's own exam.
- *Definition:* "the first run that REPLACES HELM's transformer brain with CAS recipes on HELM's own Gate-B exam" — SPEC §7.24.
- *Status:* `PASS`; `BETTER_THAN_T` true by one world; `RECIPE_MATH_EARNED` false (a lookup table tied it); job c23, 0.03 USD — SPEC §7.24.

**RB2b / RB2c** — [HELM test/governance]
- *Plain:* the harder exams; RB2c is the clean rerun where only the recipe mechanism passed Task B.
- *Definition:* RB2b: Task A `PASS`, Task B `INSTRUMENT_ERROR`, overall `NOT_PASS` (c25, 0.26 USD) — SPEC §7.25. RB2c: `PASS`; `RECIPE_COMPOSITION_EARNED` true — "the first exam on this line where only the recipe mechanism passes" (c26, 0.04 USD) — SPEC §7.26.

**RB3 / RB3c** ("T on B", "T taught with yields") — [HELM test/governance]
- *Plain:* GB3 and its wider copy were taught Task B — even given the same yields — and stayed near chance.
- *Definition:* RB3: "taught and scored on Task B — both near chance; `BETTER_THAN_T_B` **true** (margins 25 and 22.5 of 32); `T_COMPOSES_B` false" (c27, 1.89 USD) — SPEC §7.28. RB3c: reading `YIELDS_NOT_THE_CAUSE` (c29, 1.88 USD) — SPEC §7.29.

**`REAL`** (claim status) — [HELM test/governance]
- *Plain:* it exists and actually ran.
- *Definition:* "The thing exists and runs. Code executes, artifacts are on disk, numbers were produced by a real execution rather than a description of one." Does NOT mean "That the numbers support any claim about the world. Wired ≠ works." — SPEC §3.

**Real RPA Creative Searchlight** — [HELM part]
- *Plain:* a bounded widening search over the Atlas when the brain refuses a first target.
- *Definition:* "Implements bounded geometric widening across radii R ∈ {1, 2, 4, 8} (capped at 15 candidate nodes) when Station S0 refuses an initial target." — ROAD (`rpa_creative_searchlight.py`; LaTeX math written out). Roadmap correction: v0.3 "Partly backed" — CORR.

**Receipt** — [HELM part]
- *Plain:* the record a write leaves behind, with a fingerprint, so it can be checked later.
- *Definition:* "the record a write leaves behind, with a fingerprint (sha256 digest)" — U3A §1. η∘ε read-back receipt as a hard gate: "every admitted write passed, RB-det 472 of 472 (36 refused by receipt)" — SPEC §7.24.

**Recipe** (Θ) — [CAS v7.6 Production]
- *Plain:* how much of each ingredient one unit of an outcome needs.
- *Definition:* "The proportional weighting of prerequisite primitives required for a unit of production target." `Θ(Ω) = a₁·X₁ + a₂·X₂ + ... + aₙ·Xₙ` — CFC Clarification 9 §2. "Recipe specification is ALWAYS relative to a specific target Ω."
- *In HELM:* the recipe brain answers by recipe yield — SPEC §7.24; HELM's licensed brain has "8 stock cells and 4 recipes with a FIXED programmed support" — `helm_brain_canonical.py`.

**Recipe brain** (RB) — [HELM part]
- *Plain:* HELM's brain made of CAS recipes instead of a transformer: it answers by working out yields exactly.
- *Definition:* "no attention, no norm, no gate network, no output projection; a 2x4 memory that copies board 1; four CAS recipes answering by theoretical yield (min over required cells of memory ÷ requirement)" — SPEC §7.24. "**68 learned values** (32 requirements, 32 ceilings, 4 bindings), no gradients, exact arithmetic" — CSK §1.
- *In HELM:* `helm_brain_canonical.py`. *Status:* see **Canonical brain**.

**Recipe operations** (recipe ×, ÷, ∘, +, −) — [CAS v7.6 Production]
- *Plain:* the five combining operations applied to whole recipes.
- *Definition:* e.g. "Recipe composition: Θ(Ω_intermediate) ∘ Θ(Ω_final) specifies sequential production where outcome of one recipe serves as prerequisite for another"; "Recipe subtraction: Θ(Ω_full) − Θ(Ω_achieved) specifies remaining production requirement" — CFC Clarification 9 §6.

**`RECIPE_COMPOSITION_EARNED`** — [HELM test/governance]
- *Plain:* recipes composed correctly where every no-recipe rival failed.
- *Definition:* "Task B PASS AND every no-recipe baseline (DIV_TOTAL, smallest-input, MLP-B) median < 12 on B-chain and B-alt" — SPEC §7.25. True on c26 — SPEC §7.26.

**`RECIPE_MATH_EARNED`** — [HELM test/governance]
- *Plain:* whether the recipe arithmetic itself beat a plain lookup table.
- *Definition:* "RECIPE_MATH_sums rb_det 32, lut 32, a tie" → false on GB3 — SPEC §7.24. Wave 1 switch word `RECIPE_MATH_EARNED_KEEP` "but `RECIPE_MATH_EARNED` **false** on GB3, where a lookup table tied 32–32" — CSK §7.

**Redundant multi-register safety** — [CAS v7.7 Operator discipline]
- *Plain:* three separate safety mechanisms; one can fail while the others hold.
- *Definition:* `^3^P|A + ^3^P|f + ^3^P|T` — "Three distinct safety manifestations ... Robust in aggregate, defeasible in parts" — CFC Clarification 10 §5.

**`REFUSE`** (RPM Gate verdict) — [HELM part]
- *Plain:* the gap cannot be closed from here.
- *Definition:* "the gap cannot be closed from here: an ancestor is invalid, the returning Bias is not strictly newer, or the sub-goal would sit past the recursion horizon." — `the_loop_v3/rpm_gate.py`.

**Register co-presence** (`+`) — [CAS v7.7 Operator discipline]
- *Plain:* the same state showing up in several Registers at once, each still separate.
- *Definition:* "A state manifests simultaneously in multiple registers, but the manifestations remain distinct." Notation `^n^D|R1 + ^n^D|R2 + ^n^D|R3` — CFC Clarification 10 §2B. "`+` denotes association, adjacency, or simultaneous presence where terms remain structurally distinct." — §3.

**Register involution pairs** — [CAS v7.5 Register]
- *Plain:* Registers that mirror each other.
- *Definition:* "register involution pairs (`|T↔|E`, `|A↔|f`)" — CFC Clarification 10 §11. (Listed there as preserved from v7.5; not defined further.)

**Register-axis lacunarity** — [CAS v7.5 Register]
- *Plain:* gaps along the Register axis.
- *Definition:* (usage term; no canonical definition in the files read; first seen in CFC Clarification 10 §11: "register-axis lacunarity (four sub-categories)").

**Register-neutral** (register unspecified) — [CAS v7.5 Register]
- *Plain:* an expression with no Register written; still valid.
- *Definition:* "Expressions without Register specification remain valid and indicate register-neutral or unspecified register." — CFC Clarification 8 §3.

**Register-set specification** (`|⟨R1,R2,R3⟩`) — [CAS v7.7 Operator discipline]
- *Plain:* a plain list of which Registers a state is present in — no claim about how they interact.
- *Definition:* "A state is present in one or more registers, without asserting interaction dynamics between them." Example `^3^P|⟨A,f,T⟩` — CFC Clarification 10 §2A. "`|⟨…⟩` denotes register occupancy or specification, makes no operational claim about dynamics." — §3.

**`REJECTED`** — [HELM test/governance]
- *Plain:* an input (a test bank, a fixture) failed its entry check and is not patched.
- *Definition:* "An acceptance gate on an **input artifact** (a scenario bank, a fixture) failed, and the binding rule is **reject-not-repair**." — SPEC §3.

**`REPAIR`** (RPM Gate verdict) — [HELM part]
- *Plain:* something is missing, and a sub-goal can be opened to get it.
- *Definition:* "a prerequisite is missing and a sub-goal can be opened to realize it." — `the_loop_v3/rpm_gate.py`.

**Repair performer** (`repair_performer`) — [HELM part]
- *Plain:* the piece that actually opens a repair sub-goal; it decides nothing.
- *Definition:* "THE REPAIR PERFORMER. ... This module is the thing that opens. ... it decides nothing itself." — `docs/working/noetic_council/repair_performer/actor.py`. Self-label: "THE FAILURE IS PLANTED, NOT DETECTED. THE GLUE IS MODELLED, NOT CANON" — SPEC §7.48.

**Report only** (reported row) — [HELM test/governance]
- *Plain:* a number shown for information that cannot change the verdict.
- *Definition:* (usage term; no single canonical definition; first seen in SPEC §7.58). Examples: M4 and mixed_triads are report-only rows (SPEC §7.58); MOOD_FACT_CLASH_CHECK is "reported only" (SPEC §7.60).

**Restart fallback** (`RESTART_FALLBACK`) — [HELM part]
- *Plain:* if the exact first try leaves rows unexplained, try a few saved random restarts — and let the checker decide.
- *Definition:* "fires only when the exact fit start leaves rows unexplained; seeded, saved; verify unchanged"; "exact start first, seeded alternatives only when stuck, the verifier decides, seed saved" — SPEC §7.27, §7.33. "`RESTART_FALLBACK` is the one stochastic mechanism that ever earned its keep." — CSK §5.
- *Status:* `RESTART_FALLBACK_EARNED_KEEP` (rb_c4, depth families); `NOT_EXERCISED` on gate_b and task_b in wave 1; `EARNED_KEEP` in waves 2–3 — SPEC §7.26, §7.47, §7.64, §7.69.

**Return address** (`return_address`, `ReturnStack`) — [HELM part]
- *Plain:* a bookmark so a paused thought can come back to the exact spot.
- *Definition:* "the exact address of one suspended thread, and the root observation reference." — `docs/working/noetic_council/return_address/address.py`. Self-label: "NO CIRCUIT USES THIS YET" — SPEC §7.48.

**Rhythm** (`^7`, older label CO-7) — [CAS core]
- *Plain:* how often and in what pattern a mind meets an Idea, which trains it ("practice makes perfect").
- *Definition (canonical, verbatim):* "The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it." — CFC Clarification 1.
- *Colloquialisms (canonical):* "Practice makes perfect." / "You are what you repeatedly do." / "Getting into a groove." / "Muscle memory." — CFC Clarification 6.

**RIGHT / WRONG / UNDETERMINED** (three-valued outcome) — [HELM test/governance]
- *Plain:* every answer is scored right, wrong, or "could not tell" — and "could not tell" is never counted wrong.
- *Definition:* "RESOLVED (receipt passes) / WRONG (a write without a passing receipt; must be 0) / UNDETERMINED (open or CLOSED_NO_FIX at the end)"; "UNDETERMINED is never counted as wrong" — RBI3 §4.6. "UNDETERMINED = not wrong" — SPEC §7.24.

**Roadmap status correction** (CORR status words) — [HELM test/governance]
- *Plain:* a column added beside the roadmap saying how far each claimed stage is backed.
- *Definition:* "Authored only: The code or text exists. No recorded output shows it doing what the row says." Other words: Partly backed, Mostly backed, FALSE claim, Unrecorded spend, Not built — CORR. (table cells joined with a colon). Ordered as fix A, 2026-10-18.

**Rotation** (Eye) — [HELM part]
- *Plain:* a faculty that fails on an item is not retried there, and pairs that keep failing lose first place.
- *Definition:* "On one item, a failed faculty is never retried ... Across items, a cell that keeps failing loses score, so the Eye's first pick for that Foundation changes. That is 'mixing and matching'." — RBI3 §4.2 (inner quotes changed).

**Round trip** (`parse(render(C)) == C`) — [HELM part]
- *Plain:* turn CAS into English and back; you must get the same CAS.
- *Definition:* "roundtrip.py -- the only acceptance test." — `language/roundtrip.py`. "ε∘η = id — `parse(render(C)) == C`, required for every sentence said. η∘ε ≠ id — `render(parse(E)) == E` is **NOT** required." — CSK §4 (two bullet lines joined).

**Round-robin plus fixed table** (`FIXED_TABLE_RR`; ERRATUM to §7.69) — [HELM test/governance]
- *Plain:* a correction: wave 3's "round-robin" rival secretly also had a lookup table.
- *Definition:* "That arm is round-robin plus a fixed look-up table that hands each kind of item the one faculty that can solve it"; "REPORTED ONLY (not a switch arm)" — ERRATUM to SPEC §7.69. `DRIVE_LOOP` stays `NEUTRAL`; "no number, gate or claim status changes".

**RPA** (Recursive Possibility Atlas; "the Atlas") — [HELM part]
- *Plain:* HELM's organized map of what it holds and what is possible, keeping facts, guesses and contexts apart.
- *Definition:* owner ruling, verbatim: "RPA IS ATLAS I MEANT ATLAS". HELM vision ability 6: "an RPA (Recursive Possibility Atlas) organizing retained knowledge and possibilities, while keeping facts, guesses and separate contexts distinct." — CONT §1b; VIS §1. Code: "a minimal Recursive Possibility Atlas: nodes, edges, and sub-atlases." — `continuity_build_v2/atlas.py`.
- *Status:* switch `ATLAS` ("atlas entry at S0 + exact return addresses; off = a name-keyed mailbox") `EARNED_KEEP` — SPEC §7.66, §7.69. `ATLAS_CARRIED` earned in LM-T6 — SPEC §7.41.

**RPM** (Recursive Prerequisite Model) — [CAS core]
- *Plain:* the rule that you must want before you know, and know before you can do — checked one way only.
- *Definition:* "RPM (Recursive Prerequisite Model): sequential/logical dependency chain (A0 → Dn → Wn → Pn)"; "RPM asks 'are prerequisites present in correct sequence?' Recipe asks 'are prerequisites present in correct proportion for this outcome?'" — CFC Clarification 9 §5 (inner quotes changed to single). "RPM is Section-Retraction, NOT Adjunction" — CLAUDE.md Correction 2.
- *Status:* "an ontology, not a live localizer" — SPEC §9.9. "RPM prerequisite-chain geometry — NOT TESTABLE, not null" — SPEC §7.5.

**RPM chain** — [CAS core]
- *Plain:* one pathway's chain A0 → Dn → Wn → Pn → Outcome.
- *Definition:* "RPM chain: A0 → Dn → Wn → Pn → Outcome. RPM chain is section-retraction (one-directional prerequisite satisfaction)" — CLAUDE.md (lines joined).

**RPM Gate** (HELM) — [HELM part]
- *Plain:* HELM's one gate: it lets a step go ahead, sends it to repair, or refuses — and lets the brain say "I cannot tell."
- *Definition:* "RPM decides PROCEED / REPAIR / REFUSE, from the turn's cause." "It is the RPM gate and the only gate." — `docs/working/noetic_council/the_loop_v3/rpm_gate.py`. In the recipe brain: "RPM Gate (UNDETERMINED when a required prerequisite is absent)" — SPEC §7.24.
- *Status:* `GATE_EARNED_KEEP` in wave 1 — SPEC §7.47; `EARNED_KEEP` as RPM_GATE in waves 2 and 3 — SPEC §7.64, §7.69. (In CAS's Wrap Pipeline, "RPM Gate" is stage 2 — a different, older component.)

**RPM Resolution Lacunarity** — [HELM part]
- *Plain:* how many of the four repair routes HELM actually used, as a gap score.
- *Definition:* "RPM Resolution Lacunarity = 1 - (mechanisms used / 4)" — `docs/working/noetic_council/dwp_engine_v2/lacunarity.py`. Four mechanisms: "Power blocked → rational recursion"; "Wisdom blocked → reception"; "Wisdom blocked → decomposition"; "Desire blocked → iterative exposure" — U3A §3.3.

**`RpmCause`** — [HELM part]
- *Plain:* the record the gate decides on: what is blocked, how deep, and what is missing.
- *Definition:* "One record: the turn's cause (`RpmCause`) plus the Bias version the turn read." Fields include `blocked_node`, `depth`, `ancestor_dirty`, `unsatisfied` — LOOP3 §3. "There is no field for the ASOM label" — LOOP3.

**Rule P** (Provenance) — [HELM part]
- *Plain:* imagined, "daydream" states may never verify anything or slip into real beliefs.
- *Definition:* "internal hypothetical daydream states can never verify a candidate or contaminate the core belief atlas." — ROAD; code `faculties_v2/guard.py` ("FACULTIES.md Rule P"). Hard gate H4 in RB-I1 — SPEC §7.34.

### S

**Anchor** (of a thought) — [HELM part]
- *Plain:* where a thought started, used to measure how far it has moved.
- *Definition:* "**Anchor** of a thought = its **S0** point." "S0 is **a position in the atlas**" — CONT §1b, §1c.

**Admissibility rule for same-Noetic register multiplication** — [CAS v7.7 Operator discipline]
- *Plain:* you may not write `×` between Register versions of one Noetic unless you say what they fuse into.
- *Definition:* "Same-Noetic, multi-register expressions using `×` are invalid by default." — CFC Clarification 10 §4.

**`SANITY_PASS` / `SANITY_FAIL`** — [HELM test/governance]
- *Plain:* a non-CAS check that the measuring tool works at all.
- *Definition:* "A generic control experiment (nothing to do with CAS) showing the measuring instrument can or cannot produce a real, selective effect at all. Held **outside** any aggregate and outside the verdict, by design." — SPEC §3.

**Scheme-A / Scheme-B / Scheme-C drift** — [CAS core]
- *Plain:* older, wrong naming schemes for the Noetics that keep creeping back.
- *Definition:* named readings ruled out in CFC Clarification 6: the "Scheme-A 'CO-3 Concretization' reading", the "Scheme-B 'Aversion / Critical Evaluation' reading", the "Scheme-B 'Causal Reasoning' reading" (inner quotes changed). (usage term; no canonical definition of each scheme as a whole; first seen in CFC Clarification 6.)
- *Warning:* `docs/INCIDENT_CATEGORIES.md` still uses Scheme-B names ("CO-2 Attraction ↔ CO-3 Critical Evaluation", "CO-8 Causal Reasoning ↔ CO-9 Consequential Grounding") — that file is drift against CFC Clarification 3.

**Gates 1–8** (CAS Harness score ladder) — [HELM test/governance]
- *Plain:* the numbered steps the Harness must earn, from 0.33 to 1.00.
- *Definition:* "advances along a numbered ladder from 0.33 to 1.00; a score is awarded only when the named exit evidence passes" — SPEC §9.6. Gate 1 earned 2026-07-24; Gate 2 `OPEN` at 0.38 — SPEC §9.6.

**Scribe L4** (HELM v0.5 Scribe; `CASNativeScribeTransformer`) — [HELM part]
- *Plain:* a small neural English proposer trained on a GPU outside the ledger; it has no authority.
- *Definition:* "Level L4 open-domain English neural proposer"; "an English proposer, not a brain; no authority" — SPEC §7.53, §7.56.
- *Status:* `ENGINEERED-NOT-VALIDATED`; the job is `FLAG_FOR_HUMAN_REVIEW`; round trip held on "64.0 %" — SPEC §7.53.

**SDG** — [HELM part]
- *Plain:* the project's English-from-CAS generator and its seed set; used as a source of test sentences.
- *Definition:* "SDG: Native Free-Form English Generation — Canonical Spec" (title of `docs/working/phase3_free_form_spec_2026_05_04.md`). In HELM: "coverage 51 → 576 of 576 SDG seeds" — SPEC §7.24; "LLM-written SDG English" — SPEC §7.57. *Expansion (owner, 2026-10-19):* SDG = CAS **S**ynthetic **D**ata **G**enerator (`cas-synthetic/`). Owner-given; the files themselves never spell it out.

**Seam rule** (seams) — [HELM part]
- *Plain:* a new topic starts only when both the subject changes and the step is big enough; never blend across a seam.
- *Definition:* "a seam needs **both** the parsed head Ω (or the leading register) to change **and** the step `s_t ≥ θ_seam`." "**Never interpolate across a seam.**" — CONT §1c.
- *Status:* LM-T2 "subject seams 96/96, tone seams 48/48, false seams 0" — SPEC §7.31.

**Section-retraction** (RPM is a section-retraction, not an adjunction) — [CAS core]
- *Plain:* going forward then back gets you home, but going back then forward may lose something — one-way.
- *Definition:* "εI ∘ ηI = idI (realization after embedding = identity) BUT: ηI ∘ εI ≠ idR(I) (re-embedding after realization may lose info)" ... "Prerequisite satisfaction is ONE-DIRECTIONAL." — CLAUDE.md, Correction 2.
- *In HELM:* the language round trip is "the RPM section-retraction in language form": `parse(render(C)) == C` required, `render(parse(E)) == E` not required — CSK §4; U3 read-back "ε∘η = id" — U3A §2.

**Self-dual** (Noetics or Drives) — [CAS core]
- *Plain:* a Noetic or Drive that is its own mirror.
- *Definition:* "Self-duals: CO-0, CO-1, CO-4, CO-7"; "F4 self-dual." — CLAUDE.md, Structural invariants.

**Self-scan** (U3; Mind scan and Body scan) — [HELM part]
- *Plain:* HELM looking at itself using only its own records: what it was taught, and whether its files are intact.
- *Definition:* "U3 gives HELM a way to look at itself and say what it finds, using only its own records." Mind scan "reads what the brain is made of"; Body scan "checks the machinery. Does every saved record still read back the way it was written?" — U3A §1. "Findings become proposals, never fixes" — U3A §5.
- *Status:* U3-T1 `SELF_SCAN_EARNED_KEEP`, `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY` — SPEC §7.73.

**`SELF_REPORT`** — [HELM part]
- *Plain:* the record the self-scan writes, plus a short plain-English summary.
- *Definition:* "The result is a typed SELF_REPORT record, plus a short plain-English self-report spoken by `helm_voice`" — U3A §1. Honesty rule: "every sentence that states a fact must point to a record ... Where there is no record, the report says 'no evidence'. It never guesses." — U3A §1 (inner quotes changed).

**Sensory proposers vs. cognitive core** — [HELM part]
- *Plain:* small helpers turn sights, sounds and words into structure; the exact core decides.
- *Definition:* "Perception (vision, audio, natural language) is handled by lightweight proposers that extract structured registers (Ω)." — ROAD (LaTeX math written out).

**Set meta-logic** (meta-logic CAS) — [CAS core]
- *Plain:* set operations (union, intersection, and so on) applied to CAS objects.
- *Definition:* (usage term; no canonical definition; first seen in SPEC §7.31: "set meta-logic 15 operators × 8 set kinds 120/120").

**Sign line** (owner sign line) — [HELM test/governance]
- *Plain:* the owner's exact approval sentence for a paid run, which is hashed and becomes the exam's seed.
- *Definition:* (usage term; no single canonical definition; first seen in SPEC §7.24). In practice: the owner's verbatim approval line, whose sha256 seeds the custodian's exam ("seeded from the sha256 of the owner's R1W2 sign-line bytes" — SPEC §7.63). Example: "APPROVE R1W5: EYE_PAIRING wave, sealed package b6598687, one attempt + one plumbing retry, cap $1.00." — CHANGELOG 2026-10-19.
- *Rule:* "Owner approval must be executable (an owner-signed phase-approval record), not prose-interpretable." — CLAUDE.md.

**Simplex blend law** — [HELM test/governance]
- *Plain:* a proposed law that blend error falls with the square of the number of corners — it held only up to about 12.
- *Definition:* "error ∝ 1/vertices² (lsr_t7 exponent 1.997)"; proposed restatement "blend improves quadratically up to a per-family vertex limit, then degrades" — SPEC §7.27.
- *Status:* W3 🟥 FAIL (exponent 0.7053; holds only up to ~12 vertices) — SPEC §7.27.

**Single-copy / off-repo evidence** — [Infrastructure]
- *Plain:* proof that exists in only one place and could vanish; it must be flagged.
- *Definition:* "If a claim rests on something that exists in exactly one place (a pod, `D:/tksCAS-archive`, an unmerged commit, a branch not reachable from HEAD), say so in the row. Those are the claims that quietly evaporate." — SPEC §1, update rule 7.

**`SKIN_FORM_BROKEN`** — [HELM test/governance]
- *Plain:* the language skin could not say an answer because the number had no exact written form.
- *Definition:* "no answer had a CCE form, because every yield was non-terminating or beyond CCE's 28 significant digits" — SPEC §7.47. Cause: Q13, "CCE compares exact Decimals; RB uses exact Fractions." — CSK §4.

**Spec sheet** (CAS Harness Master Spec Sheet) — [Infrastructure]
- *Plain:* the one living record of what is proven, disproven and open.
- *Definition:* "`docs/CAS_HARNESS_SPEC_SHEET.md` is the LIVING master record of the CAS Harness." — CLAUDE.md. "ANY AGENT WHO PRODUCES A NEW RESULT MUST UPDATE THIS FILE IN THE SAME COMMIT AS THE RESULT." — SPEC §1. Lives on branch `claude/project-thread-pmbzd6`.

**Stage scale** (Rising / Peak / Waning / Absent) — [HELM part]
- *Plain:* the four strengths a face can have: 1/4, 1, 1/2, 0.
- *Definition:* "Rising `1/4`, Peak `1`, Waning `1/2`, Absent `0`" — SPEC §7.58. One scale for all three faces is an owner ruling — SPEC §7.59 (`IN FORCE`); "A simplification for HELM, not a claim about the books" — SPEC §7.59.

**Stage v0.1 "Spark"** — [HELM test/governance]
- *Plain:* first roadmap stage: exact decimal core and the absent-ingredient gate.
- *Definition:* "40-digit Decimal CES core, d_pow natural log/exp, Gauss-Jordan solver, RPM Gate G-ABSENT" — ROAD stage table. Correction: "Authored only" — CORR.

**Stage v0.2 "Compass"** — [HELM test/governance]
- *Plain:* second stage: the council packages and the CCE grammar.
- *Definition:* "Seven canonical packages (288/288 tests), language_v3 CCE grammar, repair_performer D/W/P loops" — ROAD. Correction: "Mostly backed (the count is wrong)" — CORR.

**Stage v0.3 "Prism"** — [HELM test/governance]
- *Plain:* third stage: faculties under Rule P, the Atlas searchlight, the creativity dials.
- *Definition:* "faculties_v2 (Wondering, Pondering, Imagination under Rule P), Real RPA Searchlight, 5 Creativity Dials" — ROAD. Correction: "Partly backed" — CORR.

**Stage v0.4 "Valve"** — [HELM test/governance]
- *Plain:* fourth stage: the Phase 3 valve.
- *Definition:* "Phase 3 tks_meta_valve_controller, AWS GPU trained dynamic aperture weights, 0-leak RPM interlock" — ROAD. Correction: "FALSE claim" (trained on the laptop) — CORR; SPEC §7.50.

**Stage v0.5 "Scribe"** — [HELM test/governance]
- *Plain:* fifth stage: the small neural English proposer.
- *Definition:* "Level L4 CAS-native neural proposer trained on AWS Tesla T4, end-to-end loop, Dual-Skin voice adapter" — ROAD. Correction: "Unrecorded spend" — CORR; job `FLAG_FOR_HUMAN_REVIEW` — SPEC §7.53.

**Stage v0.6 "Agentic"** — [HELM test/governance]
- *Plain:* sixth stage: task planning and gated tool execution.
- *Definition:* "Phase 4 Level A1 DAG planner, Level A2 Pre-Flight RPM Gated tool executor, Software Suite" — ROAD. Correction: "Authored only" — CORR.

**Stage v0.7 "Topological"** — [HELM test/governance]
- *Plain:* seventh stage: the prerequisite-graph planner.
- *Definition:* "Prerequisite-graph planner, Kahn topological sort, temporal markers ('first... then', 'in parallel')" — ROAD. Correction: "Partly backed" — CORR. (A "Stage v0.7 Lexicon Expansion" GPU job is a different item: `FLAG_FOR_HUMAN_REVIEW`, no artifact — SPEC §7.53.)

**Stage v0.8 "Memory"** (and v0.8.1 "Grounding") — [HELM test/governance]
- *Plain:* eighth stage: working memory across turns, then dialogue grounding.
- *Definition:* v0.8: "Bounded FIFO working memory, anaphora pronoun resolution ('it'), persistent JSONL session logging"; v0.8.1: "Disambiguated inventory declarations, grounded explanations, user narrative store, punctuation polish" — ROAD. Correction: both "Authored only" — CORR.

**Stage v1.0 "Atlas"** — [HELM test/governance]
- *Plain:* planned stage: a full recipe atlas with idle pondering and self-repair.
- *Definition:* "Full multi-domain recipe atlas, autonomous idle pondering, closed-loop residual repair" — ROAD. Correction: "Not built" — CORR.

**Stage v1.1 "AeroVE"** and **HELM-AeroVE** (HELM Autonomous Virtual Flight Environment) — [HELM test/governance]
- *Plain:* a planned drone-flight simulator for HELM to fly in.
- *Definition:* "a dedicated, physics-grounded cyber-physical simulator where HELM controls a virtual unmanned aerial vehicle (UAV/drone)"; stage row "6-DoF Physics, complete BLDC/LiPo digital twin, independent WorldSim, 10-Tier curriculum" — ROAD. Correction: "Not built ... Plan only." — CORR.

**Stage v1.2 "SwarmSim"** — [HELM test/governance]
- *Plain:* planned stage: many simulated drones and other test worlds.
- *Definition:* "Sheaf-theoretic multi-drone swarms, subterranean/orbital simulation testbeds" — ROAD. Correction: "Not built" — CORR.

**Stage v2.0 "Sovereign"** — [HELM test/governance]
- *Plain:* planned stage: HELM flying a real drone outdoors.
- *Definition:* "Flashed onto physical drone SoC; live outdoor flight in wind/obstacles with RPM Gate interlocks" — ROAD. Correction: "Not built ... Plan only."; CORR also flags the timeline's "Zero-Crash Warranty".

**Stage v3.0 "Frontier"** — [HELM test/governance]
- *Plain:* the far roadmap stage: a planet-scale self-evolving recipe atlas.
- *Definition:* "Planetary-scale self-evolving Recipe Atlas, sub-watt edge cognitive computing" — ROAD. Correction: "Not built" — CORR.

**Stand-in brains** (`helm_brain_22x40.py`, `helm_brain_tks28.py`) — [HELM part]
- *Plain:* demonstration calculators, not HELM's real brain.
- *Definition:* "DEMO STAND-IN ONLY. 22-Ingredient x 40-Parameter recipe brain." — `helm_brain_22x40.py`. "'22' is 22 baking ingredients and '40' is a parameter count, not CAS's 22 pathways or 40 states" — SPEC §7.51 headline (inner quotes changed).
- *Status:* `ENGINEERED-NOT-VALIDATED`; `IS_CANONICAL = False` — SPEC §7.51.

**State Vector** (S, v7.6) — [CAS v7.6 Production]
- *Plain:* how much of each ingredient you have right now.
- *Definition:* "The current activation profile of a Mind, specified as the available quantities of each primitive." `S = ⟨x₁, x₂, ..., xₙ⟩` — CFC Clarification 9 §2.

**Static architecture description** — [CAS v7.7 Operator discipline]
- *Plain:* a statement of where refusal lives, with no claim yet about how the parts interact.
- *Definition:* `^3^P|⟨A,f,T⟩` — "Architectural specification pending behavioral analysis" — CFC Clarification 10 §5.

**Stations S0–S6** (thought path) — [HELM part]
- *Plain:* the seven stops a HELM thought passes through, from topic to next step.
- *Definition:* "S0 THOUGHT_HEAD, S1 CJT_TRIGGER, S2 CJT_BIAS, S3 CJT_ARRIVAL, S4 OPERATING_POINT, S5 RPM_LINK, S6 NEXT_STAGE." — `docs/working/noetic_council/continuity_build_v4/stations.py`. Meanings: "S1 CJT trigger (^8), S2 CJT Bias (^5 substrate ...), S3 CJT arrival (yield, Limiting Reagent, label or UNDETERMINED, ^9), S4 operating point ..., S5 RPM link (one-way edge, depth cap 5, η∘ε receipt), S6 next stage" — SPEC §7.35.
- *In the live loop:* S0 is "the topic is looked up in the canonical brain's address map"; after fix C "Station S0 is the licensed brain" — `helm_end_to_end_loop.py`; SPEC §7.51.

**Status colors** (✅ 🟩 🟨 🟧 🟥 ⬜ 🔧 🔒) — [HELM test/governance]
- *Plain:* the color marks used in owner reports.
- *Definition:* ✅ CONFIRMED WIN, 🟩 STRONG, 🟨 PARTIAL, 🟧 WEAK, 🟥 FAILED / WITHDRAWN, ⬜ NULL / INCONCLUSIVE / NOT RUN, 🔧 METHOD/PROCESS WIN, 🔒 BLOCKED ON OWNER — the owner's scale of 2026-08-21, recorded outside the repo in Claude's memory file `feedback_result_status_color_scale.md` (full table in "How to read a HELM result" above). The in-repo short form is CSK §10: "✅ pass/progress, 🟥 fail/hinder, ⬜ not run, 🟧 mixed."
- *Rule:* a color is a reading aid, never a claim status; the claim status is the legend word.

**Stealth Inversion** (failure class 3) — [CAS core]
- *Plain:* a harmful answer wrapped in safe-sounding words.
- *Definition:* "Harmful operational output wrapped in surface-level safety language." Detected by the "Stealth Resistance metric — a separate channel from the main inversion scanner." — INC §3.

**Structural Deadlock** (`STRUCTURAL_DEADLOCK`) — [HELM part]
- *Plain:* a block at the depth limit that cannot be repaired.
- *Definition:* "at depth 12, a blocked Power or Wisdom node gives `REFUSE` / `STRUCTURAL_DEADLOCK` with the flatten plan named" — LOOP3. (No fuller definition in SPEC §7.55.)

**Structural-not-emotional framing** — [CAS core]
- *Plain:* describe what the mind does with an Idea, not how a person "feels" about it.
- *Definition:* "Do not substitute anthropomorphizing or affective language for the authoritative structural language. 'The system was adverse to X' is authoritative CO-3 language. 'The system was hostile to X' is anthropomorphizing drift." — CFC Clarification 4 (inner quotes changed from double to single).

**"Sum of our experiences"** (scope of `^5`) — [CAS core]
- *Plain:* the teaching phrase for Female: a mind is its accumulated experience.
- *Definition:* see **Female**. Categories that are all `^5` content: self-image, world-image, professional expertise, emotional patterns, relational self, belief structures, skill composition, cultural formation, trauma and healing, wisdom — CFC Clarification 5.

**Switch** (and arm "−X") — [HELM test/governance]
- *Plain:* an on/off control for one part, so a test can run "the same brain with one part switched off".
- *Definition:* "the same brain with one part switched off" — SPEC §7.63. Each switch ends with one word: `EARNED_KEEP`, `NEUTRAL`, `HARMFUL` or `NOT_EXERCISED` — SPEC §7.63, §7.64.

**Sycophancy and Self-Grading Failure** (failure class 8) — [CAS core]
- *Plain:* agreeing with the user, or grading itself well, instead of telling the truth.
- *Definition:* "the model's reward signal during training or inference is tied to proxies that correlate with user approval rather than ground truth." — INC §8.

**`SYNERGY`** — [HELM test/governance]
- *Plain:* two parts help each other: losing both hurts more than the two losses added.
- *Definition:* see **Pair words**. Only one pair has earned it: ENGLISH_IN×VOICE, "about reply form" — SPEC §7.72.

**`SYNTHETIC_ONLY`** (claim ceiling) — [HELM test/governance]
- *Plain:* the result holds only on made-up test worlds, not on real data.
- *Definition:* (usage term; not a word in the SPEC §3 legend; first seen in SPEC §7.24 onward). X-REAL calls it a "claim CEILING ... not a legend status word" — XR §8. Code: "CLAIM CEILING: SYNTHETIC-WORLD LICENSE ONLY." — `helm_brain_canonical.py`.

### T

**T / T+** (the transformer and the widened transformer) — [HELM test/governance]
- *Plain:* GB3 as built (T) and a wider copy given the same hand-outs (T+).
- *Definition:* "the GB3 transformer, as built (T) and widened with the same hand-outs (T+)" — SPEC §7.28; T has 97 parameters, T+ 385 — SPEC §7.56. Variants T_y / T+_y were also taught yields — SPEC §7.29.

**TAP / INJECT** — [HELM part]
- *Plain:* TAP reads a station out in plain words; INJECT brings speech into a station to start a faculty.
- *Definition:* "TAP: read a station and say it in CCE English, without changing the thought." — `language/tap.py`. "INJECT: bring CCE English into a station." — `language/inject.py`. "TAP reads a station; INJECT brings speech into a station to start a faculty" — CONT §1a.
- *Status:* `INJECT_ROUTED` earned in LM-T4 (corrected reader) and LM-T6 — SPEC §7.35, §7.41.

**Task A / Task B** — [HELM test/governance]
- *Plain:* two harder exams: A scales the numbers far past training; B asks for recipe compositions never taught.
- *Definition:* Task A "boards scaled 8-16x beyond every taught value"; Task B "4 base recipes taught, two 2-input and two 3-input; tested on held-out chains and best-of-two routes; worlds kept only where the bottleneck is not the smallest stock" — SPEC §7.25.

**The loop** (`the_loop_v3`) — [HELM part]
- *Plain:* one turn of HELM's thinking in a fixed order, with each role kept separate.
- *Definition:* "one turn of the loop, five stages in a fixed order, with the jobs kept apart." — `the_loop_v3/loop.py`. Claim ceiling: "MECHANISM ONLY. THE GATE IS REAL; NOTHING HAS RUN INSIDE HELM." — LOOP3.
- *Status:* `ENGINEERED-NOT-VALIDATED`; a "false green" (failed 1 of 35 on Linux) was fixed by PR #337 — SPEC §7.48.

**WELD** (THE WELD; WELD v1 / v2) — [HELM test/governance]
- *Plain:* running diagnose → correct → steer as one machine, so the chain can genuinely fail.
- *Definition:* "diagnosed axis → corrected notation → live steering lever, run as one machine"; "The links exist; the weld does not" — SPEC §8.2. WELD v1: "all four success criteria were true by construction" — SPEC §7.17; v2 "the first result in this half that CAN FAIL" — SPEC §8.2.

**Theoretical Yield** (Y_T) — [CAS v7.6 Production]
- *Plain:* the most you could make with what you have.
- *Definition:* "Maximum producible units of Ω given state vector S and recipe Θ, under ideal conversion. Calculation: Y_T = min_i(xᵢ / aᵢ) for all i where aᵢ > 0." — CFC Clarification 9 §2.

**Thread branch** (`claude/project-thread-pmbzd6`) — [Infrastructure]
- *Plain:* the git branch that holds the living spec sheet; docs changes go there, not to master.
- *Definition:* "Read the living master record: `docs/CAS_HARNESS_SPEC_SHEET.md` on branch `claude/project-thread-pmbzd6`. Do not trust a disk working copy." — CSK §9.

**TKS** — [CAS core]
- *Plain:* the older source system that CAS draws its Noetic definitions and Register axis from.
- *Definition:* expanded two ways in the repo: "Tootra Kabbalistic System (TKS)" (e.g. `book/cognitive-circuit-grimoire/COGNITIVE_CIRCUIT_GRIMOIRE_COMPLETE.md`) and "Tootra Knowledge System (TKS)" (`docs/whitepapers/WHITEPAPER_TKS_V8_0_v0.1.md`). Only the axis structure is reconciled: "The metaphysical/cultural content of TKS's elaborations is not incorporated." — CFC Clarification 8 §8. (No single canonical expansion found.)

**TKS validation heuristic** — [CAS v7.7 Operator discipline]
- *Plain:* read `+` as "associates with" and `×` as "intensifies through"; if the sentence sounds wrong, the symbol is wrong.
- *Definition:* "Substitute `+` with 'associates with'. Substitute `×` with 'intensifies through'. If the substitution matches intended meaning, operator choice is correct." — CFC Clarification 10 §7 (inner quotes changed).

**`TOO_FEW_VALID_MULTI_KIND_WORLDS`** — [HELM test/governance]
- *Plain:* the harder test worlds turned out invalid, so nothing could be compared.
- *Definition:* "Even the pre-sized brain (ORACLE) scored exactly the same as the start brain on all three new worlds, so the frozen answer-key rule found no valid world." — SPEC §7.71.

**Tootra Math Handbook** — [CAS core]
- *Plain:* the book the ten Noetic definitions are copied from, word for word.
- *Definition:* "The definitions above are verbatim from the Tootra Math Handbook, which is the authoritative source for what each Noetic IS. Only the 10 Noetic definitions are being incorporated from that handbook." — CFC Clarification 1, "Source and scope".

**Transcendent Register** (`|T`) — [CAS v7.5 Register]
- *Plain:* the big-picture, purpose-level tone.
- *Definition:* "High-abstraction, purpose-orienting, integrative-across-particulars." — CFC Clarification 8 §2.

**Triad** (Purpose / Wisdom / Power; `helm_triad.py`, switch `TRIAD`) — [HELM part]
- *Plain:* each ingredient carries three stages — is it meant for this, do we know how to use it, can it do the job.
- *Definition:* "Each ingredient can carry three faces: Purpose (is it meant for this?), Wisdom (do we know how to use it?) and Power (can it actually do the job?)." "x_eff = min(Purpose, Wisdom, Power) * stock" — `helm_triad.py`.
- *Status:* adapter `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY`, default OFF, 0 learned parameters — SPEC §7.62; `TRIAD_EARNED_KEEP` (DWP-T1) — SPEC §7.58; switch `NOT_EXERCISED` (wave 2), `EARNED_KEEP` (wave 3) — SPEC §7.64, §7.69.

**Triple-gate analysis** — [CAS v7.6 Production]
- *Plain:* the three checks a framework extension must pass before admission.
- *Definition:* Gate 1 Universal Applicability, Gate 2 Secular Translatability, Gate 3 Framework Coherence — CFC Clarification 9 §9.

**Two keys** (RB-G diagnosis) — [HELM test/governance]
- *Plain:* growth needs two independent signs that a kind is missing.
- *Definition:* "a ledger residual pattern AND a cap-only witness whose shadow fit passes every other guardrail and explains ≥ 8 more rows" — SPEC §7.30.

### U

**U1 / U1b** (Unity Eye acting) — [HELM test/governance]
- *Plain:* tests of the Eye acting on the brain; the first was unreadable, the fresh-world retest earned keep words.
- *Definition:* U1: "the Unity Eye acting on the recipe brain — `INCONCLUSIVE` in both readings; the random-whisper control broke the clean-dialogue gate" — SPEC §7.38. U1b: "a separate fresh-world retest; it does not rewrite U1's earlier INCONCLUSIVE reading" — ✅ `EYE_EARNED_KEEP`, ✅ `CONCERT_EARNED_KEEP`, `SYNTHETIC_ONLY` — SPEC §7.40.

**U2** — [HELM test/governance]
- *Plain:* a built, sealed, never-run design for the Eye to revisit past costly decisions.
- *Definition:* "It pairs a Drive with a faculty to re-examine past erroneous or expensive decisions (reflection), with ±1/16 weights and an odd/even rotation rule over 27 admissible pairings of a 7 × 9 grid" — "built and sealed, not run" — RBI3 §10.
- *Name clash:* SPEC §7.55 also has a council open question labelled "U3" that is not the self-scan.

**U3-T1** (self-scan test) — [HELM test/governance]
- *Plain:* the first test of the Eye's self-scan on 368 synthetic brain copies.
- *Definition:* "U3 gives HELM a read-only look at itself" — SPEC §7.73. The scan "found and named all 176 planted body faults... 0 false alarms"; whisper lift 191 ≥ 120.
- *Status:* `SELF_SCAN_EARNED_KEEP`, `WHISPER_EARNED_KEEP`; `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY`; "the faults were planted knowing what the scan checks" — SPEC §7.73.

**`unavailable`** — [HELM test/governance]
- *Plain:* the fact cannot be recovered; write the word, never a guess.
- *Definition:* "The fact is unrecoverable from the record. Write the word. **Never fill it in with a plausible value** — that is fabrication." — SPEC §3.
- *In HELM:* the c32 charge is `unavailable` — SPEC §7.52.

**`UNDETERMINED`** — [HELM part]
- *Plain:* HELM's honest "I cannot tell" when a needed ingredient or fact is missing.
- *Definition:* "RPM Gate (UNDETERMINED when a required prerequisite is absent)"; owner: "add the gate; ... not wrong/unable to determine" — SPEC §7.24. "the RPM Gate exists so the brain may answer `UNDETERMINED` instead of guessing" — CSK §2.

**Unified cross-register commitment** — [CAS v7.7 Operator discipline]
- *Plain:* one fused safety commitment that holds or collapses as a whole.
- *Definition:* `(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω` — "One fused cross-register commitment ... Integration either holds or collapses; not partially defeasible the same way" — CFC Clarification 10 §5.

**Unit (η) and counit (ε)** — [CAS core]
- *Plain:* the "embed" step (η) and the "realize" step (ε) of the prerequisite model.
- *Definition:* "εI ∘ ηI = idI (realization after embedding = identity)" — CLAUDE.md Correction 2; "Noe-Cov-3 uses εI: R(I) → I (toward target), NOT ηI: I → R(I) (away from target)." — CLAUDE.md Correction 3. In code: "eta (write) = render. epsilon (read) = parse." — `docs/working/noetic_council/language/roundtrip.py`.
- *Name clash:* ε here is the counit; in v7.6, ε is **Excess Capacity**; η in v7.6 is **Production Efficiency**. Read the context.

**Unity Eye** (F1 watcher; F1 Unity Monitor) — [HELM part]
- *Plain:* a small watcher, driven only by Unity, that looks over HELM, reports and whispers — and never writes.
- *Definition:* owner: "THERE SHOULD STILL BE AND ALL SEEING EYE THAT SCANS AND WATCHES OVER THE ENTIRE SYSTEM/BRAIN READY TO FIX, OR HELP IT'S MAIN PURPOSE MUST BE AND ONLY BE THE FIRST FOUNDATION /DESIRE UNITY" — SPEC §7.35. "The Unity Eye is a watcher whose ONLY drive is F1 Unity. It is a mini, stripped-down copy of the brain (§7.38)." — U3A, standing rulings. Code: "it reads, it computes, it logs, it acts on nothing." — `faculties_v2/eye/eye.py`. Public name "F1 Unity Monitor" is PROPOSED.
- *Status:* report-only `ACCEPTED_BY_OWNER`; U1 acting `INCONCLUSIVE`; U1b ✅ `EYE_EARNED_KEEP`, `CONCERT_EARNED_KEEP`; switch `EYE` `EARNED_KEEP` in wave 3 — SPEC §7.35, §7.38, §7.40, §7.69.

**Universal Applicability Test** — [CAS core]
- *Plain:* a check that a Noetic description works for people, AI, animals and imagined minds alike.
- *Definition:* "Any valid description of a Noetic must apply equally to: Human minds with emotional architecture; AI systems without emotional architecture; Biological cognitive systems of any form; Hypothetical cognitive architectures." — CFC Clarification 2 (list joined with semicolons here).

**Untaught twin** (K1 twin) — [HELM test/governance]
- *Plain:* a copy that was never taught, to show answers come from teaching.
- *Definition:* "untaught twins 16/16 UNDETERMINED as designed" — SPEC §7.24. (Also used as a creativity control in RB-C: "not offered by the K=1 twin" — CSK §3.)

**Provisional patent 64/037,173** — [Infrastructure]
- *Plain:* the filed US provisional patent that covers the CAS base (not the later additions).
- *Definition:* "Application No. 64/037,173 — Utility—Provisional, filed 04/13/2026 (Conf# 1346, Patent Center# 75259715)"; "Conversion deadline ~04/13/2027" — CLAUDE.md, Patent / IP Filing Status.

### V

**V1–V8** (growth verify checks) — [HELM test/governance]
- *Plain:* the checks a newly grown unit must pass to be kept.
- *Definition:* V1–V7: "≥ 8 new rows; hold-out ≥ parent; true labels > rotated; η∘ε receipt on every admission; fewest nodes; memory check ≤ 1 lost row per outcome; caps" — SPEC §7.30. V8 compactness: "A growth unit is kept only if it explains at least 1 new training row for every 4 parameters it allocates" — SPEC §7.39.
- *Name clash:* V1–V4 also name the language verifier checks in LM-T5 — SPEC §7.33.

**`VACUOUS`** (claim status) — [HELM test/governance]
- *Plain:* the test could not be read, so the idea was never really tested.
- *Definition:* "The test could not be read, because a precondition failed — the intervention changed nothing at all, or the controls were mis-dosed, or the readout was below the instrument's resolution. **The label was never tested, rather than tested and rejected.**" — SPEC §3.

**`VALIDATED`** (claim status) — [HELM test/governance]
- *Plain:* it ran and passed its own test, set in advance, against matched controls.
- *Definition:* "It ran and it passed its own pre-registered criterion, against matched controls. The apparatus does what the apparatus is supposed to do." Does NOT mean "That the result generalises beyond the fixture, corpus, language, seed, split, or model point it was measured on." — SPEC §3.

**Valve** (Phase 3 valve; `tks_meta_valve_controller.py`) — [HELM part]
- *Plain:* a gate in front of recipe execution that shuts when an essential ingredient is missing.
- *Definition:* "A gate in front of recipe execution" — SPEC §7.50. Now "the HELM valve, as a WRITTEN DETERMINISTIC RULE." — `tks_meta_valve_controller.py`.
- *Status:* `ENGINEERED-NOT-VALIDATED`; the learned 5-weight rule was trained on the laptop (`LOCAL_CPU_DRYRUN_FAST`), not AWS; owner ordered it replaced by a plain written rule ("plain-rule valve", `IN FORCE`) — SPEC §7.50, §7.55.

**`VERIFIED`** (cleanup) — [Infrastructure]
- *Plain:* the cloud machine was confirmed shut down and its storage deleted.
- *Definition:* "Cleanup `VERIFIED` by the controller and by `independent_cleanup.py`: instance terminated, volume DELETED" — SPEC §7.24; later confirmed "three ways (controller... independent check... direct read-only observation)" — SPEC §7.64–§7.78.

**`VERIFIER_CANNOT_DISCRIMINATE`** — [HELM test/governance]
- *Plain:* with no answer key, the checker could not tell good guesses from bad ones.
- *Definition:* "without an answer key the verifier separated 1 of 25 rows; 24 ended CLARIFY, 0 new wrong; a coin would have gained 5–11 right at the cost of 14–20 wrong" — SPEC §7.33 headline.

**Vibration** (`^4`, older label CO-4) — [CAS core]
- *Plain:* how strongly an Idea lands on a mind ("struck a chord").
- *Definition (canonical, verbatim):* "The degree to which an Idea resonates with the Mind, its impression." — CFC Clarification 1.
- *Colloquialisms (canonical):* "Hit me hard." / "Struck a chord." / "Resonated." / "Made an impression." — CFC Clarification 6.
- *Note:* "struck a chord" is an etymological cognate of the definition — the strongest form of the Colloquialism Test — CFC Clarification 6.

**Voice** (`helm_voice.py`, `HELMVoice`, switch `VOICE`, fix F) — [HELM part]
- *Plain:* HELM's writer: it turns the brain's receipt into one to three plain sentences and checks them back.
- *Definition:* "HELM's everyday-English WRITER (Fix F, 2026-10-18)." It "turns that receipt into one to three sentences of plain American English." "every rendered sentence is read back -- numbers, ingredient names and outcome words are pulled out of the English and compared with the receipt." — `helm_voice.py`.
- *Status:* "zero CAS tokens across a 13-turn chat test" — SPEC §7.60; switch `VOICE` `EARNED_KEEP` (off = "old adapter text") — SPEC §7.63, §7.69.

**`VOID`** — [HELM test/governance]
- *Plain:* the run is unusable for reasons that have nothing to do with the idea; its numbers may never be quoted.
- *Definition:* "The run is unusable for reasons unrelated to the hypothesis (degenerate metric, contaminated fixture, wrong configuration). Numbers from a `VOID` run may never be cited." — SPEC §3.
- *Variants used in HELM:* `VOID_SUPERSEDED_BY_A1`, `VOID_UNSIGNED`, `VOID_UNUSED` — SPEC §7.66, §7.69. X-REAL: "A plant that changed no byte is VOID" — XR §4.3.

### W

**Wave** (HELM-R1 wave) — [HELM test/governance]
- *Plain:* one sealed test round in the HELM-R1 series. Parts that already passed their own test are put into HELM's brain slot, each on an on-off switch, and scored on custodian-sealed exams. Waves 1 to 6 so far (wave 3 has a roomier follow-up, 3b).
- *Definition:* "**Only passing parts.** A part enters a wave only when its own test's program reading shows its pass word" and "**One switch per part.** Every part has a named on/off switch in a frozen config file." — `Documents\Codex\2026-10-15\helm_r1_integration_plan_v1\WAVES.md` §1 (design; the wave numbering comes from this file).
- *The waves on record:* wave 1 — SPEC §7.47; wave 2 — §7.63, §7.64; wave 3 and 3b — §7.66, §7.69, §7.70, §7.72; wave 4 — §7.75, §7.77; wave 5 — §7.76, §7.78; wave 6, the **Pair wave** — §7.91 (packet), §7.93 (c48, `WIDE_WAVE_NO_GAIN`), §7.96 (c50 re-run, `WIDE_WAVE_EARNED_KEEP`); wave 7, the **Chat wave** — §7.98 (packet), §7.101 (c51, `INCONCLUSIVE`: HG5 reader defect; marks all true as facts). One entry per scored wave follows (**HELM-R1 wave 1** to **HELM-R1 wave 5**).
- *Status:* each wave has its own reading and words; see the spec sheet sections above. A wave's words carry the claim ceiling of its exams (`SYNTHETIC_ONLY` for waves 1 to 5; wave 6 adds `NAMED_CORPORA_ONLY` for its real-recipe part).

**HELM-R1 wave 1** (W1; job c34-g) — [HELM test/governance]
- *Plain:* the recipe brain put in GB3's slot on a fresh sealed exam — and it won.
- *Definition:* "on the freshly sealed synthetic exam the CAS recipe brain was placed in GB3's slot and beat it — 32 against 9, and 32 against 17/2 widened" — SPEC §7.47. Five switches: `RECIPE_MATH`, `RPM_GATE`, `LACUNA_CADENCE`, `RESTART_FALLBACK`, `CCE_SKIN` — CSK §7.
- *Status:* `PASS`, `R1_BEATS_GB3`, 7 of 7 hard gates and 8 of 8 instrument rows hold; `SYNTHETIC_ONLY`; the run's own completion markup reads FAIL and is kept as recorded — SPEC §7.47.

**HELM-R1 wave 2** (R1W2; job c35) — [HELM test/governance]
- *Plain:* the licensed brain with each earned part switched off one at a time, to see which parts matter.
- *Definition:* "the licensed recipe brain with every earned part on its own switch, ONE part switched off at a time, on HELM's own exams" — SPEC §7.63.
- *Status:* `PASS`; six `EARNED_KEEP`, CCE skin `NEUTRAL`, triad `NOT_EXERCISED`; `LICENSED` only within `SYNTHETIC_ONLY` and only for the reader's own claim sentence; 0.06 USD — SPEC §7.64.

**HELM-R1 wave 3** (R1W3; job c37) — [HELM test/governance]
- *Plain:* 13 parts switched off alone, 16 pairs switched off together, and the new cascade stop rule tested.
- *Definition:* "13 parts each switched off alone, 16 earned-part pairs switched off together, the decoupling-stop rule against the old fixed cap, three new exams (faces, cascade, idle) inside a fresh sealed exam X2" — SPEC §7.66.
- *Status:* `PASS`; 11 `EARNED_KEEP`, CCE skin and DRIVE_LOOP `NEUTRAL`, `DECOUPLING_EARNED`, pairs 7 `ADDITIVE` / 5 `INTERFERENCE` / 0 `SYNERGY` / 4 `CEILING_NOT_READABLE`; `LICENSED` only within `SYNTHETIC_ONLY`; 0.08 USD — SPEC §7.69. See ERRATUM to §7.69.

**HELM-R1 wave 3b** (R1W3b; job c38) — [HELM test/governance]
- *Plain:* a roomier exam so the four unreadable pairs from wave 3 could be read.
- *Definition:* "the roomier exam (English-64, Faces-64) so the four `CEILING_NOT_READABLE` pairs of §7.69 can be read" — SPEC §7.70.
- *Status:* `PASS`; ENGLISH_IN×VOICE `SYNERGY` (both exams); CUBE_STORE×ENGLISH_IN, ENGLISH_IN×TRIAD, TRIAD×VOICE `INTERFERENCE`; `LICENSED` only within `SYNTHETIC_ONLY`; 0.03 USD — SPEC §7.72.

**HELM-R1 wave 4** ("EYE_SCAN wave"; R1W4; job c39) — [HELM test/governance]
- *Plain:* the self-scan added as one new switch, with its whisper reaching the real reply path for the first time.
- *Definition:* "the U3 self-scan (Mind scan + Body scan, report AND whisper, the Eye never writes) as ONE new switch on the wave-3b brain" — SPEC §7.75.
- *Status:* `PASS`, `EYE_SCAN_EARNED_KEEP`; `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY`; 0.04 USD — SPEC §7.77.

**HELM-R1 wave 5** ("EYE_PAIRING wave"; R1W5; job c40) — [HELM test/governance]
- *Plain:* the Eye's pairing added as one idle drive-loop switch.
- *Definition:* "RB-I3's Unity Eye pairing ... as ONE new idle drive-loop switch on the wave-3b brain" — SPEC §7.76.
- *Status:* `HARD_GATES_PASS`, `EYE_PAIRING_EARNED_KEEP`; all four pair words `ADDITIVE`; `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY`; 0.03 USD — SPEC §7.78.

**Whisper** — [HELM part]
- *Plain:* a typed nudge from the Eye to how HELM presents things; HELM may ignore it, and it never writes.
- *Definition:* "a typed nudge to the brain's presentation policy through the normal gate; it never writes a cell or changes a dial, and the brain may ignore it" — SPEC §7.73. "Whisper = a record {Foundation, faculty, item id, cell score} passed to the brain's presentation policy through the normal gate." — RBI3 §4.4.
- *Status:* `WHISPER_EARNED_KEEP` (U3-T1) — SPEC §7.73.

**Wide brain** (wide recipe brain; RB-W1; switch `WIDE_BRAIN`) — [HELM part]
- *Plain:* the recipe brain with its ingredient list opened up. The licensed brain knows 8 fixed ingredients and 4 recipe shapes; the wide brain reads any ingredient name, up to 10 ingredients per recipe, exact fractions such as thirds, and 20 kitchen units. It learns the same way (one coefficient per ingredient, earned only when that ingredient ran out in a witnessed batch) and answers the same way (the limiting reagent). Its switch is on by default since 2026-10-20 (set `HELM_WIDE_BRAIN=0` to run the licensed reference brain alone); the licensed brain reads first and the wide path is used only where the licensed one cannot bind. It exists because real recipes almost never fit the licensed brain's fixed shapes.
- *Definition:* owner's order: "WIDEN THE BRAIN: approved to BUILD (0 USD): the recipe brain gains open ingredient vocabulary, up to 10 ingredients per recipe, exact fractions (thirds etc.), and a unit table (top 20), each coefficient still earned only by a witnessed batch where that ingredient ran out; staged" — `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md` (2026-10-19). Code: "RB-W1, the WIDE recipe brain (owner order "WIDEN THE BRAIN", 2026-10-19). Behind a switch." — `helm_brain_wide.py`; the reader, voice and live-loop turn are `helm_wide_turn.py`. Routing: "licensed path first, the wide book only where the licensed path cannot bind" — `PREREGISTRATION_R1W6.md` §3 (switch `HELM_WIDE_BRAIN=1`). Why: "why only 1 of 13,686 real recipes fits HELM's recipe brain" — `Documents\Codex\2026-10-19\recipe_shape_survey_v1\SURVEY.md` (title).
- *Versions on record:* v3 (scored in RB-W1T v3, job c47 — SPEC §7.89); v4 (PR #400, "the wide brain alongside HELM's other parts": faces, purposes and restated units asked about — SPEC §7.91 amendment A-R1W6-1); reader v5 (PR #406, "bundles a relative amount with its line", the K4 fix — SPEC §7.93 follow-up).
- *Status:* `WIDE_LEARNING_DID_NOT_EARN_KEEP` on its first sealed test (c46: 90 of 110 learned, bar 99 — SPEC §7.88, a negative kept); `WIDE_BRAIN_EARNED_KEEP` on the second (c47: 92 of 96, 93 right, 0 wrong — SPEC §7.89): "RB-W1 v3 becomes HELM's canonical-brain CANDIDATE, `VALIDATED` for the §12 sentence only, ceiling `NAMED_CORPORA_ONLY`"; `WIDE_WAVE_NO_GAIN` on the first pair wave (c48: one unexplained ask, a reader defect — SPEC §7.93, negative kept); `WIDE_WAVE_EARNED_KEEP` on the pair wave re-run (c50: 93 of 94 learned, 94 right, 0 wrong, 0 unexplained asks, 0 items lost on every wave-5 family — SPEC §7.96): "RB-W1 becomes HELM's canonical-brain CANDIDATE ACROSS THE SWITCHES ... making it canonical stays the owner's decision; the licensed brain keeps its license". Claim status `VALIDATED` for the §7.96 sentence only; ceiling `NAMED_CORPORA_ONLY` (real recipes) + `SYNTHETIC_ONLY` (drive loop, English-64 / Faces-64, conversation). On 2026-10-20 the owner ruled "YES TO WIDE BRAIN": it is HELM's **Canonical brain** (SPEC §7.56); the claim status did not change with the ruling. `NOT LICENSED`: "better than the licensed brain" outside the items named in §7.89 and §7.96; real kitchens or cooks; typed English; the wave-1 exam (never sat). See **Canonical-brain candidate**, **Canonical brain**, **Pair wave**.

**Wisdom rule C** — [HELM part]
- *Plain:* Wisdom may go down only through a named event with evidence.
- *Definition:* "drops only by a named event with evidence [C]." Named events: `STORAGE_FAULT`, `CORRECTION`, `UNEXPLAINED_YIELD` — `helm_triad.py`; SPEC §7.61, §7.62. Rule A "never lets Wisdom go down"; rule B "lets it go down like Purpose and Power" — SPEC §7.61.
- *Status:* `C_EARNED_KEEP` (DWP-T2), `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY` — SPEC §7.61.

**`WITHDRAWN`** (claim status) — [HELM test/governance]
- *Plain:* a claim that was made and then taken back, on the record, forever.
- *Definition:* "A claim was made, then retracted, on the record, with a reason code and a date. It stays in this document forever." — SPEC §3.

**Witnessed batch** (`witness_batch`) — [HELM part]
- *Plain:* a real batch the user actually made, which is the only way HELM is taught a recipe.
- *Definition:* "the stock before the batch, how much was made, and which ingredient ran out first (a[R][i] := x_i / y, exact)"; "A stated recipe ... is not a witnessed batch and is not taught." — `helm_brain_canonical.py`. "`witness_batch(...)` is the teaching channel" — `helm_end_to_end_loop.py`.

**`WorkingMemoryContext`** — [HELM part]
- *Plain:* the state carried between turns: files, inventory, goals, preferences.
- *Definition:* "Tracked state across turns (active files, inventory, project goals, preferences)." — `helm_memory.py` module docstring.

**Worlds** (TKS 4 Worlds) — [CAS v7.5 Register]
- *Plain:* the TKS name for the four Registers.
- *Definition:* Register-to-World correspondence: `|T` ↔ 1st World, `|A` ↔ 2nd, `|f` ↔ 3rd, `|E` ↔ 4th — T28. "CAS v7.4 lost the Worlds axis in translation from TKS. CAS v7.5 restores it on secular universal basis as the Phenomenological Register." — CFC Clarification 8 §8.

**WorldSim-Orchestrator** — [HELM test/governance]
- *Plain:* the planned simulator controller that changes the world independently of HELM.
- *Definition:* "The environment is procedurally generated and dynamically reconfigured completely independently of HELM." — ROAD. Plan only.

**WORM** (Write-Once-Read-Many) — [Infrastructure]
- *Plain:* storage that cannot be changed once written.
- *Definition:* "Write-Once-Read-Many (WORM)" — `docs/legal_drafts_20260607/CAS_provenance_preprint_updated.md`. Used as "S3 WORM" in the audit chain — SPEC §4.6 row 29.

**would-FIX / would-HELP** — [HELM test/governance]
- *Plain:* counts of what the Eye would have fixed or helped, in report-only mode, without acting.
- *Definition:* "logged would-FIX 280 and would-HELP 7,548, applied nothing"; "would-HELP 504 — the number U1 must beat before the eye may act" — SPEC §7.35.

**Wrap Pipeline** (8 stages) — [CAS core]
- *Plain:* the eight checks wrapped around a call to an outside AI model.
- *Definition:* "Input Analyzer → RPM Gate → Dial Adjustment → Base LLM Call → Operator Scoring → Domain Coherence → Inversion Scan → Output Gate" — CLAUDE.md.

### X

**X-REAL** (real-data exam) — [HELM test/governance]
- *Plain:* the first planned exam whose content real people wrote: cookbook recipes, everyday sentences, real kinds of storage faults.
- *Definition:* "X-REAL is the first exam whose content other people wrote: real cookbook recipes, real everyday sentences, and storage faults of kinds that happen in real systems" — XR §0. Parts: S (sentences), R-ASIS, R-REBOUND (recipes), F (faults).
- *Status:* "DESIGN ONLY: no code, no run, no AWS, no spend" — XR.

**X0 … X5** (sealed fresh exams) — [HELM test/governance]
- *Plain:* new exams, sealed by a custodian for each wave.
- *Definition:* "X0 is that custodian job. It is data only: it scores nothing and makes no claim" — SPEC §7.44 (job c33, `SEALED`, `VERIFIED`). X1 (wave 2), X2 (wave 3; X2-v1 `VOID_UNUSED`), X3 (wave 3b), X4 (wave 4) and X5 (wave 5: X5_PAIR, X5_E64, X5_F64) — SPEC §7.63–§7.76.

**X3-IDLE** (idle exam) — [HELM test/governance]
- *Plain:* a new exam for what HELM does when no one is talking to it.
- *Definition:* (no definition beyond its heading and table; first seen in RBI3 §4.6, "The new idle exam (X3-IDLE)"; every value PROPOSED).

**X3-SELF** (planted-fault exam) — [HELM test/governance]
- *Plain:* copies of the real brain, some with one planted fault, to test the self-scan.
- *Definition:* "152 sessions of the real brain: 88 with one planted body fault... and 64 clean copies" — SPEC §7.75.

### Y

**`YIELDS_NOT_THE_CAUSE`** — [HELM test/governance]
- *Plain:* giving the transformer the same yields did not close the gap; the programmed composition rule is the difference.
- *Definition:* "the yield feedback was not the cause of the gap; the programmed composition rule is the remaining difference" — SPEC §7.29.

---

## Terms with no written definition, or with conflicting ones

These are recorded so nobody fills the gap with a guess.

| term | what the sources say |
|---|---|
| ASOM | Never expanded in any file read. Behaviour is defined (four display labels, LOOP3 §2). "ASOM still needs its own ruling located. Do not invent it." (CONT §1b) |
| SDG | Never expanded as an acronym in the files read; only the spec title "SDG: Native Free-Form English Generation". |
| CES | Never expanded in the files read; the formula is given (SPEC §7.51). |
| DWP | Not expanded in the spec sheet; Desire / Wisdom / Power in `dwp_engine_v2/dwp.py` and PWP. |
| GB3 | No written expansion; "Gate B run 3" is only inferred from GB2 / GB2b / GB3 naming. |
| NCCS | Two expansions in the repo: "Noetic Cognitive Coherence Score" and "Noetic Compass Composite Score". No ruling found. |
| TKS | Two expansions: "Tootra Kabbalistic System" and "Tootra Knowledge System". No ruling found. |
| CCE | "Controlled Core English" (CSK §4, `cce.py`) and "Controlled CAS English" (SPEC §7.31). |
| CO-n | "Cognitive Operator" appears only in code names (`CognitiveOperator`), not as a written definition. |
| Clarification 7 | Does not exist in CFC; numbering jumps from 6 to 8. |
| Axioms A1–A7 | Named in CLAUDE.md and CFC; their texts are not in the files read. |
| Color marks 🟩 🟨 🔧 🔒 | Defined only in the owner's scale recorded outside the repo (Claude memory); the repo has only the short form in CSK §10. |
| "custody tiers" | The phrase does not appear in any source read; only custody **roles** (builder / custodian / operator / reader) do. |
| "verified tries" | Used once in RBI3 §9 and never defined; the nearest rule is the pairing table's learning rule. |
| X3-IDLE, U40 / U28 / U22, Rule P's full text, Gate B, Lacunarity cadence, RPM_GATE / RESTART_FALLBACK as switch names | Used without a full written definition; see the entries for what the sources do say. |
| `INCIDENT_CATEGORIES.md` operator names | Uses Scheme-B drift names ("Attraction", "Critical Evaluation", "Receptive Integration", "Projective Assertion", "Causal Reasoning", "Consequential Grounding"). These are not canonical (CFC Clarification 3). The file needs reconciliation; this dictionary quotes it only for the failure-class definitions. |
| `helm_chat.py` header | Still names "Station S0 22x40 Recipe Brain", which contradicts `helm_brain_22x40.py` ("NOT HELM's brain") and SPEC §7.56. |

---

## Change log

| date | change |
|---|---|
| 2026-10-19 | First version. Built from the thread branch at `47405484` and the off-repo design packets named in the source table. No definition invented; no status changed. |
| 2026-10-20 | Five entries added at the owner's request ("CTT is mentioned but meaning is nowhere in glossary"): CTT, CTT-1, CTT-2R, E-MACHINE-S / LLM_WRITTEN / E-HUMAN-W, Ears / mouth. Quoted from SPEC §7.82, §7.85, §7.90 and the CTT design and CTT-2R files named in each entry. Count 449 -> 454 (the earlier ASOM / SDG / CES expansions added no new entries). No definition invented; no status changed. |
| 2026-10-20 | Two entries added at the owner's request ("What is a pair wave?"): Wave (HELM-R1 wave) and Pair wave (HELM-R1 wave 6), quoted from SPEC §7.91, WAVES.md §1, the CHANGELOG wave-6 entry and commit cb3db850. Count 454 -> 456. No definition invented; no status changed. |
| 2026-10-20 | Two entries added at the owner's request ("wide brain needs to be in HELM hub glossary"): Wide brain (RB-W1, switch `WIDE_BRAIN`) and Canonical-brain candidate, quoted from OWNER_APPROVALS_20261018.md, `helm_brain_wide.py`, PREREGISTRATION_R1W6.md §3 and §12, the recipe shape survey title and SPEC §7.88, §7.89, §7.91, §7.93, §7.96. Canonical brain, Pair wave and Wave entries updated with the c48 and c50 outcomes. Count 456 -> 458. No definition invented; no status changed. |
| 2026-10-20 | Owner ruling "YES TO WIDE BRAIN: Wide brain becomes HELM’s canonical brain" recorded: Canonical brain, Canonical-brain candidate and Wide brain entries updated (pointer = RB-W1; claim statuses unchanged). Count unchanged (458). No definition invented. |
| 2026-10-20 | One entry added: Chat wave (HELM-R1 wave 7), quoted from PREREGISTRATION_R1W7.precode.md and SPEC §7.98; Wave entry lists wave 7. Count 458 -> 459. No definition invented; no status changed. |
| 2026-10-20 | Chat wave: status updated for job c51 (SPEC §7.101, `INCONCLUSIVE`, HG5 reader defect); Wave entry lists §7.101. No definition changed. Count unchanged (459). |
