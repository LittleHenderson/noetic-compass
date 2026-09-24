"""Shared, launcher-free and torch-free facts and checks for the unchanged-arm reproduction (HELM-REPAIR-CONTROLLED-1).

WHAT THIS FOLDER DOES. It freezes ONE AWS job and later reads its result:
  * the job: seed 20260917 of the historical Helm 2.0 source 20208c92, full registered 10-pass schedule, trained by
    the same launcher (`aws/typed_pointer_launch.py`) on g7.2xlarge, from the same committed package;
  * the reading: Codex's reproduction policy revision 1 (commit bc46b36e, `REPRODUCTION_POLICY.json`), implemented
    exactly. Three verdicts only:
      STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED            valid evidence AND identical learned state AND identical panel;
      DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY   valid evidence, but learned state or any panel record differs;
      ADMISSION_INVALID_STOP                             any missing, corrupt or misbound evidence (never a fallback).
    Checkpoint-FILE identity and optimizer/RNG CONTINUATION identity are printed separately and never decide.

REVISION 2 (2026-09-24, CLAUDE_BUILT_CLAUDE_CHECKED). Conformed to policy bc46b36e (Codex amendment item 2):
  * the old rule (final.pt file sha256) and its prose "status line" parser are GONE. Nothing here reads a status word
    out of prose (review finding V1);
  * two machine-readable states replace them:
      owner_authorization  - read from the three recorded owner files, each bound by its git blob id and sha256;
      execution_admission  - a technical-readiness record (`EXECUTION_ADMISSION.json`) bound to the exact plan,
                             policy, manifest, panel, environment and reader-source hashes. Only `ADMITTED`, with every
                             binding equal and every prerequisite receipt present, lets `--write` or `--check` proceed.
    `--dry-run` and every test run without either state. No approval word is ever inserted anywhere;
  * the complete public panel (564 course records), the numerical environment and the reader's own source are pinned.

THIS MODULE IMPORTS NOTHING FROM THE LAUNCHER, torch or the network. It lives under `records/`, not `cncm/` or
`cas_meta2/`, on purpose: `pointer_contract.input_inventory` globs `*.py` under those trees.

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED (temporary Claude builder while Codex is away). It transcribes the owner's words;
it is not an owner signature.
"""
from decimal import Decimal, InvalidOperation
from hashlib import sha1, sha256
import json
import os
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]          # the CNCM folder ("FOR CODEX TO BUILD CAS NATIVE ...")
GIT_PREFIX = 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/'
HERE_REL = 'records/typed_pointer_001/admission_unchanged_repro_001'
LABEL = 'CLAUDE_BUILT_CLAUDE_CHECKED'
RUNNER = 'Claude builder (temporary takeover while Codex is away)'

# ---- the source and the one job.
SOURCE_SHA = '20208c923d41c24614504d4ecc2b289ecb66eda8'
MODEL_SEED = 20260917
JOB_KIND = 'UNCHANGED_ARM_REPRODUCTION'
LAUNCHER_REL = 'research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py'

# ---- the committed package, restored into this branch blob-identical (commit d5a7b630 on this branch).
PACKAGE_COMMIT = '3da10d84652988190f66e3c239ee5cdeee8cc9dc'
PACKAGE_REL = 'research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_20208c92'
PACKAGE_BLOBS = {'receipt.json': '597e9a2fe3acd7a0e01d019bcd62728d5e8431f1',
                 'source.zip': '5020103650864d7d6cd6b9dd3b8e60d4d5e9e279'}
ARCHIVE_SHA256 = 'c42370c4941384c852feda33303dd70a01e956d28953cf07dd1b981220f31ed8'
ARCHIVE_BYTES = 5977155
MANIFEST_SHA256 = '333381ace5c4e37ff4c7fba7338bced0a4495f0cee7a43432bc3f2cc35923d40'
MEMBER_COUNT = 270
PACKAGE_RECEIPT_SCHEMA = 'cncm.typed-pointer-package-receipt/0.1'
# The worker's package root on the AWS instance, as the historical checkpoints record it (`init_args.root`).
HISTORICAL_PACKAGE_ROOT = '/opt/cas-graph6curr/package'

# ---- Helm 2.0's own seed-17 admission (same commit as the package). The new records must match it except the job.
HELM2_ADMISSION_REL = 'records/typed_pointer_001/admission_001/20260917'
HELM2_ADMISSION_BLOBS = {'request.json': 'd8c0b6574c85edc07927c7f232dac2b398432f0e',
                         'authority.json': '8017fec08f350ac802ec6ea437555da79c4711f0',
                         'owner.json': '4fc0ef3198bfeadb1e2c846181c01f8352cdbb6a'}
HELM2_JOB = 'cas-meta2-tpntr-20260920210258-20208c92-m-20260917'
HELM2_STAMP = '20260920210258'
HELM2_BINDINGS = {'inputs_sha256': '442ae914e563fcf0bbb49d9c6d6746b0bea2b4ef7390542b135a33864a494150',
                  'design_sha256': '7d57b52bd7055dd63e8c6ed293a885b06651406e521d24c2116ef8ca84826ec6',
                  'evidence_contract_sha256': '1a0f87415314ef1f324a01237ecacbe023d84bf83735d527a5bce89f42c6a490'}
HELM2_CONDITION = 'MIXED_SAME_ITEMS'
EXPECTED_BOUNDS = {'automatic_retries': 0, 'instance_seconds_max': 14400, 'instance_type': 'g7.2xlarge', 'jobs': 1,
                   'max_wall_seconds': 12600, 'optimizer_updates_max': 1488, 'region': 'us-west-2',
                   'reservation_usd': '15.00', 'training': True}

# ---- the comparison target: the delivered Helm 2.0 seed-17 receipt (commit c8d5c430).
REFERENCE_COMMIT = 'c8d5c430eec23a8fadd98bbcd045fecf03d86239'
REFERENCE_RECEIPT_REL = 'records/typed_pointer_001/receipt_20260917'
REFERENCE_FINAL_PT_SHA256 = 'c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb'
REFERENCE_FINAL_PT_BYTES = 3670007
FINAL_PT_RECORDS = ('collected/results/artifacts/manifest.json',          # the worker's own artifact manifest
                    'collected_inventory.json',                            # the launcher's inventory of the S3 copy
                    'collected/results/artifacts/final_checkpoint.json')   # the worker's checkpoint pin
REFERENCE_BLOBS = {'collected/results/artifacts/manifest.json': 'd98b25aa6b8022da9ad7f1b2c90c8799ea5b5827',
                   'collected_inventory.json': '25a2277b00c84613b33414de1c70c4cb96ee1ba7',
                   'collected/results/artifacts/final_checkpoint.json': '123f14c8ce64b99268702a64f3d9ef20235fa196',
                   'collected/input/source.zip': PACKAGE_BLOBS['source.zip']}
FINAL_PT_WEIGHTS = 'collected/results/artifacts/final.pt'
INVENTORY_RECORD = 'collected_inventory.json'
MANIFEST_RECORD = 'collected/results/artifacts/manifest.json'
CHECKPOINT_RECORD = 'collected/results/artifacts/final_checkpoint.json'
INVENTORY_PATHS = {MANIFEST_RECORD: 'results/artifacts/manifest.json',
                   CHECKPOINT_RECORD: 'results/artifacts/final_checkpoint.json',
                   FINAL_PT_WEIGHTS: 'results/artifacts/final.pt'}

