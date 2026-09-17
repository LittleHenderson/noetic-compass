# The four mandated corrections in the CNCM homebase

**Record:** `records/noetica_corrections_001/STATUS.md`
**Modules:** `cncm/simplex.py` (Correction 4), `cncm/noetica.py` (Corrections 1, 2, 3),
`cncm/inversions.py` (7-axis scanner)
**Architecture change as code:** `cncm/analytic_decompose.py`
**Tests:** `tests/test_simplex_metric.py` (50), `tests/test_noetica_laws.py` (35),
`tests/test_inversion_axes.py` (34), `tests/test_analytic_decompose.py` (31)
**Spend:** $0.00. Pure standard library. No model, no GPU, no provider, no checkpoint.

---

## What was there before, and what was not

Measured by searching the homebase source:

| pattern | hits in `cncm/`, `tests/`, `tools/` before this work |
|---|---|
| `fisher` | 0 |
| `simplex` | 0 |
| `geodesic` | 0 |
| `inversion` | 0 |
| `is_admissible` | 0 |
| section / retraction / counit | 0 |

The mandated mathematics lived only in the Rust engine at
`noetic-compass-scaffold/noetic-compass/cas-engine/src/metric/mod.rs` (23,347 bytes,
sha256 `66fcee7d8801e4fa9607789a802d495e01e528252f1375d2cf0bf154dfb72b10`), which is an
external read-only input. The CNCM homebase had none of it.

---

## CORRECTION 4 — open simplex and Fisher-Rao metric — IMPLEMENTED

`cncm/simplex.py`. The state space is `S°_I = Δ39° = { p ∈ R^40 : p_k > 0, Σ p_k = 1 }` and
distances use the Fisher-Rao metric.

Implemented and tested: `CognitiveStateVector` refuses any zero component, any negative
component, any non-finite component, a boolean component, and any vector not summing to 1
within 1e-9; `TangentVector` refuses a non-zero sum; `fisher_rao_inner_product` = `Σ u_k v_k /
p_k`; `fisher_rao_norm`; `bhattacharyya_coefficient` = `Σ √(p_k q_k)`; `geodesic_distance` =
`2·arccos(BC)` with the arccos argument clamped. `from_logits` refuses a softmax that
underflows onto the boundary rather than nudging it.

**The two implementations are cross-checked against each other.** The geodesic distance is
defined through `arccos` of the Bhattacharyya coefficient; the norm is defined through the
inner product. On a Riemannian manifold they must agree to first order:
`d(p, p + εu) ≈ ε‖u‖_p`. Nothing in either function enforces that, so the test that measures
it is real evidence that both encode the same metric.

**Three deliberate divergences from the Rust source are recorded rather than silently carried
over:**

1. That module is Rust and lives in a different project. This is an independent pure-Python
   implementation, not a binding. Nothing here imports it.
2. Errors raise `SimplexError` subclasses carrying the same reason names as the Rust
   `MetricError` variants, so a caller can map them one to one.
3. The Rust source tests a tangent vector's sum against a flat absolute tolerance. This
   implementation scales the tolerance by the vector's L1 norm, so a large tangent vector is
   not refused for a proportional zero. The reported `total` is always the raw sum, so a
   refusal quotes an exact number. A vector summing to 40.0 is refused under both rules.

The provenance claim is checked by a test that re-hashes the Rust file when it is reachable,
and skips when it is not.

---

## CORRECTION 1 — admissibility relations — PARTIAL, BLOCKED

`cncm/noetica.py`, section 1.

**Implemented:** the mechanism. `ADMISSIBILITY` holds one `AdmissibilityRelation` per
operator, each with a status, its pair set, its authority and a digest.
`is_admissible(operator, source, target)` is the guard the instructions require before every
operator application. `admissibility_profile()` reports the whole registry.

**Frozen:** `D0` only, taken verbatim from the master instructions —
`D0 = {(I, I) : I ∈ I}`, the identity on the diagonal only. Measured: exactly 40 pairs, all
on the diagonal, over the 40 cognitive states.

**Blocked:** the other nine relations. The instruction names the mechanism and states D0, but
states no `Dk` for `^1` … `^9`. This is the same `OPEN_SEMANTICS` condition the ledger already
records for system 4. They are **not invented**.

`is_admissible` **raises** `UnregisteredAdmissibility` for those nine rather than returning
`False`:

> "We do not know" is not "no", and a guard that silently refuses everything is
> indistinguishable from a guard that works.

