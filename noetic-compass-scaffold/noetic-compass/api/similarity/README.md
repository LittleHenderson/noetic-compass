# CAS Expression Similarity — Sprint 1 Design (Idea Atlas)

Status: reference implementation, Sprint 1 (Agent G). Consumed by the Idea
Atlas graph layer (Agents E / F / H) to decide which Ideas are
"structurally close" so the front-end can later draw edges between them.

This is intentionally a small, transparent metric: a weighted cosine over
five fixed-shape feature vectors extracted from the compiled CAS artifact.
It is not a learned embedding, not a semantic-text similarity, and not a
production-yield similarity. Future work (out-of-scope below) explicitly
flags the richer comparisons we plan to add.

CAS framework version: v7.4-v7.7 (Noetics, Domains, Drives, Registers,
production-semantics primitives, named meta-sets). The 40 Cognitive States
(10 Noetics x 4 Domains), 7 Drives (F1-F7), and 4 Registers (T / A / f / E)
are the canonical primitives named in `CLAUDE.md` and
`docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`. This metric does NOT introduce
new primitives; it consumes the existing AST surface produced by
`api.notation.compiler.compile_expression`.

## Input / Output

**Input.** Two CAS source strings (or, for the lower-level
`extract_features`, two already-compiled artifact `to_dict()` payloads).

**Output of `cas_similarity(expr_a, expr_b)`.** A dict:

```
{
  "score":     float in [0, 1],           # weighted cosine, 1 == identical
  "breakdown": {
    "noetic":   float in [0, 1],          # cosine over Noetic vector
    "domain":   float in [0, 1],          # cosine over Domain vector
    "drive":    float in [0, 1],          # cosine over Drive vector
    "register": float in [0, 1],          # cosine over Register vector
    "metaset":  float in [0, 1],          # cosine over MetaSet bag vector
  },
  "weights":   {"noetic": ..., ...},      # the weights used for the score
  "valid_a":   bool,                      # compile_expression(expr_a).valid
  "valid_b":   bool,                      # compile_expression(expr_b).valid
}
```

If either expression fails to compile (`artifact.valid is False`) the
function returns `score=0.0` and zero-valued breakdown components, with
`valid_a` / `valid_b` indicating which side failed. This matches the Idea
Atlas requirement: an unparseable expression cannot be placed in the
similarity graph at all.

## The Five Feature Vectors

Vectors are extracted by walking the serialized AST (output of
`compile_expression(src).to_dict()["ast"]`) and counting occurrences of
each canonical primitive. We count the AST in source-occurrence order;
duplicated primitives count multiple times (e.g. `^2 * ^2` produces a
Noetic vector with 2 in the `^2` slot, which is structurally meaningful).

| Vector       | Shape   | Slots                                          |
|--------------|---------|------------------------------------------------|
| Noetic       | 10      | `^0` .. `^9` (CO-0 .. CO-9)                    |
| Domain       | 4       | `P`, `C`, `E`, `O` (Principled / Cognitive / Evaluative / Operational) |
| Drive        | 7       | `F1` .. `F7`                                    |
| Register     | 4       | `T`, `A`, `f`, `E` (Transcendent / Analytical / Affective / Embodied) |
| MetaSet bag  | dynamic | bag-of-names: `Noetics`, `Domains`, `Drives`, `Registers`, `States`, `NoeticCluster`, `StateCluster`, ... |

Counting rules per vector:

- **Noetic.** Increment the `CO-n` slot for every `StateLiteral` and every
  Noetic element inside a `TypedMetaSetLiteral` whose `element_type` is
  `noetic`, `state`, or `state_variant`. (A `StateLiteral` always names
  exactly one Noetic; a typed `NoeticCluster{^2,^7}` names two.) Pure
  drive primitives, RPM calls, and recipe targets contribute zero here.
- **Domain.** Increment the `P/C/E/O` slot for every `StateLiteral` whose
  `domain_explicit` would be true at AST level — concretely, whenever the
  serialized `domain` field is present AND the source was not bare `^n`.
  We approximate this from the serialized AST by counting an explicit
  domain only when the original source token included the domain (the
  serializer always emits a default `P` for bare `^n`, so we additionally
  consult the source string heuristically; see the implementation's
  `_state_has_explicit_domain` helper). For `state` / `state_variant`
  meta-set elements, all elements carry an explicit domain by parser rule,
  so each contributes.
- **Drive.** Increment the `F_k` slot for every `DriveLiteral` and for
  every `StateLiteral` whose `drive` field is non-null. RPM calls
  (`RPM(F5)`) contribute via their inner `DriveLiteral`.
