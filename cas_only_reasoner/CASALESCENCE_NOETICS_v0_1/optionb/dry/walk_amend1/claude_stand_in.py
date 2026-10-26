"""[MADE-UP DATA WALK, NOT A RESULT] Stands in for the Claude sub-agent: writes a made-up answer sheet for one exported sheet.

No sub-agent and no model is called. The made-up answers: the right letter for every item, with one exception:
for the made-up passage marked CLAUDE_FLAG the with-passage answer to its GOES_FOR question is MORE_THAN_ONE.
Usage: python -B claude_stand_in.py <project folder name> <set> <mode> <sheet number>
"""
import re, sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_fixture as F
import walk_stub
project, set_name, mode, sheet = sys.argv[1:5]
solve = HERE / project / 'optionb' / 'solve'
text = (solve / ('claude_sheet_%s_%s_%s.txt' % (set_name, mode, sheet))).read_text(encoding='utf-8')
walk_stub._load()
lines = []
for item_id, body in re.findall(r'^=== ITEM (\S+) ===$(.*?)^=== END \1 ===$', text, flags=re.M | re.S):
    question = re.search(r'^Question: (.*)$', body, flags=re.M).group(1)
    p, q = walk_stub._by_question[question]
    options = dict((t, l) for l, t in re.findall(r'^([A-F])\. (.*)$', body, flags=re.M))
    reply = options[q['right']]
    if mode == 'with_passage' and p['special'] == 'CLAUDE_FLAG' and q.get('form') == 'GOES_FOR':
        reply = 'MORE_THAN_ONE'
    lines.append('%s %s' % (item_id, reply))
out = solve / ('claude_answers_%s_%s_%s.txt' % (set_name, mode, sheet))
with open(out, 'w', encoding='utf-8', newline='\n') as stream:
    stream.write('\n'.join(lines) + '\n')
print('made-up answer sheet: %s, %d lines' % (out.name, len(lines)))