`admissibility_status()` and `frozen_operators()`/`unresolved_operators()` let a caller
distinguish the two refusals deliberately. All nine relations have an empty pair set and
authority `NOT_FROZEN`, and a test asserts no pairs were invented for them.

**Also not done:** there is no call site. The instructions say to add the guard "before every
operator application", and the CNCM homebase has no operator application to guard. What
exists is the guard, the registry and the refusal semantics — not an applied correction. That
distinction is not softened.

---

## CORRECTION 2 — RPM is a section-retraction, not an adjunction — IMPLEMENTED

`cncm/noetica.py`, section 2.

`embed` is `η : I → R(I)`; `realize` is `ε : R(I) → I`. A `Realization` carries a label plus
the `context` that realizing it added, and `ε` forgets the context.

- **`ε ∘ η = id` is enforced.** A violation raises `SectionRetractionError`. It is not a
  warning and there is no permissive mode.
- **`η ∘ ε = id` is measured, never assumed.** `round_trip_is_identity(state, context)` is
  `False` whenever the realization carried context, and
  `section_retraction_witness` reports the exact `lost_context`. This is the whole content of
  the correction: re-embedding after realization may lose information.
- **The law that does hold is idempotence.** `η∘ε` is an idempotent projection, checked for
  every state and several context widths. That is the law a gate may rely on.
- **The gate caches initial satisfaction.** `PrerequisiteGate.satisfy` freezes a node's
  satisfaction the first time it is established; a later attempt raises
  `RefusesRecomputation`, increments a counter, and leaves the cached value untouched. A gate
  that silently re-derives is a gate whose answer depends on when it was asked.
- **Realization does not disturb the cache.** `realize_node` changes the node's realization
  while the cached satisfaction of its prerequisites stands. That is the asymmetry made
  operational, and a test asserts it directly.
- **Satisfaction is one-directional.** `PREREQUISITE` maps each node to its single
  prerequisite and has no reverse entry. `enables("A0", "D1")` is `True`; `enables("D1",
  "A0")` is `False`. `satisfied_chain` walks toward the root only.

The 22 capability pathways are laid out as `A0` + `D1-D7` + `W1-W7` + `P1-P7`, with
`rpm_chain(n) = (A0, Dn, Wn, Pn)`. Admission requires the node and every prerequisite, read
from the cache. The only way to clear a cache entry is `reset(node, reason=...)`, and the
reason must be non-empty.

### A label collision found while building this, recorded rather than resolved

`P1` … `P7` each name **both** a cognitive state (`P<noetic>`) and a pathway node
(`P<purpose>`). This is not a naming slip in this module: the master instructions enumerate
the 40 states as `P0-P9, C0-C9, E0-E9, O0-O9` and the 22 pathways as
`A0 + D1-D7 + W1-W7 + P1-P7`.

Seven labels are therefore ambiguous, and no rule for resolving them is invented here —
inventing one would be exactly the "unfrozen meaning" the ledger already flags. Instead the
label domain is explicit: `STATE_DOMAIN` and `PATHWAY_DOMAIN` are named, every function that
takes a label takes its domain, `AMBIGUOUS_LABELS` reports the seven, and `label_kinds`
reports which sets contain a label. A realization that does not say which set it belongs to is
refused by `realize`, so a pathway realization can never be realized as a cognitive state just
because the labels look alike.

---

## CORRECTION 3 — Noetic Coverage uses the counit — IMPLEMENTED

`cncm/noetica.py`, section 3.

`covering_morphism(covered)` builds `ε : R(I) → I` with
`direction = "TOWARD_COVERED_OBJECT"`. `is_covering(source, target)` is `True` exactly when
`source` is a realization of `target` and the morphism used is the counit. A covering in the
unit direction raises `UnitCoveringRefused` naming both labels, so Correction 3 cannot be
silently inverted. `covering_profile()` records `noetic_cov_3 = "counit"` and
`unit_direction = "REFUSED"`.

---

## Status of the four mandated corrections

| correction | status | evidence |
|---|---|---|
| 1 — admissibility relations | **PARTIAL, BLOCKED on an unresolved authority decision** | `cncm/noetica.py`, 12 tests; D0 = 40 diagonal pairs; nine relations `NOT_FROZEN`; no call site |
| 2 — section-retraction | **IMPLEMENTED** | `cncm/noetica.py`; section law enforced, asymmetry witnessed, idempotence checked, cache discipline enforced |
| 3 — coverage uses the counit | **IMPLEMENTED** | `cncm/noetica.py`; unit direction refused |
| 4 — open simplex, Fisher-Rao | **IMPLEMENTED** | `cncm/simplex.py`, 50 tests, provenance re-verified |

