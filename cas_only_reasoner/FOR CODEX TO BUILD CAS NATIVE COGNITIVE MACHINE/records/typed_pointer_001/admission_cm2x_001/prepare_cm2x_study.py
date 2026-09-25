"""Freeze the CRITICAL-MASS 2x registered full run before the first result. Admission records only; no launch.

WHAT THIS IS. The admission writer for the critical-mass 2x version of the pointer study: ONE job, the
registered full run, model seed 20260918, 20 passes, on the existing Helm training path
(`aws/typed_pointer_launch.py` -> `cncm.typed_pointer_worker`, g7.2xlarge, us-west-2). It is deliberately
smaller than `admission_analogy_on_001/prepare_on_study.py`: that writer froze a smoke plus THREE seeds under
an earlier owner approval and needed the item-1 reading, the owner words and the migration record. This
version has one job, so it freezes one job.

WHAT IS VERSIONED, AND WHAT IS R18's. `EXPERIMENT_VERSION` is `cncm.typed-pointer-critical-mass-2x/1`. The
model and learner, the course, the held-back worlds and records, the stratified batch order, the optimizer,
the 59-packet hard development panel, the private scorer and the source logic are R18's, unchanged, and are
not restated here -- the contract is their one source. What moves is the training duration (20 passes against
R18's measured 10) and the output/resource envelope needed to finish and to hold it.

WHAT IT WRITES, and nothing else. One folder, `seeds/`:
    seeds/20260918/{owner,request,authority}.json
    seeds/study.json
Every file is opened with mode 'xb'. The receipt folder named by the records,
`records/typed_pointer_001/receipt_cm2x_20260918`, must NOT exist. The R18 admission under
`admission_analogy_on_001/seeds/20260918/` is read (for the supersession note) and never written.

THE PACKAGE. Built beforehand, locally and offline, by the launcher's own `--package` step from the source
commit: `research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_<sha8>`. This writer verifies it
byte for byte and reads the version and pass count back out of the shipped manifest, so a package built from
a different version cannot be frozen as this one.

HOW EACH RECORD IS VALIDATED. With the launcher's own functions -- `validate_request`, `validate_authority`
(under THIS version's registered 20-pass evidence contract) and `validate_owner` -- before anything is
written, and again on the bytes in `seeds.partial/` before the rename. The cost bound is checked with the
ledger's own arithmetic, `budget.validate_plan`, not with a second copy of the rule.

WHERE IT MUST RUN. From a FULL checkout at the source commit. No torch, no network, no AWS call, no ledger
write.

USAGE (run with `python -B`):
    python -B prepare_cm2x_study.py --source-sha <S> --dry-run
    python -B prepare_cm2x_study.py --source-sha <S> --write

LABEL. Coordinator direction, transcribed by the builder; NOT an owner signature. The USD 20.00 all-services
cap is the envelope this job record must fit; a launch still requires the launch operator's own authorization.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
import sys
import tempfile
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                     # the CNCM folder ("FOR CODEX TO BUILD CAS NATIVE ...")
sys.path[:0] = [str(ROOT), str(ROOT / 'research/CAS_META_2_COMPOSITION')]
from aws import budget as ledger  # noqa: E402
from aws import typed_pointer_launch as launch  # noqa: E402
from cas_meta2.typed_teaching import pointer_contract as contract  # noqa: E402

SEED = 20260918
VERSION = contract.EXPERIMENT_VERSION
STUDY_SCHEMA = 'cncm.typed-pointer-critical-mass-2x-study-admission/0.1'
OWNER_SCHEMA_NOTE = ('COORDINATOR DIRECTION, NOT AN OWNER SIGNATURE: this record fixes the envelope the '
                     '20-pass registered full run must fit. It authorizes no spend by itself.')
# The coordinator's own words, quoted verbatim from the builder brief. They are NOT the owner's words, and
# the record says so in `answered_by`, `transcribed_by_agent` and `authority_note`.
COORDINATOR_INSTRUCTION_RAW = ('Add or adjust only what is necessary so pass 10 and pass 20 are both '
                               'evaluated, the new 20-pass run is treated as the registered full run for this '
                               'new experiment version, required artifacts include pass 11-20 outputs, and '
                               'wall/instance limits plus job record fit a USD 20 all-services cap.')
COORDINATOR_MESSAGE_FULL_RAW = ('Build the smallest prospective versioned 20-pass experiment that keeps all '
                                'scientific inputs/settings equal to R18 except training duration and '
                                'necessary resource/output envelope. Preserve one-machine, no-retry, cleanup '
                                'requirements. Do not launch AWS.')
APPROVAL_CONTEXT = ('Critical-mass 2x: ONE fresh 20-pass run on the switch-ON Helm training path, seed '
                    '20260918, after R17 (the same study at 10 passes, seed 20260917) was delivered.')
SCOPE = ('The single registered full run of the critical-mass 2x version: model seed 20260918, 20 passes, '
         'one machine, no automatic retry, cleanup required. Replaces the R18 10-pass registered full run '
         'for this version; the R18 admission records stay untouched and are cited, not rewritten.')
ALL_SERVICES_CAP_USD = '20.00'
OTHER_SERVICES_ALLOWANCE_USD = '0.10'
# The measured basis of the projection: the DELIVERED R17 job (10 passes, seed 20260917). Raw fields are
# quoted in `pointer_contract.py` beside `PASSES`; the two numbers used here are its seconds per update and
# its measured non-worker overhead.
R17_RECEIPT = 'records/typed_pointer_001/receipt_analogy_on_20260917'
R17_SECONDS_PER_UPDATE = '4.896459789305442'
R17_UPDATES = 1470
NON_WORKER_OVERHEAD_SECONDS = '598.1888835440004'
PROJECTED_WORKER_SECONDS = '16937.84343287343'
PROJECTED_INSTANCE_SECONDS = '17536.03231641743'
EXPECTED_COST_USD = '13.76'
R18_JOB_RECORD = ROOT / 'records/typed_pointer_001/admission_analogy_on_001/seeds/20260918/request.json'
SEED_OUTPUT = HERE / 'seeds'
PARTIAL_OUTPUT = HERE / 'seeds.partial'
PACKAGE_PARENT = ROOT / 'research/CAS_META_2_COMPOSITION/records/typed_pointer_001'
RECEIPT_DIR = ROOT / 'records/typed_pointer_001/receipt_cm2x_20260918'


def digest(raw):
    """sha256 over BYTES -- the launcher's own digest, and the one every record field here is bound with.

    NOT `pointer_contract.digest`, which canonicalises its argument as JSON first: the authority's
    `owner_authorization_sha256`, `design_sha256` and the manifest digest are all raw-byte digests of canonical
    JSON, and using the JSON-canonicalising one raises `TypeError: Object of type bytes is not JSON
    serializable` on the first `digest(canonical(...))` call. Found by a local rehearsal of this freeze.
    """
    return launch.digest(raw)


def canonical(value):
    return launch.canonical(value)


def stop_unless(condition, reason):
    if not condition:
        raise ValueError('CM2X_ADMISSION_STOPPED:' + reason)


def git(*arguments):
    return launch.shared._run_git(list(arguments), ROOT).decode('utf-8')


def git_path(path):
    """A path spelled the way `git status` spells it: FORWARD slashes, on every platform.

    This writer's own paths come from `pathlib`, which uses backslashes on Windows, while git always reports
    forward slashes. Comparing the two without normalising them never matches, which is how the tolerance check
    came to refuse the writer's own declared outputs in a local rehearsal.
    """
    return str(path).replace('\\', '/')


def repo_path(path):
    """This writer's path as `git status --porcelain` reports it: relative to the REPOSITORY ROOT.

    The writer lives inside the CNCM folder, and `git status --porcelain` (unlike plain `git status`) always
    reports paths from the repository root, prefixed with the CNCM tree's own path inside the repository. The
    two spellings have to be reconciled before the tolerance check can mean anything.
    """
    return launch.shared.GIT_PREFIX + git_path(path.relative_to(ROOT))


def porcelain_path(field):
    """`git status --porcelain`'s path field, with git's C-style quoting undone.

    Git quotes a path that contains a space (or a byte outside ASCII) as `"..."` and escapes backslashes and
    double quotes inside it. This tree's paths all contain spaces, so every status line this writer reads is
    quoted; comparing the raw field against a plain path silently mismatches.
    """
    path = field.strip()
    if len(path) >= 2 and path.startswith('"') and path.endswith('"'):
        body, out, index = path[1:-1], [], 0
        while index < len(body):
            character = body[index]
            if character == '\\' and index + 1 < len(body):
                index += 1
                escape = body[index]
                out.append({'n': '\n', 't': '\t', '"': '"', '\\': '\\'}.get(escape, escape))
            else:
                out.append(character)
            index += 1
        return ''.join(out)
    return path


def check_source(source_sha):
    """The commit is HEAD, and the only worktree changes are this writer's own declared outputs.

    `git status --porcelain` C-QUOTES any path with a space in it, and every path in this tree has one
    ("FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"). Reading the path without undoing that quoting made the
    tolerance check compare `"cas_only_reasoner/...` against `cas_only_reasoner/...` and refuse the writer's own
    untracked package directory -- found by a local rehearsal of this freeze, before any spend.
    """
    stop_unless(type(source_sha) is str and launch.shared.HEX40.fullmatch(source_sha) is not None, 'SOURCE_SHA_FORM')
    head = git('-c', 'core.autocrlf=false', 'rev-parse', 'HEAD').strip()
    stop_unless(head == source_sha, 'HEAD_IS_NOT_THE_SOURCE_COMMIT:%s' % head[:12])
    status = git('-c', 'core.autocrlf=false', 'status', '--porcelain')
    # `git status --porcelain` reports paths relative to the REPOSITORY ROOT, while this writer's paths are
    # relative to the CNCM folder it lives in, so the repository's own prefix is what makes them comparable.
    tolerated = tuple(repo_path(path) for path in (SEED_OUTPUT, PARTIAL_OUTPUT, PACKAGE_PARENT))
    unexpected = []
    for line in status.splitlines():
        path = git_path(porcelain_path(line[3:]))
        if not any(path == hold or path.startswith(hold + '/') for hold in tolerated):
            unexpected.append(line.strip())
    stop_unless(not unexpected, 'UNEXPECTED_WORKTREE_CHANGE:' + '|'.join(unexpected)[:2000])
    stop_unless(RECEIPT_DIR.is_dir() is False, 'RECEIPT_DIR_ALREADY_EXISTS:' + str(RECEIPT_DIR))
    return head


def package_dir(source_sha):
    return PACKAGE_PARENT / ('package_' + source_sha[:8])


def verify_package(source_sha):
    """The built package's identity, plus the version and pass count read out of the SHIPPED manifest."""
    directory = package_dir(source_sha)
    stop_unless(directory.is_dir(), 'BUILD_THE_PACKAGE_FIRST:%s' % ('python -B %s --package %s --source-sha %s'
                % (ROOT / 'research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py', directory, source_sha)))
    receipt = json.loads((directory / 'receipt.json').read_bytes())
    stop_unless(receipt.get('schema') == 'cncm.typed-pointer-package-receipt/0.1'
                and receipt.get('status') == 'SOURCE_ONLY_NO_LAUNCH', 'PACKAGE_RECEIPT_SCHEMA')
    stop_unless(receipt.get('source_sha') == source_sha, 'PACKAGE_SOURCE_SHA')
    raw = (directory / 'source.zip').read_bytes()
    stop_unless(len(raw) == receipt['archive_bytes'] and digest(raw) == receipt['archive_sha256'],
                'PACKAGE_ARCHIVE_BYTES')
    manifest = receipt['manifest']
    stop_unless(digest(canonical(manifest)) == receipt['manifest_sha256'], 'PACKAGE_MANIFEST_BYTES')
    stop_unless(manifest.get('experiment', {}).get('version') == VERSION, 'PACKAGE_IS_NOT_THIS_VERSION')
    stop_unless(manifest.get('typed_design', {}).get('passes') == contract.PASSES == 20,
                'PACKAGE_IS_NOT_THE_20_PASS_DESIGN')
    with ZipFile(directory / 'source.zip') as archive:
        shipped = archive.read(launch.shared.MANIFEST_NAME)
    stop_unless(digest(shipped) == receipt['manifest_sha256'], 'PACKAGE_SHIPPED_MANIFEST')
    shipped_manifest = json.loads(shipped)
    stop_unless(shipped_manifest.get('experiment', {}).get('version') == VERSION
                and shipped_manifest.get('typed_design', {}).get('passes') == 20
                and shipped_manifest.get('worker_script') == launch.WORKER_NAME,
                'PACKAGE_SHIPPED_MANIFEST_CONTENT')
    return {'source_sha': source_sha, 'archive_sha256': receipt['archive_sha256'],
            'manifest_sha256': receipt['manifest_sha256'], 'archive_bytes': receipt['archive_bytes'],
            'archive': str(directory / 'source.zip'), 'package_dir': str(directory),
            'packaged_version': manifest['experiment']['version'],
            'packaged_passes': manifest['typed_design']['passes']}


