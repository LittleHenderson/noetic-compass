"""Format checker for label records, lean version 2.1. It checks FORM only, never meaning. Plain Python, no model.

Usage:
  check_labels_v21.py check <passages.json> <records.json>
      For the operator, not for a labeler: it stores nothing, so nothing checked this way counts as a try. Checks
      one record, a list of records or a whole labels file. Exit 0 = every record passes, 1 = at least one message.
  check_labels_v21.py take <passages.json> <records.json> <labels.json>
      How a labeler hands records in. Check AND log. <records.json> is the labeler's working file: one record or a
      list of records. Each record that is new or changed becomes the next try of its passage in
      <labels.json>.tries.jsonl. A passage is final once a try passes, or after its third try. <labels.json> is then
      written again: one row per final passage. Exit 0 = every passage of the passages file is final, 1 = some open.
A record (what a labeler writes for one passage):
  {"passage_id": "...", "none_of_these": false, "not_enough_information": [],
   "entries": [{"noetic": "^8", "label": "...", "support": "...", "mind": "...", "relative_to": "...", "certainty": "clear", "saying": "..."}]}
  "saying" is the everyday saying that fits the moment (guide rule 5): 2 to 20 words for ^2 to ^9, "" for ^1. Only its form is read.
  An entry may also carry "other_candidate" (only with certainty "ambiguous") and "reached_by" (only "reasoning", only on ^9).
A labels file: a list of final rows. A row is the record of the last try, or, when the third try still had a
  message, the "could not be labeled" row of failed_row(). The try log holds every try, one JSON line each.
In Python: check_record(record, passage_text) returns the list of messages; an empty list means the record passes.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

NOETICS = ['^%d' % i for i in range(1, 10)]
MAX_LABEL_WORDS, MAX_SUPPORT_SENTENCES, MAX_TRIES = 12, 4, 3
MIN_SAYING_WORDS, MAX_SAYING_WORDS = 2, 20      # the field "saying" of guide v2.1; it is never compared and never scored
RECORD_FIELDS = ('passage_id', 'none_of_these', 'entries', 'not_enough_information')
ENTRY_FIELDS = ('noetic', 'label', 'support', 'mind', 'relative_to', 'certainty', 'saying')
ALL_ENTRY_FIELDS = ENTRY_FIELDS + ('other_candidate', 'reached_by')
# relative_to per Noetic (table in guide v2.1): True = the label of the related thing, False = always "". Where it is True,
# "" is still right when the passage never names that thing (for ^8 and ^9: a lone entry, rule 2), and for a ^9 reached by reasoning (rule 15b).
NEEDS_RELATED = {'^1': False, '^2': False, '^3': False, '^5': False, '^4': True, '^6': True, '^7': True, '^8': True, '^9': True}
TITLES = {'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr', 'st'}
CLOSERS = '"' + "'" + chr(0x201d) + chr(0x2019) + ')]'      # marks that may close a sentence after its end mark
OPENERS = '"' + "'" + chr(0x201c) + chr(0x2018) + '(['      # marks that may open the next sentence
END_MARK = re.compile('[.!?]+[' + re.escape(CLOSERS) + ']*')


def sentence_spans(text):
    """(start, end) of every sentence of the passage. A sentence ends at . ! or ? (plus a closing quote or bracket)
    when what follows is the end of the text, or a space and then a capital letter or a digit (an opening quote may
    come first). A title such as "Dr." does not end a sentence."""
    spans, start = [], len(text) - len(text.lstrip())
    for mark in END_MARK.finditer(text):
        rest = text[mark.end():]
        after = rest.lstrip()
        first = after[1:2] if after[:1] and after[:1] in OPENERS else after[:1]
        word = re.findall(r'[A-Za-z0-9]+$', text[start:mark.start()])
        title = mark.group() == '.' and bool(word) and word[0].lower() in TITLES
        if not after or (len(after) < len(rest) and (first.isupper() or first.isdigit()) and not title):
            spans.append((start, mark.end()))
            start = len(text) - len(after)
    if text[start:].strip():
        spans.append((start, start + len(text[start:].rstrip())))
    return spans


def place_support(text, support):
    """(first, last) sentence numbers of the first place where the support is a run of whole sentences, else None."""
    spans = sentence_spans(text)
    for first in range(len(spans)):
        for last in range(first, len(spans)):
            if text[spans[first][0]:spans[last][1]] == support:
                return first, last
    return None


def find_whole(text, piece, start=0, end=None):
    """Index of the first place in text[start:end] where the piece stands as whole words, else -1."""
    end = len(text) if end is None else end
    at = text.find(piece, start, end) if piece else -1
    while at != -1:
        right = at + len(piece)
        if (at == 0 or not text[at - 1].isalnum()) and (right == len(text) or not text[right].isalnum()):
            return at
        at = text.find(piece, at + 1, end)
    return -1


def all_places(text, piece, whole=True):
    """(start, end) of every place where the piece stands in the passage (as whole words when whole is true)."""
    out, at = [], 0
    while piece:
        at = find_whole(text, piece, at) if whole else text.find(piece, at)
        if at == -1:
            break
        out.append((at, at + len(piece)))
        at += 1
    return out


def locate(text, support, label):
    """(start, end) of the label in the passage: its first whole-word place inside the placed support, else None."""
    placed = place_support(text, support)
    if placed is None:
        return None
    spans = sentence_spans(text)
    at = find_whole(text, label, spans[placed[0]][0], spans[placed[1]][1])
    return None if at == -1 else (at, at + len(label))


def copy_fault(text, piece):
    """Says where a quote stops being a copy of the passage, so the labeler can find the spot."""
    low, high = 0, len(piece)
    while low < high:
        middle = (low + high + 1) // 2
        low, high = (middle, high) if piece[:middle] in text else (low, middle - 1)
    if low == 0:
        return 'its first characters "%s" are nowhere in the passage' % piece[:20]
    return 'it follows the passage up to "%s" and then differs at "%s"' % (piece[max(0, low - 25):low], piece[low:low + 15])


def quote_faults(name, value, text):
    """Faults of a label or a relative_to as a quote: exact copy, whole words, 1 to 12 words."""
    if value == '':
        return ['%s is empty' % name]
    faults = []
    if value != value.strip():
        faults.append('%s has a space at its start or end' % name)
    elif value not in text:
        faults.append('%s is not an exact copy of passage text: %s' % (name, copy_fault(text, value)))
    elif find_whole(text, value) == -1:
        faults.append('%s must start and end at whole words of the passage' % name)
    if not 1 <= len(value.split()) <= MAX_LABEL_WORDS:
        faults.append('%s has %d words; it must have 1 to %d' % (name, len(value.split()), MAX_LABEL_WORDS))
    return faults


def entry_faults(entry, text):
    """Faults of one entry taken by itself."""
    if not isinstance(entry, dict):
        return ['is not a JSON object']
    faults = ['field "%s" is missing' % f for f in ENTRY_FIELDS if f not in entry]
    faults += ['unknown field "%s"; the fields are %s' % (f, ', '.join(ALL_ENTRY_FIELDS)) for f in entry if f not in ALL_ENTRY_FIELDS]
    faults += ['field "%s" must be text in double quotes' % f for f in ALL_ENTRY_FIELDS if f in entry and not isinstance(entry[f], str)]
    if faults:
        return faults
    noetic, label, support = entry['noetic'], entry['label'], entry['support']
    mind, related, certainty = entry['mind'], entry['relative_to'], entry['certainty']
    if noetic not in NOETICS:
        faults.append('noetic "%s" is not one of "^1" to "^9"' % noetic)
    label_faults = quote_faults('label', label, text)
    faults += label_faults
    placed = place_support(text, support)
    if placed is None and support not in text:
        faults.append('support is not an exact copy of passage text: ' + copy_fault(text, support))
    elif placed is None:
        faults.append('support must be whole sentences: start at the first word of a sentence and stop at an end mark')
    elif placed[1] - placed[0] + 1 > MAX_SUPPORT_SENTENCES:
        faults.append('support has %d sentences; at most %d' % (placed[1] - placed[0] + 1, MAX_SUPPORT_SENTENCES))
    if not label_faults and label not in support:
        faults.append('label is not inside support')
    elif not label_faults and placed is not None and locate(text, support, label) is None:
        faults.append('label is inside support only as part of a longer word')
    elif noetic == '^1' and not label_faults and placed is not None and locate(text, support, label)[0] != find_whole(text, label):
        faults.append('the support of a ^1 entry must hold the first place this name stands in the passage (rule 4)')
    if noetic == '^1' and mind != label:
        faults.append('the mind of a ^1 entry must equal its own label, character for character')
    elif noetic == '^6' and mind != '':
        faults.append('mind must be "" for ^6')
    elif noetic in NOETICS and noetic not in ('^1', '^6') and mind == '':
        faults.append('mind is empty; write the label of this record\'s ^1 entry for that Mind')
    if certainty not in ('clear', 'ambiguous'):
        faults.append('certainty must be "clear" or "ambiguous"')
    other = entry.get('other_candidate')
    if certainty == 'ambiguous' and other not in NOETICS + ['none', 'reasoning']:
        faults.append('an ambiguous entry needs other_candidate: "^1" to "^9", "none" or "reasoning"')
    elif certainty != 'ambiguous' and other is not None:
        faults.append('other_candidate is only for an entry with certainty "ambiguous"; take the field out')
    reached = entry.get('reached_by')
    if reached is not None and reached != 'reasoning':
        faults.append('reached_by may only be "reasoning"; otherwise leave the field out')
    elif reached is not None and noetic != '^9':
        faults.append('reached_by is only for ^9 (rule 15b); take the field out')
    reasoning = reached == 'reasoning' and noetic == '^9'
    if noetic in NEEDS_RELATED:      # a ^8 or ^9 with relative_to "" and no reached_by is a lone entry (guide rule 2): it passes
        if reasoning and related != '':
            faults.append('a ^9 with reached_by "reasoning" must have relative_to ""')
        elif not NEEDS_RELATED[noetic] and related != '':
            faults.append('relative_to must be "" for %s' % noetic)
    if related != '':
        faults += quote_faults('relative_to', related, text)
    words = len(entry['saying'].split())     # form only: whether the saying fits the moment is not read
    if noetic == '^1' and entry['saying'] != '':
        faults.append('saying must be "" for ^1')
    elif noetic in NOETICS[1:] and not MIN_SAYING_WORDS <= words <= MAX_SAYING_WORDS:
        faults.append('saying %s; %s needs the everyday saying that fits this moment, %d to %d words (rule 5)'
                      % ('has %d word%s' % (words, 's' * (words != 1)) if words else 'is empty', noetic, MIN_SAYING_WORDS, MAX_SAYING_WORDS))
    return faults


def check_parts(record, passage_text, passage_id=None):
    """(messages about the record, one list of messages per entry). Everything empty = the record passes."""
    if not isinstance(record, dict):
        return ['record: the reply is not one JSON object'], []
    rec = ['record: field "%s" is missing' % f for f in RECORD_FIELDS if f not in record]
    if 'labeler_failed' in record:
        rec.append('record: "labeler_failed" is written by the tools only, never by a labeler; take it out')
    if passage_id is not None and 'passage_id' in record and record['passage_id'] != passage_id:
        rec.append('record: passage_id is "%s"; it must be "%s"' % (record['passage_id'], passage_id))
    if 'none_of_these' in record and not isinstance(record['none_of_these'], bool):
        rec.append('record: none_of_these must be true or false')
    notes = record.get('not_enough_information')
    if 'not_enough_information' in record and not (isinstance(notes, list) and all(isinstance(n, str) for n in notes)):
        rec.append('record: not_enough_information must be a list of short notes in double quotes')
    entries = record.get('entries')
    if not isinstance(entries, list):
        return rec + (['record: entries must be a list'] if 'entries' in record else []), []
    if record.get('none_of_these') is True and entries:
        rec.append('record: none_of_these is true but there are entries; make it false or take the entries out')
    per = [entry_faults(entry, passage_text) for entry in entries]
    groups = {}      # (noetic, label, mind, relative_to) -> the entries that carry it
    for index, entry in enumerate(entries):
        if isinstance(entry, dict) and all(isinstance(entry.get(f), str) for f in ('noetic', 'label', 'mind')):
            groups.setdefault((entry['noetic'], entry['label'], entry['mind'], str(entry.get('relative_to'))), []).append(index)
    repeats = {i: [m + 1 for m in members if m != i] for members in groups.values() if len(members) > 1 for i in members}
    minds = {}       # label of a ^1 entry -> [does one such entry pass, number of the first such entry]
    for (noetic, label, _, _), members in groups.items():
        if noetic == '^1':
            minds.setdefault(label, [False, members[0] + 1])
            minds[label][0] = minds[label][0] or any(not per[m] and m not in repeats for m in members)
    for (noetic, _, mind, _), members in groups.items():
        for index in members:
            if index in repeats:
                per[index].append('has the same noetic, label, mind and relative_to as entry %s; keep only one of them'
                                  % ', '.join(str(m) for m in repeats[index]))
            if noetic in NOETICS and noetic not in ('^1', '^6') and mind != '' and mind not in minds:
                per[index].append('mind "%s" is not the label of a ^1 entry of this record; add that ^1 entry, or copy '
                                  'its label character for character' % mind)
            elif noetic in NOETICS and noetic not in ('^1', '^6') and mind != '' and not minds[mind][0]:
                per[index].append('its Mind entry (entry %d) does not pass; correct that entry first' % minds[mind][1])
    return rec, [['entry %d: %s' % (index + 1, fault) for fault in faults] for index, faults in enumerate(per)]


def check_record(record, passage_text, passage_id=None):
    """Every message for one record, in order. An empty list means the record passes."""
    rec, per = check_parts(record, passage_text, passage_id)
    return rec + [message for faults in per for message in faults]


def count_by_noetic(record):
    """How many different entries (by label, mind and relative_to) a try holds for each Noetic."""
    entries = record.get('entries') if isinstance(record, dict) else None
    seen = {(e['noetic'], str(e.get('label')), str(e.get('mind')), str(e.get('relative_to'))) for e in (entries if isinstance(entries, list) else [])
            if isinstance(e, dict) and e.get('noetic') in NOETICS}
    return {noetic: sum(1 for item in seen if item[0] == noetic) for noetic in {item[0] for item in seen}}


def try_state(tries, passage_text, passage_id):
    """Where a passage stands after its tries (the records, in the order they were handed in).
    LABELED = the last try has no message. NOT_LABELED = three tries and the last still has a message.
    OPEN = not final yet. BROKEN = more than three tries, or a try made after a try that passed."""
    passed = [not check_record(record, passage_text, passage_id) for record in tries]
    if len(tries) > MAX_TRIES or any(passed[:-1]):
        return 'BROKEN'
    if tries and passed[-1]:
        return 'LABELED'
    return 'NOT_LABELED' if len(tries) == MAX_TRIES else 'OPEN'


def withdrawn(tries):
    """Per Noetic: how many more entries (different by label, mind and relative_to) an earlier try held than the last holds."""
    last, out = count_by_noetic(tries[-1]) if tries else {}, {}
    for earlier in tries[:-1]:
        for noetic, count in count_by_noetic(earlier).items():
            if count - last.get(noetic, 0) > out.get(noetic, 0):
                out[noetic] = count - last.get(noetic, 0)
    return out


def failed_row(passage_id, tries):
    """The row of a passage that could not be labeled after three tries (the row the team B tool writes too)."""
    return {'passage_id': passage_id, 'none_of_these': False, 'entries': [], 'not_enough_information': [],
            'labeler_failed': True, 'tries': tries}


def read_tries(path):
    """A try log (.jsonl, one line per try) as {passage_id: [record of try 1, record of try 2, ...]}."""
    found = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get('event') == 'try':
            found.setdefault(event.get('passage_id'), []).append(event)
    return {pid: [e.get('record') for e in sorted(events, key=lambda e: e.get('n', 0))] for pid, events in found.items()}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    part = Path(str(path) + '.partial')
    part.write_text(json.dumps(value, indent=1, ensure_ascii=False) + chr(10), encoding='utf-8', newline=chr(10))
    os.replace(part, path)


def main(argv):
    if len(argv) != {'check': 3, 'take': 4}.get(argv[0] if argv else '', -1):
        print(__doc__)
        return 2
    take, passages = argv[0] == 'take', {p['id']: p['text'] for p in read_json(argv[1])}
    try:
        given = read_json(argv[2])
    except ValueError as error:
        print('%s is not JSON (%s). Nothing was read. Write one record, or a list of records, and run this again.' % (argv[2], error))
        return 2
    log_path = Path(argv[3] + '.tries.jsonl') if take else None
    tries = read_tries(log_path) if take and log_path.exists() else {}
    with_messages = 0
    for record in given if isinstance(given, list) else [given]:
        pid, note = record.get('passage_id') if isinstance(record, dict) else None, ''
        if pid not in passages:
            print('%r: this passage_id is not in %s; the record is not read' % (pid, argv[1]))
            with_messages += 1
            continue
        if take:
            past = tries.setdefault(pid, [])
            state = try_state(past, passages[pid], pid)
            if state == 'OPEN' and record not in past[-1:]:
                past.append(record)
                event = {'event': 'try', 'passage_id': pid, 'n': len(past), 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                         'record': record, 'messages': check_record(record, passages[pid], pid)}
                with open(log_path, 'a', encoding='utf-8', newline=chr(10)) as log:
                    log.write(json.dumps(event, ensure_ascii=False) + chr(10))
                state = try_state(past, passages[pid], pid)
            elif state != 'OPEN' and record != past[-1]:
                note = '. This passage is final: the changed record was NOT taken'
            record, note = past[-1], ' (try %d of %d, %s%s)' % (len(past), MAX_TRIES, 'final' if state != 'OPEN' else 'not final', note)
        failed = isinstance(record, dict) and record.get('labeler_failed') is True
        messages = ['could not be labeled after three tries'] if failed else check_record(record, passages[pid], pid)
        with_messages += bool(messages)
        print('%s: %s%s' % (pid, 'passes' if not messages else '%d message(s)' % len(messages), note))
        for message in messages:
            print('   ' + message)
    if not take:
        return 1 if with_messages else 0
    states = {pid: try_state(tries.get(pid, []), text, pid) for pid, text in passages.items()}
    write_json(argv[3], [tries[pid][-1] if states[pid] == 'LABELED' else failed_row(pid, len(tries[pid]))
                         for pid in passages if states[pid] in ('LABELED', 'NOT_LABELED')])
    count = {name: sum(1 for state in states.values() if state == name) for name in ('LABELED', 'NOT_LABELED', 'OPEN')}
    print('%s written: %d labeled, %d could not be labeled, %d still open (correct them and run this again)'
          % (argv[3], count['LABELED'], count['NOT_LABELED'], count['OPEN']))
    return 1 if count['OPEN'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
