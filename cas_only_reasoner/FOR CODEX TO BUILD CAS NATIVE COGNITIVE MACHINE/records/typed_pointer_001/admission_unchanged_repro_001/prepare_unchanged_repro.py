"""Freeze ONE job: the unchanged-arm reproduction of Helm 2.0 seed 20260917 at 20208c92. Admission records only.

WHAT THIS IS. HELM-REPAIR-CONTROLLED-1, option C: re-run seed 20260917 of the historical Helm 2.0 source
`20208c923d41c24614504d4ecc2b289ecb66eda8`, with the full registered 10-pass schedule, from the committed package
`package_20208c92`, through the same launcher (`aws/typed_pointer_launch.py`). After the run,
`recompute_reproduction_evidence.py` (AWS only) writes the evidence and `read_reproduction.py` reads it under Codex's
reproduction policy revision 1 (commit bc46b36e): STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED,
DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY, or ADMISSION_INVALID_STOP.

MODELLED ON Helm 2.0's own admission writer (`records/typed_pointer_001/prepare_study.py`). ONE job, not three. The
committed package is VERIFIED with the launcher's own functions, not rebuilt. The records are checked against Helm
2.0's own seed-17 request and authority: every field equal except the job name (and the owner-record hash).

TWO STATES, KEPT APART (revision 2; owner record ca68690b; Codex amendment item 2; review finding V1):
  * owner_authorization  - STANDING_PROJECT_AUTHORIZATION, read from the three recorded owner files (git blob ids and
                           sha256 pinned in `repro_common.OWNER_RECORDS`). Nothing reads a status word out of prose.
  * execution_admission  - `EXECUTION_ADMISSION.json` in this folder: ADMITTED only when it is committed as is, bound
                           to the exact plan, policy, manifest, panel, environment and reader-source hashes, names this
                           job, and every prerequisite receipt is present. Today it is NOT_READY.
`--dry-run` is PREPARATION ONLY: it needs neither state and reports both. `--write` and `--check` refuse unless both
hold. The job name is taken from the ADMITTED record, so the frozen job is exactly the admitted one. No approval word is
inserted anywhere to get past a check.

REFUSALS (each an explicit stop, never an `assert`):
  * THE POLICY GATE. Every pinned policy file (plan, REPRODUCTION_POLICY.json/.md, EXECUTION_MANIFEST.json,
    LAUNCH_REQUEST.json, STATISTICAL_POLICY.json, ROUTE_AND_CHECKPOINT_PROTOCOL.md, CODEX_AMENDMENTS) must be the
    pinned blob at bc46b36e; REPRODUCTION_POLICY.json must be exactly the rule the reader implements; LAUNCH_REQUEST.json
    must pin the same hashes (else POLICY_IS_NOT_THE_RULE_THE_READER_IMPLEMENTS, in every mode). Every pinned file
    must also be unchanged at the freshly fetched branch tip: `--write` and `--check` stop with POLICY_OR_PLAN_MOVED,
    `--dry-run` reports the moved files and carries on (a changed plan invalidates the ADMISSION, not preparation).
    Runs before the launcher is imported.
  * HEAD must descend from 20208c92, and differ from it ONLY by ADDED files in this folder and in `package_20208c92/`.
  * Nothing may be modified, staged or untracked, except this folder's own outputs (`frozen/`, the reading file).
  * `frozen/`, `frozen.partial/` or the receipt folder existing is refused. Nothing is overwritten or deleted.

WHAT IT WRITES (--write only). One folder, `frozen/`: `frozen/20260917/{owner,request,authority}.json` and
`frozen/study.json`, written into `frozen.partial/`, read back, re-validated with the launcher, then renamed.

--check. Run IMMEDIATELY before `launch_argv`. Launcher-free. It re-runs the existing-folder refusals, the tree and
untracked rules, both states (with a fresh fetch), `frozen/study.json` against the sha256 --write printed, every
frozen-file pin and the exact launch argv, the located archive, the ledger path (existence only) and the spend gate
(measured spend so far, STATED by the operator with its source, + $15.00 <= $60.00).

WHERE IT MUST RUN. `--dry-run` and `--write` import the launcher, read about 290 git blobs and hash 18 checkpoints:
not on the laptop (the owner's compute rule). `--print-admission-bindings` and `--check` are launcher-free.

USAGE (python -B, from the worktree root: deeper folders exceed the Windows path limit):
    python -B prepare_unchanged_repro.py --print-admission-bindings   # read-only: the hashes an admission must carry
    python -B prepare_unchanged_repro.py --dry-run                    # preparation only; writes nothing
    python -B prepare_unchanged_repro.py --write                      # needs ADMITTED; writes frozen/
    python -B prepare_unchanged_repro.py --check --study-sha256 <hex> --spend-so-far-usd <d.dd> --spend-source <text>

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED. Builder: Claude (temporary takeover while Codex is away). This script transcribes
the owner's words; it is not an owner signature.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import repro_common as common  # noqa: E402

stop_unless = common.make_stop('UNCHANGED_REPRO_ADMISSION_STOPPED:')
STUDY_SCHEMA = 'cncm.typed-pointer-unchanged-reproduction-admission/0.3'
REDUCED_SCHEDULE_MARK = b'CNCM_POINTER_REDUCED_SCHEDULE'
PREPARATION_ONLY = 'PREPARATION_ONLY_NO_OWNER_OR_EXECUTION_APPROVAL_NEEDED_OR_USED'
FINAL_PT_FINDING = (
    'final.pt is torch.save of {schema, metadata, model_state, optimizer_state, encoder_state, rng_state} '
    '(pointer_learner.py export_checkpoint at 20208c92). metadata carries run_identity (whose context.run_id is the job '
    'name, cncm/typed_pointer_worker.py line 872) and elapsed_seconds, so a genuine re-run cannot give the same FILE '
    'sha256. Policy bc46b36e therefore decides by recomputed learned-state identity AND the complete public panel; file '
    'identity is printed separately and never decides (REPRODUCTION_POLICY.json file_mismatch_alone_triggers_fallback '
    '= false).')


def load_launcher():
    """The launcher, imported exactly as `prepare_study.py` imports it. Only `prepare()` calls this."""
    sys.path[:0] = [str(common.ROOT), str(common.ROOT / 'research/CAS_META_2_COMPOSITION')]
    from aws import typed_pointer_launch as launch
    return launch


# ---------------------------------------------------------------------------------------------------------------------
# Launcher-free checks.
# ---------------------------------------------------------------------------------------------------------------------
def check_repository():
    """The commit, the tree rule, the committed package blobs, and the untracked rule. Returns HEAD."""
    prefix = common.git('rev-parse', '--show-prefix').decode('utf-8').strip()
    stop_unless(prefix == common.GIT_PREFIX, 'GIT_PREFIX:' + prefix)
    head = common.git('rev-parse', 'HEAD').decode('ascii').strip()
    stop_unless(common.git_ok('merge-base', '--is-ancestor', common.SOURCE_SHA, 'HEAD'),
                'HEAD_DOES_NOT_DESCEND_FROM_SOURCE:' + head)
    changed = common.parse_name_status_z(common.git('diff', '--name-status', '-z', '--no-renames',
                                                    common.SOURCE_SHA, 'HEAD'))
    violations = common.tree_violations(changed)
    stop_unless(not violations, 'TREE_DIFFERS_FROM_SOURCE:' + '|'.join(violations)[:2000])
    for name, blob in common.PACKAGE_BLOBS.items():
        relative = common.PACKAGE_REL + '/' + name
        stop_unless(common.blob_id(common.PACKAGE_COMMIT, relative) == blob, 'PACKAGE_PIN_AT_3DA10D84:' + name)
        stop_unless(common.has_object('HEAD', relative) and common.blob_id('HEAD', relative) == blob,
                    'PACKAGE_NOT_COMMITTED_ON_THIS_BRANCH:' + name)
        raw = (common.ROOT / relative).read_bytes()
        stop_unless(common.git_object_id(raw) == blob, 'PACKAGE_WORKING_TREE_BYTES:' + name)
    dirty = common.status_violations(common.parse_status_z(
        common.git('status', '--porcelain=v1', '-z', '--untracked-files=all')))
    stop_unless(not dirty, 'COMMIT_FIRST_ONLY_THIS_FOLDER_S_OUTPUTS_MAY_BE_UNTRACKED:' + '|'.join(dirty)[:2000])
    return head


def refuse_existing():
    for path, reason in ((common.partial_of(common.OUTPUT), 'PARTIAL_FOLDER_EXISTS_INSPECT_BY_HAND'),
                         (common.OUTPUT, 'TARGET_EXISTS_NO_OVERWRITE'),
                         (common.RECEIPT_DIR, 'RECEIPT_EXISTS_NO_AUTOMATIC_RETRY')):
        stop_unless(not path.exists(), reason + ':' + str(path))


def helm2_records():
    """Helm 2.0's own seed-17 request, authority and owner record, read from git at the package commit."""
    records = {}
    for name, blob in common.HELM2_ADMISSION_BLOBS.items():
        relative = common.HELM2_ADMISSION_REL + '/' + name
        stop_unless(common.blob_id(common.PACKAGE_COMMIT, relative) == blob, 'HELM2_ADMISSION_BLOB:' + name)
        records[name] = json.loads(common.show(common.PACKAGE_COMMIT, relative))
    request, authority = records['request.json'], records['authority.json']
    stop_unless(request['job'] == authority['job'] == records['owner.json']['job'] == common.HELM2_JOB, 'HELM2_JOB')
    stop_unless(request['source_sha'] == common.SOURCE_SHA and request['archive_sha256'] == common.ARCHIVE_SHA256
                and request['manifest_sha256'] == common.MANIFEST_SHA256, 'HELM2_REQUEST_IS_NOT_THIS_PACKAGE')
    stop_unless(all(authority[key] == value for key, value in common.HELM2_BINDINGS.items()), 'HELM2_BINDINGS')
    stop_unless(records['owner.json']['bounds'] == common.EXPECTED_BOUNDS, 'HELM2_OWNER_BOUNDS')
    stop_unless(records['owner.json']['condition'] == common.HELM2_CONDITION, 'HELM2_CONDITION')
    shipped = common.blob_id(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL + '/collected/input/source.zip')
    stop_unless(shipped == common.PACKAGE_BLOBS['source.zip'], 'HELM2_RUN_SHIPPED_A_DIFFERENT_PACKAGE:' + shipped)
    return records


