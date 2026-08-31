# CJT-DEV-P1 — Static Dual-Stream Neural Coupling Development Pilot

**Status:** blocked at the first hard gate (S7-P construction). No GPU launched.
No model loaded. No AWS call. No money spent. Protected split never touched.

**Branch:** `research/cjt-dev-gpu-pilot-v1` (from anchor `3182e0623`).
**Classification:** development-only, **non-claim-bearing** (owner directive
CJT-DEV-P1). This directory is deliberately SEPARATE from the frozen Gate 1B
package `../cjt_gate1a_static_neural_v1/` so the claim-bearing tree is untouched.

## What the pilot is

Train four small heads over frozen `Qwen2.5-0.5B-Instruct` activations and ask,
in development terms only, whether the CAS-coupled head (S3) learns the approved
construction-gold task better than a plain head (S0), a matched-capacity head
(S6), and an **independent** semantic-taxonomy head (S7-P).

The four arms:
- **S0** plain head (no attention, no profiles)
- **S3** CAS-coupled head (attention over Ideas + the 4-class CAS profile per Idea)
- **S6** same module as S3, but every Idea gets the uniform profile (capacity control)
- **S7-P** same module as S3, but Ideas get a **WordNet-derived** 4-class profile
  that must be an INDEPENDENT carving of the 16 head verbs, not the CAS carving

## The blocker: S7-P cannot be built without manufacturing it

`build_s7_pilot.py` constructs S7-P from a frozen WordNet 3.0 snapshot
(`wordnet.zip` SHA-256 `cbda5ea6eef7f36a97a43d4a75f85e07fccbb4f23657d27b4ccbc93e2646ab59`,
10,775,600 bytes, Princeton WordNet 3.0 License). The result is
`S7_PILOT_BUILD_RECEIPT.json`.

The gate requires a 4×4-balanced, WordNet-only, CAS-blind partition of the 16
verbs with **Cramér's V(S7, CAS) ≤ 0.35**, not equal to and not a permutation of
the CAS partition.

**It fails.** The 16 registered verbs' CAS classes are semantic operation-types
(attract / avert / decompose / trigger), and WordNet organizes verbs
semantically, so every principled CAS-blind WordNet *semantic* partition
correlates with CAS above the threshold:

| construction (pre-declared / diagnostic) | Cramér's V | semantic? | passes ≤0.35? |
|---|---|---|---|
| **verb primary-sense lexname** (repo's frozen `construction_law`, PRIMARY) | **0.3536** | yes | **no** (fails by 0.0036) |
| sense-1 hypernym lexname (FALLBACK) | 0.6124 | yes | no |
| primary lexname (round-robin) | 0.408 | yes | no |
| polysemy count | 0.408 | no | no |
| lemma count (round-robin) | 0.354 | no | no |
| **synset offset (round-robin)** | **0.289** | **no** | yes — **EXCLUDED** |

The only construction that passes is a **shuffle by arbitrary WordNet synset
catalog numbers** — not a semantic taxonomy. Selecting it *because* it passes the
CAS-orthogonality test is exactly the "manufacture a convenient control" the
directive forbids. So the honest verdict is `S7_PILOT_CONSTRUCTION_FAILED`, and
the pilot stops before any GPU use.

This confirms the taxonomy manifest's own `circularity_disclosure`: the dataset's
answer function is defined over the CAS classes, so no genuinely task-relevant
non-CAS control can exist on this 16-verb vocabulary.

## This is an owner governance decision, not a workaround

Resolving it (redefining S7-P as an explicitly-declared structured-random
control, changing the threshold, changing the vocabulary/resource, or dropping
the S3-vs-S7 comparison) is the owner's call — see the session report. Claude is
not the research governor and will not pick one to get past the gate.

## Files
- `build_s7_pilot.py` — deterministic, WordNet-only S7-P construction + gates.
- `S7_PILOT_BUILD_RECEIPT.json` — the frozen negative result (verdict, full
  landscape, per-verb WordNet features, pinned snapshot). A negative result is a
  load-bearing artifact and is kept, not deleted.
