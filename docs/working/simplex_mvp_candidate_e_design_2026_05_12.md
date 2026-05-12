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

1. **Disjoint identifier suffix partition.**
   - Train suffixes: 4-digit bodies in `0000-7999` AND 3-digit bodies in `000-799` AND 5-digit bodies in `00000-79999`.
   - Dev suffixes: 4-digit `8000-8999`, 3-digit `800-899`, 5-digit `80000-89999`.
   - Test suffixes: 4-digit `9000-9999`, 3-digit `900-999`, 5-digit `90000-99999`.
   - Eval (the frozen broader B3 24-pack) must use only test-bucket suffixes. Audit eval pack against this partition before Stage 4.

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

6. **Full-span labelling** (conditional on pre-Stage-1 audit).
   - If audit confirms current labels are head-only, fix the collator/anchor derivation to assign STAGE_VAR (or appropriate slot type) on EVERY sub-token of each identifier, with `typed_slot_source` pointing to the *corresponding* sub-token in the source.
   - If audit confirms full-span: no change needed.

**Stage 1 deliverable:** `cas-synthetic/data/eval/rpm_copy_grounding_v2.jsonl` (size TBD; target ~2000-3000 records to provide counterfactual / hard-negative variance) + a sister non-rpm corpus of comparable size to maintain category balance.

**Stage 1 build review (before pod work):**
- Sample-read 20 records per template variant to confirm fluency and structural correctness.
- Verify hard negatives are actually present (regex check).
- Verify counterfactual pairs have matching EN structure with different identifiers.
- Verify suffix partition holds (no train record uses dev or test suffix; no eval pack record uses train suffix).

## Stage 2 — B2 retrain + TF grounding probe

**Goal:** confirm `rpm_copy_grounding_v2` teaches the binding rule under teacher forcing before committing to on-policy.

**Build:**
- Warm-start from B2's `ckpt_final.pt`. B2 was the strict-validate stage (slot stable, no leakage); use it as the base because B1's regression guard already passed there and we want to test whether the new corpus + same training procedure produces binding.
- Train through B2-equivalent (LM + FR + slot, no copy yet) for 1000 steps on the new corpus.
- Then train through B3-equivalent (full preset + hard typed-fiber emission) for 1000 steps.

**Locked gates** (read at post-training TF eval on FRESH records — dev-bucket suffix):

| Gate | Threshold | Rationale |
|---|---|---|
| TF fresh source recovery | **≥80%** | If the data wedge teaches binding, TF should recover the right identifier almost always (TF has the correct prefix; the only question is "did the model learn to read the source") |
| Source-swap conditionality | **≥85%** | Same EN target, swap source identifiers → output should swap. Isolates binding from shape memorization. |
| Slot F1 for copy-bearing slots | **≥90%** | Slot head correctly identifies typed positions in fresh records |
| Non-rpm leakage | **0** | Same guard as B2/B3: STAGE_VAR slot never fires on non-rpm inputs |

**Kill rule:** if **any** of the four gates fails, stop. **In particular, if TF fresh recovery stays around 30%, the data/labels are still wrong** — fix the wedge before Stage 3. **Do not run DAgger on a model that hasn't learned binding under TF.**

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

**Eval pack:** the frozen broader B3 24-pack at `cas-synthetic/data/eval/broader_b3_eval_pack_2026_05_12.jsonl`. Same pack B3 failed (0/37). Same 7 locked gates as the prior broader eval plus the binding-specific gates.

**Locked first-proof gates** (all must hold):

| Gate | Threshold | Notes |
|---|---|---|
| Exact fresh identifier recovery | **≥50%** | Bounded-regex positional match — same metric as broader B3 runner |
| Free-decode / TF recovery ratio | **≥70%** | Closes the exposure-bias gap |
| Source-swap conditionality | **≥85%** | Eval pack must be regenerated with source-swap pairs OR use a sibling eval pack |
| Non-rpm copy emissions | **= 0** | Same leakage guard as broader B3 Gate 3 |
| Loop-to-cap rate | **= 0** | No record may reach max_new_tokens via phrase-loop attractor (Gate 6 strengthened) |

**Promotion-later gate:** ≥80% fresh exact recovery. This is the production-ready bar; Stage 4 only needs ≥50%.

**Kill rule:** if any of the five gates fails on the broader B3 pack, Candidate E falsifies. No retuning. Surface failure analysis; reopen deeper architectural review (Tree Decoder, Two-Pass) at that point.

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
| Stage 1 — `rpm_copy_grounding_v2` SDG | 1 week laptop | $0 |
| Stage 1 — sample-read review | 1 day | $0 |
| Stage 2 — B2 retrain + TF grounding probe | 1 day | ~$1.50 |
| Stage 3 — CAS-DAgger training | 1 day | ~$2-3 |
| Stage 4 — broader B3 eval + new gates | minutes | ~$0.10 |
| **Total** | **~2 weeks** | **~$5** |

Cumulative would reach ~$8.55 of $60 if Stage 4 completes.

## Build order (sequenced, each gated)

1. **Pre-Stage-1 audit** (`docs/working/candidate_e/audit_label_coverage_2026_05_12.md`) — laptop, $0
2. **Stage 1 SDG + sample-read review** — laptop, $0, surface samples for user approval before pod
3. **Stage 2 retrain + TF gates** — pod, ~$1.50, surface report for user gate adjudication
4. **Stage 3 CAS-DAgger** — pod, ~$2-3, only if Stage 2 passes
5. **Stage 4 fresh free-decode gate** — pod, ~$0.10, single verdict

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
- [ ] All four rejected hypotheses are correctly labeled and rationaled
- [ ] Six structural properties of `rpm_copy_grounding_v2` are sufficient (or flag additions)
- [ ] Stage 2 TF gates (≥80% / ≥85% / ≥90% / 0) are correctly calibrated
- [ ] Stage 3 loss list is complete (or flag missing terms)
- [ ] Stage 4 fresh-decode gates match Codex's locked criteria
- [ ] Anti-tuning rules are intact (no tuning against the 24-pack)
- [ ] Cost projection is realistic
- [ ] Companion files exist
- [ ] Pre-Stage-1 audit is named and gates Stage 1