---

## `cncm/analytic_decompose.py` — the architecture proposal as executable code

`records/encoder_capacity_001/ARCHITECTURE_CHANGE_SPEC_v0.2_ANALYTIC_DECOMPOSE_INIT.md` is
**PROPOSED, not run**. Until now it was prose. This module is its arithmetic, and it is
tested.

It implements the two facts the proposal rests on:

1. **The registered module contains `x ↦ T·tanh(x)` exactly.** `parameters_for_map(T)` returns
   registered-shaped parameters with `left = I₆₄`, `right = 0`, `merge = [T | 0]`, and
   `identity_residual` returns **0.0** — the identity is exact, not approximate. A test also
   perturbs the right half of `merge` by 1e6 and confirms the output does not move, which is
   why the identity holds.
2. **The frozen readout is not a constraint.** `decompose_from_free_readout` solves
   `T = R⁻¹ Wᵀ`, and `realisation_score_residual` measures the violation of
   `r_c · forward(x) = W_c · tanh(x)`, which is of order 1e-14. A singular readout is
   **refused**, never approximated.

Two mistakes were made and caught by the tests during this work, and both are now pinned:

- A **row/column convention error**: `ridge_weights` returns `d × nclass` with column `c` the
  class-`c` weight, so the score vector is `Wᵀ φ`, not `W φ`. The first version used `W φ` and
  the score residual was 29.25 instead of 1e-14. `free_readout_scores` now documents the
  orientation and a test pins it against the row-wise product.
- A **double-tanh error**: `forward` applies `tanh` itself, so passing a feature `φ = tanh(x)`
  as the module's input applies it twice. `realisation_agreement` and
  `realisation_score_residual` now take **module inputs** and apply `tanh` on the free side
  only, and `test_forgetting_the_tanh_breaks_the_identity` pins the difference so the mistake
  cannot be read as a construction failure.

`shuffled_label_control` implements the arm-C null the spec requires: a deterministic
permutation from a caller-supplied seed, so a wrong solve's score can be measured. A test
asserts the wrong solve scores at most 4 of 64 on separable data, because without that bound a
right solve proves nothing.

`scope_declaration()` reports what the construction does **not** touch: parameter names,
shapes, plasticity scope, update ceiling, frozen encoder, frozen readout, the loss, the
curriculum. `new_parameters = 0`, `requires_gpu_for_the_solve = False`,
`requires_owner_record_to_run = True`.

**No run is proposed or authorised by this record.** Any run that changes the initialisation,
the loss or `max_updates` is claim-bearing and needs an owner-signed phase record.

---

## `cncm/inversions.py` — the 7-axis scanner, judged only where a limit is frozen

The 7-axis inversion scanner was absent from the homebase: `inversion` had **0 hits**. It is
the last large piece of the Rust engine with no counterpart here. It is now implemented, and
the way it is implemented is the point.

### The instruction freezes the structure, and one limit. It does not freeze thresholds.

Frozen, and therefore enforced:

| item | value |
|---|---|
| involution pairs | `CO-2↔CO-3`, `CO-5↔CO-6`, `CO-8↔CO-9` |
| self-duals | `CO-0`, `CO-1`, `CO-4`, `CO-7` |
| dial bounds | integer `3..9`, non-overridable |
| dial divergence limit | an involution pair cannot diverge by more than **4** points |
| drive pairs | `F1↔F7`, `F2↔F6`, `F3↔F5`; `F4` self-dual |
| domain tiers | `P ≻ C ≻ E ≻ O` |
| pathway chain | `A0 → Dn → Wn → Pn`, one-directional |
| compound | "multiple axes simultaneously" |

**Not frozen:** how much state-vector involution imbalance, domain-tier inversion, drive-pair
divergence, entropy deficit or cross-domain sub-drive variance constitutes a violation. The
instructions name each quantity and state no limit for it.

**No threshold is invented.** Each axis returns its raw measurement with `frozen_limit = None`,
and `exceeds_frozen_limit` is `None` — **not `False`** — because "no limit exists" and "within
the limit" are different answers and collapsing them turns an undecided threshold into a
silent pass. A caller that wants a severity supplies its own threshold through
`AxisMeasurement.exceeds(threshold)` and owns that decision.

