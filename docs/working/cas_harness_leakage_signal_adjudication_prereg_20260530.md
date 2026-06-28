# Stage LSA - Leakage-vs-Signal Adjudication

**Determines whether the v1 to v2 collapse means the MTC v2 fixture over-corrected, or whether the original v1 detection lift was substantially surface-carried.**

Little Henderson | 352-422-2892 | wakillorenzo@gmail.com

Classification: Confidential, NDA-Gated - Pre-registration - Version 0.3 DRAFT

Status: **Not frozen. Not WORM-anchored. Do not brief raters or run this stage until v1.0 is frozen and anchored.**

---

## 0. The Fork This Stage Resolves

Two fixture families produced an enormous swing:

| Fixture | 40E hidden readout | 40E text baseline | 40E lift | F28 hidden readout | F28 text baseline | F28 lift |
|---|---:|---:|---:|---:|---:|---:|
| v1 original | 95.625% | 49.24% | +46.4 pp | 86.86% | pending historical diagnostic | pending |
| v2 de-leaked | 5.50% | 4.50% | +1.00 pp | 5.036% | 2.878% | +2.158 pp |

Two hypotheses can explain the collapse:

- **H-OVERCORRECT:** v2 removed legitimate CAS semantic content along with the leak. The items no longer mean their CAS label strongly enough, so neither text nor hidden states recover it. CAS signal may be real, but this fixture destroyed it.
- **H-LEAKAGE-WAS-SIGNAL:** a large fraction of v1's lift was carried by surface form. Remove the surface tell and little CAS-specific structure remains. The v1 detection-lift claims must then be reinterpreted and caveated.

We do **not** assume H-OVERCORRECT because it is more comfortable. Stage LSA exists so this fork can fail honestly.

## 1. The Adjudication Principle

The fork cannot be resolved by another hidden-state test alone, because hidden-state recoverability is exactly what collapsed.

The test must ask an independent oracle:

> Can CAS-competent, model-blind judges recover the CAS label from the item's meaning alone after notation and surface tells are stripped?

If judges can recover the labels, the items still carry CAS meaning and v2 likely over-corrected or broke the model-facing instrument.

If judges cannot recover the labels, then the labels were probably riding on surface form rather than meaning. In that branch, the v1 lift numbers are not externally usable without a leakage caveat and re-derivation.

## 2. Load-Bearing Two-Arm Design

This v0.3 fixes the v0.2 arm-order drift. The v2 fixture defect was identified after the v2 failure: v2 labels were attached as metadata while prompt content was rotated independently of the CAS label. That diagnosis explains the v2 null, but it does **not** re-license the original v1 lift. A broken de-leak and a leaky original can both be true.

So Stage LSA must put the original v1 question first.

### Arm A - v1 Items With The Strip Operation Applied

Source: original v1 items that produced the strong detection-lift claims.

Operation: remove answer-key wording under the frozen strip contract while preserving the concrete TKS meaning whenever that is possible.

Purpose: directly tests whether the original v1 lift was meaning-borne or surface-vocabulary-borne.

Interpretation:

- Arm A succeeds: original v1 items still carry recoverable TKS/CAS meaning after stripping surface tells. The v1 result remains scientifically live, but still externally restricted until reproduced with a non-leaking valid instrument.
- Arm A fails: original v1 labels were not recoverable from meaning after strip. The v1 detection-lift claims are treated as substantially surface-carried for the failed cells.
- Arm A is the primary adjudication arm. No v2 diagnosis can substitute for it.

### Arm B - v2 Notation-Stripped Items

Source: exact v2 fixture items already used in the 20B de-leaked run.

Purpose: tests whether v2 itself carries recoverable CAS meaning and whether the v2 generator over-corrected.

Interpretation:

- Arm A succeeds while Arm B fails: v2 generator over-corrected. Rebuild v2.5 from TKS meaning, not from metadata-only labels.
- Arm A fails while Arm B fails: H-LEAKAGE-WAS-SIGNAL is strongly supported for the failed cells.
- Arm B succeeds while Arm A fails: unexpected; investigate fixture-family mismatch before any claim.
- Both succeed: both fixture families carry recoverable meaning; proceed to v2.5 instrument design with the judge gate as acceptance criterion.

Arm B is supporting evidence. Arm A controls claim status for the original 95.625% / +46.4 pp result.

## 3. Judges

Judges are blind to model results, fixture version, expected label, and each other's answers.

### 3.1 Human CAS-Competent Raters

Minimum: `N >= 3`.

Raters must demonstrably know the CAS ontology. They must pass a qualification set before receiving LSA items.

