"""Option B, program 2: the role notes (ROLE, MIXED, QUOTES-ONLY) and the FILLER base text.

Plan: 08_OPTION_B_PLAN_v1_0.md, sections 6 and 11.2. File formats: optionb/FILE_FORMATS.md, section 3.
Every wording, every line template and every seed is read from optionb/PLAN_CONSTANTS.json.

A program builds every note. No model writes one. Nobody edits one. No label is changed.
Plain Python, standard library only. No model, no network, no key.

Canon rule. The Noetic definition lines are read, when this program runs, from Part A of
02_LABELING_GUIDE_v1_2.md, after the file's sha256 has been checked. They are copied character for
character. This file holds no definition text. Noetics are written ^1 to ^9.

The sayings lines (amendment A13; plan section 6; FILE_FORMATS.md section 3.1). Right after each
canon line comes one line with that Noetic's canonical sayings: the word Sayings, a colon, one space,
then the third cell of that Noetic's row in the table under the heading "Canonical colloquialism map"
of docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md, copied character for character. The table is read from
the file when this program runs. This file holds no saying. The program writes nothing unless
  - the file has the size and the sha256 pinned in the plan constants (sources.canonical_sayings);
  - the table has one row for each of ^0 to ^9, ten rows in all;
  - in each row the definition cell equals, character for character, the definition of that Noetic's
    line in Part A of the guide. If the two differ the program stops and reports. Nobody picks one.
A13 is the operator's reading of an owner ruling, applied to a place the owner did not name. The
owner may strike it. The owner's sentence about Mind is not printed in any note.

What it builds, for each of the eligible passages
  ROLE         For each Noetic that appears, in number order: its canon line, then its sayings line.
               Then one line per agreed
               entry: the ^1 entries first, then the others, each part in passage order. A line holds
               the short label, then the Mind and the related thing where the guide gives that Noetic
               such a field, then the full supporting quote. A supporting quote that was already
               printed in the same note is replaced by: same as for "<earlier label>".
  MIXED        The ROLE note with every tag swapped by the fixed table in the constants. Each swapped
               tag brings its own canon line and its own sayings line. Labels, Minds, related things,
               supporting quotes and the order of the lines stay as they are.
  QUOTES-ONLY  One line per ROLE entry, in the same order: the label and the supporting quote.
               No Noetic, no name, no Mind, no related thing, no canon line, no sayings line.
  FILLER       The same one sentence for every passage. It is the constant prompt.filler_sentence.
               FILE_FORMATS.md gives it no field in role_notes.json, so it is not stored there; it is
               screened and its size is printed. filler_base_text() returns it.
  The text has no heading of its own and no padding line. The job adds both.

The stand-in rule (plan section 6), per agreed pair of entries
  short label          the shorter of the two teams' quotes, by characters; on a tie team A's
  Mind, related thing  the shorter of the two teams' texts that is not empty; on a tie team A's
  supporting quote     from the start of the sentence that holds the earlier quote start to the end
                       of the sentence that holds the later quote end; each quote is found by its
                       first place in the passage

It also writes a seeded sample of 20 ROLE notes for the owner, twice: as
notes_role/owner_sample_20.json (the file format) and as OWNER_SAMPLE_ROLE_NOTES.md (to read).

Usage
  ob_role_notes.py                    Real run. Needs seal step 1. Reads optionb/elig/eligibility.json.
                                      Writes optionb/notes_role/ and optionb/OWNER_SAMPLE_ROLE_NOTES.md.
                                      Refused once seal step 2 exists.
  ob_role_notes.py --dry-run DIR      Dry run. Needs no seal. Reads DIR/elig/eligibility.json.
                                      Writes DIR/notes_role/ and DIR/OWNER_SAMPLE_ROLE_NOTES.md.
                                      DIR must not be the real optionb folder.
  --owner-sample-md FILE              Write the readable sample to FILE instead.

Exit code 0: built and written. Exit code 2: STOPPED; the reason is printed; nothing was written.
"""
import argparse
import json
import random
import re
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True   # leave no cache folder beside the frozen tools

TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import ob_eligibility as base   # noqa: E402  (helpers only: Stop, read_pinned, load_constants, write_json, sha256, in_practice)
import ob_seal                  # noqa: E402  (the seal checks)

PROGRAM = 'tools/ob_role_notes.py'
SCHEMA_NOTES = 'casalescence/optionb/role_notes/v1'
SCHEMA_SAMPLE = 'casalescence/optionb/owner_role_note_sample/v1'
SCHEMA_ELIGIBILITY = 'casalescence/optionb/eligibility/v1'
OWNER_MD_NAME = 'OWNER_SAMPLE_ROLE_NOTES.md'
MIND_NOETIC = '^1'            # the plan: "The ^1 lines come first."
PLACEHOLDER = re.compile(r'<<([A-Z_]+)>>')
Stop = base.Stop


# ----------------------------------------------------------------------------- small helpers

def fill(template, values):
    """Plain replacement of <<NAME>> placeholders, in one pass. Never str.format: the texts may hold curly brackets."""
    def swap(found):
        name = found.group(1)
        if name not in values:
            raise Stop('TEMPLATE_PLACEHOLDER_UNKNOWN', '<<%s>> in %r' % (name, template))
        return values[name]
    return PLACEHOLDER.sub(swap, template)


