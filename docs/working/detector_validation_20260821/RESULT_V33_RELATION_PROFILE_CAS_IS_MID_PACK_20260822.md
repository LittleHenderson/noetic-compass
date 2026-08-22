# V33 — RELATION LEGIBILITY PROFILE: 🟥 CAS `^8`/`^9` is **MID-PACK**. Three ordinary relations beat it. This is evidence **AGAINST** CAS-specificity.

**Date:** 2026-08-22 · `pythia-160m` (reserialized), **attested engine**, CPU, **$0**.
**Results:** `detector_v33_relation_profile_results.json`, sha256 `ec969062696610af…`
**Pre-registered before the run** (in the script's own docstring): *"if `^8`/`^9` sits at the top, that is evidence CAS names something the model encodes unusually strongly. If it sits mid-pack, that is evidence AGAINST specificity — CAS would be naming an ordinary relation, which is exactly the skeptic's objection. EITHER OUTCOME IS INFORMATIVE."*

**It sat mid-pack.**

---

## 1. The profile

Six relations, **identical pinned-pair construction**, 60 pairs each (3 frames × 20 items), 360 pairs total. **Gate passed on every relation before the model loaded** — word multisets identical, char-n-gram bag residual `0.000000`, token-length mismatches `0`. **Both surface baselines FORCED to `0.500` by arithmetic throughout.** Leave-one-pair-out; verdicts on the selection-free mean over all 12 layers; bootstrap 95% CI on per-pair scores.

| rank | relation | what it asks | mean | 95% CI | best layer |
|---|---|---|---|---|---|
| 1 | `part_whole` | contains vs entered | **`0.9347`** | `[0.9222, 0.9472]` | `1.000` |
| 2 | `causal_vs_correlate` | caused vs accompanied | **`0.9201`** | `[0.9014, 0.9368]` | `1.000` |
| 3 | `agent_patient` | who did it to whom | **`0.9146`** | `[0.8868, 0.9382]` | `1.000` |
| **4** | **`cas_8_9_trigger_arrival`** | **trigger vs arrival ← the CAS relation** | **`0.8604`** | `[0.8444, 0.8764]` | `1.000` |
| 5 | `temporal_before_after` | preceded vs followed | `0.8500` | `[0.8285, 0.8729]` | `1.000` |
| 6 | `speaker_binding` | who said what | `0.5583` | `[0.5417, 0.5757]` | `0.692` |

**CAS position: rank 4 of 6.** Beaten with **non-overlapping** CIs by `agent_patient`, `causal_vs_correlate`, and `part_whole`. Overlaps `temporal_before_after`. Beats only `speaker_binding`. **Verdict: `CAS_MID_PACK`.**

## 2. 🟥 What this means — stated plainly

**The CAS `^8`/`^9` relation is not privileged in this model.** Three ordinary linguistic relations — part/whole containment, causation-vs-correlation, and agent/patient role — are recovered from the hidden state **more strongly** than the CAS trigger/arrival relation, under an identical construction where surface cheating is arithmetically impossible.

**The sharpest detail: `causal_vs_correlate` is ALSO a causal relation, and it beats the CAS framing (`0.9201` vs `0.8604`, non-overlapping).** So this is not "the model is weak at causation." It is that **the specific CAS trigger/arrival wording is a weaker carrier of causal structure than an ordinary caused/accompanied contrast.** CAS is not carving this joint better than plain English does.

**This directly supports the skeptic's objection** that has been recorded as open since the start: *that CAS names ordinary semantic relations rather than identifying special ones.* The objection is no longer merely unrefuted — **it now has affirmative evidence.**

## 3. ✅ What this does NOT overturn

- **The instrument is further validated, not undermined.** It produced a **graded, sensible profile with a large dynamic range** (`0.5583` → `0.9347`) while every floor stayed pinned at `0.500`. A broken probe returns noise or saturates; this one ranks relations in a way that is independently plausible (containment and agent-role are core syntactic/semantic distinctions; speaker attribution is genuinely hard). **The pinned-pair method works.**
- **The dissociation stands.** `speaker_binding` remains dramatically last (`0.5583`, CI excludes every other relation's interval by a wide margin). The finding that models bind *cause*, *time*, *role*, and *containment* far better than they bind *who is speaking* is **reinforced** by this profile, not weakened — and that is the commercially load-bearing result (prompt injection).
- **Claim B is not dead.** CAS may still be usable as a **measurement and correction vocabulary** — a rubric you apply. What v33 kills is the stronger reading: that CAS names relations the model itself treats as special.

## 4. Claim-state changes required

| status | claim |
|---|---|
| 🟥 **EVIDENCE AGAINST** | **CAS-specificity.** Previously `GREY` (open/undecided). It should now read `GREY — with affirmative evidence against`, citing this profile. Three ordinary relations outrank the CAS relation with non-overlapping CIs. |
| 🟥 **WITHDRAWN** | Any reading of v32's "CAS (`0.8033`) > temporal (`0.7367`)" as evidence for CAS being special. v33 shows that gap was **verb-choice dependent**: with `preceded`/`followed` instead of `came before`/`came after`, temporal rises to `0.8500` and the CIs overlap CAS. **The v32 separation does not generalize.** |
| ✅ **UNCHANGED** | The pinned-pair instrument; the graded dissociation; the speaker-binding weakness. |

## 5. Honest scope
- One model (`pythia-160m`), 60 pairs and 3 frames per relation, one seed. The paid models were not tested on this profile.
- Relation "difficulty" is confounded with **verb frequency and concreteness** — `contained`/`entered` are common concrete verbs; `triggered`/`arrived` are less so. **This profile measures how legibly each relation is encoded AS WORDED, not the Platonic relation.** A fairer test would frequency-match the verb pairs. **That caveat cuts both ways and does not rescue CAS:** the CAS wording is the wording CAS actually uses.
- The result says nothing about whether CAS is a *useful* analytic vocabulary — only that the model does not encode its named relation more strongly than ordinary alternatives.