# ---------------------------------------------------------------------------------------------------------------------
# The two states and the policy gate (revision 2). All launcher-free; they run before the launcher is imported.
# ---------------------------------------------------------------------------------------------------------------------
def gates(*, fetch=True, require_admitted=False, job=None):
    """The policy gate always stops on a violation. The two states stop ONLY when `require_admitted` is set.

    `require_admitted=False` is the preparation-only path (`--dry-run`): it needs no owner approval and no execution
    admission, and it cannot be satisfied or bypassed by inserting any word anywhere.
    """
    policy = common.check_policy(stop_unless, fetch=fetch, require_current=require_admitted)
    owner = common.owner_authorization_state(common.read_owner_records())
    raw, committed = common.read_execution_admission()
    admission = common.execution_admission_state(
        raw, expected_bindings=common.expected_admission_bindings(), owner_state=owner, policy=policy['policy'],
        manifest=policy['manifest'], launch_request=policy['launch_request'], committed=committed, job=job)
    if require_admitted:
        stop_unless(owner['state'] == common.OWNER_AUTHORIZED,
                    'OWNER_AUTHORIZATION_NOT_ESTABLISHED:' + '|'.join(owner['reasons'])[:1500])
        stop_unless(admission['state'] == common.ADMITTED,
                    'EXECUTION_ADMISSION_IS_NOT_ADMITTED:' + '|'.join(admission['reasons'])[:1500])
    return {'policy': policy, 'owner_authorization': owner, 'execution_admission': admission}


