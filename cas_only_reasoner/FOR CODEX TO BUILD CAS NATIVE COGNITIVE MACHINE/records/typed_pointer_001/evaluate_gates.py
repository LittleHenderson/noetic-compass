"""The deterministic gate reading of the pointer study (docs/CNCM_TYPED_POINTER_STUDY_v0.1.md, section 7).

Pure standard library plus the project's pure modules and the private checker (post-run, local). Reads the
collected receipts; runs no model, imports no torch. **The label this program prints IS the claim status.** No
prose anywhere may upgrade it, and nothing else in the project may decide it.

    python evaluate_gates.py STUDY_JSON
    python evaluate_gates.py --self-test

Copied from `records/typed_practice_001/evaluate_gates.py` at HEAD `489cda65`: the same structure, the same
integrity chain shape I0-I4, the same exact arithmetic and the same three-word label vocabulary. Four things are
NEW, and each is named where it is raised. **Symbols, not line numbers, are cited in this docstring and in the
comments that carry evidence: line numbers rot with every concurrent edit of a file this reader does not own.**

* **I1** imports `cncm.typed_pointer_worker` and checks THAT worker's `SUCCESS_STATUS` and `EXPECTED_ARTIFACTS`
  (the practice reader imports `cncm.typed_practice_worker`). The pointer worker did not exist at HEAD
  `489cda65`, so the check fails CLOSED with the named code `I1:WORKER_MODULE_MISSING` rather than crashing.
* **I3** reads the in-job DG4 identity checks the worker recorded, in the corrected form of protocol section 7.1:
  the three `^6` tensors' identity equals the practice study's recorded start for that seed, a second independent
  build gives the same identity, the three seeds' identities are pairwise different, and the start is identical
  with the checkpoint check on and off. The practice I3 compared `model_state_identity` against the matched
  study's checkpoint, which the pointer container can never equal, because that value
  (`cas_meta2.typed_teaching.learner.state_identity`) digests the whole `module.state_dict()` while the pointer
  container holds far more than the `^6` block (finding RK8).
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

WHAT WAS UNDETERMINED AT HEAD `489cda65`, and what it is now. When this reader was written the pointer worker did
not exist, and two things were marked `UNCERTAIN:`. Both are now RESOLVED against the shipped worker
(`cncm/typed_pointer_worker.py`), and the reader is aligned to it rather than to a guess. Each resolution is
stated against a SYMBOL of the worker, never against a line number:

* `RESOLVED: the DG4 record's location and field names.` `_seed_and_double_build` writes the full evidence as the
  artifact `model_identity.json` and mirrors a four-boolean summary under `worker_report.json["model_identity"]`.
  I3 reads the artifact first, then the summary, and fails closed with `I3:<seed>:DG4_RECORD_MISSING` when neither
  is present.
* `RESOLVED: the evaluation phase names and the batch-log names.` `_evaluation_phases` builds `course_pNN` /
  `heldback_pNN` / `development_pNN`, and the pass logs are `pass_NN_batches.jsonl`, every name of them listed by
  `expected_artifact_names`. The reader still discovers both from the job's own manifest instead of hardcoding
  them, so a renamed prefix is read rather than refused.
* `NEW, AND NOT IN THE PROTOCOL'S I1:` the job can run a REDUCED schedule through `REDUCED_SCHEDULE_ENV` and
  `schedule_plan()`, which changes the pass count, the updates and the evaluation points, delivers normally with
  `SUCCESS_STATUS`, and marks itself `claim_bearing = False` with `schedule_plan_mode = "REDUCED"`. A smoke job
  must never be able to print a label, so I1 refuses any job that is not `claim_bearing is True and
  schedule_plan_mode == "REGISTERED"` with `I1:<seed>:REDUCED_SCHEDULE:<mode>`, and it CROSS-CHECKS that refusal
  against the `schedule_plan.json` the job sealed rather than trusting the report's own self-description (R1-9).
  The job's own required-artifact set (`report["required_artifacts"]`, the rule `deliver` itself uses) is what I1
  checks the manifest against, and for a claim-bearing REGISTERED run that set must ALSO equal the worker's
  registered `EXPECTED_ARTIFACTS` (R1, FIX 6): `_effective_required` shrinks the recorded set when a report-only
  check failed, so without this a run whose ablations silently failed was read as complete.

THE TEST THAT COULD NOT FAIL, AND HOW IT CAN NOW. `--self-test` used to exercise `seed_test` and `label_decision`
on synthetic readings only, so the code that CHOOSES WHICH QUESTION SET THE LABEL IS KEYED ON was never driven:
an adversarial 15-mutation battery left it green while feeding the label the all-kinds result, or keying it on
DIRECT_READ, both of which would print `LEARNS_NEW_WORLDS` for a machine that copied two input flags and learned
nothing (finding FP1). Three changes close that hole, and none of them moves a threshold, a population or a gate:

* the key choice is ONE pure function, `primary_keys`, and nothing else in this program may name the label's unit
  of evidence;
* every reading echoes that key set as `label_key_population` / `label_key_kinds`, so the choice can be asserted
  on directly;
* the self-test now drives `evaluate()` itself on a synthetic three-seed receipt set built in `%TEMP%`, in which
  the all-kinds gate PASSES while the RELATIONAL population test FAILS. That is the flag-copy-only outcome, and
  the label it prints must be `NO_TRANSFER_TO_NEW_WORLDS`. The synthetic worker is a stub, so this suite stays
  green whatever state the real worker module is in when it is run.

ANY UNEXPECTED ERROR BECOMES A PRINTED READING. A malformed study file used to reach `json.loads` outside any
`try`, so the program exited 1 with empty stdout and a `JSONDecodeError` traceback. The body after the contract
import is now wrapped: any error yields a printed reading with `label = VOID`, `rule = READER:<reason>` and
`READER:<reason>` in `void_paths_taken`. **Never a bare traceback, never a silent empty stdout.**
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
from math import comb
import json
from pathlib import Path
import re
import sys
import tempfile

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
CORRESPONDENCE_KIND = 'correspondence'

# ------------------------------------------------------------------------------------------------------------------
# THE LABEL'S KEY SET IS CHOSEN IN ONE PLACE. `primary_keys` is that place, and `label_keys` (the single value it
# returns for a reading) is the only name any test or report of the label's unit of evidence may read. Nothing in
# this program may widen it, and no second expression may name it: an adversarial battery mutated the label's key
# set to the ALL-KINDS result and to DIRECT_READ and left the old suite green (R1, FIX 1 / P12).
# ------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------
# I3's record contract, read off the SHIPPED worker (`cncm.typed_pointer_worker._seed_and_double_build` writes it).
# The job writes the full record as the artifact `model_identity.json`, and a four-flag summary under
# `worker_report.json["model_identity"]`; the artifact is tried FIRST because only it carries the identity values.
# The reader re-derives every comparison it can from the pinned practice receipt and from the record's own
# three-seed map, so a self-consistent but wrong record is caught.
# ------------------------------------------------------------------------------------------------------------------
DG4_ARTIFACT_NAMES = ('model_identity.json',)
DG4_REPORT_KEYS = ('model_identity',)
DG4_IDENTITY_FORM = 'THREE_^6_TENSORS_ONLY'
# The identity values, each a 64-hex `state_identity`.
DG4_FIELDS = ('core_identity', 'whole_container_identity', 'second_independent_whole_build_identity',
              'practice_recorded_model_state_identity')
# The job's own booleans. Each must be True, and each is ALSO re-derived below where the reader can.
# `phase_a_finished_before_the_model_was_seeded` is one of them (FIX 2): it used to sit in the report-only tuple
# beside the real status, written as the unconditional literal `True`, so no reader branch could ever fail on it.
# A flag that cannot vary is not evidence, so it is required as a flag here and corroborated against the phase-A
# artifact by `phase_a_failures`.
#
# R1-2, RECORDED AS A KNOWN TAUTOLOGY AND NOT REMOVED. `identical_start_with_and_without_the_checkpoint_check` is
# definitionally the same comparison as `core_identity_equals_the_practice_start` (the job writes both from the
# same two identities with the same operator, and its own artifact says so), so it CANNOT vary independently of
# it. Consequence, stated here so no later reader mistakes it for separate evidence: the reader's
# `DG4_CHECK_INDEPENDENT_START` code measures nothing beyond `I3:<seed>:DG4_FLAG:*`,
# `I3:<seed>:DG4_SIX_IDENTITY` and `I3:<seed>:DG4_START_TARGET`, which already cover the same values. It is kept
# because a job that STOPS recording the flag must fail closed rather than pass, which is the whole point of FIX 2,
# and it is named as a tautology rather than silently left looking like evidence. The DG4 checks in that record
# that CAN vary independently are the second independent whole build, the three-seed identity map, and the
# whole-container form being a different number from the three-tensor form (V3).
DG4_FLAGS = ('core_identity_equals_the_practice_start', 'double_build_equal', 'seeds_pairwise_different',
             'identical_start_with_and_without_the_checkpoint_check',
             'whole_container_form_is_a_different_number',
             'phase_a_finished_before_the_model_was_seeded')
# Report-only fields, echoed so the reader's evidence trail is complete.
DG4_OPTIONAL_FIELDS = ('phase_a_status', 'comparison_method',
                       'local_note', 'seed_core_identities', 'model_seed')
# Phase A's custody evidence (protocol section 7.2): a name of the worker's own `EXPECTED_ARTIFACTS`, sealed with
# a `status` of `COMPLETE` or `FAILED` INSIDE it. The status the reader accepts is exactly this value.
PHASE_A_COMPLETE = 'COMPLETE'
DG4_PHASE_A_ARTIFACT_NAMES = ('checkpoint_check_phase_a.json',)

# ------------------------------------------------------------------------------------------------------------------
# The ORACLE one-hop ceilings. FROZEN, reported BESIDE the label and never applied as removals: REVIEW_SYNTHESIS
# section 10.1.1 - "applying the checker's own rule to the input IS the skill under test; these are the ceiling
# baselines the label must be compared against". The numerators are that section's own readings; the denominators
# are the ELIGIBLE held questions of the kind (LK9, the "ORACLE RULES ... removes N eligible" rows of
# `lk6_gate_population_out.txt`, cross-checked against `lk1_answer_carriers_out.txt`), recomputed by this
# reader and required to equal the contract's VERIFIED_RELATIONAL_BY_KIND. Cited by ROW NAME, never by line: the
# measurements are frozen but every line number in every file in this repository has moved at least once.
# ------------------------------------------------------------------------------------------------------------------
ORACLE_CEILINGS = (
    ('parts', 'children of the whole argument, one adjacency hop', 5),
    ('edge_account', 'the full adjacency of the focus world, one-hop copy', 5),
    ('reach', 'DIRECT iff the part is a child, else ABSENT, one adjacency hop', 1),
)
# THE DECISIVE NUMBER, WHICH THE CEILING NUMERATORS ABOVE DO NOT GIVE (R1, FIX 4). Those numerators are counts of
# ELIGIBLE questions, 11 of them, and four of the 11 are already removed from the label's population by a shortcut
# rule. What a zero-learning rule actually solves INSIDE the frozen 18 is therefore a different, smaller number,
# and it is the number the label must be read beside. These are the frozen ids themselves, copied from
# `pre_design/measurements/leaks_review/lk6_gate_population_out.txt` (the "oracle one-hop (STRICT only)" row) and
# from the "rank-last pointing (needs the rank feature)" row, so the intersection with the population is COMPUTED
# here rather than restated: R1 measured the oracle rule solving 7 of the 18 in 2 kinds and 5 worlds, and the
# rank-last rule solving 5 of the 18 in 2 kinds and 2 worlds, whose union is 11 of 18.
ORACLE_ONE_HOP_SOLVED_IDS = (
    'typed-query-0dcbaf897c1b84ec4febc2e82ee4f58002d9397ab835fea95f0a9ffb847b0226',
    'typed-query-29e8f3c3bf9dd513de24e16b4cf7436352f07bc1c3d80d7151ebdfa2030043b8',
    'typed-query-35a5228878433ecea2de7adce40d9a596c42bbb9704ad6678d376769e44370de',
    'typed-query-4a0342c26f982758689611569bebd798f324a52a3b8ee25cb5f016b394e17509',
    'typed-query-6caa13d8bd54f96e3b8981d4cd9cfbef5986ea0d621e2f4833b336507b88d353',
    'typed-query-6d9f6280ddb8dc463bfb557617353b7857fba6cfda057403516a79d8a5ec1249',
    'typed-query-786bbcba487ecf70442672d83b1d36b6ab7ed062e996abf3c04569f67d203ceb',
    'typed-query-a14f184d8f6cc4f3b80a87998515fe3c707c2dfb4f92a2358f1233fc43fba1d9',
    'typed-query-c7ee82d21b69bf37a34cadf033ed59ddb829ceec26d3459ecca3b239c29f16ab',
    'typed-query-d51fda7f878d7656bdebb87867573769bc53bc3299bb3e2af514eb9a4274b445',
    'typed-query-dde56958ee3398739016ce6152278d821a1691cb5875c191e9a42077da4b16f7',
)
RANK_LAST_SOLVED_IDS = (
    'typed-query-369885551a553d5fa430a4f0389a1e547fb4b7a6234e85d2c9aace042f4fd46f',
    'typed-query-404166e8b8180ddc5758d193239cd0f8a5f91804f2f87bc6141ab9f782157005',
    'typed-query-786bbcba487ecf70442672d83b1d36b6ab7ed062e996abf3c04569f67d203ceb',
    'typed-query-aa62bbee865ac5ca1a350bb48564cea189bedbba60867d0f94250d10ed95f217',
    'typed-query-f341afc7254139140ecbc5edaba9fd164bac26896c217e61e9c9c5b5ac8b5d82',
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
     'EXPECTED_ARTIFACTS is not unique, is 500 names or more, omits worker_report/measurements, or the +3 rule is off'),
    ('I1:<seed>', 'lifecycle, worker status or artifact manifest does not satisfy the worker contract'),
    ('I1:<seed>:REDUCED_SCHEDULE:<mode>',
     'the job did not run the REGISTERED plan, so it is not a claim-bearing run and may not print a label'),
    ('I1:<seed>:REQUIRED_ARTIFACTS:<recorded>!=<registered>',
     'a claim-bearing REGISTERED run recorded a required-artifact set shorter than the registered one, which is '
     'what a run records when a report-only check silently failed (R1, FIX 6)'),
    ('I3:<seed>:PHASE_A_NOT_COMPLETE:<seen>',
     'the DG4 record does not report phase A as COMPLETE, so the custody ordering of protocol section 7.2 was '
     'never established for that seed (R1, FIX 2)'),
    ('I3:<seed>:PHASE_A_ARTIFACT:<reason>',
     'the sealed phase-A artifact is missing, unreadable, not COMPLETE, or records a start that is not the pinned '
     'practice start for that seed (R1, FIX 2)'),
    ('READER:<reason>',
     'the reading itself raised before it could be completed, so no label can be claimed: the error is printed '
     'inside a VOID reading instead of escaping as a traceback (R1, FIX 3)'),
    ('LABEL_KEY_SET:<seed>:DIVERGED:<test>!=<derived>',
     'the test that sets the label ran over a different question set from the one `primary_keys` derived, so the '
     'label would not be keyed on the RELATIONAL population (R1, FIX 1)'),
    ('I1:<seed>:<Error>', 'reading that job receipt raised OSError/ValueError/KeyError/TypeError'),
    ('I1:<seed>:SCORING:<Error>', 'a scoring file could not be read'),
    ('I1:<seed>:SCORING_PHASES_MISSING', 'the manifest holds no <prefix>_pNN_scoring.json'),
    ('I1:<seed>:SCORING_CONFLICT:<n>', 'two scoring files at one checkpoint disagree about a record'),
    ('I1:<seed>:SCORING_INCOMPLETE:<n>', 'a checkpoint does not hold every record the test needs'),
    ('I2:<seed>', 'held/excluded ids, a trained-only batch log, or the update counts do not match the frozen split'),
    ('I2:<seed>:MAIN_LOGS:<n>', 'the number of main batch logs is not the frozen pass count'),
    ('I2:<seed>:PASS_LINES:<name>', 'a pass log does not hold exactly the frozen updates per pass'),
    ('I3:<seed>', 'a DG4 identity check failed, or reading the DG4 evidence raised'),
    ('I3:<seed>:DG4_RECORD_MISSING', 'the job recorded no DG4 identity record at any accepted location'),
    ('I3:<seed>:DG4_IDENTITY_FORM:<form>', 'the record does not use the three-tensor identity form'),
    ('I3:<seed>:DG4_FIELD:<field>', 'a required DG4 field is missing or is not 64 hex characters'),
    ('I3:<seed>:DG4_FLAG:<flag>', 'a boolean the job recorded as its own DG4 evidence is not true'),
    ('I3:<seed>:DG4_START_TARGET', 'the record names a practice start that is not the pinned one for that seed'),
    ('I3:<seed>:DG4_SIX_IDENTITY', 'the first build of the three ^6 tensors does not equal the practice start'),
    ('I3:<seed>:DG4_DOUBLE_BUILD', 'the second independent whole-model build does not give the same identity'),
    ('I3:<seed>:DG4_SEED_IDENTITIES',
     'the record\'s three-seed identity map is not the three registered seeds, pairwise different, with this seed equal'),
    ('I3:<seed>:DG4_NOT_DISTINCT_FORM',
     'the whole-container identity equals the three-tensor identity, so the check compares the job to itself (V3)'),
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
    and, when worlds are given, in >= 2 worlds.

    The returned dict CARRIES THE KEY SET THE TEST RAN OVER as `keys`. That is not decoration: it is what makes
    the label's unit of evidence MEASURED rather than intended, so a reader (and the self-test) can see which
    questions the test that set the label actually used, even if a later edit changes the expression at the call
    site (R1, FIX 1).
    """
    test = paired(before, after, keys)
    b, c = test['wrong_to_right'], test['right_to_wrong']
    p = binomial_upper_tail(b, b + c)
    improved = [k for k in keys if not before[k] and after[k]]
    kinds = sorted({kind_of[k] for k in improved})
    worlds = sorted({world_of[k] for k in improved}) if world_of is not None else None
    passed = b > c and p <= ALPHA and len(kinds) >= MIN_IMPROVED_KINDS
    if world_of is not None:
        passed = passed and len(worlds) >= MIN_IMPROVED_WORLDS
    test.update(p_one_sided=str(p), p_float=float(p), improved_kinds=kinds, improved_worlds=worlds, passed=passed,
                keys=list(keys))
    return test


