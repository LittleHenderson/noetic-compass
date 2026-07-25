# GATE 2 ITEM 4 — LOCKED PRE-REGISTRATION

**Design id:** `TKS-DEFCTX-40E-PRIMARY-v1`
**Written:** 2026-07-25
**Repo state at writing:** branch `codex/cascompass-legal-live-source`, HEAD `396eb3b376c683d3d5f8ec47e93e0c4f64233f5e`
**Unblocked by:** `docs/working/gate2_closure/OWNER_SEMANTIC_AUTHORITY_REGISTRY_SIGNED_20260724.json`, receipt_hash `d0c582c948989c9ef90014547565edf83307d813b3b7617542416e56f0f442f7`, `signature_kind = INTERACTIVE_SESSION_OWNER_APPROVAL_TRANSCRIBED_BY_ASSISTANT` (a recorded authorization, explicitly **not** a cryptographic or legal signature).

---

## STATUS — READ THIS FIRST

**This design is LOCKED. It is NOT YET RUNNABLE.**

Everything below is frozen as written. No threshold, no unit of analysis, no criterion, and no control in this document may be changed after any activation is captured. But five of the objects the design requires **do not exist on disk yet**, and two of them are **owner-action blockers I cannot clear myself**. Capturing activations today would produce a number that this pre-registration explicitly refuses to license.

The honest statement is: *the experiment is designed and frozen; here is the build list that must be completed, hashed, and appended as a signed amendment before the first forward pass.*

### BUILD LIST — mandatory before capture (each becomes a hashed amendment to this file)

| # | Object | Status | Who |
|---|---|---|---|
| B1 | Repaired 40-Element holdout bank (dedup 8,320 → 5,920, bundle-disjoint re-partition), plus its repair script and new sha256 | `unavailable_until_built` | assistant |
| B2 | Arm E payload — 40 coherent non-TKS definitions, per-code length-matched, register-matched, blind-coherence-audited | `unavailable_until_authored` | assistant + independent rater |
| B3 | Arm F payloads F1–F6 (six null families, per-seed draws) | `unavailable_until_authored` | assistant |
| B4 | Arm D payload — 40 compact-CAS definitions compiled mechanically from `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` | `unavailable_until_compiled` | assistant |
| B5 | **Owner ratification of the TKS↔CAS crosswalk** used by Arm D (Domain A/B/C/D ↔ CAS Domain, TKS Noetic 1..10 ↔ CAS `^1..^9,^0`) — required for `required_run_bindings[6] tks_to_cas_crosswalk_sha256`, currently empty | **OWNER-ACTION BLOCKER** | owner |
| B6 | Multiclass positive control (`instrument_positive_control` raises `ValueError("Positive control needs exactly two classes")` — verified at `research/reconciled/experiment_admissibility.py:190`) | `unavailable_until_written` | assistant |
| B7 | Frozen control manifest incl. the pinned ENC-COS sentence encoder (`model_id` + revision + sha256), hashed to `required_run_bindings[19]` | `unavailable_until_pinned` | assistant |
| B8 | Model identity block: `resolved_model_revision`, `tokenizer_sha256`, `model_config_sha256`, `weights_manifest_sha256` (`required_run_bindings[9..12]`) | `unavailable_until_capture_host_resolved` | assistant |
| B9 | **Owner acknowledgement that the 28-Foundation axis is dropped as claim-bearing** (Section 4.4) | **OWNER-ACTION BLOCKER** | owner |

**B5 must be committed and hashed BEFORE capture, not after.** If the crosswalk is ratified only after the numbers exist, the owner — who holds the prior under test — controls whether an Arm A loss to Arm D "counts". That is unfalsifiability by procedure and this document forbids it.

### Adversarial findings this design does NOT resolve
Listed in full in Section 11. The four that matter most: (1) the concept-level sample is 40 and nothing fixes that; (2) the bank's label space *is* the TKS ontology, so Arm E is near-tautological; (3) Arm C is `unavailable` on the licensed axis, so only five of six arms actually run; (4) the paraphrase-distance artifact is real, and the only thing standing between it and a false PASS is one control (ENC-COS) and one interaction test (E9).

---

## 1. CONTROLLING TEXT

### 1.1 Roadmap, verbatim

`docs/working/CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:204-206`:

> ```
> 4. Run a same-model/revision/hook/split/budget/seed TKS definition experiment:
>    original raw TKS; deployed byte-different payload; approved rich normalized
>    definitions; compact CAS; coherent non-TKS ontology; shuffled/random nulls.
> ```

**Binding force.** `same-model` is singular. **ONE** model, one revision, one hook, one split family, one hyperparameter budget, one seed list, for every arm. A second architecture family is **out of scope for this run**. Running a second family now and reporting whichever looked better is precisely the scope drift that produced four failed W0 experiments on 2026-07-24, where four runs were scored against a self-authored paraphrase of the gate instead of its text. Every design choice below is traced back to this line or to 8.2 / 8.4 by name.

### 1.2 Spec 8.2 fair-design list, verbatim

`docs/working/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md`, section `### 8.2 Fair design`:

> Hold constant:
>
> - exact model and immutable revision;
> - tokenizer and config;
> - neutral evaluation scenarios;
> - train/calibration/holdout groups;
> - prompt style and length distribution;
> - layers and hook semantics;
> - token-position policy;
> - classifier family and hyperparameter search budget;
> - seeds;
> - surface, embedding, layer-0, random-direction, and permutation controls.
>
> Definitions should influence only the registered concept-construction or training arm. All arms must be evaluated on the same independently labeled, neutral holdout bank.

Section 5 pins a concrete value to every one of those ten bullets plus the two key sentences.

### 1.3 Spec 8.4 decision rule, verbatim

> Do not use a single arbitrary threshold for every axis. Freeze axis-specific minimum effect sizes after a power analysis and before activation capture. At minimum, the canonical arm must:
>
> - beat its strongest surface/embedding control by a preregistered practical margin;
> - beat the compact arm with a positive lower confidence bound;
> - beat coherent random and shuffled controls;
> - preserve ontology-factorization consistency;
> - repeat across seeds;
> - retain value on a held-out architecture family before a cross-family claim.

**Order of operations, honoured literally.** Section 6 (power analysis) is computed and written **before** Section 7 (frozen effect sizes), and Section 7 is frozen **before** any activation is captured. Section 9 maps every 8.4 bullet to a numbered criterion. The last bullet — held-out architecture family — is **not attempted here**; it is a later precondition for a cross-family claim and Section 12 states that no cross-family claim can issue from this run.

### 1.4 Registry, binding

`docs/working/TKS_CAS_SEMANTIC_SOURCE_REGISTRY_CANDIDATE_20260720.json`, `status = OWNER_SIGNED_SEMANTIC_AUTHORITY_REGISTRY`. Its 25 `required_run_bindings` are binding on this run and are pinned in Section 5.5. Three `future_agent_rules` govern directly (read from the file this session):

- `Do not use compact CAS summaries as substitutes for original TKS definitions in a claim-bearing probe unless the compact form is an explicitly named comparator arm.` → Arm D is named comparator-only (Section 2.4).
- `Do not remap A1-D10 to A0-D9 by position without a tested crosswalk.` → Arm C is `unavailable` on the licensed axis (Section 2.3).
- `Do not call D3DAC0EF and A124302E the same definition version.` → Arms A and B are distinct semantic versions; A-vs-B is an equivalence test, never a "just normalization" dismissal (Section 2.2, criterion E7).

Relevant `known_conflicts` (ids read from the file this session): `element_indexing_A1_D10_vs_A0_D9` (P0_SEMANTIC_IDENTITY), `owner_payload_D3DA_vs_deployed_A124` (P0_SEMANTIC_VERSION), `normalized_rich_28_defs_missing_from_index` (P1_PROVENANCE), `tks_world_to_cas_domain_and_register_collision` (P0_SEMANTIC_AXIS), `tks_foundation_vs_cas_drive_position_mapping` (P1_SEMANTIC_AXIS).

---

## 2. THE SIX ARMS

### 2.0 The concept-construction mechanism (why six arms produce six different numbers)

The existing `evaluate_stage9_elements_pilot.py` pipeline trains a probe on hidden states against integer labels. **The definition text never enters it.** Run it six times and it returns six identical numbers. Any design that does not fix this is not an under-powered experiment; it is a non-experiment.

The fix, frozen here as `probe_method = definition_anchored_prototype_readout_v1` (`required_run_bindings[17]`):

**Step 1 — anchor pass (the class direction IS the definition).** For arm α and class code `c`, take **only** the `definition` body string. The `code` and `title` fields are **discarded** — titles are byte-identical between Arm A and Arm B on 0/40 elements, so including them would inject a constant that dilutes the treatment and hands every TKS arm a shared cue Arm E cannot have. Render the body into each of `K = 4` frozen frames, one short forward pass per frame, definition body starting at position 0:

```
FRAME_1 = "Definition: {body}\nThat role describes:"
FRAME_2 = "The following describes one role.\n{body}\nThat role describes:"
FRAME_3 = "Consider this description.\n{body}\nThat role describes:"
FRAME_4 = "Description: {body}\nThat role describes:"
```

Read `residual_post` at layer `L` at the **final token of the constant trailing scaffold `"That role describes:"`**. Average over the 4 frames. Call it `a_α(c)`.

**Step 2 — item pass (arm-independent by construction).** For bank item `x_i`, render the verbatim `english` string into the **same four frames** with `{body} = english`, read `residual_post` at the same layer `L` at the final token of the **same** scaffold `"That role describes:"`, average over frames. Call it `b(x_i)`. **The item states are computed once and shared byte-identically by every arm.** No arm's text ever enters an item pass.