def admission_summary(gate):
    admission = gate['execution_admission']
    return {'policy_tip_violations': gate['policy']['tip'].get('violations'),
            'owner_authorization': gate['owner_authorization']['state'],
            'owner_authorization_reasons': gate['owner_authorization']['reasons'],
            'execution_admission': admission['state'], 'execution_admission_recorded_state': admission['recorded_state'],
            'execution_admission_reasons': admission['reasons'], 'execution_admission_job': admission['job']}


# ---------------------------------------------------------------------------------------------------------------------
# Launcher checks.
# ---------------------------------------------------------------------------------------------------------------------
def check_launcher(launch):
    launch.configure_reduced_schedule(None)          # the full registered plan; never a smoke opt-in
    stop_unless(launch.SMOKE_REQUEST is None, 'REDUCED_SCHEDULE_SET')
    stop_unless(launch.BOUNDS == common.EXPECTED_BOUNDS, 'LAUNCHER_BOUNDS_MOVED')
    stop_unless(launch.RESERVATION_USD == common.EXPECTED_BOUNDS['reservation_usd'], 'RESERVATION_MOVED')
    stop_unless(launch.contract.CONDITION == common.HELM2_CONDITION, 'CONDITION_MOVED')
    stop_unless(common.MODEL_SEED in tuple(launch.contract.MODEL_SEEDS), 'MODEL_SEED_NOT_REGISTERED')