def label_decision(complete, primary_passed):
    """The ONLY label decision in this program, in order of precedence, as (label, rule code).

    1. anything that breaks the integrity chain, or fewer than the three registered seeds -> VOID
    2. the RELATIONAL population test passes in all three seeds                        -> LEARNS_NEW_WORLDS
    3. otherwise                                                                        -> NO_TRANSFER_TO_NEW_WORLDS

    `complete` is `not failures and len(seeds) == len(contract.MODEL_SEEDS)`. `primary_passed` is the primary test
    over the key set `primary_keys` returned - NEVER the all-kinds test (FP1). No other code path sets a label.
    """
    if not complete:
        return 'VOID', 'INTEGRITY_OR_SEED_COUNT_FAILED'
    if primary_passed:
        return 'LEARNS_NEW_WORLDS', 'RELATIONAL_POPULATION_TEST_PASSED_ALL_SEEDS'
    return 'NO_TRANSFER_TO_NEW_WORLDS', 'RELATIONAL_POPULATION_TEST_FAILED'


def label_key_divergence_failures(seed, test_keys, label_keys):
    """The label's test must have run over EXACTLY the key set `primary_keys` derived, or the reading is VOID.

    This is the invariant that makes "the key set is computed in exactly one place" enforceable rather than
    descriptive. A substitution at the ONE call site that picks the set the label's test uses - the mutation R1
    used, and the one an adversarial review will try again - changes what the test ran over; without this guard
    that substitution could leave every recorded key set intact and still move the label, which is precisely how a
    test that cannot fail is built. Named `LABEL_KEY_SET:<seed>:DIVERGED`, and it can only ever WITHHOLD a label.
    """
    if list(test_keys) == list(label_keys):
        return []
    return ['LABEL_KEY_SET:%d:DIVERGED:%d!=%d' % (seed, len(list(test_keys)), len(list(label_keys)))]


