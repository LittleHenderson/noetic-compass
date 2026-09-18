"""Derive the practice study's held-back split from its frozen RULES, independently of the contract's constants.

Local, post-hoc and pre-run audit only. It imports the private checker (it reads correct answers), which is
why the worker never runs it: the contract carries the frozen result, and a test asserts that this module
re-derives exactly that result from the rules.

The rules (docs/CNCM_TYPED_PRACTICE_STUDY_v0.1.md, section 2):
1. A course world is ELIGIBLE only if no other world in the 64-world bank has the same shape: the same node
   count, the same edge list over node positions (nodes ordered as the learner's N aliases are, by ref), and
   the same declared whole. A look-alike world's answers would transfer by position without learning.
2. A world's EXPOSURE is every record focused on another world that mentions it anywhere -- in its query,
   arguments, cue, instruction or worked supports -- or whose correct answers name it.
3. The five eligible worlds with the smallest exposure, ties by world id, are held back.
4. Every exposure record of a held world is EXCLUDED from training; every record focused on a held world is
   HELD; the rest are TRAINED.
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


if __name__ == '__main__':
    from cas_meta2.typed_teaching import practice_contract as contract
    frozen, _, _ = contract.load_material(ROOT)
    result = derive(frozen)
    print(json.dumps({k: (v if k in ('held_worlds', 'answer_only_exposed', 'exposure_counts') else len(v))
                      for k, v in result.items()}, indent=1))
