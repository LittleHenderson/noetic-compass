# Dialectic Orchestration (Scaffolding)

Status: **plumbing only**. Real evaluation happens after Lever 3 lands a
better predictor and a real attractor scorer. Do not benchmark this
scaffold; it composes the existing K=9 47%-aggregate-paraphrase baseline
into a rotation pass and a score-and-pick pipeline. Multi-instance
dialog on a 47% base is noise. The scaffolding is here to lock the
INTERFACE so the real components drop in without restructuring.

Memory pointer:
`C:/Users/wakil/.claude/projects/.../project_three_instance_dialectic_proposal_2026_05_04.md`

---

## The rotating-axis pattern

Two CAS-Native instances run an internal dialog rotating through CAS
axes. Each rotation pair `(A_priming, B_priming)` is a structural
opposition along one of four axes:

- **Noetic involution** -- ^2/^3, ^5/^6, ^8/^9 (canonical pairs).
- **Domain extremes** -- P/O (precedence-order extremes); C/E (Cognitive
  vs Evaluative midpoint contrast).
- **Drive inversion** -- F1/F7, F2/F6, F3/F5 (per CLAUDE.md). F4 is
  self-dual and excluded.
- **Register inversion** -- T/E (transcendent vs embodied) and A/f
  (analytical vs affective). The four CAS v7.5 registers don't have a
  canonical involution, so the two oppositions are pragmatic.

A rotation produces two single-instance predictions. They get integrated
into a candidate `Attractor` representing the resulting `Omega_axis`
under that axis's tension. After running 1..N rotations, a third
"scorer" pass rates each attractor on CAS-native quality signals
(substance, relevance, admissibility, invariant_balance) and the
highest-composite attractor is rendered as the user-facing reply.

The architecture is NOT a multi-agent debate variant. The competitive
moat is the CAS-native attractor scoring (admissibility against the
real CAS compiler, structural-invariant balance per CLAUDE.md
involution / domain-precedence rules) instead of unstructured-text
scoring. Two attractor candidates with comparable substance get
disambiguated by structural correctness, not by another LLM's
preference.

---

## Module layout

```
cas-native/dialectic/
  instance.py        # CASInstance + AxisPriming
  rotator.py         # Rotation libraries + select_rotations()
  attractor.py       # Attractor + AttractorScore + integrate / score
  selector.py        # Top-K selection given scored pairs
  orchestrator.py    # DialecticOrchestrator + DialecticResponse
  tests/test_smoke.py
```

Each module type-hints its public API and is pure-Python (numpy / torch
are inherited from the underlying predictor only).

---

## Usage sketch

```python
from cas_native.dialectic import DialecticOrchestrator
from cas_native.inference.predict_cas import load_predictor

predictor = load_predictor(
    "cas-native/training/runs/structured-token-recoverable-paraphrase-"
    "v77fix-20epoch-gpu-20260502-1045"
)

orch = DialecticOrchestrator(predictor, max_rotations=2, top_k=1)
response = orch.respond("I keep practicing the same scale every day")

print(response.final_expression)   # CAS expression for the chosen attractor
print(response.final_english)      # NL rendering of the leading prediction
for line in response.rotation_trace:
    print(line)                    # per-rotation trace lines
```

---

## What is STUBBED vs REAL

| Component                | Real now | Stubbed (Lever 3)                 |
|--------------------------|---------|----------------------------------|
| Predictor I/O            | YES      |                                   |
| Axis-priming RECORDED   | YES      |                                   |
| Axis-priming APPLIED to model behaviour |   | needs logits intervention |
| Rotation libraries (4)   | YES      |                                   |
| `select_rotations` (rule)| YES      | learned classifier replaces it    |
| Attractor integration    | YES (conservative + / set_spec) |          |
| Substance score          | heuristic|                                   |
| Relevance score          | heuristic (rewrite_shim axis match) |          |
| Admissibility score      | YES (real `compile_expression`) |               |
| Invariant balance score  | YES (involution / domain / drive checks) |     |
| Top-K selection          | YES      |                                   |
| English rendering        | YES (cas_renderer)               |               |

The "Stubbed" column is the post-Lever-3 to-do list, not a list of
bugs. The scaffolding is consciously plumbing-only.

---

## How to plug in a real Lever 3 predictor

The `DialecticOrchestrator(predictor, ...)` constructor accepts any
callable that returns the K=9 prediction-dict shape (the 12 head outputs
documented in `cas_native.inference.predict_cas._decode_outputs`). To
swap in a Lever 3 predictor:

1. Update `predictor` so its `__call__` accepts an optional priming
   argument (e.g. `predictor(text, priming=AxisPriming(...))`).