# =====================================================================================================================
# THE POLICY TO IMPLEMENT (Codex, commit bc46b36e). Every file is pinned by blob id, sha256 and size. The sha256
# values equal the ones `LAUNCH_REQUEST.json` itself pins (checked by `launch_request_violations`).
# =====================================================================================================================
POLICY_COMMIT = 'bc46b36e60d904248fee03e5d7212f0eb5886c38'
POLICY_BRANCH = 'codex/helm-controlled-prelaunch-20260924'
POLICY_TRACKING_REF = 'refs/remotes/origin/' + POLICY_BRANCH
POLICY_FETCH_ARGS = ('fetch', 'origin', POLICY_BRANCH + ':' + POLICY_TRACKING_REF)   # explicit refspec, never a pull
POLICY_FETCH = 'git ' + ' '.join(POLICY_FETCH_ARGS)
PRELAUNCH = 'records/helm_controlled_prelaunch_20260924/'
HANDOFF = '_handoffs/HELM_NEXT_PHASE_20260923/'
POLICY_FILES = {   # name: (ROOT-relative path, git blob, sha256, bytes)
    'reproduction_policy_json': (PRELAUNCH + 'REPRODUCTION_POLICY.json', 'b8d7eb07594288f2120a3745656bf33c148acfb8',
                                 '13eee0490ce568cd7d012989c5a3bf59af0abb3c3e650370a0af2f8351cc9259', 1785),
    'reproduction_policy_md': (PRELAUNCH + 'REPRODUCTION_POLICY.md', '8106bce5063b09212189bd871ee138b52518e922',
                               '92a69981e4960d5ad30b9be127d8f9879c18f59cf5a40a55299ea5d679ac770e', 8257),
    'execution_manifest': (PRELAUNCH + 'EXECUTION_MANIFEST.json', '8c356375338617063e2c092176be41951bdc7e6e',
                           'a321e3221335db55a359962f3f800f6bfd1b0e8d46876cc7fec8350cfd366628', 53477),
    'launch_request': (PRELAUNCH + 'LAUNCH_REQUEST.json', 'f702090ae1c9138d7f13d1d70dd73cba3df90722',
                       'f2e789bb7798578896f7adb56cc70ff6d95209106861e1bc432504fb02f564d4', 6448),
    'statistical_policy': (PRELAUNCH + 'STATISTICAL_POLICY.json', '7582843f7b8ab015edab45fe5019bd6f5f52c4ea',
                           '46e564a6323c16f5c4cdf96211cc4475d342ece20d8975ed2061cdfd3d0aa055', 4938),
    'route_and_checkpoint_protocol': (PRELAUNCH + 'ROUTE_AND_CHECKPOINT_PROTOCOL.md',
                                      '16a4fb07ee6ffac5ccf9532ba5f4437a58d7c671',
                                      '8d6c469b5c2357becf9a7f930fc53cebce57d39de93608ba233cb6635b0efc07', 13128),
    'plan': (HANDOFF + 'PLAN_HELM_REPAIR_CONTROLLED_1_DRAFT.md', '2462d1589fb8b5704402c65a0b841029dc1845f3',
             '2b840818952cb7ed44b1efbf7b2f4518d596340b975eb75f5d4ea4fbc97d4753', 21058),
    'codex_amendments': (HANDOFF + 'CODEX_AMENDMENTS_20260924.md', '8841955f726766baa742226b445d957d4cc66c27',
                         '4541ddbccff7804e0fce13f76b1d3e61d8e30fdca431b4df106644ce6410f9c9', 17403),
}
# LAUNCH_REQUEST.json's own names for the files it pins, mapped to POLICY_FILES names.
LAUNCH_REQUEST_POLICY_NAMES = {'REPRODUCTION_POLICY.md': 'reproduction_policy_md',
                               'REPRODUCTION_POLICY.json': 'reproduction_policy_json',
                               'STATISTICAL_POLICY.json': 'statistical_policy',
                               'EXECUTION_MANIFEST.json': 'execution_manifest',
                               'ROUTE_AND_CHECKPOINT_PROTOCOL.md': 'route_and_checkpoint_protocol'}
LAUNCH_REQUEST_DOCUMENT_NAMES = {HANDOFF + 'PLAN_HELM_REPAIR_CONTROLLED_1_DRAFT.md': 'plan',
                                 HANDOFF + 'CODEX_AMENDMENTS_20260924.md': 'codex_amendments'}

# ---- labels, spelled exactly as REPRODUCTION_POLICY.json and REPRODUCTION_POLICY.md spell them.
REPRODUCED = 'STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED'
DOES_NOT_REPRODUCE = 'DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY'
INVALID_STOP = 'ADMISSION_INVALID_STOP'
VERDICTS = (REPRODUCED, DOES_NOT_REPRODUCE, INVALID_STOP)
COMPARISON_INCOMPLETE = 'COMPARISON_INCOMPLETE'      # a NEXT-STEP label (fallback not affordable), never a verdict
LEVEL_LABELS = {'file': ('FILE_IDENTICAL', 'FILE_DIFFERENT'),
                'learned_state': ('LEARNED_STATE_IDENTICAL', 'LEARNED_STATE_DIFFERENT'),
                'output': ('OUTPUT_REPRODUCED', 'OUTPUT_DIFFERENT'),
                'continuation': ('CONTINUATION_IDENTICAL', 'CONTINUATION_DIFFERENT')}
LEVEL_NOT_ESTABLISHED = 'NOT_ESTABLISHED'
DECIDING_LEVELS = ('learned_state', 'output')          # plus evidence validity; `file` and `continuation` never decide

# ---- the rule the reader implements, machine-readable. `policy_conformance` compares it field by field with the
# pinned REPRODUCTION_POLICY.json, so a changed policy stops every tool until the reader is conformed again.
READER_RULE = {
    'schema': 'helm.controlled.reproduction-policy/1',
    'historical_source': SOURCE_SHA,
    'reproduction_seed': MODEL_SEED,
    'file_hash_preserved': True,
    'learned_state_tolerance': 0,
    'required_for_C': ['artifact_and_environment_admission_valid', 'complete_learned_state_identical',
                       'complete_registered_output_panel_identical'],
    'continuation_identity_reported_separately': True,
    'file_mismatch_alone_triggers_fallback': False,
    'missing_or_invalid_evidence': INVALID_STOP,
    'valid_state_or_output_mismatch': DOES_NOT_REPRODUCE,
    'fallback_requires_frozen_plan_valid_mismatch_and_headroom': True,
}
# The policy's freeze fields: null in the pinned policy today, so the execution admission cannot be ADMITTED.
POLICY_FREEZE_FIELDS = ('output_panel_manifest_sha256', 'reader_source_sha256', 'reader_acceptance_receipt_sha256')

# =====================================================================================================================
# THE PINNED PUBLIC PANEL (policy "Output panel" row). Built by `build_panel_manifest.py` from committed JSON only.
# =====================================================================================================================
PANEL_MANIFEST_NAME = 'public_panel_manifest.json'
PANEL_MANIFEST_REL = HERE_REL + '/' + PANEL_MANIFEST_NAME
PANEL_MANIFEST_SHA256 = 'a27b3839f6fe5cb07d498c591395a30f06725a1ea0ee5882dcccbb1c2647c3e2'
PANEL_MANIFEST_BYTES = 442201
PANEL_MANIFEST_SCHEMA = 'cncm.helm-unchanged-reproduction-public-panel/1'
PANEL_RECORD_COUNT = 564
PANEL_RECORD_IDS_SHA256 = 'a2ec9f740ce0764b124d48cd9ceea7ceca1f342628256e5e8dc30c8a1f85da52'
PANEL_DECIDING_FIELDS = ('record_id', 'status', 'answer_sha256', 'decisions_sha256', 'grader_correct',
                         'grader_check_sha256')
