"""Freeze the FOURTH pointer job -- the AWS smoke (S10) -- before it runs. Writes admission records only. No launch.

WHY THIS FILE EXISTS. `prepare_study.py` freezes the three CLAIM-BEARING jobs
(`records/typed_pointer_001/admission_001/<seed>/`) and writes no smoke job at all, while
`aws/typed_pointer_launch.py:main()` refuses to run without `--request`, `--request-sha256`, `--authority`,
`--authority-sha256`, `--receipt-dir`, `--owner-authorization` and `--ledger-path`. The smoke therefore had
no admission records and could not be launched even though the owner approved it. This script writes the
missing set for ONE smoke job, into a NEW directory that does not collide with the claim-bearing freeze:

    records/typed_pointer_001/admission_smoke_001/<seed>/{owner.json,request.json,authority.json}
    records/typed_pointer_001/admission_smoke_001/smoke.json

Its `request.json`, `authority.json` and `owner.json` are validated by the launcher's OWN three functions --
`launch.validate_request`, `launch.validate_authority`, `launch.validate_owner` -- in that order, in the same
way `main()` and `execute()` call them, so an admission set that does not pass here cannot pass there.

ONE JOB, NOT THREE. `contract.JOB_PATTERN` is
`cas-meta2-tpntr-\\d{14}-([a-f0-9]{8})-m-(20260917|20260918|20260919)`, so a smoke job may only be named for one
of the three registered model seeds, and the bucket is `job + "-" + shared.RESOURCE_PLAN["account"]`. The job
name is 50 characters and the bucket exactly 63, which is the maximum `pointer_contract.BUCKET_PATTERN`
allows (`typed_pointer_launch.py:55-61`). The seed is the one `--seed` names; the default is the first of
`contract.MODEL_SEEDS`, and only that seed's owner record, hand-off note and receipt directory ever exist for
a single smoke launch -- one job, one owner record, which is the rule the inherited lifecycle enforces (DG9).

THE OWNER LABEL IS READ, NEVER RETYPED. `smoke_owner_labels()` takes the owner's exact recorded option label
from the string `pointer_contract.DESIGN["owner_approval"]` carries, and fails if the label is not present in
it. The label is also recorded verbatim in the protocol document at
`docs/CNCM_TYPED_POINTER_STUDY_v0.1.md:57`. Nothing here restates either text.

THE APPROVAL AND ITS LATER RE-CONFIRMATION ARE RECORDED AS TWO SEPARATE FACTS. The approval's own capture
date is `OWNER_ANSWERED_UTC_DATE`; the smoke instruction was re-confirmed by the owner on the same date with
the words `OWNER_RECONFIRMATION_RAW`. The re-confirmation is recorded as its own field and is NOT presented as
a second approval, because it is a re-confirmation of a decision already recorded and already hash-bound.

THE SMOKE'S SCHEDULE IS EXPRESSED IN THE PACKAGE, NOT IN THESE ADMISSION FILES, AND THIS SCRIPT PUTS IT THERE.
A shrunken schedule is requested at RUN time through the environment variable
`cncm.typed_pointer_worker.REDUCED_SCHEDULE_ENV`; no admission file carries it and no registered constant changes.
Until 2026-09-19 nothing in the tree set that variable for a remote job, so every AWS pointer job ran the FULL
registered plan (1,470 updates) and the smoke's 8-update schedule was impossible. That is fixed by an explicit
opt-in in the launcher -- `typed_pointer_launch.SMOKE_REQUEST`, `None` by default and set only by
`set_smoke_request()` -- which inserts ONE line into the generated bootstrap, immediately after that bootstrap's
own `CAS_META2_RUN_TEACHING_CYCLE` line, carrying this request as a literal. Ambient environment is never read at
render time, so an operator's stray variable cannot shrink a claim-bearing job's schedule.

THIS SCRIPT SETS THAT OPT-IN, AND IT SETS IT ONLY AFTER THE PACKAGE IS BUILT. With the opt-in left at `None` the
generated worker source is byte-for-byte identical to the source before the opt-in existed; with it set, the
generated source carries one extra line and no longer matches. Building the claim-bearing package from a process
whose opt-in is set would be the one way to make a claim-bearing job's package differ from its pinned bytes, so
the order below is load-bearing: build the package first, then set the opt-in, then render the bootstrap to prove
the line is really there for the smoke. `set_smoke_request()` itself re-runs the worker's own `schedule_plan()` and
refuses anything the worker would refuse, so a typo cannot silently bake a different schedule.

WHAT THIS SCRIPT DOES NOT DO. It launches nothing, reserves nothing, reads no ledger and makes no AWS call. It
builds the source-only package because the authority binds the package's `archive_sha256` and
`manifest_sha256`; that build is pure and refuses to run on a dirty tree exactly as `prepare_study.py` does,
because the package is built from HEAD bytes and the launcher re-checks every admitted input against the
working tree (`typed_pointer_launch.py:229-257`). It performs NO Windows rehearsal: `prepare_study.py`'s
rehearsal runs the PRACTICE bootstrap, while this launcher replaces the provider's bootstrap with its own
(`typed_pointer_launch.py:179-182`), so a rehearsal belongs in its own verified step and is not invented here.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'research/CAS_META_2_COMPOSITION'), str(HERE)]
from aws import typed_pointer_launch as launch
from cas_meta2.typed_teaching import pointer_contract as contract
# The labels, the question, the scope and the contract-text check are the FREEZE SCRIPT'S OWN objects. They are
# imported rather than retyped so the smoke's owner record cannot drift from the claim-bearing freeze's.
from prepare_study import OWNER_DECISIONS, OWNER_QUESTION, OWNER_SCOPE, owner_decisions_in_contract_text

PROTOCOL = ROOT / 'docs/CNCM_TYPED_POINTER_STUDY_v0.1.md'
OUTPUT = HERE / 'admission_smoke_001'
PACKAGE_PARENT = ROOT / 'research/CAS_META_2_COMPOSITION/records/typed_pointer_001'
# The owner's exact label for THIS job, an index into the imported tuple, never a retyped string.
SMOKE_LABEL_INDEX = 1
OWNER_ANSWERED_UTC_DATE = '2026-09-19'
# The owner's re-confirmation, verbatim, and the date it was given. Recorded beside the approval, not as one.
OWNER_RECONFIRMATION_RAW = 'YES YOU GOT MY APPROVAL'
OWNER_RECONFIRMATION_UTC_DATE = '2026-09-19'
SMOKE_SCOPE = ('One AWS smoke job (S10) for the pointer study under the owner-approved smoke step only; the '
               'job is not claim-bearing, and this reservation does not authorise any claim-bearing launch.')
MAXIMUM_NEW_RESERVATION_USD = '45.00'
# The contract code every reduced run is voided through, quoted from the frozen gate reader.
GATE_VOID_PATH = 'I1:<seed>:REDUCED_SCHEDULE:<mode>'
GATE_VOID_SOURCE = 'records/typed_pointer_001/evaluate_gates.py:139'
# ==================================================================================================================
# THE SHRUNKEN-SCHEDULE REQUEST, EXACTLY AS THE LAUNCHER BAKES IT INTO THE INSTANCE.
#
# It is not read from an admission file and not read from this machine's environment: `prepare()` calls
# `launch.set_smoke_request(SMOKE_REDUCED_SCHEDULE)`, and the launcher emits one line into the generated bootstrap
# carrying this dict as a literal. The request is validated three times before it can cost anything -- by this
# script through the worker's own `schedule_plan()` (`validate_reduced_schedule`), by the launcher's
# `set_smoke_request()`, and by the worker itself at run time against its own `REDUCED_SCHEDULE_KEYS`.
#
# `passes: 1` with `updates: 8` is the only self-consistent 8-update plan. The registered plan is 147 updates per
# pass, so eight updates are inside the FIRST pass: the worker re-derives the plan's pass number from the batches it
# actually took (`stats["passes"] = max(batch["pass"] for batch in batches)`) and `passes: 1` is what the plan must
# then declare. Passing `passes: 10` instead is refused by `POINTER_SCHEDULE_PASSES`, because the plan is rebuilt
# from the request, re-validated, and finally checked for equality against the schedule's own pass count.
#
# `evaluations: [0, 1]` is the two-evaluation floor, not a choice: a reload-enabled plan is REFUSED unless it
# carries an evaluation at pass `0` AND at pass `passes` (`POINTER_PLAN_RELOAD_EVALUATIONS`,
# `cncm/typed_pointer_worker.py:234-236`). With `passes: 1` those are two different checkpoints and both are
# full-course ones (`PASS_CHECKPOINTS` (0,1,2,4,6,8,10), `FULL_COURSE_CHECKPOINTS` (0,1,10)). Each numbered
# evaluation also publishes a `development_pNN` phase, so this run writes four evaluation phase pairs: course_p00,
# course_p01, development_p00, development_p01. Pass 0 is the COLD course pass in any job.
#
# `replays: true` requires `passes in evaluations` and `prelast` (`updates >= 2`), both satisfied; `reloads: true`
# exercises the restore path the checkpoint fixes exist for. `phase_b`, `ablations`, `retention` and `interference`
# are off: they are the expensive halves (phase B is report-only and the smoke plan's own section 3 skips the
# ablations), and `retention` is refused unless `interference` is on. NOTE the key-name trap recorded at
# `pre_design/AWS_SMOKE_S10_PLAN.md:249-270`: the accepted key is the PLURAL `reloads` and its value must be a BOOL
# -- a list of checkpoint names is refused with `POINTER_PLAN_FLAGS`.
#
# With `updates` set, the claim test fails on `plan["updates"] is None` alone, so `claim_bearing` is False and
# `schedule_plan.json` records `"mode": "REGISTERED" if claim_bearing else "REDUCED"` -- i.e. `"REDUCED"`, which the
# frozen gate reader voids through `I1:<seed>:REDUCED_SCHEDULE:<mode>`.
# ==================================================================================================================
SMOKE_REDUCED_SCHEDULE = {"passes": 1, "updates": 8, "evaluations": [0, 1],
                          "phase_a": ["initial", "pass_01", "final"], "reloads": True, "replays": True,
                          "phase_b": False, "ablations": False, "retention": False, "interference": False}
# What the smoke is estimated to cost, from the plan's own section 2 and 3 receipts and its corrected estimate.
SMOKE_ESTIMATE = {'worker_clock_seconds': 771, 'non_worker_overhead_seconds': 598.2,
                  'instance_seconds': 1369, 'usd_at_2_52_per_hour': '0.96'}


def write(path, value):
    raw = launch.canonical(value)
    with path.open('xb') as stream:
        stream.write(raw)
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def smoke_label():
    """The owner's exact label for the smoke job, READ out of the contract's own owner-approval record."""
    text = contract.DESIGN['owner_approval']
    label = OWNER_DECISIONS[SMOKE_LABEL_INDEX]
    assert text.count(label) == 1, 'SMOKE_LABEL_NOT_RECORDED_VERBATIM_IN_THE_CONTRACT:' + label
    return label


def validate_reduced_schedule():
    """Run `SMOKE_REDUCED_SCHEDULE` through the WORKER'S OWN `schedule_plan()` and return the accepted plan.

    This is the $0 assertion that stops a mis-formed request from being discovered on the instance, after the boot
    and the package install have been paid for. It is the worker's own rule set, not a copy of it: a request whose
    plan is refused (`POINTER_PLAN_RELOAD_EVALUATIONS`, `POINTER_PLAN_REPLAY_UPDATES`, `POINTER_PLAN_FLAGS`,
    `POINTER_PLAN_RETENTION_REQUIRES_INTERFERENCE`, ...) fails here, and so does a request that came back
    `claim_bearing`, which would mean the smoke had asked for the REGISTERED plan through the smoke path.
    """
    worker = launch._probe()
    literal = launch.canonical(SMOKE_REDUCED_SCHEDULE).decode('utf-8').rstrip('\n')
    plan, claim_bearing = worker.schedule_plan(source=literal)
    assert not claim_bearing, 'SMOKE_SCHEDULE_IS_CLAIM_BEARING'
    assert plan['updates'] == SMOKE_REDUCED_SCHEDULE['updates'], 'SMOKE_SCHEDULE_UPDATES'
    assert SMOKE_REDUCED_SCHEDULE['passes'] in SMOKE_REDUCED_SCHEDULE['evaluations'], 'SMOKE_SCHEDULE_LAST_EVALUATION'
    assert 0 in SMOKE_REDUCED_SCHEDULE['evaluations'], 'SMOKE_SCHEDULE_FIRST_EVALUATION'
    return literal, plan


def verify_bootstrap_embedding():
    """`(bootstrap_sha256, assignment_line)` for the generated bootstrap WITH the opt-in set.

    The assertion is the whole point: outside the opt-in the generated source carries no such line at all, and
    with it set it carries exactly one, immediately after the bootstrap's own teaching-cycle line.
    """
    worker = launch._probe()
    bootstrap = launch.bootstrap_source()
    assert bootstrap.count(worker.REDUCED_SCHEDULE_ENV) == 1, 'SMOKE_BOOTSTRAP_LINE_COUNT'
    anchor = bootstrap.index(launch.BOOTSTRAP_ENV_ANCHOR)
    assignment = bootstrap.index(worker.REDUCED_SCHEDULE_ENV)
    assert bootstrap.index('\n', anchor) < assignment, 'SMOKE_BOOTSTRAP_LINE_NOT_AFTER_THE_ANCHOR'
    line = bootstrap[assignment:bootstrap.index('\n', assignment)]
    assert line.endswith(repr(validate_reduced_schedule()[0])), 'SMOKE_BOOTSTRAP_LITERAL'
    return sha256(bootstrap.encode('utf-8')).hexdigest(), line


def smoke_documents(job, identity, *, seed):
    """The three admission documents for ONE smoke job, built from the launcher's own constants."""
    config = launch.worker_config(job, source_sha=identity['source_sha'])
    bucket = job + '-' + launch.shared.RESOURCE_PLAN['account']
    assert config['bucket'] == bucket and len(bucket) == 63, 'SMOKE_BUCKET_LENGTH'
    decisions_in_contract = owner_decisions_in_contract_text()
    owner = {'schema': launch.OWNER_SCHEMA, 'candidate': launch.CANDIDATE,
             'owner_instruction_raw': smoke_label(), 'owner_question': OWNER_QUESTION,
             'owner_selected_option_terms': list(OWNER_DECISIONS),
             'owner_decisions_in_contract_text': list(decisions_in_contract),
             'answered_utc_date': OWNER_ANSWERED_UTC_DATE,
             'owner_reconfirmation_raw': OWNER_RECONFIRMATION_RAW,
             'owner_reconfirmation_utc_date': OWNER_RECONFIRMATION_UTC_DATE, 'scope': SMOKE_SCOPE,
             'job': job, 'condition': contract.CONDITION, 'model_seed': seed, 'bounds': launch.BOUNDS}
    owner_sha256 = sha256(launch.canonical(owner)).hexdigest()
    request = {'schema': launch.REQUEST_SCHEMA, 'job': job,
               **{key: identity[key] for key in ('source_sha', 'archive_sha256', 'manifest_sha256')},
               'launch_authorized': False}
    authority = {'schema': launch.AUTHORITY_SCHEMA, 'job': job,
                 **{key: identity[key] for key in ('source_sha', 'archive_sha256', 'manifest_sha256')},
                 **launch.BOUNDS, 'candidate': launch.CANDIDATE, 'owner_authorization_sha256': owner_sha256,
                 'inputs_sha256': launch.frozen_inputs_hash(),
                 'design_sha256': launch.digest(launch.canonical(launch.DESIGN)),
                 'evidence_contract_sha256': launch.run_evidence.contract_digest(launch.evidence_contract()),
                 'worker_config': config}
    return owner, request, authority


