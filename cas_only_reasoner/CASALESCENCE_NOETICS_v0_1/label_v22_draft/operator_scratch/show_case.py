"""Show one passage and both teams' entries for the named Noetics. Read-only.
Usage: show_case.py W029:^2 W059:^8,^9 ..."""
import json
import sys

V = 'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/label_v21/verdict/'
passages = {p['id']: p['text'] for p in json.load(open(V + 'passages_sealed.json', encoding='utf-8'))}
rows = {}
for team in ('a', 'b'):
    for row in json.load(open(V + 'labels_team_%s.json' % team, encoding='utf-8')):
        rows[(team.upper(), row['passage_id'])] = row

for arg in sys.argv[1:]:
    pid, noetics = arg.split(':')
    want = noetics.split(',')
    print('=' * 100)
    print(pid, '|', passages[pid])
    for team in ('A', 'B'):
        row = rows.get((team, pid)) or {}
        if row.get('labeler_failed'):
            print('  team', team, 'COULD NOT LABEL')
            continue
        for e in row.get('entries', []):
            if e.get('noetic') in want:
                flag = '' if e.get('certainty') == 'clear' else ' [AMBIGUOUS, other: %s]' % e.get('other_candidate')
                if e.get('reached_by'):
                    flag += ' [reached by %s]' % e['reached_by']
                print('  %s %s label=%r | mind=%r | rel=%r | saying=%r%s' % (
                    team, e['noetic'], e['label'], e.get('mind'), e.get('relative_to'), e.get('saying'), flag))
        notes = row.get('not_enough_information') or []
        if notes:
            print('  %s notes: %s' % (team, ' / '.join(notes)[:400]))