def primary_keys(contract, population, eligible, kind_of):
    """THE ONE PLACE the label's key set is chosen: the eligible held RELATIONAL questions of the derived population.

    R1's P12 (protocol sections 4.1 and 11.3) is the behavioural test that a flag-copy-only outcome receives no
    label, and it can only mean anything if the SET OF QUESTIONS the label is keyed on is computed once and can be
    asserted on. This function is that single place. Its rules, all of them fail-CLOSED:

    * `population` is the contract's own `relational_population(frozen)` - the eligible held RELATIONAL questions
      after the frozen removals (18). With no derived population the key set is EMPTY, so the label cannot pass;
    * every returned id must belong to the tier the CONTRACT registers as its label tier
      (`DESIGN["primary_label_tier"]`), looked up through `contract.TIERS`. A contract that registered another
      tier would produce an empty set here rather than a wider one: DIRECT_READ and TEXT can never be the label's
      unit of evidence (protocol section 3; findings LK1, LK2);
    * `eligible` - every eligible held question of every kind - is the outer boundary, so a key set is never
      returned that the caller could not have derived from the population it was handed.

    The caller must run the primary test over exactly the returned list and report it as `label_key_population`.
    """
    if population is None:
        return []
    tier = contract.DESIGN.get('primary_label_tier')
    members = set(contract.TIERS.get(tier, ()))
    keys = sorted(question for question in population['question_ids'] if kind_of.get(question) in members)
    if set(keys) != set(population['question_ids']) or not set(keys) <= set(eligible):
        return []
    return keys


def solved_breakdown(ids, kind_of, world_of):
    """`{by_kind, kinds, worlds}` for a set of question ids: the shape every zero-learning floor is reported in."""
    kinds = sorted({kind_of[question] for question in ids})
    return {'by_kind': {kind: sum(1 for question in ids if kind_of[question] == kind) for kind in kinds},
            'kinds': kinds, 'worlds': sorted({world_of[question] for question in ids})}


def correspondence_run_and_reported(seeds):
    """R1-8, DERIVED: `correspondence` is run and reported only if every seed actually SCORED every one of its
    eligible questions. The field used to be the hardcoded literal `True`, which is a statement that cannot vary
    and therefore is not evidence; this returns `False` whenever a seed's checkpoints do not carry them, and
    `False` for a reading that produced no seed at all.
    """
    return bool(seeds) and all(
        entry.get('correspondence_questions_eligible', 0) > 0
        and len(entry.get('correspondence_questions_scored', [])) == entry.get('correspondence_questions_eligible')
        for entry in seeds.values())


def phase_a_failures(seed, record, artifacts, target):
    """The phase-A custody evidence, as its own failure codes. Fails CLOSED; never raises.

    Protocol section 7.2: phase A restores the practice checkpoints and MUST finish before the pointer model is
    seeded, because restoring overwrites all three global RNG streams. The job's identity record asserts that with
    `phase_a_finished_before_the_model_was_seeded` - a field that used to be the unconditional literal `True`,
    sitting beside the real status inside the report-only tuple, so **no reader branch could ever fail on it** and
    a job whose checkpoint check FAILED still delivered `SUCCESS_STATUS` and could print a label while its own
    `model_identity.json` asserted the ordering held (R1, FIX 2 / BLOCKER 2).

    Three things are required, and each is a separate code:

    1. the record's `phase_a_status` must be exactly `COMPLETE`, else `I3:<seed>:PHASE_A_NOT_COMPLETE:<seen>`;
    2. the ordering boolean must be a strict `True` - raised by `dg4_failures` as `DG4_FLAG:*`, from the flag list,
       so an ABSENT field fails closed instead of passing;
    3. the sealed phase-A artifact (`checkpoint_check_phase_a.json`, a name of the worker's own
       `EXPECTED_ARTIFACTS`) must be readable, must itself carry `status == "COMPLETE"`, and - when it records
       this seed's own practice start - that start must be the pinned one, else `I3:<seed>:PHASE_A_ARTIFACT:<code>`.

    THE SHAPE THIS READER ACCEPTS, stated because the instruction was to report it and to fail safe across the
    transition while the worker half is being made measured rather than literal: the record must carry BOTH
    `phase_a_status == "COMPLETE"` and a strict `True` ordering flag, AND the sealed artifact must corroborate it
    with its own `status == "COMPLETE"`. An OLD, unconditional literal `True` is **not distinguishable** from a
    measured `True` inside `model_identity.json` - both are the JSON value `true` - so this reader does not pretend
    to detect it there. It refuses to take the ordering on the record's own word, and corroborates it from the
    artifact the job sealed instead. That is why the literal shape is accepted ONLY when the artifact agrees, and
    why an absent field, an absent artifact, an unreadable artifact or a non-`COMPLETE` status all FAIL CLOSED.
    """
    codes = []
    status = record.get('phase_a_status') if isinstance(record, dict) else None
    if status != PHASE_A_COMPLETE:
        codes.append('I3:%d:PHASE_A_NOT_COMPLETE:%s' % (seed, status if status is not None else 'MISSING'))
    evidence, reason = None, None
    for name in DG4_PHASE_A_ARTIFACT_NAMES:
        path = Path(artifacts) / name
        if not path.is_file():
            continue
        try:
            value = _read_json(path)
        except (OSError, ValueError, TypeError) as error:
            reason = 'UNREADABLE:%s' % type(error).__name__
            break
        if isinstance(value, dict):
            evidence = value
        else:
            reason = 'NOT_A_RECORD'
        break
    if evidence is None:
        codes.append('I3:%d:PHASE_A_ARTIFACT:%s' % (seed, reason or 'MISSING'))
        return codes
    if evidence.get('status') != PHASE_A_COMPLETE:
        codes.append('I3:%d:PHASE_A_ARTIFACT:STATUS:%s' % (seed, evidence.get('status')))
    checkpoints = evidence.get('checkpoints')
    initial = checkpoints.get('initial') if isinstance(checkpoints, dict) else None
    if isinstance(initial, dict):
        recorded = initial.get('practice_recorded_model_state_identity')
        if _is_digest(recorded) and _is_digest(target) and recorded != target:
            codes.append('I3:%d:PHASE_A_ARTIFACT:START_TARGET' % seed)
    return codes


def registered_required_failures(seed, report, worker, required):
    """FIX 6: a claim-bearing REGISTERED run must have recorded the REGISTERED artifact set, not a shrunken one.

    `evaluate_gates` compared the manifest to the run's OWN recorded `required_artifacts`, and
    `cncm.typed_pointer_worker._effective_required` SHRINKS that set when a report-only check failed (a phase-A
    vector that was not produced, an ablation that reported `status != "COMPLETE"`). Every gate-critical artifact
    is read independently, so no false label followed - but a run whose ablations silently failed was read as
    COMPLETE (R1, FIX 6). For a run that claims to be claim-bearing and REGISTERED the recorded set must therefore
    EQUAL the worker's own registered `EXPECTED_ARTIFACTS`. The reduced case is untouched: a reduced run is refused
    earlier by the REDUCED check, not by this one.
    """
    if worker is None or report.get('claim_bearing') is not True:
        return []
    if report.get('schedule_plan_mode') != 'REGISTERED':
        return []
    registered = tuple(getattr(worker, 'EXPECTED_ARTIFACTS', ()) or ())
    if not registered or tuple(required) == registered:
        return []
    return ['I1:%d:REQUIRED_ARTIFACTS:%d!=%d' % (seed, len(tuple(required)), len(registered))]


def schedule_plan_failures(seed, report, schedule):
    """R1-9: the REDUCED refusal is cross-checked against the plan the job SEALED, not against its own summary.

    Both the report and `schedule_plan.json` are written by the same job, so this is not an independent
    measurement; it is a consistency check, and it fails CLOSED on every shape that is not an explicit REGISTERED,
    claim-bearing plan with no reduced request. A `schedule_plan.json` that is absent, unreadable, or silent about
    `reduced_schedule_requested` is a refusal, never a pass: withholding a label is always safe, manufacturing one
    is not.
    """
    codes = []
    if report.get('claim_bearing') is not True:
        return codes  # the report's own refusal already fired; this function only corroborates
    if isinstance(schedule, dict):
        requested = schedule.get('reduced_schedule_requested')
        if requested is not False:
            codes.append('I1:%d:REDUCED_SCHEDULE:requested=%r' % (seed, requested))
        if schedule.get('claim_bearing') is not True or schedule.get('mode') != 'REGISTERED':
            codes.append('I1:%d:REDUCED_SCHEDULE:schedule_plan_mode=%r' % (seed, schedule.get('mode')))
    else:
        codes.append('I1:%d:REDUCED_SCHEDULE:schedule_plan_unreadable' % seed)
    return codes


def reader_void(reason, error=None):
    """A PRINTED reading whose label is VOID, for any failure the reader cannot turn into a gate code (FIX 3).

    A malformed study file used to reach `json.loads` outside any `try`: the program exited 1, printed nothing on
    stdout and raised `json.decoder.JSONDecodeError`. The reader's whole job is to print a reading, so an
    unexpected error becomes one: `label = VOID`, `rule = READER:<reason>`, the same string in
    `void_paths_taken`, and the error's own type, message and innermost frame kept in `reader_failure` for the
    record. Never a bare traceback, never a silent empty stdout.
    """
    code = 'READER:' + reason
    return {
        'schema': SCHEMA, 'protocol': PROTOCOL, 'alpha': str(ALPHA),
        'min_improved_kinds': MIN_IMPROVED_KINDS, 'min_improved_worlds': MIN_IMPROVED_WORLDS,
        'min_passing_b': MIN_PASSING_B_REDERIVED, 'min_passing_b_rederived': MIN_PASSING_B_REDERIVED,
        'label': 'VOID', 'label_rule': code, 'label_tier': None, 'label_key_test': PRIMARY_TEST,
        'label_key_population': [], 'label_key_kinds': [],
        'label_key_population_source': 'READING_NOT_COMPLETED',
        'label_key_population_derived_by_primary_keys': [],
        'label_key_population_agrees_with_primary_keys': False,
        'label_vocabulary': list(LABELS),
        'label_precedence': ['1. the reading could not be completed, so no label can be claimed'],
        'flags': {}, 'seeds': {},
        'gates': {'integrity': {'pass': False, 'failures': [code]}},
        'reader_failure': {'rule': code, 'reason': reason,
                           'type': (type(error).__name__ if error is not None else None),
                           'detail': (str(error)[:400] if error is not None else None),
                           'where': _innermost_frame(error)},
        'void_paths': [{'code': path, 'meaning': meaning} for path, meaning in VOID_PATHS],
        'void_paths_taken': [code],
    }


def _innermost_frame(error):
    """The function name of the innermost traceback frame, for a diagnostic that is not a traceback."""
    if error is None:
        return None
    import traceback
    frames = traceback.extract_tb(error.__traceback__)
    return frames[-1].name if frames else None


