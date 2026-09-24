"""Shared, launcher-free and torch-free facts and checks for the unchanged-arm reproduction (HELM-REPAIR-CONTROLLED-1).

WHAT THIS FOLDER DOES. It freezes ONE AWS job and later reads its result:
  * the job: seed 20260917 of the historical Helm 2.0 source 20208c92, full registered 10-pass schedule, trained by
    the same launcher (`aws/typed_pointer_launch.py`) on g7.2xlarge, from the same committed package;
  * the reading: Codex's reproduction policy revision 1 (`REPRODUCTION_POLICY.json`, pinned in `policy_pins.json`),
    implemented exactly. Three verdicts only:
      STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED            valid evidence AND identical learned state AND identical panel;
      DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY   valid evidence, but learned state or any panel record differs;
      ADMISSION_INVALID_STOP                             any missing, corrupt or misbound evidence (never a fallback).
    Checkpoint-FILE identity and optimizer/RNG CONTINUATION identity are printed separately and never decide.

REVISION 2 (2026-09-24, CLAUDE_BUILT_CLAUDE_CHECKED). Conformed to Codex's policy revision 1 (Codex amendment item 2):
  * the old rule (final.pt file sha256) and its prose "status line" parser are GONE. Nothing here reads a status word
    out of prose (review finding V1);
  * two machine-readable states replace them:
      owner_authorization  - read from the three recorded owner files, each bound by its git blob id and sha256;
      execution_admission  - a technical-readiness record (`EXECUTION_ADMISSION.json`) bound to the exact plan,
                             policy, manifest, panel, environment and reader-source hashes. Only `ADMITTED`, with every
                             binding equal and every prerequisite receipt present, lets `--write` or `--check` proceed.
    `--dry-run` and every test run without either state. No approval word is ever inserted anywhere;
  * the complete public panel (564 course records), the numerical environment and the reader's own source are pinned.

REVISION 3 (2026-09-24, CLAUDE_BUILT_CLAUDE_CHECKED). Review of 303c281b (CHANGES_REQUIRED):
  * BLOCKER 1: the policy and owner-record pins moved to `policy_pins.json`, outside the reader digest, so Codex can
    freeze REPRODUCTION_POLICY.json with the reader digest and a re-pin never changes that digest (no hash cycle);
  * MAJOR 2: every prerequisite names a committed receipt (commit + path + sha256); the code opens it and checks its
    content and bindings; the budget figure is read from a committed spend record, never typed in;
  * MAJOR 3: only a historical `require` refusal (POINTER_/TYPED_ code) is a panel record; any other fault is invalid;
  * minors: the frozen-before-result rule, the admission re-read at the receipt commit, AMI and shipped-package checks,
    the starting-state identity as training configuration, owner records in the tip check.

REVISION 4 (2026-09-24, CLAUDE_BUILT_CLAUDE_CHECKED; branch claude/helm-unchanged-reader-rev-20260924 from the freeze
3344ae5d). Codex READER_STATIC_REVIEW_20260924 fixes 1-7 and POLICY_DECISIONS_20260924 R3-B/C/G/H/I, in ONE revision
(each change moves the reader fingerprint):
  * READING ELIGIBILITY (Codex bus codex-0021; Claude default Q-F). The frozen study (study.json 60140ae0...) froze the
    execution admission as it was, NOT_READY (5042681a...), and launched under OWNER_DIRECTION_20260924. It asks for "a
    disclosed amendment to the reader admission check only; decide() unchanged; EXECUTION_ADMISSION.json never flipped
    afterwards". So a NEW record type, READING_ELIGIBILITY.json, committed once after the freeze and before the
    evidence, binds the frozen study, the as-is NOT_READY admission (byte-identical), this reader, the pins, the panel,
    the owner-direction record, the P1b acceptance receipt, the environment lock and the review receipt. The frozen
    files and EXECUTION_ADMISSION.json are untouched; decide() is byte-identical to the freeze;
  * fix 1 / R3-B: a refusal is a plain ValueError whose COMPLETE message is on the published allowlist
    (`historical_refusal_allowlist.json`, extracted from the pinned archive by `build_refusal_allowlist.py`, carrying
    the archive hash); the display is truncated only after that check;
  * fix 2 / R3-G: the history rule counts merge commits too (`git log -m`) and compares the pinned blobs across every
    later commit, merges included;
  * fix 3 / R3-G: a missing pinned object (owner, policy, reference, freeze or eligibility receipt commit), an
    unfetched receipt branch or an unpushed receipt commit is a recoverable TOOL_STOP (exit 1) before evaluation;
  * fix 4: the spend record's sources are opened from committed, anchored blobs and checked; freshness is the R3-F
    five-minute window before the admission time;
  * fix 5 / R3-H: a review receipt resolves its pushed reviewed commit and binds the complete closure, the preparation
    writers included, plus reviewer provenance; verdict SOURCE_CONFORMANCE_PASS with no open BLOCKER/MAJOR finding;
  * fix 6 / R3-I: the environment lock `helm.reproduction-environment/1` is parsed strictly and compared with the
    observed runtime (versions parsed, not hashed). INVALID-deciding at minimum (Claude default Q-G): Python
    implementation and version, torch build, CUDA runtime, cuDNN, GPU model; other fields are diagnostic unless the
    lock itself lists them as required-equal (THIS DEFAULT IS WITHDRAWN in revision 5: every lock field is
    required-equal, per Codex Q-G);
  * fix 7 / R3-C: a frozen table of the expected verdict and levels of all eleven acceptance cases; each case's observed
    fields are compared with it, and `pass: true` is never trusted. changed-buffer prints its buffer count (0).

REVISION 5 (2026-09-24, CLAUDE_BUILT_CLAUDE_CHECKED; same branch, on top of fee4ebec). Codex's rulings
READING_STAGE_DECISIONS_20260924 Q-F / Q-G and POLICY_DECISIONS_20260924 R3-I (branch
codex/helm-controlled-prelaunch-20260924, commit dc02eb81):
  * Q-G / R3-I: EVERY field of the environment lock is required-equal, driver version and kernel included. The
    revision-4 default (driver and kernel diagnostic) is withdrawn. Only declared non-predictive ENVELOPE fields
    (`envelope.<name>`: hardware instance IDs, paths, elapsed time, or another envelope field the lock declares with a
    reason) may be diagnostic, so no lock field can be downgraded. A historical value that cannot be established is
    written as UNESTABLISHED_FROM_PUBLIC_HISTORICAL_RECORDS and reads ENVIRONMENT_ADMISSION_UNVERIFIED (INVALID); the
    current machine's value is never compared with it or accepted in its place. A lock that contradicts a value this
    reader already pins from the historical records is refused;
  * Q-F: the eligibility RULE is a frozen, committed file (`READING_ELIGIBILITY_RULE.json`, a reader source, so the
    reader fingerprint covers it). It fixes now every value that is known now, names every piece of evidence that is
    appended later (the P1b acceptance receipt hash, the environment lock, the review, the reader fingerprint, ...),
    and states that the NOT_READY admission is preserved and never rewritten and that decide() is unchanged. The
    record it governs (schema /2) is labelled POST_TRAINING_ELIGIBILITY_BEFORE_COMPARISON, carries a runner
    attestation of which deciding outputs (if any) were viewed, and must follow the training result, the lock (which
    must precede the P1b acceptance) and every receipt, and precede the production evidence. decide() is unchanged.

THIS MODULE IMPORTS NOTHING FROM THE LAUNCHER, torch or the network. It lives under `records/`, not `cncm/` or
`cas_meta2/`, on purpose: `pointer_contract.input_inventory` globs `*.py` under those trees.

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED (temporary Claude builder while Codex is away). It transcribes the owner's words;
it is not an owner signature.
"""
import ast
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha1, sha256
import io
import json
import os
from pathlib import Path
import re
import subprocess
from zipfile import BadZipFile, ZipFile

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
# THE POLICY TO IMPLEMENT (Codex; the commit is in policy_pins.json). Every file is pinned by blob id, sha256, size.
#
# REVISION 3 (review of 303c281b, BLOCKER 1): the pins are NOT in this module any more. They live in
# `policy_pins.json`, next to it. Reason: the reader-source digest covers this module, and Codex freezes
# REPRODUCTION_POLICY.json with that digest. A policy hash inside a reader source is a hash cycle: every re-pin would
# change the digest the policy must hold. Now a re-pin edits only `policy_pins.json`, which the digest does not cover.
# The pins file is bound by its sha256 in EXECUTION_ADMISSION.json, frozen/study.json and the evidence instead.
# `test_no_reader_source_carries_a_pinned_policy_hash` keeps it that way.
# =====================================================================================================================
PINS_NAME = 'policy_pins.json'
PINS_REL = HERE_REL + '/' + PINS_NAME
PINS_SCHEMA = 'cncm.helm-unchanged-reproduction-policy-pins/1'
PINS_TOP_FIELDS = ('label', 'owner_records', 'policy', 'schema', 'why_a_separate_file')
PINS_POLICY_FILE_NAMES = ('codex_amendments', 'execution_manifest', 'launch_request', 'plan', 'reproduction_policy_json',
                          'reproduction_policy_md', 'route_and_checkpoint_protocol', 'statistical_policy')
PINS_OWNER_RECORD_NAMES = ('claude_extension_md', 'codex_standing_json', 'codex_standing_md')
PRELAUNCH = 'records/helm_controlled_prelaunch_20260924/'
HANDOFF = '_handoffs/HELM_NEXT_PHASE_20260923/'


def _hex(value, length):
    return type(value) is str and re.fullmatch('[0-9a-f]{%d}' % length, value) is not None


def _relative_path(value):
    """A ROOT-relative path: forward slashes, no leading slash, no empty, '.' or '..' part."""
    return (type(value) is str and 0 < len(value) <= 400 and not value.startswith('/') and '\\' not in value
            and all(part not in ('', '.', '..') for part in value.split('/')))


def _branch(value):
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9._/-]{1,120}', value) is not None and '..' not in value


def pins_violations(pins):
    """Every way a parsed pins document is not exactly the expected form. Pure (used at import, before `same`)."""
    if type(pins) is not dict:
        return ['PINS_NOT_AN_OBJECT']
    violations = []
    if sorted(pins) != list(PINS_TOP_FIELDS) or pins.get('schema') != PINS_SCHEMA or pins.get('label') != LABEL:
        violations.append('PINS_TOP_FIELDS_SCHEMA_OR_LABEL')
    policy = pins.get('policy') if type(pins.get('policy')) is dict else {}
    if sorted(policy) != ['branch', 'commit', 'files'] or not _hex(policy.get('commit'), 40) \
            or not _branch(policy.get('branch')):
        violations.append('PINS_POLICY_HEAD')
    files = policy.get('files') if type(policy.get('files')) is dict else {}
    if sorted(files) != list(PINS_POLICY_FILE_NAMES):
        violations.append('PINS_POLICY_FILE_SET')
    for name, row in files.items():
        if not (type(row) is dict and sorted(row) == ['blob', 'bytes', 'path', 'sha256'] and _hex(row['blob'], 40)
                and _hex(row['sha256'], 64) and type(row['bytes']) is int and row['bytes'] > 0
                and _relative_path(row['path'])):
            violations.append('PINS_POLICY_FILE:' + str(name))
    owners = pins.get('owner_records') if type(pins.get('owner_records')) is dict else {}
    if sorted(owners) != list(PINS_OWNER_RECORD_NAMES):
        violations.append('PINS_OWNER_RECORD_SET')
    for name, row in owners.items():
        if not (type(row) is dict and sorted(row) == ['blob', 'branch', 'commit', 'path', 'sha256']
                and _hex(row['blob'], 40) and _hex(row['sha256'], 64) and _hex(row['commit'], 40)
                and _branch(row['branch']) and _relative_path(row['path'])):
            violations.append('PINS_OWNER_RECORD:' + str(name))
    return violations