PANEL_STATUSES = ('ANSWERED', 'REFUSED', 'ERROR')
GRADER_EXCLUDED_KEYS = ('record_id', 'prediction_id')
PREDICTION_DEPTH = 8
# The route both checkpoints run through (policy: "inference mode" is predictive configuration and must match): the
# pinned historical loader, then `PointerCourseLearner.predict` (module.eval() and torch.no_grad(), depth 8).
INFERENCE_MODE = {'module_training': False, 'no_grad': True, 'prediction_depth': PREDICTION_DEPTH,
                  'entry': 'PointerCourseLearner.predict'}

# =====================================================================================================================
# THE NUMERICAL ENVIRONMENT (policy: "numerical environment" must be validated; manifest `dependencies`). Each value is
# what the Helm 2.0 seed-17 run itself recorded or set (worker_report.json `runtime` at c8d5c430; the worker's
# `_preflight` at 20208c92; requirements-gpu.txt at 20208c92). The full lock (driver, cuDNN, Python, AMI) is NOT
# frozen in the manifest (`NOT_READY_FULL_ENVIRONMENT_NOT_FROZEN`); those are recorded by the evidence, not pinned.
# =====================================================================================================================
NUMERICAL_ENVIRONMENT = {
    'platform_system': 'Linux',
    'device': 'cuda:0',
    'visible_gpu_count': 1,
    'torch_version': '2.11.0+cu128',
    'cuda_version': '12.8',
    'gpu_name': 'NVIDIA RTX PRO 4500 Blackwell Server Edition',
    'numpy_version': '2.2.6',
    'deterministic_algorithms': True,
    'matmul_allow_tf32': False,
    'cudnn_allow_tf32': False,
    'cublas_workspace_config': ':4096:8',
}
ENVIRONMENT_RECORDED_NOT_PINNED = ('python_version', 'cudnn_version', 'driver_version', 'platform_release')
HISTORICAL_AMI = 'ami-0fbbd0facbc9e3cff'            # the Helm 2.0 run's preflight AMI (result.json at c8d5c430)
REQUIREMENTS_GPU_SHA256 = '9d0be7810014ec3a58a112dc0024a74060400dc841523abd405e5fb579179379'

# =====================================================================================================================
# THE CHECKPOINT'S OWN FIELDS (pointer_learner.py at 20208c92: CHECKPOINT_SCHEMA, METADATA_FIELDS, RUN_IDENTITY_FIELDS,
# INIT_ARGS_FIELDS) and how the policy classifies each one. Every field is in exactly one class.
# =====================================================================================================================
CHECKPOINT_SCHEMA = 'cncm.typed-pointer-checkpoint/0.1'
PAYLOAD_KEYS = ('encoder_state', 'metadata', 'model_state', 'optimizer_state', 'rng_state', 'schema')
STATE_PARTS = ('model_state', 'encoder_state', 'optimizer_state', 'rng_state')
LEARNED_STATE_PARTS = ('model_state', 'encoder_state')        # policy: tensors/buffers + encoder/vocabulary state
CONTINUATION_PARTS = ('optimizer_state', 'rng_state')         # policy: optimizer tensors/scalars, every RNG stream
METADATA_FIELDS = ('run_identity', 'run_identity_digest', 'model_revision', 'cursor', 'counters', 'elapsed_seconds',
                   'training_mode', 'model_state_identity', 'optimizer_state_identity', 'encoder_state_identity',
                   'rng_state_identity', 'init_args', 'learnable_names')
RUN_IDENTITY_FIELDS = ('context', 'learner_profile', 'encoder_identity', 'initial_model_identity', 'scope',
                       'optimizer_config', 'limits', 'initialization', 'core_rounds', 'readout', 'head_set',
                       'counters', 'counter_units', 'depth_is_not_an_input', 'prediction_depth',
                       'normalisation_placement', 'round_parameters_shared', 'dense_and_one_hot_only',
                       'scored_fields', 'measured_pooling', 'measured_stability')
INIT_ARGS_FIELDS = ('optimizer_config', 'run_context', 'limits', 'device', 'python_seed', 'root')
CONTEXT_FIELDS = ('run_id', 'course_sha256', 'condition', 'source_seed')
# Predictive configuration (policy: "architecture, switch state, number of rounds, encoder/vocabulary mapping,
# normalization settings and inference mode ... must match"): part of LEARNED-STATE identity.
PREDICTIVE_RUN_IDENTITY = ('learner_profile', 'encoder_identity', 'core_rounds', 'readout', 'head_set',
                           'prediction_depth', 'normalisation_placement', 'round_parameters_shared',
                           'dense_and_one_hot_only', 'scored_fields', 'depth_is_not_an_input')
PREDICTIVE_METADATA = ('learnable_names',)
# Training configuration (policy: "Training-configuration or software differences ... fail the environment-admission
# check"): a difference makes the evidence INVALID, never a mismatch.
TRAINING_RUN_IDENTITY = ('optimizer_config', 'initialization', 'scope', 'counters', 'counter_units',
                         'measured_pooling', 'measured_stability')
TRAINING_CONTEXT = ('course_sha256', 'condition', 'source_seed')
TRAINING_INIT_ARGS = ('optimizer_config', 'python_seed', 'device')
# Continuation (policy: "cursor/model revision and training counters"; plus the starting-state identity).
CONTINUATION_METADATA = ('cursor', 'model_revision', 'counters', 'training_mode')
CONTINUATION_RUN_IDENTITY = ('initial_model_identity',)
# Envelope (policy: "file path, root, elapsed time, storage/container layout, run identifier and administrative
# limits"): excluded from every identity, retained and reported. `run_identity_digest` is derived from run_identity,
# which carries the run identifier and the limits.
ENVELOPE_METADATA = ('elapsed_seconds', 'run_identity_digest')
ENVELOPE_RUN_IDENTITY = ('limits',)
ENVELOPE_INIT_ARGS = ('limits', 'root')
PRODUCER_IDENTITY_FIELDS = ('model_state_identity', 'optimizer_state_identity', 'encoder_state_identity',
                            'rng_state_identity')
TENSOR_DECIDING_KEYS = ('kind', 'dtype', 'shape', 'layout', 'sha256')    # stride / offset / device are envelope

# ---- the evidence the torch-side module writes on AWS, and the reader-acceptance receipt it writes in P1.
EVIDENCE_SCHEMA = 'cncm.helm-unchanged-reproduction-evidence/1'
ACCEPTANCE_SCHEMA = 'cncm.helm-unchanged-reproduction-reader-acceptance/1'
EVIDENCE_REL = 'records/typed_pointer_001/evidence_unchanged_repro_20260917/reproduction_evidence.json'
EVIDENCE_MODES = ('READING', 'ACCEPTANCE')
READER_SOURCE_FILES = ('read_reproduction.py', 'repro_common.py', 'recompute_reproduction_evidence.py')

