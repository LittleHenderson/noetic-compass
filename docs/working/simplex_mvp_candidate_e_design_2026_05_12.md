# Candidate E — Grounded On-Policy CAS-Native (DESIGN, locked 2026-05-12)

**Status:** DESIGN ONLY. Diagnosis locked. Gates locked. **No build, no SDG, no pod work until this doc passes audit.**
**Scope:** Research-track. v0-rc1 remains canonical. Test data and on-policy training only — no architecture change.
**Predecessors:** Architectural review A → C → B → D all falsified on fresh records. Candidate E is the first plan that targets the failure mechanism instead of changing the costume it wears.

## Locked diagnosis

> **The copy signal is too weak / too local / too template-correlated to force source-grounded binding on fresh identifiers.**

What the diagnostic probe confirmed (2026-05-12, laptop, $0):
- Production tokenizer (vocab=38,683) splits `stageA0_5_0296` into structured sub-tokens with literal `stage` token present (id 2897).
- `find_stage_var_spans` fires on 100/100 sampled rpm_chain training records.
- `typed_slot_source >= 0` on 1836/1836 STAGE_VAR positions across the sample. Copy supervision firing rate: **100%**.
- Therefore: copy supervision was fully operational across A / C / B / D training. The signal exists; the model didn't learn binding from it.

What the model actually learned (across A / C / B / D evidence):
- Identifier shape: yes.
- Template completion (`Let stage<X> name a foundational thought, stage<Y> name <PHRASE>`): yes.
- Local copy alignment (point at *some* source position with matching token-type): yes.
- **Source-grounded binding (the specific source identifier must equal the specific target identifier): no.**

Failure surface: free decode on fresh records returns 0/37 canonical recovery while TF returns 30% — the model can identify canonical-shaped tokens when the prefix is held correct, but cannot assemble the source-correct identifier without prefix scaffolding because nothing in training forced that binding.

## Rejected hypotheses (with reasons)

| Hypothesis | Status | Why |
|---|---|---|
| Tokenizer no-op (stage_vars are single in-vocab tokens) | **FALSIFIED** | Probe 2026-05-12: production tokenizer splits identifiers; `find_stage_var_spans` fires 100% |
| Architecture problem (transformer vs SSM) | **FALSIFIED** | A / B / D all differ in architecture and all fail with the same fingerprint |
| Exposure bias as primary cause | **DEMOTED to symptom** | The TF=30%/free=0% gap is a *symptom* of weak binding supervision, not the root cause |
| Decode-strategy fix (rep-block, beam, contrastive decode) | **REJECTED** | Decode-only ceiling is ~30% (cannot exceed TF); will not produce ≥50% canonical recovery |
| Deterministic renderer (symbolic patching of model output) | **REJECTED** | Out of scope per project commitment: solution must be learned, not post-hoc symbolic repair |
| Foreign LLM distillation / RLHF / retrieval | **REJECTED** | Hard constraint: no foreign pretrained models in production stack |
| Tune lr / batch / loss weights to coax B3 or D1 past gate | **REJECTED** | Anti-tuning rule in force |
| 11-canary pack as eval surface | **REJECTED** | Training-adjacent; gave misleadingly optimistic B3 result |

## Target

**Source-grounded learned binding.** When given fresh CAS input the model has never seen, the model must produce target identifiers that come from the actual source positions in the input — not from the training distribution of identifier shapes, not from template completion, not from local copy alignment that happens to match by type.

The architecture stays. The encoder, decoder (transformer or SSM), simplex, typed slots, hard typed-fiber emission, compiler, traceability — all kept. **Only the training data and training procedure change.**

## Pre-Stage-1 audit (gating Stage 1 work)

Before any SDG, audit whether the current collator's `typed_slot_positions` and `typed_slot_source` tag the **full identifier span** or only the **head position(s)**. The probe showed ~18 STAGE_VAR positions per rpm_chain record while a 4-stage chain has 4 identifiers × ~10 sub-tokens = ~40 positions. The ratio (~18/40) suggests partial-span coverage. This must be confirmed and the full-span labelling spec must be locked before Stage 1's data wedge writes any record.

