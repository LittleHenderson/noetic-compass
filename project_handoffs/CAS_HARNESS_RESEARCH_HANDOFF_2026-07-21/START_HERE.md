# CAS Harness Research Handoff — 2026-07-21

This folder is the durable, dated handoff for the CAS Harness work completed through 2026-07-22. It is a copy-based evidence box: original files remain in the repository, `C:\tmp`, the protected implementation checkout, and the owner's Downloads folders.

If you are new to the project, begin here. Do not start by opening the largest raw data file.

## Current truth in plain English

The latest Jacobian V1 official shadow event is Attempt 2. Its RFC3161 anchor
and negative evidence chain verified, but the run failed closed at
`PRE_CUDA_PREFLIGHT` before CUDA or model loading because the dependency
source root was mixed with the runtime `.venv`. Counts were zero model blocks,
zero artifacts, and `0/1,248` autograd calls. Status is
`FAILED_CLOSED_EVIDENCE_CHAIN_VERIFIED_NO_SCIENTIFIC_CONCLUSION / SHADOW / NONE / NOT_LICENSED`.

The corrected Attempt 3 persistent pre-stage now passes the exact frozen
15-file dependency verifier. The A40 research pod is stopped; no Attempt 3
identity, query, anchor, CUDA initialization, or model execution exists yet.
Start current work in
`11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/START_HERE.md`.

Separately, in the earlier 2026-07-21 definition-anchor diagnostic, CAS
Harness successfully loaded the exact pinned Pythia-160M model, read hidden
states at the qualified boundaries of all 12 transformer blocks, completed a
bounded canary, completed the full 3,080-prompt diagnostic, recovered the
evidence off the GPU pod, and verified the copied bytes and tensor shapes.

The scientific comparison did **not** prove that the original TKS/D3 definitions were reliably better than the A124 operational rewrites:

- D3 accuracy: `9.9065%`
- A124 accuracy: `9.4813%`
- D3 minus A124: `+0.4252` percentage points
- Paired clustered-bootstrap 95% CI: `[-0.1276, +1.0204]` percentage points
- Interpretation: the interval includes zero, so the primary comparison is **INCONCLUSIVE**

The permanent status of that earlier run is `NOT_LICENSED_DIAGNOSTIC_ONLY`, with `claim_eligible=false`. This is not a project ceiling. It is the evidence label for that exact experiment at that exact time.

## What the earlier definition diagnostic establishes

- Exact model and revision binding worked.
- Architecture-appropriate hidden-state hooks worked across all 12 GPT-NeoX blocks.
- The canary and full GPU execution paths completed.
- Raw activation tensors, token-ID hashes, reports, logs, and receipts were recovered.
- The 33-entry full-run inventory was independently rehashed off-pod.
- Interrupted first-canary logs were preserved instead of overwritten.

## What the earlier definition diagnostic does not establish

It does not license semantic-probe validity, causal control, prompt-injection detection, output control, cross-architecture universality, 300B execution, production readiness, an Evidence Packet, a WORM anchor, an `ACCEPT` verdict, or a customer/investor/Amazon claim.

The independent object-store or third-party escrow copy remains `OPEN`.

## Folder map

- `00_PROJECT_STATUS` — dated historical copies of the project dashboard, successor specification, claim boundary, and next actions. Re-read the canonical current files under `docs/working`.
- `01_FROZEN_SOURCE` — exact frozen source archive and experiment-definition inputs.
- `02_RESEARCH_EVIDENCE` — recovered canary/full-run vectors, reports, logs, receipts, and verification records.
- `03_RESEARCH_AND_ARCHITECTURE_DOCS` — universality program, J-space/Ohm/300B analysis, supplied documents, historical claim/audit context, and the 20 semantic-authority sources.
- `04_AMAZON_INTERNAL_DRAFT_DO_NOT_SEND` — internal draft only; distribution remains paused.
- `05_RUNPOD_STATE` — time-stamped provider-state record.
- `06_REPRODUCTION_GUIDES` — instructions for a human or future agent to verify and continue the work.
- `07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b` — the 13 implementation/test files directly audited for planner, adapter, fleet, and live-probe behavior.
- `99_EXCLUSIONS_AND_SECURITY` — exclusions, security scan, superseded archive, and unverified preview warnings.
- `MANIFEST.json`, `MANIFEST.sha256`, and `SHA256SUMS.txt` — machine-readable inventory and integrity checks.