# =====================================================================================================================
# OWNER AUTHORIZATION (machine-readable, bound by git blob ids). Nothing here parses prose for approval words.
# =====================================================================================================================
OWNER_AUTHORIZED = 'STANDING_PROJECT_AUTHORIZATION'
OWNER_NOT_ESTABLISHED = 'OWNER_AUTHORIZATION_NOT_ESTABLISHED'
CLAUDE_OWNER_COMMIT = 'ca68690b93db9305ea5839f7308144ce6e0b7cab'
CLAUDE_OWNER_BRANCH = 'research/helm-integration-20260923'
OWNER_RECORDS = {   # name: (commit, ROOT-relative path, git blob, sha256)
    'codex_standing_json': (POLICY_COMMIT, PRELAUNCH + 'OWNER_STANDING_AUTHORIZATION_20260924.json',
                            '10069e00869439fdbf58760b5ea712b16c652f18',
                            '7a2153567c201aa7163e1dc287a29e00568b8927e5c05f8575c8934abb601fd3'),
    'codex_standing_md': (POLICY_COMMIT, PRELAUNCH + 'OWNER_STANDING_AUTHORIZATION_20260924.md',
                          'e6cfe5b99c039ba21ac6ff68394f3648cfee8e5e',
                          '86d7f14b9a191bb90733d011c8c5d1344a29739498be9c2e48c4e3084fd10687'),
    'claude_extension_md': (CLAUDE_OWNER_COMMIT, HANDOFF + 'OWNER_STANDING_AUTHORIZATION_CLAUDE_20260924.md',
                            'f707ce455c08e51c5ce18ae5114a7d5b530a9f82',
                            '3360eefcf48af6b72b7d807d7e38928ac302353bb21afa398d25b259ba79988e'),
}
OWNER_QUOTES = {   # the owner's own words, verbatim, each pinned by sha256
    'standing_authorization': (
        'DO YOU NEED MY APPROVAL FOR ANYTHING? IF SO I HEREBY GRANT YOU IN ADVANCE ALL FUTURE AND CURRENT APPROVAL '
        'FOR THIS PROJECT', '3baf81c065ec7d7d8d4c28f0ea6dc91207fb58979991cf28769efa46874b95d1'),
    'extends_to_claude_as_runner': (
        'YES IT ABSOLUTELY DOES EXTEND TO THE SAME APPROVAL',
        'aeefbfc8c72d6688d32cb803926553c6085367f59d7551e61254573c0bbfb34a'),
}
# The fields of Codex's machine-readable owner record that must hold exactly (type AND value).
OWNER_JSON_REQUIRED = {'schema': 'helm.owner-standing-authorization/1', 'status': OWNER_AUTHORIZED,
                       'owner_instruction_verbatim': OWNER_QUOTES['standing_authorization'][0],
                       'further_owner_approval_required_for_in_scope_work': False, 'study_option': 'C',
                       'study_actual_spend_ceiling_usd': 60, 'execution_owner': 'Claude'}

# =====================================================================================================================
# EXECUTION ADMISSION (machine-readable technical readiness for THIS job). Separate from owner authorization.
# =====================================================================================================================
ADMISSION_NAME = 'EXECUTION_ADMISSION.json'
ADMISSION_REL = HERE_REL + '/' + ADMISSION_NAME
ADMISSION_PATH = HERE / ADMISSION_NAME
ADMISSION_SCHEMA = 'cncm.helm-unchanged-reproduction-execution-admission/1'
ADMITTED, NOT_READY = 'ADMITTED', 'NOT_READY'
ADMISSION_STATES = (NOT_READY, ADMITTED)
ADMISSION_FIELDS = ('schema', 'label', 'state', 'job_kind', 'model_seed', 'source_sha', 'job', 'owner_authorization',
                    'bindings', 'prerequisites', 'admitted_by', 'admitted_utc', 'note')
REQUIRED_PREREQUISITES = (
    'reader_acceptance_on_aws_p1',                     # recompute_reproduction_evidence.py --mode acceptance, PASS
    'reproduction_policy_frozen_with_panel_and_reader',  # policy JSON names this panel and this reader source
    'numerical_environment_frozen',                    # full lock: driver, cuDNN, Python, AMI (manifest NOT_READY)
    'final_launch_packet_frozen',                      # EXECUTION_MANIFEST final_freeze.frozen_launch_packet_sha256
    'budget_headroom_verified',                        # measured spend so far + $15.00 <= $60.00, from a record
    'fresh_review_of_this_revision',                   # a fresh reviewer's verdict on this exact revision
)
PREREQUISITE_PASS = 'PASS'

# ---- the spend gate for --check (plan section 0 as carried by the amended plan): spend so far + per-job <= ceiling.
CEILING_USD = '60.00'
PER_JOB_USD = '15.00'

# ---- outputs. The writer writes ONE folder (`frozen/`, via `frozen.partial/`); the reader may write ONE file.
OUTPUT = HERE / 'frozen'
READING = HERE / 'reproduction_reading.json'
RECEIPT_REL = 'records/typed_pointer_001/receipt_unchanged_repro_20260917'
RECEIPT_DIR = ROOT / RECEIPT_REL

# ---- the tree rule. Relative to ROOT. HEAD may differ from SOURCE_SHA ONLY by ADDED files under these prefixes.
ALLOWED_ADDED_PREFIXES = (HERE_REL + '/', PACKAGE_REL + '/')
INVENTORY_TREES = ('cncm/', 'research/CAS_META_2_COMPOSITION/cas_meta2/', 'research/CAS_META_2_COMPOSITION/aws/',
                   'research/CAS_META_2_COMPOSITION/requirements-gpu.txt', 'records/typed_course_001/',
                   'records/typed_interface_001/', 'records/typed_matched_001/', 'records/typed_practice_001/',
                   'research/CAS_CJT_TRANSFORMER_v0_2/')
TOLERATED_UNTRACKED = (HERE_REL + '/frozen/', HERE_REL + '/reproduction_reading.json')


def make_stop(prefix):
    """An explicit stop, never an `assert` (which `python -O` removes)."""
    def stop_unless(condition, reason):
        if not condition:
            raise SystemExit(prefix + reason)
    return stop_unless


def digest(raw):
    return sha256(raw).hexdigest()


def git_object_id(raw):
    """Git's own blob id for these bytes (SHA-1 over `blob <len>\\0<content>`)."""
    return sha1(b'blob %d\0' % len(raw) + raw).hexdigest()


def is_hex(value, length):
    return type(value) is str and len(value) == length and all(ch in '0123456789abcdef' for ch in value)


def same(left, right):
    """Exact equality, type included, all the way down: True is not 1, 60 is not 60.0, a list is not a tuple."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(same(left[key], right[key]) for key in left)
    if type(left) in (list, tuple):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def canonical(value):
    """The launcher's canonical JSON form (`graph_training_curriculum_launch.canonical`), for launcher-free code."""
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
            + '\n').encode('utf-8')


def value_digest(value):
    return digest(canonical(value))


def git(*args, cwd=None):
    return subprocess.run(['git', '-c', 'core.autocrlf=false', *args], cwd=str(cwd or ROOT), check=True,
                          capture_output=True, timeout=120).stdout


def git_ok(*args, cwd=None):
    """True when the git command exits 0 (yes/no questions such as `merge-base --is-ancestor`)."""
    return subprocess.run(['git', '-c', 'core.autocrlf=false', *args], cwd=str(cwd or ROOT), capture_output=True,
                          timeout=120).returncode == 0


def repo_path(relative):
    return GIT_PREFIX + relative


def has_object(commit, relative):
    return git_ok('cat-file', '-e', commit + ':' + repo_path(relative))


def blob_id(commit, relative):
    return git('rev-parse', commit + ':' + repo_path(relative)).decode('ascii').strip()


def show(commit, relative):
    return git('show', commit + ':' + repo_path(relative))


# ---------------------------------------------------------------------------------------------------------------------
# Labels.
# ---------------------------------------------------------------------------------------------------------------------
def level_label(level, value):
    """`True` -> the identical/reproduced word, `False` -> the different word, anything else -> NOT_ESTABLISHED."""
    if value is True:
        return LEVEL_LABELS[level][0]
    if value is False:
        return LEVEL_LABELS[level][1]
    return LEVEL_NOT_ESTABLISHED


def level_labels(levels):
    return {level: level_label(level, levels.get(level)) for level in LEVEL_LABELS}


# ---------------------------------------------------------------------------------------------------------------------
# Sources, panel, environment.
# ---------------------------------------------------------------------------------------------------------------------
def source_hashes(folder=None):
    """sha256 of each reader source file, as it sits on disk next to this module."""
    folder = HERE if folder is None else Path(folder)
    return {name: digest((folder / name).read_bytes()) for name in READER_SOURCE_FILES}


