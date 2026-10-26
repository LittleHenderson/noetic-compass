"""Option B, program 1: which passages may carry a task, which are left out, and the practice split.

Plan: 08_OPTION_B_PLAN_v1_0.md, sections 4, 5, 7.1 and 12.1. File formats: optionb/FILE_FORMATS.md,
section 2. Every number and rule name is read from optionb/PLAN_CONSTANTS.json.

Plain Python, standard library only. No model, no network, no key. It runs in a few seconds.

What it does, in order
  1. Checks the sha256 and the size of the four files it reads against PLAN_CONSTANTS.json:
     the two label files, the hidden-kinds passage file and tools/verdict.py. All are read-only.
     It also checks the pin of every source file that seal step 1 seals (seal.sources_sealed_in_step_1).
     Amendment A13 made them six. The sixth is the file that holds the table of the canonical sayings.
     It lies outside the study folder; its pinned path is counted from the study folder, two steps up.
     This program takes nothing from the guide or from that file. It only checks that each has its
     pinned size and sha256, so that a missing or changed source stops the build at its first step.
  2. Applies the exclusion rule (guide rule 15). A passage is left out when either team wrote, on it,
     a raw entry with Noetic ^8 or ^9 and "certainty": "ambiguous", or "other_candidate": "reasoning",
     or "reached_by": "reasoning".
  3. Pairs the two teams' clear entries ONE TO ONE, per passage and per Noetic, with the frozen
     same-reading test. Entries left over are counted apart as "only team A" and "only team B".
  4. Opens question forms per passage from the agreed entries. No person chooses.
  5. Splits the settings into practice, reserve and final with the sealed seed, and checks that the
     draw gives the settings written in the plan.
  6. Bars the passages named in the plan (V009 and V076) from ever carrying a task.
  7. Marks every K1 to K5 passage as one the question writer is sent (all of them, not only the
     eligible ones), so that being asked tells the writer nothing.
  8. Prints a count report. Every count stands beside the value the plan or the design gives.
  9. Writes elig/exclusions.json and elig/eligibility.json. It writes NOTHING if a count differs.

How the frozen functions are loaded (plan section 4: "Programs import the frozen functions from
tools/verdict.py after checking its hash. They do not copy or rewrite them.")
  The bytes of tools/verdict.py are read once. Their sha256 is compared with PLAN_CONSTANTS.json.
  The SAME bytes are then compiled and run as a private module named "ob_frozen_verdict". So the code
  that was hashed is the code that runs. tools/verdict.py keeps its report run behind
  `if __name__ == '__main__':`, and its top level only imports standard modules and sets constants.
  Loading it under another name therefore reads no file, writes no file and prints nothing.
  Used from it: clean, select, same_span, same_field, lenient_span, content, REQUIRED.

Usage
  ob_eligibility.py                       write optionb/elig/ (refused once seal step 1 exists)
  ob_eligibility.py --out-root DIR        write DIR/elig/ instead (a dry run into a scratch folder)
  ob_eligibility.py --report-only         print the count report and write nothing

Exit code 0: every count matched and the files were written (or --report-only was given).
Exit code 2: STOPPED. The reason is printed. Nothing was written.
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
import random
import re
import sys
import types
from pathlib import Path

sys.dont_write_bytecode = True   # leave no cache folder beside the frozen tools

TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
PROGRAM = 'tools/ob_eligibility.py'
SCHEMA_EXCLUSIONS = 'casalescence/optionb/exclusions/v1'
SCHEMA_ELIGIBILITY = 'casalescence/optionb/eligibility/v1'
SEAL_NAME = 'SEAL_OPTIONB.jsonl'
FROZEN_NAMES = ('clean', 'select', 'same_span', 'same_field', 'lenient_span', 'content', 'REQUIRED')
# The exclusion codes of FILE_FORMATS.md section 2.1, in the order they are written.
CODE_UNCERTAIN = 'UNCERTAIN_8_OR_9'
CODE_OTHER = 'OTHER_CANDIDATE_REASONING'
CODE_REACHED = 'REACHED_BY_REASONING'
CODE_ORDER = (CODE_UNCERTAIN, CODE_OTHER, CODE_REACHED)
RULE_15_NOETICS = ('^8', '^9')
# form_rules.land_second_question_needs_agreed_entries_of speaks about this type.
LAND_TYPE = 'LAND'


class Stop(Exception):
    """A refusal. main() prints it and exits with code 2. Nothing is written."""

    def __init__(self, code, detail):
        Exception.__init__(self, '%s: %s' % (code, detail))
        self.code = code
        self.detail = detail


# ----------------------------------------------------------------------------- small helpers

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def rel(path, project=PROJECT):
    """A path as text, relative to the project folder where it lies inside it, with forward slashes."""
    path = Path(path).resolve()
    try:
        return path.relative_to(Path(project).resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path, value):
    """FILE_FORMATS.md section 0: indent 1, real characters, one LF at the end, .partial then rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=1, ensure_ascii=False) + chr(10)
    partial = path.with_name(path.name + '.partial')
    with open(partial, 'wb') as handle:
        handle.write(text.encode('utf-8'))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)
    return sha256_bytes(text.encode('utf-8'))