def validate_documents(directory_writer, owner, request, authority):
    """The launcher's OWN three validators, called in `main()`'s and `execute()`'s order.

    `validate_owner` reads the owner record from a path and hashes its BYTES, so the record is written first
    by the caller's own writer and then read back. An admission set that does not pass here cannot pass the
    launcher.
    """
    launch.validate_request(request)
    launch.validate_authority(authority)
    launch.validate_owner(directory_writer, authority)


def dry_run(seed=None):
    """Build and validate the three documents for the seeded job WITHOUT writing into the tree. Costs $0.

    Two fields a dry run cannot know are the package's `archive_sha256` and `manifest_sha256`, because the
    package is built from the committed bytes that `prepare()` packs. They are supplied here from HEAD so the
    documents exercise every other field, every other hash binding and all three of the launcher's validators;
    `prepare()` then re-checks them against the real built package. Nothing is created outside a scratch file
    that this function deletes.
    """
    seed = contract.MODEL_SEEDS[0] if seed is None else seed
    assert seed in contract.MODEL_SEEDS, 'SMOKE_SEED_NOT_REGISTERED'
    source_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    job = 'cas-meta2-tpntr-' + stamp + '-' + source_sha[:8] + '-m-' + str(seed)
    # The package's two digests, read from what `build_pointer_package` would pack: the committed package
    # sources and manifest inputs at HEAD. The manifest digest is not reproducible here without building the
    # package -- `shared.manifest_for` needs the member map -- so it is recorded as NOT_SUPPLIED rather than
    # faked, and the launcher is given a well-formed placeholder ONLY to reach its own field and binding
    # checks. Every other binding (`inputs_sha256`, `design_sha256`, `evidence_contract_sha256`,
    # `worker_config`) is the real one and is checked for real.
    placeholder = 'f' * 64
    identity = {'source_sha': source_sha, 'archive_sha256': placeholder, 'manifest_sha256': placeholder}
    owner, request, authority = smoke_documents(job, identity, seed=seed)
    # Both of the smoke's own $0 checks, in the same order `prepare()` runs them: the schedule through the
    # worker's own `schedule_plan()`, then the environment line through the generated bootstrap.
    literal, plan = validate_reduced_schedule()
    launch.set_smoke_request(SMOKE_REDUCED_SCHEDULE)
    bootstrap_sha256, assignment = verify_bootstrap_embedding()
    scratch = HERE / '_smoke_dry_run_owner.json'
    scratch.write_bytes(launch.canonical(owner))
    try:
        launch.validate_request(request)
        launch.validate_authority(authority)
        launch.validate_owner(scratch, authority)
    finally:
        scratch.unlink()
    print(json.dumps({'validated_by': ['launch.validate_request', 'launch.validate_authority',
                                       'launch.validate_owner'],
                      'job': job, 'seed': seed, 'source_sha': source_sha,
                      'bucket': job + '-' + launch.shared.RESOURCE_PLAN['account'],
                      'bucket_characters': len(job) + len('-' + launch.shared.RESOURCE_PLAN['account']),
                      'archive_sha256_and_manifest_sha256': 'PLACEHOLDER_ONLY_IN_DRY_RUN',
                      'request_keys': sorted(request), 'authority_keys': sorted(authority),
                      'owner_keys': sorted(owner),
                      'authority_bounds_keys': sorted(launch.BOUNDS),
                      'owner_instruction_raw': owner['owner_instruction_raw'],
                      'owner_decisions_in_contract_text': owner['owner_decisions_in_contract_text'],
                      'reduced_schedule': SMOKE_REDUCED_SCHEDULE, 'reduced_schedule_literal': literal,
                      'reduced_schedule_worker_plan': plan,
                      'generated_bootstrap_sha256': bootstrap_sha256,
                      'generated_bootstrap_reduced_schedule_line': assignment}, sort_keys=True), flush=True)


