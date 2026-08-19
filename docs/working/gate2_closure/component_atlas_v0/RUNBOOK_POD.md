# RUNBOOK — Component Atlas v0 on RunPod (verified 2026-08-18)

Pod `w0pjqx3ndaxfkg-644110d9@ssh.runpod.io` (host `9166c3298384`), **NVIDIA A40 46GB**.

## Environment facts (measured, not assumed)
- Research venv: `/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python` (py3.11)
- `torch 2.12.0+cu130` (cuda True), `transformers 5.9.0`, `numpy 2.4.6`
- **`sklearn` was MISSING.** The venv also had **no pip**. Fix that worked:
  `$VP -m ensurepip --upgrade` (installs pip 24.0) then `$VP -m pip install scikit-learn` -> `sklearn 1.9.0`.
- **HF cache layout is FLAT**: models live at `/workspace/cas-hf-cache/models--EleutherAI--pythia-1b`,
  NOT under a `hub/` subdir. So export **`HF_HUB_CACHE=/workspace/cas-hf-cache`** (setting only
  `HF_HOME` makes it look in `$HF_HOME/hub` and miss the cache). pythia-160m/1b/2.8b all cached.

## Run (rev 0.3)
```
export HF_HUB_CACHE=/workspace/cas-hf-cache HF_HOME=/workspace/cas-hf-cache TOKENIZERS_PARALLELISM=false
VP=/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python
cd /workspace/cas-atlas-v0
nohup $VP component_atlas_v0.py --smoke --out smoke_out > smoke.log 2>&1 &   # ~90s
nohup $VP component_atlas_v0.py        --out full_out  > full.log  2>&1 &   # full pass
```

## Run (REV 0.4, gpt-neox-20b bf16) — preregistered order, do not reorder
Prereq checks before spending pod time:
- `ls /workspace/cas-hf-cache/models--EleutherAI--gpt-neox-20b/snapshots/*/ | grep safetensors`
  must show `model-*.safetensors`. The script now also checks this and aborts as
  `ABORT_CACHE_FORMAT` (deviation D53), but the 5-minute manual check is still cheaper.
- Resolve the exact commit from that snapshot directory name and pass it as `--revision`.
  The script hard-aborts as `ABORT_UNPINNED_REVISION` without one (D32).
- Free host RAM: accelerate buffers one shard at a time even with `device_map={"":0}`.
- Budget 3–8 min for the 38.4 GiB read from a network volume (~1 min from local NVMe).

```
export HF_HUB_CACHE=/workspace/cas-hf-cache HF_HOME=/workspace/cas-hf-cache \
       TOKENIZERS_PARALLELISM=false PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
VP=/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python
cd /workspace/cas-atlas-v0
REV=<40-hex commit from the snapshot dir>

# 1. D34 bf16-vs-fp32 calibration on the rev-0.3 model. BINDING precondition.
#    ~0.8-0.95 h. Writes atlas_v0_rev04_report__pythia-2.8b.json (D54), so it
#    can never clobber the 20B artifact.
nohup $VP component_atlas_v0.py --model EleutherAI/pythia-2.8b --dtype bfloat16 \
     --controls 24 --rs-samples 5 --run-dr-f2 --run-rs --out calib_bf16 \
     > calib.log 2>&1 &
#    READ IT BEFORE STEP 3. Load-bearing quantities: behavioral_change_rate
#    (fp32 ref DR-F5 0.469 / DR-F2 0.313 / AMP-F5 0.969 / RS 0.958) and the
#    BASELINE-arm byte-identity counts (17, 22, 1, 1, 17). Everything else in
#    that diff is confounded by rev-0.4 code changes (D34, corrected).

# 2. 20B go/no-go preflight. ~0.15 h, dominated by the model load.
nohup $VP component_atlas_v0.py --preflight --revision $REV --out pf20b \
     > pf.log 2>&1 &
#    go == false on DR-F5 -> apply the ONE authorised step (D50), log it in
#    PREREG section 10 FIRST, then re-run the preflight:
#      ... --preflight --revision $REV --dr-engagement-step --out pf20b_step2
#    Second NO-GO -> DO NOT launch the battery. See PREREG section 8 stop rule.

# 3. Confirmatory run. DEFAULT = F5 rail only (DR-F5 + AMP-F5 + CONN),
#    C=24 drawn / 20 gating survivors, no RS, no DR-F2. 1,920 units, ~2.3 h.
nohup $VP component_atlas_v0.py --revision $REV --out rev04_out \
     > rev04.log 2>&1 &
```
`--run-rs` adds 1,944 units (~1.7 h) and pushes the run to ~4.0 h on its own;
using it is a deviation to be logged and it CHANGES THE VERDICT LABEL
(`PASS_BOUNDED_ATLAS_V0` becomes reachable instead of
`PASS_BOUNDED_ATLAS_V0_F5_RAIL_ONLY`). Same for `--run-dr-f2`.