def load_constants(project=PROJECT, constants_path=None):
    """Returns (constants, path, sha256). The file is the only place a number or a wording comes from."""
    path = Path(constants_path) if constants_path else Path(project) / 'optionb' / 'PLAN_CONSTANTS.json'
    if not path.is_file():
        raise Stop('CONSTANTS_MISSING', '%s was not found' % path)
    data = path.read_bytes()
    return json.loads(data.decode('utf-8')), path, sha256_bytes(data)


def read_pinned(project, constants, source_name):
    """Reads one source file and refuses if its size or sha256 is not the pinned one.

    The pinned path is counted from the study folder. One source lies outside it (amendment A13):
    the file with the table of the canonical sayings, pinned as ../../docs/... . The record that is
    returned names the path exactly as the plan constants give it.
    """
    pin = constants['sources'][source_name]
    path = Path(project) / pin['path']
    if not path.is_file():
        raise Stop('SOURCE_MISSING', '%s (%s) was not found' % (source_name, path))
    data = path.read_bytes()
    digest = sha256_bytes(data)
    if len(data) != pin['bytes'] or digest != pin['sha256']:
        raise Stop('SOURCE_CHANGED', '%s is %d bytes with sha256 %s; the plan pins %d bytes and %s'
                   % (pin['path'], len(data), digest, pin['bytes'], pin['sha256']))
    return data, {'path': pin['path'], 'sha256': digest}


def load_frozen_verdict(project, constants):
    """The frozen functions of tools/verdict.py, loaded from bytes whose hash was just checked."""
    data, record = read_pinned(project, constants, 'verdict_program')
    path = Path(project) / constants['sources']['verdict_program']['path']
    module = types.ModuleType('ob_frozen_verdict')
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec', dont_inherit=True), module.__dict__)
    missing = [name for name in FROZEN_NAMES if not hasattr(module, name)]
    if missing:
        raise Stop('FROZEN_FUNCTION_MISSING', 'tools/verdict.py does not offer: %s' % ', '.join(missing))
    return module, record


def check_sealed_sources(project, constants):
    """The source files that seal step 1 seals are there with their pinned size and sha256. Returns their names.

    Amendment A13: the list is seal.sources_sealed_in_step_1. Its sixth name is the source of the
    canonical sayings, which lies outside the study folder. A missing or changed file is a refusal.
    """
    names = list(constants['seal']['sources_sealed_in_step_1'])
    if len(set(names)) != len(names) or any(name not in constants['sources'] for name in names):
        raise Stop('CONSTANTS_SHAPE', 'seal.sources_sealed_in_step_1 names a source twice, or a source that sources does not pin')
    for name in names:
        read_pinned(project, constants, name)
    return names


# ----------------------------------------------------------------------------- the rules

def rule15_codes(raw_entries):
    """The rule-15 codes found in one team's raw entries for one passage, in the fixed order."""
    found = set()
    for entry in raw_entries:
        if entry.get('noetic') in RULE_15_NOETICS and entry.get('certainty') == 'ambiguous':
            found.add(CODE_UNCERTAIN)
        if entry.get('other_candidate') == 'reasoning':
            found.add(CODE_OTHER)
        if entry.get('reached_by') == 'reasoning':
            found.add(CODE_REACHED)
    return [code for code in CODE_ORDER if code in found]


def clean_with_index(frozen, rows, passages, team):
    """frozen.clean() on one team's file, plus each kept entry's place in the raw entry list.

    The frozen function decides what is kept. To learn WHICH raw entries it kept, it is called once
    more per raw entry, on that entry alone. The two answers must agree, or the program stops.
    """
    ids = [row['passage_id'] for row in rows]
    if len(set(ids)) != len(ids) or set(ids) != set(passages):
        raise Stop('LABEL_FILE_SHAPE', 'team %s does not hold exactly one row per sealed passage' % team)
    cleaned, dropped, failed = frozen.clean(rows, passages)
    if failed:
        raise Stop('LABEL_FILE_SHAPE', 'team %s has failed rows: %s' % (team, ', '.join(sorted(failed))))
    for row in rows:
        pid = row['passage_id']
        raw = row.get('entries', [])
        kept_places = []
        for place, entry in enumerate(raw):
            alone, _, _ = frozen.clean([{'passage_id': pid, 'entries': [entry]}], passages)
            if alone[pid]['entries']:
                kept_places.append(place)
        kept = cleaned[pid]['entries']
        if len(kept_places) != len(kept):
            raise Stop('CLEAN_MISMATCH', 'team %s, %s: the kept entries could not be traced' % (team, pid))
        for place, entry in zip(kept_places, kept):
            if entry['words'] != raw[place].get('words') or entry['noetic'] != raw[place].get('noetic'):
                raise Stop('CLEAN_MISMATCH', 'team %s, %s: entry %d does not match its raw entry' % (team, pid, place))
            entry['index'] = place
    return cleaned, dropped


def same_reading(frozen, noetic, x, y):
    """FILE_FORMATS.md section 18: same_span on the words and same_field on each field in REQUIRED."""
    return frozen.same_span(x['words'], y['words']) and all(frozen.same_field(x[f], y[f]) for f in frozen.REQUIRED[noetic])


