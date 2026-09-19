"""The deterministic gate reading of the pointer study (docs/CNCM_TYPED_POINTER_STUDY_v0.1.md, section 7).

Pure standard library plus the project's pure modules and the private checker (post-run, local). Reads the
collected receipts; runs no model, imports no torch. **The label this program prints IS the claim status.** No
prose anywhere may upgrade it, and nothing else in the project may decide it.

    python evaluate_gates.py STUDY_JSON
    python evaluate_gates.py --self-test

Copied from `records/typed_practice_001/evaluate_gates.py` at HEAD `489cda65`: the same structure, the same
integrity chain shape I0-I4, the same exact arithmetic and the same three-word label vocabulary. Four things are
NEW, and each is named where it is raised:

* **I1** imports `cncm.typed_pointer_worker` and checks THAT worker's `SUCCESS_STATUS` and `EXPECTED_ARTIFACTS`
  (the practice reader imports `cncm.typed_practice_worker`). The pointer worker does not exist at HEAD
  `489cda65`, so the check fails CLOSED with the named code `I1:WORKER_MODULE_MISSING` rather than crashing.
* **I3** reads the in-job DG4 identity checks the worker recorded, in the corrected form of protocol section 7.1:
  the three `^6` tensors' identity equals the practice study's recorded start for that seed, a second independent
  build gives the same identity, the three seeds' identities are pairwise different, and the start is identical
  with the checkpoint check on and off. The practice I3 compared `model_state_identity` against the matched
  study's checkpoint, which the pointer container can never equal, because that value digests the whole
  `module.state_dict()` (`learner.py:111`, `:306`) while the pointer container holds far more than the `^6` block
  (finding RK8).
* **The label is keyed on the RELATIONAL tier** over the frozen population the CONTRACT derives - 18 questions
  after 11 frozen removals - never on the all-kinds result. One copied input flag buys `b = 10`, `c = 0`,
  `p = 0.0009765625` on `definition 5 + context 5` and would otherwise print LEARNS_NEW_WORLDS (finding FP1).
  The all-kinds test is reported as `flags.all_kinds_g_learn_passes` and nothing else; `--self-test` proves a
  flag-copy-only outcome receives no label.
* **The ORACLE one-hop ceilings are printed beside the label**, never applied as removals: applying the checker's
  own adjacency rule to the input IS the skill under test (REVIEW_SYNTHESIS section 10.1.1).

Unit of evidence: a QUESTION (`query_id`), correct at a checkpoint only if every one of its records is correct.
Each seed is tested on its own and all three must pass: the seeds share the encoder, data and schedule, so they
are replications, not extra sample size. The gate population is read from the contract
(`pointer_contract.relational_population`), never restated here; if it does not reproduce `VERIFIED_POPULATION`
and `VERIFIED_POPULATION_DIGEST` the reading is VOID.

WHAT THIS PROGRAM DOES NOT DO. It does not decide the claim, it does not round a number (every p is an exact
`fractions.Fraction`, recorded as a rational string and as its exact binary float), and it does not touch the
network, a GPU or a paid service. `$0`.

WHAT IS UNDETERMINED AT HEAD `489cda65`, marked `UNCERTAIN:` at the code that depends on it:
`UNCERTAIN: the record location and field names of the in-job DG4 identity checks.` The pointer worker is being
written, so the reader declares its own I3 record contract in `DG4_REPORT_KEYS`, `DG4_ARTIFACT_NAMES`,
`DG4_IDENTITY_FORM` and `DG4_FIELDS`. A missing record or a renamed field fails CLOSED with a named code, and the
reader reports the location it read under `seeds[seed]['dg4_source']`, so the worker builder can align to the
reader instead of the reader guessing.
`UNCERTAIN: the pointer worker's evaluation phase names.` They are discovered from the job's own artifact manifest
under the registered `<prefix>_pNN_scoring.json` convention (INTERFACE_SPEC_PIPELINE D.4) rather than hardcoded,
and the discovery is reported through the per-seed `checkpoints` list.
`UNCERTAIN: the pointer worker's main-phase batch-log names.` They are likewise discovered from the manifest (every
`*_batches.jsonl` except `interference_batches.jsonl`), so a renamed prefix is read rather than refused.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
from math import comb
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'research/CAS_META_2_COMPOSITION'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

ALPHA = Fraction(1, 100)
MIN_IMPROVED_KINDS = 2
MIN_IMPROVED_WORLDS = 2
SCHEMA = 'cncm.typed-pointer-gate-reading/0.1'
PROTOCOL = 'docs/CNCM_TYPED_POINTER_STUDY_v0.1.md'
WORKER_MODULE = 'cncm.typed_pointer_worker'
PRACTICE_RECEIPTS = ROOT / 'records/typed_practice_001'
MATCHED_RECEIPTS = ROOT / 'records/typed_matched_001'
START_CHECKPOINT_NAME = 'initial_checkpoint.json'
PRIMARY_TEST = 'G_LEARN_population'
ALL_KINDS_TEST = 'G_LEARN_all_kinds'
LABELS = ('LEARNS_NEW_WORLDS', 'NO_TRANSFER_TO_NEW_WORLDS', 'VOID')

# ------------------------------------------------------------------------------------------------------------------
# I3's record contract, declared by this reader because `cncm.typed_pointer_worker` does not exist at HEAD 489cda65.
# `UNCERTAIN:` the worker builder may name these differently. The reader ACCEPTS the first location present, reports
# it as `dg4_source`, and fails closed on any missing field, so a mismatch shows up as VOID with an exact code and
# never as a silent pass.
# ------------------------------------------------------------------------------------------------------------------
DG4_REPORT_KEYS = ('dg4_identity_checks', 'dg4')
DG4_ARTIFACT_NAMES = ('dg4_identity_checks.json', 'dg4_checks.json')
DG4_IDENTITY_FORM = 'THREE_TENSOR'
DG4_FIELDS = ('practice_start_identity', 'first_build_identity', 'second_build_identity',
              'start_without_check_identity')
DG4_OPTIONAL_FIELDS = ('whole_module_identity', 'start_with_check_identity')

# ------------------------------------------------------------------------------------------------------------------
# The ORACLE one-hop ceilings. FROZEN, reported BESIDE the label and never applied as removals: REVIEW_SYNTHESIS
# section 10.1.1 - "applying the checker's own rule to the input IS the skill under test; these are the ceiling
# baselines the label must be compared against". The numerators are that section's own readings; the denominators
# are the ELIGIBLE held questions of the kind (LK9, `lk1_answer_carriers_out.txt` lines 58-66), recomputed by this
# reader and required to equal the contract's VERIFIED_RELATIONAL_BY_KIND.
# ------------------------------------------------------------------------------------------------------------------
ORACLE_CEILINGS = (
    ('parts', 'children of the whole argument, one adjacency hop', 5),
    ('edge_account', 'the full adjacency of the focus world, one-hop copy', 5),
    ('reach', 'DIRECT iff the part is a child, else ABSENT, one adjacency hop', 1),
)
# LK11, report-only: "15 of the 45 eligible questions are decided by a single record" (REVIEW_SYNTHESIS 10.3).
# `UNCERTAIN:` whether "decided by a single record" means one record per question or one record on a side; this
# reader measures one record, prints both numbers, and does not gate on them.
LK11_SINGLE_RECORD_ELIGIBLE = 15
LK11_ELIGIBLE_TOTAL = 45

# Every path into VOID, enumerated as a code and printed by every reading under `void_paths`.
VOID_PATHS = (
    ('I0:STUDY_MUST_HAVE_EXACTLY_THE_THREE_SEEDS_WITH_RECEIPTS',
     'the study job list is not the registered model seeds with a receipt directory each'),
    ('I1:WORKER_MODULE_MISSING', 'cncm.typed_pointer_worker could not be imported'),
    ('I1:WORKER_CONSTANTS', 'the worker has no usable SUCCESS_STATUS or EXPECTED_ARTIFACTS'),
    ('I1:WORKER_ARTIFACT_CONTRACT',
     'EXPECTED_ARTIFACTS is not unique, is 500 names or more, or omits worker_report/measurements'),
    ('I1:<seed>', 'lifecycle, worker status or artifact manifest does not satisfy the worker contract'),
    ('I1:<seed>:<Error>', 'reading that job receipt raised OSError/ValueError/KeyError/TypeError'),
    ('I1:<seed>:SCORING:<Error>', 'a scoring file could not be read'),
    ('I1:<seed>:SCORING_PHASES_MISSING', 'the manifest holds no <prefix>_pNN_scoring.json'),
    ('I1:<seed>:SCORING_CONFLICT:<n>', 'two scoring files at one checkpoint disagree about a record'),
    ('I1:<seed>:SCORING_INCOMPLETE:<n>', 'a checkpoint does not hold every record the test needs'),
    ('I2:<seed>', 'held/excluded ids, a trained-only batch log, or the update counts do not match the frozen split'),
    ('I2:<seed>:MAIN_LOGS:<n>', 'the number of main batch logs is not the frozen pass count'),
    ('I2:<seed>:PASS_LINES:<name>', 'a pass log does not hold exactly the frozen updates per pass'),
    ('I3:<seed>', 'a DG4 identity check failed, or reading the DG4 evidence raised'),
    ('I3:<seed>:DG4_RECORD_MISSING', 'the job recorded no DG4 identity checks at any accepted location'),
    ('I3:<seed>:DG4_IDENTITY_FORM:<form>', 'the record does not use the three-tensor identity form'),
    ('I3:<seed>:DG4_FIELD:<field>', 'a required DG4 field is missing or is not 64 hex characters'),
    ('I3:<seed>:DG4_START_TARGET', 'the record names a practice start that is not the pinned one for that seed'),
    ('I3:<seed>:DG4_SIX_IDENTITY', 'the first build of the three ^6 tensors does not equal the practice start'),
    ('I3:<seed>:DG4_DOUBLE_BUILD', 'the second independent build does not give the same identity'),
    ('I3:<seed>:DG4_CHECK_INDEPENDENT_START', 'the start differs with the checkpoint check on and off'),
    ('I3:SEEDS_NOT_PAIRWISE_DIFFERENT', 'two of the three seeds recorded the same ^6 identity'),
    ('I3:START_TARGET:<seed>:<code>', 'the pinned practice start checkpoint could not be read or verified'),
    ('I4:<seed>', 'the frozen main, interference and replay update counts, reloads or replays do not match'),
    ('POPULATION:<reason>', 'the contract population does not reproduce VERIFIED_POPULATION and its digest'),
    ('POPULATION_ELIGIBLE:<reason>', 'the contract eligible composition does not reproduce the verified readings'),
    ('LABEL_CONTRACT:<reason>', 'the contract no longer registers the RELATIONAL tier or the flag-copy rule'),
    ('ARITHMETIC:<reason>', 'the re-derived minimum passing b is not the contract MIN_PASSING_B'),
)


def binomial_upper_tail(b, n):
    """Exact one-sided P(X >= b | n, 1/2)."""
    if n == 0:
        return Fraction(1)
    return Fraction(sum(comb(n, k) for k in range(b, n + 1)), 2 ** n)


def paired(before, after, keys):
    b = sum(1 for k in keys if not before[k] and after[k])
    c = sum(1 for k in keys if before[k] and not after[k])
    return {'wrong_to_right': b, 'right_to_wrong': c, 'pairs': len(keys)}


def question_outcomes(record_correct, questions):
    """{query_id: all records correct} for the given {query_id: [record ids]}."""
    return {q: all(record_correct[r] for r in records) for q, records in questions.items()}


def seed_test(before, after, keys, kind_of, world_of=None):
    """One seed's pre-registered test on questions: b > c, exact p <= ALPHA, improvements in >= 2 kinds
    and, when worlds are given, in >= 2 worlds."""
    test = paired(before, after, keys)
    b, c = test['wrong_to_right'], test['right_to_wrong']
    p = binomial_upper_tail(b, b + c)
    improved = [k for k in keys if not before[k] and after[k]]
    kinds = sorted({kind_of[k] for k in improved})
    worlds = sorted({world_of[k] for k in improved}) if world_of is not None else None
    passed = b > c and p <= ALPHA and len(kinds) >= MIN_IMPROVED_KINDS
    if world_of is not None:
        passed = passed and len(worlds) >= MIN_IMPROVED_WORLDS
    test.update(p_one_sided=str(p), p_float=float(p), improved_kinds=kinds, improved_worlds=worlds, passed=passed)
    return test


def label_decision(complete, primary_passed):
    """The ONLY label decision in this program, in order of precedence, as (label, rule code).

    1. anything that breaks the integrity chain, or fewer than the three registered seeds -> VOID
    2. the RELATIONAL population test passes in all three seeds                        -> LEARNS_NEW_WORLDS
    3. otherwise                                                                        -> NO_TRANSFER_TO_NEW_WORLDS

    `complete` is `not failures and len(seeds) == len(contract.MODEL_SEEDS)`. `primary_passed` is the primary test
    over `population['question_ids']` - NEVER the all-kinds test (FP1). No other code path sets a label.
    """
    if not complete:
        return 'VOID', 'INTEGRITY_OR_SEED_COUNT_FAILED'
    if primary_passed:
        return 'LEARNS_NEW_WORLDS', 'RELATIONAL_POPULATION_TEST_PASSED_ALL_SEEDS'
    return 'NO_TRANSFER_TO_NEW_WORLDS', 'RELATIONAL_POPULATION_TEST_FAILED'


def _artifacts(receipt):
    return Path(receipt) / 'collected/results/artifacts'


def _read_json(path):
    return json.loads(Path(path).read_bytes())


def _code(error):
    """The contract's own failure code out of a `ValueError("TYPED_MATCHED:" + reason)`."""
    text = str(error)
    prefix = 'TYPED_MATCHED:'
    return text[len(prefix):] if text.startswith(prefix) else text


