"""Re-derive the pointer study's held-back split from its frozen RULES, independently of the contract's constants.

Copied from `records/typed_practice_001/holdout_audit.py` (79 lines, the practice study's own audit). The FOUR
RULES are unchanged and the derivation is unchanged, because the pointer study reuses the frozen split BY IMPORT
(`pointer_contract.split` is `practice_contract.split`, test P1): the hold-out must stay byte-identical to the
practice study's so the two studies are comparable question for question.

    The rules (docs/CNCM_TYPED_POINTER_STUDY_v0.1.md, section 2; identical to the practice study's):
    1. A course world is ELIGIBLE only if no other world in the 64-world bank has the same shape: the same node
       count, the same edge list over node positions (nodes ordered as the learner's N aliases are, by ref), and
       the same declared whole. A look-alike world's answers would transfer by position without learning.
    2. A world's EXPOSURE is every record focused on another world that mentions it anywhere -- in its query,
       arguments, cue, instruction or worked supports -- or whose correct answers name it.
    3. The five eligible worlds with the smallest exposure, ties by world id, are held back.
    4. Every exposure record of a held world is EXCLUDED from training; every record focused on a held world is
       HELD; the rest are TRAINED.

WHAT IS NEW HERE, and why this is not a copy of the practice audit. The contract records FOUR schedule and
holdout digests, on four consecutive lines of `pointer_contract.pointer_schedule`:

    held_back_record_ids_digest   source.digest(held)            the frozen split's HELD records
    excluded_record_ids_digest    source.digest(excluded)        the frozen split's EXCLUDED records
    source_schedule_digest        base_stats["batches_digest"]   the SOURCE schedule -- see below
    batches_digest                source.digest(batches)         THIS study's own stratified schedule

This audit prints all four, and checks THREE of them against fixed values, re-deriving each here as well as
reading the contract's own copy:

    held            668e6ce73c426d1fcf8f2391e1a08d90c045ffb37fba95fc64e2658f5369ab1d
    excluded        b82108e14554a9fe746a7cfcb1e2cb181a99a3019dc39a3596805f10934c2621
    source schedule 1772c0a53933aa92ea7dfb6b2ce53dcd1089cb3634b089427caba3369977d275

THE THIRD IS THE SOURCE SCHEDULE AND IS NOT THIS STUDY'S OWN. `pointer_contract.pointer_schedule` draws its
stratified pass from `matched_contract.schedule(frozen, CONDITION)` and records that base schedule's own
`batches_digest` as `source_schedule_digest` -- the matched MIXED schedule the practice study's passes were built
from, unstratified: 147 updates per pass and 818 presentations per pass. A re-derivation that silently switched
to the stratified order would be caught here, and the name `source_schedule` is the only name this digest may
carry.

THE FOURTH IS THIS STUDY'S OWN SCHEDULE AND IS PRINTED AS A VALUE TO BE RECORDED, NEVER AS A PINNED LITERAL. It
is `source.digest(batches)` for the schedule `pointer_schedule` builds -- the schedule the claim-bearing jobs
will actually run: 147 updates per pass unchanged, 1176 presentations per pass, +43.8 %. It is EXPECTED TO DIFFER
from `source_schedule_digest`, because the owner's "Stratify AND train longer (Recommended)" decision moved this
study from 818 to 1176 presentations per pass while leaving the 147 updates per pass alone; the two are never
asserted equal, and this audit FAILS if they are equal. The value is a FUNCTION of the registered `PASSES` (the
pass number is inside every occurrence and presentation id), so the contract derives it for the registered count
(`pointer_contract.stratified_batches_digest`) and keeps the ten-pass number
`1c67edd74bf670a1b2b17af63209bc33bc2a92bc3a796e2d66f285d10c7b5304` only as the record. A legal change to
`PASSES` may move it, and a moved number is REPORTED as a value to record -- never adjusted to match anything.

THIS STUDY'S OWN STRATIFIED DIGEST IS NOT COMPARED AGAINST A LITERAL (review R2, item M4). It is a FUNCTION of
the registered `PASSES` -- protocol section 6 sets `PASSES` from the smoke job's measured per-update cost, and
the pass number is inside every occurrence and presentation id -- so the audit RE-DERIVES it from the contract
and checks it against the schedule this module built. The ten-pass value is kept as the record,
`1c67edd74bf670a1b2b17af63209bc33bc2a92bc3a796e2d66f285d10c7b5304`, and the contract's own ten-pass
derivation is checked against it whatever `PASSES` is. Freezing the whole-schedule digest as a literal is what
used to turn a legal `PASSES` into a false `SOURCE_SCHEDULE_IS_NOT_THE_BASE_SCHEDULE` failure -- a misleading
signal that looks like a real schedule problem and would stall a launch.

THE SCHEDULE NUMBERS ARE PRINTED BOTH WAYS. For the same artifact this audit prints `updates_per_pass`,
`presentations_per_pass`, `main_updates`, `passes`, `held_back_records`, `trained_records`, `excluded_records` and
`held_back_questions`, as `pointer_schedule` computes them AND as the split derived here counts them, together
with the values `pointer_contract.DESIGN` registers for the owner's decision. Every disagreement is a FINDING,
reported by name: nothing is adjusted to match a number. `main_updates` is `updates_per_pass x passes`, and
`PASSES` is 10 today and is the one open value in the frozen protocol (protocol section 6 sets it from the smoke
job's measured per-update cost), so it is printed and checked, never assumed.

Local, post-hoc and pre-run audit only. It imports the private checker (it reads correct answers), which is why
the worker never runs it: the contract carries the frozen result, and a test asserts that this module re-derives
exactly that result from the rules. No network, no GPU, $0.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / 'research/CAS_META_2_COMPOSITION'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

HELD_WORLD_COUNT = 5
EXPECTED_DIGESTS = {
    'held': '668e6ce73c426d1fcf8f2391e1a08d90c045ffb37fba95fc64e2658f5369ab1d',
    'excluded': 'b82108e14554a9fe746a7cfcb1e2cb181a99a3019dc39a3596805f10934c2621',
    'source_schedule': '1772c0a53933aa92ea7dfb6b2ce53dcd1089cb3634b089427caba3369977d275',
}
# The TEN-PASS stratified digest, recorded BESIDE the source schedule so the two cannot be confused. It is the
# RECORD, not the value this audit compares the built schedule against: the whole-schedule digest is a FUNCTION
# of the registered `PASSES` (protocol section 6 sets `PASSES` from the smoke job's measured per-update cost),
# so the audit re-derives it from the contract for whatever `PASSES` is (review R2, M4).
STRATIFIED_BATCHES_DIGEST_AT_10_PASSES = '1c67edd74bf670a1b2b17af63209bc33bc2a92bc3a796e2d66f285d10c7b5304'


def shape_signature(world):
    refs = sorted(node['ref'] for node in world['nodes'])
    position = {ref: at for at, ref in enumerate(refs)}
    edges = tuple(sorted((position[e['source']], position[e['target']]) for e in world['contains']))
    return len(refs), edges, position.get(world['declared_whole'])


def record_text(row):
    return json.dumps({key: value for key, value in row.items() if key != 'record_id'}, sort_keys=True)


def answer_texts(frozen):
    from cas_meta2.typed_teaching import checker, course
    return {row['record_id']: json.dumps([a['value'] for a in checker.derive_target(
                course._public(frozen['bank'], row['source_world_id']), row['query'])['admissible_answers']],
                sort_keys=True)
            for row in frozen['registry']}


def derive(frozen, answers=None):
    answers = answer_texts(frozen) if answers is None else answers
    registry = frozen['registry']
    bank = {world['world_id']: world for world in frozen['bank']['worlds']}
    course_worlds = sorted({row['source_world_id'] for row in registry})
    shapes = defaultdict(list)
    for world_id, world in bank.items():
        shapes[shape_signature(world)].append(world_id)
    eligible = [w for w in course_worlds if len(shapes[shape_signature(bank[w])]) == 1]
    texts = {row['record_id']: record_text(row) for row in registry}
    exposure = {w: sorted(row['record_id'] for row in registry if row['source_world_id'] != w
                          and (w in texts[row['record_id']] or w in answers[row['record_id']]))
                for w in eligible}
    held_worlds = sorted(w for _, w in sorted((len(exposure[w]), w) for w in eligible)[:HELD_WORLD_COUNT])
    held = sorted(row['record_id'] for row in registry if row['source_world_id'] in held_worlds)
    excluded = sorted(set().union(*(exposure[w] for w in held_worlds)) - set(held))
    answer_only = sorted(key for key in excluded if not any(w in texts[key] for w in held_worlds))
    trained = sorted(set(texts) - set(held) - set(excluded))
    return {'eligible_worlds': eligible, 'held_worlds': held_worlds, 'held': held, 'excluded': excluded,
            'answer_only_exposed': answer_only, 'trained': trained,
            'exposure_counts': {w: len(exposure[w]) for w in eligible}}


def source_schedule_digest(frozen):
    """The BASE schedule the pointer schedule is built from: `matched_contract.schedule`'s own `batches_digest`."""
    from cas_meta2.typed_teaching import matched_contract as matched, pointer_contract as contract
    return matched.schedule(frozen, contract.CONDITION)[1]['batches_digest']