def cost_bound():
    """The ledger's own rule decides the bound; the cap is applied to the reservation plus the allowance."""
    plan = launch.reservation_plan_for(launch.DESIGN)
    bound = ledger.validate_plan(plan, launch.RESERVATION_USD)
    reservation = Decimal(launch.RESERVATION_USD)
    allowance = Decimal(OTHER_SERVICES_ALLOWANCE_USD)
    cap = Decimal(ALL_SERVICES_CAP_USD)
    all_services = reservation + allowance
    stop_unless(reservation >= bound, 'RESERVATION_BELOW_THE_DECLARED_BOUND')
    stop_unless(all_services <= cap, 'ALL_SERVICES_OVER_THE_CAP:%s>%s' % (all_services, cap))
    return {'all_services_cap_usd': ALL_SERVICES_CAP_USD, 'other_services_allowance_usd':
            OTHER_SERVICES_ALLOWANCE_USD, 'hourly_usd': plan['on_demand_hourly_usd_max'],
            'ancillary_reserved_usd': plan['ancillary_reserved_usd'],
            'instance_seconds_max': plan['runtime_seconds_max'],
            'compute_and_ancillary_bound_usd': str(bound), 'reservation_usd': launch.RESERVATION_USD,
            'reservation_plus_allowance_usd': str(all_services), 'headroom_to_cap_usd': str(cap - all_services),
            'ledger_rule': ('budget.validate_plan: reserved_usd >= on_demand_hourly_usd_max x '
                            'runtime_seconds_max / 3600 + ancillary_reserved_usd'),
            'ledger_rule_verdict': 'PASS', 'expected_cost_usd': EXPECTED_COST_USD,
            'expected_basis': ('R17 measured %s s per update over %d updates, %s s of measured non-worker '
                               'overhead: projected worker clock %s s, projected instance %s s'
                               % (R17_SECONDS_PER_UPDATE, R17_UPDATES, NON_WORKER_OVERHEAD_SECONDS,
                                  PROJECTED_WORKER_SECONDS, PROJECTED_INSTANCE_SECONDS)),
            'projected_worker_seconds': PROJECTED_WORKER_SECONDS,
            'projected_instance_seconds': PROJECTED_INSTANCE_SECONDS,
            'receipt_of_the_basis': R17_RECEIPT}