def pair_one_to_one(frozen, noetic, entries_a, entries_b):
    """The pairing rule of the plan, section 4. Team A in file order; first unused team B entry that fits."""
    used = [False] * len(entries_b)
    pairs, only_a = [], []
    for x in entries_a:
        hit = None
        for place, y in enumerate(entries_b):
            if not used[place] and same_reading(frozen, noetic, x, y):
                hit = place
                break
        if hit is None:
            only_a.append(x)
        else:
            used[hit] = True
            pairs.append((x, entries_b[hit]))
    only_b = [y for place, y in enumerate(entries_b) if not used[place]]
    return pairs, only_a, only_b


def largest_pairing(frozen, noetic, entries_a, entries_b):
    """The size of the largest possible one-to-one pairing (augmenting paths). A check only."""
    fits = [[place for place, y in enumerate(entries_b) if same_reading(frozen, noetic, x, y)] for x in entries_a]
    owner = [None] * len(entries_b)

    def place_one(i, seen):
        for j in fits[i]:
            if j in seen:
                continue
            seen.add(j)
            if owner[j] is None or place_one(owner[j], seen):
                owner[j] = i
                return True
        return False

    return sum(1 for i in range(len(entries_a)) if place_one(i, set()))


def entry_record(entry):
    return {'index': entry['index'], 'words': entry['words'], 'mind': entry['mind'], 'relative_to': entry['relative_to']}


def count_by_noetic(noetics, items):
    """Entry counts per Noetic, in number order. A Noetic with zero is left out."""
    tally = collections.Counter(noetic for noetic in items)
    return {noetic: tally[noetic] for noetic in noetics if tally[noetic]}


def open_forms_for(constants, agreed_counts):
    """The forms whose needed agreed entries are all there, in the order of forms_in_order."""
    out = []
    for form in constants['forms_in_order']:
        needs = constants['forms'][form]['opens_when']
        if all(agreed_counts.get(noetic, 0) >= least for noetic, least in needs.items()):
            out.append(form)
    return out


def ceiling_for(constants, forms_open, agreed_counts):
    """The most role-step tasks one passage can carry: different forms, the LAND rule, at most two."""
    rules = constants['form_rules']
    land = [f for f in forms_open if constants['forms'][f]['type'] == LAND_TYPE]
    other = [f for f in forms_open if constants['forms'][f]['type'] != LAND_TYPE]
    second_land_ok = all(agreed_counts.get(noetic, 0) >= least
                         for noetic, least in rules['land_second_question_needs_agreed_entries_of'].items())
    land_usable = len(land) if second_land_ok else min(1, len(land))
    return min(rules['max_role_step_tasks_per_passage'], len(other) + land_usable)


def setting_roles(constants, settings):
    """The sealed draw. Returns {setting: role}, the practice list and the reserve list."""
    split = constants['split']
    start, most = split['practice_setting_count_start'], split['practice_setting_count_max']
    drawn = random.Random(constants['seeds']['split']).sample(sorted(settings), most)
    practice, reserve = drawn[:start], drawn[start:]
    if practice != split['practice_settings'] or reserve != split['reserve_settings_in_order']:
        raise Stop('SPLIT_DOES_NOT_MATCH_PLAN',
                   'the seeded draw gave practice %r and reserve %r; the plan names %r and %r'
                   % (practice, reserve, split['practice_settings'], split['reserve_settings_in_order']))
    roles = {name: 'final' for name in settings}
    for name in practice:
        roles[name] = 'practice'
    for place, name in enumerate(reserve):
        roles[name] = 'reserve_%d' % (place + 1)
    return roles, practice, reserve


def in_practice(role, practice_setting_count, start):
    """FILE_FORMATS.md section 2.2: practice, or reserve_k with k <= N - start."""
    if role == 'practice':
        return True
    if role.startswith('reserve_'):
        return int(role.split('_')[1]) <= practice_setting_count - start
    return False


# ----------------------------------------------------------------------------- the build

