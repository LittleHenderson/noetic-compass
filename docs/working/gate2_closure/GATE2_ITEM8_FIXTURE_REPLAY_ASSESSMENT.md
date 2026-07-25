# Gate 2 Item 8 — Fixture Replay Assessment

## Status block

| Field | Value |
| --- | --- |
| Gate | Gate 2 — Small-model semantic and claims closure (`0.38 -> 0.46`) |
| Item assessed | Item 8 — "Replay the strongest saved Pythia/TKS fixtures through the current live Evidence Packet path without overwriting the historical record." (`docs/working/CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:214-215`) |
| Item 8 status | **NOT CLOSED — BLOCKED.** See §9. |
| What this document does close | The fixture census (§1), the code survey of both Evidence Packet paths (§2), the ingest-compatibility finding (§3), the non-destructive replay procedure (§4), the pre-registration of what a replay would and would not establish (§5), and one independently reproduced sha256 (§6.1). It closes **none** of item 8's own text. |
| Date | 2026-07-24 |
| Branch assessed | `codex/cascompass-legal-live-source` |
| Document type | Assessment + procedure. Not a run report. No replay has been executed as of this document. |

### Claim-state line

**This document is `real` as an assessment of code and artifacts, and `open` as to item 8 itself.**
Every code fact below was read directly at the cited file:line and every artifact field was read from
the artifact named. Facts about the branch under assessment came from its working tree; the §1.1
Stage-7 fixtures were read out of git on branch `experiment/cas-probe-pythia` and are labelled as
such wherever they appear. One hash was independently recomputed on this host (see §6.1) — that single
result is `real / verified`. No replay run has been performed, so item 8 is `open`. Every candidate
fixture on this branch is `not-licensed` by its own recorded status; the §1.1 fixtures carry no
licensing field at all, only a `reserved_interpretation` scope limit — and nothing in this document
changes either. Two questions are `flagged-for-human-review` (§8.1, §8.2), with a language constraint
recorded at §8.3. Verified structural absences (`real`) are kept separate from `unavailable` gaps and
from the `open` gate requirement throughout §7.

Gate 2 exit clause, quoted, not restated:

> "Exit requires exact model/revision/tier claim rows, `control_proof: present` where controls ran,
> independently reproducible raw evidence, and a verdict consistent with preregistered criteria.
> Mixed or negative results remain `OPEN / NOT LICENSED`; criteria are not rewritten after outcomes
> are known." — `docs/working/CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:217-220`

### Scope exclusion, stated up front

The four W0 prompt-injection experiments under
`project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/GATE2_W0_FAIR_COMPARISON/`
are **excluded from this item**. Prompt-injection detection is Gate 3 (`docs/working/cas_harness_production_todo.md:955`);
those runs were executed against a self-authored paraphrase of Gate 2. Their own `STATUS.md:5` records
`GATE_2_STILL_OPEN / FOUR_ATTEMPTS_EXECUTED_ON_REAL_WEIGHTS / ALL_FAIL_AT_PRE_REGISTERED_BAR /
FAMILY_CLOSED_BY_PRE_COMMITMENT / NOT_LICENSED / NO_THRESHOLD_EVER_MOVED`. They are honest and
preserved. They are the best-instrumented Pythia fixture bank in the tree and therefore the most
likely thing a later agent will reach for. They are **not** replay subjects for item 8.

---

## 1. Ranked candidate fixtures

### 1.0 "Strongest" — adjudicated, not deferred

Item 8 says "the **strongest** saved Pythia/TKS fixtures." The table below ranks by *replay fitness*
(self-containment on local disk, an exact model/revision row, a re-hashable raw artifact). That is a
different axis from scientific strength, so the item's own word is adjudicated here first.

**On this branch's working tree, no saved fixture is scientifically strong**, on the fixtures' own
recorded numbers:

* Candidate #1's sole pre-registered primary estimand is `0.0042517006802721136` with a paired
  clustered bootstrap 95% CI of `[-0.001275510204081634, 0.010204081632653059]` — **includes zero**
  (`tks_definition_anchor_report.json → sole_preregistered_primary_estimand`), and its own
  `tfidf_surface_baselines` record a TF-IDF char-3-5-gram surface baseline at `accuracy: 1.0` on split
  `source_derived_sensitivity_v0_variant_ge_8`.
* #2, #3, #4, #5, #6 are canaries, preflights, shadow baselines and verification receipts. None
  reports a measured effect against a control; each self-declares `NOT_LICENSED` (§M7 table).

**Off this branch, one saved Pythia/TKS fixture family IS strong on its own recorded numbers** — the
Stage-7 Foundation-28 pair on branch `experiment/cas-probe-pythia` (§1.1). It is the only candidate
that clears a surface control *and* carries a matched random-control causal ablation.

Consequence for item 8: a replay run staged only from this branch's working tree replays no strong
fixture. The Stage-7 pair (§1.1) is the honest answer to "strongest," and it is **not present in this
branch's working tree** — it must be materialised out of git before it can be replayed at all.

### 1.1 The strongest saved Pythia/TKS fixture family — `experiment/cas-probe-pythia`, not this branch

Not in this branch's working tree (`ls noetic-compass-scaffold/noetic-compass/research/cas_probe/` on
`codex/cascompass-legal-live-source` returns `CAS_HARNESS_SPEC_SHEET_20260517.docx/.md`,
`__pycache__`, `evidence_packets`, `graphify-out` — none of the Stage-7 files). Read for this document
via `git show experiment/cas-probe-pythia:<path>` and `git ls-tree -r -l`:

| Blob | Bytes | Field read | Value (verbatim) |
| --- | --- | --- | --- |
| `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_pilot_probe_report_20260517.json` | 2,255,209 | `status` | `FOUNDATION_PROBE_RELIABLY_ABOVE_TEXT_BASELINE` |
| " | " | `headline.readout` / `headline.layer` / `headline.test.acc` | `focus_token` / `6` / `0.7857142857142857` |
| " | " | `best_text_baseline_by_val` | `tfidf_char_3_5` (**character-level**, test acc `0.4965986394557823`) |
| " | " | other text baselines | `tfidf_word_1_2` `0.4523809523809524`; `count_vector_word_1_2` `0.4187925170068027`; `majority` `0.03571428571428571`; `stratified_dummy` `0.0391156462585034` |
| " | " | `best_metadata_baseline_by_val` | `surface_pair_family_focus`, test acc `0.6666666666666666` |
| " | " | `headline.paired_vs_best_text` | vs `tfidf_char_3_5`: `a_only_correct` 914, `b_only_correct` 234, `exact_binomial_mcnemar_p` `2.6557483981655295e-95` |
| " | " | `decision_gates` | `{mcnemar_p_max 0.05, metadata_focus_only_test_acc_max 0.08, test_acc_lift_over_text_min 0.05}` |
| `.../stage7_foundation_layer6_ablation_report_20260517.json` | 56,257 | `status` | `FOUNDATION_SUBSPACE_CAUSAL_FOR_PROBE_READOUT` |
| " | " | `layer` / `n_random_controls` | `6` / `30` |
| " | " | `foundation_subspace_ablation.test.acc` | `0.03571428571428571` (= chance) |
| " | " | `random_complement_controls.one_sided_empirical_p_random_ge_foundation` | `0.03225806451612903` |
| " | " | `decision_gates` | `{chance_accuracy 0.03571428571428571, foundation_ablated_acc_max 0.08, random_ge_foundation_empirical_p_max 0.05}` |
| `.../stage7_foundation_pilot_activations_manifest_20260517.json` | 1,231 | `model_name` / `model_revision` | `EleutherAI/pythia-160m` / `50f5173d932e8e61f858120bcb800b97af589f46` |
| `.../stage7_foundation_pilot_20260517.jsonl` | 9,021,812 | `input_sha256` (as recorded in the reports) | `3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250` |

Why this is the strongest: it is the only saved Pythia/TKS fixture in the census whose hidden readout
(`0.7857`) beats its own **character-level** surface control (`0.4966`) on a paired test, and the only
one carrying a matched-control causal ablation (30 random complement subspaces, one-sided empirical
`p = 0.0323`) against pre-registered `decision_gates`. Both gate blocks were written into the
artifacts, not asserted here.

What it does **not** change:

* **It does not ingest either.** Its top-level keys are `activations_file, activations_sha256,
  best_metadata_baseline_by_val, best_text_baseline_by_val, decision_gates, elapsed_seconds,
  experiment, headline, input_file, input_sha256, label_names, language_baselines, metadata_baselines,
  n_records, readouts, reserved_interpretation, schema_version, split, status` (pilot report) and
  `activations_file, activations_sha256, decision_gates, experiment, foundation_subspace_ablation,
  input_file, input_sha256, label_names, layer, n_random_controls, probe_retrained_for_ablation,
  random_complement_controls, readout, reserved_interpretation, schema_version, split,
  stage70_report_file, stage70_report_sha256, status, subspace` (ablation report). Neither has `input`,
  `output`, `claim_levels`, `caveats`, `provenance`, or `model_checkpoint_id`. M1, M2, M3, M6, M8 all
  apply unchanged.