def reader_source_digest(hashes=None):
    """ONE sha256 for the independent reader: over the canonical {file: sha256} of the three reader sources."""
    return value_digest(source_hashes() if hashes is None else hashes)


def environment_digest():
    return value_digest(NUMERICAL_ENVIRONMENT)


def environment_violations(recorded):
    """Every pinned environment key the recorded environment does not match exactly (type included)."""
    recorded = recorded if type(recorded) is dict else {}
    return [key for key, value in NUMERICAL_ENVIRONMENT.items() if key not in recorded
            or not same(recorded[key], value)]


def panel_manifest_violations(raw):
    """Every way these bytes are not the pinned panel manifest. Pure."""
    if type(raw) is not bytes:
        return ['PANEL_MANIFEST_ABSENT']
    violations = []
    if digest(raw) != PANEL_MANIFEST_SHA256 or len(raw) != PANEL_MANIFEST_BYTES:
        violations.append('PANEL_MANIFEST_SHA256:' + digest(raw))
    try:
        manifest = json.loads(raw)
    except ValueError:
        return violations + ['PANEL_MANIFEST_UNREADABLE']
    if type(manifest) is not dict or manifest.get('schema') != PANEL_MANIFEST_SCHEMA:
        return violations + ['PANEL_MANIFEST_SCHEMA']
    ids = manifest.get('record_ids')
    if type(ids) is not list or len(ids) != PANEL_RECORD_COUNT or value_digest(ids) != PANEL_RECORD_IDS_SHA256:
        violations.append('PANEL_RECORD_IDS')
    rows = manifest.get('rows')
    if type(rows) is not list or [row.get('record_id') if type(row) is dict else None for row in rows] != ids:
        violations.append('PANEL_ROWS')
    if manifest.get('registered_expected_refusals') != [] or manifest.get('hset2_material_used') is not False:
        violations.append('PANEL_SCOPE')
    return violations


def load_panel_manifest(stop, raw=None):
    raw = (HERE / PANEL_MANIFEST_NAME).read_bytes() if raw is None else raw
    violations = panel_manifest_violations(raw)
    stop(not violations, 'PANEL_MANIFEST_IS_NOT_THE_PINNED_ONE:' + '|'.join(violations))
    return json.loads(raw)


# ---------------------------------------------------------------------------------------------------------------------
# The policy (Codex, bc46b36e): pins, conformance, currency at the fetched branch tip.
# ---------------------------------------------------------------------------------------------------------------------
def policy_pointers():
    return {'commit': POLICY_COMMIT, 'branch': POLICY_BRANCH,
            'files': {name: {'path': GIT_PREFIX + relative, 'blob': blob, 'sha256': sha, 'bytes': size}
                      for name, (relative, blob, sha, size) in POLICY_FILES.items()}}


def policy_conformance(policy):
    """Every deciding field of REPRODUCTION_POLICY.json that is not exactly the rule the reader implements. Pure."""
    if type(policy) is not dict:
        return ['POLICY_NOT_AN_OBJECT']
    return ['POLICY_FIELD:' + key for key, value in READER_RULE.items() if key not in policy
            or not same(policy[key], value)]


def launch_request_violations(request):
    """LAUNCH_REQUEST.json must pin exactly the policy files and documents pinned here. Pure."""
    if type(request) is not dict:
        return ['LAUNCH_REQUEST_NOT_AN_OBJECT']
    violations = []
    pinned = request.get('policy_file_sha256') if type(request.get('policy_file_sha256')) is dict else {}
    for label, name in LAUNCH_REQUEST_POLICY_NAMES.items():
        if pinned.get(label) != POLICY_FILES[name][2]:
            violations.append('LAUNCH_REQUEST_POLICY_PIN:' + label)
    for label, name in (('OWNER_STANDING_AUTHORIZATION_20260924.json', 'codex_standing_json'),
                        ('OWNER_STANDING_AUTHORIZATION_20260924.md', 'codex_standing_md')):
        if pinned.get(label) != OWNER_RECORDS[name][3]:
            violations.append('LAUNCH_REQUEST_OWNER_PIN:' + label)
    documents = request.get('preparation_document_sha256')
    documents = documents if type(documents) is dict else {}
    for label, name in LAUNCH_REQUEST_DOCUMENT_NAMES.items():
        if documents.get(label) != POLICY_FILES[name][2]:
            violations.append('LAUNCH_REQUEST_DOCUMENT_PIN:' + label)
    return violations


def read_policy_files(stop):
    """Every pinned policy file, read with `git show <POLICY_COMMIT>:<path>` (never a working copy), fully checked."""
    files = {}
    for name, (relative, blob, sha, size) in POLICY_FILES.items():
        try:
            found = blob_id(POLICY_COMMIT, relative)
            raw = show(POLICY_COMMIT, relative)
        except subprocess.CalledProcessError:
            stop(False, 'POLICY_OBJECT_MISSING:' + name + ':run `' + POLICY_FETCH + '` (do not check it out)')
        stop(found == blob and git_object_id(raw) == blob, 'POLICY_FILE_BLOB:' + name + ':' + found)
        stop(digest(raw) == sha and len(raw) == size, 'POLICY_FILE_SHA256:' + name + ':' + digest(raw))
        files[name] = raw
    return files


def policy_tip_violations(tip):
    """Every pinned file that moved at the fetched branch tip, or a tip that does not contain the pinned commit. Pure."""
    violations = []
    if type(tip) is not dict or tip.get('commit') is None:
        return ['POLICY_TRACKING_REF_MISSING:' + POLICY_TRACKING_REF]
    blobs = tip.get('blobs') if type(tip.get('blobs')) is dict else {}
    for name, (_, blob, _, _) in POLICY_FILES.items():
        if blobs.get(name) != blob:
            violations.append('MOVED_AT_TIP:' + name + ':' + str(blobs.get(name)))
    if tip.get('pinned_commit_is_ancestor') is not True:
        violations.append('PINNED_COMMIT_NOT_IN_TIP')
    return violations


def read_policy_tip(stop, *, fetch):
    """Fetch the policy branch (explicit refspec), then read the blob of every pinned file at its tip."""
    if fetch:
        try:
            git(*POLICY_FETCH_ARGS)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            stop(False, 'POLICY_TIP_NOT_FETCHED:run `' + POLICY_FETCH + '` by hand; if it fails, stop')
    if not git_ok('rev-parse', '--verify', '--quiet', POLICY_TRACKING_REF + '^{commit}'):
        return {'ref': POLICY_TRACKING_REF, 'commit': None, 'blobs': {}, 'pinned_commit_is_ancestor': False}
    commit = git('rev-parse', POLICY_TRACKING_REF + '^{commit}').decode('ascii').strip()
    blobs = {name: blob_id(commit, relative) if has_object(commit, relative) else None
             for name, (relative, _, _, _) in POLICY_FILES.items()}
    return {'ref': POLICY_TRACKING_REF, 'commit': commit, 'blobs': blobs,
            'pinned_commit_is_ancestor': git_ok('merge-base', '--is-ancestor', POLICY_COMMIT, commit)}


