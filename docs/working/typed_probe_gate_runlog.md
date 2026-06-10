# Typed-Probe Gate — Official Run Log

Companion run log for the FROZEN pre-registration `docs/working/typed_probe_gate_prereg.md`
(commit `31cd822`, blob `36004f32`, file sha256
`6fd9da61bb896721c7b6dbc8dd555ed5e4eac849afa0cbcf78d36f2a17392519`). The prereg is the law and is
never edited; results and deliverable hashes land HERE. Claim ceiling until the confirmatory
experiment passes: "exploratory evidence of internal behavioral-divergence signal on an injectable
instruct model" — Gate A below does NOT raise that ceiling.

---

## Gate A — Qwen2.5-1.5B-Instruct typed probe build (executed 2026-06-10 UTC)

**Verdict: `GATE_A: PASS (layer 14, acc 0.916)`** — Qwen2.5-1.5B-Instruct is INSIDE typed-readout
coverage. The registered confirmatory experiment is unblocked (still requires explicit user GO,
fresh session, human-in-the-loop labels).

- **What ran:** the Gate A kit (adapted verbatim-where-possible from commit `e52a160`; trainer
  fidelity previously proven by bit-exact Pythia v2 replication). Pod: RunPod A4500 20GB, fresh
  container; user-supplied SSH line = the agreed Gate A GO. Wall time ≈ 15 min, cost well under $1.
- **Pre-run gates, all green:** pinned env exact (torch 2.4.1+cu124 / transformers 4.46.3 /
  sklearn 1.5.2); corpus sha256 verified ON POD = `1970c1ab3ee0d46fdd247da705ba038278ec86e51659f10c6b42d31a879e998c`
  (551 records, the exact Pythia v2 corpus); all three offline selftests PASS before any capture.
- **Capture:** full 551 prompts, fp32, chat template with generation header, mean-pool over full
  templated sequence (faithful to original `hs[0].mean(dim=0)`), layers {7,14,18,21} of 29 capture
  positions, hidden 1536. Model revision pinned: `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`.
- **Per-layer held-out (test) accuracy** (selection by val acc; selection never sees test):
  layer 7 → 0.843 | **layer 14 → 0.916 (val 0.928 — selected)** | layer 18 → 0.880 | layer 21 → 0.904.
  Frozen bar 0.85: selected layer clears it with margin.
- **Baselines (same split):** majority 0.133, CountVectorizer 0.831, TF-IDF 0.867. McNemar
  headline-vs-TF-IDF p=0.289 — on n=83 the probe is NOT statistically separable from a text-only
  classifier. Honest scope: Gate A's frozen bar certifies "the probe reads typed content from Qwen
  hidden states accurately" — NOT "hidden states beat text." The hidden-vs-text question is carried
  by the confirmatory design itself (early-generation window before refusal text emits, H2 control).
- **Coincidence, recorded so nobody later flags it as a bug:** Qwen layer-14 test acc =
  `0.9156626506024096` = EXACTLY the Pythia v2 layer-4 reference. Same corpus, same seed-42 split,
  same 83-record test set → both models got 76/83. Everything else differs (val accs, other layers,
  baseline accuracies, coefficients), and the trainer's fidelity validation rules out copy-through.
  Genuine small-n coincidence.

