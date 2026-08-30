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
