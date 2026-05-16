# CAS Probe — Pythia interpretability experiment (research-only)

**Status:** research, not production. **DO NOT** import anything in this
directory from `api/`, `cas-native/`, `dashboard/`, or any production stack.

## Purpose

Test the central pitch of CAS Mode 7 against a fully-open language model:

> When a language model processes English text, are CAS structural axes
> (noetic, domain, register, drive) detectably present inside the model's
> internal activations — not just on its output?

If yes, CAS gives us a real interpretability handle on any open model.
If no, the CAS framing requires explicit training to surface, and the
"Mode 7 as anti-black-box" pitch needs revision.

Two tests:

1. **Detection (Stage 2).** Train a small linear classifier (a probe) to
   read CAS axis labels from Pythia hidden states. If the probe does
   better than chance, the structure is detectably in there.
2. **Causal influence (Stage 3, gated on Stage 2).** Mess with the
   detected direction inside Pythia (turn it down, scramble it) and see
   if the output changes. If yes, the structure is not just there —
   it's load-bearing.

## Isolation guardrails (user-ratified 2026-05-15)

This directory is sandboxed. Hard rules:

1. **Branch:** all work on `experiment/cas-probe-pythia`. Never merged to
   `master` without separate audit + explicit user approval.
2. **Directory:** code lives ONLY under `research/cas_probe/`. No Pythia
   imports anywhere else.
3. **Production isolation:** no Pythia imports in `api/`, `dashboard/`,
   `cas-native/` loader, chat REPL, or training stack. Pythia is the
   test subject, not part of CAS Native.
4. **Frozen labels:** the probe never reads live Wave 2.5 / Wave 3
   corpus files. It uses a frozen snapshot named
   `pythia_probe_labels_YYYYMMDD.jsonl` with a companion manifest
   (sha256, source files, record count, extraction rules).
5. **Naming:** all artifacts prefixed `pythia_` or marked
   `research_only`.
6. **Failure protocol:** if the experiment fails or is abandoned, delete
   this branch and the artifacts cleanly. CAS Native is untouched.

The key invariant: **Pythia never becomes CAS Native. It is the test
subject. CAS is the measuring instrument.**

## Stages

| Stage | Status | Deliverable |
|---|---|---|
| 1.0 | done | `README.md`, `build_pythia_probe_snapshot.py`, frozen labels jsonl, manifest |
| 1.1 | done | Pythia-160M activation capture script + smoke test |
| 2 | **done — strong signal** | linear probe training over captured activations |
| 3 | pending (eligible) | causal-influence ablation |

## Stage 2 headline result (2026-05-16)

**Verdict: STRONG_SIGNAL.** Best-layer noetic probe test accuracy
**92.8%** against a 10% chance baseline. All 13 layer positions cross
the 30% strong-signal threshold the README pre-committed to.

| Layer | Train acc | Val acc | Test acc | macro-F1 |
|---:|---:|---:|---:|---:|
| 0 (embed) | 1.000 | 0.855 | 0.884 | 0.886 |
| 1 | 1.000 | 0.884 | 0.913 | 0.912 |
| 2 | 1.000 | 0.884 | 0.913 | 0.912 |
| 3 | 1.000 | 0.899 | 0.899 | 0.902 |
| **4** | 1.000 | 0.899 | **0.928** | **0.931** |
| 5 | 1.000 | 0.884 | 0.928 | 0.926 |
| 6 | 1.000 | 0.855 | 0.913 | 0.916 |
| 7 | 1.000 | 0.812 | 0.884 | 0.884 |
| 8 | 1.000 | 0.841 | 0.899 | 0.902 |
| 9 | 1.000 | 0.812 | 0.884 | 0.887 |
| 10 | 1.000 | 0.812 | 0.870 | 0.868 |
| 11 | 1.000 | 0.812 | 0.884 | 0.886 |
| 12 | 1.000 | 0.812 | 0.870 | 0.872 |

Trained in 1.5 sec on CPU. Split: 319 train / 69 val / 69 test
(stratified, seed=42). Logistic regression with L-BFGS, balanced class
weight, StandardScaler fit on train only.

**What this means.** Pythia-160M's internal representations of these
English descriptions are detectably aligned with the CAS noetic axis at
~90%+ accuracy from layer 1 onward, peaking around mid-network
(layers 4-5).

