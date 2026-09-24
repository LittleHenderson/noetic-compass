"""Freeze the switch-ON SMOKE job -- one short reduced-schedule test run WITH ablations -- before it runs.

WHAT THIS IS. The owner's spending answer for switch-ON training ("Up to $60 (Recommended)", 2026-09-23) approves
"Short test run + 3 seeds, one at a time". This script freezes the admission records for that short test run (the
"smoke"). It is modelled on Helm 2.0's `records/typed_pointer_001/prepare_smoke.py` (read from git; that script
cannot be reused: it fixes "ablations": False, quotes the 2026-09-19 owner words and writes into
`admission_smoke_001`) and on this folder's `prepare_on_study.py`.

WHAT THE SMOKE IS FOR. The ON container has 53 state-dict keys; the worker's ablation table now owns all 53
(`cncm/typed_pointer_worker.py`, the `heads` row). A short run with ablations ON exercises that fix, the checkpoint
round trip and the collection path on the real g7.2xlarge before three ~3-hour seeds are spent. Its reduced schedule
is fixed, verbatim, in `on_study_common.SMOKE_LITERAL`: 1 pass, 8 updates, evaluations at passes 0 and 1, reloads
and replays on, phase B, retention and interference off, ABLATIONS ON. The worker marks it `claim_bearing=false`.

HOW THE SCHEDULE REACHES THE INSTANCE. Only through the package. `typed_pointer_launch.bootstrap_source()` inserts
one environment line into the generated worker when the process-local opt-in is set, and `main()` refuses
`--reduced-schedule` together with `--package`. So this script sets the opt-in with the launcher's own
`configure_reduced_schedule(literal)` and THEN builds its own package in-process, into
`research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_on_smoke_<sha8>/`. It then reads the line back out
of the BUILT `source.zip` (the only bytes that reach the instance), as Helm 2.0's `verify_bootstrap_embedding` did.
The launch process must be given the same literal with `--reduced-schedule`; the exact argv is recorded.

WHAT IT CHECKS BEFORE WRITING (any failure stops with `ANALOGY_ON_SMOKE_STOPPED:<reason>`):
  * acceptance item 1 passed: `--item1-reading` hashes to `--item1-reading-sha256` and its `item1_verdict` is
    `OFF_PRESERVED_ON_T4` (owner order: training only after item 1);
  * HEAD is the source commit; the only untracked paths are the four declared outputs of the two writers
    (`on_study_common.tolerated_prefixes`); no `.partial` folder exists;
  * the switch default is ON and the `heads` ablation row owns `analogy_head.`, both in this process AND in the
    shipped bytes of the built package;
  * seeds, bounds, the $15.00 reservation and the $60.00 ceiling; the owner's words against the committed owner
    record (commit d6c9faa9); the migration record against the tensor inventory it cites;
  * the literal through the worker's own `schedule_plan()`, then 51 artifact names / 54 required entries;
  * the built package (receipt, bytes, `_locate_archive`, manifest, inputs hash, bounds) and, if the seed package is
    already built, that both packages carry the same `inputs_sha256`.
Then the launcher's own validators: `validate_request`, `validate_authority(authority, smoke_evidence_contract())`,
`validate_owner`.

WHAT IT WRITES. One folder, `smoke/`, written first as `smoke.partial/`, read back and re-validated, then renamed:
`smoke/20260917/{owner,request,authority}.json`, `smoke/smoke.json`, `smoke/item1_reading.json` (a byte copy of the
item-1 reading). Plus the package folder above (built only by `--write`, reused after verification if it already
exists). `--dry-run` writes nothing and builds nothing.

WHERE IT MUST RUN. From a FULL checkout at the source commit under
`.../FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/<name>/`, the same checkout the jobs will be launched
from (`BUILDER_REPORT_ON_TRAINING_PREP.md`, answer (a)). No torch, no network, no AWS call.

USAGE (run with `python -B` so no `__pycache__` appears):
    python -B prepare_on_smoke.py --source-sha <S> --item1-reading <path> --item1-reading-sha256 <hex> --dry-run
    python -B prepare_on_smoke.py --source-sha <S> --item1-reading <path> --item1-reading-sha256 <hex> --write

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED. Runner: the Claude coordinator (temporary takeover). Not an owner signature.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import tempfile
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import on_study_common as common  # noqa: E402

ROOT = common.ROOT
sys.path[:0] = [str(ROOT), str(ROOT / 'research/CAS_META_2_COMPOSITION')]
from aws import typed_pointer_launch as launch  # noqa: E402
from cas_meta2.typed_teaching import pointer_contract as contract  # noqa: E402
from cas_meta2.typed_teaching import pointer_learner  # noqa: E402

stop_unless = common.make_stop('ANALOGY_ON_SMOKE_STOPPED:')
SMOKE_SCHEMA = 'cncm.typed-pointer-analogy-on-smoke-admission/0.1'
# The distinctive token inside `launch.BOOTSTRAP_ENV_ANCHOR`. The reduced-schedule line must sit right after it.
ANCHOR_TOKEN = 'CAS_META2_RUN_TEACHING_CYCLE'
APPROVAL_CONTEXT = ('HELM-ANALOGY-REPAIR-1 acceptance item 2: the short test run the owner approved before the three '
                    'switch-ON seeds ("Short test run + 3 seeds, one at a time"), on the Helm 2.0 training path.')
SMOKE_SCOPE = ('One switch-ON smoke job on seed 20260917 with a reduced schedule and ablations ON; not claim-bearing; '
               'its $15.00 reservation is part of the $60.00 ceiling and authorises no other job.')
# What the plan must be, read back from the WORKER'S OWN `schedule_plan()`. Every flag is pinned, because an omitted
# key would silently inherit the registered plan's value.
INTENDED_PLAN = {'passes': 1, 'updates': 8, 'prelast': True, 'evaluations': [0, 1],
                 'evaluation_phases': ('course_p00', 'course_p01', 'development_p00', 'development_p01'),
                 'phase_a': ['initial', 'pass_01', 'final'], 'phase_b': False, 'ablations': True,
                 'retention': False, 'interference': False, 'replays': True, 'reload': True,
                 'reloads': ['initial', 'final'], 'checkpoints': ('initial', 'pass_01', 'prelast', 'final')}
SMOKE_MUST_SHOW = ('launcher exit code 0', 'result.json completed_deliverable true, cleanup complete, status '
                   'AWS_CANDIDATE_FINISHED', 'reduced_schedule.json carries this literal',
                   'worker_report.json: ablation_status COMPLETE, report_only_status ablations and '
                   'checkpoint_check_phase_a COMPLETE, claim_bearing false')


def check_source(source_sha):
    """The commit, the tree, the switch-ON design, the owner record and the migration record."""
    stop_unless(type(source_sha) is str and launch.shared.HEX40.fullmatch(source_sha) is not None, 'SOURCE_SHA_FORM')
    common.check_head(source_sha, stop_unless)
    common.refuse_partials(stop_unless)
    dirty = common.dirty_paths(source_sha, stop_unless)
    stop_unless(not dirty, 'COMMIT_FIRST_ONLY_THE_DECLARED_OUTPUTS_MAY_BE_UNTRACKED:' + '|'.join(dirty)[:2000])
    stop_unless(launch.SMOKE_REQUEST is None, 'SMOKE_OPT_IN_ALREADY_SET_BEFORE_THIS_SCRIPT')
    worker, facts = common.check_switch_on_source(launch, contract, pointer_learner, stop_unless)
    owner_record = common.verify_owner_words(stop_unless)
    migration = common.verify_migration(stop_unless)
    return worker, facts, owner_record, migration


def validate_schedule(worker):
    """The literal through the worker's own planner; every intended value is read back from the plan it returns."""
    request = json.loads(common.SMOKE_LITERAL)
    stop_unless(launch.canonical(request).decode('utf-8').rstrip('\n') == common.SMOKE_LITERAL,
                'SMOKE_LITERAL_NOT_CANONICAL')
    stop_unless(set(request) == set(launch.SMOKE_REQUEST_KEYS) == set(worker.REDUCED_SCHEDULE_KEYS),
                'SMOKE_LITERAL_MUST_WRITE_OUT_ALL_TEN_KEYS')
    plan, claim_bearing = worker.schedule_plan(source=common.SMOKE_LITERAL)
    stop_unless(claim_bearing is False, 'SMOKE_SCHEDULE_IS_CLAIM_BEARING')
    for key, expected in INTENDED_PLAN.items():
        stop_unless(plan[key] == expected, 'SMOKE_SCHEDULE_%s:%r' % (key.upper(), plan[key]))
    stop_unless(tuple(plan['ablation_phases']) == tuple(worker.ABLATION_PHASES) and len(plan['ablation_phases']) == 5,
                'SMOKE_SCHEDULE_ABLATION_PHASES')
    names = worker.expected_artifact_names(plan)
    stop_unless(len(names) == common.SMOKE_ARTIFACT_NAMES, 'SMOKE_ARTIFACT_NAMES:%d' % len(names))
    wanted = {'ablations.json'} | {phase + suffix for phase in worker.ABLATION_PHASES
                                   for suffix in ('_predictions.json', '_scoring.json')}
    stop_unless(wanted <= set(names), 'SMOKE_ABLATION_ARTIFACTS_NOT_REQUIRED')
    return plan, names