def load_pins(raw):
    """The parsed pins, or an explicit stop at import (never an `assert`). Nothing runs on a bad pins file."""
    try:
        pins = json.loads(raw)
    except ValueError:
        pins = None
    violations = pins_violations(pins)
    if violations:
        raise SystemExit('UNCHANGED_REPRO_POLICY_PINS_INVALID:' + '|'.join(violations))
    return pins


PINS_RAW = (HERE / PINS_NAME).read_bytes()
PINS_SHA256 = sha256(PINS_RAW).hexdigest()
_PINS = load_pins(PINS_RAW)
POLICY_COMMIT = _PINS['policy']['commit']
POLICY_BRANCH = _PINS['policy']['branch']
POLICY_FILES = {   # name: (ROOT-relative path, git blob, sha256, bytes)
    name: (row['path'], row['blob'], row['sha256'], row['bytes'])
    for name, row in sorted(_PINS['policy']['files'].items())}


def tracking_ref(branch):
    return 'refs/remotes/origin/' + branch


def fetch_args(branch):
    """An explicit refspec into the remote-tracking ref only: never a pull, never a local branch."""
    return ('fetch', 'origin', branch + ':' + tracking_ref(branch))


POLICY_TRACKING_REF = tracking_ref(POLICY_BRANCH)
POLICY_FETCH_ARGS = fetch_args(POLICY_BRANCH)
POLICY_FETCH = 'git ' + ' '.join(POLICY_FETCH_ARGS)
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
    'frozen_before_reproduction_result_required': True,     # revision 3 (review finding 5); enforced by the reader
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
ENVIRONMENT_RECORDED_NOT_PINNED = ('python_version', 'cudnn_version', 'driver_version', 'platform_release',
                                   'python_implementation', 'machine', 'compute_capability')     # last 3: revision 4
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
# REVISION 3 (review finding 8): `initial_model_identity` moved HERE from continuation. The route protocol makes the
# starting state a frozen check that must pass "before its first optimizer update", and the policy's continuation row
# lists only optimizer, RNG, cursor/revision and counters. A different start is therefore a run that was not the
# registered one: INVALID, never a fallback-eligible mismatch. Open question for Codex (BUILDER_REPORT 10.6).
TRAINING_RUN_IDENTITY = ('optimizer_config', 'initialization', 'initial_model_identity', 'scope', 'counters',
                         'counter_units', 'measured_pooling', 'measured_stability')
TRAINING_CONTEXT = ('course_sha256', 'condition', 'source_seed')
TRAINING_INIT_ARGS = ('optimizer_config', 'python_seed', 'device')
# Continuation (policy: "cursor/model revision and training counters").
CONTINUATION_METADATA = ('cursor', 'model_revision', 'counters', 'training_mode')
CONTINUATION_RUN_IDENTITY = ()
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
EVIDENCE_SCHEMA = 'cncm.helm-unchanged-reproduction-evidence/2'              # revision 4: full-message refusals
ACCEPTANCE_SCHEMA = 'cncm.helm-unchanged-reproduction-reader-acceptance/2'   # revision 4: per-case observed fields
EVIDENCE_REL = 'records/typed_pointer_001/evidence_unchanged_repro_20260917/reproduction_evidence.json'
EVIDENCE_MODES = ('READING', 'ACCEPTANCE')
# The files the ONE reader digest covers. `policy_pins.json` is deliberately NOT one of them (BLOCKER 1, revision 3).
# Revision 4 adds the published refusal allowlist: it decides which panel rows are model refusals, so it is covered.
# Revision 5 adds the frozen eligibility rule (Codex Q-F): it decides which eligibility record is acceptable, so it is
# covered too. It holds no reader, policy or owner-record hash, so covering it makes no hash cycle.
REFUSAL_ALLOWLIST_NAME = 'historical_refusal_allowlist.json'
ELIGIBILITY_RULE_NAME = 'READING_ELIGIBILITY_RULE.json'
READER_SOURCE_FILES = ('read_reproduction.py', 'repro_common.py', 'recompute_reproduction_evidence.py',
                       REFUSAL_ALLOWLIST_NAME, ELIGIBILITY_RULE_NAME)

# ---- panel rows: what is model behaviour and what is an infrastructure fault (review MAJOR 3, revision 3).
# The historical `require` (source.require, matched_contract.require at 20208c92) raises ValueError whose message is a
# code starting POINTER_ or TYPED_ (for example POINTER_SLOT_COVERAGE, TYPED_MATCHED:POINTER_NODE_FEATURE_WIDTH:3).
# Only such a refusal is a panel record ("failed/refused records remain records"). Every other exception, a grader
# crash, or a prediction for the wrong record is an INFRASTRUCTURE FAULT: the evidence is invalid, never a mismatch.
HISTORICAL_REFUSAL_PATTERN = r'(POINTER|TYPED)_[A-Z0-9_]+(:[\x20-\x7e]*)?'
PANEL_INFRASTRUCTURE_FAULT = 'ERROR'
# ---- revision 4 (Codex R3-B, reader review fix 1): the explicit allowlist. `build_refusal_allowlist.py` extracts it
# from the pinned archive (c42370c4...) and publishes it next to this module; the reader digest covers it. A message
# is a refusal only when it satisfies the code shape above AND equals an `exact` entry or fullmatches a `patterns` entry.
REFUSAL_ALLOWLIST_SCHEMA = 'cncm.helm-historical-refusal-allowlist/1'
REFUSAL_CODE_HEADS = ('POINTER_', 'TYPED_')
REFUSAL_DETAIL = '[\\x21-\\x7e]{1,200}'            # a dynamic part: printable ASCII, no space, no newline
REFUSAL_MESSAGE_MAX = 400
REFUSAL_ALLOWLIST_FIELDS = ('counts', 'detail_class', 'exact', 'integer_class', 'label', 'patterns', 'rule', 'schema',
                            'source', 'unresolved')


def refusal_allowlist_violations(document):
    """Every way a parsed allowlist is not the published form bound to the pinned archive. Pure."""
    if type(document) is not dict:
        return ['ALLOWLIST_NOT_AN_OBJECT']
    violations = []
    if sorted(document) != list(REFUSAL_ALLOWLIST_FIELDS) or document.get('schema') != REFUSAL_ALLOWLIST_SCHEMA \
            or document.get('label') != LABEL or document.get('detail_class') != REFUSAL_DETAIL:
        violations.append('ALLOWLIST_FIELDS_SCHEMA_LABEL_OR_DETAIL')
    source = document.get('source') if type(document.get('source')) is dict else {}
    if not (source.get('package_commit') == PACKAGE_COMMIT and source.get('archive_sha256') == ARCHIVE_SHA256
            and source.get('archive_git_blob') == PACKAGE_BLOBS['source.zip']
            and source.get('archive_bytes') == ARCHIVE_BYTES):
        violations.append('ALLOWLIST_SOURCE_IS_NOT_THE_PINNED_ARCHIVE')
    for key in ('exact', 'patterns'):
        items = document.get(key)
        if not (type(items) is list and items and all(type(item) is str and item.isascii() and '\n' not in item
                                                      for item in items) and items == sorted(set(items))):
            violations.append('ALLOWLIST_' + key.upper() + '_FORM')
    if not violations:
        for item in document['exact']:
            if not item.startswith(REFUSAL_CODE_HEADS):
                violations.append('ALLOWLIST_EXACT_NOT_A_CODE:' + item[:60])
        for item in document['patterns']:
            try:
                re.compile(item)
            except re.error:
                violations.append('ALLOWLIST_PATTERN_DOES_NOT_COMPILE:' + item[:60])
    return violations


def load_refusal_allowlist(raw):
    """`(exact frozenset, compiled patterns)`. An absent file gives an EMPTY allowlist (every refusal then reads as an
    infrastructure fault, the fail-closed direction); a present but malformed file stops at import."""
    if raw is None:
        return frozenset(), ()
    try:
        document = json.loads(raw)
    except ValueError:
        document = None
    violations = refusal_allowlist_violations(document)
    if violations:
        raise SystemExit('UNCHANGED_REPRO_REFUSAL_ALLOWLIST_INVALID:' + '|'.join(violations)[:600])
    return frozenset(document['exact']), tuple(re.compile(item) for item in document['patterns'])


REFUSAL_ALLOWLIST_PATH = HERE / REFUSAL_ALLOWLIST_NAME
REFUSAL_ALLOWLIST_RAW = REFUSAL_ALLOWLIST_PATH.read_bytes() if REFUSAL_ALLOWLIST_PATH.is_file() else None
REFUSAL_ALLOWLIST_SHA256 = sha256(REFUSAL_ALLOWLIST_RAW).hexdigest() if REFUSAL_ALLOWLIST_RAW is not None else None
REFUSAL_EXACT, REFUSAL_PATTERNS = load_refusal_allowlist(REFUSAL_ALLOWLIST_RAW)

# ---- the training machine as each receipt's preflight.json records it (review MINOR 7, revision 3).
PREFLIGHT_RECORD = 'preflight.json'
PREFLIGHT_PINS = {'ami': HISTORICAL_AMI, 'instance_type': EXPECTED_BOUNDS['instance_type'],
                  'region': EXPECTED_BOUNDS['region']}
SHIPPED_PACKAGE_RECORD = 'collected/input/source.zip'
REQUIREMENTS_MEMBER = 'research/CAS_META_2_COMPOSITION/requirements-gpu.txt'

# =====================================================================================================================
# OWNER AUTHORIZATION (machine-readable, bound by git blob ids). Nothing here parses prose for approval words.
# =====================================================================================================================
OWNER_AUTHORIZED = 'STANDING_PROJECT_AUTHORIZATION'
OWNER_NOT_ESTABLISHED = 'OWNER_AUTHORIZATION_NOT_ESTABLISHED'
OWNER_RECORDS = {   # name: (commit, ROOT-relative path, git blob, sha256) -- from policy_pins.json (revision 3)
    name: (row['commit'], row['path'], row['blob'], row['sha256'])
    for name, row in sorted(_PINS['owner_records'].items())}
OWNER_RECORD_BRANCHES = {name: row['branch'] for name, row in sorted(_PINS['owner_records'].items())}
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
# REVISION 3 (review MAJOR 2): a prerequisite is never self-asserted. Each entry names a receipt by commit and path; the
# code opens that committed blob, checks its sha256, and checks its CONTENT (schema, pass status, and bindings to this
# job, this reader and this revision). A 'PASS' plus a 64-hex string no longer passes anything by itself.
PREREQUISITE_FIELDS = ('receipt_commit', 'receipt_path', 'receipt_sha256', 'status', 'what_passes_it')
ACCEPTANCE_PASS, ACCEPTANCE_FAIL = 'READER_ACCEPTANCE_PASS', 'READER_ACCEPTANCE_FAIL'
VACUOUS = 'VACUOUS'
# The P1 acceptance cases, in the order `recompute_reproduction_evidence.acceptance_mode` records them. `changed_buffer`
# is VACUOUS for this architecture (no registered buffers at 20208c92); the case passes only while that stays true.
ACCEPTANCE_CASES = ('self_identity', 'equal_state_different_envelope', 'continuation_only_different', 'changed_value',
                    'changed_encoder_state', 'missing_key', 'dtype_change', 'altered_output', 'changed_buffer',
                    'state_equal_output_tampered', 'corrupt_reference')