Why CAS-competent, not CAS-blind: a rater who does not know the ontology cannot judge whether a notation-stripped item carries a CAS label. This stage tests whether CAS meaning survives without leakage, not whether an uninformed reader can rediscover the ontology.

The framework author may only serve as a separately labeled non-confirmatory fourth rater. Author-rater results must be published in the final write-up alongside the primary results, never appendix-only, and are never pooled into confirmatory metrics.

### 3.2 Independent-Model Rater

Model: `gemini-3.1-pro-preview`.

Reason: project default Gemini model already recorded in project docs; it is not one of the audited open-weight target models and is not part of the activation harness.

If `gemini-3.1-pro-preview` is deprecated or renamed before freeze, this prereg must be revised, re-hashed, and WORM-anchored before any run.

The model rater receives the 40-Element and 28-Foundation definition sheets in-context and assigns labels to notation-stripped items. The model-rater arm is scalable and reproducible; the human-rater arm is the ground-truth anchor.

## 4. Items And Strip Contract

### 4.1 Item Sets

Run both axes:

- 40E: original v1 items and v2 items.
- F28: original v1 items and v2 items.

If the original v1 item text cannot be reconstructed exactly, this stage is blocked until the reconstruction artifact is versioned and signed off.

### 4.2 Notation-Strip Contract

The strip operation must be frozen before any judge sees data.

Core anti-drift rule:

> Strip the answer-key wording. Do not strip the TKS meaning.

This rule is empirical, not aspirational. Some TKS words do double duty: they are both source-definition words and possible answer-key tells. If an Element cannot be made concrete without those terms, that Element is marked vocabulary-dependent rather than quietly forced into a "clean" prompt.

It removes:

- CAS/TKS labels, codes, class badges, symbolic notation, and source-vocabulary answer keys.
- Repeated cue-card lists or class definition blocks.
- Stable class handles introduced by fixture scaffolding.

It preserves:

- Ordinary scenario prose.
- Concrete actors, settings, events, choices, evidence, actions, and consequences.
- Meaning-bearing content that a rater could use without seeing the answer label.
- The original TKS distinction in plain concrete form, when such a form exists.

The exact strip script or manual redaction protocol must be logged with:

- input artifact SHA256,
- output artifact SHA256,
- strip rules version,
- reviewer identity or script commit,
- timestamp.

If the strip operation is under-specified, that is finding #0 and Stage LSA cannot run.

### 4.3 Leakage-Positive Controls

Include held-out v1-style notation-intact control items, unlabeled to judges.

Purpose: confirm that judges can score near-ceiling when the tell is present.

Control threshold:

- Human majority-vote accuracy must be `>= 85%`.
- Independent-model rater accuracy must be `>= 85%`.

If either fails, abort and fix the judge protocol before interpreting Arm A or Arm B.

## 5. Confirmatory Thresholds

Let `R` be judge recovery accuracy on notation-stripped items.

Chance:

- 40E chance: `2.50%`
- F28 chance: `3.57%`

Anchors:

- v1 40E text baseline: `49.24%`
- v1 40E hidden readout: `95.625%`
- v2 40E hidden readout: `5.50%`
- v2 F28 hidden readout: `5.036%`

Pre-registered thresholds:

| Axis | R_low | R_high | Rationale |
|---|---:|---:|---|
| 40E | `15%` | `60%` | `15%` is far above chance but much closer to chance than v1 text baseline; `60%` is meaningfully above the v1 text baseline. |
| F28 | `12%` | `50%` | `12%` is far above 28-way chance but still low; `50%` is strong recovery for 28-way Foundation labels. |

Decision:

- `R >= R_high`: the tested items are meaning-bearing for that arm and axis.
- `R <= R_low`: the tested items are not meaning-bearing after strip for that arm and axis.
- `R_low < R < R_high`: GREY; partial meaning-bearing, no binary claim.

Do not move thresholds after seeing judge results.

### 5.1 Per-Element / Per-Foundation Status

Overall axis accuracy is not enough. Stage LSA must also report recovery per class:

- 40E: one status for each Element `A1` through `D10`.
- F28: one status for each Foundation/Register cell.

Per-class status:

- `meaning_bearing`: class-level recovery reaches `R_high`.
- `vocabulary_dependent`: class-level recovery is at or below `R_low`.
- `grey_partial`: class-level recovery falls between `R_low` and `R_high`.

Only `meaning_bearing` classes can carry future detection-lift claims. `vocabulary_dependent` classes cannot carry detection-lift claims until they are rebuilt or merged into a larger meaning-bearing class.

If a class has fewer than 10 rated items, class-level status is reported as descriptive only and cannot license or retire that class by itself.

## 6. Aggregation Rules

