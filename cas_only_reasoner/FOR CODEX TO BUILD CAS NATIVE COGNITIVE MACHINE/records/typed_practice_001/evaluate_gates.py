"""The deterministic gate reading of the practice study (docs/CNCM_TYPED_PRACTICE_STUDY_v0.1.md, section 5).

Pure standard library plus the project's pure modules and the private checker (post-run, local). Reads the
collected receipts; runs no model. The label it prints IS the study's outcome. Prose does not override it.

    python evaluate_gates.py STUDY_JSON

Unit of evidence: a QUESTION (``query_id``), correct at a checkpoint only if every one of its records is
correct. Each seed is tested on its own and all three must pass: the seeds share the encoder, data and
schedule, so they are replications, not extra sample size. Held-back questions that a mechanism-free
shortcut already answers (the most common world-agnostic trained answer of the kind) are excluded from the
gate and reported separately. The shortcut is computed in the learner's own output symbols: world ids as
their global W aliases, node references as their per-world N aliases, so "the most common answer" means the
most common thing the machine could emit while ignoring the input. Gains must span at least two kinds AND
at least two held worlds.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
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
INTERFERENCE_UPDATES, REPLAY_UPDATES = 16, 2
MATCHED_RECEIPTS = ROOT / 'records/typed_matched_001'


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


def _artifacts(receipt):
    return Path(receipt) / 'collected/results/artifacts'


def _rows(receipt, phase):
    scored = json.loads((_artifacts(receipt) / (phase + '_scoring.json')).read_bytes())
    return {row['record_id']: bool(row['correct']) for row in scored['rows']}


def seed_summary(receipt):
    """A quick per-job readout for the operator log; the gates come from evaluate()."""
    report = json.loads((_artifacts(receipt) / 'worker_report.json').read_bytes())
    return {'scores': report.get('scores'), 'development': report.get('development_scores'),
            'retention': report.get('retention_scores'), 'status': report.get('status')}


NODE_REF = re.compile(r'world-[0-9a-f]{64}/n([0-9]+)')
WORLD_REF = re.compile(r'world-[0-9a-f]{64}')


def alias_form(value, bank_order):
    """An answer in the learner's output symbols: node references -> per-world N aliases, worlds -> global W."""
    text = NODE_REF.sub(lambda m: 'N' + m.group(1), json.dumps(value, sort_keys=True))
    return WORLD_REF.sub(lambda m: 'W%d' % bank_order[m.group(0)], text)


def _admissible(frozen, row):
    from cas_meta2.typed_teaching import checker, course
    return [a['value'] for a in checker.derive_target(course._public(frozen['bank'], row['source_world_id']),
                                                       row['query'])['admissible_answers']]


def _bank_order(frozen):
    return {w: i for i, w in enumerate(sorted(x['world_id'] for x in frozen['bank']['worlds']))}


def shortcut_answers(frozen, trained):
    """Per kind, the most common trained answer in alias form (ties by text): the input-blind constant."""
    bank_order = _bank_order(frozen)
    counts = {}
    for row in frozen['registry']:
        if row['record_id'] in trained:
            counts.setdefault(row['query']['kind'], Counter())[alias_form(_admissible(frozen, row)[0], bank_order)] += 1
    return {kind: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for kind, c in counts.items()}


def eligible_questions(frozen, trained, questions):
    """Held questions NOT answered by their kind's alias-form shortcut; the gate's population."""
    bank_order = _bank_order(frozen)
    shortcut = shortcut_answers(frozen, trained)
    by_id = {row['record_id']: row for row in frozen['registry']}
    eligible, shortcut_hit = [], []
    for q, records in questions.items():
        row = by_id[records[0]]
        forms = {alias_form(value, bank_order) for value in _admissible(frozen, row)}
        (shortcut_hit if shortcut.get(row['query']['kind']) in forms else eligible).append(q)
    return sorted(eligible), sorted(shortcut_hit), shortcut