2. In `instance.py`, replace the body of `CASInstance.predict` so it
   forwards `priming` to the predictor:

   ```python
   prediction = self.predictor(text, priming=active_priming)
   ```

3. Drop the `priming-stubbed` note from `notes`; once priming is real,
   the trace just records the priming-applied envelope.

Everything else (rotator, attractor, selector, orchestrator) stays
identical. The orchestrator is unaware of priming semantics; it only
hands them through.

For logits-level priming:
- `cas_native.inference.constrained_sampling` already implements logit
  masks for structured-token decoding. The pattern there is what the
  Lever 3 priming layer will reuse.
- `cas_native.inference.generate_samples_primed` shows priming-by-prefix
  as a degenerate baseline; Lever 3 should improve on it.

---

## How to extend the rotation library

Edit `rotator.py`. Each library is a `list[tuple[AxisPriming,
AxisPriming]]`. Add new pairs by constructing two `AxisPriming` objects
that disagree on one axis. Example -- adding a new Drive contrast over
F4 (self-dual) holding the rest fixed:

```python
ROTATION_F4_HOLD = [
    (AxisPriming(drive_bias="F4", noetic_bias=2),
     AxisPriming(drive_bias="F4", noetic_bias=3)),
]
```

To make `select_rotations` consider it, pass `libraries=[..., ROTATION_F4_HOLD]`.

To replace `select_rotations` with a learned classifier:

```python
class LearnedSelector:
    def __init__(self, model): self.model = model
    def __call__(self, query_text, k=2):
        logits = self.model.score_rotations(query_text)
        ranked = sorted(zip(ALL_ROTATIONS, logits), key=lambda r: -r[1])
        return [r[0] for r in ranked[:k]]
```

then the orchestrator can monkey-patch `select_rotations` or take a
`rotation_selector=` parameter (small refactor, deliberately deferred).

---

## How to swap the attractor scoring rubric

Edit `attractor.py`. The four sub-scorers are independent functions:

- `_score_substance(attractor) -> (float, notes)`
- `_score_relevance(attractor, query_text) -> (float, notes)`
- `_score_admissibility(attractor) -> (float, notes)`
- `_score_invariant_balance(attractor) -> (float, notes)`

Each returns a value in `[0, 1]` plus a list of trace notes.
Replace any of them in place; the contract is just the signature.

Composite weights are exported as `DEFAULT_WEIGHTS`. To re-tune at
runtime without code edits, pass `score_weights=...` to
`DialecticOrchestrator(...)` -- it forwards the dict into
`score_attractor`.

For a fully learned scorer, write a callable `score(attractor,
query_text) -> AttractorScore` and register it where
`score_attractor` is invoked in `orchestrator.respond`.

---

## Citations / connections

- **Du, Yilun et al. 2023.** *Improving Factuality and Reasoning in
  Language Models through Multiagent Debate.* (The "have multiple LLMs
  debate" pattern.) Our rotating-axis search is structurally distinct:
  we do not run unstructured text debate; we run targeted axis
  oppositions and integrate via CAS notation, not through natural
  language back-and-forth.
- **Marvin Minsky, *The Society of Mind* (1986).** Multi-agent cognition
  as a Society of K-lines / agents with specialised concerns. The four
  rotation libraries are CAS-axis-typed analogs to Minsky's specialised
  agents.
- **Hubert Hermans, dialogical self theory (1990s).** "I-positions" in
  internal dialog. Our two-instance dialog is operationally a two-I
  rotation; the third instance's role (scoring + selection) maps onto
  Hermans's "meta-position".
- **CLAUDE.md Clarification 10 (CAS v7.7).** Operator discipline for
  same-state multi-register expressions: `+` for co-presence, `x` for
  cross-register integration with explicit emergent result, `|<...>` for
  set-spec. The integration policy in `attractor.integrate_predictions`
  is a direct implementation of this discipline.

---

## Performance targets (orchestrator, not training)

- 1 rotation = 2 forward passes + 1 score = ~150 ms total on CPU with
  the K=9 baseline checkpoint.
- `max_rotations=2, top_k=1` (default) targets <500 ms wall-clock per
  query, in line with the platform-wide assessment latency target in
  CLAUDE.md.
- The orchestrator never trains, never checkpoints, never makes network
  calls.

---

## Smoke verification

```
cd noetic-compass-scaffold/noetic-compass
PYTHONIOENCODING=utf-8 python -m pytest cas-native/dialectic/tests/test_smoke.py -v
```

Expected: all tests pass in <30 seconds. Plumbing only -- no capability
claims.
