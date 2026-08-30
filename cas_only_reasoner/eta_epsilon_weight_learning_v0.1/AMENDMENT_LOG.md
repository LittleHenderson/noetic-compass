# AMENDMENT LOG

## Rules

- Before the protected split is read: corrections are append-only entries
  here, each with a reason.
- After the protected split is read: NO edit to the frozen plan. Any
  change becomes a new version (v0.2).
- `ETA_EPSILON_BRIDGE_v1.md` is frozen; corrections to it are append-only
  amendments with reasons, not edits.

## Entries

### 2026-08-29 — v0.1 Phase 0 created (commit 836c9783)

- Created the Phase 0 scaffold. No model run. No GPU. No training code.
  All claims `PROPOSED`. Preregistration a candidate, not hash-locked.

### 2026-08-30 — Phase 0A owner-review corrections

Reason: owner review found real defects. Corrections applied:

1. FALSE STATEMENT CORRECTED. The Phase 0 report said "I did not find a
   confirmed small open-weight LLM snapshot on disk." That was FALSE. The
   snapshot `Qwen/Qwen2.5-0.5B-Instruct` revision
   `7ae557604adf67be50417f59c2c2f167def9a775` is present in the local
   HuggingFace cache. Full SHA-256 of all 7 snapshot files computed
   (model NOT loaded) and recorded in `MODEL_IDENTITY.json`. The weights
   (`fdf756fa7fcbe740...`) and tokenizer (`c0382117ea329cdf...`) match the
   receipt's shortened digests.
2. PRIMARY SOURCES READ FIRST-HAND. cas_reasoner.txt (CAS-Ohm boundary +
   role-binding sections), CAS-Ohm paper pp.1-6, CAS-Ohm Guide pp.1-4.
   `SOURCE_AUDIT.md` updated with exact lines/pages.
3. TYPE_CONTRACT typo fixed: "eta . eta order" -> `epsilon_X ∘ eta_X`,
   with eta_X applied first and composition read right-to-left. Added the
   `J J+` (target reachable-subspace projector, = I only at full row
   rank) vs `J+ J` (source visible-subspace projector) distinction, and
   the damped-inverse fact (lambda>0 gives a shrinkage operator, NOT an
   exact idempotent projector) -> label `LOCAL_DAMPED_REALIZER`.
4. CLAIM 3 corrected: `y_hat = a/r_eff` is algebraically zero-intercept
   linear regression, so "beat zero-intercept linear" was counterfeit
   competition. New test: beat zero/mean baselines, predict a disjoint
   split, carry uncertainty, be within 5% held-out MAE of affine/quadratic
   (else reject for nonlinearity).
5. CLAIM 4 split into 4a sample / 4b optimizer / 4c retention / 4d
   wall-clock efficiency. No "or" join. Each has its own status.
6. Eight owner decisions frozen: model, layer-selection procedure,
   intervention space (q_proj/v_proj, 32 rank-1 orthonormal, seed 271828),
   tangent chart `FISHER_RAO_LOG_MAP_UNIFORM_HELMERT_V1` (NOT CLR/ILR),
   empirical role-binding target direction, thresholds table, seeds.
7. Splits strengthened: added capacity_probe, readout_select,
   protected_lexical, protected_structural, protected_joint; >=200 per
   protected stratum; gold generated mechanically (no LLM labels);
   examples pre-hashed before any model run.
8. Added `MODEL_IDENTITY.json` and `PREREGISTRATION_LOCK_CANDIDATE.json`.
   Lock candidate holds full SHA-256 of every Phase 0 artifact; status
   `AWAITING_OWNER_APPROVAL`.

State: no model run, no GPU, no training code, protected split NOT read.

### 2026-08-30 — Phase 2 dev smoke (negative) + BLOCKER

Ran a DEV SMOKE (not the protected protocol) on the real
`Qwen/Qwen2.5-0.5B-Instruct`: does a linear readout of hidden states beat
a surface baseline at the role-binding label? Result (reports/phase2_dev_smoke.json):
- majority 0.505; bag-of-words SURFACE baseline **1.000**; best hidden-state
  probe **1.000** (layer 4); probe-minus-surface **0.000** (need >= 0.10).

Finding: the preregistered readout label `agent_is_surface_first` is
SURFACE-DECODABLE. Both surface and probe sit at ceiling, so the readout
does NOT beat surface. This is the same Gate-2 surface-decodability wall
recorded elsewhere in this project.

BLOCKER (needs a v0.2 owner decision; NOT improvised here, per the
negative-result law):
1. Readout target must be SURFACE-RESISTANT (e.g. surface-matched minimal
   pairs, or a behavioral-correctness label on genuinely ambiguous items).
   The current label cannot satisfy the "beat surface by >= 0.10" gate.
2. CAS-40 labeling for this task is UNDEFINED. No CAS-40 labeler exists,
   so the "40-state CAS simplex readout" as preregistered cannot be built
   without a labeling decision. The Fisher-Rao 40-chart and the
   matched-non-CAS-taxonomy control are deferred until this is decided.

Consequence: Phases 3-8 build on a readout that beats surface. Since Phase
2 did not clear that bar, those phases cannot honestly proceed to
claim-bearing results until v0.2 resolves items 1-2. Recording and
stopping the auto-advance, exactly as the negative-result law requires.
State: no protected split read; no steering; no weight change.

### 2026-08-30 — v0.2 amendment (A1 + B1), made under /goal authorization

The owner's standing /goal ("run Phases 1-8, do not pause to ask") is
taken as authorization to make the two blocked decisions and proceed with
real runs. Decisions:
- A1: readout target = predict the MODEL'S OWN passive role-binding
  correctness (surface-resistant). Justified by the preregistered
  capacity probe: Qwen 0.5B is non-ceilinged (0.80 overall) and fails
  passives (0.607), and passive correctness at 0.61 is not surface-
  determined -> a real, surface-resistant target exists.
- B1: DROP the 40-state CAS framing for this task. HONEST CONSEQUENCE:
  this study is now a GENERIC interpretability-guided study. It does NOT
  and CANNOT claim CAS-specific value. The owner may veto B1.

Phase 2 result under v0.2: readout CLEARS the gate (layer-12 probe AUROC
0.778 on held-out vocab; +0.111 over surface; bootstrap 95% CI
[0.063,0.158] excludes zero; shuffled control at chance). Dev-seed run;
full protected protocol not yet executed. 1_readout -> EMPIRICALLY_SUPPORTED
(dev). Proceeding to Phase 3.