**Audit deliverable** (~30-60 min laptop work):
- For 20 sampled rpm_chain training records, dump per-position `typed_slot_positions.argmax(dim=-1)` and check whether STAGE_VAR appears on every sub-token of each identifier or only on a subset (head, tail, both).
- Document the existing labelling rule (head-only / full-span / other) in a short audit memo.
- If labels are head-only, Stage 1 must change `find_stage_var_spans` and `_derive_anchors` to emit full-span labels AND `rpm_copy_grounding_v2` must use the full-span spec.

If audit confirms full-span labelling: Stage 1 inherits the existing label scheme.
If audit confirms head-only labelling: Stage 1 specifies full-span as a load-bearing addition.

## Stage 1 — `rpm_copy_grounding_v2` data wedge

**Goal:** build a training corpus that *requires* source-grounded binding to fit, not just shape + template + local alignment.

**Six required structural properties** (every property must be implemented; partial implementation is not a Stage 1 pass):

1. **Disjoint identifier suffix partition** (patched per audit 2026-05-12 — the frozen broader B3 pack is treated as an external reserved eval set, not part of the new partition).

   - Train suffixes: 4-digit bodies in `0000-7999` AND 3-digit bodies in `000-799` AND 5-digit bodies in `00000-79999`.
   - Dev suffixes: 4-digit `8000-8999`, 3-digit `800-899`, 5-digit `80000-89999`.
   - Test suffixes: 4-digit `9000-9999`, 3-digit `900-999`, 5-digit `90000-99999`.

   **Broader-B3 reserved-eval blacklist:** the frozen broader B3 eval pack (`broader_b3_eval_pack_2026_05_12.jsonl`) uses 15 unique identifier bodies that span all three new buckets (6 train-range, 5 dev-range, 4 test-range). These bodies must be subtracted from ALL generated train/dev/test/source-swap corpora to prevent leakage. The frozen pack itself stays as-is (apples-to-apples B3 comparison preserved).

   Blacklist bodies (extracted from the frozen pack 2026-05-12):
   ```
   3-digit (4 bodies): 707, 884, 932, 978
   4-digit (5 bodies): 5568, 6846, 8472, 8768, 9871
   5-digit (6 bodies): 19672, 77848, 79730, 81399, 87663, 94055
   ```

   Stage 1 SDG must enforce: `generated_body not in BROADER_B3_BLACKLIST` for every record in every artifact (train, dev, test, source-swap-dev, source-swap-eval). Verify post-generation via a regex audit pass.

2. **Counterfactual source pairs.**
   - For every base rpm_chain record, generate N (≥3) *parallel* records with:
     - Same noetic bindings (`^0^P; ^7^P_{F5}; ...`)
     - Same EN reply structure (same template, same phrase fillers)
     - **Different** identifier suffixes (sampled from train-bucket only)
   - The model cannot satisfy these records by template completion alone — it must produce the *specific* identifier from each source.

3. **Hard negatives in source.**
   - For each rpm_chain record, the source CAS expression contains the canonical identifiers PLUS 1-2 distractor identifiers (same prefix family, different suffix) that do NOT appear in the target reply.
   - Forces the copy head to point at the *specific* source position, not just any source position with type=STAGE_VAR.
   - Distractor placement: scattered through the CAS expression, NOT clustered with the canonical identifiers.

4. **Template diversification.**
   - Vary the rpm_chain EN reply structure across at least 8 templates:
     - `Let X name <P1>, Y name <P2>.`
     - `Define X as <P1>; define Y as <P2>.`
     - `In this chain, X represents <P1>, and Y represents <P2>.`
     - `<P1> is named X, while <P2> is named Y.`
     - `The expression binds X to <P1> and Y to <P2>.`
     - `Identify X: <P1>. Identify Y: <P2>.`
     - `X stands for <P1>; Y stands for <P2>.`
     - `Where X is <P1> and Y is <P2>.`
   - Each template appears with comparable frequency across the rpm bucket. Breaks "Let stage..." as a loop prior.

