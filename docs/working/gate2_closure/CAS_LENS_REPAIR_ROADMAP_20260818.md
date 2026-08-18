# CAS output-lens → repair-loop — gated validation roadmap (2026-08-18)

**Principle:** validate link-by-link, reject-don't-repair. No layer is built into the
tests or the engine until its prerequisite passes its gate. This is the same discipline
that caught the surface-separability failure (`RESULT_TRACK_A_PILOT_G1_REJECTED.md`) —
extended across the reframe. See [[project_cas_output_lens_reframe]].

## Why not design it all at once
Every capability below is a statement about, or an operation on, CAS structure read from
an output. All of them depend on the **lens being non-arbitrary**. Building the residual /
RPM / steering layers before the lens is validated = elaborate machinery on a fiction
(the exact trap G1 caught). So the discoveries become a *sequence of gates*, not a design.

## Status of each piece
| Piece | In architecture? | Validated? |
|---|---|---|
| Hidden-state probing / ablation (Gate 1) | yes | yes (real Pythia) |
| Drive-local steering (repair mechanism) | yes | yes (cross-arch: Pythia + Qwen2.5) |
| Compiler / `cas predict` / CCDL notation | yes | round-trip is the asymptote |
| 40-simplex `Δ°₃₉` + Fisher-Rao + Noetic Topos | yes (formalized) | formal only, not empirical |
| RPM ontology (A0→Dn→Wn→Pn) | yes | ontology, not as a live localizer |
| Component/topology **recognition** (Field Manual) | no | no |
| CAS-Ohm quantification: `ΔI`, `R_hidden`, ASOM | no (WORKING DRAFT v0.1) | no |
| Recursive RPM → steer **repair loop** | no | no |

## The gated sequence
Each stage is built only after the one above passes.

1. **Lens non-arbitrary (flat 40-cell labels).** — L1/L3, **running now**.
   Gate: reader↔reader agreement > reader↔thesaurus (L1); readers split matched-surface
   pairs the thesaurus must tie (L3). Fail → honest stop.
2. **Lens at component/topology granularity.** Read text → circuit topology (rails,
   resistors, CJTs, feedback, test points), not just a cell.
   Gate: same convergence/discrimination, at the topology level (harder for a thesaurus,
   more meaningful). This is the *real* lens; flat labels are the necessary floor.
3. **Residual is measurable.** Can `I_obs` be read from behaviour/internals so that
   `ΔI = I_obs − I_pred` behaves? Gate: `ΔI` stays ~0 when aligned and moves the right
   way for a **known injected fault** (starve a leg / clamp a path and watch ΔI).
4. **RPM localization is non-arbitrary.** Recursive D→W→P scan on a failed bias finds the
   *first unmet prerequisite* — and identifies which leg (Desire/source-outside,
   Wisdom/flow-through, Power/capability). Gate: localization matches the injected root cause.
5. **Steering-repair closes the loop.** Steer the localized leg; recurse deeper if `ΔI`
   doesn't close (one-directional prerequisite satisfaction → fix propagates up). Gate:
   `ΔI` heals up after targeted steering vs a matched control steer. Steering mechanism
   already validated; this tests the *closed loop*, not the mechanism.

## Discipline notes carried from the manuals
- ASOM gates *which* repair: **Starved** → recurse-and-supply; **Misaligned** → reframe,
  not more supply. The residual adjudicates (wrong strategy → `ΔI` won't close).
- Topology exactness: **Drive/stimulus sits OUTSIDE the CJT** (source); **attention flows
  THROUGH** it (measured at a test point); bias controls inside; effect comes out.
- Aggregate hides compensating faults ("healthy parent total can mask an overloaded +
  a starved branch that cancel") → always probe children. = "aggregate metrics never get
  to be the audit."
- Honesty ceiling (all manuals): every number is a design score / observed rating, **not**
  a voltmeter reading from a model. The residual proves flow **consistency**, not semantic
  **correctness** — semantic correctness is what stages 1–2 establish.
- "Flexibility becomes manipulation when the knob has no stops": steering is licensed only
  to close a measured `ΔI` on a *detected* fault, and stops when closed.

## Recommended engine step (from the guide, deferred until gates pass)
Define a versioned CAS-Ohm calibration profile per model: V range, R components, `I_FS`,
residual tolerance, saturation ceiling, card-phase thresholds → a repeatable test spec.

**Current frontier:** Stage 1 (L1/L3). Nothing below it is built yet, by design.
