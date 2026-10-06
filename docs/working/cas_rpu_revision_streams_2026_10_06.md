# Revision Streams: the organism, the controls, and what the matrix is allowed to say

**Date:** 2026-10-06
**Builds on:** `docs/working/cas_rpu_reasoning_processor_2026_08_28.md` (the processor) and
`docs/working/revision_streams_contract_2026_10_06.md` (the binding semantics, §0 above all).
**Code:** `scripts/cas_rpu/{events,encoder,organism,revision,controls,ablations,scoring,revision_experiment}.py`
**Reproduce:** `python scripts/cas_rpu/revision_experiment.py --check` (both worlds, n=40, seed 20261006; ~1 s)

---

## 1. What this is, in one paragraph

The 2026-08-28 note ended on an honest gap: the processor reasons natively, but
every item it was tested on is also solved by a breadth-first search, so nothing
showed that holding beliefs, retracting them, or abstaining with a named gap was
*doing* anything. This note is the next layer. The processor is wrapped in an
**organism** — one workspace that outlives the question, one memory, a
motivation that moves, a heartbeat that audits — and fed a **stream** of
statements, guesses, denials, retractions and questions. A **task family**
generates such streams in four classes, each built around one mechanism of a
held-belief reasoner. A **recompute oracle** defines the right answer to every
question by replaying the log. Ten **controls** are that oracle with one rule
broken; seven **ablations** are the organism with one workspace rule removed.
The experiment runs all of them over the same probes and prints a matrix.

## 2. The claim, fixed before the first line of code

Ground truth over a finite event stream is a function of the stream. A solver
that keeps two sets of pairs and re-walks the graph on every question is
therefore correct on every probe, with no truth maintenance in it. That solver
is `ctl_recompute`, it is the first row of every table, and it is at 100% by
construction. **Nothing in this family can show that truth maintenance is
necessary, or that the organism is superior to recompute-from-scratch on
correctness.** Six adversarial reviews of the design each arrived at this (four
built the replayer and matched the oracle they were reviewing); the contract
states it in §0 so nobody reads the matrix as more than it is.

What the family does establish, and the only wording permitted:

1. **Convergence.** The organism — which holds conclusions across episodes,
   answers them from the record, and un-holds them when their support dies —
   agrees with recompute-from-scratch on every probe, in both worlds, with
   zero heartbeat faults. That is the soundness of a *held-belief* reasoner.
2. **Diagnosis.** Each class detects a failure mode of a held-belief reasoner,
   and each ablation fails inside the class or column it was built to expose
   and nowhere else. Every control is labelled as what it is: the oracle minus
   one rule.
3. **Cost,** reported as measured, in two different currencies that are not
   compared across rows.

Forbidden: "load-bearing" without "relative to the solver that lacks it",
"necessary", "superior".

## 3. "It doesn't read English yet; problems arrive already encoded"

The processor's input type is a triple `(subject, relation, object)` and a
query pair. The sentence means three things, and each has a consequence.

**What it means.** No stage of the processor sees a string of English. The
premises of every problem, and every event of every stream, are already in
CAS form when they arrive: `("A", "leads_to", "B")`, not "A leads to B". Who
did the encoding, and by what rules, was outside the processor and — in the
2026-08-28 note — outside the repository.

**What it entails.** Every semantic decision that turns a sentence into a
triple is made *before* the reasoner sees anything. If those decisions are
made by a person, the person is part of the system under test. If they are
made by a language model, the sever test (`test_cas_rpu_sever.py`, which
shows the architecture reasons with no model in the loop) is quietly undone,
because reasoning has been put back on the wrong side of the line. So the
boundary has to be *written down*. `encoder.py` is that: a closed regular
grammar of five productions — fact, negation, hypothesis, retract, ask — each
mapping to exactly one `Event`, with total rejection of anything else
(`E-ENC-001`..`008`) and an exact inverse (`encode(render(e)) == e`). The
encoder never guesses, so its every decision can be listed, which is what
makes "the processor was handed this and nothing else" checkable.