def noetic_number(noetic):
    return int(noetic[1:])


def filler_base_text(constants):
    """The FILLER notes text. It is the same for every passage."""
    return constants['prompt']['filler_sentence']


def words_by_space(text):
    return len(text.split())


# ----------------------------------------------------------------------------- the canon lines

def guide_definitions(project, constants):
    """Every definition line of guide Part A, read from the file. Returns ([(noetic, name, definition)], input record)."""
    rules = constants['role_notes']
    data, record = base.read_pinned(project, constants, 'labeling_guide')
    lines = data.decode('utf-8').split(chr(10))
    starts = [i for i, line in enumerate(lines) if line.startswith(rules['canon_section_start'])]
    if len(starts) != 1:
        raise Stop('CANON_SECTION_NOT_FOUND', 'the guide does not hold exactly one line that starts with %r' % rules['canon_section_start'])
    ends = [i for i, line in enumerate(lines) if i > starts[0] and line.startswith(rules['canon_section_end'])]
    if not ends:
        raise Stop('CANON_SECTION_NOT_FOUND', 'no line starts with %r after Part A' % rules['canon_section_end'])
    pattern = re.compile(rules['canon_line_regex'])
    found = [m.groups() for m in (pattern.match(line) for line in lines[starts[0]:ends[0]]) if m]
    noetics = [noetic for noetic, _, _ in found]
    if len(found) != rules['canon_lines_expected'] or len(set(noetics)) != len(noetics):
        raise Stop('CANON_LINES_NOT_AS_EXPECTED', 'Part A gave %d definition lines; the plan expects %d' % (len(found), rules['canon_lines_expected']))
    return found, record


def read_canon(project, constants):
    """The canon lines of guide Part A, copied from the file. Returns (note lines, names, input record)."""
    rules = constants['role_notes']
    found, record = guide_definitions(project, constants)
    note_lines, names = {}, {}
    for noetic, name, definition in found:
        if noetic in rules['canon_noetics_used']:
            note_lines[noetic] = fill(rules['canon_note_line'], {'NOETIC': noetic, 'NAME': name, 'DEFINITION': definition})
            names[noetic] = name
    missing = [n for n in rules['canon_noetics_used'] if n not in note_lines]
    if missing:
        raise Stop('CANON_LINES_NOT_AS_EXPECTED', 'Part A has no line for %s' % ', '.join(missing))
    return note_lines, names, record


# ----------------------------------------------------------------------------- the sayings lines (amendment A13)

def read_sayings(project, constants):
    """The sayings lines, copied from the table of the canonical sayings. Returns (note lines, input record).

    Nothing is retyped. The table is read from the pinned file. The three refusals of plan section 6:
    the file does not have its pinned size and sha256 (read_pinned stops); the table does not give one
    row for each of ^0 to ^9; a definition cell is not, character for character, the definition of
    that Noetic's line in Part A of the guide. On a difference nobody picks one of the two texts.
    """
    rules = constants['role_notes']
    data, record = base.read_pinned(project, constants, rules['sayings_source_key'])
    lines = data.decode('utf-8').split(chr(10))
    starts = [i for i, line in enumerate(lines) if line.startswith(rules['sayings_section_start'])]
    if len(starts) != 1:
        raise Stop('SAYINGS_TABLE_NOT_FOUND', 'the file of the sayings does not hold exactly one line that starts with %r' % rules['sayings_section_start'])
    ends = [i for i, line in enumerate(lines) if i > starts[0] and line.startswith(rules['sayings_section_end'])]
    if not ends:
        raise Stop('SAYINGS_TABLE_NOT_FOUND', 'no line starts with %r after the table of the sayings' % rules['sayings_section_end'])
    pattern, group = re.compile(rules['sayings_row_regex']), rules['sayings_row_groups']
    rows = [m for m in (pattern.match(line) for line in lines[starts[0]:ends[0]]) if m]
    by_noetic = {m.group(group['noetic']): m for m in rows}
    guide, _ = guide_definitions(project, constants)
    in_guide = {noetic: definition for noetic, _, definition in guide}
    if len(rows) != rules['sayings_rows_expected'] or len(by_noetic) != len(rows) or set(by_noetic) != set(in_guide):
        raise Stop('SAYINGS_ROWS_NOT_AS_EXPECTED', 'the table of the sayings gave %d rows for %s; the plan expects %d rows, one for each of %s'
                   % (len(rows), ', '.join(sorted(by_noetic)) or 'no Noetic', rules['sayings_rows_expected'], ', '.join(sorted(in_guide))))
    differ = [noetic for noetic in sorted(by_noetic) if by_noetic[noetic].group(group['definition']) != in_guide[noetic]]
    if differ:
        raise Stop('SAYINGS_DEFINITION_DIFFERS_FROM_THE_GUIDE', 'for %s the definition cell of the table of the sayings is not, character for character, '
                   'the definition in Part A of the guide. The two must agree. Nobody picks one of the two texts. Report this'
                   % ', '.join(differ))
    if list(rules['sayings_noetics_used']) != list(rules['canon_noetics_used']) or any(n not in by_noetic for n in rules['sayings_noetics_used']):
        raise Stop('CONSTANTS_SHAPE', 'role_notes.sayings_noetics_used is not role_notes.canon_noetics_used, or it names a Noetic the table has no row for')
    note_lines = {}
    for noetic in rules['sayings_noetics_used']:
        cell = by_noetic[noetic].group(group['sayings'])
        note_lines[noetic] = fill(rules['sayings_note_line'], {'SAYINGS': cell})
        if not note_lines[noetic].startswith(rules['sayings_frame_word'] + ':') or not note_lines[noetic].endswith(cell):
            raise Stop('CONSTANTS_SHAPE', 'role_notes.sayings_note_line does not start with the frame word %r and end with the sayings cell'
                       % rules['sayings_frame_word'])
    return note_lines, record


