# REPLICATION BUNDLE — eta_epsilon_weight_learning_v0.1

External replication status: **REPLICATION_OPEN**. The author's own rerun
is INTERNAL review only (internal-review law); it does not count as
independent replication. This bundle exists so an outside party can rerun
and attest.

## What was run

A GENERIC interpretability-guided training study on Qwen2.5-0.5B-Instruct
(v0.2 amendment B1 dropped the 40-state CAS framing, so this is NOT a test
of CAS-specific value). Phases 1-7. Phase 8 is this bundle.

## Environment

- `replication/environment_lock.txt` (key deps): torch 2.11.0+cu128,
  transformers 5.16.1, numpy 2.5.2, tokenizers 0.23.1, accelerate 1.14.0.
- Python 3.x (venv), Windows, CUDA GPU (RTX 4070 class). Phase 1 is CPU.
- Model: local `Qwen/Qwen2.5-0.5B-Instruct` revision
  `7ae557604adf67be50417f59c2c2f167def9a775`. Full file SHA-256 in
  `../MODEL_IDENTITY.json` (weights `fdf756fa7fcbe740...`).

## Dataset

Deterministic mechanical grammar, `src/data_gen.py`, seed 20260830. No
language model labels anything. Gold roles are set by the template. Lexical
split holds out 3 nouns + 2 verbs for test.

## One-command runner

```
PY=<path-to-cas-gpu-python> bash replication/run_all.sh
```

Runs Phases 1-7; raw results land in `reports/*.json`. Then:

```
python replication/gen_summary.py   # -> replication/FINAL_RESULTS.json
```

## Manifests

- Checkpoint: `../MODEL_IDENTITY.json`.
- Raw results + their SHA-256: `replication/FINAL_RESULTS.json`.
- Claim ledger: `../CLAIM_LEDGER.json`.
- Full change history + every deviation: `../AMENDMENT_LOG.md`.

## Known determinism caveats (honest)

- Phase 1 (numpy/torch CPU): fully deterministic.
- Phases 2-7 use CUDA + fp16/fp32 + generation; small numeric
  nondeterminism across GPUs/driver versions is possible. Headline
  verdicts are robust to it; exact third-decimal digits may vary.
- Phases 6-7 are SMALL sweeps (N in {8,16,32}, 2 seeds) - indicative, not
  the full protected protocol (protected strata, 10 seeds, full control
  battery). Treat as dev-level evidence.

## Claim-by-claim attestation form (for the external replicator)

For each claim, fill: reran? / matched within tolerance? / notes.

| claim | author status | you reran? | matched? | notes |
|---|---|---|---|---|
| software_right_inverse | SOFTWARE_VERIFIED |  |  |  |
| 1_readout | EMPIRICALLY_SUPPORTED (dev) |  |  |  |
| 2_realization | EMPIRICALLY_SUPPORTED (directional) |  |  |  |
| 3_dose | EMPIRICALLY_SUPPORTED (first-order, saturating) |  |  |  |
| 4a_sample_efficiency | EMPIRICALLY_SUPPORTED (dev) |  |  |  |
| 4b_optimizer_efficiency | INCONCLUSIVE |  |  |  |
| 4c_retention | EMPIRICALLY_SUPPORTED (via replay) |  |  |  |
| 4d_wall_clock_efficiency | INCONCLUSIVE |  |  |  |

Conflict-of-interest field (replicator): ______________________________

## Internal-review law

The author is not independent. Until an outside party completes the form
above on their own hardware, external status remains REPLICATION_OPEN.
