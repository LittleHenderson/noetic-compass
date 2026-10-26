# AUDIT TARGET INVENTORY — CAS / Noetic Compass / CAS Harness
Audited live from disk 2026-08-22; every path re-verified against the current filesystem and git state. Paths only. No instructions.

---

## 0. Repository roots + git branch/HEAD

### Repo 1 — tksCAS
C:\Users\wakil\OneDrive\Desktop\tksCAS
    branch  codex/cascompass-legal-live-source
    HEAD    aff15693bc3e3af174231099cfcef22660e41777
    commit  aff15693  2026-08-22  docs(spec-sheet): RELATION PROFILE -- CAS ^8/^9 is MID-PACK (rank 4 of 6); affirmative evidence AGAINST CAS-specificity
    remote  origin  https://github.com/LittleHenderson/noetic-compass.git
    tree    42 dirty paths (mostly book\ LaTeX/build artifacts; see git status)

### Repo 2 — interpretability successor
C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820
    branch  codex/cas-interpretability-successor-v2
    HEAD    e889d19009834ed0643daf02996ffea472987b23
    commit  e889d190  2026-08-22  research(v33): RELATION PROFILE -- CAS ^8/^9 is MID-PACK; three ordinary relations beat it. Evidence AGAINST CAS-specificity ($0)
    remote  origin  https://github.com/LittleHenderson/noetic-compass.git
    gitdir  linked worktree of Repo 1 .git: C:\Users\wakil\OneDrive\Desktop\tksCAS\.git\worktrees\cas_interpretability_successor_20260820
    tree    1 untracked path: ?? infra\runpod_precreate_guardian_aws\

### Divergence flag
Both repos share the same root document set (identical .docx / .pdf / CLAUDE.md / CHANGELOG.md filenames at top level) but have diverged.
infra\ , tools\runpod_open_weight_canary_v2\ , and the v1-v33 detector series exist ONLY in Repo 2.
Any reference to "the CLAUDE.md" must be repo-qualified.

---

## 1. Repo 1 — tksCAS

### 1.1 Governance and identity (root)
CLAUDE.md
CHANGELOG.md
README.md
README_CAS_CLI.md
TASKS_SETUP_GUIDE.md
CAS_NATIVE_INVENTORSHIP_MEMO.md
NOETIC_COMPASS_INVENTORSHIP_MEMO.md
CAS_Provisional_Patents_ALL_FIVE.md
PATENT_READINESS_MEMO.md
DISCLOSURE_TIMELINE_EVIDENCE.md
compliance_check.py
vercel.json
render.yaml
cas.bat
bg.sh

### 1.2 Source documents (root, binary/PDF/DOCX)
Noetic_Compass_TAD_v2_CORRECTED.docx
Noetic_Compass_PDR_v2_CAS.docx
Noetic_Compass_Operations_Manual_v2_CAS.docx
Noetic_Compass_Operations_Manual_v2_CAS.docx.bak
Noetic_Compass_Operations_Manual_v2_CAS_recovered.md
Noetic_Compass_Business_Plan_v3_CAS_COMPLETE.docx
Noetic_Compass_Technical_Feature_Overview.docx
CAS_Master_Terminology_Reference.docx
CAS_Alignment_Architecture_Paper_v2.docx
TKS_Alignment_Architecture_Paper.docx
48_Dimensions_Light_and_TKS.docx
phases.docx
TKS_v7_4_FULL_CORRECTED.pdf
TKS_v7_4_REFEREE_DEFENSIBLE (1).pdf
When Light and Consciousness Share the Same Number_ 48-Dimensional Structures in Quantum Photonics and the Tootra Kabbalistic System.pdf
_tmp_2506_21734v3.pdf
_tmp_TKS_FORMAL_MATHEMATICAL_MANUAL_v6_1_COMPLETE.txt
_tmp_TKS_FULL_Cognitive_Framework.txt
_tmp_TKS_v7_4_FULL_CORRECTED.txt
_tmp_TKS_v7_4_REFEREE_DEFENSIBLE_1.txt
all_docx_text.txt
extracted_Noetic_Compass_Operations_Manual_v2_CAS\
recover_docx_text.py
generate_overview_doc.py

### 1.3 docs\ — normative and reference (root files)
docs\CAS_HARNESS_SPEC_SHEET.md                 (living master record of harness capabilities)
docs\CAS_FOUNDATIONAL_CLARIFICATIONS.md        (normative Noetic definitions)
docs\AI_MISALIGNMENT_INCIDENTS_DATABASE.md
docs\INCIDENT_CATEGORIES.md
docs\TAXONOMY_DEVELOPMENT_NOTES.md
docs\CAS_NATIVE_AI_CLAUDE_PLAYBOOK.md
docs\CAS_PREVENTION_CLAIMS.md
docs\CITATION_INDEX.md
docs\REGULATORY_MAPPING.md
docs\NOETICCOMPASS_COM_FEATURE_SPEC.md
docs\CODEX_BUILD_TEMPORAL_COGNITIVE_SCORE.md
docs\CODEX_DEPLOY_DIRECTIVE.md
docs\README.md
docs\self_improving_harness.pdf
docs\forex_trading_execution_plan.pdf
docs\paper_a_v2_section_5_7_diagloop_draft_2026_05_04.md
docs\paper_a_v2_section_5_7_v3_results_template.md
docs\working\AUDIT_TARGET_INVENTORY_20260822.md    (this file)

### 1.4 docs\ subdirectories
docs\architecture\
docs\data\
docs\design\
docs\future\
docs\legal_drafts_20260607\
docs\reference\
docs\releases\
docs\review\
docs\stakeholder\
docs\whitepapers\
docs\working\

### 1.5 Code and product trees
book\
book-formatting\
cas-forex\
cas-native-agent-swarm-scaffold\
cas-synthetic\
cascompass-landing\
noetic-compass-scaffold\
live-trace-worker\
offline-cas\
tools\              (contains ONLY tools\aws_gate5\ — the canary tools exist only in Repo 2)
ip\
dist\
peer_review\
pdf_review\
project_handoffs\
evidence_runs\
stage6_v6_artifacts\
graphify-out\

### 1.6 Root-level experiment scripts
closedbook_kwik_capture.py
knockout_from_generations.py
kwik_enhanced_probe.py
kwik_semantic_entropy.py
lic_eval.py
lic_eval_closedbook.py
lic_eval_coupled.py
lic_eval_fast.py
lic_eval_ortho.py
lic_eval_tuned.py
run_license_oneshot.sh
pt.py
pt_200.py
pt_adm.py
pt_adm2.py
pt_all3.py
pt_inj_delta.py
pt_inject.py
pt_q15.py
pt_q15_delta.py
pt_xfer.py
tmp_probe.py

### 1.7 Root-level artifacts, logs, archives
cas_diagram.html
cas_diagram.svg
oneshot_product.html
oneshot_product.svg
previous_product.svg
quoted_product.svg
repl_product.html
repl_product.svg
repl_product2.html
repl_product2.svg
v1_smoke_lr_fix_manifest_20260505.json
v1_smoke_lr_fix_samples_20260505.jsonl
launch_stopped_after_epoch2_collapse_20260505.log
grimoire_float_probe.stdout.txt
tokenizer_run.out
expr_run.out
texput.log
headers.txt
cas_runpod_operational_backup_20260526.tar.gz
cas_runpod_tksCAS_metadata_backup_20260526.tar.gz
cas_unfrozen_min.tar.gz
noetic-compass-scaffold.tar.gz
pr4_changes.tar
tmp\
tmp_*.log / tmp_*.err.log   (agent_information_flow, agent_message_bus, cas_forex_ui, mt4_activation, mt4_ping, mt4_session, terminal_receipt)
tmp_mt4_activation_dashboard.json
_tmp_lang_tests\
_tmp_playground_IJ_snippet.js
_tmp_playground_bundle.js
codex_pytest_tmp_level3\
codex_tier3_pytest_tmp\
codex_tier3_pytest_tmp_manual\
manual_tmp_test\
New folder\
0,
Claude Setup (2).exe

---

## 2. Repo 2 — interpretability successor

### 2.1 Root (shared document set — same filenames as Repo 1 §1.1/§1.2)
CLAUDE.md
CHANGELOG.md
README.md
README_CAS_CLI.md
TASKS_SETUP_GUIDE.md
CAS_NATIVE_INVENTORSHIP_MEMO.md
NOETIC_COMPASS_INVENTORSHIP_MEMO.md
CAS_Provisional_Patents_ALL_FIVE.md
PATENT_READINESS_MEMO.md
DISCLOSURE_TIMELINE_EVIDENCE.md
(plus the same root .docx/.pdf/.txt source-document set as Repo 1 §1.2)

### 2.2 infra\ — guardian stacks (Repo 2 only)

infra\aws_gpu_standby\
    README.md
    template.yaml

