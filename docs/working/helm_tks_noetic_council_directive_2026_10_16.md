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

## 12. False-positive resistance: the failure this project keeps repeating

**A check that looks for a token instead of measuring the thing will pass falsely, and it will pass
falsely silently.** This is not a hypothetical. In one session the council found five instances of
it, and two of them were in the council's own code.

### The five, with their harmless-looking code

| # | the check | what it actually did | what made it true when it should not have been |
|---|---|---|---|
| 1 | the R1-RT gate reading searched the plan folder for the string `R1-RT` | found **four documents that merely mention R1-RT** | `WAVES.md` contains that string and sits in the same folder, so **filesystem walk order alone** could have flipped the gate to satisfied with **no byte changing** |
| 2 | the bridge reading searched for files named `bridge`/`adapter`/`host_` | matched `cncm_bridge.py` | that file is **INERT** — it grants `INERT_PROPOSAL_ONLY_NOT_ADMITTED_BY_CURRENT_CNCM` and imports no kernel — and it matched a **name search** |
| 3 | the same reading's second attempt accepted `host_summary.py` | read it as an adapter carrying the recipe brain | it is a **test harness** that merely mentions the word |
| 4 | a job supervisor tested for the stage's declared outputs at the stage output root | sealed a **clean run as FAIL** | the runner keeps artefacts one directory down (`out/r1w1_out/`), so the file it called missing was present and hash-matching |
| 5 | a controller recorded `IdempotentParameterMismatch` as "launch refused" | reported that no instance was created | the instance **was running** and billed for **297 seconds** |

Each was written by someone who believed the check measured the thing it named. None of them threw.
Every one produced a green or a red that was wrong.

### The rules that follow, and they are not optional

1. **A reading must open the artefact, not count its name.** If a condition says an adapter exists,
   the reading opens the candidate and asks what it does. If a condition says an approval exists, the
   reading demands an **admission phrase**, not a mention of the subject.
2. **A mention is never a gate.** Report mentions **as mentions**, with their count and their
   filenames, so the reason a reading is unsatisfied is visible rather than implied.
3. **`ok=None` blocks.** A reading that cannot be taken blocks the gate. It never passes, and it is
   never quietly skipped. This is the one rule that has held throughout.
4. **A half-met condition is not a met condition, and the reading must say which half is absent.**
   The R1-RT gate reading is the worked example: *"HALF MET, HALF ABSENT. W1's reading exists and is
   licensed, so that half is met. 5 document(s) MENTION R1-RT and NONE of them is an approval."*
5. **Every reading names its own source**, so anyone can re-run it. A reading nobody can re-run is a
   guess wearing a filename.
6. **When a check is repaired, the repair is proved by re-running it against the case that fooled
   it.** Fixing the code is not the proof; showing the old input now fails is.

### What to do when you find one

- Fix the reading, and state in the commit what it used to return and what it returns now.
- **Keep the old behaviour visible in the code as a comment**, so the next agent does not "simplify"
  it back into the false positive. Items 1 and 2 above carry exactly such comments.
- If the false positive produced a record, **correct the record** — a second erratum is cheaper than
  a wrong claim, and this project keeps its errata on the page rather than editing history.

## 13. Portability: what runs where, and what it reads

The council was built on this machine, so its paths are this machine's paths. That is worth stating
plainly rather than discovering later.

### The machinery is portable

Measured by copying eight files into an empty folder — no journal, no seats directory, no
environment — and running the loop there: **it runs, writes its own journal, and reaches the same
diagnosis.** The eight files are `council_loop.py`, the three `run_loop_*.py` runners, the three
`target_*.py` modules, and `verify_r1_rt_rules.py`.

**A reading that names a path on this machine is not portable; a reading that names a record is.**

### The rule this produced, now enforced in the code

`RT_SPECIFIED` originally listed a **hard-coded worktree directory** to find the R1-RT design. The
design is **committed** to `origin/claude/project-thread-pmbzd6`; the worktree was only where it was
written. Had that worktree been removed, the reading would have reported **"no design" while the
design sat on the branch** — wrong about the one thing it names, which is exactly what section 12
forbids.

It now reads the live branch through `git show <branch>:<dir>` and falls back to disk only when git
cannot be reached, and its detail says **which source was used**. The rule generalises: **prefer
the record to the path.**

### What each target reads, and where it breaks elsewhere