def check_policy(stop, *, fetch=True, require_current=True):
    """STOP unless the pinned policy files are intact, conformed and consistent with LAUNCH_REQUEST.

    Currency at the fetched branch tip STOPS only when `require_current` (the --write and --check paths). Policy:
    "A changed plan invalidates affected technical admission evidence" -- the admission, not preparation -- so the
    preparation-only path reports a moved tip and carries on.
    """
    files = read_policy_files(stop)
    loaded = {name: json.loads(files[name]) for name in ('reproduction_policy_json', 'execution_manifest',
                                                         'launch_request')}
    violations = (policy_conformance(loaded['reproduction_policy_json'])
                  + launch_request_violations(loaded['launch_request']))
    stop(not violations, 'POLICY_IS_NOT_THE_RULE_THE_READER_IMPLEMENTS:' + '|'.join(violations)[:1500])
    tip = read_policy_tip(stop, fetch=fetch)
    moved = policy_tip_violations(tip)
    if require_current:
        stop(not moved, 'POLICY_OR_PLAN_MOVED:' + '|'.join(moved)[:1500] + ':a changed plan or policy invalidates '
             'the technical admission; re-pin POLICY_COMMIT and POLICY_FILES after review')
    return {'pointers': policy_pointers(), 'policy': loaded['reproduction_policy_json'],
            'manifest': loaded['execution_manifest'], 'launch_request': loaded['launch_request'],
            'tip': {'ref': tip['ref'], 'commit': tip['commit'], 'violations': moved}}


def policy_freeze_violations(policy, manifest, launch_request, bindings, prerequisites):
    """Machine-readable readiness fields of the pinned policy files. Any violation keeps the admission NOT_READY. Pure.

    These are booleans and hashes written by Codex's records, never prose. Today every one of them fails: the pinned
    policy has null panel/reader/acceptance hashes and the manifest and launch request say launch_enabled=false.
    """
    violations = []
    policy = policy if type(policy) is dict else {}
    manifest = manifest if type(manifest) is dict else {}
    launch_request = launch_request if type(launch_request) is dict else {}
    prerequisites = prerequisites if type(prerequisites) is dict else {}
    if policy.get('output_panel_manifest_sha256') != PANEL_MANIFEST_SHA256:
        violations.append('POLICY_PANEL_MANIFEST_NOT_FROZEN_TO_THIS_PANEL')
    if policy.get('reader_source_sha256') != (bindings or {}).get('reader_source_sha256'):
        violations.append('POLICY_READER_SOURCE_NOT_FROZEN_TO_THIS_READER')
    acceptance = (prerequisites.get('reader_acceptance_on_aws_p1') or {})
    if not is_hex(policy.get('reader_acceptance_receipt_sha256'), 64) or policy.get(
            'reader_acceptance_receipt_sha256') != (acceptance if type(acceptance) is dict else {}).get(
            'receipt_sha256'):
        violations.append('POLICY_READER_ACCEPTANCE_RECEIPT_NOT_FROZEN')
    if policy.get('main_launch_ready') is not True:
        violations.append('POLICY_MAIN_LAUNCH_READY_IS_NOT_TRUE')
    freeze = manifest.get('final_freeze') if type(manifest.get('final_freeze')) is dict else {}
    packet = (prerequisites.get('final_launch_packet_frozen') or {})
    if not is_hex(freeze.get('frozen_launch_packet_sha256'), 64) or freeze.get('frozen_launch_packet_sha256') != (
            packet if type(packet) is dict else {}).get('receipt_sha256'):
        violations.append('MANIFEST_LAUNCH_PACKET_NOT_FROZEN')
    if manifest.get('launch_enabled') is not True:
        violations.append('MANIFEST_LAUNCH_ENABLED_IS_NOT_TRUE')
    if launch_request.get('launch_enabled') is not True:
        violations.append('LAUNCH_REQUEST_LAUNCH_ENABLED_IS_NOT_TRUE')
    return violations


# ---------------------------------------------------------------------------------------------------------------------
# State 1: owner authorization. Machine-readable fields and verbatim quotes of blob-bound records. Pure evaluation.
# ---------------------------------------------------------------------------------------------------------------------
def read_owner_records():
    """`{name: {'blob': ..., 'raw': ...} | None}` from git at the pinned commits. Absent objects are None, not a stop."""
    records = {}
    for name, (commit, relative, _, _) in OWNER_RECORDS.items():
        if not has_object(commit, relative):
            records[name] = None
            continue
        records[name] = {'blob': blob_id(commit, relative), 'raw': show(commit, relative)}
    return records


def owner_authorization_state(records):
    """`{'state', 'reasons', 'records'}`. STANDING_PROJECT_AUTHORIZATION only when every check below holds.

    It never searches prose for an approval word. It checks: each record's git blob id and sha256 against its pin; the
    exact machine fields of Codex's JSON record (type and value); and that the owner's two verbatim quotes are the
    pinned bytes (the standing grant equals the JSON field; the extension to Claude occurs exactly once in Claude's
    record). A prose file that merely says "approved" can therefore never produce the state.
    """
    reasons = []
    records = records if type(records) is dict else {}
    for name, (words, pinned) in OWNER_QUOTES.items():
        if digest(words.encode('utf-8')) != pinned:
            reasons.append('OWNER_QUOTE_EDITED:' + name)
    raws = {}
    for name, (_, _, blob, sha) in OWNER_RECORDS.items():
        record = records.get(name)
        raw = record.get('raw') if type(record) is dict else None
        if type(raw) is not bytes:
            reasons.append('OWNER_RECORD_MISSING:' + name)
            continue
        if record.get('blob') != blob or git_object_id(raw) != blob:
            reasons.append('OWNER_RECORD_BLOB:' + name)
        if digest(raw) != sha:
            reasons.append('OWNER_RECORD_SHA256:' + name)
        raws[name] = raw
    if 'codex_standing_json' in raws:
        try:
            parsed = json.loads(raws['codex_standing_json'])
        except ValueError:
            parsed = None
        if type(parsed) is not dict:
            reasons.append('OWNER_JSON_UNREADABLE')
        else:
            reasons.extend('OWNER_JSON_FIELD:' + key for key, value in OWNER_JSON_REQUIRED.items()
                           if key not in parsed or not same(parsed[key], value))
    if 'claude_extension_md' in raws:
        text = raws['claude_extension_md'].decode('utf-8', 'replace')
        if text.count(OWNER_QUOTES['extends_to_claude_as_runner'][0]) != 1:
            reasons.append('OWNER_EXTENSION_QUOTE_NOT_EXACTLY_ONCE')
    return {'state': OWNER_NOT_ESTABLISHED if reasons else OWNER_AUTHORIZED, 'reasons': reasons,
            'records': {name: {'commit': commit, 'path': GIT_PREFIX + relative, 'blob': blob, 'sha256': sha}
                        for name, (commit, relative, blob, sha) in OWNER_RECORDS.items()}}


# ---------------------------------------------------------------------------------------------------------------------
# State 2: execution admission. A JSON record bound to exact hashes; ADMITTED only if everything holds. Pure evaluation.
# ---------------------------------------------------------------------------------------------------------------------
def expected_admission_bindings(hashes=None):
    """The exact hashes an admission record must carry for THIS revision of THIS folder."""
    hashes = source_hashes() if hashes is None else hashes
    return {'policy_commit': POLICY_COMMIT,
            'policy_files_sha256': {name: pin[2] for name, pin in POLICY_FILES.items()},
            'owner_records_blob': {name: pin[2] for name, pin in OWNER_RECORDS.items()},
            'panel_manifest_sha256': PANEL_MANIFEST_SHA256,
            'numerical_environment_sha256': environment_digest(),
            'reader_rule_sha256': value_digest(READER_RULE),
            'reader_sources_sha256': dict(hashes),
            'reader_source_sha256': reader_source_digest(hashes),
            'reference_final_pt_sha256': REFERENCE_FINAL_PT_SHA256,
            'package_archive_sha256': ARCHIVE_SHA256,
            'source_sha': SOURCE_SHA, 'model_seed': MODEL_SEED, 'job_kind': JOB_KIND}