def build(project, constants):
    """Everything is worked out here. Nothing is written. Returns a dict that main() reports and saves."""
    elig = constants['eligibility']
    noetics = constants['role_notes']['canon_noetics_used']
    types_in_order = constants['types_in_order']
    start = constants['split']['practice_setting_count_start']
    most = constants['split']['practice_setting_count_max']

    frozen, verdict_record = load_frozen_verdict(project, constants)
    passages_bytes, passages_record = read_pinned(project, constants, 'passages')
    a_bytes, a_record = read_pinned(project, constants, 'labels_team_a')
    b_bytes, b_record = read_pinned(project, constants, 'labels_team_b')
    passage_rows = json.loads(passages_bytes.decode('utf-8'))
    rows_a = json.loads(a_bytes.decode('utf-8'))
    rows_b = json.loads(b_bytes.decode('utf-8'))
    texts = {p['id']: p['text'] for p in passage_rows}
    if len(texts) != len(passage_rows):
        raise Stop('PASSAGE_FILE_SHAPE', 'a passage id is repeated')
    raw_a = {row['passage_id']: row.get('entries', []) for row in rows_a}
    raw_b = {row['passage_id']: row.get('entries', []) for row in rows_b}
    clean_a, dropped_a = clean_with_index(frozen, rows_a, texts, 'A')
    clean_b, dropped_b = clean_with_index(frozen, rows_b, texts, 'B')

    roles, practice_settings, reserve_settings = setting_roles(constants, {p['setting'] for p in passage_rows})
    barred_ids = set(elig['barred_passage_ids'])
    used_kinds = set(elig['passage_kinds_used'])
    missing_barred = sorted(barred_ids - set(texts))
    if missing_barred:
        raise Stop('BARRED_PASSAGE_UNKNOWN', ', '.join(missing_barred))

    out_passages, exclusions = [], []
    totals = {n: [0, 0, 0] for n in noetics}            # agreed, only A, only B over ALL passages
    pairing_cells, pairing_cells_largest = 0, 0
    unused_kind_would_open = []
    for p in passage_rows:
        pid, kind = p['id'], p['kind']
        reasons = (['A:' + c for c in rule15_codes(raw_a[pid])] + ['B:' + c for c in rule15_codes(raw_b[pid])])
        excluded = bool(reasons)
        if excluded:
            exclusions.append({'id': pid, 'kind': kind, 'reasons': reasons})
        agreed, only_a, only_b = [], [], []
        for noetic in noetics:
            ea = frozen.select(clean_a[pid]['entries'], noetic)
            eb = frozen.select(clean_b[pid]['entries'], noetic)
            pairs, left_a, left_b = pair_one_to_one(frozen, noetic, ea, eb)
            if ea or eb:
                pairing_cells += 1
                pairing_cells_largest += len(pairs) == largest_pairing(frozen, noetic, ea, eb)
            totals[noetic][0] += len(pairs)
            totals[noetic][1] += len(left_a)
            totals[noetic][2] += len(left_b)
            agreed += [{'noetic': noetic, 'a': entry_record(x), 'b': entry_record(y)} for x, y in pairs]
            only_a += [dict({'noetic': noetic}, **entry_record(x)) for x in left_a]
            only_b += [dict({'noetic': noetic}, **entry_record(y)) for y in left_b]
        agreed_counts = count_by_noetic(noetics, [e['noetic'] for e in agreed])
        only_a_counts = count_by_noetic(noetics, [e['noetic'] for e in only_a])
        only_b_counts = count_by_noetic(noetics, [e['noetic'] for e in only_b])
        would_open = open_forms_for(constants, agreed_counts)
        usable = (not excluded) and kind in used_kinds
        if (not excluded) and kind not in used_kinds and would_open:
            unused_kind_would_open.append(pid)
        forms_open = would_open if usable else []
        types_open = [t for t in types_in_order if any(constants['forms'][f]['type'] == t for f in forms_open)]
        leftover_noetics = set(only_a_counts) | set(only_b_counts)
        record = {
            'id': pid, 'kind': kind, 'setting': p['setting'], 'text': p['text'],
            'setting_role': roles[p['setting']],
            'writer_asks': kind in used_kinds,
            'excluded': excluded,
            'barred': pid in barred_ids,
            'eligible': usable and bool(forms_open),
            'agreed': agreed_counts, 'only_a': only_a_counts, 'only_b': only_b_counts,
            'open_forms': forms_open, 'open_types': types_open,
            'max_role_step_tasks': ceiling_for(constants, forms_open, agreed_counts),
            'leftover_on_type': {t: any(n in leftover_noetics for n in constants['form_rules']['type_noetics_for_leftover_views'][t])
                                 for t in types_open},
            'any_leftover_2_to_9': any(n != '^1' for n in leftover_noetics),
            'entries': None if excluded else {'agreed': agreed, 'only_a': only_a, 'only_b': only_b},
        }
        out_passages.append(record)

    # ---- counts, with the same keys as counts_real in PLAN_CONSTANTS.json
    eligible = [r for r in out_passages if r['eligible']]
    task_passages = [r for r in eligible if not r['barred']]          # a barred passage never carries a task
    excluded_by_kind = collections.Counter(x['kind'] for x in exclusions)
    eligible_by_kind = collections.Counter(r['kind'] for r in eligible)
    by_count = {}
    for n in range(start, most + 1):
        practice = [r for r in task_passages if in_practice(r['setting_role'], n, start)]
        final = [r for r in task_passages if not in_practice(r['setting_role'], n, start)]
        asked = [r for r in out_passages if r['writer_asks']]
        by_count[str(n)] = {
            'practice_passages': len(practice), 'final_passages': len(final),
            'role_step_ceiling_practice': sum(r['max_role_step_tasks'] for r in practice),
            'role_step_ceiling_final': sum(r['max_role_step_tasks'] for r in final),
            'k1_to_k5_practice': sum(1 for r in asked if in_practice(r['setting_role'], n, start)),
            'k1_to_k5_final': sum(1 for r in asked if not in_practice(r['setting_role'], n, start)),
        }
    practice_start = [r for r in task_passages if in_practice(r['setting_role'], start, start)]
    final_start = [r for r in task_passages if not in_practice(r['setting_role'], start, start)]

    def per_type(rows):
        return {t: sum(1 for r in rows if t in r['open_types']) for t in types_in_order}

    whole_word = constants['forbidden_words']['leak_screen_words']['words'][2]   # 'correct'
    if whole_word != 'correct':
        raise Stop('CONSTANTS_SHAPE', 'the third answer-leak word is %r, not correct' % whole_word)
    counts = {
        'note': 'REAL. Counted by tools/ob_eligibility.py in this run, from the sealed files, with the rules in PLAN_CONSTANTS.json.',
        'passages': len(out_passages),
        'settings': len(roles),
        'entries_agreed_only_a_only_b': {n: list(totals[n]) for n in noetics},
        'excluded_passages': len(exclusions),
        'excluded_by_kind': {k: excluded_by_kind[k] for k in sorted(excluded_by_kind)},
        'passages_after_exclusion': len(out_passages) - len(exclusions),
        'eligible_passages': len(eligible),
        'eligible_by_kind': {k: eligible_by_kind[k] for k in sorted(eligible_by_kind)},
        'passages_per_type': per_type(eligible),
        'passages_by_number_of_types': {str(k): v for k, v in sorted(collections.Counter(len(r['open_types']) for r in eligible).items())},
        'k1_to_k5_passages': sum(1 for r in out_passages if r['writer_asks']),
        'eligible_passage_without_agreed_mind_entry': [r['id'] for r in eligible if not r['agreed'].get('^1')],
        'eligible_passages_holding_the_whole_word_correct': [r['id'] for r in eligible
                                                             if re.search(r'\b%s\b' % re.escape(whole_word), r['text'], re.I)],
        'by_practice_setting_count': by_count,
        'practice_at_%d_passages_per_type' % start: per_type(practice_start),
        'final_at_%d_passages_per_type' % start: per_type(final_start),
        'final_at_%d_passages_that_can_carry_one_task_only' % start: sum(1 for r in final_start if r['max_role_step_tasks'] == 1),
    }

    # ---- numbers the design gives in its text, for the cross-check part of the report
    two_to_nine = [n for n in noetics if n != '^1']
    final_leftover = {t: [sum(1 for r in final_start if r['leftover_on_type'].get(t)), sum(1 for r in final_start if t in r['open_types'])]
                      for t in types_in_order}
    pull_push = [r for r in eligible if 'PULL-PUSH' in r['open_types']]
    extras = {
        'eligible_agreed_entries': sum(sum(r['agreed'].values()) for r in eligible),
        'eligible_agreed_entries_2_to_9': sum(r['agreed'].get(n, 0) for r in eligible for n in two_to_nine),
        'eligible_only_a_2_to_9': sum(r['only_a'].get(n, 0) for r in eligible for n in two_to_nine),
        'eligible_only_b_2_to_9': sum(r['only_b'].get(n, 0) for r in eligible for n in two_to_nine),
        'passages_with_an_agreed_entry': {n: sum(1 for r in out_passages if r['agreed'].get(n)) for n in two_to_nine},
        'eligible_with_a_type_without_leftover': sum(1 for r in eligible if any(not v for v in r['leftover_on_type'].values())),
        'eligible_without_any_leftover_2_to_9': sum(1 for r in eligible if not r['any_leftover_2_to_9']),
        'final_with_a_type_without_leftover': sum(1 for r in final_start if any(not v for v in r['leftover_on_type'].values())),
        'final_without_any_leftover_2_to_9': sum(1 for r in final_start if not r['any_leftover_2_to_9']),
        'final_open_a_type_other_than_land_or_habit': sum(1 for r in final_start if any(t not in ('LAND', 'HABIT') for t in r['open_types'])),
        'final_open_only_land_or_habit': sum(1 for r in final_start if all(t in ('LAND', 'HABIT') for t in r['open_types'])),
        'final_open_one_type': sum(1 for r in final_start if len(r['open_types']) == 1),
        'final_open_two_types': sum(1 for r in final_start if len(r['open_types']) == 2),
        'final_leftover_on_needed_noetic': final_leftover,
        'pull_push_both_2_and_3': sum(1 for r in pull_push if r['agreed'].get('^2') and r['agreed'].get('^3')),
        'pull_push_only_one': sum(1 for r in pull_push if not (r['agreed'].get('^2') and r['agreed'].get('^3'))),
        'final_passages_with_exactly_one_open_form': sum(1 for r in final_start if len(r['open_forms']) == 1),
        'final_passages_with_two_open_forms_but_one_task': [r['id'] for r in final_start
                                                            if len(r['open_forms']) >= 2 and r['max_role_step_tasks'] == 1],
        'entries_dropped_by_clean': {'team_a': dropped_a, 'team_b': dropped_b},
        'pairing_cells': pairing_cells,
        'pairing_cells_where_rule_finds_the_largest_pairing': pairing_cells_largest,
        'unused_kind_passages_that_would_open_a_form': unused_kind_would_open,
        'barred_passages': [{'id': r['id'], 'kind': r['kind'], 'setting_role': r['setting_role'], 'eligible': r['eligible'],
                             'open_types': r['open_types']} for r in out_passages if r['barred']],
        'writer_asks_by_setting_role': dict(sorted(collections.Counter(r['setting_role'] for r in out_passages if r['writer_asks']).items())),
    }
    return {'passages': out_passages, 'exclusions': exclusions, 'counts': counts, 'extras': extras,
            'practice_settings': practice_settings, 'reserve_settings': reserve_settings,
            'inputs': [a_record, b_record, passages_record, verdict_record]}


