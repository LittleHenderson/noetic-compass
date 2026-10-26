"""[MADE-UP DATA WALK, NOT A RESULT] Write the made-up source files of the scratch project copy.

It writes, under optionb/dry/walk_amend1/project/:
  verdict/passages_kinds_HIDDEN_FROM_LABELERS.json   144 made-up passages in 48 made-up settings
  verdict/labels_team_a.json, labels_team_b.json     made-up label entries of two made-up teams
  design_v2/optionB_final.json                       a made-up design text that states the made-up counts
  optionb/PLAN_CONSTANTS.json                        the real constants with ONLY these blocks changed:
        sources.labels_team_a / labels_team_b / passages / design   (size and sha256 of the made-up files)
        counts_real                                                  (the counts of the made-up data)
        split.practice_settings, split.reserve_settings_in_order     (the seeded draw over the made-up settings)
Every other constant (floors, targets, briefs, models, seeds, rules) is the real one.
It also writes FIXTURE_TABLE.json and CONSTANTS_CHANGES.json beside this script.

No real passage, label or note is opened. Nothing outside optionb/dry/walk_amend1/ is written.
"""
import hashlib
import importlib.util
import json
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_fixture as F  # noqa: E402

P = HERE / 'project'
LF = chr(10)
PER_SETTING = 3
SETTINGS = ['made-up setting %02d' % n for n in range(1, 49)]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline=LF) as stream:
        stream.write(text)
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': sha(data)}


def dump(path, value):
    return write(path, json.dumps(value, indent=1, ensure_ascii=False) + LF)