### 6.1 Human Primary Metric

Primary human score uses majority vote across at least three raters.

For each item:

- If at least two of three raters choose the same label, that label is the majority answer.
- If no majority exists, mark the item `no_majority` and count it as incorrect for primary accuracy.

Report separately:

- majority-vote accuracy,
- individual rater accuracies,
- unanimous-agreement subset accuracy,
- no-majority rate.

### 6.2 Human Inter-Rater Reliability

Report pairwise Cohen's kappa and raw agreement.

Interpretation:

- `kappa >= 0.50` and raw agreement `>= 70%`: human anchor is usable.
- Below either threshold: report results, but classify judge reliability as weak and do not use the stage to license claims without a rater-calibration rerun.

### 6.3 Human-Model Agreement

The independent-model arm is trusted only on items where it agrees with the human majority anchor.

Report:

- raw agreement with human majority,
- Cohen's kappa against human majority,
- model accuracy on all items,
- model accuracy on human-agreement subset.

Trust threshold:

- raw agreement with human majority `>= 70%`,
- Cohen's kappa `>= 0.50`.

If the model-rater misses either threshold, use it as supporting evidence only. The human arm remains primary.

## 7. Hypotheses And Consequence Map

### H-OVERCORRECT Supported

Condition:

- Arm A reaches `R_high` and Arm B falls at or below `R_low`.

Meaning:

- v1 items still carry CAS meaning after strip.
- v2 generator over-corrected or decoupled labels from meaning.

Action:

- MTC remains OPEN.
- Build v2.5 with the judge-gate as an acceptance criterion before GPU capture.
- v1 lift numbers still remain externally restricted until a non-leaking valid instrument reproduces them.

### Both Arms Meaning-Bearing

Condition:

- Arm A reaches `R_high` and Arm B reaches `R_high`.

Meaning:

- Both fixture families carry recoverable CAS meaning to competent judges.
- The v2 hidden-state failure is then not explained by absent human-readable meaning alone; investigate model-facing prompt form, readout configuration, layer choice, or capture path before any new GPU run.

Action:

- MTC remains OPEN.
- v1 lift numbers still remain externally restricted until reproduced with a non-leaking valid instrument.
- v2.5 design must preserve the judge-passed meaning but improve model-facing recoverability.

### H-LEAKAGE-WAS-SIGNAL Supported

Condition:

- Arm A falls at or below `R_low`.

Meaning:

- v1 labels are not recoverable from meaning after strip.
- Original v1 detection lift was substantially surface-carried.

Action:

- 40E/F28 detection-lift claims move to **NOT LICENSED** pending re-derivation on a non-leaking fixture.
- Spec-sheet `+46.4 pp` / `+39.7 pp` style headline lifts receive a leakage caveat.
- This is disclosed as a primary finding, not buried.

### GREY

Condition:

- Arm A falls between `R_low` and `R_high`.

Meaning:

- Items carry partial CAS meaning; both overcorrection and leakage likely contributed.

Action:

- Report the recoverable fraction.
- Do not license clean detection-lift claims.
- Build a smaller human-reviewed fixture with clearer meaning before any new GPU capture.

## 8. What Stage LSA Does Not Do

Stage LSA does not:

- rebuild a valid MTC instrument,
- prove CAS specificity,
- adjudicate the eta-to-epsilon bridge tier,
- adjudicate causal-ablation tiers,
- adjudicate WORM Evidence Packet integrity,
- prove metaphysical universality.

Even a clean H-OVERCORRECT result only says: "the v2 fixture broke the signal; build a better instrument." Specificity still requires a valid matched-taxonomy run afterward.

## 9. Sequencing And Cost Discipline

Run Stage LSA before any new 20B/100B/300B capture.

Order:

1. Recover exact v1 item text and v2 item text.
2. Freeze strip contract.
3. Build Arm A and Arm B judge packets, with Arm A reviewed first in analysis.
4. Add leakage-positive controls.
5. Freeze this prereg as v1.0.
6. WORM-anchor prereg plus input artifact hashes.
7. Brief raters.
8. Collect human ratings.
9. Collect independent-model ratings.
10. Compute adjudication report.
11. Decide whether v2.5 GPU capture is warranted.

No new GPU spend is justified until LSA resolves the fork.

## 10. WORM Freeze Requirement

Before any rater is briefed:

1. Freeze this document as v1.0.
2. Compute SHA256 of the frozen document.
3. Compute SHA256 of all input item files and strip-output files.
4. Anchor the prereg and artifact manifest through the Evidence Packet S3 Object Lock/WORM flow.
5. Record the WORM trace ID in this document and in the LSA run directory.