**No NCCS score is produced.** The 15% inversion-resistance component needs thresholds that
have not been decided. A 15%-weighted number built on invented cut-offs would be a scoring
capability with no authority behind it, so `nccs_inversion_resistance` reads
`NOT_PRODUCED`.

**The compound axis cannot be reached from an unfrozen reading.** `P` is `True` only when more
than one axis exceeds a **frozen** limit. A test drives every measured-only axis to an extreme
— a state concentrated at `1e9 : 1e-9`, a drive at 1000, sub-drives at 0 and 1000 — and
confirms the compound flag stays `False`.

Per axis:

| axis | reading | limit |
|---|---|---|
| **N** | max &#124;dial(a) − dial(b)&#124; over the three frozen pairs | **4 dial points, frozen** |
| **N** (state vector) | relative mass imbalance per pair | none |
| **W** | count of adjacent tier inversions along `P ≻ C ≻ E ≻ O` | none |
| **F** | max &#124;F_a − F_b&#124; over the frozen pairs | none |
| **E** | `1 − H(p)/log 40`, from Correction 4 | none |
| **S** | largest population variance of one drive over the four domains | none |
| **A** | nodes satisfied before their prerequisites | **0, frozen by the chain** |
| **P** | more than one axis over a frozen limit | frozen definition |

Axis `E` is where this work pays off on the mandated mathematics: the entropy deficit is
computed on the open simplex from `cncm/simplex.py`, and because every component of a
`CognitiveStateVector` is strictly positive the entropy is always defined and always finite.
A test drives it with `[1e-12] * 40` and `[1e6] + [1e-6] * 39` to confirm.

Two readings of `N` are reported separately. `frozen_axes` names the axes that are **judged**
(an axis counts as judged when any of its readings has a frozen limit); `unfrozen_readings`
lists the specific readings without one, so `N`'s state-vector reading is not hidden behind
`N`'s dial reading. A test asserts both.

### The state-index authority, established rather than assumed

Building axis `W` exposed a real ambiguity. `cncm/simplex.py` says nothing about which of its
40 components corresponds to which state, and `inversions.py` initially assumed a noetic-major
layout while `cncm/noetica.py` enumerates the states domain-major
(`P0-P9, C0-C9, E0-E9, O0-O9`, per the instructions). Those two orders disagree, and the
disagreement would have been silent.

Resolved by giving the mapping exactly one home: `noetica.STATE_INDEX`, `noetica.state_at` and
`noetica.index_of`, with `simplex.py` carrying a pointer to it and stating that it fixes no
ordering of its own. `inversions.py` reads masses through `STATE_INDEX` by label rather than
by arithmetic on indices, so it cannot assume a layout. A test asserts the bijection onto
0–39, that the counts match `simplex.NUM_STATES`, and that a state concentrated on `C5` moves
the `C` domain mass and the `5` Noetic mass and nothing else.

### Status

**IMPLEMENTED as a diagnostic. NOT LICENSED as a scorer.** The scanner measures and reports;
it does not grade, and it deliberately refuses to emit the NCCS component that would require
unfrozen thresholds. Stealth — named in the NCCS weights as "7 axes + stealth + compound
severity" — has no definition in the instructions and is reported as
`ABSENT_FROM_THE_INSTRUCTIONS` rather than guessed.

---

## What this record does NOT claim

- **Correction 1 is not applied.** The guard exists; there is nothing to guard. Nine of ten
  relations are undecided. This is a partial implementation and is reported as one.
- **Passing tests are not a cognitive machine.** Per the homebase's own completion rule, a
  narrow passing test, a visible interface or a schema is not proof that the complete machine
  exists. What exists here is four sets of laws, guards and one closed-form construction — not
  a working CASFormer.
- **`inversions/` is no longer absent.** The 7-axis scanner is implemented as a diagnostic in
  `cncm/inversions.py`, with the frozen structure enforced and no threshold invented. It is not
  licensed as a scorer.
- **The label collision is recorded, not solved.** Whether `P1`-`P7` should be renamed, or
  namespaced, or whether the pathway graph should be re-expressed, is an authority decision.
- **The stealth axis is not implemented.** The NCCS weights name it and the instructions do not
  define it. It is reported as absent rather than invented.
- **Nothing here was trained, executed or measured on a device.** Every number comes from
  arithmetic on bytes already on disk.