def build(source_sha, package, job, *, owner_question):
    """The three job records, in memory, built and validated with the launcher's own functions."""
    inputs_sha256 = launch.frozen_inputs_hash(source_sha)
    design_sha256 = digest(canonical(launch.DESIGN))
    evidence_contract_sha256 = launch.run_evidence.contract_digest(launch.evidence_contract())
    r18_raw = R18_JOB_RECORD.read_bytes() if R18_JOB_RECORD.is_file() else None
    owner = {'schema': launch.OWNER_SCHEMA, 'candidate': launch.CANDIDATE,
             'owner_instruction_raw': COORDINATOR_INSTRUCTION_RAW,
             'owner_message_full_raw': COORDINATOR_MESSAGE_FULL_RAW,
             'owner_question': owner_question, 'answered_date': '2026-09-24',
             'answered_by': 'coordinator direction to the builder (not the owner)',
             'approval_context': APPROVAL_CONTEXT, 'scope': SCOPE,
             'authority_note': OWNER_SCHEMA_NOTE, 'transcribed_by_agent': True, 'is_owner_signature': False,
             'label': 'DEEPSEEK_BUILT_CODEX_TO_REVIEW', 'runner': 'Codex (launch operator)',
             'job': job, 'job_kind': 'registered_full_run', 'experiment_version': VERSION,
             'condition': contract.CONDITION, 'model_seed': SEED, 'bounds': launch.BOUNDS,
             'cost_bound': cost_bound(),
             'one_machine_at_a_time': True, 'automatic_retries': 0, 'cleanup_required': True,
             'best_checkpoint_selection': False,
             'evaluated_pass_checkpoints': list(contract.PASS_CHECKPOINTS),
             'supersedes': {'what': 'the R18 10-pass registered full run for seed %d' % SEED,
                            'why': ('the 20-pass run is the registered full run for experiment version %s'
                                    % VERSION),
                            'r18_job_record': (None if r18_raw is None else
                                               {'path': str(R18_JOB_RECORD), 'sha256': digest(r18_raw)}),
                            'r18_records_untouched': True}}
    owner_raw = canonical(owner)
    identity = {key: package[key] for key in ('source_sha', 'archive_sha256', 'manifest_sha256')}
    request = {'schema': launch.REQUEST_SCHEMA, 'job': job, **identity, 'launch_authorized': False}
    authority = {'schema': launch.AUTHORITY_SCHEMA, 'job': job, **identity, **launch.BOUNDS,
                 'candidate': launch.CANDIDATE, 'owner_authorization_sha256': digest(owner_raw),
                 'inputs_sha256': inputs_sha256, 'design_sha256': design_sha256,
                 'evidence_contract_sha256': evidence_contract_sha256,
                 'worker_config': launch.worker_config(job, source_sha=source_sha)}
    stop_unless(authority['worker_config']['inputs_sha256'] == inputs_sha256, 'CONFIG_INPUTS_HASH')
    stop_unless(authority['worker_config']['design']['passes'] == contract.PASSES == 20, 'CONFIG_PASSES')
    stop_unless(authority['worker_config']['design']['experiment_version'] == VERSION, 'CONFIG_VERSION')
    launch.validate_request(request)
    launch.validate_authority(authority)
    with tempfile.TemporaryDirectory(prefix='prepare_cm2x_') as scratch:
        probe = Path(scratch) / 'owner.json'
        probe.write_bytes(owner_raw)
        launch.validate_owner(probe, authority)
    return owner_raw, request, authority