def verify_package(launch):
    """The committed package, byte for byte, as the launcher will locate and ship it. Launcher functions only."""
    directory = common.ROOT / common.PACKAGE_REL
    receipt_raw = (directory / 'receipt.json').read_bytes()
    receipt = json.loads(receipt_raw)
    stop_unless(receipt.get('schema') == common.PACKAGE_RECEIPT_SCHEMA
                and receipt.get('status') == 'SOURCE_ONLY_NO_LAUNCH'
                and receipt.get('source_sha') == common.SOURCE_SHA, 'PACKAGE_RECEIPT')
    stop_unless(receipt.get('archive_sha256') == common.ARCHIVE_SHA256
                and receipt.get('manifest_sha256') == common.MANIFEST_SHA256
                and receipt.get('archive_bytes') == common.ARCHIVE_BYTES
                and receipt.get('member_count') == common.MEMBER_COUNT, 'PACKAGE_RECEIPT_IDENTITY')
    archive = directory / 'source.zip'
    raw = archive.read_bytes()
    stop_unless(launch.digest(raw) == common.ARCHIVE_SHA256 and len(raw) == common.ARCHIVE_BYTES, 'PACKAGE_ARCHIVE')
    stop_unless(launch._git_object_id(raw) == common.PACKAGE_BLOBS['source.zip'], 'PACKAGE_ARCHIVE_BLOB')
    del raw
    located = Path(launch.lifecycle._locate_archive(common.ARCHIVE_SHA256))
    stop_unless(launch.digest(located.read_bytes()) == common.ARCHIVE_SHA256, 'LOCATED_ARCHIVE_BYTES')
    rows = launch.frozen_inputs(common.SOURCE_SHA)
    names = launch.package_data_files(rows)
    bare = [{key: value for key, value in row.items() if key != 'committed_content_sha256'} for row in rows]
    registered = launch.run_evidence.contract_digest(launch.evidence_contract())
    with ZipFile(archive) as bundle:
        members = [info.filename for info in bundle.infolist()]
        stop_unless(len(members) == len(set(members)) == common.MEMBER_COUNT, 'PACKAGE_MEMBER_COUNT')
        expected = set(names) | {launch.WORKER_NAME, launch.shared.MANIFEST_NAME}
        stop_unless(set(members) == expected, 'PACKAGE_MEMBER_SET:' + '|'.join(sorted(set(members) ^ expected))[:800])
        manifest_raw = bundle.read(launch.shared.MANIFEST_NAME)
        stop_unless(launch.digest(manifest_raw) == common.MANIFEST_SHA256, 'PACKAGE_MANIFEST_BYTES')
        manifest = json.loads(manifest_raw)
        stop_unless(launch.canonical(manifest) == launch.canonical(receipt['manifest']), 'PACKAGE_RECEIPT_MANIFEST')
        stop_unless(manifest['source_sha'] == common.SOURCE_SHA, 'PACKAGE_MANIFEST_SOURCE')
        stop_unless(launch.canonical(manifest['inputs']) == launch.canonical(bare), 'PACKAGE_INPUT_ROWS')
        stop_unless(manifest['inputs_sha256'] == launch.frozen_inputs_hash(common.SOURCE_SHA)
                    == common.HELM2_BINDINGS['inputs_sha256'], 'PACKAGE_INPUTS_SHA256')
        stop_unless(all(manifest['frozen_budget'].get(key) == value for key, value in launch.BOUNDS.items()),
                    'PACKAGE_BOUNDS')
        stop_unless(launch.canonical(manifest['typed_design']) == launch.canonical(launch.DESIGN), 'PACKAGE_DESIGN')
        stop_unless(manifest['transport']['predeclared_contract_sha256'] == registered
                    == common.HELM2_BINDINGS['evidence_contract_sha256'], 'PACKAGE_EVIDENCE_CONTRACT')
        for name in names:                                        # one member at a time: bounded memory
            stop_unless(bundle.read(name) == launch.git_package_bytes(launch.ROOT, common.SOURCE_SHA, name),
                        'PACKAGE_MEMBER_IS_NOT_THE_SOURCE_COMMIT:' + name)
        worker = bundle.read(launch.WORKER_NAME)
    stop_unless(worker == launch.run_evidence.unified_worker_source(launch.render_worker()).encode('utf-8'),
                'PACKAGE_WORKER_IS_NOT_WHAT_THIS_LAUNCHER_RENDERS')
    stop_unless(REDUCED_SCHEDULE_MARK not in worker, 'PACKAGE_WORKER_CARRIES_A_REDUCED_SCHEDULE')
    return {'source_sha': common.SOURCE_SHA, 'directory': str(directory), 'archive': str(archive),
            'archive_sha256': common.ARCHIVE_SHA256, 'archive_bytes': common.ARCHIVE_BYTES,
            'manifest_sha256': common.MANIFEST_SHA256, 'member_count': common.MEMBER_COUNT,
            'receipt_sha256': launch.digest(receipt_raw), 'committed_at': common.PACKAGE_COMMIT,
            'blobs': dict(common.PACKAGE_BLOBS), 'receipt_recorded_archive_path': receipt['archive'],
            'archive_the_launcher_locates': str(located),
            'located_archive_is_in_this_checkout': located.resolve() == archive.resolve(),
            'inputs_sha256': manifest['inputs_sha256'], 'predeclared_contract_sha256': registered,
            'shipped_worker_member_sha256': launch.digest(worker),
            'verified_with': ['digest', '_git_object_id', 'lifecycle._locate_archive', 'frozen_inputs',
                              'frozen_inputs_hash', 'package_data_files', 'git_package_bytes', 'render_worker',
                              'run_evidence.unified_worker_source', 'evidence_contract',
                              'run_evidence.contract_digest']}


def compare_with_helm2(launch, request, authority, helm2):
    """Every request and authority field equal to Helm 2.0's seed-17 one, except the job and the owner hash."""
    old_request, old_authority = helm2['request.json'], helm2['authority.json']
    for key in set(request) | set(old_request):
        if key != 'job':
            stop_unless(request.get(key) == old_request.get(key), 'REQUEST_DIFFERS_FROM_HELM2:' + key)
    for key in set(authority) | set(old_authority):
        if key not in ('job', 'owner_authorization_sha256', 'worker_config'):
            stop_unless(authority.get(key) == old_authority.get(key), 'AUTHORITY_DIFFERS_FROM_HELM2:' + key)
    stop_unless(common.config_equal_except_job(launch.canonical(authority['worker_config']).decode('ascii'),
                                               launch.canonical(old_authority['worker_config']).decode('ascii'),
                                               authority['job'], common.HELM2_JOB),
                'WORKER_CONFIG_DIFFERS_FROM_HELM2_BEYOND_THE_JOB_NAME')
    return True


