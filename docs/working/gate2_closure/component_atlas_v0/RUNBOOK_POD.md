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

## Run
```
export HF_HUB_CACHE=/workspace/cas-hf-cache HF_HOME=/workspace/cas-hf-cache TOKENIZERS_PARALLELISM=false
VP=/workspace/cas-jacobian-v1-bootstrap/jacobian_lens_v1/.venv/bin/python
cd /workspace/cas-atlas-v0
nohup $VP component_atlas_v0.py --smoke --out smoke_out > smoke.log 2>&1 &   # ~90s
nohup $VP component_atlas_v0.py        --out full_out  > full.log  2>&1 &   # full pass
```

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