- **Register.** Increment the `T/A/f/E` slot for every register surfaced
  on a `StateLiteral` or `DriveLiteral`, including each entry of a
  `register_set` (CAS v7.7 `|<R1,R2,...>` form). `drive_register` and
  `drive_register_set` count too.
- **MetaSet bag.** Increment a slot keyed by name for every
  `MetaSetLiteral` (`Noetics`, `Domains`, `Drives`, `Registers`, `States`,
  custom `Foundation_n`, ...) AND for every `TypedMetaSetLiteral`'s
  constructor (`NoeticCluster`, `StateCluster`, `RelationCluster`, ...).
  This is the only vector whose dimension is dynamic; cosine is computed
  over the union of names (missing names => 0 in that side's vector).

## Default Weights

```
noetic   = 0.40
domain   = 0.20
drive    = 0.20
register = 0.10
metaset  = 0.10
                ----
                1.00
```

Reasoning:

- **Noetic gets the largest weight (0.40).** The 10 Noetics are the
  authoritative primitives of the CAS framework — they describe *what*
  the cognitive operation is. Two ideas that share Noetics but differ in
  Domain are still structurally about the same dynamic (e.g. `^2^P`
  principled attraction vs `^2^C` cognitive attraction are both `^2`
  attraction). Two ideas that share a Domain but differ in Noetic are
  about completely different dynamics (e.g. `^2^P` attraction vs `^3^P`
  aversion in the same domain).
- **Domain (0.20) and Drive (0.20) are co-equal second tier.** Domain
  specifies the precedence tier (P > C > E > O); Drive specifies the
  motivational architecture. Both are structurally important but
  subordinate to the Noetic identity of the operation.
- **Register (0.10) is tertiary.** Register is optional in v7.5 and absent
  in v7.4 expressions. Many expressions in the corpus omit it, which
  would over-penalize register-neutral comparisons if weighted higher.
  When neither side specifies a register, the register vectors are
  zero-on-both-sides; see "Vacuous-axis renormalization" below for how
  that case is folded into the composite score.
- **MetaSet bag (0.10).** Helps cluster meta-logic expressions
  (`^2 in Noetics` vs `^7 in Noetics` should share the `Noetics` name)
  but is the lowest-resolution signal — many distinct ideas reference
  the same canonical set names.

These weights are tunable via the `weights` parameter of `cas_similarity`.
The defaults are the Sprint 1 starting point; they will be revisited
after the Idea Atlas graph has empirical data on edge quality.

### Vacuous-axis renormalization

An axis is **vacuous** for a given pair of expressions when both sides
have an all-zero vector on that axis. (E.g. comparing two register-
neutral expressions makes the register axis vacuous; comparing two
expressions with no drive primitives makes the drive axis vacuous.)

A vacuous axis carries no information — both expressions made the same
(null) commitment on that axis. Including its weight in the denominator
of the weighted average would penalize agreement-on-absence, which is
the wrong direction.

Sprint 1 handles this by **excluding vacuous axes from the weighted
average and renormalizing the remaining weights so they sum to 1.0**:

```
score = sum(w_axis * cosine_axis for axis in axes if not vacuous(axis))
        / sum(w_axis            for axis in axes if not vacuous(axis))
```

If every axis is vacuous on both sides (two structurally empty
expressions) the metric returns 1.0 by convention. If a single axis is
non-vacuous, the metric collapses to that axis's cosine.

Consequences worth knowing:

- Two identical register-neutral expressions score 1.0 (not 0.9).
- `^2` vs `^7` (disjoint Noetics, both default-P, no drives, no
  registers, no meta-sets) drops the drive / register / metaset axes
  and computes `(0*0.4 + 1*0.2) / 0.6 = 1/3 ≈ 0.333`.
- `^2^P` vs `^2^C` (shared Noetic, disjoint Domain) drops the same three
  axes and computes `(1*0.4 + 0*0.2) / 0.6 = 2/3 ≈ 0.667`.
- Adding a register to one side and not the other un-vacuates the
  register axis on both sides (one zero vector vs one non-zero vector
  has cosine 0), so the score moves toward zero rather than staying
  flat. This is the desired behavior: a register-bearing expression and
  a register-neutral expression are *not* the same Idea structurally.

## Inversion-Pair Semantics (Open Research Question)

CAS v7.4 establishes three Noetic involution pairs:
`^2 / ^3` (Positive / Negative), `^5 / ^6` (Female / Male), and
`^8 / ^9` (Above-Cause / Below-Effect). The remaining four Noetics
(`^0`, `^1`, `^4`, `^7`) are self-dual.

**Question.** Should an expression containing `^2` be MORE similar to one
containing `^3` (because they share an involution axis) or LESS similar
(because they are structural opposites)?

**Sprint 1 default decision.** Treat the two Noetics as DISTINCT with no
proximity bonus and no penalty. The Noetic vector slots `^2` and `^3` are
orthogonal in cosine space, exactly like any other two distinct Noetics.

**Reasoning.**

1. **Conservative starting point.** Any non-orthogonal coupling between
   `^2` and `^3` is an opinion about what "structural similarity" means
   in the framework. The framework itself names the pair as an
   *involution* (a duality), not as a proximity. Encoding either polarity
   into the metric without empirical justification would bake an
   editorial choice into the math.

2. **Different use cases want different answers.**
   - For an *AI-safety incident clustering* use case (group cases by what
     went structurally wrong), `^2`-misalignment and `^3`-misalignment
     are different failure modes; treating them as similar would hide the
     distinction.
   - For a *teaching-material grouping* use case (group lessons that
     teach an involution pair together), treating them as similar is
     desirable.
   - For a *production-recipe substitution* use case (find recipes that
     could swap an inverted prerequisite), an explicit anti-similarity
     (penalty) might be the right answer.

3. **The colloquialism test agrees with orthogonality.** "Drawn to it
   like a moth to a flame" (`^2`) and "rubs me the wrong way" (`^3`) are
   not paraphrases of each other. They name opposite dynamics. Cosine
   orthogonality (no bonus, no penalty) matches the colloquial intuition
   that the two are about a *shared axis* but are distinct positions on
   it.

**Configurable knob (Sprint 1+).** The `cas_similarity` weights dict
accepts an optional `inversion_policy` field with three values:
`"neutral"` (default — orthogonal, current behavior), `"merge"`
(treat `^2` and `^3` as the same slot for the Noetic vector — merges
involution pairs), and `"penalize"` (subtract a small constant from the
Noetic-component score when both sides have ONLY their inverted partner
present and otherwise equal context). The default is `"neutral"`; the
other two are wired in as one-line behavioral toggles for downstream
agents to evaluate empirically.

## Out-of-Scope (Sprint 1 — Future Work)

The following structural comparisons are intentionally NOT in the Sprint 1
metric. They are listed here so consumers don't expect them and so future
sprints have a clear next-target list:

1. **Production-yield similarity (`Y_T(Omega)` for the same `Omega`).**
   Comparing two recipes that target the same production target by
   theoretical-yield magnitude, limiting-reagent identity, or efficiency.
   This requires execution by the Rust cas-engine (the Python compiler
   parses but does not evaluate yield expressions). Future work: a
   `cas_similarity_yield(recipe_a, recipe_b, target=Omega_x)` companion.

2. **Foundation / SubFoundation overlap.** The 28 Domain-Specific Drives
   (`F_k^D`) and the broader Foundation_n meta-sets (`F_1|T in
   Foundation_1`, etc.) carry richer overlap structure than a flat
   bag-of-names captures. Future work: a typed Foundation similarity
   sub-vector that respects the F-vs-F^D distinction and the Foundation
   group structure.

3. **Register-pattern temporal sequencing.** The activation list returned
   by `artifact.activations()` is per-position in source order and carries
   register-set metadata. Sequence-aware similarity (e.g. dynamic-time-
   warping over register patterns, or n-gram overlap of consecutive
   `(position, register_set)` pairs) would distinguish two expressions
   that have identical bag-of-Noetics counts but different temporal
   arrangement. Sprint 1 explicitly throws this information away (the
   five vectors are bag-of-counts, position-agnostic). Future work: a
   `cas_similarity_sequence(expr_a, expr_b)` that consumes the
   activation list directly.

4. **RPM chain / pathway overlap.** The 22 Capability Pathways
   (`A0 -> Dn -> Wn -> Pn`) form a partial order; two RPM calls that
   target related drives in the same pathway tier are arguably more
   similar than the bag-of-Drives count captures.

5. **Inversion-pair coupling beyond the toggle.** The `inversion_policy`
   knob above is a coarse instrument. A learned coupling matrix over the
   10 Noetics (with the involution pairs as one structural prior) is a
   richer answer that would be appropriate once we have ground-truth
   similarity labels from the Idea Atlas user-feedback loop.

## Determinism and Performance

- Pure stdlib (no NumPy, no SciPy). All vectors are `list[float]`.
- One `compile_expression` call per side. Compilation is the dominant
  cost; the cosine math is O(dim) over four small fixed-size vectors plus
  one variable-size bag.
- Deterministic: same inputs always yield the same output to full
  floating-point precision.
- Re-entrant / thread-safe: no module-level mutable state.
