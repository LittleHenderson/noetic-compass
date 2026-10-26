"""Build the worked examples E1 to E10 of guide v2.2 (draft) from the sealed v2.1 passages. Plain Python, read-only inputs.

Every label, support, mind and relative_to is cut from the passage text by sentence number and checked to be an exact
copy, so nothing is retyped. Writes:
  worked_examples_passages.json  the passages used (id and text), for the checker's operator mode
  worked_examples_records.json   one record per example passage (only the entries for its point, plus the ^1 entries)
  worked_examples_section.md     the guide section, ready to insert
Each example keeps the owner-approved answer of the 2026-10-07 review (OWNER_ANSWER_REALITY_ENGINEERING_EXAMPLES_20261007.json)."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEALED = HERE.parent / 'label_v21' / 'verdict' / 'passages_sealed.json'
TEXT = {p['id']: p['text'] for p in json.load(open(SEALED, encoding='utf-8'))}


def sentences(pid):
    return re.split(r'(?<=[.!?])\s+', TEXT[pid].strip())


def sup(pid, first, last=None):
    s = sentences(pid)
    last = first if last is None else last
    out = ' '.join(s[first - 1:last])
    assert out in TEXT[pid], (pid, first, last)
    return out


def entry(pid, noetic, label, support, mind, rel, saying, certainty='clear', other=None):
    for name, val in (('label', label), ('mind', mind), ('relative_to', rel)):
        assert val == '' or val in TEXT[pid], (pid, name, val)
    assert label in support, (pid, 'label not in support', label)
    e = {'noetic': noetic, 'label': label, 'support': support, 'mind': mind, 'relative_to': rel,
         'certainty': certainty, 'saying': saying}
    if other:
        e['other_candidate'] = other
    return e


def mind(pid, name, s):
    return entry(pid, '^1', name, sup(pid, s), name, '', '')


EX = []

# E1 Positive: one entry for each thing the Mind is drawn to (W029)
p = 'W029'
s24 = sup(p, 2, 4)
EX.append(('E1', 'Positive: one entry for each thing the Mind is drawn to', p, [
    mind(p, 'Jenny', 1),
    entry(p, '^2', 'the dodgems', s24, 'Jenny', '', 'Drawn to it like a moth to a flame.'),
    entry(p, '^2', 'the Ferris wheel', s24, 'Jenny', '', 'It speaks to me.'),
    entry(p, '^2', 'the ring toss game', s24, 'Jenny', '', "Can't resist."),
], 'Each activity is a separate thing Jenny is drawn to: "Each activity promised a different kind of enjoyment." '
   'Wrong: one entry for "her exciting afternoon", the plan that holds them. The book names the thing itself: the `^2` '
   'of the dog is "The doggy treat used to lure and reward--something the dog likes" (Reality Engineering, p. 73).'))

# E2 Negative: indifference is not dislike (W003)
p = 'W003'
EX.append(('E2', 'Negative: a thing that leaves the Mind cold is not `^3`', p, [
    mind(p, 'Julian', 1),
    entry(p, '^4', 'offered him nothing', sup(p, 2), 'Julian', 'Their frenetic energy', 'It made no impression on him.'),
], 'Julian walks past the fish; he is not repelled by them. `^3` is "adverse to and repelled by", and its sayings are '
   'visceral (Part A, A6). A thing that only leaves the Mind cold is a weak `^4`. Wrong: `^3` "the display of small, '
   'darting fish".'))

# E3 Vibration: the label says what the Idea did to the Mind (W005)
p = 'W005'
EX.append(('E3', 'Vibration: the label says what the Idea did to the Mind', p, [
    mind(p, 'Noah', 1),
    mind(p, 'Younger workers', 4),
    entry(p, '^4', 'made him instantly flinch', sup(p, 2), 'Noah', 'The sound of a snapping fibre', 'Hit me hard.'),
    entry(p, '^4', 'barely noticed', sup(p, 2, 4), 'Younger workers', 'The sound of a snapping fibre',
          'It barely registered with them.'),
], '"Faint and sharp" describes the sound, not its impression on Noah, so it is not the `^4` label. The book: "how '
   'deeply "sit" is registering, how quickly he responds" (p. 73). "the sound" in the fourth sentence is a pointer, so '
   'the second entry\'s support reaches back to the sentence that names it in full (rule 16, step 4).'))

# E4 Female and Rhythm: each Idea that is part of who the Mind is (W002)
p = 'W002'
EX.append(('E4', 'Female and Rhythm: what the Mind is made of, and how often', p, [
    mind(p, 'Gary', 1),
    entry(p, '^5', 'a lifeboat volunteer', sup(p, 1), 'Gary', '', "It's who I am."),
    entry(p, '^5', 'a familiar routine imprinted on him', sup(p, 5), 'Gary', '', 'Part of what makes me me.'),
    entry(p, '^7', 'had served for years', sup(p, 1), 'Gary', 'a lifeboat volunteer', 'Practice makes perfect.'),
], 'Both the role he has taken on and the routine imprinted on him are part of who Gary is, so each is a `^5`. The '
   'routine is what the repetition left behind, so it is `^5`, not `^7`; the `^7` label is the rate-and-pattern words. '
   'The book: "Noetic 5 (Female) = "I am the sum of my experiences"" (p. 74).'))

# E5 Male: the whole the parts make up (W020, W023)
p = 'W020'
s13 = sup(p, 1, 3)
EX.append(('E5a', 'Male: the whole is named in full, never by a pointer', p, [
    entry(p, '^6', 'the power supply', s13, '', 'The faulty tanning machine', 'Breaking it down.'),
    entry(p, '^6', 'the sensors', s13, '', 'The faulty tanning machine', 'Breaking it down.'),
], 'The other five parts are written the same way. "the problem" is "the" plus one bare word, a pointer back to the '
   'machine that puzzled Robert, so the related thing is named in full (rule 16, step 4). The book: "the trainer '
   '(Idea) contains within it the instruction to sit (another Idea)" (p. 73).'))
p = 'W023'
s24 = sup(p, 2, 4)
EX.append(('E5b', 'Male: the whole the passage says the parts make up', p, [
    entry(p, '^6', 'a loose wire connecting the joystick', s24, '', "the machine's unresponsiveness", 'Breaking it down.'),
    entry(p, '^6', 'a jammed coin mechanism', s24, '', "the machine's unresponsiveness", 'Breaking it down.'),
], 'The other faults are written the same way. The passage says what the faults make up: "Each problem contributed to '
   'the machine\'s unresponsiveness." Wrong: "the faulty arcade game" as the related thing.'))

# E6 Male: a list of things noticed is not ^6 (W001) -- no entries for the point
p = 'W001'
EX.append(('E6', 'Male: a list of things a Mind notices is not `^6`', p, [
    mind(p, 'Evelyn', 1),
], 'Write no `^6`. The passage lists what Evelyn noticed, not the parts of one named whole. A thing is never its own '
   'part. Wrong: `^6` "the fry" with the related thing "the fry".'))

# E7 Recognizing a sign is a clear Cause and Effect (W022)
p = 'W022'
s24 = sup(p, 2, 4)
EX.append(('E7', 'Recognizing a sign is a clear Cause and Effect', p, [
    mind(p, 'Yolanda', 1),
    entry(p, '^8', 'a subtle yellowing on the underside of a single leaf', s24, 'Yolanda',
          'a nutrient deficiency that could quickly spread if left unaddressed', 'Made me think of...'),
    entry(p, '^9', 'a nutrient deficiency that could quickly spread if left unaddressed', s24, 'Yolanda',
          'a subtle yellowing on the underside of a single leaf', 'It just clicked.'),
], 'She "knew it signaled" the deficiency. By the owner\'s answer of 2026-10-07, recognizing a sign that brings a '
   'different Idea to Mind is a clear pair (rule 15(a)). The book: "The thought `I need milk\' (B9) triggered by '
   'noticing the empty carton (D8)" (p. 51).'))

# E8 One trigger, several things brought (W059)
p = 'W059'
trig = 'The cool morning air and the sweet scent of apples'
EX.append(('E8', 'One trigger, several things brought to Mind', p, [
    mind(p, 'Tina', 1),
    entry(p, '^8', trig, sup(p, 2), 'Tina', 'a day long ago', 'That reminds me...'),
    entry(p, '^9', 'a day long ago', sup(p, 2), 'Tina', trig, 'It just popped into my head.'),
    entry(p, '^9', 'her childhood bedroom window, open to a similar breeze', sup(p, 2, 3), 'Tina', trig,
          'A vivid picture came to me.'),
    entry(p, '^9', 'A sense of youthful freedom', sup(p, 2, 4), 'Tina', trig, 'The thought came to me.'),
], 'The `^8` is paired with what the passage says it "reminded her of". The picture and the feeling are parts of the '
   'same memory ("It was a memory she had not considered in years."), so each is a `^9` of the same trigger. The book: '
   'the `^9` is "the specific thought, memory, conclusion, or simpler idea generated by a mental trigger" (p. 50).'))

# E9 A memory placed right after a sign, with no linking word (W005)
p = 'W005'
s23 = sup(p, 2, 3)
EX.append(('E9', 'A memory right after a sign, with no word linking them', p, [
    mind(p, 'Noah', 1),
    entry(p, '^8', 'The sound of a snapping fibre', s23, 'Noah', 'a machine malfunction from years ago',
          'Triggered a memory.', 'ambiguous', 'none'),
    entry(p, '^9', 'a machine malfunction from years ago', s23, 'Noah', 'The sound of a snapping fibre',
          'It came back to him.', 'ambiguous', 'none'),
], 'The memory follows the sound, but no word says the sound brought it. That is rule 15(d): an uncertain pair. A clear '
   'pair needs a link such as "reminded", "brought back" or "made him think of".'))

# E10 Evidence that brings a conclusion to Mind is its Cause; evidence is not Male by itself (W137)
p = 'W137'
s24 = sup(p, 2, 4)
cause = 'Its shortness, combined with the way families drifted quickly past'
EX.append(('E10', 'Evidence can be a Cause; it is Male only inside a named whole', p, [
    mind(p, 'Brenda', 1),
    entry(p, '^8', cause, s24, 'Brenda', 'a slow day for that stall', 'Made me think of...'),
    entry(p, '^9', 'a slow day for that stall', s24, 'Brenda', cause, 'It just clicked.'),
], 'The owner\'s ruling of 2026-10-07: "Allow both relationships when each independently meets its definition. Remove '
   'the blanket rule excluding Cause whenever reasoning occurs. Do not automatically label evidence as Male. For example 8, '
   'mark Cause and Effect; Male is not established by the passage." The shortness and the drifting families are the joint '
   'subject of "told her": together they bring the slow day to Brenda\'s Mind, so they are one `^8` (table, `^8` row), '
   'named by the stretch that says it (rule 16, step 2). No whole that they make up is named, so there is no `^6`.'))

records, used = [], {}
for eid, title, pid, entries, why in EX:
    used[pid] = TEXT[pid]
    records.append({'passage_id': pid, 'none_of_these': False, 'entries': entries, 'not_enough_information': []})

# One record per passage for the checker: W005 appears in E3 and E9, so join its entries.
by_pid = {}
for rec in records:
    if rec['passage_id'] in by_pid:
        seen = {json.dumps(e, sort_keys=True) for e in by_pid[rec['passage_id']]['entries']}
        by_pid[rec['passage_id']]['entries'] += [e for e in rec['entries'] if json.dumps(e, sort_keys=True) not in seen]
    else:
        by_pid[rec['passage_id']] = json.loads(json.dumps(rec))
json.dump([{'id': k, 'text': v} for k, v in used.items()], open(HERE / 'worked_examples_passages.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
json.dump(list(by_pid.values()), open(HERE / 'worked_examples_records.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

lines = ['### Worked examples from the version 2.1 run (owner-approved, 2026-10-07)', '',
         'These passages come from the sealed set of the version 2.1 run, which is never labeled again. Each shows the '
         'answer the owner approved on 2026-10-07 (`label_v22_draft/OWNER_ANSWER_REALITY_ENGINEERING_EXAMPLES_20261007.json`). '
         'Only the entries for the point are shown, with the `^1` entries they need; the passages hold other roles too.', '']
for eid, title, pid, entries, why in EX:
    lines += ['Example %s (%s), from passage %s: "%s"' % (eid, title, pid, TEXT[pid]), '', '```json']
    lines += [json.dumps(e, ensure_ascii=False) for e in entries]
    lines += ['```', '', why, '']
(HERE / 'worked_examples_section.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')
print('examples', len(EX), '| passages', len(used), '| records', len(by_pid))