* **Its M7 profile is worse, not better.** It carries no `licensing_status`, no `claim_eligible`, no
  `claim_status` — only `status` and a free-text `reserved_interpretation`:
  *"A pass would support hidden-state readout beyond text baselines; it would not prove generation
  control or solve the black-box problem"* (pilot) and *"a causal intervention on the
  representation/readout, not a causal language-generation test"* (ablation). A shim that drops
  `reserved_interpretation` strips the only scope limit these two artifacts carry.
* **Its raw NPZ is `unavailable`.** `stage7_foundation_pilot_activations_20260517.npz`
  (`activations_sha256` = `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f`) is not
  in `git ls-tree -r experiment/cas-probe-pythia -- .../research/cas_probe/` and is not in this
  branch's working tree. So the §6.1-style re-hash demonstration is **not** available for this
  fixture; only candidate #1 offers it.

### 1.2 Replay-fitness ranking (this branch's working tree)

Ranked by fitness as a replay subject for item 8: self-containment on local disk, presence of an
exact model/revision row, and presence of a re-hashable raw artifact. **Not** ranked by scientific
strength — that is adjudicated in §1.0, and every fixture in this table is `claim_eligible: false`.

| # | Path (relative to `C:/Users/wakil/OneDrive/Desktop/tksCAS/`) | Size | What it measured | Headline numbers / status (verbatim from the artifact) | Completeness |
| --- | --- | --- | --- | --- | --- |
| 1 | `project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/02_RESEARCH_EVIDENCE/full_recovery/artifacts/full/tks_definition_anchor_report.json` | 255,466 B | Zero-shot definition-anchor diagnostic on Foundation-28; nearest-anchor-by-cosine, attention-masked mean-token pooling, shared primary layer 1 | `sole_preregistered_primary_estimand.name` = `D3_MINUS_A124_FULL28_ACCURACY_DELTA`; `estimate` = `0.0042517006802721136`; `paired_clustered_bootstrap_95_ci` = `[-0.001275510204081634, 0.010204081632653059]` (**includes zero**); `evaluation_split` = `stage7_test`; `status` = `SOLE_PREREGISTERED_PRIMARY_ESTIMAND_NOT_LICENSED`. Chance levels: full `0.03571428571428571`, drive `0.14285714285714285`, register `0.25`. TF-IDF char-3-5-gram surface baseline reaches `accuracy: 1.0` on split `source_derived_sensitivity_v0_variant_ge_8` | **Highest.** Report + 109,414,103 B raw NPZ + local manifest + `FULL_BUNDLE_SHA256SUMS`, all present. Carries `tfidf_surface_baselines`, `deterministic_shuffled_label_control`, `bootstrap`, `paired_comparisons`, `per_layer_arm_metrics`, `token_length_confound`, `source_generator_bias`, `multiplicity_boundary` |
| 2 | `.../04_PROTOCOL_AND_ANCHOR/ATTEMPT_11_TECHNICAL_CANARY_PASS_GATE1/evidence/jacobian_lens_canary_v1_execution_receipt.json` (+ `..._receiver_receipt.json`, 7,396 B) | 174,830 B | Jacobian-lens live-model canary, producer side, with an independent receiver receipt | Producer: `producer_status` = `TECHNICAL_CANARY_PASS_CANDIDATE_PENDING_INDEPENDENT_VERIFICATION`, `claim_status` = `NOT_LICENSED`, `execution_mode` = `SHADOW`, `verdict` = `NONE`, `run_id` = `jlcv1-rfc3161-2f7f8aa400618cb9692e22a5910d810a38be9f8a4dbaa3eaf1a4f5c327daeed0`. Receiver: `receiver_status` = `TECHNICAL_CANARY_PASS_OPERATOR_ATTESTED_PENDING_EXTERNAL_REPRODUCTION`, `claim_status` = `NOT_LICENSED`, `execution_mode` = `SHADOW`, `verdict_influence` = `NONE` | **High.** Producer + independent receiver + `jacobian_lens_canary_v1_anchor_receipt.json` (5,597 B) + `PRE_REVERIFY.json` + `launch_started/finished.json` + `post_run_capture.json` + `wrapper.stdout.log` all local. Second copy at `D:/tksCAS-archive/` |
| 3 | `.../02_RESEARCH_EVIDENCE/full_recovery/OFF_POD_VERIFICATION.json` | 5,410 B | Off-pod recovery + revision-binding verification for the TKS run | `schema_version` = `cas_harness_off_pod_verification.v1`; `licensing_status` = `NOT_LICENSED_DIAGNOSTIC_ONLY`; `claim_eligible` = `false` | **High for its purpose.** Smallest artifact carrying the exact model/revision row the exit clause demands. No raw vectors of its own |
| 4 | `.../02_RESEARCH_EVIDENCE/full_recovery/artifacts/canary-8prompt-2layer/tks_definition_anchor_canary_receipt.json` | 25,181 B | 8-prompt / 2-layer canary of the same TKS diagnostic | `status` = `CANARY_PASS`; `licensing_status` = `NOT_LICENSED_CANARY_ONLY`; `claim_eligible` = `false`; `created_at` = `2026-07-21T10:42:24.204183+00:00` | **High.** Receipt + 555,869 B vectors NPZ + manifest + `SHA256SUMS`. Same schema family as #1 at 1/200th the size — the correct smoke subject |
| 5 | `.../02_RESEARCH_EVIDENCE/supporting_local_preflight/cas-pythia-hook-equivalence-local-20260721.json` | 19,769 B | Pythia GPT-NeoX block-hook equivalence preflight; pins the 12 hooked module paths | `status` = `PREFLIGHT_PASS`; `licensing_status` = `NOT_LICENSED_PREFLIGHT_ONLY`; `claim_eligible` = `false`; `created_at` = `2026-07-21T09:05:09.302257+00:00` | **Medium-high.** Self-contained single file; carries `equivalence`, `adapter_qualification_status`, `comparison_contract`, `universality_status`. No raw vectors |
| 6 | `.../08_JSPACE_CAS_OHM_SHADOW_2026-07-21/research_shadow_baseline_final.json` | 6,598 B | J-space / CAS-Ohm shadow baseline | `schema_version` = `cas_harness_research_shadow.v1`; `execution_mode` = `SHADOW`; `claim_status` = `NOT_LICENSED`; `claim_eligible` = `false` | **Medium.** Shares the `cas_harness_research_shadow.*` family with #2, so one shim covers both. Not a headline measured outcome |
| 7 | `noetic-compass-scaffold/noetic-compass/atlas-viewer/test-fixtures/pythia_160m_reference_trace.json` | — | Nothing. UI test fixture | `schema_version` = `atlas_viewer_trace_v1`; carries `evidence_packet_id` = `7a3f9e2c-1d44-4b6a-9c8e-5f0a2b1c7d83` | **Not a measured-outcome fixture.** Listed only because it is a *third* trace schema already in-tree and any shim must declare which schema it targets |
| — | `.../10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/CJT_BIAS_RPM_OHM_STATISTICAL_V1.json` | 22,907 B | **Nothing yet.** A frozen pre-registered protocol with no results: `status` = `FROZEN_PROSPECTIVE_CANDIDATE_REQUIRES_EXTERNAL_ANCHOR_BEFORE_OFFICIAL_EXECUTION` | n/a | **Not a fixture.** Recorded so it is not mistaken for a saved run |
| — | `.../11_.../GATE2_W0_FAIR_COMPARISON/evidence/` — 4 `injection_detection_w0_report_*.json` reports; the glob `evidence/*.json` matches 5 files because `injection_detection_attempts_registry.json` also matches (directory listed on this host: those 5 plus `injection_scorer_run.stdout` and `w0_hidden_pi_v0.npz`) | — | Prompt-injection detection, 4 attempts | `ALL_FAIL_AT_PRE_REGISTERED_BAR` (`STATUS.md:5`) | **Excluded — Gate 3, not Gate 2.** See the scope exclusion above |

Exact-model claim row available from #1 and #3, verbatim from
`tks_definition_anchor_report.json → provenance`:
`model_id` = `EleutherAI/pythia-160m`; `requested_model_revision` =
`50f5173d932e8e61f858120bcb800b97af589f46`; `model_pin_status` =
`{"canary_override": false, "integrity_pinned": true, "is_exact_40_hex": true, "requested_revision": "50f5173d932e8e61f858120bcb800b97af589f46"}`;
`model.parameter_count` = `162322944`; `model.architectures` = `["GPTNeoXForCausalLM"]`;
`model.hidden_size` = `768`; `model.num_hidden_layers` = `12`.

---

## 2. The live Evidence Packet path

Two distinct "Evidence Packet" paths exist. Item 8 says "the current live Evidence Packet path,"
singular. This is adjudicated in §8.1; both are documented here because only one of them can emit the
field the exit clause names.

### 2.1 Path A — the served path (`evidence_packet.v1`)