infra\runpod_guardian_live_candidate\
    README.md
    RUNBOOK.md
    template.yaml
    state_machine.asl.json
    core-lock.json
    create_deployment_binding.py
    build.ps1
    .gitignore
    src\
        __init__.py
        guardian_runtime.py
    tests\
        test_guardian_runtime.py
    dist\
        build-manifest.json
        guardian-runtime.zip                 (local disk only — not tracked in git)
    .verify-build-a\guardian-runtime.zip
    .verify-build-b\guardian-runtime.zip
    .verify-quota-a\guardian-runtime.zip
    .verify-quota-b\guardian-runtime.zip

infra\runpod_precreate_guardian_aws\          (untracked in git: ?? infra\runpod_precreate_guardian_aws\)
    README.md
    RUNBOOK.md
    template.yaml
    state_machine.asl.json
    schemas\
        authorization_record.schema.json
        execution_request.schema.json
        inventory_evidence.schema.json
        launch_admission_evidence.schema.json
        signed_receipt_envelope.schema.json
        terminal_evidence.schema.json
    tests\
        test_guardian_iac_contract.py

### 2.3 tools\runpod_open_weight_canary_v2\ (Repo 2 only)
README.md
aws_production_guardian_core.py
verify_activation_parameters.py
preflight_live_activation.py
preprod_account_preflight.py
precreate_guardian_bridge.py
precreate_guardian_offline.py
precreate_guardian_runpod_adapter.py
run_precreate_guardian.py
launch_canary_pod.py
measure_guardian_timing_evidence.py
create_provider_launch_receipt.py
provider_transport_probe.py
induce_missed_ticks.py
github_stop_supervisor.py
arm_github_supervisor.ps1
probe_readonly.ps1
watchdog_armed.ps1
watchdog_unarmed.ps1
requirements-canary-py312-cu128.lock.txt
test_aws_production_guardian_core.py
test_verify_activation_parameters.py
test_preprod_account_preflight.py
test_precreate_guardian_bridge.py
test_precreate_guardian_offline.py
test_precreate_guardian_runpod_adapter.py
test_run_precreate_guardian.py
test_launch_canary_pod.py
test_measure_guardian_timing_evidence.py
test_induce_missed_ticks.py

### 2.4 tools\aws_gate5\ (present in BOTH repos, same files)
tools\aws_gate5\
    README.md
    CALIBRATION_EVIDENCE.txt
    known_live_failure_lint.sh
    .gitattributes

### 2.5 docs\working\detector_validation_20260821\ — full v1-v33 detector series (Repo 2 only)
Write-ups:
    PREREG_DETECTOR_VALIDATION.md
    RESULT_DETECTOR_VALIDATION_20260821.md                       (v1)
    RESULT_DETECTOR_VALIDATION_V2_CROSS_TOPIC_20260821.md
    RESULT_DETECTOR_VALIDATION_V3_MULTIAXIS_20260821.md
    RESULT_DETECTOR_VALIDATION_V4_DOMAIN_20260821.md
    RESULT_DETECTOR_VALIDATION_V5_OPERATOR10_20260821.md
    RESULT_DETECTOR_VALIDATION_V6_HARDENING_NEGATIVE_20260821.md
    RESULT_DETECTOR_VALIDATION_V7_REGISTERDIVERSE_BOUNDED_20260821.md
    RESULT_DETECTOR_VALIDATION_V8_CAUSAL_20260821.md
    RESULT_DETECTOR_VALIDATION_V10_SCALE_PYTHIA69B_20260821.md
    RESULT_DETECTOR_VALIDATION_V11_DOMAIN_FRAMINGMATCHED_20260821.md
    RESULT_DETECTOR_VALIDATION_V12_OPERATOR10_FRAMINGMATCHED_20260821.md
    RESULT_DETECTOR_VALIDATION_V13_CAUSE_EFFECT_CONSTRUCTCORRECT_20260821.md
    RESULT_DETECTOR_VALIDATION_V14_SCALE_CONTROLS_PYTHIA69B_20260821.md
    RESULT_DETECTOR_VALIDATION_V15_SCALE_DOMAIN_PYTHIA69B_20260821.md
    RESULT_DETECTOR_VALIDATION_V16_SCALE_CAUSAL_PYTHIA69B_20260821.md
    RESULT_DETECTOR_VALIDATION_V17_SCALE_CAUSAL_OPS_PYTHIA69B_20260821.md
    RESULT_DETECTOR_VALIDATION_V18_STRUCTURED_NULL_20260821.md
    RESULT_DETECTOR_VALIDATION_V19_DECISIVE_NULL_AND_V11_V15_CORRECTION_20260821.md
    RESULT_V20_SHORTEST_RULE_AUDIT_OF_ALL_STANDING_RESULTS_20260821.md
    RESULT_V21_HAND_ADVERSARIAL_NOTHING_SURVIVES_20260821.md
    RESULT_V22_MATCHED_MINIMAL_PAIRS_20260821.md
    RESULT_V23_ORDER_MATCHED_PAIRS_20260821.md
    RESULT_V24_COUNTERBALANCED_FAILED_DESIGN_20260821.md
    RESULT_V25_ROLE_BINDING_20260821.md
    RESULT_V26_CAS_PINNED_ROLE_20260821.md
    RESULT_V27_SPEAKER_BINDING_NULL_20260821.md
    RESULT_V28_LAYER_INDEXING_RESOLVED_20260821.md
    RESULT_V29_SCALE_INJECTION_DISSOCIATION_20260821.md
    RESULT_V30_INSTRUCT_WITHIN_MODEL_DISSOCIATION_20260821.md
    RESULT_V31_INSTRUCTION_TUNING_DOES_NOT_INSTALL_SPEAKER_BINDING_20260821.md
    RESULT_V32_SCALEUP_N100_CONFIRMS_AND_CORRECTS_20260822.md
    RESULT_V33_RELATION_PROFILE_CAS_IS_MID_PACK_20260822.md
    SYNTHESIS_CAS_READING_AND_CORRECTION_CAPABILITY_20260821.md
    SYNTHESIS_V2_FINAL_STATE_20260821.md
    PAPER_DRAFT_SPEAKER_BINDING_GAP_20260821.md
Scripts + result JSON (each .py paired with _results.json):
    detector_validation.py / detector_validation_results.json                    (v1)
    detector_validation_v2.py / detector_validation_v2_results.json
    detector_validation_v3_multiaxis.py / detector_validation_v3_results.json
    detector_validation_v4_domain.py / detector_validation_v4_domain_results.json
    detector_validation_v5_operator10.py / detector_validation_v5_operator10_results.json
    detector_validation_v6_hardening.py / detector_validation_v6_hardening_results.json
    detector_validation_v7_registerdiverse.py / detector_validation_v7_registerdiverse_results.json
    detector_validation_v8_causal.py / detector_validation_v8_causal_results.json
    detector_validation_v9_surface_domain_operator.py / detector_validation_v9_surface_results.json
    detector_validation_v10_scale_pythia69b.py / detector_validation_v10_scale_pythia69b_results.json
    detector_validation_v11_domain_framingmatched.py / ..._results.json
    detector_validation_v12_operator10_framingmatched.py / ..._results.json
    detector_validation_v13_cause_effect_constructcorrect.py / ..._results.json
    detector_validation_v14_scale_controls_pythia69b.py / ..._results.json
    detector_validation_v15_scale_domain_pythia69b.py / ..._results.json
    detector_validation_v16_scale_causal_pythia69b.py / ..._results.json
    detector_validation_v17_scale_causal_ops_pythia69b.py / ..._results.json
    detector_validation_v18_structured_null.py / ..._results.json
    detector_validation_v19_decisive_null_pythia69b.py / ..._results.json
    detector_v22_minimal_pairs.py / ..._results.json
    detector_v23_order_matched.py / ..._results.json
    detector_v24_counterbalanced.py / ..._results.json
    detector_v25_counterbalanced_v2.py / ..._results.json
    detector_v26_cas_pinned.py / ..._results.json
    detector_v27_speaker_binding.py / ..._results.json
    detector_v29_scale_injection_pythia69b.py / ..._results.json
    detector_v30_instruct_qwen.py / ..._results.json
    detector_v31_clean_attribution.py / ..._results.json
    detector_v32_scaleup.py / ..._results.json
    detector_v33_relation_profile.py / ..._results.json
    audit_all_stimuli.py / audit_all_stimuli_results.json
    hand_adversarial_audit.py / hand_adversarial_results.json
    template_audit.py
    layer_indexing_probe.py                       (v28)

