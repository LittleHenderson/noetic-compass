# Revision Streams — the semantic contract

**Date:** 2026-10-06 (amended the same day; see §12)
**Status:** binding on `scripts/cas_rpu/{organism,revision,controls,ablations,scoring}.py`.
Every rule here was fixed *before* the module it governs was written, and the
oracle in `revision.py` is its executable form. The organism is correct iff it
agrees with the oracle on every scored probe. Where this file and the oracle
disagree, the oracle is wrong. Where this file and the live `Workspace` or
`runtime` disagree on a stream the generator emits, one of them is wrong and
§12 records which was changed and why.

---

## 0. The claim this family is allowed to make

Ground truth over a finite event stream is a function of the stream, so
recomputing from the log is always a correct solver with no truth
maintenance in it. Of the six adversarial reviews of the design, four built
such a replayer and matched the oracle they were reviewing on every probe;
none of those oracles was this one, so the statement is made here by
construction (`ctl_recompute`, §9), not by their numbers. **No item in this
family can separate a correct organism from a correct replayer on
correctness.** That is not a defect to fix; it is B4 one level up, and it is
stated first so nobody reads the matrix as more than it is.

What the family *does* establish, and the only wording permitted:

1. **A convergence contract.** The organism — which holds beliefs across
   episodes, derives conclusions once and reuses them, and un-derives them
   when their support dies — agrees with recompute-from-scratch on every
   probe. That is the soundness of a *held-belief* reasoner, and it is not
   free: every ablation below breaks it somewhere.
2. **A diagnostic suite.** Each item class detects a failure mode of a
   reasoner that holds beliefs, and each ablation of the organism reproduces
   a failure inside the class or column it was built to expose. Every control
   is labelled for what it is: the recompute oracle with one rule deliberately
   broken.
3. **Cost.** Per-ask work (workspace reads + association edge visits) is
   reported for the organism and the replayer as the stream grows, as a design
   measurement with no empirical claim. `HypothesisBank.surface` walks every
   live proposition on every ask, so the organism's per-ask reads grow with
   its workspace as the replayer's grow with its log; only a direct hit on a
   standing conclusion is cheaper, and it still pays the walk first. The
   column therefore shows where the two *differ*, not that one beats the
   other.

Forbidden wordings: "load-bearing" without "relative to the solver that lacks
it"; "necessary"; "superior"; "exactly one failure mode" for an ablation
whose failing set is reported per probe rather than pinned. `ctl_recompute`
is the **first row** of every table and is pinned by test at 100% on every
column it can produce.

## 1. Events

`events.Event(kind, subject, obj, relation)`; kinds FACT, HYPOTHESIS,
NEGATION, RETRACT, ASK; relations `leads_to` (the one chained over) and
`co_occurs` (associative: `^8` follows it, `^6` rejects it). Reflexive events
are refused at construction (E-EV-003).

**Grammar restriction.** HYPOTHESIS, NEGATION and ASK carry `leads_to` only;
FACT and RETRACT carry either relation. The oracle works in pair space and
has no semantics for a denied or guessed *association*; it refuses such an
event (E-RS-009) and the generator never emits one. The organism's workspace
would record one harmlessly, which is outside the scored grammar.

## 2. Oracle state and transitions

Four sets of ordered pairs, replayed in stream order:

| set     | holds                                         |
|---------|-----------------------------------------------|
| `pos`   | positive `leads_to` pairs given and not since retracted |
| `neg`   | negated `leads_to` pairs given                |
| `hyp`   | hypothesised pairs not superseded             |
| `assoc` | `co_occurs` pairs given and not since retracted |

plus the per-pair **holding state** of §5. Transitions, each `ACCEPTED`
unless stated:

- `FACT leads_to (s,o)`: `pos.add`; `hyp.discard((s,o))` (a guess confirmed
  is no longer a guess).
- `FACT co_occurs (s,o)`: `assoc.add`.
- `HYPOTHESIS (s,o)`: if `(s,o) in pos`, or `(s,o) in neg`, or `(s,o)` is
  currently **held** (§5) → **no-op** (a guess against a known fact or
  denial is dead on arrival; a guess about a conclusion the organism already
  holds adds nothing, and the workspace drops it by its strength rule). Else
  `hyp.add`.
  Invariant, pinned by test: `pos ∩ hyp = ∅` at every position.
- `NEGATION (s,o)`: `neg.add`; `hyp.discard((s,o))` (refutation). There is no
  negative retract in the grammar; `neg` only grows within an item.
