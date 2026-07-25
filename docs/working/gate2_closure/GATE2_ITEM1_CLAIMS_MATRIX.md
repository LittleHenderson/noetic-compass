# Gate 2 Item 1 — Model-by-Revision-by-Evidence-Tier Claims Matrix

## Status block

| Field | Value |
|---|---|
| **Addresses (does NOT close)** | Gate 2 item 1 — "Publish a model-by-revision-by-evidence-tier matrix reconciling every v1.0, v2.1, investor, engineering, and archived claim. Remove blanket six-model wording unless raw evidence supports the exact rows." (`docs/working/CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:189-191`) |
| **What it actually closes** | Clause 1 (publish a model-by-revision-by-evidence-tier matrix) and, as of revision 4, **all five claim categories now carry rows** — v1.0 and archived are added in §4.6; v2.1, investor and engineering were already in §4.1-4.3. Clause 2's verb is "reconciling **every** … claim," and that is **not** met: coverage within the v1.0 sheet (7 rows, all from `:515`/`:521`) and within the five archived sheets (5 rows) is **representative, not exhaustive** — revision 4 found further unreconciled assertions in the archived bodies that revision 3's rows did not reach (§5.2 "first ACCEPT" row). Clause 3 ("Remove blanket six-model wording") is **unmet**: it is an edit verb, no live surface was edited, and this document has no authority to edit legal-drafts or NDA-distributed surfaces. §9.1 names every surface and line that needs the edit and points at the replacement text. Three of the four Gate 2 exit conditions still fail (§9). |
| **Date** | 2026-07-24 (revision 4, third adversarial-review pass applied — enumeration counts re-run, archived "first ACCEPT" audit redone, four internal count conflicts reconciled) |
| **Item exit state** | **PARTIAL — NOT CLOSED.** See §9. |
| **Branch this was built on** | `codex/cascompass-legal-live-source` (HEAD) |
| **Compute performed** | None. This is a document-and-artifact reconciliation only. |
| **Git writes performed** | None. |

### Revision note — 2026-07-24 revision 2

An adversarial review re-ran the §7 negatives by **filename enumeration** (`git ls-tree -r --name-only <branch>`) instead of string grep. Five findings changed the document, **three of them in the direction of more evidence, not less**:

1. `experiment/cas-probe-pythia:…/stage7_foundation_layer6_ablation_report_20260517.json` **exists.** Revision 1 called the Pythia-160M F28 causal result "markdown only / no machine-readable JSON located." That was wrong; the JSON carries a preregistered `decision_gates` block. §4.1 row 1 and §7 gap 7 are corrected. (Root cause: revision 1 grepped the literal string `0.0323`, but the JSON stores `0.03225806451612903`; the markdown rounds it.)
2. The strongest Pythia-160M **F28** text control is `tfidf_char_3_5` — a **character** 3-5-gram arm — not word-level. That row is `control_proof: **present**`, not `partial`.
3. The strongest Pythia-160M **40E** text control is also `tfidf_char_3_5` (50.089%). Revision 1 wrote "~50.1% word-level." Same correction: `control_proof: **present**`.
4. `§5.2`'s "none found this pass" rows were wrong for two prohibited phrases. *(Revision-3 note: this correction was announced here and never carried into §5.2, and the scope was understated — it is three phrases wrong plus one near-form. §5.2 was fully re-run in revision 3; the counts below are superseded by the ones there.)*
5. A Pythia-160M 40E numeric conflict (89.799% vs 91.719%) was propagated unreconciled. It is now §5.3 item 3 with both artifacts named.

### Revision note — 2026-07-24 revision 3

A second adversarial review found that revision 2 **announced** five corrections in the note above but only carried three of them into the body. Revision 3 finishes the job and adds four further corrections. Everything changed, and its direction:

| # | Change | Direction |
|---|---|---|
| 1 | §7 gap 7 still read "prose-backed, not artifact-backed" — contradicting revision 2's own note. Gap 7 is now rewritten around the located JSON. | **more evidence** |
| 2 | §4.4 Pythia-160M **F28** row still read "word-level only / `partial`". Now `control_proof: present` (`tfidf_char_3_5`), selected layer **6**, JSON artifact named, paired McNemar `2.6557483981655295e-95` reported. | **more evidence** |
| 3 | §4.4 Pythia-160M **40E** row still read "~50.1% word-level / `partial`". Now `control_proof: present` (`tfidf_char_3_5` 50.089%), selected layer **5**, JSON artifact named. | **more evidence** |
| 4 | §4.4 20B F28 row read "Selected layer: not stated". The packet states `readout.layer 40`. | neutral (accuracy) |
| 5 | §5.2 "none found this pass" was wrong on **three** rows outright and one in near-form. *(Counts corrected in revision 4 — see the revision-4 note; the sub-counts printed here in revision 3 were 7 / 4 and the total was given as 30, none of which was derivable from the table.)* Corrected and derivable: 15 hits for the lab/corpus/language phrase (14 assertions + 1 status-table entry recording it as `LICENSED`), **8** for "two independent evidence tiers … six models", **11** for "first ACCEPT", 1 near-verbatim for "works on any open-weight model", 1 near-form for "controls model output" → **36 additional line-level violations** over revision 2. | **less evidence** |
| 6 | §5.3 item 3 (the 89.799% vs 91.719% conflict) was announced in revision 2 and never written. Now present, with both artifacts named and both traced to real runs. | neutral (accuracy) |
| 7 | New **§4.6** reconciles the v1.0 spec sheet and the five archived v1.6–v2.0 sheets — the two roadmap-clause-2 categories revision 2 omitted entirely. | **less evidence** (adds overstated rows) |
| 8 | §4.4 preamble claimed every row was recomputed from `layer_scan`. Only four of fourteen rows have a `layer_scan`. Preamble narrowed. | **less evidence** |
| 9 | §4.4 Qwen2.5-1.5B-Instruct row now carries the source's own `McNemar p = 0.289 — NOT statistically separable` finding, and §4.5 gains item 7. | **less evidence** |
| 10 | §7 gains gap 14 (referenced twice in revision 2 but never written) and gap 15; §9 gains §9.1 (referenced in the status block but never written), a roadmap-clause-3 row, and a downgraded preregistration cell. | **less evidence** |

Net: two corrections raise the evidence, six lower it, two are neutral. The item verdict does not change — it was `PARTIAL / OPEN` before and remains so.

### Revision note — 2026-07-24 revision 4

A third adversarial review re-ran the document's own printed verification commands and found that two of them did not reproduce, that the archived "first ACCEPT" audit was scoped to one file when the phrase is live in three, and that four internal counts conflicted. Every command below was re-run before it was reprinted.

