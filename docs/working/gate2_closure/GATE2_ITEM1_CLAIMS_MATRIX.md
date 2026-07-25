# Gate 2 Item 1 — Model-by-Revision-by-Evidence-Tier Claims Matrix

## Status block

| Field | Value |
|---|---|
| **Addresses (does NOT close)** | Gate 2 item 1 — "Publish a model-by-revision-by-evidence-tier matrix reconciling every v1.0, v2.1, investor, engineering, and archived claim. Remove blanket six-model wording unless raw evidence supports the exact rows." (`docs/working/CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:189-191`) |
| **What it actually closes** | Clause 1 (publish the matrix) and the v2.1 / investor / engineering slices of clause 2, now extended to the v1.0 and archived slices in §4.6. Clause 3 ("Remove blanket six-model wording") is **unmet** — no live surface was edited; see §9.1. |
| **Date** | 2026-07-24 (revision 2, adversarial-review corrections applied) |
| **Item exit state** | **PARTIAL — NOT CLOSED.** See §9. |
| **Branch this was built on** | `codex/cascompass-legal-live-source` (HEAD) |
| **Compute performed** | None. This is a document-and-artifact reconciliation only. |
| **Git writes performed** | None. |

### Revision note — 2026-07-24 revision 2

An adversarial review re-ran the §7 negatives by **filename enumeration** (`git ls-tree -r --name-only <branch>`) instead of string grep. Five findings changed the document, **three of them in the direction of more evidence, not less**:

1. `experiment/cas-probe-pythia:…/stage7_foundation_layer6_ablation_report_20260517.json` **exists.** Revision 1 called the Pythia-160M F28 causal result "markdown only / no machine-readable JSON located." That was wrong; the JSON carries a preregistered `decision_gates` block. §4.1 row 1 and §7 gap 7 are corrected. (Root cause: revision 1 grepped the literal string `0.0323`, but the JSON stores `0.03225806451612903`; the markdown rounds it.)
2. The strongest Pythia-160M **F28** text control is `tfidf_char_3_5` — a **character** 3-5-gram arm — not word-level. That row is `control_proof: **present**`, not `partial`.
3. The strongest Pythia-160M **40E** text control is also `tfidf_char_3_5` (50.089%). Revision 1 wrote "~50.1% word-level." Same correction: `control_proof: **present**`.
4. `§5.2`'s "none found this pass" rows were wrong for two prohibited phrases; §5.2 now records 14 live hits for one of them and 7 for the other, with file:line.
5. A Pythia-160M 40E numeric conflict (89.799% vs 91.719%) was propagated unreconciled. It is now §5.3 item 3 with both artifacts named.

### Explicit claim-state line

**Real:** the numeric readout, ablation, and weight-geometry values in §4 — every one was recomputed or re-read from raw JSON in this pass and reproduces exactly.
**Simulated:** nothing in this document.
**Accepted:** nothing. No standing `ACCEPT` exists anywhere in the project record.
**Withdrawn:** the GPT-NeoX-20B Stage 9 40E `ACCEPT`; `accept_revival_allowed: false`.
**Unavailable:** the GPT-NeoX-20B model revision; model-specific F28 causal evidence for four of six model points; 40E evidence for four of six; weight geometry for five of six; any character-level surface control **at 20B** (both Pythia-160M axes now have one — see revision note); cross-seed variation everywhere; the locked Pythia-160M F28 activation binary; any dated preregistration artifact for the 20B ≥30 pp / ≤65% ablation gate (§7 gap 14).
**Open / not licensed:** every blanket six-model claim listed in §5; the prompt-injection W0 result; universality; 300B.
**Flagged for human review:** three internal inconsistencies (§5.3 — two count errors plus one unreconciled Pythia-160M 40E numeric conflict) and one live model-provenance defect (§8).

This document licenses nothing. It is a claim-control document, not an independent replication.

---

## 1. Vocabulary lock

Two vocabularies are reused verbatim from `project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/04_AMAZON_INTERNAL_DRAFT_DO_NOT_SEND/CAS_HARNESS_AMAZON_CLAIM_EVIDENCE_MANIFEST_20260721.json` rather than inventing new words:

- `claim_status_vocabulary` (verified present in that file): `ACCEPT`, `FLAG_FOR_HUMAN_REVIEW`, `LICENSED`, `NOT LICENSED`, `OPEN`, `present`, `unavailable`.
- `evidence_class`: `DEMONSTRATED_RESEARCH_RESULT`, `DIAGNOSTIC_OR_APPARATUS_EVIDENCE`, `ENGINEERING_OBJECTIVE`.

Two fields are added because the roadmap exit clause requires them and no existing document carries them:

- `control_proof` ∈ `{present, partial, unavailable}` — `present` only when a same-split surface control ran **and** included a character-level n-gram arm.
- `STATUS` ∈ `{supported, overstated, unavailable, withdrawn}` — the per-claim verdict required by this deliverable.

`supported` means: the exact wording, scoped to the exact model and revision named in the row, is backed by a located raw artifact whose numbers reproduce. It does **not** mean licensed.

---

## 2. Branch-split warning — read before the matrix

Claim documents and raw evidence live on **disjoint, unmerged branches**. Verified this pass with `git merge-base --is-ancestor`:

| Branch | Is it an ancestor of HEAD? | What it holds |
|---|---|---|
| `master` | **No** | All GPT-NeoX-20B 40E/F28 raw artifacts; `pythia160m_gate1/` regenerated packets |
| `experiment/cas-probe-pythia` | **No** | Every non-160M model revision; STAGE8/14/15/16 probe reports; `stage14_weight_geometry_alignment_20260519.json`; the Stage 7 160M markdown reports |
| `codex/claims-remediation-20260719` (commit `d6069513`) | **No** | The 2026-07-19 claim-evidence matrix and the withdrawal/superseded banners |
| HEAD (`codex/cascompass-legal-live-source`) | — | The spec sheets, executive summary, synopsis, review brief — i.e. the **claims**, with none of the above evidence |

`git cat-file -t HEAD:docs/legal_drafts_20260607/CAS_HARNESS_CLAIM_EVIDENCE_MATRIX_20260719.md` → `fatal: path ... does not exist in 'HEAD'`.
`git branch -a --contains d6069513` → `codex/claims-remediation-20260719` only.

**Consequence, stated plainly: no single checkout can reproduce one *headline* claim row end to end today.** The Gate 2 exit requirement "independently reproducible raw evidence" is **NOT SATISFIED** by the current tree. Resolving this is a merge/publication decision outside item 1's scope.

**Scope qualifier (added revision 2, so §2 and §7.1 do not contradict each other).** The statement above is about the headline evidence rows in §4.4. It is not literally true of *every* artifact: §7.1 establishes that two Stage 7 **smoke**-capture artifacts (`stage7_foundation_pilot_smoke_activations_manifest_20260517.json`, `stage7_foundation_pilot_smoke_activations_20260517.npz`) are present at HEAD with exactly matching recorded SHA-256, i.e. a genuine partial end-to-end path at HEAD. That path covers `n_records: 56` across 28 classes — a smoke fixture, not the 2,352-record F28 evaluation set — so it reproduces no claim row in §4.4. Both statements stand: a real HEAD-reachable hash-verified path exists, and it is not sufficient to reproduce any headline row.

---

## 3. Model identity table (seven model points, not six)

