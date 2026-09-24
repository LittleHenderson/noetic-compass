"""Freeze ONE job: the unchanged-arm reproduction of Helm 2.0 seed 20260917 at 20208c92. Admission records only.

WHAT THIS IS. HELM-REPAIR-CONTROLLED-1, option C (plan section 4a): re-run seed 20260917 of the historical Helm 2.0
source `20208c923d41c24614504d4ecc2b289ecb66eda8`, with the full registered 10-pass schedule, from the committed
package `package_20208c92`, through the same launcher (`aws/typed_pointer_launch.py`). `read_reproduction.py` then
reads `REPRODUCES` / `DOES_NOT_REPRODUCE` / `INCOMPLETE` against the Helm 2.0 receipt's `final.pt` sha256.

MODELLED ON Helm 2.0's own admission writer at this commit, `records/typed_pointer_001/prepare_study.py`, and on the
switch-ON writers (`admission_analogy_on_001/`, branch `claude/helm-builder-continuation-20260923`). Differences:
  * ONE job, not three. Seed 20260917 only.
  * The package is NOT built here. The committed one (commit 3da10d84, restored blob-identical on this branch) is
    VERIFIED with the launcher's own functions: its archive and manifest digests, its input rows against
    `frozen_inputs(20208c92)`, every data member against `git_package_bytes(20208c92)`, its worker member against
    `render_worker()`, its evidence contract against `evidence_contract()`, and the launcher's own `_locate_archive`.
  * No rehearsal. The same package bytes were rehearsed at 3da10d84 (`admission_001/rehearsal*`,
    EXACT_PACKAGE_WINDOWS_REFUSAL_BEFORE_NUMERIC_IMPORT); Helm 2.0's delivered seed-17 run shipped the same bytes
    (its `collected/input/source.zip` is blob 50201036, the package's blob).
  * The records are checked against Helm 2.0's own seed-17 request and authority: every field equal except the job
    name (and the owner-record hash); the worker config equal once the job name is swapped.
  * The owner record quotes the owner's launch approval and option-C delegation, and the plan's option-C text,
    verbatim, each checked to occur exactly once in the plan blob at commit 197caa32.

REFUSALS (each an explicit stop, never an `assert`):
  * HEAD must descend from 20208c92, and differ from it ONLY by ADDED files in this folder and in `package_20208c92/`.
    Any difference under `cncm/`, `cas_meta2/`, `aws/` or the other input-inventory trees is refused by name.
  * Nothing may be modified, staged or untracked, except this folder's own outputs (`frozen/`, the reading file).
  * `frozen/`, `frozen.partial/` or the receipt folder `records/typed_pointer_001/receipt_unchanged_repro_20260917`
    existing is refused. Nothing is overwritten and nothing is deleted.

WHAT IT WRITES (--write only). One folder, `frozen/`: `frozen/20260917/{owner,request,authority}.json` and
`frozen/study.json`, written into `frozen.partial/`, read back, re-validated with the launcher, then renamed.

WHERE IT MUST RUN. From this checkout (`_worktrees/helm-unchanged-repro-20260924`), the checkout the job will be
launched from: the launcher derives the canonical meta1 ledger path from its own location. No torch, no network, no
AWS call. It does read about 290 git blobs and hash the 18 practice checkpoints (the launcher's own input check).

USAGE (run with `python -B`, from anywhere):
    python -B prepare_unchanged_repro.py --dry-run     # builds and validates everything, writes nothing
    python -B prepare_unchanged_repro.py --write       # the same, then writes frozen/
Job stamps are taken at run time, so --write produces a different job name from the dry run.

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED. Builder: Claude (temporary takeover while Codex is away). This script transcribes
the owner's words; it is not an owner signature. The plan requires this writer to be REVIEWED before the job runs.
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
STUDY_SCHEMA = 'cncm.typed-pointer-unchanged-reproduction-admission/0.1'
REDUCED_SCHEDULE_MARK = b'CNCM_POINTER_REDUCED_SCHEDULE'
# A builder finding, recorded (not acted on) because only the owner may change the plan's test. See BUILDER_REPORT.md.
FINAL_PT_FINDING = (
    'final.pt is torch.save of {schema, metadata, model_state, optimizer_state, encoder_state, rng_state} '
    '(pointer_learner.py export_checkpoint, lines 2045-2082 at 20208c92). metadata carries run_identity, whose '
    'context.run_id is the job name (cncm/typed_pointer_worker.py line 872), and elapsed_seconds, a time.monotonic '
    'wall-clock reading (pointer_learner.py lines 1837-1838). A re-run needs a fresh job name (new bucket) and cannot '
    'repeat the elapsed time, so its final.pt bytes, and therefore its sha256, cannot equal Helm 2.0\'s even if every '
    'weight is identical. Under the plan\'s test as written this job is expected to read DOES_NOT_REPRODUCE. The '
    'reader records the weight-only identities (model_state_identity and three more) as NON-DECIDING diagnostics.')


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
    # The delivered Helm 2.0 run shipped exactly this package: its collected source.zip is the package's blob.
    shipped = common.blob_id(common.REFERENCE_COMMIT, common.REFERENCE_RECEIPT_REL + '/collected/input/source.zip')
    stop_unless(shipped == common.PACKAGE_BLOBS['source.zip'], 'HELM2_RUN_SHIPPED_A_DIFFERENT_PACKAGE:' + shipped)
    return records


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
    # The launcher's OWN search, by the hash the request binds. It follows the receipt's recorded `archive` path,
    # which names the checkout the package was built in (see BUILDER_REPORT.md, open question 2), and it hashes the
    # file it finds before accepting it, so whichever copy it finds is these exact bytes.
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


def build(launch, *, stamp, plan, package, helm2):
    """Every record, in memory, validated with the launcher before anything is written."""
    job = common.check_stamp(stamp, stop_unless)
    stop_unless(re.fullmatch(launch.JOB_PATTERN, job) is not None, 'JOB_FORM:' + job)
    stop_unless(launch.contract.parse_job(job) == (common.HELM2_CONDITION, common.MODEL_SEED), 'JOB_PARSE')
    owner = common.owner_record(schema=launch.OWNER_SCHEMA, candidate=launch.CANDIDATE, job=job,
                                condition=launch.contract.CONDITION, bounds=launch.BOUNDS, plan=plan)
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


def study_record(launch, *, head, plan, package, job, bindings):
    owner_words, plan_words = common.quotes_record()
    return {'schema': STUDY_SCHEMA, 'status': 'FROZEN_BEFORE_FIRST_RUN', 'label': common.LABEL,
            'runner': common.RUNNER, 'source_sha': common.SOURCE_SHA, 'prepared_at_head': head,
            'source_checkout': str(common.ROOT), 'candidate': launch.CANDIDATE, 'config_schema': launch.CONFIG_SCHEMA,
            'package': package, **bindings, 'bindings_equal_helm2_seed_17': True,
            'records_equal_helm2_seed_17_except_job_name': True,
            'helm2_admission': {'commit': common.PACKAGE_COMMIT,
                                'folder': common.GIT_PREFIX + common.HELM2_ADMISSION_REL,
                                'blobs': dict(common.HELM2_ADMISSION_BLOBS), 'job': common.HELM2_JOB},
            'comparison_target': common.reference_pointer(),
            'owner_words_verbatim': owner_words, 'plan_text_verbatim': plan_words, 'plan_record': plan,
            'owner_answered_date': common.OWNER_ANSWERED_DATE,
            'verdict_rule': {'reproduces': plan_words['plan_test_reproduces'],
                             'does_not_reproduce': plan_words['plan_test_does_not_reproduce'],
                             'incomplete': plan_words['plan_stop_not_delivered'],
                             'reader': 'records/typed_pointer_001/admission_unchanged_repro_001/read_reproduction.py'},
            'builder_finding_final_pt_identity': FINAL_PT_FINDING,
            'before_launch_required': [plan_words['plan_job_order_item_3'], plan_words['plan_before_each_job'],
                                       plan_words['plan_earlier_stop'], plan_words['plan_ceiling'],
                                       'the owner rules on builder_finding_final_pt_identity (BUILDER_REPORT.md)'],
            'not_enforced_by_this_writer': ('the review, the measured-spend checks and the job order are checked by '
                                            'the operator before running launch_argv; this writer only freezes'),
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
    plan = common.read_plan(stop_unless)
    helm2 = helm2_records()
    launch = load_launcher()
    check_launcher(launch)
    package = verify_package(launch)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    files, job, bindings = build(launch, stamp=stamp, plan=plan, package=package, helm2=helm2)
    stop_unless(bindings == common.HELM2_BINDINGS, 'BINDINGS_DIFFER_FROM_HELM2')
    study_raw = launch.canonical(study_record(launch, head=head, plan=plan, package=package, job=job,
                                              bindings=bindings))
    files.append((common.OUTPUT / 'study.json', study_raw))
    if not write:
        print(json.dumps({'mode': 'DRY_RUN_NOTHING_WRITTEN', 'job': job['job'], 'head': head,
                          'archive_the_launcher_locates': package['archive_the_launcher_locates'],
                          'canonical_ledger': str(launch.CANONICAL_LEDGER),
                          'canonical_ledger_is_file_here': launch.CANONICAL_LEDGER.is_file(),
                          'note': 'job stamps are taken at run time, so --write produces a different job name'},
                         sort_keys=True), flush=True)
        for path, raw in files:
            print(json.dumps({'would_write': str(path), 'bytes': len(raw), 'sha256': common.digest(raw)},
                             sort_keys=True), flush=True)
        print(json.dumps({'launch_argv': job['launch_argv']}), flush=True)
        return 0
    launch.validate_ledger_path(launch.CANONICAL_LEDGER)     # a stat only: the admission is tied to this checkout

    def recheck(locate):
        """The launcher's own checks again, on the bytes as they now sit in `frozen.partial/`."""
        request = json.loads(locate(job['request']['path']).read_bytes())
        authority = json.loads(locate(job['authority']['path']).read_bytes())
        validate(launch, request, authority, locate(job['owner']['path']))
        compare_with_helm2(launch, request, authority, helm2)
        study = json.loads(locate(common.OUTPUT / 'study.json').read_bytes())
        stop_unless(study['jobs'][0]['launch_argv'] == job['launch_argv'], 'STUDY_ARGV')

    written = common.write_folder_atomically(common.OUTPUT, files, recheck, stop_unless)
    print(json.dumps({'prepared': job['job'], 'receipt_dir': job['receipt_dir'], 'written': written,
                      'study_json_sha256': common.digest(study_raw), 'launch_argv': job['launch_argv']},
                     sort_keys=True), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    try:
        return prepare(write=args.write)
    except subprocess.CalledProcessError as error:
        raise SystemExit('UNCHANGED_REPRO_ADMISSION_STOPPED:GIT:' + ' '.join(map(str, error.cmd))[:400]) from error


if __name__ == '__main__':
    raise SystemExit(main())