def observed(frozen, derived):
    """The digests as THIS module's rules derive them."""
    from cas_meta2.typed_teaching import pointer_contract as contract
    return {'held': contract.digest(derived['held']), 'excluded': contract.digest(derived['excluded']),
            'source_schedule': source_schedule_digest(frozen),
            'stratified_schedule': stratified_schedule_digest(frozen)}


def stratified_schedule_digest(frozen, passes=None):
    """The STRATIFIED schedule's digest AS THIS MODULE DERIVES IT: the contract's own call, re-made.

    Never a literal. `passes` defaults to the registered `PASSES`, because the whole-schedule digest is a
    function of the pass count (review R2, M4): the pass number is inside every occurrence and presentation id.
    """
    from cas_meta2.typed_teaching import pointer_contract as contract
    return contract.stratified_batches_digest(frozen, passes)


def schedule_reading(frozen, derived):
    """The schedule facts, as `pointer_schedule` computes them AND as the split derived here counts them.

    `main_updates` is `updates_per_pass x passes` and `PASSES` is the one open value in the frozen protocol, so
    every number is PRINTED and compared; the `agreements` map is what `failed()` turns into findings, and no
    number is ever adjusted to match another.
    """
    from cas_meta2.typed_teaching import pointer_contract as contract
    _, stats = contract.pointer_schedule(frozen)
    design = contract.DESIGN
    counted = {'held_back_records': len(derived['held']), 'trained_records': len(derived['trained']),
               'excluded_records': len(derived['excluded'])}
    fields = ('passes', 'updates_per_pass', 'presentations_per_pass', 'main_updates', 'presentations',
              'held_back_records', 'trained_records', 'excluded_records', 'held_back_questions')
    schedule = {key: stats[key] for key in fields}
    registered = {
        'schedule_stratified': design['schedule_stratified'],
        'schedule_stratified_decision': design['schedule_stratified_decision'],
        'passes': design['passes'],
        'updates_per_pass': design['schedule_stratified_updates_per_pass'],
        'presentations_per_pass': design['schedule_stratified_presentations_per_pass'],
        'presentations_per_pass_unstratified_source':
            design['schedule_unstratified_presentations_per_pass'],
        'updates_per_pass_unstratified_source': design['schedule_unstratified_updates_per_pass'],
    }
    return {
        'from_pointer_schedule': schedule,
        'counted_from_the_split_derived_here': counted,
        'registered_by_the_contract_design': registered,
        'agreements': {
            'updates_per_pass_is_the_registered_decision':
                schedule['updates_per_pass'] == registered['updates_per_pass'],
            'presentations_per_pass_is_the_registered_decision':
                schedule['presentations_per_pass'] == registered['presentations_per_pass'],
            'main_updates_is_updates_per_pass_times_passes':
                schedule['main_updates'] == schedule['updates_per_pass'] * schedule['passes'],
            'passes_is_the_registered_value': schedule['passes'] == registered['passes'],
            'held_back_records_agree_with_the_split_derived_here':
                schedule['held_back_records'] == counted['held_back_records'],
            'trained_records_agree_with_the_split_derived_here':
                schedule['trained_records'] == counted['trained_records'],
            'excluded_records_agree_with_the_split_derived_here':
                schedule['excluded_records'] == counted['excluded_records'],
            'updates_per_pass_is_unchanged_from_the_source': (
                schedule['updates_per_pass'] == registered['updates_per_pass_unstratified_source']),
            'presentations_per_pass_is_not_the_source_value': (
                schedule['presentations_per_pass'] != registered['presentations_per_pass_unstratified_source']),
        },
    }