**What it implies.** The claim "the thing reasons" is a claim about what
happens *after* encoding, and it is only as strong as the boundary is narrow.
A reasoner that accepts "the committee was reluctant to endorse the proposal"
would need an encoder that decides what the subject is, what the relation is,
and whether reluctance is a negation, a hypothesis, or neither — and every one
of those is a judgement the processor would then be credited for. The five
productions are therefore not a limitation to apologise for; they are the
measured width of the gap between "reasons over CAS structure" and "reads
English", stated so the gap is not mistaken for closed. Closing it — an
encoder for open English — would be a different project with a different
honesty problem, and it is listed under Next, not claimed here.

## 4. What was built

| module | what it is | the one thing it enforces |
|---|---|---|
| `events.py` | the five event kinds, the shared contract between everything else | reflexive events refused; no sixth kind hidden in a flag |
| `encoder.py` | the English boundary (§3) | rejection is total; the grammar is the list of semantic decisions |
| `organism.py` | one workspace, one memory, one processor, a motivation, a heartbeat; `consume(event)` | you may forget what you were told, never what you derived (`E-ORG-001`) or were never told (`E-ORG-002`); every standing conclusion is audited every beat (`E-ORG-003`); motivation may change what is asked, never what is answered |
| `revision.py` | `StreamDifficulty`, the oracle `replay()`, `StreamItem`/`StreamSet` with fingerprints, `generate_revision_set()` | ground truth is computed, never passed in (`E-RS-005`); no item the bank could not fairly see (`E-RS-006`); balance ceiling (`E-RS-007`); paired worlds byte-identical |
| `controls.py` | one `Replayer` with eight rule flags; `ctl_recompute` + nine "minus one rule" | each control differs from the oracle in exactly one field (introspected) |
| `ablations.py` | seven `Workspace` subclasses, each removing one rule | `overrides` declares the surface; a test asserts nothing else moved and every other rule survives |
| `scoring.py` | per-probe columns with the contract's bounds; `Matrix` | 0/0 is unscored, never 100%; naming columns scored only on a right verdict |
| `revision_experiment.py` | the run; `--check` turns the §0 claims into an exit code | fingerprints print first |

The organism's three new organs, in the words of the request that asked for them:

- **An organism, not organs.** The processor answered one problem on one fresh
  workspace and forgot. The organism's workspace persists: a conclusion landed
  in one episode is held, answered from the record on re-ask, and taken down by
  the workspace's transitive cascade when a given it rests on is retracted or
  denied — and the response names what fell.
- **A motivation system.** Ambition as *state*: an abstention raises F2 Wisdom,
  a dispute raises F6 Structure, a conclusion raises F7 Purpose. Low gain
  (≤ 0.2, `E-ORG-004`), relaxing toward its constitution every beat, with one
  rule the contract had not foreseen: engagement is constitutional, so
  successes cannot relax the will to know below the RPM Desire gate. When a
  fact closes a gap the organism owed, it re-asks on its own. The hard law is
  tested non-vacuously: identical verdicts, lacunae and contested keys under
  beta 0 and beta 0.2, while the two motivations demonstrably diverge.
- **A heartbeat.** Not an event, never scored. Experience decays unless LEARN
  refreshes it; motivation relaxes; every standing conclusion's roots are
  checked. A healthy organism never faults. The two ablations that break a
  cascade are caught here, structurally, before the broken belief can be
  answered from the record as if it were sound.

## 5. The result

Fingerprints (n=40, seed 20261006, `h3-d4-p1`, pinned in `test_cas_rpu_revision.py`):

```
open    PENDING
closed  PENDING
```

Per-class probe balance, open world: PENDING. No verdict exceeds the 60%
ceiling in any class (`E-RS-007`, judged in integers).

### 5.1 Convergence

The organism agrees with the oracle on every probe of both worlds (verdict,
contested keys, lacuna bounds, withdrawn bounds) and raises zero heartbeat
faults. `--check` fails if it does not.

### 5.2 The matrix (open world; % of probes correct; — = not scored)

PENDING: the table printed by `revision_experiment.py`, reproduced verbatim.