**File:** `noetic-compass-scaffold/noetic-compass/api/routes/evidence.py` (863 lines).

| Property | Value | Citation |
| --- | --- | --- |
| Router | `APIRouter(prefix="/evidence", tags=["evidence"])` | `api/routes/evidence.py:54` |
| Wired into the app | `from api.routes import (… evidence, …)` then `app.include_router(evidence.router)` | `api/main.py:32`, `api/main.py:135` |
| Entry point (in-process) | `build_packet_for_trace(trace_id) -> EvidencePacket` | `api/routes/evidence.py:689` |
| Real-trace assembler | `_packet_from_trace(trace_id, trace)` | `api/routes/evidence.py:602` |
| Trace loader | `_load_trace_artifact(trace_id)` | `api/routes/evidence.py:276` |
| GET route | `@router.get("/{trace_id}", response_model=EvidencePacket)` | `api/routes/evidence.py:837` |
| POST verify route | `@router.post("/{trace_id}/verify", response_model=VerifyHashesResponse)` | `api/routes/evidence.py:851` |
| Write surface | **None.** Module docstring: "Reads on-disk artifacts only; nothing is written" | `api/routes/evidence.py:3-4` |

Write-surface claim independently checked: a grep of `evidence.py` for `write_text`, `open(...,'w')`,
and `json.dump` returned zero hits. Both handlers only read and hash.

**Input schema.** `_packet_from_trace` reads exactly these keys off the trace dict, and no others
(`api/routes/evidence.py:602-686`):

`checkpoint_manifest_path`, `code_commit_sha`, `weights_path`, `tokenizer_path`, `corpus_path`,
`weights_sha`, `tokenizer_hash`, `corpus_sha256`, `model_checkpoint_id`, `checkpoint_label`,
`code_commit_summary`, `run_command`, `claim_levels`, `input`, `cas_expression`, `output`,
`copy_slot_trace`, `caveats`.

**Output schema.** The pydantic `EvidencePacket` model (`api/routes/evidence.py:62-80`):
`schema_version` (hard default `"evidence_packet.v1"` at `:69`), `trace_id`, `generated_at`, `input`,
`cas_expression`, `output`, `copy_slot_trace`, `provenance`, `hashes`, `claim_levels`, `caveats`.
Schema authority is `docs/working/evidence_packet_2026_05_15/SPEC.md` §4 (`trace_id` documented as
UUID4 at `SPEC.md:147`).

**Validation gates on Path A:**

1. **Auth.** `PUBLIC_PATHS = {"/health", "/health/db", "/health/ready", "/auth/token", "/docs",
   "/openapi.json", "/redoc"}` (`api/middleware/auth.py:15`). `/evidence` is not in it, and the
   GET-only `/forex` bypass at `api/middleware/auth.py:29-30` does not apply. Missing/non-Bearer
   header → 401 (`api/middleware/auth.py:33-37`). An in-process call to `build_packet_for_trace()`
   bypasses this gate entirely.
2. **Discovery.** `_candidate_trace_paths` (`api/routes/evidence.py:257-273`) searches exactly five
   locations for a file literally named `{trace_id}.json`:
   `dashboard/public/traces/`, `cas-native/trace/captures/`, `.tmp/traces/`,
   `<tksCAS>/cas-synthetic/data/traces/`, `cas-native/trace/`.
   Sanitization is only `trace_id.replace("/", "_").replace("\\", "_")` (`:259`) — no UUID4 check on
   the read side. 404 if nothing is found (`api/routes/evidence.py:847-848`).
3. **Verify path allowlist.** `_resolve_allowed_path` (`api/routes/evidence.py:221-249`) rejects with
   `"path is outside allowed roots"` (`:233-234`), `"file not found locally"` (`:236-237`),
   `"path could not be resolved"` (`:231`), or an over-size message (`:243-247`). Allowed roots are
   `_project_root()` and `_scaffold_root()` (`:204-206`); `_project_root()` = `parents[4]` of
   `api/routes/evidence.py` = `tksCAS/` (`:110-115`). Size cap `_MAX_VERIFY_FILE_BYTES` = 8 GiB
   (`:201`).
4. **Verify bindings.** Only four artifact/hash/path triples are ever checked:
   `("weights","weights_sha","weights_path")`, `("tokenizer","tokenizer_hash","tokenizer_path")`,
   `("english_bpe","english_bpe_hash","english_bpe_path")`, `("corpus","corpus_sha256","corpus_path")`
   (`_ARTIFACT_BINDINGS`, `api/routes/evidence.py:713-718`), plus a `code_commit` check against
   `git rev-parse HEAD`. Artifacts with no expected SHA in the packet are skipped silently —
   `if expected is None: continue` (`:738-739`).
5. **`overall` computation** (`api/routes/evidence.py:815-822`): no checks → `unable_to_verify`;
   all match → `all_match`; all non-matching with `actual is None` → `unable_to_verify`; otherwise
   `partial_mismatch`.
6. **Claim vocabulary.** `claim_levels[].level` is locked to four values —
   `cas_hard_trace | source_copy_evidence | derived_trace | neural_attribution_estimate` —
   in `dashboard/src/lib/evidence_packet.ts:24-28` and `SPEC.md:57`. `support_status` is locked to six
   values (`dashboard/src/lib/evidence_packet.ts:37-43`, `SPEC.md:70`). The pydantic model does not
   enforce this (the fields are `dict[str, Any]`), so the lock is a client-side/spec contract, not a
   server rejection. **A shim that invents a fifth level would pass the server and break the UI.**

**The only sanctioned writer into Path A's discovery set** is `_persist_evidence_trace` in
`api/routes/mode7.py:1408-1445`, which writes `<scaffold>/.tmp/traces/{trace_id}.json`
(`api/routes/mode7.py:1518`) and enforces a strict UUID4 regex `_UUID4_RE` (`:1403`, enforced `:1439`)
as a path-traversal defense. Note the asymmetry: the writer enforces UUID4, the reader does not.

### 2.2 Path B — the offline merge path (`cas_harness_stage9_40e_evidence_packet.v1`)

**File:** `noetic-compass-scaffold/noetic-compass/live-trace-worker/scripts/merge_stage9_40e_evidence_packet.py`.

| Property | Value | Citation |
| --- | --- | --- |
| Schema | `SCHEMA_VERSION = "cas_harness_stage9_40e_evidence_packet.v1"` | `:20` |
| Verdict constant | `REVIEW_VERDICT = "FLAG_FOR_HUMAN_REVIEW"`, emitted as `"verdict"` | `:49`, `:472` |
| Builder | `build_packet(...)` | `:405` |
| **Emits the `control_proof` KEY** | `"control_proof": control_proof` — always present in the packet | `:464` |
| **Emits `control_proof.status == "present"`** | **Only when `--cover-report` is supplied.** `control_proof` is built by `_make_optional_proof(tier_name="cover_discovery", report_path=cover_report, …)`; with `report_path is None` it returns `{"status": "missing", "tier": tier_name, "required_for_final_verdict": True, "source_report": None, "blocking_reason": f"{tier_name} report was not supplied"}` | built `:426-431`; `_make_optional_proof` `:348-384`; missing branch `:355-365`; `"present"` branch `:369-384`; CLI flag `--cover-report` `:555`, threaded `:564` |
| Also emits | `causal_proof`, `output_bridge_proof`, `tier_statuses`, `verifier` | `:438-472` |
| Input | a run report JSON via `_load_json` | `:71`; hard `SystemExit(f"required report does not exist: {path}")` at `:75` |
| **Writes** | `output_json.write_text(...)`, `output_markdown.write_text(...)`, after `mkdir(parents=True, exist_ok=True)` | `:544`, `:548`, `:542-543` |
| Write targets | `--output-json` / `--output-markdown`, defaults `DEFAULT_OUTPUT_JSON` / `DEFAULT_OUTPUT_MARKDOWN` | `:557-558`, `:28-34` |

**`control_proof` does not exist anywhere under `api/`.** Verified by ripgrep over
`noetic-compass-scaffold/noetic-compass/api/` — zero hits. It exists only in this script and its test.
Path A therefore **cannot** emit `control_proof: present`, structurally. This is a `real`
verified-absent code fact, not an open question (§7 row 1).

### 2.3 `control_proof: present` is not reachable on this branch — from either path

The exit clause names `control_proof: present`. Three facts together determine whether any replay
under item 8 can produce it:

1. **Path A cannot emit the field at all** — ripgrep result above.
2. **Path B emits the field but the value is `missing` by default.** `_make_optional_proof` returns
   `status: "missing"` whenever its `report_path` is `None`
   (`merge_stage9_40e_evidence_packet.py:355-365`); `status: "present"` requires a real report file
   (`:369-384`). `control_proof`'s `report_path` is the optional `--cover-report` argument
   (`:426-431`, `:555`, `:564`). Nothing in the merger's defaults supplies it —
   `DEFAULT_READOUT_REPORT` / `DEFAULT_OUTPUT_JSON` / `DEFAULT_OUTPUT_MARKDOWN` (`:22-34`) cover the
   readout and the outputs only; there is no `DEFAULT_COVER_REPORT`.