- `RETRACT leads_to (s,o)`: if `(s,o) in pos` → `pos.discard` → ACCEPTED.
  Otherwise **REFUSED**, state unchanged. (Includes: the pair was never given;
  the pair was retracted already; the pair is held only as a derived
  conclusion.) Retracting a *contested* pair — one in `pos & neg` — is
  ACCEPTED and leaves it merely denied.
- `RETRACT co_occurs (s,o)`: `assoc.discard` if present, else REFUSED.
- `ASK`: no state change except the holding state (§5); produces an
  `Expectation` (§3).

Generator guard **E-RS-010**: a HYPOTHESIS is never emitted on a pair that was
YES-asked earlier in the item (held or uncertain, §5). Outside that
exclusion the oracle and the workspace differ on a guess about an
*uncertain* pair (the oracle keeps it; the workspace keeps it only if its
derived record has already fallen), and §11 records this.

## 3. The verdict for `ASK(s, t)`, `s != t`

```
contested = pos & neg
clean     = pos - contested
```

Evaluate in order; the first that applies is the verdict:

1. `(s,t) in neg` and `reach(s,t,clean)`   → **INADMISSIBLE**, contested_required = {(s,t)}
   (the chain is sound and the conclusion is denied as a given: a dispute about this exact claim)
2. `reach(s,t,clean)`                        → **YES**
3. `reach(s,t, clean | contested)`           → **INADMISSIBLE**,
   `contested_required = { k in contested : k lies on some simple s→t route over clean|contested }`
   (simple = no repeated node; on the acyclic graphs the generator emits this
   equals the reflexive-reach formulation `reach*(s,k.s) and reach*(k.o,t)`, so
   a disputed first or last link is included; E-RS-006 bounds the enumeration)
4. `(s,t) in neg`                            → **NO** in both worlds
   (an explicit denial with no route at all is knowledge, not a gap)
5. closed world                              → **NO**
6. open world                                → **UNKNOWN**, with lacunae (§4)

`reach` is "there is a path of ≥1 edge".

Why rule 4 sits after rule 3 and not before it: a denial that is itself
disputed (`F(a,b) N(a,b) A(a,b)`) is not knowledge, and a denied pair whose
only route runs through a disputed link is a dispute about that link. The
runtime's Rule C pins both (`test_a_contradictory_premise_set_is_inadmissible`,
`test_a_contested_claim_asked_directly_is_a_dispute_not_a_denial`). A denied
pair behind a route that association surfaced but `^6` could not complete
(`F(a,b) Q(b,c) N(a,c) A(a,c)`) is NO in both worlds: the runtime consults the
given denial before abstaining (`test_a_given_denial_outranks_a_partial_route_association_surfaced`).

Convention, stated not derived: a HYPOTHESIS does not reopen a closed world.
H-bridge is NO under `closed_world=True`.

The organism answers INADMISSIBLE in exactly two cases, and the runtime's
Rule C is the executable form of rule 3: a landed conclusion whose status is
CONTRADICTED (rule 1), or no landing and some surfaced route whose every
absent link is contested (rule 3). The `contested` cell is scored as **set
equality** with `contested_required`.

## 4. Lacunae (open world, UNKNOWN only)

```
G_all      = (clean | contested | hyp | assoc) - (neg - pos)
admissible = { (u,v) in (hyp | assoc | {(s,t)}) :
               (u,v) not in clean, (u,v) not in neg,
               reach*(s,u,G_all) and reach*(v,t,G_all) }
required   = admissible & (hyp | assoc)
```

`reach*` is reflexive (`u == u` holds with no edge). The walk graph keeps
contested links, because `^8` walks every positive record including a
disputed one; it drops pairs that are only denied. A reported lacuna set is
correct iff `required ⊆ reported ⊆ admissible`. The lower bound defeats
"name nothing"; the upper bound defeats "name the whole frontier product".
A denied pair is never a lacuna, and neither is a contested one: **a dispute
is not a gap** (`Workspace.lacunae` excludes keys held CONTRADICTED in either
polarity; the processor names such a link through `contested()`). A gap
*beyond* a contested link is on a route `^8` surfaces and is a legitimate
thing to want to know; it is required.

Lacunae are not scored on YES, NO or INADMISSIBLE, and the `named` column is
scored only where the verdict was right (a wrong verdict is one miss, not
two). Under a closed world the column is unscored everywhere, and class N
reduces to plain reachability — stated, not hidden. On a probe whose
`required` is empty, naming nothing is correct; `abl_amnesic_ask` fails only
where something was required.