def contract_reading(frozen):
    """The same digests as the CONTRACT records them, re-derived from the contract's own calls."""
    from cas_meta2.typed_teaching import pointer_contract as contract
    held, _, excluded = contract.split(frozen)
    _, stats = contract.pointer_schedule(frozen)
    return {'held': contract.digest(held), 'excluded': contract.digest(excluded),
            'source_schedule': stats['source_schedule_digest'],
            'recorded_held': stats['held_back_record_ids_digest'],
            'recorded_excluded': stats['excluded_record_ids_digest'],
            'stratified_batches_digest': stats['batches_digest'],
            'derived_stratified_batches_digest': contract.STRATIFIED_BATCHES_DIGEST,
            'derived_stratified_batches_digest_at_10_passes':
                contract.stratified_batches_digest(frozen, contract.TEN_PASSES),
            'passes': contract.PASSES}


def audit(frozen):
    derived = derive(frozen)
    seen, recorded = observed(frozen, derived), contract_reading(frozen)
    return {
        'digests': seen,
        'expected_digests': dict(EXPECTED_DIGESTS),
        'matches_the_frozen_values': {key: seen[key] == EXPECTED_DIGESTS[key] for key in EXPECTED_DIGESTS},
        'matches_the_contract': {key: seen[key] == recorded[key] for key in EXPECTED_DIGESTS},
        'contract_recorded_ids_digest': {'held': recorded['recorded_held'] == seen['held'],
                                        'excluded': recorded['recorded_excluded'] == seen['excluded']},
        # M4. This study's own stratified digest is re-derived for the REGISTERED pass count and checked against
        # the schedule built here, the digest the contract reports for it, and the constant the contract derived
        # at import. Never against a frozen ten-pass literal -- that is what made a legal `PASSES` fail.
        'passes': recorded['passes'],
        'stratified_digest_is_the_derived_one_for_the_registered_passes':
            seen['stratified_schedule'] == recorded['stratified_batches_digest']
            == recorded['derived_stratified_batches_digest'],
        # The ten-pass identity is KEPT as the record, and stays checkable whatever `PASSES` is.
        'stratified_digest_at_10_passes_matches_the_record':
            recorded['derived_stratified_batches_digest_at_10_passes'] == STRATIFIED_BATCHES_DIGEST_AT_10_PASSES,
        # ... and the base MIXED schedule is still a DIFFERENT digest from this study's stratified one.
        'stratified_schedule_is_a_different_digest': seen['stratified_schedule'] != seen['source_schedule'],
        'schedule': schedule_reading(frozen, derived),
        'held_worlds': derived['held_worlds'],
        'answer_only_exposed': derived['answer_only_exposed'],
        'exposure_counts': derived['exposure_counts'],
        'eligible_worlds': len(derived['eligible_worlds']), 'held': len(derived['held']),
        'excluded': len(derived['excluded']), 'trained': len(derived['trained']),
    }


