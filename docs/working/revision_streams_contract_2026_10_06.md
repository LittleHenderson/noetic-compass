# Revision Streams — the semantic contract

**Date:** 2026-10-06
**Status:** binding on `scripts/cas_rpu/{organism,revision,controls,ablations,scoring}.py`.
Every rule here was fixed *before* any of those modules was written, and the
oracle in `revision.py` is its executable form. The organism is correct iff it
agrees with the oracle on every scored probe. Where this file and the oracle
disagree, the oracle is wrong.

---

## 0. The claim this family is allowed to make

Six independent adversarial reviews of the design each built a two-set BFS
that replays the event log and matched the oracle on every probe (one on
6,016 asks, another on 5,321, zero disagreements). The reason is structural:
ground truth over a finite event stream is a function of the stream, so
recomputing from the log is always a correct solver with no truth
maintenance in it. **No item in this family can separate a correct organism
from a correct replayer on correctness.** That is not a defect to fix; it is
B4 one level up, and it is stated first so nobody reads the matrix as more
than it is.

What the family *does* establish, and the only wording permitted:

1. **A convergence contract.** The organism — which holds beliefs across
   episodes, derives conclusions once and reuses them, and un-derives them
   when their support dies — agrees with recompute-from-scratch on every
   probe. That is the soundness of a *held-belief* reasoner, and it is not
   free: every ablation below breaks it.
2. **A diagnostic suite.** Each item class detects exactly one failure mode
   of a reasoner that holds beliefs, and each ablation of the organism
   reproduces exactly one. Every control is labelled for what it is: the
   recompute oracle with one rule deliberately broken.
3. **Cost.** The one axis on which incremental maintenance can beat replay.
   Per-ask work (workspace reads + association edge visits) is reported for
   the organism and the replayer as the stream grows, as a design
   measurement, with no empirical claim.

Forbidden wordings: "load-bearing" without "relative to the solver that lacks
it"; "necessary"; "superior". `ctl_recompute` is the **first row** of every
table and is pinned by test at 100% on every column it can produce.

## 1. Events

`events.Event(kind, subject, obj, relation)`; kinds FACT, HYPOTHESIS,
NEGATION, RETRACT, ASK; relations `leads_to` (the one chained over) and
`co_occurs` (associative: `^8` follows it, `^6` rejects it). Reflexive events
are refused at construction (E-EV-003).

## 2. Oracle state and transitions

Four sets of ordered pairs, replayed in stream order:

| set     | holds                                         |
|---------|-----------------------------------------------|
| `pos`   | positive `leads_to` pairs given and not since retracted |
| `neg`   | negated `leads_to` pairs given                |
| `hyp`   | hypothesised pairs not superseded             |
| `assoc` | `co_occurs` pairs given and not since retracted |

Transitions, each `ACCEPTED` unless stated:

- `FACT leads_to (s,o)`: `pos.add`; `hyp.discard((s,o))` (a guess confirmed
  is no longer a guess).
- `FACT co_occurs (s,o)`: `assoc.add`.
- `HYPOTHESIS (s,o)`: if `(s,o) in pos or (s,o) in neg` → **no-op** (a guess
  against a known fact or a known denial is dead on arrival). Else `hyp.add`.
- `NEGATION (s,o)`: `neg.add`; `hyp.discard((s,o))` (refutation). There is no
  negative retract in the grammar; `neg` only grows within an item.
- `RETRACT leads_to (s,o)`: if `(s,o) in pos` → `pos.discard` → ACCEPTED.
  Otherwise **REFUSED**, state unchanged. (Includes: the pair was never given;
  the pair is held only as a derived conclusion.) Retracting a *contested*
  pair — one in `pos & neg` — is ACCEPTED and leaves it merely denied.
- `RETRACT co_occurs (s,o)`: `assoc.discard` if present, else REFUSED.
- `ASK`: no state change; produces an `Expectation` (below).

## 3. The verdict for `ASK(s, t)`, `s != t`

```
contested = pos & neg
clean     = pos - contested
```

Evaluate in order; the first that applies is the verdict:

1. `(s,t) in neg` and `reach(s,t,clean)`   → **INADMISSIBLE**, contested_required = {(s,t)}
   (the chain is sound and the conclusion is denied as a given: a dispute about this exact claim)
2. `(s,t) in neg`                            → **NO** in both worlds (an explicit denial is knowledge, not a gap)
3. `reach(s,t,clean)`                        → **YES**
4. `reach(s,t, clean | contested)`           → **INADMISSIBLE**,
   `contested_required = { k in contested : reach*(s, k.s, clean|contested) and reach*(k.o, t, clean|contested) }`
   using **reflexive** `reach*` (so a disputed first or last link is included)
