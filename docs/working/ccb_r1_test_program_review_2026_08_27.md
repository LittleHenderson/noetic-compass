# CCB-R1 Test Program — Review, Additions, and a Working Stage 0

**Date:** 2026-08-27
**Reviews:** the parallel agent's `CCB_R1_TEST_PROGRAM.md` / `AUDIT_RECONCILIATION.md` draft
**Companion to:** `docs/working/cas_pcba_reasoning_audit_2026_08_27.md`
**Ships with:** `scripts/ccb_r1/stage0_lint.py`, two fixtures, `scripts/tests/test_ccb_r1_stage0_lint.py`

---

## 1. Verdict on the draft

**The staging is right and the cheap-first instinct is right.** Stages 0–4 needing no model, no GPU, and no external data is the correct shape: it means the architecture can be falsified before a dollar of compute is spent. The axis-mapped fault injection (Stage 2) and the SOP-PO-005-derived firewall sweep (Stage 3) are the two strongest ideas — both convert audit findings into executable checks.

**One methodological flaw is serious enough to fix before anything is built** (§2 below). Five gaps are worth closing (§3). Stage 0 is real and I have built it (§4).

**On the PDF asymmetry:** the parallel agent reports verbatim verification of the three source PDFs, which I could not locate in either the repo or Drive. I take that at face value and it materially improves coverage — but it means **no single reviewer has seen both halves of the evidence base.** Before Stage 1 freezes any semantics, the three PDFs should land in the repo so the citations are checkable by whoever maintains the tests later. An unreproducible verification is a single point of failure, not a closed gap.

---

## 2. The flaw to fix first: Stage 1 is circular as written

Stage 1 is described as *"the formalization of the book's declared gap"* — the book has syntax for stateful/temporal statements but no semantics — and simultaneously as a test stage with "seven reasoning tasks with golden traces."

Those are two different activities, and running them as one makes the stage unfalsifiable:

> If the same act both **defines** what a CJT computes and **authors** the golden traces that check it, the traces cannot fail. They record the implementation's behaviour, not the specification's requirements. Green means self-consistent, not correct.

This is not pedantry. It is the difference between "our simulator does what our simulator does" and "our simulator does what CAS says it must." Only the second is evidence.

**Fix — split Stage 1 into three artifacts with a barrier between them:**

| | Artifact | Authored from | Must not see |
| :-- | :-- | :-- | :-- |
| **1a** | `CJT_OPERATIONAL_SEMANTICS.md` — what a CJT computes, what bias/gain/cutoff/saturation mean numerically, what a region transition is | the three PDFs + SOP-PO-005 | any simulator code |
| **1b** | the deterministic simulator | 1a only | the golden traces |
| **1c** | golden traces for the seven tasks | 1a only | the simulator |

Then 1b vs 1c is a real test. Where they disagree, either the simulator is wrong or 1a is ambiguous — and **1a's ambiguities are the actual deliverable**, because they are the book's gap made precise. Expect the first run to disagree a lot. That is the finding, not a failure.

The barrier is cheap to enforce: write 1a, freeze it, then generate 1b and 1c independently (different agents/sessions, or the same person on different days with 1a as the only input).

---

## 3. Five gaps worth closing

### 3.1 No baselines — nothing in Stages 0–4 can distinguish "works" from "works better than trivial"

Every stage asks *does CCB-R1 do what CCB-R1 says*. None asks *does the structure buy anything*. Stage 1's ^8-only control is the right idea and should be generalised into a standing baseline set run against **every** behavioural stage:

- **B0 — ^8-only associative chain.** The artifact's own named control. Must fail deduction tasks. If it passes, the task doesn't test deduction.
- **B1 — no-bias ablation.** Should fail to compile (Stage 0 catches it), not silently produce answers.
- **B2 — random-bias control.** Same board, biases drawn at random per run. Quantifies how much of the behaviour is structure vs. accident.
- **B3 — unstructured LLM.** Same tasks, no CAS scaffold. The only baseline that answers the funder's question: *what does the architecture add?*

Without B3 in particular, a fully green Stage 0–4 is a statement about internal consistency and cannot be quoted as evidence of reasoning capability.

### 3.2 Stage 3's headline experiment rewards ignoring evidence

As written: *"hold evidence fixed, vary framing/context/authority and Foundation profile, assert conclusion invariance."*

Two problems:

**(a) It conflates two different properties.** Invariance under **Foundation-profile** variation is the ambition firewall. Invariance under **framing/authority** variation is social-engineering resistance (SOP-SE-001/002). Running them as one sweep means a failure cannot be localised to either. Split into 3A (firewall) and 3B (manipulation resistance) with separate pass criteria.

**(b) Invariance is not always the correct behaviour.** If a perturbation carries genuine evidential weight, the conclusion *should* move. A board that never updates scores a perfect firewall and is useless. The sweep therefore needs two arms:

| Arm | Perturbation | Required behaviour | Failure mode caught |
| :-- | :-- | :-- | :-- |
| **3A-inv** | evidentially irrelevant (framing, requester identity, Foundation profile, register of the request) | conclusion **invariant** | motivated reasoning |
| **3A-sens** | evidentially relevant (a new fact, a retracted premise, a contradicting source) | conclusion **moves, in the right direction** | evidence-blindness / rigidity |

Pass requires **both**. Reporting only 3A-inv would let a stuck board look like a principled one. This is the single most important correction to the experiment as drafted.

### 3.3 The advantage claim is never measured as a rate

Both audits agree the lacuna→subgoal move is the most defensible advantage claim. Stage 1 tests it as a golden trace — a unit test that it fires once. That is not the claim. The claim is a **rate**:

> On questions whose answer is absent from the CMB, what fraction produce `NEEDS_INFORMATION` rather than a confident wrong answer — and how does that compare to B3 on the same items?

Add **Stage 3C — abstention calibration**, with a held-out set of items partitioned into *answerable from memory* / *not answerable*, reporting a 2×2 of (answerable × answered) plus wrong-answer rate on the unanswerable half. Two failure modes to watch, because they trade off: never abstaining (hallucination) and always abstaining (uselessness). Report both arms or the number is meaningless.

This is the most fundable result in the program and currently the least specified.

### 3.4 Stage 2's metric needs a denominator and a false-positive arm

"Score = stage-localization accuracy" is underspecified. A scanner that always reports "stage 3" scores well on stage-3 injections. Specify:

- a **confusion matrix** over (injected stage × reported stage), including a *no fault detected* row and column;
- a **false-positive rate on unfaulted runs** — inject nothing, assert silence;
- **axis-mapping accuracy** scored separately from stage-localization accuracy (getting the stage right but the axis wrong is a different defect).

### 3.5 No kill criteria

"Negatives kept as assets" is the right instinct but is not yet an experiment, because nothing is specified that would stop the program. Before Stage 1, write down what result retires CCB-R1 or forces a redesign. Candidates:

- 3A-sens shows the board is invariant to *relevant* evidence → it is not reasoning, it is a fixed-point.
- B3 matches or beats the board on every behavioural stage → the scaffold adds no capability.
- Stage 1c and 1b cannot be reconciled without repeatedly amending 1a → the semantics are underdetermined; stop and finish the specification.
- Stage 2 localization is at chance → the diagnosability claim, which is the architecture's main selling point over an opaque model, is unsupported.

A program with no kill criterion will always conclude that more stages are needed.

---

## 4. Stage 0 is built, and it works

Shipped in this branch:

```
scripts/ccb_r1/stage0_lint.py                              the linter
scripts/ccb_r1/fixtures/ccb_r1_section11_original.board    the audited netlist, verbatim
scripts/ccb_r1/fixtures/ccb_r1_section11_corrected.board   a conformant rebuild
scripts/tests/test_ccb_r1_stage0_lint.py                   4 regression tests, passing
```

Against the **original** §11 netlist it independently reproduces every hand-found audit finding — 11 findings, 4 critical:

```
[CRITICAL] L-DOMAIN     infer: ascends E->C against domain descent (Inversion Axis W)
[CRITICAL] L-FIREWALL   infer: bias goal_bias is goal-derived (F5 in E-domain)
[CRITICAL] L-ORPHAN     action: declared but no CJT writes it
[CRITICAL] L-OUTPUT     cas_decision: declared output is never assigned
[MAJOR   ] L-BIASDOM    infer: bias goal_bias is E-domain but governs a C-domain target
[MAJOR   ] L-FEEDBACK   learn: targets C-domain memory_bias; canonical path is O->P
[MAJOR   ] L-BETA       learn/intake: gain '...' is not machine-checkable
[MINOR   ] L-DANGLE     conclusion: written but consumed by nothing
[MINOR   ] L-DIODE      d_pc, d_eo: gate edges the board does not have
```

Against the **corrected** board it returns clean. That second result matters as much as the first: a lint nothing can pass is a lint nobody will run.

**Two findings from building it**, both worth carrying into the rest of the program:

1. **The firewall rule is about domain, not drive.** My first version flagged `charter_bias` (`^5^P_{F7}|T`) as goal-derived because it carries F7 Purpose. That is wrong — F7 in the **Principled** domain is a charter, the legitimate governor of an evaluation stage. Ambition and principle are distinguished by the *domain* coordinate, not the drive. Stated as "no F5/F7 bias on evaluation," the rule is a false-positive generator; stated as "no F5/F7 bias **outside the Principled domain**," it is correct. The regression test pins this.
2. **`...` passes a naive numeric check.** `[0-9.]+` matches `...` because `.` is inside the character class, so a placeholder gain silently validated as a number before crashing on `float()`. Pinned by test. Trivial, and exactly the kind of thing that would have made a "green" Stage 0 meaningless.