def failed(result):
    """The audit's explicit stop list: never an assert, and never a silent disagreement."""
    bad = ['DIGEST:%s' % key for key in EXPECTED_DIGESTS if not result['matches_the_frozen_values'][key]]
    bad += ['CONTRACT:%s' % key for key in EXPECTED_DIGESTS if not result['matches_the_contract'][key]]
    bad += ['CONTRACT_ID_DIGEST:%s' % key for key in result['contract_recorded_ids_digest']
            if not result['contract_recorded_ids_digest'][key]]
    if not result['stratified_digest_is_the_derived_one_for_the_registered_passes']:
        bad.append('STRATIFIED_DIGEST_IS_NOT_THE_DERIVED_ONE_FOR_PASSES_%d' % result['passes'])
    if not result['stratified_digest_at_10_passes_matches_the_record']:
        bad.append('STRATIFIED_TEN_PASS_DIGEST_MOVED')
    if not result['stratified_schedule_is_a_different_digest']:
        bad.append('SOURCE_SCHEDULE_IS_NOT_THE_BASE_SCHEDULE')
    for key in sorted(result['schedule']['agreements']):
        if not result['schedule']['agreements'][key]:
            bad.append('SCHEDULE:' + key)
    return bad


if __name__ == '__main__':
    from cas_meta2.typed_teaching import pointer_contract as contract
    frozen, _, _ = contract.load_material(ROOT)
    result = audit(frozen)
    print(json.dumps(result, indent=1))
    failures = failed(result)
    schedule = result['schedule']
    source = schedule['registered_by_the_contract_design']
    print(json.dumps({
        'status': 'HOLDOUT_AUDIT_FAILED' if failures else 'HOLDOUT_AUDIT_PASS',
        'failures': failures,
        'digests': result['digests'],
        'this_study_schedule_digest_to_record': result['digests']['stratified_schedule'],
        'source_schedule_digest': result['digests']['source_schedule'],
        'source_schedule_is_not_this_study_s_schedule':
            'source_schedule_digest %s is the SOURCE schedule: the matched MIXED, unstratified schedule the '
            'practice study\u2019s passes were built from, %d presentations per pass. THIS study\u2019s own '
            'stratified schedule is a DIFFERENT digest, %s, and is EXPECTED TO DIFFER, because the owner\u2019s '
            '"%s" decision moved this study from %d to %d presentations per pass while leaving the %d updates per '
            'pass unchanged. The two must never be asserted equal; this audit fails if they are.'
            % (result['digests']['source_schedule'], source['presentations_per_pass_unstratified_source'],
               result['digests']['stratified_schedule'], source['schedule_stratified_decision'],
               source['presentations_per_pass_unstratified_source'], source['presentations_per_pass'],
               source['updates_per_pass']),
        'schedule_numbers': schedule['from_pointer_schedule'],
        'schedule_numbers_counted_from_the_split_derived_here': schedule['counted_from_the_split_derived_here'],
        'schedule_numbers_registered_by_the_contract_design': source,
        'schedule_agreements': schedule['agreements'],
    }, indent=1), flush=True)
    raise SystemExit(1 if failures else 0)