# Revision 4, fix 7: the FROZEN expected outcome of every case. `recompute_reproduction_evidence.acceptance_specs` and
# `acceptance_mode` take their expectations from here, and the reader compares each case's OBSERVED fields with it.
# `levels` lists only the levels a case registers (other levels are free). missing_key / dtype_change: the pinned
# historical loader refuses both, so no complete panel exists and the answer is ADMISSION_INVALID_STOP (Codex R3-B:
# "if the historical loader cannot produce a complete valid panel, the decision is ADMISSION_INVALID_STOP").
# changed_buffer: VACUOUS only while the restored reference prints exactly zero buffers (Codex R3-C).
ACCEPTANCE_EXPECTED = {
    'self_identity': {'verdict': REPRODUCED,
                      'levels': {'file': True, 'learned_state': True, 'output': True, 'continuation': True}},
    'equal_state_different_envelope': {'verdict': REPRODUCED, 'levels': {'file': False, 'learned_state': True,
                                                                         'output': True, 'continuation': True}},
    'continuation_only_different': {'verdict': REPRODUCED,
                                    'levels': {'learned_state': True, 'output': True, 'continuation': False}},
    'changed_value': {'verdict': DOES_NOT_REPRODUCE, 'levels': {'learned_state': False}},
    'changed_encoder_state': {'verdict': DOES_NOT_REPRODUCE, 'levels': {'learned_state': False}},
    'missing_key': {'verdict': INVALID_STOP, 'levels': {'learned_state': False}},
    'dtype_change': {'verdict': INVALID_STOP, 'levels': {'learned_state': False}},
    'altered_output': {'verdict': DOES_NOT_REPRODUCE, 'levels': {'learned_state': False, 'output': False}},
    'changed_buffer': {'status': VACUOUS, 'reference_buffer_count': 0},
    'state_equal_output_tampered': {'verdict': DOES_NOT_REPRODUCE, 'levels': {'learned_state': True, 'output': False}},
    'corrupt_reference': {'verdict': INVALID_STOP, 'levels': {}},
}
# Revision 4, fix 5 (Codex R3-H): scoped verdicts, a RESOLVED and PUSHED reviewed commit, the complete code closure
# (the preparation writers included) and a reviewer provenance record. The historical NO_BLOCKER_OR_MAJOR_FINDING_OPEN
# receipt (schema /1) is preserved in history but does not establish readiness, so /1 is refused here.
REVIEW_RECEIPT_SCHEMA = 'cncm.helm-unchanged-reproduction-review-receipt/2'
REVIEW_RECEIPT_FIELDS = ('attribution', 'closure', 'job_kind', 'label', 'model_seed', 'reviewed_branch',
                         'reviewed_commit', 'reviewed_panel_manifest_sha256', 'reviewed_policy_pins_sha256',
                         'reviewed_reader_source_sha256', 'reviewed_reader_sources_sha256', 'reviewer',
                         'reviewer_provenance', 'schema', 'scope', 'unresolved_findings', 'verdict')
REVIEW_PASS = 'SOURCE_CONFORMANCE_PASS'               # a reviewer's machine field; prose is never read
REVIEW_VERDICTS = ('SOURCE_CONFORMANCE_PASS', 'CHANGES_REQUIRED')
REVIEW_SEVERITIES = ('BLOCKER', 'MAJOR', 'MINOR', 'NOTE')
REVIEW_BLOCKING_SEVERITIES = ('BLOCKER', 'MAJOR')     # owner rule 2026-09-24: only these hold a launch or a reading
INDEPENDENCE_LABEL = 'EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT'
WRITER_FILES = ('prepare_unchanged_repro.py', 'write_launch_under_owner_direction.py')
REVIEW_CLOSURE_FILES = READER_SOURCE_FILES + WRITER_FILES + (PANEL_MANIFEST_NAME, PINS_NAME)
# Revision 4, fix 4: every spend source is a committed blob (commit + path + sha256) that the code OPENS and checks,
# and the figure is fresh: measured at most five minutes before the admission time (Codex R3-F window).
SPEND_RECORD_SCHEMA = 'cncm.helm-unchanged-reproduction-spend-record/2'
SPEND_RECORD_FIELDS = ('basis', 'job', 'label', 'measured_spend_so_far_usd', 'measured_utc', 'schema', 'sources',
                       'study')
SPEND_SOURCE_FIELDS = ('commit', 'path', 'sha256')
SPEND_FRESHNESS_SECONDS = 300
STUDY_NAME = 'HELM-REPAIR-CONTROLLED-1'

# ---- revision 4: the READING ELIGIBILITY record (Codex bus codex-0021; Claude default Q-F). The frozen study and the
# as-is admission are upstream facts of this reader (no hash cycle: the eligibility record, downstream, binds this
# reader, never the reverse).
FREEZE_COMMIT = '3344ae5d7bcc0d5ff50f1bce220f77a063ece65a'
FROZEN_STUDY_SHA256 = '60140ae0587e983120f37cb3499ecdc19e59f23cc0363520b2814e9e413f8a12'
FROZEN_ADMISSION_SHA256 = '5042681aa3e6e034a88cf6e516ee8dbf2f9b97b2d09f2f9bf4e234ad552bfb50'
LAUNCH_BASIS = 'OWNER_DIRECTION_20260924'
FROZEN_FILES = ('frozen/study.json', 'frozen/20260917/request.json', 'frozen/20260917/authority.json',
                'frozen/20260917/owner.json')
ELIGIBILITY_NAME = 'READING_ELIGIBILITY.json'
ELIGIBILITY_REL = HERE_REL + '/' + ELIGIBILITY_NAME
# Revision 5 (Codex Q-F): schema /2. No /1 record was ever written; /2 adds the chronology label, the frozen rule it
# follows, the numerical-environment digest, the writer blobs and the runner attestation.
ELIGIBILITY_SCHEMA = 'cncm.helm-unchanged-reproduction-reading-eligibility/2'
ELIGIBLE = 'READING_ELIGIBLE'
ELIGIBILITY_CHRONOLOGY = 'POST_TRAINING_ELIGIBILITY_BEFORE_COMPARISON'     # Codex Q-F; never a prelaunch admission
ELIGIBILITY_RECEIPTS = ('reader_acceptance', 'environment_lock', 'review')
ELIGIBILITY_RULE_REL = HERE_REL + '/' + ELIGIBILITY_RULE_NAME
ELIGIBILITY_RULE_SCHEMA = 'cncm.helm-unchanged-reproduction-reading-eligibility-rule/1'
# The status claims only what the file itself shows. "Before U17 launch" is shown by git order (the rule's commit must
# precede the U17 training result) and by the runner attestation, never by this word.
ELIGIBILITY_RULE_STATUS = 'RULE_FROZEN_EVIDENCE_APPENDED_LATER'
FROZEN_JOB = 'cas-meta2-tpntr-20260924123354-20208c92-m-20260917'          # frozen/study.json jobs[0].job
FROZEN_DECIDE_SHA256 = '637db5ebe7608dae5eec1df3c8c9657f6099308517e8257908b3e92e2742b635'   # decide() at the freeze
WRITER_BLOBS_AT_FREEZE = {'prepare_unchanged_repro.py': 'ee1ca1e8399d5618ca4b4f33f9d27e3bd4a52bfe',
                          'write_launch_under_owner_direction.py': 'aed75bfb72fff5d0eac1d48e03562c4ed6fd9135'}
# The owner-direction record the frozen study names, at the commit that added it (the disclosed 33d2e789 chronology).
OWNER_DIRECTION = {'commit': '33d2e7893948152221501da3902781a3babb9a4d',
                   'path': HANDOFF + 'OWNER_STOP_POLISHING_20260924.md',
                   'blob': 'e76f1005e8fb9d7fad9fa2bd5e8cf377446512c4',
                   'sha256': '626b81fef3d481cdcd264560ca6106ee1e4c3fabde705be4ebdca9146f2729eb'}
# The fields whose values arrive later (their order is the order the frozen rule lists them in).
ELIGIBILITY_APPENDED = ('reader_acceptance', 'environment_lock', 'review', 'reader', 'policy_pins_sha256',
                        'eligibility_rule', 'runner_attestation', 'written_by', 'written_utc', 'note')
ATTESTATION_FIELDS = ('attester', 'deciding_outputs_viewed', 'rule_on_launch_checkout_before_u17_launch', 'statement')
ROUTE_ADMISSION, ROUTE_ELIGIBILITY = 'EXECUTION_ADMISSION_ADMITTED', 'READING_ELIGIBILITY_RECORD'

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