- 08_JSPACE_CAS_OHM_SHADOW_2026-07-21 — final full Git bundle, code-bound
  shadow receipt, implementation/test report, reproduction commands, and
  independent review for the disabled J-Space/Jacobian-lens/CAS-Ohm
  foundation.
- `09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21` — exact committed bundle,
  unmocked isolated-run receipt, protocol/lock copies, independent review, and
  novice reproduction instructions for deterministic CJT/Bias/RPM/CAS-Ohm
  plumbing.

- `10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22`
  - exact answer on combined live-model execution, the audited statistical-
  evidence source checkpoint, complete Git bundle, frozen protocol, tests,
  review decisions, and the next Pythia-160M technical-canary gate.

- `11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22` - controlling continuation
  for exact V1 source/model/token publications, the nonofficial Pythia
  differentiability diagnostic, red-team repairs, the verified RFC3161 anchor,
  the retained Attempt 2 pre-CUDA failure, and corrected Attempt 3 preparation.
  Start with its `START_HERE.md`; the signed anchor and negative evidence chain
  do not constitute a model, steering, or scientific result.

## Exact source and model identity

- Frozen branch: `codex/tks-definition-ab-20260721`
- Frozen commit: `da00bd9407e7e82662b53edd77980040e34eacf4`
- Frozen tree: `a95852594ce6c2e19862cb048bb3419b39812526`
- Protected parent: `81b5c18bd83e1f01ccd398dcad3865a674335b7f`
- Frozen source ZIP SHA-256: `CAEB3171D8F461E81AEB164888A41A7C33E105D2813A253DF25A833CC58A2E20`
- Model: `EleutherAI/pythia-160m`
- Model revision: `50f5173d932e8e61f858120bcb800b97af589f46`

## Critical evidence hashes

- Raw full-run NPZ: `454A4F017D56ED393E50D7E88D29486B3379E96AE930A1123698C6275298EAD6`
- Full 33-entry inventory: `B44E4457DE6763BC41A27AA1B746CBABA19A753F788F472B2FE4EF9546624A93`
- Off-pod verification record: `DB115601DF8F2984D56F6C9F5CDE09F598B77308ACD6CF978109583F375C2E9C`
- Plain-English result summary: `0EED1D9BC572D0B9E79BE1C980C0DDAD6227F58DD6A8693A1081A26DF0E8F90A`

## RunPod snapshot

- Research pod: `nppakqiaux91mk`
- Name: `cas-tks-anchor-diagnostic-20260721`
- GPU while running: one NVIDIA RTX 4000 Ada, 20 GB
- Advertised research rate: `$0.266/hour`
- State after evidence recovery: verified stopped on 2026-07-21
- GPU billing after stop: ceased
- Retained stopped-volume charge observed: `$0.006/hour`
- Production pod `hilj2rzs54gi06`: untouched

Provider state and prices change. Recheck RunPod before relying on this snapshot.

## What to do next

1. Run the verification steps in `06_REPRODUCTION_GUIDES/HOW_TO_VERIFY_THIS_HANDOFF.md`.
2. Read `00_PROJECT_STATUS/CLAIM_STATUS.md` before repeating any capability claim.
3. Read the canonical current tracker at `docs/working/cas_harness_production_todo.md` and successor specification at `docs/working/CAS_HARNESS_CUSTOMER_PRODUCTION_SUCCESSOR_SPEC_20260716.md`; treat `00_PROJECT_STATUS` as a dated snapshot.
4. Continue fresh Jacobian Attempt 3 only through `11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/05_ATTEMPT_03_PREPARATION.md`. The neutral holdout remains a later scientific gate.
5. Mirror this handoff into an independently controlled object store or escrow and verify every hash.

