# FINAL SUMMARY — eta_epsilon_weight_learning_v0.1 (Phases 1-8)

Read this with `CLAIM_BOUNDARY.md` and `AMENDMENT_LOG.md`. Numbers are
exact and come from `reports/*.json`. Status words are from the frozen
vocabulary.

## The one honest headline

On a small open-weight model (Qwen2.5-0.5B) and a narrow skill (passive
role binding), a hidden-state readout, a readout-guided weight update, a
proportional dose model, and readout-guided training **do work as a
generic interpretability-guided method** — but this study **dropped the
CAS-specific framing (B1)**, so it is **NOT evidence that CAS specifically
helps**. "Learn fast" appears only as "fewer examples on one narrow
skill," never the "hours from scratch" fiction.

## Claim ledger (final)

| claim | status | headline number |
|---|---|---|
| software_right_inverse | SOFTWARE_VERIFIED | 9/9 tests; exact right-inverse err 3e-16 |
| 1_readout | EMPIRICALLY_SUPPORTED (dev) | layer-12 probe AUROC 0.778 vs surface 0.667, +0.111 (95% CI [0.063,0.158]) on held-out vocab |
| 2_realization | EMPIRICALLY_SUPPORTED (directional) | guided LoRA edit beats random +5.2pp flip, collateral 0.73% |
| 3_dose | EMPIRICALLY_SUPPORTED (first-order) | r_eff 1.615, held-out nRMSE 0.008; but quadratic 8x better -> saturation |
| 4a_sample_efficiency | EMPIRICALLY_SUPPORTED (dev) | guided hits 0.90 at N=8; ordinary never reaches it |
| 4b_optimizer_efficiency | INCONCLUSIVE | not isolated |
| 4c_retention | EMPIRICALLY_SUPPORTED (via replay) | replay keeps active 0.944 vs 0.000 without it |
| 4d_wall_clock_efficiency | INCONCLUSIVE | overhead not measured |
| external replication | REPLICATION_OPEN | author rerun is internal only |

## The honest caveats, all in one place

1. **Not CAS-specific.** B1 was adopted (under /goal authorization)
   because role-binding's answer is surface-marked and there is no CAS-40
   labeler. So "CAS" is not load-bearing in these results. See
   `PHASE2_BLOCKER_DECISION_BRIEF.md`.
2. **Phase 2 first tried a bad readout label** (voice) that was
   surface-decodable (probe 1.0 = surface 1.0). The working readout is the
   model's own correctness, which is surface-resistant only because
   passive accuracy is 0.61 (not 0 or 1).
3. **Realization is directional, not full-strength.** One weight step
   fixes 5.6% (< the 10pp bar); magnitude is Phase 6's job.
4. **Dose is proportional only to first order** — real saturation at high
   dose.
5. **Retention fix (replay) is standard rehearsal**, not a CAS or novel
   mechanism.
6. **Small sweeps, dev seeds.** Phases 6-7 use N in {8,16,32}, 2 seeds.
   Not the full protected protocol.

## What genuinely came out of it

The mechanism chain is internally coherent and each link was tested and
either supported (with caveats) or honestly refuted:
- readout reads role-binding correctness above surface (1);
- its direction is causal for behavior at both activation (Phase 3) and
  weight (Phase 4) levels;
- dose->response is a clean first-order proportional law that saturates;
- readout-guided training is more sample-efficient and more stable than
  ordinary LoRA on this skill (4a);
- naive training forgets catastrophically (Phase 6) and replay fixes it
  (Phase 7).

That is a real, modest, honestly-bounded result on ONE narrow skill with
a small model — and explicitly not a demonstration of CAS-specific value
or of fast general learning.
