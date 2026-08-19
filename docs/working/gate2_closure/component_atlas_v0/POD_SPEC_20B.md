# POD SPEC — GPT-NeoX-20B atlas run (2026-08-19)

Why a new pod: the current pod `w0pjqx3ndaxfkg` (A40 46GB) is **disk-quota full** at 52G.
20B needs ~41G of model and only ~15.4G is safely freeable against ~18G required. The GPU
also forces bf16 (fp32 at 20.55B params = **76.6 GiB**, card has 44.99 GiB).

## Choose ONE — the GPU decides whether the bf16 deviation survives

| Option | VRAM | 20B fp32 (76.6 GiB) | 20B bf16 (38.3 GiB) | Verdict |
|---|---|---|---|---|
| **A100 80GB / H100 80GB** | 80 GiB | ✗ 96% of card — OOM with activations | ✓ comfortable, ~41 GiB spare | **bf16, D33 stays** |
| **H200 141GB / A100 80GB ×2** | 141 / 160 GiB | ✓ fits with room | ✓ | **fp32 — D33 can be WITHDRAWN** |

**Recommendation: H200 141GB (or 2×80GB).** It is the only configuration that lets us run
**fp32** and therefore **delete deviation D33 entirely** — no precision compromise, no
bf16-vs-fp32 calibration precondition (D34), and ~1 h less total pod time because the
calibration run disappears. On an 80GB card we would still be running the exact bf16 design
that is already frozen, which is fine but keeps the precision caveat on the record forever.

## Non-negotiable specs
- **Disk volume: ≥ 120 GB** (20B ≈ 41G + pythia-2.8b 5.4G for any calibration + HF blobs +
  outputs + headroom). The current pod died at 52G — do not repeat that.
- **CUDA-capable, PyTorch 2.x**, Python 3.11.
- SSH access with the same key (`~/.ssh/id_ed25519`).

## Bootstrap (one paste on the new pod)
`bootstrap_20b_pod.sh` in this directory does all of it:
1. creates the venv layout and installs `torch`, `transformers`, `numpy`, `scikit-learn`
   (the old pod's venv had **no pip and no sklearn** — `ensurepip` then install);
2. sets `HF_HUB_CACHE` (**not** `HF_HOME` alone — the old cache was flat and `HF_HOME`
   looks in `$HF_HOME/hub` and misses it);
3. downloads `EleutherAI/gpt-neox-20b` with **retries and `max_workers=3`** (8 workers
   plus an unauthenticated rate limit is what wedged the first attempt), fully detached
   under `setsid` so it survives the SSH session;
4. prints the resolved snapshot commit — **record it as the pin**; the atlas hard-aborts as
   `ABORT_UNPINNED` without one.

## Then
- Transfer `component_atlas_v0.py` (frozen at repo commit `f5175d96`, sha256
  `3aa3259fcbad3c5ce3135b34c1560e144f3e1759046c3196d0ece3efdfe9cc1a`) by the tar+base64
  `@@`-tagged PTY method in `RUNBOOK_POD.md`; verify sha256 on both ends.
- Run `--preflight` FIRST (~10 min at 20B, dominated by the 38–77 GiB load). It reads no
  test statistic and cannot be tuned toward a pass.
- If the preflight goes, run the confirmatory pass.

## If the new pod has > 80 GiB VRAM, do this BEFORE running
Withdraw **D33** (bf16) and **D34** (the bf16-vs-fp32 calibration precondition) in the prereg
with a dated entry saying they were withdrawn because the resource constraint that forced
them no longer applies, and set `--dtype float32`. That is a deviation *reduction* and must be
logged like any other change, before the run.

## Watch item, unchanged by hardware
The validated Stage-9 40E probe peaked at **layer 2 of 44**. D56 (repo commit `f5175d96`)
widened the search to the full depth (`sweep_lo=1`, `L_STAR_MIN=2`) and made `DR_OFFSET`
adapt, so a shallow `L*` is now selectable instead of aborting. If `L*` lands below
`0.25 × depth` the report stamps `shallow_l_star_surface_caveat` and **no PASS may be read
as deep semantic structure**.