5. **Anti-loop examples.**
   - Include records that *complete cleanly without repetition* — short rpm chains (2-stage) with concise replies, 3- and 4-stage chains with terminal connectives that close the structure ("and that completes the chain"). Diverse termination patterns.
   - Optional: include adversarial examples where the target reply contains a near-repetition that resolves rather than loops — teaches the model that template-like prefixes do not entail looping.

6. **Full-span labelling** (status after pre-Stage-1 audit 2026-05-12).
   - Audit result: **within-span coverage is FULL** (every sub-token of each labelled identifier gets STAGE_VAR + sequential `typed_slot_source`). No fix needed on this axis.
   - Audit file: `docs/working/candidate_e/audit_label_coverage_2026_05_12.md`.

7. **Cross-chain full coverage** (load-bearing per pre-Stage-1 audit 2026-05-12).
   - Audit result: **partial — current collator labels only 2 of 4 unique identifiers per rpm_chain record (50%), and 0 of any repeat occurrences. Total identifier-occurrence coverage is 33%.** This is the load-bearing labelling defect.
   - Stage 1 must fix `_derive_anchors` / `find_stage_var_spans` (or equivalent) so that **every distinct identifier occurrence in the target text** (including W-, P-, and repeat-stage identifiers) is labelled with `typed_slot_positions = STAGE_VAR` and a valid `typed_slot_source` pointing at the corresponding source CAS position.
   - Per-record post-generation verification: STAGE_VAR span count must equal identifier-occurrence count in target text. Audit script script must run on the train + dev + test + source-swap-dev + source-swap-eval corpora.
   - Audit file: `docs/working/candidate_e/audit_label_coverage_2026_05_12.md` (Sections 4-6 specify the fix).

**Stage 1 deliverables** (per audit 2026-05-12 — corpus paths corrected; training corpora live under `data/path_d/`, eval packs live under `data/eval/`):

| Artifact | Path | Purpose |
|---|---|---|
| Training corpus (train-bucket suffixes) | `cas-synthetic/data/path_d/rpm_copy_grounding_v2_train.jsonl` | What the model trains on |
| Dev corpus (dev-bucket suffixes) | `cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.jsonl` | Stage 2b TF fresh-source-recovery + slot-F1 + non-rpm-leakage gates |
| **Source-swap dev corpus** (dev-bucket suffixes; paired records) | `cas-synthetic/data/path_d/rpm_copy_grounding_v2_source_swap_dev.jsonl` | Stage 2b source-swap conditionality gate — paired records with same EN target, different source identifiers |
| Test corpus (test-bucket suffixes) | `cas-synthetic/data/path_d/rpm_copy_grounding_v2_test.jsonl` | Stage 3 on-policy eval (held out from both training and dev) |
| Source-swap eval pack (test-bucket suffixes; paired records) | `cas-synthetic/data/eval/rpm_copy_grounding_v2_source_swap_eval.jsonl` | Stage 4 source-swap conditionality gate (production-target validation pack) |

Size targets: ~2000-3000 train records to provide counterfactual / hard-negative variance + a sister non-rpm corpus of comparable size to maintain category balance. Dev / test packs sized to ~200 records each. Source-swap dev pack: ~50 paired records (100 evaluations). Source-swap eval pack: ~50 paired records (100 evaluations).

**Record metadata:** every record carries an `eval_meta` dict containing the suffix bucket (`train` / `dev` / `test`), the identifier body, the chain length, the prefixes, and (for source-swap records) a `source_swap_pair_id` that links paired records. The regen step verifies no record's body is in the broader-B3 blacklist.

**Stage 1 build review (before pod work):**
- Sample-read 20 records per template variant to confirm fluency and structural correctness.
- Verify hard negatives are actually present (regex check).
- Verify counterfactual pairs have matching EN structure with different identifiers.
- Verify suffix partition holds (no train record uses dev or test suffix; no eval pack record uses train suffix).

## Stage 2 — B2 retrain + TF grounding probe (split into E2a + E2b per audit 2026-05-12)

**Goal:** confirm `rpm_copy_grounding_v2` teaches the binding rule under teacher forcing before committing to on-policy.

