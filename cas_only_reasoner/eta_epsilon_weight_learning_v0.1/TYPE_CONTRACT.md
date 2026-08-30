# TYPE CONTRACT (Phase 0A corrected)

Function composition is read RIGHT TO LEFT: in `g ∘ f`, `f` is applied
first, then `g`. Formal maths and empirical approximations use different
symbols and are never silently mixed.

## Formal maps (source: ch05_legacy_collapse.tex) — no hats

    eta_X : X -> R(X)         section / embedding (split monomorphism)
    epsilon_X : R(X) -> X     retraction / realization (split epimorphism)
    epsilon_X ∘ eta_X = id_X

Rules:
- Composition order: in `epsilon_X ∘ eta_X`, `eta_X` is applied FIRST
  (embed), then `epsilon_X` (retract). The result is `id_X`.
  (Correction from Phase 0: the earlier draft wrote "eta . eta order",
  a typo; the composite in question is `epsilon_X ∘ eta_X`.)
- The other composite is NOT the identity: `eta_X ∘ epsilon_X != id_R(X)`.
- `epsilon` is a RETRACTION / split epimorphism, NOT a counit. No
  adjunction is assumed.
- The idempotent `P = eta_X ∘ epsilon_X` satisfies `P^2 = P` (a
  projection), for the EXACT formal maps only.
- The RPM monad `return` is a SEPARATE construction; do NOT identify it
  with the section `eta` without a separate typed bridge. A
  section-retraction is not, by itself, a monad.

## Empirical maps — hats, and their real types

    eta_hat  : desired CAS-coordinate change -> candidate neural
               intervention
    epsilon_hat : neural realization -> CAS behavior coordinate

- NEVER write `epsilon_hat ∘ eta_hat = id` for neural work. The most it
  can establish is
  `epsilon_hat ∘ eta_hat ≈ projection onto the reachable target
  subspace`.
- Exact `= I` is allowed ONLY for a declared finite-dimensional LINEAR
  map, under full rank, with lambda = 0 (see below).
- Do NOT reuse the retired CAS-Harness labels. There `eta` was a probe
  (hidden -> CAS class) and `epsilon` a prefix generator (CAS class ->
  prefix); those compose hidden->prefix, which is NOT an identity and
  INVERTS the formal direction.

## Pseudoinverse and projection facts (Phase 0A correction)

For a linear map `J : R^m -> R^k` with Moore-Penrose pseudoinverse `J+`:

- `J J+` is the projector onto the REACHABLE subspace in TARGET space
  (R^k). It equals the target-space identity `I_k` ONLY when `J` has full
  ROW rank.
- `J+ J` is the projector onto the parameter directions VISIBLE through
  `J` in SOURCE space (R^m).
- Both `J J+` and `J+ J` are exact idempotent projectors (symmetric,
  `P^2 = P`) for the exact Moore-Penrose inverse.

For the DAMPED (Tikhonov / ridge) right inverse
`J_lambda+ = J^T (J J^T + lambda I)^-1` with `lambda > 0`:

- `J J_lambda+` and `J_lambda+ J` are NOT, in general, exact idempotent
  projectors. `J J_lambda+ = J J^T (J J^T + lambda I)^-1` is a shrinkage
  operator with eigenvalues `s^2 / (s^2 + lambda) < 1`.
- Therefore, for any lambda > 0 or any nonlinear model, label the
  operator `LOCAL_DAMPED_REALIZER`, NOT an exact section-retraction
  projector. Call a projector `LOCAL_EMPIRICAL_PROJECTION` only when it
  is not the exact-linear full-rank case.

## Implementation names

    cas_readout            hidden state -> CAS coordinate
    cas_target_realizer    desired CAS change -> intervention
    activation_realizer    intervention -> activation change
    weight_update_realizer intervention -> effective weight change
    bridge_error           distance between target and observed CAS state
    response_residual      observed movement minus predicted movement
    reachable_fraction     fraction of a target direction reachable by the
                           chosen intervention space

## Coordinate rule

The readout emits a point on the open 40-state simplex (40 probabilities,
each > floor, summing to 1) = 39 independent directions. Do NOT invert 40
raw unconstrained coordinates. Use the frozen Fisher-Rao tangent chart
`FISHER_RAO_LOG_MAP_UNIFORM_HELMERT_V1` (see PREREGISTRATION §4). This
chart matches the declared Fisher-Rao geometry; CLR/ILR (Aitchison) are
NOT used. v0.1 controls ONE target direction inside that chart.