### 2.6 docs\working\aws_gate1_evidence_20260821\ — AWS gate evidence (Repo 2 only)
MANIFEST.json
GATE1_STATUS.md
GATE_STATUS_2026_08_21.md
GATE2_EXECUTED_20260821.md
GATE2_REBUILD_RECORD_20260821.md
GATE3_FREEZE_AUDIT.md
GATE3_FREEZE_RECORD.md
GATE4_LAUNCH_PLAN.md
GATE4_LAUNCH_PATH_ABSENT_20260821.md
GATE4_CORRECTION_REAL_BLOCKER_20260821.md
GATE4_PROTECTED_POD_DRIFT_20260821.md
GATE4_STOCK_AND_PRICE_20260821.md
GATE4_STRUCTURAL_BLOCKER_20260821.md
GUARDIAN_REDEPLOYED_20260821.md
EXECUTION_AUTHORIZATION_20260821.md
CONSOLIDATED_SEVEN_STEP_VERIFICATION_20260821.md
BOOTSTRAP_CIRCULARITY.md
HOW_TO_REVIEW_THE_CHANGE_SET.md
MODEL_REPIN_RECORD_20260821.md
PREFLIGHT_AUDIT_RAW_20260821.txt
PREFLIGHT_AUDIT_VERIFIED_20260821.md
REVIEW_THIS_CHANGE_SET_v3.md
RUNBOOK_STEP2_REDERIVE_LIVE_GUARDIAN_BINDING_20260821.md
SECOND_ACCOUNT_RUNBOOK.md
STOP_MEASUREMENT_OPTIONS_v2.md
TIMING_EVIDENCE_PREREGISTRATION.md
TRANSPORT_PROBE_RESULT.md
mfa_device_state.json
cloudtrail_trail_inventory.json
console_login_events_us_east_1.json
console_login_events_us_west_2.json
containment_snapshot.json
s3_worm_capability.json
cloudtrail_seal\
    SEAL_MANIFEST.json
    us_east_1_console_login.json.gz
    us_west_2_all_management_events.json.gz
mfa_session_evidence\
    MANIFEST.json
    mfa_session_evidence.json
timing_evidence\
    deployment-binding.PREPROD.json
    live_changeset_parameters.PREPROD.json
    source-manifest.json
    timing-evidence.json

### 2.7 docs\working\can_cas_assessment_20260821\ — CAN assessment (Repo 2 only)
CAN_CAS_HARNESS_DEEPDIVE_MEMO.md
CAN_CAS_CAPABILITY_ROADMAP.md
VERIFIED_FINDINGS.md

### 2.8 docs\working\ — other successor-only docs
STEP2_LIVE_CHANGE_SET_REVIEW_20260822.md
RUNPOD_PRECREATE_GUARDIAN_DESIGN_20260820.md
OPEN_WEIGHT_TRAJECTORY_CANARY_V2_PREREG.json
CAS_HARNESS_CURRENT_STATE.json
CAS_HARNESS_SPEC_SHEET_SCOPE_20260818.md
CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md
CAS_HARNESS_COMBINED_LIVE_MODEL_CANARY_READINESS_20260722.md
CAS_HARNESS_CUSTOMER_PRODUCTION_SUCCESSOR_SPEC_20260716.md
CAS_HARNESS_JSPACE_OHM_300B_CAPABILITY_ANALYSIS_20260720.md
CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md
CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md
CAS_HARNESS_PROGRESS_REPORT_20260727.md
CAS_HARNESS_BRIDGE_SCRIPT_RECOVERY_20260818.md
CAS_HARNESS_AMAZON_REVIEW_BRIEF_20260615.pdf
AWS_GATE5_OPERATOR_RUNBOOK_20260818.md
AWS_GATE5_EVIDENCE_INSPECTION_CHECKLIST.md
AWS_GATE5_PACKAGE_CORRECTIONS_20260819.md
AWS_GATE5_STEP4_CAPSULE_UPLOAD_MAP.md
research_cav_steering_20260821\
    PREREG_RESEARCH_CAV_STEERING.md
    cav_experiment.py
    cav_results.json
    RESULT_RESEARCH_CAV_STEERING_20260821.md
agent_exchange\
can_cas_assessment_20260821\
detector_validation_20260821\
aws_gate1_evidence_20260821\
gate2_closure\  gate3_injection\  gate4_board_change_v2\  gate4_next_board\  gate5_weld\  gate5_weld_v3\
candidate_a..e dirs (candidate_b1, candidate_b2, candidate_b3, candidate_c, candidate_d1, candidate_e)
broader_b3_eval\  broader_b3_eval_at192\  mtc_matched_taxonomy_20260530\  cas_brain_map_2026_05_14\
compliance_drafts_20260604\  production_readiness\  research_2026_05_05\  track_a_phase_a\  track_b_tks_672\

### 2.9 Attested engine paths (all verified present on disk)
noetic-compass-scaffold\noetic-compass\live-trace-worker\app\runtime\open_weight\engine.py
noetic-compass-scaffold\noetic-compass\live-trace-worker\app\runtime\open_weight\identity.py
noetic-compass-scaffold\noetic-compass\live-trace-worker\app\runtime\event_stream.py
noetic-compass-scaffold\noetic-compass\api\services\cas_harness_interpretability_adapter.py

### 2.10 Other trees (mirror Repo 1)
book\  cas-forex\  cas-native-agent-swarm-scaffold\  cas-synthetic\  cascompass-landing\
offline-cas\  ip\  dist\  peer_review\  pdf_review\  project_handoffs\  docs\

---

## 3. Archive — D:\tksCAS-archive