5. closed world                              → **NO**
6. open world                                → **UNKNOWN**, with lacunae (section 4)

`reach` is "there is a path of ≥1 edge"; `reach*` additionally holds for
`u == u`.

## 4. Lacunae (open world, UNKNOWN only)

```
G_all      = (clean | contested | hyp | assoc) - neg
admissible = { (u,v) in (hyp | assoc | {(s,t)}) :
               (u,v) not in clean, (u,v) not in neg,
               reach*(s,u,G_all) and reach*(v,t,G_all) }
required   = admissible & (hyp | assoc)
```

A reported lacuna set is correct iff `required ⊆ reported ⊆ admissible`. The
lower bound defeats "name nothing"; the upper bound defeats "name the whole
frontier product". A denied pair is never a lacuna. Lacunae are not scored on
YES, NO or INADMISSIBLE. Under a closed world the column is unscored
everywhere, and class N reduces to plain reachability — stated, not hidden.

Lacunae are keyed `s|leads_to|o`; the oracle works in pairs; `scoring.py`
converts.

## 5. Withdrawn (a capability column, not correctness)

After each RETRACT or NEGATION event at position *i*:

```
withdrawn_required  = { (s',t') : an earlier ASK whose verdict was YES,
                        reach(s',t',clean_before) and not reach(s',t',clean_after) }
withdrawn_permitted = { (s',t') : an earlier YES ask for which the affected pair
                        lies on some clean_before route: reach*(s',k.s) and reach*(k.o,t') }
```

Correct iff `required ⊆ reported ⊆ permitted`. The replayer *can* produce this
column by recomputing its own earlier answers; the column measures held-state
discipline, and the doc says so.

## 6. Scoring unit, balance, lifetime

- **Unit: the ASK probe.** Every verdict/lacuna/contested cell is a fraction
  of probes.
- **Balance** is computed at the probe level and reported per class: the
  fraction of probes with each expected verdict. No single verdict may exceed
  60% of probes in any class (warm-up probes that establish a held conclusion
  are mostly YES, so 50% is not achievable in R and C; 60% is the registered
  ceiling and the generator refuses sets that breach it, E-RS-007).
- **One `Organism` per `StreamItem`.** Tokens are drawn per item from
  `AA..ZZ`; sharing an organism across items would let item *k*'s leftovers
  create routes in item *k+j*. The runner instantiates per item.
- **E-RS-005** asserts the oracle's verdict equals the designed verdict on
  **every** probe of every item (controls included), not only the diagnostic
  probe; a mismatch rejects the item and redraws (64 attempts).