def _reader_reason(error):
    """A short, stable `READER:<reason>` token: the error type plus its message, cut and de-spaced."""
    text = re.sub(r'[^0-9A-Za-z]+', '_', str(error)).strip('_')
    return '%s:%s' % (type(error).__name__, text[:80]) if text else type(error).__name__


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
    required_count = getattr(worker, 'EVIDENCE_REQUIRED_COUNT', None)
    if (not all(type(name) is str and name for name in names) or len(set(names)) != len(names)
            or len(names) >= 500
            or not any(name.endswith('worker_report.json') for name in names)
            or not any(name.endswith('measurements.json') for name in names)
            or (required_count is not None and required_count != len(names) + 3)):
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
    """(record, source) for the job's in-job DG4 identity evidence; (None, None) when the job recorded none.

    The artifact `model_identity.json` is tried FIRST because only it carries the identity values; the summary the
    worker mirrors into `worker_report.json["model_identity"]` carries four booleans and would fail closed on the
    missing identities, which is the correct outcome for a job whose DG4 artifact is absent.
    """
    for name in DG4_ARTIFACT_NAMES:
        path = artifacts / name
        if path.is_file():
            value = _read_json(path)
            if isinstance(value, dict):
                return value, name
    for key in DG4_REPORT_KEYS:
        value = report.get(key)
        if isinstance(value, dict):
            return value, 'worker_report.json:' + key
    return None, None


