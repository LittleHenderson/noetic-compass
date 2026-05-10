# v0-rc1 — Noetic Compass CAS-Native v0 Release Candidate

**Status:** Frozen 2026-05-10. Code tag created locally; checkpoint
archived locally with SHA-256 hashes populated below. Push pending
user confirmation.
**Release-candidate composition:** Git tag `v0-rc1` freezes the
inference/scaffold code. The runtime checkpoint is archived separately
and is part of the release **by SHA-256, not by git**.

Per the audit-modified v1e design doc
(`docs/working/v1e_pointer_copy_fractal_decoder_design_2026_05_10.md`),
freezing v0-rc1 is non-negotiable and goes first. Phase 1B
(opt-in shadow-mode fractal decoder) only proceeds against this frozen
baseline.

---

## 1. Code freeze — `v0-rc1` git tag

| Field | Value |
|---|---|
| Tag | `v0-rc1` (annotated) |
| Commit SHA | `255b2a7a1749301f184c5dff59551badf85a601d` |
| Commit short | `255b2a7` |
| Commit message | *"Fractal repair Phase 1: strict log-only verifier — records not close"* |
| Commit author / date | LittleHenderson, 2026-05-10 08:40 PDT |
| Tag message | *"v0 release candidate — v1c+scaffolds 18/24 baseline state"* |
| Tag author / date | LittleHenderson, 2026-05-10 14:29 PDT |
| Push status | LOCAL ONLY (awaiting user confirmation to push master + tag) |

### 1.1 Inference stack frozen at `v0-rc1`

The 8 inference files at `v0-rc1` and their blob SHAs (from
`git ls-tree -r 255b2a7 -- noetic-compass-scaffold/noetic-compass/cas-native/inference`):

| File | Blob SHA |
|---|---|
| `cas-native/inference/identifier_repair.py` | `11b883b481659c0a4a47bba2dea809b42a6dda97` |
| `cas-native/inference/fractal_repair.py` | `11c5ad26948d0df0b59e70b5160c3a2a6a962a8e` |
| `cas-native/inference/postprocessor.py` | `32985e73112bd9da97498d6c5d964dd5d759f5a0` |
| `cas-native/inference/rpm_retry.py` | `3ddc3470a802a06ed460a7cc592ee808f052cfa6` |
| `cas-native/inference/rpm_repair.py` | `686269d98204d6a0409f02da3a40bb64401d1459` |
| `cas-native/inference/routed_generate.py` | `6ac25ca6355eeffaf75d9f7984a9cbba39369d92` |
| `cas-native/inference/generation_cleanup.py` | `b2a5e82a8dee19f815090a988df07390367c3b95` |
| `cas-native/inference/meta_logic_repair.py` | `cd23d954340d01efc040ffe61dc472bb64115025` |

Inference behavior at this commit matches the 18/24 acceptable+ audit
(see §3). The `fractal_repair` module is **log-only** at this commit —
it parses Φ<…> and reports `cardinality_matches` / `sequence_matches`
but never mutates `final_text`. No behavioral diff vs the audit run.

### 1.2 What is explicitly NOT in v0-rc1

The 3 post-audit, v1d-driven inference-vocab patches were EXCLUDED:

- `9015f42` — cardinality regex (meta_logic_repair) + abutting-indicator
  dedup (fractal_repair)
- `810b66e` — `_NOETIC_INDICATORS` vocab expansion across 5 inference
  files + meta-logic prompt tuning
- `879b551` — narrow vocab patch

These belong on the v1e path and are to be re-evaluated against the
expanded fractal eval suite during Phase 1B.

All v1d corpus/regen/retrain commits (`153dd49` through `c88bcf4`) are
also EXCLUDED from v0-rc1.

---

## 2. Runtime checkpoint archive

**Important:** the git tag freezes inference code only. The runtime
**model checkpoint is part of the release by SHA-256**, archived
separately, NOT in git.

### 2.1 Checkpoint identity (verified against pulled manifest)