- **E-RS-006 fairness guard**: for every probe the generator counts simple
  routes `s→t` over the graph `^8` actually walks at that position — all
  non-negated pairs in `pos | contested | hyp | assoc` **plus** any pair the
  organism would hold as DERIVED from an earlier YES probe — and rejects the
  item if routes > 8 or longest > 6 (the bank's `limit` and `max_hops`). No
  failure may be attributable to a design constant rather than a mechanism.

## 7. Item classes

Four mechanisms, four classes; each class half diagnostic (the mechanism must
fire) and half control (it must not). `StreamDifficulty(hops=3, distractors=4,
probes_before=1, shadow=True, interleave=2)`; `hops ≥ 2` (E-RS-001);
`probes_before ≥ 1` for the stale variants (E-RS-002). Backbone chain
`c0→…→ch` over opaque tokens; one designated link `L`; when `shadow`, an
associative `co_occurs` shadow under `L`; `distractors` from spare nodes;
`interleave` unrelated facts between perturbation and probe.

| class | mechanism | diagnostic variants | control variants |
|---|---|---|---|
| **R** retraction | transitive retraction of a *held* derivation | R-simple (retract L, probe); R-stale (probe YES, retract L, probe); R-deep (also hold intermediates) | R-control (retract an off-path distractor); R-revive (retract L, re-assert L, probe) |
| **H** hypothesis | the hypothesis/assertive firewall | H-bridge (L given only as HYPOTHESIS); H-refute (then NEGATION L) | H-control (full chain + off-path hypothesis); H-confirm (then FACT L) |
| **C** contradiction | assertive-only contradiction, localized | C-blocked (NEGATION L); C-stale (probe YES first, then NEGATION L) | C-bypassed (second clean chain exists); C-unrelated (negate a distractor) |
| **N** lacuna | open-world abstention with named gap | N-gap (L never given, shadow present) | N-control (complete chain, shadow on a present link); N-actionable (then FACT L) |

Paired worlds: `generate(seed, closed_world=False)` and `(…, True)` yield
byte-identical event streams; the oracle differs only by UNKNOWN→NO. Pinned.

## 8. The organism's event handling

`Organism(profile=None, memory=None, *, closed_world=False)` owns ONE
`Workspace`, ONE `CognitiveMemoryBoard`, one `ReasoningProcessor`, a
`Motivation`, a `Heartbeat`. `consume(event) -> Response`.

- FACT → `ws.fact(...)` (a RETRACTED pid revives; its old consequences stay
  down until re-derived).
- HYPOTHESIS → `ws.hypothesize(..., stage="stream")` (the workspace's own
  rules make it dead on arrival against an assertive counter).
- NEGATION → `ws.fact(..., negated=True)`.
- RETRACT → by the status of the positive pid:
  - absent → REFUSED `E-ORG-002`
  - HYPOTHESIS → REFUSED `E-ORG-002` (a guess is not something you were told)
  - DERIVED → REFUSED `E-ORG-001`, message names its roots ("that was
    derived, not given; it rests on …")
  - FACT, or CONTRADICTED with empty support (i.e. a *given* that is in
    dispute) → `ws.retract(pid)` → ACCEPTED. (The workspace reinstates the
    other side of a contradiction.)
- ASK → `processor.run_in(ws, Problem(name, relation, (), (s,t),
  closed_world=ws.closed_world), profile=motivation.profile())`. On CONCLUDED
  YES the conclusion pid enters `standing`.
- After every RETRACT/NEGATION: `withdrawn` = standing pids no longer
  ASSERTIVE (exact, because the workspace cascade is transitive).
- Every `consume` ends with `heartbeat.beat()`: CMB decay tick; motivation
  relaxes toward its constitution (rate ≤ 0.2); audit every standing pid —
  all `ws.roots(pid)` must be ASSERTIVE given facts, else fault `E-ORG-003`
  "standing conclusion with dead root".

**Motivation** (`constitution: FoundationProfile`, mutable `g`, `relax=0.1`,
`beta=0.05`, both design values ≤ 0.2): NEEDS_INFORMATION raises `g[F2]`;
INADMISSIBLE raises `g[F6]`; CONCLUDED raises `g[F7]`, lowers `g[F2]`
slightly. `wants()` = lacunae of episodes that ended NEEDS_INFORMATION still
unanswered. When a FACT closes a want and `g[F2] ≥ 0.5`, the organism
re-asks on its own and reports `resolved`. Self-asks are never scored.

**Hard law, tested:** the same stream under `beta=0` and `beta=0.2` yields
identical verdicts, lacunae and contested keys on every ASK. Motivation may
change *what is asked* and *whether it engages*; it cannot reach `^6`/`^9`,
by signature.

## 9. Controls (each `(events, closed_world) -> list[Answer]`)

Headline first: `ctl_recompute` — two sets + in-order add/discard + BFS per
ask (+ `hyp`/`assoc` sets and two reflexive reach passes for lacunae). 100%
by construction; pinned. Then, each labelled "oracle minus one rule":
`ctl_order_blind` (final static graph; fails exactly the staleness probes),
`ctl_no_forget`, `ctl_credulous`, `ctl_last_writer`, `ctl_global_poison`,
`ctl_mute`, `ctl_fixed_world`, `ctl_memo` (first-answer memo never
invalidated; fails exactly probes whose verdict differs from the **first**
probe on the same pair in the item), `ctl_memo_flush` (memo cleared on any
mutation; correct everywhere — the honest comparator for transitive
retraction).

## 10. Ablations (Workspace subclasses / runtime flags)

`abl_nontransitive_retract` (fails exactly R-stale, R-deep);
`abl_no_firewall` (H-bridge, H-refute); `abl_last_writer_add` (C-blocked,
C-stale); `abl_no_cascade` (C-stale); `abl_amnesic_ask` (the `named` column
on open-world UNKNOWN probes); `abl_fixed_world` (the paired-set signature);
`abl_no_sweep` (self-triggering `^8`: the `named` precision column on probes
following an earlier abstention in the same item).

## 11. Edge cases the generator never emits, and the oracle still defines

- NEGATION of a pair held only DERIVED (never given): oracle `neg.add`;
  rule 3.1 then makes a re-ask INADMISSIBLE. The organism's workspace
  contradicts the derivation and cascades; its re-ask lands the route again
  and hits rule 3.1. Agree.
- HYPOTHESIS then FACT then RETRACT on one pair: both forget the "maybe".
  Documented.
- RETRACT of a contested pair: see §2; the organism reinstates the denial.
