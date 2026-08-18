# CAS Harness — η→ε bridge script recovery into git (2026-08-18)

**What:** The flagship η→ε bridge scripts — which produced the load-bearing 20B 40-Element
result (+1.412 probe-Δ, `PROBE_PREDICTED_40E_ETA_EPSILON_BRIDGE_PASS`) — were **not in git**
and not on the local disk (only the reproducibility notes + the productionized *siblings*
survived locally). This preserves them.

**Recovered files** (into `noetic-compass-scaffold/noetic-compass/live-trace-worker/`):
| File | Location | Lines | SHA-256 |
|---|---|---|---|
| `scripts/run_stage9_40e_eta_epsilon_bridge.py` | flagship 40E bridge | 919 | `92e6fd525bb9e247ee04640ad3f2b95f07b7ae29c48784606cf37dc3f32cf8bf` |
| `scripts/run_open_weight_eta_epsilon_bridge.py` | dependency (`mean_logprob_continuation`) | 1054 | `f52fbbe33ae28d08eeb932902a2be1d0ce209204ed57dece28b98b6bb5b76faa` |
| `tests/test_stage9_40e_eta_epsilon_bridge.py` | test | 127 | — |
| `tests/test_open_weight_eta_epsilon_bridge.py` | test | 344 | — |

**Source:** RunPod pod `w0pjqx3ndaxfkg`, `/workspace/cas-jlcv1-official-c2b56a67-73499b56/repo/.../live-trace-worker/`. The `run_stage9_40e_eta_epsilon_bridge.py` sha256 is byte-identical across all 9 `cas-jlcv1-official-*` snapshots and the `a10-suite-worker` / `a10-shadow-worker` copies — one authoritative version. The already-in-repo dependency `run_open_weight_probe_shard.py` (probe capture) is unchanged.

**Transfer method (for the record):** `tar czf` on the pod → `base64` tagged per-line with `@@` (survives the SSH-proxy PTY) → reassembled locally with `scratchpad/extract_tgz.py` (drops PTY-injected 1-char fragments). Decoded 23255/23255 bytes; flagship sha256 re-verified in-repo = pod.

**What the bridge is** (from its docstring): `scenario text -> hidden-state 40E readout (η) -> readable 40E CAS realization prefix (ε) -> second model likelihood pass against the paired counterfactual element`. Likelihood-level evidence only; does NOT emit ACCEPT/SUPPRESS (that is the verifier / Evidence Packet merge layer). Uses `sklearn.LogisticRegression` (the balanced-logistic probe).

**Still not preserved:** raw activation NPZ (git-ignored, 100MB+, on pod / D: archive); `cas_harness_evidence_bridge.py` service-side packet module (verify it's in `api/`, follow-up).