def function_source(text, name):
    """The exact source text of the top-level function `name` in `text` (decorators excluded), or None. Pure."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, TypeError):
        return None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(text, node)
    return None


def decide_source_sha256(raw):
    """sha256 of the exact `decide()` source text in a read_reproduction.py file's bytes, or None. Pure.
    Revision 4: `decide()` must stay byte-identical to the freeze; the reader and the eligibility record both check."""
    if type(raw) is not bytes:
        return None
    try:
        source = function_source(raw.decode('utf-8'), 'decide')
    except UnicodeDecodeError:
        return None
    return None if source is None else digest(source.encode('utf-8'))


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


def environment_unrecorded(recorded):
    """The recorded-not-pinned keys (driver, cuDNN, Python, kernel) the evidence failed to record at all."""
    recorded = recorded if type(recorded) is dict else {}
    return [key for key in ENVIRONMENT_RECORDED_NOT_PINNED if key not in recorded]


# ---------------------------------------------------------------------------------------------------------------------
# Revision 4, fix 6 (Codex R3-I): the environment lock `helm.reproduction-environment/1`, parsed strictly and compared
# with the OBSERVED runtime (versions parsed, never merely hashed or presence-checked). Pure.
# ---------------------------------------------------------------------------------------------------------------------
ENVIRONMENT_LOCK_SCHEMA = 'helm.reproduction-environment/1'
ENVIRONMENT_LOCK_STATUS = 'FROZEN'
ENVIRONMENT_LOCK_TOP = ('accelerator', 'comparison', 'image', 'libraries', 'numerics', 'runtime', 'schema',
                        'source_commit', 'status')
ENVIRONMENT_LOCK_SHAPE = {
    'image': ('ami_id', 'provider', 'region'),
    'runtime': ('kernel', 'machine', 'os', 'python_implementation', 'python_version'),
    'accelerator': ('compute_capability', 'driver_version', 'gpu_model', 'instance_type'),
    'libraries': ('cuda_runtime', 'cudnn', 'packages', 'torch'),
    'numerics': ('cudnn_allow_tf32', 'deterministic_algorithms', 'dtype', 'environment_variables',
                 'float32_matmul_precision', 'matmul_allow_tf32', 'seeds', 'thread_counts'),
}
ENVIRONMENT_LOCK_LEAVES = tuple(section + '.' + key for section, keys in ENVIRONMENT_LOCK_SHAPE.items() for key in keys)
ENVIRONMENT_BOOL_LEAVES = ('numerics.cudnn_allow_tf32', 'numerics.deterministic_algorithms', 'numerics.matmul_allow_tf32')
ENVIRONMENT_MAP_LEAVES = ('numerics.environment_variables', 'numerics.seeds', 'numerics.thread_counts')
# Revision 5 (Codex R3-I and Q-G). The revision-4 default (driver and kernel diagnostic) is WITHDRAWN: Codex ruled
# "the proposed blanket diagnostic-only driver/kernel treatment conflicts with the fixed R3-I policy". So the lock MUST
# list EVERY lock field as required-equal (numerical, software, library, image, runtime and accelerator fields alike,
# driver version and kernel included), and a difference in any of them makes the evidence INVALID, never a mismatch.
ENVIRONMENT_REQUIRED_EQUAL = ENVIRONMENT_LOCK_LEAVES
# Only declared non-predictive ENVELOPE fields may be diagnostic (R3-I: "only hardware instance IDs, paths, elapsed time
# and other declared non-predictive envelope fields are diagnostic"). They are named `envelope.<name>`, carry a reason,
# and are never lock fields, so no lock field can be downgraded by listing it as diagnostic.
ENVIRONMENT_DIAGNOSTIC_PREFIX = 'envelope.'
ENVIRONMENT_DIAGNOSTIC_PATTERN = r'envelope\.[a-z][a-z0-9_]{0,63}'
# A historical value that cannot be established from the public historical records is written as this exact string.
# It is an explicit blocker: every source reads ENVIRONMENT_ADMISSION_UNVERIFIED (INVALID) for that field, and the
# current machine's value is never compared with it or accepted in its place (R3-I, Q-G).
ENVIRONMENT_UNESTABLISHED = 'UNESTABLISHED_FROM_PUBLIC_HISTORICAL_RECORDS'
ENVIRONMENT_UNVERIFIED = 'ENVIRONMENT_ADMISSION_UNVERIFIED'
# lock leaf -> (key in an observed environment: the evidence / acceptance `environment`, a worker_report `runtime`;
# how the two values are parsed before they are compared).
ENVIRONMENT_OBSERVED = {
    'runtime.python_implementation': ('python_implementation', 'text'),
    'runtime.python_version': ('python_version', 'version'),
    'runtime.os': ('platform_system', 'text'),
    'runtime.kernel': ('platform_release', 'text'),
    'runtime.machine': ('machine', 'text'),
    'accelerator.gpu_model': ('gpu_name', 'text'),
    'accelerator.compute_capability': ('compute_capability', 'version'),
    'accelerator.driver_version': ('driver_version', 'version'),
    'libraries.torch': ('torch_version', 'torch'),
    'libraries.cuda_runtime': ('cuda_version', 'version'),
    'libraries.cudnn': ('cudnn_version', 'cudnn'),
    'numerics.deterministic_algorithms': ('deterministic_algorithms', 'bool'),
    'numerics.matmul_allow_tf32': ('matmul_allow_tf32', 'bool'),
    'numerics.cudnn_allow_tf32': ('cudnn_allow_tf32', 'bool'),
}
# Required-equal lock fields that no observed environment records. They are listed in every reading (never silently
# passed): the lock's own form, the historical pins below and the reader's separate pinned checks (training-machine
# preflight, shipped package, numerical environment, training configuration) are what hold them.
ENVIRONMENT_NOT_OBSERVED_ANYWHERE = tuple(path for path in ENVIRONMENT_LOCK_LEAVES if path not in ENVIRONMENT_OBSERVED)
# Observed keys that carry a predictive value; an envelope (diagnostic) field may never reuse one of their names.
ENVIRONMENT_PREDICTIVE_KEYS = frozenset([key for key, _ in ENVIRONMENT_OBSERVED.values()] + list(NUMERICAL_ENVIRONMENT)
                                        + list(ENVIRONMENT_RECORDED_NOT_PINNED))
# Revision 5: lock field -> the value this reader ALREADY pins from the public historical records (the Helm 2.0 seed-17
# receipt at c8d5c430 and its worker/requirements at 20208c92). A lock that contradicts one of them is refused, so the
# lock cannot replace a known historical value with another machine's value.
ENVIRONMENT_HISTORICAL_PINS = {
    'image.ami_id': HISTORICAL_AMI,
    'image.region': PREFLIGHT_PINS['region'],
    'accelerator.instance_type': PREFLIGHT_PINS['instance_type'],
    'runtime.os': NUMERICAL_ENVIRONMENT['platform_system'],
    'accelerator.gpu_model': NUMERICAL_ENVIRONMENT['gpu_name'],
    'libraries.torch': NUMERICAL_ENVIRONMENT['torch_version'],
    'libraries.cuda_runtime': NUMERICAL_ENVIRONMENT['cuda_version'],
    'numerics.deterministic_algorithms': NUMERICAL_ENVIRONMENT['deterministic_algorithms'],
    'numerics.matmul_allow_tf32': NUMERICAL_ENVIRONMENT['matmul_allow_tf32'],
    'numerics.cudnn_allow_tf32': NUMERICAL_ENVIRONMENT['cudnn_allow_tf32'],
}
ENVIRONMENT_HISTORICAL_VARIABLES = {'CUBLAS_WORKSPACE_CONFIG': NUMERICAL_ENVIRONMENT['cublas_workspace_config']}


class _Refused(ValueError):
    pass


def _unique_pairs(pairs):
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise _Refused('DUPLICATE_KEY')
    return dict(pairs)


def _no_constant(name):
    raise _Refused('NON_FINITE:' + name)


def strict_json_object(raw):
    """A JSON object from bytes, refusing duplicate keys and NaN/Infinity; None otherwise. Pure."""
    if type(raw) is not bytes:
        return None
    try:
        value = json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=_no_constant)
    except (ValueError, RecursionError):
        return None
    return value if type(value) is dict else None


def _normal(parts):
    parts = tuple(parts)
    while len(parts) > 1 and parts[-1] == 0:
        parts = parts[:-1]
    return parts


def parse_version(value):
    """'3.12.3' -> (3, 12, 3); trailing zero parts dropped ('12.8.0' == '12.8'). None when not a dotted number."""
    if type(value) is not str or re.fullmatch(r'\d{1,6}(\.\d{1,6}){0,5}', value) is None:
        return None
    return _normal(int(part) for part in value.split('.'))


def parse_torch_version(value):
    """'2.11.0+cu128' -> ((2, 11), 'cu128'): the release AND the build tag both count."""
    match = re.fullmatch(r'(\d{1,6}(?:\.\d{1,6}){0,5})(?:\+([A-Za-z0-9.]{1,32}))?', value) if type(value) is str \
        else None
    return None if match is None else (parse_version(match.group(1)), match.group(2) or '')


def parse_cudnn_version(value):
    """torch reports cuDNN as an int (91002 = 9.10.2; 8902 = 8.9.2); a lock writes '9.10.2'. Both parse to a tuple."""
    if type(value) is int and 0 < value < 10 ** 7:
        if value >= 90000:
            return _normal((value // 10000, value // 100 % 100, value % 100))
        return _normal((value // 1000, value // 100 % 10, value % 100))
    return parse_version(value)


def parse_environment_value(kind, value):
    """The comparable form of one value, or None when it cannot be parsed (never guessed)."""
    if kind == 'text':
        return value if type(value) is str and value else None
    if kind == 'bool':
        return value if type(value) is bool else None
    if kind == 'version':
        return parse_version(value)
    if kind == 'torch':
        return parse_torch_version(value)
    if kind == 'cudnn':
        return parse_cudnn_version(value)
    return None


def environment_lock_violations(raw):
    """`(violations, lock)` for the raw lock bytes. Unknown, duplicate, null or missing fields refuse (R3-I). Pure.

    Revision 5 (Codex R3-I, Q-G): `required_equal` lists EVERY lock field exactly once; `diagnostic_only` may name only
    declared envelope fields (`envelope.<name>`, each with a reason). A field whose historical value cannot be
    established holds ENVIRONMENT_UNESTABLISHED (an explicit blocker, read as ENVIRONMENT_ADMISSION_UNVERIFIED). A lock
    that contradicts a historical value this reader already pins is refused."""
    lock = strict_json_object(raw)
    if lock is None:
        return ['LOCK_NOT_A_STRICT_JSON_OBJECT'], None
    violations = []
    if sorted(lock) != list(ENVIRONMENT_LOCK_TOP):
        return ['LOCK_TOP_FIELDS'], None
    if lock['schema'] != ENVIRONMENT_LOCK_SCHEMA or lock['status'] != ENVIRONMENT_LOCK_STATUS \
            or not is_hex(lock['source_commit'], 40):
        violations.append('LOCK_SCHEMA_STATUS_OR_SOURCE_COMMIT')
    shaped = True
    for section, keys in ENVIRONMENT_LOCK_SHAPE.items():
        if type(lock[section]) is not dict or sorted(lock[section]) != sorted(keys):
            violations.append('LOCK_SECTION_FIELDS:' + section)
            shaped = False
            continue
        for key in keys:
            path, value = section + '.' + key, lock[section][key]
            if type(value) is str and value == ENVIRONMENT_UNESTABLISHED:
                continue                                  # an explicit blocker, read as UNVERIFIED by every source
            if path in ENVIRONMENT_BOOL_LEAVES:
                ok = type(value) is bool
            elif path in ENVIRONMENT_MAP_LEAVES:
                ok = type(value) is dict and all(type(name) is str and name and type(item) in (str, int)
                                                 and type(item) is not bool for name, item in value.items())
            elif path == 'libraries.packages':
                ok = (type(value) is list and value and all(
                    type(row) is dict and sorted(row) == ['name', 'sha256', 'version'] and type(row['name']) is str
                    and row['name'] and type(row['version']) is str and row['version'] and is_hex(row['sha256'], 64)
                    for row in value) and len({row['name'] for row in value}) == len(value))
            else:
                ok = type(value) is str and bool(value.strip())
            if not ok:
                violations.append('LOCK_VALUE:' + path)
            elif path in ENVIRONMENT_OBSERVED and parse_environment_value(ENVIRONMENT_OBSERVED[path][1], value) is None:
                violations.append('LOCK_VALUE_UNPARSEABLE:' + path)
    if shaped:
        violations.extend(environment_lock_historical_contradictions(lock))
    comparison = lock['comparison'] if type(lock['comparison']) is dict else {}
    required, diagnostic = comparison.get('required_equal'), comparison.get('diagnostic_only')
    if sorted(comparison) != ['diagnostic_only', 'required_equal'] or type(required) is not list \
            or type(diagnostic) is not list:
        return violations + ['LOCK_COMPARISON_FIELDS'], None
    if not all(type(path) is str for path in required) or not all(
            type(row) is dict and sorted(row) == ['path', 'reason'] and type(row['path']) is str
            and type(row['reason']) is str and row['reason'].strip() for row in diagnostic):
        return violations + ['LOCK_COMPARISON_ENTRY_FORM'], None
    missing = [path for path in ENVIRONMENT_REQUIRED_EQUAL if path not in required]
    if missing:
        violations.append('LOCK_REQUIRED_EQUAL_LACKS:' + ','.join(missing))
    if len(set(required)) != len(required) or any(path not in ENVIRONMENT_LOCK_LEAVES for path in required):
        violations.append('LOCK_REQUIRED_EQUAL_UNKNOWN_OR_DUPLICATE')
    paths = [row['path'] for row in diagnostic]
    not_envelope = [path for path in paths if not environment_envelope_path(path)]
    if not_envelope:
        violations.append('LOCK_DIAGNOSTIC_ONLY_MAY_NAME_ENVELOPE_FIELDS_ONLY:' + ','.join(not_envelope)[:300])
    if len(set(paths)) != len(paths):
        violations.append('LOCK_DIAGNOSTIC_ONLY_DUPLICATE')
    return violations, (lock if not violations else None)


def environment_envelope_path(path):
    """True for a declared envelope (diagnostic) field: `envelope.<name>`, never a lock field, never a name that an
    observed environment uses for a predictive value (driver, kernel, Python, cuDNN, ...). Pure."""
    return (type(path) is str and re.fullmatch(ENVIRONMENT_DIAGNOSTIC_PATTERN, path) is not None
            and path[len(ENVIRONMENT_DIAGNOSTIC_PREFIX):] not in ENVIRONMENT_PREDICTIVE_KEYS)


def environment_lock_historical_contradictions(lock):
    """Every lock field that contradicts a value this reader already pins from the historical records. Pure.
    (UNESTABLISHED is a contradiction here too: these values ARE established.)"""
    found = []
    for path, pinned in ENVIRONMENT_HISTORICAL_PINS.items():
        section, name = path.split('.')
        value = lock[section][name]
        if path in ENVIRONMENT_OBSERVED:
            kind = ENVIRONMENT_OBSERVED[path][1]
            ok = (parse_environment_value(kind, value) is not None
                  and parse_environment_value(kind, value) == parse_environment_value(kind, pinned))
        else:
            ok = same(value, pinned)
        if not ok:
            found.append('LOCK_CONTRADICTS_THE_HISTORICAL_PIN:' + path)
    variables = lock['numerics']['environment_variables']
    for name, pinned in ENVIRONMENT_HISTORICAL_VARIABLES.items():
        if not (type(variables) is dict and same(variables.get(name), pinned)):
            found.append('LOCK_CONTRADICTS_THE_HISTORICAL_PIN:numerics.environment_variables.' + name)
    return found


def environment_lock_unestablished(lock):
    """The lock fields whose historical value could not be established (each is an explicit blocker). Pure."""
    lock = lock if type(lock) is dict else {}
    found = []
    for path in ENVIRONMENT_LOCK_LEAVES:
        section, name = path.split('.')
        if type(lock.get(section)) is dict and lock[section].get(name) == ENVIRONMENT_UNESTABLISHED:
            found.append(path)
    return found


def _shown(value):
    return value if type(value) in (str, int, bool) else None


def environment_lock_comparison(lock, observed, source, *, must_observe):
    """`(invalid, diagnostic, not_observed)` for ONE observed environment against a valid lock. Pure.

    Revision 5: every lock field is required-equal. A field that differs, or cannot be parsed, is INVALID. A field the
    source does not record is INVALID when `must_observe` (the evidence and the P1b acceptance record every field by
    construction) and only reported otherwise (the historical training receipts never recorded Python or cuDNN; the
    lock, frozen from the public historical records, carries those values). A field the lock marks UNESTABLISHED is
    INVALID for every source (ENVIRONMENT_ADMISSION_UNVERIFIED): the observed value is shown for disclosure but is never
    compared with anything or accepted in place of the historical value. Declared envelope fields are reported only."""
    observed = observed if type(observed) is dict else {}
    invalid, diagnostic, not_observed = [], [], []
    for path in ENVIRONMENT_LOCK_LEAVES:
        section, name = path.split('.')
        key, kind = ENVIRONMENT_OBSERVED.get(path, (None, None))
        if lock[section][name] == ENVIRONMENT_UNESTABLISHED:
            invalid.append(ENVIRONMENT_UNVERIFIED + ':' + source + ':' + path)
            if key is not None and key in observed:
                diagnostic.append({'source': source, 'path': path, 'lock': ENVIRONMENT_UNESTABLISHED,
                                   'observed': _shown(observed[key]), 'accepted': False})
            continue
        if key is None:
            continue                                      # listed once per reading: ENVIRONMENT_NOT_OBSERVED_ANYWHERE
        if key not in observed:
            if must_observe:
                invalid.append('ENVIRONMENT_NOT_OBSERVED:' + source + ':' + path)
            else:
                not_observed.append(source + ':' + path)
            continue
        expected = parse_environment_value(kind, lock[section][name])
        found = parse_environment_value(kind, observed[key])
        if found is None or found != expected:
            invalid.append(('ENVIRONMENT_UNPARSEABLE:' if found is None else 'ENVIRONMENT_DIFFERS_FROM_LOCK:')
                           + source + ':' + path)
    for row in lock['comparison']['diagnostic_only']:
        name = row['path'][len(ENVIRONMENT_DIAGNOSTIC_PREFIX):]
        if name in observed:
            diagnostic.append({'source': source, 'path': row['path'], 'observed': _shown(observed[name]),
                               'reason': row['reason']})
    return invalid, diagnostic, not_observed


# ---------------------------------------------------------------------------------------------------------------------
# Revision 5 (Codex Q-F): the FROZEN eligibility rule. `READING_ELIGIBILITY_RULE.json` is committed before U17 launches
# and is a reader source, so the reader fingerprint covers it. It fixes every value that is known now, names every
# piece of evidence that is appended later, and states what is never rewritten. It holds no reader, policy or owner-
# record hash (no hash cycle). This code and the rule must agree exactly, or nothing runs (checked at import, like the
# pins and the allowlist). An absent rule refuses every eligibility record (fail closed).
# ---------------------------------------------------------------------------------------------------------------------
ELIGIBILITY_FIXED = {
    'schema': ELIGIBILITY_SCHEMA, 'label': LABEL, 'state': ELIGIBLE, 'chronology': ELIGIBILITY_CHRONOLOGY,
    'job': FROZEN_JOB, 'job_kind': JOB_KIND, 'model_seed': MODEL_SEED, 'source_sha': SOURCE_SHA,
    'launch_basis': LAUNCH_BASIS,
    'frozen_study': {'commit': FREEZE_COMMIT, 'path': GIT_PREFIX + HERE_REL + '/frozen/study.json',
                     'sha256': FROZEN_STUDY_SHA256},
    'execution_admission_as_is': {'path': GIT_PREFIX + ADMISSION_REL, 'sha256': FROZEN_ADMISSION_SHA256,
                                  'state': NOT_READY},
    'decide_source_sha256': FROZEN_DECIDE_SHA256,
    'owner_direction_record': dict(OWNER_DIRECTION),
    'panel_manifest_sha256': PANEL_MANIFEST_SHA256,
    'numerical_environment_sha256': value_digest(NUMERICAL_ENVIRONMENT),
    'writer_blobs': dict(WRITER_BLOBS_AT_FREEZE),
}
ELIGIBILITY_FIELDS = tuple(sorted(set(ELIGIBILITY_FIXED) | set(ELIGIBILITY_APPENDED)))
ELIGIBILITY_RULE_TOP = ('appended_later', 'decide_unchanged', 'decisions', 'environment_rule', 'fixed_now', 'label',
                        'never', 'order', 'preserved_never_rewritten', 'record', 'schema', 'status', 'study')
ELIGIBILITY_RULE_EXACT = ('fixed_now', 'record')                 # compared exactly; the other sections carry prose
DECISION_FIELDS = ('blob', 'branch', 'by', 'commit', 'items', 'path')


def _prose(value):
    return type(value) is str and bool(value.strip()) and value.isascii() and '\n' not in value


def eligibility_rule_expected():
    """The machine part of the frozen rule, exactly as this code implements it (prose `statement`s excluded). Pure."""
    return {
        'record': {'path': ELIGIBILITY_REL, 'schema': ELIGIBILITY_SCHEMA, 'state': ELIGIBLE,
                   'chronology': ELIGIBILITY_CHRONOLOGY, 'committed_versions': 1, 'fields': list(ELIGIBILITY_FIELDS)},
        'fixed_now': ELIGIBILITY_FIXED,
        'preserved_never_rewritten': {'freeze_commit': FREEZE_COMMIT, 'frozen_files': list(FROZEN_FILES),
                                      'execution_admission': ADMISSION_REL, 'execution_admission_state': NOT_READY},
        'decide_unchanged': {'file': 'read_reproduction.py', 'function': 'decide',
                             'source_sha256_at_freeze': FROZEN_DECIDE_SHA256},
        'environment_rule': {'lock_schema': ENVIRONMENT_LOCK_SCHEMA,
                             'required_equal': list(ENVIRONMENT_REQUIRED_EQUAL),
                             'diagnostic_only_pattern': ENVIRONMENT_DIAGNOSTIC_PATTERN,
                             'unestablished_value': ENVIRONMENT_UNESTABLISHED,
                             'unestablished_reads': ENVIRONMENT_UNVERIFIED,
                             'lock_committed_before_p1b_acceptance': True},
    }


def eligibility_rule_violations(rule):
    """Every way a parsed rule is not the frozen rule this code implements. Pure."""
    if type(rule) is not dict:
        return ['RULE_NOT_A_STRICT_JSON_OBJECT']
    if sorted(rule) != list(ELIGIBILITY_RULE_TOP):
        return ['RULE_TOP_FIELDS']
    violations = []
    if not (rule['schema'] == ELIGIBILITY_RULE_SCHEMA and rule['label'] == LABEL
            and rule['status'] == ELIGIBILITY_RULE_STATUS and rule['study'] == STUDY_NAME):
        violations.append('RULE_SCHEMA_LABEL_STATUS_OR_STUDY')
    for name, expected in eligibility_rule_expected().items():
        section = rule[name]
        if name in ELIGIBILITY_RULE_EXACT:
            ok = same(section, expected)
        else:
            ok = (type(section) is dict and _prose(section.get('statement'))
                  and same({key: value for key, value in section.items() if key != 'statement'}, expected))
        if not ok:
            violations.append('RULE_SECTION:' + name)
    appended = rule['appended_later']
    if not (type(appended) is list
            and [row.get('field') if type(row) is dict else None for row in appended] == list(ELIGIBILITY_APPENDED)
            and all(sorted(row) == ['evidence', 'field'] and _prose(row['evidence']) for row in appended)):
        violations.append('RULE_APPENDED_LATER')
    decisions = rule['decisions']
    if not (type(decisions) is list and decisions and all(
            type(row) is dict and sorted(row) == list(DECISION_FIELDS) and _prose(row['by'])
            and _branch(row['branch']) and _hex(row['commit'], 40) and _hex(row['blob'], 40)
            and _relative_path(row['path']) and type(row['items']) is list and row['items']
            and all(_prose(item) for item in row['items']) for row in decisions)):
        violations.append('RULE_DECISIONS')
    for name in ('order', 'never'):
        if not (type(rule[name]) is list and rule[name] and all(_prose(line) for line in rule[name])):
            violations.append('RULE_PROSE_LIST:' + name)
    return violations


def load_eligibility_rule(raw):
    """The parsed frozen rule; None when the file is absent (every eligibility record is then refused). A present but
    non-conforming rule stops at import: this code and the frozen rule must agree exactly."""
    if raw is None:
        return None
    rule = strict_json_object(raw)
    violations = eligibility_rule_violations(rule)
    if violations:
        raise SystemExit('UNCHANGED_REPRO_ELIGIBILITY_RULE_INVALID:' + '|'.join(violations)[:600])
    return rule


ELIGIBILITY_RULE_PATH = HERE / ELIGIBILITY_RULE_NAME
ELIGIBILITY_RULE_RAW = ELIGIBILITY_RULE_PATH.read_bytes() if ELIGIBILITY_RULE_PATH.is_file() else None
ELIGIBILITY_RULE_SHA256 = digest(ELIGIBILITY_RULE_RAW) if ELIGIBILITY_RULE_RAW is not None else None
ELIGIBILITY_RULE = load_eligibility_rule(ELIGIBILITY_RULE_RAW)


def attestation_violations(attestation):
    """The runner's attestation (Codex Q-F): who attests, that this rule was on the U17 launch checkout before U17
    launched, and WHICH deciding outputs (if any) were viewed before this record. A viewed output is disclosed, never a
    reason to revise eligibility; it is printed in the reading. Pure."""
    if not (type(attestation) is dict and sorted(attestation) == list(ATTESTATION_FIELDS)):
        return ['RUNNER_ATTESTATION_FORM']
    violations = []
    if not (_prose(attestation['attester']) and _prose(attestation['statement'])):
        violations.append('RUNNER_ATTESTATION_ATTESTER_OR_STATEMENT')
    viewed = attestation['deciding_outputs_viewed']
    if not (type(viewed) is list and all(_prose(item) for item in viewed) and len(set(viewed)) == len(viewed)):
        violations.append('RUNNER_ATTESTATION_VIEWED_LIST_FORM')
    if attestation['rule_on_launch_checkout_before_u17_launch'] is not True:
        violations.append('RULE_WAS_NOT_ON_THE_LAUNCH_CHECKOUT_BEFORE_U17_LAUNCH')
    return violations


def is_historical_refusal(message):
    """True only for a COMPLETE message on the published historical allowlist (revision 4, Codex R3-B). Pure.

    The caller passes the whole message, never a truncated display: a coded prefix followed by added prose, a newline
    or a CUDA fault is not on the allowlist, so it is an infrastructure fault (INVALID), never a model refusal."""
    if not (type(message) is str and 0 < len(message) <= REFUSAL_MESSAGE_MAX and message.isascii()
            and re.fullmatch(HISTORICAL_REFUSAL_PATTERN, message) is not None):
        return False
    return message in REFUSAL_EXACT or any(pattern.fullmatch(message) for pattern in REFUSAL_PATTERNS)


def preflight_violations(preflight):
    """Every pinned training-machine field (AMI, instance type, region) the receipt's preflight.json does not match."""
    preflight = preflight if type(preflight) is dict else {}
    return [key + '=' + str(preflight.get(key))[:60] for key, value in PREFLIGHT_PINS.items()
            if not same(preflight.get(key), value)]