# ----------------------------------------------------------------------------- sentences

def sentence_spans(text, rules):
    """(start, end) of each sentence, by the fixed sentence rule of the plan, section 6."""
    end_pattern = re.compile(rules['sentence_end_regex'])
    guard = re.compile(r"(?<![A-Za-z0-9'])(?:%s)$" % '|'.join(re.escape(w) for w in rules['sentence_end_not_after']))
    spans, start = [], 0
    while start < len(text) and text[start].isspace():
        start += 1
    for found in end_pattern.finditer(text):
        marks = re.match(r'[.!?]+', found.group(0)).group(0)
        if marks == '.' and guard.search(text[:found.start()]):
            continue                      # a single full stop right after Mr, Dr, ... does not end a sentence
        if found.end() <= start:
            continue
        spans.append((start, found.end()))
        start = found.end()
        while start < len(text) and text[start].isspace():
            start += 1
    if start < len(text):
        spans.append((start, len(text.rstrip())))
    if not spans:
        raise Stop('PASSAGE_HAS_NO_SENTENCE', repr(text[:60]))
    return spans


def sentence_at(spans, position):
    """The index of the sentence that holds a character position."""
    index = 0
    for place, (start, _) in enumerate(spans):
        if start <= position:
            index = place
    return index


# ----------------------------------------------------------------------------- one passage

def shorter(a, b):
    """The shorter text by characters; on a tie team A's."""
    return a if len(a) <= len(b) else b


def shorter_not_empty(a, b):
    """The shorter of the two that is not empty; on a tie team A's; '' when both are empty."""
    if a and b:
        return shorter(a, b)
    return a or b


def entry_line(rules, entry, noetic, name, blank=False, quotes_only=False):
    """One note line. With blank=True every quoted passage part is emptied (for the answer-leak screen)."""
    def part(text):
        return '' if blank else text

    if quotes_only:
        line = fill(rules['quotes_only_line_start'], {'LABEL': part(entry['label'])})
    else:
        template = rules['line_mind_entry'] if entry['supporting_quote'] is None else rules['line_entry_start']
        line = fill(template, {'NOETIC': noetic, 'NAME': name, 'LABEL': part(entry['label'])})
        if entry['mind']:
            line += fill(rules['line_part_mind'], {'MIND': part(entry['mind'])})
        if entry['relative_to']:
            line += fill(rules['line_part_relative'], {'RELATIVE_TO': part(entry['relative_to'])})
    if entry['supporting_quote'] is not None:
        if entry['same_as_label'] is not None:
            line += fill(rules['line_part_same_as'], {'EARLIER_LABEL': part(entry['same_as_label'])})
        else:
            line += fill(rules['line_part_quote'], {'QUOTE': part(entry['supporting_quote'])})
    return line


