# RESULT — contrastive-activation steering through the attested C10 path

**Research-grade. `NOT_PACKET_ELIGIBLE`, `NOT_A_SCIENTIFIC_EXPERIMENT_RESULT`. Ran 2026-08-21 on the owner's laptop (CPU), $0 spent, no pod touched, no AWS resource involved.** Prereg: `PREREG_RESEARCH_CAV_STEERING.md` (written before any load, deviation D1 logged before the rerun). Raw numbers: `cav_results.json` (sha256 `e153beee9caea92d…`). Script: `cav_experiment.py`.

---

## Finding 0 — found before the experiment even ran, and it is the bigger one

**The frozen canary would die at model-load on the A40.** Proven byte-for-byte, not inferred:

- The downloaded `model.safetensors` at pinned revision `50f5173d932e8e61f858120bcb800b97af589f46` hashes to `29D2E457A664E41C12C735F20A36DC0956A665F614A54CE5DB21A32E75965270` — **exactly the file the canary preregistration pins**.
- That file holds **184** tensors, including **36** legacy GPT-NeoX buffers (`attention.bias`, `attention.masked_bias`, `rotary_emb.inv_freq` × 12 layers).
- Under the canary's own pinned `transformers==5.8.1`, the loaded model's `state_dict()` has **148** keys — the 36 legacy buffers are simply not registered by modern modeling code.
- `verify_loaded_weight_values` demands **exact set equality** and raises `loaded model values do not match safetensors bytes: missing=[36 buffers]`.

**Therefore the canary fails at `load_open_weight_runtime`, on the pod, after the create attempt is spent, before any capture.** The one authorized create attempt would have burned on a guaranteed failure. This was caught for `$0` because this research run exercised the identical code path locally first.

Also proven in passing: the **148 shared tensors match byte-exactly** (`changed=[]` in the failure report), which is what makes the derived-snapshot workaround below faithful.

**Canary-lane fix is an owner/reviewer decision** (it re-freezes pinned artifacts): re-pin the model file set to a re-serialized fp16 artifact (new `model.safetensors` hash, new tree manifest) — the derived snapshot below is exactly that artifact, with provenance. Patching the verifier instead would break the hash-locked source freeze and is not recommended.

## The derived snapshot (workaround, full provenance)

| | |
|---|---|
| Derived from | pinned revision `50f5173d…`, file `29D2E457…` |
| Method | `from_pretrained(dtype=float16)` → `save_pretrained(safe_serialization=True)` under `transformers 5.8.1` |
| New `model.safetensors` | **324,662,840 B**, sha256 `d5861d3237c5f8e952b4ebf05179f3bc50d479186fbe96845d22660d96c50d97` (fp16, the 148 functional tensors, byte-identical values) |
| `config.json` / tokenizer files | **byte-identical to the pinned snapshot** (copied, not regenerated) |
| Dropped | only the 36 non-functional legacy buffers (recomputed at runtime by modeling code) |

Engine attestation on the derived snapshot: **passed** — weight manifest `AD7CB93367AB3382…`, 12 layers, hidden 768.

## The steering experiment — exact results

Vector `v` = residual difference (`wonderful` − `terrible` contrast pair) at layer 6, step 0. `‖v‖ = 6.915401`. Random control `r`: same norm, `cos(v,r) = 0.077840` (near-orthogonal). Environment: `torch 2.5.1+cu121` (device `cpu`), `transformers 5.8.1`, seed 0, greedy, 2 tokens.

| prompt | baseline top | `ΔM(+v)` | `ΔM(−v)` | `ΔM(+r)` | top-token events |
|---|---|---:|---:|---:|---|
| `T1` "Overall, the film was" | ` a` | **+2.5000** | **−3.3750** | +0.2500 | `−v` flips top to ` rated` |
| `T2` "My honest review: the food tasted" | ` great` | **+3.3750** | **−3.2500** | +0.1250 | **`−v` flips ` great` → ` bad`**; `+r` → ` like` |
| `T3` "She looked at the painting and said it was" | ` a` | **+2.5000** | **−2.3750** | +0.6250 | none |

Engine controls: `noop` max|Δlogit| = **0.0** (bit-exact); `zero` at L6: `‖Δlogits‖₂ = 1009.870`, top → ` the`.

## Verdict against the preregistered predictions — applied as written

- **P1 (noop ≡ baseline): PASS**, exactly `0.0`.
- **P2 (zero ≥ 10× any additive arm): FAIL AS WRITTEN.** `zero` is the largest single effect (`1009.870` vs max additive `606.133`) — direction right — but the ratio is `1.67×`, not the required `10×`.
- **P3 (direction): 3/3 and 3/3** — every `+v` positive, every `−v` negative.
- **P4 (targeting): 3/3** — mean `|ΔM(±v)|` = `2.8958` vs mean `|ΔM(+r)|` = `0.3333`, a **`8.69×`** targeting ratio at identical norm.

**The prereg's decision rule fires on P2: `ENGINE_ANOMALY`, investigate before any interpretation.** Investigation outcome: **the engine is exonerated** — `noop` is bit-exact (hooks clean), `zero` is the largest single effect, and the failure is the prediction's own uncalibrated `10×` multiplier (the l2 metric spans a 50,304-token vocabulary; a norm-7 injection at layer 6 amplifies through six further layers more than guessed).

**Final label: `P2_FAILED_AS_WRITTEN — EXPLORATORY_POSITIVE ONLY.`** Under its own preregistration this run may **not** claim `SUGGESTIVE_POSITIVE`, and this document does not. The directional and targeting results (P3, P4, and the ` great`→` bad` flip) are reported as exploratory. A follow-up wanting the stronger label needs a **new** preregistration with a calibrated P2 — this one is not revivable.

## Claim states

- **Real:** everything above — real pinned-provenance weights, real forward passes, full engine attestation, all numbers measured.
- **Open:** replication across layers, seeds, prompt families; effect-size calibration; any product use.
- **Not licensed:** any customer- or regulator-facing sentence citing these numbers. Research-grade only.

## What this run proved about the harness itself

1. **C10's additive path does real, targeted, direction-controllable work on real weights** — first semantics-bearing use of the attested intervention path (only `noop`/`zero` had ever run).
2. **C01/C04 capture arrays are usable research instruments** — the steering vector was *built from* the engine's own captured residuals.
3. **The fail-closed discipline works end to end** — memory floor refused (deviation logged), allowlist refused stray files, byte verifier refused two dtype/skew mismatches, and the prereg's own decision rule then refused the flattering headline.
