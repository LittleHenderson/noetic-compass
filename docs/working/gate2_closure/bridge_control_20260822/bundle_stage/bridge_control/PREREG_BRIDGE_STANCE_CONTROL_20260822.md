# PREREG — Bridge stance-matched non-CAS prefix control (frontier #16) — 2026-08-22

**Status: PRE-REGISTERED BEFORE EXECUTION.** No criterion, template, or binding may be edited after the GPU run starts. The $0 fixture build is already complete and hash-pinned; the only remaining step is the paid execution binding described in §6.

---

## 1. Purpose

Frontier #16 (spec sheet §10.16): the stance-explicitness-matched non-CAS English prefix control for the η→ε bridge that Cap. 2's caveat says was never run. Without it, the licensed observation "+1.412050" is consistent with *"a fluent prefix naming the answer is attended"* rather than CAS structure. This run measures whether a **non-CAS plain-English prefix carrying the same content** produces a comparable likelihood shift on the **same 80 frozen cases**.

## 2. Frozen inputs (all sha256-verified locally 2026-08-22)

| artifact | sha256 |
|---|---|
| original bridge result JSON (80 cases, May run) | `9363F54B89122B5F2EB20954FFBE56C4447D69F68D2E8A9E1CC2E7F42F27EE2B` |
| scenario fixture `stage9_original_40e_scenarios_20260527.json` (8,320 items) | `b2ad0481daaa1e5597a445a7ad8a9f2a4d108ead213818edd2ffb665af55b537` |
| activation dataset npz (4.16 GB) | `5f9a14714dcad87991a04a8317119b4eeb8097af7377446e59efb1c65f428610` |
| probe eval report | `e90268444fd914f558b2244c90c9d039936fc273bdefbad266ebaf844d004030` |
| bridge script (working copy; identical to commit `6269147d` by git diff) | `9177c24b56d862c24bb6e328ff4eb4319f507f45f72035c6a988a88e8958ff9a` |
| bridge script (pod-attested, verified in-repo 2026-08-18) | `92e6fd525bb9e247ee04640ad3f2b95f07b7ae29c48784606cf37dc3f32cf8bf` |

Lineage note, on the record: the working copy differs from the pod-attested hash because post-recovery edits touched the CLI/selection layers; the ε-template functions (`readable_prefix`, `raw_prefix`, `element_phrase`, the gloss tables) are the load-bearing part and are pin-honest by construction — the CAS prefix strings are **embedded in the hash-pinned fixture below**, so the run consumes fixed strings, not live code.

## 3. The control fixture (already built, $0)

- `bridge_control_fixture_20260822.json` — **sha256 `042ff22bf5b6ce8e9336c02bb7687b8ba75b077bb39e0fb55429cc90ec9c34cb`**
- 80 cases; scenario ids **byte-identical to the original run's selection** (verified in the builder output).
- Per case: prompt, base prompt, correct/partner continuations (same `element_phrase` strings as the May run), and prefix variants:
  - `cas_probe` / `cas_gold` — CAS readable realization (probe-predicted / gold label)
  - `ctrl_probe` / `ctrl_gold` — the control (below)
  - `cas_raw` — raw CAS symbols (sanity vs the May null)

### 3.1 Control template — pinned verbatim

```
Plain-English context for the focused role:
- What it is about: {operator name, lowercase} - {operator gloss}
- The sense in play: {domain name, lowercase} - {domain gloss}
- In short: {element phrase}
Use this context as background for the next sentence.
```

Stance-matching contract, checked at build time: same five-line structure, same gloss content, same element phrase, same closing instruction sentence, **zero CAS vocabulary** (no "CAS", no codes, no Operator/Domain labels). Length ratio ctrl/CAS: mean **0.930663**, min **0.926582**, max **0.935123** — inside the pre-registered band [0.85, 1.15].

## 4. Method (identical to the original bridge)

Model `EleutherAI/gpt-neox-20b`, `torch.float16`, `device_map=auto`, `max_length=256`. For each case × condition: `prompt = prefix + base_prompt`; score `correct_continuation` vs `partner_continuation` with `mean_logprob_continuation` (the May-run machinery, imported — not reimplemented). Conditions: `none`, `cas_probe`, `ctrl_probe`, `cas_gold`, `ctrl_gold`, `cas_raw`. Margins = correct − partner; deltas = margin − none-margin per case.

The original run had **no model revision pin**; this run resolves the revision at install time and **records it** (HF cache snapshot id) in the results.

## 5. Pre-registered criteria and verdicts

- **C1 (control sanity):** `ctrl_probe` delta-vs-none mean **> 0** — a fluent naming prefix must shift likelihoods above none, else the control arm is invalid (`CONTROL_ARM_INVALID_C1`).
- **C2 (THE COMPARISON):** mean(`cas_probe` delta) − mean(`ctrl_probe` delta), plus the paired per-case sign test (CAS delta > CTRL delta, two-sided exact binomial, p ≤ 0.05).

| outcome | verdict word |
|---|---|
| C1 ∧ (CAS−CTRL ≥ **+0.10**) ∧ sign p ≤ 0.05 | `CAS_FRAMING_ADDS_BEYOND_CONTENT` — CAS framing carries weight beyond naming content; settles frontier #16 in the positive direction |
| C1 ∧ (CAS−CTRL ≤ **−0.10**) ∧ sign p ≤ 0.05 | `CAS_FRAMING_WORSE_THAN_PLAIN_NAMING` — a negative for CAS framing, also a settlement |
| C1 ∧ |CAS−CTRL| < 0.10 | `NO_DETECTABLE_FRAMING_ADVANTAGE` — the shift is framing-generic; the "+1.412 = fluent prefix naming the answer" reading stands; Cap. 2 stays `REAL` + `PARTIAL`, caveat confirmed |

