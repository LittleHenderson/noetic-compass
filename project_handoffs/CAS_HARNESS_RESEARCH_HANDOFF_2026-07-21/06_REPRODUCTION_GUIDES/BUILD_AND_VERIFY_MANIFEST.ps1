param(
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$manifestPath = Join-Path $root "MANIFEST.json"
$manifestHashPath = Join-Path $root "MANIFEST.sha256"
$checksumsPath = Join-Path $root "SHA256SUMS.txt"

function Get-RelativePath {
    param([string]$FullName)
    return $FullName.Substring($root.Length).TrimStart('\').Replace('\', '/')
}

function Get-Category {
    param([string]$RelativePath)
    switch -Regex ($RelativePath) {
        '^01_FROZEN_SOURCE/' { return 'source' }
        '^02_RESEARCH_EVIDENCE/' { return 'raw_evidence' }
        '^03_RESEARCH_AND_ARCHITECTURE_DOCS/' { return 'documentation' }
        '^04_AMAZON_INTERNAL_DRAFT_DO_NOT_SEND/' { return 'internal_draft' }
        '^05_RUNPOD_STATE/' { return 'receipt' }
        '^07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b/' { return 'source' }
        '^08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/SOURCE/' { return 'source' }
        '^08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/PINNED_DEPENDENCY/' { return 'source' }
        '^08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/SECURITY_BOUNDARY\.md$' { return 'provenance_or_exclusion' }
        '^09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/.+\.bundle$' { return 'source' }
        '^09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/.+RECEIPT.+\.json$' { return 'receipt' }
        '^10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/.+\.bundle$' { return 'source' }
        '^10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/(SOURCE_IDENTITY\.json|TEST_AND_REVIEW_RECEIPT\.md)$' { return 'receipt' }
        '^11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/01_FROZEN_INPUTS/' { return 'receipt' }
        '^11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/03_IMPLEMENTATION_CHECKPOINT/.+\.bundle$' { return 'source' }
        '^11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/04_PROTOCOL_AND_ANCHOR/' { return 'receipt' }
        '^11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/05_GPU_EXECUTION_EVIDENCE/' { return 'raw_evidence' }
        '^11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/06_INDEPENDENT_VERIFICATION/' { return 'receipt' }
        '^99_EXCLUSIONS_AND_SECURITY/' { return 'provenance_or_exclusion' }
        default { return 'documentation' }
    }
}

function Get-Confidentiality {
    param([string]$RelativePath)
    if ($RelativePath -like '04_AMAZON_INTERNAL_DRAFT_DO_NOT_SEND/*' -or
        $RelativePath -like '99_EXCLUSIONS_AND_SECURITY/UNVERIFIED_PREVIEW_DO_NOT_DISTRIBUTE/*') {
        return 'restricted'
    }
    if ($RelativePath -like '02_RESEARCH_EVIDENCE/*' -or
        $RelativePath -like '03_RESEARCH_AND_ARCHITECTURE_DOCS/SUPPLIED_SOURCE_INPUTS/*' -or
        $RelativePath -like '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/*' -or
        $RelativePath -like '09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/*' -or
        $RelativePath -like '10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/*' -or
        $RelativePath -like '11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/*') {
        return 'internal'
    }
    return 'ordinary'
}

function Get-DistributionStatus {
    param([string]$RelativePath)
    if ($RelativePath -like '04_AMAZON_INTERNAL_DRAFT_DO_NOT_SEND/*' -or
        $RelativePath -like '99_EXCLUSIONS_AND_SECURITY/UNVERIFIED_PREVIEW_DO_NOT_DISTRIBUTE/*') {
        return 'paused'
    }
    return 'not_applicable'
}

$sourceMap = @{
    '00_PROJECT_STATUS/cas_harness_production_todo_2026-07-21.md' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_harness_production_todo.md'
    '00_PROJECT_STATUS/customer_production_successor_spec_2026-07-21.md' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_HARNESS_CUSTOMER_PRODUCTION_SUCCESSOR_SPEC_20260716.md'
    '01_FROZEN_SOURCE/cas-tks-anchor-diagnostic-20260721-da00bd94.zip' = 'C:\tmp\cas-tks-anchor-diagnostic-20260721-da00bd94.zip'
    '02_RESEARCH_EVIDENCE/supporting_local_preflight/cas-pythia-hook-equivalence-local-20260721.json' = 'C:\tmp\cas-pythia-hook-equivalence-local-20260721.json'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/PINNED_DEPENDENCY/jacobian-lens-581d398.bundle' = 'C:\tmp\jacobian-lens-581d398.bundle'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/CONTRACTS/CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md' = 'C:\tmp\cas-jspace-ohm-shadow-20260721\docs\working\CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md'
    '09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\.tmp\c\docs\working\CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md'
    '09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/CJT_BIAS_RPM_OHM_SYNTHETIC_V0.json' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\.tmp\c\noetic-compass-scaffold\noetic-compass\live-trace-worker\research_protocols\CJT_BIAS_RPM_OHM_SYNTHETIC_V0.json'
    '09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/CJT_BIAS_RPM_OHM_SYNTHETIC_V0.lock.txt' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\.tmp\c\noetic-compass-scaffold\noetic-compass\live-trace-worker\research_requirements\CJT_BIAS_RPM_OHM_SYNTHETIC_V0.lock.txt'
    '10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/CAS_HARNESS_COMBINED_LIVE_MODEL_CANARY_READINESS_20260722.md' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_HARNESS_COMBINED_LIVE_MODEL_CANARY_READINESS_20260722.md'
    '10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md'
    '10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/CAS_HARNESS_CUSTOMER_PRODUCTION_SUCCESSOR_SPEC_20260716.md' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_HARNESS_CUSTOMER_PRODUCTION_SUCCESSOR_SPEC_20260716.md'
    '10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/cas_harness_production_todo_20260722_snapshot.md' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_harness_production_todo.md'
    '10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/CJT_BIAS_RPM_OHM_STATISTICAL_V1.json' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\.tmp\c\noetic-compass-scaffold\noetic-compass\live-trace-worker\research_protocols\CJT_BIAS_RPM_OHM_STATISTICAL_V1.json'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/ONTOLOGY/CAS_HARNESS_CJT_EXTERNAL_DRIVE_ONTOLOGY_20260721_at_5d9a9d42.md' = 'C:\tmp\cas-jspace-ohm-shadow-20260721\docs\working\CAS_HARNESS_CJT_EXTERNAL_DRIVE_ONTOLOGY_20260721.md'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/PROTOCOLS/RESEARCH_SHADOW_at_5d9a9d42.md' = 'C:\tmp\cas-jspace-ohm-shadow-20260721\noetic-compass-scaffold\noetic-compass\live-trace-worker\RESEARCH_SHADOW.md'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/CAS_HARNESS_JSPACE_OHM_300B_CAPABILITY_ANALYSIS_20260720.md' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_HARNESS_JSPACE_OHM_300B_CAPABILITY_ANALYSIS_20260720.md'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/TKS_CAS_SEMANTIC_SOURCE_REGISTRY_CANDIDATE_20260720.json' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\TKS_CAS_SEMANTIC_SOURCE_REGISTRY_CANDIDATE_20260720.json'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SUPPLIED_SOURCE_INPUTS/CAS_vs_JSpace_Comparison_Memo_v1.docx' = 'C:\Users\wakil\Downloads\CAS_vs_JSpace_Comparison_Memo_v1.docx'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SUPPLIED_SOURCE_INPUTS/CAS_Ohm_Quantification_Guide-2.pdf' = 'C:\Users\wakil\Downloads\CAS_Ohm_Quantification_Guide-2.pdf'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SUPPLIED_SOURCE_INPUTS/CAS_Ohm_Harness_Operationalization_Addendum_v0_1.docx' = 'C:\Users\wakil\Downloads\CAS_Ohm_Harness_Operationalization_Addendum_v0_1.docx'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/formal_corpus/TKS_v7.4_MASTER.tex' = 'C:\Users\wakil\Downloads\Everthing-Tootra-TKS\TKS_v7.4_MASTER.tex'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/formal_corpus/TKS_v7_4_FULL_BEAUTIFUL.txt' = 'C:\Users\wakil\Downloads\Everthing-Tootra-TKS\TKS_v7_4_FULL_BEAUTIFUL.txt'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/formal_corpus/TKS_FORMAL_MATHEMATICAL_MANUAL_v7.2_COMPLETE.tex' = 'C:\Users\wakil\Downloads\Everthing-Tootra-TKS\TKS_FORMAL_MATHEMATICAL_MANUAL_v7.2_COMPLETE.tex'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/formal_corpus/tootra_math_handbook (1).md' = 'C:\Users\wakil\Downloads\Everthing-Tootra-TKS\tootra_math_handbook (1).md'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/normalized_canon/canon_index.json' = 'C:\Users\wakil\Downloads\Everthing-Tootra-TKS\canon\normalized\canon_index.json'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/normalized_canon/canon_elements_40.json' = 'C:\Users\wakil\Downloads\Everthing-Tootra-TKS\canon\normalized\canon_elements_40.json'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/normalized_canon/canon_subfoundations_28_defs.json' = 'C:\Users\wakil\Downloads\Everthing-Tootra-TKS\canon\normalized\canon_subfoundations_28_defs.json'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/normalized_canon/canon_acquisitions_22.json' = 'C:\Users\wakil\Downloads\Everthing-Tootra-TKS\canon\normalized\canon_acquisitions_22.json'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/repository_normative/CAS_FOUNDATIONAL_CLARIFICATIONS.md' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\CAS_FOUNDATIONAL_CLARIFICATIONS.md'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/repository_normative/tks_owner_locked_definitions_20260603_D3_workspace.json' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\tks_owner_locked_definitions_20260603.json'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/protected_deployed/tks_owner_locked_definitions_20260603_A124_deployed.json' = 'C:\Users\wakil\CAS-Harness-Run\noetic-compass-scaffold\noetic-compass\api\resources\tks_owner_locked_definitions_20260603.json'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/repository_normative/noetic_topos_journal_main.tex' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\peer_review\journal_submission\main.tex'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/repository_normative/noetic-topos_dashboard.md' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\noetic-compass-scaffold\noetic-compass\dashboard\public\noetic-topos.md'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/repository_normative/noetic_topos_compiled_main.pdf' = 'C:\Users\wakil\Downloads\main.pdf'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/repository_normative/TKS_v7_4_Review_and_Corrections.pdf' = 'C:\Users\wakil\Downloads\TKS_v7_4_Review_and_Corrections.pdf'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/repository_normative/TKS_v7_4_REFEREE_DEFENSIBLE.pdf' = 'C:\Users\wakil\Downloads\TKS_v7_4_REFEREE_DEFENSIBLE.pdf'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/repository_normative/TKS_v7_4_CORRECTED_CHAPTERS.pdf' = 'C:\Users\wakil\Downloads\TKS_v7_4_CORRECTED_CHAPTERS.pdf'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/repository_normative/compiler.py' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\noetic-compass-scaffold\noetic-compass\api\notation\compiler.py'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/repository_normative/v74_baseline.py' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-synthetic\generator\v74_baseline.py'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SEMANTIC_AUTHORITY_SOURCES/repository_normative/Programming_in_CAS_v0_4_MECH_AUDIT.md' = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\book\programming_in_cas\Programming_in_CAS_v0_4_MECH_AUDIT.md'
    '99_EXCLUSIONS_AND_SECURITY/SUPERSEDED_DO_NOT_USE/cas-tks-anchor-diagnostic-20260721-0fd25a7b-SUPERSEDED-DO-NOT-USE.zip' = 'C:\tmp\cas-tks-anchor-diagnostic-20260721-0fd25a7b.zip'
    '99_EXCLUSIONS_AND_SECURITY/UNVERIFIED_PREVIEW_DO_NOT_DISTRIBUTE/cas_harness_amazon_brief_p1_UNVERIFIED.png' = 'C:\tmp\cas_harness_amazon_brief_p1.png'
}

$continuationProtocolRoot = 'C:\tmp\cas-jspace-ohm-shadow-20260721\noetic-compass-scaffold\noetic-compass\live-trace-worker\research_protocols'
foreach ($name in @(
    'JACOBIAN_LENS_CANARY_V0.canonical.sha256',
    'JACOBIAN_LENS_CANARY_V0.json',
    'JACOBIAN_LENS_CANARY_V0.md',
    'JACOBIAN_LENS_CANARY_V0.sha256',
    'JSPACE_CORRESPONDENCE_V0_DRAFT.canonical.sha256',
    'JSPACE_CORRESPONDENCE_V0_DRAFT.json',
    'JSPACE_CORRESPONDENCE_V0_DRAFT.md',
    'JSPACE_CORRESPONDENCE_V0_DRAFT.sha256'
)) {
    $sourceMap["08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/PROTOCOLS/$name"] = Join-Path $continuationProtocolRoot $name
}

$historicalWorking = @(
    'cas_harness_original_closure_methodology_20260526.md',
    'cas_harness_synopsis_20260630.md',
    'cjt_pcba_cas_harness_claim_audit_20260617.md',
    'cas_harness_launch_security_audit_plan_20260604.md',
    'cas_harness_amazon_review_brief_20260615.md',
    'CAS_HARNESS_AMAZON_REVIEW_BRIEF_20260615.pdf'
)
foreach ($name in $historicalWorking) {
    $sourceMap["03_RESEARCH_AND_ARCHITECTURE_DOCS/HISTORICAL_CLAIM_AND_AUDIT_CONTEXT/$name"] = "C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\$name"
}
$sourceMap['03_RESEARCH_AND_ARCHITECTURE_DOCS/HISTORICAL_CLAIM_AND_AUDIT_CONTEXT/CAS_HARNESS_SPEC_SHEET_current.md'] = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\legal_drafts_20260607\CAS_HARNESS_SPEC_SHEET_current.md'
$sourceMap['03_RESEARCH_AND_ARCHITECTURE_DOCS/HISTORICAL_CLAIM_AND_AUDIT_CONTEXT/CAS_HARNESS_SPEC_SHEET_current.pdf'] = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\legal_drafts_20260607\CAS_HARNESS_SPEC_SHEET_current.pdf'

$criticalExpected = @{
    '01_FROZEN_SOURCE/cas-tks-anchor-diagnostic-20260721-da00bd94.zip' = 'CAEB3171D8F461E81AEB164888A41A7C33E105D2813A253DF25A833CC58A2E20'
    '02_RESEARCH_EVIDENCE/full_recovery/artifacts/full/tks_definition_anchor_raw_diagnostic_vectors.npz' = '454A4F017D56ED393E50D7E88D29486B3379E96AE930A1123698C6275298EAD6'
    '02_RESEARCH_EVIDENCE/full_recovery/artifacts/full/tks_definition_anchor_report.json' = '0440462D278DA53B2FC217F252DFF0D295C878B356FD53BCCB38CC810407CDEF'
    '02_RESEARCH_EVIDENCE/full_recovery/artifacts/full/FULL_BUNDLE_SHA256SUMS' = 'B44E4457DE6763BC41A27AA1B746CBABA19A753F788F472B2FE4EF9546624A93'
    '02_RESEARCH_EVIDENCE/full_recovery/OFF_POD_VERIFICATION.json' = 'DB115601DF8F2984D56F6C9F5CDE09F598B77308ACD6CF978109583F375C2E9C'
    '02_RESEARCH_EVIDENCE/full_recovery/RESULT_SUMMARY.md' = '0EED1D9BC572D0B9E79BE1C980C0DDAD6227F58DD6A8693A1081A26DF0E8F90A'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SUPPLIED_SOURCE_INPUTS/CAS_vs_JSpace_Comparison_Memo_v1.docx' = 'A6236EEAB5194F875A105E5153E5B47948C147A3EDAFC5241EAFACBA979B1259'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SUPPLIED_SOURCE_INPUTS/CAS_Ohm_Quantification_Guide-2.pdf' = '89AE13C0A5D6208E328E9EDC55F816609BB172076CC13093DCCCCF418145CE64'
    '03_RESEARCH_AND_ARCHITECTURE_DOCS/SUPPLIED_SOURCE_INPUTS/CAS_Ohm_Harness_Operationalization_Addendum_v0_1.docx' = '0B62BBC66828A273E5458CC4D98EEE9B341554A474CCACB6387B209B5F0BE5E5'
    '04_AMAZON_INTERNAL_DRAFT_DO_NOT_SEND/CAS_HARNESS_AMAZON_TECHNICAL_EVALUATION_SPEC_20260721.md' = '22B651F84B5D6EFAA3B5F65BD63F4CA09D4A116F2932D35088C238DD33F9C8B2'
    '04_AMAZON_INTERNAL_DRAFT_DO_NOT_SEND/CAS_HARNESS_AMAZON_CLAIM_EVIDENCE_MANIFEST_20260721.json' = 'F799BC74BBDE2DDCC50FE82AA387052082F0D67540064D7C7C216645ECEDBC44'
    '04_AMAZON_INTERNAL_DRAFT_DO_NOT_SEND/LATEST.json' = 'A0C0974AA1158B84071B3B047EF29C76F65EC0C2F31AF499A3956B8EFA2BF8D9'
    '99_EXCLUSIONS_AND_SECURITY/SUPERSEDED_DO_NOT_USE/cas-tks-anchor-diagnostic-20260721-0fd25a7b-SUPERSEDED-DO-NOT-USE.zip' = 'C6DE7ED1B9B947EC216B0643364BB2546921B07EFD9B0B3091EDD0CE1E84D55E'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/SOURCE/cas-jspace-ohm-shadow-405fb389.bundle' = 'F5756D1D972F2EBA5A998C090BEECEC9A4F5A2591E923503C9F7A6BD9515E88B'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/PINNED_DEPENDENCY/jacobian-lens-581d398.bundle' = '1DA9F6D9EF4E185615C1BD7A5B548C1FCAC513340C24B1DD8DE68115FC793E82'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/PROTOCOLS/JACOBIAN_LENS_CANARY_V0.json' = 'FB302300829889072C68E5FD0F0E9AC1710DAA58AAB4AAE5ABC76A8EEE360CB1'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/PROTOCOLS/JSPACE_CORRESPONDENCE_V0_DRAFT.json' = '31DCFDA7F85ABC02F9692B95C82D0E6C9F89CA2C44AB063ACF83A7AC3CE5215D'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/ONTOLOGY/CAS_HARNESS_CJT_EXTERNAL_DRIVE_ONTOLOGY_20260721.md' = '03290474C171E310844E38AB10377DA7363215431A7F99D3965AA235F80EA417'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/SOURCE/cas-jspace-ohm-shadow-5d9a9d42.bundle' = 'E4E971A7990A4AEFD1EC550A4FFD870256301342EB7F18C6397D236D64FFFB5E'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/CONTRACTS/CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md' = 'C39EB46BCC5AA3D482C9A53EC82FBF4362058F56817B0C3E644D3FD9636BA4FE'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/ONTOLOGY/CAS_HARNESS_CJT_EXTERNAL_DRIVE_ONTOLOGY_20260721_at_5d9a9d42.md' = '0A2962D9ACC824BF8959B5F35830875E1728EB2EA33F7ED8CCBA039D5594DEB7'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/PROTOCOLS/RESEARCH_SHADOW_at_5d9a9d42.md' = '62C86955D5568E05C79FBE787980D2790C911F06D9809E10622926CE2C989146'
    '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/PRIOR_SNAPSHOTS/CAS_HARNESS_JSPACE_OHM_300B_CAPABILITY_ANALYSIS_before_refresh_20260721.md' = 'F932951A85643AAF1F2D2CC3C8C8DFB7A06DD11494122633F3A7F95CC1306FD6'
    '09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/CAS_HARNESS_CJT_OHM_SYNTHETIC_25053461.bundle' = '28CB29B80E27DD1E13E86E9C889B13A6963CE48DE40C65703A75BB23E0CCF8BF'
    '09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/CJT_BIAS_RPM_OHM_SYNTHETIC_RECEIPT_25053461.json' = '76E907BD8A51B466A8BFB0BA84EE5D9A2E5DDA7C51CC4B171D86C07B3FC9E764'
    '09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/CJT_BIAS_RPM_OHM_SYNTHETIC_V0.json' = 'F8382F355B4058C14A439260C42E4066ABBEAF033AE2F499AF759500F49D61DB'
    '09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/CJT_BIAS_RPM_OHM_SYNTHETIC_V0.lock.txt' = '4DD1DCACCB2D531F4A8FCF0A50CE77CC60D9F48F276DC32190247BFF7C406D46'
    '09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md' = '860692F3C15030F8489865F1051F1358C441208408985D837FD44B8483D06881'
    '09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/RESEARCH_SHADOW_at_25053461.md' = '1768EDDE07F42E6DE82130F1A73C65541E10F915DF38B9BB224CD542F9BE3547'
    '10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/CAS_HARNESS_CJT_OHM_STAT_EVIDENCE_50cd375f.bundle' = '7BD5EF9281932D967CDB16D877D24C96DE2A595E03850F8FE41AE6694551A9C5'
    '10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/CJT_BIAS_RPM_OHM_STATISTICAL_V1.json' = '2452A8CB52038F2F6F93FC2217537BA1432622C9EDA70E99C5039AD2825F14E7'
}

function Resolve-SourcePath {
    param([string]$RelativePath)
    if ($sourceMap.ContainsKey($RelativePath)) { return $sourceMap[$RelativePath] }
    if ($RelativePath -like '01_FROZEN_SOURCE/reference/*') {
        return 'C:\tmp\cas-harness-tks-definition-ab-20260721\docs\reference\' + ($RelativePath.Substring('01_FROZEN_SOURCE/reference/'.Length).Replace('/', '\'))
    }
    if ($RelativePath -like '02_RESEARCH_EVIDENCE/full_recovery/*') {
        return 'C:\tmp\cas-tks-anchor-diagnostic-20260721\full_recovery\' + ($RelativePath.Substring('02_RESEARCH_EVIDENCE/full_recovery/'.Length).Replace('/', '\'))
    }
    if ($RelativePath -like '04_AMAZON_INTERNAL_DRAFT_DO_NOT_SEND/*') {
        $name = $RelativePath.Substring('04_AMAZON_INTERNAL_DRAFT_DO_NOT_SEND/'.Length)
        $candidate = 'C:\tmp\cas-amazon-eval-20260721\docs\external\amazon\' + $name.Replace('/', '\')
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    if ($RelativePath -like '07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b/*') {
        $suffix = $RelativePath.Substring('07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b/'.Length)
        $candidate = 'C:\Users\wakil\CAS-Harness-Run\noetic-compass-scaffold\noetic-compass\' + $suffix.Replace('/', '\')
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    return $null
}

if ($VerifyOnly) {
    foreach ($required in @($manifestPath, $manifestHashPath, $checksumsPath)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing integrity file: $required" }
    }
    $manifestHashLine = (Get-Content -LiteralPath $manifestHashPath | Select-Object -First 1)
    if ($manifestHashLine -notmatch '^([A-Fa-f0-9]{64})  MANIFEST\.json$') { throw 'Malformed MANIFEST.sha256' }
    $actualManifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash
    if ($actualManifestHash -ne $Matches[1]) { throw "MANIFEST hash mismatch: expected $($Matches[1]), actual $actualManifestHash" }
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    $actualChecksumsHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $checksumsPath).Hash
    if ($actualChecksumsHash -ne $manifest.sha256sums_sha256) { throw 'SHA256SUMS.txt hash does not match MANIFEST.json' }
    $verified = 0
    foreach ($line in Get-Content -LiteralPath $checksumsPath) {
        if ($line -notmatch '^([A-Fa-f0-9]{64})  (.+)$') { throw "Malformed checksum line: $line" }
        $expected = $Matches[1]
        $relative = $Matches[2]
        $path = Join-Path $root $relative.Replace('/', '\')
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing payload file: $relative" }
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash
        if ($actual -ne $expected) { throw "Payload hash mismatch: $relative" }
        $verified++
    }
    [pscustomobject]@{
        Status = 'HANDOFF_VERIFICATION_PASS'
        PayloadFilesVerified = $verified
        ManifestSHA256 = $actualManifestHash
        SHA256SUMSSHA256 = $actualChecksumsHash
        ClaimStatus = $manifest.global_claim_status
        AmazonDistributionAllowed = $manifest.amazon_distribution_allowed
    } | Format-List
    exit 0
}

$excludedNames = @('MANIFEST.json', 'MANIFEST.sha256', 'SHA256SUMS.txt')
$files = @(Get-ChildItem -LiteralPath $root -Recurse -File -Force | Where-Object { $excludedNames -notcontains $_.Name } | Sort-Object FullName)
$createdUtc = (Get-Date).ToUniversalTime().ToString('o')
$entries = @()
$checksumLines = @()
$sourceMismatches = @()
$criticalMismatches = @()

foreach ($file in $files) {
    $relative = Get-RelativePath $file.FullName
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash
    $checksumLines += "$hash  $relative"
    $sourcePath = Resolve-SourcePath $relative
    $sourceExists = $false
    $sourceHash = $null
    $sourceMatches = $null
    if ($sourcePath -and (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        $sourceExists = $true
        $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash
        $sourceMatches = ($sourceHash -eq $hash)
        if (-not $sourceMatches) { $sourceMismatches += $relative }
    }
    $expectedHash = $null
    $expectedMatches = $null
    if ($criticalExpected.ContainsKey($relative)) {
        $expectedHash = $criticalExpected[$relative]
        $expectedMatches = ($hash -eq $expectedHash)
        if (-not $expectedMatches) { $criticalMismatches += $relative }
    }
    $entries += [pscustomobject]@{
        artifact_id = (($relative -replace '[^A-Za-z0-9]+', '_').Trim('_').ToLowerInvariant())
        category = Get-Category $relative
        relative_path = $relative
        copied_from = $(if ($sourcePath) { $sourcePath } else { 'generated_in_handoff' })
        bytes = $file.Length
        sha256 = $hash
        copied_at_utc = $file.CreationTimeUtc.ToString('o')
        original_preserved = $true
        claim_status = 'NOT_LICENSED_DIAGNOSTIC_ONLY'
        confidentiality = Get-Confidentiality $relative
        distribution_status = Get-DistributionStatus $relative
        verification = [pscustomobject]@{
            hash_recomputed_after_copy = $true
            source_exists = $sourceExists
            source_sha256 = $sourceHash
            source_hash_matches_copy = $sourceMatches
            expected_sha256 = $expectedHash
            matches_expected_hash = $expectedMatches
        }
    }
}

if ($sourceMismatches.Count -gt 0) { throw "Copied files differ from current sources: $($sourceMismatches -join ', ')" }
if ($criticalMismatches.Count -gt 0) { throw "Critical expected hashes do not match: $($criticalMismatches -join ', ')" }

$checksumLines | Set-Content -LiteralPath $checksumsPath -Encoding utf8
$checksumsHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $checksumsPath).Hash
$manifest = [ordered]@{
    schema_version = 'cas_harness.research_handoff_manifest.v1'
    handoff_id = 'CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21'
    created_at_utc = $createdUtc
    timezone = 'America/Los_Angeles'
    canonical_folder = $root
    copy_only_policy = $true
    originals_preserved = $true
    global_claim_status = 'NOT_LICENSED_DIAGNOSTIC_ONLY'
    claim_eligible = $false
    amazon_distribution_status = 'DISTRIBUTION_PAUSED_INTERNAL_REVIEW_DRAFT'
    amazon_distribution_allowed = $false
    source_identity = [ordered]@{
        branch = 'codex/tks-definition-ab-20260721'
        commit = 'da00bd9407e7e82662b53edd77980040e34eacf4'
        tree = 'a95852594ce6c2e19862cb048bb3419b39812526'
        protected_parent = '81b5c18bd83e1f01ccd398dcad3865a674335b7f'
    }
    continuation_source_identities = @(
        [ordered]@{
            purpose = 'J-Space, Jacobian-lens, CAS-Ohm, eraser-contract, and verdict-quarantine continuation'
            status = 'INTERMEDIATE_SUPERSEDED_BY_5d9a9d42'
            branch = 'codex/jspace-ohm-shadow-20260721'
            commit = '405fb3896367f10cdc1a96c4253cbaaadbbb22fa'
            tree = '68da4b52c7fc459d43e1906f35ea8dd37cda4bdf'
            protected_parent = '81b5c18bd83e1f01ccd398dcad3865a674335b7f'
            milestone_commits = @(
                '14629b76',
                'de1a117d',
                'd4dc5628',
                '1e92b5bb',
                '405fb389'
            )
            bundle_relative_path = '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/SOURCE/cas-jspace-ohm-shadow-405fb389.bundle'
            bundle_sha256 = 'F5756D1D972F2EBA5A998C090BEECEC9A4F5A2591E923503C9F7A6BD9515E88B'
            protocol_canonical_sha256 = [ordered]@{
                JACOBIAN_LENS_CANARY_V0 = '1a6745617a641649fa9f270220c17921409b05b8168cfcb806b2056e6763aff5'
                JSPACE_CORRESPONDENCE_V0_DRAFT = '228df1ff6cb231f2920bc92e22f9a99e30b36b5b08c7120fc5ab76369dc285b4'
            }
        },
        [ordered]@{
            purpose = 'Final continuation including the prospective CJT Bias, corrected RPM, and CAS-Ohm experiment contract'
            status = 'PROSPECTIVE_CONTRACT_BASE_SUPERSEDED_BY_25053461_SYNTHETIC_MVP'
            branch = 'codex/jspace-ohm-shadow-20260721'
            commit = '5d9a9d4206990e673d86a0c62518fd1a44ab6b1e'
            tree = '92340278032bdbb5e98bf67381f62e81f1dc008e'
            protected_parent = '81b5c18bd83e1f01ccd398dcad3865a674335b7f'
            predecessor_commit = '405fb3896367f10cdc1a96c4253cbaaadbbb22fa'
            milestone_commits = @(
                '14629b76',
                'de1a117d',
                'd4dc5628',
                '1e92b5bb',
                '405fb389',
                '5d9a9d42'
            )
            bundle_relative_path = '08_JSPACE_CAS_OHM_SHADOW_2026-07-21/CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/SOURCE/cas-jspace-ohm-shadow-5d9a9d42.bundle'
            bundle_sha256 = 'E4E971A7990A4AEFD1EC550A4FFD870256301342EB7F18C6397D236D64FFFB5E'
            contract_sha256 = 'C39EB46BCC5AA3D482C9A53EC82FBF4362058F56817B0C3E644D3FD9636BA4FE'
            protocol_canonical_sha256 = [ordered]@{
                JACOBIAN_LENS_CANARY_V0 = '1a6745617a641649fa9f270220c17921409b05b8168cfcb806b2056e6763aff5'
                JSPACE_CORRESPONDENCE_V0_DRAFT = '228df1ff6cb231f2920bc92e22f9a99e30b36b5b08c7120fc5ab76369dc285b4'
            }
        },
        [ordered]@{
            purpose = 'Deterministic CJT, Bias, RPM, and CAS-Ohm synthetic recovery MVP'
            status = 'CURRENT_SYNTHETIC_MVP_SHADOW_NOT_LICENSED'
            branch = 'codex/jspace-ohm-synthetic-20260721'
            commit = '25053461c94de23850da7f9c853c420aab1bae62'
            tree = 'b377232896eb5bd4c087268dcc0988d88dfba290'
            protected_parent = '81b5c18bd83e1f01ccd398dcad3865a674335b7f'
            predecessor_commit = '5d9a9d4206990e673d86a0c62518fd1a44ab6b1e'
            harness_status = 'SYNTHETIC_HARNESS_MVP_PASS'
            execution_mode = 'SHADOW'
            verdict_influence = 'NONE'
            claim_status = 'NOT_LICENSED'
            claim_eligible = $false
            model_execution = 'NONE_SYNTHETIC_ONLY'
            bundle_relative_path = '09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/CAS_HARNESS_CJT_OHM_SYNTHETIC_25053461.bundle'
            bundle_sha256 = '28CB29B80E27DD1E13E86E9C889B13A6963CE48DE40C65703A75BB23E0CCF8BF'
            receipt_relative_path = '09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21/CJT_BIAS_RPM_OHM_SYNTHETIC_RECEIPT_25053461.json'
            receipt_file_sha256 = '76E907BD8A51B466A8BFB0BA84EE5D9A2E5DDA7C51CC4B171D86C07B3FC9E764'
            envelope_content_sha256 = '816c7f387a1cf42f971a64a885b537984694057bab4891747df152919ec01ef1'
            report_content_sha256 = '61007b04ae3d7eb96cf4d94e3c3a264794eec55d4cb041b0a5cd3ce93a5f46f6'
            protocol_sha256 = 'F8382F355B4058C14A439260C42E4066ABBEAF033AE2F499AF759500F49D61DB'
            research_lock_sha256 = '4DD1DCACCB2D531F4A8FCF0A50CE77CC60D9F48F276DC32190247BFF7C406D46'
        },
        [ordered]@{
            purpose = 'Statistical-evidence and ceremony-preparation source hardening for the CJT, Bias, RPM, and CAS-Ohm synthetic lane'
            status = 'CURRENT_STATISTICAL_EVIDENCE_SOURCE_CHECKPOINT_SHADOW_NOT_LICENSED'
            branch = 'codex/cjt-ohm-stat-evidence-20260721'
            commit = '50cd375fdc179e6a60fbed785e5b726d1fd34c23'
            tree = '5072a086dbf6450e681c31f2f02dc581e1c90f4b'
            protected_parent = '25053461c94de23850da7f9c853c420aab1bae62'
            predecessor_commit = '25053461c94de23850da7f9c853c420aab1bae62'
            execution_mode = 'SHADOW'
            verdict_influence = 'NONE'
            claim_status = 'NOT_LICENSED'
            claim_eligible = $false
            model_execution = 'NONE'
            official_outcomes_generated = $false
            bundle_relative_path = '10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/CAS_HARNESS_CJT_OHM_STAT_EVIDENCE_50cd375f.bundle'
            bundle_sha256 = '7BD5EF9281932D967CDB16D877D24C96DE2A595E03850F8FE41AE6694551A9C5'
            protocol_relative_path = '10_COMBINED_LIVE_MODEL_READINESS_AND_STATISTICAL_EVIDENCE_2026-07-22/CJT_BIAS_RPM_OHM_STATISTICAL_V1.json'
            protocol_file_sha256 = '2452A8CB52038F2F6F93FC2217537BA1432622C9EDA70E99C5039AD2825F14E7'
            offline_drand_verifier_javascript_sha256 = '2840ad448b42a251394812dfc97367d83631954ab51b0c1f2b02d76e4207c829'
            focused_tests_passed = 158
            live_trace_worker_tests_passed = 576
            production_quarantine_tests_passed = 100
            postrepair_audits = 'APPROVE'
        }
    )
    model_identity = [ordered]@{
        model_id = 'EleutherAI/pythia-160m'
        revision = '50f5173d932e8e61f858120bcb800b97af589f46'
        architecture = 'GPTNeoXForCausalLM'
        layers = 12
        hidden_size = 768
    }
    runpod_snapshot = [ordered]@{
        snapshot_date = '2026-07-21'
        research_pod_id = 'nppakqiaux91mk'
        state = 'STOPPED'
        gpu_billing_ceased = $true
        retained_storage_usd_per_hour = 0.006
        production_pod_id = 'hilj2rzs54gi06'
        production_pod_untouched = $true
        mutable_provider_state = $true
    }
    open_gates = @(
        'independent_object_store_or_escrow',
        'independently_authored_neutral_holdout',
        'semantic_probe_validation',
        'causal_and_output_control',
        'prompt_injection_detection',
        'external_anchor_and_real_model_cjt_bias_rpm_ohm_execution',
        'cross_architecture_universality',
        'genuine_300b_execution',
        'production_readiness',
        'customer_production_ACCEPT'
    )
    exclusions = @('credentials', 'env_files', 'ssh_private_keys', 'provider_tokens', 'browser_sessions', 'model_caches', 'venvs', 'node_modules', 'git_worktrees', 'unrelated_CAS_Forex_changes')
    secret_scan_result = 'SEE_99_EXCLUSIONS_AND_SECURITY/SECRET_SCAN_RECORD.md'
    payload_file_count = $entries.Count
    payload_total_bytes = ($entries | Measure-Object -Property bytes -Sum).Sum
    sha256sums_sha256 = $checksumsHash
    artifacts = $entries
}

$manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding utf8
$manifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash
"$manifestHash  MANIFEST.json" | Set-Content -LiteralPath $manifestHashPath -Encoding ascii

[pscustomobject]@{
    Status = 'HANDOFF_MANIFEST_BUILT'
    PayloadFiles = $entries.Count
    PayloadBytes = $manifest.payload_total_bytes
    ManifestSHA256 = $manifestHash
    SHA256SUMSSHA256 = $checksumsHash
    SourceMismatches = $sourceMismatches.Count
    CriticalMismatches = $criticalMismatches.Count
} | Format-List