**Honest caveats reviewers should expect to push on.**

1. **Lexical-vs-conceptual ambiguity.** The English descriptions were
   written by Claude with knowledge of the source CAS expression.
   Claude probably embedded stylistic patterns per noetic (^2 →
   "drawn", "attraction"; ^3 → "resisting", "rejecting"; ^7 →
   "groove", "practice"). The probe could be reading those surface
   features rather than deep conceptual structure. This is the
   classic interpretability problem.
2. **Train accuracy 1.000 on every layer.** That is expected for L2-
   regularized logistic regression with 768-dim features and only
   ~32 samples per class in train. Generalization gap (train minus
   test) is 7-13 pp, which is consistent with the probe not just
   memorizing.
3. **Small test set.** 69 samples means ~7 per class on average. The
   92.8% point estimate has wide confidence intervals; real accuracy
   on a held-out distribution might be 85-97%.
4. **Single architecture.** We haven't shown this transfers. OLMo or
   Qwen need to be probed before the Glass House pitch is
   defensible.

Stage 3 (causal ablation) is the right next move because it
disambiguates point 1. If ablating the detected direction changes the
output in a way that matches the noetic semantics, the structure is
real. If it just scrambles output, the probe is reading surface
features and the Glass House claim needs revision.

Artifacts on disk:

- `pythia_noetic_probes_20260515.npz` — trained probes (coefs,
  intercepts, scaler params, per-layer).
- `pythia_noetic_probes_report_20260515.json` — full per-layer
  metrics, split indices, decision gates, verdict.

## Files

- `.gitattributes` — pins LF line endings on the research JSON / JSONL /
  Python / Markdown files so the manifest's sha256 of the snapshot
  matches the on-disk bytes on any host (Windows, Linux, macOS).
- `pythia_probe_source_wave3_cas_to_english_20260515.jsonl` — vendored
  slice of the wave3 corpus, containing only the 1,129 `cas_to_english`
  records. Vendored inside the branch so a clean checkout can rebuild
  the labels snapshot without depending on out-of-branch files.
- `build_pythia_probe_snapshot.py` — joins the vendored wave3 slice with
  `cas-synthetic/data/path_d/seeds.jsonl` (tracked at its canonical
  path) and writes a frozen snapshot + manifest. Deterministic: re-running
  with the same source files produces byte-identical output. Includes a
  regex-based CAS-notation leakage filter (added post-audit) so the
  probe cannot read its label off the prompt.
- `pythia_probe_labels_20260515.jsonl` — frozen labels for the
  experiment. **Read-only.** Regenerate by re-running the builder.
- `pythia_probe_manifest_20260515.json` — sha256 of the snapshot,
  source-file paths + hashes, record count, class distribution,
  extraction rules in plain text, and rejection counts (including the
  new leakage-regex rejections).
- `capture_pythia_activations.py` — Stage 1.1 capture script. Loads
  Pythia-160M, mean-pools hidden states per layer, dumps a `.npz`. NOT
  YET RUN — requires explicit user OK to install `transformers` and
  download Pythia weights.

## Decision gates

- **Stage 2 pass:** best-layer noetic-probe test accuracy ≥ 30%
  (vs 10% chance baseline across 10 noetic classes).
- **Stage 2 weak:** 20%–30%. Run ablation analysis to understand which
  noetics are detectable and which are not.
- **Stage 2 fail:** <20%. CAS structure is not naturally factored in
  Pythia's activations at the prompt-encoding level. Revisit:
  (a) try later layers, (b) try generation-side encoding, (c) declare
  the CAS framing requires explicit training to surface.
- **Stage 3 pass:** ablating the detected direction changes the output
  measurably (output similarity drops below a threshold).

## What CAS Mode 7 means here

Mode 7's mechanistic-attribution surface (`Mode7LiveShell` in the
dashboard, `api/routes/mode7.py` on the backend) was built against CAS
Native's own activations — which have named axes by construction.

For a fully-open foreign model like Pythia, "Mode 7" means the same
*idea* — bind activations to CAS commitments, trace them through the
network, test their causal role — but the binding needs trained probes
because Pythia doesn't have CAS axes baked into its architecture.

If this experiment succeeds, the pitch becomes: *"Mode 7 works on any
open-weight model after training probes; with CAS Native, the probes are
the architecture."*