3. **No cover-discovery report exists on this branch.** Searched on 2026-07-24:
   `ls noetic-compass-scaffold/noetic-compass/docs/working/ | grep -iE 'stage9|40e|cover'` → three
   `.md` planning files only (`stage9_40e_20b_ai2_brief_20260527.md`,
   `stage9_40e_20b_causal_chain_plan_20260527.md`,
   `stage9_40e_20b_runpod_causal_execution_runbook_20260527.md`), no JSON report;
   `ls docs/working/ | grep -iE 'stage9|40e|cover'` → 8 files, none a cover-discovery report;
   a `rglob("*cover*")` over `live-trace-worker/`, `noetic-compass-scaffold/noetic-compass/docs/` and
   `docs/` returned only source and test modules
   (`live-trace-worker/scripts/discover_stage9_40e_neuron_covers.py`,
   `live-trace-worker/app/runtime/cover_library.py`,
   `live-trace-worker/tests/test_cover_library.py`,
   `live-trace-worker/tests/test_stage9_40e_neuron_covers.py`), plus unrelated
   `*coverage*` docs. **The discovery script exists; its output report does not.** Recorded as
   `unavailable` on this branch, scoped to those paths (§7).

Fourth fact, and the one that closes the question for item 8 specifically: the tier is
`cover_discovery` and the artifact ids are `stage9_40e_cover_discovery_report` (`:429-430`) — the
Stage-9 40E / GPT-NeoX-20B sparse-neuron-cover family. **None of the Pythia/TKS candidates in §1 or
§1.1 is a cover-discovery report**, so no item-8 fixture could populate that tier even if the shim
existed. Item 8 cannot produce `control_proof: present` by any route currently on this branch.

---

## 3. Compatibility matrix

Question asked of each fixture: *does it ingest as-is into Path A* — i.e. can it be dropped into one
of the five discovery directories, named `{trace_id}.json`, and produce a meaningful packet with no
transformation?

**Answer for every candidate: no.** The overlap between fixture top-level keys and the keys
`_packet_from_trace` reads (`api/routes/evidence.py:602-686`) is nil in every case.

| Fixture | Ingests as-is? | Concrete mismatches |
| --- | --- | --- |
| #1 `tks_definition_anchor_report.json` | **No** | M1, M2, M3, M4, M5, M6, M7, M8 |
| #2 Attempt-11 producer + receiver receipts | **No** | M1, M2, M3 (no `provenance` key at all — producer top-level keys are `artifact_count, artifact_inventory_sha256, artifacts, autograd_grad_counters, base_protocol_id, bindings, blocks, claim_eligible, claim_status, execution_mode, failure_retention, functional_checks, input_publications, maximum_producer_status, numerical_summary, official_pass_authorized, producer_status, protocol_id, receipt_kind, run_id, runtime, schema_version, verdict`), M4, M6, M7, M8 |
| #3 `OFF_POD_VERIFICATION.json` | **No** | M1, M2, M3, M6, M7, M8 |
| #4 `tks_definition_anchor_canary_receipt.json` | **No** | M1, M2, M3, M4, M5, M6, M7, M8 |
| #5 `cas-pythia-hook-equivalence-local-20260721.json` | **No** | M1, M2, M6, M7, M8. Has an `input` key but it is a hook-equivalence input record, not `{text: …}` — see M1 note |
| #6 `research_shadow_baseline_final.json` | **No** | M1, M2, M3, M6, M7, M8 |
| #7 `pythia_160m_reference_trace.json` | **No** | M1, M2, M6. Third schema (`atlas_viewer_trace_v1`); not a measured-outcome fixture |
| §1.1 Stage-7 pilot probe report (`experiment/cas-probe-pythia`) | **No** | M1, M2, M3 (no `provenance` key), M6, M8. Also not in this branch's working tree at all — must be materialised from git before staging. M7 applies in its harshest form: no `licensing_status` / `claim_eligible` / `claim_status` field exists to carry, only `status` and free-text `reserved_interpretation` |
| §1.1 Stage-7 layer-6 ablation report (`experiment/cas-probe-pythia`) | **No** | Same as the row above. Its `decision_gates` and `random_complement_controls` blocks have no packet field to land in either |

### The mismatches, concretely

**M1 — `input` / `output` absent → silent empty packet.**
`_packet_from_trace` reads `trace.get("input") or {"text": ""}` (`api/routes/evidence.py:678`) and
`trace.get("output") or {"text": ""}` (`:680`). The 27 top-level keys of `tks_definition_anchor_report.json`
are, verbatim: `bootstrap, chance_levels, claim_eligible, compact_comparator_interpretation,
created_at, definition_change_contract, deterministic_shuffled_label_control, diagnostic_class,
integrity_inputs_pinned, licensing_status, local_raw_diagnostic_artifact, method, multiplicity_boundary,
non_claim, paired_comparisons, per_layer_arm_metrics, per_layer_metric_scope, provenance,
schema_version, selected_layer_results, shared_layer_selection_trace,
shared_validation_selected_primary_layer, sole_preregistered_primary_estimand, source_generator_bias,
tfidf_surface_baselines, token_length_confound, token_length_summary`. Neither `input` nor `output` is
present. Result: a packet whose input and output are empty strings. No error is raised.
(Fixture #5 does have an `input` key, but it is not `{text: …}`-shaped; it would be passed through
verbatim and render as an unrecognized object.)

**M2 — `claim_levels`, `caveats`, `cas_expression`, `copy_slot_trace` absent.**
All four are absent from every candidate. `claim_levels` falls back to a single synthetic row,
`{"claim": "Trace artifact loaded from disk for this trace_id.", "level": "derived_trace", …}`
(`api/routes/evidence.py:665-673`). The packet would therefore assert nothing about what was measured.
`caveats` falls back to `None` (`:685`) — i.e. no caveat at all.