def evaluate(study_path):
    from cas_meta2.typed_teaching import practice_contract as contract
    study = json.loads(Path(study_path).read_bytes())
    frozen, _, _ = contract.load_material(ROOT)
    held, trained, excluded = contract.split(frozen)
    _, stats = contract.practice_schedule(frozen)
    main_updates = stats['main_updates']
    held_questions = contract.held_back_questions(frozen)
    trained_set = set(trained)
    trained_questions = {}
    for row in frozen['registry']:
        if row['record_id'] in trained_set:
            trained_questions.setdefault(row['query']['query_id'], []).append(row['record_id'])
    kind_of = {row['query']['query_id']: row['query']['kind'] for row in frozen['registry']}
    world_of = {row['query']['query_id']: row['source_world_id'] for row in frozen['registry']}
    eligible, shortcut_hit, shortcut = eligible_questions(frozen, trained_set, held_questions)
    failures, seeds = [], {}
    jobs = study.get('jobs') if isinstance(study, dict) else None
    jobs = [job for job in jobs if isinstance(job, dict)] if isinstance(jobs, list) else []
    if (sorted(str(job.get('model_seed')) for job in jobs) != sorted(str(s) for s in contract.MODEL_SEEDS)
            or not all(isinstance(job.get('receipt_dir'), str) for job in jobs)):
        failures.append('I0:STUDY_MUST_HAVE_EXACTLY_THE_THREE_SEEDS_WITH_RECEIPTS')
        jobs = []
    for job in jobs:
        seed, receipt = job['model_seed'], Path(job['receipt_dir'])
        art = _artifacts(receipt)
        try:  # I1 -- completion and evidence
            lifecycle = json.loads((receipt / 'result.json').read_bytes())
            report = json.loads((art / 'worker_report.json').read_bytes())
            manifest = {row['name'] for row in json.loads((art / 'manifest.json').read_bytes())['artifacts']}
            from cncm import typed_practice_worker as worker
            if not (lifecycle.get('completed_deliverable') is True and lifecycle.get('cleanup', {}).get('complete') is True
                    and report.get('status') == worker.SUCCESS_STATUS and set(worker.EXPECTED_ARTIFACTS) <= manifest):
                failures.append('I1:%d' % seed)
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append('I1:%d:%s' % (seed, type(error).__name__))
            continue
        try:  # I2 -- held worlds and excluded carriers never trained
            material = json.loads((art / 'protocol_material.json').read_bytes())
            seen, lines = set(), 0
            logs = ['pass_%02d_batches.jsonl' % n for n in range(1, contract.PASSES + 1)] + ['interference_batches.jsonl']
            for name in logs:
                for line in (art / name).read_bytes().splitlines():
                    lines += 1
                    seen.update(p['record_id'] for p in json.loads(line)['predictions'])
            if (material['held_back_record_ids'] != held or material['excluded_record_ids'] != excluded
                    or not seen <= trained_set or lines != main_updates + INTERFERENCE_UPDATES):
                failures.append('I2:%d' % seed)
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append('I2:%d:%s' % (seed, type(error).__name__))
        try:  # I3 -- the same random start as the matched study
            mine = json.loads((art / 'initial_checkpoint.json').read_bytes())['metadata']['model_state_identity']
            theirs = json.loads((MATCHED_RECEIPTS / ('receipt_%d_m' % seed) / 'collected/results/artifacts/'
                                 'initial_checkpoint.json').read_bytes())['metadata']['model_state_identity']
            if mine != theirs:
                failures.append('I3:%d' % seed)
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append('I3:%d:%s' % (seed, type(error).__name__))
        try:  # I4 -- counts, reloads, replays
            replay = json.loads((art / 'replay_report.json').read_bytes())
            totals = report['global_actual_work']['totals']
            if not (report['main_training_delta']['optimizer_updates'] == main_updates
                    and report['interference_delta']['optimizer_updates'] == INTERFERENCE_UPDATES
                    and totals['optimizer_updates'] == main_updates + INTERFERENCE_UPDATES + REPLAY_UPDATES
                    and len(replay['replays']) == 2 and len(replay['reloads']) == 3):
                failures.append('I4:%d' % seed)
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append('I4:%d:%s' % (seed, type(error).__name__))
        try:
            at = {0: _rows(receipt, 'course_p00'), 1: _rows(receipt, 'course_p01'), 10: _rows(receipt, 'course_p10')}
            for n in (2, 4, 6, 8):
                at[n] = _rows(receipt, 'heldback_p%02d' % n)
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures.append('I1:%d:SCORING_%s' % (seed, type(error).__name__))
            continue
        heldq = {n: question_outcomes(at[n], held_questions) for n in at}
        trainq = {n: question_outcomes(at[n], trained_questions) for n in (0, 1, 10)}
        seeds[seed] = {
            'held_questions_correct': {str(n): sum(heldq[n].values()) for n in sorted(heldq)},
            'eligible_questions_correct': {str(n): sum(heldq[n][q] for q in eligible) for n in sorted(heldq)},
            'shortcut_questions_correct': {str(n): sum(heldq[n][q] for q in shortcut_hit) for n in sorted(heldq)},
            'trained_questions_correct': {str(n): sum(trainq[n].values()) for n in (0, 1, 10)},
            'held_records_correct': {str(n): sum(at[n][r] for r in held) for n in sorted(at)},
            'trained_records_correct': {str(n): sum(at[n][r] for r in trained) for n in (0, 1, 10)},
            'G_LEARN_p0_to_p10': seed_test(heldq[0], heldq[10], eligible, kind_of, world_of),
            'MORE_PRACTICE_p1_to_p10': seed_test(heldq[1], heldq[10], eligible, kind_of, world_of),
            'TRAINED_p0_to_p10': seed_test(trainq[0], trainq[10], sorted(trained_questions), kind_of),
            'TRAINED_p1_to_p10': seed_test(trainq[1], trainq[10], sorted(trained_questions), kind_of),
            'held_questions_by_world': {w[:14]: {str(n): sum(heldq[n][q] for q in held_questions if world_of[q] == w)
                                               for n in (0, 1, 10)} for w in sorted({world_of[q] for q in held_questions})},
            'held_questions_by_kind': {kind: {str(n): sum(heldq[n][q] for q in held_questions if kind_of[q] == kind)
                                              for n in (0, 1, 10)} for kind in sorted({kind_of[q] for q in held_questions})},
            'development': report.get('development_scores'), 'retention': report.get('retention_scores'),
            'pass_summaries': report.get('pass_summaries')}
    complete = not failures and len(seeds) == 3
    gates = {'integrity': {'pass': complete, 'failures': failures}}
    if complete:
        for name in ('G_LEARN_p0_to_p10', 'MORE_PRACTICE_p1_to_p10', 'TRAINED_p0_to_p10', 'TRAINED_p1_to_p10'):
            gates[name] = {'pass': all(s[name]['passed'] for s in seeds.values()),
                           'per_seed': {str(k): s[name]['passed'] for k, s in seeds.items()}}
        label = 'LEARNS_NEW_WORLDS' if gates['G_LEARN_p0_to_p10']['pass'] else 'NO_TRANSFER_TO_NEW_WORLDS'
        flags = {'more_practice_helps_new_worlds': gates['MORE_PRACTICE_p1_to_p10']['pass'],
                 'trained_questions_rise_from_start': gates['TRAINED_p0_to_p10']['pass'],
                 'trained_questions_rise_with_more_practice': gates['TRAINED_p1_to_p10']['pass']}
    else:
        label, flags = 'VOID', {}
    return {'schema': 'cncm.typed-practice-gate-reading/0.3', 'protocol': 'docs/CNCM_TYPED_PRACTICE_STUDY_v0.1.md',
            'alpha': str(ALPHA), 'min_improved_kinds': MIN_IMPROVED_KINDS, 'min_improved_worlds': MIN_IMPROVED_WORLDS,
            'label': label, 'flags': flags,
            'gates': gates, 'seeds': {str(k): v for k, v in seeds.items()},
            'held_worlds': stats['held_worlds'], 'held_questions': len(held_questions),
            'eligible_questions': len(eligible), 'shortcut_questions': len(shortcut_hit),
            'shortcut_answers': shortcut, 'held_records': len(held), 'trained_records': len(trained),
            'excluded_records': len(excluded), 'main_updates': main_updates}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: evaluate_gates.py STUDY_JSON')
    reading = evaluate(sys.argv[1])
    print(json.dumps(reading, indent=1, sort_keys=True))