def dg4_failures(seed, record, target, seeds):
    """The four DG4 checks of protocol section 7.1, as the job recorded them, with every comparison re-derived.

    (a) the three `^6` tensors of the first build equal the practice start for this seed
    (b) a second independent build of the whole model gives the same identity as the first
    (c) the three seeds' `^6` identities are pairwise different
    (d) the start is identical with the checkpoint check on and off
    The reader does not believe the job's booleans: it re-derives each one from the identity values in the same
    record, re-derives the target from the PINNED practice receipt, and requires the whole-container identity to be
    a DIFFERENT number from the three-tensor identity, because a check that compares a job to itself proves nothing
    (V3). `DG4_FLAG:*` is raised when a recorded boolean disagrees with the reader's own derivation or is not true.
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
    for flag in DG4_FLAGS:
        if record.get(flag) is not True:
            codes.append('I3:%d:DG4_FLAG:%s' % (seed, flag))
    if len(values) != len(DG4_FIELDS):
        return codes
    if values['practice_recorded_model_state_identity'] != target:
        codes.append('I3:%d:DG4_START_TARGET' % seed)
    if values['core_identity'] != target:
        codes.append('I3:%d:DG4_SIX_IDENTITY' % seed)
    if values['second_independent_whole_build_identity'] != values['whole_container_identity']:
        codes.append('I3:%d:DG4_DOUBLE_BUILD' % seed)
    if values['whole_container_identity'] == values['core_identity']:
        codes.append('I3:%d:DG4_NOT_DISTINCT_FORM' % seed)
    recorded = record.get('seed_core_identities')
    expected_seeds = sorted(str(value) for value in seeds)
    if (type(recorded) is not dict or sorted(recorded) != expected_seeds
            or not all(_is_digest(value) for value in recorded.values())
            or len(set(recorded.values())) != len(recorded)
            or recorded.get(str(seed)) != values['core_identity']):
        codes.append('I3:%d:DG4_SEED_IDENTITIES' % seed)
    if (record.get('identical_start_with_and_without_the_checkpoint_check') is not True
            or values['core_identity'] != values['practice_recorded_model_state_identity']):
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
    """The reading for one study file. A reading is ALWAYS printed: never a bare traceback, never empty stdout.

    FIX 3 (R1). Two things sat outside any `try` and turned a malformed study file into `exit 1` with a
    `JSONDecodeError` traceback and nothing on stdout: the material load and `pointer_schedule` just after the
    contract import, and `admissible_answers` in the per-seed loop. Both are inside the reading path now, and the
    body after the contract import is wrapped here as well, because a reader whose whole job is to print a
    deterministic status must print VOID rather than die. The label vocabulary is unchanged: a `READER:` reading
    is `VOID`, one of the three words, and it can only ever WITHHOLD a label, never manufacture one.
    """
    try:
        from cas_meta2.typed_teaching import pointer_contract as contract
    except Exception as error:  # the contract is the reader's own dependency; a broken import is still a reading
        return reader_void('CONTRACT_IMPORT:%s' % type(error).__name__, error)
    try:
        return _evaluate(study_path, contract)
    except Exception as error:  # noqa: BLE001 - the reader must print a status, not a traceback
        return reader_void(_reader_reason(error), error)


def _evaluate(study_path, contract):
    """The reading, with the contract already imported. Every unexpected error here becomes a VOID reading."""
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

    # ---- THE LABEL'S KEY SET, in exactly one place (R1, FIX 1) --------------------------------------------
    # `primary_keys` is the only expression in this program that NAMES the label's unit of evidence, the primary
    # test below runs over exactly this list, and the list is echoed into the reading as `label_key_population`
    # so R1's P12 can assert on it. `eligible_all` is passed in only as the OUTER BOUNDARY, so nothing wider than
    # the derived population can ever be returned. `label_key_divergence_failures` then makes that a checked
    # invariant rather than a convention: if the test the label is keyed on ran over anything else, the reading is
    # VOID and the label cannot be earned.
    label_keys = primary_keys(contract, population, eligible_all, kind_of)

    # ---- the zero-learning floors INSIDE the label's population: reported, never subtracted (R1, FIX 4/FIX 5) -
    # The ceiling numerators in `ORACLE_CEILINGS` count ELIGIBLE questions; four of those eleven are already
    # removed from the population by a shortcut rule, so the number a zero-learning rule actually solves inside
    # the frozen 18 is smaller and is what the label must be read beside. The rank-last rule is worse: the
    # contract's own comment says the questions it solves "are removed instead", and they are NOT - all five
    # remain in the 18.
    population_id_set = set(population['question_ids']) if population else set()
    oracle_solved = sorted(population_id_set & set(ORACLE_ONE_HOP_SOLVED_IDS))
    rank_solved = sorted(population_id_set & set(RANK_LAST_SOLVED_IDS))

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
        report, manifest_names, schedule = {}, [], None
        try:  # I1 -- completion and evidence, against the POINTER worker's own constants
            lifecycle = _read_json(receipt / 'result.json')
            report = _read_json(art / 'worker_report.json')
            manifest_names = [row['name'] for row in _read_json(art / 'manifest.json')['artifacts']]
            schedule = _read_json(art / 'schedule_plan.json')
            # The worker's own rule (`deliver`, the `required` local): the required set is the one the run
            # RECORDED, falling back to the registered constant. A reduced run records a shorter set, and is
            # refused below. FIX 6 then refuses a CLAIM-BEARING run that recorded a shorter set than the
            # registered one, which is what `_effective_required` writes when a report-only check failed.
            required = report.get('required_artifacts')
            required = tuple(required) if isinstance(required, list) else tuple(getattr(worker, 'EXPECTED_ARTIFACTS',
                                                                                        ()))
            if worker is None:
                pass  # the named code was already raised once, before any seed was read
            elif not (lifecycle.get('completed_deliverable') is True
                      and lifecycle.get('cleanup', {}).get('complete') is True
                      and report.get('status') == worker.SUCCESS_STATUS
                      and set(required) <= set(manifest_names)):
                failures.append('I1:%d' % seed)
            failures.extend(registered_required_failures(seed, report, worker, required))
            # A non-claim-bearing run may never print a label (`schedule_plan`, `run`): the reduced schedule is
            # the smoke path, and it is marked as such by the job itself.
            if not (report.get('claim_bearing') is True and report.get('schedule_plan_mode') == 'REGISTERED'):
                failures.append('I1:%d:REDUCED_SCHEDULE:%s' % (seed, report.get('schedule_plan_mode')))
            # ... and the refusal does not rest on the report's own self-description: the sealed plan is read
            # too, and a plan that does not say REGISTERED with no reduced request is itself a refusal (R1-9).
            failures.extend(schedule_plan_failures(seed, report, schedule))
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
        record, source = None, None
        try:  # I3 -- the in-job DG4 identity checks (the corrected form of protocol section 7.1)
            record, source = dg4_record(art, report)
            if record is None:
                failures.append('I3:%d:DG4_RECORD_MISSING' % seed)
            else:
                failures.extend(dg4_failures(seed, record, start_targets.get(seed), seed_order))
                # The phase-A custody ordering is EVIDENCE THE JOB ASSERTS, so the reader measures it (FIX 2):
                # required COMPLETE in the record AND corroborated by the artifact the job sealed.
                failures.extend(phase_a_failures(seed, record, art, start_targets.get(seed)))
                if _is_digest(record.get('core_identity')):
                    six_identities[seed] = record['core_identity']
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
            failures.extend('I1:%d:%s' % (seed, code) for code in scoring_problems)
            if not at:
                failures.append('I1:%d:SCORING_PHASES_MISSING' % seed)
                continue
            checkpoints = sorted(at)
            start, final = checkpoints[0], checkpoints[-1]
            full = [n for n in checkpoints if set(at[n]) >= set(trained)]
            first = min([n for n in full if n > start], default=None)
            needed = sorted({record_id for records in held_questions.values() for record_id in records})
            incomplete = [n for n in (start, final) if not set(at[n]) >= set(needed)]
            for n in incomplete:
                failures.append('I1:%d:SCORING_INCOMPLETE:%d' % (seed, n))
            if incomplete:
                continue
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append('I1:%d:SCORING:%s' % (seed, type(error).__name__))
            continue
        # Every question-set expression below reads `label_keys` for the label's own unit of evidence: there is no
        # second copy of the key choice to drift from it. The all-kinds set and the per-tier sets are REPORTED.
        tier_ids = {tier: sorted(q for q in eligible_all if tier_of[kind_of[q]] == tier) for tier in contract.TIERS}
        heldq = {n: question_outcomes(at[n], held_questions) for n in checkpoints}
        trainq = {n: question_outcomes(at[n], trained_questions) for n in full}
        correspondence_ids = sorted(q for q in eligible_all if kind_of[q] == CORRESPONDENCE_KIND)
        correspondence_scored = sorted(q for q in correspondence_ids if q in heldq[start] and q in heldq[final])
        gained = []
        for key in label_keys:
            if not heldq[start][key] and heldq[final][key]:
                gained.append({'query_id': key, 'kind': kind_of[key], 'world': world_of[key],
                               'records': len(held_questions[key]),
                               'admissible_answers': len(admissible_answers(frozen, by_id[held_questions[key][0]]))})
        primary = seed_test(heldq[start], heldq[final], label_keys, kind_of, world_of)
        failures.extend(label_key_divergence_failures(seed, primary['keys'], label_keys))
        entry = {
            'checkpoints': checkpoints, 'full_course_checkpoints': full,
            'start_checkpoint': start, 'first_checkpoint': first, 'final_checkpoint': final,
            'held_questions_correct': {str(n): sum(heldq[n].values()) for n in checkpoints},
            'population_questions_correct': {str(n): sum(heldq[n][q] for q in label_keys) for n in checkpoints},
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
            'MORE_PRACTICE_population': (seed_test(heldq[first], heldq[final], label_keys, kind_of, world_of)
                                         if first is not None else {'evaluated': False}),
            ALL_KINDS_TEST: seed_test(heldq[start], heldq[final], eligible_all, kind_of, world_of),
            'TRAINED_start_to_final': (seed_test(trainq[start], trainq[final], sorted(trained_questions), kind_of)
                                       if start in trainq and final in trainq else {'evaluated': False}),
            'TRAINED_first_to_final': (seed_test(trainq[first], trainq[final], sorted(trained_questions), kind_of)
                                       if first is not None and first in trainq and final in trainq
                                       else {'evaluated': False}),
            'gained_questions': gained, 'gained_single_record': sum(1 for row in gained if row['records'] == 1),
            'dg4_source': None, 'dg4_extra_fields': [], 'dg4_phase_a_status': None,
            'dg4_whole_container_identity': None, 'schedule_plan_mode': report.get('schedule_plan_mode'),
            'claim_bearing': report.get('claim_bearing'),
            'development': report.get('development_scores'), 'retention': report.get('retention_scores'),
            'pass_summaries': report.get('pass_summaries'),
            # R1-8: `correspondence` must be shown to have been RUN AND REPORTED, not asserted to have been.
            'correspondence_questions_eligible': len(correspondence_ids),
            'correspondence_questions_scored': correspondence_scored,
            'label_key_population_size': len(label_keys),
        }
        for tier, keys in sorted(tier_ids.items()):
            entry['G_LEARN_' + tier] = (primary if tier == 'RELATIONAL'
                                        else seed_test(heldq[start], heldq[final], keys, kind_of, world_of))
        for kind in contract.KINDS:
            keys = sorted(q for q in eligible_all if kind_of[q] == kind)
            entry['G_LEARN_kind_' + kind] = seed_test(heldq[start], heldq[final], keys, kind_of, world_of)
        # The evidence echo: which record I3 read, and the report-only fields around it.
        entry['dg4_source'] = source
        entry['dg4_extra_fields'] = sorted(set(record) & set(DG4_OPTIONAL_FIELDS)) if record else []
        entry['dg4_phase_a_status'] = (record or {}).get('phase_a_status')
        entry['dg4_whole_container_identity'] = (record or {}).get('whole_container_identity')
        seeds[seed] = entry

    if len(six_identities) == len(seed_order) and len(set(six_identities.values())) != len(six_identities):
        failures.append('I3:SEEDS_NOT_PAIRWISE_DIFFERENT')

    # ---- THE LABEL'S KEY SET AS MEASURED FROM THE TEST THAT SET THE LABEL (R1, FIX 1) ---------------------
    # `label_keys` is what `primary_keys` DERIVED; this is the set the primary test each seed actually RAN ON,
    # read back out of the test dicts. Both are reported, so the two cannot silently diverge: a substitution at
    # the call site moves the measured set even when it leaves the derived one untouched, which is exactly the
    # mutation that used to leave the suite green.
    measured_key_sets = [list(entry[PRIMARY_TEST]['keys']) for entry in seeds.values()
                         if isinstance(entry.get(PRIMARY_TEST), dict) and 'keys' in entry[PRIMARY_TEST]]
    label_key_population = list(measured_key_sets[0]) if measured_key_sets else list(label_keys)
    label_key_kinds = sorted({kind_of[question] for question in label_key_population if question in kind_of})
    label_key_population_agrees = bool(measured_key_sets) and all(
        keys == list(label_keys) for keys in measured_key_sets)

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
        # THE LABEL'S KEY SET, echoed so that which questions the label is keyed on is a MEASURED number in the
        # reading and not an inference from the prose (R1, FIX 1 / P12). `label_key_population` is read back out of
        # the primary test each seed ran; `..._derived_by_primary_keys` is what the derivation returned.
        'label_key_population': label_key_population,
        'label_key_population_size': len(label_key_population),
        'label_key_population_source': ('PRIMARY_TEST_KEYS_AS_RUN' if measured_key_sets
                                        else 'PRIMARY_KEYS_NO_SEED_REACHED_THE_PRIMARY_TEST'),
        'label_key_population_derived_by_primary_keys': label_keys,
        'label_key_population_agrees_with_primary_keys': label_key_population_agrees,
        'label_key_kinds': label_key_kinds,
        'label_key_tiers_disjoint_from': {tier: sorted(set(label_key_kinds) & set(contract.TIERS[tier]))
                                          for tier in contract.TIERS if tier != contract.DESIGN.get(
                                              'primary_label_tier')},
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
            # FIX 4 (R1). The numerators above count ELIGIBLE questions and four of them are already removed
            # from the label's population by a shortcut rule, so the number the one-hop rule actually solves
            # inside the frozen 18 is smaller, and it is the number a ZERO-LEARNING rule already achieves on the
            # questions the label is keyed on. PRINTED BESIDE THE LABEL, REPORTING ONLY: no threshold, no
            # population and no gate reads these values, and `MIN_PASSING_B` stays 7.
            'population_ids_the_rule_solves': oracle_solved,
            'oracle_solvable_in_the_label_population': len(oracle_solved),
            'oracle_solvable_breakdown': solved_breakdown(oracle_solved, kind_of, world_of),
            'oracle_solvable_eligible_not_in_the_label_population': len(set(ORACLE_ONE_HOP_SOLVED_IDS)
                                                                        - population_id_set),
            # FIX 5 (R1). The contract's own comment says the rank-solvable questions "are removed instead",
            # and `DESIGN["node_rank_decision_status"]` records the same claim. They are NOT removed: all five
            # remain in the frozen 18. The contract file belongs to another agent, so this reader shows the
            # measurement instead of repeating the claim.
            'rank_last_ids_the_rule_solves': rank_solved,
            'rank_last_solvable_in_the_label_population': len(rank_solved),
            'rank_last_solvable_breakdown': solved_breakdown(rank_solved, kind_of, world_of),
            'rank_last_solvable_contract_claim': ('REMOVED_INSTEAD_OF_ADOPTED' if contract.REMOVALS else None),
            'node_rank_decision_status': contract.DESIGN.get('node_rank_decision_status'),
            'node_rank_feature': contract.DESIGN.get('node_rank_feature'),
            'oracle_or_rank_solvable_in_the_label_population': len(set(oracle_solved) | set(rank_solved)),
            'label_population': (population['total'] if population else 0),
            'floor_note': ("a zero-learning rule already answers these questions of the label's own population; "
                           "they are REPORTED and NOT subtracted, so the label must be read beside them"),
        },
        'correspondence': {
            'declared_false_negative': bool(population['removed_by_rule'].get('inexpressible', {})
                                            .get(CORRESPONDENCE_KIND)) if population else False,
            'removal_class': ('inexpressible' if 'inexpressible' in contract.REMOVAL_RULES else None),
            'in_label_population': bool(population and population['by_kind'].get(CORRESPONDENCE_KIND, 0)),
            # R1-8: `correspondence` must be shown to have been RUN AND REPORTED, not asserted to have been.
            'still_run_and_reported': correspondence_run_and_reported(seeds),
            'still_run_and_reported_by_seed': {
                str(seed): {'eligible': seed_entry['correspondence_questions_eligible'],
                            'scored': len(seed_entry['correspondence_questions_scored'])}
                for seed, seed_entry in seeds.items()},
            'eligible_questions': eligible_by_kind.get(CORRESPONDENCE_KIND, 0),
            'population_questions': (population['by_kind'].get(CORRESPONDENCE_KIND, 0) if population else 0),
            'removed_questions': (population['removed_by_rule']['inexpressible'].get(CORRESPONDENCE_KIND, [])
                                  if population else []),
            'g_learn': gates['kind_g_learn'].get(CORRESPONDENCE_KIND) if complete else None,
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


# ==================================================================================================================
# R1's P12: the synthetic study `--self-test` drives `evaluate()` with. Everything lives under `%TEMP%`; no
# receipt, no torch, no network and no GPU is touched, and every value is derived from the FROZEN material and
# from the pinned practice starts this reader already reads. The fixture is designed so that the ALL-KINDS gate
# PASSES while the RELATIONAL population test FAILS - the flag-copy-only outcome of finding FP1 - which is the one
# arrangement in which a label keyed on the WRONG question set prints LEARNS_NEW_WORLDS and a label keyed on the
# right one prints NO_TRANSFER_TO_NEW_WORLDS. Without it, the label path was never driven and the battery that
# mutated it stayed green (R1, FIX 1 / BLOCKER 1).
# ==================================================================================================================
P12_SCORING_NAMES = ('course_p00_scoring.json', 'course_p10_scoring.json')


class SelftestWorkerStub:
    """The three names this reader takes off a worker, so P12 can be driven without the REAL worker module.

    `worker_module()` is replaced for the duration of the drive, which keeps this suite green whatever state the
    real worker is in while it is being edited - and the real worker's own artifact contract has its own checks
    above. The stub's `EXPECTED_ARTIFACTS` is exactly the artifact set the fixture writes, so the FIX 6 comparison
    (`required_artifacts == EXPECTED_ARTIFACTS`) is exercised rather than bypassed.
    """

    def __init__(self, names):
        self.SUCCESS_STATUS = 'COMPLETE_TYPED_POINTER_ARM'
        self.EXPECTED_ARTIFACTS = tuple(names)
        self.EVIDENCE_REQUIRED_COUNT = len(self.EXPECTED_ARTIFACTS) + 3


def _write_json(path, value):
    Path(path).write_bytes(json.dumps(value, sort_keys=True).encode('utf-8'))


def _phase_a_bad_dir(name, body):
    """A fresh directory holding ONE phase-A artifact, for the phase-A refusal checks of FIX 2."""
    directory = Path(tempfile.mkdtemp(prefix='cncm_pointer_gate_phase_a_%s_' % name))
    _write_json(directory / DG4_PHASE_A_ARTIFACT_NAMES[0], body)
    return directory


def p12_fixture(contract):
    """Write the synthetic three-seed receipt set of R1's P12. Returns `(study_path, stub, facts)`.

    The learning outcome is the FP1 flag-copy: every one of the ten held DIRECT_READ questions (`definition` 5 +
    `context` 5, two kinds over five held worlds) moves False -> True between the first and the last scored
    checkpoint, and NO other held question moves at all. The integrity chain is COMPLETE - every I1-I4 condition
    the reader checks is satisfied by construction, including the DG4 identity fields, which carry the PINNED
    practice starts because that is the only value I3 accepts - so the label is `NO_TRANSFER_TO_NEW_WORLDS` rather
    than `VOID`, and a mutant label path is visible in the label itself.
    """
    frozen, _, _ = contract.load_material(ROOT)
    held, trained, excluded = contract.split(frozen)
    _, stats = contract.pointer_schedule(frozen)
    held_questions = contract.held_back_questions(frozen)
    kind_of = {row['query']['query_id']: row['query']['kind'] for row in frozen['registry']}
    targets = {seed: practice_start(contract, seed)[0] for seed in contract.MODEL_SEEDS}
    copied = {question for question in held_questions if kind_of[question] in contract.DIRECT_READ}
    correspondence = {question for question in held_questions if kind_of[question] == CORRESPONDENCE_KIND}
    after = {row['record_id']: (row['query']['query_id'] in copied) for row in frozen['registry']}

    base = Path(tempfile.mkdtemp(prefix='cncm_pointer_gate_p12_'))
    names = ['pass_%02d_batches.jsonl' % number for number in range(1, stats['passes'] + 1)]
    names += ['interference_batches.jsonl'] + list(P12_SCORING_NAMES)
    names += ['initial_reload_predictions.json', 'final_reload_predictions.json', 'retained_reload_predictions.json']
    names += ['replay_1_predictions.json', 'replay_2_predictions.json']
    names += ['model_identity.json', DG4_PHASE_A_ARTIFACT_NAMES[0], 'schedule_plan.json',
              'protocol_material.json', 'replay_report.json', 'worker_report.json', 'measurements.json']
    stub = SelftestWorkerStub(names)

    for seed in contract.MODEL_SEEDS:
        receipt = base / ('receipt_%d' % seed)
        art = receipt / 'collected/results/artifacts'
        art.mkdir(parents=True)
        _write_json(receipt / 'result.json', {'completed_deliverable': True, 'cleanup': {'complete': True}})
        _write_json(art / 'manifest.json', {'artifacts': [{'name': name} for name in names]})
        _write_json(art / 'worker_report.json', {
            'schema': 'cncm.typed-pointer-worker-report/0.1', 'status': stub.SUCCESS_STATUS,
            'claim_bearing': True, 'schedule_plan_mode': 'REGISTERED', 'required_artifacts': list(names),
            'main_training_delta': {'optimizer_updates': stats['main_updates']},
            'interference_delta': {'optimizer_updates': contract.INTERFERENCE_UPDATES},
            'global_actual_work': {'totals': {'optimizer_updates': stats['main_updates']
                                              + contract.INTERFERENCE_UPDATES + contract.REPLAY_UPDATES}},
            'development_scores': [], 'retention_scores': None, 'pass_summaries': []})
        _write_json(art / 'schedule_plan.json', {
            'schema': 'cncm.typed-pointer-schedule-plan/0.1', 'claim_bearing': True, 'mode': 'REGISTERED',
            'reduced_schedule_requested': False, 'required_artifacts': list(names),
            'registered_required_artifacts': list(names)})
        _write_json(art / 'measurements.json', {'schema': 'cncm.typed-pointer-measurements/0.1'})
        _write_json(art / 'protocol_material.json', {'held_back_record_ids': list(held),
                                                     'excluded_record_ids': list(excluded)})
        _write_json(art / 'replay_report.json', {'replays': list(range(contract.REPLAY_UPDATES)),
                                                'reloads': ['initial', 'final', 'retained']})
        whole = sha256(('whole-container-%d' % seed).encode('ascii')).hexdigest()
        _write_json(art / 'model_identity.json', {
            'schema': 'cncm.typed-pointer-model-identity/0.1', 'model_seed': seed,
            'identity_form': DG4_IDENTITY_FORM, 'core_identity': targets[seed],
            'whole_container_identity': whole, 'second_independent_whole_build_identity': whole,
            'practice_recorded_model_state_identity': targets[seed],
            'core_identity_equals_the_practice_start': targets[seed] is not None,
            'whole_container_form_is_a_different_number': whole != targets[seed],
            'double_build_equal': True,
            'seed_core_identities': {str(other): targets[other] for other in contract.MODEL_SEEDS},
            'seeds_pairwise_different': True,
            'identical_start_with_and_without_the_checkpoint_check': True,
            'phase_a_finished_before_the_model_was_seeded': True,
            'phase_a_status': PHASE_A_COMPLETE,
            'comparison_method': 'P12 fixture: the values are the PINNED practice starts for the three seeds'})
        _write_json(art / DG4_PHASE_A_ARTIFACT_NAMES[0], {
            'schema': 'cncm.typed-pointer-post-block-vectors/0.1', 'seed': seed, 'status': PHASE_A_COMPLETE,
            'report_only': True,
            'checkpoints': {'initial': {'practice_recorded_model_state_identity': targets[seed],
                                        'three_key_form_equals_the_practices_own_identity': True, 'exact': True}}})
        for name in names:
            if name.endswith('_batches.jsonl') and name != 'interference_batches.jsonl':
                lines = b'{"predictions": []}\n' * stats['updates_per_pass']
            elif name == 'interference_batches.jsonl':
                lines = b'{"predictions": []}\n' * contract.INTERFERENCE_UPDATES
            else:
                continue
            (art / name).write_bytes(lines)
        rows = [{'record_id': row['record_id'], 'correct': bool(after[row['record_id']])}
                for row in frozen['registry']]
        _write_json(art / P12_SCORING_NAMES[0], {'rows': [dict(row, correct=False) for row in rows]})
        _write_json(art / P12_SCORING_NAMES[-1], {'rows': rows})

    study_path = base / 'study.json'
    _write_json(study_path, {'jobs': [{'model_seed': seed, 'receipt_dir': str(base / ('receipt_%d' % seed))}
                                      for seed in contract.MODEL_SEEDS]})
    return study_path, stub, {'base': str(base), 'targets': targets, 'copied_questions': len(copied),
                              'correspondence_records': sorted(record for row in frozen['registry']
                                                               if row['query']['query_id'] in correspondence
                                                               for record in [row['record_id']]),
                              'passes': stats['passes'], 'held_records': len(held),
                              'trained_records': len(trained)}


def p12_drop_correspondence(facts, contract):
    """Remove every `correspondence` record from the LAST scoring file of every receipt, and report how many.

    This is the second half of R1-8's evidence: the reading is taken AGAIN on the same fixture, with the
    questions the flag is about no longer scored, so the reading's `still_run_and_reported` has to MOVE. A
    hardcoded `True` cannot produce `False` here, which is exactly what made the old field not evidence.
    """
    dropped = set(facts['correspondence_records'])
    for seed in contract.MODEL_SEEDS:
        path = (Path(facts['base']) / ('receipt_%d' % seed) / 'collected/results/artifacts'
                / P12_SCORING_NAMES[-1])
        body = json.loads(path.read_bytes())
        body['rows'] = [row for row in body['rows'] if row['record_id'] not in dropped]
        _write_json(path, body)
    return len(dropped)


def p12_reading(study_path, stub):
    """`evaluate(study_path)` with `worker_module` stubbed. The stub is removed in a `finally`, so it cannot leak."""
    saved = globals()['worker_module']
    globals()['worker_module'] = lambda: (stub, None)
    try:
        return evaluate(study_path)
    finally:
        globals()['worker_module'] = saved


def p12_run(contract):
    """`{reading, unscored_reading, facts, error}` for the P12 drive: a broken fixture FAILS the checks.

    Two readings are taken from the same fixture. The FIRST is the complete one - the flag-copy-only study whose
    label must be `NO_TRANSFER_TO_NEW_WORLDS`. The SECOND is taken after `p12_drop_correspondence` has removed the
    `correspondence` records from the last scoring file, and is what proves the reader's
    `correspondence.still_run_and_reported` is MEASURED: it must come back `False` there and `True` in the first
    reading (R1-8).
    """
    try:
        study_path, stub, facts = p12_fixture(contract)
    except Exception as error:  # noqa: BLE001 - the suite must report this, not die of it
        return {'reading': {}, 'unscored_reading': {}, 'facts': {}, 'dropped': 0,
                'error': '%s: %s' % (type(error).__name__, error)}
    try:
        reading = p12_reading(study_path, stub)
        dropped = p12_drop_correspondence(facts, contract)
        unscored = p12_reading(study_path, stub)
        return {'reading': reading, 'unscored_reading': unscored, 'facts': facts, 'dropped': dropped,
                'error': None}
    except Exception as error:  # `evaluate` returns a VOID reading rather than raising; belt and braces
        return {'reading': {}, 'unscored_reading': {}, 'facts': facts, 'dropped': 0,
                'error': '%s: %s' % (type(error).__name__, error)}


def self_test():
    """The reader's own test of its label decision path: the arithmetic, the label, AND the code that chooses
    which question set the label is keyed on.

    The load-bearing case is the flag-copy-only outcome of finding FP1: a machine that copies the input flags gets
    `b = 10`, `c = 0` on `definition 5 + context 5` over five worlds, `p = 1/1024 = 0.0009765625`, which clears
    the arithmetic, the >= 2 kinds rule and the >= 2 worlds rule. That outcome must receive NO label: the all-kinds
    result is a flag, and the label is keyed on the RELATIONAL population alone.

    `seed_test` and `label_decision` are exercised on synthetic readings below AND `evaluate()` itself is driven
    on the synthetic three-seed receipt set of `p12_fixture`, because a test that only reads the label out of a
    hand-made reading never touches the code that decides WHICH question set the label is keyed on (R1, FIX 1).
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
          DG4_IDENTITY_FORM == 'THREE_^6_TENSORS_ONLY' and len(DG4_FIELDS) == 4
          and 'practice_recorded_model_state_identity' in DG4_FIELDS
          and 'phase_a_finished_before_the_model_was_seeded' in DG4_FLAGS
          and DG4_ARTIFACT_NAMES == ('model_identity.json',) and DG4_REPORT_KEYS == ('model_identity',),
          'I3 reads the artifact %r first, then worker_report.json%r, and requires the identity fields %r with the booleans %r'
          % (list(DG4_ARTIFACT_NAMES), list(DG4_REPORT_KEYS), list(DG4_FIELDS), list(DG4_FLAGS)))
    check('oracle_ceilings_are_not_removals', len(ORACLE_CEILINGS) == 3
          and [numerator for _, _, numerator in ORACLE_CEILINGS] == [5, 5, 1],
          'the one-hop ceilings %r are printed beside the label and subtract nothing'
          % ([numerator for _, _, numerator in ORACLE_CEILINGS],))
    check('zero_learning_floor_ids_are_frozen_and_well_formed',
          len(ORACLE_ONE_HOP_SOLVED_IDS) == 11 and len(set(ORACLE_ONE_HOP_SOLVED_IDS)) == 11
          and len(RANK_LAST_SOLVED_IDS) == 5 and len(set(RANK_LAST_SOLVED_IDS)) == 5
          and all(type(value) is str and value.startswith('typed-query-') for value in ORACLE_ONE_HOP_SOLVED_IDS)
          and all(type(value) is str and value.startswith('typed-query-') for value in RANK_LAST_SOLVED_IDS),
          'the oracle one-hop rule answers %d frozen ids and the rank-last rule %d; the intersections with the '
          'label population are computed in `_evaluate`, not restated'
          % (len(ORACLE_ONE_HOP_SOLVED_IDS), len(RANK_LAST_SOLVED_IDS)))

    # ---- the I3 record logic, on synthetic DG4 records: the four checks of protocol section 7.1 -------------
    seeds = tuple(contract.MODEL_SEEDS)
    target = 'a' * 64
    other = {str(seed): '%064x' % (index + 1) for index, seed in enumerate(seeds)}
    other[str(seeds[0])] = target
    good = {'identity_form': DG4_IDENTITY_FORM, 'core_identity': target,
            'whole_container_identity': 'b' * 64, 'second_independent_whole_build_identity': 'b' * 64,
            'practice_recorded_model_state_identity': target, 'seed_core_identities': dict(other),
            'core_identity_equals_the_practice_start': True, 'double_build_equal': True,
            'seeds_pairwise_different': True, 'identical_start_with_and_without_the_checkpoint_check': True,
            'whole_container_form_is_a_different_number': True,
            'phase_a_finished_before_the_model_was_seeded': True}
    check('dg4_good_record_passes', dg4_failures(seeds[0], good, target, seeds) == [],
          'a well-formed DG4 record raises no I3 code')
    wrong_identity = dict(good, core_identity='c' * 64)
    check('dg4_wrong_start_is_caught', dg4_failures(seeds[0], good, 'd' * 64, seeds) != []
          and any('DG4_SIX_IDENTITY' in code for code in dg4_failures(seeds[0], wrong_identity, target, seeds))
          and any('DG4_START_TARGET' in code for code in dg4_failures(seeds[0], good, 'd' * 64, seeds)),
          'a ^6 identity that is not the pinned practice start, and a record naming a different target, both fail')
    check('dg4_second_build_and_pairwise_and_check_off_are_caught',
          any('DG4_DOUBLE_BUILD' in code for code in dg4_failures(
              seeds[0], dict(good, second_independent_whole_build_identity='e' * 64), target, seeds))
          and any('DG4_FLAG:seeds_pairwise_different' in code for code in dg4_failures(
              seeds[0], dict(good, seeds_pairwise_different=False), target, seeds))
          and any('DG4_SEED_IDENTITIES' in code for code in dg4_failures(
              seeds[0], dict(good, seed_core_identities={str(seeds[0]): target, str(seeds[1]): target,
                                                         str(seeds[2]): 'f' * 64}), target, seeds))
          and any('DG4_CHECK_INDEPENDENT_START' in code for code in dg4_failures(
              seeds[0], dict(good, identical_start_with_and_without_the_checkpoint_check=False), target, seeds)),
          'the second build, the three-seed difference map and the with/without-check equality each raise their own '
          'code; R1-2: the last of those three is a KNOWN TAUTOLOGY against DG4_SIX_IDENTITY, kept only so a job '
          'that drops the flag fails closed, and the checks in that record that CAN vary independently are '
          'DG4_DOUBLE_BUILD, DG4_SEED_IDENTITIES and DG4_NOT_DISTINCT_FORM')
    check('dg4_whole_container_form_must_be_a_different_number',
          any('DG4_NOT_DISTINCT_FORM' in code for code in dg4_failures(
              seeds[0], dict(good, whole_container_identity=target), target, seeds)),
          'a container identity equal to the three-tensor identity is the vacuous self-comparison V3 warns about')
    check('dg4_missing_evidence_fails_closed',
          dg4_record(Path('__reader_selftest_no_such_dir__'), {}) == (None, None)
          and dg4_record(Path('__reader_selftest_no_such_dir__'), {'model_identity': 'not a dict'}) == (None, None)
          and any(code == 'I3:<seed>:DG4_RECORD_MISSING' for code, _ in VOID_PATHS),
          'no record at any accepted location -> I3:<seed>:DG4_RECORD_MISSING, never a crash and never a pass')

    # ---- FIX 2: the phase-A custody ordering, which used to be a literal no reader branch could fail on -------
    phase_a_dir = Path(tempfile.mkdtemp(prefix='cncm_pointer_gate_phase_a_'))
    complete_record = dict(good, phase_a_status=PHASE_A_COMPLETE,
                           phase_a_finished_before_the_model_was_seeded=True)
    _write_json(phase_a_dir / DG4_PHASE_A_ARTIFACT_NAMES[0],
                {'status': PHASE_A_COMPLETE, 'checkpoints': {'initial': {
                    'practice_recorded_model_state_identity': target}}})
    check('phase_a_complete_record_and_sealed_artifact_are_accepted',
          phase_a_failures(seeds[0], complete_record, phase_a_dir, target) == []
          and phase_a_failures(seeds[0], complete_record, Path('__reader_selftest_no_such_dir__'), target)
          != [],
          'COMPLETE in the record and in the artifact -> no code; the same record with no artifact -> a code')
    check('phase_a_failed_status_fails_closed_where_it_used_to_pass',
          any('PHASE_A_NOT_COMPLETE:FAILED' in code for code in phase_a_failures(
              seeds[0], dict(complete_record, phase_a_status='FAILED'), phase_a_dir, target))
          and any('PHASE_A_NOT_COMPLETE:MISSING' in code for code in phase_a_failures(
              seeds[0], {key: value for key, value in complete_record.items() if key != 'phase_a_status'},
              phase_a_dir, target))
          and any('PHASE_A_NOT_COMPLETE:MISSING' in code for code in phase_a_failures(
              seeds[0], {'phase_a_finished_before_the_model_was_seeded': True}, phase_a_dir, target)),
          'a FAILED phase A, a record with no phase_a_status at all, and the OLD report-only literal shape each '
          'raise a code: the ordering is never accepted on the record\'s own word')
    check('phase_a_artifact_that_disagrees_fails_closed',
          any('PHASE_A_ARTIFACT:STATUS' in code for code in phase_a_failures(
              seeds[0], complete_record,
              _phase_a_bad_dir('status', {'status': 'FAILED'}), target))
          and any('PHASE_A_ARTIFACT:START_TARGET' in code for code in phase_a_failures(
              seeds[0], complete_record,
              _phase_a_bad_dir('start', {'status': PHASE_A_COMPLETE, 'checkpoints': {'initial': {
                  'practice_recorded_model_state_identity': 'f' * 64}}}), target)),
          'an artifact that is not COMPLETE, and one recording a start that is not the pinned one, each raise a code')
    check('dg4_flags_now_require_the_phase_a_ordering_boolean',
          any('DG4_FLAG:phase_a_finished_before_the_model_was_seeded' in code for code in dg4_failures(
              seeds[0], {key: value for key, value in complete_record.items()
                         if key != 'phase_a_finished_before_the_model_was_seeded'}, target, seeds))
          and 'phase_a_finished_before_the_model_was_seeded' not in DG4_OPTIONAL_FIELDS,
          'an absent ordering boolean fails closed as a DG4 flag, and it is no longer a report-only field')

    # ---- FIX 6 and R1-9: the two artifact-contract refusals, on synthetic reports ---------------------------
    stub = SelftestWorkerStub(('worker_report.json', 'measurements.json'))
    registered = tuple(stub.EXPECTED_ARTIFACTS)
    shrunken = registered[:-1]
    check('fix6_claim_bearing_run_must_record_the_registered_artifact_set',
          registered_required_failures(1, {'claim_bearing': True, 'schedule_plan_mode': 'REGISTERED'},
                                       stub, registered) == []
          and any('REQUIRED_ARTIFACTS' in code for code in registered_required_failures(
              1, {'claim_bearing': True, 'schedule_plan_mode': 'REGISTERED'}, stub, shrunken))
          and registered_required_failures(1, {'claim_bearing': False, 'schedule_plan_mode': 'REDUCED'},
                                           stub, shrunken) == []
          and registered_required_failures(1, {'claim_bearing': True, 'schedule_plan_mode': 'REGISTERED'},
                                           None, shrunken) == [],
          'a REGISTERED claim-bearing run whose recorded set is shorter than EXPECTED_ARTIFACTS is refused; the '
          'reduced case is left alone, and no worker means the earlier named code stands')
    check('r1_9_reduced_refusal_is_cross_checked_against_the_sealed_plan',
          schedule_plan_failures(1, {'claim_bearing': True}, {'claim_bearing': True, 'mode': 'REGISTERED',
                                                              'reduced_schedule_requested': False}) == []
          and any('REDUCED_SCHEDULE' in code for code in schedule_plan_failures(
              1, {'claim_bearing': True}, {'claim_bearing': True, 'mode': 'REGISTERED',
                                           'reduced_schedule_requested': True}))
          and any('REDUCED_SCHEDULE' in code for code in schedule_plan_failures(1, {'claim_bearing': True}, {}))
          and any('REDUCED_SCHEDULE' in code for code in schedule_plan_failures(
              1, {'claim_bearing': True}, {'claim_bearing': True, 'mode': 'REDUCED'}))
          and schedule_plan_failures(1, {'claim_bearing': False}, None) == [],
          'a sealed plan that requests a reduced schedule, an unreadable plan, and a plan that is not REGISTERED '
          'each raise a code; a non-claim-bearing report is refused by its own named code instead')

    # ---- FIX 3: a broken reading is a printed VOID reading, never a traceback and never empty stdout ----------
    malformed = Path(tempfile.mkdtemp(prefix='cncm_pointer_gate_malformed_')) / 'study.json'
    malformed.write_bytes(b'{"jobs": [ this is not json\n')
    malformed_reading = evaluate(malformed)
    missing_reading = evaluate(Path('__reader_selftest_no_such_dir__/study.json'))
    check('fix3_malformed_study_prints_a_void_reading_instead_of_a_traceback',
          malformed_reading.get('label') == 'VOID'
          and str(malformed_reading.get('label_rule', '')).startswith('READER:')
          and any(str(code).startswith('READER:') for code, _ in VOID_PATHS)
          and any(code.startswith('READER:') for code in malformed_reading.get('void_paths_taken', []))
          and malformed_reading.get('reader_failure', {}).get('type') == 'JSONDecodeError',
          'label = %r, rule = %r, reader_failure = %r'
          % (malformed_reading.get('label'), malformed_reading.get('label_rule'),
             malformed_reading.get('reader_failure')))
    check('fix3_a_missing_study_is_also_a_reading_and_not_a_traceback',
          missing_reading.get('label') == 'VOID'
          and str(missing_reading.get('label_rule', '')).startswith('READER:')
          and missing_reading.get('reader_failure', {}).get('type') == 'FileNotFoundError',
          'label = %r, rule = %r' % (missing_reading.get('label'), missing_reading.get('label_rule')))
    check('fix3_a_void_reading_keeps_the_three_word_vocabulary',
          malformed_reading.get('label') in LABELS
          and malformed_reading.get('label_vocabulary') == list(LABELS)
          and malformed_reading.get('label') != 'LEARNS_NEW_WORLDS',
          'a reader failure can only ever WITHHOLD a label: label = %r of %r'
          % (malformed_reading.get('label'), list(LABELS)))

    # ---- P12: `evaluate()` itself, on a synthetic COMPLETE three-seed study whose all-kinds gate PASSES -------
    p12 = p12_run(contract)
    reading, facts, p12_error = p12['reading'], p12['facts'], p12['error']
    gates = reading.get('gates', {})
    integrity = gates.get('integrity', {})
    ceilings = reading.get('oracle_ceilings', {})
    population = reading.get('population', None) or {}
    keys = reading.get('label_key_population', None)
    check('p12_fixture_premises_hold',
          p12_error is None
          and all(_is_digest(value) for value in facts.get('targets', {}).values())
          and len(set(facts.get('targets', {}).values())) == len(contract.MODEL_SEEDS)
          and facts.get('copied_questions') == 10,
          'P12 fixture in %r: pinned targets %r, %r flag-copy questions over the held worlds; error = %r'
          % (facts.get('base'), sorted(facts.get('targets', {})), facts.get('copied_questions'), p12_error))
    check('p12_reading_is_complete_so_a_mutated_label_is_visible',
          p12_error is None and integrity.get('pass') is True,
          'integrity failures = %r' % (integrity.get('failures'),))
    check('p12_flag_copy_only_outcome_has_the_ALL_KINDS_gate_PASSING',
          gates.get(ALL_KINDS_TEST, {}).get('pass') is True
          and reading.get('flags', {}).get('all_kinds_g_learn_passes') is True,
          'the all-kinds %s gate passes per seed = %r' % (ALL_KINDS_TEST,
                                                          gates.get(ALL_KINDS_TEST, {}).get('per_seed')))
    check('p12_flag_copy_only_outcome_has_the_RELATIONAL_gate_FAILING',
          gates.get(PRIMARY_TEST, {}).get('pass') is False,
          'the RELATIONAL population test fails per seed = %r' % (gates.get(PRIMARY_TEST, {}).get('per_seed'),))
    check('p12_flag_copy_only_outcome_gets_no_label',
          reading.get('label') == 'NO_TRANSFER_TO_NEW_WORLDS',
          'label = %r (%r) while the all-kinds gate passes and the RELATIONAL population test fails: a mutant '
          'label keyed on the all-kinds result, or on DIRECT_READ, prints LEARNS_NEW_WORLDS here'
          % (reading.get('label'), reading.get('label_rule')))
    check('p12_label_key_set_is_the_relational_population',
          keys is not None and list(keys) == sorted(population.get('question_ids', []))
          and list(keys) == list(reading.get('label_key_population_derived_by_primary_keys') or [])
          and reading.get('label_key_population_agrees_with_primary_keys') is True
          and reading.get('label_key_population_source') == 'PRIMARY_TEST_KEYS_AS_RUN'
          and population.get('total') == contract.VERIFIED_POPULATION
          and len(keys) == len(population.get('question_ids', []))
          and len(keys) != reading.get('eligible_questions')
          and len(keys) != reading.get('eligible_by_tier', {}).get('DIRECT_READ'),
          'the set the label test RAN ON = %d ids, equal to the derived population %r and to what `primary_keys` '
          'returned; the ALL-KINDS eligible set is %r ids and a DIRECT_READ-only key set %r ids, so a swap to '
          'either is caught here - the measured set moves even when the derived one does not'
          % (len(keys or []), population.get('by_kind'), reading.get('eligible_questions'),
             reading.get('eligible_by_tier', {}).get('DIRECT_READ')))
    check('label_key_divergence_guard_can_fire',
          label_key_divergence_failures(1, ['a', 'b'], ['a', 'b']) == []
          and any('DIVERGED' in code for code in label_key_divergence_failures(1, [], ['a', 'b']))
          and any('DIVERGED' in code for code in label_key_divergence_failures(1, ['a', 'b', 'c'], ['a', 'b']))
          and any(code.startswith('LABEL_KEY_SET:') for code, _ in VOID_PATHS),
          'the invariant "the label test ran over exactly the set `primary_keys` derived" is a named VOID path, '
          'and it fires on both a wider and a narrower key set')
    check('p12_label_key_set_is_disjoint_from_DIRECT_READ_and_TEXT',
          set(reading.get('label_key_kinds', None) or []) <= set(contract.RELATIONAL)
          and set(reading.get('label_key_kinds') or []).isdisjoint(set(contract.DIRECT_READ) | set(contract.TEXT))
          and set(reading.get('label_key_kinds') or []) == {kind for kind, count
                                                            in (population.get('by_kind', {}) or {}).items() if count}
          and reading.get('label_key_tiers_disjoint_from', {}).get('DIRECT_READ') == []
          and reading.get('label_key_tiers_disjoint_from', {}).get('TEXT') == [],
          'label_key_kinds = %r of the RELATIONAL tier, disjoint from DIRECT_READ %r and TEXT %r'
          % (reading.get('label_key_kinds'), list(contract.DIRECT_READ), list(contract.TEXT)))
    check('p12_oracle_floor_inside_the_label_population_is_the_measured_seven',
          ceilings.get('oracle_solvable_in_the_label_population') == 7
          and len(ceilings.get('population_ids_the_rule_solves', None) or []) == 7
          and len(ceilings.get('oracle_solvable_breakdown', {}).get('kinds', None) or []) == 2
          and len(ceilings.get('oracle_solvable_breakdown', {}).get('worlds', None) or []) == 5
          and ceilings.get('applied_as_removals') is False
          and set(ceilings.get('population_ids_the_rule_solves', None) or []) <= set(population.get('question_ids', [])),
          'the one-hop rule solves %r of the %r the label is keyed on, the ceiling applies no removal'
          % (ceilings.get('oracle_solvable_in_the_label_population'), ceilings.get('label_population')))
    check('p12_rank_last_floor_inside_the_label_population_is_the_measured_five',
          ceilings.get('rank_last_solvable_in_the_label_population') == 5
          and len(ceilings.get('rank_last_ids_the_rule_solves', None) or []) == 5
          and len(ceilings.get('rank_last_solvable_breakdown', {}).get('kinds', None) or []) == 2
          and len(ceilings.get('rank_last_solvable_breakdown', {}).get('worlds', None) or []) == 2,
          'the rank-last rule solves %r of the label population in kinds %r and worlds %r, though the contract '
          'comment and node_rank_decision_status say those questions were removed instead'
          % (ceilings.get('rank_last_solvable_in_the_label_population'),
             ceilings.get('rank_last_solvable_breakdown', {}).get('kinds'),
             len(ceilings.get('rank_last_solvable_breakdown', {}).get('worlds', None) or [])))
    check('p12_union_of_the_zero_learning_floors_is_eleven_of_eighteen',
          ceilings.get('oracle_or_rank_solvable_in_the_label_population') == 11
          and ceilings.get('label_population') == 18,
          'the oracle and rank-last sets cover %r of the %r-question label population'
          % (ceilings.get('oracle_or_rank_solvable_in_the_label_population'), ceilings.get('label_population')))
    check('correspondence_still_run_and_reported_is_measured_not_a_literal',
          reading.get('correspondence', {}).get('still_run_and_reported') is True
          and reading.get('correspondence', {}).get('in_label_population') is False
          and bool(reading.get('correspondence', {}).get('still_run_and_reported_by_seed'))
          and all(row.get('eligible', 0) > 0 and row.get('scored') == row.get('eligible')
                  for row in reading.get('correspondence', {}).get(
                      'still_run_and_reported_by_seed', {}).values()),
          'per-seed scored/eligible = %r' % (reading.get('correspondence', {})
                                             .get('still_run_and_reported_by_seed'),))
    check('p12_fixture_is_under_temp_and_writes_nothing_in_the_repository',
          bool(facts.get('base'))
          and str(Path(facts.get('base', '')).parent) == str(Path(tempfile.gettempdir()))
          and Path(facts.get('base', '')).name.startswith('cncm_pointer_gate_p12_'),
          'fixture base = %r, temp = %r' % (facts.get('base'), tempfile.gettempdir()))

    check('r1_8_correspondence_still_run_and_reported_can_be_false',
          correspondence_run_and_reported({'1': {'correspondence_questions_eligible': 5,
                                                 'correspondence_questions_scored': [1, 2, 3, 4, 5]}}) is True
          and correspondence_run_and_reported({'1': {'correspondence_questions_eligible': 5,
                                                     'correspondence_questions_scored': [1, 2, 3]}}) is False
          and correspondence_run_and_reported({}) is False,
          'a literal cannot vary; this flag is False when a seed scored fewer correspondence questions than it '
          'has eligible, and False for a reading with no seed at all')
    check('r1_8_the_reading_moves_that_flag_when_correspondence_is_not_scored',
          reading.get('correspondence', {}).get('still_run_and_reported') is True
          and (p12.get('unscored_reading') or {}).get('correspondence', {}).get(
              'still_run_and_reported') is False
          and p12.get('dropped', 0) > 0,
          'the complete fixture reports %r; with %r correspondence records removed from the last scoring file the '
          'same reader reports %r, so the field is measured rather than written'
          % (reading.get('correspondence', {}).get('still_run_and_reported'), p12.get('dropped'),
             (p12.get('unscored_reading') or {}).get('correspondence', {}).get('still_run_and_reported')))
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
    reading = evaluate(sys.argv[1])  # never raises: an unexpected error comes back as a VOID reading (FIX 3)
    try:
        text = json.dumps(reading, indent=1, sort_keys=True)
    except (TypeError, ValueError) as error:  # a reading that cannot be printed is still a printed reading
        text = json.dumps(reader_void('UNSERIALIZABLE_READING:%s' % type(error).__name__, error), indent=1,
                          sort_keys=True)
    print(text)