Reading it: `ctl_recompute` and `ctl_memo_flush` are 100% everywhere by
construction. Each broken control fails in the class whose rule it lacks and
passes the rest — those passes are "right for the wrong reason", and the
per-variant table lists them so a pass is never read as a mechanism. Each
ablation's failing cells lie inside the class or column it was built to
expose: retraction without cascade fails inside R; a told guess filed as a
given fails inside H; last-writer-wins and no-dispute-cascade fail inside C;
an amnesic `ask` loses the `named` column and nothing else; a fixed world is
perfect on the open set and wrong on exactly the closure probes of the closed
set. The audit raised PENDING faults for `abl_no_cascade` and PENDING for
`abl_nontransitive_retract`, and none for the organism.

### 5.3 What the unmarked-guess ablation showed

`abl_no_sweep` removes the stage mark on `^8`'s route guesses, so they are
neither swept nor skipped by the next walk. Through the organism, on a hand
stream, a lingering guess is named as a gap (tested). On the generated family
it changed **no scored cell**. That is the honest result: the mark is not
load-bearing for correctness on this family, relative to the organism that
lacks it, and the generator does not emit the probe pattern that would show
it. Reported, not claimed.

### 5.4 Cost

PENDING: the cost table. Two currencies: a control counts adjacency entries
expanded plus pairs filtered; an organism counts `Workspace.ask` calls plus
propositions scanned by `^8`. They are not compared across rows. Within rows,
on this family, the organism's repeat asks are not cheaper than its first asks,
because `HypothesisBank.surface` walks every live proposition on every ask
before a standing conclusion can be hit directly. The replayer's cost grows
with its log and the organism's with its workspace. Nothing here supports
"incremental maintenance beats replay"; the design note's earlier sentence to
that effect was corrected in the contract (§12, C6).

## 6. What was fixed on the way

Five defects a living workspace would hit, fixed first and alone so every later
regression is attributable (`cc645b9`): a hypothesis refuted on arrival could
overwrite a contradicted record; a hypothesis could outrank evidence by being
re-guessed; a conclusion already held was re-derived from itself; a
contradiction anywhere refused every question (now local to the queried route);
and `^8` re-triggered on its own earlier route guesses (now swept, and skipped).

Two more from the after-the-fact cross-check of the contract (§12 of the
contract records all of it): a given denial behind a route that association
surfaced but `^6` could not complete was answered "I do not know" instead of
NO (`runtime.py`); and a key held in both polarities was reported as a gap to
go and acquire, when it is a dispute (`Workspace.lacunae`). Both are tested.

The cross-check also moved one oracle rule (a disputed denial is a dispute,
not knowledge, as the runtime already pinned), gave the oracle a per-pair
holding state so a withdrawn conclusion ages out as it leaves the organism's
`standing`, keyed denials and guesses to `leads_to` only, and replaced every
"fails exactly" claim about an ablation with a class-level containment check
plus the probe-level set reported from the run.

## 7. How to interact with it

```
python scripts/cas_rpu/revision_experiment.py                 # the matrix, both worlds
python scripts/cas_rpu/revision_experiment.py --check         # exit 1 unless the §0 claims hold
python scripts/cas_rpu/revision_experiment.py --json out.json # matrices and checks as data
python scripts/cas_rpu/revision_experiment.py --solvers organism ctl_order_blind --n 12
```

A stream by hand, through the organism:

```python
from events import fact, ask, retract
from organism import Organism
org = Organism()
for r in org.run_stream([fact("A", "B"), fact("B", "C"), ask("A", "C"), retract("B", "C"), ask("A", "C")]):
    print(r)
print(org.report())
```

Or in English, through the boundary:

```python
from encoder import encode
org.consume(encode("A leads to B"))
org.consume(encode("forget that B leads to C"))
print(org.consume(encode("does A lead to C?")).verdict)
```

## 8. Next

1. **A probe pattern for the unmarked-guess ablation**, if one is wanted: an
   abstention on a pair whose endpoints lie on a later question's route. It
   would turn §5.3's "reported" into a diagnostic cell — or confirm that the
   mark is hygiene, not correctness.
2. **Open-English encoding** is a different project with a different honesty
   problem (§3). The five productions are the current measured width of the
   gap.
3. **Recipe coefficients for outcomes beyond the three shipped**, and a
   `Consequence` computed by the processor rather than supplied to it
   (carried over).
4. **Register-aware banks** (carried over): `|T`, `|f` and `|E` are
   represented in the Foundation bank; no stage varies with them.