**M3 — same key name, unrelated meaning, silently dropped. This is the dangerous one.**
Both `tks_definition_anchor_report.json` and the packet have a key named `provenance`. They are not
the same thing. The fixture's `provenance` has these keys (read directly): `arm_manifest, arms,
capture_contract, code, created_at, diagnostic_class, hardware, input_integrity_start_end, model,
model_id, model_pin_status, non_claim, requested_model_revision, schema_version, scenario_sources,
seed, source_generator_bias, token_length_confound, token_length_summary`.
`_packet_from_trace` **never reads `trace["provenance"]`.** It rebuilds `provenance` from
`trace["model_checkpoint_id"]`, `trace["code_commit_sha"]`, `trace["checkpoint_label"]`,
`trace["code_commit_summary"]`, `trace["run_command"]` (`api/routes/evidence.py:649-663`). Handing the
fixture dict straight to the builder yields `provenance.model_checkpoint_id == "unknown"` (`:650-652`)
with no exception. **The exact-model/exact-revision rows the Gate 2 exit clause demands would vanish
without any error surfacing.**

**M4 — hashes are the wrong type.**
The packet expects four flat scalars plus a flat `on_disk_paths` dict
(`api/routes/evidence.py:641-647`, bindings `:713-718`). The fixtures store hashes as **lists of
objects**: `provenance.code.critical_file_hashes[] = [{path, sha256, bytes}, …]` (6 entries in #1),
`provenance.input_integrity_start_end.snapshot.files[]`, `model.resolved_artifacts.artifacts[]`
(each `{filename, cache_path, resolved_path, bytes, sha256}`), and per-file
`expected_artifact_sha256{filename: sha}` in #4. There is no 1:1 mapping onto `weights_sha` /
`tokenizer_hash` / `corpus_sha256`. **Any choice a shim makes is an editorial act and must be
disclosed in `caveats`.**

**M5 — recorded paths are pod paths and will be rejected.**
Every path inside #1 and #4 is a RunPod path, e.g.
`/workspace/cas-tks-anchor-diagnostic-20260721/artifacts/full/tks_definition_anchor_raw_diagnostic_vectors.npz`
(`local_raw_diagnostic_artifact.path`) and
`/workspace/cas-tks-anchor-diagnostic-20260721/source/repo/noetic-compass-scaffold/…/run_tks_definition_anchor_diagnostic.py`
(`provenance.code.script_path`). `_resolve_allowed_path` rejects these with
`"path is outside allowed roots"` (`api/routes/evidence.py:233-234`) or `"file not found locally"`
(`:236-237`). Consequence: every check row gets `actual: null, match: false`, and `overall` computes to
`unable_to_verify` (`:819-820`).
**Recoverable, and this is the item's best available demonstration** — see §6.1.

**M6 — the fixture's own `schema_version` has nowhere to go.**
`EvidencePacket.schema_version` is a hard default `"evidence_packet.v1"` (`api/routes/evidence.py:69`)
and is not settable from the trace. `cas_harness_tks_definition_anchor_diagnostic.v1`,
`cas_harness_research_shadow.jacobian_lens_canary_execution_receipt.v3`,
`cas_harness_off_pod_verification.v1`, `cas_harness.pythia_gpt_neox_block_hook_equivalence_preflight.v1`,
`atlas_viewer_trace_v1` — none can be expressed except in free text.

**M7 — no typed carrier for claim state. This is the Gate-2-critical mismatch.**
The `EvidencePacket` model (`api/routes/evidence.py:62-80`) has **no field** for any of:
`licensing_status`, `claim_eligible`, `claim_status`, `execution_mode`, `verdict_influence`,
`verdict`, `non_claim`, `technical_only_notice`, `cryptographic_model_origin_proven`,
`external_reproduction_verified`. Every candidate fixture carries some of these, and every one is
`NOT_LICENSED` and/or `claim_eligible: false`:

| Fixture | Recorded claim state |
| --- | --- |
| #1 | `licensing_status: NOT_LICENSED_DIAGNOSTIC_ONLY`, `claim_eligible: false` |
| #2 producer | `claim_status: NOT_LICENSED`, `execution_mode: SHADOW`, `verdict: NONE` |
| #2 receiver | `claim_status: NOT_LICENSED`, `execution_mode: SHADOW`, `verdict_influence: NONE`, `receiver_status: TECHNICAL_CANARY_PASS_OPERATOR_ATTESTED_PENDING_EXTERNAL_REPRODUCTION`, **`cryptographic_model_origin_proven: false`**, **`external_reproduction_verified: false`**, `technical_only_notice` = `"Mathematical consistency plus an RFC3161-anchored operator execution was verified. This is not cryptographic model-origin proof and not external reproduction. It grants no semantic, prompt-injection, output-control, universality, 300B, CJT, RPM, J-Space, or CAS-Ohm license."` (values read directly, 2026-07-24 — the two booleans are `false`, not merely "present") |
| #3 | `licensing_status: NOT_LICENSED_DIAGNOSTIC_ONLY`, `claim_eligible: false` |
| #4 | `licensing_status: NOT_LICENSED_CANARY_ONLY`, `claim_eligible: false` |
| #5 | `licensing_status: NOT_LICENSED_PREFLIGHT_ONLY`, `claim_eligible: false` |
| #6 | `claim_status: NOT_LICENSED`, `execution_mode: SHADOW`, `claim_eligible: false` |

These cannot be smuggled into `claim_levels[].level`, which is locked to four values
(`SPEC.md:57`, `dashboard/src/lib/evidence_packet.ts:24-28`). The only available carriers are
`caveats: list[str]` and the free-text `support_rationale` / `rationale` fields. **A replay that drops
them renders a not-licensed shadow diagnostic as an ordinary Evidence Packet. Preventing exactly that
is what item 8 has to be designed around.**

**M8 — discovery fails before any of the above matters.**
No candidate is discoverable today. Verified on disk on this host:
`dashboard/public/traces/` — does not exist. `cas-native/trace/captures/` — does not exist.
`<tksCAS>/cas-synthetic/data/traces/` — does not exist. `.tmp/traces/` — exists, contains exactly three
unrelated UUID-named files: `57476114-79d5-4689-b1f9-65b869e24d99.json`,
`94b1b116-3a6f-4cd3-8687-222d78e24cda.json`, `b232683e-09a3-4e0a-ba55-a203d0204e17.json`.
Neither `project_handoffs/` nor `.claude/worktrees/` nor `D:/tksCAS-archive/` is searched by
`_candidate_trace_paths`. Additionally, every fixture is named for its content
(`tks_definition_anchor_report.json`), not for a `trace_id`.

---

## 4. Non-destructive replay procedure

Two properties together constitute "without overwriting the historical record":
**(a)** no write to any tracked path or any fixture file, and **(b)** a ledger proving the replay
output is a derived view, not a restatement of the original.

### 4.0 Hard rules

1. **Never invoke `merge_stage9_40e_evidence_packet.py` without BOTH `--output-json` and
   `--output-markdown`** pointed at `docs/working/gate2_closure/` or a scratch dir. It calls
   `write_text` unconditionally with no exist-check (`:544`, `:548`) against defaults inside
   `noetic-compass-scaffold/noetic-compass/docs/working/` (`:28-34`). This is the only action in the
   whole item that can overwrite a historical record. (Partial mitigation already in place: the
   default input `gpt_neox_20b_stage9_original_40e_probe_eval_report_20260527.json` does not exist on
   this branch — verified by `ls` — so a default invocation `SystemExit`s at `:75` before writing.)
2. **Never open a fixture file for writing.** The shim reads only.
3. **Do not `git add` or commit anything under `.tmp/`.**

### 4.1 Step 0 — record the pre-state (proves the original was untouched)

```
# from C:/Users/wakil/OneDrive/Desktop/tksCAS
python - <<'PY'
import hashlib, json, pathlib
roots = [
 "project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/02_RESEARCH_EVIDENCE/full_recovery",
 "project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/04_PROTOCOL_AND_ANCHOR/ATTEMPT_11_TECHNICAL_CANARY_PASS_GATE1",
 "project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/02_RESEARCH_EVIDENCE/supporting_local_preflight",
]
out = {}
for r in roots:
    for p in sorted(pathlib.Path(r).rglob("*")):
        if p.is_file():
            h = hashlib.sha256()
            for c in iter(lambda f=p.open("rb"): f.read(1<<20), b""): h.update(c)
            st = p.stat()
            out[str(p).replace("\\","/")] = {"sha256": h.hexdigest(), "bytes": st.st_size, "mtime_ns": st.st_mtime_ns}
