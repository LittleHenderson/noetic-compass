"""Builds Part A of the labeling guide, version 2.1, out of the canon file. Plain Python, no model.

Nothing is retyped here. Every canon block is cut out of docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md by its heading (inside
the worked verification: by its bold label), and the owner's sentence on Mind is cut out of the owner's ruling record.
The only lines this program writes itself are the heading of Part A, its opening paragraph and the source marks, which
start with "[A". The ten definition lines keep the guide's line form: the name and the definition are copied, the
index is written the guide's way.

Usage:
  build_guide_part_a_v21.py write <out-file>
      Writes the Part A text (UTF-8, LF line ends) and prints one line per block: its size and where it starts.
  build_guide_part_a_v21.py check [<guide>]
      Compares Part A of the guide on disk (from the line that starts "## Part A" up to, not including, the line that
      starts "## Part B") with a fresh extraction. Prints exactly IDENTICAL and exits 0, or prints the first
      difference and exits 1. The seal tool calls this.
Every mode refuses (exit 2, a line that starts with REFUSED) unless the canon file has the sha256 CANON_SHA256 and
every block is found exactly as expected.
In Python: build() returns (text, blocks); check(guide) returns '' when identical, else the first difference. Both
raise Refused when the canon file is not the pinned one or a block is not found as expected. The two files Part A is
made of are CANON (pinned by CANON_SHA256) and RULING (the owner's ruling record; a change to the owner's words there
shows up as a difference in check).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
CANON = STUDY.parent.parent / 'docs' / 'CAS_FOUNDATIONAL_CLARIFICATIONS.md'
CANON_SHA256 = 'cda85c03273c47f7df9ac53258920b95ba7b3b2007b0e760856a67497f661880'
RULING = STUDY / 'OWNER_RULING_MIND_AND_COLLOQUIALISMS_20261005.json'
GUIDE = STUDY / '02_LABELING_GUIDE_v2_1.md'
PART_START, PART_END = '## Part A', '## Part B'
DASH, TICK, NL = chr(0x2014), chr(0x2713), chr(10)
DEFINITION = re.compile(r'- \*\*\^(\d) \(CO-(\d)\): (.+?)\*\* ' + DASH + ' (.+)')
MAP_ROW = re.compile(r'\| \^(\d) (.+?) \| (.+?) \| (.+) \|')
BOLD_LABEL = re.compile(r'\*\*[^*]+:\*\*')


class Refused(Exception):
    pass


def body(lines, clarification, heading):
    """(first, last) line indexes, counted from 0, of the text under the one "### heading" of one clarification,
    without the empty lines at its two ends. The text stops at the next heading or at a "---" rule."""
    tops = [i for i, line in enumerate(lines) if line.startswith('## Clarification %d:' % clarification)]
    if len(tops) != 1:
        raise Refused('the canon file holds %d headings of Clarification %d; exactly 1 is needed' % (len(tops), clarification))
    stop = next((i for i in range(tops[0] + 1, len(lines)) if lines[i].startswith('## ')), len(lines))
    heads = [i for i in range(tops[0], stop) if lines[i] == '### ' + heading]
    if len(heads) != 1:
        raise Refused('Clarification %d holds %d headings "%s"; exactly 1 is needed' % (clarification, len(heads), heading))
    first = heads[0] + 1
    last = next((i for i in range(first, stop) if lines[i].startswith('#') or lines[i] == '---'), stop) - 1
    while first <= last and not lines[first].strip():
        first += 1
    while last >= first and not lines[last].strip():
        last -= 1
    if first > last:
        raise Refused('Clarification %d, "%s": there is no text under the heading' % (clarification, heading))
    return first, last


def one_quote(lines, clarification, heading):
    """Line index of the one block-quote line under a heading."""
    first, last = body(lines, clarification, heading)
    quoted = [i for i in range(first, last + 1) if lines[i].startswith('> ')]
    if len(quoted) != 1:
        raise Refused('Clarification %d, "%s": %d quoted lines; exactly 1 is needed' % (clarification, heading, len(quoted)))
    return quoted[0]


def build():
    """(the Part A text, the blocks). A block is (mark, letter of the build order, source, first canon line, last canon
    line, copied text); canon lines are counted from 1, and are 0 for the block that comes from the ruling record."""
    raw = CANON.read_bytes()
    found = hashlib.sha256(raw).hexdigest()
    if found != CANON_SHA256:
        raise Refused('the canon file %s has sha256 %s; this program is built for %s' % (CANON, found, CANON_SHA256))
    lines, blocks = raw.decode('utf-8').split(NL), []

    def add(letter, source, first, last, text):
        where = 'canon line %d' % (first + 1) if first == last else 'canon lines %d to %d' % (first + 1, last + 1)
        blocks.append(('A%d' % (len(blocks) + 1), letter, source.replace('@', where), first + 1, last + 1, text))

    # (a) the ten definitions, in the guide's line form
    first, last = body(lines, 1, 'The Ten Noetics')
    parsed = [DEFINITION.fullmatch(line) for line in lines[first:last + 1]]
    if len(parsed) != 10 or not all(parsed) or [m.group(1) + m.group(2) for m in parsed] != ['%d%d' % (i, i) for i in range(10)]:
        raise Refused('Clarification 1, "The Ten Noetics": the text is not ten definition lines ^0 to ^9')
    definitions = [(m.group(3), m.group(4)) for m in parsed]
    add('a', 'Clarification 1, "The Ten Noetics" (@): the ten names and definitions. The line form is the guide\'s.', first, last,
        NL.join('- `^%d` **%s** %s %s' % (i, name, DASH, meaning) for i, (name, meaning) in enumerate(definitions)))

    # (b) the owner's sentence on Mind, out of the ruling record
    ruling = json.loads(RULING.read_text(encoding='utf-8'))
    typed, day = ruling['owner_text_verbatim'], ruling['received_pacific'][:10]
    sentence = typed[:typed.find('.') + 1]
    if not sentence.upper().startswith('MIND ') or not re.fullmatch(r'\d{4}-\d\d-\d\d', day):
        raise Refused('%s: owner_text_verbatim does not start with the sentence on Mind, or received_pacific has no date' % RULING.name)
    blocks.append(('A2', 'b', 'Owner\'s ruling of %s on Mind, exactly as typed (record `%s`).' % (day, RULING.name), 0, 0, '> ' + sentence))

    # (c) the principle of the Colloquialism Test
    at = one_quote(lines, 6, 'The principle')
    add('c', 'Clarification 6, "The principle" (@).', at, at, lines[at])

    # (d) the whole map of sayings and the paragraph after it
    first, last = body(lines, 6, 'Canonical colloquialism map')
    rows = [MAP_ROW.fullmatch(line) for line in lines[first + 2:first + 12]]
    if (not lines[first].startswith('| Noetic |') or not lines[first + 1].startswith('| :---') or not all(rows) or last != first + 13
            or lines[first + 12] != '' or lines[last].startswith('|')
            or [(int(m.group(1)), m.group(2), m.group(3)) for m in rows] != [(i, name, meaning) for i, (name, meaning) in enumerate(definitions)]):
        raise Refused('Clarification 6, "Canonical colloquialism map": not a table of rows ^0 to ^9 that repeats the ten '
                      'definitions of Clarification 1, followed by one paragraph')
    add('d', 'Clarification 6, "Canonical colloquialism map" (@): the whole table and the paragraph after it.', first, last,
        NL.join(lines[first:last + 1]))

    # (e) the colloquial framing of ^5
    at = one_quote(lines, 5, 'Colloquial framing')
    add('e', 'Clarification 5, "Colloquial framing" of `^5` %s (@).' % definitions[5][0], at, at, lines[at])

    # (f) the three annotations of the worked verification, each from its bold label to its end, without the check-mark sentence
    first, last = body(lines, 6, 'Worked verification of the test across all ten Noetics')
    noetic, notes = None, {}
    for i in range(first, last + 1):
        head = re.match(r'`\^(\d)` ', lines[i])
        noetic = int(head.group(1)) if head else noetic
        label = BOLD_LABEL.search(lines[i])
        if label:
            kept, tick, tail = lines[i][label.start():].rpartition(' ' + TICK)
            if not tick or noetic is None or noetic in notes or tail.count('.') != 1:
                raise Refused('canon line %d: an annotation that does not end with one check-mark sentence, or a second one for a Noetic' % (i + 1))
            notes[noetic] = (i, kept)
    if sorted(notes) != [3, 4, 8]:
        raise Refused('the worked verification holds annotations for %s; they are needed for ^3, ^4 and ^8 and no other' % sorted(notes))
    for noetic in (3, 4, 8):
        at, kept = notes[noetic]
        add('f', 'Clarification 6, worked verification of `^%d` %s (@): the annotation, from its bold label to its end.%s'
            % (noetic, definitions[noetic][0], ' "These colloquialisms" are the sayings of `^%d`.' % noetic if 'these colloquialisms' in kept else ''),
            at, at, kept)

    # (g) the Diagnostic application: the two questions and the paragraph after them
    first, last = body(lines, 6, 'Diagnostic application')
    if [line[:3] for line in lines[first:last + 1] if re.match(r'\d\. ', line)] != ['1. ', '2. ']:
        raise Refused('Clarification 6, "Diagnostic application": the two numbered questions are not there')
    add('g', 'Clarification 6, "Diagnostic application" (@): the whole section.', first, last, NL.join(lines[first:last + 1]))

    # (h) the definition governs: second bullet of "What this clarification does NOT change"
    first, last = body(lines, 6, 'What this clarification does NOT change')
    if last != first + 1 or not all(line.startswith('- ') for line in lines[first:last + 1]):
        raise Refused('Clarification 6, "What this clarification does NOT change": the text is not two bullets')
    add('h', 'Clarification 6, "What this clarification does NOT change" (@): the second bullet.', last, last, lines[last])

    out = [PART_START + ' ' + DASH + ' Canon and the owner\'s ruling on Mind (copied by a script, never retyped)', '',
           'Built by `tools/build_guide_part_a_v21.py` from `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` (sha256 `%s`). A line that starts '
           'with `[A` is a source mark written by the study. All other text of Part A is copied character for character: it is '
           'canon, except A2, which is the owner\'s. Two things of form are the study\'s: the line form of A1, and the quote sign `>` '
           'before A2.' % CANON_SHA256, '']
    for mark, _, source, _, _, text in blocks:
        out += ['[%s] %s' % (mark, source), '', text, '']
    return NL.join(out) + NL, blocks


def check(guide=GUIDE):
    """'' when Part A of the guide equals a fresh extraction, else one line that says where they first differ."""
    fresh = build()[0]
    lines = Path(guide).read_bytes().decode('utf-8').split(NL)
    starts = [i for i, line in enumerate(lines) if line.startswith(PART_START)]
    ends = [i for i, line in enumerate(lines) if line.startswith(PART_END)]
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        return 'DIFFERENT: %s does not hold one line "%s" followed by one line "%s"' % (guide, PART_START, PART_END)
    on_disk = NL.join(lines[starts[0]:ends[0]]) + NL
    if on_disk == fresh:
        return ''
    at = next((i for i, (a, b) in enumerate(zip(on_disk, fresh)) if a != b), min(len(on_disk), len(fresh)))
    return ('DIFFERENT at line %d of the guide (character %d of Part A; the guide holds %d characters there, a fresh extraction %d): '
            'the guide has %a, the fresh extraction has %a'
            % (starts[0] + 1 + on_disk[:at].count(NL), at, len(on_disk), len(fresh), on_disk[at:at + 60], fresh[at:at + 60]))


def main(argv):
    try:
        if len(argv) == 2 and argv[0] == 'write':
            text, blocks = build()
            Path(argv[1]).write_bytes(text.encode('utf-8'))
            for mark, letter, source, _, _, copied in blocks:
                print('%-3s (%s) %5d bytes  %s' % (mark, letter, len(copied.encode('utf-8')), source))
            print('canon file sha256 %s' % CANON_SHA256)
            print('Part A: %d bytes, sha256 %s, written to %s' % (len(text.encode('utf-8')), hashlib.sha256(text.encode('utf-8')).hexdigest(), argv[1]))
            return 0
        if argv[:1] == ['check'] and len(argv) <= 2:
            difference = check(argv[1] if len(argv) == 2 else GUIDE)
            print(difference or 'IDENTICAL')
            return 1 if difference else 0
    except (Refused, OSError, ValueError, KeyError) as error:
        print('REFUSED: %s' % error)
        return 2
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