def study_record(source_sha, package, bindings, job, *, owner_question):
    document = launch.evidence_contract()
    required_keys = set(launch.run_evidence.contract_keys(document))
    pass_names = ['pass_%02d_%s.jsonl' % (number, suffix) for number in range(11, 21)
                  for suffix in ('batches', 'updates')]
    return {'schema': STUDY_SCHEMA, 'status': 'FROZEN_BEFORE_FIRST_RUN', 'experiment_version': VERSION,
            'pass_multiplier_over_r18': contract.VERSION_PASS_MULTIPLIER,
            'source_sha': source_sha, 'source_checkout': str(ROOT), 'candidate': launch.CANDIDATE,
            'config_schema': launch.CONFIG_SCHEMA, 'condition': contract.CONDITION, 'model_seed': SEED,
            'one_machine_at_a_time': True, 'automatic_retries': 0, 'cleanup_required': True,
            'cleanup_owner': ('the launcher lifecycle (aws/graph_training_candidate_launch.py): compute '
                              'cleanup runs on every exit path and `cleanup.complete` is part of the '
                              'delivered test'),
            'best_checkpoint_selection': False,
            'training_duration': {'passes': contract.PASSES, 'checkpoints_evaluated':
                                  list(contract.PASS_CHECKPOINTS), 'full_course_checkpoints':
                                  list(contract.FULL_COURSE_CHECKPOINTS),
                                  'both_durations_evaluated': [10, 20],
                                  'registered_full_run_is_the_20_pass_plan': True},
            'required_artifacts': {'count': document['required_count'],
                                   'evidence_contract_sha256': bindings['evidence_contract_sha256'],
                                   'pass_output_names_required': pass_names,
                                   'covers_passes_11_to_20': all('results/artifacts/' + name in required_keys
                                                                 for name in pass_names),
                                   'pass_10_evaluations': ['course_p10', 'development_p10'],
                                   'pass_20_evaluations': ['course_p20', 'development_p20']},
            'limits': launch.BOUNDS, 'cost_bound': cost_bound(), 'canonical_ledger': str(launch.CANONICAL_LEDGER),
            'canonical_ledger_is_file_here': launch.CANONICAL_LEDGER.is_file(),
            'package': package, 'source_facts': bindings, 'owner_question': owner_question,
            'owner_note': OWNER_SCHEMA_NOTE,
            'supersedes': ('the R18 10-pass registered full run (admission_analogy_on_001/seeds/20260918) for '
                           'experiment version %s; R18 receipt and admission bytes are not modified' % VERSION),
            'job': job, 'job_record': None, 'run_with': ('the launcher\'s own recorded argv below; one job, so '
                                                         'there is nothing to sequence and no runner retries'),
            'numeric_runs_completed': 0}