Lacunae are keyed `s|leads_to|o`; the oracle works in pairs; `scoring.py`
converts.

## 5. Withdrawn (a capability column, not correctness)

The oracle tracks, per pair, a **holding state** in {held, uncertain}
(untracked otherwise):

- An ASK answered YES makes the pair **held**. An ASK answered otherwise
  untracks it.
- At every RETRACT or NEGATION event at position *i*, REFUSED ones included
  (then both sets below are empty):
  - `affected` = {the event's pair} if that pair was in `clean_before`
    (RETRACT removes it; NEGATION makes it contested), else ∅.
  - A NEGATION of a pair *p* that is held or uncertain makes *p* **dead** and
    **required**: the organism's derived record of *p* is contradicted and
    falls.
  - For every other tracked pair *q* = (s',t'): if some `clean_before` route
    s'→t' passes through an affected *k* (`reach*(s',k.s) and reach*(k.o,t')`
    over `clean_before`), then if `not reach(s',t',clean_after)` → *q* is
    **dead**, **required** if it was held and **permitted** either way; else
    *q* becomes **uncertain** and is **permitted** (the organism's one
    derivation may have rested on the dead route while another clean route
    survives). Pairs no affected link touches are unchanged and not
    permitted.
  - Dead pairs are untracked until a later YES ask holds them again.

Correct iff `required ⊆ reported ⊆ permitted`. The replayer *can* produce
this column by recomputing its own earlier answers; the column measures
held-state discipline, and the doc says so. The organism's `withdrawn`
(standing pids no longer ASSERTIVE, §8) is within these bounds, not equal to
`required`: on a pair with two clean routes it withdraws when the route it
derived through dies (permitted, not required), and a withdrawn pid leaves
`standing` so it is never reported twice.

## 6. Scoring unit, balance, lifetime

- **Unit: the ASK probe.** Every verdict/lacuna/contested cell is a fraction
  of probes; the withdrawn cell is a fraction of RETRACT/NEGATION events.
- **Balance** is computed at the probe level and reported per class: the
  fraction of probes with each expected verdict. No single verdict may exceed
  60% of probes in any class (warm-up probes that establish a held conclusion
  are mostly YES, so 50% is not achievable in R and C; 60% is the registered
  ceiling and the generator refuses sets that breach it, E-RS-007, judged in
  integers so 3/5 is admitted). The generator meets it by giving every
  variant a balancing probe — the "sound half" of a broken chain answered
  YES, or a reverse ask answered UNKNOWN/NO — none of which fires the class
  mechanism inside a control variant.
- **One `Organism` per `StreamItem`.** Tokens are drawn per item from
  `AA..ZZ`; sharing an organism across items would let item *k*'s leftovers
  create routes in item *k+j*. The runner instantiates per item.
- **E-RS-005** asserts the oracle's verdict equals the designed verdict on
  **every** probe of every item (controls included), not only the diagnostic
  probe; a mismatch rejects the item and redraws (64 attempts).
- **E-RS-006 fairness guard**: for every probe the generator counts simple
  routes `s→t` over the graph `^8` actually walks at that position — all
  non-negated positive records: `pos | contested | hyp | assoc` **plus** any
  pair the organism would hold as DERIVED from an earlier YES probe — and
  rejects the item if routes > 8 or longest > 6 (the bank's `limit` and
  `max_hops`, pinned by test to `HypothesisBank.surface`'s defaults). `^8`
  reads ACTIVE at the processor's defaults, so `limit=8`, not `limit//2`, is
  the operative bound. No failure may be attributable to a design constant
  rather than a mechanism.
- **ACCEPTED/REFUSED** on non-ASK events is recorded in the organism's
  `Response` and compared with the oracle's `refused` indices by the
  experiment's checks; it is not a scored cell.
- **Determinism.** Every set the organism, oracle or scorer emits (lacunae,
  contested, withdrawn, candidates, wants) is sorted before it reaches a
  `Response`, an `Expectation` or a fingerprint; pinned by repeat-run
  equality tests in each module.

## 7. Item classes

Four mechanisms, four classes; each class half diagnostic (the mechanism must
fire) and half control (it must not). `StreamDifficulty(hops=3, distractors=4,
probes_before=1, shadow=True, interleave=2)`; `hops ≥ 2` (E-RS-001);
`probes_before ≥ 1` for the stale variants (E-RS-002). Backbone chain
`c0→…→ch` over opaque tokens; one designated link `L`; when `shadow`, an
associative `co_occurs` shadow under `L`; `distractors` from spare nodes that
can never create or shorten a queried route; `interleave` unrelated facts
between perturbation and probe.

| class | mechanism | diagnostic variants | control variants |
|---|---|---|---|
| **R** retraction | transitive retraction of a *held* derivation | R-simple (retract L, probe); R-stale (probe YES, retract L, probe); R-deep (also hold intermediates) | R-control (retract an off-path distractor); R-revive (retract L, re-assert L, probe) |
| **H** hypothesis | the hypothesis/assertive firewall | H-bridge (L given only as HYPOTHESIS); H-refute (then NEGATION L) | H-control (full chain + off-path hypothesis); H-confirm (then FACT L) |
| **C** contradiction | assertive-only contradiction, localized | C-blocked (NEGATION L); C-stale (probe YES first, then NEGATION L) | C-bypassed (second clean chain exists); C-unrelated (negate a distractor) |
| **N** lacuna | open-world abstention with named gap | N-gap (L never given, shadow present) | N-control (complete chain, shadow on a present link); N-actionable (then FACT L) |

Class H's verdict column separates only a solver that promotes "maybe" to
evidence on ingest; `Workspace.derive`'s refusal of hypothesis support
(E-WS-002) is pinned by unit test, not by this family. The firewall's scored
product here is the `named` column on H-bridge and the absence of a dispute
on H-refute.

Paired worlds: `generate(seed, closed_world=False)` and `(…, True)` yield
byte-identical event streams; the oracle differs only by UNKNOWN→NO (and
emptied lacunae). Pinned. The rng never reads `closed_world`; acceptance is
judged in both worlds regardless of the one requested.

## 8. The organism's event handling

`Organism(profile=None, memory=None, *, closed_world=False, processor_kwargs=None,
motivation_kwargs=None, workspace_factory=Workspace)` owns ONE `Workspace`,
ONE `CognitiveMemoryBoard`, one `ReasoningProcessor`, a `Motivation`, a
`Heartbeat`. `consume(event) -> Response`.

- FACT → `ws.fact(...)` (a RETRACTED pid revives; its old consequences stay
  down until re-derived).
- HYPOTHESIS → `ws.hypothesize(..., stage="stream")` (the workspace's own
  rules make it dead on arrival against an assertive counter, and drop it
  against a stronger record of the same claim).
- NEGATION → `ws.fact(..., negated=True)`.
- RETRACT → by the status of the positive pid (same rule for a `co_occurs` pid):
  - absent, or RETRACTED → REFUSED `E-ORG-002`
  - HYPOTHESIS (or ASSUMPTION) → REFUSED `E-ORG-002` (a guess is not something you were told)
  - DERIVED, or CONTRADICTED **with non-empty support** (a derivation later
    denied) → REFUSED `E-ORG-001`, message names its roots ("that was
    derived, not given; it rests on …")
  - FACT, or CONTRADICTED with empty support (a *given* that is in dispute)
    → `ws.retract(pid)` → ACCEPTED. (The workspace reinstates the other side
    of a contradiction.)
- ASK → `processor.run_in(ws, Problem(name, relation, (), (s,t),
  closed_world=ws.closed_world), profile=motivation.profile())`. On CONCLUDED
  YES the conclusion pid enters `standing`. Lacunae are the episode's own
  (`ws.lacunae(since=mark)`, the mark FETCH recorded), reported only on
  UNKNOWN. Contested keys are those the COMMIT step named, reported only on
  INADMISSIBLE.
- After every event: `withdrawn` = standing pids no longer ASSERTIVE, sorted;
  each **leaves `standing`** (so it is reported once and the audit below
  never sees it). Within the §5 bounds, not equal to `required`.
- Every `consume` ends with `heartbeat.beat()`: CMB decay tick; motivation
  relaxes toward its constitution (rate ≤ 0.2); audit every pid **still in
  `standing`** — the pid and all `ws.roots(pid)` must be ASSERTIVE, else
  fault `E-ORG-003` "standing conclusion with dead root". A healthy organism
  never faults; `abl_no_cascade` and `abl_nontransitive_retract` do.

**Motivation** (`constitution: FoundationProfile`, mutable `g`, `relax=0.1`,
`beta=0.05`, both in `[0, 0.2]`, else `E-ORG-004`): NEEDS_INFORMATION raises
`g[F2]`; INADMISSIBLE raises `g[F6]`; CONCLUDED raises `g[F7]`, lowers
`g[F2]` by `beta/2`. **Engagement is constitutional, not moody:** the RPM
Desire gate reads `10·g[F2]` against `DEFAULT_SUFFICIENCY = 5.0`, so if the
constitution's `g[F2] ≥ 0.5`, perturbation and relaxation never take `g[F2]`
below 0.5. Without this, successes at `beta=0.2` would drop Wisdom-desire
under the gate and a later question would go unasked — a verdict depending
on mood. `wants()` = lacunae of episodes that ended NEEDS_INFORMATION still
unanswered in either polarity. When a FACT closes a want and `g[F2] ≥ 0.5`,
the organism re-asks on its own and reports `resolved`. Self-asks never
enter `standing` and are never scored.

**Hard law, tested non-vacuously:** the same stream under `beta=0` and
`beta=0.2` yields identical verdicts, lacunae and contested keys on every
ASK, while the two motivations demonstrably diverge. Motivation may change
*what is asked* and *how keenly*; it cannot reach `^6`/`^9`, by signature,
and the organism itself never calls a bank (a test greps its source).

## 9. Controls (each `(events, closed_world) -> ControlRun`)

One `Replayer` class parameterised by `Rules` (eight fields); every control
below is the headline with **exactly one** field flipped, pinned by
introspection. Headline first: `ctl_recompute` — two sets + in-order
add/discard + BFS per ask (+ `hyp`/`assoc` sets and two reflexive reach
passes for lacunae). 100% by construction; pinned. Under a closed world
`hyp`, `assoc` and both reach passes are dead code: two sets and a BFS.

Then, each labelled "oracle minus one rule":

- `ctl_order_blind` — final static graph; an ask sees the future. Fails
  exactly the probes whose verdict differs from the item's **final-state**
  verdict on the same pair: on R-stale that is the warm-up probe, not the
  diagnostic one.
- `ctl_no_forget` — RETRACT leaves `pos` untouched.
- `ctl_credulous` — HYPOTHESIS enters `pos` (and a refuted guess becomes a dispute).
- `ctl_last_writer` — a later polarity overwrites the earlier; nothing is ever contested.
- `ctl_global_poison` — any dispute anywhere refuses every ask.
- `ctl_mute` — never names a lacuna.
- `ctl_fixed_world` — always open world (the paired-set signature).
- `ctl_memo` — first answer per pair, never invalidated; fails exactly the
  probes whose verdict differs from the **first** probe on the same pair.
- `ctl_memo_flush` — memo cleared on any mutation; correct everywhere — the
  honest comparator for transitive retraction.

**Right for the wrong reason.** The per-variant table lists, for each broken
control, the probes it passes while lacking the mechanism (e.g.
`ctl_fixed_world` passes every open-set probe; `ctl_last_writer` passes
C-unrelated and C-bypassed), so a pass is never read as a mechanism.

## 10. Ablations (`Workspace` subclasses handed to `Organism(workspace_factory=…)`)

Each removes one rule at code level; `overrides` declares the surface touched
and a test asserts nothing else moved. The checked claim is **class-level
containment**: the failing cells lie inside the class (or column) the
ablation was built to expose and nowhere else; the probe-level failing set is
reported by the experiment, not pinned, because it depends on each variant's
probe layout.

- `abl_nontransitive_retract` — `retract()` without its cascade (the
  contradiction cascade stays). Expected inside R (R-stale, R-deep; R-revive
  if a probe sits between the retract and the re-assert). The audit faults.
- `abl_no_firewall` — a *told* HYPOTHESIS (stage `stream`) is filed as FACT;
  `^8`'s own bookkeeping is untouched. Expected inside H (H-bridge,
  H-refute, and the warm probe of H-confirm).
- `abl_last_writer_add` — `add()` lets the newcomer overwrite an assertive
  counterpart; nothing is ever CONTRADICTED. Expected inside C (C-blocked, C-stale).
- `abl_no_cascade` — `_cascade` is a no-op when the source pid is
  CONTRADICTED (the two calls in `add()`); explicit retraction still
  cascades. Expected inside C (C-stale). The audit faults.
- `abl_amnesic_ask` — `ask()` records nothing. Every verdict right; the
  `named` column fails wherever `required` is non-empty (N-gap).
- `abl_fixed_world` — the flag is accepted and ignored. Perfect on the open
  set; wrong on every closed-world probe whose verdict is rule 5.
- `abl_no_sweep` — `^8`'s route guesses are filed **unmarked** (stage `""`
  instead of `"^8"`), so the sweep finds nothing *and* the next walk does not
  skip them. Disabling `sweep()` alone changes nothing, because
  `HypothesisBank.surface` skips the mark unconditionally (measured, tested).
  Verdicts never change; the `named` column loses precision on a probe whose
  route passes through an earlier abstention's endpoints (reproduced by test
  through the organism). Whether the generated family contains that pattern
  is reported, not claimed.

