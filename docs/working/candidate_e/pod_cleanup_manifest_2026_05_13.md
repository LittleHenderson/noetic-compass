# Pod Cleanup Manifest — 2026-05-13T00:38Z

Cleanup of stale training-artifact dirs on RunPod, to free user-quota headroom for E2c continuation. Per Codex audit 2026-05-13T00:33Z and user "go" 00:38Z. Decision: `docs/working/agent_exchange/decisions.md` 2026-05-13T00:38Z entry.

**Cleanup safety per Codex's requirement:** exact resolved paths only, no wildcards in the destructive command.

## Paths to delete

| path | size (bytes) | size (GB) | reason |
|---|---|---|---|
| `/workspace/tksCAS/stage7_diagnostic_replay_20260511T113303Z` | 3325958169 | 3.10 | diagnostic replay, completed |
| `/workspace/tksCAS/stage7_candidate_a_untied_20260511T130552Z` | 4217082476 | 3.93 | Candidate A FALSIFIED at criterion 1 |
| `/workspace/tksCAS/stage7_candidate_b1_lmfr_20260511T195649Z` | 3325634327 | 3.10 | B1 superseded by B2 (B2 kept) |
| `/workspace/tksCAS/stage7_candidate_b3_full_hardemit_20260511T235917Z` | 3326053053 | 3.10 | B3 FALSIFIED on broader B3 eval |
| `/workspace/tksCAS/stage7_candidate_c_hardemit_20260511T173200Z` | 3326070525 | 3.10 | Candidate C FALSIFIED |
| `/workspace/tksCAS/stage7_candidate_d1_ssm_lmfr_20260512T042905Z` | 3871933539 | 3.61 | D1, off the candidate path |
| `/workspace/tksCAS/broader_b3_eval_20260512T034633Z` | ~1 MB | <0.01 | broader B3 eval result, archived |
| `/workspace/tksCAS/broader_b3_eval_20260512T034633Z.log` | 923 | <0.01 | log of above |
| `/workspace/tksCAS/broader_b3_eval_at192_20260512T042336Z` | ~1 MB | <0.01 | broader B3 eval result, archived |
| `/workspace/tksCAS/broader_b3_eval_at192_20260512T042336Z.log` | 934 | <0.01 | log of above |
| `/workspace/tksCAS/eval_e2c_20260512T205026Z` | empty | 0 | dust from failed launch today |
| `/workspace/tksCAS/eval_e2c_20260512T205026Z.log` | 0 | 0 | dust |
| `/workspace/tksCAS/eval_e2c_20260512T210934Z` | empty | 0 | dust |
| `/workspace/tksCAS/eval_e2c_20260512T210934Z.log` | 0 | 0 | dust |
| `/workspace/tksCAS/eval_e2c_20260512T211016Z` | empty | 0 | dust |
| `/workspace/tksCAS/eval_e2c_20260512T211016Z.log` | 0 | 0 | dust |
| `/workspace/tksCAS/eval_e2c_20260512T211103Z` | empty | 0 | dust |
| `/workspace/tksCAS/eval_e2c_20260512T211103Z.log` | 0 | 0 | dust |
| `/workspace/tksCAS/eval_e2c_20260512T211247Z` | empty | 0 | dust |
| `/workspace/tksCAS/eval_e2c_blocking_20260512T212521Z` | empty | 0 | dust from blocking-ssh GPU launch |
| `/workspace/tksCAS/eval_e2c_cpu_20260512T212541Z` | empty | 0 | dust |
| `/workspace/tksCAS/eval_e2c_cpu_20260512T212709Z` | empty | 0 | dust from 2h CPU eval (killed before write) |
| `/workspace/tksCAS/eval_e2c_test` | empty | 0 | dust |

**Total: ~21,392 MB ≈ 20.4 GB**

## Paths to KEEP (active warm-start chain)

| path | size | reason |
|---|---|---|
| `/workspace/tksCAS/stage7_candidate_b2_lmfr_slot_20260511T212819Z` | 3.1 GB | E2a warm-start origin |
| `/workspace/tksCAS/stage_e2a_warmup_20260512T150330Z` | 3.1 GB | E2b warm-start origin |
| `/workspace/tksCAS/stage_e2b_full_20260512T172129Z` | 3.1 GB | E2c warm-start origin |
| `/workspace/tksCAS/stage_e2c_anchor_20260512T192622Z` | 2.5 GB | **E2c continuation warm-start origin** (the load-bearing ckpt) |
| `/workspace/tksCAS/noetic-compass-scaffold` | 5.7 GB | code |
| `/workspace/tksCAS/cas-synthetic` | 25 MB | corpora |
| `/workspace/tksCAS/stage6_v6_artifacts` | 3.8 MB | tokenizer |

Plus all small eval result dirs (eval_e2a_*, eval_e2b_* etc.) and pointer files (last_*_run.txt) — too small to matter.

## Post-cleanup verification

Required checks:
- `df -h /workspace`
- File count check: `ls /workspace/tksCAS/ | wc -l` should drop by ~22 entries
- Quota: `quota -v` (kernel may refuse this in container; `df` is the fallback)
- Quota headroom: ≥10 GB free, target 15-20 GB

## Destructive command

Generated below. Exact paths, no wildcards.