## File transfer through the SSH proxy PTY (the pattern that works)
- Send: `gzip -c f.py | base64 -w 64 | sed 's/^/@@/'` inside a `<< 'B64EOF'` heredoc; on the pod
  `sed 's/^@@//' | base64 -d | gunzip`. sha256 verified equal both ends.
- Receive: `gzip -c f.json | base64 -w 64 | sed 's/^/@@/'`, then locally extract with
  **`grep -o '@@[A-Za-z0-9+/=]*'`** (NOT `grep '^@@'` — the first line hides behind a shell prompt)
  and drop fragments shorter than 20 chars before `base64 -d | gunzip`.
- Local python cannot read Git-Bash `/tmp/...` paths; write to a Windows path.

## Smoke result 2026-08-18 (mechanical validation only — smoke numbers are NEVER evidence)
`atlas_v0_SMOKE_report.json`. Completed end-to-end in **89.2s**, `status=NULL_ATLAS_V0`, 0/3 evaluable passed.
What it PROVED (the point of a smoke run): hooks work on transformers 5.9.0 (no tuple/Tensor crash),
pinned revision loads, all 5 core tests + CONN + 2 sanity + surface control execute, report schema
writes. **Both preregistered VACUOUS escapes fired correctly with their real reasons** —
`DR_F2` VACUOUS (baseline presence 0.50 < 0.6 precondition), `RS_F5` VACUOUS (baseline hedging
0.00 < 0.25 frac) — i.e. the adversarial reviewer's auto-doom fix is live and working.
Discovery: `L*=6` (acc 0.875) vs `shuffled_label_floor_max 0.5`, `L_dr=2`.
**Watch for the full run:** RS-F5 is the increase-sign anchor; if 24-token continuations still
hedge too rarely it goes VACUOUS again and the verdict rests on DR/DR/AMP/CONN only (the prereg
says headline that condition explicitly).

## Rev 0.3 run order (pythia-2.8b) — PREFLIGHT FIRST
Everything above describes the rev-0.2 run on pythia-1b and is kept as the record of it.
Rev 0.3 defaults to `EleutherAI/pythia-2.8b`, writes `atlas_v0_rev03_report.json`
(the rev-0.2 `atlas_v0_report.json` is never touched), and takes **~1.9 h**, not 30 min.

```
# 0. cache preflight (gating, do this before anything else)
ls /workspace/cas-hf-cache/models--EleutherAI--pythia-2.8b/snapshots/
cat /workspace/cas-hf-cache/models--EleutherAI--pythia-2.8b/refs/main
# the pinned sha is 2a259cdd96a4beb1cdf467512e3904197345f6a9 and must contain model.safetensors

# 1. smoke (mechanical only, ~2 min)
nohup $VP component_atlas_v0.py --smoke --out smoke_out_28b > smoke28.log 2>&1 &

# 2. BEHAVIOURAL PREFLIGHT — declared in advance, go/no-go, ~5 min
nohup $VP component_atlas_v0.py --preflight --out preflight_28b > preflight.log 2>&1 &
#    -> atlas_v0_rev03_preflight.json; proceed only if "go": true
#       (all three behavioural-change rates >= 0.60)

# 3. confirmatory run (~1.9 h). --local-files-only is now the DEFAULT.
nohup $VP component_atlas_v0.py --out full_out_pythia28b > full28.log 2>&1 &
#    reduced fallback if pod time is short (LOG IT as a deviation first):
#    ... --controls 20 --rs-samples 3     # ~1.2 h; C=19 is REJECTED by a hard guard
```
The report is flushed at every stage boundary, so a late crash keeps everything up to that point.