def prepare(seed=None):
    seed = contract.MODEL_SEEDS[0] if seed is None else seed
    assert seed in contract.MODEL_SEEDS, 'SMOKE_SEED_NOT_REGISTERED'
    assert all(owner_decisions_in_contract_text()), 'OWNER_DECISIONS_MISSING_FROM_CONTRACT_TEXT'
    assert float(launch.RESERVATION_USD) <= float(MAXIMUM_NEW_RESERVATION_USD)
    source_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--', '.'], cwd=ROOT, text=True).strip()
    assert not dirty, 'COMMIT_FIRST_THE_PACKAGE_IS_BUILT_FROM_HEAD:\n' + dirty[:2000]
    OUTPUT.mkdir()
    PACKAGE_PARENT.mkdir(exist_ok=True)
    # THE ORDER HERE IS LOAD-BEARING. The package is built with the launcher's smoke opt-in still at its default
    # `None`, so this package's generated worker source is byte-for-byte the source every other job's package
    # carries; the opt-in is set only afterwards, and only to prove the smoke's schedule reaches the instance.
    assert launch.SMOKE_REQUEST is None, 'SMOKE_OPT_IN_ALREADY_SET_BEFORE_THE_PACKAGE_WAS_BUILT'
    package = launch.build_pointer_package(PACKAGE_PARENT / ('package_smoke_' + source_sha[:8]),
                                           source_sha=source_sha)
    literal, plan = validate_reduced_schedule()
    launch.set_smoke_request(SMOKE_REDUCED_SCHEDULE)          # both of the launcher's own checks run inside
    assert launch.SMOKE_REQUEST is SMOKE_REDUCED_SCHEDULE, 'SMOKE_OPT_IN_NOT_SET'
    bootstrap_sha256, assignment = verify_bootstrap_embedding()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    job = 'cas-meta2-tpntr-' + stamp + '-' + source_sha[:8] + '-m-' + str(seed)
    directory = OUTPUT / str(seed)
    directory.mkdir()
    identity = {'source_sha': package['source_sha'], 'archive_sha256': package['archive_sha256'],
                'manifest_sha256': package['manifest_sha256']}
    owner, request, authority = smoke_documents(job, identity, seed=seed)
    owner_pin = write(directory / 'owner.json', owner)
    validate_documents(directory / 'owner.json', owner, request, authority)
    jobs = [{'job': job, 'condition': contract.CONDITION, 'model_seed': seed,
             'bucket': job + '-' + launch.shared.RESOURCE_PLAN['account'],
             'request': write(directory / 'request.json', request),
             'authority': write(directory / 'authority.json', authority), 'owner': owner_pin,
             'receipt_dir': str(HERE / ('receipt_smoke_' + str(seed))), 'claim_bearing': False}]
    smoke = {'schema': 'cncm.typed-pointer-smoke-admission/0.1', 'status': 'FROZEN_BEFORE_FIRST_RUN',
             'job_kind': 'AWS_SMOKE_S10_NOT_CLAIM_BEARING', 'source_sha': source_sha,
             'candidate': launch.CANDIDATE, 'config_schema': launch.CONFIG_SCHEMA,
             'package_archive_sha256': package['archive_sha256'],
             'package_manifest_sha256': package['manifest_sha256'], 'package_archive': package['archive'],
             'protocol_sha256': sha256(PROTOCOL.read_bytes()).hexdigest(),
             'plan_sha256': sha256((HERE / 'pre_design/AWS_SMOKE_S10_PLAN.md').read_bytes()).hexdigest(),
             'owner_label_verbatim': smoke_label(), 'owner_label_source': 'pointer_contract.DESIGN["owner_approval"]',
             'owner_label_protocol_line': 'docs/CNCM_TYPED_POINTER_STUDY_v0.1.md:57',
             'owner_reconfirmation_raw': OWNER_RECONFIRMATION_RAW,
             'owner_reconfirmation_utc_date': OWNER_RECONFIRMATION_UTC_DATE,
             'owner_decisions_in_contract_text': owner['owner_decisions_in_contract_text'],
             'reduced_schedule_env': launch._probe().REDUCED_SCHEDULE_ENV,
             'reduced_schedule_request': SMOKE_REDUCED_SCHEDULE,
             'reduced_schedule_request_literal': literal,
             'reduced_schedule_worker_plan': plan,
             'reduced_schedule_claim_bearing': False,
             'reduced_schedule_opt_in': 'typed_pointer_launch.set_smoke_request(SMOKE_REDUCED_SCHEDULE)',
             'reduced_schedule_package_opt_in_was_none_when_built': True,
             'generated_bootstrap_sha256': bootstrap_sha256,
             'generated_bootstrap_reduced_schedule_line': assignment,
             'reduced_schedule_gate_void_path': GATE_VOID_PATH, 'gate_void_source': GATE_VOID_SOURCE,
             'estimate': SMOKE_ESTIMATE, 'reservation_per_job_usd': launch.RESERVATION_USD,
             'maximum_new_reservation_usd': MAXIMUM_NEW_RESERVATION_USD,
             'jobs_execute_sequentially': True, 'automatic_retries': 0, 'jobs': jobs}
    pin = write(OUTPUT / 'smoke.json', smoke)
    print(json.dumps({'status': smoke['status'], 'job': job, 'owner': owner, 'smoke': pin}, sort_keys=True),
          flush=True)


def arguments(argv):
    """`--seed <registered seed>` and `--dry-run` only. There is no `--execute`: this script launches nothing."""
    seed, dry = None, False
    while argv:
        if argv[0] == '--dry-run':
            argv, dry = argv[1:], True
        elif argv[0] == '--seed':
            assert len(argv) > 1 and argv[1].isdigit(), 'SMOKE_ARGUMENTS'
            seed, argv = int(argv[1]), argv[2:]
        else:
            raise AssertionError('SMOKE_ARGUMENTS:' + repr(argv[0]))
    return seed, dry


if __name__ == '__main__':
    _seed, _dry = arguments(sys.argv[1:])
    dry_run(_seed) if _dry else prepare(_seed)