ATTEMPT_06_GPU_EXECUTION_FAILED_CLOSED_PHASE_TWO\
ATTEMPT_06_IMPLEMENTATION_FREEZE_29551624_20260723\
ATTEMPT_06_PRE_ANCHOR_F3E3ADAD_20260723\
ATTEMPT_06_REMOTE_PRESTAGE_ZP2S9PSCGNCN0B_20260723\
ATTEMPT_07_GPU_EXECUTION_FAILED_CLOSED_MODEL_LOAD\
ATTEMPT_07_IMPLEMENTATION_FREEZE_88B59DE9\
ATTEMPT_08_GPU_EXECUTION_FAILED_CLOSED_CANARY_EXECUTION\
ATTEMPT_09_GPU_EXECUTION_FAILED_CLOSED_LOCAL_JVP_VJP\
ATTEMPT_09_IMPLEMENTATION_FREEZE_6D676840\
ATTEMPT_10_PRODUCER_PASS_CANDIDATE_RECEIVER_GPU_IDENTITY_BLOCK\
ATTEMPT_11_TECHNICAL_CANARY_PASS_GATE1\
ATTEMPT_11_TECHNICAL_CANARY_PASS_GATE1_final\
awscli_user_20260815\
cas_harness_prompt_injection_audit_packet_20260615\
cas_harness_spec_sheets_canonical_20260526\
cas_harness_tracker_aws_handoff_recovery_20260815\
cas_harness_tracker_sync_recovery_20260815\
cas_harness_tracker_upload_staging_20260815\
cas_harness_tracker_upload_staging_20260815T0928Z\
cas_injection_roundtable_20260610\
cas-forex-evidence_runs_20260628_101216\
cas68_recipe_audit_20260610\
checkpoints\
cjt_bias_vibration_causal_expanded_qwen_20260618\
cjt_bias_vibration_causal_qwen_20260618\
cjt_bias_vibration_w0_qwen_20260618\
cjt_bias_vibration_w0_qwen_v1_20260618\
condition3_mtc_capture_20260531\
condition3_mtc_capture_20260603\
condition3_mtc_comparator_20260603\
definition_locked_tks_mtc_20260603\
detection_probe_20260610\
detector_scale_pythia69b_20260821\
enabled_predicate_prespeech_qwen_phi_20260611\
enabled_predicate_qwen_chat_w0_20260611\
evidence_first_master_plan_docs_20260812T1640Z\
evidence_first_master_plan_reboot_bundle_20260812T1646Z\
evidence_first_master_plan_reboot_bundle_latest\
expl2_involution_gap_20260610\
gate2_w0_fair_comparison_attempt1_20260724\
gate4_board_change_pilot_20260819\
gpt_neox_20b_activation_cover_ablation_20260526\
gpt_neox_20b_balanced_logistic_closure_20260526\
gpt_neox_20b_first_real_activation_pass_20260526\
gpt_neox_20b_probe_dataset_eval_20260526\
gpt_neox_20b_stage7_eta_epsilon_bridge_20260526\
gpt_neox_20b_stage9_original_40e_bridge_proof_20260528\
gpt_neox_20b_stage9_original_40e_causal_proof_20260528\
gpt_neox_20b_stage9_original_40e_closure_20260527\
gpt_neox_20b_tks40_balanced_logistic_guarded_20260527\
grounded_factual_qa_hallucination_w0_qwen_20260618\
grounded_factual_qa_hallucination_w0_qwen_grouped_20260618\
grounded_factual_qa_hallucination_w1_w8_qwen_timing_20260618\
hidden_prompt_injection_w0_large_v1_qwen_20260617\
item4_scramble_null_licensed_20260725\
mtc_matched_taxonomy_20260530\
outcome_native_hallucination_preanswer_qwen05_hard_v2_20260618\
outcome_native_hallucination_qwen05_hard_v2_20260618\
outcome_native_hallucination_qwen05_large_v1_20260618\
outcome_native_hallucination_w0_prompt_risk_qwen05_hard_v2_20260618\
pathB_multilayer_20260610\
prespeech_causal_team_20260610\
project_coherence_ecd_consensus_replication_v1_20260813\
project_coherence_ecd_consensus_replication_v2_20260813\
project_coherence_ecd_consensus_replication_v2_packets_20260813\
project_coherence_ecd_exact_endpoint_v1_20260813\
project_coherence_ecd_exact_endpoint_v1_20260813_independent_packets\
project_coherence_ecd_runpod_20260813\
project_coherence_ecd_stage1_integrated_replays_20260812\
project_coherence_ecd_stage1_receipts_20260812\
project_coherence_ecd_stage2_pilot_20260813\
project_coherence_gate5_aws_full_verifier_20260815\
project_coherence_gate5_cloud_windows_source_capsule_20260815\
project_coherence_gate5_cloud_windows_source_capsule_20260815_failed_artifact_normalization_probe\
project_coherence_gate5_cloud_windows_source_capsule_20260815_failed_longpath_probe\
project_coherence_gate5_cloud_windows_source_capsule_20260815_failed_longpath_status_probe\
project_coherence_gate5_cloud_windows_source_capsule_20260815_failed_overlay_index_refresh\
project_coherence_gate5_cloud_windows_source_capsule_20260815_failed_overlay_stat_probe\
project_coherence_gate5_coldstart_unarmed_20260815\
project_coherence_gate5_corrected_package_20260819\
project_coherence_gate5_current_head_20260815\
project_coherence_gate5_one_hour_package_20260818\
project_coherence_gate5_reconciliation_bff8d682_20260807\
project_coherence_open_weight_canary_v2_20260820\
project_coherence_phase0_expanded_receipts_20260812\
project_coherence_phase0_freeze_2425698D_20260812T1635Z\
project_coherence_phase0_integrated_replays_20260812\
project_coherence_runpod_zero_model_smoke_20260813\
project_coherence_stageb_model_binding_ea1996a4_20260807\
project_coherence_stageb_retained_blobs\
project_coherence_stagec_activation_budget_postgres_live_20260813\
project_coherence_stagec_attempt_claim_postgres_live_20260814\
project_coherence_stagec_object_lock_365_probe_20260814\
project_coherence_stagec_object_lock_365_probe_v2_20260814\
project_coherence_stagec_object_lock_365_probe_v3_20260814\
project_coherence_stagec_rfc3161_digicert_compat_v1_20260814\
project_handoffs_oversize_20260816\
project_upload\
pythia160m_activation_cover_ablation_20260603\
pythia160m_gate1_reproduction_20260531\
pythia160m_object_lock_anchor_20260603\
qwen_confirmatory_20260610\
qwen_confirmatory_v3_20260610\
qwen_gate_a_20260610\
qwen_prespeech_behavior_probe_20260610\
qwen_v6_boundary_relabel_seed_bank_20260615\
qwen_v6_calibrated_continuation_20260612\
qwen_v6_expanded_bank_v2_s16_generation_only_20260615\
qwen_v6_expanded_bank_v2_s16_w0_all_layers_20260615\
qwen_v6_matched_chain_break_20260612\
qwen_v6_matched_chain_break_w0_all_layers_seed00_47_v2_20260615\
qwen_v6_seed16_s16_generation_only_20260615\
qwen_v6_seed32_s16_target2_generation_only_20260615\
runpod_runs\
session_scratch\
stage_e2c_cont_20260513T002539Z\
stage_e3_20260513T043823Z\
stage27_smoke_files_ai2_pitch_20260526\
stage6_v6_artifacts\
steering_causal_20260611\
structural_break_20260611\
topos_bridge_verification_20260610\
typed_probe_v4_tooling_20260610\
v0_rc1\
v1e_phase_c\
w0_rpm_lacunarity_all_layers_qwen_20260611\
cas_harness_prompt_injection_audit_packet_20260615.tgz
cas_harness_prompt_injection_combined_gate_20260615.tgz
ECD_STAGE1_PR_BODY.md
evidence_first_master_plan_docs_20260812T1640Z.zip
evidence_first_master_plan_reboot_bundle_20260812T1646Z.zip
project_coherence_phase0_freeze_2425698D_20260812T1635Z.zip
PROJECT_COHERENCE_PHASE0_POST_REBOOT_RUNBOOK_20260812.md
qwen_v6_boundary_relabel_seed_bank_20260615.tgz
qwen_v6_expanded_w0_matched_prespeech_result_20260615.tgz
qwen_v6_w0_matched_prespeech_result_20260615.tgz

---

## 4. Memory directory (135 files) — C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\memory
Outside both git repos. Index: MEMORY.md + 134 memory files (1 fact each, YAML frontmatter).

MEMORY.md
cas_diagram_and_clusters.md
cas_grammar_subtleties.md
cas_ohm_diagnostic_architecture.md
feedback_agent_exchange_file_protocol.md
feedback_aggregate_metrics_never_get_to_be_the_audit.md
feedback_always_restore_baseline_hparams_for_full_retrains.md
feedback_anti_drift_gates_not_content_preservation.md
feedback_audit_corpus_before_proposing_reuse.md
feedback_audit_only_after_automated_checks.md
feedback_back_up_successful_runs_imperative.md
feedback_canary_cost_dominates_short_runs.md
feedback_cas_best_lm_six_properties.md
feedback_cas_forex_bot_understanding_not_advisor.md
feedback_cas_forex_epistemics_and_risk_cap_handoff.md
feedback_cas_harness_localization_claim_language.md
feedback_cas_harness_standing_owner_authorization.md
feedback_cas_native_5_layer_eval.md
feedback_cas_native_data_strategy_2026_05_13.md
feedback_cas_native_metrics_priority.md
feedback_cas_native_underfit_over_overfit_short_epochs.md
feedback_cas_token_enum_must_include_metalogic_and_fractals.md
feedback_char_level_surface_control_required.md
feedback_eval_file_slip_recurrent.md
feedback_external_data_for_conversational_discipline.md
feedback_fetch_master_before_launch.md
feedback_gemini_citations_need_verification.md
feedback_gemini_default_model.md
feedback_gpu_vs_cpu_for_real_training_runs.md
feedback_gpu_work_goes_to_runpod_not_local_install.md
feedback_grade_samples_dont_hand_procedure.md
feedback_limit_default_128_trap.md
feedback_no_defeatist_framing_in_cas_forex.md
feedback_no_foreign_architecture_cas_only.md
feedback_object_traceability_required.md
feedback_owner_action_items_at_end.md
feedback_parallelize_sdg_with_training.md
feedback_plain_language_no_jargon.md
feedback_postprocessor_policy_line.md
feedback_push_immediately_after_commit.md
feedback_pythonfaulthandler_does_not_make_sigquit_safe.md
feedback_real_metric_is_samples.md
feedback_result_status_color_scale.md
feedback_rotating_sample_prompts_required.md
feedback_rpm_content_fidelity_next_not_retraining.md
feedback_samples_are_the_only_true_eval_for_cas_native.md
feedback_schedule_followup_agents_pattern.md
feedback_seed_rpm_silhouette_production_path.md
feedback_separate_evidence_levels_in_status.md
feedback_set_wakeup_for_background_work.md
feedback_simplex_mvp_user_review_guardrails_2026_05_11.md
feedback_spec_sheet_is_living_master_record.md
feedback_tks_definitions_are_derived_never_paraphrase.md
feedback_traceability_is_the_whole_purpose.md
feedback_train_progress_logging_required.md
feedback_use_canonical_colloquialisms_as_operator_aliases.md
feedback_use_real_tks_definitions_for_recoverability.md
feedback_user_drives_full_control_no_babying.md
feedback_user_ratifications_2026_05_04.md
feedback_v1d_decision_rule_pointer_copy.md
feedback_validator_stack_layered_hierarchy.md
offline_cas_banner_preferences.md
project_20b_run_results_scoped_vs_production_accept.md
project_28_foundations_canon_authority.md
project_atlas_live_auth_posture_2026_05_23.md
project_atlas_live_wire_runpod_behind_api_2026_05_23.md
project_atlas_live_worker_scope_2026_05_23.md
project_b_pipeline_validated_2026_05_12.md
project_b3_broader_eval_falsified_2026_05_12.md
project_books_ip_decision_publish_us_only_2026_07_25.md
project_cabs_gravity_v2_thesis_2026_05_09.md
project_candidate_b_bounded_transformer_test_2026_05_11.md
project_cas_forex_2026_07_01_landed_state.md
project_cas_forex_dispatch_money_broker_control.md
project_cas_forex_first_real_backtest_no_edge_2026_06_21.md
project_cas_forex_intelligent_execution_loop.md
project_cas_forex_live_profitable_finish_2026_06_28.md
project_cas_forex_llm_bot_runtime_2026_06_24.md
project_cas_forex_money_movement_requirement.md
project_cas_forex_regime_switching_simulator.md
project_cas_forex_session_handoff_2026_06_27.md
project_cas_forex_user_selectable_multi_timeframe.md
project_cas_harness_attempt6_crlf_freeze_2026_07_23.md
project_cas_harness_attempt9_local_vjp_wall_2026_07_24.md
project_cas_harness_aws_gate5_p1_bridge_fix_2026_08_16.md
project_cas_harness_aws_runpod_lane_two_repos.md
project_cas_harness_gate1_earned_2026_07_24.md
project_cas_harness_gate2_attempt1_honest_fail_2026_07_24.md
project_cas_harness_gate2_scope_error_2026_07_24.md
project_cas_harness_is_data_harvest_for_cas_native.md
project_cas_harness_item4_first_licensed_result_2026_07_25.md
project_cas_harness_specsheet_capabilities.md
project_cas_native_codex_to_compiler_north_star.md
project_cas_native_demo_v0_amazon_pitch_target_2026_05_13.md
project_cas_native_v2_first_structured_emergence.md
project_cas_output_lens_reframe.md
project_cas_transformer_modality_mismatch_pivot.md
project_cas_transformer_nl_front_door_architecture.md
project_coherence_stage_a_complete_2026_08_07.md
project_coherence_stage_b_constraints.md
project_deepseek_revised_diagnosis_2026_05_03.md
project_drive_local_eraser_steering_cross_scale_2026_05_21.md
project_exposure_button_traceability.md
project_gate2_independent_bank_blind_authors.md
project_k9_baretemplate_partial_success_2026_05_02.md
project_living_thought_atlas_flagship_2026_05_13.md
project_mtc_path2_condition3_decision_2026_05_31.md
project_native_gen_open_questions_already_answered.md
project_option_c_task_tokens_2026_05_09.md
project_paraphrase_failure_modes_diagnoses.md
project_path_c_base_manifold_typed_fibers_correction_2026_05_07.md
project_path_d_wave_2_5_promoted_2026_05_08.md
project_path_d_wave_4_v1_mix_2026_05_08.md
project_path_d_wave3_full_run_gate_criteria_2026_05_07.md
project_pr6_diagloop_eval_mode_bug_2026_05_03.md
project_pr6_diagloop_full_shortcut_2026_05_03.md
project_pr6_diagloop_smoke_2026_05_03.md
project_sae_research_track_deferred_post_product.md
project_sggs_implementation_started_2026_05_13.md
project_simplex_architecture_review_framing_2026_05_11.md
project_simplex_diagnostic_decision_standard_2026_05_11.md
project_simplex_mvp_signoff_with_modifications_2026_05_11.md
project_simplex_redesign_revisit_after_v0.md
project_sparse_neuron_cover_causal_localization_2026_05_21.md
project_three_instance_dialectic_proposal_2026_05_04.md
project_v1_architectural_milestone_2026_05_09.md
project_v1_locked_plan_path_c_d_2026_05_07.md
project_v1e_architecture_pivot_design_2026_05_10.md
project_v1e_killswitch_tripped_simplex_pivot_2026_05_11.md
project_v1e_phase2_decision_2026_05_11.md
project_v76_metalogic_two_failure_modes_2026_05_04.md
project_version_b_conversational_plan.md
reference_cas_forex_ui_ux_plan.md
reference_tkscas_monorepo_gitignore_data_policy.md
sggs_v2_v3_backlog_pointer.md