def build_passage(constants, canon_lines, sayings_lines, names, passage):
    """The three notes of one eligible passage, and the facts about them. Returns (record, extras).

    canon_lines comes from read_canon() and sayings_lines from read_sayings(). The head of a ROLE or
    MIXED note is, for each Noetic shown, in number order: its canon line, then its sayings line
    (amendment A13). A head line is frame text: it is never blanked.
    """
    rules = constants['role_notes']
    printed_fields = constants['eligibility']['fields_printed']
    swap = rules['mixed_swap_table']
    text = passage['text']
    spans = sentence_spans(text, rules)
    entries, covered = [], set()
    for pair in passage['entries']['agreed']:
        noetic, a, b = pair['noetic'], pair['a'], pair['b']
        place_a, place_b = text.find(a['words']), text.find(b['words'])
        if place_a < 0 or place_b < 0:
            raise Stop('QUOTE_NOT_IN_PASSAGE', '%s %s' % (passage['id'], noetic))
        quote, first_sentence, last_sentence = None, None, None
        if not (noetic == MIND_NOETIC and rules['mind_entries_have_no_supporting_quote']):
            first_sentence = sentence_at(spans, min(place_a, place_b))
            last_sentence = sentence_at(spans, max(place_a + len(a['words']), place_b + len(b['words'])) - 1)
            quote = text[spans[first_sentence][0]:spans[last_sentence][1]]
            covered.update(range(first_sentence, last_sentence + 1))
        entries.append({
            'noetic': noetic, 'name': names[noetic],
            'mixed_noetic': swap[noetic], 'mixed_name': names[swap[noetic]],
            'label': shorter(a['words'], b['words']),
            'mind': shorter_not_empty(a['mind'], b['mind']) if 'mind' in printed_fields[noetic] else '',
            'relative_to': shorter_not_empty(a['relative_to'], b['relative_to']) if 'relative_to' in printed_fields[noetic] else '',
            'supporting_quote': quote, 'same_as_label': None,
            'offset': min(place_a, place_b), 'a_index': a['index'], 'b_index': b['index'],
        })
    # Note order: the ^1 entries first, then the others; inside each part by place in the passage,
    # then by Noetic number, then by team A's entry order.
    entries.sort(key=lambda e: (0 if e['noetic'] == MIND_NOETIC else 1, e['offset'], noetic_number(e['noetic']), e['a_index']))
    printed = {}
    for entry in entries:
        quote = entry['supporting_quote']
        if quote is None:
            continue
        if quote in printed:
            entry['same_as_label'] = printed[quote]
        else:
            printed[quote] = entry['label']

    def note(blank, kind):
        if kind == 'quotes_only':
            return chr(10).join(entry_line(rules, e, None, None, blank, quotes_only=True) for e in entries)
        tag, tag_name = ('noetic', 'name') if kind == 'role' else ('mixed_noetic', 'mixed_name')
        shown = sorted({e[tag] for e in entries}, key=noetic_number)
        head = [line for n in shown for line in (canon_lines[n], sayings_lines[n])]
        return chr(10).join(head + [entry_line(rules, e, e[tag], e[tag_name], blank) for e in entries])

    role_text, mixed_text, quotes_only_text = note(False, 'role'), note(False, 'mixed'), note(False, 'quotes_only')
    frames = {'role': note(True, 'role'), 'mixed': note(True, 'mixed'), 'quotes_only': note(True, 'quotes_only')}
    if any(chr(13) in built for built in (role_text, mixed_text, quotes_only_text)):
        raise Stop('NOTE_TEXT_NOT_CLEAN', '%s: a note holds a CR' % passage['id'])
    if any('CO-' in frame for frame in frames.values()):
        raise Stop('NOTE_TEXT_NOT_CLEAN', '%s: the frame text holds CO- notation' % passage['id'])
    word_pattern = constants['question_rules']['word_sequence_regex']
    size_pattern = rules['size_count_regex']
    record = {
        'id': passage['id'],
        'entries': entries,
        'role_text': role_text, 'mixed_text': mixed_text, 'quotes_only_text': quotes_only_text,
        'frame_blanked': frames,
        'size': {'role_size_count': len(re.findall(size_pattern, role_text)), 'role_words': len(re.findall(word_pattern, role_text)),
                 'passage_size_count': len(re.findall(size_pattern, text)), 'passage_words': len(re.findall(word_pattern, text))},
        'left_out': {'only_a': passage['only_a'], 'only_b': passage['only_b']},
    }
    extras = {'sentences': len(spans), 'sentences_quoted': len(covered),
              'sayings_lines_role': len({e['noetic'] for e in entries}), 'sayings_lines_mixed': len({e['mixed_noetic'] for e in entries}),
              'entries_besides_mind': sum(1 for e in entries if e['noetic'] != MIND_NOETIC),
              'same_as_lines': sum(1 for e in entries if e['same_as_label'] is not None),
              'fields_not_passage_text': sum(1 for e in entries for f in ('mind', 'relative_to') if e[f] and e[f] not in text)}
    return record, extras


# ----------------------------------------------------------------------------- the answer-leak patterns

def screen_hits(constants, text):
    """Rule (a) and rule (d) of the answer-leak screen on one text. Rules (b) and (c) need a question."""
    hits = []
    for place, pattern in enumerate(constants['leak_screen']['rule_a_patterns']):
        hits += ['a%d:%s' % (place + 1, found.group(0)) for found in re.finditer(pattern, text)]
    for word in constants['forbidden_words']['leak_screen_words']['words']:
        hits += ['d:%s' % found.group(0) for found in re.finditer(r'\b%s\b' % re.escape(word), text, re.I)]
    return hits


# ----------------------------------------------------------------------------- the report

def spread(numbers):
    return '%d / %s / %d' % (min(numbers), ('%g' % statistics.median(numbers)), max(numbers))


def design_text_numbers(project, constants):
    """Three numbers the design states about the notes. Read from the pinned design file. None if not found."""
    try:
        data, record = base.read_pinned(project, constants, 'design')
    except Stop:
        return {}, None
    spec = json.loads(data.decode('utf-8'))['spec']
    out = {}
    found = re.search(r'reproduced by a reviewer as ([0-9.]+)%', spec['source_passages_and_role_descriptions'])
    out['sentence_share_text'] = found.group(1) if found else None
    found = re.search(r'of the (\d+) final role notes, (\d+) quote exactly one passage sentence and (\d+) hold exactly one entry besides \^1', spec['task_design'])
    out['final_one_sentence'] = int(found.group(2)) if found else None
    out['final_one_entry'] = int(found.group(3)) if found else None
    return out, record


