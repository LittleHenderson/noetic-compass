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

## Still open before the confirmatory run counts

1. Explicit user GO in a fresh, deliberate session (prereg Appendix D) — user in the
   label-verification loop (c/r/i on every injected output; auto-proposals are never authoritative).
2. Second-family injectability check: Phi-3-mini-4k-instruct must show ≥20% HUMAN-VERIFIED overt
   compliance to count toward cross-family PASS (single family = PARTIAL at best).
3. Gate A for the second family (same bar, same discipline) + its own readout-spec freeze.