def rendered_line(worker):
    """In-process render only (dry run without a package): the line right after the anchor. Not the shipped bytes."""
    lines = launch.bootstrap_source().splitlines()
    anchors = [index for index, line in enumerate(lines) if line.strip() == launch.BOOTSTRAP_ENV_ANCHOR]
    stop_unless(len(anchors) == 1, 'RENDERED_ANCHOR_COUNT')
    expected = 'os.environ[%r] = %r' % (worker.REDUCED_SCHEDULE_ENV, common.SMOKE_LITERAL)
    stop_unless(lines[anchors[0] + 1].strip() == expected, 'RENDERED_LINE_NOT_AFTER_ANCHOR')
    return expected


def verify_bootstrap_embedding(archive, worker):
    """`(worker_member_sha256, shipped_assignment)` read out of the BUILT package, not out of a fresh render.

    Ported from Helm 2.0's `prepare_smoke.py`, whose measured facts still hold for this launcher (`aws/` is unchanged
    since 20208c92): the bootstrap is embedded in the transport-wrapped worker as a one-line string literal, so its
    quotes arrive as `\\'` and its newlines as the two characters `\\` `n`. Adjacency to the anchor is asserted, not
    only presence.
    """
    with ZipFile(archive) as bundle:
        source = bundle.read(launch.WORKER_NAME).decode('utf-8')
    stop_unless(ANCHOR_TOKEN in launch.BOOTSTRAP_ENV_ANCHOR, 'ANCHOR_TOKEN_DRIFTED')
    for label, needle in (('ANCHOR', ANCHOR_TOKEN), ('ENV_VAR', worker.REDUCED_SCHEDULE_ENV)):
        stop_unless(source.count(needle) == 1, 'PACKAGE_%s_COUNT:%d' % (label, source.count(needle)))
    anchor_at = source.index(ANCHOR_TOKEN)
    env_at = source.index(worker.REDUCED_SCHEDULE_ENV)
    stop_unless(anchor_at < env_at, 'PACKAGE_LINE_BEFORE_THE_ANCHOR')
    open_at = source.rindex('os.environ[', 0, env_at)
    stop_unless(env_at - open_at <= 16, 'PACKAGE_ASSIGNMENT_SHAPE:%d' % (env_at - open_at))
    between = source[anchor_at + len(ANCHOR_TOKEN):open_at]
    stop_unless('os.environ[' not in between, 'PACKAGE_ASSIGNMENT_BETWEEN_ANCHOR_AND_LINE')
    separators = between.count('\n') + between.count('\\n')
    stop_unless(separators == 1, 'PACKAGE_SEPARATOR_COUNT:%d' % separators)
    stop_unless(len(between) <= 48, 'PACKAGE_LINE_NOT_ADJACENT:%d' % len(between))
    # The assignment ends at the next escaped newline (or a real one, whichever comes first).
    ends = [at for at in (source.find('\\n', env_at), source.find('\n', env_at)) if at != -1]
    assignment = source[open_at:min(ends) if ends else len(source)]
    stop_unless(assignment.count(common.SMOKE_LITERAL) == 1, 'PACKAGE_LITERAL_NOT_IN_THE_SHIPPED_LINE')
    return common.digest(source.encode('utf-8')), assignment


