"""Sort the unmatched bar-row entries of the v2.1 run by why they did not pair. Read-only, descriptive only.

For each unmatched entry of Noetic r (team T, passage p):
  PRESENCE  the other team has no bar-row entry of r in p at all (one team saw the role, the other did not);
  SAME_THING_OTHER_LINK  the other team has an r entry whose label shares a content word with this label, but the
                         pair failed on the Mind or the related thing (or on the scorer's stricter place test);
  OTHER_THING  the other team has r entries in p, but none names a thing sharing a content word with this label.
Prints counts per Noetic and writes example passages to the JSON path given as argv[1].
The scorer's own pairing is the authority; this sort only describes its leftovers."""
import json
import re
import sys
from collections import Counter, defaultdict

STUDY = 'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/'
V = STUDY + 'label_v21/verdict/'
sys.path.insert(0, STUDY + 'tools')
import verdict as attempt1  # noqa: E402  (its small-word list, read only)

SMALL = set()
for name in dir(attempt1):
    val = getattr(attempt1, name)
    if isinstance(val, (set, frozenset)) and len(val) > 20 and all(isinstance(x, str) for x in val):
        SMALL |= set(val)

report = json.load(open(V + 'VERDICT_REPORT.json', encoding='utf-8'))
passages = {p['id']: p['text'] for p in json.load(open(V + 'passages_sealed.json', encoding='utf-8'))}
rows = {}
for team in ('a', 'b'):
    for row in json.load(open(V + 'labels_team_%s.json' % team, encoding='utf-8')):
        rows[(team.upper(), row['passage_id'])] = row


def content(s):
    return {w for w in re.findall(r"[a-z0-9']+", s.lower()) if w not in SMALL}


def bar(e):
    if e.get('certainty') != 'clear':
        return False
    if e.get('noetic') == '^9' and e.get('reached_by') == 'reasoning':
        return False
    return True


def entries(team, pid, r):
    row = rows.get((team, pid)) or {}
    return [e for e in row.get('entries', []) if e.get('noetic') == r and bar(e)]


counts = defaultdict(Counter)
examples = defaultdict(lambda: defaultdict(list))
for u in report['unmatched']:
    r, pid, team = u['row'], u['passage'], u['team']
    if r == '^1':
        continue
    other = 'B' if team == 'A' else 'A'
    oth = entries(other, pid, r)
    if not oth:
        kind = 'PRESENCE'
    elif any(content(u['label']) & content(o['label']) for o in oth):
        kind = 'SAME_THING_OTHER_LINK'
    else:
        kind = 'OTHER_THING'
    counts[r][kind] += 1
    counts[r]['team_' + team] += 1
    examples[r][kind].append(pid)

summary = {}
for r in sorted(counts):
    c = counts[r]
    total = c['PRESENCE'] + c['SAME_THING_OTHER_LINK'] + c['OTHER_THING']
    summary[r] = dict(c, total=total)
    print(r, 'unmatched', total, '| one team only (presence):', c['PRESENCE'], '| same thing, other Mind or link:',
          c['SAME_THING_OTHER_LINK'], '| other thing named:', c['OTHER_THING'], '| from A', c['team_A'], 'from B', c['team_B'])

out = {'summary': summary,
       'example_passages': {r: {k: sorted(set(v))[:12] for k, v in d.items()} for r, d in examples.items()}}
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), indent=1)
