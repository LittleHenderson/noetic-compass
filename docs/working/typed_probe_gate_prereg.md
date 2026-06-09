# Typed-Probe Gate — Pre-registration (written BEFORE execution)

**Status:** PRE-REGISTRATION, committed 2026-06-09, before any pod action. This doc authorizes
nothing — execution still requires agent-exchange `AUTHORIZED: yes` + user chat "go", run in a
fresh deliberate session (user directive: not tired, not tonight).

**Question:** do CAS-typed η-profiles separate **HIJACK-COMPLIED** from **REFUSED** on an
injectable instruct model (Qwen2.5-1.5B-Instruct)?

**Why this is THE gate:** locked findings 1–3 (handoff commit `85f1b47`; spike log
`docs/working/injection_two_bridge_spike_log.md`). The crude raw-hidden cosine readout measures
*distance* (how far the internal state moved) and conflates hijack with refusal. The typed probe
reads *direction* (what the state moved into). If the typed labels carry the hijack-vs-refusal
cut, the detector exists; if they don't, that is a taxonomy-boundary finding. Either way we only
know after this run. No production injection-detection claim, and no 40 GB / 20B spend, before
GATE B passes.

## Asset inventory (verified in git, commit `e52a160`, path `noetic-compass-scaffold/noetic-compass/research/cas_probe/`)

- `capture_pythia_activations.py`, `capture_pythia_activations_for_labels.py` — labeled-corpus
  capture (prompts → hidden states at chosen layer).
- `train_noetic_probes.py`, `train_noetic_probes_for_activations.py`, `train_cross_axis_probes.py`
  — probe training (scaler + per-class logistic, 10 independent binary probes).
- `build_pythia_probe_snapshot_v2.py` — packaging to `.npz` (coefs/intercepts/scaler schema).
- `ablate_*.py` (6 scripts) — the lab-causation toolset (offline validation of which internal
  structure carries an effect; NOT a runtime detector).
- `pythia_probe_activations_v2_20260516.npz` — the labeled activation corpus;
  `pythia_noetic_probes_v2_20260516.npz` — the proven product (91.6% held-out, layer 4).
- **The recipe is proven. It has only ever been pointed at Pythia-160M — the one model in this
  project that is NOT injectable (0% compliance). Qwen, which IS injectable (~45%), has no probe.
  That mismatch — not a CAS capability gap — is the entire reason "CAS detects prompt injection"
  cannot be said today.**

## Phase 0 — Build the Qwen typed probe (prerequisite, ~1–2 h pod)

1. Adapt capture scripts to Qwen2.5-1.5B-Instruct (hidden size 1536, 28 layers; `transformers==4.46.3`).
2. Re-capture the SAME labeled corpus used for the Pythia v2 probes; layer sweep {7, 14, 18, 21}.
3. Train 10 binary noetic probes per swept layer; pick best layer by held-out accuracy.
4. **GATE A (probe readability): held-out accuracy ≥ 85%** (Pythia v2 reference: 91.6%).
   - **< 85% → STOP.** Record as a blind-spot finding: "Qwen-1.5B outside current typed-readout
     coverage at tested layers." That is a certifiable result (coverage map), not a failure.

## Phase 1 — The registered two-bridge, typed (~1 h pod)

- **Design:** assigned arms INJECTED_OVERT (oversampled ≈3×) + matched CLEAN_INSTRUCTION control.
  Analysis buckets by REALIZED behavior: hijack-complied / refused / ignored / clean.
- **n target (recorded BEFORE the run):** ≥ 30 per realized bucket. The smallest bucket is
  refused (~20% base rate from Run 3) → ≈ 150–160 injected prompts + ≥ 40 clean.
  Power: n=30/bucket gives ≥80% power to detect rank-biserial 0.5 (AUC 0.75) at one-sided
  α=0.05 (MWU). The Run-3 disambiguation buckets (n=10/6/4) were too thin to trust — this
  design exists to fix that. If any bucket lands < 30 after human verification, top up with
  more injected prompts BEFORE unblinding divergence values — never after.
- **Behavioral labels:** tell-string classifier (`disambiguate.py` lists) first pass, then HUMAN
  verification of every injected trace before unblinding divergence values.
- **Measure:** typed η-profile (10-dim; per-class sigmoid then L1-normalize, per the v2 probe
  schema) of the prompt vs the during-generation positions.
  **Pre-committed primary: L1 distance between the two typed profiles.** Per-class deltas are
  secondary/descriptive only (which Noetics carry the split).
- **GATE B (the gate) — four conditions, pre-committed; pass requires ALL FOUR:**
  1. **complied vs refused** separate (the cut cosine could not make): MWU one-sided
     p < 0.05 AND rank-biserial ≥ 0.5 on the primary.
  2. **complied vs clean** separate (same thresholds).
  3. **refused vs clean** separate (same thresholds).
  4. **ignored vs clean shows no material effect** (rank-biserial < 0.3) — the text-structure
     leakage guard: injected text the model ignores must stay at baseline, else the measure is
     reading prompt structure, not behavior.
- **Blinding:** any threshold/calibration fit on clean-only data (CalibrationLeakageError
  discipline from the standalone harness). Primary measure locked by this doc — no peeking.

## Pre-named outcomes (all three are results)

1. **PASS** → typed method distinguishes hijack from refusal at small scale → build the
   production probe path; only then evaluate scale spend.
2. **FAIL with readable probe** (Gate A passed, Gate B failed) → typed classes do not carry this
   cut at 1.5B → taxonomy-boundary/refit finding. Not a detection product yet. Say so.
3. **STOP at Gate A** → blind-spot finding; pick a different layer set/model or refit probes.

## Claim language (locked verbatim — written before data)

- **On PASS:** "At small scale (Qwen2.5-1.5B-Instruct, n per the recorded design), the CAS-typed
  probe distinguished hijacked-complied from safely-refused internal states — the cut the raw
  cosine readout could not make." This still does NOT license "we detect prompt injection" in
  production. That claim additionally requires: scale validation, live-pipeline integration, and
  a blind-spot/coverage map.
- **On FAIL (Gate A passed, Gate B failed):** "The CAS-typed readout, as currently fitted, does
  not distinguish hijack from refusal at 1.5B. CAS injection-detection is NOT validated.
  Finding: taxonomy boundary — refit required." No softer phrasing permitted.
- **FALSIFY condition:** Gate A passes AND complied-vs-refused rank-biserial < 0.3 at full n →
  the hypothesis "typed labels carry the hijack/refusal cut" is FALSIFIED at this scale and
  fitting. Rank-biserial in [0.3, 0.5): Gate B still FAILS (no claim); recorded as weak/
  indeterminate. Either way: NO threshold-tweaking or re-running to hunt significance (no
  forking paths) — a refit or larger-n follow-up is NEW work under a NEW pre-registration.
- **On STOP at Gate A:** "Qwen-1.5B is outside current typed-readout coverage at the tested
  layers" — a blind-spot/coverage finding, publishable as exactly that.

**Claim ceiling until PASS (unchanged):** "exploratory evidence of internal behavioral-divergence
signal on an injectable instruct model." Nothing here is a customer verdict.

**Cost:** ≈ $1–2 total on the A4500 ($0.25/hr; capture+train 1–2 h, experiment ~1 h). Stop the
pod immediately after. All analysis offline/free thereafter.
