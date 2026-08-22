# V12 — Framing-matched Operator-10 control: does the FLAGSHIP survive stripping the colloquialisms?

**Date:** 2026-08-21 · **Model:** `pythia-160m` (reserialized `d5861d32…`), attested engine, CPU, **$0**.
**Results file (co-located):** `detector_validation_v12_operator10_framingmatched_results.json`, sha256 `50d09c797525c8a8…`

## Why
Operator-10 (the "10 Noetic rungs") is the strongest axis (v5 160m `0.550` vs surface `0.250`; v10 6.9b `0.800` vs `0.250`, surface-robust). But its stimuli are anchored to the **canonical colloquialism map** (`^2` "moth to a flame", `^4` "struck a chord", `^8` "that reminds me"…), which are themselves lexically distinctive. This tests whether the strength is real structure or **colloquialism-matching**.

## Design
TRAIN on the 6 canonical-colloquialism exemplars per operator (v5 set). TEST on **2 FRESH non-colloquial phrasings per operator** that carry the same Noetic operation without the signature colloquialism vocabulary (e.g. `^2` → "From the first glance she wanted the little blue house"). Compare on the same 20-item fresh set vs a char-ngram (n=2,3,4) surface baseline. 10-way, chance `0.10`.

## Result (exact)
- **activation `0.500` (10/20, L5)** vs **char-ngram surface `0.550` (11/20)** vs label-shuffle `0.200`.
- **activation − surface = `−0.050` → the word-counter WINS.**
- Per-operator activation on fresh phrasings: `^0` 2/2, `^2` 2/2, `^4` 2/2 (transfer); `^1` 0/2, `^6` 0/2, `^9` 0/2 (collapse); `^3` `^5` `^7` `^8` 1/2.

## Verdict — COLLOQUIALISM_CONFOUNDED (the flagship is BOUNDED)
Both activation (`0.500`) and surface (`0.550`) sit well above chance (`0.10`), so *some* signal transfers from colloquial training to fresh test — **but the activation detector does NOT beat surface across the register shift.** The transferable signal is surface-carried, not a register-independent structural representation.

**What this bounds:** Operator-10 is **surface-robust WITHIN the colloquial register** (v5/v10: same style, held-out items — activation beats surface there) but does **NOT** beat surface when tested on **fresh, giveaway-free phrasings**. The "10 Noetic rungs" result is real for colloquial-style stimuli and does **not** certify that the model carries a register-independent representation of the 10 Noetics. Three operators (`^0` Idea, `^2` Positive, `^4` Vibration) transfer to fresh wording; three (`^1` Mind, `^6` Male, `^9` Effect) collapse.

## Claim state
- **Real:** all numbers, real pythia-160m via attested engine. **Accepted:** none.
- **Verdict:** bounding NEGATIVE — the flagship does not survive a colloquialism-stripped control at this scale/n.
- **Open:** larger n; the 6.9b framing-matched Operator-10 control (may transfer better at scale — the 6.9b same-register result was much stronger); better-matched fresh stimuli.
- **Caveat:** activation best-of-12-layers selected on the 20-item test set; surface gets no selection; n=2 fresh per operator — research-grade.
