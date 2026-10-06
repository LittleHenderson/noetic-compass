# The CAS Reasoning Processor — the brain, not the harness

**Date:** 2026-08-28
**Status:** built and tested. Bounded software evidence only.
**Governs:** `scripts/cas_rpu/{foundations,workspace,banks,runtime,demo,repl}.py`
**Sources:** `docs/reference/pdf/CAS_Ohm_Quantification_Guide.pdf`,
`docs/reference/pdf/CAS_PCBA_Engineer.docx`,
`docs/reference/pdf/RESEARCH_PAPER_CAS_OHM_1_0_v0.2.pdf`

---

## The question this answers

> Can reasoning processing be built from CAS PCBA engineering alone — not a
> harness around a language model, but the thing that reasons?

**Structurally, yes, and it now runs.** `python scripts/cas_rpu/demo.py` takes
CAS-encoded premises and produces CAS-encoded conclusions with a full
derivation trace, with no model, no key, and no network anywhere in the path.

What that sentence does *not* claim is in [What this is not](#what-this-is-not).
Read that section before quoting this one.

## Harness versus brain, and which this is

The decisive test is where the novel conclusion originates.

| A CAS harness | This |
|---|---|
| The model generates the thought | `^8` surfaces the candidates |
| CAS inspects or redirects the result | `^6`/`^9` produce the result |
| The model holds the working state | `Workspace` and the CMB hold it |
| The model makes the plan | RPM makes and descends the sub-goals |
| Remove CAS and it still reasons | Remove CAS and there is nothing left |

`test_cas_rpu_sever.py::NoModelInTheLoopTests` makes the second column
structural rather than aspirational: it scans every module in the package and
fails if any of them imports a transport, a client, or the network. The cord is
not merely unused. It is absent.

## What was already there, and what was missing

The parts bin was well stocked. `cjt_sim.py` (CJT maths against the Guide's
worked numbers), `cmb.py` (the 40-cell memory bank), `cdab.py` (the differential
comparator), `rpm.py` (first-unmet-prerequisite descent) all predate this work
and are reused unchanged.

Two things were missing, and they are what this adds:

1. **The Foundation Engine Bank** — the 28 sub-Foundations as a goal system
   with recipes, so the processor has ambitions and can say which prerequisite
   bottlenecks an outcome.
2. **The execution cycle** — a control unit that schedules the organs until a
   task is finished. Without one, the components never wake each other.

## The instruction cycle

```
FETCH -> PRIME -> ASSOCIATE -> DECOMPOSE -> INFER -> COMPARE
      -> CHECK_PREREQUISITES -> COMMIT -> ACT -> LEARN
```

In CAS terms: CMB recall; the Foundation engines and the outcome recipe; `^8`
candidate triggering; `^6` decomposition; `^9` conclusion; CDAB comparison; RPM
`D -> W -> P`; Schmitt commit; `P -> C -> E -> O`; filtered low-gain feedback.

A worked trace, from the demo:

```
[01] FETCH                ^C  8 premise(s) loaded; CMB charge 0.60
[02] PRIME                ^P  target F2|A; Theta(deduction) = 1*F2|A + 0.2*F6|A
                              + 0.3*F7|A -> deduction; Y_T=0.630, limiting
                              reagent F2|A; dominant F2|A
[03] ASSOCIATE            ^C  ^8 active: 3 candidate route(s) surfaced
[04] DECOMPOSE            ^E  ^6 VS -> DE -> NX: 1/2 constituent(s) supported
[05] DECOMPOSE            ^E  ^6 VS -> KP -> NX: 1/2 constituent(s) supported
[06] DECOMPOSE            ^E  ^6 VS -> QS -> IU -> TR -> NX: 4/4 supported
[07] INFER                ^C  ^9 YES on VS -> QS -> IU -> TR -> NX
[08] COMPARE              ^E  CDAB winner ... by margin 0.383
[09] CHECK_PREREQUISITES  ^E  RPM D=9.0 W=8.0 P=7.0 -> CONCLUDED
[10] COMMIT               ^E  committed at confidence 0.80
[11] ACT                  ^O  emitting conclusion: VS ->[leads_to] NX
[12] LEARN                ^P  CMB write at beta=0.05 (low gain, filtered)

backtracked from:
  VS -> DE -> NX: missing VS|leads_to|DE
  VS -> KP -> NX: missing KP|leads_to|NX
```

`VS -> NX` appears in no premise. The processor made it, from four premises it
names, having thrown out two routes that association offered it.

## Three laws, enforced structurally

### 1. Association is not deduction

`^8` Above/Cause is associative triggering. Deduction is `^6` decomposition plus
`^9` landing. The PCBA book names the failure directly:

> "`^8^C_{F2}|A -> ^9^C_{F2}|A` is the cognitive short circuit. It jumps
> straight from the Above/Cause trigger to the Below/Effect result with no
> intermediate processing ... the answer is produced without doing the cognitive
> work that would make it sound."

`BankTrace.fire` raises `E-BANK-003` on that transition. It is a refusal, not a
warning.

**The subtle part, and the one defect worth confessing.** The first
implementation had `^8` walk only edges of the queried relation. That version
passed every test and was wrong: `^8` was verifying its own output, so `^6`
could never find a missing constituent and the deduction had silently moved into
the trigger. `^8` now associates across *any* relation, because that is what
"one thing leads to another" licenses. The consequence is the point — a route
surfaced through a `co_occurs` edge is a real candidate and a real possible
error, so `^6` has real work and can genuinely fail. Both behaviours are pinned:
`test_association_crosses_relation_types_and_can_therefore_be_wrong` and
`test_restricting_the_walk_makes_decomposition_a_rubber_stamp`.

### 2. Gain is not truth

| Bank | Gain | Why |
|---|---|---|
| `^8` generation | `beta > 1` | too little is tunnel vision; too much is a fireworks factory |
| `^6` decomposition | `beta == 1` | **the truth firewall** |
| `^9` inference | `beta == 1` | same |
| learning feedback | `beta <= 0.2` | one outcome must not rewrite the constitution |

Unity is exact. A stage at 1.02 exaggerates by 2%, and `E-BANK-002` refuses it.

### 3. Ambition may choose the question; it must not choose the answer

`DecompositionBank.decompose` and `InferenceBank.land` have **no parameter**
through which a `FoundationProfile` could reach them.
`test_the_evaluation_banks_cannot_be_handed_the_ambition` asserts the
signatures, so the firewall is a property of the code shape rather than a
promise in a docstring — the same trick the Stage 5 calibration gate uses.

The distinction that took a test failure to get right: ambition legitimately
decides **whether to engage**. A processor with no Desire for the target halts
at the RPM Desire block. That is choosing the question. What it may not do is
change the verdict or the confidence once engaged, and three tests pin that —
including one that raises the ambition to 1.0 against a gap and watches the gap
stay open.

## The Foundation Engine Bank, and a correction

An earlier sketch of this bank proposed `TF1..TF7` / `DF1..DF7` with worlds
`a,b,c,d`, reasoning that the TKS Foundations and CAS Drive rails are different
objects. **The observation is right and the conclusion is wrong**, and the
prior audit (`cas_pcba_reasoning_audit_2026_08_27.md`) had already said so.
Verified directly against the sources rather than taken on faith:

- `docs/reference/tks_28_foundations_translation_key.md:41` — "CAS Drive names
  are authoritative. Where TKS labels use different nomenclature, the mapping is
  by position in the 7-Foundation sequence, not by label."
- The same file's Register-to-World table — the four Worlds **are** the four
  Registers: `|T` 1st, `|A` 2nd, `|f` 3rd, `|E` 4th.
- `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py:73` — `VALID_REGISTERS = ("T","A","f","E")`, with a
  `SubFoundations` meta-set of 28 members spelled `F5|A`.

A `TF5b` production would have been a **third** spelling — `F5b` (TKS), `F5|A`
(compiler), `TF5b` (sketch) — for one position, in a design whose own first rule
warns against symbolic soup. This module uses `F5|A`, and
`test_the_superseded_tf_spelling_is_not_accepted` keeps it that way.

**One in-repo inconsistency is left standing rather than silently picked:**
`offline-cas/cas_terminal.py:358` calls the 28 "7 x 4 Domains". The translation
key and CLAUDE.md's v7.5 section both say Registers, and Registers is what is
implemented. Reconciling the terminal's glossary is separate work.

### Recipes, because a bare arrow cannot find a bottleneck

The sketch wrote routing as `TF5b -> DF2 + DF5 + DF6` — a v7.6 recipe with the
proportions deleted. Without coefficients the bank cannot compute a bottleneck,
which is the one thing it exists to do. So `Recipe` carries them, per
Clarification 9:

```
Theta(deduction) = 1.0*F2|A + 0.2*F6|A + 0.3*F7|A -> deduction
Y_T = min_i(x_i / a_i)          the theoretical yield
L   = argmin                     the limiting reagent
```

This makes the bank say something a label could not:

```
single-minded  deduction   Y_T=0.000  limiting F6|A
balanced       deduction   Y_T=0.630  limiting F2|A
```

An ambition spiked entirely on analytical Wisdom **cannot produce a deduction**,
because the outcome also needs Structure to hold the chain together and Purpose
to keep going. Wanting one thing intensely does not supply the rest of the
recipe.

The coefficients are **design values** — "declared by a board or profile, not
measured", in the research paper's sense. They carry no empirical claim.

## The seven mechanisms

| Mechanism | Where | Pinned by |
|---|---|---|
| Global workspace | `workspace.Workspace` | `ProvenanceTests` |
| Scheduler | `runtime` ten phases | `TraceTests` |
| Branching and search | candidate list from `^8` | capability 3 |
| Binding and substitution | `workspace.Pattern` | `BindingTests` |
| Backtracking | `Episode.backtracks` | capability 8 |
| Truth maintenance | `workspace.Status` | `TruthMaintenanceTests` |
| Halting controller | `Terminal` + tick bound | `TerminationTests` |

Two details in truth maintenance are load-bearing. A conclusion **may not rest
on a hypothesis** (`E-WS-002`) — that is the step by which a machine turns its
own guess into its own evidence. And retraction is **transitive**: withdrawing
an assumption withdraws everything resting on it, because a processor that keeps
the consequences is holding conclusions with no remaining reason to believe them.

## Open world versus closed world

The single most consequential flag. Under an open world an unclosable chain is
`NEEDS_INFORMATION`; under a closed one it is a legitimate `NO`. The processor
does not merely abstain — it names the gap:

```
[04] DECOMPOSE  ^E  ^6 had no candidate to decompose; VS reaches {QS},
                    IU is reached from {AA} -- no join
[05] CHECK_...  ^E  RPM W=0.0 -> NEEDS_INFORMATION; 1 lacuna(e) recorded;
                    descended into 'acquire VS|leads_to|IU'
```

The RPM planner genuinely descends: the Wisdom block becomes a sub-desire, the
descent bottoms out, and the report names the acquisition that would unblock the
parent. That is the difference between "no" and "here is the exact thing I would
need".

## The sever test

`scripts/tests/test_cas_rpu_sever.py`, one test per capability:

| # | Capability | Result |
|---|---|---|
| 1 | intermediate states not in the input | derives `VS -> NX` from four premises |
| 2 | retrieve relevant memories | reads `C5`; distinguishes charge from lacuna |
| 3 | multiple hypotheses | 3 routes surfaced |
| 4 | decompose premises | every link named |
| 5 | derive conclusions | support listed |
| 6 | detect contradictions | `INADMISSIBLE` |
| 7 | recurse into missing prerequisites | descends to depth 1 |
| 8 | backtrack | 2 decoys rejected |
| 9 | justified answer | provenance bottoms out in premises |
| 10 | complete trace | all ten phases, monotone ticks |

Plus three honesty tests: it does not answer what the premises cannot settle, an
associative route alone never becomes a conclusion, and the conclusion never
rests on a hypothesis.

**128 tests, all green.** The 262 existing CCB-R1 tests are unaffected.

## What this is not

Stated up front so it is not discovered later.

- **Bounded software evidence only.** Per the research paper, synthetic boards
  "validate software behavior only; they are not experiments on a live model and
  cannot establish causal or empirical validity." Nothing here is a research
  packet or authenticated evidence.
- **A trivial graph solver answers the same items.** The prior Stage 5 work
  established this for the reachability family (`b4_trivial_solver` scores what
  the board scores). Passing the sever test shows the architecture **reasons
  natively** — it does not show CAS structure is necessary, superior, or more
  efficient for this task. Any claim of the second kind needs a task family
  where the structure earns its keep and a control that lacks it.
- **No proof of computational universality.** None is offered.
- **Nothing about consciousness.** "Cognitive" means structural throughout, in
  the book's sense: a CJT no more thinks than a transistor is electronic-minded.
- **The premise encoding is given, not learned.** Problems arrive already in CAS
  triples. Natural language in and out would need encoder and decoder
  peripherals, and the semantics of English-to-CAS encoding are not formalised in
  the sources. That boundary is real and is where an LLM could legitimately sit
  **as a peripheral** without making this a harness — but the boundary must be
  strict, and it is not implemented here.
- **The reasoning is over relational triples.** Arithmetic, temporal reasoning,
  quantification over infinite domains, and defeasible inference are all absent.
- **`Recipe` coefficients are declared.** They are design values chosen to be
  inspectable, not fitted to anything.
- **CAS-Ohm quantities are not physical.** V, I, R here are design-scale
  quantities on the unit normalisation; `volt`, `ampere`, `ohm` are forbidden
  aliases per the research paper's Rule 2.3.

## A scale trap worth recording

The first version fed the Guide's p.12 worked numbers (`V=8, R=2`) into specs
declared on `Scale.UNIT`, where `sat` lives in `(0,1]`. Every bank pinned at
saturation and the `^8` bank silently truncated its candidate list. That is
**Preserved Conflict 3.1** (scale and saturation) biting in practice, and the
cure is to keep the two normalisations apart rather than to widen `sat`. The
banks now declare unit scale and use drive values that put `I` near 0.4–0.5.

## How to interact with it

### The console

```
python scripts/cas_rpu/repl.py
```

Type premises, ask a question, read the trace. `help` lists everything.

```
cas> VS -> QS                    a premise
cas> QS -> IU
cas> ? VS -> IU                  ask, and get the full phase trace back
cas> why                         the support tree under the conclusion
```

The commands worth knowing:

| Command | What it does |
|---|---|
| `A -> B` | a premise, using the default `leads_to` relation |
| `A -reports_to-> B` | the same with a named relation |
| `A ~> B` | an **associative** link (`co_occurs`) — `^8` follows it, `^6` rejects it |
| `not A -> B` | an explicit negation; two that disagree make the set `INADMISSIBLE` |
| `? A -> B` | reason about it |
| `why` / `trace` / `lacunae` | provenance, phase trace, unanswered questions |
| `world open\|closed` | whether an unclosable chain is `UNKNOWN` or a legitimate `NO` |
| `ambition F5\|A 1.0` | change the goal channel and watch the verdict *not* move |
| `memory 0.6` | pre-charge the `^5` experience cell |
| `scenario ladder\|gap\|assoc\|contra` | load a worked example |

`~>` is the interesting one. It is how you make the machine backtrack: `^8`
will happily surface a route through an associative edge, and `^6` will throw
it out, which is the whole `association is not deduction` law in two keystrokes.

### One-shot, for scripting

```
python scripts/cas_rpu/repl.py -p "VS->QS, QS->IU" -a "VS->IU" --quiet   # YES
python scripts/cas_rpu/repl.py -p "VS->QS" -a "VS->IU" --quiet           # UNKNOWN
python scripts/cas_rpu/repl.py -p "VS->QS" -a "VS->IU" --closed --quiet  # NO
```

Exit status carries the verdict, so a script can gate on whether the processor
was **willing to commit**: `0` concluded, `2` withheld (`NEEDS_*`), `3`
inadmissible. Piped stdin runs as a script.

### Four things worth trying

1. **Watch it backtrack.** `scenario ladder` then `? VS -> NX`. Three routes
   surfaced, two thrown out, the trace names which constituent was missing.
2. **Watch it refuse to guess.** `scenario gap` then `? VS -> IU`. It names the
   frontier — what the source reaches, what reaches the target — and descends
   into the acquisition that would unblock it. Then `world closed` and ask
   again: the same premises now yield a legitimate `NO`.
3. **Try to bribe it.** `scenario gap`, then `ambition F5|A 1.0`, then ask
   again. The gap stays open. Ambition sets `PRIME` and `COMPARE`; it cannot
   reach `^6` or `^9`.
4. **Break it honestly.** `scenario contra`. Two premises that disagree and it
   refuses the question rather than picking a side.

## Reproduce

```
python scripts/cas_rpu/demo.py                                   # no cost
python scripts/cas_rpu/repl.py                                   # interactive
python -m unittest discover -s scripts/tests -p 'test_cas_rpu_*.py'
```

## Next

1. ~~**A task family where structure earns its keep.**~~ Done, with a
   correction to the question: `docs/working/cas_rpu_revision_streams_2026_10_06.md`.
   The honest gap above turned out to be unclosable on correctness — ground
   truth over a finite event stream is a function of the stream, so a replayer
   with no truth maintenance is always right — and the family was built to
   establish what *can* be established: that an organism which holds, reuses
   and un-holds conclusions converges with recompute-from-scratch on every
   probe, that each mechanism's removal fails a named class and nothing else,
   and what each costs. The contract (`revision_streams_contract_2026_10_06.md`
   §0) fixes the permitted wording.
2. ~~**Encoder and decoder peripherals**, with the strict boundary stated above.~~
   Done for a closed grammar of five productions (`encoder.py`); open English
   is a different project, see the 2026-10-06 note §3.
3. **Recipe coefficients for outcomes beyond the three shipped**, and a
   `Consequence` computed by the processor rather than supplied to it.
4. **Register-aware banks.** The banks currently run analytically (`|A`). `|T`,
   `|f` and `|E` are represented in the Foundation bank but no stage varies with
   them.