| # | Change | Direction |
|---|---|---|
| 1 | §7 gap 2 / verification block printed `grep -i ablation` on `experiment/cas-probe-pythia` → **24 paths**. The command returns **29**. Corrected, and the six unlisted paths are named (the `decode_ablations` family; none is a model ablation report, so the gap's conclusion is unchanged). The companion `master` count of 16 re-ran exactly and is left alone. | neutral (accuracy) |
| 2 | §7 gap 14 / verification block printed `grep -i prereg` on `experiment/cas-probe-pythia` → **4 paths**, naming only the Stage 22 trio and `stage24b_…_prereg`. The command returns **80**. Corrected: all 80 were screened by filename, exactly 2 matched `40_element\|40e\|20b\|neox`, and both are the Stage 24B CPU-recap pair. Conclusion unchanged; the *stated search* is now true as printed. | neutral (accuracy) |
| 3 | §5.2 "first ACCEPT" row and §4.6.2 row 28 said "4 assertions, all in the archived v1.7 sheet body." Re-counted with an exact-phrase search: the phrase is live in **v1_7, v1_8 and v1_9**, and two of those hits are row-level status cells reading `LICENSED with explicit scope` for a verdict the project withdrew. §9.1 gains them as row-level tombstone items. | **less evidence** |
| 4 | §4.6.2 row 27 and §5.2's "causally validated across six models" row cited the causal `LICENSED` cell at `v1_6:544`. That line is the cross-architecture cell; the causal cell is `v1_6:541`. Corrected in both places. | neutral (accuracy) |
| 5 | Four internal count conflicts reconciled: §4.4 preamble said "fourteen rows" for a 13-row table; §9's `control_proof` cell said "eight rows" where seven are enumerable; the §5.2 headline total was stated as 30 (revision note), 22 (§10) and 22 (§6) with the table summing to something else again. §5.2 now carries an explicit derivation and the dependent places quote it. | neutral (accuracy) |
| 6 | §5.2 applied two different inclusion rules to the same `project_handoffs` snapshot copy — counted in the lab/corpus/language row, omitted from the tiers row. One rule is now stated in the search-method paragraph and applied to both. | **less evidence** |
| 7 | §4.6.1 row 24c said CPL2 reports exist for "Stage 8 / 14 / 15 / 16 / 19D / 19E." 19D and 19E are **scripts with no report**. Corrected, and the `+0.554` figure now carries its full field path (`conditions.probe_readable.…`) because the sibling `gold_readable` value is different. | neutral (accuracy) |
| 8 | Status block clause-2 wording narrowed from "all five claim categories" to "all five categories carry rows; v1.0 and archived coverage is representative, not exhaustive" — which change 3 proves. | **less evidence** |

Net: no correction raises the evidence; three lower it; five are accuracy. The item verdict does not change — `PARTIAL / OPEN` before, `PARTIAL / OPEN` after.

### Explicit claim-state line

**Real:** the numeric readout, ablation, and weight-geometry values in §4 — every one was re-read from a raw JSON field or (for the four F28 rows that carry a `layer_scan`) recomputed from it, and reproduces exactly. Where a row's number is transcribed from a markdown table rather than a JSON field, the row's `Raw artifact` cell says so; see the §4.4 preamble.
**Simulated:** nothing in this document.
**Accepted:** nothing. No standing `ACCEPT` exists anywhere in the project record.
**Withdrawn:** the GPT-NeoX-20B Stage 9 40E `ACCEPT`; `accept_revival_allowed: false`.
**Unavailable:** the GPT-NeoX-20B model revision; model-specific F28 causal evidence for four of six model points; 40E evidence for four of six; weight geometry for five of six; any character-level surface control **at 20B on either axis** — and on the F28 axis at 20B, any text control at all against the headline number (both Pythia-160M axes now have a character arm; see revision note 3); cross-seed variation everywhere; the locked Pythia-160M F28 activation binary; any dated preregistration artifact for the 20B ≥30 pp / ≤65% ablation gate (§7 gap 14); which of the two Pythia-160M 40E runs is canonical (§7 gap 15); the v1.0 sheet's "lacunarity 0.015–0.021" range and its "three preflight predictions held" count (§4.6.1 rows 24d, 24e); the Pythia-160M lower endpoint of the "+0.283 → +0.554" bridge doubling — no Pythia-160M CPL2 report exists on any branch (§4.6.1 row 24c); a full audit of the "immutable WORM evidence" phrase family (§5.2).
**Open / not licensed:** every blanket six-model claim listed in §5; the prompt-injection W0 result; universality; 300B.
**Flagged for human review:** three internal inconsistencies (§5.3 — two count errors plus one unreconciled Pythia-160M 40E numeric conflict, now written out with both artifacts named); **four** archived status-table cells across **three** sheets recording a prohibited or withdrawn claim as `LICENSED` (§4.6.2 row 27 — `v1_6:541` the causal clause, `v1_6:545` the lab/corpus/language clause; §4.6.2 row 28 — `v1_8:522` and `v1_9:1220`, both the withdrawn Stage 9 40E `ACCEPT`. Revision-4 correction: revision 3 recorded one, at a line number that was itself wrong); one live model-provenance defect (§8).

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
| 21b | "**Five axes collapse to exact chance under subspace ablation with clean random nulls.**" — the untrimmed opening clause of the same line as row 21 (revision-2 addition; revision 1 trimmed it off and inventoried nothing) | `docs/working/cas_harness_synopsis_20260630.md:101`; **second live surface located in revision 3:** `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:282` ("Five axes pass collapse-to-exact-chance under subspace ablation with clean random nulls") | scope not stated in the sentence; sits inside a paragraph whose next sentence is about GPT-NeoX-20B | mixed | Multi-axis causal | Enumerated by filename on `experiment/cas-probe-pythia`. **Three** axes verified this pass as reaching exact chance, **all Pythia-160M**: Stage 3 noetic layer-3 (`pythia_ablation_layer3_20260515.json` → `probe_accuracy_unablated 0.8985507246376812` → `probe_accuracy_ablated 0.10144927536231885`, chance 1/10); Stage 6.5 role-bound layer-5 (`stage6_role_bound_layer5_ablation_report_20260516.json` → `noetic_subspace_ablation.test.acc 0.1`, `random_complement_controls.mean/max_disruption 0.0`, `one_sided_empirical_p_random_ge_noetic 0.03225806451612903`, `status "ROLE_BOUND_SUBSPACE_CAUSAL_FOR_PROBE_READOUT"`); Stage 7.1 foundation layer-6 (row 1, `0.03571428571428571` = exact 1/28). A fourth artifact, `stage9_factor_ablation_report_20260517.json` (`status "STAGE9_FACTOR_CHECK_FULL_PASS"`, layer 5), reports three sub-task ablations by **disruption** (domain `0.6729910714285714`, noetic `0.8154017857142858`, interaction `0.8729910714285714`) — accuracies not read this pass. A fifth artifact, `pythia_ablation_domain_layer5_n30_20260516.json` (Stage 4.1, `n_random_directions 30`, `n_permutations 10000`), reports per-class kept-rates, not an axis accuracy. **The five axes are never named at `:101`, and no single artifact enumerates all five.** Decisively: the 40-Element axis **at 20B does not collapse to chance** — `66.897%` against a `chance_baseline.accuracy 0.025` (row 20/21) | **overstated** — true of no more than the Pythia-160M axis family, adjacent to a 20B sentence that contradicts it |
| 22 | "Weight-geometry: 2.83× random (p = 0.0099)" | `docs/working/paper_b_causal_localization_draft_outline_20260523.md:56`; matrix cell "PASS reported: 2.83 times random; p=.0099" at `d6069513:…MATRIX_20260719.md:34` | `EleutherAI/pythia-2.8b` | `2a259cdd…` | Static weight geometry | `experiment/cas-probe-pythia:…/stage14_weight_geometry_alignment_20260519.json`. **Three** checks, `n_random 100`: `output_logit_lens_energy_fraction` 2.830531385486643 (p 0.009900990099009901); `output_weight_energy_fraction` 1.0621312951730846 (p 0.009900990099009901); `input_weight_energy_fraction` 1.0033496167943243 (**p 0.3465346534653465**). Artifact's own text: "At least one weight-geometry check is above random same-rank controls." No multiplicity policy stated | **overstated** (reports best-of-three as the result) |
| 23 | Stored verdict `ACCEPT` in the historical 20B 40E evidence packet | `master:…/gpt_neox_20b_stage9_original_40e_evidence_packet_20260528T0455Z.json` (packet bytes preserved) | `gpt-neox-20b` | **`unavailable`** | 40E packet | Amazon manifest records the retraction `withdrawn_stage9_40e_accept` with `accept_revival_allowed: false`. The corresponding F28 packet on master already reads `output.verdict = 'FLAG_FOR_HUMAN_REVIEW'` | **withdrawn** |

### 4.4 Underlying raw evidence rows (model × tier), verified this pass

**Preamble corrected in revision 3.** Revision 2 said "every accuracy below was recomputed from the raw `layer_scan` blocks." That is true of **four of the thirteen rows** (revision-4 correction — revision 3 wrote "fourteen"; the table below has 13 body rows and the three-way breakdown that follows enumerates 4 + 6 + 3 = 13), not all of them. Checked by loading each report and testing for the key: `layer_scan` is present in `STAGE8_PYTHIA1B_PROBE_REPORT_20260517.json`, `STAGE14_PYTHIA28B_PROBE_REPORT_20260518.json`, `STAGE15_OLMO1B_PROBE_REPORT_20260519.json`, `STAGE16_QWEN15B_PROBE_REPORT_20260519.json` — the four non-160M F28 rows — and absent everywhere else. Precisely:

- **Recomputed from a `layer_scan`:** Pythia-1B F28, Pythia-2.8B F28, OLMo-1B F28, Qwen2.5-1.5B F28.
- **Re-read from a named JSON field, not a `layer_scan`:** Pythia-160M F28 (`headline.test.acc`), Pythia-160M 40E (`headline.test.acc`), 20B F28 (`readout.heldout_accuracy`), 20B 40E readout (`best_layer.test_acc`; the layer sweep is under `per_layer`, a differently-named block), 20B 40E causal (`primary_result`), Pythia-2.8B weight geometry (three named energy-fraction fields).
- **Transcribed from a markdown table, no JSON located:** Qwen2.5-1.5B-Instruct typed row (`typed_probe_gate_runlog.md`), Pythia-2.8B F28-vs-GoEmotions row and Qwen-1.5B W0 row (`CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md:391, :393`).

Every Wilson interval **was** recomputed independently for every row that carries one, and each matches the 2026-07-19 matrix to the digit.

| Model | Revision | Axis | Selected layer | correct/n_test | Accuracy | Wilson 95% (descriptive) | Strongest surface control + type | `control_proof` | Seeds | Split | `evidence_class` | `claim_status` | Raw artifact |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pythia-160m | `50f5173d…` | F28 | **6** (`headline.layer`) | 1848/2352 | 78.571% (`headline.test.acc 0.7857142857142857`) | [76.867, 80.182] | **`tfidf_char_3_5` — a CHARACTER 3-5-gram TF-IDF arm — test acc 0.4965986394557823 (49.660%)**, recorded as `best_text_baseline_by_val`. Word arms are weaker: `tfidf_word_1_2` 0.4523809523809524, `count_vector_word_1_2` 0.4187925170068027. Strongest surface-metadata arm `surface_pair_family_focus` 0.6666666666666666, hence the "+11.9 pp" (`test_acc_lift_over_best_metadata 0.11904761904761907`); lift over the char text arm is `0.2891156462585034` | **`present`** (revision-3 correction) | 1 | fixed 1344/672/2352 | `DEMONSTRATED_RESEARCH_RESULT` | `present` | **JSON located (revision-3 correction):** `experiment/cas-probe-pythia:…/stage7_foundation_pilot_probe_report_20260517.json` — `n_records 4368`, `readout "focus_token"`, `status "FOUNDATION_PROBE_RELIABLY_ABOVE_TEXT_BASELINE"`, preregistered `decision_gates {mcnemar_p_max 0.05, metadata_focus_only_test_acc_max 0.08, test_acc_lift_over_text_min 0.05}`, and `headline.paired_vs_best_text {b_name "tfidf_char_3_5", a_only_correct 914, b_only_correct 234, exact_binomial_mcnemar_p 2.6557483981655295e-95}`. Markdown companion `STAGE7_FOUNDATION_PILOT_REPORT_20260517.md` |
| pythia-1b | `f73d7dcc…` | F28 | 8 | 1938/2352 | 82.39796% | [80.806, 83.884] | `unavailable` in this artifact | `unavailable` | 1 | fixed 1344/672/2352 | `DEMONSTRATED_RESEARCH_RESULT` | `present` | `experiment/cas-probe-pythia:…/STAGE8_PYTHIA1B_PROBE_REPORT_20260517.json` |
| pythia-2.8b | `2a259cdd…` | F28 | 14 | 2020/2352 | 85.88435% | [84.419, 87.233] | `unavailable` in this artifact | `unavailable` | 1 | fixed 1344/672/2352 | `DEMONSTRATED_RESEARCH_RESULT` | `present` | `experiment/cas-probe-pythia:…/STAGE14_PYTHIA28B_PROBE_REPORT_20260518.json` |
| OLMo-1B-hf | `aee7752d…` | F28 | 16 | 2131/2352 | 90.60374% | [89.357, 91.718] | `unavailable` in this artifact | `unavailable` | 1 | fixed 1344/672/2352 | `DEMONSTRATED_RESEARCH_RESULT` | `present` | `experiment/cas-probe-pythia:…/STAGE15_OLMO1B_PROBE_REPORT_20260519.json` |
| Qwen2.5-1.5B | `8faed761…` | F28 | 11 | 1929/2352 | 82.01531% | [80.411, 83.515] | `unavailable` in this artifact | `unavailable` | 1 | fixed 1344/672/2352 | `DEMONSTRATED_RESEARCH_RESULT` | `present` | `experiment/cas-probe-pythia:…/STAGE16_QWEN15B_PROBE_REPORT_20260519.json` |
| gpt-neox-20b | **`unavailable`** | F28 | **40** (`readout.layer`; revision-3 correction — revision 2 said "not stated") | 2043/2352 | 86.8622% (`readout.heldout_accuracy 0.868622`) | [85.437, 88.168] | word-hash centroid 42.28% — and it is **legacy context for a superseded method**, not a control on the reported number: `readout.legacy_centroid_context {test_acc 0.510369, text_hash_centroid_test_acc 0.422811, note "Legacy centroid report is retained as cover-discovery context; the S7-F28 gate uses balanced logistic."}`. No text control at all is reported against the balanced-logistic 86.862%; no character-level arm anywhere in the packet | `partial` | not stated | fixed | `DEMONSTRATED_RESEARCH_RESULT` | `FLAG_FOR_HUMAN_REVIEW` (`output.verdict` in packet) | `master:…/S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json`. The packet also carries a `matched_controls` block (`same_size_random_controls` 20 trials, `wrong_cover_control`, `label_drop_exceeds_random_max: true`) — a random/wrong-cover axis, not a surface-text axis |
| pythia-160m | `50f5173d…` | 40E | **5** (`headline.layer`) | 4023/4480 | 89.799% (`headline.test.acc 0.8979910714285714`; × 4480 = 4023.0 exactly) | [88.878, 90.652] | **`tfidf_char_3_5` — CHARACTER 3-5-gram TF-IDF — test acc 0.5008928571428571 (50.089%)**, recorded as `best_text_baseline_by_val`. Word arms `tfidf_word_1_2` and `count_vector_word_1_2` both 0.5; strongest metadata arm `pair_focus` 0.5. Lift `test_acc_lift_over_best_text 0.39709821428571423` | **`present`** (revision-3 correction; revision 2 called this "~50.1% word-level") | not stated | fixed 2560/1280/4480 | `DEMONSTRATED_RESEARCH_RESULT` | `present` | **JSON located (revision-3 correction):** `experiment/cas-probe-pythia:…/stage9_elements_pilot_probe_report_20260517.json` — `n_records 8320`, `readout "focus_token"`, `status "STAGE9_40_ELEMENTS_READOUT_PASS_CLEAN"`, preregistered `decision_gates {test_acc_min 0.2, test_acc_lift_over_text_min 0.05, mcnemar_p_max 0.05, null_test_acc_max 0.1, null_mcnemar_p_min 0.2}`, `paired_vs_best_text {b_name "tfidf_char_3_5", exact_binomial_mcnemar_p 0.0}`. **Not** the `master:…/pythia160m_gate1/` packet revision 2 cited — that is a different run reporting a different number; see §5.3 item 3 |
| gpt-neox-20b | **`unavailable`** | 40E readout | 2 | 4284/4480 | 95.625% | [94.986, 96.186] | CountVectorizer(1-2 grams) 49.241%; HashingVectorizer(1-2 ngrams) 50.0% — **word-level only** | `partial` | 2026 | fixed by `metadata.split`; group overlap 0 | `DEMONSTRATED_RESEARCH_RESULT` | `FLAG_FOR_HUMAN_REVIEW` | `master:…_probe_eval_report_20260527.json` |
| gpt-neox-20b | **`unavailable`** | 40E causal | 2 | — | 95.625% → 66.897% (28.7277 pp) | n/a | random same-rank: mean 0.0681 pp, max 0.2679 pp | `present` (random-control axis only) | not stated | fixed | `DIAGNOSTIC_OR_APPARATUS_EVIDENCE` | `OPEN` (preregistered gate missed) | `master:…_subspace_ablation_report_20260528T0155Z.json` |
| pythia-2.8b | `2a259cdd…` | Static weight geometry | n/a | — | 2.8305× / 1.0621× / 1.0033× random | n/a | `n_random 100` same-rank random | `present` | not stated | n/a | `DIAGNOSTIC_OR_APPARATUS_EVIDENCE` | `present` | `experiment/cas-probe-pythia:…/stage14_weight_geometry_alignment_20260519.json` |
| Qwen2.5-1.5B-**Instruct** | `989aa798…` | Typed readout | 14 | 76/83 | 91.566% | not computed here (n=83) | TF-IDF 86.7%; CountVectorizer 83.1%; majority 13.3% — word-level. **Revision-3 addition, from the same quoted block:** `docs/working/typed_probe_gate_runlog.md:31-32` states "McNemar headline-vs-TF-IDF p=0.289 — on n=83 the probe is NOT statistically separable from a text-only classifier," and the source itself scopes the gate to "the probe reads typed content from Qwen hidden states accurately" — NOT "hidden states beat text" | `partial`, **and the row licenses no hidden-beats-text reading at all** | 42 | seed-42 split, 551-record corpus `1970c1ab…` | `DEMONSTRATED_RESEARCH_RESULT` | `present` (typed coverage `PASS` only) | `docs/working/typed_probe_gate_runlog.md:12-38` |
| pythia-2.8b | `2a259cdd…` | F28 vs GoEmotions | 24 | — | F28 49.857%, +13.857 pp | n/a | GoEmotions rival 57.143%; scrambled F28 3.857% | `present` | not stated | not stated | `DEMONSTRATED_RESEARCH_RESULT` | **`BLOCKED_CAS_NOT_RECOVERABLE`** — preregistered +20 pp floor missed | `docs/working/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md:391` |
| Qwen-1.5B | not recorded | Prompt-injection W0 | 18 | — | hidden BA 89.6875% | n/a | later char n-gram 92.5-93.1% — **char-level, and it won** | `present` | not stated | not stated | `DEMONSTRATED_RESEARCH_RESULT` | **`OPEN / NOT LICENSED`** — initial PASS **withdrawn** | `docs/working/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md:393` |

### 4.5 Per-row uncertainty the 2026-07-19 matrix omits

Verified directly from the raw `layer_scan` blocks this pass:

1. **Every F28 row is one fixed split, one seed.** All four located reports carry `split {train: 1344, val: 672, test: 2352}` identically. No cross-validation, no cross-seed. The Wilson intervals are single-split descriptive binomial intervals and cover none of that.
2. **Pythia-1B and Pythia-2.8B layer choice was decided by the lacunarity tie-break, not validation accuracy.** Both report `selected_val_accuracy = 1.0`. Pythia-1B has **three** layers at val 1.0 (positions 8, 9, 10); Pythia-2.8B has **thirteen** (positions 14-26). Under `selection_rule: "highest validation 28-way Foundation accuracy; ties within 0.001 broken by lowest val lacunarity"`, the tie-break did the selecting. No Wilson interval covers this.
3. **Three of four selected layers are not the best test layer.** Pythia-1B: selected L8 0.82398 vs best L13 0.89328. Pythia-2.8B: selected L14 0.85884 vs best L13 0.88095. Qwen2.5-1.5B: selected L11 0.82015 vs best L28 0.91241. OLMo-1B is the exception — selected L16 *is* the best layer (0.90604). **These four layer pairs are measured values read from the `layer_scan` blocks.** The reading that this "evidences honest selection" is an **interpretation, not a measurement**, and is labelled as such here: it is consistent with selection never having seen test, but a leak-free selection rule is established by the rule text and the split, not by an outcome pattern. Revision 2 stated the interpretation with the same authority as the numbers; revision 3 separates them.
4. **The Pythia-1B hedge is unnecessary.** The 2026-07-19 matrix writes "about 1,938/2,352"; `0.8239795918367347 × 2352 = 1938.0` exactly.
5. **Pythia-2.8B weight geometry is best-of-three with no multiplicity policy.** See row 22.
6. **"107×" is against the random max, not the mean.** Against the mean it is 421.97×. Name the divisor or drop the ratio.
7. **The one row whose own source declares non-separability (revision-3 addition).** `docs/working/typed_probe_gate_runlog.md:31-32` states, inside the same block this document quotes for the 91.566% number: "McNemar headline-vs-TF-IDF p=0.289 — on n=83 the probe is NOT statistically separable from a text-only classifier." Revision 2 printed 91.566% beside "TF-IDF 86.747%" and omitted this. It is the single explicit negative-uncertainty finding in the source material for any row in §4.4, and it belongs in a section titled "per-row uncertainty the 2026-07-19 matrix omits."
8. **The two Pythia-160M rows are single-seed and their split is fixed by the fixture, not resampled (revision-3 addition).** F28 `split {train 1344, val 672, test 2352}` out of `n_records 4368`; 40E `split {train 2560, val 1280, test 4480}` out of `n_records 8320`. Neither report carries a seed field or a cross-validation block. Their now-`present` `control_proof` says a character-level arm ran on the same split; it says nothing about seed or split variability.

### 4.6 The v1.0 spec sheet and the five archived investor sheets (revision-3 addition)

Roadmap clause 2 names five claim categories: *"every v1.0, v2.1, investor, engineering, and archived claim."* Revision 2 reconciled three of them (v2.1 — rows 16-17; investor / consolidated current sheet — rows 7, 9-12; engineering — rows 1-8, 13-15, 18-21b) and left **v1.0** and **archived** with zero claim rows. The v1.0 sheet appeared only once, as a count error in §5.3 item 1; the archived sheets appeared only in §6's line-1 banner check. This section closes that omission.

#### 4.6.1 v1.0 — `noetic-compass-scaffold/noetic-compass/research/cas_probe/CAS_HARNESS_SPEC_SHEET_20260517.md`

Front matter at `:1-8` is YAML with `status: Internal — pending IP attorney review before external use`; `:509` reads "Authorization for external use | Pending IP attorney clearance". The document is **not** externally licensed by its own terms — but it is the origin of numbers that later sheets inherited, so its claims need STATUS rows.

| # | Claim wording (quoted, trimmed) | `file:line` | Model | Revision | Evidence tier | Raw artifact | STATUS |
|---|---|---|---|---|---|---|---|
| 24a | "detection above text and metadata baselines (**up to 89.8% on 40 classes, +39.7pp lift**)" | `:521` | `EleutherAI/pythia-160m` | `50f5173d…` | 40E readout vs surface controls | `experiment/cas-probe-pythia:…/stage9_elements_pilot_probe_report_20260517.json` → `headline.test.acc 0.8979910714285714` (89.799% ≈ "89.8%") and `headline.test_acc_lift_over_best_text 0.39709821428571423` (+39.71 pp ≈ "+39.7pp"). Both reproduce. The lift is over `tfidf_char_3_5` (a **character** arm), so this row's `control_proof` is **present** | **supported at Pythia-160M 40E scope.** The sentence's own scope is "two open models (Pythia-160M and Pythia-1B)"; no Pythia-1B 40E artifact exists on any branch (§7 gap 3), so the two-model framing is **overstated** |
| 24b | "**causally load-bearing readout** (collapse to exact chance under ablation)" | `:521` | `EleutherAI/pythia-160m` | `50f5173d…` | Subspace ablation | `stage7_foundation_layer6_ablation_report_20260517.json` → ablated `0.03571428571428571` = exact 1/28; `pythia_ablation_layer3_20260515.json` → `0.10144927536231885` = exact 1/10. Both reproduce | **supported at Pythia-160M scope only** — no ablation artifact exists for Pythia-1B (§7 gap 2), so the "two open models" scope is **overstated** |
| 24c | "likelihood conditioning via the η → ε bridge (**effect doubled from +0.283 to +0.554 at 6× scale, p ≈ 10⁻¹⁴**)" | `:521` | `pythia-160m` → `pythia-1b` | `50f5173d…` → `f73d7dcc…` | η→ε likelihood bridge | Upper endpoint located: `experiment/cas-probe-pythia:…/STAGE8_PYTHIA1B_CPL2_REPORT_20260517.json` → **full field path `conditions.probe_readable.delta_vs_none.mean` = `0.5542184012276785`** (≈ +0.554). **Revision-4 correction — the condition must be named:** the sibling `conditions.gold_readable.delta_vs_none.mean` is `0.5800083705357143`, a different number, so an unqualified "`delta_vs_none.mean`" citation does not identify the figure. The v1.0 sentence says only "+0.554", which matches `probe_readable`. Lower endpoint **`unavailable`**: filename enumeration of the experiment branch returns **14** `cpl2` paths — JSON+MD **report pairs for Stage 8, 14, 15 and 16 only**, plus six `probe_stage*_cpl2.py` scripts. **Revision-4 correction:** revision 3 wrote that reports exist for "Stage 8 / 14 / 15 / 16 / 19D / 19E"; Stage 19D (`probe_stage19D_phi2_cpl2.py`) and 19E (`probe_stage19E_tinyllama_cpl2.py`) are **scripts with no report of any kind**. There is no Pythia-160M CPL2 JSON. The load-bearing conclusion is unchanged. `p ≈ 10⁻¹⁴` not located in any field read this pass | **partially supported** — the +0.554 endpoint reproduces; the +0.283 endpoint and the p-value are `unavailable`, so "effect doubled" is not reproducible from raw artifacts |
| 24d | "clean structural factorization (**lacunarity 0.015–0.021**)" | `:521` | `pythia-160m` | `50f5173d…` | Lacunarity | Self-referential: the only located source for `0.021` is the **same document** at `:83` ("the Foundations axis measured 0.021"). Searched `stage*probe_report*.json` on `experiment/cas-probe-pythia` for `0.015` / `0.021`; the one hit is `stage6_role_bound_full_probe_report_20260516.json`, a **different axis** (role-bound, not Foundations/40E) | **`unavailable`** as a raw-artifact-backed range; the interval's endpoints are not located in a JSON field |
| 24e | "framework-predictive validity (**three preflight predictions held**)" | `:521` | `pythia-160m` | `50f5173d…` | Preregistration | One of the three is documented in-document at `:83` ("The lacunarity preflight prediction … was committed before Stage 7 ran and held"). No dated preregistration artifact enumerating three predictions was located; see §7 gap 14 for the parallel 20B failure | **`unavailable`** — the count "three" is not traceable to a dated artifact |
| 24f | "**Six closed evidence tiers** on two open models" then enumerating **five** | `:521` | n/a | n/a | count | See §5.3 item 1 | **flagged for human review** (arithmetic, not evidence) |
| 24g | "A software service that looks inside **any open-weight large language model** … **proves** the structure is causally load-bearing, and **conditions the model's output**" | `:515` | all | mixed | aggregate | Two prohibited shorthands in one sentence: "works on any open-weight model" (Amazon spec:427) and, in near-form, "controls model output" (Amazon spec:433). Six model points ≠ "any". "Proves … causally load-bearing" is row 24b's claim at a scope row 24b does not support | **overstated** |

#### 4.6.2 The five archived investor sheets under `noetic-compass-scaffold/noetic-compass/docs/marketing/`

All five carry a line-1 banner (verified in §6): v1.6, v1.7, v1.8, v1.9 → `SUPERSEDED 2026-06-04 — contains retracted scoped-ACCEPT and Object-Lock-COMPLIANCE/immutability claims; see v2.0.`; v2.0 → `**SUPERSEDED 2026-06-04 by v2.1** …`. A supersession banner is **not** a claim retraction: the banner names only the ACCEPT and Object-Lock retractions, and every six-model and lab/corpus/language claim inside the bodies is left standing and unannotated.

| # | Claim wording (quoted, trimmed) | `file:line` (all under `…/docs/marketing/`) | Model | Revision | Evidence tier | Raw artifact | STATUS |
|---|---|---|---|---|---|---|---|
| 25 | "empirically confirmed on **six open-weight models across three architecture families** … and on **two independent evidence tiers** (activation-trace and weight-geometry)" | `v1_6…20260527.md:56`; `v1_7…20260528.md:76`; `v1_8…20260528.md:79`; `v1_9…20260530.md:118`; `v2_0…20260604.md:134` | all six | mixed | aggregate | Prohibited verbatim: "'two independent evidence tiers across six models' is prohibited" (`d6069513:…MATRIX_20260719.md:92-93`). Raw position: the **weight-geometry tier exists for one model point only** — `stage14_weight_geometry_alignment_20260519.json`, Pythia-2.8B (§7 gap 4). A tier present on 1 of 6 points cannot be asserted across 6 | **overstated** (five archived surfaces) |
| 26 | "**Mechanism is empirically established as not lab-specific, not training-corpus-specific, not language-specific**, and not scale-bounded below 20B parameters" (and the "not axis-specific" variant) | `v1_6:312`, `v1_6:720`; `v1_7:419`, `v1_7:810`; `v1_8:359`, `v1_8:778`; `v1_9:968`, `v1_9:1498`; `v2_0:986`, `v2_0:1539` | all six | mixed | aggregate | Prohibited verbatim (`matrix:97-98`). Raw position: **every** model point in §4.4 was run on **one frozen English synthetic fixture**, `input_sha256 3e4a1aca…` (§3). One corpus, one language. The claim is contradicted by the fixture's own identity | **overstated** — ten hits across five archived sheets |
| 27 | "\| 'Mechanism is not lab-specific, not corpus-specific, not language-specific, not scale-bounded below 20B' \| **LICENSED** \|" — the prohibited phrase entered in a claim-**status** table as licensed | `v1_6:545` | all six | mixed | governance | Same refutation as row 26. This is the most serious archived hit: it is not prose but a **status assignment**, and the status assigned is the one the project's own 2026-07-19 governance rules prohibit outright | **overstated, and the recorded status is wrong on its face.** An adjacent row in the same table carries the same defect at the six-model scope of rows 2-6: **`v1_6:541`** "The detected structure is causally load-bearing for cognitive readout \| LICENSED". **Revision-4 correction:** revision 3 cited that cell as `v1_6:544`; `:544` is the *cross-architecture* cell ("This works cross-architecture (Pythia + OLMo + Qwen — three independent families) \| LICENSED"). Re-read directly: `:541` causal, `:544` cross-architecture, `:545` lab/corpus/language |
| 28 | "**First ACCEPT verdict** in the project record (PR #107). Scoped to the Stage 9 40E validation packet" and its restatements | **Re-audited in revision 4 — the scope was wrong.** `v1_7:546`, `:604`, `:806`; `v1_8:438`, `:486`, `:522`, `:774`; `v1_9:1052`, `:1178`, `:1220`, `:1492` — **11 lines across three archived sheets**, not four lines in one. `v1_7:24` is a twelfth under a one-token-looser pattern (see §5.2 for the exact patterns and per-file counts) | `gpt-neox-20b` | **`unavailable`** | 40E packet | Prohibited: "'first ACCEPT' / any standing `ACCEPT`" (Amazon spec:434). The verdict was retracted — `withdrawn_stage9_40e_accept`, `accept_revival_allowed: false` (§4.3 row 23), and the live consolidated sheet already strikes it through at `CAS_HARNESS_SPEC_SHEET_current.md:388`. **What is and is not wrong, stated exactly.** The withdrawal **is** applied at document level on every one of these sheets — all three carry the line-1 banner `> SUPERSEDED 2026-06-04 — contains retracted scoped-ACCEPT and Object-Lock-COMPLIANCE/immutability claims; see v2.0.` — and it **is** applied in the current sheets, where the same status row reads `NOT LICENSED — WITHDRAWN in v2.0 (pre-fix overclaim; … no ACCEPT stands)` at `v2_0:1248` and `v2_1:1247`. What is left standing is **row-level**: two status-table cells, `v1_8:522` and `v1_9:1220`, both reading `\| "First ACCEPT verdict in project record on Stage 9 40E validation packet" \| LICENSED with explicit scope \|`, unstruck and unannotated inside superseded files. That is a **row-level tombstone gap in archived files, not a live overclaim**. `v1_7:604` is *not* one of them — it reads "scoped explicitly and not licensed as a production verdict" — and `v1_7:546` records the status as "Closed (v1.7)", not LICENSED | **withdrawn** — retracted at document level by banner and corrected in the current sheets, but two archived row-level `LICENSED` cells for the withdrawn verdict remain (§9.1) |
| 29 | "The 20B chain closes on two cognitive axes: Foundation-28 … and 40-Element …" together with "Causal localization is empirically established at head-level … and sparse MLP-neuron-cover-level" | `v1_7:82` (representative; the same paragraph recurs across the archived family) | all six / `gpt-neox-20b` | mixed | aggregate | Prohibited verbatim (`matrix:99`, and `matrix:94-96` for the causal-establishment clause). Raw position: the 20B 40E preregistered gate was **missed** (rows 6/20/21), and the sparse cover is Pythia-160M-only (row 7) | **overstated** |

**Why this section does not change the item verdict.** Every row here is `overstated`, `unavailable`, or `withdrawn`. Adding the two missing roadmap categories moves clause 2 from *three of five* to *five of five* reconciled, but it adds no `supported` row except 24a and 24b at Pythia-160M scope — which are the same two artifacts §4.4 already carried. Clause 3 remains untouched; see §9.1.

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

**`docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:308`** (revision-3 addition — the prohibited phrase revision 2 reported as absent; the same sentence is also at `project_handoffs/…/HISTORICAL_CLAIM_AND_AUDIT_CONTEXT/CAS_HARNESS_SPEC_SHEET_current.md:308`)
- Live: "Both canonical methods replicate at 20B parameter scale without protocol adjustment. The mechanism is empirically established as **not lab-specific, not corpus-specific, not language-specific, not scale-bounded below 20B, and not axis-specific.** Cross-architecture closure on Foundation-28 holds across three independent families (Pythia / GPT-NeoX, OLMo, Qwen)."
- Supported replacement: *"Both canonical methods ran at 20B parameter scale without protocol adjustment. Foundation-28 held-out readout replicates across three independent model families. Every model point was evaluated on a single frozen English synthetic fixture (`input_sha256 3e4a1aca…`), so no corpus-independence or language-independence claim is supported: one corpus, one language, no cross-corpus or cross-language arm was run. Lab-independence is supported only in the weak sense that the six model points were released by three different organisations; the evaluation fixture, protocol and labels are ours throughout. Axis-independence is not supported — the 40-Element preregistered causal gate at 20B was missed."*

**`docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:59`** (revision-3 addition — the second prohibited phrase revision 2 reported as absent; the same sentence recurs at marketing `v1_6:56`, `v1_7:76`, `v1_8:79`, `v1_9:118`, `v2_0:134`, `v2_1:133`)
- Live: "The prediction has been empirically confirmed on **six open-weight models across three architecture families** … and on **two independent evidence tiers** (activation-trace and weight-geometry)."
- Supported replacement: *"The prediction has been empirically tested on six open-weight model points across three architecture families on the activation-trace tier. The weight-geometry tier exists for one model point only (Pythia-2.8B), where one of three checks — output logit-lens energy fraction, 2.8305× random, empirical p = 0.0099 — is materially above 100 same-rank random controls and the other two are not (1.0621×, p = 0.0099; 1.0033×, p = 0.3465). A second evidence tier on one of six points does not support a two-tier claim across six."*

**`docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:282`** (revision-3 addition — the "pre-registered" attribution, and a second live surface for the five-axes claim)
- Live: "**Five axes pass collapse-to-exact-chance under subspace ablation with clean random nulls.** … The **pre-registered** ≥30 pp / ≤65% gate was narrowly missed by 1.27–1.90 pp on each disjunct; documented openly."
- Supported replacement: *"Three axes have been verified this pass to collapse to exact chance under subspace ablation with clean random nulls, all on Pythia-160M: noetic (layer 3, 89.855% → 10.145% = exact 1/10); role-bound (layer 5, → 10.0%, random disruption 0.0, empirical p = 0.0323); Foundation-28 (layer 6, 78.571% → 3.571% = exact 1/28, random disruption 0.0, empirical p = 0.0323, all three preregistered `decision_gates` met). No single artifact enumerates five. The 40-Element axis at GPT-NeoX-20B does **not** collapse to chance: it falls to 66.897% against a 2.5% chance baseline. The 20B ≥30 pp / ≤65% threshold was missed on both disjuncts; the threshold is documented only in claim documents written after the outcome, so it should be described as a stated gate, not a pre-registered one, until a dated artifact is produced."*

**`docs/working/paper_b_causal_localization_draft_outline_20260523.md:56`**
- Live: "Weight-geometry: 2.83× random (p = 0.0099)."
- Supported replacement: *"Static weight geometry on Pythia-2.8B, three checks against 100 same-rank random controls: output logit-lens energy fraction 2.8305× random (empirical p = 0.0099); output weight energy fraction 1.0621× (p = 0.0099); input weight energy fraction 1.0033× (p = 0.3465, not above random). One of three checks is materially above control; no multiplicity correction was applied. This supports a bounded alignment-inspection claim, not generation control."*

### 5.2 Prohibited-phrase register (merged, deduplicated) and live violations

From `d6069513:…/CAS_HARNESS_CLAIM_EVIDENCE_MATRIX_20260719.md:92-100` and `project_handoffs/…/CAS_HARNESS_AMAZON_TECHNICAL_EVALUATION_SPEC_20260721.md:426-434`.

**Search method (revision-3 correction).** Revision 2 recorded "none found this pass" against eight rows. Three of those were wrong. Revision 3 re-ran the register with a recursive case-insensitive content search across `docs/`, `noetic-compass-scaffold/noetic-compass/docs/marketing/`, `noetic-compass-scaffold/noetic-compass/research/cas_probe/` and `project_handoffs/`, over `*.md`, using each phrase's distinctive substring rather than the full sentence, and inspecting each hit to classify it as an **assertion** or as an entry in a NOT-LICENSED / prohibition table. Only assertions count as violations. Line numbers below were read directly.

**Inclusion rule (stated in revision 4; revision 3 applied two different rules to the same file).** The counted surface set is: the live legal-drafts sheet `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md`; the six marketing sheets `v1_6` … `v2_1`; the v1.0 research sheet `…/research/cas_probe/CAS_HARNESS_SPEC_SHEET_20260517.md`; the live engineering surfaces named in §5.1; and **the `project_handoffs/…/HISTORICAL_CLAIM_AND_AUDIT_CONTEXT/` snapshot copy of the live sheet**, which is counted because it was distributed as part of the 2026-07-21 handoff and therefore carries the phrase to a reader independently. Revision 3 counted that snapshot inside the lab/corpus/language row and omitted it from the tiers row; revision 4 counts it in both. **Excluded, and named so the exclusion is not a hidden omission:** the machine-converted derivatives under `…/research/cas_probe/graphify-out/converted/`, which hold four pre-v1.6 sheet versions (`v1_2` … `v1_5`) carrying **16** further hits of the lab/corpus/language phrase and **0** of "first ACCEPT". They are tool output re-derived from sheets that predate the archived family this document reconciles, they are not a distribution surface, and no row below counts them.

| Prohibited phrase | Source rule | Live violations found on disk |
|---|---|---|
| "two independent evidence tiers across six models" | matrix:92-93 | **REVISION-3 CORRECTION — revision 2 said "none found." Count corrected in revision 4: 7 → 8.** 8 assertions, each combining "six open-weight models across three architecture families" and "two independent evidence tiers (activation-trace and weight-geometry)" **in one sentence**: `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:59`; **its `project_handoffs/…/HISTORICAL_CLAIM_AND_AUDIT_CONTEXT/CAS_HARNESS_SPEC_SHEET_current.md:59` snapshot copy (added in revision 4 under the inclusion rule above — revision 3 counted this same snapshot in the lab/corpus/language row and omitted it here)**; marketing `v1_6:56`, `v1_7:76`, `v1_8:79`, `v1_9:118`, `v2_0:134`, `v2_1:133`. Re-run: `grep -rn "two independent evidence tiers" --include=*.md` over the counted surface set returns exactly these 8. Refuted by §7 gap 4 — the weight-geometry tier exists for Pythia-2.8B only |
| "Presence, causal role, and conditionability across six models" | matrix:94-96 | `CAS_HARNESS_SPEC_SHEET_current.md:83`; `cas_harness_synopsis_20260630.md:24` |
| "Not lab-specific, not corpus-specific, not language-specific" | matrix:97-98 | **REVISION-3 CORRECTION — revision 2 said "none found."** 15 hits: 14 assertions plus one status-table entry. Live/current: `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:308`; its snapshot copy `project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/03_RESEARCH_AND_ARCHITECTURE_DOCS/HISTORICAL_CLAIM_AND_AUDIT_CONTEXT/CAS_HARNESS_SPEC_SHEET_current.md:308`; marketing `v2_1:985` and `v2_1:1547`. Archived: `v2_0:986`, `v2_0:1539`; `v1_9:968`, `v1_9:1498`; `v1_8:359`, `v1_8:778`; `v1_7:419`, `v1_7:810`; `v1_6:312`, `v1_6:720`. **Plus one status-table entry recording the phrase as `LICENSED`: `v1_6:545`** (§4.6.2 row 27). Refuted by the fixture identity: one frozen English synthetic corpus, `input_sha256 3e4a1aca…`, on every model point |
| "The 20B chain closes on two axes" | matrix:99 | `CAS_HARNESS_SPEC_SHEET_current.md:28,67`; `cas_harness_synopsis_20260630.md:85`; `cas_harness_executive_summary_20260630.md:17`; v2.1 marketing sheet `:146,158`; archived `v1_7:82`, `v1_8:92`, `v1_9:131` and `v2_0:147` (**revision-4 addition — revision 3 enumerated only `v1_7:82` and referred to "the recurring archived paragraph" without line numbers, which is not re-runnable**; `grep -rn "chain closes on two" *.md` under `…/docs/marketing/` returns exactly `v1_7:82`, `v1_8:92`, `v1_9:131`, `v2_0:147`, `v2_1:146`) (§4.6.2 row 29) |
| "Every verdict is validated causally" | matrix:100 | `CAS_HARNESS_SPEC_SHEET_current.md:522` |
| "causally validated across six models" | Amazon spec:426 | `cas_harness_amazon_review_brief_20260615.md:54`; `cas_harness_executive_summary_20260630.md:12,14`; archived **`v1_6:541`** records the causal clause as `LICENSED` in a status table (**revision-4 correction — revision 3 cited `:544`, which is the cross-architecture cell**) |
| "works on any open-weight model" | Amazon spec:427 | **REVISION-3 CORRECTION.** One assertion, in near-verbatim form: `noetic-compass-scaffold/noetic-compass/research/cas_probe/CAS_HARNESS_SPEC_SHEET_20260517.md:515` — "looks inside **any** open-weight large language model" (§4.6.1 row 24g). The one other hit, `docs/working/CAS_HARNESS_JSPACE_OHM_300B_CAPABILITY_ANALYSIS_20260720.md:84`, is a **denial** of the claim, not an assertion |
| "universal interpretability" | Amazon spec:428 | **none as an assertion.** All 8 hits are NOT-LICENSED table entries — `CAS_HARNESS_SPEC_SHEET_current.md:455` and the matching row in each marketing sheet, each reading "\| 'Universal interpretability platform' \| NOT LICENSED (three families ≠ universal) \|". Correctly recorded, correctly bounded |
| "validated at 300B" | Amazon spec:429 | **none as an assertion.** One hit, `CAS_HARNESS_SPEC_SHEET_current.md:441`, is the prohibition itself: "NOT LICENSED — 300B is ENGINEERED, NOT VALIDATED" |
| "immutable WORM evidence" | Amazon spec:430 | **`unavailable` — still not searched exhaustively.** The one hit read this pass, `docs/working/cas_harness_production_todo.md:2788`, is an engineering status entry that hedges correctly ("does not create customer-production `ACCEPT`"). The marketing surfaces carry Object-Lock/immutability language that the archived line-1 banners already name as retracted; a full audit of that phrase family is out of this item's scope and is recorded as a gap, not as a clean negative |
| "independently reproducible" when required raw artifacts are absent | Amazon spec:431 | **the whole tree is in violation** — see §2 |
| "prompt-injection detector" as a closed product capability | Amazon spec:432 | **none as an assertion.** All hits read this pass are denials or NOT-LICENSED records: `CAS_HARNESS_JSPACE_OHM_300B_CAPABILITY_ANALYSIS_20260720.md:377` ("not a validated prompt-injection detector"); `cas_harness_production_todo.md:16570, :16868` (both keep it `OPEN` / `NOT LICENSED`); `cas_harness_topos_instruction_integrity_roundtable_20260610.md:103`. `CJT_PCBA_IMPLEMENTATION_BLUEPRINT.md:286` is a design-section heading, not a capability claim |
| "controls model output" as a general capability | Amazon spec:433 | **REVISION-3 CORRECTION.** No verbatim hit. One near-form assertion: `CAS_HARNESS_SPEC_SHEET_20260517.md:515` — "conditions the model's output" presented as a delivered service property (§4.6.1 row 24g). Recorded as near-form, not verbatim, because the distinction between conditioning likelihood and controlling output is exactly what the rule protects |
| "first ACCEPT" / any standing `ACCEPT` | Amazon spec:434 | **REVISION-4 RE-AUDIT — revision 3 said "4 assertions, all in the archived v1.7 sheet body: `v1_7:24`, `:82`, `:94`, `:546`." That is wrong three ways: `:82` and `:94` do not carry the phrase at all (they are the six-model and probing-chain paragraphs), and the phrase is live in v1.8 and v1.9 as well.** Re-counted with a stated pattern. **Pattern A, exact phrase `First ACCEPT verdict in project record`**, counted per file with `grep -c` under `…/docs/marketing/`: **v1_6 = 0, v1_7 = 3, v1_8 = 4, v1_9 = 4, v2_0 = 3, v2_1 = 3.** Lines — v1_7 `:546`, `:604`, `:806`; v1_8 `:438`, `:486`, `:522`, `:774`; v1_9 `:1052`, `:1178`, `:1220`, `:1492`; v2_0 `:1071`, `:1205`, `:1248`; v2_1 `:1070`, `:1204`, `:1247`. **Pattern B, the one-token-looser `First ACCEPT verdict`**, adds exactly one line, `v1_7:24` ("**First ACCEPT verdict** in the project record (PR #107)"), which is the line §4.6.2 row 28 quotes; per-file it gives v1_7 = 4 and is otherwise identical. **Violations = 11** (Pattern A; 12 under Pattern B): v1_7 3 + v1_8 4 + v1_9 4. **The 6 v2_0/v2_1 hits are not violations** — all six are struck through and their status cells read `NOT LICENSED — WITHDRAWN in v2.0 (pre-fix overclaim; … no ACCEPT stands)` at `v2_0:1248` / `v2_1:1247`; they are the retraction, correctly recorded. **Two of the 11 are row-level `LICENSED` cells** — `v1_8:522` and `v1_9:1220`, both `\| "First ACCEPT verdict in project record on Stage 9 40E validation packet" \| LICENSED with explicit scope \|`. All three violating files carry the line-1 banner naming the scoped-ACCEPT retraction, so this is a **row-level tombstone gap in superseded archived files, not a live overclaim** (§4.6.2 row 28; work order at §9.1). Note on a rejected count: an earlier review reported "11 such lines in v1.7 alone" plus 6 each in v1.8/v1.9; that is not reproducible with either pattern above and is **not** carried here. The live consolidated sheet is clean — `CAS_HARNESS_SPEC_SHEET_current.md:388, :450, :487` all strike it through and record the withdrawal. Historical packet bytes retain `ACCEPT` by design (§4.3 row 23) |

**Net effect of the re-run.** Three rows moved from "none found" to a populated violation list, one row moved from "none found" to a near-form violation, one moved from "none found" to an exhaustively-checked clean negative with the hits enumerated, and one ("immutable WORM evidence") is now honestly marked `unavailable` rather than left as an unlabeled non-search. All movement in this table is toward **more** violations, i.e. **less** licensed claim surface.

**The headline number, defined and derived (revision 4).** Revision 3 stated this quantity three incompatible ways — "30 additional line-level violations" in the revision-3 note, "Twenty-two new prohibited-phrase violations" in §10, and "22 line-level hits in §5.2" in §6 — and none of the three was derivable from the table. One definition now governs, and every other place quotes it.

> **N₃₋₄ = the count of line-level violations recorded by rows this document's re-runs moved off "none found this pass" / "none live".** It is the sum of those rows' own enumerations, and only those rows: **8** ("two independent evidence tiers", corrected 7 → 8 by the inclusion rule) **+ 15** ("not lab-specific …", 14 assertions + the `v1_6:545` status cell) **+ 1** ("works on any open-weight model", near-verbatim) **+ 1** ("controls model output", near-form) **+ 11** ("first ACCEPT", Pattern A; 12 under Pattern B) = **36**.

Two quantities that are **not** N₃₋₄ and must not be conflated with it: the number of §5.2 register rows carrying any violation (**10 of 14**, unchanged — the four remaining are the three clean negatives plus the `unavailable` WORM row), and the subset of N₃₋₄-and-earlier line-level hits that sits inside the four banner-carrying archived sheets v1.6–v1.9 (**28**, derived in §6).

### 5.3 Flagged for human review — internal inconsistencies, not evidence overstatements

Both directions of error appear. **None of these three is an overstatement of evidence** — items 1 and 2 are internal arithmetic that a reviewer will catch, and item 3 (added in revision 3) is a cross-run numeric conflict where both numbers are real and neither is inflated. They are grouped here because each requires a human decision this document cannot make on its own authority.

1. `noetic-compass-scaffold/noetic-compass/research/cas_probe/CAS_HARNESS_SPEC_SHEET_20260517.md:521` — "**Six closed evidence tiers** on two open models (Pythia-160M and Pythia-1B)" then enumerates **five** in the same sentence (detection; causally load-bearing readout; likelihood conditioning; clean structural factorization; framework-predictive validity). Note this "six" counts **tiers on two models**, not six model points; it must never be conflated with the six-model claim.
2. `docs/legal_drafts_20260607/CAS_provenance_preprint_updated.md:19` and `:97` — "Across **five model points** spanning three independent architecture families (EleutherAI Pythia/GPT-NeoX at four scales, AI2 OLMo, Alibaba Qwen)" while enumerating **six** (160M, 1B, 2.8B, 20B, OLMo, Qwen). Understating, in a patent-adjacent legal draft.
3. **Pythia-160M 40-Element: 89.799% vs 91.719% — two different numbers for the same axis, model, and `n_test`** (announced in the revision-2 note, written here in revision 3). Both trace to real runs; neither is fabricated; they are **not the same run**:

   | Number | Artifact | Selected layer | `n_train` / `n_test` | Text control recorded |
   |---|---|---|---|---|
   | **89.799%** (`0.8979910714285714`) | `experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/stage9_elements_pilot_probe_report_20260517.json`, `headline` block, `readout "focus_token"`, `status "STAGE9_40_ELEMENTS_READOUT_PASS_CLEAN"` | **5** | 2560 / 4480 | `tfidf_char_3_5` 0.5008928571428571 — **character-level** |
   | **91.719%** (`0.9171875`) | `master:noetic-compass-scaffold/noetic-compass/docs/working/pythia160m_gate1/pythia160m_stage9_40e_40_element_probe_eval_report.json`, `best_layer` block, `status "packet_ready_evaluation_completed"` | **3** | 3840 / 4480 | `text_hash_baseline` 0.5 (HashingVectorizer 1-2 ngrams — **word-level**); `confirmed_text_baseline_report: null` |

   Same axis, same model, same `n_test` of 4480, **different `n_train` (2560 vs 3840), different selected layer, different control suite.** They are the original Stage 9 pilot and a later regenerated Gate-1 packet, not a discrepancy inside one run.

   **What revision 2 got wrong:** it printed the 89.799% number and cited "regenerated packet on `master:…/pythia160m_gate1/`" as its artifact. That directory reports 91.719%. The number was right; the attribution was wrong. §4.4 now cites `stage9_elements_pilot_probe_report_20260517.json` and says explicitly that it is not the gate1 packet.

   **Why this is flagged rather than resolved:** nothing located this pass states which run is the project's authority for the Pythia-160M 40E row, and the two runs disagree by 1.92 pp with different training-set sizes. The v1.0 spec sheet's "up to 89.8% on 40 classes" (§4.6.1 row 24a) inherits the **pilot** number. A human must decide which run is canonical; this document does not pick one. Until it is picked, any downstream document citing a Pythia-160M 40E accuracy must name the artifact it means.

---

## 6. Banner-state correction

`docs/working/cas_harness_production_todo.md:2331-2332` asserts: "May/June historical sheets carry superseded/withdrawn banners; v2.1 and the consolidated current sheet are no longer claim authority."

**Verified false in the working tree.** Read directly on 2026-07-24:

- `…/marketing/CAS_HARNESS_SPEC_SHEET_v2_1_INVESTOR_EXTERNAL_NDA_20260604.md` lines 1-8 carry a v2.1-supersedes-v2.0 note only — **no withdrawal banner**. The string `WITHDRAWN FOR EXTERNAL RELIANCE` returns zero matches under `noetic-compass-scaffold/noetic-compass/` on disk; it exists only in `d6069513`.
- `…/research/cas_probe/CAS_HARNESS_SPEC_SHEET_20260517.md` lines 1-8 are YAML front matter with `status: Internal — pending IP attorney review before external use` — **no superseded banner**, contrary to the matrix's own governance rule at `d6069513:…MATRIX_20260719.md:90-91`.
- `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md` lines 1-10 carry no distribution-paused banner.
- Banners **are** present on the older sheets: v1.6, v1.7, v1.8, v1.9 (`SUPERSEDED 2026-06-04 — contains retracted scoped-ACCEPT and Object-Lock-COMPLIANCE/immutability claims; see v2.0.`) and v2.0 (`**SUPERSEDED 2026-06-04 by v2.1** — adds §9.8.1 uniqueness claim posture …`), each at line 1.

**Revision-3 qualifier: a supersession banner is not a claim retraction.** The four v1.6-v1.9 banners name exactly two retracted claim families — scoped-ACCEPT and Object-Lock/immutability. They say nothing about the six-model causal claims, the "two independent evidence tiers" claim, or the "not lab-specific / not corpus-specific / not language-specific" claim, all of which stand unannotated inside those bodies (§4.6.2 rows 25-29, and **28** line-level hits in §5.2). **Revision-4 correction and derivation** — revision 3 wrote "22" with no derivation. This number is the v1.6–v1.9 subset of §5.2's enumerated hits, and it is **not** N₃₋₄ (=36, §5.2), which counts all surfaces: "two independent evidence tiers" `v1_6:56`, `v1_7:76`, `v1_8:79`, `v1_9:118` = **4**; "not lab-specific …" `v1_6:312`, `:545`, `:720`, `v1_7:419`, `:810`, `v1_8:359`, `:778`, `v1_9:968`, `:1498` = **9**; "the 20B chain closes on two axes" `v1_7:82`, `v1_8:92`, `v1_9:131` = **3**; the causal `LICENSED` cell `v1_6:541` = **1**; "first ACCEPT" `v1_7:546/:604/:806`, `v1_8:438/:486/:522/:774`, `v1_9:1052/:1178/:1220/:1492` = **11**. 4+9+3+1+11 = **28**. The v2.0 banner is narrower still: it points to v2.1 and states "All five v2.0 corrected claim boundaries are unchanged." A reader who takes "SUPERSEDED" as "claims withdrawn" will be wrong about every claim except ACCEPT and Object-Lock. §6 checked line 1 and stopped there; §4.6.2 checks the bodies.

The discrepancy is recorded here, not silently patched into the todo. Anyone who treats `todo:2331-2345` as the current state will build on a false premise.

---

## 7. Gaps register — `unavailable`, with the exact search performed

Each of these is a valid negative result, re-runnable by an external reviewer.

**Method correction (revision 3).** Revision 1 established several of these negatives by **string grep**, which is refutable by a single rounding difference — that is exactly how it missed the Stage 7 ablation JSON (it grepped `0.0323`; the JSON stores `0.03225806451612903`). Every gap below has now been re-established by **filename enumeration**, which cannot miss a file because of its contents:

```
git ls-tree -r --name-only experiment/cas-probe-pythia
git ls-tree -r --name-only master
```

filtered per gap on `ablation`, `stage7_foundation`, `stage9`, `40e|element`, `evidence_packets`, `pythia160m_gate1`, `weight_geometry`, `cpl2`, `prereg`. Where enumeration located a candidate, the file was then opened and its fields read. Gaps that survived enumeration are marked **re-established**; gaps that did not are marked **withdrawn**.

1. **GPT-NeoX-20B model revision.** Searched `master:…/gpt_neox_20b_stage9_original_40e_capture_metadata_20260527.json` (`"model_revision": null`), the 40E probe eval report, the 40E subspace ablation report, and `master:…/S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json` (`model.model_revision = None`; only `model_key`/`model_type` populated). Corroborated by `project_handoffs/…/CAS_HARNESS_AMAZON_CLAIM_EVIDENCE_MANIFEST_20260721.json`, which sets `exact_revisions_available: false`. → **`unavailable`. Not recoverable without a re-capture.**
2. **Model-specific F28 causal evidence for Pythia-1B, Pythia-2.8B, OLMo-1B, Qwen2.5-1.5B.** **Re-established by enumeration (revision 3).** `git ls-tree -r --name-only experiment/cas-probe-pythia | grep -i ablation` returns **29 paths** (**revision-4 correction — revision 3 printed 24, which does not reproduce**; the six unlisted paths are the `decode_ablations` family: `docs/working/candidate_a_decode_ablations_2026_05_11.json`, `docs/working/candidate_b3/decode_ablations.json`, `docs/working/candidate_c/decode_ablations.json`, `docs/working/diagnostic_replay_decode_ablations_2026_05_11.json`, `…/cas-native/evaluation/decode_ablations.py`, `…/cas-native/tests/evaluation/test_decode_ablations.py` — all CAS-Native decoder studies, **none is a model ablation report**, so the gap's conclusion is unchanged); every ablation *report* among the 29 is Pythia-160M — `pythia_ablation_layer3_20260515.json`, `…_continuation_20260515.json`, `…_per_class_layer3_20260515.json`, `…_per_class_layer3_clean_20260516.json`, `…_random_control_layer3_20260516.json`, `…_random_control_layer3_n30_20260516.json`, `pythia_ablation_domain_layer5_n30_20260516.json`, `stage6_role_bound_layer5_ablation_report_20260516.json`, `stage7_foundation_layer6_ablation_report_20260517.json`, `stage9_factor_ablation_report_20260517.json`, plus `stage22_cas_harness_ablation_{bench,prereg}_20260519.json` (a harness-condition study, not a model ablation). The same command on `master` returns only the 20B report and the two `pythia160m_gate1/` reports. **No ablation report names Pythia-1B, Pythia-2.8B, OLMo-1B or Qwen2.5-1.5B on any branch.** → **`unavailable`**, matching the 2026-07-19 matrix's "Not located."
3. **40E-axis evidence for Pythia-1B, Pythia-2.8B, OLMo-1B, Qwen2.5-1.5B.** **Re-established by enumeration (revision 3).** `git ls-tree -r --name-only experiment/cas-probe-pythia | grep -iE "40e|element"` returns 18 paths: the Stage 9 elements family (fixture builder, capture script, `stage9_elements_pilot_probe_report_20260517.json`, manifests, `STAGE9_40_ELEMENTS_{GATES,PROBE_REPORT}_20260517.md`), the Stage 24B token-sonar family, and their tests. All are Pythia-160M. On `master`, the 40E artifacts are the `gpt_neox_20b_stage9_original_40e_*` family and `pythia160m_gate1/`. → **`unavailable`**
4. **Static-weight-geometry tier for every model point except Pythia-2.8B.** `stage14_weight_geometry_alignment_20260519.json` is the only such artifact on any branch. → **`unavailable`**
5. **Character-level n-gram surface control at GPT-NeoX-20B — both axes.** **Re-established and widened (revision 3).** Read the `controls` block of `master:…gpt_neox_20b_stage9_original_40e_probe_eval_report_20260527.json` in full: `confirmed_text_baseline_report` (CountVectorizer 1-2 grams, 0.4924107142857143), `text_hash_baseline` (HashingVectorizer 1-2 ngrams, 2^14, 0.5), `majority_class_test_acc`, `shuffled_label_hidden_best_layer` (20 trials). No arm declares `analyzer='char'`. The **F28** side is worse: `master:…/S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json` reports **no text control at all** against its headline `readout.heldout_accuracy 0.868622` — the only text figure in the packet is `readout.legacy_centroid_context.text_hash_centroid_test_acc 0.422811`, explicitly retained as "cover-discovery context" for a superseded centroid method. → **`control_proof: partial`** on both 20B rows. Under the project's standing char-level-surface-control rule, no hidden-beats-surface framing of either 20B row is supported. **Scope note:** this gap is now 20B-only. Both Pythia-160M rows do have a character arm (`tfidf_char_3_5`) and are `present`; see §4.4.
6. **Cross-seed variation for every F28 and 40E row.** All four located F28 reports share one fixed split (1344/672/2352); the 20B 40E report pins `seed: 2026` with `"split": "fixed split by metadata.split; test_split=test"`. → **`unavailable`**
7. **~~Machine-readable JSON for the Pythia-160M F28 causal PASS.~~ GAP WITHDRAWN — this was a false negative.** Revision 1 searched `git grep -l "0.0323"` plus `"78.57"`/`"3.57"` variants across `experiment/cas-probe-pythia`, `master` and HEAD, restricted to `*.json`, and concluded "prose-backed, not artifact-backed." **That conclusion is wrong and is retracted.** Filename enumeration finds it in one command: `git ls-tree -r --name-only experiment/cas-probe-pythia | grep stage7_foundation` returns 14 paths including **`noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_layer6_ablation_report_20260517.json`** and **`…/stage7_foundation_pilot_probe_report_20260517.json`**. Both were opened and their fields are quoted at §4.1 row 1 and §4.4 respectively. The grep failed because the JSON stores `0.03225806451612903` and the markdown rounds it to `0.0323` — a rounding difference, not an absence. **Root-cause lesson, recorded so it is not repeated:** a negative established by string grep is refutable by rounding, formatting, or key naming; negatives in this document are now established by filename enumeration first, content read second. Nothing about the Pythia-160M F28 causal result is prose-only: it has a machine-readable report **and** a preregistered `decision_gates` block.
8. **The locked Pythia-160M F28 activation binary.** `STAGE7_FOUNDATION_ABLATION_REPORT_20260517.md` records SHA-256 `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f` and states the ~304 MB artifact "lives on RunPod only." The file at `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_pilot_activations_20260517.npz` on disk (317,617,680 bytes) hashes to `f63a66de86366a63ea0fd786ad0dc0bef68d5634be3b5fae525d4fb667f14d53` — **a different artifact.** This is already documented by the project at `experiment/cas-probe-pythia:…/research/cas_probe/README.md:2500-2512` as a local CPU recapture with `Formal gate valid: false`. → the locked binary is **`unavailable`**; the on-disk file is a recapture and must not be cited as the Stage 7 artifact.
9. **Eight of fifteen Amazon-manifest evidence artifacts.** Re-checked every `path` in `evidence_artifacts` against the working tree: all six `gpt_neox_20b_*` and all four `pythia160m_gate1/*` entries are **absent from the current checkout** (present on `master`). The five `C:/tmp/cas-tks-anchor-diagnostic-20260721/…` entries are present on disk.
10. **The two corrected-PDF SHA-256 values asserted at `docs/working/cas_harness_production_todo.md:2343` and `:2345`.** Grepped both hashes repo-wide; they appear only as prose in that file and in `project_handoffs` snapshots of it. The PDFs named in `d6069513` are not on disk. → **neither hash independently verified. Do not cite them as evidence.**
11. **Per-model evidence packets.** **Re-established by enumeration (revision 3).** `git ls-tree -r --name-only experiment/cas-probe-pythia | grep -i evidence_packets` returns exactly 8 paths — four packets in `.json`/`.md` pairs: `stage21a_allow_qwen15b_000`, `stage21a_caveat_olmo1b_009`, `stage21a_constrain_olmo1b_054`, `stage21a_suppress_olmo1b_054`. They cover OLMo-1B and Qwen2.5-1.5B only, are Stage 21a steering packets rather than readout/causal evidence packets, and live only on `experiment/cas-probe-pythia`. The directory exists on disk at HEAD but its contents are untracked there. → **`unavailable` at HEAD; no per-model readout evidence packet exists on any branch for Pythia-1B or Pythia-2.8B.**
12. **Independent object-store / third-party escrow mirror** for the 2026-07-21 definition-anchor bundle. Recorded by the Amazon manifest itself as `pythia160_tks_anchor_independent_object_store`, `availability: unavailable`, `status: OPEN`. → **`OPEN`**
13. **`gpt20_f28_source_archive`** (`C:/tmp/gpt_neox_20b_foundation28_and_40element_20260526`). Declared `availability_in_protected_tree: unavailable` by the Amazon manifest; not re-checkable from the repo. → **`unavailable`**
14. **A dated preregistration artifact for the 20B 40E "≥30 pp drop / ≤65% floor" gate.** *(Referenced twice in revision 2 and never written; written here in revision 3. This is the gap that forces the §9 downgrade.)* Rows 6, 20 and 21, and §9's fourth exit cell, all turn on that threshold having been **preregistered** and then missed. Searched:
    - The full key list of `master:…/gpt_neox_20b_stage9_original_40e_subspace_ablation_report_20260528T0155Z.json`: `ablation_tier`, `axis`, `base_method_label`, `chance_baseline`, `created_at`, `dataset_summary`, `important_limit`, `method_contract`, `method_label`, `packet_decision`, `per_layer`, `primary_result`, `provenance`, `reference_probe_report`, `schema_version`, `split`, `status`. **There is no gate, threshold, criterion, or preregistration field.**
    - Repo-wide for the threshold text (`≥ 30 pp`, `65% floor`, `min_drop_pp`, `floor_accuracy`) across `docs/`. **Two hits, both claim documents written after the outcome:** `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:282` and `docs/working/cas_harness_synopsis_20260630.md:101`.
    - Filename enumeration for preregistration artifacts: `git ls-tree -r --name-only experiment/cas-probe-pythia | grep -i prereg` returns `STAGE22_CAS_HARNESS_ABLATION_PREREG_20260519.md`, `stage22_cas_harness_ablation_prereg_20260519.json`, `run_stage22_harness_ablation_prereg.py`, and `stage24b_40_element_cpu_recap_prereg_20260521.json`. The Stage 22 file **was opened**: its keys are `claim_boundary`, `conditions`, `default_customer_mode`, `metrics`, `naming_boundary`, `schema_version`, `scope`, `stage22_1_followup`, `validation`, and its `conditions` describe a harness-layer ablation study (floor raw model / bridge only / mode selector BALANCED / HIGH_PRECISION). **It is a different experiment and contains no 20B subspace-ablation threshold.** It is also dated 2026-05-19, nine days before the 20B run.

    → **`unavailable`.** The threshold may well have been fixed in advance — the project's discipline elsewhere is real, and the Pythia-160M ablation report the same team wrote *does* carry a machine-readable `decision_gates` block. But no dated artifact establishes it for the 20B gate, and the exit clause says *"criteria are not rewritten after outcomes are known."* A criterion evidenced only by post-outcome prose cannot be scored as satisfying that clause. **Cheapest fix available, and it requires no compute:** add a `decision_gates` block to the 20B report in the same shape as `stage7_foundation_layer6_ablation_report_20260517.json`, dated and signed, stating that it records a threshold fixed on a named earlier date — or, if no such date can be evidenced, restate the 20B result without the word "pre-registered."
15. **Cross-run reconciliation for the Pythia-160M 40E axis.** Two runs report 89.799% (layer 5, `n_train` 2560) and 91.719% (layer 3, `n_train` 3840) on the same `n_test` of 4480; see §5.3 item 3. Searched both artifacts' `provenance`/`method_contract`/`status` fields and the surrounding directories for a statement of which run supersedes which. **None found.** → **`unavailable`; flagged for human review, not resolvable by this document.**

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
| `control_proof: present` where controls ran | **MIXED** (cell **re-derived** in revision 3) | Revision 2 scored this on rows that were misclassified. Re-derived from the corrected §4.4: **`present` on six rows** — Pythia-160M F28 (`tfidf_char_3_5` 0.4966) and Pythia-160M 40E (`tfidf_char_3_5` 0.5009), both **upgraded in revision 3**; the 20B 40E causal random-control axis; the Pythia-2.8B weight-geometry random controls (`n_random 100`); and the two universality-program rows that ran char n-grams. **`partial` or `unavailable` on eight rows** — the 20B 40E readout (word arms only), the 20B F28 readout (no text control at all against the headline number), the four non-160M F28 rows (no control block in the artifact), and the typed Qwen-Instruct row (word-level, and its own source records `p = 0.289`, not separable). The cell stays **MIXED**: the correction improves it materially but the largest-scale rows — the ones the headline claims lean on — are still the unproven ones. |
| Independently reproducible raw evidence | **NOT SATISFIED** | The branch split (§2). No checkout reproduces one row end to end. |
| Verdict consistent with preregistered criteria | **PARTIAL** (**downgraded from SATISFIED in revision 3**) | The verdicts are negative and no criterion was rewritten — that much holds. **Where it is satisfied, with a located preregistration:** Pythia-160M F28 causal, `stage7_foundation_layer6_ablation_report_20260517.json` carries a machine-readable `decision_gates {chance_accuracy 0.03571428571428571, foundation_ablated_acc_max 0.08, random_ge_foundation_empirical_p_max 0.05}`; Pythia-160M F28 and 40E readout, `decision_gates` blocks in both probe reports; Pythia-2.8B F28-vs-GoEmotions, +20 pp floor missed → `BLOCKED_CAS_NOT_RECOVERABLE`; Qwen W0 injection, char n-gram won → PASS withdrawn → `OPEN / NOT LICENSED`. **Where it is not:** the 20B 40E causal gate ("≥30 pp drop / ≤65% floor"). The ablation JSON has **no gate field**, and the only sources for the threshold are two claim documents written after the outcome (`CAS_HARNESS_SPEC_SHEET_current.md:282`, `synopsis:101`) — see §7 gap 14. Against a clause reading *"criteria are not rewritten after outcomes are known,"* a criterion evidenced only by post-outcome prose cannot be scored SATISFIED. The verdict on that row (`OPEN`, gate missed) is unaffected and remains correct; what is unproven is the word "pre-registered." |

**Item 1 is `PARTIAL / OPEN`, not closed.** The matrix now exists with a revision dimension and covers all five roadmap claim categories, and the blanket wording is inventoried with replacement text — but **three of four exit conditions fail** (revision 2 said two of four; the preregistration cell was downgraded in revision 3).

### 9.1 Roadmap clause 3 — "Remove blanket six-model wording" — is UNMET

The exit table above scores the four **exit-clause** conditions. It does not score the **item text**, whose third clause reads, verbatim: *"Remove blanket six-model wording unless raw evidence supports the exact rows"* (`docs/working/CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:189-191`).

**The operative verb is "Remove." Nothing was removed.**

- Git writes performed by this item: **none** (status block).
- Live surfaces edited: **none**.
- What this document did instead: inventory the wording (§4.1, §4.2, §4.6) and supply exact supported replacement text (§5.1).

Editing live claim surfaces — the consolidated spec sheet, the executive summary, the synopsis, the Amazon review brief, the investor sheets — is a publication decision with legal exposure (`CAS_HARNESS_SPEC_SHEET_current.md` is a legal-drafts document; the marketing sheets are NDA-distributed). This document does not have and does not claim the authority to make it. **But the clause is unmet, and no reading of §9 should suggest otherwise.**

**Exactly which surfaces need the edit, and what the replacement is.** Every one is specified in §5.1 with supported wording already written; this table is the work order.

| Surface | Lines to edit | Replacement text is at | Nature |
|---|---|---|---|
| `docs/working/cas_harness_executive_summary_20260630.md` | `:12`, `:13`, `:14`, `:17` | §5.1 blocks 1-4 | live engineering claim surface |
| `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md` | `:28`, `:59`, `:67`, `:83`, `:282`, `:308`, `:321`, `:522` | §5.1 block 5 (`:28/:67/:83/:522`); `:59` and `:308` are §5.2 rows 1 and 3, new in revision 3; `:282` is the "pre-registered" attribution, §7 gap 14; `:321` is the neuron-cover scope, §4.1 row 7 | live legal-drafts surface — **highest authority, and it carries two prohibited phrases revision 2 reported as absent** |
| `docs/working/cas_harness_synopsis_20260630.md` | `:24`, `:85`, `:101` (opening clause only), `:118` | §5.1 block 6; `:101`'s opening clause is §4.1 row 21b | live engineering surface; `:101`'s **second** sentence is correct and must be kept |
| `docs/working/cas_harness_amazon_review_brief_20260615.md` | `:54` | §5.1 block 7 | live external-facing brief |
| `…/docs/marketing/CAS_HARNESS_SPEC_SHEET_v2_1_INVESTOR_EXTERNAL_NDA_20260604.md` | `:133`, `:146`, `:158`, `:985`, `:1547` | §5.1 block 8, plus the withdrawal banner that currently exists only in `d6069513` | live investor surface under NDA |
| `docs/working/paper_b_causal_localization_draft_outline_20260523.md` | `:56` | §5.1 block 9 | draft paper |
| Archived sheets v1.6-v2.0 (§4.6.2) | v1_6 `:56/:312/:544/:545/:720`; v1_7 `:24/:76/:82/:94/:419/:546/:810`; v1_8 `:79/:359/:778`; v1_9 `:118/:968/:1498`; v2_0 `:134/:986/:1539` | Same replacements | **Do not rewrite archived history.** The correct action is an added in-body retraction block, not an edit to the claims — the line-1 banners name only the ACCEPT and Object-Lock retractions and leave every six-model and lab/corpus/language claim standing |
| `…/research/cas_probe/CAS_HARNESS_SPEC_SHEET_20260517.md` (v1.0) | `:515`, `:521` | §4.6.1 rows 24a-24g | archived; same treatment — annotate, do not rewrite |

Until those edits land on the live surfaces, **clause 3 is open**, and §10's "what survives" paragraph is the only place in the repository where the supported width is stated.

---

## 10. What this matrix licenses

Plainly: almost nothing that the live documents currently say. The matrix now carries **36 claim rows** (§4.1 rows 1-7, §4.2 rows 8-17, §4.3 rows 18-23 including 21b, §4.6 rows 24a-24g and 25-29 — the last twelve added in revision 3). Recounted from the corrected rows:

| STATUS | Count | Rows |
|---|---|---|
| `supported` | **2** | 18 (20B 40-Element readout number at `executive_summary:13`); 21 (the fully-caveated 20B ablation sentence at `synopsis:101`, minus its "pre-registered" attribution — §7 gap 14) |
| `supported at a narrowed model scope only` | **3** | 1 (Pythia-160M F28 subspace ablation, against a preregistered gate); 24a (Pythia-160M 40E 89.8% / +39.7 pp); 24b (Pythia-160M collapse-to-chance). Each is `overstated` at the scope its own sentence asserts |
| `partially supported` | **1** | 24c (the +0.554 bridge endpoint reproduces; the +0.283 endpoint and the p-value are `unavailable`) |
| `overstated` | **25** | 2-17, 19, 20, 21b, 22, 24g, 25, 26, 27, 29 |
| `withdrawn` | **2** | 23 (the 20B Stage 9 40E `ACCEPT`); 28 (the same `ACCEPT`, still asserted in four places in the archived v1.7 sheet body) |
| `unavailable` | **2** | 24d (lacunarity 0.015-0.021); 24e ("three preflight predictions held") |
| `flagged for human review` | **1** | 24f (six tiers claimed, five enumerated) |

Every blanket six-model formulation on every live surface — the consolidated current spec sheet, the executive summary, the synopsis, the Amazon review brief, and the v2.1 investor sheet — is overstated, and after the §5.2 re-run **10 of the 14 register rows carry violations**, where revision 2 recorded 6. Two of the newly-found phrasings (`current.md:59` "two independent evidence tiers" and `current.md:308` "not lab-specific, not corpus-specific, not language-specific") sit on the **highest-authority live surface** — a legal-drafts document — and were both reported absent by revision 2. One archived sheet (`v1_6:545`) records a prohibited phrase as `LICENSED` in a status table. Of the remaining four rows, **three are clean** — "universal interpretability", "validated at 300B", "prompt-injection detector as a closed capability" — and each is clean because the phrase appears **only** as its own prohibition in a NOT-LICENSED table, which is the correct state. The fourth ("immutable WORM evidence") is `unavailable`: not searched exhaustively, and now labelled as such rather than left as an unlabelled non-search.

**Direction of the revision-3 net change.** Two rows gained evidence (Pythia-160M F28 and 40E `control_proof` → `present`, both now with a located machine-readable artifact). Twelve rows were added, none of them `supported` at their asserted scope. Twenty-two new prohibited-phrase violations were found. One exit cell was downgraded. The picture got more accurate in both directions and, on balance, more constrained.

What survives, stated at the width the raw artifacts actually support: **Foundation-28 held-out readout replicates on six model points across three architecture families on one frozen English synthetic fixture, with exact denominators out of 2,352 and descriptive single-split Wilson intervals; at Pythia-160M both axes clear a character-level n-gram control on the same split — F28 78.571% vs `tfidf_char_3_5` 49.660% (paired exact-binomial McNemar p = 2.66×10⁻⁹⁵) and 40-Element 89.799% vs `tfidf_char_3_5` 50.089% — and the F28 subspace ablation collapses readout to exact 1/28 chance against 30 same-rank random removals with disruption 0.0, all three of its preregistered `decision_gates` met; the 40-Element readout reaches 95.625% at GPT-NeoX-20B but only against word-level text controls near 50%, with no character arm at that scale on either axis; subspace ablation is causally suggestive at 20B but missed the threshold reported as its gate, and no dated preregistration for that threshold has been located; sparse-neuron-cover causal control is Pythia-160M only; static weight geometry is Pythia-2.8B only and is one of three checks, the other two at 1.06× and 1.00× random.** That is a real and substantial research result — and the Pythia-160M half of it is stronger than the 2026-07-19 matrix or revision 1 of this document recorded, because a character-level control and a preregistered decision gate were both present and both missed. It is not "presence, causal role, and conditionability across six models," it is not "two axes closed at 20B," and it is not independently reproducible from any current checkout. Nothing here moves any claim to `LICENSED`, no `ACCEPT` is revived, and the negative results — the 20B causal near-miss, the Pythia-2.8B GoEmotions block, the withdrawn Qwen injection PASS — stay `OPEN / NOT LICENSED` exactly as their preregistrations required.

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

**Raw evidence opened for the first time in revision 3 — branch `experiment/cas-probe-pythia`**
- `…/stage7_foundation_layer6_ablation_report_20260517.json` (§4.1 row 1; §7 gap 7 withdrawal)
- `…/stage7_foundation_pilot_probe_report_20260517.json` (§4.4 Pythia-160M F28 row: `best_text_baseline_by_val`, `language_baselines`, `metadata_baselines`, `headline`, `decision_gates`, `split`, `n_records`)
- `…/stage9_elements_pilot_probe_report_20260517.json` (§4.4 Pythia-160M 40E row; §4.6.1 row 24a; §5.3 item 3)
- `…/STAGE8_PYTHIA1B_CPL2_REPORT_20260517.json` (§4.6.1 row 24c — `delta_vs_none.mean 0.5542184012276785`)
- `…/stage22_cas_harness_ablation_prereg_20260519.json` (§7 gap 14 — opened and ruled out as a different experiment)
- `…/stage6_role_bound_layer5_ablation_report_20260516.json`, `…/pythia_ablation_layer3_20260515.json` (§4.1 row 21b; §4.6.1 row 24b)

**Raw evidence opened for the first time in revision 3 — branch `master`**
- `…/pythia160m_gate1/pythia160m_stage9_40e_40_element_probe_eval_report.json` (§5.3 item 3 — `best_layer {layer 3, test_acc 0.9171875}`, `controls`, `n_train 3840`, `n_test 4480`)
- `…/S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json`, `readout` / `output` / `matched_controls` / `claim_levels` blocks (§4.4 20B F28 row — `readout.layer 40`, `output.verdict FLAG_FOR_HUMAN_REVIEW`)

**Claim surfaces opened for the first time in revision 3**
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/CAS_HARNESS_SPEC_SHEET_20260517.md:83, 508-509, 513, 515, 521, 523, 531` (v1.0 — §4.6.1)
- `…/docs/marketing/CAS_HARNESS_SPEC_SHEET_v1_6_INVESTOR_EXTERNAL_NDA_20260527.md:1, 56, 312, 538-550, 544, 545, 566, 720`
- `…/docs/marketing/CAS_HARNESS_SPEC_SHEET_v1_7_INVESTOR_EXTERNAL_NDA_20260528.md:1, 24, 76, 82, 94, 419, 546, 647, 810`
- `…/docs/marketing/CAS_HARNESS_SPEC_SHEET_v1_8_INVESTOR_EXTERNAL_NDA_20260528.md:1, 79, 359, 526, 778`
- `…/docs/marketing/CAS_HARNESS_SPEC_SHEET_v1_9_INVESTOR_EXTERNAL_NDA_20260530.md:1, 118, 968, 1228, 1498`
- `…/docs/marketing/CAS_HARNESS_SPEC_SHEET_v2_0_INVESTOR_EXTERNAL_NDA_20260604.md:1, 134, 986, 1256, 1539`
- `…/docs/marketing/CAS_HARNESS_SPEC_SHEET_v2_1_INVESTOR_EXTERNAL_NDA_20260604.md:133, 985, 1255, 1547`
- `docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md:59, 282, 308, 388, 441, 450, 455, 487`
- `project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/03_RESEARCH_AND_ARCHITECTURE_DOCS/HISTORICAL_CLAIM_AND_AUDIT_CONTEXT/CAS_HARNESS_SPEC_SHEET_current.md:308`
- `docs/working/CAS_HARNESS_JSPACE_OHM_300B_CAPABILITY_ANALYSIS_20260720.md:84, 377`
- `docs/working/cas_harness_production_todo.md:2788, 16570, 16868`
- `docs/working/cas_harness_topos_instruction_integrity_roundtable_20260610.md:103`
- `docs/working/typed_probe_gate_runlog.md:31-32` (the McNemar `p=0.289` non-separability line)

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

**Verification commands added in revision 3** (filename enumeration replaces string grep as the method for establishing a negative — see the §7 preamble)

- `git ls-tree -r --name-only experiment/cas-probe-pythia | grep -i stage7_foundation` → 14 paths, **including the two JSONs revision 1 declared absent**
- `git ls-tree -r --name-only experiment/cas-probe-pythia | grep -i ablation` → 24 paths, every model-ablation report Pythia-160M (§7 gap 2)
- `git ls-tree -r --name-only master | grep -i ablation` → 16 paths, only the 20B report and two `pythia160m_gate1/` reports (§7 gap 2)
- `git ls-tree -r --name-only experiment/cas-probe-pythia | grep -iE "40e|element"` → 18 paths, all Pythia-160M (§7 gap 3)
- `git ls-tree -r --name-only experiment/cas-probe-pythia | grep -i evidence_packets` → 8 paths, four `stage21a_*` packets, OLMo/Qwen only (§7 gap 11)
- `git ls-tree -r --name-only experiment/cas-probe-pythia | grep -i cpl2` → 14 paths; CPL2 reports exist for Stage 8/14/15/16/19D/19E and **no Pythia-160M CPL2 report exists** (§4.6.1 row 24c)
- `git ls-tree -r --name-only experiment/cas-probe-pythia | grep -i prereg` → 4 paths; `stage22_cas_harness_ablation_prereg_20260519.json` opened, key list read, ruled out as a different experiment (§7 gap 14)
- `git ls-tree -r --name-only master | grep -i pythia160m_gate1` → 14 paths (§4.1 row 7; §5.3 item 3)
- Recursive case-insensitive content search for each of the 14 prohibited phrases across `docs/`, `noetic-compass-scaffold/noetic-compass/docs/marketing/`, `noetic-compass-scaffold/noetic-compass/research/cas_probe/` and `project_handoffs/`, over `*.md`, each hit opened and classified assertion-vs-prohibition (§5.2)
- Key-presence test for `layer_scan` across all located probe reports → present in exactly four (§4.4 preamble)
- `0.8979910714285714 × 4480 = 4023.0` exactly; `0.7857142857142857 × 2352 = 1848.0` exactly
- `0.7857142857142857 − 0.4965986394557823 = 0.2891156462585034` (matches `test_acc_lift_over_best_text` in the artifact); `0.7857142857142857 − 0.6666666666666666 = 0.11904761904761907` (matches `test_acc_lift_over_best_metadata`)
- `0.8979910714285714 − 0.5008928571428571 = 0.39709821428571423` (matches `test_acc_lift_over_best_text`, and reproduces the v1.0 sheet's "+39.7pp")
- `0.9171875 − 0.8979910714285714 = 0.0191964…` → the 1.92 pp Pythia-160M 40E conflict (§5.3 item 3)
