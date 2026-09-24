"""Freeze the three switch-ON pointer-training jobs before the first result. Admission records only; no launch.

WHAT THIS IS. The admission writer for HELM-ANALOGY-REPAIR-1 item 2: train switch-ON checkpoints on the existing
Helm training path (`aws/typed_pointer_launch.py` -> `cncm.typed_pointer_worker`, g7.2xlarge, us-west-2), three
seeds, one job per seed. It is modelled on `records/typed_pointer_001/prepare_study.py` (the Helm 2.0 freeze) and
calls the SAME launcher functions to build and check every record. It differs where that script cannot be reused:

  * it writes ONLY `admission_analogy_on_001/<seed>/{owner,request,authority}.json` and
    `admission_analogy_on_001/study.json`, each opened with mode 'xb' (never overwritten), and refuses before
    writing anything if any of them, any seed folder, or any receipt folder already exists;
  * receipt folders are `records/typed_pointer_001/receipt_analogy_on_<seed>` and must not exist;
  * the owner record quotes the owner's 2026-09-23 words verbatim (below), not the 2026-09-19 decisions;
  * it does NOT build the source package and does NOT run a rehearsal. The package is built beforehand by the
    launcher's own `--package` step (the command is printed by `--dry-run` and recorded in `study.json`), at the
    path `prepare_study.py` used: `research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_<sha8>`.
    This writer then verifies that package byte for byte and points every record at it.

HOW EACH RECORD IS VALIDATED. With the launcher's own functions, exactly as `prepare_study.py` does:
`launch.validate_request(request)`, `launch.validate_authority(authority)` (the registered 10-pass evidence
contract, because these are full runs), and `launch.validate_owner(path, authority)`. All of it runs BEFORE any
file is written. `validate_owner` reads a path, so the owner bytes are first checked from a file in a temporary
directory outside the repository that is deleted at once; after `--write`, every written file is read back and
checked again, owner from its final path.

WHERE IT MUST RUN. From a FULL (non-sparse) checkout at the source commit, located where the launcher can find the
canonical meta1 budget ledger (a checkout under `.../FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/`).
`launch.worker_config` -> `pointer_contract.make_config` loads the frozen course, and `launch.frozen_inputs_hash`
reads the working-tree inventory (cncm/, cas_meta2/, the pinned course material and the 18 practice checkpoints).
It needs no torch and no network.

USAGE (from anywhere; paths are resolved from this file):
    python prepare_on_study.py --source-sha <40 hex> --dry-run     # prints what it would write; writes nothing
    python prepare_on_study.py --source-sha <40 hex> --write       # writes the ten files, then re-checks them
    optional: --owner-question "<the question the owner answered, verbatim>"

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED. Runner: the Claude coordinator (temporary takeover). This script transcribes the
owner's words; it is not an owner signature.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import inspect
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'research/CAS_META_2_COMPOSITION')]
from aws import typed_pointer_launch as launch
from cas_meta2.typed_teaching import pointer_contract as contract
from cas_meta2.typed_teaching import pointer_learner

RECEIPTS = ROOT / 'records/typed_pointer_001'
PACKAGE_PARENT = ROOT / 'research/CAS_META_2_COMPOSITION/records/typed_pointer_001'
LAUNCHER = ROOT / 'research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py'
STUDY_SCHEMA = 'cncm.typed-pointer-analogy-on-study-admission/0.1'
PACKAGE_RECEIPT_SCHEMA = 'cncm.typed-pointer-package-receipt/0.1'

# The owner's words, verbatim, as the coordinator relayed them. Item 3 is the approval; the full message is kept
# so no item is separated from its context. Neither is paraphrased. The sha256 pins catch an accidental edit.
OWNER_INSTRUCTION_RAW = '3. YOU HAVE THE GO AHEAD FOR THE SWITCH ON MODEL'
OWNER_MESSAGE_FULL_RAW = ('4. KEEP IT (G6E.XLARGE) 3. YOU HAVE THE GO AHEAD FOR THE SWITCH ON MODEL '
                          '2. GO WITH YOUR RECOMMENDATION 6 AND 7 NODE 1. FOR RESCORER PICK WHICH EVER ONE '
                          'MAKES FOR A BETTER MODEL')
OWNER_INSTRUCTION_SHA256 = 'a8c84d3c9fe8906b0f8c4a1aa8065648c2c341003ecc2065ec9e2854f73a0a6d'
OWNER_MESSAGE_FULL_SHA256 = 'f3a62b2e43112d0d120437948d47e7707152021ec8f49a3b742d4b0186372f58'
OWNER_ANSWERED_DATE = '2026-09-23'
OWNER_ITEM = '3'
APPROVAL_CONTEXT = ('HELM-ANALOGY-REPAIR-1 acceptance item 2: train switch-ON checkpoints, three seeds, one job per '
                    'seed, on the Helm 2.0 training path (coordinator brief, 2026-09-23).')
SCOPE = ('One of three switch-ON pointer-training seeds (20260917, 20260918, 20260919); one job per seed; '
         'no automatic retry.')
BUDGET_BASIS = ("Each job reserves the launcher's pinned RESERVATION_USD ($15.00); the total is 3 x $15.00 = "
                "$45.00, as the coordinator's brief of 2026-09-23 states it. The owner's quoted words approve the "
                "switch-ON model and name no dollar amount.")
LABEL = 'CLAUDE_BUILT_CLAUDE_CHECKED'
RUNNER = 'Claude coordinator (temporary takeover)'
CLAIM_BEARING_SEMANTICS = ('The worker marks a full 10-pass run claim_bearing=true as a historical-protocol flag '
                           '(cncm/typed_pointer_worker.py, schedule_plan). This is NOT a design-v0.2 claim.')
# The numbers the brief states. The writer refuses, rather than silently recording other numbers, if the
# launcher or the contract has moved.
EXPECTED_SEEDS = (20260917, 20260918, 20260919)
EXPECTED_BOUNDS = {'training': True, 'jobs': 1, 'automatic_retries': 0, 'reservation_usd': '15.00',
                   'instance_type': 'g7.2xlarge', 'region': 'us-west-2'}
MAXIMUM_NEW_RESERVATION_USD = '45.00'


def stop_unless(condition, reason):
    """Explicit stop, never an `assert` (which `python -O` removes)."""
    if not condition:
        raise SystemExit('ANALOGY_ON_ADMISSION_STOPPED:' + reason)


def git(*args):
    return subprocess.run(['git', '-c', 'core.autocrlf=false', *args], cwd=ROOT, check=True,
                          capture_output=True).stdout


def package_dir(source_sha):
    return PACKAGE_PARENT / ('package_' + source_sha[:8])


def package_command(source_sha):
    """The launcher's own `--package` step, exactly as `prepare_study.py`'s `build_pointer_package` call."""
    return ['python', '-B', str(LAUNCHER), '--package', str(package_dir(source_sha)), '--source-sha', source_sha]


def dirty_paths_except(allowed_prefix):
    """Every changed or untracked path under ROOT, except those under `allowed_prefix` (repo-relative)."""
    fields = git('status', '--porcelain=v1', '-z', '--untracked-files=all', '--', '.').split(b'\0')
    dirty, index = [], 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        code, path = entry[:2].decode('ascii'), entry[3:].decode('utf-8')
        if 'R' in code or 'C' in code:
            index += 1                      # a rename or copy carries its source path as the next field
        if not path.startswith(allowed_prefix):
            dirty.append(code + ' ' + path)
    return dirty


def check_source(source_sha):
    """The commit, the tree, and that this source really is the switch-ON design with the ablation fix."""
    stop_unless(type(source_sha) is str and launch.shared.HEX40.fullmatch(source_sha) is not None, 'SOURCE_SHA_FORM')
    head = git('rev-parse', 'HEAD').decode('ascii').strip()
    stop_unless(head == source_sha, 'SOURCE_SHA_IS_NOT_HEAD:' + head)
    prefix = git('rev-parse', '--show-prefix').decode('utf-8').strip()
    stop_unless(prefix == launch.shared.GIT_PREFIX, 'GIT_PREFIX:' + prefix)
    allowed = prefix + package_dir(source_sha).relative_to(ROOT).as_posix() + '/'
    dirty = dirty_paths_except(allowed)
    stop_unless(not dirty, 'COMMIT_FIRST_ONLY_THE_PACKAGE_MAY_BE_UNTRACKED:' + '|'.join(dirty)[:2000])
    launch.configure_reduced_schedule(None)            # full runs: the registered plan, never a smoke opt-in
    stop_unless(launch.SMOKE_REQUEST is None, 'REDUCED_SCHEDULE_SET')
    default = inspect.signature(pointer_learner._build_container).parameters['analogy_focus_comparison'].default
    stop_unless(default is True, 'SWITCH_DEFAULT_IS_NOT_ON')
    worker = launch._probe()
    heads = dict(worker.ABLATION_COMPONENTS).get('heads', ())
    stop_unless('analogy_head.' in heads, 'ABLATION_HEADS_ROW_LACKS_ANALOGY_HEAD')
    stop_unless(tuple(contract.MODEL_SEEDS) == EXPECTED_SEEDS, 'MODEL_SEEDS_CHANGED')
    stop_unless(all(launch.BOUNDS.get(key) == value for key, value in EXPECTED_BOUNDS.items())
                and launch.RESERVATION_USD == launch.BOUNDS['reservation_usd'], 'BOUNDS_CHANGED')
    stop_unless(Decimal(launch.RESERVATION_USD) * len(EXPECTED_SEEDS) == Decimal(MAXIMUM_NEW_RESERVATION_USD),
                'TOTAL_RESERVATION')
    stop_unless(launch.digest(OWNER_INSTRUCTION_RAW.encode('utf-8')) == OWNER_INSTRUCTION_SHA256
                and launch.digest(OWNER_MESSAGE_FULL_RAW.encode('utf-8')) == OWNER_MESSAGE_FULL_SHA256
                and OWNER_INSTRUCTION_RAW in OWNER_MESSAGE_FULL_RAW, 'OWNER_WORDS_EDITED')
    return {'analogy_focus_comparison_default': default, 'ablation_heads_row': list(heads),
            'model_variant': pointer_learner.MODEL_VARIANT, 'checkpoint_schema': pointer_learner.CHECKPOINT_SCHEMA}


def check_package(source_sha):
    """`None` if the package is not built yet; otherwise the verified identity every record points at."""
    directory = package_dir(source_sha)
    if not directory.exists():
        return None
    receipt_raw = (directory / 'receipt.json').read_bytes()
    receipt = json.loads(receipt_raw)
    stop_unless(receipt.get('schema') == PACKAGE_RECEIPT_SCHEMA and receipt.get('status') == 'SOURCE_ONLY_NO_LAUNCH'
                and receipt.get('source_sha') == source_sha, 'PACKAGE_RECEIPT')
    archive = directory / 'source.zip'
    raw = archive.read_bytes()
    stop_unless(launch.digest(raw) == receipt['archive_sha256'] and len(raw) == receipt['archive_bytes'],
                'PACKAGE_ARCHIVE_BYTES')
    # The launcher finds the archive through the receipt's own `archive` path (`_locate_archive`), so that path
    # must be this very file in this checkout, and the launcher's own search must return it.
    stop_unless(Path(receipt['archive']).resolve() == archive.resolve(), 'PACKAGE_ARCHIVE_PATH')
    stop_unless(launch.lifecycle._locate_archive(receipt['archive_sha256']).resolve() == archive.resolve(),
                'LAUNCHER_CANNOT_LOCATE_THIS_ARCHIVE')
    with ZipFile(archive) as bundle:
        manifest_raw = bundle.read(launch.shared.MANIFEST_NAME)
        worker_source = bundle.read(launch.WORKER_NAME)
    stop_unless(launch.digest(manifest_raw) == receipt['manifest_sha256'], 'PACKAGE_MANIFEST_BYTES')
    manifest = json.loads(manifest_raw)
    stop_unless(launch.canonical(manifest) == launch.canonical(receipt['manifest']), 'PACKAGE_RECEIPT_MANIFEST')
    stop_unless(manifest['inputs_sha256'] == launch.frozen_inputs_hash(source_sha), 'PACKAGE_INPUTS_NOT_THIS_SOURCE')
    stop_unless({key: manifest['frozen_budget'].get(key) for key in launch.BOUNDS} == launch.BOUNDS,
                'PACKAGE_BOUNDS')
    stop_unless(manifest['transport']['predeclared_contract_sha256']
                == launch.run_evidence.contract_digest(launch.evidence_contract()), 'PACKAGE_EVIDENCE_CONTRACT')
    # Built with the smoke opt-in unset: the generated worker carries no shrunken-schedule line.
    stop_unless(b'CNCM_POINTER_REDUCED_SCHEDULE' not in worker_source, 'PACKAGE_HAS_A_REDUCED_SCHEDULE')
    return {'source_sha': source_sha, 'archive_sha256': receipt['archive_sha256'],
            'manifest_sha256': receipt['manifest_sha256'], 'archive': str(archive),
            'archive_bytes': receipt['archive_bytes'], 'receipt_sha256': launch.digest(receipt_raw)}


def targets():
    """Every path this writer creates, and the receipt folders that must not exist yet."""
    seeds = {seed: HERE / str(seed) for seed in EXPECTED_SEEDS}
    files = [path / name for path in seeds.values() for name in ('owner.json', 'request.json', 'authority.json')]
    receipts = {seed: RECEIPTS / ('receipt_analogy_on_' + str(seed)) for seed in EXPECTED_SEEDS}
    return seeds, files + [HERE / 'study.json'], receipts


def pin(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': launch.digest(raw)}


def build(source_sha, identity, owner_question):
    """Every record, in memory. `identity` is the verified package identity, or `None` before the package exists."""
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    seeds, _, receipts = targets()
    pending = identity is None
    package = identity or {'source_sha': source_sha, 'archive_sha256': 'PENDING_PACKAGE',
                           'manifest_sha256': 'PENDING_PACKAGE'}
    inputs_sha256 = launch.frozen_inputs_hash(source_sha)
    design_sha256 = launch.digest(launch.canonical(launch.DESIGN))
    evidence_contract_sha256 = launch.run_evidence.contract_digest(launch.evidence_contract())
    files, jobs = [], []
    for seed in EXPECTED_SEEDS:
        job = 'cas-meta2-tpntr-' + stamp + '-' + source_sha[:8] + '-m-' + str(seed)
        stop_unless(re.fullmatch(launch.JOB_PATTERN, job) is not None, 'JOB_FORM:' + job)
        owner = {'schema': launch.OWNER_SCHEMA, 'candidate': launch.CANDIDATE,
                 'owner_instruction_raw': OWNER_INSTRUCTION_RAW, 'owner_message_full_raw': OWNER_MESSAGE_FULL_RAW,
                 'owner_item_answered': OWNER_ITEM, 'answered_date': OWNER_ANSWERED_DATE,
                 'owner_question': owner_question,
                 'owner_question_note': (None if owner_question is not None else
                                         'Not given to the builder; the coordinator holds the question.'),
                 'approval_context': APPROVAL_CONTEXT, 'scope': SCOPE, 'budget_basis': BUDGET_BASIS,
                 'transcribed_by_agent': True, 'is_owner_signature': False,
                 'label': LABEL, 'runner': RUNNER, 'job': job, 'condition': contract.CONDITION,
                 'model_seed': seed, 'bounds': launch.BOUNDS}
        owner_raw = launch.canonical(owner)
        identity_fields = {key: package[key] for key in ('source_sha', 'archive_sha256', 'manifest_sha256')}
        request = {'schema': launch.REQUEST_SCHEMA, 'job': job, **identity_fields, 'launch_authorized': False}
        authority = {'schema': launch.AUTHORITY_SCHEMA, 'job': job, **identity_fields, **launch.BOUNDS,
                     'candidate': launch.CANDIDATE, 'owner_authorization_sha256': launch.digest(owner_raw),
                     'inputs_sha256': inputs_sha256, 'design_sha256': design_sha256,
                     'evidence_contract_sha256': evidence_contract_sha256,
                     'worker_config': launch.worker_config(job, source_sha=source_sha)}
        # The config's own inputs hash must be the launcher's (the guard `inputs_hash_cross_check` exists for).
        stop_unless(authority['worker_config']['inputs_sha256'] == inputs_sha256, 'CONFIG_INPUTS_HASH')
        if not pending:
            launch.validate_request(request)
            launch.validate_authority(authority)
            with tempfile.TemporaryDirectory(prefix='prepare_on_study_') as scratch:
                probe = Path(scratch) / 'owner.json'
                probe.write_bytes(owner_raw)
                launch.validate_owner(probe, authority)
        directory = seeds[seed]
        raws = {'owner': owner_raw, 'request': launch.canonical(request), 'authority': launch.canonical(authority)}
        for name, raw in raws.items():
            files.append((directory / (name + '.json'), raw))
        pins = {name: pin(directory / (name + '.json'), raw) for name, raw in raws.items()}
        receipt_dir = str(receipts[seed])
        jobs.append({'job': job, 'condition': contract.CONDITION, 'model_seed': seed, **pins,
                     'receipt_dir': receipt_dir,
                     'launch_argv': ['--execute', '--request', pins['request']['path'],
                                     '--request-sha256', pins['request']['sha256'],
                                     '--authority', pins['authority']['path'],
                                     '--authority-sha256', pins['authority']['sha256'],
                                     '--owner-authorization', pins['owner']['path'],
                                     '--receipt-dir', receipt_dir, '--ledger-path', str(launch.CANONICAL_LEDGER)]})
    return files, jobs, package, pending, {'inputs_sha256': inputs_sha256, 'design_sha256': design_sha256,
                                           'evidence_contract_sha256': evidence_contract_sha256}


def study_record(source_sha, source_facts, package, jobs, bindings, owner_question):
    return {'schema': STUDY_SCHEMA, 'status': 'FROZEN_BEFORE_FIRST_RUN', 'label': LABEL, 'runner': RUNNER,
            'source_sha': source_sha, 'source_checkout': str(ROOT), 'candidate': launch.CANDIDATE,
            'config_schema': launch.CONFIG_SCHEMA, **source_facts, **bindings,
            'package_archive': package.get('archive'), 'package_archive_sha256': package['archive_sha256'],
            'package_manifest_sha256': package['manifest_sha256'],
            'package_receipt_sha256': package.get('receipt_sha256'), 'package_command': package_command(source_sha),
            'owner_instruction_raw': OWNER_INSTRUCTION_RAW, 'owner_message_full_raw': OWNER_MESSAGE_FULL_RAW,
            'owner_item_answered': OWNER_ITEM, 'answered_date': OWNER_ANSWERED_DATE,
            'owner_question': owner_question, 'approval_context': APPROVAL_CONTEXT, 'budget_basis': BUDGET_BASIS,
            'claim_bearing_semantics': CLAIM_BEARING_SEMANTICS, 'jobs': jobs,
            'maximum_new_reservation_usd': MAXIMUM_NEW_RESERVATION_USD,
            'reservation_per_job_usd': launch.RESERVATION_USD, 'bounds': launch.BOUNDS,
            'one_job_per_seed': True, 'automatic_retries': 0,
            'launcher': str(LAUNCHER), 'canonical_ledger': str(launch.CANONICAL_LEDGER),
            'execute_study_py': ('NOT APPLICABLE: records/typed_pointer_001/execute_study.py requires the five '
                                 '2026-09-19 decisions and the Helm 2.0 protocol; launch each job with its own '
                                 'launch_argv instead'),
            'rehearsal': 'NOT RUN BY THIS WRITER (it writes only the admission records)',
            'numeric_runs_completed': 0}


def prepare(source_sha, *, write, owner_question=None):
    stop_unless(owner_question is None or (type(owner_question) is str and owner_question.strip()), 'OWNER_QUESTION')
    source_facts = check_source(source_sha)
    seeds, paths, receipts = targets()
    existing = [str(path) for path in [*seeds.values(), *paths, *receipts.values()] if path.exists()]
    stop_unless(not existing, 'TARGET_EXISTS_NO_OVERWRITE:' + '|'.join(existing))
    identity = check_package(source_sha)
    if write:
        stop_unless(identity is not None, 'BUILD_THE_PACKAGE_FIRST:' + json.dumps(package_command(source_sha)))
        launch.validate_ledger_path(launch.CANONICAL_LEDGER)   # a stat only: the admission is tied to this checkout
    files, jobs, package, pending, bindings = build(source_sha, identity, owner_question)
    study = study_record(source_sha, source_facts, package, jobs, bindings, owner_question)
    study_raw = launch.canonical(study)
    files.append((HERE / 'study.json', study_raw))
    stop_unless(sorted(str(path) for path, _ in files) == sorted(str(path) for path in paths), 'TARGET_SET')
    if not write:
        print(json.dumps({'mode': 'DRY_RUN_NOTHING_WRITTEN', 'package_built': not pending,
                          'validated_with_launcher_functions': not pending,
                          'package_command': package_command(source_sha),
                          'canonical_ledger': str(launch.CANONICAL_LEDGER),
                          'canonical_ledger_is_file_here': launch.CANONICAL_LEDGER.is_file(),
                          'note': 'job stamps are taken at run time, so --write produces different job names '
                                  'and hashes from this dry run'}, sort_keys=True), flush=True)
        for path, raw in files:
            print(json.dumps({'would_write': str(path), 'bytes': len(raw), 'sha256': launch.digest(raw),
                              'content': json.loads(raw)}, sort_keys=True), flush=True)
        return 0
    for seed, directory in seeds.items():
        directory.mkdir()
    for path, raw in files:
        with path.open('xb') as stream:
            stream.write(raw)
    # Read every file back and re-run the launcher's own checks on the bytes that are now on disk.
    for path, raw in files:
        stop_unless(path.read_bytes() == raw, 'WRITTEN_BYTES:' + str(path))
    for job in jobs:
        request = json.loads(Path(job['request']['path']).read_bytes())
        authority = json.loads(Path(job['authority']['path']).read_bytes())
        launch.validate_request(request)
        launch.validate_authority(authority)
        launch.validate_owner(job['owner']['path'], authority)
        print(json.dumps({'prepared': job['job'], 'receipt_dir': job['receipt_dir']}), flush=True)
    print(json.dumps({'status': study['status'], 'study': pin(HERE / 'study.json', study_raw)}), flush=True)
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