def main():
    constants_path = P / 'optionb' / 'PLAN_CONSTANTS.json'
    real_bytes = (HERE.parent.parent / 'PLAN_CONSTANTS.json').read_bytes()
    C = json.loads(real_bytes.decode('utf-8'))
    split = C['split']
    drawn = random.Random(C['seeds']['split']).sample(sorted(SETTINGS), split['practice_setting_count_max'])
    practice, reserve = drawn[:split['practice_setting_count_start']], drawn[split['practice_setting_count_start']:]
    role_of = {name: 'final' for name in SETTINGS}
    role_of.update({name: 'practice' for name in practice})
    role_of.update({name: 'reserve_%d' % (k + 1) for k, name in enumerate(reserve)})
    # ids: the final passages first, so that the barred ids V009 and V076 are final passages
    order = sorted(SETTINGS, key=lambda name: ({'final': 0, 'reserve_4': 1, 'reserve_3': 2, 'reserve_2': 3, 'reserve_1': 4, 'practice': 5}[role_of[name]], name))
    rows = []
    for setting in order:
        for _ in range(PER_SETTING):
            index = len(rows)
            p = F.person(index)
            p.update({'id': 'V%03d' % (index + 1), 'setting': setting, 'role': role_of[setting], 'kind': 'K%d' % (index % 5 + 1), 'special': None})
            rows.append(p)
    final = [p for p in rows if p['role'] == 'final' and p['id'] not in C['eligibility']['barred_passage_ids']]
    practice_rows = [p for p in rows if p['role'] == 'practice']
    marks_final = ['EXCLUDED_A_UNCERTAIN_8', 'EXCLUDED_B_REACHED_BY_REASONING', 'EXCLUDED_A_OTHER_CANDIDATE', 'KIND_K6', 'KIND_K7',
                   'SINGLE_FORM', 'SINGLE_FORM', 'SINGLE_FORM', 'ONLY_A_EXTRA_2', 'CLAUDE_FLAG', 'GUESSABLE', 'SUPPORT_FAILS_TWICE', 'LEAK_WORD']
    for mark, p in zip(marks_final, final[5::7]):
        p['special'] = mark
    for mark, p in zip(['SINGLE_FORM', 'SPARE_PASS', 'SUPPORT_FAILS_ONCE'], practice_rows[2::7]):
        p['special'] = mark
    assert sum(1 for p in rows if p['special']) == len(marks_final) + 3

    passages, team_a, team_b = [], [], []
    for p in rows:
        if p['special'] == 'KIND_K6':
            p['kind'] = 'K6'
        if p['special'] == 'KIND_K7':
            p['kind'] = 'K7'
        text = F.passage_text(p)
        assert '===' not in text and '^' not in text
        passages.append({'id': p['id'], 'kind': p['kind'], 'setting': p['setting'], 'text': text})
        entries = [{'noetic': '^1', 'words': p['name'], 'mind': '', 'relative_to': ''},
                   {'noetic': '^2', 'words': 'the ' + p['liked'], 'mind': p['name'], 'relative_to': ''}]
        if p['special'] != 'SINGLE_FORM':
            entries += [{'noetic': '^3', 'words': 'the ' + p['disliked'], 'mind': p['name'], 'relative_to': ''},
                        {'noetic': '^7', 'words': 'Every morning for nine years', 'mind': p['name'], 'relative_to': 'dusted the ' + p['obj']}]
        a, b = [dict(e) for e in entries], [dict(e) for e in entries]
        for entry in b:                      # team B words its related thing a little differently
            if entry['noetic'] == '^7':
                entry['relative_to'] = 'the ' + p['obj']
        if p['special'] == 'ONLY_A_EXTRA_2':
            a.append({'noetic': '^2', 'words': 'the ' + p['other'], 'mind': p['name'], 'relative_to': ''})
        if p['special'] == 'EXCLUDED_A_UNCERTAIN_8':
            a.append({'noetic': '^8', 'words': 'A ' + p['thing'], 'mind': p['name'], 'relative_to': 'the ' + p['obj'], 'certainty': 'ambiguous'})
        if p['special'] == 'EXCLUDED_B_REACHED_BY_REASONING':
            b.append({'noetic': '^9', 'words': 'the ' + p['obj'], 'mind': p['name'], 'relative_to': 'A ' + p['thing'], 'reached_by': 'reasoning'})
        if p['special'] == 'EXCLUDED_A_OTHER_CANDIDATE':
            a.append({'noetic': '^5', 'words': 'nine years', 'mind': p['name'], 'relative_to': '', 'other_candidate': 'reasoning'})
        team_a.append({'passage_id': p['id'], 'entries': a})
        team_b.append({'passage_id': p['id'], 'entries': b})

    pins = {'passages': dump(P / 'verdict' / 'passages_kinds_HIDDEN_FROM_LABELERS.json', passages),
            'labels_team_a': dump(P / 'verdict' / 'labels_team_a.json', team_a),
            'labels_team_b': dump(P / 'verdict' / 'labels_team_b.json', team_b)}
    dump(HERE / 'FIXTURE_TABLE.json', {'note': 'MADE-UP. Never a case.', 'passages': {p['id']: p for p in rows}})

    changes = []

    def change(path, value):
        node = C
        for key in path[:-1]:
            node = node[key]
        changes.append({'key': '.'.join(path), 'real_value_sha256': sha(json.dumps(node[path[-1]], sort_keys=True).encode()),
                        'made_up_value_sha256': sha(json.dumps(value, sort_keys=True).encode())})
        node[path[-1]] = value

    for name, pin in pins.items():
        change(['sources', name, 'bytes'], pin['bytes'])
        change(['sources', name, 'sha256'], pin['sha256'])
    change(['split', 'practice_settings'], practice)
    change(['split', 'reserve_settings_in_order'], reserve)

    # the counts of the made-up data, worked out by the eligibility tool's own function build()
    spec = importlib.util.spec_from_file_location('walk_ob_eligibility', P / 'tools' / 'ob_eligibility.py')
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    result = tool.build(P, C)
    counts, extras = result['counts'], result['extras']
    design = {'note': 'MADE-UP design text for the walk. It only states the made-up counts in the sentences the tools look for.',
              'spec': {'source_passages_and_role_descriptions':
                       'MADE-UP. They hold %d agreed entries (%d of them ^2 to ^9). There are %d entries only team A gave and %d only team B gave (^2 to ^9).'
                       % (extras['eligible_agreed_entries'], extras['eligible_agreed_entries_2_to_9'], extras['eligible_only_a_2_to_9'], extras['eligible_only_b_2_to_9']),
                       'sizes_and_what_can_be_concluded': 'MADE-UP. No size is stated here.',
                       'guidance_groups': {'note': 'MADE-UP'}, 'task_design': 'MADE-UP. No count is stated here.'}}
    pin = dump(P / 'design_v2' / 'optionB_final.json', design)
    change(['sources', 'design', 'bytes'], pin['bytes'])
    change(['sources', 'design', 'sha256'], pin['sha256'])
    new_counts = {'note': 'MADE-UP DATA WALK. Counts of the made-up passages and labels, worked out by tools/ob_eligibility.py build().'}
    new_counts.update({k: v for k, v in counts.items() if k != 'note'})
    change(['counts_real'], new_counts)
    made = write(constants_path, json.dumps(C, indent=1, ensure_ascii=False) + LF)
    dump(HERE / 'CONSTANTS_CHANGES.json', {
        'note': 'MADE-UP DATA WALK, NOT A RESULT. The scratch constants are the real constants with only the keys below changed. '
                'They pin the made-up source files, state their counts, and name the made-up settings of the seeded draw.',
        'real_constants_sha256': sha(real_bytes), 'scratch_constants': made, 'changed_keys': changes,
        'made_up_counts': {k: counts[k] for k in ('passages', 'settings', 'excluded_passages', 'eligible_passages', 'k1_to_k5_passages', 'by_practice_setting_count')},
        'special_passages': {p['id']: [p['special'], p['role']] for p in rows if p['special']},
        'barred': {pid: [r['role'] for r in rows if r['id'] == pid] for pid in C['eligibility']['barred_passage_ids']}})
    print(json.dumps({'passages': len(rows), 'practice': practice, 'reserve': reserve, 'scratch_constants': made,
                      'eligible': counts['eligible_passages'], 'excluded': counts['excluded_passages'],
                      'by_practice_setting_count': counts['by_practice_setting_count'],
                      'special': {p['id']: [p['special'], p['role']] for p in rows if p['special']}}, indent=1))


if __name__ == '__main__':
    main()
