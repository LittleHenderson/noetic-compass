# DIRECTIVE — SELF-INSTANTIATING TKS NOETIC COUNCIL FOR HELM DEVELOPMENT

**Directive ID:** HELM-TKS-RPM-001
**Status:** ACTIVE, implemented, and exercised on real HELM work. Not a proposal.
**Owner:** Little Henderson (Wakil; Prof. Hermes M. Thoth). All decisions are his.
**Written:** 2026-10-16 PDT, by the council's first operating session.
**Authority:** the owner's directive of 2026-10-16 plus its architecture extension (RPM integration).

This document is the standing instruction. It tells any agent working on HELM what the council
is, where its machinery lives, how to run it, what has been verified and what has not, and when
to use it at all. Read it before investigating a complex HELM problem as a single agent.

---

## 1. What the council is

HELM work is not solved by one agent thinking alone. It is solved by a council of **ten seats,
one for each canonical TKS Noetic**, driven by the **canonical TKS Recursive Prerequisite Model
(RPM)**, with the **40 Elements** activated only when a problem needs finer resolution.

The ten seat definitions are verbatim from the Tootra Math Handbook and are not renameable,
rephraseable or softenable. The authoritative text is
`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 1. Every seat's definition is
assert-checked against that table by the machinery, character for character, at import time. A
seat that drifts fails loudly instead of quietly.

**The council is one council.** The ten members persist across tasks and across loop turns. They
are not re-created per task and not duplicated per candidate.

## 2. The loop, exactly

The owner's loop, which the machinery implements in this order:

1. **Target outcome** — what is HELM trying to accomplish.
2. **RPM diagnosis** — which required conditions are satisfied, missing, uncertain, or blocking.
3. **TKS Noetic Council** — the ten operations investigate the identified blocker. Each seat uses
   its canonical operation, not an invented definition.
4. **Conditional Element analysis** — activate the relevant TKS 40 Elements when deeper
   resolution is needed.
5. **Resolve and verify** — implement, test, update the prerequisite state. RPM re-evaluates the
   target; if another condition blocks it, the council investigates again.

**The loop is the point.** The council does not discuss a bug and hand back an answer. It keeps
working the specific unmet conditions until the outcome is reached or exactly why it cannot be is
established and written down.

## 3. Where the machinery lives

| What | Path |
|---|---|
| The council loop and the seats | `C:\Users\wakil\Documents\Codex\2026-10-16\noetic_loop\council_loop.py` |
| The RPM engine of record | `C:\Users\wakil\Documents\Codex\2026-10-16\rpm_council_work\H_c8\engine.py` |
| The engine's own suite | `...\H_c8\test_rpm.py` (40 tests) |
| Engine selection rule | `...\noetic_loop\target_engine_repair.py` `select_candidate()` |
| Target: the engine's own repair | `...\noetic_loop\target_engine_repair.py` |
| Target: HELM-R1 wave 1 | `...\noetic_loop\target_helm_r1_wave1.py` |
| Loop runners | `...\noetic_loop\run_loop.py`, `run_loop_helm_r1.py` |
| The record of every turn | `...\noetic_loop\journal\LOOP_JOURNAL.jsonl` and `LOOP_ITERATION_NNN.json` |
| The seats' reports | `...\noetic_loop\seats\CO0_IDEA.md` … `CO9_BELOW_EFFECT.md` |
| The record writer for wave 1 | `...\noetic_loop\write_r1w1_record.py` |
| The run backup with three confirmations | `...\noetic_loop\backup_r1w1_wave1.py` |

**Interpreter:** `C:\Python314\python.exe`, always with `-B`. Each script states its own usage.

## 4. The two halves, and why both are needed

The council runs in **two halves**. Both are required, and neither substitutes for the other.

**The machine half.** `council_loop.py` holds the ten seats and their canonical definitions, the
canonical stage-to-Noetic activation map, the 40 Elements, and the anti-drift checks. It runs the
RPM diagnosis over a declared prerequisite graph and emits a **work order**: the blocker, the
stage, the seats the canon activates, the Elements when they are needed, the frontier (where the
failure physically is), and the journal record. Its output is deterministic and re-runnable.

**The independent half.** For each real problem, the orchestrator spawns **ten genuinely
independent agents**, one per Noetic, each given the same problem and evidence and each required
to investigate alone before any other seat's conclusion is exposed. They cannot see each other's
work. Their reports are written to `seats/` and returned to the orchestrator, which is the only
channel between them.

**This distinction is not cosmetic and must never be blurred.** The machine half is
deterministic reasoning about a declared graph. The independent half is ten separate reasoning
contexts that can genuinely surprise each other. When independent agents cannot be spawned, the
council may be run as ten separately maintained reasoning contexts, and that fallback **must be
stated as a fallback** in the report. It must never be described as independent agent execution.

## 5. The 10 seats

Each seat's operation is its canonical definition read as a directive, and nothing else.

| Seat | Noetic | Canonical definition (verbatim) | That seat's operation | Colloquialism |
|---|---|---|---|---|
| 1 | CO-0 Idea | All things in and outside the Mind. | ENUMERATE WHAT THERE IS. Report the full set of Ideas in scope without selecting by relevance or by the outcome already wanted. | "It's all in your head." |
| 2 | CO-1 Mind | Various degrees of awareness that processes, stores, outputs, and intakes Ideas. | MAP AWARENESS. Report what is processed, stored, output, intaken, and the degree of awareness each stands at. | "Paying attention." / "Making up your mind." |
| 3 | CO-2 Positive | An Idea the Mind has an affinity for and is attracted toward. | FIND THE ATTRACTION. Report what the target has affinity for and is attracted toward — what it is trying to reach. | "Drawn to it like a moth to a flame." |
| 4 | CO-3 Negative | An Idea the Mind is adverse to and repelled by. | FIND THE REPULSION. Report what the target is adverse to and repelled by, **as aversion, not as critique**. | "Can't stomach it." |
| 5 | CO-4 Vibration | The degree to which an Idea resonates with the Mind, its impression. | MEASURE THE IMPRESSION. Report the magnitude of the effect, not its direction. Cost, latency, size, count. | "Hit me hard." / "Struck a chord." |
| 6 | CO-5 Female | A Mind impregnated with an Idea, the Ideas a Mind is composed of. | READ THE ACCUMULATED SUBSTRATE. Report what the blocker is composed of and what history it carries. | "We are the sum of our experiences." |
| 7 | CO-6 Male | An Idea impregnated with another Idea, the Ideas an Idea is composed of. | DECOMPOSE. Take the blocker apart into the Ideas it is composed of and name which part owns which fault. | "Unpacking an idea." / "Breaking it down." |
| 8 | CO-7 Rhythm | The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it. | READ THE EXPOSURE PATTERN. Report the rate and repetition of the failing exposure and what it has entrained. | "Practice makes perfect." / "Muscle memory." |
| 9 | CO-8 Above/Cause | An Idea that triggers a different Idea than itself to come to Mind. | TRACE THE TRIGGER. Report which Idea brings which other Idea to Mind, **as triggering, not as deduction**. | "That reminds me…" |
| 10 | CO-9 Below/Effect | The Idea brought to Mind by an Above/Cause trigger. | REPORT WHAT LANDED. Name the terminal effect actually brought to Mind, with its measured value. | "It just popped into my head." |

### The two anti-drift rules that are enforced by a program

These are the drift patterns this project has been bitten by before. They are checked, not merely
advised. `council_loop.check_seat_report(noetic, text)` returns the offending words.

- **CO-3 Negative is VISCERAL, not analytical.** "Audit", "scrutinise", "find the flaws",
  "critical evaluation", "assess the quality" are drift. Analytical work belongs to CO-6 Male.
- **CO-8 Above/Cause is associative TRIGGERING, not analytical reasoning.** "Therefore",
  "deduce", "it follows logically" are drift. Deductive causal analysis is a compound of CO-6 and
  CO-9, not CO-8.

Every report that returns from a seat must be checked against these before it is used.

## 6. The 40 Elements, and what they are not

**10 Noetics × 4 Worlds = 40 Elements.** The 4-Worlds axis is reframed in CAS v7.5 as the four
Phenomenological Registers — Transcendent `|T`, Analytical `|A`, Affective `|f`, Embodied `|E`
(Clarification 8). Element notation is `^n|R`.

**The Elements are NOT 10 Noetics × 4 Domains.** The cross-product with P/C/E/O is the **40
Cognitive States**, which is a different thing. Substituting one for the other is exactly the
error this project has a history of; the machinery generates the Elements and assert-checks them
against 40 and against both axes so the substitution cannot happen quietly.

**They are not 40 extra agents, and the directive says not to spawn them as such.** The
implemented choice is the fourth of the four options the directive offered: the Elements are a
**deeper, interconnected reasoning layer the council navigates**, activated conditionally and
only when a stated reason justifies it. `council_loop.elements_needed()` returns the reason on
every turn, and the reason is journalled. Elements fire when:

- the blocker is `UNKNOWN`, `CIRCULAR`, `DEPTH_EXCEEDED` or `DELIBERATION_EXHAUSTED` — that is,
  not a plain shortfall; or
- the same condition blocked the target on an earlier loop turn; or
- the blocker sits at recursion depth > 0, below the target.

An activation is reported with its register definitions, never as a bare list of symbols.

## 7. RPM, as implemented

The engine implements the canonical four-stage chain per condition. Stage meanings:

| Stage | Meaning |
|---|---|
| `A0` | does this condition need to exist for the target at all |
| `D` | is the condition UNDERSTOOD and specified |
| `W` | is there a committed MECHANISM that can satisfy it |
| `P` | is it ESTABLISHED by evidence |

**The canonical distinction the engine preserves, and the whole reason it exists:** a
prerequisite being **genuinely satisfied**, being **assumed satisfied**, and remaining
**unknown** are three different states, and the engine never collapses them. An assumed
prerequisite surfaces as `ASSUMED`, distinct from `SATISFIED`. Triage is three-valued: a reading
that cannot be taken returns `ok=None`, which **blocks** the gate rather than passing it.

**Section-retraction, not adjunction.** Prerequisite satisfaction is **one-directional**. ε∘η = id
but η∘ε ≠ id. The engine must not assume reversibility, and a repair must not make it.

**Recursive operation.** When the blocking condition has its own prerequisites, they are
investigated recursively by the same rules. The diagnosis returns the **frontier** — the leaves
of the tree, deepest first — which is where the failure physically is. The canon activates the
council on the root's stage; the frontier is reported beside it, because a council told only
"the target is blocked at D" has to guess while a council told which named check failed does not.

### Safeguards, and which of them are genuine RPM and which are engineering

This distinction is required by the directive. Both are listed, separately.

**Genuine canonical behaviour:** the cycle report (a cyclic prerequisite graph is reported as a
blocker, never iterated and never crashed); the three-valued evidence states; one-directional
gating; A0 ungated; the contradictory-prerequisite report.

**Engineering safeguards added for software reliability:** S1 the depth cap; S2 the walk's path
guard; S3 the repeat guard for a condition already diagnosed in this run; S4 the deliberation
cap; S5 the explicit stack in the cycle walk. These exist so the machine cannot hang, recurse
forever, or re-diagnose the same unresolved condition; they are not RPM rules and must not be
presented as such.

**Measured honesty about the fixes.** On the engine of record (`H_c8`, sha256
`64c957e948a7754c6c4e8175b07299188a5892e75952b87e36d2d9b0847022ba`), ablation A2 showed the S2
path guard can be **deleted** with the suite still green and the cycle probe still true. It was
**measured and deliberately not deleted**, because it is what makes the diagnosis tree say where
the walk re-entered. That is recorded rather than quietly cleaned up.

**Known limit, unfixed and stated:** `evaluate_condition` has no depth bound of its own. Measured
on the engine of record: a forward chain of 1500 and a ring of 2000 both raise `RecursionError`
with 997 frames. S1 bounds `_diagnose` only. This is pre-existing, was not introduced by the
repairs, and no current target reaches it. Do not claim it is fixed.

## 8. How to run one turn

```
C:\Python314\python.exe -B <noetic_loop>\run_loop.py              # the engine's own target
C:\Python314\python.exe -B <noetic_loop>\run_loop_helm_r1.py      # the HELM-R1 target
```

Each turn prints, in order: the target outcome, the ten seats, the engine of record and the rule
that selected it, the RPM diagnosis (blocker, condition, blocked stage, evidence there, recursion
depth, and the frontier), the seats the canon activates for that stage **and** for the stage that
physically failed, the Elements with their activation reason and register definitions, and the
journal path. It writes `LOOP_ITERATION_NNN.json` and appends to `LOOP_JOURNAL.jsonl`.

**One turn is steps 1–4.** Step 5 — resolve and verify — is the seats' work, done outside the
script, and the loop's **next** turn measures whether it landed. That is the feedback loop
working: nothing is called resolved until a re-diagnosis says the condition moved.

**Adding a new target is adding a module**, not editing the council. A target module supplies
`task()` returning `target_id`, `target_statement`, `threshold` and a `conditions()` callable
returning `RequiredCondition` objects. Every reading inside must be a **program reading**: it
names the exact file, command or check that produced its value, and no number is typed by hand.
`target_helm_r1_wave1.py` is the worked example, and it is written to be copied.

## 9. When to activate the council, and when not to

**Do not run the ten-seat process on trivial operations.** Simple, low-risk edits get ordinary
execution.

**Activate it** for: complex reasoning problems; persistent defects; architectural decisions;
ambiguous failures; anything where independent perspectives could materially change the result;
and any task that has failed repeatedly.

**Once activated, the council decides whether the Elements are necessary** — not the
orchestrator's habit. The reason is journalled every turn.

**Prevent endless discussion.** When the evidence is sufficient, converge, implement, and verify.
The deliberation cap and the repeat guard exist to make that mechanical rather than a matter of
willpower.

## 10. The verification rule for anything the council implements

A resolution is not resolved because the council agreed. It is resolved when a **program-emitted
reading** says so, with frozen thresholds, and the loop's next turn confirms the condition moved.

- Claim status comes from a deterministic program reading, never from prose.
- A claim may not be widened beyond the reading's own words.
- **Never delete a negative result.** Disconfirmations are load-bearing product assets.
- A failed hard gate stays failed. It is not "PASS with caveats".
- Every number stays exact — never rounded, never paraphrased.
- Where a reading could not be taken, say so; do not substitute an estimate.

**Independent verification is a seat's job, not the orchestrator's.** When work is implemented,
at least one seat is re-tasked to try to **falsify** it rather than confirm it: re-hash every
number against its source, check nothing was deleted, and check the claim is no wider than the
reading's own words. Its verdict is reported as it returns, including when it disagrees.

## 11. Standing safeguards against the council's own failure modes

- **Infinite recursion** — S1 depth cap; S4 deliberation cap.
- **Repeated diagnosis of the same unresolved condition** — S3 repeat guard; a repeat is escalated
  to the Elements instead of silently re-run.
- **Circular dependencies** — the cycle report; measured on rings of 1 to 9 nodes and on rings of
  120 and 900.
- **Unproductive deliberation** — the caps above, plus the rule that when the evidence is
  sufficient the council converges and implements.
- **Silent drift of a seat from its canonical definition** — import-time assert against the
  authoritative table, plus the executable anti-drift checks.
- **A reading that cannot be taken being treated as a pass** — `ok=None` blocks the gate.
- **Confusing the machine half with the independent half** — they are reported separately and the
  fallback is always labelled as a fallback.

## 12. Reporting to the owner

Every council report to the owner uses the owner's colour scale and ends with the owner's
required sign-off lines.

**Colour scale:** ✅ done and verified · 🟩 a frozen mark met · 🟨 ahead but not by the frozen
rule · 🟧 partial or mixed · 🟥 a frozen mark missed, kept forever · ⬜ not run · 🔧 building ·
🔒 frozen.

**Every update ends with, in this order:**

```
🎁 FOR WAKIL TO DO: (what he must do, or "Nothing right now.")
🚀 NEXT: (what is next in the project process)
🎉 WHAT IS CURRENTLY HAPPENING: (a run, a test, a build, or "Nothing is running.")
```

**Plain English is permanent.** Lead with the outcome. Short sentences, one idea each. Define
jargon on first use. Separate what was measured from what was inferred from what is not known.
Keep every literal exact. Ask him only for new money, irreversible steps, a new experiment line,
or a real research choice.

## 13. What is verified, and what is not

**Verified, with its reading:**

| Claim | Reading |
|---|---|
| The engine is canon-faithful on its own suite | 40 tests, 0 failures, 0 errors; 4 of 4 canonical probes pass |
| A cyclic prerequisite graph is reported at the target | `canon_probe_cycle_at_target` true; rings of 1–9, 120 and 900 nodes all read `CIRCULAR` |
| The section law holds | ε(η(s)) = s on 1001 values, 0 violations |
| Gating is one-directional | measured `[True, True, False, False]`, depth 2, completeness 0.5 |
| A0 is not gated | root satisfied true, prerequisite_satisfied true |
| The 40 Elements are 10 Noetics × 4 Worlds | generated and assert-checked at import |
| The seat definitions match the canon | character-for-character assert against `rpm.NOETICS` |
| The anti-drift checks fire on drift and stay silent otherwise | 5 exercised cases, all as expected |
| The loop closes on a real target | `LOOP_JOURNAL.jsonl`: iterations 8–9 blocked, iteration 10 `SATISFIED` |
| The council corrected its orchestrator | five corrections by five seats in one turn, each verified against the bytes |

**Not verified, and stated so that nobody assumes otherwise:**

- The council has been exercised on **two** targets. That is not coverage of the class.
- The `evaluate_condition` depth limit above remains unfixed.
- The Elements are implemented as a **conditional reasoning layer**; the other three options the
  directive offered — Elements as dynamically activated subagents, as a diagnostic vocabulary, as
  a navigable layer — have **not** been compared against it experimentally. The choice was made on
  the directive's own reasoning and the project's history, not on a measurement.
- The independent half depends on a spawn capability existing. Where it does not, the fallback
  applies and must be labelled.

## 14. Amendment log

| Date | Change |
|---|---|
| 2026-10-16 | Written. The council's first operating session: engine of record established at `H_c8`; two targets defined; ten independent seats run on the HELM-R1 blocker; find section 7.47 and the four stranded sections 7.40–7.43 recorded in the living master record; the wave-1 run backed up with three confirmations. |
