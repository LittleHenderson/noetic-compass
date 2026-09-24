"""Freeze the three switch-ON pointer-training jobs before the first result. Admission records only; no launch.

WHAT THIS IS. The admission writer for HELM-ANALOGY-REPAIR-1 item 2: train switch-ON checkpoints on the existing
Helm training path (`aws/typed_pointer_launch.py` -> `cncm.typed_pointer_worker`, g7.2xlarge, us-west-2), three
seeds, one job per seed. It is modelled on `records/typed_pointer_001/prepare_study.py` (the Helm 2.0 freeze) and
calls the SAME launcher functions to build and check every record. Its sibling `prepare_on_smoke.py` freezes the
short test run (the smoke) that the owner approved to run first; `run_on_study.py` runs all four jobs in order and
enforces the owner's stop rules.

REVISION 2 (2026-09-23), after a fresh review of 2cd6aed9 (verdict CHANGES_REQUIRED):
  * BUDGET (review finding 2). The first revision said the owner named no dollar amount. That was wrong. The owner
    was asked the budget question quoted in `on_study_common.OWNER_BUDGET_QUESTION_RAW` and answered
    "Up to $60 (Recommended)" (owner record, commit d6c9faa9, addendum to section 3). The records now quote the
    question, the answer and the chosen option's text verbatim, and state the $60.00 ceiling (smoke $15.00 + 3 x
    $15.00), one machine at a time, no automatic retries, and the three stop rules.
  * ITEM 1 FIRST. `--item1-commit <C> --item1-reading-sha256 <hex>` are required. The reading is read with
    `git show <C>:<fixed RESULTS_READING.json path>` (revision 1, review MINOR 4); <C> must be an ancestor of
    `origin/research/helm-integration-20260923`; the bytes must hash to the given value; and `item1_verdict` must
    be `OFF_PRESERVED_ON_T4`. Otherwise nothing is written. The commit, blob id, sha256 and verdict are recorded,
    and a byte copy is written beside the records.
  * SEED DELIVERED RULE (revision 1, review MINOR 1). study.json records the coordinator's decision verbatim:
    "coordinator decision 2026-09-24: owner's delivered test only; degraded checks reported, not a stop".
  * ORDERING (finding 3). HEAD must still be the source commit, but the tree may now carry, untracked, exactly the
    declared outputs of both writers: the two package folders and the smoke writer's `smoke/` folder
    (`on_study_common.tolerated_prefixes`). Nothing else. Both packages must carry the same `inputs_sha256`.
  * CRASH SAFETY (finding 5). All admission files are written into `seeds.partial/`, read back and re-validated,
    and only then renamed to `seeds/`. An existing `.partial` folder stops every writer until a person inspects it.
  * MIGRATION RECORD. The committed `MIGRATION_ON_SHAPES.json` (53 keys / 203,424 parameters ON versus 48 / 174,303
    OFF, the five `analogy_head` tensors, the Helm 2.0 `initial.pt` identities) is verified and pinned in the record.
  * The package's shipped bytes are now also checked: switch default ON and the `heads` row owning `analogy_head.`
    are read (with `ast`) from the built `source.zip`, not only from this process's imports.

WHAT IT WRITES. One folder, `seeds/`: `seeds/<seed>/{owner,request,authority}.json` for 20260917, 20260918, 20260919,
`seeds/study.json`, `seeds/item1_reading.json`. Every file is opened with mode 'xb'. Receipt folders are
`records/typed_pointer_001/receipt_analogy_on_<seed>` and must not exist.

THE PACKAGE. Built beforehand by the launcher's own `--package` step (a separate process, so the smoke opt-in is
unset and the shipped worker carries no reduced-schedule line), at
`research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_<sha8>`. This writer verifies it byte for byte.

HOW EACH RECORD IS VALIDATED. With the launcher's own functions: `validate_request`, `validate_authority` (the
registered 10-pass evidence contract, because these are full runs) and `validate_owner`, before anything is
written, and again on the bytes in `seeds.partial/` before the rename.

WHERE IT MUST RUN. From a FULL checkout at the source commit under
`.../FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/<name>/`, the same checkout the jobs will be launched
from. No torch, no network, no AWS call.

USAGE (run with `python -B`):
    python -B prepare_on_study.py --source-sha <S> --item1-commit <C> --item1-reading-sha256 <hex> --dry-run
    python -B prepare_on_study.py --source-sha <S> --item1-commit <C> --item1-reading-sha256 <hex> --write
    optional: --owner-question "<the question behind the item-3 answer, verbatim>"

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED. Runner: the Claude coordinator (temporary takeover). This script transcribes the
owner's words; it is not an owner signature.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import on_study_common as common  # noqa: E402

ROOT = common.ROOT
sys.path[:0] = [str(ROOT), str(ROOT / 'research/CAS_META_2_COMPOSITION')]
from aws import typed_pointer_launch as launch  # noqa: E402
from cas_meta2.typed_teaching import pointer_contract as contract  # noqa: E402
from cas_meta2.typed_teaching import pointer_learner  # noqa: E402

stop_unless = common.make_stop('ANALOGY_ON_ADMISSION_STOPPED:')
STUDY_SCHEMA = 'cncm.typed-pointer-analogy-on-study-admission/0.2'
OWNER_ITEM = '3'
APPROVAL_CONTEXT = ('HELM-ANALOGY-REPAIR-1 acceptance item 2: train switch-ON checkpoints, three seeds, one job per '
                    'seed, on the Helm 2.0 training path, after the smoke and only after acceptance item 1 passed.')
SCOPE = ('One of three switch-ON pointer-training seeds (20260917, 20260918, 20260919); one job per seed; '
         'no automatic retry; launched only after the smoke delivered, by run_on_study.py.')
CLAIM_BEARING_SEMANTICS = ('The worker marks a full 10-pass run claim_bearing=true as a historical-protocol flag '
                           '(cncm/typed_pointer_worker.py, schedule_plan). This is NOT a design-v0.2 claim.')


def check_source(source_sha):
    """The commit, the tree, the switch-ON design, the owner record and the migration record."""
    stop_unless(type(source_sha) is str and launch.shared.HEX40.fullmatch(source_sha) is not None, 'SOURCE_SHA_FORM')
    common.check_head(source_sha, stop_unless)
    common.refuse_partials(stop_unless)
    dirty = common.dirty_paths(source_sha, stop_unless)
    stop_unless(not dirty, 'COMMIT_FIRST_ONLY_THE_DECLARED_OUTPUTS_MAY_BE_UNTRACKED:' + '|'.join(dirty)[:2000])
    launch.configure_reduced_schedule(None)            # full runs: the registered plan, never a smoke opt-in
    stop_unless(launch.SMOKE_REQUEST is None, 'REDUCED_SCHEDULE_SET')
    _, facts = common.check_switch_on_source(launch, contract, pointer_learner, stop_unless)
    owner_record = common.verify_owner_words(stop_unless)
    migration = common.verify_migration(stop_unless)
    return facts, owner_record, migration


def package_command(source_sha):
    """The launcher's own `--package` step, exactly as `prepare_study.py`'s `build_pointer_package` call."""
    return ['python', '-B', str(common.LAUNCHER), '--package', str(common.seed_package_dir(source_sha)),
            '--source-sha', source_sha]


def check_package(source_sha):
    """`None` if the package is not built yet; otherwise the verified identity every record points at."""
    directory = common.seed_package_dir(source_sha)
    if not directory.exists():
        return None
    return common.verify_package(launch, directory, source_sha, stop_unless, smoke=False)


def targets():
    """Every admission path this writer creates (inside `seeds/`), and the receipt folders that must not exist."""
    seeds = {seed: common.SEED_OUTPUT / str(seed) for seed in common.SEEDS}
    files = [path / name for path in seeds.values() for name in ('owner.json', 'request.json', 'authority.json')]
    files += [common.SEED_OUTPUT / 'study.json', common.SEED_OUTPUT / common.ITEM1_COPY_NAME]
    receipts = {seed: common.seed_receipt_dir(seed) for seed in common.SEEDS}
    return seeds, files, receipts


def build(source_sha, identity, *, owner_question, owner_record, item1):
    """Every record, in memory. `identity` is the verified package identity, or `None` before the package exists."""
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    seeds, _, receipts = targets()
    pending = identity is None
    package = identity or {'source_sha': source_sha, 'archive_sha256': 'PENDING_PACKAGE',
                           'manifest_sha256': 'PENDING_PACKAGE'}
    inputs_sha256 = launch.frozen_inputs_hash(source_sha)
    design_sha256 = common.digest(launch.canonical(launch.DESIGN))
    evidence_contract_sha256 = launch.run_evidence.contract_digest(launch.evidence_contract())
    smoke_jobs = common.other_job_names(common.SMOKE_OUTPUT / 'smoke.json')
    files, jobs = [], []
    for seed in common.SEEDS:
        job = 'cas-meta2-tpntr-' + stamp + '-' + source_sha[:8] + '-m-' + str(seed)
        stop_unless(re.fullmatch(launch.JOB_PATTERN, job) is not None, 'JOB_FORM:' + job)
        stop_unless(job not in smoke_jobs, 'JOB_NAME_COLLIDES_WITH_THE_SMOKE_JOB_RERUN_IN_A_SECOND:' + job)
        owner = {'schema': launch.OWNER_SCHEMA, 'candidate': launch.CANDIDATE,
                 'owner_instruction_raw': common.OWNER_INSTRUCTION_RAW,
                 'owner_message_full_raw': common.OWNER_MESSAGE_FULL_RAW,
                 'owner_item_answered': OWNER_ITEM, 'answered_date': common.OWNER_ANSWERED_DATE,
                 'owner_question': owner_question,
                 'owner_question_note': (None if owner_question is not None else
                                         'The question behind item 3 was not given to the builder; the owner record '
                                         '(commit d6c9faa9) lists it as "training a switch-ON model".'),
                 **common.owner_budget_fields(owner_record), 'item1_reading': item1,
                 'approval_context': APPROVAL_CONTEXT, 'scope': SCOPE,
                 'transcribed_by_agent': True, 'is_owner_signature': False,
                 'label': common.LABEL, 'runner': common.RUNNER, 'job': job, 'job_kind': 'seed',
                 'condition': contract.CONDITION, 'model_seed': seed, 'bounds': launch.BOUNDS}
        owner_raw = launch.canonical(owner)
        identity_fields = {key: package[key] for key in ('source_sha', 'archive_sha256', 'manifest_sha256')}
        request = {'schema': launch.REQUEST_SCHEMA, 'job': job, **identity_fields, 'launch_authorized': False}
        authority = {'schema': launch.AUTHORITY_SCHEMA, 'job': job, **identity_fields, **launch.BOUNDS,
                     'candidate': launch.CANDIDATE, 'owner_authorization_sha256': common.digest(owner_raw),
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
        pins = {name: common.pin(directory / (name + '.json'), raw) for name, raw in raws.items()}
        receipt_dir = str(receipts[seed])
        jobs.append({'job': job, 'kind': 'seed', 'condition': contract.CONDITION, 'model_seed': seed,
                     'claim_bearing_flag_expected': True, **pins, 'receipt_dir': receipt_dir,
                     'reservation_usd': launch.RESERVATION_USD,
                     'launch_command': ['python', '-B', str(common.LAUNCHER)],
                     'launch_argv': ['--execute', '--request', pins['request']['path'],
                                     '--request-sha256', pins['request']['sha256'],
                                     '--authority', pins['authority']['path'],
                                     '--authority-sha256', pins['authority']['sha256'],
                                     '--owner-authorization', pins['owner']['path'],
                                     '--receipt-dir', receipt_dir, '--ledger-path', str(launch.CANONICAL_LEDGER)]})
    return files, jobs, package, pending, {'inputs_sha256': inputs_sha256, 'design_sha256': design_sha256,
                                           'evidence_contract_sha256': evidence_contract_sha256}


def study_record(source_sha, source_facts, package, jobs, bindings, *, owner_question, owner_record, item1,
                 migration, smoke_inputs):
    return {'schema': STUDY_SCHEMA, 'status': 'FROZEN_BEFORE_FIRST_RUN', 'label': common.LABEL,
            'runner': common.RUNNER, 'source_sha': source_sha, 'source_checkout': str(ROOT),
            'candidate': launch.CANDIDATE, 'config_schema': launch.CONFIG_SCHEMA, **source_facts, **bindings,
            'package': package, 'package_command': package_command(source_sha),
            'smoke_package_inputs_sha256': smoke_inputs,
            'inputs_sha256_equal_across_packages': (True if smoke_inputs is not None else
                                                    'SMOKE_PACKAGE_NOT_BUILT_YET_THE_SMOKE_WRITER_CHECKS_IT'),
            'owner_instruction_raw': common.OWNER_INSTRUCTION_RAW,
            'owner_message_full_raw': common.OWNER_MESSAGE_FULL_RAW, 'owner_item_answered': OWNER_ITEM,
            'answered_date': common.OWNER_ANSWERED_DATE, 'owner_question': owner_question,
            'approval_context': APPROVAL_CONTEXT, **common.owner_budget_fields(owner_record),
            'item1_reading': item1, 'migration_record': migration,
            'starts': {'rule': ('matched starts from the same seeds as Helm 2.0, with the five analogy_head tensors '
                                'seeded separately (seed 20260923)'),
                       'helm2_initial_pt_sha256': migration['helm2_initial_pt_sha256'],
                       'deciding_check': 'prereg amendment A5.5 (commit d7023288), on AWS, after training'},
            'limits': launch.BOUNDS, 'claim_bearing_semantics': CLAIM_BEARING_SEMANTICS,
            'seed_delivered_rule': common.SEED_DELIVERED_RULE,
            'seed_delivered_rule_means': ('a seed counts as delivered when the launcher says so: exit 0, '
                                          'completed_deliverable true, cleanup complete, status '
                                          'AWS_CANDIDATE_FINISHED; a non-empty degraded_checks list is logged and '
                                          'reported by run_on_study.py, not a stop'),
            'jobs': jobs,
            'launch_order': ['smoke:%d' % common.SMOKE_SEED] + ['seed:%d' % seed for seed in common.SEEDS],
            'launcher': str(common.LAUNCHER), 'canonical_ledger': str(launch.CANONICAL_LEDGER),
            'run_with': 'records/typed_pointer_001/admission_analogy_on_001/run_on_study.py',
            'execute_study_py': ('NOT APPLICABLE: records/typed_pointer_001/execute_study.py requires the five '
                                 '2026-09-19 decisions and the Helm 2.0 protocol; run_on_study.py launches each job '
                                 'with its own launch_argv instead'),
            'rehearsal': 'NOT RUN BY THIS WRITER (it writes only the admission records)',
            'numeric_runs_completed': 0}


def prepare(source_sha, *, write, item1_commit, item1_sha256, owner_question=None):
    stop_unless(owner_question is None or (type(owner_question) is str and owner_question.strip()), 'OWNER_QUESTION')
    item1, item1_raw = common.read_item1(item1_commit, item1_sha256, stop_unless)
    source_facts, owner_record, migration = check_source(source_sha)
    seeds, paths, receipts = targets()
    existing = [str(path) for path in [common.SEED_OUTPUT, *receipts.values()] if path.exists()]
    stop_unless(not existing, 'TARGET_EXISTS_NO_OVERWRITE:' + '|'.join(existing))
    identity = check_package(source_sha)
    if write:
        stop_unless(identity is not None, 'BUILD_THE_PACKAGE_FIRST:' + json.dumps(package_command(source_sha)))
        launch.validate_ledger_path(launch.CANONICAL_LEDGER)   # a stat only: the admission is tied to this checkout
    smoke_inputs = common.other_package_inputs(common.smoke_package_dir(source_sha))
    inputs_sha256 = launch.frozen_inputs_hash(source_sha)
    stop_unless(identity is None or identity['inputs_sha256'] == inputs_sha256, 'SEED_PACKAGE_INPUTS')
    stop_unless(smoke_inputs in (None, inputs_sha256), 'SEED_AND_SMOKE_PACKAGES_CARRY_DIFFERENT_INPUTS')
    files, jobs, package, pending, bindings = build(source_sha, identity, owner_question=owner_question,
                                                    owner_record=owner_record, item1=item1)
    study = study_record(source_sha, source_facts, package, jobs, bindings, owner_question=owner_question,
                         owner_record=owner_record, item1=item1, migration=migration, smoke_inputs=smoke_inputs)
    study_raw = launch.canonical(study)
    files += [(common.SEED_OUTPUT / 'study.json', study_raw), (common.SEED_OUTPUT / common.ITEM1_COPY_NAME, item1_raw)]
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
            print(json.dumps({'would_write': str(path), 'bytes': len(raw), 'sha256': common.digest(raw)},
                             sort_keys=True), flush=True)
        print(json.dumps({'study_record': json.loads(study_raw)}, sort_keys=True), flush=True)
        return 0

    def recheck(locate):
        """The launcher's own checks again, on the bytes as they now sit in `seeds.partial/`."""
        for job in jobs:
            request = json.loads(locate(job['request']['path']).read_bytes())
            authority = json.loads(locate(job['authority']['path']).read_bytes())
            launch.validate_request(request)
            launch.validate_authority(authority)
            launch.validate_owner(locate(job['owner']['path']), authority)
        stop_unless(common.digest(locate(common.SEED_OUTPUT / common.ITEM1_COPY_NAME).read_bytes())
                    == item1['sha256'], 'ITEM1_COPY_BYTES')

    written = common.write_folder_atomically(common.SEED_OUTPUT, files, recheck, stop_unless)
    for job in jobs:
        print(json.dumps({'prepared': job['job'], 'receipt_dir': job['receipt_dir']}), flush=True)
    print(json.dumps({'status': study['status'], 'written': written, 'study_json_sha256': common.digest(study_raw),
                      'inputs_sha256': inputs_sha256}, sort_keys=True), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--item1-commit', required=True)
    parser.add_argument('--item1-reading-sha256', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--write', action='store_true')
    parser.add_argument('--owner-question')
    args = parser.parse_args(argv)
    return prepare(args.source_sha, write=args.write, item1_commit=args.item1_commit,
                   item1_sha256=args.item1_reading_sha256, owner_question=args.owner_question)


if __name__ == '__main__':
    raise SystemExit(main())