Both directions are recorded as results; no outcome upgrades Cap. 2 without the artifact path, and nothing may produce an ACCEPT.

## 6. Execution binding (the paid part — owner-authorized 2026-08-22)

- AWS `g6e.xlarge` (NVIDIA L40S, 48 GiB) in `us-west-2`, via the existing inert `cas-aws-gpu-standby-v1` launch template (SSM-only role, no ingress, 443 egress only, encrypted gp3, termination protection).
- Hard cost cap **$4.00**; the instance runs the job once and **self-terminates** (bootstrap ends with shutdown + termination protection disabled).
- Results land in S3 and are re-verified locally against the prereg before any spec-sheet edit.
- No RunPod resources, no guardian ledger rows, no provider calls — this is the designated AWS GPU fallback path, distinct from the frozen A40 canary.

## 7. What a WIN would and would NOT license

A `CAS_FRAMING_ADDS_BEYOND_CONTENT` licenses exactly: *"on the frozen 80-case 40E fixture at 20B, the CAS readable prefix shifts next-token likelihoods more than a content-matched plain-English prefix, at the pre-registered margin."* It does **not** license CAS-specificity generally, any claim beyond this model/fixture, or any change to the `FLAG_FOR_HUMAN_REVIEW` packet.

## 8. Pinned hashes

- prereg (this file): recorded after writing
- runner `run_bridge_control_20b.py`: `0b15888dd3d655b52c64196a0e535260884ed0bb38fedc3c3993c5538bfcf2b4`
- builder `build_control_fixture.py`: `a07859e9f2258acf4d43159053968a8f85553490076aa83f4350dd7edc9a0809`
- fixture: `042ff22bf5b6ce8e9336c02bb7687b8ba75b077bb39e0fb55429cc90ec9c34cb`

## 9. AMENDMENT A1 (2026-08-22, pre-execution) — runner repathed for the Linux host

The runner's platform-path constants were replaced with `__file__`-relative paths so the same script executes on the AWS Ubuntu host. No condition, template, criterion, or fixture byte changed. The §8 runner hash is superseded: new runner sha256 `ec85c0788a67cd40cbbe4cfd3c141c070ea335dbfc0302e42bece294bd17607c`. The execution binding (§6) is unchanged.

## 10. AMENDMENT A2 (2026-08-23, pre-execution retry) — first bootstrap attempt failed BEFORE the experiment

Attempt 1 (instance `i-07d520cdebaa4d90f`) never reached the experiment: the system pip install raced PEP 668 and the instance-role credential propagation, so no job log ever landed in S3 and the trap's self-terminate could not authenticate. **Zero experiment data was produced or recorded**; the local watchdog force-terminated the instance at the 150-minute bound. Attempt-1 spend ≈ **$4.65** is recorded as infrastructure overhead, not experiment cost. The bootstrap is hardened for the retry (venv installs, a 5-minute credential-wait loop, a retry-hardened fail path) — **no criterion, template, condition, or fixture byte changed.** The retry re-launches under the same §5 criteria and §6 binding; the new instance id is recorded in `launch_state.json`.

## 11. AMENDMENT A3 (2026-08-23, second pre-execution retry) — AMI lacks python3-venv; switch to NGC container

Attempt 2 (instance `i-030d049169a66ea0e`) failed at venv creation: the DL AMI ships no `python3-venv`, and apt is unreachable because the standby security group allows egress on 443 only. **Zero experiment data again**; the instance was terminated by local control (overhead ≈ **$0.93**). Bootstrap v3 switches to the DL AMI's preinstalled Docker engine — `nvcr.io/nvidia/pytorch:24.10-py3` (torch 2.5.1, CUDA 12.4, pulled over 443) with the model, cache, and results on the mounted `/workspace` volume — plus a 2-hour `shutdown` failsafe independent of any AWS API. **No criterion, template, condition, or fixture byte changed.**

## 12. AMENDMENT A4 (2026-08-23, third pre-execution retry) — ephemeral-container mistake fixed; single-session container

Attempt 3 (instance `i-0ea63764389961dcf`) reached the container stage (NGC 24.10 pulled, deps installed, versions verified) but died at model download: each `docker run --rm` step is an ephemeral container, so the deps installed in one step were absent in the next. **Zero experiment data again** (overhead ≈ **$0.27**). Bootstrap v4 runs deps → model download → experiment in **one container session** (`set -e` inside), with the same mounted cache, plus the unchanged failsafes. **No criterion, template, condition, or fixture byte changed.**

## 13. AMENDMENT A5 (2026-08-23, fourth pre-execution retry) — NGC image lacks `accelerate`

Attempt 4 (instance `i-0e5cb321655de7875`) reached the container session with the corrected single-session pipeline and failed only because `device_map="auto"` requires the `accelerate` package, which the NGC 24.10 image does not ship by default (deps verified: torch 2.5.0a0+…nv24.10, transformers 5.8.1). **Zero experiment data again** (overhead ≈ **$0.06**; self-terminate fired correctly). Bootstrap v5 adds `accelerate` to the container pip line. **No criterion, template, condition, or fixture byte changed.**