---

## 5. Session scratchpads (outside git — intermediate artifacts, failed attempts, raw pod scripts)

Scratchpad A (primary; the originals that were later copied into Repo 2 detector series / guardian / canary artifacts):
C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS\48bed170-da71-4777-8d00-6c209e1475ff\scratchpad\

    __pycache__\   awsenv\   fdgen\   gz\   mlenv\   models\   wt-master\   wt-master2\
    _36ideas_prev.txt
    _layer_probe.py
    _section39.md
    armed_execute.py
    audit_all_stimuli.py / audit_all_stimuli_results.json
    audit_tail.txt
    aws_status_check.py
    bd_old.json
    binding_hashes.txt
    binding_input.json
    binding_inputs_partial.json
    binding_new.json
    binding_version.txt
    capability_roadmap.md
    cav_experiment.py / cav_results.json
    cfn_to_json.py
    changeset_inputs.json
    collect2.py
    collect3.py
    ct_export.py
    decisive.py
    deepdive_report.md
    detector_v22..v27, v32, v33  (*.py + *_results.json)
    detector_validation.py and v2..v9, v11..v13, v18  (*.py + *_results.json)
    gate1_bundle.py
    goal_check.py
    guardian-runtime.zip                (local-only copy; the canonical one is infra\runpod_guardian_live_candidate\dist\)
    hand_adversarial_audit.py / hand_adversarial_results.json
    ideas36.txt
    induction_result.json
    key_check.py
    make_trail.py
    new_artifact.txt
    old_binding.json
    pod_experiment_clean_attribution.py
    pod_experiment_decisive_null.py
    pod_experiment_instruct.py
    pod_experiment_pythia69b.py
    pod_experiment_scale_causal.py
    pod_experiment_scale_causal_ops.py
    pod_experiment_scale_controls.py
    pod_experiment_scale_domain.py
    pod_experiment_scale_injection.py
    pod_orchestrate.py
    pod_results_*.json        (clean_attribution, decisive_null, instruct, pythia69b, scale_causal, scale_causal_ops, scale_controls, scale_domain, scale_injection)
    pod_watchdog.py
    preflight_exec.py
    PREREG_BACKUP.json
    probe_plugin.py
    quota_watch.py
    real_trace_smoke.py
    realpath.py
    rehearsal.json / rehearsal.txt / rehearsal_run_id.txt
    repin_attestation.json
    repin_smoke.py
    scaleup_run.log
    scaleup_run2.log
    scen.py
    sec47.md
    secret_arn.json
    secret_watch.sh
    set_runpod_secret.sh
    template_compact.json
    template_fixed.json
    template_fixed_packaged.json
    template_packaged.json
    template_resolved.json
    template_v3.json
    trace_gate.py
    v33_run.log
    verify.py / verify2.py / verify3.py / verify_real.py
    wait_restore.py
    wait_tick.py
    watch4.py
    watchdog.log

Scratchpad B (sibling session scratchpad — currently EMPTY, 0 files):
C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS\47e27b5f-962d-463f-9794-2d8199af66e9\scratchpad\

---

## 6. Session transcripts and workflow journals (outside git)

### Claude Code session transcripts (this project)
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\05cb92a5-93c8-4a2c-960a-73b631677a7c.jsonl
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\13b1f454-a6e7-4953-850c-5f02abfff57e.jsonl
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\200b38e3-6d5c-4b7e-8c2e-0390118f981e.jsonl
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\3331c3bc-bbeb-4e4e-a50c-b9138ed35ce1.jsonl
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\3606ca7b-1fa2-4689-9f06-5f6d98e974ba.jsonl
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\3a9106b6-9105-4c4d-a9cf-f3eaaca6acbc.jsonl
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\47e27b5f-962d-463f-9794-2d8199af66e9.jsonl
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\48bed170-da71-4777-8d00-6c209e1475ff.jsonl
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\4fae7019-54d6-4485-b761-802e29b99732.jsonl
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\8a50c2ca-34b6-43c1-b27e-59828c6ab21c.jsonl
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\8bbfd72e-a382-4927-b975-6ac16fa7f140.jsonl
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\9bea0aa3-1a28-4143-ba94-63aa65a260f4.jsonl
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\b93dbc7e-7198-4706-9190-582845355dfa.jsonl

### Claude Code per-session workflow dirs
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\<session-uuid>\subagents\workflows\   (e.g. 8a50c2ca\subagents\workflows\wf_0205a87b-3ce ... wf_fe86604b-479)
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\<session-uuid>\subagents\agent-*.jsonl / agent-*.meta.json
C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\<session-uuid>\tool-results\

### Claude Code global sessions
C:\Users\wakil\.claude\sessions\34408.*.key
C:\Users\wakil\.claude\sessions\9232.c21c021f59a45dc35f8048e25f95d801731787bbb43467bbcd53806936a1a8d0.key
C:\Users\wakil\.claude\sessions\9232.json

### DeepSeek Harness session (current harness, tksCAS workspace)
C:\Users\wakil\.dsh\sessions\--C-Users-wakil-OneDrive-Desktop-tksCAS--\session-bd62d315-acba-425f-b8f1-c626887b6657\session.jsonl.zstd
C:\Users\wakil\.dsh\storages\session_projcache.json
C:\Users\wakil\.dsh\storages\workspace.json

### DeepSeek CLI sessions
C:\Users\wakil\.deepseek\sessions\   (14 items: 8 session dirs + 10 session .json files + checkpoints\)
C:\Users\wakil\.deepseek\audit.log

### Codex session transcripts (rollouts)
C:\Users\wakil\.codex\sessions\2026\04\{22,24,25,26,27,28,29,30}\rollout-*.jsonl
C:\Users\wakil\.codex\sessions\2026\05\rollout-*.jsonl
C:\Users\wakil\.codex\sessions\2026\06\rollout-*.jsonl
C:\Users\wakil\.codex\sessions\2026\07\rollout-*.jsonl
C:\Users\wakil\.codex\sessions\2026\08\rollout-*.jsonl