| target | what it reads | portable? |
|---|---|---|
| `ENGINE_CANON_FAITHFUL` | the engine candidates under `Documents\Codex\2026-10-16\rpm_council_work\` | **no** — it is a repository of the engine's own repair history, and it is this machine's |
| `HELM_R1_WAVE1_DONE` | the frozen reader's verdict, the run receipts, the AWS ledger, and the live record through `git show` | **partly** — the record half is portable; the verdict and receipts are files this machine holds |
| `HELM_R1_RT_HOSTED` | the runtime source, the recipe brain package, `WAVES.md`, and the design on the live branch | **partly** — the design and the plan are portable; the runtime and package are disk copies |
| any Run reading | the run's own receipts by path | **no** — a receipt lives where it was written |

**None of this is a defect to fix now.** It is a limit to state, because a future agent on another
machine will otherwise read a green reading and believe it.

### A junction that copies into infinity

Measured while backing up the working record, and recorded because naive tooling walks straight
into it.

**`rpm_council_work\E_c5\rpm_council` is a directory junction whose target is `E_c5` — its own
parent.** It was left behind by an earlier session's copy step. Following it nests `rpm_council`
inside itself without end.

What that did: `shutil.copytree` followed it, **left 121 directories in the archive**, and then died
with `WinError 1921` when the path passed the Windows limit. The backup's own tree scan had also
reported a suspiciously long path, which is what pointed at it.

**The rule that follows: prune reparse points, never follow them.** A backup or a tree scan must skip
junctions and symlinks and **say how many it skipped**, because a pruned link means the backup does
not contain that subtree and a reader of the manifest is entitled to know. The three trees now back
up as 56, 148 and 4 files with the junction pruned and counted, and the engine hashes in the manifest
match the loop journal's recorded `engine_sha256` exactly — which is how the backup proves it copied
the right bytes.

**This is also why the council's working record was not already backed up safely.** Wave 1's run was
backed up; the machinery, the seat reports and the journal were not, and a naive copy of them fails.

### What lives only on this machine, and matters

- the engine of record and the candidates it was selected from,
- the wave-1 verdict, its receipts, the supervisor receipt, and the AWS ledger,
- the runtime source and the recipe brain packages,
- the seat reports under `noetic_loop\seats\`,
- the loop journal.

The wave-1 **run** is backed up at `D:\tksCAS-archive\helm_r1_w1_c34g_20261016\` with three
confirmations, and that backup is the durable copy of the result. The rest has no backup, and that
is recorded here rather than assumed away.

## 14. Reporting to the owner

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

## 15. What is verified, and what is not

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
| The council runs from a fresh checkout | eight files copied into an empty folder: the loop ran, wrote its own journal, and reached the same diagnosis |
| The R1-RT input rule matches the runtime's own oracle | 20,000 random and 98,304 exhaustive cases, 0 disagreements |
| The R1-RT output rule survives the decoder's arithmetic | 4 constants x 8 labels, 32 of 32 correct, and the all-zero trap demonstrated |
| The two halves of R1-RT refuse each other | `runtime.py:9` is an unguarded `import torch` and 17 of 34 runtime files import it; `rb/no_torch.py` refuses a process already holding torch and raises on install. Both import orders fail |
| The runtime cross-checks the brain's routing | `runtime.py:1011-1025` compares three telemetry fields with `torch.equal` against the materialized route and raises on mismatch |

**Not verified, and stated so that nobody assumes otherwise:**

- The council has been exercised on **two** targets. That is not coverage of the class.
- The `evaluate_condition` depth limit above remains unfixed.
- The Elements are implemented as a **conditional reasoning layer**; the other three options the
  directive offered — Elements as dynamically activated subagents, as a diagnostic vocabulary, as
  a navigable layer — have **not** been compared against it experimentally. The choice was made on
  the directive's own reasoning and the project's history, not on a measurement.
- The independent half depends on a spawn capability existing. Where it does not, the fallback
  applies and must be labelled.

## 16. Amendment log

| Date | Change |
|---|---|
| 2026-10-16 | **Section 12 added: false-positive resistance.** Five instances of one failure were found in a single session — a check that looks for a token instead of measuring the thing — two of them in the council's own code. Four of the five: the gate reading that matched mere mentions of R1-RT and could have flipped on filesystem walk order; the bridge reading that matched an INERT stub by filename; the supervisor that sealed a clean run FAIL for looking one directory too high; the controller that recorded "launch refused" for an instance that was running and billed for 297 seconds. The rules that follow are now standing: open the artefact rather than counting its name, report mentions as mentions, treat `ok=None` as blocking, state which half of a half-met condition is absent, name every reading's source, and prove a repaired check by re-running it against the input that fooled it. |
| 2026-10-16 | **Section 13 added: portability.** The council runs from a fresh checkout (measured), but several readings name paths on this machine. The rule that follows is enforced in the code: `RT_SPECIFIED` now reads the design from the live branch through `git show` rather than from a hard-coded worktree path, because the design is committed and the worktree was only where it was written. Prefer the record to the path. |
| 2026-10-16 | **Junction hazard recorded** in section 13: `rpm_council_work\E_c5\rpm_council` is a junction targeting its own parent, and following it made `shutil.copytree` leave 121 directories and die on the Windows path limit. Reparse points are now pruned and counted, never followed. The council's working record is backed up with three confirmations at `D:\tksCAS-archive\noetic_council_20261016\`, and the manifest's engine hashes match the loop journal's recorded `engine_sha256`. |
| 2026-10-16 | **Route D measured from inside the runtime, not from outside it.** One call to the runtime's own `_prepare_inference` — the method containing the brain call at `runtime.py:1006` — returned `_PreparedInference` against the patched copy, with the real CASformer. The operation bank received exactly one case and it was the runtime's own content, `case_id='probe-tick'`. Both holders were empty afterwards. The negative control — the same path through the old three-argument signature — gave the bank `None` while the bank still ran, so the probe can tell delivering from not delivering. Peak 220.5 MiB of the 300 MiB laptop rule. |
| 2026-10-16 | **The case arrives as a `mappingproxy` with tuple values**, measured rather than assumed: `case_id=str`, `edges=tuple`, `nodes=tuple`, `route=tuple`, `task_id=str`. It is read-only and `edges` is `((0, 1),)` rather than `[[0, 1]]`. Any operation that mutates it or calls `.append()` on it will fail. Recorded in appendix D section 5. |
| 2026-10-16 | **Three defects in the runtime-path probe, all three found by running it, all three recorded rather than quietly fixed.** The unpatched-detector asked whether the bank had `_active_case` as a class attribute — it does not, the bank creates it at call time — and so aborted a good run. The node's "was it cleared" check sampled the holder before `network.forward_node`'s `finally` ran, and falsely accused the patch of leaking it. The negative control asserted a sentinel for a missing argument that the patched node can never produce, because it always passes its holder down as an explicit `None`. |
| 2026-10-16 | **Route D's central assumption falsified by measurement, and recorded as appendix E rather than quietly dropped.** The design assumed the sealed recipe brain could be hosted in the runtime's own process. It cannot: `rb/__init__.py` installs a blocker on import whose `install()` raises if torch is already loaded, and once installed the blocker refuses any later `import torch`. **All four import orders were refused**, each run in its own subprocess, and `numpy` rides in with torch so there is no partial order. Route D as designed is not buildable. The refusal is not an obstacle to route around: it is how the brain's own run is shown to be torch-free, and the package is frozen. HELM's own `rb3` package resolves the same shape the other way, on purpose, and says so in its docstring. |
| 2026-10-16 | **What the falsification does not cost.** Appendix A, B and C are unchanged. Appendix D's patch is unchanged, tested and now **necessary rather than convenient**: across a process boundary the in-runtime operation becomes the brain's client, and a client has to send the question, so `cause.content` reaching the operation is the only way it can know what to ask. The corrected shape is **the patch plus a process boundary**. The envelope must be re-costed. Four things remain unmeasured and are named in appendix E section 7 rather than glossed. |
| 2026-10-16 | **Three further defects in the runtime-path probe, found after the first three were recorded, and kept as a separate row rather than folded into it.** **Fourth:** the unpatched-detector asked whether the bank had `_active_case` as an attribute of its class. It does not, for a correctly patched tree — the node sets its own holder in `__init__`, but the bank creates `self._active_case` at **call time** inside `forward` — so the detector **aborted a good run**. It now tests the thing the patch changes, the bank's `forward` signature. **Fifth:** the node's "was it cleared" check read the holder inside a wrapper around `node.forward`, which runs *before* `network.forward_node`'s `finally` clears it, so it always saw the live case and reported **"the node was not cleared"** — a false accusation against the patch, which was then confirmed correct once the holder was read after the whole call. **Sixth:** the negative control asserted a sentinel for a missing argument that the patched node can never produce, because it always passes its holder down as an explicit `None`; the control now asserts `None`. Seven probe defects in total across the two versions, every one found by running it. |
| 2026-10-16 | **Appendix F written: the frozen input rule is falsified, and the ceiling it puts on the brain is 36 of 288.** Appendix A froze stock exactly `0` or `1` and requirement exactly `1`, so a missing leg yields exactly zero. `rb/brain.py`'s readout tests `best == ZERO` and refuses on gate **G2**. Measured on a live brain: one leg missing gives `UNDETERMINED`/`G2`. No requirement value avoids it — all five values across the brain's own bounds `[0.05, 20]` gave `G2`, because zero divided by anything is still zero — and a second allocated recipe makes it **worse**: gate `G1`, both active sets empty. The runtime's own dataset is authored balanced across its eight answers (`native_task.py:189`), so `ALL_LEGS_PRESENT` is exactly one eighth of cases: **36 of 288**. That is the brain's ceiling on this task, and on the other 252 its answer is `UNDETERMINED`, which the project's own scoring counts as not wrong and not right. |
| 2026-10-16 | **A second, independent mismatch measured: the answer alphabet.** The brain has `RECIPES = 4` and its own labels `L0`–`L3`; the task produces **8** answers (`native_task.py:23`) and the decoder reads channels `0`–7. One readout returns exactly one `beta[winner]` and there are four beta slots, so **at most four answers can ever be named by one readout**. SHORT BY 4. This would be reachable by a wider brain; it is recorded because it is independent of the gate problem and has to be solved separately. |
| 2026-10-16 | **A candidate repair, with its arithmetic measured and its permission explicitly not.** Give the cells values that are never zero — a reference cell at index 0, leg cells 1..7, padding — so the minimum is `1` and the brain's own argmin finds the first missing leg. Run on a live brain over **every route length from one leg to seven and every position of a single missing leg: 35 cases, 0 gated, 35 agreed.** What is NOT measured, and is the whole remaining question: the reference cell has to know whether *every* leg is present. That is a conjunction over the same facts the rule already reads, so it may be legitimate, but it is closer to the answer than anything else in the bridge and `RT_SHIM_NO_MATH` exists to draw exactly that line. Whether it crosses is a design question, not a measurement, and it is not decided. The candidate also changes a frozen appendix and would need its own freeze and the owner's line. |
| 2026-10-16 | **Appendix F fed back into the loop as two new leaves.** `RT_ANSWER_ALPHABET_COVERS` and `RT_INPUT_RULE_SURVIVES_GATE`, both read from the packages' own source so the readings move if either package moves, and both prerequisites of `RT_BRIDGE_EXISTS`. Iteration 20's diagnosis tree now reads `HELM_R1_RT_HOSTED` → `RT_BRIDGE_EXISTS` → three measured leaves, all three UNSATISFIED, plus `RT_GATE_OPEN` UNKNOWN. No safeguard fired, no cycle, no contradiction. |
| 2026-10-16 | **A guard that looked like a guard, and was not, in the amendment log's own writer.** The first version of round 15's row-insertion script guarded each row with a short marker string, and one marker was written `appendix F` while the text says `Appendix F`. The check is case-sensitive, so it answered `False` forever and **inserted all four rows twice**. Found by running the script a second time and reading the line that said `ADDED` when it should have said `nothing to do`. The script now asserts that every marker is a literal substring of the row it guards, so a marker that can never match fails loudly instead of silently re-adding. This is section 12's failure in miniature: a check that looks like a check. |
| 2026-10-16 | **Third target added: `HELM_R1_RT_HOSTED`** (host the recipe brain inside HELM's own runtime), with its measured state, its three names, its nine marks and five arms, both frozen conversion rules, and its run envelope. Its two open conditions are the bridge code and the owner's word. |
| 2026-10-16 | Written. The council's first operating session: engine of record established at `H_c8`; two targets defined; ten independent seats run on the HELM-R1 blocker; find section 7.47 and the four stranded sections 7.40–7.43 recorded in the living master record; the wave-1 run backed up with three confirmations. |
