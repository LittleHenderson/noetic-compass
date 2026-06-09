# Injection Two-Bridge — Spike Log (scientific record)

**Status:** SMALL-SCALE DIAGNOSTIC spikes. Unless explicitly tagged CONFIRMATORY, every entry is
**exploratory** and is **NOT** a continuation of the pre-registered H1/H2/H3 injection-detection
hypothesis. None of these are customer verdicts or the 20B headline. The matched control
(INJECTED_OVERT vs CLEAN_INSTRUCTION) is retained in every run.

## Run 1 — 2026-06-09 — Pythia-160M, output-text emitted bridge — GREY
- **Method:** internal η-profile of the PROMPT (mean-pooled, layer 4, noetic-10 probe) vs η-profile of
  the re-encoded EMITTED TEXT. n=20/arm.
- **Result:** Mann-Whitney p=0.328, rank-biserial=0.085 → **GREY** (no separation).
- **Diagnosis:** degenerate-text confound — Pythia-160M's greedy generations are repetition loops, so
  the emitted-text profile drifts from the prompt regardless of injection. The matched control caught it.

## Run 2 — 2026-06-09 — Pythia-160M, internal-during-generation bridge — GREY
- **Method:** prompt internal profile vs internal η-profile over the GENERATED token positions (same
  probe). Dodges the output-text confound (both sides are internal states). n=20/arm.
- **Result:** Mann-Whitney p=0.399, rank-biserial=0.050 → **GREY** (no separation; marginally weaker).
- **Diagnosis:** **substrate failure** — Pythia-160M is a base LM that IGNORES the injections (does not
  comply with "reply OWNED"; repeats in both arms). No hijack occurs → nothing to detect. Coheres with
  the harness's own verify-overt gate (these injections would not be marked `succeeded` on a base 160M).

## Run 3 — 2026-06-09 — Qwen2.5-1.5B-Instruct, internal-trajectory shift — EXPLORATORY (planned)
- **EXPLORATORY, NOT a continuation of the pre-registered H1/H2/H3.** Escalates to an INJECTABLE
  instruct model (the variable that matters is instruction-following, not size).
- **Method:** divergence between the prompt's internal state and the internal state DURING generation,
  via a **crude, model-agnostic raw-hidden-state readout (NO trained CAS probe).** n≈20/arm, matched control.
- ⚠️ **Claim caveat:** this measures *"did the internal trajectory shift mid-stream"* — a **different
  claim** than the registered *"internal state diverges from what it externalized."* A separation here
  does **NOT** validate CAS injection-detection; it is a different mechanism in the same family.
- **Gate:** confirm the injections actually **succeed** on Qwen (verify-overt) before interpreting —
  else it is the 160M substrate problem again.
- **Decision value:** clean separation → "internal bridge carries trajectory signal on an injectable
  model; build the Qwen CAS probe + run the registered method"; clean null → "method/operationalization
  problem, not scale; stop before the 40 GB spend."

---
*Standing conclusion: Pythia-160M is not a valid injection-detection substrate (not injectable). The
two-bridge method remains UNTESTED on a valid substrate — NOT falsified.*