def validate(launch, request, authority, owner_path):
    """The launcher's own three validators, with the registered 10-pass evidence contract (the default)."""
    launch.validate_request(request)
    launch.validate_authority(authority)
    launch.validate_owner(owner_path, authority)


def build(launch, *, stamp, gate, package, helm2):
    """Every record, in memory, validated with the launcher before anything is written."""
    job = common.check_stamp(stamp, stop_unless)
    stop_unless(re.fullmatch(launch.JOB_PATTERN, job) is not None, 'JOB_FORM:' + job)
    stop_unless(launch.contract.parse_job(job) == (common.HELM2_CONDITION, common.MODEL_SEED), 'JOB_PARSE')
    owner = common.owner_record(schema=launch.OWNER_SCHEMA, candidate=launch.CANDIDATE, job=job,
                                condition=launch.contract.CONDITION, bounds=launch.BOUNDS,
                                owner_state=gate['owner_authorization'], admission=gate['execution_admission'])
    owner_raw = launch.canonical(owner)
    identity = {'source_sha': common.SOURCE_SHA, 'archive_sha256': package['archive_sha256'],
                'manifest_sha256': package['manifest_sha256']}
    request = {'schema': launch.REQUEST_SCHEMA, 'job': job, **identity, 'launch_authorized': False}
    authority = {'schema': launch.AUTHORITY_SCHEMA, 'job': job, **identity, **launch.BOUNDS,
                 'candidate': launch.CANDIDATE, 'owner_authorization_sha256': launch.digest(owner_raw),
                 'inputs_sha256': launch.frozen_inputs_hash(common.SOURCE_SHA),
                 'design_sha256': launch.digest(launch.canonical(launch.DESIGN)),
                 'evidence_contract_sha256': launch.run_evidence.contract_digest(launch.evidence_contract()),
                 'worker_config': launch.worker_config(job, source_sha=common.SOURCE_SHA)}
    stop_unless(authority['worker_config']['inputs_sha256'] == authority['inputs_sha256'], 'CONFIG_INPUTS_HASH')
    stop_unless(launch.inputs_hash_cross_check(common.SOURCE_SHA)[2] is True, 'INPUTS_HASH_CROSS_CHECK')
    with tempfile.TemporaryDirectory(prefix='prepare_unchanged_repro_') as scratch:
        probe = Path(scratch) / 'owner.json'
        probe.write_bytes(owner_raw)
        validate(launch, request, authority, probe)
    compare_with_helm2(launch, request, authority, helm2)
    directory = common.OUTPUT / str(common.MODEL_SEED)
    raws = {'owner': owner_raw, 'request': launch.canonical(request), 'authority': launch.canonical(authority)}
    files = [(directory / (name + '.json'), raw) for name, raw in raws.items()]
    pins = {name: common.pin(directory / (name + '.json'), raw) for name, raw in raws.items()}
    argv = common.launch_argv(launcher=common.ROOT / common.LAUNCHER_REL, request=pins['request'],
                              authority=pins['authority'], owner=pins['owner'], receipt_dir=common.RECEIPT_DIR,
                              ledger=launch.CANONICAL_LEDGER)
    job_record = {'job': job, 'kind': common.JOB_KIND, 'condition': launch.contract.CONDITION,
                  'model_seed': common.MODEL_SEED, 'reproduces_job': common.HELM2_JOB, **pins,
                  'receipt_dir': str(common.RECEIPT_DIR), 'reservation_usd': launch.RESERVATION_USD,
                  'reduced_schedule': None, 'evidence_contract': 'REGISTERED_10_PASS',
                  'launch_cwd': str(common.ROOT), 'launch_argv': argv}
    return files, job_record, {'inputs_sha256': authority['inputs_sha256'],
                               'design_sha256': authority['design_sha256'],
                               'evidence_contract_sha256': authority['evidence_contract_sha256']}