def prepare(source_sha, *, write, owner_question=None):
    stop_unless(owner_question is None or (type(owner_question) is str and owner_question.strip()),
                'OWNER_QUESTION')
    stop_unless(not SEED_OUTPUT.exists() and not PARTIAL_OUTPUT.exists(),
                'TARGET_EXISTS_NO_OVERWRITE:' + str(SEED_OUTPUT))
    head = check_source(source_sha)
    package = verify_package(source_sha)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    job = 'cas-meta2-tpntr-' + stamp + '-' + source_sha[:8] + '-m-' + str(SEED)
    stop_unless(re.fullmatch(launch.JOB_PATTERN, job) is not None, 'JOB_FORM:' + job)
    stop_unless(len(job + contract.BUCKET_SUFFIX) <= 63, 'BUCKET_TOO_LONG')
    owner_raw, request, authority = build(source_sha, package, job, owner_question=owner_question)
    bindings = {'inputs_sha256': authority['inputs_sha256'], 'design_sha256': authority['design_sha256'],
                'evidence_contract_sha256': authority['evidence_contract_sha256']}
    study = study_record(source_sha, package, bindings, job, owner_question=owner_question)
    job_record = {'job': job, 'kind': 'registered_full_run', 'condition': contract.CONDITION,
                  'model_seed': SEED, 'claim_bearing_flag_expected': True,
                  'experiment_version': VERSION, 'passes': contract.PASSES,
                  'receipt_dir': str(RECEIPT_DIR), 'reservation_usd': launch.RESERVATION_USD,
                  'launch_command': ['python', '-B',
                                     str(ROOT / 'research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py')],
                  'launch_argv': ['--execute', '--request', str(SEED_OUTPUT / str(SEED) / 'request.json'),
                                  '--request-sha256', digest(canonical(request)),
                                  '--authority', str(SEED_OUTPUT / str(SEED) / 'authority.json'),
                                  '--authority-sha256', digest(canonical(authority)),
                                  '--owner-authorization', str(SEED_OUTPUT / str(SEED) / 'owner.json'),
                                  '--receipt-dir', str(RECEIPT_DIR),
                                  '--ledger-path', str(launch.CANONICAL_LEDGER)]}
    study['job_record'] = job_record
    files = [(SEED_OUTPUT / str(SEED) / 'owner.json', owner_raw),
             (SEED_OUTPUT / str(SEED) / 'request.json', canonical(request)),
             (SEED_OUTPUT / str(SEED) / 'authority.json', canonical(authority)),
             (SEED_OUTPUT / 'study.json', canonical(study))]
    if not write:
        print(json.dumps({'mode': 'DRY_RUN_NOTHING_WRITTEN', 'head': head[:12], 'job': job,
                          'limits': launch.BOUNDS, 'cost_bound': cost_bound(),
                          'required_artifact_count': launch.evidence_contract()['required_count'],
                          'receipt_dir': str(RECEIPT_DIR),
                          'package': package, 'would_write': [str(path) for path, _ in files]},
                         sort_keys=True), flush=True)
        return 0
    PARTIAL_OUTPUT.mkdir(parents=True)
    for path, raw in files:
        target = PARTIAL_OUTPUT / path.relative_to(SEED_OUTPUT)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'xb') as stream:
            stream.write(raw)
    # Re-read the bytes as they now sit on disk and re-run the launcher's own checks on them.
    request_back = json.loads((PARTIAL_OUTPUT / str(SEED) / 'request.json').read_bytes())
    authority_back = json.loads((PARTIAL_OUTPUT / str(SEED) / 'authority.json').read_bytes())
    launch.validate_request(request_back)
    launch.validate_authority(authority_back)
    launch.validate_owner(PARTIAL_OUTPUT / str(SEED) / 'owner.json', authority_back)
    PARTIAL_OUTPUT.rename(SEED_OUTPUT)
    for path, _ in files:
        print(json.dumps({'written': str(path), 'bytes': path.stat().st_size,
                          'sha256': digest(path.read_bytes())}, sort_keys=True), flush=True)
    print(json.dumps({'status': study['status'], 'job': job, 'experiment_version': VERSION,
                      'passes': contract.PASSES, 'receipt_dir': str(RECEIPT_DIR),
                      'launch_command': ' '.join(job_record['launch_command'] + job_record['launch_argv'])},
                     sort_keys=True), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source-sha', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--write', action='store_true')
    parser.add_argument('--owner-question')
    args = parser.parse_args(argv)
    return prepare(args.source_sha, write=args.write, owner_question=args.owner_question)


if __name__ == '__main__':
    raise SystemExit(main())