6. Read 08_JSPACE_CAS_OHM_SHADOW_2026-07-21/START_HERE.md before continuing
   J-Space, Jacobian-lens, or CAS-Ohm work.
7. Read
   `09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/START_HERE.md` before
   reproducing or extending the synthetic lane.

8. Read
   `10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/START_HERE.md`
   before claiming that J-Space, RPM, CJT Bias, or CAS-Ohm has improved a
   live-model probe.
9. Continue current Jacobian canary work only from
   `11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/START_HERE.md`; the older V0
   executor instructions are superseded wherever the V1 checkpoint says so.
   For the next official attempt, follow that folder's
   `05_ATTEMPT_03_PREPARATION.md` and preserve Attempt 2 unchanged.

## Do not

- Do not distribute the Amazon folder; it is `DISTRIBUTION_PAUSED_INTERNAL_REVIEW_DRAFT`.
- Do not call this diagnostic `ACCEPT`, `LICENSED`, universal, semantic validation, prompt-injection detection, output control, or 300B execution.
- Do not deploy the archive under `99_EXCLUSIONS_AND_SECURITY/SUPERSEDED_DO_NOT_USE`.
- Do not delete or rewrite interrupted/failed logs.
- Do not use the production pod for research experiments.
- Do not treat an honesty boundary as a permanent limit on what CAS Harness is intended to become.

## 2026-07-21 J-Space/CAS-Ohm final continuation

Read
`08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/START_HERE.md`.
The final continuation is bound to commit
`5d9a9d4206990e673d86a0c62518fd1a44ab6b1e` and includes:

- a complete final Git bundle plus the preserved `405fb389` intermediate;
- the pinned Jacobian-lens source bundle;
- frozen exact-token canary and correspondence-draft protocols;
- the CJT external-drive ontology;
- the prospective CJT Bias, corrected v7.4 RPM, and CAS-Ohm experiment
  contract; and
- the verdict-quarantine security boundary and current verification record.

These are `SHADOW / verdict_influence=NONE / NOT_LICENSED` artifacts.
They are an executable research foundation and prospective design, not a new
GPU result or a licensed customer capability.

## 2026-07-21 synthetic CJT/Bias/RPM/CAS-Ohm MVP

Folder `09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21` closes the
deterministic synthetic-plumbing implementation step at commit
`25053461c94de23850da7f9c853c420aab1bae62`. Its bundle and unmocked
`python -I` receipt verify `SYNTHETIC_HARNESS_MVP_PASS` only under
permanent `SELF_HASHED_UNATTESTED / SHADOW / NONE / NOT_LICENSED` fields.
It uses no GPU, model, hidden state, or customer verdict path and does not
license prompt-injection detection, output control, universality, or 300B
execution.

## 2026-07-22 combined readiness and statistical-evidence source checkpoint

Folder
`10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22`
records the controlling answer: the components have not yet been joined in
one live-model experiment. It freezes audited source commit
`50cd375fdc179e6a60fbed785e5b726d1fd34c23`, complete bundle SHA-256
`7BD5EF9281932D967CDB16D877D24C96DE2A595E03850F8FE41AE6694551A9C5`,
the statistical protocol, `158` focused tests, `576` worker tests, and
`100` production-ingress quarantine tests.

No public-randomness ceremony, official outcome, model run, GPU run, or new
license occurred at that source checkpoint. The next executable phase is
fresh official Attempt 3 of the differentiable Pythia-160M
`JACOBIAN_LENS_CANARY_V1`, using the verified separate dependency layout and
exact `24_000_000_000`-byte capacity gate.