The Stage 2 gates measure *source recovery* and *source-swap conditionality* — both require the copy/pointer objective to be live in the trained model. Stage 2 is therefore split into two substages; the TF gate applies after E2b.

### E2a — LM + FR + slot warmup

**Build:**
- Warm-start from B2's `ckpt_final.pt`. B2 was the strict-validate stage (slot stable, no leakage); use it as the base because B1's regression guard already passed there.
- Loss preset: `lm=1, fr=1, slot_type=1, copy=0, phrase_bias_aux=0` (identical to `b2` / `d2` ablation).
- Train on `rpm_copy_grounding_v2_train.jsonl` for 1000 steps.

**Internal sanity checks** (not the locked TF gate — those apply after E2b):
- Per-batch `train_progress` losses finite.
- At step 250 / 500 / 750 / 1000: canary read; no phrase loops, no triviality.
- Slot F1 on dev-bucket records ≥80% before promoting to E2b (cheap LM+slot check; not the binding gate).

### E2b — Add copy / pointer-span / contrastive / coverage objectives under teacher forcing

**Build:**
- Warm-start from E2a's `ckpt_final.pt`.
- Loss preset: full set with new objectives active:
  - `L_lm` (gold-prefix LM, teacher forcing — no model-prefix mix yet; that's Stage 3)
  - `L_fr` (Fisher-Rao on simplex)
  - `L_slot` (slot-type CE)
  - `L_pointer` (per-position copy loss — already exists)
  - `L_span` (new: span-coherence — penalize per-token copy decisions that don't form a contiguous source-span on STAGE_VAR positions)
  - `L_contrastive_margin` (new: correct source position scores higher than hard-negative source positions by margin m)
  - `L_coverage` (new: penalize the same source position being pointed at twice when target has distinct identifiers)
  - `L_phrase_bias_aux` (existing)
- Train on `rpm_copy_grounding_v2_train.jsonl` for 1000 steps.

**Locked TF gates** (read at post-E2b TF eval on FRESH dev-bucket records):

| Gate | Threshold | Rationale |
|---|---|---|
| TF fresh source recovery | **≥80%** | If the data wedge + copy/span objectives teach binding, TF should recover the right identifier almost always (TF has the correct prefix; the only question is "did the model learn to read the source") |
| Source-swap conditionality | **≥85%** | Same EN target, swap source identifiers → output should swap. Isolates binding from shape memorization. **Measured on the dedicated `rpm_copy_grounding_v2_source_swap_dev.jsonl` artifact** (per audit 2026-05-12: a separate file rather than embedded in the dev pack, so the source-swap subset's size and composition are explicit). |
| Slot F1 for copy-bearing slots | **≥90%** | Slot head correctly identifies typed positions in fresh records |
| Non-rpm leakage | **0** | STAGE_VAR slot never fires on non-rpm inputs |

**Kill rule:** if **any** of the four gates fails after E2b, stop. **In particular, if TF fresh recovery stays around 30%, the data/labels are still wrong** — fix the wedge before Stage 3. **Do not run DAgger on a model that hasn't learned binding under TF.**

**Why split:** E2a alone (LM+FR+slot, no copy) cannot satisfy the TF source-recovery gate because the copy/pointer objective is the mechanism that learns source binding. Gating TF recovery on E2a would test only template completion, not binding. E2b adds the copy/span/contrastive/coverage signal under teacher forcing; the TF gate then validates that these objectives + the new corpus actually produce source binding before any on-policy work begins.

## Stage 3 — CAS-DAgger / on-policy training

**Gated on Stage 2 validation.** If Stage 2 fails, Stage 3 does not start.

**Goal:** close the TF→free-decode gap by training on the model's own outputs.

**Losses** (jointly weighted; specific weights TBD per smoke run, NOT tuned against the broader B3 pack):

- `L_lm_gold` — LM cross-entropy under teacher forcing (gold prefix)
- `L_lm_model` — LM cross-entropy under model's own corrupted prefix (DAgger roll-in)
- `L_slot` — slot-type cross-entropy
- `L_pointer` — typed source-span pointer loss (existing per-position copy loss + new span-coherence term)
- `L_contrastive_margin` — source-position contrastive: correct source position scores higher than hard-negative source positions by margin m
- `L_coverage` — coverage loss penalizing the model for pointing at the same source position twice when target has distinct identifiers
- `L_unlikelihood` — penalize repeated stage_clause / phrase patterns within a generated sequence

**DAgger schedule:** linear ramp on model-prefix mix from 0% → 50% over the 1000 training steps. Cap at 50% per Huszár 2015's biased-gradient critique.

**Smoke gates during training** (catch early failures):
- Per-batch `train_progress` must include `loss_lm_gold`, `loss_lm_model`, `loss_pointer`, `loss_contrastive_margin`, `loss_unlikelihood`. All must remain finite.
- At step 250 / 500 / 750 / 1000: canary on dev-bucket records — phrase loops, triviality.

## Stage 4 — Fresh free-decode gate (the proof gate)

**Eval packs (TWO required per audit 2026-05-12):**

| Pack | Path | Purpose |
|---|---|---|
| **Frozen broader B3 24-pack** | `cas-synthetic/data/eval/broader_b3_eval_pack_2026_05_12.jsonl` | Continuity with the bar B3 failed (0/37). Apples-to-apples with B3 baseline. Locked since 2026-05-12. |
| **Sibling source-swap eval pack** | `cas-synthetic/data/eval/rpm_copy_grounding_v2_source_swap_eval.jsonl` | Source-swap conditionality cannot be measured on the broader B3 pack alone — it has no paired source-swap records. Generated in Stage 1; held out from all training. |

**Both packs must pass for Stage 4 to validate.** Failure on either falsifies Candidate E.

**Locked first-proof gates:**

*On the frozen broader B3 24-pack (continuity gates):*

| Gate | Threshold | Notes |
|---|---|---|
| Exact fresh identifier recovery | **≥50%** | Bounded-regex positional match — same metric as broader B3 runner |
| Free-decode / TF recovery ratio | **≥70%** | Closes the exposure-bias gap |
| Non-rpm copy emissions | **= 0** | Same leakage guard as broader B3 Gate 3 |
| Loop-to-cap rate | **= 0** | No record may reach max_new_tokens via phrase-loop attractor (Gate 6 strengthened) |

*On the sibling source-swap eval pack (conditionality gate):*

| Gate | Threshold | Notes |
|---|---|---|
| Source-swap conditionality | **≥85%** | For paired records (same EN target, different source identifiers), the model's output identifier must swap with the source. Per-record: success if generated identifier matches the source-position-correct identifier, not the other pair member's identifier. |

**Promotion-later gate:** ≥80% fresh exact recovery on broader B3 pack AND ≥90% source-swap conditionality on sibling pack. This is the production-ready bar; Stage 4 only needs the first-proof thresholds above.

**Kill rule:** if **any** of the five gates fails on **either** pack, Candidate E falsifies. No retuning. Surface failure analysis; reopen deeper architectural review (Tree Decoder, Two-Pass) at that point.

## Anti-tuning + anti-overclaim discipline (carried forward)

- **Do not tune any threshold / loss weight / hparam against the 24-pack.** The 24-pack is the gate, not the training signal.
- **TF improvement is not success.** Free-decode on fresh records is the only headline metric.
- **No success claim from training-adjacent or training-overlapping records.** Verify suffix-partition guarantee at every stage.
- **No deterministic output repair, no symbolic patcher.** The learned model must produce the right identifier on its own.
- **No DAgger until TF grounding passes.** Stage 3 is gated on Stage 2.
- **No D2 / D3 / additional architecture-hopping** while E is in flight.
- **Sample-read every batch of records before promotion.** Stats narrow the search; samples decide.

## Cost projection

| Stage | Wall-clock | Pod $ |
|---|---|---|
| Pre-Stage-1 audit (full-span labelling check) | 1 hr laptop | $0 |
| Stage 1 — `rpm_copy_grounding_v2` SDG (train/dev/test + source-swap pack) | 1 week laptop | $0 |
| Stage 1 — sample-read review | 1 day | $0 |
| Stage 2a — LM+FR+slot warmup retrain | ~half day | ~$0.40 |
| Stage 2b — add copy/span/contrastive/coverage TF training + TF grounding gates | ~half day | ~$0.60 |
| Stage 3 — CAS-DAgger on-policy training | 1 day | ~$2-3 |
| Stage 4 — broader B3 + source-swap eval | minutes | ~$0.15 |
| **Total** | **~2 weeks** | **~$5** |

Cumulative would reach ~$8.55 of $60 if Stage 4 completes.

## Build order (sequenced, each gated)

1. **Pre-Stage-1 audit** (`docs/working/candidate_e/audit_label_coverage_2026_05_12.md`) — laptop, $0
2. **Stage 1 SDG (train/dev/test + source-swap pack) + sample-read review** — laptop, $0, surface samples for user approval before pod
3. **Stage 2a — LM+FR+slot warmup retrain** — pod, ~$0.40, surface internal sanity check before promoting to 2b
4. **Stage 2b — add copy/span/contrastive/coverage TF training + TF gates** — pod, ~$0.60, surface gate verdict for user adjudication
5. **Stage 3 CAS-DAgger** — pod, ~$2-3, only if Stage 2b's TF gate passes
6. **Stage 4 dual-pack eval (broader B3 + source-swap)** — pod, ~$0.15, single verdict

Each stage's kill/validate gate is locked in this doc. No tuning between stages. No bundle-authorization; each stage requires explicit user OK after surface.

## What's explicitly out of scope

- Tokenizer rewrite (falsified)
- Deterministic CAS renderer / output patcher (rejected)
- Tree Decoder / Two-Pass / Compiler-in-Loop (deferred; only if Candidate E falsifies)
- Three-instance dialectic (deferred per memory `project_three_instance_dialectic_proposal_2026_05_04.md`; requires base model fresh-records accuracy >0% first)
- Foreign LLM distillation / RLHF / retrieval-augmentation (hard constraint violation)
- Scale increase / longer training schedule (orthogonal; failure is binding, not capacity)

## Companion files

- `docs/working/broader_b3_eval/broader_b3_eval_findings.md` — the failure this candidate addresses
- `docs/working/candidate_d1/smoke_report.json` — the most recent precursor failure
- `docs/working/simplex_mvp_staged_training_canonical_recipe_2026_05_12.md` — the B1/B2/B3 schedule E mirrors
- `docs/future/cas_self_training_recursive_gated_successor_2026_05_12.md` — long-horizon target downstream of E
- Memory: `project_b3_broader_eval_falsified_2026_05_12.md`, `feedback_cas_best_lm_six_properties.md`, `feedback_no_foreign_architecture_cas_only.md`, `feedback_real_metric_is_samples.md`

## Audit checklist for reviewer (Codex or user)

Before authorizing Stage 1, confirm:

- [ ] Diagnosis is correctly stated (binding rule failure; not tokenizer; not architecture)
- [ ] Rejected hypotheses are correctly labeled and rationaled (currently 8 rows in the rejected table)
- [ ] Six structural properties of `rpm_copy_grounding_v2` are sufficient (or flag additions)
- [ ] Stage 2 is split into E2a (LM+FR+slot warmup) and E2b (copy/span/contrastive/coverage added); TF gate applies after E2b
- [ ] Stage 2b TF gates (≥80% / ≥85% / ≥90% / 0) are correctly calibrated
- [ ] Stage 3 loss list is complete (or flag missing terms)
- [ ] Stage 4 requires BOTH the broader B3 24-pack AND the sibling source-swap eval pack to pass
- [ ] Stage 1 corpus paths put training data under `data/path_d/` and eval packs under `data/eval/`
- [ ] Broader-B3 reserved-eval blacklist (15 bodies, 3-/4-/5-digit) is explicit and Stage 1 SDG enforces exclusion across all 5 artifacts
- [ ] Stage 2b source-swap gate references the dedicated `rpm_copy_grounding_v2_source_swap_dev.jsonl` artifact (not a subset of the dev pack)
- [ ] Anti-tuning rules are intact (no tuning against the 24-pack)
- [ ] Cost projection is realistic
- [ ] Companion files exist
- [ ] Pre-Stage-1 audit is named and gates Stage 1