def study_record(launch, *, head, gate, package, job, bindings):
    admission = gate['execution_admission']
    return {'schema': STUDY_SCHEMA, 'status': 'FROZEN_BEFORE_FIRST_RUN', 'label': common.LABEL,
            'runner': common.RUNNER, 'source_sha': common.SOURCE_SHA, 'prepared_at_head': head,
            'source_checkout': str(common.ROOT), 'candidate': launch.CANDIDATE, 'config_schema': launch.CONFIG_SCHEMA,
            'package': package, **bindings, 'bindings_equal_helm2_seed_17': True,
            'records_equal_helm2_seed_17_except_job_name': True,
            'helm2_admission': {'commit': common.PACKAGE_COMMIT,
                                'folder': common.GIT_PREFIX + common.HELM2_ADMISSION_REL,
                                'blobs': dict(common.HELM2_ADMISSION_BLOBS), 'job': common.HELM2_JOB},
            'comparison_target': common.reference_pointer(),
            'owner_words_verbatim': {name: words for name, (words, _) in common.OWNER_QUOTES.items()},
            'owner_authorization': {'state': gate['owner_authorization']['state'],
                                    'records': gate['owner_authorization']['records']},
            'execution_admission': {'state': admission['state'], 'record_sha256': admission['record_sha256'],
                                    'job': admission['job'], 'record': common.GIT_PREFIX + common.ADMISSION_REL,
                                    'bindings': common.expected_admission_bindings()},
            'reading_rule': common.reading_rule_record(), 'policy_tip_at_freeze': gate['policy']['tip'],
            'readers': {'evidence': 'records/typed_pointer_001/admission_unchanged_repro_001/'
                                    'recompute_reproduction_evidence.py (AWS only)',
                        'verdict': 'records/typed_pointer_001/admission_unchanged_repro_001/read_reproduction.py'},
            'builder_finding_final_pt_identity': FINAL_PT_FINDING,
            'before_launch_required': ['execution_admission ADMITTED for this job (every prerequisite receipt present)',
                                       'measured spend so far + $15.00 <= $60.00',
                                       'prepare_unchanged_repro.py --check passes, run immediately before launch_argv'],
            'check_before_launch': ('python -B <this file> --check --study-sha256 <study.json sha256> '
                                    '--spend-so-far-usd <measured spend so far> --spend-source <where it was read>'),
            'not_enforced_by_this_writer': ('the $30 stop before the third training job and the job order are the '
                                            'amended envelope\'s; --check enforces the two states, the policy gate, '
                                            'the pins and the $60.00 arithmetic on the stated figure'),
            'limits': launch.BOUNDS, 'jobs': [job], 'launcher': str(common.ROOT / common.LAUNCHER_REL),
            'canonical_ledger': str(launch.CANONICAL_LEDGER), 'automatic_retries': 0,
            'execute_study_py': ('NOT USED: records/typed_pointer_001/execute_study.py requires three jobs and the '
                                 'five 2026-09-19 decisions; this one job is launched with its own launch_argv'),
            'rehearsal': ('NOT RUN BY THIS WRITER: the identical package bytes were rehearsed at 3da10d84 '
                          '(records/typed_pointer_001/admission_001/rehearsal_stdout.txt, rehearsal_stderr.txt)'),
            'numeric_runs_completed': 0}


def prepare(*, write):
    refuse_existing()                    # first, so a leftover `.partial` is named as such, not as "untracked"
    head = check_repository()
    gate = gates(fetch=True, require_admitted=write)
    helm2 = helm2_records()
    launch = load_launcher()
    check_launcher(launch)
    package = verify_package(launch)
    if write:
        stamp = common.stamp_of(gate['execution_admission']['job'])     # the ADMITTED job, exactly
        stop_unless(stamp is not None, 'ADMITTED_JOB_NAME_FORM')
    else:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    files, job, bindings = build(launch, stamp=stamp, gate=gate, package=package, helm2=helm2)
    stop_unless(bindings == common.HELM2_BINDINGS, 'BINDINGS_DIFFER_FROM_HELM2')
    study_raw = launch.canonical(study_record(launch, head=head, gate=gate, package=package, job=job,
                                              bindings=bindings))
    files.append((common.OUTPUT / 'study.json', study_raw))
    if not write:
        print(json.dumps({'mode': 'DRY_RUN_NOTHING_WRITTEN', 'path': PREPARATION_ONLY, 'job': job['job'],
                          'head': head, **admission_summary(gate),
                          'archive_the_launcher_locates': package['archive_the_launcher_locates'],
                          'canonical_ledger': str(launch.CANONICAL_LEDGER),
                          'canonical_ledger_is_file_here': launch.CANONICAL_LEDGER.is_file(),
                          'note': '--write takes the job name from the ADMITTED record, not from this dry run'},
                         sort_keys=True), flush=True)
        for path, raw in files:
            print(json.dumps({'would_write': str(path), 'bytes': len(raw), 'sha256': common.digest(raw)},
                             sort_keys=True), flush=True)
        print(json.dumps({'launch_argv': job['launch_argv']}), flush=True)
        return 0
    launch.validate_ledger_path(launch.CANONICAL_LEDGER)     # a stat only: the admission is tied to this checkout

    def recheck(locate):
        """The launcher's own checks again, on the bytes as they now sit in `frozen.partial/`, and both states."""
        request = json.loads(locate(job['request']['path']).read_bytes())
        authority = json.loads(locate(job['authority']['path']).read_bytes())
        validate(launch, request, authority, locate(job['owner']['path']))
        compare_with_helm2(launch, request, authority, helm2)
        study = json.loads(locate(common.OUTPUT / 'study.json').read_bytes())
        stop_unless(study['jobs'][0]['launch_argv'] == job['launch_argv'], 'STUDY_ARGV')
        gates(fetch=False, require_admitted=True, job=job['job'])      # again, just before the rename

    written = common.write_folder_atomically(common.OUTPUT, files, recheck, stop_unless)
    print(json.dumps({'prepared': job['job'], 'receipt_dir': job['receipt_dir'], 'written': written,
                      'study_json_sha256': common.digest(study_raw), 'launch_argv': job['launch_argv'],
                      'next': 'commit frozen/ by explicit path, push, then run --check immediately before launch'},
                     sort_keys=True), flush=True)
    return 0