def execution_admission_state(raw, *, expected_bindings, owner_state, policy, manifest, launch_request,
                              committed, job=None):
    """`{'state', 'recorded_state', 'reasons', 'record_sha256', 'job'}`. ADMITTED only when ALL of these hold:

      * the record is JSON with exactly ADMISSION_FIELDS, the pinned schema and label;
      * its `state` is the word ADMITTED (any other word, including an approval word from prose, is NOT_READY);
      * it is for this job kind, seed and source; its `job` has this admission's form and, when `job` is given, equals it;
      * its owner_authorization names STANDING_PROJECT_AUTHORIZATION and the pinned owner-record blobs, AND the owner
        records themselves evaluate to that state now (`owner_state`);
      * its bindings equal `expected_bindings` exactly (plan, policy, manifest, panel, environment, reader sources);
      * every REQUIRED_PREREQUISITES entry is PASS with a 64-hex receipt sha256;
      * the pinned policy files' own machine-readable readiness fields agree (`policy_freeze_violations`);
      * the record is committed as is (`committed`), so it is a recorded fact, not a local edit.
    """
    reasons = []
    try:
        record = json.loads(raw) if type(raw) is bytes else None
    except ValueError:
        record = None
    if type(record) is not dict:
        return {'state': NOT_READY, 'recorded_state': None, 'reasons': ['ADMISSION_RECORD_ABSENT_OR_NOT_JSON'],
                'record_sha256': digest(raw) if type(raw) is bytes else None, 'job': None}
    recorded = record.get('state')
    if set(record) != set(ADMISSION_FIELDS):
        reasons.append('ADMISSION_FIELDS')
    if record.get('schema') != ADMISSION_SCHEMA or record.get('label') != LABEL:
        reasons.append('ADMISSION_SCHEMA_OR_LABEL')
    if recorded not in ADMISSION_STATES:
        reasons.append('ADMISSION_STATE_UNKNOWN:' + str(recorded)[:80])
    elif recorded != ADMITTED:
        reasons.append('ADMISSION_STATE_IS:' + recorded)
    if not (same(record.get('job_kind'), JOB_KIND) and same(record.get('model_seed'), MODEL_SEED)
            and same(record.get('source_sha'), SOURCE_SHA)):
        reasons.append('ADMISSION_IS_FOR_ANOTHER_JOB_KIND')
    recorded_job = record.get('job')
    if stamp_of(recorded_job) is None or recorded_job == HELM2_JOB:
        reasons.append('ADMISSION_JOB_NAME:' + str(recorded_job)[:80])
    elif job is not None and recorded_job != job:
        reasons.append('ADMISSION_IS_FOR_ANOTHER_JOB:' + str(recorded_job))
    owner = record.get('owner_authorization') if type(record.get('owner_authorization')) is dict else {}
    if owner.get('state') != OWNER_AUTHORIZED or owner.get('records') != {
            name: pin[2] for name, pin in OWNER_RECORDS.items()}:
        reasons.append('ADMISSION_OWNER_AUTHORIZATION_BINDING')
    if (owner_state or {}).get('state') != OWNER_AUTHORIZED:
        reasons.append('OWNER_AUTHORIZATION_NOT_ESTABLISHED_NOW')
    bindings = record.get('bindings') if type(record.get('bindings')) is dict else {}
    for key in sorted(set(bindings) | set(expected_bindings)):
        if key not in bindings or key not in expected_bindings or not same(bindings[key], expected_bindings[key]):
            reasons.append('ADMISSION_BINDING:' + key)
    prerequisites = record.get('prerequisites') if type(record.get('prerequisites')) is dict else {}
    if set(prerequisites) != set(REQUIRED_PREREQUISITES):
        reasons.append('ADMISSION_PREREQUISITE_SET')
    for name in REQUIRED_PREREQUISITES:
        entry = prerequisites.get(name) if type(prerequisites.get(name)) is dict else {}
        if entry.get('status') != PREREQUISITE_PASS or not is_hex(entry.get('receipt_sha256'), 64):
            reasons.append('PREREQUISITE_NOT_PASSED:' + name)
    reasons.extend(policy_freeze_violations(policy, manifest, launch_request, expected_bindings, prerequisites))
    if recorded == ADMITTED and not (type(record.get('admitted_by')) is str and record['admitted_by'].strip()
                                     and type(record.get('admitted_utc')) is str
                                     and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',
                                                      record['admitted_utc'])):
        reasons.append('ADMISSION_ADMITTED_BY_OR_TIME')
    if committed is not True:
        reasons.append('ADMISSION_RECORD_NOT_COMMITTED_AS_IS')
    return {'state': ADMITTED if (recorded == ADMITTED and not reasons) else NOT_READY, 'recorded_state': recorded,
            'reasons': reasons, 'record_sha256': digest(raw), 'job': recorded_job}


def read_execution_admission():
    """`(raw or None, committed)`: the admission record's bytes, and whether HEAD carries exactly these bytes."""
    if not ADMISSION_PATH.is_file():
        return None, False
    raw = ADMISSION_PATH.read_bytes()
    committed = has_object('HEAD', ADMISSION_REL) and blob_id('HEAD', ADMISSION_REL) == git_object_id(raw)
    return raw, committed


# ---------------------------------------------------------------------------------------------------------------------
# The spend gate for --check: measured spend so far + $15.00 <= $60.00.
# ---------------------------------------------------------------------------------------------------------------------
def spend_gate(text, stop):
    """The figure is STATED by the operator (dollars, at most two decimals); the arithmetic is enforced here."""
    form = type(text) is str and re.fullmatch(r'\d{1,4}(\.\d{1,2})?', text) is not None
    stop(form, 'SPEND_FIGURE_FORM:' + str(text))
    try:
        spent = Decimal(text)
    except InvalidOperation:
        spent = None
    stop(spent is not None, 'SPEND_FIGURE_FORM:' + str(text))
    after = spent + Decimal(PER_JOB_USD)
    stop(after <= Decimal(CEILING_USD), 'SPEND_SO_FAR_PLUS_PER_JOB_BOUND_EXCEEDS_CEILING:' + str(after) + '>' + CEILING_USD)
    return {'spend_so_far_usd': str(spent), 'per_job_bound_usd': PER_JOB_USD, 'after_this_job_at_most_usd': str(after),
            'ceiling_usd': CEILING_USD}


# ---------------------------------------------------------------------------------------------------------------------
# The tree rule and the untracked rule (pure functions over git's -z output, so they can be tested without git).
# ---------------------------------------------------------------------------------------------------------------------
def parse_name_status_z(raw):
    """`git diff --name-status -z --no-renames` output -> [(status, repo-relative path)]."""
    fields = [field for field in raw.split(b'\0')]
    if fields and fields[-1] == b'':
        fields.pop()
    if len(fields) % 2:
        raise ValueError('NAME_STATUS_FIELDS_ODD')
    return [(fields[i].decode('ascii'), fields[i + 1].decode('utf-8')) for i in range(0, len(fields), 2)]


def tree_violations(entries):
    """Every difference between SOURCE_SHA and HEAD that is not an ADDED file under an allowed prefix."""
    allowed = tuple(GIT_PREFIX + prefix for prefix in ALLOWED_ADDED_PREFIXES)
    inventory = tuple(GIT_PREFIX + prefix for prefix in INVENTORY_TREES)
    violations = []
    for status, path in entries:
        if path.startswith(inventory):
            violations.append('INVENTORY:' + status + ':' + path)
        elif status != 'A' or not path.startswith(allowed):
            violations.append('OUTSIDE_THIS_ADMISSION:' + status + ':' + path)
    return violations


def parse_status_z(raw):
    """`git status --porcelain=v1 -z` output -> [(two-letter code, repo-relative path)]."""
    fields = raw.split(b'\0')
    entries, index = [], 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        code, path = entry[:2].decode('ascii'), entry[3:].decode('utf-8')
        if 'R' in code or 'C' in code:
            index += 1
        entries.append((code, path))
    return entries