### Codex session work areas
C:\Users\wakil\Documents\Codex\2026-04-30\in-the-following-folder-c-users\
C:\Users\wakil\Documents\Codex\2026-07-28\realtime-voice-chat\
C:\Users\wakil\Documents\Codex\2026-08-04\a\
C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\   (aws_cloudshell_unarmed_20260815..18, cas_interpretability_successor_20260820, gate5-*, project_coherence_*, runpod_*, scout-cache-*, tools)
C:\Users\wakil\Documents\Codex\2026-08-13\the\

### Handoff transcripts (raw pod sessions)
C:\Users\wakil\OneDrive\Desktop\tksCAS\project_handoffs\CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21\02_RESEARCH_EVIDENCE\full_recovery\logs\run_verified_canary_transcript.log
C:\Users\wakil\OneDrive\Desktop\tksCAS\project_handoffs\CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21\11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22\04_PROTOCOL_AND_ANCHOR\ATTEMPT_04_REMOTE_PREPARATION_BE97BC7F\REMOTE_COMMAND_TRANSCRIPT.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\project_handoffs\CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21\11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22\04_PROTOCOL_AND_ANCHOR\ATTEMPT_06_REMOTE_PRESTAGE_ZP2S9PSCGNCN0B_20260723\PRESTAGE_TRANSCRIPT.txt
C:\Users\wakil\OneDrive\Desktop\tksCAS\project_handoffs\CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21\11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22\04_PROTOCOL_AND_ANCHOR\ATTEMPT_06_REMOTE_PRESTAGE_ZP2S9PSCGNCN0B_20260723\PRESTAGE_TRANSCRIPT.stderr.txt
D:\tksCAS-archive\ATTEMPT_06_GPU_EXECUTION_FAILED_CLOSED_PHASE_TWO\diagnostic\phase_two_diagnostic_transcript.txt
D:\tksCAS-archive\ATTEMPT_06_REMOTE_PRESTAGE_ZP2S9PSCGNCN0B_20260723\PRESTAGE_TRANSCRIPT.txt
D:\tksCAS-archive\ATTEMPT_06_REMOTE_PRESTAGE_ZP2S9PSCGNCN0B_20260723\PRESTAGE_TRANSCRIPT.stderr.txt

### Workflow journals (ndjson)
D:\tksCAS-archive\project_coherence_ecd_consensus_replication_v1_20260813\runs\20260813T225241Z-6e9fb3bab8f5\journal.ndjson
D:\tksCAS-archive\project_coherence_ecd_consensus_replication_v2_20260813\runs\20260813T232228Z-3b5789c43170\journal.ndjson
D:\tksCAS-archive\project_coherence_ecd_stage2_pilot_20260813\prospective_holdout_runner_v1\runs\20260813T215326Z-da71732fb128\journal.ndjson
D:\tksCAS-archive\project_coherence_ecd_stage2_pilot_20260813\prospective_holdout_runner_v2\runs\20260813T220626Z-3c59754767f3\journal.ndjson

---

## 7. External source PDFs — C:\Users\wakil\Downloads