# ---------------------------------------------------------------------------------------------------------------------
# --check: immediately before launch. Launcher-free.
# ---------------------------------------------------------------------------------------------------------------------
def check_frozen_committed():
    """`frozen/` has no uncommitted change, and every file in it is committed at HEAD with exactly these bytes."""
    folder = common.HERE_REL + '/frozen'
    dirty = common.git('status', '--porcelain=v1', '-z', '--untracked-files=all', '--', folder)
    stop_unless(dirty == b'', 'COMMIT_THE_FROZEN_RECORDS_FIRST:' + dirty.decode('utf-8', 'replace')[:800])
    on_disk = sorted(path.relative_to(common.ROOT).as_posix() for path in common.OUTPUT.rglob('*') if path.is_file())
    tracked = sorted(item.decode('utf-8') for item in common.git('ls-files', '-z', '--', folder).split(b'\0') if item)
    stop_unless(on_disk and on_disk == tracked, 'FROZEN_FILE_SET_IS_NOT_THE_COMMITTED_SET')
    for relative in on_disk:
        stop_unless(common.blob_id('HEAD', relative) == common.git_object_id((common.ROOT / relative).read_bytes()),
                    'FROZEN_FILE_NOT_COMMITTED_AS_IS:' + relative)
    return on_disk


def check_pin(pin, folder):
    path = Path(pin['path'])
    stop_unless(path.parent == folder and path.is_file(), 'PINNED_FILE_MISSING_OR_ELSEWHERE:' + str(pin['path']))
    raw = path.read_bytes()
    stop_unless(len(raw) == pin['bytes'] and common.digest(raw) == pin['sha256'], 'PIN:' + str(pin['path']))
    return json.loads(raw)


def check_study(study, admission, *, output=None):
    """Everything frozen/study.json says, against the files, this checkout, the pins and the CURRENT admission."""
    output = common.OUTPUT if output is None else output
    stop_unless(study.get('schema') == STUDY_SCHEMA and study.get('status') == 'FROZEN_BEFORE_FIRST_RUN',
                'STUDY_SCHEMA_OR_STATUS')
    stop_unless(study.get('source_sha') == common.SOURCE_SHA and study.get('source_checkout') == str(common.ROOT),
                'NOT_THE_CHECKOUT_THE_RECORDS_WERE_WRITTEN_IN')
    stop_unless(common.same(study.get('reading_rule'), common.reading_rule_record()),
                'FROZEN_UNDER_A_DIFFERENT_READING_RULE')
    frozen_admission = study.get('execution_admission') if type(study.get('execution_admission')) is dict else {}
    stop_unless(frozen_admission.get('state') == common.ADMITTED
                and frozen_admission.get('record_sha256') == admission.get('record_sha256')
                and frozen_admission.get('job') == admission.get('job')
                and common.same(frozen_admission.get('bindings'), common.expected_admission_bindings()),
                'FROZEN_UNDER_A_DIFFERENT_EXECUTION_ADMISSION')
    stop_unless(study.get('automatic_retries') == 0 and study.get('numeric_runs_completed') == 0, 'STUDY_COUNTERS')
    jobs = study.get('jobs')
    stop_unless(type(jobs) is list and len(jobs) == 1 and type(jobs[0]) is dict, 'STUDY_ONE_JOB')
    job = jobs[0]
    stop_unless(job.get('kind') == common.JOB_KIND and job.get('model_seed') == common.MODEL_SEED
                and job.get('receipt_dir') == str(common.RECEIPT_DIR) and job.get('reduced_schedule') is None
                and job.get('job') != common.HELM2_JOB and job.get('job') == admission.get('job'), 'STUDY_JOB')
    stamp = common.stamp_of(job['job'])
    stop_unless(stamp is not None, 'STUDY_JOB_NAME_FORM:' + str(job['job']))
    common.check_stamp(stamp, stop_unless)
    folder = output / str(common.MODEL_SEED)
    owner, request, authority = (check_pin(job[name], folder) for name in ('owner', 'request', 'authority'))
    expected = common.launch_argv(launcher=common.ROOT / common.LAUNCHER_REL, request=job['request'],
                                  authority=job['authority'], owner=job['owner'], receipt_dir=common.RECEIPT_DIR,
                                  ledger=study.get('canonical_ledger'))
    stop_unless(job.get('launch_argv') == expected and '--reduced-schedule' not in expected, 'LAUNCH_ARGV')
    stop_unless(request.get('job') == authority.get('job') == owner.get('job') == job['job'], 'RECORDS_JOB')
    stop_unless(request.get('source_sha') == common.SOURCE_SHA and request.get('archive_sha256')
                == common.ARCHIVE_SHA256 and request.get('manifest_sha256') == common.MANIFEST_SHA256
                and request.get('launch_authorized') is False, 'REQUEST_IDENTITY')
    stop_unless(authority.get('owner_authorization_sha256') == job['owner']['sha256']
                and all(authority.get(key) == value for key, value in common.HELM2_BINDINGS.items()),
                'AUTHORITY_BINDINGS')
    stop_unless(owner.get('bounds') == common.EXPECTED_BOUNDS
                and common.same(owner.get('reading_rule'), common.reading_rule_record())
                and (owner.get('execution_admission') or {}).get('record_sha256') == admission.get('record_sha256')
                and owner.get('approval_words_inserted_by_builder') is False, 'OWNER_RECORD')
    located = Path(str((study.get('package') or {}).get('archive_the_launcher_locates')))
    stop_unless(located.is_file(), 'LOCATED_ARCHIVE_GONE:' + str(located))
    raw = located.read_bytes()
    stop_unless(len(raw) == common.ARCHIVE_BYTES and common.digest(raw) == common.ARCHIVE_SHA256,
                'LOCATED_ARCHIVE_CHANGED:' + str(located))
    ledger = Path(str(study.get('canonical_ledger')))
    stop_unless(ledger.is_file(), 'CANONICAL_LEDGER_NOT_FOUND:' + str(ledger))     # a stat only; never opened
    return job