## 11. Edge cases the generator never emits, and the oracle still defines

- NEGATION of a pair held only DERIVED (never given): oracle `neg.add`; the
  organism's workspace contradicts the derivation and cascades; a re-ask
  lands the route again and hits rule 1 — INADMISSIBLE on both sides. The
  withdrawn column at that NEGATION is **required** on both sides (§5).
- HYPOTHESIS then FACT then RETRACT on one pair: both forget the "maybe".
- RETRACT of a contested pair: ACCEPTED on both sides; the organism
  reinstates the denial.
- A guess about an **uncertain** pair (excluded by E-RS-010): the oracle keeps
  it; the workspace keeps it only if the derived record has already fallen
  (otherwise the stronger record absorbs it and it does not survive that
  record's later fall). Documented divergence outside the grammar.
- Contested links on a cycle through route nodes (never generated:
  distractors come from spare nodes): rule 3 is defined over simple routes,
  which is what `^8` surfaces; plain reachability would name more.
- No eager contradiction audit: a reinstated denial is re-tested the next
  time its pair is asked (the rule-1 landing path), so a second derivation
  hidden by reinstatement is caught at ask time, never earlier. Stated as
  the rejected alternative.

## 12. Amendments (2026-10-06, after the cross-check)

The judge stage of the design workflow was interrupted; an after-the-fact
cross-check (`scratchpad/contract_crosscheck.md`, 11 contradictions, 11 gaps,
11 overclaims, 24 audited streams) drove the live `Workspace` + `run_in`
against the §2–§5 oracle. On every §7 variant (96 streams, 187 probes) they
agreed. On edge streams the contract defines they diverged by construction.
Resolution, each adopted where the organism's behaviour was the principled
one and already pinned, or fixed in the runtime where it was not:

| finding | change | where |
|---|---|---|
| A1/A2 rule 2 before rule 4 contradicted Rule C and a pinned test | denial-with-no-route moved to rule 4 | §3, `controls.py`, `revision.py` |
| A3 runtime abstained on a given denial behind a partial route | consult the denial before `_prerequisite_stop` | `runtime.py` + test |
| A5 contested keys reported as lacunae; `G_all` dropped contested links | "a dispute is not a gap"; walk graph keeps contested links | §4, `workspace.lacunae` + test, `controls.py`, `revision.py` |
| A4 guess about a held derivation | HYPOTHESIS no-op when held; E-RS-010 | §2, `revision.py` |
| A6/C8 §5 YES-asks never aged; `standing` was one-shot | holding state held/uncertain/dead; withdrawn pids leave `standing` | §5, §8, `revision.py` (organism already so) |
| A7 RETRACT rule not exhaustive | RETRACTED → E-ORG-002; CONTRADICTED with support → E-ORG-001 | §8 (organism already so) |
| A8 hard law vs RPM Desire gate | engagement is constitutional (`g[F2]` floor) | §8 (organism already so) |
| A9 pair-space oracle vs relation-keyed workspace | grammar restriction; E-RS-009 | §1, `controls.py`, `revision.py` |
| A10/C5 `abl_no_sweep` changed nothing | ablation removes the stage mark | §10, `ablations.py` + tests |
| A11/B1 `contested_required` over `reach*`; cell bound unstated | simple routes; set equality | §3, §6, `controls.py` |
| B2–B11 | absorbed as stated sentences | §0, §3, §6, §7, §9, §11 |
| C1 balance ceiling | met by the generator's balancing probes; ceiling kept, judged in integers | §6 |
| C2 `ctl_order_blind` "staleness probes" | defined as final-state difference | §9 |
| C3/C4/C9 "fails exactly" for ablations | class-level containment checked; probe sets reported | §10, `revision_experiment.py` |
| C6/C7 §0 provenance and "can beat replay" | corrected | §0 |
| C10/C11 | wording | §4, §11 |
