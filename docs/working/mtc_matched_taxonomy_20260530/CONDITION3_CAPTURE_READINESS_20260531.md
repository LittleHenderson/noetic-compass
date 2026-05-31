# Condition-3 capture readiness — assessment (2026-05-31)

## Short version

Condition-3 was built for **Path 2**: take the SAME real CAS element meaning that
Condition-2 carries (40 elements = 10 noetic dynamics × 4 domains-as-register) and
instantiate it inside concrete everyday scenarios that ALSO carry ordinary topic +
event-frame content. The everyday content is assigned **orthogonally** to the CAS
element, so the pre-registration's coherent non-CAS opponents materialize from
non-CAS fields only — the exact thing Condition-2 could not supply.

All **three** local ($0 CPU) gates are GREEN:

1. **Surface Gate — PASS.** CAS-label text leakage = **6.25%** (2.5× the 2.5%
   chance floor), *below* Condition-2's 6.9%. The surface copy-shortcut is killed.
2. **Fixture-Eligibility Gate — ELIGIBLE.** Control B (`NC40_TOPIC_FRAME_V1`)
   reconstructs from `control_semantic.topic_40` + `.frame_40` only, exactly
   balanced per split, orthogonal to CAS within a permutation-null band, and the
   ordinary content is 100% text-recoverable.
3. **Meaning-Preservation Gate — PASS.** A reader using only the 40-Element
   definition sheet recovers the element at **40/40 (100%)**, every domain and
   every noetic — far above both the 2.5% chance floor and the 6.25% text baseline.