def shipped_package_violations(raw):
    """The package a receipt says it shipped must be the pinned archive blob, carrying the pinned requirements file."""
    if type(raw) is not bytes:
        return ['SHIPPED_PACKAGE_ABSENT']
    violations = []
    if git_object_id(raw) != PACKAGE_BLOBS['source.zip'] or len(raw) != ARCHIVE_BYTES:
        violations.append('SHIPPED_PACKAGE_IS_NOT_THE_PINNED_ARCHIVE')
    try:
        with ZipFile(io.BytesIO(raw)) as bundle:
            requirements = bundle.read(REQUIREMENTS_MEMBER)
    except (BadZipFile, KeyError, ValueError):
        return violations + ['SHIPPED_PACKAGE_HAS_NO_REQUIREMENTS_MEMBER']
    if digest(requirements) != REQUIREMENTS_GPU_SHA256:
        violations.append('SHIPPED_REQUIREMENTS_SHA256:' + digest(requirements))
    return violations


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
# The policy (Codex; pinned in policy_pins.json): pins, conformance, currency at the fetched branch tips.
# ---------------------------------------------------------------------------------------------------------------------
def policy_pointers():
    return {'commit': POLICY_COMMIT, 'branch': POLICY_BRANCH,
            'pins': {'path': GIT_PREFIX + PINS_REL, 'sha256': PINS_SHA256},
            'files': {name: {'path': GIT_PREFIX + relative, 'blob': blob, 'sha256': sha, 'bytes': size}
                      for name, (relative, blob, sha, size) in POLICY_FILES.items()}}


