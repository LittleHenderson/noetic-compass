# CAS PCBA Reasoning Processor ("CCB-R1") — Audit of Agent Output

**Date:** 2026-08-27
**Auditor:** Claude Code (lead) + 13-agent adversarial audit workflow
**Subject:** An agent-produced design answering *"can REASONING PROCESSING BE DEVELOPED PURE FROM CAS PCBA ENGINEERING ONLY"* — proposing a board-level reasoning processor named **CCB-R1 / CAS-RPU**.
**Status:** Audit only. No implementation authorized by this doc. No change made to any CAS artifact.

---

## Verdict

**The artifact's answer is right. Its build plan is not — because it was written as if this repository were empty.**

The central claim — that a reasoning architecture can be specified from CAS components alone — is defensible, and the artifact qualifies it honestly. Section 14 splits "pure" into four separate claims and returns three negatives (pure I/O: not formalized; pure physical machine: wrong category; proven general reasoner: no). That is the right shape of answer and the part a referee would respect.

Where it fails is **reuse and self-consistency**. It proposes a grammar extension, a namespace, and an adapter that already ship *and execute* in this repo. And its one machine-readable deliverable — the §11 netlist — violates both safety laws the document itself calls load-bearing.

**Net: keep the argument and §3/§14/§15. Discard §1 and §12. Rebuild §11.**

Severity profile after adversarial verification: **0 critical, 21 major, 49 minor, 22 credits** (92 findings survived, 29 refuted). Every finding initially scored "critical" was downgraded on verification. There is no fatal flaw here — but there is a large amount of avoidable spend.

---

## Audit method and scope limit

Six independent audit lenses (canon fidelity, source fidelity, internal consistency, mathematical-corrections compliance, answer quality, IP/governance) each produced findings; a dedicated adversarial verifier then attempted to refute each finding by re-reading the primary sources. Only survivors are reported.

> **AMENDED 2026-08-27** — all three source documents have since been supplied and are
> committed to `docs/reference/pdf/`. The scope limit below is preserved as written for the
> record; see `docs/working/cas_pcba_audit_source_verification_2026_08_27.md` for what the
> sources settled. Headline changes: the `A22` claim is **contradicted** (zero occurrences
> across all seven readable sources); the page 13/14/15 citations and the paper's four
> disclaimers are **confirmed**, several near-verbatim; and the board inventory
> (CMB/CDAB/CPMB/CSB, Schmitt, diodes) and CCDL are all **confirmed real**. Nothing in this
> audit remains unverifiable for want of a source.

### The three source PDFs were not available

`CAS_PCBA_Engineer.pdf`, `CAS_Ohm_Quantifications_Guide-1.pdf`, and `RESEARCH_PAPER_CAS_OHM_1_0_v0.2.pdf` are **not in the repository** and were **not found in the connected Google Drive** (searched by title and by full text for `CJT`, `CAS-Ohm`, `PCBA`, `Cognitive Junction Transistor`, `Cognitive Memory Board`).

Roughly 40% of the artifact therefore **could not be verified or falsified**. Nothing in the list below was scored as false — only as unverifiable:

- Every page-anchored citation: the "page 13" Understanding→Evaluation→Response diagram, the "page 15" RPM diagram, and the "page 14 nested-CJT diagram [that] **explicitly requires** keeping child test points" (the least hedged and least corroborated of the three — it is the sole warrant for Law 5).
- The board inventory and its design values: CMB's 40-cell capacitor bank and three leakage tiers, CDAB internals, CPMB, CSB, COB, the Schmitt two-threshold design, and the unity-gain amplifier example that Law 3 and the §6 "truth firewall" rest on.
- **CCDL itself.** `CCDL` appears zero times in this repo. `compiler.py` never calls itself CCDL and has no `board`/`node`/`cjt`/`diode`/`probe`/`feedback` productions. So "using current CCDL forms" can be neither confirmed nor refuted — and any criticism that equates CCDL with `compiler.py` is a category error.
- The CAS-Ohm V/R/I model and the research paper's four "is not" disclaimers.
- The claim that a "clean definitions source" writes `A22`.

**To close this gap:** check the three PDFs into the repo or a versioned docs store, and name the file and page of the "clean definitions source" that allegedly writes `A22`.

### Two corrections to this audit's own working assumptions

Stated openly, because both are instructive and both initially told against the artifact unfairly:

1. **The artifact's Foundation labels and 28-cell grid are canonical, not invented.** An early evidence pack scored "Association / Wealth / Continuation" as euphemisms for TKS's "Unity / Material / Lust". That reading came from the **superseded v6.1 manual**. `_tmp_TKS_v7_4_FULL_CORRECTED.txt:1643` Table 1.1 "Terminology Equivalence for the Seven Foundations" gives `F1 Unity → **Association**`, `F6 Material → **Wealth**`, `F7 Lust/Continuation → **Continuation**` as the *canonical v7.4 labels*, with the usage convention: *"In formal proofs and definitions, use the canonical v7.4 label."* Likewise `:1730` Table 1.2 "Canonical 28 Sub-Foundations" contains the artifact's cells verbatim — "Abstract unification of Ideas", "category-level grouping", "Affective synchrony", "Material continuity". **The artifact's TKS fidelity is materially better than a v6.1-only reading suggests.** Four of six lenses made this error before verification caught it.
2. **`CJT` is not absent from this repo.** `all_docx_text.txt` carries **SOP-PO-005: CJT Circuit Analysis** from `Noetic_Compass_Operations_Manual_v2_CAS.docx`. It is a citable in-repo anchor the artifact did not use — see the note under Finding #3.

That this audit fell into the obsolete-manual trap twice is itself evidence for corpus fix **C3** below.

---

## Decisive findings

### #1 — The World-axis question is unresolved inside the owner's own shipped code, and it is the root cause of the artifact's worst section

This is the finding that changes the most, because **it is yours to fix regardless of what happens to the artifact.**

`compiler.py` holds both answers at once — confirmed by execution, not just reading:

| Location | Says |
| :--- | :--- |
| `compiler.py:1214` `META_SET_ALIASES = {"Worlds": "Domains", ...}` | 4 Worlds → **Domains** (P/C/E/O) |
| `compiler.py:1190-1197` `subfoundations` built over `VALID_REGISTERS = ("T","A","f","E")` | 4 Worlds → **Registers** |
| `docs/reference/tks_28_foundations_translation_key.md:47` | Registers authoritative (`\|T Transcendent = 1st World`) |
| Drive doc `cas_forecast_view` (owner's prototype) | "a/P-spiritual, b/C-mental, c/E-emotional, d/O-physical" → **Domains** |

The artifact silently took the Domain horn — its Gate 1 lists "the World-to-Domain adapter" — without naming the conflict. **That single unflagged choice is what forces it to need a `TF` namespace at all**, because under Worlds→Domains, `TF5b` is *not* `F5|A` and has no shipped representation.

**Consequence:** until this is answered, `TF5b` and `F5|A` may or may not denote the same cell, and 280 shipped scenarios are graded on the Register reading while the compiler's `Worlds` keyword returns Domains. Registers and Domains are declared *orthogonal* under v7.5, so this alias currently merges two axes the patent framing keeps distinct.

### #2 — Section 12's entire extension agenda duplicates working, tested code, and its stated premise is false

The artifact writes:

> *"It does not have a native slot for a TKS Sub-Foundation such as `5b`. Therefore the 28 Sub-Foundations cannot be inserted into the current notation without either an adapter or a language extension."*

The state literal **does** have that slot. Executed against the shipped compiler:

```
compile_expression('^8^C_{F5|A}')
 -> StateLiteral(operator=8, domain='C', drive=5, drive_register='A')   warnings=[]

len(BUILTIN_META_SETS['SubFoundations']) == 28
sorted(BUILTIN_META_SETS['Foundation_5']) == ['F5|A', 'F5|E', 'F5|T', 'F5|f']
```

And the world-letter adapter it asks to have built **is already running in production code**: `live-trace-worker/scripts/build_foundation28_scenarios.py:77` ships

```python
REGISTER_TO_LEGACY_WORLD: dict[str, str] = {"T": "a", "A": "b", "f": "c", "E": "d"}
```

and line 170 emits `legacy_foundation_code` — i.e. `F5|A` **is already stamped `5b`** across the 280-scenario library `foundation28_balanced_v0_20260526.json`, with a regression test at `tests/test_build_foundation28_scenarios.py:30`.

`SubFoundations`, `Foundation_1..7`, `SubFoundationSet`, and the alias `DriveRegisterPositions → SubFoundations` are all in the shipped grammar (`compiler.py:177-178`, `1212-1218`).

**Consequence:** an implementer following §12 writes a `foundation_ref ::= "TF" ...` production for objects the compiler already parses, producing a **third spelling** for one position — `F5b` (TKS) / `F5|A` (compiler) / `TF5b` (artifact) — in a document whose own §1 warns against "symbolic soup." This is the largest single item of avoidable spend in the plan.

**Credit where due, graded separately:** the *narrow* claim is correct. `compiler.py:186` publishes `<state> ::= <operator> "^" <domain> ("_{" <drive_ref> "}")?` — genuinely no sub-foundation coordinate, and no register either. But the lexer (`compiler.py:1342`) *does* handle registers and `CO-5^C_{F2}|A` compiles clean. **The artifact is more current than the BNF string it is critiquing.** That stale BNF is corpus fix **C4**.

### #3 — The flagship netlist violates the two laws the artifact calls most important

Three defects in §11, all checkable with no external source:

- **The inference stage runs backwards up the domain order.** `node decomposition: ^6^E_{F6}|A;` → `node conclusion: ^9^C_{F2}|A;` via `cjt infer` is **E → C**, in a netlist that declares `diode d_ce: Diode< ^C -> ^E >;` and follows §10's *"Diodes make that direction structural."* Under CLAUDE.md this is a live **Inversion Axis W** ("Domain precedence violation") hit, produced by the document's most quotable deliverable.
- **Ambition is wired into the answer.** §6 states the document's core safety principle: *"**Ambition may choose the question. It must not choose the answer.**"* §11 then writes `CJT< decomposition | goal_bias => conclusion >` where `goal_bias: ^5^E_{F5}|A`. `β=1.0` constrains *amplification*, not the *bias port*. The in-repo SOP-PO-005 model is explicitly four-terminal — *"Cause (C), Bias (B), Effect (E), and Gain (β)"* — so a unity-gain stage with a goal-derived bias still lets ambition set the answer. The firewall is stated as a gain constraint when it needs to be a **bias-independence** constraint plus an executable test.
- **`action` is an orphan node.** `node action: ^9^O_{F5}|E;` is probed (`probe tp_action`) and is the source of the only feedback edge — but **no `cjt` writes it.** The missing edge is exactly the `|A → |E` conversion §10 singles out as most safety-critical. That same feedback edge runs **O → C** (`action -> memory_bias`) while §4 and Law 4 both promise the canonical **O → P**; `charter_bias` is read but never written. Separately, `output: cas_decision` is declared and never assigned, and `diode d_eo: Diode< ^E -> ^O >` gates a transition that does not exist in the netlist.

**The useful irony:** SOP-PO-005's procedure — *"Present identical inputs through different 'bias' conditions: same question with different framing, context, or authority. Measure gain (β): how much does bias amplify/attenuate output?"* — **is** the sweep test that would enforce the artifact's own firewall. The artifact cited an unavailable PDF for its unity-gain doctrine when a shipped in-repo SOP defines β as framing-sensitivity and hands it the test procedure for free.

### #4 — TF/DF re-opens a question the repo closed in writing

`docs/reference/tks_28_foundations_translation_key.md:41`:

> *"CAS Drive names are authoritative. Where TKS labels use different nomenclature, the mapping is by position in the 7-Foundation sequence, not by label. TKS-specific labels ... are never carried into the CAS v7.5 expression."*

§12 then writes `foundation target_power_strategy: TF5b;` — a TKS label inside a proposed CAS expression.

**Important nuance:** the artifact's *observation* is factually correct — canonical TKS F6 is **Wealth** while CAS F6 is **Structure**, and TKS F7 is **Continuation** while CAS F7 is **Purpose**. The label divergence is real. What the artifact missed is that the translation key already *resolves* it by position. Drop `TF`/`DF`; use `F1`–`F7` and `F5|A`. (Entangled with #1: positional identity of *labels* does not by itself settle whether a Foundation *target* requires a Drive *mixture* — that is a separate and possibly legitimate design claim, and it should be argued as a proposal against the translation key rather than assumed.)

### #5 — Two integration gaps decide whether CCB-R1 is a component or a second platform

`is_admissible` **ships and is enforced** — `cas-engine/src/ontology/operators.rs:110`, `cas-engine/src/python_bindings.rs:59`, called at `compiler.py:1588` and guarded in the algebra. CLAUDE.md **CORRECTION 1** mandates the guard *"before every operator application"* — and every `CJT< src | bias => tgt >` is one. The artifact never engages it. Its `INADMISSIBLE` terminal state is an *episode verdict*, a different concept, with no mechanism behind it — and the name collision will confuse implementers.

Separately, **nothing maps CJT quantities onto `CognitiveStateVector` on Δ39°** (`simplex`, `Fisher`, `probabilit` = 0 occurrences in the artifact). As specified, CCB-R1 cannot be scored by NCCS, cannot be swept by the 7-axis scanner, and cannot be drift-tracked. Fix both and it is an executive layer; leave them and it is a parallel, unscoreable architecture.

### #6 — The Foundation-to-Drive Adapter re-derives v7.6 without its coefficients

`TF5b ↝ DF2 Wisdom + DF5 Agency + DF6 Structure` is a **recipe with the proportional weights removed**. Clarification 9 (`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md:427`) already writes `Θ(Ω) = a₁·X₁ + a₂·X₂ + ...` over exactly these primitives, and `:432` already defines the State Vector `S` that the artifact hand-rolls as `gₘ`/`qₘw`. Because the adapter carries no coefficients, **the Foundation Engine Bank cannot compute a bottleneck** — which is the one thing it exists to do. The artifact never cites v7.5 Registers, v7.6, or v7.7 (`Recipe`, `Yield`, `Limiting`, `Clarification` = 0 occurrences).

**Correctly *not* a duplicate:** the RPM "first insufficient prerequisite → subgoal" loop is *not* v7.6's Limiting Reagent. Clarification 9 §5 explicitly holds sequence and proportion apart (*"Recipe ≠ RPM"*). The artifact is right to keep them separate.

### Lower-tier, one line each

- **Gate 1's "A0 versus A22" should not gate the program.** `A22` = 0 hits across all four TKS texts in the repo. `docs/archive/superseded/TKS_FORMAL_MATHEMATICAL_MANUAL_v6_1_COMPLETE.txt` §2.14 defines `A = {A0} ∪ {Dm} ∪ {Wm} ∪ {Pm}` with `|A| = 22` — **22 is the cardinality, not a symbol.** Most likely a misreading of `|A| = 22`. It remains formally *unverifiable* (it may appear in a missing PDF), but it is uncitable against anything on disk, and `RPM(F5)` emits `chain=['A0 -> D5', ...]` today.
- The netlist's safety-critical `β` values are literal `...` placeholders on both ends of the asymmetry — nothing a compiler could reject.
- The RPM descent has **no depth or progress bound**; infinite subgoal regress is unhandled.
- The four terminal states have **no exit for a D-block** (desire insufficient).
- The anti-scalar claim is unhonoured: §5B rejects *"smashing life into one scalar utility number"*, but the Schmitt commit stage must threshold something scalar, and the 28→1 aggregation is never specified.

---

## What the artifact got right

Credited with the same specificity as the criticism.

**The `^8` / `^6+^9` discipline, made structural.** *"^8 Above/Cause is not deduction. It is associative triggering."* This is the exact drift CLAUDE.md records as having already contaminated compiler code, cas-engine docstrings, and multiple chapters. The artifact does not merely restate the rule — it splits the board into a Hypothesis Generator (`^8`) and a Reasoning ALU (`^6`/`^9`), promotes it to Law 2, and derives a non-obvious failure signature: *"It might be fluent while quietly skipping the load-bearing middle."* **All six lenses credited this independently.** It should survive any rewrite.

**TKS source fidelity better than first scored.** The 28-cell grid and the Foundation labels are canonical v7.4 (Tables 1.1 and 1.2), not invented. See "corrections" above.

**No-new-primitives restraint, in the one place it counted.** *"It does not automatically create new canonical acquisitions named D5b, W5b, and P5b. Those would be an explicit future extension."* That preserves `|A| = 22` and declines an 85-element expansion — exactly the discipline §12 fails to apply to itself.

**Canon-accurate structure elsewhere:** Definition 2.14's 22 acquisitions quoted verbatim; `a=Spiritual, b=Mental, c=Emotional, d=Physical` matching Definition 2.12; `P→C→E→O` with filtered `O→P` matching Domain Descent; every bias node typed `^5` across three Domains — a faithful and non-obvious reading of the "^5 as substrate" doctrine in Clarification 5; the CDAB's *matched gain and shared bias* requirement, which is the correct experimental control. It also uses **CAS** Noetic numbering correctly throughout (`^6` Male for decomposition, `^8` for triggering) rather than importing the superseded v6.1 numbering.

**RPM as first-block recursion, independently defensible.** The `first insufficient prerequisite → subgoal → re-measure → return to parent` loop matches TKS Definition 7.10 / Theorem 7.11 (monadic short-circuit at first failure) and Definition 7.14's diagnostic — so it survives even if the three PDFs are never recovered.

**Calibrated epistemics.** §14's four-way partition with three refusals, the "wrong category" disposal of the physical-substrate question, *"These are design or calibrated quantities, not literal electricity,"* and Gate 5's *"the same-sample circular identity must not be passed off as validation"* are the parts most liftable into external material without exposure. Gate 4's diagnosability criterion — *"The machine must identify the failed stage rather than merely produce a wrong answer"* — is the right success standard and the cheapest high-value next step.

**The lacuna→subgoal move.** Typing an empty CMB region as a W-prerequisite failure converts "I don't know" into a plan. It is what makes `NEEDS_INFORMATION` non-decorative, and it is the most defensible advantage claim over an unstructured LLM pipeline.

---

## Action list

### A. Fix in the artifact (ordered)

1. **Delete §12's `foundation_ref` EBNF.** Cite `compiler.py:1190-1218` and adopt `F{d}|{R}`. Verify with `compile_expression('^8^C_{F5|A}')`. Narrow the residual ask to what is genuinely missing — recursion stack, `policy=first_unmet_recurse`, `return=parent` — layered on the existing `<rpm_call>` production, not a second `RPM` form.
2. **Delete `TF`/`DF`.** Use `F1`–`F7` per `tks_28_foundations_translation_key.md:41`. If many-to-many Foundation→Drive routing is a real design claim, argue it *as a proposal against* the translation key and give it v7.6 coefficients: `Θ(Ω_F5|A) = a·F2 + b·F5 + c·F6 → Ω`.
3. **Rebuild §11.** Retype `decomposition` or `conclusion` so the spine descends monotonically; move `goal_bias` off `cjt infer`; add the missing `cjt` that writes `action` with the `|A→|E` conversion and CSB gate; add `feedback constitutional: action -> charter_bias [β ≤ 0.01, tau=very_slow]` as the canonical O→P path; replace `[β=...]` with constraint intervals a compiler can reject.
4. **Restate the truth firewall as a conjunction**, not a gain value: `β=1` on evaluation **AND** bias-independence from `^6` through `^9` **AND** the sweep test (hold evidence fixed, vary the Foundation profile, assert `conclusion` invariant). SOP-PO-005 already specifies this procedure.
5. **Rewrite Gate 1.** Drop "A0 versus A22" (use `A0`). Restate the World item as the two-sided question with both files named. Add the Definition 2.14 vs Table 14.1 D-index note.
6. **Rewrite Gate 4 as a conformance suite** against the shipped 7-axis scanner (SOP-ID-001): name the axis each ablation should trip — `break P→C→E→O` → **W**; `starve Wisdom` / `overdrive Agency` → **F**; RPM breakage → **A** — and treat ablations with no axis counterpart as candidate scanner gaps. Cheapest high-value work in the plan.
7. **Add the missing integration specs:** an `is_admissible` precondition on every `CJT` edge (and rename the Gate 3 verdict to end the name collision); a readout map from CJT activation to `p_k` on Δ39° with strict `p_k > 0`; an RPM depth/progress bound; a fifth terminal state for a D-block.
8. **Fix citations.** Re-attribute the `^8`/`^6+^9` rule to CLAUDE.md / Clarification 6 (checkable) rather than to an unproducible PDF; cite **SOP-PO-005** for the C/B/E/β model; add a source-availability header naming the three absent PDFs. Promote §14 to the front.

### B. Fix in the corpus — independent of this artifact

These exist whether or not CCB-R1 is ever built.

- **C1 — Resolve the World axis** and write it into `CAS_FOUNDATIONAL_CLARIFICATIONS.md` as a numbered clarification. On the evidence the **Register** reading is better supported (translation key, subfoundation construction, the 280-scenario library, Clarification 8's cross-validation). Then either delete `META_SET_ALIASES["Worlds"]` or re-point it — grep every consumer first — and add a regression test asserting `Worlds == Registers` and `SubFoundations == Drives × Worlds`.
- **C2 — Unblock the translation key.** `tks_28_foundations_translation_key.md:68` says full population *"requires direct access to the TKS 28 Foundations source document."* **That document is already in the repo**: `_tmp_TKS_v7_4_FULL_CORRECTED.txt:1694-1730`, §1.1.1 "The 28 Sub-Foundations (Canonical Grid)" / Table 1.2. A scheduled v7.5 deliverable is blocked on something on disk.
- **C3 — Quarantine or header-warn the superseded v6.1 manual.** `docs/archive/superseded/TKS_FORMAL_MATHEMATICAL_MANUAL_v6_1_COMPLETE.txt` carries Noetic naming inverted relative to canon (`5 Gender (Masculine)` / `6 Gender (Feminine)`, and `2/3` as Above/Below) and the pre-v7.4 Foundation labels (Unity/Material/Lust). v7.4 corrects both (`5 Female / Receptive`, `6 Male / Projective`; Association/Wealth/Continuation). **This audit fell into that trap twice**, and four of six audit lenses mis-scored the artifact because of it. Anyone — human or agent — told to "read TKS as source" will import drift.
- **C4 — File the stale grammar comment.** `compiler.py:186` publishes `<state> ::= <operator> "^" <domain> ("_{" <drive_ref> "}")?` — no register, no drive-register — while the lexer (`compiler.py:1342`) and AST (`StateLiteral(..., register, drive_register)`) both support them.
- **C5 — Log the TKS D-index homonymy.** Definition 2.14 binds `Dm` to Foundation `m`; Table 14.1 "Complete Domain Reference" independently uses `D1`–`D7` for Spirit/Life/Knowledge/Love/Power/Wealth/Expression, which does not line up for `m ∈ {1,2,3,7}`. Inert for the RPM chain (Definition 7.10 fixes the reading), but it will bite someone.

### C. Governance note

The artifact names a product (`CCB-R1`, `CAS-RPU`), proposes language primitives, and carries **no equivalent of the no-new-primitives paragraph** that v7.5/v7.6/v7.7 each carry for USPTO #64/037,173. As an internal design memo that breaks no rule. But `docs/working/cas_v7_7_rollout_plan.md:35-38` gates *"public disclosure of v7.7 beyond current development team"* on IP-attorney consultation. **If any version of the TF/DF framing or the `foundation_ref` production leaves the dev team, route it through the rollout plan and state plainly whether it is notational refinement or primitive introduction.** Treating Foundations as an axis *distinct* from Drives is the specific thing that would read as a new primitive axis — flag it to counsel rather than deciding it in a design memo. (This is risk-flagging, not legal advice.)

---

## Revised verdict on the engineering question

**Yes — a reasoning processor can be specified from CAS components alone, and the artifact's four-way qualification of "pure" is the right answer. But a canon-compliant version reuses roughly half of what this document proposes to build.**

The canon-compliant architecture is the same machine with a different bill of materials:

| Function | Artifact proposes | Should reuse |
| :--- | :--- | :--- |
| Sub-foundation addressing | new `TF` grammar production | shipped `F{d}\|{R}`, `SubFoundations`, `Foundation_1..7`, `SubFoundationSet`; `REGISTER_TO_LEGACY_WORLD` for `a/b/c/d` |
| Foundation→outcome routing | hand-rolled `gₘ` / `qₘw` | v7.6 recipe `Θ(Ω) = a₁·X₁ + ... → Ω`, State Vector `S`, `Y_T = min(xᵢ/aᵢ)` |
| Operator transitions | ungated `CJT<...>` | `is_admissible(operator, source, target)` as a precondition on every CJT edge |
| Fault detection | bespoke Gate 4 ablations | the 7-axis inversion scanner (SOP-ID-001), feeding the 15% Inversion Resistance term |
| Scoring surface | none | `CognitiveStateVector` on Δ39° with strict `p_k > 0`, so NCCS can score it |
| Bias/gain semantics | unavailable PDF | SOP-PO-005's C/B/E/β model and its bias-sweep procedure |

**What is genuinely new and worth building:** the CJT-cascade-plus-RPM-recursion spine; the `^8` / `^6+^9` bank separation; the lacuna→typed-subgoal conversion; the bias-independence firewall (restated as independence plus a sweep test, not as `β=1`); the domain-descent *plus* power-sequencing double protection; and Gate 4's diagnosability standard.

That set is a real architecture. It is also small enough to prototype **against** the existing engine rather than **beside** it — which is the difference between an executive layer and a second, unscoreable platform.

---

## Appendix — audit provenance

- Audit workflow: 6 parallel audit lenses → 6 adversarial refutation agents → 1 synthesis. 13 agents, ~1.64M tokens, 275 tool calls.
- 92 findings survived verification; 29 were refuted and excluded.
- Post-verification severity: 0 critical, 21 major, 49 minor, 22 credits.
- Every finding initially scored critical was downgraded on verification — the artifact has no fatal flaw.