1095C (HENDERSON LITTLE).pdf
191484143 Notice Of Appeal.pdf
2.3_AS_IndustryJobsTEM3v6.pdf
2.3_AS_IndustryJobsTEMv6.pdf
2022_W-2.pdf
2023-08-06 17_55_55.pdf
20230707Littl_Henderson_2023_resume_73dd196d-8c40-4b86-a6cc-97a692b75e0a.pdf
20230909Littl_Henderson_2023_resume_0cebe058-4a9a-4a48-809d-4fbc5dcfb1cd.pdf
2026-07-06 Statement - USB Checking 5033.pdf
2506.21734v3.pdf
2509.25236v3.pdf
2605.22166v1.pdf
28 fOUNDATIONS 1.0.pdf
3.0_DB_NetworkingPlanTEMv6.pdf
3.1_AS_MissionStatement_V6.pdf
30_Day_Tootra_Calendar_Custom_Generated (1).pdf
30_Day_Tootra_Calendar_Custom_Generated.pdf
30_Day_Tootra_Calendar_Custom.pdf
30_Day_Tootra_Calendar.pdf
30_day_tootra_element_calendar_corrected.pdf
30_day_tootra_element_interpretation_calendar.pdf
30_Day_Tootra_Element_Interpretations.pdf
30_days_tootra_element_calendar.pdf
30_Days_Tootra_Elemental_Interpretations (1).pdf
30_Days_Tootra_Elemental_Interpretations.pdf
4-Conflict_Resolution_Activity.pdf
4.0 Reflection  Video.pdf
4.1 Portfolio Competency 2.pdf
4.1 Portfolio Competency.pdf
4.1 Portfolio Competency3.pdf
4.1 Portfolio Competency4.pdf
4.1 Portfolio Competency6.pdf
40 Element Equations 4522.pdf
40 Element Equations 4562.pdf
40 Element Equations3060.pdf
40 Element Formulas YAISA EDITED.pdf
40 Element Formulas.pdf
40 Elements for GPT 0.2v (1).pdf
40 Elements for GPT 0.2v.pdf
40 Elements for GPT.pdf
4c1384ec-cccb-44f5-9774-5408701c6fdd__7f6d2e1f-c4a1-43ae-889b-1720273dc979.pdf
75539240-The-Problem-Book.pdf
A Summary of Your Rights Under the Fair Credit Reporting Act.pdf
AFBSummary_824605184.pdf
Alien Ice cream.pdf
AMAZT Corp Vendor Additional Acknowledgments and Authorizations For Background Check.pdf
application_credit_report_344072.pdf
application_document_21289550_20241029070855.pdf
Atticus LLC_ Invoice 000073224.pdf
Automated_Marketing_Conversation_Notes.pdf
Book of Formulas and Interpretations 222.pdf
Book of Formulas and Interpretations.pdf
Book of Formulas and Interpretations333.pdf
BOOK OF KABBALISTIC CALCULUS W 40 E DEFS.pdf
BOOK OF KABBALISTIC CALCULUS.pdf
C++_Symbols_Guide.pdf
CA_EA_STRF (2).docx.pdf
campus-3220.pdf
CAN_to_TKS_CAS_Mapping.pdf
CARD FORMULA.pdf
CAS_14-Capability_Integrated-Path_Status_2026-08-20.pdf
CAS_Forex_Web_Phone_AI_Trading_Spec_2026-07-06.pdf
cas_harness_forex_trading_execution_plan.pdf
CAS_HARNESS_SPEC_SHEET_20260517.PDF
CAS_HARNESS_SPEC_SHEET_current.pdf
CAS_HARNESS_SPEC_SHEET_v1_6_RECONCILED.pdf
CAS_NATIVE_ARCHITECTURE_PROVISIONAL_DISCLOSURE.pdf
CAS_Ohm_Quantification_Guide-1.pdf
CAS_Ohm_Quantification_Guide-2.pdf
CAS_PCBA_Engineer (1).pdf
CAS_PCBA_Engineer (3).pdf
CAS_PCBA_Engineer_interior_KDP.pdf
cas_pcba_engineer_wrap_print.pdf
cas_pcba_engineer_wrap_v2.pdf
cas_pcba_engineer_wrap.pdf
CAS_PCBA_Schematic_Component_Field_Manual.pdf
CAS_PCBA_Symbol_Atlas_and_Drafting_Manual.pdf
CAS_provenance_preprint_updated.pdf
CAS_Provenance_Preprint.pdf
CAS_Provisional_Drafts_All_Mechanisms.pdf
CAS_provisional_filing_guide_updated.pdf
CAS_provisional_flowcharts_described.pdf
CAS_Provisional_Flowcharts.pdf
CAS_provisional_patent_updated.pdf
CAS_Self_Filing_Provisional_Guide.pdf
Catalog_Elevate_2023_January (3).docx.pdf
CC-G20000088342.pdf
CCDL_EXT_R1_v0.2_Changelog.pdf
certificate (1).pdf
certificate.pdf
CHAMP_Plan.pdf
chatgpt overton convo - Copy.pdf
chatgpt overton convo.pdf
ConfigurationOperation.pdf
ConfigurationOperation33.pdf
Confirmation - EAPP - Washington Connection (Your Link to Services).pdf
Consent for Electronic Signature and Delivery.pdf
Consumer Conditioning school.pdf
COP2334.pdf
COS-G20000088342.pdf
Coursera JCBBHEGMV72C.pdf
Coursera NYKT6M8HTNTJ.pdf
Coursera PTYUZFTMBKY8.pdf
Cover_Letter_Little_Henderson.pdf
coverletter HEADSTR.pdf
coverletter.pdf
Dave Banking Direct Deposit Enrollment Form.pdf
DeepSeek Harness Vocabulary Cheat Sheet.pdf
Defendant_Motion_for_Hardship_Declaration.pdf
DEP1013_CourseSyllabus(1).pdf
Disclosure Regarding Background Check.pdf
document (1).pdf
document (2).pdf
document_15-Jul-2026_10_54_23.pdf
document.pdf
Document1.pdf
Document2 (1).pdf
Document2.pdf
DOCUSIGN WELCOME.docx.pdf
DON'T DIE_by Zero.pdf
ENC1101Syllabus.pdf
Enhanced_Saint_John_Formula_Table.pdf
Enhanced_Saint_John_Formula_Table2.pdf
Enhanced_Saint_John_Formula_Table3.pdf
enrollment-checklist-FullSail.pdf
Every Psychological Trap.pdf
fictitous_name.pdf
FOR SCHOOL.pdf
Full Sail Student Portal (1).pdf
Full Sail Student Portal.pdf
Fullsail loan.pdf
Gmail - Safeguard- Step 1- reply to start process and become a vendor.pdf
Goals ^0 Schedule.pdf
grok_report.pdf
HeroApp.pdf
HeroApp333.pdf
heroes.pdf
House.pdf
Inmate Release Information Detail.pdf
InstaScreen QuickApp™.pdf
Kaizen Presentation Implementing VoiceActivated AI for Motherboard Assembly and Rework.pdf
knowing your program.pdf
Learning_Python_Mind_Map.pdf
Likeness_Addendum_(1) (1).pdf
Littl Henderson 2023 resume.pdf
Little Henderson_Amazon PeopleSoft Onboarding Questionnaire for Vendors_Project Kuiper (1).pdf
Little Henderson_Amazon PeopleSoft Onboarding Questionnaire for Vendors_Project Kuiper (2).pdf
Little Henderson_Amazon PeopleSoft Onboarding Questionnaire for Vendors_Project Kuiper.pdf
Little Henderson.pdf
Little_Henderson_Letter_1 (1) (1) (1).pdf
Little_Henderson_Letter_1 (1) (1).pdf
Little_Henderson_Letter_1 (1).pdf
Little_Henderson_Letter_1 (2).pdf
Little_Henderson_Letter_1.0.pdf
Little_Henderson_Letter_1.1.pdf
Little_Henderson_Letter_1.pdf
Little_Henderson_Resume.pdf
Little_Henderson.pdf
LittleHenderson_ShippingLabel.pdf
Lost and Found in the Maze of Mathematics.pdf
lunar-mansion-tootra.pdf
Madeleynis_Oliva_Cruz_-_Babysitter.pdf
main.pdf
MAJIK AND THE TRUE KABBALAH.pdf
mini-resume update (1) (1)-2.0_compressed.pdf
mini-resume update (1) (1)-2.0.pdf
mini-resume update (1) (1)-2.pdf
mission statement 3.1.pdf
MONOGRAPH_CAS_CORE_8_v0.3.pdf
MONOGRAPH_CAS_OHM_1_0_v0.3.pdf
MONOGRAPH_CAS_PCBA_8_v0.3.pdf
MONOGRAPH_NOETIC_TOPOS_2_0_v0.3.pdf
MONOGRAPH_TKS_V8_0_v0.3.pdf
My_Networking_Plan.pdf
my-document.pdf
NDA_alpha_partner.pdf
NDA_alpha_partner1.pdf
NewPRdesignFIXEDLINKS.pdf
Noetic Mapping.pdf
NOETIC_COMPASS_PROVISIONAL_DISCLOSURE.pdf
noetic_fractals_complete - Copy.pdf
noetic_fractals_complete.pdf
Noetic_Topos_Revision_Plan.pdf
noetic-assessment-4-13-2026--1-54-15-PM.pdf
noetic-assessment-4-7-2026--3-32-22-AM.pdf
noetic-assessment-4-7-2026--6-47-52-AM.pdf
noetic-compass-book.pdf
noetic-compass-bookv2.pdf
noetic-topos (1).pdf
noetic-topos.pdf
Noetics^0DiscreteMathematics.pdf
non_attorney_representative_practice_exam_final 1.pdf
non_attorney_representative_practice_exam_sanitized 2.pdf
Notes_240215_161354.pdf
operation configuration.pdf
Other State Law Notices.pdf
Payslip_to_Print_-_Report_Design_08_02_2023 (1) (1).pdf
Payslip_to_Print_-_Report_Design_08_02_2023 (1) (1).pdf (1).pdf
Payslip_to_Print_-_Report_Design_08_02_2023 (1) (1).pdf (2).pdf
Payslip_to_Print_-_Report_Design_08_02_2023 (1) (1).pdf (3).pdf
Payslip_to_Print_-_Report_Design_08_02_2023 (1) (1).pdf (4).pdf
Payslip_to_Print_-_Report_Design_08_02_2023 (1) (1).pdf.pdf
Payslip_to_Print_-_Report_Design_08_02_2023 (1) (2).pdf
Payslip_to_Print_-_Report_Design_08_02_2023 (1) (3).pdf
Payslip_to_Print_-_Report_Design_08_02_2023 (1) (4).pdf
PDF.pdf
pdfView.go.pdf
placeit_invoice_4725002.pdf
Please_DocuSign___Little_Henderson_FULL_TIME.pdf
Please_DocuSign___URGENT_TRIGO_ONBOARDING_I.pdf
PracticeMathTest.pdf
Privacy policy (1).pdf
Privacy policy.pdf
Program code files.pdf
Programming_in_CAS_Complete_Expanded_Designed.pdf
Programming_in_CAS_Complete.md (1).pdf
Programming_in_CAS_Complete.md.pdf
Quest 5.pdf
Reality_Engineering_interior_KDP.pdf
reality_engineering_wrap_print.pdf
reality_engineering_wrap_v2.pdf
reality_engineering_wrap.pdf
Receipt-2870-6778-0046.pdf
Reflecting_on_Public_Speaking_Essay.pdf
Rescued document.pdf
RESEARCH_PAPER_CAS_CORE_8_v0.2.pdf
RESEARCH_PAPER_CAS_OHM_1_0_v0.2.pdf
RESEARCH_PAPER_CAS_PCBA_8_v0.2.pdf
RESEARCH_PAPER_NOETIC_TOPOS_2_0_v0.2.pdf
RESEARCH_PAPER_TKS_V8_0_v0.2.pdf
resume update.pdf
Resume_2 (1) (1).pdf
Resume_2 (1).pdf
Resume_2.pdf
resume_converted_to_pdf.pdf
resume+update+(1).pdf
RISEModelforSelf-Evaluation-PDF.pdf
Saint John Formula Table.pdf
Saint John.pdf
Saint_John_Formula_Table.pdf
schools_elevate_programs_sdr-bootcamp_pricing_8784944501_templates_8784944501-asd.pdf
Script for Introducing Brandon Blackwell at Full Sail University Hall of Fame Ceremony.pdf
SDV3111CourseAt-A-Glance.pdf
self-improving-harness.pdf
single-label.pdf
spacex coverletter.pdf
Spell Writing.pdf
Strategy test (1).pdf
Strategy test.pdf
Structure of Tootra n Practice.pdf
SUPERIORITY_OF_TKS_COMPLETE_MANUSCRIPT.pdf
superiority_of_tks_final_manuscript_v3.0.pdf
superiority_of_tks_final_manuscript_v3.000.pdf
superiority_of_tks_final_manuscript_v3.2.pdf
superstrength8weekstrengthbuildingworkout.pdf
SUPRERIORITY OF TKS for ai editing.pdf
SUPRERIORITY OF TKS version 2.pdf
SUPRERIORITY OF TKS version 3.pdf
SUPRERIORITY OF TKS.pdf
TEM1000-O_CourseSyllabus.pdf
ten-proofs-oai.pdf
testCertified2.pdf
testCertifiedmail.pdf
tex.pdf
TEXT - Think Python 2e.pdf
The 28 Foundations.pdf
The 40 Elements for Ai.pdf
the 40 Elements Training Data.pdf
The Book 40 Element Formulas.pdf
The Book of Usora.pdf
The C++ Programming Language(Fourth Edition).pdf
the current Noetic.pdf
The Noetics ^0 Elements Equations ^0 Formulas.pdf
The Superiority of TKS.pdf
THE_KITAB_AL_NIZAM.pdf
The_Superiority_of_TKS.pdf
thinking_in_cognitive_architecture_cinematic_wrap_print.pdf
Thinking_in_Cognitive_Architecture_interior_KDP.pdf
Thinking_in_Cognitive_Architecture_v1.pdf
thinking_in_cognitive_architecture_wrap_v2.pdf
thinking_in_cognitive_architecture_wrap.pdf
ThomasCalculus11thtextbookSolutions.pdf
TikTok-Getting-Started.docx.pdf
TKS_Abstraction_Ladder_and_Consciousness_Unlock_Spec (1).pdf
TKS_Abstraction_Ladder_and_Consciousness_Unlock_Spec.pdf
TKS_Cognitive_Framework_Expanded_Book_v3_Voice.pdf
TKS_COMPLETE_COMPANION_GUIDE_1 (1) (1).pdf
TKS_FORMAL_MANUAL_v6.1_CLEAN_DEFINITIONS.pdf
TKS_FORMAL_MATHEMATICAL_MANUAL_v6.0_MASTER.pdf
TKS_FORMAL_MATHEMATICAL_MANUAL_v6.1_COMPLETE.pdf
TKS_FULL_Cognitive_Framework (1).pdf
TKS_FULL_Cognitive_Framework.pdf
TKS_Master_README_CLI_Runbook (1).pdf
TKS_Master_README_CLI_Runbook.pdf
TKS_Module_7_Governance_Rails.pdf
TKS_NJT_Scenario_Booklet.pdf
TKS_Overton_Book_from_Conversation - Copy.pdf
TKS_Overton_Book_from_Conversation.pdf
TKS_v7_4_AIRTIGHT_PATCHES_v2.pdf
TKS_v7_4_AIRTIGHT_PATCHES_v3_FINAL.pdf
TKS_v7_4_AIRTIGHT_PATCHES_v4_FINAL.pdf
TKS_v7_4_AIRTIGHT_PATCHES_v5_FINAL.pdf
TKS_v7_4_AIRTIGHT_PATCHES_v6_FINAL.pdf
TKS_v7_4_CORRECTED_CHAPTERS (1).pdf
TKS_v7_4_CORRECTED_CHAPTERS.pdf
TKS_v7_4_FULL_BEAUTIFUL (1).pdf
TKS_v7_4_FULL_BEAUTIFUL.pdf
TKS_v7_4_IMPLEMENTED_CORRECTIONS.pdf
TKS_v7_4_REFEREE_DEFENSIBLE.pdf
TKS_v7_4_Review_and_Corrections.pdf
TO-DO-LIST App.pdf
Todays_Element_Interpretations.pdf
Tootra Calendar.pdf
tootra formula combinations.pdf
Tootra_Elements_Interpretations.pdf
Tootra_Elements_March_2024.pdf
tootra_expression_scenarios.pdf
tootra_math_handbook (1).pdf
tootra_math_handbook.pdf
Tootra_Outreach_Campaign_Complete.pdf
Tootra_Outreach_Campaign_Corrected.pdf
Tootra_Outreach_Campaign.pdf
tootra_training_curriculum.pdf
Transmutation_Codification.pdf
TRG77d749P1-Henderson-Little.pdf
Trigo_ADR_Americas_-_Offer_of_Employment.pdf
Trigo_New_Hire_Benefits_Presentation_2025.pdf
TWL7O5VM.pdf
Untitled document (1).pdf
Untitled document.pdf
videoplayback-mp4-d6459c21-47e6t.pdf
We The People by Zero.pdf
wealth operation.pdf
webtest.skillcheck.com_onlinetesting_servlet_com.skillcheck.session_management.SK_Servlet_ID=TOTAL-SMSSOLUTIONS&MODE=REPORTRETRIEVAL,5455363572586269877,html.pdf
WHITEPAPER_CAS_CORE_8_v0.1.pdf
WHITEPAPER_CAS_OHM_1_0_v0.1.pdf
WHITEPAPER_CAS_PCBA_8_v0.1.pdf
WHITEPAPER_NOETIC_TOPOS_2_0_v0.1.pdf
WHITEPAPER_TKS_V8_0_v0.1.pdf
WorkPlayFitPush_Week2.pdf

