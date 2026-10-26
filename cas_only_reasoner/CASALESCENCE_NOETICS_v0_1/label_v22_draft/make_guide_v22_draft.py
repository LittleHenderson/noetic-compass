"""Make 02_LABELING_GUIDE_v2_2_DRAFT.md from 02_LABELING_GUIDE_v2_1.md. Every change is an exact replacement that must
match once, so a moved or missing anchor stops the build. Part A is not touched. Plain Python."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / '02_LABELING_GUIDE_v2_1.md'
OUT = HERE / '02_LABELING_GUIDE_v2_2_DRAFT.md'
text = SRC.read_text(encoding='utf-8')
assert '\r\n' not in text


def once(old, new):
    global text
    n = text.count(old)
    if n != 1:
        sys.exit('FAILED: anchor found %d times: %r' % (n, old[:90]))
    text = text.replace(old, new)


def line_starting(prefix):
    lines = [ln for ln in text.split('\n') if ln.startswith(prefix)]
    if len(lines) != 1:
        sys.exit('FAILED: %d lines start with %r' % (len(lines), prefix))
    return lines[0]


# 1. Title and status.
once('# 02 — Labeling guide, version 2.1 (candidate, not yet in force)',
     '# 02 — Labeling guide, version 2.2 (candidate, not yet in force)')
old_status = line_starting('Status: CANDIDATE.')
new_status = (
    'Status: CANDIDATE. Not in force until the owner has signed and the passages are sealed. Nothing has been labeled under '
    'it. It was built on 2026-10-07 from version 2.1, after the owner\'s answers of that day '
    '(`label_v22_draft/OWNER_ANSWER_REALITY_ENGINEERING_EXAMPLES_20261007.json`).\n\n'
    'Version 2.2 differs from version 2.1 only by the owner\'s answers of 2026-10-07 to a comparison with the owner\'s book '
    '*Reality Engineering* (canon by the owner\'s ruling of 2026-09-21), including his ruling that day on example 8. The '
    'book\'s ten definitions (printed page 446) are word for word the definitions of Part A, so Part A is unchanged. What '
    'changes is how they are applied: rules 2, 5 and 15 take the owner\'s answers on signs and on reasoning; the table and '
    'rule 3 gain lines; X1, X5 and X6 follow; and worked examples from the version 2.1 run (E1 to E10) show the answers the '
    'owner approved. Version 2.1\'s reasoning flag is gone: the owner\'s answers settle that a conclusion reached by reasoning '
    'is an Effect like any other. The last change table lists every change, and which ones are the operator\'s.')
once(old_status, new_status)

# 1c. The other candidate "reasoning" keeps its place, with a pointer that still fits.
once('`"none"`, or `"reasoning"` (see rule 15).',
     '`"none"`, or `"reasoning"` (an Idea that may have been worked out rather than brought to Mind; rule 15(b)).')
# 1b. The reasoning flag is no longer used, and its field is no longer named anywhere a labeler reads.
once('- `reached_by`: used only under rule 15(b). Write `"reached_by": "reasoning"` on a conclusion the Mind worked out. Leave the field out everywhere else.\n',
     '')
once('## Part B — How to label in this study (working convention, v2.1)', '## Part B — How to label in this study (working convention, v2.2)')

# 2. Table rows.
once('| `^2` Positive | the Idea the Mind has an affinity for and is attracted toward | that Mind | `""` |',
     '| `^2` Positive | the Idea the Mind has an affinity for and is attracted toward; one entry for each such thing (E1) | that Mind | `""` |')
once('| `^3` Negative | the Idea the Mind is adverse to and repelled by | that Mind | `""` |',
     '| `^3` Negative | the Idea the Mind is adverse to and repelled by; a thing that only leaves the Mind cold is not `^3` but a weak `^4` (E2) | that Mind | `""` |')
once('| `^4` Vibration | the words that state how strongly or how weakly the Idea impresses the Mind | that Mind | the Idea that resonates |',
     '| `^4` Vibration | the words that state how strongly or how weakly the Idea impresses the Mind: what it did to the Mind, never words that only describe the thing (E3) | that Mind | the Idea that resonates |')
once('| `^5` Female | the Idea or Ideas the Mind is composed of (what it has lived, learned, come to believe, become skilled in) | that Mind | `""` |',
     '| `^5` Female | the Idea or Ideas the Mind is composed of (what it has lived, learned, come to believe, become skilled in, a role it has taken on, a routine imprinted on it); one entry for each (E4) | that Mind | `""` |')
once('| `^6` Male | the Idea or Ideas that another Idea is composed of | `""` | the Idea they compose |',
     '| `^6` Male | the Idea or Ideas that another Idea is composed of; a list of things a Mind notices is not `^6` unless the passage shows them as parts of one whole (E6) | `""` | the Idea they compose: the whole the passage says they make up, named in full (E5); never the part itself |')
once('| `^8` Above/Cause | the Idea that triggers a different Idea to come to Mind | that Mind | the Idea it brings to Mind (the `^9`) |',
     '| `^8` Above/Cause | the Idea that triggers a different Idea to come to Mind; one entry for each trigger. Several things that '
     'together bring one Idea, as the joint subject of one verb ("…, combined with …, told her"), are one `^8`, named by that '
     'stretch (E10) | that Mind | the Idea it brings to Mind (the `^9`); when it brings several, the one the passage says it '
     'brought (E8) |')
once('| `^9` Below/Effect | the Idea brought to Mind | that Mind | its trigger (the `^8`) |',
     '| `^9` Below/Effect | the Idea brought to Mind; when one trigger brings several, each is a `^9` of that trigger (E8) | that Mind | its trigger (the `^8`) |')

# 2b. Rule 2 (how a pair or a lone entry is written) and rule 5 (the Test) follow rule 15 as changed.
once('The two rule-15 cases keep their flags: a conclusion reached by reasoning (rule 15b) is marked on its own, with '
     '`"reached_by": "reasoning"`; a sign whose way of working the passage does not reveal (rule 15d) is marked as an uncertain '
     'pair. When the passage gives only one of the two, and rule 5 marks it (for example a thought that comes out of nowhere, '
     'with no trigger named), write that one entry alone, with `relative_to` `""` and a note under `not_enough_information`.',
     'A sign that the passage does not link to the Idea (rule 15d) is marked as an uncertain pair. When the passage gives only '
     'one of the two and no partner (a thought that comes out of nowhere, with no trigger named; or a conclusion whose evidence '
     'is not a Cause, rule 15(b)), and rule 5 marks it, write that one entry alone, with `relative_to` `""` and a note under '
     '`not_enough_information`.')
once('`^8` is triggering, not reasoning (A8). Nothing else decides presence.',
     '`^8` is triggering, not reasoning (A8). Where reasoning and triggering meet, the owner\'s ruling of 2026-10-07 applies '
     '(rule 15(b)). Nothing else decides presence.')

# 3. Rule 3.
once('3. **No Mind, no `^8`/`^9`.** Rain making a road wet is not `^8`. The definition needs an Idea coming to Mind.',
     '3. **No Mind, no `^8`/`^9`.** Rain making a road wet is not `^8`. The definition needs an Idea coming to Mind. '
     'The physical examples of *Reality Engineering* (gravity and a falling apple, heat and sweating) describe '
     'Physical-world Elements, not labels in a passage (owner\'s answer, 2026-10-07).')

# 4. Rule 15 (a), a pending note after (b), and (d).
once('    - **(a) The sign directly brings a different Idea to Mind.** Mark `^8` and `^9`. Words that show this: "reminded", "brought back", "made her think of", "came to him", "was suddenly in".',
     '    - **(a) The sign directly brings a different Idea to Mind.** Mark `^8` and `^9`. Recognizing a sign is this case: '
     'when the Mind knows, recognises or can tell what a sign means, the sign is the `^8` and what it means is the `^9` '
     '(owner\'s answer, 2026-10-07; *Reality Engineering*, p. 51: "The thought \'I need milk\' (B9) triggered by noticing '
     'the empty carton (D8)"; worked example E7). The passage must link the sign and the Idea: one sentence says that the sign '
     'brought it. Either the sign is the subject of a verb that brings, gives or tells (for example "reminded", "brought back", '
     '"made her think of", "took him back to", "told her", "meant"), or the Mind "knew", "recognised" or "could tell" from the '
     'sign what it means. Without such a sentence it is (d). A thought that only "came to him", or a Mind that "was suddenly '
     'in" another place, shows that an Idea came, not what brought it (owner\'s answer, 2026-10-07). Words that show this: '
     '"reminded", "brought back", "made her think of", "knew", "recognised", "could tell", "meant".')
old_b = line_starting('    - **(b) The Mind works through evidence to a conclusion.**')
once(old_b,
     '    - **(b) The Mind works through evidence to a conclusion.** The conclusion is a `^9`, an Effect like any other '
     '(owner\'s answers, 2026-10-07). The owner\'s ruling of 2026-10-07 decides the evidence: "Allow both relationships when '
     'each independently meets its definition. Remove the blanket rule excluding Cause whenever reasoning occurs. Do not '
     'automatically label evidence as Male." So apply rule 5 to each piece of evidence on its own. It is the conclusion\'s '
     '`^8` when the passage links it to the conclusion as (a) says, so that it brings the conclusion to Mind as a trigger does '
     '(E10); then the two quote each other. It is `^6` when the passage names an Idea it is part of (E5, E6). It may be both, '
     'or neither. Working a conclusion out by logical analysis, with no such link, is `^6`, not `^8` (Part A, A8); then the '
     '`^9` stands alone with `relative_to` `""` (rule 2; X6). Words that show this: "worked out", "checked", "ruled out", '
     '"compared", "so it had to be".')
once('    - **(c) Both happen.** Mark both, each attached to its own words.',
     '    - **(c) Both happen.** Mark both, each attached to its own words. A conclusion is written once, as one `^9`. If '
     'several triggers each bring it, each gets its own `^8` quoting the `^9`, and the `^9` quotes the one the passage names '
     'first.')
once('    - **(d) The passage does not reveal which happened.** Do not mark a clear pair. Mark an uncertain pair: both entries get `"certainty": "ambiguous"` with `"other_candidate": "reasoning"`. Uncertain entries are counted separately and never count as a clear pair. A passage that says only that the Mind "knew", "recognised", "could tell" or that the sign "meant" something is this case.',
     '    - **(d) The passage does not show that the sign brought the Idea.** A different Idea follows the sign, but no word '
     'links them. Do not mark a clear pair. Mark an uncertain pair: both entries get `"certainty": "ambiguous"` with '
     '`"other_candidate": "none"`. Uncertain entries are counted separately and never count as a clear pair. A memory placed '
     'right after a sign is this case (owner\'s answer, 2026-10-07; worked example E9).')

# 5. X5 follows the owner's answer on signs.
once('"certainty": "ambiguous", "saying": "Made me think of...", "other_candidate": "reasoning"}',
     '"certainty": "clear", "saying": "Made me think of..."}')
once('"certainty": "ambiguous", "saying": "It just clicked.", "other_candidate": "reasoning"}',
     '"certainty": "clear", "saying": "It just clicked."}')
once('Rule 15(d): the passage says she knew, not how.',
     'Rule 15(a): she knew what the soft step meant, and recognizing a sign is a clear Cause and Effect (owner\'s answer, 2026-10-07).')

# 5b. X1 follows the owner's answer on a memory that follows a sign with no linking word (rule 15(d)).
once('"relative_to": "her aunt\'s hallway", "certainty": "clear", "saying": "Triggered a memory."}',
     '"relative_to": "her aunt\'s hallway", "certainty": "ambiguous", "saying": "Triggered a memory.", "other_candidate": "none"}')
once('"relative_to": "the steam smelled of cloves", "certainty": "clear", "saying": "All at once it came back to her."}',
     '"relative_to": "the steam smelled of cloves", "certainty": "ambiguous", "saying": "All at once it came back to her.", '
     '"other_candidate": "none"}')
once('What Renate noticed is a happening that no noun names alone,',
     'No word links the smell to the hallway: the memory follows it at once. By rule 15(d) (owner\'s answer, 2026-10-07) that '
     'is an uncertain pair, with `"other_candidate": "none"`. What Renate noticed is a happening that no noun names alone,')

# 5c. X6: Tobias works the answer out by logical analysis, which Part A, A8, places under ^6, not ^8. No flag any more.
x6_support = 'He added the first two, compared the sum with the quote, and worked out that the pump was the whole difference.'
once(' {"noetic": "^9", "label": "the pump was the whole difference", "support": "%s", "mind": "Tobias", "relative_to": "", '
     '"certainty": "clear", "saying": "It just clicked.", "reached_by": "reasoning"}\n], "not_enough_information": []}' % x6_support,
     ' {"noetic": "^9", "label": "the pump was the whole difference", "support": "%s", "mind": "Tobias", "relative_to": "", '
     '"certainty": "clear", "saying": "It just clicked."}\n], "not_enough_information": ["The conclusion is worked out by '
     'analysis, not brought by a trigger, so it stands alone (rules 2 and 15(b))."]}' % x6_support)
once('Rule 15(b). No `^8`. `^6` has no Mind, so its `mind` is `""`. Every part gets the saying, one entry each.',
     'Rule 15(b). Tobias works the answer out by logical analysis ("compared", "worked out"), which Part A, A8, places '
     'under `^6`, not `^8`; so the comparison is not a Cause, and the `^9` stands alone with a note (rule 2). The owner\'s '
     'ruling of 2026-10-07 allows a Cause only where the evidence itself meets the `^8` definition (compare E10). The bill is '
     'named as the whole its lines make up, so each line is `^6`. `^6` has no Mind, so its `mind` is `""`. Every part gets '
     'the saying, one entry each.')

# 6. Worked examples, then the history of changes: the tables up to version 2.1 move out, by a pointer.
section = (HERE / 'worked_examples_section.md').read_text(encoding='utf-8').rstrip('\n')
cut = text.index('## Changes before version 2.1')
assert text.count('## Changes before version 2.1') == 1 and text.count('## Changes from version 1.2 to version 2.1') == 1
text = (text[:cut] + section + '\n\n## Changes before version 2.2\n\n'
        'The change tables up to version 2.1 stand, unchanged, at the end of `02_LABELING_GUIDE_v2_1.md` and of '
        '`02_LABELING_GUIDE_v1_2.md`. The working rules are conventions for applying the definitions in this study; they do '
        'not change a definition, and the owner may correct any of them.\n')

# 7. The change table for this version.
text = text.rstrip('\n') + '\n\n' + (
    '## Changes from version 2.1 to version 2.2\n\n'
    'Source of every change: the owner\'s answer "yes" of 2026-10-07 to the review '
    '`label_v22_draft/REALITY_ENGINEERING_REVIEW_DRAFT_v0_1.md` (sha256 '
    '`e1b45da1f8b0b3b160c158a119402cd11e128bb1481e1e930da9f074d633febb`), and his ruling of the same day on example 8 '
    '(both in `label_v22_draft/OWNER_ANSWER_REALITY_ENGINEERING_EXAMPLES_20261007.json`). Changes marked "operator" are the '
    'operator\'s way of applying those answers, made after the review rounds of 2026-10-07; the owner adopts them by signing, '
    'or corrects them. Part A, rules 1, 4, 6 to 14 and 16, and the examples P00, X2 to X4 and X7 to X11 are unchanged.\n\n'
    '| Where | Change | Review example |\n'
    '|---|---|---|\n'
    '| Status; history | New status and a note on *Reality Engineering*. The change tables up to version 2.1 move out, by a pointer | — |\n'
    '| Table, `^2` | One entry for each thing the Mind is drawn to | 1 (E1) |\n'
    '| Table, `^3` | A thing that only leaves the Mind cold is a weak `^4`, not `^3` | 2 (E2) |\n'
    '| Table, `^4` | The label says what the Idea did to the Mind, never only what the thing is like | 3 (E3) |\n'
    '| Table, `^5` | A role taken on and a routine imprinted are `^5`; one entry for each | 4 (E4) |\n'
    '| Table, `^6` | The related thing is the whole the passage says the parts make up, named in full; a list of things noticed is not `^6` | 5, 6 (E5a, E5b, E6) |\n'
    '| Table, `^9` | One trigger may bring several things; each is a `^9` of that trigger | 9 (E8) |\n'
    '| Rule 3 | The book\'s physical examples are Elements, not passage labels | 11 |\n'
    '| Table, `^8` | One entry for each trigger; things that together bring one Idea, as the joint subject of one verb, are one `^8`; with several Ideas brought, the related thing is the one the passage says it brought (operator) | 9, 8 (E8, E10) |\n'
    '| Rule 2 | Its sentence on the two rule-15 cases follows rule 15 as changed; a lone entry also covers a conclusion whose evidence is not a Cause | 8, 10 |\n'
    '| Rule 5 | Points to the owner\'s ruling where reasoning and triggering meet | 8 |\n'
    '| Rule 15(a) | Recognizing a sign is a clear `^8` and `^9`; "knew", "recognised", "could tell" and "meant" move here from (d). This answers the owner\'s open question 1 | 7 (E7) |\n'
    '| Rule 15(a), the link | A clear pair needs one sentence saying the sign brought the Idea: the sign is the subject of a verb that brings, gives or tells, or the Mind knows from the sign what it means. "came to him" and "was suddenly in" are not links (operator, applying answer 10) | 10 |\n'
    '| Rule 15(b) | The owner\'s ruling on example 8, quoted. Evidence is a Cause when the passage links it to the conclusion as (a) says; Male only inside a named whole; both, or neither. Logical analysis with no link stays `^6` (Part A, A8) | 8 (E10) |\n'
    '| The reasoning flag of version 2.1 | Gone, from the rules, the field list, X6 and the instructions: a conclusion reached by reasoning is an Effect like any other, since the owner\'s answers settle open question 2. In attempt 2 such a conclusion was counted apart; now every clear `^9` counts (operator) | 8 |\n'
    '| Rule 15(c) | A conclusion is written once, as one `^9`; with several triggers, each gets its own `^8` and the `^9` quotes the one named first (operator) | 8 |\n'
    '| Rule 15(d) | Now the case where no sentence links the sign and the Idea; other candidate `"none"` | 10 (E9) |\n'
    '| X1 | The smell and the hallway become an uncertain pair: no sentence links them (operator, applying answer 10) | 10 |\n'
    '| X5 | The pair is clear, by rule 15(a) as changed | 7 |\n'
    '| X6 | Entries as before, without the flag; the lone `^9` gains its note; the note cites Part A, A8, and the owner\'s ruling | 8 |\n'
    '| Worked examples | E1 to E10, from sealed version 2.1 passages, with the answers the owner approved | 1 to 10 |\n')
OUT.write_text(text, encoding='utf-8', newline='\n')
print('written', OUT.name, len(text.encode('utf-8')), 'bytes')