def ensure_package(source_sha, worker, *, write):
    """`(identity, built_by_this_run)`. Builds only with `write`; an existing package is verified and reused.

    Reuse is what makes a crash after the build safe: the build is the launcher's own function and cannot be made
    atomic from here (its receipt pins the absolute archive path, so the folder cannot be renamed afterwards).
    """
    directory = common.smoke_package_dir(source_sha)
    built = False
    if not directory.exists():
        if not write:
            return None, False
        stop_unless(launch.SMOKE_REQUEST == json.loads(common.SMOKE_LITERAL), 'SMOKE_OPT_IN_NOT_SET_BEFORE_BUILD')
        launch.build_pointer_package(directory, source_sha=source_sha)
        built = True
    identity = common.verify_package(launch, directory, source_sha, stop_unless, smoke=True)
    worker_sha256, assignment = verify_bootstrap_embedding(Path(identity['archive']), worker)
    stop_unless(worker_sha256 == identity['shipped_worker_member_sha256'], 'SHIPPED_WORKER_READ_TWICE_DIFFERS')
    return {**identity, 'shipped_reduced_schedule_assignment': assignment}, built


def documents(source_sha, identity, *, contract_document, owner_record, item1):
    """The smoke's three admission documents, built from the launcher's own constants."""
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    job = 'cas-meta2-tpntr-' + stamp + '-' + source_sha[:8] + '-m-' + str(common.SMOKE_SEED)
    stop_unless(re.fullmatch(launch.JOB_PATTERN, job) is not None, 'JOB_FORM:' + job)
    stop_unless(job not in common.other_job_names(common.SEED_OUTPUT / 'study.json'),
                'JOB_NAME_COLLIDES_WITH_A_SEED_JOB_RERUN_IN_A_SECOND:' + job)
    config = launch.worker_config(job, source_sha=source_sha)
    bucket = job + '-' + launch.shared.RESOURCE_PLAN['account']
    stop_unless(config['bucket'] == bucket and len(bucket) == 63, 'SMOKE_BUCKET')
    owner = {'schema': launch.OWNER_SCHEMA, 'candidate': launch.CANDIDATE,
             'owner_instruction_raw': common.OWNER_BUDGET_ANSWER_RAW,
             'owner_instruction_is': ('the option the owner chose when asked the budget question below; its text '
                                      'approves "Short test run + 3 seeds, one at a time"'),
             'owner_training_approval_raw': common.OWNER_INSTRUCTION_RAW,
             'owner_message_full_raw': common.OWNER_MESSAGE_FULL_RAW,
             'answered_date': common.OWNER_ANSWERED_DATE, 'approval_context': APPROVAL_CONTEXT, 'scope': SMOKE_SCOPE,
             **common.owner_budget_fields(owner_record), 'item1_reading': item1,
             'transcribed_by_agent': True, 'is_owner_signature': False, 'label': common.LABEL,
             'runner': common.RUNNER, 'job': job, 'job_kind': 'smoke', 'condition': contract.CONDITION,
             'model_seed': common.SMOKE_SEED, 'claim_bearing': False,
             'reduced_schedule_literal': common.SMOKE_LITERAL, 'bounds': launch.BOUNDS}
    owner_raw = launch.canonical(owner)
    identity_fields = {key: identity[key] for key in ('source_sha', 'archive_sha256', 'manifest_sha256')}
    request = {'schema': launch.REQUEST_SCHEMA, 'job': job, **identity_fields, 'launch_authorized': False}
    authority = {'schema': launch.AUTHORITY_SCHEMA, 'job': job, **identity_fields, **launch.BOUNDS,
                 'candidate': launch.CANDIDATE, 'owner_authorization_sha256': common.digest(owner_raw),
                 'inputs_sha256': launch.frozen_inputs_hash(source_sha),
                 'design_sha256': common.digest(launch.canonical(launch.DESIGN)),
                 'evidence_contract_sha256': launch.run_evidence.contract_digest(contract_document),
                 'worker_config': config}
    stop_unless(authority['worker_config']['inputs_sha256'] == authority['inputs_sha256'], 'CONFIG_INPUTS_HASH')
    return job, bucket, owner_raw, request, authority


