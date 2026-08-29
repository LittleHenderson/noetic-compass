# External Replication Bundle v0.1 — the path to E6

**Who this is for:** an evaluator OUTSIDE the developing party's
session and provenance — a person or organization that did not build
this system and was not commissioned by the agent that built it.
Internal AI audits already exist on the record; they count as E5
supporting evidence, never E6. **E6 unlocks only for the exact claims
you independently reproduce, and only when the evaluator is external.**

## What you need

- Python 3.12+ with `pytest` (`pip install pytest`).
- This repository at branch `phase4-hybrid-cortex`
  (commit `bd54031e`; baseline `2526360b`).
- OPTIONAL, for the live-cortex leg only: `torch` + `transformers`
  and the model snapshot `Qwen/Qwen2.5-0.5B-Instruct` revision
  `7ae557604adf67be50417f59c2c2f167def9a775` in the local Hugging Face
  cache. The deterministic legs need no model.

## One command

```bash
python run_replication.py
```

Add `--cortex` for the live-model smoke. The runner re-executes all
fourteen board test suites, re-derives the qualification level,
re-computes the deterministic digests, and writes
`replication_report.json` with a report digest.

## What the claims are (claim-by-claim replication form)

Attest each claim SEPARATELY. Reproducing the kernel tests does not
replicate the neural head-to-head; reproducing the head-to-head does
not replicate the self-improvement claims. Tick only what you ran.

| # | Claim | How to verify | Reproduced? (yes/no/deviation) |
|---|-------|---------------|--------------------------------|
| 1 | Kernel conformance (34 tests: typed intents, sole-writer coordinator, sealed traces, deterministic replay) | suite `CAS_RRK_v0.1` | |
| 2 | Learning + self-improvement (45 tests incl. the G8 causal ablation and the G9 evidence-derived synthesis) | suite `CAS_RLP_v0.1` | |
| 3 | Exact mathematics + verified identity search (34 tests; discovery digest `bd4a444406b0833c`) | suite `CCB_M1_v0.1` + digest check | |
| 4 | Native language board (18 tests) | suite `CCB_L1_v0.1` | |
| 5 | Semantic binding layer (19 tests) | suite `CAS_SEM_v0.1` | |
| 6 | Workbench projection (13 tests) | suite `CAS_WORKBENCH_v0.1` | |
| 7 | Qualification standard incl. RMB gates and the E6 bar (35 tests) | suite `CRQS_v0.1` | |
| 8 | Tool board typed fault halts (20 tests) | suite `CCB_T1_v0.1` | |
| 9 | CAS-Ohm panel restrictions R1–R10 (10 tests) | suite `CAS_OHM_INSTRUMENT_v0.1` | |
| 10 | Cortex head-to-head harness (10 tests; the sealed 20-item result is developer-run and environment-stamped) | suite `CORTEX_H2H_v0.1` | |
| 11 | Long-term goals with kernel-earned completion + fact-echo guard (11 tests) | suite `CAS_LTG_v0.1` | |
| 12 | Self-model with live-probe-derived claims (8 tests) | suite `CAS_SM_v0.1` | |
| 13 | Multi-domain long-horizon integration, digest `cdd76e945484e3f4` (8 tests) | suite `CNCM_G10_v0.1` + digest check | |
| 14 | Hybrid cortex authority firewall + grounding gate (19 tests) | suite `CAS_CORTEX_v0.1` | |
| 15 | Qualified level derives to exactly `CAS-G9 / E5 / A0` | `CRQS_v0.1/run_demo.py` output | |
| 16 | (optional, `--cortex`) model identity `fdf756fa7fcbe740`; grounded parse answers through the kernel; fabricated packet dies at `UNGROUNDED_TERM` | cortex smoke output | |

## Attestation form (complete after the run)

```
Evaluator name / organization:
Relationship to the developing party (conflicts of interest):
Date:
Environment (OS, CPU, Python version):
Command(s) run:
All suite counts matched expected?          yes / no (list deviations)
Qualification output matched expected?      yes / no
Deterministic digests matched?              yes / no (list)
Cortex smoke run?                           yes / no / n.a.
Deviations, failures, or surprises (REQUIRED - "none" only if none):
Claims reproduced (list row numbers from the table):
Signature:
```

## Known caveats (read before attesting)

See `expected_results.json` → `known_caveats`. In particular: the
qualification you should reproduce is **CAS-G9 / E5 / A0** — a
higher level was once computed, refuted by internal audit, and
withdrawn; the refutation records are part of the evidence, not a
blemish to explain away.

## What to do with the completed form

Return `replication_report.json` + the completed attestation to the
owner. A valid external attestation becomes a replication record with
`external: true` and a `claim` field naming the rows reproduced; two
such records covering the qualified level's load-bearing claims lift
the evidence tier to E6 under `CRQS_v0.1/crqs/evidence.py`.
