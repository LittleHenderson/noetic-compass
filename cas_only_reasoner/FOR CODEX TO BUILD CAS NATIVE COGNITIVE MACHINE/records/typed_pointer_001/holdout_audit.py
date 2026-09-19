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

WHAT IS NEW HERE, and why this is not a copy of the practice audit. This audit prints the THREE DIGESTS the
frozen split and the frozen schedule must equal, and checks them three ways: against the values this file's rules
re-derive, against the values the CONTRACT records, and against the three values the study was frozen on:

    held           668e6ce73c426d1fcf8f2391e1a08d90c045ffb37fba95fc64e2658f5369ab1d
    excluded       b82108e14554a9fe746a7cfcb1e2cb181a99a3019dc39a3596805f10934c2621
    source schedule 1772c0a53933aa92ea7dfb6b2ce53dcd1089cb3634b089427caba3369977d275

The third is the SOURCE schedule: `pointer_contract.pointer_schedule` draws its stratified pass from
`matched_contract.schedule(frozen, CONDITION)` and records that base schedule's own `batches_digest` as
`source_schedule_digest` (`pointer_contract.py:314`). It is the digest of the practice study's unstratified
MIXED order, NOT of the stratified pointer schedule (`1c67edd74bf670a1b2b17af63209bc33bc2a92bc3a796e2d66f285d10c7b5304`),
so a re-derivation that silently switched to the stratified order would be caught here.

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
# The stratified pointer schedule's own digest, recorded BESIDE the source schedule so the two cannot be confused.
STRATIFIED_BATCHES_DIGEST = '1c67edd74bf670a1b2b17af63209bc33bc2a92bc3a796e2d66f285d10c7b5304'


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
    """The three digests as THIS module's rules derive them."""
    from cas_meta2.typed_teaching import pointer_contract as contract
    return {'held': contract.digest(derived['held']), 'excluded': contract.digest(derived['excluded']),
            'source_schedule': source_schedule_digest(frozen)}


def contract_reading(frozen):
    """The same three digests as the CONTRACT records them, re-derived from the contract's own calls."""
    from cas_meta2.typed_teaching import pointer_contract as contract
    held, _, excluded = contract.split(frozen)
    _, stats = contract.pointer_schedule(frozen)
    return {'held': contract.digest(held), 'excluded': contract.digest(excluded),
            'source_schedule': stats['source_schedule_digest'],
            'recorded_held': stats['held_back_record_ids_digest'],
            'recorded_excluded': stats['excluded_record_ids_digest'],
            'stratified_batches_digest': stats['batches_digest']}


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
        'stratified_schedule_is_a_different_digest':
            recorded['stratified_batches_digest'] == STRATIFIED_BATCHES_DIGEST
            and recorded['stratified_batches_digest'] != seen['source_schedule'],
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
    if not result['stratified_schedule_is_a_different_digest']:
        bad.append('SOURCE_SCHEDULE_IS_NOT_THE_BASE_SCHEDULE')
    return bad


if __name__ == '__main__':
    from cas_meta2.typed_teaching import pointer_contract as contract
    frozen, _, _ = contract.load_material(ROOT)
    result = audit(frozen)
    print(json.dumps(result, indent=1))
    failures = failed(result)
    if failures:
        print(json.dumps({'status': 'HOLDOUT_AUDIT_FAILED', 'failures': failures}, indent=1), flush=True)
        raise SystemExit(1)
    print(json.dumps({'status': 'HOLDOUT_AUDIT_PASS', 'digests': result['digests']}, indent=1), flush=True)