| Field | Value |
|---|---|
| Logical name | `v1c VALIDTOK 5ep` |
| Description | v1c base + `[VALID]`/`[INVALID]` task-token extended tokenizer, 5-epoch training |
| Pod run-dir | `/workspace/tksCAS/noetic-compass-scaffold/noetic-compass/cas-native/training/runs/v1c_VALIDTOK_5ep_20260510T014338Z/` |
| Run start | 2026-05-10T01:43:38Z (from `run_info.txt`) |
| Archive path | `D:\tksCAS-archive\v0_rc1\v1c_VALIDTOK_5ep\` |
| Pulled date | 2026-05-10 |
| `checkpoint_id` (from manifest) | `ad158110-3654-4977-b2ed-d7656b0bf289` |
| `global_step` | 8790 |
| `tokenizer_kind` | `ExtendedHybridCASTokenizer` |
| `extended_vocab_size` | 38685 (base 38683 + 2 task tokens) |
| `reserved_token_count` | 253 (base was 198; +55 includes `[VALID]`/`[INVALID]`) |

Identity verification rationale: distinct `checkpoint_id` from
b3_full_50k base (`7ae0a6ab-cac1-4ac7-96d8-605448c282e4`), distinct
vocab size (38685 vs 38683), distinct global_step (8790 vs base 14845),
distinct pod run-dir matching the 18/24-audit-era timestamp.
This IS v1c VALIDTOK 5ep, not v1d (which lives at
`v1d_VALIDTOK_2ep_20260510T183743Z` on the same pod).

### 2.2 Archived files and SHA-256 hashes

| File | SHA-256 | Size (bytes) | Pulled date |
|---|---|---:|---|
| `model_final.pt` | `52544C7CB69176B52C608E90081BCE330DC06DCE91F9536D410A33B4B4DACB25` | 585,047,108 | 2026-05-10 |
| `tokenizer.json` | `9C544425C9C08140070B2F3929ADEF864BBFAFB0C00C1D687F2D6B98E0589B9B` | 446,446 | 2026-05-10 |
| `english_bpe.json` | `AC4D12A6D26CC1194EA31FEE8CDC07D52A0A759964810956B13CAFEA08A06889` | 1,455,353 | 2026-05-10 |
| `checkpoint_manifest.json` | `B5506C796D2D058BFD323F9B4DFE341947C065770C745445228067478717091B` | 42,680 | 2026-05-10 |

Additional archived file (not part of the SHA-pinned release tuple but
preserved for traceability):

| File | Size (bytes) | Purpose |
|---|---:|---|
| `run_info.txt` | 98 | Run-dir name + PID + UTC start timestamp |

**SHA-256 recomputation command** (PowerShell, for verification on any
machine):
```
Get-FileHash -Algorithm SHA256 "D:\tksCAS-archive\v0_rc1\v1c_VALIDTOK_5ep\model_final.pt"
Get-FileHash -Algorithm SHA256 "D:\tksCAS-archive\v0_rc1\v1c_VALIDTOK_5ep\tokenizer.json"
Get-FileHash -Algorithm SHA256 "D:\tksCAS-archive\v0_rc1\v1c_VALIDTOK_5ep\english_bpe.json"
Get-FileHash -Algorithm SHA256 "D:\tksCAS-archive\v0_rc1\v1c_VALIDTOK_5ep\checkpoint_manifest.json"
```

Cross-check: the `english_bpe_hash` field in `checkpoint_manifest.json`
(`ac4d12a6...08a06889`) matches the SHA-256 above for `english_bpe.json`
↔ this confirms the BPE file was not corrupted in transit and matches
what the training run consumed.

---

## 3. Frozen `routed_generate` flag profile (v0 deployed behavior)

These are the inference flags that produced the 18/24 audit. The
v0-canary CI gate (§5) compares byte-for-byte against the frozen
baseline outputs generated under these flags.

```python
apply_repair = True                  # Phase 1 repairs ON
apply_rpm_retry = False              # Phase 3 corrective-retry shipped but OFF (negative result)
seed_rpm_silhouette = True           # rpm decoder seed default-on (commit c820e8b)
prepend_task_token = True            # [VALID]/[INVALID] task-token routing
apply_fractal_decoder = False        # v1e Phase 1B mechanism; NOT in v0
apply_pointer_copy = False           # v1e Phase 3 mechanism; NOT in v0
apply_aux_heads = False              # v1e Phase 2β mechanism; NOT in v0
```

---

## 4. Frozen eval baseline (18/24 acceptable+)

| Field | Value |
|---|---|
| Audit file | `cas-synthetic/data/path_d/v1_eval_pack_24records_20260510T072551Z_CODEX_GRADED.md` |
| Eval-pack JSONL | `cas-synthetic/data/path_d/v1_eval_pack_24records_20260510T072551Z.jsonl` |
| Eval-pack MD | `cas-synthetic/data/path_d/v1_eval_pack_24records_20260510T072551Z.md` |
| Acceptable+ count | 18/24 |
| Strong band (green + high yellow) | 10/24 |
| Green records | 1, 2, 4, 6, 7, 23, 24 (count: 7) |
| High yellow | 17, 18, 21 (count: 3) |
| Yellow | 3, 5, 8, 9, 11, 19, 20, 22 (count: 8) |
| Wrong / flop | 10, 12, 13, 14, 15, 16 (count: 6) |
| Grader | Codex |

This is the baseline the v0-canary CI gate locks in.

---

## 5. v0-canary CI gate (DETERMINISTIC, AUTOMATED)

Per audit-modified design doc §3.1 step 4:

- **Trigger:** any PR touching `noetic-compass-scaffold/noetic-compass/cas-native/inference/**` or `noetic-compass-scaffold/noetic-compass/cas-native/model/**`.
- **Action:** run the 24-record eval pack
  (`cas-synthetic/scripts/v1_eval_pack_24records.py`) against the
  archived `v1c_VALIDTOK_5ep` checkpoint with the `routed_generate`
  flag profile from §3.
- **Comparison:** per-record `final_text` byte-for-byte against the
  archived baseline outputs in
  `v1_eval_pack_24records_20260510T072551Z.jsonl` (specifically the
  `final_text` field per record).
- **Behavior on diff:** any byte-level diff BLOCKS the PR and surfaces
  the diff for human review. The diff is the failure signal.
- **What this is NOT:** the canary does NOT require fresh human grading
  per PR. It compares to a frozen-text baseline. Re-baseline only when
  the user explicitly approves a `v0.N-rc` bump.

Implementation note: the CI harness needs the archived checkpoint
accessible at a known path. The simplest production setup is to mount
the `D:\tksCAS-archive\v0_rc1\v1c_VALIDTOK_5ep\` directory into the CI
runner; alternatively, the CI runner pulls the checkpoint at start by
SHA-256 from a content-addressed store.

---

## 6. Kill-switch criteria

Per design doc §4 (heuristic, user-confirmed at each fork; no
auto-pivot):

- B-grade pattern looks like Path γ → surface simplex pivot to user.
- C-grade returns regression on 24-pack canary → v1e checkpoint
  discarded; v0-rc1 stays deployed.
- A-grade returns flat on records 10/11/12 → A not funded.
- Cumulative cost exceeds 12 eng-weeks before A ships → surface
  simplex to user.
- `v0-canary-evaluation` ever fails on the deployed v0-rc1 checkpoint
  with `apply_fractal_decoder=False` → freeze guarantee broke; debug
  before any further v1e work.

---

## 7. Re-baseline policy

The frozen eval baseline (§4) and frozen flag profile (§3) are NOT
modified except by explicit user-approved `v0.N-rc` bump. v1e Phase 2
Path α (B promotes to production default) is the first scheduled
re-baseline event.

When a re-baseline happens:
- New tag `v0.N-rc1` on the new commit.
- Updated `V0_RELEASE_CANDIDATE.md` with new flag profile, new
  archived baseline outputs, new SHA-256 hashes if checkpoint changes.
- The prior v0-rc tag remains in git history as the prior canary
  reference.

---

## 8. Open items before v0-rc1 is complete

- [x] Pull `model_final.pt`, `tokenizer.json`, `english_bpe.json`,
  `checkpoint_manifest.json` from RunPod to
  `D:\tksCAS-archive\v0_rc1\v1c_VALIDTOK_5ep\`. (2026-05-10)
- [x] Compute SHA-256 for all 4 archived files; fill §2.2 table.
  (2026-05-10)
- [x] Verify the archived `checkpoint_manifest.json` references the
  v1c VALIDTOK 5ep run-dir on the pod and has distinct
  `checkpoint_id` + vocab size 38685 vs base. (See §2.1)
- [ ] Commit the release doc + push `v0-rc1` tag to `origin` (awaiting
  user go-ahead).
- [ ] Implement the v0-canary CI harness per §5 (separate task,
  blocks v1e Phase 1B per task #133).