**Step 3 — centering.**
`u_α(c) = ℓ2norm( a_α(c) − mean over the 40 classes of a_α )` — arm-internal class centering. Everything constant across an arm (devotional first-person voice in Arm A, copy-edit register in Arm B, compiled register in Arm D, Panksepp/Schwartz vocabulary in Arm E, mean length) lives in that mean and is removed. **What survives is only what distinguishes class c from the other 39 within that arm.** This is necessary but *not* sufficient: it removes the grand mean only. Block structure that is constant within a domain (Arm A's Spiritual/Mental/Emotional/Physical scaffolding) **survives centering**, and per-class length variation survives centering. The earlier claim in a draft design that "Arm A wins because it sounds different is arithmetically excluded" is **withdrawn as false**; the correct statement is that arm-*global* style is removed and domain-block style is not, which is why Section 3 adds the equal-token-budget replicate and Section 8 adds F5.
`v(x_i) = ℓ2norm( b(x_i) − mean over CALIBRATION items of b )` — one item mean, label-free, identical for every arm.

**Step 4 — readout.** `ŷ(x_i) = argmax_c cos( v(x_i), u_α(c) )`.
**Zero fitted parameters can change an argmax.** No classifier, no ridge, no logistic regression, no per-arm shrinkage. A softmax temperature `τ` is fitted per arm on calibration **for ECE only**; it is monotone in cosine and provably cannot alter any prediction; it is disclosed as the single per-arm fitted scalar.
A whitened variant is reported as a **secondary, non-gating** diagnostic: ZCA with a **single shared shrinkage 0.1**, covariance fitted on the pooled union of calibration items and all six arms' anchors, so the transform is byte-identical for every arm. (A per-arm Ledoit-Wolf shrinkage — as one draft design proposed — would be an arm-varying analysis hyperparameter masquerading as a hold-constant; it is forbidden here.)

**Why `u` and `v` are commensurable.** Both are read at the **final token of the identical constant string `"That role describes:"`**, after content that starts at position 0, through the identical four frames. Both are "the model's state after being asked what role the preceding text describes." This is the load-bearing step of the entire design and it is the one a draft design left least defended; it is fixed here by structural symmetry rather than by a whitening transform fitted on one distribution and applied to another.

**What varies across arms:** exactly the 40 definition body strings fed into Step 1. Nothing else in the pipeline reads the arm identity. The arm label enters the code only as a path to a JSON file of definition strings.

### 2.1 Arm A — `TKS_OWNER_RAW_40_28_D3DA_V1` — **THE CANONICAL ARM**

- **Resolved path:** `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/tks_owner_locked_definitions_20260603.json`
- **sha256:** `d3dac0ef5c94ccd768da0f18987846d8d0c0fa0b366e13dccc49c82252d2fc12` — recomputed this session, matches registry source id `owner_raw_40_28_workspace`.
- **Coverage:** 40/40 Elements (`A1`..`D10`) and 28/28 Foundations (`1a`..`7d`). Element definition length min 71 / mean 196.2 / max 686 chars.
- **Instantiation:** `tks_40_elements[*].definition`, verbatim, into the 4 frames. `code` and `title` discarded.
- **Code binding:** Arm A's element codes are literally `A1`..`D10` and the bank's `element_label` is literally `A1`..`D10`. **No crosswalk is required for Arm A or Arm B on the licensed axis.** This is a decisive advantage of the 40-Element axis over the 28-Foundation axis (Section 4.4).
- `required_run_bindings[2] definition_source_id = owner_raw_40_28_workspace`; `[4] definition_variant = owner_raw`.

### 2.2 Arm B — `TKS_DEPLOYED_NORMALIZED_40_28_A124_V1`

- **Resolved path:** `C:/Users/wakil/CAS-Harness-Run/noetic-compass-scaffold/noetic-compass/api/resources/tks_owner_locked_definitions_20260603.json`
- **sha256:** `a124302ed93c7b8571b24a5cdf14433adf904eb94fd65895c6fd25fae58e28a0` — recomputed this session.
- **Coverage:** 40/40 + 28/28, same code sets as Arm A (set equality verified). 20/40 element definition strings differ from Arm A; 0/40 titles differ. Element mean length 198.2 chars (Arm A 196.2).
- **Instantiation:** identical to Arm A.
- **Status:** a **DISTINCT semantic version**, never "Arm A normalized". `controlling_principle 3` of the registry: byte-different payloads are different semantic versions until an explicit transformation manifest proves otherwise. `known_conflict owner_payload_D3DA_vs_deployed_A124` requires an owner-adjudicated transformation diff; **no such artifact exists on disk** (searched `docs/working/`, `api/resources/`, `canon/normalized/`). No post-hoc "it's just copy-editing" claim may be made about any A-vs-B result, in either direction.
- `[4] definition_variant = deployed_normalized`.

### 2.3 Arm C — normalized rich Sub-Foundation definitions — **`unavailable` ON THE LICENSED AXIS**

- **Resolved path (28-Foundation half):** `C:/Users/wakil/Downloads/Everthing-Tootra-TKS/canon/normalized/canon_subfoundations_28_defs.json`
- **sha256:** `5507bf6f85f63dc62847ea5f9018b6ad4471ca8acfe851a0f50d2b4ebbf6c88d` — recomputed this session, matches the spec's `5507BF...`.
- **Coverage:** 28/28 Foundations (`1a`..`7d`), field `meaning`, mean 126.6 chars. **0/40 Elements.**
- **The 40-Element companion is blocked, not missing.** `canon_elements_40.json`, sha256 `f56eabed920236c36dd7f1c2b1334de822be770bfd4df1c72331673644eb4177` (recomputed this session), is keyed on the **`A0`..`D9` zero-based scheme**, not `A1`..`D10`. That is `known_conflict element_indexing_A1_D10_vs_A0_D9`, severity `P0_SEMANTIC_IDENTITY`. `required_run_bindings[6] tks_to_cas_crosswalk_sha256` has **no artifact anywhere on disk** to point at, and `future_agent_rule 2` forbids remapping by position. Its `definition` field is also min 13 / mean 21.1 / max 36 chars — a ~9× length mismatch against Arm A's 196.2, which independently violates 8.2's "prompt style and length distribution" hold-constant.
- **Decision, frozen:** Arm C is recorded **`unavailable`** on the 40-Element axis. It is not substituted, not remapped, and not silently dropped from the narrative. **The licensed axis therefore runs FIVE of the six specified arms.** This is a real cost of the axis swap and it is stated plainly in Sections 11 and 12.

### 2.4 Arm D — compact CAS — **COMPARATOR-ONLY PER THE SPEC**

**Spec 8.1, verbatim: `Arm D: shortened CAS translation summaries, explicitly comparator-only.`** Registry `future_agent_rule 1` independently confirms it. **Arm D is never a candidate for the licensed claim.** This is stated here, before any number exists, and Section 10 states the converse that a draft design omitted: comparator-only status governs what Arm D may be claimed *for*; it does **not** make "Arm D beats Arm A" uninformative.

- **Source:** `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`, sha256 `cda85c03273c47f7df9ac53258920b95ba7b3b2007b0e760856a67497f661880` — recomputed this session.
- **It does not exist as records.** Measured: the file defines the 10 Noetics, 4 Domains, 7 Drives and 4 Registers; the 40 and 28 are *generated* by cross-product and never enumerated by code. Arm D must be **COMPILED**, and that compilation is a new authorship act at `claim_bearing_precedence` **tier 7 (pedagogical summary)** — second-lowest of eight.
- **Compilation rule, deterministic, zero authorial discretion, executed by a committed script:**
  `definition(domain d, noetic n) = "<verbatim Noetic ^n definition from Clarification 1>" + " " + "<verbatim Domain-d definition>"`.
  Output emitted as `{code, title, definition}` JSON with its own `source_id = arm_d_compiled_compact_cas_v1`, its own sha256, and `authorship: ASSISTANT_COMPILED_TIER_7`.
- **HARD DISCLOSURE — the crosswalk does not exist.** Compiling Arm D onto `A1`..`D10` requires two mappings that are not ratified artifacts: TKS World `A/B/C/D` (Spiritual/Mental/Emotional/Physical) → CAS Domain, which is `known_conflict tks_world_to_cas_domain_and_register_collision` (P0_SEMANTIC_AXIS); and TKS Noetic `1..10` → CAS `^1..^9,^0`. The bank asserts both internally in its `element_domain` and `element_cas_noetic` fields, but a bank is `claim_bearing_precedence` **tier 8 (generated fixture)** and cannot supply authority for a tier-1 claim.
  **Every A-vs-D number is stamped `CONDITIONAL_ON_UNRATIFIED_CROSSWALK` unless B5 is completed.** 8.4's "beat the compact arm" criterion **cannot be licensed** until the owner ratifies the crosswalk, **and the ratification must be hashed into `required_run_bindings[6]` before capture**, not after.
- **One confound the axis swap removes.** On the 28-Foundation axis, Arm D's natural compile rule (Drive sentence + Register sentence) is *functionally identical to the bank's own generator* — verified this session at `build_stage7_foundation_fixture.py:202-204`, `_role_phrase(f,bundle,family) = _register_frame(register, _drive_core(drive, bundle), bundle, family)`. That would confound the headline A−D contrast with "structurally matches the label-generating process." On the 40-Element axis the bank's labels come from `_ELEMENT_GLOSSES` — 40 independently authored strings, verified this session at `build_stage9_elements_fixture.py:69-118` — which are **not** generated from a Noetic×Domain template. The reverse-contamination is removed by the axis choice, not assumed away. It is nonetheless **measured**: Arm D's per-class Jaccard to the bank glosses is a mandatory published covariate (Section 8, S13).

### 2.5 Arm E — coherent matched non-TKS ontology — **MUST BE CONSTRUCTED (B2)**

Nothing suitable exists on disk. Searched `docs/working/`, `api/resources/`, `canon/normalized/`, `research/cas_probe/` on `master` and on `experiment/cas-probe-pythia`, and all 20 registry source paths.

- **Construction, to remove authorship bias:** I do not author a rival ontology from scratch. I take **externally-authored, published primitive sets** and cross-product them into the same combinatorial shape the 40-Element axis uses (10 × 4):
  **Schwartz's 10 basic human values** (Self-Direction, Stimulation, Hedonism, Achievement, Power, Security, Conformity, Tradition, Benevolence, Universalism) × **Tinbergen's 4 questions** (mechanism, ontogeny, function, phylogeny) = 40 cells. Both are real, published, internally coherent, non-TKS frameworks with genuine external provenance. Names only are borrowed; definition prose is newly written.
- **Bijection: fixed and pre-registered BEFORE capture, never searched over.** Schwartz value `n` → TKS Noetic index `n` in the listed order; Tinbergen question `j` → TKS World `j` in the order `A, B, C, D`. No alternative bijection is tried, scored, or reported.
- **Matching, mechanically enforced before capture:** per-code token count within **±10%** of the index-matched Arm A definition, measured with the tokenizer pinned in `required_run_bindings[10]`, full per-code table published in the arm manifest. Register matched on four statistics with pre-registered tolerances: mean words/sentence ±15%, type-token ratio ±0.05, first-person pronoun rate ±0.02, Flesch-Kincaid grade ±1.5.
- **STRAW-MAN GATE, run BEFORE capture, binding:** 80 definitions (40 Arm A + 40 Arm E) shuffled and rated blind to arm, 1–5, on "coherent, non-circular definition of a distinct category", by a pre-registered independent rater. Arm E must score **≥ mean(Arm A) − 0.5**. A failure means Arm E is rewritten and re-audited. **A failed audit is a design defect and is NEVER reported as an Arm E loss.**
- `authorship: ASSISTANT_AUTHORED_FROM_EXTERNAL_ONTOLOGIES`, own `source_id` and sha256, registered before capture per bindings 1–4.

### 2.6 Arm F — nulls, six families, **ALL DRAWN PER SEED (B3)**

Never a single arbitrary draw. On 2026-07-24 a single-seed draw flipped a published margin's sign (+0.0375 → −0.0094, 14/20 seeds non-positive). Every F family is redrawn for each of the 20 registered seeds and reported as **mean and worst-of-20**.

| id | Construction | What it isolates |
|---|---|---|
| `F1` | Arm A definitions permuted across codes by a seeded **derangement** (no fixed points — a plain permutation leaves some classes correctly bound and silently weakens the null) | binding of definition to code |
| `F2` | Arm A definitions with token order shuffled **within** each definition; bag of words preserved **exactly** | composition, holding unigrams identical |
| `F3` | Anchors `u(c)` replaced by seeded random unit vectors, norm-matched to the empirical `‖u_A(c)‖` distribution | whether *any* anchor would do |
| `F4` | **Synonym-substituted Arm A** — word order and clause composition preserved, content-word identity replaced with synonyms | unigram identity, holding composition identical |
| `F5` | Non-ontological public-domain prose, per-code matched to Arm A's token length and to the same four style statistics | whether length and voice alone suffice |
| `F6` | **Coherent random** — Arm E's definitions attached to TKS codes by a seeded derangement | 8.4's "coherent random control", literally |

**F2 and F4 are a matched pair and neither is interpretable alone.** F2 destroys composition and keeps unigrams; F4 destroys unigrams and keeps composition. A draft design gated on F2 alone and called it "the bag-of-words killer"; that is wrong, because mean-pooling a scrambled string through a transformer does not return the ordered string's vector for reasons that have nothing to do with compositional semantics — attention is position-sensitive, so scrambling degrades the representation simply by making the text ungrammatical. F4 is what separates "composition carries meaning" from "the model encodes ungrammatical token soup worse". Section 7 gates on F2 and **requires** the F4 comparison as an interpretive disclosure with a pre-registered withdrawal rule.

---

## 3. LENGTH / FORMAT NEUTRALISATION

Length is the most obvious confound in this experiment and it cannot be fully eliminated. This section states exactly what is matched, exactly what is not, and what happens when it is not.

### 3.1 Format is matched exactly

- Identical `K = 4` frames, byte-identical, identical order, for every arm. Frame text contains **no** ontology-specific vocabulary, no code, no title, no domain word, no register word. The frame set is frozen in this file and hashed into `required_run_bindings[19]`.
- Identical trailing read-out scaffold `"That role describes:"` on **both** the anchor side and the item side.
- `code` and `title` omitted from every anchor, for every arm.
- Item text is the bank's `english` string **verbatim**, byte-identical across arms, in identical row order.
- One forward pass per (frame × unit). No shared long prefix. This structurally eliminates the anchor-context-depth confound that a draft in-context design carried, where the same code's anchor sat at a different absolute token offset in every arm because it followed a different amount of preceding definition text (Arm A ~2,400-token prefix vs Arm C ~900).

### 3.2 Token count is matched where it can be authored, and is a covariate where it cannot

| Arm | Element definition length | Matching |
|---|---|---|
| A | min 71 / mean 196.2 / max 686 chars (measured) | reference |
| B | mean 198.2 chars (measured) | naturally within ~1% of A; no authoring needed |
| C | `unavailable` on this axis | n/a |
| D | compiled; **will be short and cannot be matched without becoming a different source** | **covariate + equal-budget replicate** |
| E | authored | **per-code ±10% of the index-matched Arm A definition** |
| F1 | permutation of A | exact by construction |
| F2 | scramble of A | **token-identical by construction** |
| F3 | no text | n/a |
| F4 | synonym substitution of A | per-code ±10% |
| F5 | authored neutral prose | per-code ±10% + four style statistics |
| F6 | permutation of E | inherits E's matching |

**Residual, stated plainly.** Because each anchor is its own short pass with content beginning at position 0, the absolute index of the read token equals the framed definition's token count. That index therefore varies with definition length. **This cannot be removed without either padding (which changes what the model reads) or truncation (which is a different text).** It is handled four ways, all pre-registered:

1. **Per-code token counts published for all six arms**, before capture, in the arm manifests.
2. **MANDATORY EQUAL-TOKEN-BUDGET REPLICATE.** Every arm's definitions truncated at **sentence boundaries** (never mid-clause — mid-clause truncation produces ungrammatical fragments and is corruption, not a length control) to the shortest arm's per-code token budget. The full experiment is re-run on the truncated payloads. **If any licensed contrast does not survive the equal-budget replicate with the same sign, that contrast is reported `LENGTH_CONFOUNDED / NOT LICENSED`.** This is criterion E8.
3. **Length as a concept-level covariate.** Per-class accuracy regressed on per-class framed-definition token count; the licensed margin must survive with length in the model, reported with and without.
4. **F5**, the length-and-register-matched neutral-prose null, answers directly whether any text of this length and voice suffices.

### 3.3 Style is partially matched and the residual is disclosed

Arm-internal class centering (Section 2.0 Step 3) removes what is constant across an arm. It does **not** remove domain-block style (Arm A's Spiritual/Mental/Emotional/Physical scaffolding is constant within a 10-class domain block, not across all 40) and it does **not** remove per-class length. F5 and the equal-budget replicate are the instruments that address the residual. No claim is made that style is "arithmetically excluded."

---

## 4. THE NEUTRAL HOLDOUT BANK

### 4.1 Identity

- **File:** `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage9_elements_pilot_20260517.jsonl`
- **Pinned by git blob id, not path:** `165df0f6ff08c80fe1c42cd4412478527aabc934`. It exists **only** on branch `experiment/cas-probe-pythia`, not on `master`.
- **sha256:** `2f8637eedff0fb4d9e6191bd5c051ddc21cea699e33621896469a2e522306889` — matches the `input_sha256` recorded in `stage9_elements_pilot_probe_report_20260517.json`, so the bank is unaltered since the 2026-05-17 results were produced.
- `required_run_bindings[7] fixture_sha256` points at the **repaired** artifact (B1), which gets its own sha256.

### 4.2 Mandatory repair before use (B1)

Measured by me this session by reading the blob:

- 8,320 rows but only **5,920 unique `english`** → `duplication_factor = 1.4054`, which **FAILS** `assess_admissibility`'s `no_row_duplication` check (`research/reconciled/experiment_admissibility.py:110`, requires `<= 1.0001`).
- **Dedup is lossless:** 0 duplicated `english` strings carry conflicting labels (verified).
- Post-dedup, measured: **5,920 rows, 2,960 `base_sentence` clusters of exactly 2 rows each, 2,960 / 2,960 clusters carry BOTH labels, 148 rows per label for all 40 labels, 0 `base_sentence` spans more than one bundle.**
- The **published `train`/`val`/`test` fields are DISCARDED**: they leak 160 identical `english` and 80 identical `base_sentence` between train and test (and identically for train–val and val–test). New partition per Section 5.4.

Per-bundle composition after dedup, measured:

| bundle | rows | clusters |
|---|---|---|
| `bundle001_expense_audit` | 640 | 320 |
| `bundle002_garden_irrigation` | 480 | 240 |
| `bundle003_library_archive` | 480 | 240 |
| `bundle004_warehouse_pick` | 480 | 240 |
| `bundle031_food_safety` | 480 | 240 |
| `bundle032_water_utility` | 480 | 240 |
| `bundle041_patient_triage` | 960 | 480 |
| `bundle042_disaster_relief` | 640 | 320 |
| `bundle043_energy_grid` | 640 | 320 |
| `bundle044_privacy_review` | 640 | 320 |

Four bundles carry 7 paraphrase families, six carry 4 (`_TEST_ONLY_FAMILIES = compressed_minimal, long_embedded_clause, counter_alias_hard_negative` are appended only to the originally-test bundles). **The ten bundles are therefore NOT exchangeable in size or composition.** Bundle-level inference with G = 10 treats non-exchangeable units as exchangeable; this is disclosed as a limitation (Section 11) and mitigated by stratified bundle draws (Section 5.4) and by publishing per-bundle family composition in the split manifest.

### 4.3 Label provenance, and the argument that labeling is NOT derived from any single arm's wording

- The 40 class glosses are `_ELEMENT_GLOSSES` in `build_stage9_elements_fixture.py` (lines 69–118 on `experiment/cas-probe-pythia`), read by me this session: **40 distinct, independently authored strings**, one per `A1`..`D10`, e.g. `A4 = "subtle aetheric energy, aura, and purpose-frequency behind a thing"`, `B6 = "left-brain logic, criticism, rigidity, and conscious analysis"`. They are **not** a template cross-product.
- **Dated 2026-05-17, seventeen days BEFORE the 2026-06-03 arm payloads exist.** They cannot be derived from Arm A's or Arm B's wording as a matter of chronology.
- Measured wording independence against Arm A (scout measurement, this session): **0 of 40** glosses share a five-word n-gram with the matching Arm A definition; **0 of 40** contain the element title verbatim; content-word Jaccard **min 0.056 / mean 0.234 / max 0.538**.
- `anti_leak_flags` set on 8,320 / 8,320 rows: `contains_framework_word: false`, `contains_literal_element_code: false`, `counterbalanced_keyword_pack: true`.
- Every item carries **two competing glosses** and a `Focus: A.` / `Focus: B.` marker that alone selects the label — e.g. `"A is the role where ultimate source-awareness…; B is the role where a truth or virtue that quiets the soul…"`. `pair_kind` is adversarially matched (same-domain noetic cycles and same-noetic domain cycles), so the two glosses in a sentence come from neighbouring classes.

**The honest limit.** The bank is neutral with respect to arm **WORDING**. It is **NOT** neutral with respect to TKS **CONCEPTS** — its 40 labels *are* the TKS ontology, authored by this project. Consequences, pre-registered:

- **Arm E cannot win by construction.** Beating a foreign ontology on a TKS-labelled bank demonstrates that TKS definitions describe TKS labels better than Schwartz×Tinbergen does, which is close to a restatement of the setup. Criterion E6 is therefore declared **the weakest of 8.4's six** and is never headlined.
- **Jaccard mean 0.234 with max 0.538 is not "absent".** A draft design measured this for Arm A only and then asserted "the lexical bridge is already measured absent." That inference is **withdrawn**. Per-class content-word Jaccard and max shared n-gram between **every arm** (A, B, D, E, and each F family) and the bank glosses are a **mandatory covariate published before capture** (Section 8, S13), and the licensed margin must survive conditioning on it at concept level (n = 40).
- **This caps the claim.** No result from this bank can support a claim that TKS concepts are more universal than other concept sets. It can only support a claim about *wording within the TKS concept set*.

### 4.4 The 28-Foundation axis is DROPPED as claim-bearing

**A draft design made `stage7_foundation_pilot_20260517.jsonl` the primary axis because it is hygienically cleaner (`duplication_factor` exactly 1.0000, zero cross-split leakage). That is choosing the primary axis on hygiene rather than on construct validity, and it is wrong.**

Verified this session by reading `build_stage7_foundation_fixture.py` on `experiment/cas-probe-pythia`:

```
line 202: def _role_phrase(foundation, bundle, family) -> str:
line 203:     drive, register = foundation
line 204:     return _register_frame(register, _drive_core(drive, bundle), bundle, family)
```

The 28 class texts are `_register_frame[r](_drive_core[d])` — **7 drive-core templates × 4 register-frame templates**, with no content specific to foundation position `1a`..`7d` beyond drive⊗register. Three consequences:

1. **Construct collapse.** Any semantic content in Arm A's 330-char holistic foundation definitions that is not decomposable into drive × register is **invisible** to that bank and can only add noise. The axis cannot measure what the experiment exists to measure.
2. **Label-side effective n is 11, not 28.** The class-discriminative text reduces to 7 drive cores + 4 register frames. No bootstrap over rows, clusters, classes, seeds, or bundles in any of the three draft designs resamples those 11 strings. Every published MDE on that axis is optimistic by roughly `sqrt(28/11) ≈ 1.6×`. This is the 2026-07-24 defect (640 rows / 80 unique prompts) recurring one abstraction level deeper.
3. **Reverse contamination onto Arm D.** The register frames paraphrase Clarification 8 — `"the explicit reasoning pass that tests"` / `"the sequential logic that tests"` against Clarification 8's `"explicit, sequential, logical"`; `"the value-toned pull that makes X feel important"` against `"value-laden, feeling-toned"`; `"the concrete handling that puts X into contact"` against `"sensorimotor, concrete"`; `"the ultimate-purpose frame"` against `"high-abstraction, purpose-orienting"`. `_anti_leak_flags` tests only the four literal register names and four world names, so none of this trips it. Arm D's natural compile rule on that axis reproduces the bank's own generator.

**Frozen decision.** The 28-Foundation axis is run and reported for 8.3 completeness, stamped `CONSTRUCT_INVALID_AXIS`, and **no criterion in Section 7 is gated on it**. 8.3's "28-way and factorized Foundation/World macro-F1" is delivered as a descriptive number that licenses nothing. Owner acknowledgement of this scope reduction is build item **B9**.

### 4.5 Disqualified bank

`C:/Users/wakil/CAS-Harness-Run/noetic-compass-scaffold/noetic-compass/docs/working/definition_locked_tks_mtc_20260603/definition_locked_tks40_f28_fixture_20260603.json`, sha256 `812b4a73c2c4c70c36c52500897e8a7afabb29430e2f93eb06823a2ad38bb1bf`. **816 / 816 rows embed the Arm B definition verbatim** as `"Source definition: <Arm B text>"`. Using it would put the definition inside the evaluation input, violating 8.2's "Definitions should influence only the registered concept-construction or training arm," and Arm B would win by string match. It is retained **only** as an explicitly-labelled contaminated positive control (Section 8, S14) and is excluded from every claim.

---

## 5. HELD CONSTANT — the full 8.2 list, with the concrete value each is pinned to

### 5.1 "exact model and immutable revision"

**ONE model for all six arms**, per roadmap:204-206 `same-model/revision/...`.

- **Selection rule, frozen now:** a single open-weight decoder-only model with ≥ 16 transformer blocks and a context window ≥ 1,024 tokens, for which an arm-free supervised reference number on this exact bank is produced as part of this run (Section 5.6).
- `required_run_bindings[8] model_id`: the candidate carried forward from the draft designs is `Qwen/Qwen2.5-1.5B-Instruct`. **This is not yet pinned.**
- `[9] resolved_model_revision`, `[10] tokenizer_sha256`, `[11] model_config_sha256`, `[12] weights_manifest_sha256`: **`unavailable_until_capture_host_resolved`** (build item B8). They are resolved on the capture host and written into a hashed amendment to this file **before** the first forward pass. **I will not fabricate a revision hash.**
- `[13] adapter_version`: `none` (no adapter; frozen base weights only).
- **A second architecture family is OUT OF SCOPE.** 8.4's held-out-family bullet is a later precondition for a cross-family claim (Section 12).

### 5.2 "tokenizer and config"

Hashed separately at `[10]` and `[11]` so 8.2's requirement is auditable rather than asserted. `[22] dtype = bf16 weights / fp32 readout`; `[23] quantization = none`; `attn_implementation` and batch size **pinned in the amendment** (they are not among the 25 bindings and their omission is a real gap — bf16 reduction order differs between prefill and cached paths and between batch sizes). **Determinism precondition P3**: the identical input run twice must produce a bit-identical vector, or capture halts.

### 5.3 "neutral evaluation scenarios"

The repaired 40-Element bank (B1), byte-identical rows in identical order for every arm. Bank text never contains any arm's definition wording (Section 4.3). Item states are computed once and **shared** by all arms, so "same holdout bank" is satisfied by identity, not by re-derivation.

### 5.4 "train/calibration/holdout groups"

- **There is no train split.** The primary readout fits nothing on labels.
- **Partition unit = `contrast_bundle_id`**, the top of the dependence hierarchy. Never rows, never `base_sentence` alone.
- **Per seed:** a stratified draw of **3 calibration bundles / 7 holdout bundles**, stratified so that each side contains at least one 7-family bundle and at least one 4-family bundle (the bundles are not exchangeable — Section 4.2). Holdout ≈ 4,100 rows / ≈ 2,050 clusters, exact counts varying by seed and recorded per seed.
- The **same realised partition** is used by all six arms and all controls within a seed.
- Calibration is used for exactly three things, all label-free except the third: the item mean in Step 3; the pooled covariance for the secondary whitened variant; and — once, on seed 0 only — the layer choice (Section 5.6), which does use labels but is arm-blind.
- The split generator plus all 20 realised partitions are hashed into one **split manifest** → `[18] split_sha256`.

### 5.5 "prompt style and length distribution"

Section 3 in full. Format matched exactly; token count matched per-code within ±10% for Arms E, F4, F5 and by construction for F1/F2; **reported as a covariate plus a mandatory equal-token-budget replicate for Arm D**, which cannot be length-matched without becoming a different source.

### 5.6 "layers and hook semantics"

- `[14] hook_semantic = residual_stream_post_block_L` (maps to the spec 9.1 Probe IR `residual_pre` of block L+1), identical everywhere.
- **Layer grid, frozen:** layer 0 (retained permanently as the layer-0 control) plus every 2nd block to the top.
- **`[15] layer` — selection rule, frozen, and it is arm-free.** `L` is chosen **once**, on **seed 0's calibration bundles only**, by the calibration macro-F1 of an **arm-free supervised multinomial logistic probe** on the item states `b(x_i)` — a probe that never sees any definition text from any arm. `L` is then frozen for all six arms, all controls, and all 20 seeds.
  *Why not "the mean across all six arms", as two draft designs proposed:* that mean includes the null arms, and `F1` scores by lexical topic alone (its lines carry real Arm A vocabulary, only mis-bound), so maximising a mean that contains it actively selects the layer at which lexical topic matching works best. An arm-free supervised reference has no such preference.
- The **full holdout layer sweep for every arm is reported** as 8.3's layer-stability metric and as criterion E11; it gates nothing and can never move `L`.
- **The supervised probe doubles as the capability reference `R_sup`** — the arm-free anchor that says what the states can carry at all.

### 5.7 "token-position policy"

`[16] token_position_policy`: **final token of the constant scaffold `"That role describes:"`**, on both the anchor side and the item side, averaged over the 4 frozen frames. Identical for every arm. `wrong_token` control = the first content token (Section 8, S12).

### 5.8 "classifier family and hyperparameter search budget"

**There is no classifier and no search.** Cosine-argmax to definition-derived prototypes. Zero fitted parameters can change a prediction. The single per-arm fitted scalar is the softmax temperature `τ`, which is monotone in cosine, cannot alter any argmax, affects ECE only, and is disclosed here. The secondary whitened variant uses **one shared shrinkage 0.1** on a **pooled** covariance — identical for every arm.

**Budget symmetry with the controls, which two draft designs violated.** The hidden arms get one layer choice made by an arm-free probe. The ENC-COS control (Section 8, S4) gets the same *number* of free choices: its pooling mode is selected once on seed-0 calibration by the same arm-free criterion, then frozen. No arm and no control gets a larger search than any other.

### 5.9 "seeds"

`[25] random_seeds = [0,1,2,...,19]` — 20 seeds, the same list for every arm. Seeds govern: the stratified bundle partition draw, the F1/F6 derangements, the F3 random directions, and the bootstrap resampling. Because the readout is closed-form, there is **no optimizer seed** and the fit contributes zero seed variance.

**A frank note on what seed variation does and does not buy here.** Seeds resample the *item* side (partition, bootstrap) and the *null* draws. They do **not** resample the 40 authored definitions, the model, the layer, or the bank glosses. Section 6 shows the concept-level term is ~4× the item-level term, so a 20-seed gate is a real hurdle on the smaller of the two variance components and **is not a substitute for concept-level inference**. Both are reported; both must pass.

### 5.10 "surface, embedding, layer-0, random-direction, and permutation controls"

Section 8 in full. The **entire control family is frozen as a manifest and hashed into `[19] control_manifest_sha256` BEFORE capture**, so "strongest surface control" is a `max()` over a pre-committed set and can never be chosen after seeing results.

### 5.11 Remaining bindings

`[1] semantic_registry_version` = `OWNER_SIGNED_SEMANTIC_AUTHORITY_REGISTRY`, registry sha256 `9469a10ae330749c61d157518b849a3737b0f5bd268e44c7bd6334625a38c483`. `[5] symbol_indexing_scheme = A1..D10 (TKS one-based)`. `[6] tks_to_cas_crosswalk_sha256` = **empty; Arm D blocked on B5**. `[20] code_commit`, `[21] container_digest`, `[24] hardware_topology`: recorded at capture.

---

## 6. EFFECTIVE SAMPLE SIZE AND POWER ANALYSIS

**Row count is not sample size.** This section is written **before** Section 7, per 8.4's explicit ordering.

### 6.1 Four denominators, and the one that governs is not the big one

All measured by me this session from the git blob.

| Level | Unit | n | Role |
|---|---|---|---|
| Rows | deduped `english` | **5,920** (from 8,320) | **not** an independence unit |
| Item clusters | `base_sentence` | **2,960** total; ≈ **2,050** in holdout | item-noise unit |
| **Concepts** | **authored definition per class** | **40** | **the unit that carries the treatment** |
| Topical | `contrast_bundle_id` | **10** | generalisation unit |

Quoting 5,920 or 4,144 as `n` would be the 2026-07-24 error (640 quoted, 80 honest) in a milder form.

**The concept level governs.** Every gated contrast in 8.4 — canonical minus compact, canonical minus coherent-random, canonical minus shuffled — is a comparison between two sets of authored definition strings. There are 40 of them. No amount of bank size fixes that.

### 6.2 Admissibility gate compliance (`research/reconciled/experiment_admissibility.py`, read this session)

| Check | Result |
|---|---|
| `no_row_duplication` (`<= 1.0001`) | **1.4054 FAIL as published; 1.0000 PASS after mandatory dedup (B1)** |
| `effective_n >= MIN_EFFECTIVE_N_FOR_MARGIN_GATE = 200` (line 44) | ≈ 2,050 clusters **PASS** |
| `balanced_accuracy_quantum <= 0.015` (line 141) | `1/2050 = 0.000488` **PASS**; per-class step `1/104 = 0.0096` also PASS |
| `exact_prompt_groups` | **WOULD FAIL and is amended, not bypassed.** That check requires one prompt text per group; here a group deliberately holds a 2-item minimal counterfactual pair. Pre-registered replacement, strictly stricter: `counterfactual_pair_group` (group holds exactly 2 texts differing only in the focus marker) **PLUS** `mixed_label_group_count == unique_group_count`. **Measured: 2,960 / 2,960.** The 2026-07-24 W0 bank had 0/80 groups carrying both labels; this bank has 100%. |
| `instrument_positive_control` | **RAISES `ValueError("Positive control needs exactly two classes")` at line 190.** Does not apply to a 40-way task. Multiclass replacement specified in Section 8, S15 (build item B6). |
| Constants calibration | `MIN_EFFECTIVE_N_FOR_MARGIN_GATE = 200` and the `0.015` quantum were derived from a **0.15 binary** margin. Their applicability to a 40-way task is asserted, not derived. **Disclosed as an apparatus gap** (Section 11). |

### 6.3 Empirical inputs — measured from artifacts on disk, not guessed

A draft design set the concept-level dispersion by guess (`sd = 0.15`) while the empirical number sat in the repo. I computed it. From `stage9_elements_pilot_probe_report_20260517.json` on `experiment/cas-probe-pythia` (headline hidden readout, layer 5, vs the strongest text baseline `tfidf_char_3_5`, both on the published test split of this exact bank):

- hidden per-class F1: **min 0.598 / mean 0.909 / sd 0.079**
- `tfidf_char_3_5` per-class F1: **min 0.034 / mean 0.468 / sd 0.150**
- **per-class delta (hidden − tfidf): min 0.008 / mean 0.441 / sample sd 0.1790, 0 of 40 classes negative**
- discordance rate `p_dis = 2193 / 4480 = 0.4895`
- headline macro-F1 0.9088 vs `tfidf_char_3_5` 0.4680 (lift **+0.4408**); majority 0.0250

**Frozen planning value: `σ_c = 0.18`.** It is the measured per-class delta dispersion on this exact bank. It is measured on a *hidden-vs-surface* contrast, which has a large mean effect and therefore probably larger dispersion than an arm-vs-arm contrast will have — so it is **conservative** (larger SE → larger MDE → higher bar). **The realised `σ̂_c` will be reported against 0.18 for every gated contrast** (a draft design froze a planning σ and never checked it; that is not permitted here).

### 6.4 Power computation

**Estimand, stated once and gated as stated.** All frozen bars in Section 7 are in **macro-F1**. The concept-level estimand is: compute `Δ_c = F1_armX(c) − F1_armY(c)` once per class on the full holdout, then **bootstrap those 40 scalars**. (Resampling 40 classes and recomputing macro-F1 on a resampled confusion matrix is invalid — precision depends on the omitted classes' false positives — and is forbidden.) The bundle-level estimand is the per-bundle macro-F1 difference, `G = 10`, `t_9`.

**Concept level (binding).**
`SE_c = σ_c / √C = 0.18 / √40 = 0.02846`.
One-sided `α = 0.05` (z = 1.6449), power 0.80 (z = 0.8416), sum 2.4865.
**MDE_concept = 2.4865 × 0.02846 = 0.0708 macro-F1.**
Difference-in-differences: `SE = √2 × 0.02846 = 0.04025` → **MDE_DiD = 0.1001**.

**Bundle level.** `SE_b = τ / √10`. At planning `τ = 0.03`, `SE_b = 0.00949`, one-sided `t_9` MDE ≈ `(1.8331 + 0.8834) × 0.00949 = 0.0258`. At `τ = 0.10`, MDE = 0.086. **Pre-registered escape clause:** `τ` is estimated from the 10 observed per-bundle differences **after** capture; **if `τ̂ > 0.10`, bundle-level inference is declared UNDERPOWERED and that contrast is reported OPEN / NOT LICENSED. The bar is not lowered and the clustering unit is not changed to rescue it.**

**Item level (not binding).** Per-class F1 SE at `p ≈ 0.9` with ~52 holdout clusters per class = `√(0.9×0.1/52) = 0.0416`; macro over 40 = `0.0416/√40 = 0.0066`. **Item noise ≈ 0.007 versus concept 0.0285 — the concept term is ~4× larger and irreducible.** This is why the class count, not the row count, sets every bar.

**Power at the frozen bars (concept level, one-sided α = 0.05):**

| Bar | z | Power |
|---|---|---|
| +0.08 | (0.08/0.02846) − 1.6449 = 1.166 | **0.88** |
| +0.15 | 5.271 − 1.6449 = 3.626 | **0.9999** |
| DiD, LCB>0 only, MDE 0.100 | — | disclosed, no magnitude bar |

**Sensitivity of the tightest bar (+0.08) to `σ_c`:** `σ_c = 0.12` → power 0.99; `0.18` → 0.88; `0.24` → 0.68; `0.30` → 0.51.

### 6.5 CONJUNCTIVE POWER — disclosed now, before capture

Section 7 gates a **conjunction** of criteria (an intersection-union test, whose level is bounded by the max component level, so **no Bonferroni correction is applied or needed** — applying one here would be statistically wrong and would silently under-power the gate).

But conjunction destroys power. Eight gated criteria each at ~0.88 give a joint pass probability bounded above by 0.88 and, if loosely independent, as low as `0.88^8 ≈ 0.36`. The criteria are positively correlated (they share the same Arm A readout), so the truth is somewhere in **[0.36, 0.88]** and I cannot pin it more tightly without pilot data I do not have.

**This is disclosed here, in advance, for one reason: so that a `NOT LICENSED` outcome can never later be used as an argument that a bar was "set too high".** `NOT LICENSED` is a plausible modal outcome of a correctly-designed conjunctive gate even when every true effect equals its bar. The bars do not move.

---

## 7. FROZEN AXIS-SPECIFIC MINIMUM EFFECT SIZES

**Frozen 2026-07-25, after the power analysis in Section 6, before any activation capture. Never moved afterward, in either direction, for any reason, including a near miss. All figures are macro-F1 on the 40-Element holdout. Every criterion requires BOTH a concept-level (n = 40) and a bundle-level (G = 10) 95% one-sided lower confidence bound > 0 unless stated otherwise.**

| id | Contrast | Frozen bar | Reasoning |
|---|---|---|---|
| **E1** | Arm A − **strongest** surface/embedding control (`max` over S2, S3, S4, S5, chosen before capture) | **≥ +0.15** | 8.4 bullet 1. 2.1× MDE_concept. Historical supervised lift on this exact bank was +0.4408, so a practical bar well above MDE is justified; but this readout is **zero-shot**, so the historical number is context, not a prediction. |
| **E2** | Arm A − Arm D (canonical minus compact) | **≥ +0.08** point estimate **AND** LCB > 0 | 8.4 bullet 2. 1.13× MDE_concept, power 0.88. Both are required: 8.4 asks for a positive lower bound, and the point floor stops a statistically-positive +0.01 from licensing anything. **Stamped `CONDITIONAL_ON_UNRATIFIED_CROSSWALK` and NOT LICENSABLE until build item B5.** |
| **E3** | Arm A − F1 (shuffled binding), **worst of 20 seeds** | **≥ +0.15**; and F1's 20-seed mean must land in `[0.005, 0.075]` (chance = 0.0250) | 8.4 bullet 3. Worst-of, not mean. Implies Arm A absolute macro-F1 ≥ ~0.175. |
| **E4** | Arm A − F6 (coherent random: Arm E definitions deranged onto TKS codes) | **≥ +0.08**, LCB > 0 | 8.4 bullet 3, "coherent random", literally. |
| **E5** | Arm A − F2 (word-order-scrambled A, unigrams identical) | **≥ +0.08**, LCB > 0 | Composition test. **Mandatory paired disclosure:** `Arm A − F4` (synonym-substituted A, composition identical, unigrams destroyed) is reported alongside with its ratio. **Pre-registered withdrawal rule: if `(A − F4) ≥ (A − F2)`, the effect is unigram identity rather than composition, and the compositional reading of E5 is WITHDRAWN in the write-up even if E5 passes its bar.** |
| **E6** | Arm A − Arm E (coherent aligned non-TKS rival) | **≥ +0.08**, LCB > 0 | 8.4 bullet 3. **Declared IN ADVANCE the WEAKEST of the six criteria and never headlined** — the bank's label space *is* the TKS ontology, so this is close to tautological (Section 4.3). |
| **E7** | Arm A vs Arm B | **TOST equivalence, band ±0.05, 90% CI. NO directional bar.** | Two distinct semantic versions with no transformation manifest on disk. Reported as `EQUIVALENT_AT_THIS_POWER` or `DISTINGUISHABLE`, **never** as "just normalization". **If `DISTINGUISHABLE` with B > A, see Section 10 — that refutes the canonical-wording prior.** Equivalence CI half-width at concept level ≈ `1.685 × 0.02846 = 0.048 < 0.05`, so a ±0.05 band is resolvable. |
| **E8** | **Equal-token-budget replicate** | Sign agreement with the native-length run on **every** licensed contrast | Section 3.2. A licensed contrast that flips or vanishes under sentence-boundary truncation to the shortest arm's budget is reported `LENGTH_CONFOUNDED / NOT LICENSED`. |
| **E9** | **SUBSTRATE × ARM INTERACTION** — `(A − D)_hidden − (A − D)_ENC-COS` | **LCB > 0**, no magnitude bar; MDE 0.100 disclosed. **PLUS:** Spearman ρ between the six-arm ordering under the hidden readout and under ENC-COS must be **< 0.9**; if `ρ ≥ 0.9`, report **`CONFOUNDED / NOT LICENSED` regardless of every other criterion.** | **This is the decisive criterion.** It is what separates "hidden states encode the semantics" from "TKS wording is nearer in paraphrase space to TKS-derived glosses." See Section 8, S4. |
| **E10** | **Seed dispersion** | **All 20 seeds positive** on E1, E2, E3, E4, E5, E6, E9; **and** seed sd ≤ 0.5 × the bar for each. One non-positive seed ⇒ NOT LICENSED. | 8.4 bullet 5. This is the 2026-07-24 lesson encoded as a gate. It would have caught the +0.0375 → −0.0094 sign flip. |
| **E11** | **Leave-one-bundle-out** | A-over-D and A-over-surface orderings hold in **≥ 9 of 10** held-out topical bundles | honest topical n = 10 |
| **E12** | **Ontology-factorization consistency** | Under Arm A, the 10-way **Noetic** macro-F1 and the 4-way **Domain** macro-F1 must **each** beat their own strongest surface control by **≥ +0.10**, LCB > 0 | 8.4 bullet 4. **The "28-way minus the product of the two factor accuracies ≤ 0.10" test proposed in a draft design is DISCARDED as mathematically wrong** — the product is the joint accuracy under *independent* factor errors, real factor errors are positively correlated, so the criterion fires on well-behaved factorised readouts; and it compares a macro-F1 to a product of accuracies. The 2×2 table of (Noetic correct) × (Domain correct) and its odds ratio with CI are **reported descriptively**; **no threshold is applied, because no threshold was derivable from data available before capture.** That is stated rather than invented. |
| **E13** | **Layer stability** | E1 must hold at **≥ 60%** of layers in the frozen grid, not only at the selected `L` | 8.3 |
| **E14** | **Calibration** | ECE ≤ 0.10 for Arm A, **reported, non-gating** | 8.3. Temperature is monotone and cannot change an argmax. |

### 7.1 Hard preconditions — run and passed BEFORE any criterion is scored

| id | Precondition | Failure verdict |
|---|---|---|
| **P1** | Multiclass positive control (S15): plant an orthonormal per-class direction at 3.0 SD into the item states and require the **exact** anchor→prototype→cosine path to recover **macro-F1 ≥ 0.90** | `INSTRUMENT_BROKEN`, halt |
| **P2** | Contaminated-fixture check (S14): on `812b4a73...` Arm B must reach **≥ 0.90** by string presence | `INSTRUMENT_BROKEN`, halt |
| **P3** | Determinism: identical input run twice yields a **bit-identical** vector; numerical-noise floor measured and reported alongside E7's ±0.05 band | halt and pin `attn_implementation` / batch size |
| **P4** | `Arm A − F3` (random-direction anchors) **≥ +0.20** | `INSTRUMENT_INSENSITIVE / NOT SCORED` — a statement about the ruler, never about the definitions |
| **P5** | Arm A's zero-shot macro-F1 must **not exceed** the arm-free supervised reference `R_sup` by more than +0.05 | leakage suspected; halt and investigate |
| **P6** | Arm E straw-man audit passed (Section 2.5); Arm E and F5 length/register matching tables published | halt; rewrite Arm E |
| **P7** | Build items B1–B9 complete and hashed into an amendment to this file | capture forbidden |

### 7.2 Graded external calibrator — required, and pre-registered as such

P1 validates plumbing, not sensitivity. A planted 3.0-SD direction is a near-degenerate task; passing it says the machinery propagates a signal, not that a zero-shot cosine-to-prototype readout has any capacity for 40-way semantic paraphrase matching. **Therefore: the identical pipeline, identical frames, identical scaffold, identical layer, is additionally run on a public zero-shot text-classification set with a published achievable range, and that number is reported next to Arm A's.** Without it, a null across six arms cannot be distinguished from "the ruler has no resolution at this task difficulty." The specific public set is **`unavailable_until_pinned`** and is pinned in the control manifest (B7) before capture.

---

## 8. CONTROLS — and why each is beatable in principle

**The entire manifest below is frozen and hashed into `required_run_bindings[19]` BEFORE capture.** "Strongest surface control" is a `max()` over this pre-committed set, never a favourite chosen afterwards.

### 8.0 The structural argument, stated precisely — and its limit

All six arms consume **byte-identical** item text; item states are computed once and shared. Therefore any statistic that is a function of the holdout text alone — every tf-idf, char-n-gram, count, or hashing control applied to the *items* — emits **one number, not six**, and is mathematically incapable of producing a between-arm difference.

**That is a statement about bag-of-substrings feature maps, and a draft design over-generalised it into blanket immunity.** The correct statement is: the controls that matter here are **substrate-swapped twins** — the *identical* anchor→centre→cosine-argmax procedure with the encoder replaced. Those *do* produce six numbers and *can* reproduce the arm ordering. That is why S2, S3, S4 and S5 below are not item-only baselines; each is the same procedure with a different encoder.

### 8.1 The manifest

| id | Control | Beatable in principle? |
|---|---|---|
| **S1** | Majority class | Chance = **0.0250** (measured). Trivially beatable; it is a floor reference, not an adversary. |
| **S2** | **tf-idf char(3,5) substrate twin** — identical procedure, model replaced by a char-n-gram vectorizer fitted unsupervised on calibration items; definitions vectorised, arm-centred, cosine-argmax. Six numbers. | **Yes, and measured beaten.** On this exact bank the *supervised* `tfidf_char_3_5` probe reaches 0.4680 macro-F1 against hidden 0.9088. Under the zero-shot prototype rule it is strictly weaker (the supervised probe at least saw labels; this one sees none). Beatable, and demonstrably not at ceiling. |
| **S3** | **tf-idf word(1,2) substrate twin** | Same argument; supervised reference 0.4524 acc on the sibling bank. |
| **S4** | **ENC-COS — order-aware frozen sentence encoder substrate twin. MANDATORY. THE ADVERSARY THAT DECIDES THE EXPERIMENT.** `ŷ(x_i) = argmax_c cos(Enc(definition_α(c)), Enc(x_i))`, pinned model + revision + sha256, no model internals, identical rows, identical arm-centring, **identical selection budget** (one pooling choice made on seed-0 calibration by the arm-free criterion). | **Yes — and it may well win.** It is *not* subject to the order-insensitivity ceiling that caps S2/S3: it can bind the `Focus: A.` marker to a span, and the bank is a **semantic paraphrase of the same TKS concepts**, so a strong paraphrase-sensitive encoder is a genuinely dangerous adversary. **If it wins, or if its six-arm ordering matches the hidden ordering at ρ ≥ 0.9, the result is `CONFOUNDED / NOT LICENSED` (E9).** This outcome is live, pre-registered, and is the reason this is an experiment rather than a demonstration. **No truncation risk:** items are ~40–60 tokens and the longest Arm A definition is 686 chars ≈ ~160 tokens, both far inside a 512-token window — the auto-passing-by-truncation defect that a draft in-context design carried (a 2,400-token prefix truncating the item out of the control's window entirely) is structurally impossible here. |
| **S5** | **Layer-0 control** — same model, embedding-layer output, same pooling, same rule. A bag-of-embeddings reference inside the model's own space. | **Yes.** It is a genuine encoder with real lexical signal; it is weaker than mid-layer but not degenerate. 8.2 requires it by name. |
| **S6** | **Random-direction control = Arm F3**, seeded random unit vectors norm-matched to `‖u_A(c)‖`, redrawn per seed | Expected at chance 0.0250. 8.2 requires it by name. |
| **S7** | **Shuffled control = Arm F1**, per-seed derangement, worst-of-20 reported | Beatable by any binding-sensitive readout; unbeatable by a pure topic-matcher. That asymmetry is the point. |
| **S8** | **Composition control = Arm F2** (order scrambled, unigrams identical) | See E5's withdrawal rule. |
| **S9** | **Vocabulary control = Arm F4** (synonyms substituted, order and composition identical) | The disambiguating partner to S8. Neither is interpretable alone. |
| **S10** | **Length-and-register control = Arm F5** (neutral non-ontological prose, per-code matched) | Answers "is any text of this length and voice enough?" |
| **S11** | **Coherent-random control = Arm F6** (Arm E definitions deranged onto TKS codes) | 8.4's "coherent random", literally. |
| **S12** | **Wrong-axis / wrong-layer / wrong-token** — 28-Foundation prototypes scored against the 40-Element bank through a forced arbitrary mapping; the frozen grid re-run at a deliberately mismatched layer; the readout taken at the first content token | All expected near chance. Roadmap item 7. |
| **S13** | **LEXICAL-OVERLAP COVARIATE AND CONTROL.** For **every** arm (A, B, D, E, F1–F6) and **every** class, publish content-word Jaccard and max shared n-gram against the bank gloss for that class, **before capture**. Plus a classifier whose *only* features are the 40 per-class Jaccard similarities. **Pre-registered rule: the licensed margin must survive with per-class overlap as a concept-level covariate (n = 40), reported with and without.** | **Yes, and this is the single most important non-encoder control.** Measured Arm A overlap is Jaccard **min 0.056 / mean 0.234 / max 0.538** — not absent. Arm E will sit near zero by construction, so an uncontrolled A > E could be nothing but overlap. |
| **S14** | **Contaminated positive control** — the recitation fixture `812b4a73...`, where 816/816 rows embed the Arm B text verbatim. Arm B must win by string match (P2). | Permanently labelled `CONTAMINATED`; excluded from every claim. |
| **S15** | **Multiclass instrument positive control** (build item B6) — planted orthonormal per-class direction at 3.0 SD through the exact pipeline, require ≥ 0.90 (P1). Replaces `instrument_positive_control`, which raises `ValueError` on non-binary and therefore **silently does not apply**. Plus the graded external calibrator of Section 7.2. | The binary guard is replaced, not skipped, and the replacement is pre-registered. |
| **S16** | **Targeted ablation vs matched controls** (8.3) — project out the top-39 directions of the Arm A prototype span and rescore; compare against a **same-rank random** projection and against a rank-39 projection in the orthogonal complement | Arm A's drop must exceed same-rank random with LCB > 0. |
| **S17** | **Permutation tests** — 10,000 shuffles at the **`base_sentence` group level** (never row level: row-level shuffling of clustered data is what made p anticonservative on 2026-07-24), plus a bundle-level sign-flip test | **Floors disclosed on every p** — see 8.2 below. |

### 8.2 p-value floors, disclosed in advance

- Row/group permutation at 10,000 draws: floor `1/10001 = 9.999e-05`. Reported via `permutation_p_disclosure` as **`p <= 1/10001 (floor; zero of 10,000 shuffles beat observed)`** and **never as a magnitude**.
- Bundle-level sign-flip has only `2^10 = 1,024` distinct sign assignments. **Its hard floor is `p = 0.000977` and no run of this design can ever report a smaller p from it.** Any smaller number in output is a bug.
- Per-seed derangement nulls across 20 seeds: floor `1/21 = 0.0476`, so the A-vs-F1 verdict rests on the **effect-size bar (E3)**, not on its p. Stated up front.
- The existing `stage9_elements_pilot_probe_report_20260517.json` contains `exact_binomial_mcnemar_p = 0.0` — a float-underflow artifact. **It is neither reproduced nor quoted.** McNemar is recomputed in log space.

### 8.3 Rank as a confound — acknowledged, not controlled away

Arm D's compiled definitions are drawn from a small pool (10 Noetic sentences + 4 Domain sentences), so after arm-internal centering its prototype matrix has **at most ~13 degrees of freedom** against Arm A's 39. It cannot represent Noetic×Domain interaction. Since the bank's `pair_kind` includes same-domain noetic cycles and same-noetic domain cycles, Arm D is structurally handicapped on some contrasts by **capacity, not by wording quality**. F3 is built as a rank-and-spectrum-matched control precisely because rank is understood to be a confound — and a draft design then omitted that control for the one gated arm-vs-arm comparison in 8.4.

**Fixed here:** a **rank-matched Arm A ablation** is added — Arm A's prototype matrix projected to Arm D's realised effective rank — and is reported alongside E2. **If Arm A's advantage over Arm D does not survive rank matching, E2 is reported `RANK_CONFOUNDED / NOT LICENSED`.** The realised effective rank of every arm's centred prototype matrix is published.

---

## 9. DECISION RULE

### 9.1 Mapping to 8.4, bullet by bullet

| 8.4 requirement | Criterion |
|---|---|
| beat its strongest surface/embedding control by a preregistered practical margin | **E1** (+0.15 over `max(S2,S3,S4,S5)`) |
| beat the compact arm with a positive lower confidence bound | **E2** (+0.08 and LCB > 0) — **blocked on B5** |
| beat coherent random and shuffled controls | **E3** (F1 shuffled), **E4** (F6 coherent random) |
| preserve ontology-factorization consistency | **E12** |
| repeat across seeds | **E10** (all 20 seeds positive) |
| retain value on a held-out architecture family | **NOT ATTEMPTED — out of scope, Section 12** |

### 9.2 The canonical arm (Arm A) is LICENSED if and only if ALL of the following hold

1. Every precondition **P1–P7** passed.
2. **E1** ≥ +0.15 with concept-level and bundle-level 95% one-sided LCB > 0.
3. **E2** ≥ +0.08 with LCB > 0 at both levels, **and** the crosswalk ratification (B5) is hashed into `required_run_bindings[6]` and dated **before** the capture timestamp, **and** E2 survives the rank-matched Arm A ablation (Section 8.3).
4. **E3** worst-of-20 ≥ +0.15, with F1's mean inside `[0.005, 0.075]`.
5. **E4** ≥ +0.08 with LCB > 0.
6. **E5** ≥ +0.08 with LCB > 0, **and** the F4 disclosure does not trigger the withdrawal rule.
7. **E6** ≥ +0.08 with LCB > 0 (weakest criterion; passing it is necessary, never sufficient, never headlined).
8. **E7** reported; if `DISTINGUISHABLE` with B > A, see Section 10 — **the claim does not issue**.
9. **E8** sign agreement under the equal-token-budget replicate.
10. **E9** interaction LCB > 0 **and** ENC-COS rank correlation ρ < 0.9.
11. **E10** all 20 seeds positive on E1, E2, E3, E4, E5, E6, E9, with seed sd ≤ 0.5 × bar.
12. **E11** ≥ 9 of 10 bundles.
13. **E12** both factor axes ≥ +0.10 over their own strongest surface control.
14. **E13** E1 holds at ≥ 60% of the layer grid.
15. Realised `σ̂_c` reported against the 0.18 planning value, and realised `τ̂ ≤ 0.10`, for every gated contrast.

### 9.3 Everything else

**Any single failure ⇒ that axis is `OPEN / NOT LICENSED`, and the overall verdict is `NOT LICENSED`.**

- **Mixed results stay mixed.** A run that clears 13 of 15 conditions is `NOT LICENSED`. It is reported as "13 of 15 conditions met, two open, here are which," never as a partial win.
- **A negative result is `NOT LICENSED`.** So is a null across all arms.
- **Criteria are never rewritten after outcomes are known.** No bar moves, no clustering unit changes, no contrast is re-run under a different unit to rescue it, no control is swapped for a weaker one, no axis is added post hoc. (Roadmap exit clause; project honesty law.)
- **An effect below the resolvable size is reported as `NOT RESOLVABLE AT C = 40`, never as "no effect" and never as grounds to move a bar.** Concretely: an A−D advantage below ≈ 0.071, or a DiD below ≈ 0.100, is not a small effect — it is an unmeasurable one by this design.
- **Headline contrast list, frozen here in order, so no post-hoc narrative selection is possible:** E1, then E9, then E2, then E5, then E3/E4, then E10. E6 is never headlined. E7 is reported neutrally unless it triggers Section 10.

---

## 10. WHAT A NEGATIVE RESULT WOULD MEAN

The owner's prior under test is: **original raw TKS wording (Arm A) carries more of the semantic content than the deployed copy-edit (Arm B), the compact CAS restatement (Arm D), or a foreign ontology (Arm E).** This section spells out, before any data exists, exactly what would falsify it. **This is the section that makes the experiment real, and two of the three draft designs did not have it.**

### 10.1 The outcomes that REFUTE the prior

**R1 — Arm D ≥ Arm A.** If the compact CAS arm matches or beats the canonical arm with a non-negative lower bound at either level, the prior is **REFUTED**, not merely unproven. Stated in as many words, because a draft design left the door open to dismiss exactly this:

> **Arm D's comparator-only status governs what Arm D may be claimed FOR. It does NOT make "Arm D beats Arm A" uninformative. If Arm D ≥ Arm A, the reported finding is that compact CAS restatements preserve as much of the readable semantic content as the original owner wording, and the canonical-wording claim is refuted.**

Tier-7 provenance means a *win over* Arm D is worth less (it is a win over an artifact I compiled). It does not mean a *loss to* Arm D can be waved away.

**R2 — Arm B > Arm A outside the ±0.05 equivalence band.** If 20 comma-and-clause-level copy edits move macro-F1 by more than a fifth of the E1 bar, then either the deployed normalization genuinely improved the definitions — refuting "the original wording is superior" — or the readout is measuring lexical noise rather than semantics, which refutes the whole instrument. **Either way the canonical-wording claim does not issue.** This is reported as a refutation, not as "a neutral version difference."

**R3 — Arm E ≥ Arm A.** If a Schwartz×Tinbergen ontology, evaluated on a bank whose 40 labels *are* the TKS ontology, matches Arm A, then TKS wording carries no advantage even on its home ground. This is the strongest possible disconfirmation available in this design and it is very unlikely; its unlikeliness is exactly why E6 is the weakest *confirmatory* criterion.

**R4 — the ENC-COS ordering matches the hidden ordering (ρ ≥ 0.9), or ENC-COS beats Arm A.** The finding is then: *TKS wording is nearer in paraphrase space to TKS-derived glosses than the comparators are.* That is a property of two texts. It is not a claim about hidden states, about cognition, or about universality. **Reported `CONFOUNDED / NOT LICENSED`.**

**R5 — Arm A ≈ Arm F2 (order scrambled).** If destroying word order costs nothing, the readout is a bag of words and the semantic claim dies. **Paired requirement:** if `(A − F4) ≥ (A − F2)`, the surviving mechanism is unigram identity, and the compositional reading is withdrawn even when E5 passes.

**R6 — Arm A does not survive the equal-token-budget replicate.** Then length, not lineage, is the explanation. Arm A's element definitions run to 686 characters; Arm D's compiled units will be short. Longer text plausibly produces better-separated anchors for reasons that have nothing to do with whose ontology it is. **Reported `LENGTH_CONFOUNDED / NOT LICENSED`.** This reading is pre-committed now precisely because it is the reading that would be most tempting to argue around afterwards.

**R7 — Arm A does not survive the S13 lexical-overlap covariate or the rank-matched ablation.** Then the ordering is word overlap (or Arm D's rank cap), not semantics.

### 10.2 The outcome that falsifies NOTHING — and must not be dressed up as a falsification

**A flat null across all six arms.** If Arms A–F all land within noise of each other and P4 trips (`Arm A − F3 < +0.20`), the correct report is `INSTRUMENT_INSENSITIVE / NOT SCORED`. It says the zero-shot cosine-to-prototype channel is too lossy to distinguish these definition sets at 40-way. **It does not say the definitions do not differ.** The honest write-up phrase is fixed here: **"not resolvable through this channel"** — never "no difference exists."

This is why the graded external calibrator (Section 7.2) is mandatory. Without a known-achievable external reference run through the identical pipeline, a null across six arms cannot be distinguished from a broken ruler, and that ambiguity is exactly the hole through which four W0 experiments fell on 2026-07-24.

### 10.3 What a genuine PASS would mean, stated narrowly

*On the repaired 40-Element bank, on one named model at one named revision and one named layer, under a zero-shot definition-anchored prototype readout with no supervision, the original raw TKS wording produces a class geometry that is read out more accurately than a compact CAS restatement, a coherent foreign ontology, six null families, and the strongest of four pre-committed surface and embedding substrates — and that advantage is not reproduced by an order-aware paraphrase encoder running the identical procedure.*

That is the entire claim. Section 12 lists what it still cannot support.

---

## 11. PRE-REGISTERED LIMITATIONS

Including every unresolved adversarial finding.

### 11.1 The binding limitation

**The concept-level sample is 40, and no amount of bank size fixes it.** Every gated contrast compares two sets of 40 authored strings. 5,920 rows, 2,960 clusters, 20 seeds and 10,000 bootstrap resamples reduce the item-noise term to ≈ 0.007 macro-F1 while leaving the concept-level term at ≈ 0.028 — four times larger and irreducible. **An A-over-D advantage below ≈ 0.071 macro-F1 is not resolvable by this design**, and a difference-in-differences below ≈ 0.100 is not resolvable at all. If the true advantage of original wording over compact CAS is real but modest — say 0.04 — this experiment will honestly fail to license it, and that failure will be reported as `NOT RESOLVABLE AT C = 40`. Two follow-on repairs exist and neither is in scope: run both axes jointly for C = 68 (raises n but mixes a construct-invalid axis), or author independently-written definition *variants* per class so the concept-level term can be estimated rather than assumed.

### 11.2 Unresolved adversarial findings, carried forward

| # | Finding | Status here |
|---|---|---|
| 1 | Bank is concept-contaminated: its 40 labels **are** the TKS ontology | **UNRESOLVED.** Caps the claim; E6 declared weakest and never headlined. |
| 2 | Arm A→bank Jaccard mean 0.234 (max 0.538) is not "absent"; five of six arms were never measured | **PARTIALLY RESOLVED.** S13 makes it a mandatory pre-capture covariate for all arms with a survival requirement — but the covariate adjustment itself has n = 40. |
| 3 | Arm C `unavailable` on the licensed axis; **only five of six specified arms actually run** | **UNRESOLVED**, registry-blocked (`element_indexing_A1_D10_vs_A0_D9`, P0). |
| 4 | Arm D needs an unratified crosswalk; owner holds the prior under test | **BLOCKED on B5.** Mitigated by requiring ratification hashed **before** capture. |
| 5 | Arm D is rank-capped (~13 dof vs Arm A's 39) | **PARTIALLY RESOLVED** by the rank-matched Arm A ablation (Section 8.3); the underlying asymmetry remains real. |
| 6 | Arm D and Arm E are assistant-authored artifacts; a win over them is worth less than a win over an owner source | **UNRESOLVED and disclosed.** Arm D is tier 7 (second-lowest of eight). |
| 7 | The 10 bundles are **not exchangeable** (480–960 rows, 4 vs 7 paraphrase families) | **PARTIALLY RESOLVED** by stratified draws and published composition; G = 10 inference still treats non-exchangeable units as exchangeable. |
| 8 | `MIN_EFFECTIVE_N_FOR_MARGIN_GATE = 200` and the `0.015` quantum were calibrated on a **0.15 binary** margin | **UNRESOLVED apparatus gap**, disclosed. A 40-way recalibration is proposed but not derived here. |
| 9 | `instrument_positive_control` raises `ValueError` on non-binary | **REPLACED (B6), not skipped**, plus the graded external calibrator. |
| 10 | Percentile bootstrap under-covers at ~40 outer clusters (typically 88–91% against nominal 95%) | **PARTIALLY RESOLVED:** BCa intervals are used at the concept level and the coverage caveat is reported alongside every LCB. No cluster-count correction is claimed to be exact. |
| 11 | Conjunctive power over ~8 gated criteria is in `[0.36, 0.88]` and cannot be pinned | **DISCLOSED IN ADVANCE** (Section 6.5) so a NOT LICENSED cannot be used to argue a bar down. |
| 12 | Zero-shot readout may floor for **all** arms | **UNRESOLVED risk.** P1, P4 and the graded external calibrator distinguish a broken ruler from a real null, but not a *merely insensitive* one from a real null. |
| 13 | Residual anchor read-position varies with definition length | **PARTIALLY RESOLVED** by isolated per-definition passes, per-code token publication, the equal-budget replicate (E8), the length covariate, and F5. It cannot be eliminated. |
| 14 | `attn_implementation` and batch size are not among the 25 required bindings | **DISCLOSED**; pinned in the amendment; determinism precondition P3 added. |
| 15 | 28-Foundation axis: construct collapse, label-side n = 11, Arm D reverse contamination | **RESOLVED BY DROPPING THE AXIS** (Section 4.4). It licenses nothing here. |

### 11.3 Second-order honesty notes

- The `signature_kind` on the enabling receipt is `INTERACTIVE_SESSION_OWNER_APPROVAL_TRANSCRIBED_BY_ASSISTANT` — a recorded authorization, not a cryptographic or legal signature. The registry states it unblocks roadmap item 4 **only** and licenses no empirical claim.
- `σ_c = 0.18` is measured on a hidden-vs-surface contrast, not an arm-vs-arm one. It is used as a conservative planning value and the realised `σ̂_c` is reported against it.
- The historical +0.4408 lift on this bank was produced by a **supervised** probe on Pythia-era activations. It is context for what the bank can carry, **not** a prediction for this zero-shot readout, and it is never quoted as one.

---

## 12. WHAT THIS CANNOT LICENSE

Even a full PASS on all fifteen conditions in Section 9.2 does **not** license any of the following.

1. **No cross-family universality claim.** One model, one revision — roadmap:204-206 says `same-model`. 8.4's held-out-architecture-family bullet is **not attempted** in this run. It is a separate, later precondition, and running a second family now and reporting the better one is the exact scope drift that produced four failures on 2026-07-24.

2. **No causal claim.** This is a correlational readout. S16's targeted ablation compares prototype-span removal against same-rank random removal; that is evidence about which directions carry the readout, **not** an intervention on model behaviour. The permitted phrasing is `causally supports`; the forbidden phrasing is `found the neurons` or `TKS structure causes`.

3. **No product ACCEPT, no customer-facing claim, no marketing claim.** This is a scoped internal validation of one readout on one bank. Scoped-validation ACCEPT ≠ customer ACCEPT.

4. **No claim about the 28 Foundations.** That axis is stamped `CONSTRUCT_INVALID_AXIS` (Section 4.4) and its numbers license nothing.

5. **No claim involving Arm C.** Arm C is `unavailable` on the licensed axis. The run is five-armed, not six-armed, and any write-up saying "all six arms" is wrong.

6. **No claim that compact CAS summaries are semantically deficient in general.** Arm D is assistant-compiled at precedence tier 7 through an unratified crosswalk. At best the result says *this particular mechanical compilation* reads out worse on *this* bank.

7. **No claim that TKS concepts are more universal than other concept sets.** The bank's label space *is* the TKS ontology. Beating Arm E on it is close to tautological (Section 4.3). At most the result speaks to *wording within* the TKS concept set.

8. **No claim of universality of the TKS codomain from formal properties.** Registry `future_agent_rule 4`: `Do not use formal universality of the TKS codomain as proof of empirical hidden-state readability.`

9. **No claim beyond one layer, one hook, one token-position policy, one readout family.** E13 reports layer stability; it does not extend the claim to other hooks or readouts.

10. **No retroactive re-scoping.** If the result is `NOT LICENSED`, that is the result. It is not re-framed as "promising", "directionally supportive", or "pending a larger run" in any artifact, and no bar in Section 7 is revisited.

---

*Design and pre-registration only. Nothing was run, no activation was captured, no git commit was made. Every path, sha256, row count, cluster count, bundle count, per-class F1 and dispersion figure in this document was measured this session from the artifact named beside it; every value not measured is marked `unavailable` with what was searched. The model revision (`required_run_bindings[9]`) and every artifact required for Arms D, E and F are `unavailable_until_authored` and must be built, hashed, and appended as a signed amendment to this file before any capture.*