That combination — meaning fully recoverable by a reader, near-chance from a word
counter, AND a real coherent same-size opponent present — is what makes a fixture
eligible for the FULL comparative MTC.1 gate (the stronger claim "CAS is cleaner
than serious same-size non-CAS opponents"), which Condition-2 was structurally
BLOCKED from earning.

## What Condition-3 is

One prompt simultaneously carries:

- **Real CAS meaning.** The focused role names a **noetic dynamic** (the verb
  phrase after "the one who …", a faithful paraphrase of the authoritative
  definition — e.g. ^3 Negative stays visceral "shrinks from it on a gut level",
  ^8 Above/Cause stays associative "makes an unrelated idea surface", ^6 Male is
  compositional "pulls its components out and exposes them") and the **domain as
  register** (A=Spiritual/transcendent, B=Mental/analytical, C=Emotional/affective,
  D=Physical/embodied), carried by a single adjective in a shared manner template.
  A counterfactual partner role + a `Focus: A/B` marker disambiguate the element.
- **Ordinary topic/event content.** An everyday scene names a **topic_40** sector
  (8: healthcare … public_safety) and a **frame_40** event frame (5:
  classification … risk_mitigation), drawn from the Control B manifest.

Example (test, element B4 = Mental Vibration):

> "In a hospital ward reviewing a patient's care plan, as they classify which
> category it falls in: A is the one who **registers the tremor it sets off, in a
> logical way**; B is the one who consists of its accumulated history, in a logical
> way. **Focus: A.**"

The scene (hospital / classification) is orthogonal scaffold; the element is read
from the focused role's dynamic ("registers the tremor" → ^4 Vibration) and register
("logical" → B Mental) → **B4**.

## Honesty properties (why the three gates do not contradict)

- **Train/test split is by counterfactual pair.** All CAS carrier phrasings (noetic
  dynamics and register adjectives) are authored **content-word-disjoint** across
  train↔test, so a bag-of-words classifier trained on train cannot transfer the CAS
  surface to test → Surface Gate near chance. A human reads through synonyms → the
  meaning still lands → Meaning-Preservation high. The gap between the two IS the
  point.
- **Domain-as-register uses SHARED manner templates, not per-domain clause shapes.**
  This was the decisive fix. With per-domain clause shapes ("of its …" for A, "by
  …ing it through" for B, …), the **syntactic skeleton** is a stable cross-split
  fingerprint that a 1-2gram classifier reads even when content words differ —
  domain leaked at ~45% and the CAS label sat at ~9-10% (NEAR-PASS/FAIL). Moving the
  register into a shared template (`in a {adj} way` / `with a {adj} bearing` / `on
  {adj} ground`) used identically by all four domains, with the register carried
  ONLY by a disjoint adjective, collapsed domain recovery to 26.1% (≈ 25% chance)
  and the CAS label to 6.25% (PASS). The residual is the noetic axis (37.5%); the
  noetic dynamics are deliberately left rich and natural because they carry the core
  meaning a reader must recover, and the joint label already passes.
- **Orthogonality is calibrated, not asserted.** Raw NMI is biased upward at 40×40
  sparsity over a few hundred rows per split, so the gate compares the real
  NMI(CAS_element, NC40_cell) against a permutation null and passes only if it sits
  inside the null's 97.5th percentile band (real 0.1651 ≤ null p97.5 0.1738). The
  scaffold is assigned by a **CAS-blind seeded shuffle** of a balanced 40-cell
  multiset per split — the shuffle key knows nothing about domain/noetic.

## Fixture facts

- File: `mtc_condition3_topical_scenarios_20260531.jsonl` (1440 rows, 720 train /
  720 test, 36 per element, 18 per NC40 cell per split, all 40 NC40 cells present).
- Manifest: `mtc_condition3_topical_scenarios_20260531_manifest.json`
  (`schema_version=mtc_condition3_fixture_manifest.v1`); records the orthogonality +
  balance block and the SHA-256 of the JSONL.
- Builder: `build_mtc_condition3_topical_scenarios.py` (refuses to write if balance
  is off or real NMI exceeds the null band).
- Domain⊥topic NMI = 0.0047, noetic⊥frame NMI = 0.0118 (the carried axes do not
  bleed into the scaffold axes).

## Gate artifacts

| Gate | Script | Result file | Verdict |
|---|---|---|---|
| Surface | `surface_gate_condition3.py` | `surface_gate_condition3_result.json` | PASS (6.25%) |
| Fixture-Eligibility | `fixture_eligibility_gate_condition3.py` | `fixture_eligibility_gate_condition3_result.json` | ELIGIBLE |
| Meaning-Preservation | `build_condition3_meaning_preservation_packet.py` → rate → `score_condition3_meaning_preservation.py` | rater sheet + answer key + protocol | PASS (40/40) |

## Caveat on the Meaning-Preservation rating

The reader-recovery rating was produced by this agent reading each prompt against
the definition sheet — i.e. a **competent-reader recoverability demonstration**,
not an independent human study (the same posture as the Condition-2 gate). The
adjective→domain and dynamic→noetic mappings are designed to be recoverable, so a
100% self-rating confirms the meaning is *in principle* recoverable from the sheet;
it is not evidence about an unfamiliar human rater. If a stronger claim is wanted
before GPU spend, run the packet (`condition3_mp_rater_sheet_20260531.csv` +
`condition3_mp_protocol_20260531.md`) past one or more independent human raters and
re-score; the answer key and scorer are already in place.

## Status / next step

- Condition-3: **all three local gates GREEN.** Eligible for the FULL comparative
  MTC.1 capture (hidden-vs-text + Control A/B/C/D opponents), which is the stronger
  claim the project is chasing.
- **No GPU dollars spent yet.** The remaining work is the one GPU capture; per the
  prereg, that capture can now PASS/FAIL the comparative gate rather than landing
  `BLOCKED_FIXTURE_NOT_ELIGIBLE` the way a Condition-2 capture would.
- Recommended before launch: (a) optional independent human MP rating per the caveat
  above; (b) ~~materialize Control C~~ **DONE (2026-05-31).**

## Control C (NC28) — materialized (2026-05-31)

Control C (`NC28_TOPIC_FUNCTION_NESTED_V1` = 7 `topic_7` × 4 `function_4` = 28 cells)
is the SECONDARY same-size opponent. It cannot be balanced on the full 1440-row
fixture because the fold is many-to-one (`customer_support`+`public_safety` →
`human_services`; `procedure`+`tradeoff_decision` → `choose_action`), which yields
18/36/72-row cells, AND 720 is not divisible by 28. So it is materialized as a
**balanced view**: every cell downsampled to the minimum (18/cell × 28 = **504 rows
per split, 1008 total**) via a CAS-blind seeded shuffle (selector never reads any CAS
field). All 40 CAS elements remain covered in both splits (6–17 train / 9–15 test).

The local Control-C gate (`materialize_control_c_condition3.py` →
`control_c_nc28_balanced_view_20260531.json`) is **ELIGIBLE_SECONDARY** — all four
checks pass on the view:

| Check | Result |
|---|---|
| Reconstructs from `topic_7`+`function_4` only | 28/28 cells, exact set match |
| Balanced per split | 18/cell, 7 topics + 4 functions uniform |
| Orthogonal to CAS (null band) | NMI 0.1675 ≤ null p97.5 0.1833 |
| Ordinary content present in text | topic_7 100%, function_4 100% recoverable |

The view JSON records the exact `sample_id`s so the GPU Control-C arm runs on
precisely this balanced 1008-row set. NC28 remains the *secondary* opponent (the
`public_safety`→`human_services` fold is genuinely approximate); Control B (NC40) is
the primary opponent and balances on the full fixture.