def validate(request, authority, owner_path, contract_document):
    """The launcher's OWN three validators, in `main()`'s order, against the smoke's own evidence contract."""
    launch.validate_request(request)
    launch.validate_authority(authority, contract_document)
    launch.validate_owner(owner_path, authority)


def prepare(source_sha, *, write, item1_path, item1_sha256):
    item1, item1_raw = common.read_item1(item1_path, item1_sha256, stop_unless)
    worker, source_facts, owner_record, migration = check_source(source_sha)
    receipt_dir = common.smoke_receipt_dir()
    stop_unless(not common.SMOKE_OUTPUT.exists(), 'TARGET_EXISTS_NO_OVERWRITE:' + str(common.SMOKE_OUTPUT))
    stop_unless(not receipt_dir.exists(), 'RECEIPT_EXISTS_NO_RETRY:' + str(receipt_dir))
    plan, names = validate_schedule(worker)
    # THE SAME ENTRY POINT `main(--reduced-schedule <literal>)` USES, set BEFORE the package is built.
    literal, configured_plan = launch.configure_reduced_schedule(common.SMOKE_LITERAL)
    stop_unless(literal == common.SMOKE_LITERAL and configured_plan == plan
                and launch.SMOKE_REQUEST == json.loads(common.SMOKE_LITERAL), 'SMOKE_CONFIGURE_PATH_DIVERGED')
    contract_document = launch.smoke_evidence_contract()
    stop_unless(launch.canonical(contract_document) == launch.canonical(launch.job_evidence_contract()),
                'SMOKE_CONTRACT_IS_NOT_WHAT_THE_LAUNCH_PROCESS_WILL_USE')
    stop_unless(contract_document['required_count'] == common.SMOKE_REQUIRED_COUNT == len(names) + 3
                and contract_document.get('reduced_schedule_source') == literal
                and contract_document.get('claim_bearing') is False, 'SMOKE_CONTRACT_SHAPE')
    registered = launch.evidence_contract()
    if write:
        launch.validate_ledger_path(launch.CANONICAL_LEDGER)   # a stat only: the admission is tied to this checkout
    identity, built = ensure_package(source_sha, worker, write=write)
    rendered = None
    if identity is None:
        rendered = rendered_line(worker)
        identity = {'source_sha': source_sha, 'archive_sha256': 'f' * 64, 'manifest_sha256': 'f' * 64}
    inputs_sha256 = launch.frozen_inputs_hash(source_sha)
    stop_unless(identity.get('inputs_sha256', inputs_sha256) == inputs_sha256, 'SMOKE_PACKAGE_INPUTS')
    seed_inputs = common.other_package_inputs(common.seed_package_dir(source_sha))
    stop_unless(seed_inputs in (None, inputs_sha256), 'SEED_AND_SMOKE_PACKAGES_CARRY_DIFFERENT_INPUTS')
    job, bucket, owner_raw, request, authority = documents(source_sha, identity, contract_document=contract_document,
                                                           owner_record=owner_record, item1=item1)
    with tempfile.TemporaryDirectory(prefix='prepare_on_smoke_') as scratch:
        probe = Path(scratch) / 'owner.json'
        probe.write_bytes(owner_raw)
        validate(request, authority, probe, contract_document)
    directory = common.SMOKE_OUTPUT / str(common.SMOKE_SEED)
    raws = {'owner': owner_raw, 'request': launch.canonical(request), 'authority': launch.canonical(authority)}
    pins = {name: common.pin(directory / (name + '.json'), raw) for name, raw in raws.items()}
    job_record = {'job': job, 'kind': 'smoke', 'condition': contract.CONDITION, 'model_seed': common.SMOKE_SEED,
                  'claim_bearing': False, 'bucket': bucket, **pins, 'receipt_dir': str(receipt_dir),
                  'reservation_usd': launch.RESERVATION_USD,
                  'launch_command': ['python', '-B', str(common.LAUNCHER)],
                  'launch_argv': ['--execute', '--reduced-schedule', literal,
                                  '--request', pins['request']['path'], '--request-sha256', pins['request']['sha256'],
                                  '--authority', pins['authority']['path'],
                                  '--authority-sha256', pins['authority']['sha256'],
                                  '--owner-authorization', pins['owner']['path'], '--receipt-dir', str(receipt_dir),
                                  '--ledger-path', str(launch.CANONICAL_LEDGER)],
                  'must_show_to_count_as_passed': list(SMOKE_MUST_SHOW)}
    smoke = {'schema': SMOKE_SCHEMA, 'status': 'FROZEN_BEFORE_FIRST_RUN', 'label': common.LABEL,
             'runner': common.RUNNER, 'job_kind': 'AWS_SMOKE_SWITCH_ON_WITH_ABLATIONS_NOT_CLAIM_BEARING',
             'source_sha': source_sha, 'source_checkout': str(ROOT), 'candidate': launch.CANDIDATE,
             'config_schema': launch.CONFIG_SCHEMA, **source_facts,
             'package': {**identity, 'built_by_this_run': built,
                         'folder': str(common.smoke_package_dir(source_sha)),
                         'built_in_process_after_configure_reduced_schedule': True},
             'package_is_placeholder_dry_run_only': rendered is not None,
             'rendered_line_in_process_dry_run_only': rendered,
             'inputs_sha256': inputs_sha256, 'seed_package_inputs_sha256': seed_inputs,
             'inputs_sha256_equal_across_packages': (True if seed_inputs is not None else
                                                     'SEED_PACKAGE_NOT_BUILT_YET_THE_SEED_WRITER_CHECKS_IT'),
             'design_sha256': authority['design_sha256'],
             'reduced_schedule_env': worker.REDUCED_SCHEDULE_ENV, 'reduced_schedule_literal': literal,
             'reduced_schedule_worker_plan': plan, 'reduced_schedule_artifact_names': len(names),
             'reduced_schedule_claim_bearing': False,
             'evidence_contract_sha256': authority['evidence_contract_sha256'],
             'evidence_contract_required_count': contract_document['required_count'],
             'evidence_contract_launcher_side': ('typed_pointer_launch.job_evidence_contract(), which is '
                                                 'smoke_evidence_contract() once --reduced-schedule is given'),
             'registered_evidence_contract_sha256': launch.run_evidence.contract_digest(registered),
             'registered_evidence_contract_required_count': registered['required_count'],
             'exit_code_rule': ('launch.main() returns 0 only if completed_deliverable is true, which needs '
                                'COMPLETE_VERIFIED collection against THIS 54-entry contract'),
             'owner_instruction_raw': common.OWNER_BUDGET_ANSWER_RAW,
             'owner_training_approval_raw': common.OWNER_INSTRUCTION_RAW,
             'owner_message_full_raw': common.OWNER_MESSAGE_FULL_RAW, 'answered_date': common.OWNER_ANSWERED_DATE,
             'approval_context': APPROVAL_CONTEXT, **common.owner_budget_fields(owner_record),
             'expected_cost_as_put_to_the_owner': 'a ~$1.50 short test run (owner budget question)',
             'item1_reading': item1, 'migration_record': migration,
             'starts': {'rule': ('matched starts from the same seeds as Helm 2.0, with the five analogy_head tensors '
                                 'seeded separately (seed 20260923)'),
                        'helm2_initial_pt_sha256': migration['helm2_initial_pt_sha256'],
                        'deciding_check': 'prereg amendment A5.5 (commit d7023288), on AWS, after training'},
             'limits': launch.BOUNDS, 'jobs': [job_record],
             'launch_order': ['smoke:%d' % common.SMOKE_SEED] + ['seed:%d' % seed for seed in common.SEEDS],
             'launcher': str(common.LAUNCHER), 'canonical_ledger': str(launch.CANONICAL_LEDGER),
             'run_with': 'records/typed_pointer_001/admission_analogy_on_001/run_on_study.py',
             'numeric_runs_completed': 0}
    smoke_raw = launch.canonical(smoke)
    entries = [(directory / (name + '.json'), raw) for name, raw in raws.items()]
    entries += [(common.SMOKE_OUTPUT / 'smoke.json', smoke_raw),
                (common.SMOKE_OUTPUT / common.ITEM1_COPY_NAME, item1_raw)]
    if not write:
        print(json.dumps({'mode': 'DRY_RUN_NOTHING_WRITTEN', 'package_built': identity.get('archive') is not None,
                          'package_folder': str(common.smoke_package_dir(source_sha)),
                          'validated_with_launcher_functions': True,
                          'identity_is_placeholder': rendered is not None,
                          'canonical_ledger': str(launch.CANONICAL_LEDGER),
                          'canonical_ledger_is_file_here': launch.CANONICAL_LEDGER.is_file(),
                          'note': 'the job stamp is taken at run time, so --write produces a different job name '
                                  'and different hashes from this dry run'}, sort_keys=True), flush=True)
        for path, raw in entries:
            print(json.dumps({'would_write': str(path), 'bytes': len(raw), 'sha256': common.digest(raw)},
                             sort_keys=True), flush=True)
        print(json.dumps({'smoke_record': json.loads(smoke_raw)}, sort_keys=True), flush=True)
        return 0
    stop_unless(rendered is None, 'WRITE_WITHOUT_A_BUILT_PACKAGE')

    def recheck(locate):
        """The launcher's validators again, on the bytes as they now sit on disk."""
        on_disk = {name: json.loads(locate(directory / (name + '.json')).read_bytes()) for name in raws}
        validate(on_disk['request'], on_disk['authority'], locate(directory / 'owner.json'), contract_document)
        stop_unless(common.digest(locate(common.SMOKE_OUTPUT / common.ITEM1_COPY_NAME).read_bytes())
                    == item1['sha256'], 'ITEM1_COPY_BYTES')

    written = common.write_folder_atomically(common.SMOKE_OUTPUT, entries, recheck, stop_unless)
    print(json.dumps({'status': smoke['status'], 'job': job, 'written': written,
                      'smoke_json_sha256': common.digest(smoke_raw),
                      'package_built_by_this_run': built, 'inputs_sha256': inputs_sha256}, sort_keys=True), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--item1-reading', required=True)
    parser.add_argument('--item1-reading-sha256', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    return prepare(args.source_sha, write=args.write, item1_path=args.item1_reading,
                   item1_sha256=args.item1_reading_sha256)


if __name__ == '__main__':
    raise SystemExit(main())