# ----------------------------------------------------------------------------- the report

def design_numbers(project, constants):
    """Numbers the design states in its text. Read from the pinned design file, never retyped here.

    Returns {name: value or None}. None means the sentence was not found in the design text.
    """
    try:
        data, record = read_pinned(project, constants, 'design')
    except Stop as stop:
        return {}, None, str(stop)
    spec = json.loads(data.decode('utf-8'))['spec']
    source = spec['source_passages_and_role_descriptions']
    sizes = spec['sizes_and_what_can_be_concluded']
    groups = json.dumps(spec['guidance_groups'], ensure_ascii=False)
    out = {}

    def grab(names, pattern, text):
        found = re.search(pattern, text)
        for place, name in enumerate(names):
            out[name] = int(found.group(place + 1)) if found else None

    grab(['eligible_agreed_entries', 'eligible_agreed_entries_2_to_9'],
         r'They hold (\d+) agreed entries \((\d+) of them \^2 to \^9\)', source)
    grab(['eligible_only_a_2_to_9', 'eligible_only_b_2_to_9'],
         r'(\d+) entries only team A gave and (\d+) only team B gave \(\^2 to \^9\)', source)
    grab(['eligible_with_a_type_without_leftover'],
         r'(\d+) of the \d+ passages have at least one open question type with no left-over entry', source)
    grab(['eligible_without_any_leftover_2_to_9'], r'(\d+) have no left-over \^2 to \^9 entry at all', source)
    grab(['final_with_a_type_without_leftover', 'final_without_any_leftover_2_to_9',
          'final_open_a_type_other_than_land_or_habit', 'final_open_only_land_or_habit',
          'final_open_one_type', 'final_open_two_types'],
         r'Of the \d+ final passages: (\d+) have at least one open type with no left-over entry on its needed Noetic\. '
         r'(\d+) have no left-over \^2 to \^9 entry at all\. (\d+) open a type other than LAND or HABIT\. '
         r'(\d+) open only LAND or HABIT\. (\d+) open one type, (\d+) open two\.', sizes)
    grab(['pull_push_both_2_and_3', 'pull_push_only_one'],
         r'of the \d+ PULL-PUSH passages, (\d+) have both \^2 and \^3 agreed.*?; (\d+) have only one', groups)
    grab(['final_passages_with_exactly_one_open_form'], r'(\d+) passages open only one form', sizes)
    found = re.search(r'match the verdict report: ([^.]*)\.', source)
    out['passages_with_an_agreed_entry'] = ({n: int(v) for n, v in re.findall(r'(\^\d) (\d+)', found.group(1))} if found else None)
    found = re.search(r'final passages with a left-over entry on the needed Noetic: ([^.]*)\.', source)
    out['final_leftover_on_needed_noetic'] = ({t: [int(x), int(y)] for t, x, y in re.findall(r'([A-Z][A-Z-]+) (\d+) of (\d+)', found.group(1))}
                                               if found else None)
    return out, record, None