def evidence_policy_block():
    """What an evidence file (and so its producer) must say about the policy it was made under. Revision 3 adds the
    sha256 of `policy_pins.json`, so evidence made under other pins is invalid."""
    return {'commit': POLICY_COMMIT, 'reproduction_policy_json_sha256': POLICY_FILES['reproduction_policy_json'][2],
            'policy_pins_sha256': PINS_SHA256}


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


def tip_watch():
    """`{branch: {'commits': [pinned commits], 'files': {name: (path, blob)}}}`: every pinned file on its own branch.

    Revision 3 (review NOTE 12): the three owner records are watched too, not only the policy files, so a later owner
    record at a branch tip (a withdrawal, say) stops `--write` and `--check` until a reviewed re-pin. Pure.
    """
    watch = {}

    def add(branch, commit, name, relative, blob):
        entry = watch.setdefault(branch, {'commits': [], 'files': {}})
        if commit not in entry['commits']:
            entry['commits'].append(commit)
        entry['files'][name] = (relative, blob)
    for name, (relative, blob, _, _) in POLICY_FILES.items():
        add(POLICY_BRANCH, POLICY_COMMIT, name, relative, blob)
    for name, (commit, relative, blob, _) in OWNER_RECORDS.items():
        add(OWNER_RECORD_BRANCHES.get(name, POLICY_BRANCH), commit, 'owner:' + name, relative, blob)
    return watch


def policy_tip_violations(tips):
    """Every pinned file that moved at its fetched branch tip, or a tip that does not contain a pinned commit. Pure."""
    violations = []
    tips = tips if type(tips) is dict else {}
    for branch, entry in tip_watch().items():
        tip = tips.get(branch)
        if type(tip) is not dict or tip.get('commit') is None:
            violations.append('TRACKING_REF_MISSING:' + tracking_ref(branch))
            continue
        blobs = tip.get('blobs') if type(tip.get('blobs')) is dict else {}
        for name, (_, blob) in entry['files'].items():
            if blobs.get(name) != blob:
                violations.append('MOVED_AT_TIP:' + name + ':' + str(blobs.get(name)))
        if tip.get('pinned_commits_are_ancestors') is not True:
            violations.append('PINNED_COMMIT_NOT_IN_TIP:' + branch)
    return violations


def read_policy_tips(stop, *, fetch):
    """Fetch each watched branch (explicit refspec, remote-tracking ref only), then read each pinned file's blob."""
    tips = {}
    for branch, entry in tip_watch().items():
        if fetch:
            try:
                git(*fetch_args(branch))
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
                stop(False, 'POLICY_TIP_NOT_FETCHED:run `git ' + ' '.join(fetch_args(branch))
                     + '` by hand; if it fails, stop')
        ref = tracking_ref(branch)
        if not git_ok('rev-parse', '--verify', '--quiet', ref + '^{commit}'):
            tips[branch] = {'ref': ref, 'commit': None, 'blobs': {}, 'pinned_commits_are_ancestors': False}
            continue
        commit = git('rev-parse', ref + '^{commit}').decode('ascii').strip()
        tips[branch] = {'ref': ref, 'commit': commit,
                        'blobs': {name: blob_id(commit, relative) if has_object(commit, relative) else None
                                  for name, (relative, _) in entry['files'].items()},
                        'pinned_commits_are_ancestors': all(git_ok('merge-base', '--is-ancestor', pinned, commit)
                                                            for pinned in entry['commits'])}
    return tips


def check_policy(stop, *, fetch=True, require_current=True):
    """STOP unless the pinned policy files are intact, conformed and consistent with LAUNCH_REQUEST.

    Currency at the fetched branch tips STOPS only when `require_current` (the --write and --check paths). Policy:
    "A changed plan invalidates affected technical admission evidence" -- the admission, not preparation -- so the
    preparation-only path reports a moved tip and carries on.
    """
    files = read_policy_files(stop)
    loaded = {name: json.loads(files[name]) for name in ('reproduction_policy_json', 'execution_manifest',
                                                         'launch_request')}
    violations = (policy_conformance(loaded['reproduction_policy_json'])
                  + launch_request_violations(loaded['launch_request']))
    stop(not violations, 'POLICY_IS_NOT_THE_RULE_THE_READER_IMPLEMENTS:' + '|'.join(violations)[:1500])
    tips = read_policy_tips(stop, fetch=fetch)
    moved = policy_tip_violations(tips)
    if require_current:
        stop(not moved, 'POLICY_OR_PLAN_MOVED:' + '|'.join(moved)[:1500] + ':a changed plan, policy or owner record '
             'invalidates the technical admission; re-pin policy_pins.json after review')
    return {'pointers': policy_pointers(), 'policy': loaded['reproduction_policy_json'],
            'manifest': loaded['execution_manifest'], 'launch_request': loaded['launch_request'],
            'tip': {'tips': {branch: {'ref': tip['ref'], 'commit': tip['commit']} for branch, tip in tips.items()},
                    'violations': moved}}


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
            'policy_pins_sha256': PINS_SHA256,
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


def load_object(raw):
    """A JSON object from bytes, or None."""
    if type(raw) is not bytes:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    return value if type(value) is dict else None


def _label_value(level, label):
    """A level label back to its value: the identical word -> True, the different word -> False, else None."""
    words = LEVEL_LABELS.get(level)
    if words is None or label not in words:
        return None
    return label == words[0]


def acceptance_case_violations(case):
    """Revision 4, fix 7: ONE acceptance case against the frozen table `ACCEPTANCE_EXPECTED`. Pure.

    The producer's `pass` is never trusted. The reader re-derives the outcome from the case's OBSERVED fields: the
    observed verdict must be `decide()` of the observed validity and levels (a second, independent derivation), and it
    must equal the registered verdict, with every registered level. `pass` must then agree with that derivation."""
    name = case.get('case') if type(case) is dict else None
    expected = ACCEPTANCE_EXPECTED.get(name)
    if expected is None:
        return ['CASE_NOT_REGISTERED:' + str(name)[:40]]
    if 'status' in expected:                                    # changed_buffer: VACUOUS with a printed zero count
        ok = (case.get('status') == expected['status'] and case.get('reference_buffers') == []
              and type(case.get('reference_buffer_count')) is int
              and case.get('reference_buffer_count') == expected['reference_buffer_count']
              and type(case.get('why')) is str and bool(case['why'].strip()) and case.get('pass') is True)
        return [] if ok else ['CHANGED_BUFFER_NOT_RECORDED_AS_VACUOUS_WITH_NO_BUFFERS']
    violations = []
    if case.get('expected_verdict') != expected['verdict'] or not same(case.get('expected_levels'),
                                                                        expected['levels']):
        violations.append('CASE_EXPECTATION_IS_NOT_THE_FROZEN_TABLE:' + name)
    labels = case.get('observed_levels') if type(case.get('observed_levels')) is dict else {}
    reasons = case.get('invalid_reasons')
    if sorted(labels) != sorted(LEVEL_LABELS) or type(reasons) is not list \
            or case.get('observed_verdict') not in VERDICTS:
        return violations + ['CASE_OBSERVED_FIELDS_MALFORMED:' + name]
    values = {level: _label_value(level, labels[level]) for level in LEVEL_LABELS}
    valid = not reasons
    derived = (INVALID_STOP if not valid else
               INVALID_STOP if any(values[level] is None for level in LEVEL_LABELS) else
               REPRODUCED if values['learned_state'] and values['output'] else DOES_NOT_REPRODUCE)
    if derived != case['observed_verdict']:
        violations.append('CASE_VERDICT_IS_NOT_DERIVED_FROM_ITS_OBSERVED_FIELDS:' + name)
    outcome = (case['observed_verdict'] == expected['verdict']
               and all(values[level] is value for level, value in expected['levels'].items()))
    if not outcome:
        violations.append('CASE_OBSERVED_IS_NOT_THE_REGISTERED_OUTCOME:' + name)
    if case.get('pass') is not outcome:
        violations.append('CASE_PASS_FIELD_CONTRADICTS_THE_OBSERVED_FIELDS:' + name)
    return violations