def status_violations(entries):
    """Everything git status reports, except UNTRACKED files that are this folder's own outputs."""
    tolerated = tuple(GIT_PREFIX + prefix for prefix in TOLERATED_UNTRACKED)
    return [code + ' ' + path for code, path in entries if not (code == '??' and path.startswith(tolerated))]


# ---------------------------------------------------------------------------------------------------------------------
# Record builders (pure: the launcher's constants are passed in).
# ---------------------------------------------------------------------------------------------------------------------
def job_name(stamp):
    return 'cas-meta2-tpntr-' + stamp + '-' + SOURCE_SHA[:8] + '-m-' + str(MODEL_SEED)


def stamp_of(job):
    """The 14-digit stamp of a job name of this admission's form, or None."""
    match = re.fullmatch(r'cas-meta2-tpntr-(\d{14})-' + SOURCE_SHA[:8] + '-m-' + str(MODEL_SEED), str(job))
    return match.group(1) if match else None


def check_stamp(stamp, stop):
    stop(type(stamp) is str and re.fullmatch(r'\d{14}', stamp) is not None, 'STAMP_FORM')
    stop(stamp != HELM2_STAMP and job_name(stamp) != HELM2_JOB, 'STAMP_IS_HELM2_S_OWN_STAMP_A_NEW_JOB_IS_REQUIRED')
    return job_name(stamp)


def reference_pointer():
    return {'final_pt_sha256': REFERENCE_FINAL_PT_SHA256, 'final_pt_bytes': REFERENCE_FINAL_PT_BYTES,
            'commit': REFERENCE_COMMIT, 'receipt': GIT_PREFIX + REFERENCE_RECEIPT_REL,
            'records': {name: {'path': GIT_PREFIX + REFERENCE_RECEIPT_REL + '/' + name, 'blob': REFERENCE_BLOBS[name]}
                        for name in FINAL_PT_RECORDS}}


def reading_rule_record():
    """What the frozen records say about the reading: the policy, the labels, the pins. No prose status anywhere."""
    return {'policy': policy_pointers(), 'reader_rule': dict(READER_RULE), 'verdicts': list(VERDICTS),
            'level_labels': {key: list(value) for key, value in LEVEL_LABELS.items()},
            'deciding': 'evidence valid AND learned state identical AND every panel record identical',
            'never_deciding': ['file identity', 'continuation identity'],
            'panel_manifest': {'path': GIT_PREFIX + PANEL_MANIFEST_REL, 'sha256': PANEL_MANIFEST_SHA256,
                               'record_count': PANEL_RECORD_COUNT, 'record_ids_sha256': PANEL_RECORD_IDS_SHA256},
            'numerical_environment': dict(NUMERICAL_ENVIRONMENT),
            'numerical_environment_sha256': environment_digest(),
            'evidence_path': GIT_PREFIX + EVIDENCE_REL}


def owner_record(*, schema, candidate, job, condition, bounds, owner_state, admission):
    """The owner record the launcher reads (schema, candidate, owner_instruction_raw, job, bounds), plus bindings.

    `owner_instruction_raw` is the owner's standing grant, verbatim, from the blob-bound owner record. No approval word
    is added by this builder, and the record says so.
    """
    return {'schema': schema, 'candidate': candidate,
            'owner_instruction_raw': OWNER_QUOTES['standing_authorization'][0],
            'owner_words_verbatim': {name: words for name, (words, _) in OWNER_QUOTES.items()},
            'owner_authorization': {'state': owner_state['state'], 'records': owner_state['records']},
            'execution_admission': {'state': admission['state'], 'record_sha256': admission['record_sha256'],
                                    'job': admission['job']},
            'transcribed_by_agent': True, 'is_owner_signature': False, 'approval_words_inserted_by_builder': False,
            'label': LABEL, 'runner': RUNNER, 'job': job, 'job_kind': JOB_KIND, 'condition': condition,
            'model_seed': MODEL_SEED, 'source_sha': SOURCE_SHA, 'reproduces_job': HELM2_JOB,
            'comparison_target': reference_pointer(), 'reading_rule': reading_rule_record(),
            'scope': ('ONE job: seed 20260917 of source 20208c92, the full registered 10-pass schedule, the committed '
                      'package_20208c92, one machine, no automatic retry, under the standing project authorization, '
                      'only after the execution admission for this exact job is ADMITTED, and only if measured spend '
                      'so far + $15.00 <= $60.00 (checked by `prepare_unchanged_repro.py --check` just before '
                      'launch).'),
            'bounds': bounds}


def launch_argv(*, launcher, request, authority, owner, receipt_dir, ledger):
    """The exact argv, in `execute_study.py`'s order. No `--reduced-schedule`: this is the full registered run."""
    return ['python', '-B', str(launcher), '--execute',
            '--request', request['path'], '--request-sha256', request['sha256'],
            '--authority', authority['path'], '--authority-sha256', authority['sha256'],
            '--owner-authorization', owner['path'], '--receipt-dir', str(receipt_dir),
            '--ledger-path', str(ledger)]


def config_equal_except_job(new_text, old_text, new_job, old_job):
    """True when the two canonical worker configs are the same text once the job name is swapped."""
    if new_job == old_job or new_text.count(new_job) != old_text.count(old_job) or new_text.count(new_job) != 2:
        return False
    return new_text.replace(new_job, old_job) == old_text


# ---------------------------------------------------------------------------------------------------------------------
# Writing.
# ---------------------------------------------------------------------------------------------------------------------
def partial_of(folder):
    return folder.with_name(folder.name + '.partial')


def pin(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': digest(raw)}


def write_folder_atomically(final, entries, recheck, stop):
    """Write every file into `<final>.partial`, read it all back, re-run `recheck`, then rename into place.

    If anything fails, the `.partial` folder stays for a person to inspect, and every later run refuses until it is
    dealt with by hand. Nothing here deletes anything.
    """
    partial = partial_of(final)
    stop(not final.exists(), 'TARGET_EXISTS_NO_OVERWRITE:' + str(final))
    stop(not partial.exists(), 'PARTIAL_FOLDER_EXISTS_INSPECT_BY_HAND:' + str(partial))
    relative = []
    for path, raw in entries:
        stop(Path(path).is_relative_to(final) and type(raw) is bytes, 'ENTRY_OUTSIDE_TARGET:' + str(path))
        stop(b'\r' not in raw, 'ENTRY_HAS_CR_BYTES:' + str(path))      # committed under `text eol=lf`
        relative.append((Path(path).relative_to(final), raw))
    stop(len({item for item, _ in relative}) == len(relative), 'ENTRY_DUPLICATED')
    partial.mkdir()
    for item, raw in relative:
        target = partial / item
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    present = sorted(path.relative_to(partial).as_posix() for path in partial.rglob('*') if path.is_file())
    stop(present == sorted(item.as_posix() for item, _ in relative), 'PARTIAL_FILE_SET')
    for item, raw in relative:
        stop((partial / item).read_bytes() == raw, 'WRITTEN_BYTES:' + item.as_posix())
    recheck(lambda path: partial / Path(path).relative_to(final))
    try:
        os.rename(partial, final)
    except OSError as error:        # e.g. a OneDrive sync lock: fail closed, leave `.partial` for a person
        stop(False, 'RENAME_FAILED_PARTIAL_LEFT_INSPECT_BY_HAND:pause OneDrive sync during --write:'
             + type(error).__name__ + ':' + str(error)[:300])
    for item, raw in relative:
        stop((final / item).read_bytes() == raw, 'RENAMED_BYTES:' + item.as_posix())
    return [pin(final / item, raw) for item, raw in relative]
