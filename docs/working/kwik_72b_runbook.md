# 72B License Test — Runbook (execute when the big pod is up)

Goal: run the closed-book KWIK pre-answer probe on **Qwen2.5-72B-Instruct** and check the
full license gate (floor / margin / residual / held-out / 1000-perm). 72B is where the
"knows-what-it-knows" signal is strongest and where residual (the binding gate, 0.692 on 14B)
has the best chance of crossing 0.75. REAL numbers only — no LICENSED stamp unless every gate passes.

## Pod requirement
72B bf16 ≈ 145 GB VRAM. Options (any works; script supports all):
- **2×A100 80GB (160 GB) — bf16, zero compromise (recommended for the cleanest test).**
  Run with `--device-map auto`.
- **1×A100 80GB or 1×H100 80GB + 8-bit (~75 GB) — near-bf16 hidden states, cheaper single GPU.**
  Run with `--load-8bit`.
- Disk volume: **≥ 250 GB** (the bf16 checkpoint download is ~145 GB even for 8-bit-on-load).

Give me the SSH host + port; I reuse `~/.ssh/id_ed25519`. I stop the current 48 GB pod once this one is confirmed.

## Steps (I run these)
```bash
# 0. deps (8-bit path only)
pip install -q bitsandbytes

# 1. capture (pick ONE line)
#    2xA100 bf16:
python3 closedbook_kwik_capture.py --model-id Qwen/Qwen2.5-72B-Instruct --n 8000 \
  --device-map auto --out /root/kwik_72b.npz --gen-out /root/kwik_72b_gens.jsonl
#    1xA100/H100 8-bit:
python3 closedbook_kwik_capture.py --model-id Qwen/Qwen2.5-72B-Instruct --n 8000 \
  --load-8bit --out /root/kwik_72b.npz --gen-out /root/kwik_72b_gens.jsonl

# 2. fast gate (PCA-256, concat readouts) — read floor/margin/residual/held-out
python3 lic_eval_fast.py /root/kwik_72b.npz --out=/root/lic_report_fast_72b.json

# 3. if (and only if) floor+margin+residual+held-out all PASS, run the permutation:
python3 lic_eval_fast.py /root/kwik_72b.npz --perm --out=/root/lic_report_fast_72b_perm.json
```

## Decision
- All five gates PASS (incl. perm p<0.001) → flip
  `cas_harness_active_goal_claim_audit_20260617.json` hallucination_detection → LICENSED, commit the
  reproducible report. THE WIN.
- Residual still < 0.75 → honest stop: report the exact number; do NOT stamp. The 72B result is the
  definitive answer on whether pre-answer hidden-state detection can clear this gate at all.

## Honest odds (stated up front)
Margin (0.131) and held-out (0.739) very likely clear at 72B (within 0.02 on 14B, bigger model adds
signal). Residual (0.692 → need 0.75) is the coin-flip — ~1/3 that all gates pass. Frontier-level bar.