def acceptance_receipt_violations(document, expected_bindings, environment_lock=None):
    """The P1 receipt: READER_ACCEPTANCE_PASS, every registered case in order, each case's OBSERVED fields equal to the
    frozen table (revision 4, fix 7), made by THIS reader, in the pinned (and, when given, the locked) environment."""
    if type(document) is not dict:
        return ['NOT_A_JSON_OBJECT']
    violations = []
    if document.get('schema') != ACCEPTANCE_SCHEMA or document.get('label') != LABEL:
        violations.append('SCHEMA_OR_LABEL')
    if document.get('status') != ACCEPTANCE_PASS:
        violations.append('STATUS:' + str(document.get('status'))[:60])
    cases = document.get('cases') if type(document.get('cases')) is list else []
    if [case.get('case') if type(case) is dict else None for case in cases] != list(ACCEPTANCE_CASES):
        violations.append('CASE_SET_OR_ORDER')
    found = [item for case in cases for item in acceptance_case_violations(case)]
    if not cases or found or not all(type(case) is dict and case.get('pass') is True for case in cases):
        violations.append('A_CASE_DID_NOT_PASS')
    violations.extend(item for item in found if item.startswith('CHANGED_BUFFER'))
    violations.extend('CASE:' + item for item in found if not item.startswith('CHANGED_BUFFER'))
    if environment_lock is not None:
        invalid, _, _ = environment_lock_comparison(environment_lock, document.get('environment'), 'P1B_ACCEPTANCE',
                                                    must_observe=True)
        violations.extend('ENVIRONMENT_LOCK:' + item for item in invalid)
    producer = document.get('producer') if type(document.get('producer')) is dict else {}
    if not (same(producer.get('sources_sha256'), expected_bindings.get('reader_sources_sha256'))
            and producer.get('reader_source_sha256') == expected_bindings.get('reader_source_sha256')):
        violations.append('NOT_MADE_BY_THE_ADMITTED_READER')
    if document.get('panel_manifest_sha256') != PANEL_MANIFEST_SHA256:
        violations.append('PANEL_MANIFEST')
    if (document.get('numerical_environment_sha256') != environment_digest()
            or environment_violations(document.get('environment')) or document.get('environment_violations') != []):
        violations.append('ENVIRONMENT')
    return violations


def policy_receipt_violations(document, entry, policy):
    """The frozen-policy prerequisite's receipt IS the pinned REPRODUCTION_POLICY.json at the pinned commit. Pure."""
    violations = []
    if (entry.get('receipt_commit') != POLICY_COMMIT
            or entry.get('receipt_path') != POLICY_FILES['reproduction_policy_json'][0]):
        violations.append('NOT_THE_PINNED_POLICY_FILE')
    if type(document) is not dict or not same(document, policy):
        violations.append('NOT_THE_POLICY_THE_GATE_READ')
    return violations


def manifest_freeze(manifest):
    return manifest['final_freeze'] if type(manifest) is dict and type(manifest.get('final_freeze')) is dict else {}


def environment_receipt_violations(raw, manifest):
    """The environment-lock receipt is the file the manifest's final freeze names, with dependencies frozen. Pure."""
    violations = []
    if manifest_freeze(manifest).get('dependency_lock_sha256') != digest(raw):
        violations.append('NOT_THE_DEPENDENCY_LOCK_THE_MANIFEST_NAMES')
    dependencies = manifest.get('dependencies') if type(manifest) is dict else None
    status = dependencies.get('status') if type(dependencies) is dict else None
    if type(status) is not str or status.startswith('NOT_READY'):
        violations.append('MANIFEST_DEPENDENCIES_STATUS:' + str(status)[:60])
    return violations


def packet_receipt_violations(raw, manifest):
    """The launch-packet receipt is the file the manifest's final freeze names. Pure."""
    if manifest_freeze(manifest).get('frozen_launch_packet_sha256') != digest(raw):
        return ['NOT_THE_PACKET_THE_MANIFEST_NAMES']
    return []


def spend_violations(text):
    """`(violations, summary)`: measured spend so far + $15.00 <= $60.00. The arithmetic is done here. Pure."""
    if not (type(text) is str and re.fullmatch(r'\d{1,4}(\.\d{1,2})?', text) is not None):
        return ['SPEND_FIGURE_FORM:' + str(text)[:40]], None
    try:
        spent = Decimal(text)
    except InvalidOperation:
        return ['SPEND_FIGURE_FORM:' + text], None
    after = spent + Decimal(PER_JOB_USD)
    summary = {'spend_so_far_usd': str(spent), 'per_job_bound_usd': PER_JOB_USD,
               'after_this_job_at_most_usd': str(after), 'ceiling_usd': CEILING_USD}
    if after > Decimal(CEILING_USD):
        return ['SPEND_SO_FAR_PLUS_PER_JOB_BOUND_EXCEEDS_CEILING:' + str(after) + '>' + CEILING_USD], summary
    return [], summary