def check_before_launch(*, study_sha256, spend_so_far_usd, spend_source):
    for path, reason in ((common.partial_of(common.OUTPUT), 'PARTIAL_FOLDER_EXISTS_INSPECT_BY_HAND'),
                         (common.RECEIPT_DIR, 'RECEIPT_EXISTS_NO_AUTOMATIC_RETRY')):
        stop_unless(not path.exists(), reason + ':' + str(path))
    stop_unless(common.OUTPUT.is_dir(), 'NOTHING_FROZEN_RUN_WRITE_FIRST:' + str(common.OUTPUT))
    stop_unless(type(spend_source) is str and len(spend_source.strip()) >= 8, 'SPEND_SOURCE_REQUIRED')
    spend = common.spend_gate(spend_so_far_usd, stop_unless)
    head = check_repository()
    frozen = check_frozen_committed()
    raw = (common.OUTPUT / 'study.json').read_bytes()
    stop_unless(common.is_hex(study_sha256, 64) and common.digest(raw) == study_sha256,
                'STUDY_SHA256:' + common.digest(raw))
    study = json.loads(raw)
    frozen_job = (study.get('jobs') or [{}])[0].get('job') if type(study.get('jobs')) is list else None
    gate = gates(fetch=True, require_admitted=True, job=frozen_job)
    job = check_study(study, gate['execution_admission'])
    print(json.dumps({'mode': 'CHECK_PASSED_NOTHING_LAUNCHED', 'head': head, 'frozen_files': frozen,
                      **admission_summary(gate), 'policy_tip': gate['policy']['tip'], 'job': job['job'],
                      'spend': spend, 'spend_figure_source': spend_source.strip(),
                      'spend_figure_is': 'STATED_BY_THE_OPERATOR_NOT_READ_FROM_A_RECORD',
                      'not_checked_here': ['the $30 stop before the third training job', 'the amended job order'],
                      'launch_cwd': str(common.ROOT), 'launch_argv': job['launch_argv']}, sort_keys=True), flush=True)
    return 0


def print_admission_bindings():
    """Read-only. The exact bindings an EXECUTION_ADMISSION.json must carry for this revision. No approval involved."""
    print(json.dumps({'mode': 'ADMISSION_BINDINGS_READ_ONLY', 'path': PREPARATION_ONLY,
                      'bindings': common.expected_admission_bindings(),
                      'required_prerequisites': list(common.REQUIRED_PREREQUISITES)}, sort_keys=True, indent=1),
          flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--print-admission-bindings', action='store_true')
    parser.add_argument('--study-sha256')
    parser.add_argument('--spend-so-far-usd')
    parser.add_argument('--spend-source')
    args = parser.parse_args(argv)
    try:
        if args.print_admission_bindings:
            return print_admission_bindings()
        if args.check:
            return check_before_launch(study_sha256=args.study_sha256, spend_so_far_usd=args.spend_so_far_usd,
                                       spend_source=args.spend_source)
        return prepare(write=args.write)
    except subprocess.CalledProcessError as error:
        raise SystemExit('UNCHANGED_REPRO_ADMISSION_STOPPED:GIT:' + ' '.join(map(str, error.cmd))[:400]) from error


if __name__ == '__main__':
    raise SystemExit(main())