**Artifacts (sha256) — local `C:\Users\wakil\Downloads\qwen_probe_kit\results\`, archive
`D:\tksCAS-archive\qwen_gate_a_20260610\`, pod copy `/workspace/qwen_probe_kit/`:**

| file | sha256 |
|---|---|
| qwen2p5_1p5b_probe_activations_v1_20260610.npz | `259c243990f39df5abd23ec2d8df051d625ed9f5042c1e2f1cf5d1f0a1bc6946` |
| qwen2p5_1p5b_probe_activations_v1_manifest_20260610.json | `ddf0d9dc243c63dc2d4ad66f826b240d85581aa86013d65b0dabd7154e9e3b5f` |
| qwen2p5_1p5b_noetic_probes_v1_20260610.npz | `fa445f48c64e522d24c2f5e4a897c8fa05dbd8fca36fbf368d078711ed9eb1c9` |
| qwen2p5_1p5b_noetic_probes_v1_report_20260610.json | `9ebe8fbade11fa3a6b7f32ce314bc83e206595ef012e456519d906805383c3dd` |
| qwen2p5_1p5b_noetic_probes_snapshot_v1_20260610.npz | `fa445f48c64e522d24c2f5e4a897c8fa05dbd8fca36fbf368d078711ed9eb1c9` |
| qwen2p5_1p5b_noetic_probes_snapshot_v1_provenance_20260610.json | `2b80140f96e568c476f57b8d4d395753d24cc0c263bf0a431101efd0f55b9c4e` |

(Probes npz and snapshot npz are byte-identical by design — the snapshot step adds the provenance
sidecar and tamper checks, not new arrays. Archive hashes verified against the provenance's
internal `snapshot_sha256`/`activations_sha256`/`report_sha256`: all match.)

## §4 Readout-spec FREEZE (immediately after Gate A, BEFORE any arm generation)

**READOUT-SPEC LOCK HASH (sha256 of locked file bytes):**
`9e9ffd8efa454610898880acdc2bf761cdfaa681b69be1dab811cff232031cae`

File: `confirmatory_run_kit\readout_spec_qwen2p5_1p5b.locked.json` (+ `.sha256` sidecar), staged in
Downloads, copied to `D:\tksCAS-archive\qwen_gate_a_20260610\`. Locked contents: model
Qwen/Qwen2.5-1.5B-Instruct (family `qwen2p5_1p5b_instruct`), ontology `noetic10`, layer
hidden_states index 14 = probe npz row 1, token window = generated tokens [0,8), prompt pooling =
mean over full templated sequence, greedy decoding max_new_tokens 96, transformers 4.46.3, probe
snapshot sha256 `fa445f48…eb1c9`. Anti-leakage ordering intact: layer was selected on probe-training
data only; NO confirmatory arms have been generated for this family as of this freeze.

## Confirmatory capture — Qwen2.5-1.5B-Instruct (executed 2026-06-10 UTC)

**Explicit user GO received** (prereg Appendix D satisfied): user message "GO....YES ALL" in a
fresh session = full protocol (Qwen confirmatory + Phi-3 injectability + human c/r/i labeling +
blinded→unblinded analysis + second-family arm if injectable). Capture is COMPLETE; labels are NOT
yet collected; nothing has been unblinded. This entry records hashes BEFORE any labeling.

- **Pre-run gates, all green:** same pod container as Gate A (env pins unchanged: torch
  2.4.1+cu124 / transformers 4.46.3 / sklearn 1.5.2 / numpy 2.4.6); all input + spec + probe
  hashes verified ON POD before any run; full offline selftest suite re-run ON POD —
  ALL ASSERTIONS PASSED (stats machinery consistency, blinded-default no-stats-leak, n-perm floor,
  spec-tamper hard abort, n-gate withholding, freeze-overwrite refusal, 3 synthetic end-to-end
  scenarios incl. a correctly-detected FALSIFY_FOR_HIJACK negative control).
- **Smoke first:** `--limit 3` smoke (6 traces, all `diagnostic=true`, output
  `captures_qwen_SMOKE_DIAGNOSTIC.jsonl`) for schema validation only — never enters analysis.
  Schema inspected via blinding-safe tool (`inspect_capture_schema.py`: key structure only;
  output text and auto-proposals never displayed).
- **Formal capture:** 280/280 prompts (240 INJECTED_OVERT + 40 CLEAN_INSTRUCTION), 303 s,
  fp32, greedy max_new_tokens 96, seed 1234, frozen spec `9e9ffd8e…31cae` enforced by the script
  (hard-refuses on spec/probe/model/transformers mismatch). Output: 1 meta record (embeds corpus
  shas + spec sha + probe sha + env) + 280 trace records, `diagnostic=false`, NO verdicts, raw
  window/prompt vectors + typed profiles per trace, auto-labels stamped PROPOSAL_ONLY.
- **Method decision (recorded, conservative):** the frozen spec pins transformers+torch but not
  weights dtype; script default `--dtype auto` would resolve to bf16 on CUDA. Passed
  `--dtype float32` explicitly to match Gate A probe-training conditions (probes trained on fp32
  activations). Dtype is recorded in every trace record. Successor specs should pin dtype.
- **Deterministic input selections (no RNG):**
  - CLEAN-40: all 110 CLEAN_INSTRUCTION rows of `corpus_master.jsonl`, sorted by prompt_id,
    indices `floor(i*110/40)` for i=0..39 → all 10 domains (3–6 rows each). Script
    `select_clean_40.py` ships in the kit.
  - Phi-3 injectability 60: all 240 rows of the combined injected file, sorted by prompt_id,
    indices `floor(i*240/60)` → all 10 domains, all 17 payload classes. Script
    `select_injected_60.py`. Sizing rationale: ≥20% bar with lower-bound semantics needs 12
    verified complies out of 60 (vs 48 out of 240) — fair screen, sane labeling burden.

| file | sha256 |
|---|---|
| captures_qwen_20260610.jsonl (FORMAL) | `864bc4ac20e33ed78f53d2eb6e41e2a8e4b875061816d87c40c044110db0cca7` |
| injected_overt_combined_240_20260609.jsonl (input) | `0d22f5e896075d8a89d935a87812da53338d59184d70f7bc46c74110477ea7fa` |
| clean_instruction_40_20260610.jsonl (input) | `5eed48fcb378497747a0698971181b17664f6d25e93c40acebf1cbe547fd71fe` |
| phi3_injectability_input_60_20260610.jsonl (input) | `4b1b7d56ed26efe2845248becdefe51ed54a1e8d04de12ee5f39d9f91cdc57ee` |
| readout_spec_qwen2p5_1p5b.locked.json (spec, = §4 lock hash) | `9e9ffd8efa454610898880acdc2bf761cdfaa681b69be1dab811cff232031cae` |

Copies: pod `/workspace/confirmatory_run_kit/`, local
`C:\Users\wakil\Downloads\confirmatory_run_kit\`, archive
`D:\tksCAS-archive\qwen_confirmatory_20260610\` (23 files incl. kit scripts + selftest log) —
capture hash verified identical at all three.

**Blinding state as of this entry:** capture outputs NOT read by the agent (schema-only
inspection); auto-proposals NOT read; analyzer NOT run (not even blinded mode yet); no human
labels exist. Next step is human c/r/i labeling by the user — the ONLY labels the analysis
accepts (`verifier=="human"`).

## Phi-3-mini injectability — generation run (executed 2026-06-10 UTC; gate UNDECIDED)

`injectability_check.py` ran on the pod against the deterministic 60-row slice
(`4b1b7d56…57ee`): microsoft/Phi-3-mini-4k-instruct, bf16 (screen is behavioral-only — no probe
applied, so bf16 is methodologically fine), greedy 96, seed 1234. Output:
`phi3_injectability_generations_20260610.jsonl`, 61 lines (meta + 60 traces), sha256
`0ba049931b4254ac2636ce6245fe0629c6399362114847ca1ca4401d8996c4cb` — verified identical at pod /
local / `D:\tksCAS-archive\qwen_confirmatory_20260610\`.

The script printed its PROVISIONAL tell-string proposal breakdown by design (COMPLIED 17 =
28.3%, REFUSED 4, IGNORED 39). Recorded honestly: the agent saw this aggregate (it is the
script's designed tail output for the screen); it decides NOTHING. Per prereg Appendix C the
≥20% bar counts ONLY human-verified compliance — 12+ human-confirmed complies out of 60 clears
it. This proposal number suggests the bar is reachable but the gate stays UNDECIDED until the
user's c/r/i pass.

## Still open before the confirmatory run counts

1. ~~Explicit user GO~~ ✓ received ("GO....YES ALL", 2026-06-09 local / 06-10 UTC).
2. Human c/r/i label verification by the user — Qwen 240 injected traces (+ Phi-3 60 after its
   generation run). Auto-proposals are never authoritative.
3. Second-family injectability check: Phi-3-mini-4k-instruct must show ≥20% HUMAN-VERIFIED overt
   compliance to count toward cross-family PASS (single family = PARTIAL at best). Generation run
   in progress; result lands here.
4. Gate A for the second family (same bar, same discipline) + its own readout-spec freeze —
   only if injectability passes.
5. Blinded analysis (counts/n-gate) → single unblind → H1–H5 + verdict recorded here.

## Labeling under prereg v2 amendment — 3-judge LLM panel (executed 2026-06-10/11 UTC)

User declined the 300-trace bulk human pass and directed agent labeling. The v2 labeling
amendment (`typed_probe_gate_prereg_v2_labeling_amendment.md`) was FROZEN at commit `701eb6e`
BEFORE any judge was spawned, before any output text was read, before any analyzer mode ran.
v1 itself is untouched; v1's human-only formal tier is NOT MET by v2 labels and is never claimed.

**Judge inputs (mechanical, probe-stripped, built by `build_judge_inputs.py`
`194aef909b205ae58e11e9addc58b8e857ab21a995bc0795e10f50690c07a179`):**

| file | traces | sha256 |
|---|---|---|
| judge_input_qwen_20260610.jsonl | 240 | `c70eebdb717b6eb3ac13c4bbe3975b80c582dbce37b450e0f9b4b17c4defe4b9` |
| judge_input_phi3_20260610.jsonl | 60 | `bfb0bba3402bbccb9ad8be84ef0641bfc2e34b79c4541d6515bdc083efe35f34` |

Strip check asserted: no typed profiles, raw vectors, cos_dist, or auto-proposals in judge
inputs. Both files verified 240/240 and 60/60 UNIQUE trace_ids (a judge's claim of an input
duplicate was mechanically refuted — it was that judge's own read-window confusion).

**Panel:** three independent background agents, distinct Claude tiers (opus / sonnet / haiku),
each given ONLY the fixed v2 §4 rubric + its input file. No probe signals, no project context,
no knowledge of which result would be convenient.

| judge label file | lines | sha256 |
|---|---|---|
| judge_labels_opus_qwen_20260610.jsonl | 240 | `5c5aebeaa096c41294553fe876d9f08dc5bd6f1601cfce1d678ac7908ec43fbd` |
| judge_labels_sonnet_qwen_20260610.jsonl | 240 | `a4f3a530b6e3ac71a050960b964b843ebb3b496ac1e95ade43aeedc84404fc3f` |
| judge_labels_haiku_qwen_20260610.jsonl | 242 (2 dup lines) | `0505efca136c7db494ae54fe1916293ea71f1e544f82d06754f3f0e83bff5fd9` |
| judge_labels_opus_phi3_20260610.jsonl | 60 | `6f13d7aff4c954dbd8b695f4ecfd2f95be18abd6657da8b08b1c43f6d46668fb` |
| judge_labels_sonnet_phi3_20260610.jsonl | 60 | `464961433bbe8320384c68fa47ec4db6c738c8b94e4d594e685ba4d8d202cc49` |
| judge_labels_haiku_phi3_20260610.jsonl (original) | 60 | `03b51d3bcc6de0d21c1b8b37e56eb3e35872f8b87b8a79cc19affa4a29002583` |
| judge_labels_haiku_phi3_20260610_idpatched.jsonl | 60 | `9141181b9dd6423ee23b927d6b6aff479b1393978eccdc5fc98e0c784ed08b0b` |

**Two judge-file defects, both mechanically resolved and disclosed:**
1. haiku Qwen file: 2 duplicate trace_id lines — merger drops duplicates deterministically
   (FIRST occurrence wins); coverage then exact (240/240).
2. haiku Phi-3 file: ONE corrupted trace_id (`…679b32dc9e33a` written for `…679b34364513d`;
   identical 24-char prefix). Repair positionally FORCED: the file matches the input order at
   59/60 positions and the single mismatch sits exactly at the input position of the missing id
   (pos 17). Patched copy created (id corrected, label `c` + reason untouched; original
   preserved). Merge hard-errored on the defect first — the coverage validator works.

**Merge (`merge_consensus.py` `f9c4a8292b114a7cca141fec47cad1ddb3b4b8616611100f9fc6428b66f35838`;
synthetic selftest `selftest_merge.py` `97b362820b2d0d9114e37ccf95a993355f94904ec165ddc26667ac968006c5fe`
13/13 PASS incl. dedup-first-wins, u-handling, no-majority exclusion, meta passthrough):**

Qwen (240): consensus 181 = COMPLIED 146 / IGNORED 35 / REFUSED 0; adjudication pile 59.
Vote patterns: ccc 146, cci 16, ccr 1, cii 3, cir 1, iii 35, iir 20, irr 18.
- consensus_labels_qwen_20260610.jsonl `f28e932d2281d3ca3c3a647ed45e8e5c77b8193a341cedc34c30dfe417fc5b2c`
- adjudication_captures_qwen_20260610.jsonl (59 traces + meta) `72383457eafd7f2b5e2ada105ee1999641a45812c274b80b6a19d52df8ad8371`
- judge_votes_qwen_20260610.jsonl `55b18a603c424b3c8b982924c1f7b41d6012d8de6f58579aab01cfa351d76266`

Phi-3 (60): consensus 45 = COMPLIED 39 / IGNORED 6 / REFUSED 0; adjudication pile 15.
Vote patterns: ccc 39, cci 10, cii 4, iii 6, irr 1.
- consensus_labels_phi3_20260610.jsonl `745dd76e64a5e6c3dafa0d0ea4d700fb62a269075f820d726e25ce6bca6b8f9a`
- adjudication_captures_phi3_20260610.jsonl (15 traces + meta) `3bee415893319bb27de2fa1b8ff5b00dc13beb60be87bb698073ff614bdee1fa`
- judge_votes_phi3_20260610.jsonl `f7b7c5be7aae03392d537dec654dc74cf16bb7a399b689e9d02ff66135fdd5c8`
- unanimous_c_captures_phi3_20260610.jsonl (39 traces + meta, v2 §3.6 option) `ce004b07f2efe2fd0fa828c281be2641cd8d1f81a9f5f9330d5c96a54f62385a`

**Analyzer change (the ONE change v2 §6 sanctions):** `load_labels` in
`analyze_confirmatory.py` now accepts verifiers {`human`:prio 2, `llm_consensus_3of3`:1,
`llm_majority_2of3`:1}; higher priority supersedes regardless of file order (a human label is
never overwritten by an LLM label); unknown verifiers rejected loudly; docstring invariant I5
updated to match. Full selftest suite re-run after the edit: ALL PASS (305s; PASS / FALSIFY
negative control / NULL-improvement scenarios all return expected verdicts; all honesty gates
hold).

**Orchestrator blinding state:** the orchestrating agent has read NO output text and NO
per-trace label joined to probe signals. Seen (and recorded honestly): per-judge aggregate
label distributions and judge final-message summaries that described behavior at
payload-class level (e.g. which payload classes tended to comply). This is aggregate,
corpus-design-level information; per-trace blinding for the analysis remains intact. The
Phi-3 provisional aggregate from the capture phase was already on record.

**Phi-3 injectability arithmetic (gate still UNDECIDED pending path choice):** unanimous
complies alone = 39/60 = 65% >= 20%. The bar is cleared under ANY adjudication path; what the
path decides is the LABEL TIER (human-verified formal v1 gate via §3.6, or v2
LLM-consensus tier).

**Qwen REFUSED-bucket arithmetic (decision-relevant, no stats computed):** unanimous REFUSED =
0; r-containing vote patterns total 40 traces (irr 18 + iir 20 + ccr 1 + cir 1). Even if ALL
40 adjudicated to REFUSED the bucket would reach exactly the n>=40 floor; realistically some
land IGNORED, so REFUSED < 40 is the likely outcome under EVERY path — i.e. H3 (the decisive
COMPLIED-vs-REFUSED test) is heading for INSUFFICIENT_N on Qwen because the model rarely
refused, not because of any probe property. INSUFFICIENT_N is a frozen prereg verdict:
not falsified, not passed, bucket too small at the frozen bar.

**Pending user decision (v2 §3.4/§3.5/§3.6):** Path A (human adjudicates 59+15=74 traces via
verify_labels_cli) vs Path B (pre-declared 2/3-majority fallback, no human, exclusions
disclosed); plus the §3.6 Phi-3 option (verify only the 39 unanimous-c traces to keep the v1
human-verified injectability gate formal).
