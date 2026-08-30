# TYPE CONTRACT

Formal maths and empirical approximations use DIFFERENT symbols. They
must never be silently mixed.

## Formal maps (source: ch05_legacy_collapse.tex) — no hats

    eta_X : X -> R(X)        section / embedding (split monomorphism)
    epsilon_X : R(X) -> X    retraction / realization (split epimorphism)
    epsilon_X . eta_X = id_X

Rules:
- `eta . eta` order: exact composite embeds FIRST (eta), then retracts
  (epsilon). `epsilon . eta = id_X`.
- The other composite is NOT the identity:
  `eta_X . epsilon_X != id_R(X)`.
- `epsilon` is a RETRACTION / split epimorphism. It is NOT a counit. No
  adjunction is assumed.
- The idempotent `P = eta . epsilon` satisfies `P^2 = P` (a projection).
- The RPM monad `return` is a SEPARATE construction. Do NOT identify it
  with the section `eta` unless a separate typed bridge proves it. A
  section-retraction is not, by itself, a monad.

## Empirical maps — hats, and their real types

    eta_hat  : desired CAS-coordinate change -> candidate neural
               intervention
    epsilon_hat : neural realization -> CAS behavior coordinate

Rules:
- NEVER write `epsilon_hat . eta_hat = id` for neural work. The most it
  can establish is:
  `epsilon_hat . eta_hat ~= projection onto the reachable target
  subspace`.
- `epsilon_hat . eta_hat = I` is allowed ONLY as an exact statement about
  a declared finite-dimensional LINEAR map when all rank conditions hold.
- Do NOT reuse the old CAS-Harness labels. In the harness, `eta` was a
  probe (hidden state -> CAS class) and `epsilon` was a prefix generator
  (CAS class -> prefix tokens). Those compose hidden->prefix, which is
  NOT an identity and INVERTS the formal direction. That naming is
  retired here.

## Implementation names (declare what they do)

    cas_readout            hidden state -> CAS coordinate
    cas_target_realizer    desired CAS change -> intervention
    activation_realizer    intervention -> activation change
    weight_update_realizer intervention -> effective weight change
    bridge_error           distance between target and observed CAS state
    response_residual      observed movement minus predicted movement
    reachable_fraction     fraction of a target direction actually
                           reachable by the chosen intervention space

## Projection labelling

Call `P` an exact section-retraction projector ONLY for an exact linear
map with full rank. For a damped inverse or a nonlinear model, label it
`LOCAL_EMPIRICAL_PROJECTION`.

## Coordinate rule

The readout emits a point on the open 40-state simplex (40 probabilities
summing to 1, each > floor). That is 39 independent directions. Do NOT
invert 40 raw unconstrained coordinates. Use one frozen 39-dimensional
tangent chart (chosen in Phase 0, see PREREGISTRATION). v0.1 controls ONE
target direction inside that chart.
