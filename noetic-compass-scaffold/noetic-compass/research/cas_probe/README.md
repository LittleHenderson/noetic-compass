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
| 1.1 | pending | Pythia-160M activation capture script + smoke test |
| 2 | pending | linear probe training over captured activations |
| 3 | pending (gated) | causal-influence ablation if Stage 2 passes |

## Files

- `build_pythia_probe_snapshot.py` — joins `cas-synthetic/data/path_d/wave3_full/wave3_smoke_*.jsonl`
  with `cas-synthetic/data/path_d/seeds.jsonl`, filters to records with
  exactly one noetic, writes a frozen snapshot + manifest.
- `pythia_probe_labels_20260515.jsonl` — frozen labels for the
  experiment. **Read-only.** Regenerate by re-running the builder with
  the same source files.
- `pythia_probe_manifest_20260515.json` — sha256 of the snapshot,
  source file paths + hashes, record count, class distribution, extraction
  rules in plain text.

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