def report(result, constants, design, design_note):
    """Prints every count beside its plan or design value. Returns (plan_ok, design_ok, lines that differ)."""
    counts, extras = result['counts'], result['extras']
    real = constants['counts_real']
    start = constants['split']['practice_setting_count_start']
    different = []
    lines = []

    def row(label, got, want, source, gating=True):
        if want is None:
            mark = 'NO DESIGN VALUE FOUND'
        elif got == want:
            mark = 'MATCH'
        else:
            mark = 'DIFFERENT'
            different.append({'count': label, 'real': got, 'design': want, 'source': source, 'gating': gating})
        lines.append('  %-58s REAL %-22s %-11s %-22s %s' % (label, json.dumps(got, ensure_ascii=False), source,
                                                            json.dumps(want, ensure_ascii=False), mark))

    def head(text):
        lines.append('')
        lines.append(text)

    head('A. COUNTS THE PLAN PINS (PLAN_CONSTANTS.json, counts_real). All must match, or nothing is written.')
    plan_keys = [k for k in real if k != 'note']
    flat = []
    for key in plan_keys:
        got, want = counts.get(key), real[key]
        if isinstance(want, dict) and all(isinstance(v, dict) for v in want.values()):
            for sub in want:
                for leaf in want[sub]:
                    flat.append(('%s[%s].%s' % (key, sub, leaf), (got or {}).get(sub, {}).get(leaf), want[sub][leaf]))
        elif isinstance(want, dict):
            for sub in sorted(set(want) | set(got or {})):
                flat.append(('%s[%s]' % (key, sub), (got or {}).get(sub), want.get(sub)))
        else:
            flat.append((key, got, want))
    for label, got, want in flat:
        row(label, got, want, 'plan')
    extra_keys = sorted(set(counts) - set(real))
    if extra_keys:
        different.append({'count': 'keys', 'real': extra_keys, 'design': [], 'source': 'plan', 'gating': True})
        lines.append('  keys the plan does not hold: %s  DIFFERENT' % ', '.join(extra_keys))
    whole_equal = {k: counts.get(k) for k in plan_keys} == {k: real[k] for k in plan_keys}
    if not whole_equal and not any(d['source'] == 'plan' for d in different):
        different.append({'count': 'counts as a whole', 'real': 'not equal', 'design': 'counts_real', 'source': 'plan', 'gating': True})
        lines.append('  the counts object as a whole is not equal to counts_real  DIFFERENT')
    plan_ok = whole_equal and not any(d['source'] == 'plan' for d in different)

    head('B. COUNTS THE DESIGN STATES IN ITS TEXT (design_v2/optionB_final.json). The first four must match.')
    if design_note:
        lines.append('  the design file could not be read: %s' % design_note)
    must = ('eligible_agreed_entries', 'eligible_agreed_entries_2_to_9', 'eligible_only_a_2_to_9', 'eligible_only_b_2_to_9')
    for name in must:
        row(name, extras[name], design.get(name), 'design')
    design_ok = not any(d['source'] == 'design' for d in different) and all(design.get(name) is not None for name in must)

    head('C. MORE DESIGN NUMBERS, SHOWN FOR INFORMATION. They gate nothing.')
    for name in ('eligible_with_a_type_without_leftover', 'eligible_without_any_leftover_2_to_9',
                 'final_with_a_type_without_leftover', 'final_without_any_leftover_2_to_9',
                 'final_open_a_type_other_than_land_or_habit', 'final_open_only_land_or_habit',
                 'final_open_one_type', 'final_open_two_types', 'pull_push_both_2_and_3', 'pull_push_only_one',
                 'final_passages_with_exactly_one_open_form'):
        row(name, extras[name], design.get(name), 'design-info', gating=False)
    for name in ('passages_with_an_agreed_entry', 'final_leftover_on_needed_noetic'):
        want = design.get(name)
        for sub in extras[name]:
            row('%s[%s]' % (name, sub), extras[name][sub], None if want is None else want.get(sub), 'design-info', gating=False)

    head('D. THE TASK LIST IN PLAIN WORDS (REAL, from this run)')
    c8 = counts['by_practice_setting_count'][str(start)]
    by_kind = ', '.join('%s %d' % kv for kv in sorted(counts['excluded_by_kind'].items(), key=lambda kv: (-kv[1], kv[0])))
    lines += [
        '  %d passages in %d settings.' % (counts['passages'], counts['settings']),
        '  %d left out by rule 15 (%s). %d remain.' % (counts['excluded_passages'], by_kind, counts['passages_after_exclusion']),
        '  %d eligible (%s).' % (counts['eligible_passages'], ', '.join('%s %d' % kv for kv in counts['eligible_by_kind'].items())),
        '  The eligible passages hold %d agreed entries; %d of them are ^2 to ^9.' % (extras['eligible_agreed_entries'], extras['eligible_agreed_entries_2_to_9']),
        '  Left out of every note and counted apart, ^2 to ^9: %d only team A gave, %d only team B gave.' % (extras['eligible_only_a_2_to_9'], extras['eligible_only_b_2_to_9']),
        '  Agreed / only team A / only team B, all passages: ' + '; '.join('%s %d/%d/%d' % ((n,) + tuple(v)) for n, v in counts['entries_agreed_only_a_only_b'].items()) + '.',
        '  Passages per type: ' + ', '.join('%s %d' % kv for kv in counts['passages_per_type'].items()) + '.',
        '  Practice (%d settings): %d eligible passages (%s).' % (start, c8['practice_passages'], ', '.join('%s %d' % kv for kv in counts['practice_at_%d_passages_per_type' % start].items())),
        '  Final: %d passages (%s).' % (c8['final_passages'], ', '.join('%s %d' % kv for kv in counts['final_at_%d_passages_per_type' % start].items())),
        '  The question writer is sent %d K1 to K5 passages: %d in practice settings, %d in final settings.' % (counts['k1_to_k5_passages'], c8['k1_to_k5_practice'], c8['k1_to_k5_final']),
        '  Writer passages by setting role: %s.' % json.dumps(extras['writer_asks_by_setting_role'], ensure_ascii=False),
        '  Role-step ceilings: %d final, %d practice.' % (c8['role_step_ceiling_final'], c8['role_step_ceiling_practice']),
        '  Final passages that can carry one task only: %d. Of these, %d open exactly one form. The other %d open both LAND forms but hold one agreed ^4 entry, so the LAND rule allows one task: %s.'
        % (counts['final_at_%d_passages_that_can_carry_one_task_only' % start], extras['final_passages_with_exactly_one_open_form'],
           len(extras['final_passages_with_two_open_forms_but_one_task']), json.dumps(extras['final_passages_with_two_open_forms_but_one_task'])),
        '  Barred passages: %s.' % json.dumps(extras['barred_passages'], ensure_ascii=False),
        '  Entries dropped by the frozen clean step (bad quote or label): team A %d, team B %d.' % (extras['entries_dropped_by_clean']['team_a'], extras['entries_dropped_by_clean']['team_b']),
        '  Pairing check: the file-order rule finds as many pairs as the largest possible pairing in %d of %d passage-and-Noetic cells.' % (extras['pairing_cells_where_rule_finds_the_largest_pairing'], extras['pairing_cells']),
        '  Passages of a kind that is not used (K6 to K9), not excluded, whose agreed entries would open a form: %d %s.' % (len(extras['unused_kind_passages_that_would_open_a_form']), json.dumps(extras['unused_kind_passages_that_would_open_a_form'])),
    ]
    print(chr(10).join(lines).lstrip(chr(10)))
    return plan_ok, design_ok, different