Required fields after freeze:

- `lsa_prereg_sha256`
- `lsa_prereg_worm_trace_id`
- `lsa_input_manifest_sha256`
- `lsa_strip_manifest_sha256`
- `s3_object_lock_verified: true`

If WORM anchor fails, Stage LSA can be exploratory only and cannot move claim status.

## 11. Honest External Framing

Until LSA resolves, use this wording:

> A de-leaked re-build of the 40E/F28 detection fixtures did not reproduce the original lift; we are adjudicating whether the de-leaking removed legitimate signal or whether the original lift was surface-carried, before making further detection-lift claims at this granularity.

Do not say:

- "CAS failed."
- "v1 was fake."
- "v2 proves leakage."
- "MTC is closed."
- "CAS specificity is falsified."

The correct claim is narrower:

> The v1/v2 collapse opened a leakage-vs-signal fork. Stage LSA is the pre-registered judge-based adjudication before further detection-lift claims or expensive recapture.

## 12. Tier-Closure Entry

| Evidence Tier | Status |
|---|---|
| Leakage-vs-signal adjudication (v1 to v2 collapse) | OPEN - Stage LSA v0.3 draft; makes v1-stripped recovery Arm A and primary; adds per-Element/per-Foundation meaning-survival status; not frozen; not WORM-anchored |

## 13. Immediate Next Work

Artifact package started at:

`docs/working/lsa_artifacts_20260530/`

Current status:

1. Exact v1 40E and F28 source items: located and extracted into the artifact package.
2. Exact v2 40E and F28 source items: located in `live-trace-worker/scenarios/`.
3. Draft strip contract: created as `lsa_strip_contract_v0_1.md`; not frozen.
4. 40E/F28 sample packet for rater-protocol smoke: generated as `lsa_sample_packet_v0_1.json`; private and not for raters.
5. Draft redaction map: created as `lsa_sample_redactions_v0_1.json`; not frozen.
6. Rater-facing smoke packet: generated as `lsa_sample_packet_rater_view_v0_1.json`; hidden labels/source IDs/private originals removed. This is for protocol review only, not confirmatory rating.
7. Smoke redaction review: created as `lsa_smoke_redaction_review_v0_1.md`. Result: privacy leak check passes, deterministic shuffle passes, but mixed Arm A / Arm B packet fails final blinding because v1 and v2 item styles are visually different.
8. Arm A-only rater smoke packet: generated as `lsa_arm_a_sample_packet_rater_view_v0_1.json`; hidden labels/source IDs/private originals and rater-facing `Arm A` / `original v1` metadata removed.
9. Definition sheets: created as `lsa_definition_sheet_40e_v0_1.md` and `lsa_definition_sheet_f28_v0_1.md`.
10. Rating template and scorer: created as `lsa_arm_a_smoke_rating_template_v0_1.csv` and `score_lsa_ratings.py`.
11. Scorer sanity check: synthetic perfect ratings produce 1.0 accuracy and `meaning_bearing` status at the axis level, while per-class one-item smoke rows remain `descriptive_only_under_10_items`.
12. Arm A runbook: created as `LSA_ARM_A_RUNBOOK_v0_1.md`; identifies safe rater files, private scoring files, synthetic-only files, scoring command, and interpretation rules.
13. Freeze checklist: created as `LSA_FREEZE_CHECKLIST_v0_1.md`; makes WORM anchoring, packet QA, rater blinding, and hash capture explicit before any rating.
14. Full Arm A redaction queue: generated as `lsa_arm_a_full_redaction_queue_private_v0_1.jsonl` with 12,688 private work items: 8,320 40E and 4,368 F28. Every row starts as `needs_human_rewrite`; this is the human strip queue, not a rater packet.
15. Minimum-class redaction batch: generated as `lsa_arm_a_min_class_redaction_batch_private_v0_1.jsonl` with 680 private work items: 10 per 40E label and 10 per F28 label. This is the first practical human-redaction batch, not a rater packet.
16. 20-item calibration smoke: generated as `lsa_arm_a_20_item_redaction_sheet_private_v0_1.csv` with 10 40E and 10 F28 rows. This is a usability/calibration pass only; it cannot license or retire detection-lift claims.
17. 20-item materializer: created as `materialize_lsa_arm_a_20_item_rater_packet.py`. It correctly blocks until every row has `judge_text_stripped` filled and `redaction_status=ready_for_rating`.
18. Remaining: review Arm A redactions, freeze Stage LSA v1.0, freeze strip contract, build full stripped Arm A packet first, then WORM-anchor before any rating begins. Arm B should be run separately as diagnostic, not mixed into the same confirmatory rater packet.