def utc_instant(text):
    """A UTC timestamp 'YYYY-MM-DDTHH:MM:SS[.ffffff]Z' as an aware datetime, or None. Pure."""
    if type(text) is not str or re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z', text) is None:
        return None
    try:
        return datetime.strptime(text[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def spend_record_violations(document, job, *, opened_sources=None, admitted_utc=None):
    """`(violations, summary)` for the budget receipt: a committed spend record for THIS job, figure read from it.

    Revision 4 (reader review fix 4): every source names a commit and the gatherer OPENS its committed blob
    (`opened_sources`, one raw bytes-or-None per source, in order); each must exist and match its sha256. Freshness:
    `measured_utc` is at most SPEND_FRESHNESS_SECONDS before, and never after, the admission time `admitted_utc`."""
    if type(document) is not dict:
        return ['NOT_A_JSON_OBJECT'], None
    violations = []
    if (sorted(document) != list(SPEND_RECORD_FIELDS) or document.get('schema') != SPEND_RECORD_SCHEMA
            or document.get('label') != LABEL or document.get('study') != STUDY_NAME):
        violations.append('SCHEMA_FIELDS_LABEL_OR_STUDY')
    if stamp_of(document.get('job')) is None or document.get('job') != job:
        violations.append('FOR_ANOTHER_JOB:' + str(document.get('job'))[:80])
    measured = utc_instant(document.get('measured_utc'))
    if measured is None:
        violations.append('MEASURED_UTC')
    if not (type(document.get('basis')) is str and document['basis'].strip()):
        violations.append('BASIS')
    sources = document.get('sources')
    if not (type(sources) is list and sources and all(
            type(item) is dict and sorted(item) == list(SPEND_SOURCE_FIELDS) and _hex(item['commit'], 40)
            and _relative_path(item['path']) and _hex(item['sha256'], 64) for item in sources)):
        violations.append('SOURCES')
    else:
        opened = opened_sources if type(opened_sources) is list else []
        for index, item in enumerate(sources):
            raw = opened[index] if index < len(opened) else None
            if type(raw) is not bytes:
                violations.append('SOURCE_NOT_OPENED_AS_A_COMMITTED_ANCHORED_BLOB:%d' % index)
            elif digest(raw) != item['sha256']:
                violations.append('SOURCE_SHA256:%d' % index)
    admitted = utc_instant(admitted_utc)
    if measured is not None:
        if admitted is None:
            violations.append('FRESHNESS_NOT_ESTABLISHED:NO_ADMISSION_TIME')
        elif measured > admitted:
            violations.append('MEASURED_AFTER_THE_ADMISSION')
        elif (admitted - measured).total_seconds() > SPEND_FRESHNESS_SECONDS:
            violations.append('STALE:%d_SECONDS' % int((admitted - measured).total_seconds()))
    found, summary = spend_violations(document.get('measured_spend_so_far_usd'))
    return violations + found, summary


def closure_blobs(folder=None):
    """`{name: git blob id}` of every REVIEW_CLOSURE_FILES member as it sits on disk here (None when absent)."""
    folder = HERE if folder is None else Path(folder)
    return {name: git_object_id((folder / name).read_bytes()) if (folder / name).is_file() else None
            for name in REVIEW_CLOSURE_FILES}


def review_receipt_violations(document, expected_bindings, facts=None):
    """A fresh reviewer's machine verdict on THIS reader revision and THESE pins. Prose is never read. Pure.

    Revision 4 (reader review fix 5, Codex R3-H). `facts` are git facts gathered by `review_facts`: whether the reviewed
    commit resolves and is reachable from the freshly fetched tip of `reviewed_branch`, the closure blobs AT the
    reviewed commit, the closure blobs running here, and (after a freeze) the writer blobs at the freeze commit. The
    stated closure must equal all of them; no BLOCKER or MAJOR finding may be open."""
    if type(document) is not dict:
        return ['NOT_A_JSON_OBJECT']
    violations = []
    if (sorted(document) != list(REVIEW_RECEIPT_FIELDS) or document.get('schema') != REVIEW_RECEIPT_SCHEMA
            or not (type(document.get('label')) is str and document['label'].strip())):
        violations.append('SCHEMA_FIELDS_OR_LABEL')
    if document.get('verdict') != REVIEW_PASS:
        violations.append('VERDICT:' + str(document.get('verdict'))[:60])
    findings = document.get('unresolved_findings')
    if not (type(findings) is list and all(
            type(item) is dict and sorted(item) == ['execution_consequence', 'id', 'severity']
            and type(item['id']) is str and item['id'] and item['severity'] in REVIEW_SEVERITIES
            and type(item['execution_consequence']) is str and item['execution_consequence'].strip()
            for item in findings)):
        violations.append('UNRESOLVED_FINDINGS_FORM')
    else:
        violations.extend('UNRESOLVED_BLOCKING_FINDING:' + item['id'][:40] for item in findings
                          if item['severity'] in REVIEW_BLOCKING_SEVERITIES)
    if not _branch(document.get('reviewed_branch')):
        violations.append('REVIEWED_BRANCH')
    provenance = document.get('reviewer_provenance')
    if not (type(provenance) is dict and sorted(provenance) == ['reference', 'source']
            and all(type(value) is str and value.strip() for value in provenance.values())):
        violations.append('REVIEWER_PROVENANCE')
    if document.get('attribution') != {'builder': LABEL, 'independence': INDEPENDENCE_LABEL}:
        violations.append('ATTRIBUTION')
    if not (type(document.get('scope')) is str and document['scope'].strip()):
        violations.append('SCOPE')
    closure = document.get('closure')
    if not (type(closure) is dict and sorted(closure) == sorted(REVIEW_CLOSURE_FILES)
            and all(_hex(value, 40) for value in closure.values())):
        violations.append('CLOSURE_FORM')
        closure = None
    if type(facts) is not dict:
        violations.append('REVIEW_FACTS_NOT_GATHERED')
    else:
        if facts.get('reviewed_commit_resolves') is not True:
            violations.append('REVIEWED_COMMIT_NOT_RESOLVED')
        if facts.get('reviewed_commit_pushed') is not True:
            violations.append('REVIEWED_COMMIT_NOT_ON_THE_FETCHED_REVIEWED_BRANCH')
        if closure is not None:
            at_commit = facts.get('closure_at_reviewed_commit') or {}
            running = facts.get('closure_running') or {}
            violations.extend('CLOSURE_IS_NOT_THE_REVIEWED_COMMIT:' + name for name in REVIEW_CLOSURE_FILES
                              if at_commit.get(name) != closure[name])
            violations.extend('CLOSURE_IS_NOT_WHAT_RUNS_HERE:' + name for name in REVIEW_CLOSURE_FILES
                              if running.get(name) != closure[name])
            at_freeze = facts.get('writer_blobs_at_freeze')
            if at_freeze is not None:
                violations.extend('WRITER_IS_NOT_THE_ONE_THAT_WROTE_THE_FREEZE:' + name for name in WRITER_FILES
                                  if (at_freeze or {}).get(name) != closure[name])
    if not (same(document.get('reviewed_reader_sources_sha256'), expected_bindings.get('reader_sources_sha256'))
            and document.get('reviewed_reader_source_sha256') == expected_bindings.get('reader_source_sha256')):
        violations.append('NOT_THIS_READER_REVISION')
    if document.get('reviewed_policy_pins_sha256') != expected_bindings.get('policy_pins_sha256'):
        violations.append('NOT_THESE_POLICY_PINS')
    if document.get('reviewed_panel_manifest_sha256') != PANEL_MANIFEST_SHA256:
        violations.append('NOT_THIS_PANEL')
    if not (same(document.get('job_kind'), JOB_KIND) and same(document.get('model_seed'), MODEL_SEED)):
        violations.append('NOT_THIS_JOB_KIND')
    if not _hex(document.get('reviewed_commit'), 40):
        violations.append('REVIEWED_COMMIT')
    reviewer = document.get('reviewer')
    if not (type(reviewer) is str and reviewer.strip()) or reviewer == RUNNER:
        violations.append('REVIEWER_NOT_NAMED_OR_IS_THE_BUILDER')
    return violations


def prerequisite_violations(prerequisites, receipts, *, expected_bindings, policy, manifest, job, admitted_utc=None):
    """`(reasons, spend)`. Each prerequisite must be PASS AND its committed receipt must check out. Pure.

    `receipts` is `read_prerequisite_receipts`' output: `{name: {'commit', 'path', 'raw'}}`, one entry only for a receipt
    that git holds at a commit anchored in HEAD's (or the receipt commit's) history or the pinned policy commit's.
    Revision 4: the budget entry also carries `'sources'` (each source's opened committed bytes, or None) and the
    review entry carries `'facts'` (`review_facts`); `admitted_utc` is the admission time the spend must be fresh for.
    """
    reasons, spend = [], None
    prerequisites = prerequisites if type(prerequisites) is dict else {}
    receipts = receipts if type(receipts) is dict else {}
    if set(prerequisites) != set(REQUIRED_PREREQUISITES):
        reasons.append('ADMISSION_PREREQUISITE_SET')
    for name in REQUIRED_PREREQUISITES:
        entry = prerequisites.get(name) if type(prerequisites.get(name)) is dict else {}
        if sorted(entry) != list(PREREQUISITE_FIELDS):
            reasons.append('PREREQUISITE_FIELDS:' + name)
        if entry.get('status') != PREREQUISITE_PASS or not is_hex(entry.get('receipt_sha256'), 64):
            reasons.append('PREREQUISITE_NOT_PASSED:' + name)
            continue
        receipt = receipts.get(name) if type(receipts.get(name)) is dict else {}
        raw = receipt.get('raw')
        if (type(raw) is not bytes or receipt.get('commit') != entry.get('receipt_commit')
                or receipt.get('path') != entry.get('receipt_path')):
            reasons.append('PREREQUISITE_RECEIPT_NOT_A_COMMITTED_ANCHORED_BLOB:' + name)
            continue
        if digest(raw) != entry['receipt_sha256']:
            reasons.append('PREREQUISITE_RECEIPT_SHA256:' + name)
            continue
        found, summary = [], None
        if name == 'reader_acceptance_on_aws_p1':
            found = acceptance_receipt_violations(load_object(raw), expected_bindings)
        elif name == 'reproduction_policy_frozen_with_panel_and_reader':
            found = policy_receipt_violations(load_object(raw), entry, policy)
        elif name == 'numerical_environment_frozen':
            found = environment_receipt_violations(raw, manifest)
        elif name == 'final_launch_packet_frozen':
            found = packet_receipt_violations(raw, manifest)
        elif name == 'budget_headroom_verified':
            found, summary = spend_record_violations(load_object(raw), job, opened_sources=receipt.get('sources'),
                                                     admitted_utc=admitted_utc)
        elif name == 'fresh_review_of_this_revision':
            found = review_receipt_violations(load_object(raw), expected_bindings, receipt.get('facts'))
        else:                                           # a name added to REQUIRED_PREREQUISITES without a checker
            found = ['NO_CHECKER']
        reasons.extend('PREREQUISITE_RECEIPT:' + name + ':' + item for item in found)
        if name == 'budget_headroom_verified' and not found:
            spend = summary
    return reasons, spend


def anchored_blob(commit, path, anchors):
    """Impure. The committed bytes at `commit:path` ONLY when `commit` is an ancestor of (or equal to) an anchor."""
    if not (is_hex(commit, 40) and _relative_path(path)):
        return None
    if not any(git_ok('merge-base', '--is-ancestor', commit, anchor) for anchor in anchors):
        return None
    return show(commit, path) if has_object(commit, path) else None


def review_facts(document, *, freeze_commit=None):
    """Impure (git only; the caller fetched the reviewed branch first). The facts `review_receipt_violations` checks."""
    document = document if type(document) is dict else {}
    commit, branch = document.get('reviewed_commit'), document.get('reviewed_branch')
    resolves = is_hex(commit, 40) and git_ok('cat-file', '-e', commit + '^{commit}')
    pushed = bool(resolves and _branch(branch) and git_ok('merge-base', '--is-ancestor', commit, tracking_ref(branch)))
    return {'reviewed_commit_resolves': resolves, 'reviewed_commit_pushed': pushed,
            'closure_at_reviewed_commit': {name: blob_id(commit, HERE_REL + '/' + name)
                                           if resolves and has_object(commit, HERE_REL + '/' + name) else None
                                           for name in REVIEW_CLOSURE_FILES},
            'closure_running': closure_blobs(),
            'writer_blobs_at_freeze': None if freeze_commit is None else {
                name: blob_id(freeze_commit, HERE_REL + '/' + name)
                if has_object(freeze_commit, HERE_REL + '/' + name) else None for name in WRITER_FILES}}


def read_prerequisite_receipts(raw, *, anchors):
    """Impure. For each prerequisite of the admission record `raw`: the receipt's bytes, read with
    `git show <receipt_commit>:<receipt_path>`, ONLY when that commit is an ancestor of (or equal to) one of `anchors`.
    A missing, malformed or unanchored receipt is simply absent; the pure check then names it.
    Revision 4: the budget receipt's sources are opened the same way (fix 4) and the review receipt's git facts are
    gathered (fix 5)."""
    record = load_object(raw)
    prerequisites = record.get('prerequisites') if record and type(record.get('prerequisites')) is dict else {}
    receipts = {}
    for name in REQUIRED_PREREQUISITES:
        entry = prerequisites.get(name) if type(prerequisites.get(name)) is dict else {}
        commit, path = entry.get('receipt_commit'), entry.get('receipt_path')
        found = anchored_blob(commit, path, anchors)
        if found is None:
            continue
        receipts[name] = {'commit': commit, 'path': path, 'raw': found}
        document = load_object(found) or {}
        if name == 'budget_headroom_verified' and type(document.get('sources')) is list:
            receipts[name]['sources'] = [anchored_blob(item.get('commit'), item.get('path'), anchors)
                                         if type(item) is dict else None for item in document['sources']]
        elif name == 'fresh_review_of_this_revision':
            receipts[name]['facts'] = review_facts(document)
    return receipts


def execution_admission_state(raw, *, expected_bindings, owner_state, policy, manifest, launch_request,
                              committed, job=None, receipts=None):
    """`{'state', 'recorded_state', 'reasons', 'record_sha256', 'job', 'spend'}`. ADMITTED only when ALL of these hold:

      * the record is JSON with exactly ADMISSION_FIELDS, the pinned schema and label;
      * its `state` is the word ADMITTED (any other word, including an approval word from prose, is NOT_READY);
      * it is for this job kind, seed and source; its `job` has this admission's form and, when `job` is given, equals it;
      * its owner_authorization names STANDING_PROJECT_AUTHORIZATION and the pinned owner-record blobs, AND the owner
        records themselves evaluate to that state now (`owner_state`);
      * its bindings equal `expected_bindings` exactly (plan, policy, pins, manifest, panel, environment, reader);
      * every REQUIRED_PREREQUISITES entry is PASS AND its committed receipt (`receipts`) checks out: sha256, schema,
        pass status, and binding to this job / this reader / this revision (`prerequisite_violations`);
      * the pinned policy files' own machine-readable readiness fields agree (`policy_freeze_violations`);
      * the record is committed as is (`committed`), so it is a recorded fact, not a local edit.
    `spend` is the budget summary read from the budget receipt (None unless that receipt checks out).
    """
    reasons = []
    try:
        record = json.loads(raw) if type(raw) is bytes else None
    except ValueError:
        record = None
    if type(record) is not dict:
        return {'state': NOT_READY, 'recorded_state': None, 'reasons': ['ADMISSION_RECORD_ABSENT_OR_NOT_JSON'],
                'record_sha256': digest(raw) if type(raw) is bytes else None, 'job': None, 'spend': None}
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
    found, spend = prerequisite_violations(prerequisites, receipts, expected_bindings=expected_bindings, policy=policy,
                                           manifest=manifest, job=recorded_job,
                                           admitted_utc=record.get('admitted_utc'))
    reasons.extend(found)
    reasons.extend(policy_freeze_violations(policy, manifest, launch_request, expected_bindings, prerequisites))
    if recorded == ADMITTED and not (type(record.get('admitted_by')) is str and record['admitted_by'].strip()
                                     and type(record.get('admitted_utc')) is str
                                     and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',
                                                      record['admitted_utc'])):
        reasons.append('ADMISSION_ADMITTED_BY_OR_TIME')
    if committed is not True:
        reasons.append('ADMISSION_RECORD_NOT_COMMITTED_AS_IS')
    admitted = recorded == ADMITTED and not reasons
    return {'state': ADMITTED if admitted else NOT_READY, 'recorded_state': recorded,
            'reasons': reasons, 'record_sha256': digest(raw), 'job': recorded_job, 'spend': spend if admitted else None}


def read_execution_admission():
    """`(raw or None, committed)`: the admission record's bytes, and whether HEAD carries exactly these bytes."""
    if not ADMISSION_PATH.is_file():
        return None, False
    raw = ADMISSION_PATH.read_bytes()
    committed = has_object('HEAD', ADMISSION_REL) and blob_id('HEAD', ADMISSION_REL) == git_object_id(raw)
    return raw, committed


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