Run it:

```
python3 scripts/ccb_r1/stage0_lint.py scripts/ccb_r1/fixtures/ccb_r1_section11_original.board   # exit 1
python3 scripts/ccb_r1/stage0_lint.py scripts/ccb_r1/fixtures/ccb_r1_section11_corrected.board  # exit 0
python3 -m unittest scripts.tests.test_ccb_r1_stage0_lint                                       # 4 tests OK
```

**Scope honesty:** this linter parses the board layer with its own regex parser and calls the shipped compiler only to validate the CAS state literals. It does no semantics. That is the correct division of labour for Stage 0 — and see §5 for why the board layer is not the compiler's job yet.

---

## 5. Does the CAS compiler need upgrading?

**For the state algebra: no. Verified by execution, not reading.**

| Capability | Status |
| :-- | :-- |
| `compile_expression('^8^C_{F5\|A}')` — sub-foundation-pinned state | ✅ compiles today |
| `SubFoundations` (28), `Foundation_1..7`, `SubFoundationSet` | ✅ ship |
| `DriveRegisterPositions` → `SubFoundations` alias | ✅ ships |
| `is_admissible` (CORRECTION 1) | ✅ enforced in cas-engine + compiler |
| v7.6 recipe semantics — `Θ`, recipe, yield, leakage, inhibitor, efficiency, production_target | ✅ already first-class |

That last row matters for the test program: the Foundation→Drive adapter needs **zero** compiler work. Recipe notation `Θ(Ω) = a₁·X₁ + … → Ω` is already a construct, so Stage 1's 28-lane arbitration can be expressed in shipped notation rather than invented.

**For the board layer: nothing to upgrade, because it was never there.** `board`, `cjt`, `CJT`, `diode`, `probe`, `feedback`, `Diode` all occur **zero** times in `compiler.py`. The netlist language is a separate front-end that does not exist in this repo. Two options:

- **(a) Extend the CAS compiler** with board productions.
- **(b) Keep the board layer as a separate front-end** that emits CAS expressions and calls the compiler to validate them.

**Recommend (b), at least through Stage 4.** Three reasons: it leaves the patent-sensitive core untouched (no new primitives in the topos — the exact posture v7.5/7.6/7.7 each preserve for USPTO #64/037,173); it is cheap, as the working linter shows; and the board layer's semantics are precisely what Stage 1 is supposed to discover. Freezing a grammar around semantics you have not yet pinned down is how the §12 mistake happens a second time. Promote to (a) once 1a is stable and the board language has stopped changing.

**Two genuine compiler changes the audit did surface,** neither a capability upgrade:

1. **`compiler.py:186`** — the published `state`-literal BNF is stale, omitting the register and drive-register coordinates the lexer accepts. Documentation fix.
2. **`META_SET_ALIASES["Worlds"] = "Domains"`** — this one is blocked on a decision, not on code. Resolving the World axis toward Registers means deleting or re-pointing the alias, which **is** a breaking compiler change for any consumer using the `Worlds` keyword. Grep consumers first, then change with a regression test asserting `Worlds == Registers` and `SubFoundations == Drives × Worlds`.

---

## 6. Sequencing

The draft ends by asking whether to fix the action list first or review the program first. Neither, quite — **one decision gates both**, and it is cheap:

> **Resolve the World axis (audit item C1) before Stage 0 runs on anything but the fixtures.**

Stage 0's `F{d}|{R}` requirement silently encodes the Register reading. If the corpus later rules Worlds→Domains, every board written against Stage 0 is mis-addressed and the 280-scenario library disagrees with the compiler's own `Worlds` keyword. This is a one-paragraph decision in `CAS_FOUNDATIONAL_CLARIFICATIONS.md`, and the evidence favours Registers.

Then, in order:

1. **C1 World-axis decision** — one paragraph, unblocks everything.
2. **Apply the audit action lists** — rebuild §11 (a conformant board now exists as a fixture), drop TF/DF, restate the firewall as the conjunction, add the fifth terminal state for a D-block.
3. **Run Stage 0 against the rebuilt board**, in CI.
4. **Write 1a (`CJT_OPERATIONAL_SEMANTICS.md`) and freeze it** — the barrier in §2. This is the long pole and the real intellectual work.
5. **Then 1b and 1c independently**, plus baselines B0–B3.
6. Stage 2 with the confusion matrix; Stage 3 split into 3A-inv / 3A-sens / 3B / 3C.

Kill criteria (§3.5) get written at step 4, before any behavioural data exists. Preregistration after the fact is not preregistration.
