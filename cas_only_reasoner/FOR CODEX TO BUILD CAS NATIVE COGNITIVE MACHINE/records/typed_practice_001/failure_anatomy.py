"""How the practice study failed on new worlds: a descriptive reading of the sealed answers.

No neural work, no model load: it reads the sealed predictions and scorings already in the receipts.
Nothing here is a gate. The claim status of the study is the label from evaluate_gates.py.

Per seed, split (held back / practised) and pass (0, 10) it reports:
  right        - records answered right
  changed      - records whose answer at pass 10 differs from pass 0
  modal        - records whose answer equals the most common answer the machine gave to that kind in that
                 split at that pass (high = one answer for every world, i.e. the input is being ignored)
  borrowed     - wrong held-back answers (pass 0 gives the untrained baseline) that are a right answer to some PRACTISED record of the same kind
                 (in the learner's alias symbols), i.e. an answer carried over from a practised world
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evaluate_gates as eg  # noqa: E402  (sets up the import path the same way the gate reader does)

SEEDS = ('20260917', '20260918', '20260919')


def _answers(receipt, phase, bank_order):
    blob = json.loads((eg._artifacts(receipt) / (phase + '_predictions.json')).read_bytes())
    return {p['record_id']: eg.alias_form(p['answer']['value'], bank_order) for p in blob['predictions']}


def main():
    from cas_meta2.typed_teaching import practice_contract as contract
    frozen, _, _ = contract.load_material(eg.ROOT)
    held, trained, _ = contract.split(frozen)
    held_ids, trained_ids = set(held), set(trained)  # split() returns record ids
    by_id = {row['record_id']: row for row in frozen['registry']}
    kind = {rid: row['query']['kind'] for rid, row in by_id.items()}
    bank_order = eg._bank_order(frozen)
    practised_right = defaultdict(set)
    for rid in trained_ids:
        for value in eg._admissible(frozen, by_id[rid]):
            practised_right[kind[rid]].add(eg.alias_form(value, bank_order))
    held_right = {rid: {eg.alias_form(v, bank_order) for v in eg._admissible(frozen, by_id[rid])} for rid in held_ids}

    report = {'boundary': __doc__.strip().splitlines()[0], 'seeds': {}}
    for seed in SEEDS:
        receipt = HERE / ('receipt_' + seed)
        out = {}
        answers = {ph: _answers(receipt, 'course_' + ph, bank_order) for ph in ('p00', 'p10')}
        right = {ph: eg._rows(receipt, 'course_' + ph) for ph in ('p00', 'p10')}
        for name, ids in (('held_back', held_ids), ('practised', trained_ids)):
            row = {'records': len(ids)}
            for ph in ('p00', 'p10'):
                modal = {k: Counter(answers[ph][r] for r in ids if kind[r] == k).most_common(1)[0][1]
                         for k in {kind[r] for r in ids}}
                row[ph] = {'right': sum(right[ph][r] for r in ids), 'modal': sum(modal.values())}
            row['changed_p00_to_p10'] = sum(answers['p00'][r] != answers['p10'][r] for r in ids)
            out[name] = row
        for ph in ('p00', 'p10'):  # pass 0 is the untrained baseline for the same count
            wrong = [r for r in held_ids if not right[ph][r]]
            out['held_back'][ph]['wrong'] = len(wrong)
            out['held_back'][ph]['borrowed'] = sum(answers[ph][r] in practised_right[kind[r]]
                                                   and answers[ph][r] not in held_right[r] for r in wrong)
        per_kind = defaultdict(lambda: [0, 0, 0])
        for r in held_ids:
            per_kind[kind[r]][0] += 1
            per_kind[kind[r]][1] += right['p10'][r]
            per_kind[kind[r]][2] += answers['p00'][r] != answers['p10'][r]
        out['held_back_by_kind_p10'] = {k: {'records': v[0], 'right': v[1], 'changed': v[2]}
                                        for k, v in sorted(per_kind.items())}
        report['seeds'][seed] = out
    text = json.dumps(report, indent=1, sort_keys=True) + '\n'
    (HERE / 'failure_anatomy_result.json').write_bytes(text.encode('utf-8'))
    print(text)


if __name__ == '__main__':
    main()