# ----------------------------------------------------------------------------- main

def main(argv=None):
    parser = argparse.ArgumentParser(description='Option B: eligibility, exclusions and the practice split.')
    parser.add_argument('--project', default=str(PROJECT), help='the CASALESCENCE_NOETICS_v0_1 folder')
    parser.add_argument('--constants', default=None, help='PLAN_CONSTANTS.json (default: <project>/optionb/PLAN_CONSTANTS.json)')
    parser.add_argument('--out-root', default=None, help='where elig/ is written (default: <project>/optionb)')
    parser.add_argument('--report-only', action='store_true', help='print the count report and write nothing')
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):      # FILE_FORMATS.md section 0: a laptop tool prints in UTF-8
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', newline=chr(10))
    project = Path(args.project).resolve()
    try:
        constants, constants_path, constants_sha = load_constants(project, args.constants)
        work = project / constants['work_folder']
        out_root = Path(args.out_root).resolve() if args.out_root else work
        seal = work / SEAL_NAME
        if not args.report_only and out_root == work.resolve() and seal.is_file() and seal.read_bytes().strip():
            raise Stop('ALREADY_SEALED', '%s exists. The eligibility files are sealed in step 1 and are not written again.' % rel(seal, project))
        sealed_sources = check_sealed_sources(project, constants)
        result = build(project, constants)
        design, design_record, design_note = design_numbers(project, constants)
        print('Option B eligibility. Program %s. Constants sha256 %s.' % (PROGRAM, constants_sha))
        print('The %d source files of seal step 1 have their pinned size and sha256: %s.'
              % (len(sealed_sources), ', '.join(constants['sources'][name]['path'] for name in sealed_sources)))
        plan_ok, design_ok, different = report(result, constants, design, design_note)
        print()
        gating = [d for d in different if d['gating']]
        info = [d for d in different if not d['gating']]
        print('COUNTS THAT DIFFER AND GATE THE BUILD: %d' % len(gating))
        for d in gating:
            print('  %s: REAL %s, %s %s' % (d['count'], json.dumps(d['real'], ensure_ascii=False), d['source'], json.dumps(d['design'], ensure_ascii=False)))
        print('COUNTS THAT DIFFER AND GATE NOTHING: %d' % len(info))
        for d in info:
            print('  %s: REAL %s, %s %s' % (d['count'], json.dumps(d['real'], ensure_ascii=False), d['source'], json.dumps(d['design'], ensure_ascii=False)))
        if not plan_ok:
            raise Stop('COUNTS_DO_NOT_MATCH_PLAN', '%d count(s) differ from counts_real' % sum(1 for d in gating if d['source'] == 'plan'))
        if not design_ok:
            raise Stop('COUNTS_DO_NOT_MATCH_DESIGN', 'one of the four design entry totals differs or was not found in the design text')
        if args.report_only:
            print('REPORT ONLY. Nothing was written.')
            return 0
        made_by = {'program': PROGRAM, 'sha256': sha256_file(Path(__file__).resolve()), 'utc': utc_now()}
        inputs = result['inputs'] + [{'path': rel(constants_path, project), 'sha256': constants_sha}]
        if design_record:
            inputs.append(design_record)
        by_kind = collections.Counter(x['kind'] for x in result['exclusions'])
        exclusions = {'schema': SCHEMA_EXCLUSIONS, 'made_by': made_by, 'inputs': inputs,
                      'count': len(result['exclusions']),
                      'by_kind': {k: by_kind[k] for k in sorted(by_kind)},
                      'passages': result['exclusions']}
        eligibility = {'schema': SCHEMA_ELIGIBILITY, 'made_by': made_by, 'inputs': inputs,
                       'practice_settings': result['practice_settings'],
                       'reserve_settings_in_order': result['reserve_settings'],
                       'counts': result['counts'],
                       'counts_match_plan': True,
                       'passages': result['passages']}
        folder = out_root / 'elig'
        sha_x = write_json(folder / 'exclusions.json', exclusions)
        sha_e = write_json(folder / 'eligibility.json', eligibility)
        print('WROTE %s  sha256 %s' % (rel(folder / 'exclusions.json', project), sha_x))
        print('WROTE %s  sha256 %s' % (rel(folder / 'eligibility.json', project), sha_e))
        print('ELIGIBILITY_OK. Every gating count matched.')
        return 0
    except Stop as stop:
        print('STOPPED: %s: %s. Nothing was written.' % (stop.code, str(stop.detail).rstrip('.')))
        return 2


if __name__ == '__main__':
    sys.exit(main())