pathlib.Path("docs/working/gate2_closure/item8_fixture_prestate_20260724.json").write_text(
    json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
print(len(out), "files fingerprinted")
PY
```

Also record `git status --porcelain` and `git rev-parse HEAD` into the same directory. These two
records are the evidence that nothing historical moved.

### 4.2 Step 1 — write the shim (read-only, one module)

Location: `docs/working/gate2_closure/item8_fixture_to_evidence_packet_shim.py`, or under
`live-trace-worker/scripts/` if it is to be a durable tool. It must:

* open every fixture read-only and never mutate one;
* map fixture → an `evidence_packet.v1`-shaped **trace dict** (the keys listed in §2.1, not the packet
  keys — the builder rebuilds the packet);
* set `model_checkpoint_id` from the fixture's `provenance.model_id` (M3 defence);
* rewrite the pod paths of M5 to the local recovered paths, and **record the rewrite as a caveat**;
* copy every claim-state string of M7 verbatim into `caveats[]`;
* keep `claim_levels[].level` inside the four locked values.

Required tests (these are the honesty gates, not optional polish):

1. every fixture status string (`licensing_status`, `claim_status`, `execution_mode`,
   `verdict`/`verdict_influence`, `claim_eligible`, `official_pass_authorized`,
   `maximum_producer_status`, `cryptographic_model_origin_proven`, `external_reproduction_verified`,
   and — for the §1.1 Stage-7 fixtures, which have no claim-state field — `status` and the full
   `reserved_interpretation` text) appears **verbatim** in the emitted `caveats`, with booleans
   rendered as their values (`false`), never as bare key names;
2. `claim_levels[].level` only ever takes one of `cas_hard_trace | source_copy_evidence |
   derived_trace | neural_attribution_estimate`;
3. every path rewrite is disclosed as a caveat;
4. the emitted `provenance.model_checkpoint_id` is `EleutherAI/pythia-160m` and a dedicated caveat
   carries revision `50f5173d932e8e61f858120bcb800b97af589f46`;
5. the emitted `schema_version` of the source fixture appears in `caveats`;
6. if a §1.1 Stage-7 fixture is in scope, the caveats record that it was materialised from branch
   `experiment/cas-probe-pythia` and is not in this branch's working tree, and that its raw
   activations NPZ is `unavailable` so no re-hash was performed for it.

### 4.3 Step 2 — replay in-process, writing nothing at all (preferred)

There is an existing, passing, in-repo precedent for exactly this shape:
`noetic-compass-scaffold/noetic-compass/tests/test_evidence_routes.py:171-259`
(`test_evidence_get_preserves_s7_f28_20b_packet_claims`; the function body ends at `:259`). It replays
a research run (`trace_id = "gpt-neox-20b-s7-f28-balanced-logistic"`, model `EleutherAI/gpt-neox-20b`)
through the live builder by monkeypatching `evidence_route._load_trace_artifact` to return a
hand-built dict, then asserts `body["claim_levels"] == trace["claim_levels"]` (`:258`) and that the
caveat `"verifier merge is still pending"` survives (`:259`). It writes nothing, needs no JWT beyond the test
fixture's headers, and **proves the builder does not rewrite claim rows or caveats.**

Use the same mechanism: monkeypatch `_load_trace_artifact` with the shim output, or call
`evidence.build_packet_for_trace(trace_id)` directly (`api/routes/evidence.py:689`). Zero disk writes,
zero auth setup.

Replay order — smallest first, so a shim bug is caught cheaply:

1. `tks_definition_anchor_canary_receipt.json` (25,181 B, `CANARY_PASS`) — shim smoke.
2. `cas-pythia-hook-equivalence-local-20260721.json` (19,769 B, `PREFLIGHT_PASS`).
3. `OFF_POD_VERIFICATION.json` (5,410 B) — supplies the exact model/revision row.
4. `jacobian_lens_canary_v1_receiver_receipt.json` (7,396 B), then the 174,830 B producer receipt.
5. **Last:** `tks_definition_anchor_report.json` with the NPZ path rewritten, so `POST /verify`
   performs a genuine sha256 re-hash (§6.1).

### 4.4 Step 3 — only if an HTTP/UI demonstration is required

Stage shim output into `noetic-compass-scaffold/noetic-compass/.tmp/traces/`. This directory is
git-ignored — verified: `git check-ignore -v .tmp/traces/replay_x.json` returns
`noetic-compass-scaffold/noetic-compass/.gitignore:20:.tmp/`. Nothing tracked can be mutated by
writing there.

* Use filenames that collide with none of the three existing files listed in M8.
* Prefer explicit non-UUID names, e.g. `replay_tks_definition_anchor_full_20260721.json`, so replay
  artifacts are never mistaken for live Mode 7 captures. The read route accepts these
  (`api/routes/evidence.py:259` only strips slashes) even though the Mode 7 writer's UUID4 gate
  (`api/routes/mode7.py:1439`) could never have produced them. **Disclose this deviation** —
  `SPEC.md:147` documents `trace_id` as UUID4, so a reviewer will find it.
* HTTP replay needs a JWT Bearer token (`api/middleware/auth.py:33-37`); confirmed by
  `tests/test_evidence_routes.py:40-46`, which asserts 401 on both endpoints without auth.

### 4.5 Step 4 — where output goes

All replay output goes to `docs/working/gate2_closure/`. Nothing goes into `project_handoffs/`,
`D:/tksCAS-archive/`, or `noetic-compass-scaffold/noetic-compass/docs/working/`.

* `item8_fixture_prestate_20260724.json` — Step 0 fingerprints.
* `item8_replay_packets/<fixture>.packet.json` — the rendered packets.
* `item8_replay_ledger_20260724.json` — the ledger (§4.6).
* `item8_fixture_poststate_20260724.json` — Step 5 fingerprints.

### 4.6 The replay ledger (required)

Per fixture, record: source path; source sha256; fixture `schema_version`; fixture
`licensing_status` / `claim_status` / `claim_eligible` / `execution_mode` / `verdict` verbatim; **every
field the shim DROPPED**; **every field the shim INVENTED**; every path rewritten (from → to); and the
resulting packet's `overall` verify result. The dropped/invented columns are what make the replay a
derived view rather than a restatement.

### 4.7 Step 5 — prove the original was untouched

Re-run the Step 0 fingerprint script into `item8_fixture_poststate_20260724.json` and diff against the
prestate. The proof of non-destruction is: **prestate == poststate on every sha256, byte count, and
mtime_ns**, plus a `git status --porcelain` showing no modification under `project_handoffs/` and no
new tracked file under `.tmp/`. Attach both files and the diff to the ledger.

---

## 5. What a successful replay would and would not establish

Pre-registered here, before any run, so it cannot be adjusted afterward.

**Would establish (`real`, if the run succeeds):** that the live packet builder ingests a shimmed
research fixture and renders it; that claim rows and caveats survive the builder unmodified (already
demonstrated by `tests/test_evidence_routes.py:258-259`); and — for candidate #1 only — that
`POST /verify` can re-hash a real 109 MB raw artifact and return `all_match` on that row.

**Would not establish (`not-licensed`, unchanged):** anything about the underlying science. #1's sole
pre-registered primary estimand is `0.0042517006802721136` with a 95% CI of
`[-0.001275510204081634, 0.010204081632653059]` — **an interval that includes zero** — and its own
`non_claim` states it "does not license semantic-probe validity, causal control, prompt-injection
detection, output control, cross-architecture universality, 300B execution, production readiness, an
ACCEPT verdict, or any customer/investor claim," and further that "The NPZ and its manifest are local
diagnostic artifacts, not WORM anchors or Evidence Packets." #2 self-declares `claim_status:
NOT_LICENSED`, `execution_mode: SHADOW`, `verdict: NONE`, `official_pass_authorized: false`.

**Also would not establish, for the §1.1 Stage-7 fixtures specifically.** Those are the strongest
saved Pythia/TKS fixtures by their own numbers (§1.0), so it is worth pre-registering the limit
explicitly: rendering them through the packet builder would establish that the builder ingests them.
It would establish nothing about the Stage-7 result itself, which is already bounded by the fixtures'
own `reserved_interpretation` text — *"A pass would support hidden-state readout beyond text
baselines; it would not prove generation control or solve the black-box problem"* and *"a causal
intervention on the representation/readout, not a causal language-generation test."* A replay does not
re-run the probe, does not re-run the ablation, and does not add a control.

**And would not establish `control_proof: present`.** Not by any route on this branch — see §2.3 and
§8.1. This is pre-registered here so it cannot be presented as a surprise after a run.

A successful replay is therefore: **real plumbing + not-licensed content.** It does not by itself move
Gate 2 from `0.38` toward `0.46`. Item 8 is infrastructure whose value is that it makes items 1-7
presentable.

---

## 6. Verified facts established while writing this document

### 6.1 The one independently reproduced result (`real / verified`)

The recovered raw diagnostic NPZ was re-hashed on this host on 2026-07-24:

```
file:     project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/02_RESEARCH_EVIDENCE/
          full_recovery/artifacts/full/tks_definition_anchor_raw_diagnostic_vectors.npz
bytes:    109,414,103
recorded: 454a4f017d56ed393e50d7e88d29486b3379e96ae930a1123698c6275298ead6
           (tks_definition_anchor_report.json -> local_raw_diagnostic_artifact.sha256)
computed: 454a4f017d56ed393e50d7e88d29486b3379e96ae930a1123698c6275298ead6
result:   MATCH
```

This matters operationally: the local copy sits under `_project_root()` (= `tksCAS/`, per
`api/routes/evidence.py:110-115`) and so passes the allowlist, and 109,414,103 B is far under the 8 GiB
cap (`:201`). **A shim that rewrites the pod path to this local path lets `POST /verify` return a
genuine `all_match` on the `corpus` row rather than `unable_to_verify`.** That is the strongest
demonstration available for item 8, and it is the reason the path rewrite of M5 is worth doing — and
the reason it must be disclosed as a caveat rather than performed silently.

The NPZ's recorded shapes are `definition_shape [3, 28, 12, 768]` and `eval_shape [3080, 12, 768]`,
with `allow_pickle: false` and status
`LOCAL_DIAGNOSTIC_ARTIFACT_ATOMIC_WRITE_REOPEN_VERIFIED`.

### 6.2 Gaps closed from the gathering pass

Read directly out of
`.../ATTEMPT_11_TECHNICAL_CANARY_PASS_GATE1/evidence/jacobian_lens_canary_v1_execution_receipt.json`
on 2026-07-24 — all three values, not just the first:

| Field | Value |
| --- | --- |
| `verdict` | `"NONE"` |
| `official_pass_authorized` | `false` |
| `maximum_producer_status` | `"TECHNICAL_CANARY_PASS_CANDIDATE_PENDING_INDEPENDENT_VERIFICATION"` |

`official_pass_authorized: false` matters for M7: it is a fourth claim-state boolean with no typed home
in `evidence_packet.v1`, and it says the producer receipt does not authorize an official pass. No part
of this receipt is now recorded as `unavailable`.

### 6.3 Existence of the Stage-7 Foundation fixture family

Recorded here because an earlier pass treated this family as unavailable and that was wrong. Both
Stage-7 JSONs exist and were read for this document via
`git show experiment/cas-probe-pythia:noetic-compass-scaffold/noetic-compass/research/cas_probe/<file>`,
with blob sizes taken from `git ls-tree -r -l experiment/cas-probe-pythia`. Full field readout in
§1.1. They are `real` as artifacts and `unavailable` in this branch's working tree — two different
statuses, both recorded.

---

## 7. Recorded gaps and verified absences

Two different statuses appear in this table and are deliberately not merged. A **verified absence in
code** is `real` — the search ran and returned nothing, which is a finding. An **`open` gate
requirement** is a question the evidence does not answer. An **`unavailable`** row is something not
found in the paths searched, where the search itself is the record.

| Gap / absence | What was searched | Status |
| --- | --- | --- |
| `control_proof` in the served path | ripgrep for `control_proof` under `noetic-compass-scaffold/noetic-compass/api/` → 0 hits. It exists only at `live-trace-worker/scripts/merge_stage9_40e_evidence_packet.py:464` and its test | `real` — verified structural absence: Path A cannot emit the field. (The *gate requirement* that something emit `control_proof: present` remains `open`; that is §8.1, a separate status) |
| A cover-discovery report for Path B's `--cover-report` | `ls noetic-compass-scaffold/noetic-compass/docs/working/ \| grep -iE 'stage9\|40e\|cover'` → 3 planning `.md` files, no JSON; `ls docs/working/ \| grep -iE 'stage9\|40e\|cover'` → 8 files, none a cover-discovery report; `rglob("*cover*")` over `live-trace-worker/`, `noetic-compass-scaffold/noetic-compass/docs/`, `docs/` → source and test modules only (`discover_stage9_40e_neuron_covers.py`, `cover_library.py`, `test_cover_library.py`, `test_stage9_40e_neuron_covers.py`) plus unrelated `*coverage*` docs | `unavailable` on this branch, scoped to those paths. Consequence: Path B emits `control_proof.status = "missing"` (`merge_stage9_40e_evidence_packet.py:355-365`), never `present`, unless such a report is produced first |
| A Pythia/TKS fixture that could populate the `cover_discovery` tier | Tier name and artifact ids read at `merge_stage9_40e_evidence_packet.py:426-431` (`cover_discovery`, `stage9_40e_cover_discovery_report`); compared against the §1 and §1.1 census | `real` — verified mismatch. No item-8 fixture is a cover-discovery report; the tier is the Stage-9 40E / GPT-NeoX-20B family |
| Stage-7 Foundation-28 pilot + layer-6 ablation reports | Present on branch `experiment/cas-probe-pythia` (§1.1); absent from this branch's working tree (`ls noetic-compass-scaffold/noetic-compass/research/cas_probe/`) | `real` as artifacts (read via `git show`), `unavailable` in this working tree. **Correction to an earlier pass that treated them as unavailable outright** |
| Stage-7 raw activations NPZ `stage7_foundation_pilot_activations_20260517.npz` | `git ls-tree -r experiment/cas-probe-pythia -- .../research/cas_probe/` → not tracked; not in this working tree | `unavailable`. Only its `sha256` (`d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f`) is recorded, so no §6.1-style re-hash is possible for this fixture |
| Path B's default input | `ls noetic-compass-scaffold/noetic-compass/docs/working/gpt_neox_20b_stage9_original_40e_probe_eval_report_20260527.json` → no such file. Same for the default output packet | `unavailable` on `codex/cascompass-legal-live-source`. The script fails closed at `:75`, which is correct behaviour |
| WORM / customer-API Evidence Packet writer | `docs/working/cas_harness_production_todo.md:17050` describes customer-API and hosted live-worker Evidence Packets carrying `instruction_integrity`, attributed to branch `codex/cas-harness-public-beta-candidate`. ripgrep for `worm\|WORM\|object_lock\|anchor` under `api/` returned only `visual_grounding.py`, `mode7.py`, `notation/inversion.py`, `notation/compiler.py` — no evidence-packet writer | `unavailable` on this branch. **If the roadmap means that path by "the current live Evidence Packet path," this assessment targets the wrong code** — see §8.1 |
| Saved Pythia run JSONs for Stage 27F/G sparse neuron-cover or Stage 27P eraser steering | `ls docs/working/ \| grep -iE 'stage27\|neuron_cover\|eraser\|sparse_cover\|27f\|27g\|27p'` → 0; `ls docs/working/*.json` → 32 files, none matching; `ls noetic-compass-scaffold/noetic-compass/docs/working/*.json \| grep -iE 'stage9\|40e\|stage27\|cover\|eraser\|pythia\|probe'` → 0 | `unavailable` **in this branch's working tree**, in the searched locations. Not a claim about other branches — the Stage-7 family (§1.1) is a worked example of a saved Pythia fixture that this class of working-tree search does not reach. `git branch --list` shows the repo carries a large branch set; other saved Pythia fixtures may be reachable the same way |
| Full-repo grep | `grep -rn` from the `tksCAS` root times out (>120 s); two attempts killed. All searches used ripgrep with explicitly narrowed paths | Every "not found" above is scoped to the paths named, **not** to the whole repository |

---

## 8. Flagged for human review

### 8.1 Which path is "the current live Evidence Packet path"?

Item 8 says the path, singular. Two exist and only one can satisfy the exit clause:

| | Path A | Path B |
| --- | --- | --- |
| File | `api/routes/evidence.py` | `live-trace-worker/scripts/merge_stage9_40e_evidence_packet.py` |
| Schema | `evidence_packet.v1` | `cas_harness_stage9_40e_evidence_packet.v1` |
| Served by the app? | **Yes** (`api/main.py:135`) | No — offline CLI |
| Writes? | **No** (`evidence.py:3-4`) | **Yes** (`:544`, `:548`) |
| Emits the `control_proof` key? | **No** (absent from all of `api/`) | **Yes** (`:464`) |
| Can emit `control_proof: present`? | **No** — field does not exist | **Not on this branch** — requires `--cover-report` (`:426-431`, `:555`); no such report found (§2.3, §7) |

A third piece of in-repo evidence bears directly on "which path is live," and it corroborates Path A
being the served surface while classing Evidence Packets as export-time, not worker-runtime, output:
`live-trace-worker/app/schemas/methods.py:51` records
`"evidence_packet": "accepted only by artifact/export code, not by the live worker runtime"` (and
`:52` says the same of `spatial_evidence_layer`). The same table records
`"sparse_neuron_cover": "no live worker causal cover discovery is wired yet"` (`:54`) — consistent
with §2.3's finding that no cover-discovery report exists to supply `--cover-report`.

**The premise has changed since the first draft of this section.** It is not "Path A is live but
cannot emit `control_proof`, Path B can." It is:

> On this branch, **neither path can produce `control_proof: present`.** Path A has no such field
> (ripgrep, §2.2). Path B has the field but its value defaults to
> `{"status": "missing", …, "blocking_reason": "cover_discovery report was not supplied"}`
> (`merge_stage9_40e_evidence_packet.py:355-365`), and the report that would flip it to `present` does
> not exist here (§2.3 item 3) and could not be produced by any item-8 fixture anyway, because the
> tier is `cover_discovery` — the Stage-9 40E / GPT-NeoX-20B family, not Pythia/TKS (§2.3 item 4).

That kills option (a) as previously written. The revised options, none of which an agent may pick
unilaterally:

* **(a′) Replay targets both paths.** Still produces no `control_proof: present` — Path B would emit
  `status: "missing"` with its blocking reason. Legitimate as an honest artifact; it does not satisfy
  the exit clause's `control_proof: present` clause.
* **(b) `evidence_packet.v1` gains a control-proof field.** Engineering work plus a schema change to a
  locked spec (`SPEC.md` §4, and the four-/six-value client locks at
  `dashboard/src/lib/evidence_packet.ts:24-28`, `:37-43`).
* **(c) The exit clause is read as scoped.** The clause says `control_proof: present` **"where controls
  ran"** (`CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:217-220`). On that reading, item 8 —
  a replay of saved fixtures through a packet builder — is not a run where controls ran, and the
  clause does not bind it. This is the reading that would let item 8 close without new schema work,
  and it is exactly the kind of reading an agent must not adopt on its own.
* **(d) Produce a cover-discovery report first.** `discover_stage9_40e_neuron_covers.py` exists
  (`live-trace-worker/scripts/`). This is out of item 8's scope and out of Pythia/TKS scope — it is
  Stage-9 40E work on a 20B model.

**Owner adjudication required before any shim is written.** The decision is now (a′)/(b)/(c)/(d), and
the honest framing is that no option except (b) or (d) makes `control_proof: present` reachable, and
neither is item-8 work.

### 8.2 Claim-state blurring is the highest-severity risk in this item

Stated once more because it is the thing most likely to go wrong quietly: the live packet has no typed
home for `licensing_status` / `claim_status` / `claim_eligible` / `execution_mode` /
`verdict_influence` (M7), and the four-value `claim_levels[].level` vocabulary is locked
(`SPEC.md:57`, `dashboard/src/lib/evidence_packet.ts:24-28`). Every candidate fixture is
`NOT_LICENSED`. If the shim drops those strings, a shadow diagnostic renders as an ordinary Evidence
Packet. The caveats-completeness test in §4.2 is **mandatory, not optional**. Whether the right long-term
fix is a typed `claim_state` block on `evidence_packet.v1` is an owner/spec decision, not a shim
decision.

### 8.3 Reserved language

`docs/working/evidence_packet_2026_05_15/SPEC.md:10`: *"Reserved language: **never 'irrefutable.'**
Always **tamper-evident, reproducible, independently inspectable**."* The fuller rule is at
`SPEC.md:35-37`: never "irrefutable", "proven", "guaranteed correct", or "verified by
Claude/Codex/Anthropic"; and *"A neural attribution number is evidence. A hash match is
tamper-evident. A compile pass is deterministic."* Replay output and its ledger must observe both.
Note this constrains §1.1's language too: the Stage-7 ablation's `status` string contains the word
`CAUSAL`, and quoting a status field verbatim is allowed, but the replay ledger must not restate it as
a proof claim.

---

## 9. Verdict

**Item 8 is NOT closable as documentation-plus-a-replay-run today. It requires engineering work
first — a read-only fixture→packet shim — and, before that, an owner decision that is now sharper than
"which path": whether item 8 is bound by the exit clause's `control_proof: present` at all.**

This verdict is re-derived after correcting the `control_proof` premise and after adding the Stage-7
fixture family that an earlier pass missed. Neither correction rescues item 8; the second makes the
engineering finding stronger, not weaker.

Plainly:

1. **Zero candidate fixtures ingest as-is — now nine, not seven.** Discovery fails first (M8: no
   fixture lives in any of the five directories at `api/routes/evidence.py:257-273`, and none is named
   for a trace_id), and even after staging, the key overlap with what `_packet_from_trace` reads is nil
   (M1, M2, M3). The two Stage-7 reports added at §1.1 fail the same way and are additionally not in
   this branch's working tree. There is no "just point it at the file" version of this item.
2. **The engineering required is small and bounded** — one read-only mapping module plus five tests
   (§4.2). It is not a research task and needs no compute. But it is engineering, and item 8 cannot be
   marked done by writing a document. This is a finding about the code, not a preference: the input
   schema `_packet_from_trace` reads (`:602-686`) and the fixture schemas have an empty intersection,
   and no code in the tree bridges them.
3. **"Strongest" is now adjudicated (§1.0), and the answer complicates the item.** The strongest saved
   Pythia/TKS fixture family is the Stage-7 Foundation-28 pilot + layer-6 ablation on branch
   `experiment/cas-probe-pythia` — hidden readout `0.7857` vs its own **character-level** surface
   control `0.4966`, McNemar `p = 2.66e-95`, plus 30 matched random-complement controls at one-sided
   `p = 0.0323` against pre-registered `decision_gates`. Item 8 says replay *the strongest* fixtures.
   Doing that honestly means materialising artifacts out of another branch, and it means the shim must
   carry `reserved_interpretation` — the only scope limit those two artifacts have — because they
   carry no `licensing_status` or `claim_eligible` field at all.
4. **The replay itself, once the shim exists, is genuinely non-destructive** and can be executed with
   zero disk writes via the mechanism already proven at
   `tests/test_evidence_routes.py:171-259`. The one write hazard in the whole item is Path B's
   unconditional `write_text` (`:544`, `:548`), fully mitigated by always passing `--output-json` and
   `--output-markdown`.
5. **The blocking question is §8.1, and it is not "which path."** Both paths were surveyed and neither
   can produce `control_proof: present` on this branch: Path A has no such field; Path B's value
   defaults to `missing` absent a `--cover-report` that does not exist here and whose tier
   (`cover_discovery`) no Pythia/TKS fixture could fill. So the owner question is whether item 8 is
   bound by that clause — the clause reads `control_proof: present` **"where controls ran"** — or
   whether a schema change (option b) or out-of-scope Stage-9 work (option d) is being asked for.
   Shim work before that answer risks being aimed at code that cannot close the gate.
6. **Even a fully successful replay leaves Gate 2 where it is.** On this branch's working tree the
   best fixture's primary estimand has a 95% CI that includes zero and its own `non_claim` disclaims
   semantic-probe validity; the best-instrumented Pythia fixture self-declares
   `NOT_LICENSED / SHADOW / verdict: NONE / official_pass_authorized: false`. The genuinely strong
   Stage-7 family (§1.1) bounds itself in its own `reserved_interpretation`. Per the exit clause,
   "Mixed or negative results remain `OPEN / NOT LICENSED`." Item 8 makes items 1-7 presentable; it
   does not supply evidence of its own.

**Recommended next action:** owner adjudicates §8.1 as restated — (a′) both paths and accept
`control_proof: missing`, (b) schema change, (c) scoped reading of "where controls ran", or (d)
produce a cover-discovery report (out of item-8 scope). Then decide whether "strongest" means the
Stage-7 family (§1.1, cross-branch) or the on-branch census (§1.2). Then build the shim per §4.2 with
its five tests, and execute §4.1 → §4.7 in the order given. Do not run anything against
`--output-json` defaults.

---

## Sources

Every file below was opened and read for this document on 2026-07-24 on branch
`codex/cascompass-legal-live-source`. Paths are absolute.

**Controlling text**
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md` (Gate 2 section; item 8 at `:214-215`; exit clause at `:217-220`)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/cas_harness_production_todo.md` (`:954` Gate 2 definition, `:955` Gate 3 = prompt injection, `:17050` WORM/customer-API note — cited from the gathering pass, not independently re-read)

**Live Evidence Packet path (Path A)**
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/routes/evidence.py`
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/main.py`
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/middleware/auth.py`
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/api/routes/mode7.py` (`_persist_evidence_trace`, `_UUID4_RE` — cited from the gathering pass, not independently re-read)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/tests/test_evidence_routes.py`
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/dashboard/src/lib/evidence_packet.ts`
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/docs/working/evidence_packet_2026_05_15/SPEC.md`
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/.gitignore` (`:20` = `.tmp/`)

**Offline merge path (Path B)**
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/live-trace-worker/scripts/merge_stage9_40e_evidence_packet.py`
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/live-trace-worker/app/schemas/methods.py` (`:51` `evidence_packet` method note, `:52` `spatial_evidence_layer`, `:54` `sparse_neuron_cover`)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/live-trace-worker/scripts/discover_stage9_40e_neuron_covers.py` (existence confirmed by search; contents not read)

**Strongest saved Pythia/TKS fixtures — branch `experiment/cas-probe-pythia`, NOT this branch's working tree**

Read via `git show experiment/cas-probe-pythia:<path>`; blob sizes via
`git ls-tree -r -l experiment/cas-probe-pythia`. Paths are repo-relative on that branch.
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_pilot_probe_report_20260517.json` (2,255,209 B)
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_layer6_ablation_report_20260517.json` (56,257 B)
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_pilot_activations_manifest_20260517.json` (1,231 B)
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_pilot_manifest_20260517.json` (1,675 B)
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_pilot_validation_20260517.json` (1,195 B)
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_pilot_20260517.jsonl` (9,021,812 B — listed in the tree; contents not read)
- `noetic-compass-scaffold/noetic-compass/research/cas_probe/stage7_foundation_pilot_activations_20260517.npz` — **not tracked on that branch and not on disk here.** `unavailable`; only its recorded sha256 is known

**Candidate fixtures**
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/02_RESEARCH_EVIDENCE/full_recovery/artifacts/full/tks_definition_anchor_report.json`
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/02_RESEARCH_EVIDENCE/full_recovery/artifacts/full/tks_definition_anchor_raw_diagnostic_vectors.npz` (re-hashed, §6.1)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/02_RESEARCH_EVIDENCE/full_recovery/artifacts/full/tks_definition_anchor_local_artifact_manifest.json` (listed; contents not read)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/02_RESEARCH_EVIDENCE/full_recovery/artifacts/full/FULL_BUNDLE_SHA256SUMS` (listed; contents not read)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/02_RESEARCH_EVIDENCE/full_recovery/artifacts/canary-8prompt-2layer/tks_definition_anchor_canary_receipt.json`
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/02_RESEARCH_EVIDENCE/full_recovery/OFF_POD_VERIFICATION.json`
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/02_RESEARCH_EVIDENCE/supporting_local_preflight/cas-pythia-hook-equivalence-local-20260721.json`
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/04_PROTOCOL_AND_ANCHOR/ATTEMPT_11_TECHNICAL_CANARY_PASS_GATE1/evidence/jacobian_lens_canary_v1_execution_receipt.json`
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/04_PROTOCOL_AND_ANCHOR/ATTEMPT_11_TECHNICAL_CANARY_PASS_GATE1/evidence/jacobian_lens_canary_v1_receiver_receipt.json`
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/04_PROTOCOL_AND_ANCHOR/ATTEMPT_11_TECHNICAL_CANARY_PASS_GATE1/` (directory listing: `STATUS.md`, `evidence/PRE_REVERIFY.json`, `jacobian_lens_canary_v1_anchor_receipt.json`, `..._post_run_capture.json`, `..._execution_receipt.json.publication.json`, `launch_started.json`, `launch_finished.json`, `wrapper.stdout.log`)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/08_JSPACE_CAS_OHM_SHADOW_2026-07-21/research_shadow_baseline_final.json` (from the gathering pass; not independently re-read)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/CJT_BIAS_RPM_OHM_STATISTICAL_V1.json` (from the gathering pass; not independently re-read)
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/noetic-compass-scaffold/noetic-compass/atlas-viewer/test-fixtures/pythia_160m_reference_trace.json` (from the gathering pass; not independently re-read)

**Excluded but recorded**
- `C:/Users/wakil/OneDrive/Desktop/tksCAS/project_handoffs/CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21/11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/GATE2_W0_FAIR_COMPARISON/STATUS.md`

**Second copy / fallback**
- `D:/tksCAS-archive/ATTEMPT_11_TECHNICAL_CANARY_PASS_GATE1` and `..._final` (recorded from the gathering pass as reachable on this host; not opened for this document)