### C:\Users\wakil\Downloads\files (3)\
CCDL_EXT_R1_v0.3_Changelog.pdf
CCDL_SEM_R1_v0.1_Skeleton.pdf
Foundation_Drive_Profile_v0.1.pdf
Ontology_Freeze_v1.0-rc2_Amendments.pdf
fd_generator.py
fd_profile_inputs.json
fd_routing_28.json

---

## 8. Live cloud identifiers

### AWS
Account (primary)                807562639912   (us-west-2)
Account (preprod)                063693212118   (us-west-2)
IAM user                         cas-g5-operator   (arn:aws:iam::807562639912:user/cas-g5-operator)
MFA device ARN                   arn:aws:iam::807562639912:mfa/cas-g5-operator-authenticator   (EnableDate 2026-08-20T23:00:15+00:00)
Root MFA (u2f security key)      arn:aws:iam::807562639912:u2f/root/Securitykey-XZ25DBS6DVHGZCEHKAFQD7ER2M
AWS credential profile           [default]  region us-west-2  (C:\Users\wakil\.aws\config; C:\Users\wakil\.aws\credentials — key ID on file, secret not reproduced here)
CloudTrail trail                 cas-harness-audit-v1   (arn:aws:cloudtrail:us-west-2:807562639912:trail/cas-harness-audit-v1; created/verified 2026-08-21, multi-region, log-file validation on, global events; note: the same-day evidence file cloudtrail_trail_inventory.json predates Option A and recorded trail_count 0)
S3 bucket (WORM)                 cas-harness-cloudtrail-worm-807562639912   (Object Lock GOVERNANCE 1 yr, destination prefix cloudtrail)
S3 bucket (guardian artifacts)   cas-harness-runpod-92754088   (ObjectLock Enabled, versioning Enabled)
S3 bucket (preprod artifacts)    cas-harness-preprod-artifacts-063693212118
CloudFormation stack             cas-runpod-guardian-v1            (807562639912, us-west-2, UPDATE_COMPLETE, ActivationMode INERT)
CloudFormation stack             cas-harness-preprod-guardian      (063693212118, us-west-2, stack id 739b3640-9d12-11f1-ba34-069fd0246e89, ActivationMode LIVE)
CloudFormation stack (standby)   cas-aws-gpu-standby-v1            (g6e.xlarge / NVIDIA L40S; CREATE_COMPLETE; zero EC2 instances)
Guardian ledger table            cas-runpod-guardian-global-v1-807562639912   (COUNT 0)
Guardian ledger table (preprod)  cas-runpod-guardian-global-v1-063693212118
KMS signing key (preprod)        arn:aws:kms:us-west-2:063693212118:key/c657f4d6-fc95-48f3-9a72-84027e4f556c
Secrets Manager (preprod)        arn:aws:secretsmanager:us-west-2:063693212118:secret:cas-harness-preprod-provider-placeholder-K1Uxd7
State machine (preprod)          arn:aws:states:us-west-2:063693212118:stateMachine:cas-harness-preprod-guardian-guardian
Guardian Lambdas (preprod)       cas-harness-preprod-guardian-{control,create,create-proxy,observe,observe-proxy,recovery,starter,stop,stop-proxy}
Guardian runtime zip (prod)      sha256 326f483639b8b48ec8718ddf166663a721710e353968cde59d601bc22858baf9   (ActivationMode INERT)
Guardian runtime zip (preprod)   sha256 9ebc90c2048669a0026dafb046b465c7d5a7405b172d32bcacf55ad80548e16e
RunPod provider account          user_38E4xHk5H6yjrzEh4KUse08Ia8U

### RunPod pods (14 = 2 protected + 12 scale-run) + 2 historical
Protected / standing:
    q2oqlooejhin7s        (heavy_moccasin_gerbil, H200 SXM x1, EXITED — never delete or mutate)
    vernmyfb3ck9po        (cas-open-weight-canary-v2-20260820t124254257z-d874dad6, A40 x1, EXITED — keep stopped)
Scale-run pods (12; attested in RESULT_DETECTOR_VALIDATION_V14..V19 and RESULT_V29..V31 write-ups):
    5dv04y7rb3di1n
    79s7qa90zpx4dp
    mr6rcjslgaeg8i        (owner-authorized paid A40 pythia-6.9b research run, verified EXITED)
    mlr773s3qic1zt
    sa7wy64kfny07m
    5kshsd3n5utxdz
    j9h3dor7g90hcc
    g0za4pqxzhlcks
    0uafguwfrfy6as
    vj7np0zmiwtsck
    pb5cdkvnoqh3py
    6c7ml3ejpw66jb
Historical:
    nppakqiaux91mk        (research pod cas-tks-anchor-diagnostic-20260721, stopped)
    hilj2rzs54gi06        (production pod at 2026-07-21 handoff; no longer returned by account inventory)
RunPod network volume          hfelwlp1va   (130 GB — never mutate or delete)
RunPod credential files        C:\Users\wakil\.runpod\config.toml   C:\Users\wakil\.runpod\ssh\RunPod-Key-Go(.pub)
LLM key env file (paths only)  C:\Users\wakil\.cas_llm_keys.env   (DASHSCOPE, DEEPSEEK, ZHIPU)

### Models (four model IDs; the pinned revision)
EleutherAI/pythia-160m          HF revision 50f5173d932e8e61f858120bcb800b97af589f46
                                (reserialized model.safetensors sha256 d5861d3237c5f8e952b4ebf05179f3bc50d479186fbe96845d22660d96c50d97 — the local-snapshot REV used by every detector script)
EleutherAI/pythia-6.9b          (scale runs v10, v14-v19, v29; direct transformers, paid A40)
Qwen/Qwen2.5-7B                 (v31 clean attribution)
Qwen/Qwen2.5-7B-Instruct        (v30 instruct test)

### USPTO
Provisional application         64/037,173   (utility provisional, filed 04/13/2026, Conf# 1346, Patent Center# 75259715)