def _is_digest(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


MIN_PASSING_B_REDERIVED = min(b for b in range(0, 200) if binomial_upper_tail(b, b) <= ALPHA)
SCORING_NAME = re.compile(r'^(?P<prefix>[A-Za-z0-9_]+)_p(?P<number>\d{2})_scoring\.json$')


def min_passing_b_failures(contract):
    """The reader re-derives its own threshold and refuses a contract that registers a different one."""
    if MIN_PASSING_B_REDERIVED != contract.MIN_PASSING_B:
        return ['ARITHMETIC:MIN_PASSING_B:%d!=%d' % (MIN_PASSING_B_REDERIVED, contract.MIN_PASSING_B)]
    return []


def worker_module():
    """The pointer worker module, or (None, code). Imported without torch; fails closed, never raises."""
    try:
        from cncm import typed_pointer_worker as worker
    except ImportError:
        return None, 'I1:WORKER_MODULE_MISSING'
    except Exception as error:  # a worker that raises on import is a missing worker for this reader's purposes
        return None, 'I1:WORKER_MODULE_MISSING:%s' % type(error).__name__
    return worker, None


def worker_contract_failures(worker):
    """P7's shape rules on the worker's own artifact contract, checked once before any seed is read."""
    if worker is None:
        return ['I1:WORKER_MODULE_MISSING']
    status = getattr(worker, 'SUCCESS_STATUS', None)
    expected = getattr(worker, 'EXPECTED_ARTIFACTS', None)
    if type(status) is not str or not status or type(expected) not in (tuple, list) or not expected:
        return ['I1:WORKER_CONSTANTS']
    names = tuple(expected)
    if (not all(type(name) is str and name for name in names) or len(set(names)) != len(names)
            or len(names) >= 500
            or not any(name.endswith('worker_report.json') for name in names)
            or not any(name.endswith('measurements.json') for name in names)):
        return ['I1:WORKER_ARTIFACT_CONTRACT']
    return []


def required_reloads(worker):
    """The reload count the worker's own artifact contract registers (practice: initial, final, retained = 3)."""
    if worker is None:
        return None
    return sum(1 for name in worker.EXPECTED_ARTIFACTS if name.endswith('_reload_predictions.json'))


def required_replays(worker):
    """The replay count the worker's own artifact contract registers (practice: 2)."""
    if worker is None:
        return None
    return len({name.split('_predictions.json')[0] for name in worker.EXPECTED_ARTIFACTS
                if re.fullmatch(r'replay_\d+_predictions\.json', name)})


def practice_start(contract, seed):
    """(identity, failures) for the practice study's recorded start of one seed, verified against the frozen pin.

    The value I3 must match is fixed by protocol section 7.1: the `^6` three-tensor identity of a fresh
    `matched._framework` build equals that seed's recorded `model_state_identity`. The reader reads the receipt,
    hashes it against `contract.CHECKPOINT_PINS`, and only then takes `metadata.model_state_identity`; the copy
    under `collected/results/artifacts/` is accepted because M1 measured the two byte-identical.
    """
    name = 'records/typed_practice_001/receipt_%d/checkpoints/%s' % (seed, START_CHECKPOINT_NAME)
    pin = contract.CHECKPOINT_PINS.get(name)
    if pin is None:
        return None, ['I3:START_TARGET:%d:PIN_MISSING' % seed]
    for path in (ROOT / name,
                 PRACTICE_RECEIPTS / ('receipt_%d' % seed) / 'collected/results/artifacts' / START_CHECKPOINT_NAME):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            return None, ['I3:START_TARGET:%d:PIN_MISMATCH' % seed]
        try:
            return json.loads(raw)['metadata']['model_state_identity'], []
        except (ValueError, KeyError, TypeError) as error:
            return None, ['I3:START_TARGET:%d:%s' % (seed, type(error).__name__)]
    return None, ['I3:START_TARGET:%d:RECEIPT_MISSING' % seed]


def matched_start(seed):
    """The matched study's recorded start. Report-only: the practice and matched values agreed when the practice
    study's own I3 passed (`PRACTICE_STUDY_RESULT.md`), so a disagreement here is printed, not gated."""
    path = (MATCHED_RECEIPTS / ('receipt_%d_m' % seed) / 'collected/results/artifacts' / START_CHECKPOINT_NAME)
    try:
        return _read_json(path)['metadata']['model_state_identity']
    except (OSError, ValueError, KeyError, TypeError):
        return None


def dg4_record(artifacts, report):
    """(record, source) for the job's in-job DG4 identity checks; (None, None) when the job recorded none.

    `UNCERTAIN:` the location. The reader accepts the first of `DG4_REPORT_KEYS` inside `worker_report.json`, then
    the first of `DG4_ARTIFACT_NAMES` as a standalone artifact, and reports which one it used.
    """
    for key in DG4_REPORT_KEYS:
        value = report.get(key)
        if isinstance(value, dict):
            return value, 'worker_report.json:' + key
    for name in DG4_ARTIFACT_NAMES:
        path = artifacts / name
        if path.is_file():
            value = _read_json(path)
            if isinstance(value, dict):
                return value, name
    return None, None


def dg4_failures(seed, record, target):
    """The four DG4 checks of protocol section 7.1, as the job recorded them, with (a)'s target re-derived here.

    (a) the three `^6` tensors of the first build equal the practice start for this seed
    (b) a second independent build gives the same identity
    (d) the start is identical with the checkpoint check on and off
    (c) the three seeds' identities pairwise different - re-derived across seeds by the caller, because one job
        cannot see the other two.
    The reader re-derives (a)'s target from the PINNED practice receipt, so a job that records a self-consistent
    but wrong start identity is caught here rather than believed.
    """
    codes = []
    if record.get('identity_form') != DG4_IDENTITY_FORM:
        codes.append('I3:%d:DG4_IDENTITY_FORM:%s' % (seed, record.get('identity_form')))
    values = {}
    for field in DG4_FIELDS:
        value = record.get(field)
        if not _is_digest(value):
            codes.append('I3:%d:DG4_FIELD:%s' % (seed, field))
        else:
            values[field] = value
    if len(values) != len(DG4_FIELDS):
        return codes
    if values['practice_start_identity'] != target:
        codes.append('I3:%d:DG4_START_TARGET' % seed)
    if values['first_build_identity'] != target:
        codes.append('I3:%d:DG4_SIX_IDENTITY' % seed)
    if values['second_build_identity'] != values['first_build_identity']:
        codes.append('I3:%d:DG4_DOUBLE_BUILD' % seed)
    if values['start_without_check_identity'] != values['first_build_identity']:
        codes.append('I3:%d:DG4_CHECK_INDEPENDENT_START' % seed)
    return codes


def admissible_answers(frozen, row):
    """The row's admissible answers, from the public side only: the same call the practice reader makes."""
    from cas_meta2.typed_teaching import checker, course
    target = checker.derive_target(course._public(frozen['bank'], row['source_world_id']), row['query'])
    return target['admissible_answers']


def scoring_rows(artifacts, names):
    """(checkpoint -> {record_id: correct}, failures) merged over every `<prefix>_pNN_scoring.json` in `names`.

    The phase names are DISCOVERED from the job's own manifest, not hardcoded: a pointer job's evaluation points
    are the practice study's, reused by import, but the reader assumes no more than the registered
    `<prefix>_pNN_scoring.json` convention. A record scored twice at one checkpoint must have agreed.
    """
    rows, failures = {}, []
    for name in sorted(names):
        match = SCORING_NAME.match(name)
        if match is None:
            continue
        number = int(match.group('number'))
        try:
            scored = _read_json(artifacts / name)
            table = {row['record_id']: bool(row['correct']) for row in scored['rows']}
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append('SCORING:%s:%s' % (type(error).__name__, name))
            continue
        bucket = rows.setdefault(number, {})
        for key, value in table.items():
            if key in bucket and bucket[key] != value:
                failures.append('SCORING_CONFLICT:%d' % number)
            bucket[key] = value
    return rows, failures


def evaluate(study_path):
    from cas_meta2.typed_teaching import pointer_contract as contract
    study = _read_json(study_path)
    frozen, _, _ = contract.load_material(ROOT)
    held, trained, excluded = contract.split(frozen)
    _, stats = contract.pointer_schedule(frozen)
    main_updates, updates_per_pass, passes = stats['main_updates'], stats['updates_per_pass'], stats['passes']
    held_questions = contract.held_back_questions(frozen)
    trained_set = set(trained)
    trained_questions = {}
    for row in frozen['registry']:
        if row['record_id'] in trained_set:
            trained_questions.setdefault(row['query']['query_id'], []).append(row['record_id'])
    by_id = {row['record_id']: row for row in frozen['registry']}
    kind_of = {row['query']['query_id']: row['query']['kind'] for row in frozen['registry']}
    world_of = {row['query']['query_id']: row['source_world_id'] for row in frozen['registry']}
    seed_order = list(contract.MODEL_SEEDS)
    worker, worker_code = worker_module()

    failures = []
    failures.extend(min_passing_b_failures(contract))
    failures.extend(worker_contract_failures(worker))

    # ---- the contract's own label contract, and the population it derives --------------------------------
    if contract.DESIGN.get('primary_label_tier') != 'RELATIONAL':
        failures.append('LABEL_CONTRACT:PRIMARY_TIER:%s' % contract.DESIGN.get('primary_label_tier'))
    if contract.DESIGN.get('flag_copy_alone_cannot_pass') is not True:
        failures.append('LABEL_CONTRACT:FLAG_COPY_RULE:%s' % contract.DESIGN.get('flag_copy_alone_cannot_pass'))
    if not contract.REMOVALS:
        failures.append('LABEL_CONTRACT:REMOVALS_EMPTY:POPULATION_UNRECONCILED')

    population = None
    try:
        population = contract.relational_population(frozen)
    except ValueError as error:
        failures.append('POPULATION:%s' % _code(error))
    except Exception as error:  # the population is the label's unit of evidence: never a crash, always a code
        failures.append('POPULATION:%s' % type(error).__name__)
    if population is not None:
        if population['total'] != contract.VERIFIED_POPULATION:
            failures.append('POPULATION:TOTAL:%d!=%d' % (population['total'], contract.VERIFIED_POPULATION))
        if population['by_kind'] != contract.VERIFIED_POPULATION_BY_KIND:
            failures.append('POPULATION:BY_KIND')
        if population['digest'] != contract.VERIFIED_POPULATION_DIGEST:
            failures.append('POPULATION:DIGEST')
        if (population['eligible_total'] != contract.VERIFIED_ELIGIBLE_RELATIONAL
                or population['eligible_by_kind'] != contract.VERIFIED_RELATIONAL_BY_KIND):
            failures.append('POPULATION_ELIGIBLE:RELATIONAL')
        if population['eligible_by_world'] != contract.VERIFIED_RELATIONAL_BY_WORLD:
            failures.append('POPULATION_ELIGIBLE:BY_WORLD')

    # ---- the eligible held questions of EVERY kind: the contract's own shortcut exclusion, re-used ---------
    # 45 = the 50 held questions minus the 5 the practice study's input-blind shortcut already answers. The
    # contract returns those 5 ids, so this is a subtraction, not a re-derivation of the shortcut.
    shortcut_ids = sorted(population['shortcut_question_ids']) if population else []
    eligible_all = sorted(set(held_questions) - set(shortcut_ids))
    eligible_by_kind = {kind: sum(1 for q in eligible_all if kind_of[q] == kind) for kind in contract.KINDS}
    tier_of = {kind: tier for tier, kinds in contract.TIERS.items() for kind in kinds}
    eligible_by_tier = {tier: sum(1 for q in eligible_all if tier_of[kind_of[q]] == tier) for tier in contract.TIERS}
    if population is not None:
        if len(eligible_all) != contract.VERIFIED_ELIGIBLE_TOTAL:
            failures.append('POPULATION_ELIGIBLE:TOTAL:%d!=%d'
                            % (len(eligible_all), contract.VERIFIED_ELIGIBLE_TOTAL))
        if eligible_by_tier != population['eligible_by_tier']:
            failures.append('POPULATION_ELIGIBLE:BY_TIER')
        if {kind: eligible_by_kind[kind] for kind in contract.RELATIONAL} != contract.VERIFIED_RELATIONAL_BY_KIND:
            failures.append('POPULATION_ELIGIBLE:ELIGIBLE_BY_KIND')

    # ---- I3's targets, read once: they do not depend on the jobs ------------------------------------------
    start_targets = {}
    for seed in seed_order:
        value, codes = practice_start(contract, seed)
        start_targets[seed] = value
        failures.extend(codes)

    jobs = study.get('jobs') if isinstance(study, dict) else None
    jobs = [job for job in jobs if isinstance(job, dict)] if isinstance(jobs, list) else []
    if (sorted(str(job.get('model_seed')) for job in jobs) != sorted(str(seed) for seed in seed_order)
            or not all(isinstance(job.get('receipt_dir'), str) for job in jobs)):
        failures.append('I0:STUDY_MUST_HAVE_EXACTLY_THE_THREE_SEEDS_WITH_RECEIPTS')
        jobs = []

    seeds, six_identities = {}, {}
    for job in jobs:
        seed, receipt = int(job['model_seed']), Path(job['receipt_dir'])
        art = _artifacts(receipt)
        report, manifest_names = {}, []
        try:  # I1 -- completion and evidence, against the POINTER worker's own constants
            lifecycle = _read_json(receipt / 'result.json')
            report = _read_json(art / 'worker_report.json')
            manifest_names = [row['name'] for row in _read_json(art / 'manifest.json')['artifacts']]
            if worker is None:
                pass  # the named code was already raised once, before any seed was read
            elif not (lifecycle.get('completed_deliverable') is True
                      and lifecycle.get('cleanup', {}).get('complete') is True
                      and report.get('status') == worker.SUCCESS_STATUS
                      and set(worker.EXPECTED_ARTIFACTS) <= set(manifest_names)):
                failures.append('I1:%d' % seed)
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append('I1:%d:%s' % (seed, type(error).__name__))
            continue
        try:  # I2 -- held worlds and excluded carriers never trained, and the frozen update counts
            material = _read_json(art / 'protocol_material.json')
            main_logs = sorted(name for name in manifest_names
                               if name.endswith('_batches.jsonl') and name != 'interference_batches.jsonl')
            seen, lines = set(), 0
            if len(main_logs) != passes:
                failures.append('I2:%d:MAIN_LOGS:%d' % (seed, len(main_logs)))
            for name in [*main_logs, 'interference_batches.jsonl']:
                count = 0
                for line in (art / name).read_bytes().splitlines():
                    count += 1
                    seen.update(p['record_id'] for p in json.loads(line)['predictions'])
                lines += count
                if name != 'interference_batches.jsonl' and count != updates_per_pass:
                    failures.append('I2:%d:PASS_LINES:%s' % (seed, name))
            if (material['held_back_record_ids'] != held or material['excluded_record_ids'] != excluded
                    or not seen <= trained_set or lines != main_updates + contract.INTERFERENCE_UPDATES):
                failures.append('I2:%d' % seed)
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append('I2:%d:%s' % (seed, type(error).__name__))
        try:  # I3 -- the in-job DG4 identity checks (the corrected form of protocol section 7.1)
            record, source = dg4_record(art, report)
            if record is None:
                failures.append('I3:%d:DG4_RECORD_MISSING' % seed)
            else:
                failures.extend(dg4_failures(seed, record, start_targets.get(seed)))
                if _is_digest(record.get('first_build_identity')):
                    six_identities[seed] = record['first_build_identity']
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append('I3:%d:%s' % (seed, type(error).__name__))
        try:  # I4 -- counts, reloads, replays
            replay = _read_json(art / 'replay_report.json')
            totals = report['global_actual_work']['totals']
            if not (report['main_training_delta']['optimizer_updates'] == main_updates
                    and report['interference_delta']['optimizer_updates'] == contract.INTERFERENCE_UPDATES
                    and totals['optimizer_updates'] == (main_updates + contract.INTERFERENCE_UPDATES
                                                        + contract.REPLAY_UPDATES)
                    and len(replay['replays']) == (required_replays(worker) or contract.REPLAY_UPDATES)
                    and len(replay['reloads']) == (required_reloads(worker) or 3)):
                failures.append('I4:%d' % seed)
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append('I4:%d:%s' % (seed, type(error).__name__))
        try:  # the scoring files: the unit of evidence behind every test below
            at, scoring_problems = scoring_rows(art, manifest_names)
            failures.extend('%s:%d' % (code, seed) for code in scoring_problems)
            if not at:
                failures.append('I1:%d:SCORING_PHASES_MISSING' % seed)
                continue
            checkpoints = sorted(at)
            start, final = checkpoints[0], checkpoints[-1]
            full = [n for n in checkpoints if set(at[n]) >= set(trained)]
            first = min([n for n in full if n > start], default=None)
            needed = sorted({record for records in held_questions.values() for record in records})
            incomplete = [n for n in (start, final) if not set(at[n]) >= set(needed)]
            for n in incomplete:
                failures.append('I1:%d:SCORING_INCOMPLETE:%d' % (seed, n))
            if incomplete:
                continue
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append('I1:%d:SCORING:%s' % (seed, type(error).__name__))
            continue
        population_ids = list(population['question_ids']) if population else []
        tier_ids = {tier: sorted(q for q in eligible_all if tier_of[kind_of[q]] == tier) for tier in contract.TIERS}
        heldq = {n: question_outcomes(at[n], held_questions) for n in checkpoints}
        trainq = {n: question_outcomes(at[n], trained_questions) for n in full}
        gained = []
        for key in population_ids:
            if not heldq[start][key] and heldq[final][key]:
                gained.append({'query_id': key, 'kind': kind_of[key], 'world': world_of[key],
                               'records': len(held_questions[key]),
                               'admissible_answers': len(admissible_answers(frozen, by_id[held_questions[key][0]]))})
        primary = seed_test(heldq[start], heldq[final], population_ids, kind_of, world_of)
        entry = {
            'checkpoints': checkpoints, 'full_course_checkpoints': full,
            'start_checkpoint': start, 'first_checkpoint': first, 'final_checkpoint': final,
            'held_questions_correct': {str(n): sum(heldq[n].values()) for n in checkpoints},
            'population_questions_correct': {str(n): sum(heldq[n][q] for q in population_ids) for n in checkpoints},
            'eligible_questions_correct': {str(n): sum(heldq[n][q] for q in eligible_all) for n in checkpoints},
            'shortcut_questions_correct': {str(n): sum(heldq[n][q] for q in shortcut_ids) for n in checkpoints},
            'tier_questions_correct': {tier: {str(n): sum(heldq[n][q] for q in keys) for n in checkpoints}
                                       for tier, keys in sorted(tier_ids.items())},
            'kind_questions_correct': {kind: {str(n): sum(heldq[n][q] for q in eligible_all if kind_of[q] == kind)
                                              for n in checkpoints} for kind in contract.KINDS},
            'world_questions_correct': {world: {str(n): sum(heldq[n][q] for q in held_questions
                                                               if world_of[q] == world) for n in checkpoints}
                                        for world in sorted({world_of[q] for q in held_questions})},
            'trained_questions_correct': {str(n): sum(trainq[n].values()) for n in full},
            PRIMARY_TEST: primary,
            'MORE_PRACTICE_population': (seed_test(heldq[first], heldq[final], population_ids, kind_of, world_of)
                                         if first is not None else {'evaluated': False}),
            ALL_KINDS_TEST: seed_test(heldq[start], heldq[final], eligible_all, kind_of, world_of),
            'TRAINED_start_to_final': (seed_test(trainq[start], trainq[final], sorted(trained_questions), kind_of)
                                       if start in trainq and final in trainq else {'evaluated': False}),
            'TRAINED_first_to_final': (seed_test(trainq[first], trainq[final], sorted(trained_questions), kind_of)
                                       if first is not None and first in trainq and final in trainq
                                       else {'evaluated': False}),
            'gained_questions': gained, 'gained_single_record': sum(1 for row in gained if row['records'] == 1),
            'dg4_source': None, 'dg4_extra_fields': [],
            'development': report.get('development_scores'), 'retention': report.get('retention_scores'),
            'pass_summaries': report.get('pass_summaries'),
        }
        for tier, keys in sorted(tier_ids.items()):
            entry['G_LEARN_' + tier] = (primary if tier == 'RELATIONAL'
                                        else seed_test(heldq[start], heldq[final], keys, kind_of, world_of))
        for kind in contract.KINDS:
            keys = sorted(q for q in eligible_all if kind_of[q] == kind)
            entry['G_LEARN_kind_' + kind] = seed_test(heldq[start], heldq[final], keys, kind_of, world_of)
        record, source = dg4_record(art, report)
        entry['dg4_source'] = source
        entry['dg4_extra_fields'] = sorted(set(record) & set(DG4_OPTIONAL_FIELDS)) if record else []
        seeds[seed] = entry

    if len(six_identities) == len(seed_order) and len(set(six_identities.values())) != len(six_identities):
        failures.append('I3:SEEDS_NOT_PAIRWISE_DIFFERENT')

    complete = not failures and len(seeds) == len(seed_order)
    primary_passed = complete and all(entry[PRIMARY_TEST]['passed'] for entry in seeds.values())
    label, rule = label_decision(complete, primary_passed)
    gates = {'integrity': {'pass': complete, 'failures': failures}}
    flags = {}
    if complete:
        gates[PRIMARY_TEST] = {'pass': primary_passed,
                               'per_seed': {str(k): v[PRIMARY_TEST]['passed'] for k, v in seeds.items()}}
        gates[ALL_KINDS_TEST] = {'pass': all(v[ALL_KINDS_TEST]['passed'] for v in seeds.values()),
                                 'per_seed': {str(k): v[ALL_KINDS_TEST]['passed'] for k, v in seeds.items()}}
        for name in ('MORE_PRACTICE_population', 'TRAINED_start_to_final', 'TRAINED_first_to_final'):
            gates[name] = {'pass': all(v[name].get('evaluated', True) and v[name]['passed'] for v in seeds.values()),
                           'per_seed': {str(k): v[name].get('passed') for k, v in seeds.items()}}
        for tier in ('DIRECT_READ', 'TEXT'):
            gates['G_LEARN_' + tier] = {'pass': all(v['G_LEARN_' + tier]['passed'] for v in seeds.values()),
                                        'per_seed': {str(k): v['G_LEARN_' + tier]['passed']
                                                     for k, v in seeds.items()}}
        gates['kind_g_learn'] = {kind: {'pass': all(v['G_LEARN_kind_' + kind]['passed'] for v in seeds.values()),
                                        'per_seed': {str(k): v['G_LEARN_kind_' + kind]['passed']
                                                     for k, v in seeds.items()}}
                                 for kind in contract.KINDS}
        flags = {
            'all_kinds_g_learn_passes': gates[ALL_KINDS_TEST]['pass'],
            'more_practice_helps_population': gates['MORE_PRACTICE_population']['pass'],
            'trained_questions_rise_from_start': gates['TRAINED_start_to_final']['pass'],
            'trained_questions_rise_with_more_practice': gates['TRAINED_first_to_final']['pass'],
            'direct_read_tier_g_learn_passes': gates['G_LEARN_DIRECT_READ']['pass'],
            'text_tier_g_learn_passes': gates['G_LEARN_TEXT']['pass'],
        }
    return {
        'schema': SCHEMA, 'protocol': PROTOCOL, 'alpha': str(ALPHA),
        'min_improved_kinds': MIN_IMPROVED_KINDS, 'min_improved_worlds': MIN_IMPROVED_WORLDS,
        'min_passing_b': contract.MIN_PASSING_B, 'min_passing_b_rederived': MIN_PASSING_B_REDERIVED,
        'label': label, 'label_rule': rule, 'label_tier': contract.DESIGN.get('primary_label_tier'),
        'label_key_test': PRIMARY_TEST, 'label_vocabulary': list(LABELS),
        'label_precedence': [
            '1. any integrity failure, or fewer than the three registered seeds -> VOID',
            '2. %s passes in all three seeds over the RELATIONAL population -> LEARNS_NEW_WORLDS' % PRIMARY_TEST,
            '3. otherwise -> NO_TRANSFER_TO_NEW_WORLDS',
            'the all-kinds %s is a reported flag and never sets the label (FP1)' % ALL_KINDS_TEST,
        ],
        'flags': flags, 'gates': gates, 'seeds': {str(k): v for k, v in seeds.items()},
        'tiers': contract.TIERS,
        'tier_g_learn': ({tier: gates['G_LEARN_' + tier] for tier in ('DIRECT_READ', 'TEXT')} if complete else {}),
        'kinds': {kind: {'eligible': eligible_by_kind[kind],
                         'population': (population['by_kind'].get(kind, 0) if population else 0),
                         'removed': (sum(len(population['removed_by_rule'][rule_name].get(kind, []))
                                         for rule_name in contract.REMOVAL_RULES) if population else 0)}
                  for kind in contract.KINDS},
        'eligible_by_tier': eligible_by_tier,
        'oracle_ceilings': {
            'applied_as_removals': False,
            'note': ("one-hop adjacency baselines, printed beside the label and never subtracted from the "
                     "population: applying the checker's own rule to the input IS the skill under test"),
            'rules': [{'kind': kind, 'rule': text, 'solves': numerator, 'of_eligible': eligible_by_kind[kind],
                       'share': (str(Fraction(numerator, eligible_by_kind[kind])) if eligible_by_kind[kind]
                                 else None)}
                      for kind, text, numerator in ORACLE_CEILINGS],
            'contract_unreconciled_readings': dict(contract.UNRECONCILED_REMOVAL_READINGS),
        },
        'correspondence': {
            'declared_false_negative': True, 'removal_class': 'inexpressible',
            'in_label_population': False, 'still_run_and_reported': True,
            'eligible_questions': eligible_by_kind.get('correspondence', 0),
            'population_questions': (population['by_kind'].get('correspondence', 0) if population else 0),
            'removed_questions': (population['removed_by_rule']['inexpressible'].get('correspondence', [])
                                  if population else []),
            'g_learn': gates['kind_g_learn'].get('correspondence') if complete else None,
        },
        'contract': {
            'candidate': contract.CANDIDATE, 'machine': contract.DESIGN.get('machine'),
            'tiers': contract.TIERS, 'removal_rules': list(contract.REMOVAL_RULES),
            'removals': {rule_name: {kind: sorted(questions)
                                     for kind, questions in sorted(contract.REMOVALS[rule_name].items())}
                         for rule_name in contract.REMOVAL_RULES},
            'verified_population': contract.VERIFIED_POPULATION,
            'verified_population_by_kind': contract.VERIFIED_POPULATION_BY_KIND,
            'verified_population_digest': contract.VERIFIED_POPULATION_DIGEST,
            'verified_eligible_total': contract.VERIFIED_ELIGIBLE_TOTAL,
            'verified_eligible_relational': contract.VERIFIED_ELIGIBLE_RELATIONAL,
            'main_counters': list(contract.MAIN_COUNTERS),
            'learner_max_updates_ceiling': contract.LEARNER_MAX_UPDATES_CEILING,
            'primary_label_rule': contract.DESIGN.get('primary_label_rule'),
            'flag_copy_alone_cannot_pass': contract.DESIGN.get('flag_copy_alone_cannot_pass'),
            'gate_population': contract.DESIGN.get('gate_population'),
            'schedule_stratified': contract.DESIGN.get('schedule_stratified'),
        },
        'population': population,
        'lk11': {'register_single_record_eligible': LK11_SINGLE_RECORD_ELIGIBLE,
                 'register_eligible_total': LK11_ELIGIBLE_TOTAL,
                 'measured_eligible_total': len(eligible_all),
                 'measured_single_record_eligible': sum(1 for q in eligible_all if len(held_questions[q]) == 1),
                 'measured_single_record_population': sum(1 for q in (population['question_ids'] if population
                                                                      else []) if len(held_questions[q]) == 1),
                 'gate': False},
        'held_worlds': stats['held_worlds'], 'passes': passes, 'updates_per_pass': updates_per_pass,
        'main_updates': main_updates, 'interference_updates': contract.INTERFERENCE_UPDATES,
        'replay_updates': contract.REPLAY_UPDATES,
        'held_questions': len(held_questions), 'eligible_questions': len(eligible_all),
        'shortcut_questions': len(shortcut_ids), 'population_questions': (population['total'] if population else 0),
        'held_records': len(held), 'trained_records': len(trained), 'excluded_records': len(excluded),
        'start_targets': {str(k): v for k, v in start_targets.items()},
        'matched_start_targets': {str(seed): matched_start(seed) for seed in seed_order},
        'void_paths': [{'code': code, 'meaning': meaning} for code, meaning in VOID_PATHS],
        'void_paths_taken': sorted(set(failures)),
    }


def self_test():
    """The reader's own test of its label decision path. Pure, no receipts, no torch, no material load.

    The load-bearing case is the flag-copy-only outcome of finding FP1: a machine that copies the input flags gets
    `b = 10`, `c = 0` on `definition 5 + context 5` over five worlds, `p = 1/1024 = 0.0009765625`, which clears
    the arithmetic, the >= 2 kinds rule and the >= 2 worlds rule. That outcome must receive NO label: the all-kinds
    result is a flag, and the label is keyed on the RELATIONAL population alone.
    """
    from cas_meta2.typed_teaching import pointer_contract as contract
    checks = []

    def check(name, condition, detail):
        checks.append({'check': name, 'pass': bool(condition), 'detail': detail})

    check('binomial_upper_tail_10_10', binomial_upper_tail(10, 10) == Fraction(1, 1024),
          '%s = %r' % (binomial_upper_tail(10, 10), float(binomial_upper_tail(10, 10))))
    check('binomial_upper_tail_5_10', binomial_upper_tail(5, 10) == Fraction(638, 1024),
          '%s = %r' % (binomial_upper_tail(5, 10), float(binomial_upper_tail(5, 10))))
    check('min_passing_b_rederived', MIN_PASSING_B_REDERIVED == 7,
          'smallest b with 2**-b <= %s at c = 0: %d' % (ALPHA, MIN_PASSING_B_REDERIVED))
    check('min_passing_b_read_from_contract', contract.MIN_PASSING_B == MIN_PASSING_B_REDERIVED,
          'contract.MIN_PASSING_B = %d' % contract.MIN_PASSING_B)
    check('six_fails_seven_passes', binomial_upper_tail(6, 6) == Fraction(1, 64)
          and binomial_upper_tail(6, 6) > ALPHA and binomial_upper_tail(7, 7) <= ALPHA,
          '2**-6 = %r > %s; 2**-7 = %r <= %s' % (float(binomial_upper_tail(6, 6)), ALPHA,
                                                 float(binomial_upper_tail(7, 7)), ALPHA))
    check('contract_keys_the_label_on_relational',
          contract.DESIGN.get('primary_label_tier') == 'RELATIONAL'
          and contract.DESIGN.get('flag_copy_alone_cannot_pass') is True,
          'primary_label_tier = %r, flag_copy_alone_cannot_pass = %r'
          % (contract.DESIGN.get('primary_label_tier'), contract.DESIGN.get('flag_copy_alone_cannot_pass')))

    # the FP1 outcome: 10 gained DIRECT_READ questions over 5 worlds, no relational gain at all
    counts = {'definition': 5, 'context': 5, 'parts': 2, 'edge_account': 5, 'reach': 6, 'analogy': 5}
    worlds = ['world-selftest-%d' % n for n in range(5)]
    kind_of, world_of, copied, relational = {}, {}, set(), []
    for kind, count in counts.items():
        for _ in range(count):
            key = 'typed-query-selftest-%03d' % len(kind_of)
            kind_of[key] = kind
            world_of[key] = worlds[len(kind_of) % len(worlds)]
            if kind in ('definition', 'context'):
                copied.add(key)
            if kind in contract.RELATIONAL:
                relational.append(key)
    relational = sorted(relational)
    before = {key: False for key in kind_of}
    after = {key: key in copied for key in kind_of}
    all_kinds = seed_test(before, after, sorted(kind_of), kind_of, world_of)
    primary = seed_test(before, after, relational, kind_of, world_of)
    decision_label, decision_rule = label_decision(True, primary['passed'])
    check('flag_copy_only_all_kinds_gate_passes',
          all_kinds['passed'] is True and all_kinds['wrong_to_right'] == 10 and all_kinds['right_to_wrong'] == 0
          and all_kinds['p_one_sided'] == '1/1024' and all_kinds['p_float'] == 0.0009765625
          and len(all_kinds['improved_kinds']) == 2 and len(all_kinds['improved_worlds']) >= 2,
          'b = %d, c = %d, p = %s = %r, kinds = %r, worlds = %d'
          % (all_kinds['wrong_to_right'], all_kinds['right_to_wrong'], all_kinds['p_one_sided'],
             all_kinds['p_float'], all_kinds['improved_kinds'], len(all_kinds['improved_worlds'])))
    check('flag_copy_only_primary_test_fails',
          primary['passed'] is False and primary['wrong_to_right'] == 0 and primary['right_to_wrong'] == 0
          and primary['p_one_sided'] == '1',
          'population b = %d, c = %d, p = %s' % (primary['wrong_to_right'], primary['right_to_wrong'],
                                                 primary['p_one_sided']))
    check('flag_copy_only_gets_no_label',
          decision_label == 'NO_TRANSFER_TO_NEW_WORLDS' and decision_label != 'LEARNS_NEW_WORLDS',
          'label = %s (%s) while flags.all_kinds_g_learn_passes would be True' % (decision_label, decision_rule))

    # a genuine relational gain at the boundary: b = 7, c = 0, two kinds, two worlds
    genuine = relational[:7]
    real = seed_test({key: False for key in genuine}, {key: True for key in genuine}, genuine, kind_of, world_of)
    check('seven_gains_in_two_kinds_two_worlds_passes',
          real['passed'] is True and real['p_one_sided'] == '1/128'
          and len(real['improved_kinds']) >= 2 and len(real['improved_worlds']) >= 2,
          'b = %d, p = %s, kinds = %r, worlds = %d' % (real['wrong_to_right'], real['p_one_sided'],
                                                       real['improved_kinds'], len(real['improved_worlds'])))
    six = relational[:6]
    check('six_gains_do_not_pass',
          seed_test({key: False for key in six}, {key: True for key in six}, six, kind_of, world_of)['passed']
          is False,
          'b = 6 -> p = %s = %r > %s' % (binomial_upper_tail(6, 6), float(binomial_upper_tail(6, 6)), ALPHA))
    check('a_tie_does_not_pass',
          seed_test({'q': True}, {'q': False}, ['q'], {'q': 'parts'}, {'q': 'world-1'})['passed'] is False,
          'b = 0, c = 1 is refused by b > c')
    check('genuine_gain_earns_the_label', label_decision(True, real['passed'])[0] == 'LEARNS_NEW_WORLDS',
          'label = %s' % label_decision(True, real['passed'])[0])
    check('integrity_failure_is_void',
          {label_decision(False, p)[0] for p in (True, False)} == {'VOID'},
          'complete = False -> VOID whatever the gate says')
    check('label_vocabulary_is_exactly_three',
          sorted({label_decision(c, p)[0] for c in (True, False) for p in (True, False)}) == sorted(LABELS),
          'the four (complete, passed) outcomes land in %r' % (list(LABELS),))
    check('void_paths_enumerated',
          any(code.startswith('POPULATION') for code, _ in VOID_PATHS)
          and any(code.startswith('I3:') for code, _ in VOID_PATHS)
          and all(type(meaning) is str and meaning for _, meaning in VOID_PATHS),
          '%d enumerated paths into VOID' % len(VOID_PATHS))
    check('dg4_contract_declared',
          DG4_IDENTITY_FORM == 'THREE_TENSOR' and len(DG4_FIELDS) == 4 and bool(DG4_REPORT_KEYS)
          and bool(DG4_ARTIFACT_NAMES),
          'I3 accepts %r in worker_report.json, then %r as an artifact, and requires %r'
          % (list(DG4_REPORT_KEYS), list(DG4_ARTIFACT_NAMES), list(DG4_FIELDS)))
    check('oracle_ceilings_are_not_removals', len(ORACLE_CEILINGS) == 3
          and [numerator for _, _, numerator in ORACLE_CEILINGS] == [5, 5, 1],
          'the one-hop ceilings %r are printed beside the label and subtract nothing'
          % ([numerator for _, _, numerator in ORACLE_CEILINGS],))
    print(json.dumps({'self_test': checks, 'passed': sum(1 for row in checks if row['pass']),
                      'failed': [row['check'] for row in checks if not row['pass']]}, indent=1, sort_keys=True))
    if all(row['pass'] for row in checks):
        print('SELFTEST_PASS %d checks' % len(checks))
        return 0
    print('SELFTEST_FAIL')
    return 1


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--self-test':
        raise SystemExit(self_test())
    if len(sys.argv) != 2:
        raise SystemExit('usage: evaluate_gates.py STUDY_JSON | --self-test')
    if not Path(sys.argv[1]).is_file():
        raise SystemExit('STUDY_JSON_MISSING: no reading printed, so no label is claimed: %s' % sys.argv[1])
    print(json.dumps(evaluate(sys.argv[1]), indent=1, sort_keys=True))
