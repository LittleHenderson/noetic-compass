# Composition layer — the architectural answer to the measured decision-shape gap

**Status:** IMPLEMENTED as a component. **NOT LICENSED as a change to the registered course.**
**Module:** `cncm/composition.py`  **Tests:** `tests/test_composition.py` (26)
**Evidence:** `records/encoder_capacity_001/DECISION_STRUCTURE_RESULT.md`,
`answer_conjunction.txt`, `joint_binding.txt`
**Spend:** $0.00. Pure standard library. No model, no GPU, no provider, no target opened.
**Requires:** an owner decision on the boundary question in section 5 before anything is wired
into a run.

---

## 1. The measurement this answers

The recorded score decomposes **exactly** by the shape of the decision each kind requires —
nothing left over, at both cursors:

| cursor | recorded total | one decision | many decisions, one entity |
|---|---:|---:|---:|
| 0 | 39 | 30 | 9 |
| 160 | **189** | **174** | **15** |

| shape | questions | before | after | factor |
|---|---:|---:|---:|---:|
| **ONE DECISION** — `correspondence`, `reach`, `analogy` | 265 = 46.99% | 11.32% | **65.66%** | 5.80× |
| **MANY INDEPENDENT DECISIONS ABOUT ONE ENTITY** — `edge_account` 16 slots, `role_set` 6, `parts` 4, `context` 5, `definition` 3 | 299 = 53.01% | 3.01% | **5.02%** | 1.67× |

`admissible_answer_count` is **1** for every question of all five many-decision kinds, in both
arms at both cursors. Those slots are not sixteen questions. They are **sixteen readings of one
entity**, and the schema records that.

The forward pass emits one vector per slot and the readout takes an independent argmax per slot.
Nothing can force slot 3 to agree with slot 1, and nothing knows the sixteen edge slots describe
one graph. **The gap between 65.66% and 5.02% is the size of that inability.**

**And the two columns are inverted:** the machine scores **65.66%** where the answer is one choice
among *several* admissible answers, and **5.02%** where the answer is a *uniquely determined
fact*. Being told the answer is unique is the worse case, because uniqueness is exactly what this
architecture cannot exploit.

## 2. The two operations

`cncm/composition.py` supplies the missing mechanism. Both operations are structural; neither is
learned.

**Binding.** `Binding.commit(role, entity)` resolves an entity once and refuses a second,
different value with `BindingConflict`. The measured defect — `definition` cites the focus world
for one reference and a *different* world for the other in **70 of 70** answers — becomes a
refusal instead of a quiet disagreement. Re-committing the same value is allowed; the first
commitment always stands; a conflict counter records the attempt.

**Derivation.** `compose(kind, binding, structure, arguments)` returns a `Composition` naming
which slots were **derived** from the bound entity's declared structure and which remain the
network's. Per kind:

| kind | slots | derived from the bound entity |
|---|---:|---|
| `edge_account` | 16 | the whole edge reading — present and absent pairs over the declared nodes |
| `context` | 5 | `setting_ref`, `participants` |
| `definition` | 3 | `kind_ref`, `function_ref`, `whole` |
| `parts` | 4 | `contained_nodes`, from the supplied `whole` |
| `role_set` | 6 | **nothing** — its answer reads a supplied focal excerpt, which is an argument rather than a reading of the bound entity |

`role_set` is reported as undetermined rather than invented, and the one-decision kinds derive
nothing at all.

## 3. What it deliberately does not do

**It does not resolve the entity.** `compose` raises if the world role is unbound, with the reason
stated in the error: it derives readings *of a resolved entity* and does not resolve it. Deciding
*which* world a question is about stays the machine's job. That is the boundary.

**It does not read a packet, a target, or a model.** The caller adapts its own material into
`DeclaredStructure`. The module has no dependency outside `cncm.canonical`.

## 4. Two defects caught by tests rather than by inspection

Both are recorded because both are the kind that produce a plausible wrong object.

**The composition identity initially ignored which entity it was composed of.** `edge_account`
and `parts` derive node-pair readings, and the entity's own identifier never appears in them, so
two entities declaring coincidentally identical structure produced **the same digest**. A
composition is a composition *of* something, so `Composition` now carries the binding, and
`test_two_worlds_with_identical_structure_still_compose_differently` pins the distinction: the
derived values genuinely coincide, and the identities must not.

**`_plain` had no mapping branch**, so `edge_account`'s derived dict reached `as_dict` with its
nested tuples unconverted. The digest was unaffected — `canonical.to_primitive` handles mappings —
which is exactly why it survived until a test looked at the rendered value.

## 5. The boundary question, stated and NOT resolved

For four of the five many-decision kinds (`context`, `definition`, `edge_account`, and `parts`
given its argument) the query states `focus_world_id` directly, and the world's declarations are
in the packet. So the machine is being asked to **reproduce, by 64-way classification, an
identifier the question supplies and the document declares.**

That is a defect in the decision structure. It is **also** a boundary problem, and the boundary is
not mine to draw. Round 7 of this record already found a variant that crossed it — pre-selecting
the focus world's row into the *encoding* — and withdrew it as task deletion.

The two are different and the difference is the whole question:

| | what it does | effect |
|---|---|---|
| **Task deletion** | gives the machine the answer in its input | does not make the task easier; removes it |
| **A composition layer** | leaves the machine to resolve which entity the question is about, and requires the readings of that entity to be derived and consistent | removes an architectural inability, not the task |

If every one of those 34 slots is derived, the answer for 299 of 564 questions becomes a lookup of
material the question already points at. Whether that is the intended task, an unintended
consequence of the course contract's slot plan, or something the frozen contract already decides,
**is an owner decision and this record does not pre-empt it.**

## 6. Status of the component

| | |
|---|---|
| implemented | `cncm/composition.py`, 26 tests, all passing |
| licensed to run | **no** |
| wired into any run | **no** |
| changes the registered course | **no** — and wiring it in would, which is why it is not wired in |
| changes the plastic scope | **no** — it adds no parameter |
| authorises anything | **no** |

**Nothing here proposes to change the course contract, the loss, the encoder, the readout or the
update ceiling.** The module is a component with its own tests. Using it inside a run would change
what the run measures, and that requires the section 5 decision first.

## 7. What is NOT claimed

- **No accuracy claim.** Nothing here has been run against any evaluation. The 65.66% and 5.02%
  figures are the *recorded* baseline the gap is measured against, not a result of this module.
- **The kind-to-shape mapping is a reading of the schema**, taken from `answers.RULES`,
  `answers._ARGUMENTS` and the public slot plans. It is not a claim about the contract's intent.
- **The slot counts are the measured medians** from `answer_conjunction.txt`, and a test asserts
  the module's constants equal them; they are not re-derived here.
- **The role names are this module's own** and are not part of the frozen course contract.
- **`role_set` is not solved.** It derives nothing, so its 36 questions gain nothing from this
  module.
- **One arm, one seed** for every recorded figure. `MIXED_SAME_ITEMS`, seed `20260919`.
