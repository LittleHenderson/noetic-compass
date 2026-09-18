# DROP_IN_RESULT — the constraint layer is now a faithful drop-in, and the wiring is one import swap

**Round 41. The layer becomes installable without changing anything until it is switched on.**
**$0.00. Pure standard library plus the project's pure modules. No torch, no GPU, no model, no
training, no new run.**

Code: `cncm/answer_constraints.py` — `score_decisions` added.
Tests: `tests/test_answer_constraints.py`, **21 passing**, now exercised against **real packets**.

---

## 1. What was added

```python
def score_decisions(packet, scores, *, declared_constraints=False) -> dict
```

**A drop-in for `cas_meta2.typed_teaching.slots.score_decisions`.** With the flag off — the default —
it is exactly the run's own decoder. With it on, it applies the declared-constraint layer.

**Why a flag rather than a new function.** Round 40 measured that `binding._query_spec` reads kind,
field, group, scope, coordinates and symbols, and **never the decision contract**. So with the flag off
**nothing anywhere changes** — not one digest, not one score. That was measured across all 564 packets
and 2,598 slots in `measure_wiring_impact.py`. **Making the layer available while it is off costs
nothing; switching it on is the owner's call, and that call is now a one-line change.**

## 2. The faithfulness property, verified on real data

Two tests, both passing:

| test | what it establishes |
|---|---|
| `test_the_drop_in_is_the_runs_own_decoder_when_the_flag_is_off` | on **24 real packets with their real recorded scores**, `ac.score_decisions(p, s) == slots.score_decisions(p, s)` exactly, both with the flag omitted and with it explicitly `False` |
| `test_a_kind_without_rules_is_untouched_by_the_flag` | on **every real `role_set` record**, enabling the flag returns exactly the run's own decisions |
| `test_the_flag_moves_a_kind_that_has_a_rule` | on real `parts` records, enabling the flag **does** change decisions — so the flag is not inert |

Together those three pin the property that matters: **off is the run; on is the layer; and the layer
touches only the kinds it has measured rules for.**

## 3. Three faults found while building it, all recorded

**The module imported `cas_meta2` at load time**, which broke the property that the *rules* operate on
plain packet and plan dictionaries and must stay usable without the run's package. **The import is now
inside `score_decisions`**, and `test_the_rules_do_not_need_the_run_package` holds that.

**A module-level `pytest.importorskip` skipped the entire test file** — 1 test collected, 1 skipped.
Replaced with a targeted `skipif` and an explicit path insertion, so the faithfulness tests **run**
instead of skipping.

**Hand-built fixtures cannot exercise the run's decoder at all.** `slots.compile_slots` runs the full
packet validation and rejects them with `TYPED_SOURCE_PUBLIC_FIELDS`. The first version of the drop-in
test failed for exactly that reason, and the tests now use **real packets and real recorded scores**.
**This is the fifth round in a row where running against real artifacts found something a hand-built
fixture hid** — and this time it was the test that hid it, not the code.

## 4. Where this leaves the objective

| | |
|---|---|
| **the layer** | built, tested (**21 tests**), measured |
| **its benefit** | **+6.6194 points pooled** (34.6631% → 41.2825%), **+12.4861** on the many-decision half, **+0.0000** on the one-decision half |
| **its robustness** | gain is world-invariant (+6.5603% / +6.6785%), and not an exposure artefact |
| **its cost to install** | **one digest**, and the decisions. Nothing else. |
| **its availability** | **now a drop-in.** Off by default, byte-identical when off, verified on real packets |

**The remaining act is a switch, not a build.** `slots.score_decisions` is called in one place
(`learner._forward`); pointing that call at `answer_constraints.score_decisions(..., declared_constraints=True)`
is the whole change, and it is the owner's to make because it changes what the run's decoder does.

**NOT LICENSED, and unchanged:** that a run realises +6.6194 points. Every measurement ran **offline
against recorded scores**. A run would also re-learn the block under a changed `plan_digest`, and that
is not modelled anywhere in this record.
