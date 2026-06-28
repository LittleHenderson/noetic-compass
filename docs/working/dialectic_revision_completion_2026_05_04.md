# Dialectic v1 Sequencing Revision — Completion Note (2026-05-04)

## Deliverable

`docs/working/dialectic_v1_sequencing_revision_2026_05_04.md`

## 1. Word count

Approximately **2,150 words** (~310 lines). Within the 1500-2500 word
budget specified in the task brief. Sections present per the spec:

1. The revised sequencing
2. What "real implementation" means (vs scaffold)
3. The three deliverables for the real prototype (table)
4. Pre-committed pass / half-pass / fail
5. The first demoable use case (with trace rendering)
6. Sequencing relative to other v1 follow-ons
7. Long-term vs near-term framing

Plus an Appendix on residual risks.

## 2. Total dev days estimated for the prototype

**2.5-3.5 days of focused work, parallelizable.**

- D1 (logits-level priming): 1-2 days
- D2 (compiler-admissibility patch): 0.5 day
- D3 (v1 integration smoke test): 0.5 day

D1 and D2 touch disjoint files (predictor surface vs scaffold scoring),
so they can run in parallel. D3 gates on both. First demoable run
projected for **2026-05-08** — four days from this revision.

## 3. The single most controversial decision

**Dropping D2 from the scaffold report's 2-3 day estimate to 0.5 day,
on the basis of empirical compiler verification done during this
revision.**

Specifically: the scaffold report
(`docs/working/dialectic_scaffolding_report_2026_05_04.md`) lists Task 2
(real CAS-compiler-based admissibility scoring) as a 2-3 day item with
"gating dependency: the compiler grammar extension." During this
revision I ran four direct `compile_expression` calls against
`api.notation.compile_expression` from
`noetic-compass-scaffold/noetic-compass`:

| Expression | `valid` |
|---|---|
| `^3^P|⟨A,f,T⟩` (Unicode set-spec) | `True` |
| `^3^P|<A,f,T>` (ASCII set-spec) | `True` |
| `^3^P|A + ^3^P|f` (co-presence) | `True` |
| `^8^E_{F6} = Ω` (Omega) | `True` |
| `meta: ^8^E_{F6} = Ω` (renderer prefix) | `False` (`parsing@4: unexpected token ':'`) |

The grammar already accepts the set-spec form (both Unicode and ASCII)
and the co-presence form. The single real gap is the `meta:` prefix,
which is a renderer-only annotation and is fixed by stripping the prefix
before passing to the compiler. That is a one-line normalization in
`attractor._score_admissibility`, not a grammar extension.

The controversial part: this contradicts the in-place scaffold note
`"set_spec |<...> form not yet in compiler grammar"` and tells the
caller to delete a stale comment that the scaffold author left for
exactly this reason — to flag a known limitation.

Possible objections:

- **The compiler may accept the literal but reject it semantically
  later.** I did not run admissibility checks under all 40 cognitive
  states or all 7 drives; only the surface form was verified. The
  revision should be re-checked against a broader expression set during
  D2 to make sure `valid=True` holds across the production range, not
  just on the 4 examples I tested.
- **The scaffold author may have been working against an older compiler
  pin.** The compiler in the scaffold tree
  (`noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`,
  5813 lines) clearly shipped the Clarification 10 set-spec grammar
  ahead of when the dialectic scaffold was written. Different compiler
  pins in different worktrees could explain the disagreement; D2 should
  start by confirming pin consistency.
- **Aggressively shrinking D2 makes the 2.5-3.5 day total feel
  optimistic.** That's the right concern. The mitigation is the
  pre-committed pass/fail in Section 4 of the revision: if D3 reports
  FAIL on day 3, we slip the demo, not the gate.

I am confident in the call but not so confident I'd skip the broader
expression sweep at the start of D2.

## 4. Is the user's request to move from "Year 2" to "near-term"
   achievable as proposed?

**Yes, conditional on three gates.**

| # | Gate | Risk if unmet |
|---|------|---|
| 1 | v1 retrain lands at ≥60% free-form coverage by ~2026-05-05 03:00 PDT | Multi-instance dialog remains noise; prototype slips to v2 retrain (no D1/D2 rework) |
| 2 | Additive logit bias actually flips the per-head argmax under inverted primings on at least one demo prompt during D1 | Escalate to temperature modulation in D1.5; +1 day. If even that fails, prototype bumps back into multi-week territory |
| 3 | The compiler accepts the production range of dialectic-emitted expressions, not just the 4 examples I verified | D2 grows from 0.5 day to 1-1.5 days; total slips to 3-4 days |

If all three gates clear, the revised plan is achievable as proposed,
with first demoable trace on the v1 checkpoint by 2026-05-08.

If gate 1 fails, the prototype slips cleanly — D1 and D2 are
predictor-version-agnostic and survive intact for whichever predictor
version eventually clears the coverage threshold.

If gate 2 fails, the FAIL branch in Section 4 of the revision is the
honest call; we identify the failure on day 3 of the build, not month 12
of the project, which is itself a win over the original Year 2
sequencing.

If gate 3 fails, the slip is small (half-day to 1-day) and absorbed by
the parallel D1 work.

**Bottom line: the move from Year 2 to near-term is achievable, the
prototype is realistic, and the gates are tight enough to falsify the
plan inside one week if any of the assumptions break.**

---

## Files touched by this work

- **Created:** `docs/working/dialectic_v1_sequencing_revision_2026_05_04.md`
- **Created:** `docs/working/dialectic_revision_completion_2026_05_04.md`
  (this file)
- **Read-only references:**
  `noetic-compass-scaffold/noetic-compass/cas-native/dialectic/`
  (entire scaffold tree, 1995 LOC),
  `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py`,
  `noetic-compass-scaffold/noetic-compass/cas-native/inference/predict_cas.py`,
  `noetic-compass-scaffold/noetic-compass/cas-native/inference/cas_renderer.py`,
  `docs/working/dialectic_scaffolding_report_2026_05_04.md`,
  `docs/working/lever3_script_completion_2026_05_04.md`,
  `CLAUDE.md` (Clarification 10).
- **No code modified.** Per task constraints (READ-ONLY research /
  planning).