| Model id | `model_revision` | Where the revision is recorded | Reachable from HEAD? |
|---|---|---|---|
| `EleutherAI/pythia-160m` | `50f5173d932e8e61f858120bcb800b97af589f46` | `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_pilot_smoke_activations_manifest_20260517.json` (on disk, field `model_revision`) | **Yes** |
| `EleutherAI/pythia-1b` | `f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2` | `experiment/cas-probe-pythia:.../stage8_pythia1b_activations_manifest_20260517.json` | No |
| `EleutherAI/pythia-2.8b` | `2a259cdd96a4beb1cdf467512e3904197345f6a9` | `experiment/cas-probe-pythia:.../stage14_pythia28b_activations_manifest_20260518.json` | No |
| `allenai/OLMo-1B-hf` | `aee7752d9c08ee4775e9b0091426d8410e8f6a89` | `experiment/cas-probe-pythia:.../stage15_olmo1b_activations_manifest_20260519.json` | No |
| `Qwen/Qwen2.5-1.5B` | `8faed761d45a263340a0528343f099c05c9a4323` | `experiment/cas-probe-pythia:.../stage16_qwen15b_activations_manifest_20260519.json` | No |
| `Qwen/Qwen2.5-1.5B-Instruct` | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` | `docs/working/typed_probe_gate_runlog.md:26` | **Yes** |
| `EleutherAI/gpt-neox-20b` | **`unavailable`** — literal `null` | `master:.../gpt_neox_20b_stage9_original_40e_capture_metadata_20260527.json` field `"model_revision": null`; corroborated at `master:.../S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json` field `model.model_revision = None` | No |

Two identity facts that blanket wording erases:

1. **"Qwen" is ambiguous.** `Qwen2.5-1.5B` (rev `8faed761…`, F28 readout 82.015%) and `Qwen2.5-1.5B-Instruct` (rev `989aa798…`, typed readout 91.566%) are different models with different revisions and different results. The "six model points" phrase has never included the Instruct variant.
2. **The 20B revision cannot be recovered.** `"model_revision": null` is baked into the only capture metadata. It must not be filled in by looking up a plausible HuggingFace commit — that would be fabrication. It reads `unavailable`.

Every model point above shares one frozen English synthetic fixture: `input_sha256 = 3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250`, verified identical in all five stage manifests.

---

## 4. The claims matrix — one row per (claim, model, revision)

Claim wording is quoted verbatim and trimmed. `f:l` = file and line, verified by direct read on 2026-07-24.

### 4.1 The blanket six-model causal claim

| # | Claim wording (quoted, trimmed) | Where it appears (`file:line`) | Model | Revision | Evidence tier | Raw artifact | STATUS |
|---|---|---|---|---|---|---|---|
| 1 | "**Causal role** — ablating the structure collapses readout … head-level + **sparse MLP-neuron-cover (112/112, p < 10⁻³³)** with necessity *and* sufficiency" — asserted under the header "**What is proven (LICENSED).** Across **six open-weight model points in three architecture families**" | `docs/working/cas_harness_executive_summary_20260630.md:12,14` | `EleutherAI/pythia-160m` | `50f5173d…` | F28 subspace-ablation; sparse MLP-neuron cover | **Machine-readable JSON located (revision-2 correction):** `experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_layer6_ablation_report_20260517.json` → `layer 6`; `probe_retrained_for_ablation.test.acc 0.7857142857142857`; `foundation_subspace_ablation.test.acc 0.03571428571428571` (= exact 1/28 chance); `n_random_controls 30`; `random_complement_controls {mean_disruption 0.0, max_disruption 0.0, one_sided_empirical_p_random_ge_foundation 0.03225806451612903}`; `status "FOUNDATION_SUBSPACE_CAUSAL_FOR_PROBE_READOUT"`; **preregistered** `decision_gates {chance_accuracy 0.03571428571428571, foundation_ablated_acc_max 0.08, random_ge_foundation_empirical_p_max 0.05}` — all three met. `activations_sha256 d2fc03ad…`, so the JSON is bound to the same locked binary, which remains **`unavailable`** (§7 gap 8). Markdown companion `…/STAGE7_FOUNDATION_ABLATION_REPORT_20260517.md` rounds p to `0.0323` | **supported at Pythia-160M scope only** — the subspace-ablation clause reproduces exactly against a preregistered gate; the surrounding **six-model** scope of the sentence is **overstated** (rows 2-6), and the neuron-cover clause is row 7 |
| 2 | same as #1 | `docs/working/cas_harness_executive_summary_20260630.md:12,14` | `EleutherAI/pythia-1b` | `f73d7dcc…` | F28 causal | **`unavailable`** — no ablation report on any branch | **overstated** |
| 3 | same as #1 | `docs/working/cas_harness_executive_summary_20260630.md:12,14` | `EleutherAI/pythia-2.8b` | `2a259cdd…` | F28 causal | **`unavailable`** | **overstated** |
| 4 | same as #1 | `docs/working/cas_harness_executive_summary_20260630.md:12,14` | `allenai/OLMo-1B-hf` | `aee7752d…` | F28 causal | **`unavailable`** | **overstated** |
| 5 | same as #1 | `docs/working/cas_harness_executive_summary_20260630.md:12,14` | `Qwen/Qwen2.5-1.5B` | `8faed761…` | F28 causal | **`unavailable`** | **overstated** |
| 6 | same as #1 | `docs/working/cas_harness_executive_summary_20260630.md:12,14` | `EleutherAI/gpt-neox-20b` | **`unavailable`** | 40E subspace ablation | `master:…/gpt_neox_20b_stage9_original_40e_subspace_ablation_report_20260528T0155Z.json` — `packet_decision: "not_applicable_ablation_diagnostic_only"`; `important_limit: "This is a causal-subspace diagnostic report, not a packet verdict."` Preregistered gate (≥30 pp drop or ≤65% floor) **missed** at 28.7277 pp / 66.897% | **overstated** |
| 7 | "**sparse MLP-neuron-cover (112/112, p < 10⁻³³)**" scoped to six models | `docs/working/cas_harness_executive_summary_20260630.md:14`; `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:321`; `docs/working/cas_harness_synopsis_20260630.md:118` | `EleutherAI/pythia-160m` **only** | `50f5173d…` | Sparse neuron-cover, 28 classes × 4 conditions | `docs/working/cas_harness_original_closure_methodology_20260526.md:192,200-203` and `docs/working/paper_b_causal_localization_draft_outline_20260523.md:52` both attribute it to the Pythia-160M comparator (`:192` "Pythia-160M comparator: 28/28 wins, p = 3.7×10⁻⁹"; `:203` "Bidirectional, both directions clean of random — this is the headline 112/112 result"). **Revision-2 correction to the supporting sentence:** revision 1 said "the only located cover JSON … candidate discovery, not validated matched ablation." Filename enumeration of `master` shows **four** cover artifacts, and one *is* a matched ablation: `master:…/pythia160m_gate1/pythia160m_stage9_40e_neuron_covers.json` (`"cover_discovery_tier": "candidate-readout-weight-v0"`, caveat "candidate-only until matched ablation validates targeted drops"); `master:…/pythia160m_gate1/pythia160m_activation_cover_ablation_report.json` (`ablation_mode "activation_level_train_mean_replacement"`, layer 3, clean acc `0.376786`, label-specific cover drop `0.054762` vs same-size random `max_drop_from_clean 0.005953` over 20 trials and wrong-cover drop `0.003572`; `label_drop_exceeds_random_max: true`; `important_limit`: "activation-level post-hoc ablation on captured vectors … not yet a live forward-pass hook intervention"); `master:…/pythia160m_gate1/pythia160m_stage9_40e_subspace_ablation_report.json`; `master:…/gpt_neox_20b_stage9_original_40e_neuron_covers_top8_20260528T0210Z.json`. So matched-control cover ablation **does** exist for Pythia-160M — at activation level, not weight level. The row's conclusion is unchanged: every one of these is Pythia-160M or 20B, none is the other four model points | **overstated** (as a six-model claim; the underlying cover work is Pythia-160M-scoped and stronger than revision 1 stated) |

### 4.2 The blanket scale/axis claims

| # | Claim wording (quoted, trimmed) | Where it appears (`file:line`) | Model | Revision | Evidence tier | Raw artifact | STATUS |
|---|---|---|---|---|---|---|---|
| 8 | "Validated **up to 20B parameters on two cognitive axes**" | `docs/working/cas_harness_executive_summary_20260630.md:17` | `gpt-neox-20b` | **`unavailable`** | F28 + 40E | Prohibited verbatim by the 2026-07-19 matrix rule "'The 20B chain closes on two axes' is prohibited. Use the precise 20B row." (`d6069513:…/CAS_HARNESS_CLAIM_EVIDENCE_MATRIX_20260719.md:99`) | **overstated** |
| 9 | "three independent model families across six model points, with a 20B scale extension closed on two cognitive axes" | `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:28` | all seven | mixed | aggregate | same prohibition | **overstated** |
| 10 | "across six model points and three architecture families … The η → ε bridge conditions next-token likelihood…" | `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:67` | all six | mixed | F28 readout + bridge | Readout + bridge **do** replicate on six F28 points; the surrounding paragraph is what fails (see §5.1) | **overstated** |
| 11 | "closed in May 2026 on the **presence, causal role, and conditionability** of the structure across six model points, two cognitive axes at 20B" | `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:83` | all six | mixed | aggregate | Prohibited verbatim: "'Presence, causal role, and conditionability across six models' is prohibited." (`d6069513:…MATRIX_20260719.md:94`) | **overstated** |
| 12 | "**six models in three architecture families on two cognitive axes at 20B** … every verdict is a typed classification read from hidden states and validated causally" | `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:522` | all six | mixed | aggregate | Prohibited verbatim: "'Every verdict is validated causally' is prohibited." (`d6069513:…MATRIX_20260719.md:100`) | **overstated** |
| 13 | "The probing chain **closed in May 2026** on three things: the **presence**, the **causal role**, and the **conditionability** of that structure, across six model points." | `docs/working/cas_harness_synopsis_20260630.md:24` | all six | mixed | aggregate | same prohibition as #11 | **overstated** |
| 14 | "Validated claim spans **six model points across three architecture families**, with a **20B scale extension closed on two cognitive axes**." | `docs/working/cas_harness_synopsis_20260630.md:85` | all six | mixed | aggregate | same prohibition as #8 | **overstated** |
| 15 | "CAS-shaped structure is linearly readable from model activations and is causally load-bearing, across six model points and three families up to 20B." | `docs/working/cas_harness_amazon_review_brief_20260615.md:54` | all six | mixed | aggregate | Item #1 on the prohibited-shorthand list: "causally validated across six models" (`project_handoffs/…/CAS_HARNESS_AMAZON_TECHNICAL_EVALUATION_SPEC_20260721.md:426`) | **overstated** |
| 16 | "across six model points and three architecture families … The η → ε bridge conditions next-token likelihood…" | `noetic-compass-scaffold/noetic-compass/docs/marketing/CAS_HARNESS_SPEC_SHEET_v2_1_INVESTOR_EXTERNAL_NDA_20260604.md:146` | all six | mixed | aggregate | Withdrawal banner exists **only** in `d6069513`; file head on disk (lines 1-8) carries no withdrawal notice | **overstated** |
| 17 | "The probing chain closed in May 2026 across six model points, two cognitive axes at 20B" | `noetic-compass-scaffold/noetic-compass/docs/marketing/CAS_HARNESS_SPEC_SHEET_v2_1_INVESTOR_EXTERNAL_NDA_20260604.md:158` | all six | mixed | aggregate | same as #16 | **overstated** |

### 4.3 The specific numeric claims

| # | Claim wording (quoted, trimmed) | Where it appears (`file:line`) | Model | Revision | Evidence tier | Raw artifact | STATUS |
|---|---|---|---|---|---|---|---|
| 18 | "GPT-NeoX-20B 40-Element readout **95.625%**" | `docs/working/cas_harness_executive_summary_20260630.md:13` | `gpt-neox-20b` | **`unavailable`** | 40E held-out readout | `master:…/gpt_neox_20b_stage9_original_40e_probe_eval_report_20260527.json` → `best_layer {layer: 2, test_acc: 0.95625, test_macro_f1: 0.9561734767543545}`, `n_train 3840`, `n_test 4480`, `train_test_group_overlap_count 0`. Recomputed: 4284/4480 = 95.625%, Wilson 95% [94.986, 96.186] | **supported** |
| 19 | "**95.625%** vs ~49% text baseline" (comparative framing) | `docs/working/cas_harness_executive_summary_20260630.md:13` | `gpt-neox-20b` | **`unavailable`** | 40E readout vs surface control | Same file. Controls block holds exactly two text arms: `CountVectorizer(1-2 grams)` 0.4924107142857143 and `HashingVectorizer(1-2 ngrams, 2^14 features)` 0.5 — **both word/token-level**. No `analyzer='char'` arm exists. `control_proof: partial` | **overstated** |
| 20 | "**107× signal-to-noise at 20B**" | `docs/working/cas_harness_executive_summary_20260630.md:14` | `gpt-neox-20b` | **`unavailable`** | 40E causal diagnostic | `master:…_subspace_ablation_report_20260528T0155Z.json` `primary_result`: `true_disruption 0.2872767857142857`, `random_same_rank_max_disruption 0.002678571428571419`, `random_same_rank_mean_disruption 0.0006808035714286175`. Recomputed: 0.2872767857 ÷ **max** = 107.25; ÷ **mean** = 421.97. The divisor is the random **max** and is not named in the claim; the sentence also omits that the preregistered gate was missed | **overstated** |
| 21 | "40-Element at GPT-NeoX-20B drops **95.625% → 66.897%** (28.73 pp), random-matched controls 0.068 pp mean — a **107× signal-to-noise ratio**. The pre-registered gate (≥30 pp drop / ≤65% floor) was **narrowly missed** … and documented" | `docs/working/cas_harness_synopsis_20260630.md:101` (**second sentence onward** — the line's opening clause is row 24) | `gpt-neox-20b` | **`unavailable`** | 40E causal diagnostic | Same artifact. Every number reproduces; the near-miss is disclosed; the divisor is still unnamed. The word "pre-registered" in this sentence is itself unsourced — see §7 gap 14 | **supported for the quoted span**, with the "pre-registered" attribution `unavailable` |
| 21b | "**Five axes collapse to exact chance under subspace ablation with clean random nulls.**" — the untrimmed opening clause of the same line as row 21 (revision-2 addition; revision 1 trimmed it off and inventoried nothing) | `docs/working/cas_harness_synopsis_20260630.md:101` | scope not stated in the sentence; sits inside a paragraph whose next sentence is about GPT-NeoX-20B | mixed | Multi-axis causal | Enumerated by filename on `experiment/cas-probe-pythia`. **Three** axes verified this pass as reaching exact chance, **all Pythia-160M**: Stage 3 noetic layer-3 (`pythia_ablation_layer3_20260515.json` → `probe_accuracy_unablated 0.8985507246376812` → `probe_accuracy_ablated 0.10144927536231885`, chance 1/10); Stage 6.5 role-bound layer-5 (`stage6_role_bound_layer5_ablation_report_20260516.json` → `noetic_subspace_ablation.test.acc 0.1`, `random_complement_controls.mean/max_disruption 0.0`, `one_sided_empirical_p_random_ge_noetic 0.03225806451612903`, `status "ROLE_BOUND_SUBSPACE_CAUSAL_FOR_PROBE_READOUT"`); Stage 7.1 foundation layer-6 (row 1, `0.03571428571428571` = exact 1/28). A fourth artifact, `stage9_factor_ablation_report_20260517.json` (`status "STAGE9_FACTOR_CHECK_FULL_PASS"`, layer 5), reports three sub-task ablations by **disruption** (domain `0.6729910714285714`, noetic `0.8154017857142858`, interaction `0.8729910714285714`) — accuracies not read this pass. A fifth artifact, `pythia_ablation_domain_layer5_n30_20260516.json` (Stage 4.1, `n_random_directions 30`, `n_permutations 10000`), reports per-class kept-rates, not an axis accuracy. **The five axes are never named at `:101`, and no single artifact enumerates all five.** Decisively: the 40-Element axis **at 20B does not collapse to chance** — `66.897%` against a `chance_baseline.accuracy 0.025` (row 20/21) | **overstated** — true of no more than the Pythia-160M axis family, adjacent to a 20B sentence that contradicts it |
| 22 | "Weight-geometry: 2.83× random (p = 0.0099)" | `docs/working/paper_b_causal_localization_draft_outline_20260523.md:56`; matrix cell "PASS reported: 2.83 times random; p=.0099" at `d6069513:…MATRIX_20260719.md:34` | `EleutherAI/pythia-2.8b` | `2a259cdd…` | Static weight geometry | `experiment/cas-probe-pythia:…/stage14_weight_geometry_alignment_20260519.json`. **Three** checks, `n_random 100`: `output_logit_lens_energy_fraction` 2.830531385486643 (p 0.009900990099009901); `output_weight_energy_fraction` 1.0621312951730846 (p 0.009900990099009901); `input_weight_energy_fraction` 1.0033496167943243 (**p 0.3465346534653465**). Artifact's own text: "At least one weight-geometry check is above random same-rank controls." No multiplicity policy stated | **overstated** (reports best-of-three as the result) |
| 23 | Stored verdict `ACCEPT` in the historical 20B 40E evidence packet | `master:…/gpt_neox_20b_stage9_original_40e_evidence_packet_20260528T0455Z.json` (packet bytes preserved) | `gpt-neox-20b` | **`unavailable`** | 40E packet | Amazon manifest records the retraction `withdrawn_stage9_40e_accept` with `accept_revival_allowed: false`. The corresponding F28 packet on master already reads `output.verdict = 'FLAG_FOR_HUMAN_REVIEW'` | **withdrawn** |

### 4.4 Underlying raw evidence rows (model × tier), verified this pass

Every accuracy below was recomputed from the raw `layer_scan` blocks; every Wilson interval was recomputed independently and matches the 2026-07-19 matrix to the digit.

| Model | Revision | Axis | Selected layer | correct/n_test | Accuracy | Wilson 95% (descriptive) | Strongest surface control + type | `control_proof` | Seeds | Split | `evidence_class` | `claim_status` | Raw artifact |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pythia-160m | `50f5173d…` | F28 | not stated in a JSON | 1848/2352 | 78.571% | [76.867, 80.182] | 49.7% text; "+11.9 pp over strongest surface-metadata" — word-level only | `partial` | 1 | fixed 1344/672/2352 | `DEMONSTRATED_RESEARCH_RESULT` | `present` | Markdown: `STAGE7_FOUNDATION_PILOT_REPORT_20260517.md` (experiment branch). JSON **`unavailable`** |
| pythia-1b | `f73d7dcc…` | F28 | 8 | 1938/2352 | 82.39796% | [80.806, 83.884] | `unavailable` in this artifact | `unavailable` | 1 | fixed 1344/672/2352 | `DEMONSTRATED_RESEARCH_RESULT` | `present` | `experiment/cas-probe-pythia:…/STAGE8_PYTHIA1B_PROBE_REPORT_20260517.json` |
| pythia-2.8b | `2a259cdd…` | F28 | 14 | 2020/2352 | 85.88435% | [84.419, 87.233] | `unavailable` in this artifact | `unavailable` | 1 | fixed 1344/672/2352 | `DEMONSTRATED_RESEARCH_RESULT` | `present` | `experiment/cas-probe-pythia:…/STAGE14_PYTHIA28B_PROBE_REPORT_20260518.json` |
| OLMo-1B-hf | `aee7752d…` | F28 | 16 | 2131/2352 | 90.60374% | [89.357, 91.718] | `unavailable` in this artifact | `unavailable` | 1 | fixed 1344/672/2352 | `DEMONSTRATED_RESEARCH_RESULT` | `present` | `experiment/cas-probe-pythia:…/STAGE15_OLMO1B_PROBE_REPORT_20260519.json` |
| Qwen2.5-1.5B | `8faed761…` | F28 | 11 | 1929/2352 | 82.01531% | [80.411, 83.515] | `unavailable` in this artifact | `unavailable` | 1 | fixed 1344/672/2352 | `DEMONSTRATED_RESEARCH_RESULT` | `present` | `experiment/cas-probe-pythia:…/STAGE16_QWEN15B_PROBE_REPORT_20260519.json` |
| gpt-neox-20b | **`unavailable`** | F28 | not stated | 2043/2352 | 86.8622% | [85.437, 88.168] | word-hash centroid 42.28% (legacy context) | `partial` | not stated | fixed | `DEMONSTRATED_RESEARCH_RESULT` | `FLAG_FOR_HUMAN_REVIEW` (`output.verdict` in packet) | `master:…/S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json` |
| pythia-160m | `50f5173d…` | 40E | not stated in a JSON | 4023/4480 | 89.799% | [88.878, 90.652] | ~50.1% word-level | `partial` | not stated | fixed | `DEMONSTRATED_RESEARCH_RESULT` | `present` | Prose/markdown; regenerated packet on `master:…/pythia160m_gate1/` |
| gpt-neox-20b | **`unavailable`** | 40E readout | 2 | 4284/4480 | 95.625% | [94.986, 96.186] | CountVectorizer(1-2 grams) 49.241%; HashingVectorizer(1-2 ngrams) 50.0% — **word-level only** | `partial` | 2026 | fixed by `metadata.split`; group overlap 0 | `DEMONSTRATED_RESEARCH_RESULT` | `FLAG_FOR_HUMAN_REVIEW` | `master:…_probe_eval_report_20260527.json` |
| gpt-neox-20b | **`unavailable`** | 40E causal | 2 | — | 95.625% → 66.897% (28.7277 pp) | n/a | random same-rank: mean 0.0681 pp, max 0.2679 pp | `present` (random-control axis only) | not stated | fixed | `DIAGNOSTIC_OR_APPARATUS_EVIDENCE` | `OPEN` (preregistered gate missed) | `master:…_subspace_ablation_report_20260528T0155Z.json` |
| pythia-2.8b | `2a259cdd…` | Static weight geometry | n/a | — | 2.8305× / 1.0621× / 1.0033× random | n/a | `n_random 100` same-rank random | `present` | not stated | n/a | `DIAGNOSTIC_OR_APPARATUS_EVIDENCE` | `present` | `experiment/cas-probe-pythia:…/stage14_weight_geometry_alignment_20260519.json` |
| Qwen2.5-1.5B-**Instruct** | `989aa798…` | Typed readout | 14 | 76/83 | 91.566% | not computed here (n=83) | TF-IDF 86.747%; CountVectorizer 83.1%; majority 13.3% — word-level | `partial` | 42 | seed-42 split, 551-record corpus `1970c1ab…` | `DEMONSTRATED_RESEARCH_RESULT` | `present` (typed coverage `PASS` only) | `docs/working/typed_probe_gate_runlog.md:12-38` |
| pythia-2.8b | `2a259cdd…` | F28 vs GoEmotions | 24 | — | F28 49.857%, +13.857 pp | n/a | GoEmotions rival 57.143%; scrambled F28 3.857% | `present` | not stated | not stated | `DEMONSTRATED_RESEARCH_RESULT` | **`BLOCKED_CAS_NOT_RECOVERABLE`** — preregistered +20 pp floor missed | `docs/working/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md:391` |
| Qwen-1.5B | not recorded | Prompt-injection W0 | 18 | — | hidden BA 89.6875% | n/a | later char n-gram 92.5-93.1% — **char-level, and it won** | `present` | not stated | not stated | `DEMONSTRATED_RESEARCH_RESULT` | **`OPEN / NOT LICENSED`** — initial PASS **withdrawn** | `docs/working/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md:393` |

### 4.5 Per-row uncertainty the 2026-07-19 matrix omits

Verified directly from the raw `layer_scan` blocks this pass:

1. **Every F28 row is one fixed split, one seed.** All four located reports carry `split {train: 1344, val: 672, test: 2352}` identically. No cross-validation, no cross-seed. The Wilson intervals are single-split descriptive binomial intervals and cover none of that.
2. **Pythia-1B and Pythia-2.8B layer choice was decided by the lacunarity tie-break, not validation accuracy.** Both report `selected_val_accuracy = 1.0`. Pythia-1B has **three** layers at val 1.0 (positions 8, 9, 10); Pythia-2.8B has **thirteen** (positions 14-26). Under `selection_rule: "highest validation 28-way Foundation accuracy; ties within 0.001 broken by lowest val lacunarity"`, the tie-break did the selecting. No Wilson interval covers this.
3. **Three of four selected layers are not the best test layer — favourable, and it evidences honest selection.** Pythia-1B: selected L8 0.82398 vs best L13 0.89328. Pythia-2.8B: selected L14 0.85884 vs best L13 0.88095. Qwen2.5-1.5B: selected L11 0.82015 vs best L28 0.91241. OLMo-1B is the exception — selected L16 *is* the best layer (0.90604). Record this; it is the strongest single piece of evidence that selection never saw test.
4. **The Pythia-1B hedge is unnecessary.** The 2026-07-19 matrix writes "about 1,938/2,352"; `0.8239795918367347 × 2352 = 1938.0` exactly.
5. **Pythia-2.8B weight geometry is best-of-three with no multiplicity policy.** See row 22.
6. **"107×" is against the random max, not the mean.** Against the mean it is 421.97×. Name the divisor or drop the ratio.

---

## 5. Blanket and aggregate claims raw evidence does NOT support

### 5.1 Deletion list with exact supported replacement wording

Each entry: the live wording, then the wording that **would** be supported by the rows in §4.4.

**`docs/working/cas_harness_executive_summary_20260630.md:12,14`**
- Live: "**What is proven (LICENSED).** Across **six open-weight model points in three architecture families** … **Causal role** — ablating the structure collapses readout (107× signal-to-noise at 20B); head-level + **sparse MLP-neuron-cover (112/112, p < 10⁻³³)** with necessity *and* sufficiency."
- Supported replacement: *"Foundation-28 held-out readout and the η→ε likelihood bridge replicated on six model points across three families. Causal evidence is not six-model. Subspace ablation closed on Pythia-160M F28 (78.6% → 3.57% exact chance; 30 same-rank random removals, disruption 0.0; empirical p = 0.0323). The sparse MLP-neuron-cover result (112/112 across 28 classes × 4 conditions, p < 10⁻³³) is Pythia-160M only. At GPT-NeoX-20B the 40-Element subspace ablation is a diagnostic (packet_decision: not_applicable_ablation_diagnostic_only) that missed its preregistered gate. Model-specific causal evidence for Pythia-1B, Pythia-2.8B, OLMo-1B and Qwen2.5-1.5B is unavailable."*

**`docs/working/cas_harness_executive_summary_20260630.md:13`**
- Live: "GPT-NeoX-20B 40-Element readout **95.625%** vs ~49% text baseline"
- Supported replacement: *"GPT-NeoX-20B 40-Element held-out readout 95.625% (4,284/4,480; descriptive Wilson 95% CI 94.986-96.186), against word-level text controls of 49.241% (CountVectorizer 1-2 grams) and 50.0% (HashingVectorizer 1-2 ngrams). No character-level n-gram control was run on this row, so control_proof is partial and no hidden-beats-all-surface claim is licensed."*

**`docs/working/cas_harness_executive_summary_20260630.md:14`** (107× fragment)
- Supported replacement: *"At 20B, removing the learned 40-Element readout subspace dropped accuracy 28.7277 pp (95.625% → 66.897%) against same-rank random controls of 0.0681 pp mean / 0.2679 pp max — a 107× ratio against the random **maximum** (421.97× against the mean). The preregistered gate required ≥30 pp drop or ≤65% floor and was missed on both arms."*

**`docs/working/cas_harness_executive_summary_20260630.md:17`**
- Live: "Validated **up to 20B parameters on two cognitive axes**"
- Supported replacement: *"At 20B, F28 readout (86.862%) and 40-Element readout (95.625%) both produced held-out results, and the 40-Element η→ε bridge passed at the likelihood level. The 40-Element preregistered causal gate remains OPEN after a near-miss, and the 20B evidence packet stands at FLAG_FOR_HUMAN_REVIEW. No 20B axis is closed."*

**`docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:28, :67, :83, :522`**
- Live phrases: "three independent model families across six model points, with a 20B scale extension closed on two cognitive axes"; "across six model points and three architecture families … The 20B chain closes on two cognitive axes."; "closed in May 2026 on the **presence, causal role, and conditionability** … across six model points"; "**six models in three architecture families on two cognitive axes at 20B** … every verdict is a typed classification read from hidden states and validated causally".
- Supported replacement for all four: *"Foundation-28 held-out readout and η→ε likelihood conditioning replicated on six model points across three architecture families on one frozen English synthetic fixture. Causal support is model- and tier-specific, not six-model. Static weight-geometry evidence exists only for Pythia-2.8B. No 20B axis is closed and no verdict is validated causally across models."*

**`docs/working/cas_harness_synopsis_20260630.md:24, :85`**
- Same replacement as the spec-sheet block. Note this file already reports the 20B near-miss correctly at `:101`; `:24` and `:85` contradict `:101` inside the same document.

**`docs/working/cas_harness_amazon_review_brief_20260615.md:54`**
- Live: "CAS-shaped structure is linearly readable from model activations and is causally load-bearing, across six model points and three families up to 20B."
- Supported replacement: *"CAS-shaped structure is linearly readable from model activations at six model points across three families up to 20B. That it is causally load-bearing is established model-specifically only on Pythia-160M (F28) and remains a missed-gate diagnostic at 20B (40-Element); it is unavailable on the other four model points."*

**`noetic-compass-scaffold/noetic-compass/docs/marketing/CAS_HARNESS_SPEC_SHEET_v2_1_INVESTOR_EXTERNAL_NDA_20260604.md:146, :158`**
- Same replacement, plus the file needs the withdrawal banner that currently exists only in `d6069513`.

**`docs/working/paper_b_causal_localization_draft_outline_20260523.md:56`**
- Live: "Weight-geometry: 2.83× random (p = 0.0099)."
- Supported replacement: *"Static weight geometry on Pythia-2.8B, three checks against 100 same-rank random controls: output logit-lens energy fraction 2.8305× random (empirical p = 0.0099); output weight energy fraction 1.0621× (p = 0.0099); input weight energy fraction 1.0033× (p = 0.3465, not above random). One of three checks is materially above control; no multiplicity correction was applied. This supports a bounded alignment-inspection claim, not generation control."*

### 5.2 Prohibited-phrase register (merged, deduplicated) and live violations

From `d6069513:…/CAS_HARNESS_CLAIM_EVIDENCE_MATRIX_20260719.md:92-100` and `project_handoffs/…/CAS_HARNESS_AMAZON_TECHNICAL_EVALUATION_SPEC_20260721.md:426-434`:

| Prohibited phrase | Source rule | Live violations found on disk |
|---|---|---|
| "two independent evidence tiers across six models" | matrix:92-93 | none found this pass |
| "Presence, causal role, and conditionability across six models" | matrix:94-96 | `CAS_HARNESS_SPEC_SHEET_current.md:83`; `cas_harness_synopsis_20260630.md:24` |
| "Not lab-specific, not corpus-specific, not language-specific" | matrix:97-98 | none found this pass |
| "The 20B chain closes on two axes" | matrix:99 | `CAS_HARNESS_SPEC_SHEET_current.md:28,67`; `cas_harness_synopsis_20260630.md:85`; `cas_harness_executive_summary_20260630.md:17`; v2.1 marketing sheet `:146,158` |
| "Every verdict is validated causally" | matrix:100 | `CAS_HARNESS_SPEC_SHEET_current.md:522` |
| "causally validated across six models" | Amazon spec:426 | `cas_harness_amazon_review_brief_20260615.md:54`; `cas_harness_executive_summary_20260630.md:12,14` |
| "works on any open-weight model" | Amazon spec:427 | none found this pass |
| "universal interpretability" | Amazon spec:428 | none found this pass |
| "validated at 300B" | Amazon spec:429 | none found this pass |
| "immutable WORM evidence" | Amazon spec:430 | not searched exhaustively this pass |
| "independently reproducible" when required raw artifacts are absent | Amazon spec:431 | **the whole tree is in violation** — see §2 |
| "prompt-injection detector" as a closed product capability | Amazon spec:432 | none found this pass |
| "controls model output" as a general capability | Amazon spec:433 | none found this pass |
| "first ACCEPT" / any standing `ACCEPT` | Amazon spec:434 | none live; historical packet bytes retain `ACCEPT` by design (§4.3 row 23) |

### 5.3 Flagged for human review — count inconsistencies, not evidence overstatements

Both directions of error appear. Neither is an overstatement of evidence; both are internal arithmetic that a reviewer will catch.

1. `noetic-compass-scaffold/noetic-compass/research/cas_probe/CAS_HARNESS_SPEC_SHEET_20260517.md:521` — "**Six closed evidence tiers** on two open models (Pythia-160M and Pythia-1B)" then enumerates **five** in the same sentence (detection; causally load-bearing readout; likelihood conditioning; clean structural factorization; framework-predictive validity). Note this "six" counts **tiers on two models**, not six model points; it must never be conflated with the six-model claim.
2. `docs/legal_drafts_20260607/CAS_provenance_preprint_updated.md:19` and `:97` — "Across **five model points** spanning three independent architecture families (EleutherAI Pythia/GPT-NeoX at four scales, AI2 OLMo, Alibaba Qwen)" while enumerating **six** (160M, 1B, 2.8B, 20B, OLMo, Qwen). Understating, in a patent-adjacent legal draft.

---

## 6. Banner-state correction

`docs/working/cas_harness_production_todo.md:2331-2332` asserts: "May/June historical sheets carry superseded/withdrawn banners; v2.1 and the consolidated current sheet are no longer claim authority."

**Verified false in the working tree.** Read directly on 2026-07-24:

- `…/marketing/CAS_HARNESS_SPEC_SHEET_v2_1_INVESTOR_EXTERNAL_NDA_20260604.md` lines 1-8 carry a v2.1-supersedes-v2.0 note only — **no withdrawal banner**. The string `WITHDRAWN FOR EXTERNAL RELIANCE` returns zero matches under `noetic-compass-scaffold/noetic-compass/` on disk; it exists only in `d6069513`.
- `…/research/cas_probe/CAS_HARNESS_SPEC_SHEET_20260517.md` lines 1-8 are YAML front matter with `status: Internal — pending IP attorney review before external use` — **no superseded banner**, contrary to the matrix's own governance rule at `d6069513:…MATRIX_20260719.md:90-91`.
- `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md` lines 1-10 carry no distribution-paused banner.
- Banners **are** present on the older sheets: v1.6, v1.7, v1.8, v1.9 (`SUPERSEDED 2026-06-04 …`) and v2.0 (`SUPERSEDED 2026-06-04 by v2.1`), each at line 1.

The discrepancy is recorded here, not silently patched into the todo. Anyone who treats `todo:2331-2345` as the current state will build on a false premise.

---

## 7. Gaps register — `unavailable`, with the exact search performed

Each of these is a valid negative result, re-runnable by an external reviewer.

1. **GPT-NeoX-20B model revision.** Searched `master:…/gpt_neox_20b_stage9_original_40e_capture_metadata_20260527.json` (`"model_revision": null`), the 40E probe eval report, the 40E subspace ablation report, and `master:…/S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json` (`model.model_revision = None`; only `model_key`/`model_type` populated). Corroborated by `project_handoffs/…/CAS_HARNESS_AMAZON_CLAIM_EVIDENCE_MANIFEST_20260721.json`, which sets `exact_revisions_available: false`. → **`unavailable`. Not recoverable without a re-capture.**
2. **Model-specific F28 causal evidence for Pythia-1B, Pythia-2.8B, OLMo-1B, Qwen2.5-1.5B.** Enumerated every `.json` under `experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/` (60+ files: STAGE8/14/15/16 probe + CPL2, stage10-22 series, evidence_packets/). No ablation report exists for any of the four. → **`unavailable`**, matching the 2026-07-19 matrix's "Not located."
3. **40E-axis evidence for Pythia-1B, Pythia-2.8B, OLMo-1B, Qwen2.5-1.5B.** Same enumeration. Only Pythia-160M (stage9_elements) and GPT-NeoX-20B carry a 40E artifact. → **`unavailable`**
4. **Static-weight-geometry tier for every model point except Pythia-2.8B.** `stage14_weight_geometry_alignment_20260519.json` is the only such artifact on any branch. → **`unavailable`**
5. **Character-level n-gram surface control for the 20B 40E readout.** Read the `controls` block of `master:…_probe_eval_report_20260527.json` in full: `confirmed_text_baseline_report` (CountVectorizer 1-2 grams), `text_hash_baseline` (HashingVectorizer 1-2 ngrams, 2^14), `majority_class_test_acc`, `shuffled_label_hidden_best_layer` (20 trials). No arm declares `analyzer='char'`. → **`control_proof: partial`**. Under the project's standing char-level-surface-control rule, no hidden-beats-surface framing of this row is supported.
6. **Cross-seed variation for every F28 and 40E row.** All four located F28 reports share one fixed split (1344/672/2352); the 20B 40E report pins `seed: 2026` with `"split": "fixed split by metadata.split; test_split=test"`. → **`unavailable`**
7. **Machine-readable JSON for the Pythia-160M F28 causal PASS.** Searched `git grep -l "0.0323"` and `"78.57"`/`"3.57"` variants across `experiment/cas-probe-pythia`, `master`, and HEAD, restricted to `*.json`. The number is sourced from `experiment/cas-probe-pythia:…/STAGE7_FOUNDATION_ABLATION_REPORT_20260517.md` (markdown prose). → **prose-backed, not artifact-backed.**
8. **The locked Pythia-160M F28 activation binary.** `STAGE7_FOUNDATION_ABLATION_REPORT_20260517.md` records SHA-256 `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f` and states the ~304 MB artifact "lives on RunPod only." The file at `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_pilot_activations_20260517.npz` on disk (317,617,680 bytes) hashes to `f63a66de86366a63ea0fd786ad0dc0bef68d5634be3b5fae525d4fb667f14d53` — **a different artifact.** This is already documented by the project at `experiment/cas-probe-pythia:…/research/cas_probe/README.md:2500-2512` as a local CPU recapture with `Formal gate valid: false`. → the locked binary is **`unavailable`**; the on-disk file is a recapture and must not be cited as the Stage 7 artifact.
9. **Eight of fifteen Amazon-manifest evidence artifacts.** Re-checked every `path` in `evidence_artifacts` against the working tree: all six `gpt_neox_20b_*` and all four `pythia160m_gate1/*` entries are **absent from the current checkout** (present on `master`). The five `C:/tmp/cas-tks-anchor-diagnostic-20260721/…` entries are present on disk.
10. **The two corrected-PDF SHA-256 values asserted at `docs/working/cas_harness_production_todo.md:2343` and `:2345`.** Grepped both hashes repo-wide; they appear only as prose in that file and in `project_handoffs` snapshots of it. The PDFs named in `d6069513` are not on disk. → **neither hash independently verified. Do not cite them as evidence.**
11. **Per-model evidence packets.** `noetic-compass-scaffold/noetic-compass/research/cas_probe/evidence_packets/` exists on disk but its contents are not tracked at HEAD; the four `stage21a_*` packets live only on `experiment/cas-probe-pythia`. → **`unavailable` at HEAD.**
12. **Independent object-store / third-party escrow mirror** for the 2026-07-21 definition-anchor bundle. Recorded by the Amazon manifest itself as `pythia160_tks_anchor_independent_object_store`, `availability: unavailable`, `status: OPEN`. → **`OPEN`**
13. **`gpt20_f28_source_archive`** (`C:/tmp/gpt_neox_20b_foundation28_and_40element_20260526`). Declared `availability_in_protected_tree: unavailable` by the Amazon manifest; not re-checkable from the repo. → **`unavailable`**

### 7.1 One correction available to the Amazon manifest

`CAS_HARNESS_AMAZON_CLAIM_EVIDENCE_MANIFEST_20260721.json` lists two artifacts under `missing_or_external_artifacts` with `availability_in_protected_tree: "unavailable"`. Both are **present on disk with exactly matching SHA-256**, verified this pass:

| `artifact_id` | Path | Recorded SHA-256 | Computed | Result |
|---|---|---|---|---|
| `pythia160_f28_activation_manifest` | `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_pilot_smoke_activations_manifest_20260517.json` | `AE364271…652878F` | `AE364271BD08245D016566CA9A3F72F5B628F19DE50EA1B33573AADEB652878F` | **MATCH** |
| `pythia160_f28_activation_npz` | `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_pilot_smoke_activations_20260517.npz` | `04800D4263…20B4913` | `04800D4263E16FF1AA25653D58FE8DB3531A9035602429EA7E658413320B4913` | **MATCH** |

Upgrade these two to `present`. Leave every other availability field untouched. Caveat: this is the **smoke** capture (`n_records: 56`, `n_classes: 28`), not the full 2,352-record F28 evaluation set — it does not close gap 8.

---

## 8. Gate-3 boundary box

The four 2026-07-24 W0 prompt-injection experiments are **Gate 3 scope** (`docs/working/CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:255`; `docs/working/cas_harness_production_todo.md:955`). They carry **no Gate 2 credit** and are not cited anywhere in §4. The directory name `GATE2_W0_FAIR_COMPARISON` is misleading; the word "injection" does not appear in the Gate 2 section at all.

One fact from those files belongs here, because item 1 must inventory every place the project claims what a model was shown to do:

**Model-provenance defect (real, live).** In `project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/GATE2_W0_FAIR_COMPARISON/evidence/`:

- `injection_detection_w0_report_pythia1b_attempt3_meanpool.json` → `"model": "EleutherAI/pythia-160m"`
- `injection_detection_w0_report_pythia28b_attempt4_meanpool.json` → `"model": "EleutherAI/pythia-160m"`

while `injection_detection_attempts_registry.json` in the same directory records attempt 3 as `EleutherAI/pythia-1b` and attempt 4 as `EleutherAI/pythia-2.8b`. None of the four reports carries a `model_revision` field. Two artifacts assert a false fact about which model produced them.

Already flagged independently at `.../expert_panel/panel_structured_findings.json:34`. **Do not overwrite the historical reports** — write a separate provenance-corrections file. This defect is recorded, not resolved, by item 1.

---

## 9. Item-1 exit self-assessment

Against the Gate 2 exit clause, verbatim: *"Exit requires exact model/revision/tier claim rows, `control_proof: present` where controls ran, independently reproducible raw evidence, and a verdict consistent with preregistered criteria. Mixed or negative results remain `OPEN / NOT LICENSED`; criteria are not rewritten after outcomes are known."*

| Exit requirement | State | Why |
|---|---|---|
| Exact model/revision/tier claim rows | **PARTIAL** | Six of seven model points have exact revisions (§3). GPT-NeoX-20B — the highest-profile point — is `unavailable` and unrecoverable without a re-capture. |
| `control_proof: present` where controls ran | **MIXED** | Present only on the 20B causal random-control axis, the Pythia-2.8B weight-geometry random controls, and the two universality-program rows that ran char n-grams. The 20B 40E readout, every F28 readout row, and the typed Qwen-Instruct row are `partial` or `unavailable`. |
| Independently reproducible raw evidence | **NOT SATISFIED** | The branch split (§2). No checkout reproduces one row end to end. |
| Verdict consistent with preregistered criteria | **SATISFIED, and the verdicts are negative** | 20B 40E causal: gate missed, `OPEN`. Pythia-2.8B F28-vs-GoEmotions: +20 pp floor missed, `BLOCKED_CAS_NOT_RECOVERABLE`. Qwen W0 injection: char n-gram won, PASS withdrawn, `OPEN / NOT LICENSED`. No criterion was rewritten. |

**Item 1 is `PARTIAL / OPEN`, not closed.** The matrix now exists with a revision dimension and the blanket wording is inventoried with replacement text, but two of four exit conditions fail.

---

## 10. What this matrix licenses

Plainly: almost nothing that the live documents currently say. Of the 23 claim rows in §4, **two are `supported`** (the 20B 40-Element readout number at `executive_summary:13`, and the fully-caveated 20B ablation sentence at `synopsis:101`), **one is `withdrawn`**, **one is `unavailable`**, and **nineteen are `overstated`**. Every blanket six-model formulation on every live surface — the consolidated current spec sheet, the executive summary, the synopsis, the Amazon review brief, and the v2.1 investor sheet — is overstated, and four of them use phrasings the project's own 2026-07-19 governance rules name as prohibited verbatim.

What survives, stated at the width the raw artifacts actually support: **Foundation-28 held-out readout replicates on six model points across three architecture families on one frozen English synthetic fixture, with exact denominators out of 2,352 and descriptive single-split Wilson intervals; the 40-Element readout reaches 95.625% at GPT-NeoX-20B against word-level text controls near 50%; subspace ablation is causally suggestive at 20B but missed its preregistered gate; sparse-neuron-cover causal control is Pythia-160M only; static weight geometry is Pythia-2.8B only and is one of three checks.** That is a real and substantial research result. It is not "presence, causal role, and conditionability across six models," it is not "two axes closed at 20B," and it is not independently reproducible from any current checkout. Nothing here moves any claim to `LICENSED`, no `ACCEPT` is revived, and the negative results — the 20B causal near-miss, the Pythia-2.8B GoEmotions block, the withdrawn Qwen injection PASS — stay `OPEN / NOT LICENSED` exactly as their preregistrations required.

---

## Sources

Every file below was opened, read, or queried during this pass on 2026-07-24.

**Controlling text**
- `docs/working/CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md` (Gate 2 section, lines 188-225; Gate 3 at :255)
- `docs/working/cas_harness_production_todo.md:954-955, 2331-2345`

**Prior claim-control work (unmerged commit `d6069513`, branch `codex/claims-remediation-20260719`)**
- `d6069513:docs/legal_drafts_20260607/CAS_HARNESS_CLAIM_EVIDENCE_MATRIX_20260719.md` (all 121 lines)

**Live claim surfaces at HEAD**
- `docs/working/cas_harness_executive_summary_20260630.md:12-17`
- `docs/working/cas_harness_synopsis_20260630.md:24, 85, 101, 118`
- `docs/working/cas_harness_amazon_review_brief_20260615.md:54`
- `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:1-10, 28, 67, 83, 321, 522`
- `docs/legal_drafts_20260607/CAS_provenance_preprint_updated.md:19, 97`
- `docs/legal_drafts_20260607/CAS_provisional_flowcharts_described.md:145`
- `docs/legal_drafts_20260607/CAS_provisional_patent_updated.md:222`
- `noetic-compass-scaffold/noetic-compass/docs/marketing/CAS_HARNESS_SPEC_SHEET_v2_1_INVESTOR_EXTERNAL_NDA_20260604.md:1-8, 146, 158`
- `noetic-compass-scaffold/noetic-compass/docs/marketing/CAS_HARNESS_SPEC_SHEET_v1_6…v2_0_INVESTOR_EXTERNAL_NDA_*.md:1` (banner check)
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/CAS_HARNESS_SPEC_SHEET_20260517.md:1-8, 521`
- `docs/working/cas_harness_original_closure_methodology_20260526.md:186-203`
- `docs/working/paper_b_causal_localization_draft_outline_20260523.md:12, 22, 46-56`
- `docs/working/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md:380-400`
- `docs/working/typed_probe_gate_runlog.md:12-42`

**Raw evidence — branch `experiment/cas-probe-pythia`**
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/STAGE8_PYTHIA1B_PROBE_REPORT_20260517.json`
- `…/STAGE14_PYTHIA28B_PROBE_REPORT_20260518.json`
- `…/STAGE15_OLMO1B_PROBE_REPORT_20260519.json`
- `…/STAGE16_QWEN15B_PROBE_REPORT_20260519.json`
- `…/stage8_pythia1b_activations_manifest_20260517.json`
- `…/stage14_pythia28b_activations_manifest_20260518.json`
- `…/stage15_olmo1b_activations_manifest_20260519.json`
- `…/stage16_qwen15b_activations_manifest_20260519.json`
- `…/stage14_weight_geometry_alignment_20260519.json`
- `…/pythia_ablation_domain_layer5_n30_20260516.json`
- `…/pythia_ablation_random_control_layer3_n30_20260516.json`
- `…/STAGE7_FOUNDATION_PILOT_REPORT_20260517.md`
- `…/STAGE7_FOUNDATION_ABLATION_REPORT_20260517.md`
- `…/README.md:2500-2530`

**Raw evidence — branch `master`**
- `noetic-compass-scaffold/noetic-compass/docs/working/gpt_neox_20b_stage9_original_40e_capture_metadata_20260527.json`
- `…/gpt_neox_20b_stage9_original_40e_probe_eval_report_20260527.json`
- `…/gpt_neox_20b_stage9_original_40e_subspace_ablation_report_20260528T0155Z.json`
- `…/S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json`
- `…/pythia160m_gate1/pythia160m_stage9_40e_neuron_covers.json`
- `…/gpt_neox_20b_stage9_original_40e_eta_epsilon_bridge_per2_20260528T0455Z.json` (existence confirmed only)

**On-disk artifacts at HEAD (hashes computed this pass)**
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_pilot_smoke_activations_manifest_20260517.json`
- `…/stage7_foundation_pilot_smoke_activations_20260517.npz`
- `…/stage7_foundation_pilot_activations_20260517.npz`
- `…/stage9_elements_pilot_activations_20260517.npz`

**Manifests and governance**
- `project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/04_AMAZON_INTERNAL_DRAFT_DO_NOT_SEND/CAS_HARNESS_AMAZON_CLAIM_EVIDENCE_MANIFEST_20260721.json`
- `project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/04_AMAZON_INTERNAL_DRAFT_DO_NOT_SEND/CAS_HARNESS_AMAZON_TECHNICAL_EVALUATION_SPEC_20260721.md:416-435`
- `master:noetic-compass-scaffold/noetic-compass/research/cas_probe/cas_harness_public_evidence_manifest.json`

**Gate-3-scope files, inventoried for provenance only (no Gate 2 credit)**
- `project_handoffs/…/11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/GATE2_W0_FAIR_COMPARISON/evidence/injection_detection_attempts_registry.json`
- `…/evidence/injection_detection_w0_report_pythia160m.json`
- `…/evidence/injection_detection_w0_report_pythia160m_attempt2_meanpool.json`
- `…/evidence/injection_detection_w0_report_pythia1b_attempt3_meanpool.json`
- `…/evidence/injection_detection_w0_report_pythia28b_attempt4_meanpool.json`
- `…/expert_panel/panel_structured_findings.json:34`

**Gather input**
- `docs/working/gate2_closure/gate2_item1_claims_gather_raw_20260724.json`

**Verification commands run**
- `git merge-base --is-ancestor {master,experiment/cas-probe-pythia,d6069513} HEAD` → all three: **not ancestors**
- `git branch -a --contains d6069513` → `codex/claims-remediation-20260719` only
- `git cat-file -t HEAD:docs/legal_drafts_20260607/CAS_HARNESS_CLAIM_EVIDENCE_MATRIX_20260719.md` → does not exist
- Independent Wilson-95% recomputation of all eight readout rows (all reproduce the 2026-07-19 matrix to the digit)
- `0.2872767857142857 / 0.002678571428571419 = 107.25`; `/ 0.0006808035714286175 = 421.97`
- SHA-256 recomputation of four on-disk `.npz`/`.json` artifacts