def measure(constants, records, extras, eligibility_passages):
    """Every number of the count report, as one dict. All REAL: measured on the notes just built."""
    word_pattern = constants['question_rules']['word_sequence_regex']
    size_pattern = constants['role_notes']['size_count_regex']
    start = constants['split']['practice_setting_count_start']
    by_id = {p['id']: p for p in eligibility_passages}
    out = {'notes': len(records), 'lengths': {}, 'screen_frame': {}, 'screen_full_text': {}}
    for group, key in (('ROLE', 'role'), ('MIXED', 'mixed'), ('QUOTES-ONLY', 'quotes_only')):
        texts = [r[key + '_text'] for r in records]
        frames = [r['frame_blanked'][key] for r in records]
        out['lengths'][group] = {
            'words_by_white_space': spread([words_by_space(t) for t in texts]),
            'words_by_word_regex': spread([len(re.findall(word_pattern, t)) for t in texts]),
            'size_count': spread([len(re.findall(size_pattern, t)) for t in texts]),
            'characters': spread([len(t) for t in texts]),
            'lines': spread([t.count(chr(10)) + 1 for t in texts]),
        }
        hit_frames = [(r['id'], screen_hits(constants, f)) for r, f in zip(records, frames)]
        hit_full = [(r['id'], screen_hits(constants, t)) for r, t in zip(records, texts)]
        out['screen_frame'][group] = {'notes_hit': sum(1 for _, h in hit_frames if h), 'ids': [i for i, h in hit_frames if h]}
        out['screen_full_text'][group] = {'notes_matched': sum(1 for _, h in hit_full if h), 'ids': [i for i, h in hit_full if h]}
    filler = filler_base_text(constants)
    out['filler'] = {'text': filler, 'words_by_white_space': words_by_space(filler), 'size_count': len(re.findall(size_pattern, filler)),
                     'screen_hits': screen_hits(constants, filler)}
    passage_words = [words_by_space(by_id[r['id']]['text']) for r in records]
    out['passage_words_by_white_space'] = spread(passage_words)
    out['role_words_over_passage_words_percent'] = spread([100 * words_by_space(r['role_text']) // w for r, w in zip(records, passage_words)])
    shares = [x['sentences_quoted'] / x['sentences'] for x in extras]
    out['sentence_share_text'] = '%.1f' % (100 * sum(shares) / len(shares))
    final = [x for r, x in zip(records, extras)
             if not by_id[r['id']]['barred'] and not base.in_practice(by_id[r['id']]['setting_role'], start, start)]
    out['final_notes'] = len(final)
    out['final_one_sentence'] = sum(1 for x in final if x['sentences_quoted'] == 1)
    out['final_one_entry'] = sum(1 for x in final if x['entries_besides_mind'] == 1)
    out['sayings_lines_role'] = sum(x['sayings_lines_role'] for x in extras)
    out['sayings_lines_mixed'] = sum(x['sayings_lines_mixed'] for x in extras)
    out['sayings_lines_per_role_note'] = spread([x['sayings_lines_role'] for x in extras])
    out['same_as_lines'] = sum(x['same_as_lines'] for x in extras)
    out['notes_with_a_same_as_line'] = sum(1 for x in extras if x['same_as_lines'])
    out['printed_fields_not_passage_text'] = sum(x['fields_not_passage_text'] for x in extras)
    out['notes_without_a_mind_line'] = [r['id'] for r in records if not any(e['noetic'] == MIND_NOETIC for e in r['entries'])]
    out['entries'] = sum(len(r['entries']) for r in records)
    out['entries_besides_mind'] = sum(x['entries_besides_mind'] for x in extras)
    return out


def print_report(numbers, design):
    lines = ['ROLE NOTES BUILT (all numbers REAL, measured in this run)',
             '  Notes built: %d passages, each with ROLE, MIXED and QUOTES-ONLY text.' % numbers['notes'],
             '  Agreed entries used: %d (%d of them are not ^1).' % (numbers['entries'], numbers['entries_besides_mind']),
             '',
             'LENGTH, shown as shortest / median / longest',
             '  %-12s %-22s %-22s %-18s %-18s %s' % ('group', 'words (white space)', 'words (word regex)', 'size count', 'characters', 'lines')]
    for group, row in numbers['lengths'].items():
        lines.append('  %-12s %-22s %-22s %-18s %-18s %s' % (group, row['words_by_white_space'], row['words_by_word_regex'],
                                                             row['size_count'], row['characters'], row['lines']))
    lines += ['  "words (white space)" is len(text.split()). "words (word regex)" counts [A-Za-z0-9\']+ ; this is the role_words field.',
              '  "size count" counts every word and every punctuation mark; this is the role_size_count field.',
              '  The passages themselves: %s words (white space).' % numbers['passage_words_by_white_space'],
              '  ROLE note words as a percent of passage words: %s.' % numbers['role_words_over_passage_words_percent'],
              '  FILLER base text, the same for every passage (%d words, size count %d): %s' % (numbers['filler']['words_by_white_space'], numbers['filler']['size_count'], numbers['filler']['text']),
              '',
              'ANSWER-LEAK PATTERNS (rule a: an option letter written as a choice; rule d: the words answer, option, correct)',
              '  Rules (b) and (c) compare a note with a question. No question exists yet, so they can not be run here.',
              '  Screened text = the frame text: the note with every quoted passage part emptied.',
              '  A sayings line (amendment A13) is frame text. It stays whole in the frame text: the word Sayings and the sayings text are screened.']
    for group, row in numbers['screen_frame'].items():
        lines.append('  %-12s notes hit: %d of %d %s' % (group, row['notes_hit'], numbers['notes'], json.dumps(row['ids']) if row['ids'] else ''))
    lines.append('  %-12s hits: %d %s' % ('FILLER', len(numbers['filler']['screen_hits']), json.dumps(numbers['filler']['screen_hits']) if numbers['filler']['screen_hits'] else ''))
    sayings_hits = {noetic: hits for noetic, hits in numbers['sayings_lines_screen_hits'].items() if hits}
    lines.append('  The %d sayings lines, each screened by itself: %d hit %s' % (len(numbers['sayings_lines_screen_hits']), len(sayings_hits),
                                                                             json.dumps(sayings_hits) if sayings_hits else ''))
    lines.append('  For information only, the same patterns on the full text (quoted passage parts kept). These are not hits by the rule:')
    for group, row in numbers['screen_full_text'].items():
        lines.append('  %-12s notes matched: %d of %d %s' % (group, row['notes_matched'], numbers['notes'], json.dumps(row['ids']) if row['ids'] else ''))
    lines += ['',
              'OTHER FACTS',
              '  Sayings lines (amendment A13), one after each canon line: %d in the ROLE notes, %d in the MIXED notes. Per ROLE note: %s.'
              % (numbers['sayings_lines_role'], numbers['sayings_lines_mixed'], numbers['sayings_lines_per_role_note']),
              '  Lines that say: same as for "...": %d, in %d notes.' % (numbers['same_as_lines'], numbers['notes_with_a_same_as_line']),
              '  Printed Minds or related things that are not word-for-word passage text: %d.' % numbers['printed_fields_not_passage_text'],
              '  Notes with no ^1 line: %s.' % json.dumps(numbers['notes_without_a_mind_line']),
              '  Share of a passage\'s sentences that its ROLE note quotes, mean over all notes: %s%%. The design says %s%%;'
              % (numbers['sentence_share_text'], design.get('sentence_share_text')),
              '    that figure was measured before the plan fixed the sentence rule (a full stop after Mr, Dr and the like does not end a sentence).',
              '  Of the %d final role notes, %d quote exactly one passage sentence (the design says %s) and %d hold exactly one entry besides ^1 (the design says %s).'
              % (numbers['final_notes'], numbers['final_one_sentence'], design.get('final_one_sentence'), numbers['final_one_entry'], design.get('final_one_entry'))]
    print(chr(10).join(lines))


# ----------------------------------------------------------------------------- the owner's sample

def left_out_sentence(left_out):
    def one(counts):
        return ', '.join('`%s` %d' % (n, k) for n, k in counts.items()) if counts else 'none'
    return 'Only team A gave: %s. Only team B gave: %s.' % (one(left_out['only_a']), one(left_out['only_b']))


def owner_markdown(constants, sample, numbers, guide_sha, sayings_sha, status_line, made_utc, barred_ids):
    """The readable sample. Canon lines and sayings lines appear only inside the notes, copied by the program."""
    seed = constants['seeds']['owner_role_note_sample']
    rows = ['| %s | %s | %s | %s |' % ((group,) + tuple(row['words_by_white_space'].split(' / ')))
            for group, row in numbers['lengths'].items()]
    rows.append('| the passages themselves | %s | %s | %s |' % tuple(numbers['passage_words_by_white_space'].split(' / ')))
    out = [
        '# Option B: %d sample role notes for the owner' % len(sample),
        '',
        '**%s**' % status_line,
        '',
        'Built on %s by `tools/ob_role_notes.py`. A program built every note. No model wrote one. Nobody edited one.' % made_utc,
        '',
        '## What this file is',
        '',
        'A role note is the text that model B gets next to a passage, in the group called ROLE.',
        'It says which words of the passage occupy which Noetic.',
        'The notes use nine Noetics, `^1` to `^9`. In this study a Noetic is used as a role that words of the passage can occupy.',
        'Each note prints the definition lines it needs.',
        'Right after each definition line it prints one line with that Noetic\'s canonical sayings. That line starts with the word `Sayings`.',
        '',
        'The program copies those definition lines, character for character, from Part A of `02_LABELING_GUIDE_v1_2.md`.',
        'The sha256 of that file is `%s`.' % guide_sha,
        'Nobody retyped a definition.',
        '',
        'The program copies the sayings, character for character, from the table "Canonical colloquialism map" in Clarification 6 of `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`.',
        'The sha256 of that file is `%s`.' % sayings_sha,
        'Nobody retyped a saying. The program builds no note if a definition in that table differs from the guide.',
        '',
        '**The sayings lines are new (amendment A13).**',
        'They are the operator\'s reading of the owner\'s ruling of 2026-10-05 on the colloquialisms.',
        'That ruling is about labeling. It does not name these notes. So the owner may strike the sayings lines (question 22 below).',
        'The owner\'s sentence about Mind is not printed in any note.',
        'The labels behind these notes were made under labeling guide version 1.2, before that ruling. They were not made again.',
        '',
        'A note uses only entries that both label teams agree on.',
        'An entry is one marked role: a Noetic, the quoted words and, where the guide asks for them, the Mind and the related thing.',
        'Team A is Claude Sonnet sub-agents. Team B is DeepSeek `deepseek-chat`.',
        'An entry that only one team gave is left out of the note. It is counted under each note below.',
        '',
        'A program drew these %d passages with seed %d from the %d eligible passages. Nobody chose them.' % (len(sample), seed, numbers['notes']),
        'The seed is a rule of the plan (PROPOSED). The count of %d eligible passages is REAL: the program counted it in this run.' % numbers['notes'],
        '',
        '## How one note is laid out',
        '',
        '1. First comes the head. For each Noetic that appears in the note, in number order: its definition line, then its sayings line.',
        '2. Then come the `^1` lines. A `^1` line holds the label only.',
        '3. Then come the other entries, in the order their words appear in the passage.',
        '4. The label is the shorter of the two teams\' quotes.',
        '5. The supporting quote is the whole sentence, or sentences, of the passage that hold both teams\' quotes.',
        '6. `same as for "..."` means that supporting quote was already printed higher up in the same note.',
        '',
        'Model B sees a note under the plain heading `Notes:`, after one padding line. Those two lines are not shown here.',
        '',
        '## How long the notes are',
        '',
        'REAL, measured in this run on all %d notes. Words are counted by splitting on white space.' % numbers['notes'],
        '',
        '| Text | Shortest | Median | Longest |',
        '|---|---:|---:|---:|',
    ] + rows + [
        '',
        'The median is the middle value: half the notes are shorter and half are longer.',
        'ROLE is the tested note. MIXED is the same note with wrong role tags; it is a control.',
        'QUOTES-ONLY is the same labels and supporting quotes with no role tags; it is a control.',
        'Only ROLE notes are shown below.',
        '',
        '## What the owner is asked',
        '',
        'This file is the sample that question 14 of the plan offers (`08_OPTION_B_PLAN_v1_0.md`, section 22).',
        'It can help with questions 6, 7 and 22 of the same section:',
        '',
        '- Question 6. May the canon definition lines be printed, word for word, inside the role notes that model B reads?',
        '- Question 7. Is the stand-in acceptable: label = the shorter quote, supporting quote = the whole sentence?',
        '- Question 22. May each definition line be followed by that Noetic\'s canonical sayings, copied character for character (amendment A13)?',
        '',
        'Until the owner says otherwise, the plan\'s defaults apply: the definition lines are printed, the stand-in is used, and the sayings lines are printed.',
        'If the owner strikes the sayings lines, a new plan version is written before anything is sealed.',
        'The owner is the only authority on the definitions.',
        '',
        '---',
    ]
    for place, item in enumerate(sample):
        fence = '```'
        if fence in item['role_text']:
            raise Stop('NOTE_TEXT_NOT_CLEAN', 'a note holds a code fence: %s' % item['id'])
        out += [
            '',
            '## Sample %d of %d: passage %s' % (place + 1, len(sample), item['id']),
            '',
            '**Passage**',
            '',
            '> ' + item['text'],
            '',
            '**ROLE note**',
            '',
            fence + 'text',
            item['role_text'],
            fence,
            '',
            '**Left out of this note.** ' + left_out_sentence(item['left_out']),
        ]
        if item['id'] in barred_ids:
            out += ['', 'This passage is barred. It never carries a task. The plan gives this reason: "%s".' % constants['eligibility']['barred_reason']]
    return chr(10).join(out) + chr(10)


def write_text(path, text):
    """UTF-8, LF line ends, .partial then rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + '.partial')
    with open(partial, 'wb') as handle:
        handle.write(text.encode('utf-8'))
    partial.replace(path)
    return base.sha256_bytes(text.encode('utf-8'))


# ----------------------------------------------------------------------------- main

def main(argv=None):
    parser = argparse.ArgumentParser(description='Option B: build the role notes.')
    parser.add_argument('--project', default=str(PROJECT), help='the CASALESCENCE_NOETICS_v0_1 folder')
    parser.add_argument('--dry-run', default=None, metavar='DIR', help='read DIR/elig/eligibility.json, write under DIR, need no seal')
    parser.add_argument('--owner-sample-md', default=None, metavar='FILE', help='where the readable owner sample is written')
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):      # FILE_FORMATS.md section 0: a laptop tool prints in UTF-8
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', newline=chr(10))
    project = Path(args.project).resolve()
    try:
        constants, constants_path, constants_sha = base.load_constants(project)
        work = (project / constants['work_folder']).resolve()
        dry = args.dry_run is not None
        root = Path(args.dry_run).resolve() if dry else work
        if dry and root == work:
            raise Stop('DRY_RUN_INTO_THE_REAL_FOLDER', 'a dry run must write to another folder than %s' % base.rel(work, project))
        if not dry:
            try:
                ob_seal.require_steps(project, ['1_PLAN_AND_SOURCES'], constants)
                if ob_seal.has_step(project, '2_ROLE_NOTES', constants):
                    raise Stop('ALREADY_SEALED', 'seal step 2 exists. The role notes are sealed and are not written again')
            except ob_seal.Refused as refusal:
                raise Stop(refusal.code, refusal.detail)
        eligibility_path = root / 'elig' / 'eligibility.json'
        if not eligibility_path.is_file():
            raise Stop('ELIGIBILITY_MISSING', '%s was not found. Run tools/ob_eligibility.py first' % base.rel(eligibility_path, project))
        eligibility_bytes = eligibility_path.read_bytes()
        eligibility = json.loads(eligibility_bytes.decode('utf-8'))
        if eligibility.get('schema') != SCHEMA_ELIGIBILITY or eligibility.get('counts_match_plan') is not True:
            raise Stop('ELIGIBILITY_NOT_USABLE', 'the eligibility file has another schema, or its counts do not match the plan')
        eligible = [p for p in eligibility['passages'] if p['eligible']]
        if len(eligible) != constants['counts_real']['eligible_passages']:
            raise Stop('COUNTS_DO_NOT_MATCH_PLAN', '%d eligible passages; the plan counts %d' % (len(eligible), constants['counts_real']['eligible_passages']))

        canon_lines, names, guide_record = read_canon(project, constants)
        sayings_lines, sayings_record = read_sayings(project, constants)      # amendment A13; refuses as plan section 6 says
        records, extras = [], []
        for passage in eligible:
            record, extra = build_passage(constants, canon_lines, sayings_lines, names, passage)
            records.append(record)
            extras.append(extra)

        numbers = measure(constants, records, extras, eligibility['passages'])
        numbers['sayings_lines_screen_hits'] = {noetic: screen_hits(constants, line) for noetic, line in sayings_lines.items()}
        design, design_record = design_text_numbers(project, constants)
        print('Option B role notes. Program %s. %s' % (PROGRAM, 'DRY RUN into %s. No seal was needed or checked.' % base.rel(root, project) if dry
                                                         else 'Real run. Seal step 1 was checked.'))
        print_report(numbers, design)
        frame_hits = (sum(row['notes_hit'] for row in numbers['screen_frame'].values()) + len(numbers['filler']['screen_hits'])
                      + sum(1 for hits in numbers['sayings_lines_screen_hits'].values() if hits))
        if frame_hits:
            raise Stop('FRAME_TEXT_HITS_THE_ANSWER_LEAK_SCREEN', '%d note(s) or sayings line(s) hold a forbidden pattern in their fixed frame words' % frame_hits)

        made_by = {'program': PROGRAM, 'sha256': base.sha256_file(Path(__file__).resolve()), 'utc': base.utc_now()}
        inputs = [{'path': base.rel(eligibility_path, project), 'sha256': base.sha256_bytes(eligibility_bytes)},
                  guide_record,
                  sayings_record,
                  {'path': base.rel(constants_path, project), 'sha256': constants_sha},
                  {'path': 'tools/ob_eligibility.py', 'sha256': base.sha256_file(TOOLS / 'ob_eligibility.py')},
                  {'path': 'tools/ob_seal.py', 'sha256': base.sha256_file(TOOLS / 'ob_seal.py')}]
        if design_record:
            inputs.append(design_record)
        notes_file = {'schema': SCHEMA_NOTES, 'made_by': made_by, 'inputs': inputs,
                      'canon': {'source': constants['sources']['labeling_guide']['path'], 'sha256': guide_record['sha256'],
                                'lines': canon_lines, 'names': names,
                                'sayings_source': sayings_record['path'], 'sayings_sha256': sayings_record['sha256'],
                                'sayings_lines': sayings_lines},
                      'passages': records}
        seed = constants['seeds']['owner_role_note_sample']
        picked = random.Random(seed).sample(sorted(p['id'] for p in eligible), constants['role_notes']['owner_sample_size'])
        by_id = {r['id']: r for r in records}
        text_by_id = {p['id']: p['text'] for p in eligible}
        sample = [{'id': pid, 'text': text_by_id[pid], 'role_text': by_id[pid]['role_text'], 'left_out': by_id[pid]['left_out']} for pid in picked]
        sample_file = {'schema': SCHEMA_SAMPLE, 'made_by': made_by, 'inputs': inputs, 'seed': seed, 'passages': sample}
        if dry:
            status_line = ('Status: DRY RUN. Built before any seal exists. These notes are not sealed yet. '
                           'A real run writes this file again; the notes come out the same if the plan and the label files have not changed.')
        else:
            status_line = 'Status: built after seal step 1 and before seal step 2. These notes are not sealed yet.'
        markdown = owner_markdown(constants, sample, numbers, guide_record['sha256'], sayings_record['sha256'], status_line, made_by['utc'],
                                  {p['id'] for p in eligible if p['barred']})
        md_path = Path(args.owner_sample_md).resolve() if args.owner_sample_md else root / OWNER_MD_NAME

        folder = root / 'notes_role'
        sha_notes = base.write_json(folder / 'role_notes.json', notes_file)
        sha_sample = base.write_json(folder / 'owner_sample_20.json', sample_file)
        sha_md = write_text(md_path, markdown)
        print()
        print('WROTE %s  sha256 %s' % (base.rel(folder / 'role_notes.json', project), sha_notes))
        print('WROTE %s  sha256 %s' % (base.rel(folder / 'owner_sample_20.json', project), sha_sample))
        print('WROTE %s  sha256 %s' % (base.rel(md_path, project), sha_md))
        print('Owner sample, seed %d: %s' % (seed, ', '.join(picked)))
        print('ROLE_NOTES_OK.')
        return 0
    except Stop as stop:
        print('STOPPED: %s: %s. Nothing was written.' % (stop.code, str(stop.detail).rstrip('.')))
        return 2


if __name__ == '__main__':
    sys.exit(main())
