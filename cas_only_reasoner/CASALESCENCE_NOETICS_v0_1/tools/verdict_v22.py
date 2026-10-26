"""Entry-by-entry label agreement, lean version 2.2 (plan 09_LABEL_AGREEMENT_PLAN_v2_2.md). Plain Python, no model.
It imports two files that sit beside it: check_labels_v21.py (the format checker) and verdict.py (the attempt-1
program: its filler list, its word splitting and its table of required fields; never changed, and sealed too).

MODES
  fixture (or --fixture)  Scores the hand-made fixture. Prints PASS when every number equals FIXTURE_EXPECTED.json.
  old                     The new counting on the attempt-1 labels, read-only. The old "words" is the label, at its
                          first place. It shows what the new counting alone does to attempt 1. Not a verdict.
  practice                The chain check on the practice passages: the tools run end to end and each receipt names
                          the guide; per team, the share of entries the checker rejected and the three limits that
                          make a verdict run INVALID. No agreement number. No outcome word.
                          --passages P --labels-a A [A2 ...] --labels-b B [--guide G --instructions I --receipt-a RA --receipt-b RB]
                          Not named: this folder's guide and instructions; <first labels file>.receipt.json.
  verdict                 Refuses unless every validity rule holds. Prints every table and the outcome word per
                          Noetic. Writes <out>.json (whole numbers and text only) and <out>.md.
                          --seal S --passages P --guide G --instructions I --plan PL --labels-a A [A2 ...] --labels-b B
                          --receipt-a RA --receipt-b RB --out PREFIX

THE MEASURE, for each Noetic ^1 to ^9, over CLEAR entries that are not a ^9 reached by reasoning (the bar row)
  Inside one passage the two teams' entries are paired ONE TO ONE. Two entries may pair only if: they have the same
  Noetic; their labels point at the same place (the two character spans overlap, AND every content word of the
  label with fewer different content words is a content word of the other label); their Minds pass the same test
  (the labels of the two ^1 entries; ^6 has no Mind); and, where REQUIRED in verdict.py names relative_to, the two
  related things pass the same test (both empty agree; one empty and one filled do not).
  Where things stand: a label at its first place inside its support; a ^1 label, and so a Mind, at the first place
  its name stands in the passage; a related thing at every place its words stand.
  The pairing has the most pairs that can be made. M = pairs. only A, only B = entries left over.
  E = M / (M + only A + only B). A case = a passage where at least one team has a bar-row entry.
  Kappa = Cohen's kappa on "has at least one bar-row entry", over the analysed passages.

TWO THINGS PRINTED WITH NO BAR OF THEIR OWN (they change no count above)
  Strict-label view, beside every E: the entries are paired again when two labels agree only if their spans overlap AND
  they have the same content words in the same order (Mind and related thing: the test above). M' = those pairs; the
  number is M' / (A + B - M'). Labels that agree only because one holds the other's words do not pair there.
  Reasoning-flag line (verdict and fixture mode): a ^9 reached by reasoning is counted apart only when the labeler sets
  the flag. Per team: how many clear ^9 entries without the flag have a support that holds an example word of guide
  rule 15(b), and in which passages. The words are read from the guide text at run time.

FILES (the team B tool and "check_labels_v21.py take" both write the first two)
  labels file   a list of final rows: a record, or a row with "labeler_failed": true.
  try log       <labels file>.tries.jsonl, one line per try: {"event": "try", "passage_id", "n", "record"}.
  receipt       a JSON object with "guide_sha256"; the other hashes and "complete" are checked when they are there.
  seal          SEAL.json of seal_v22.py: "is_a_seal": true, <role>["sha256"] for seven files, the owner's signed numbers.
"""
import argparse
import array
import collections
import copy
import hashlib
import json
import os
import random
import re
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_labels_v21 as checker  # noqa: E402
import verdict as attempt1  # noqa: E402

# ---- The numbers the owner signs, and the seeds. Nothing below this block holds a bar. ----
BAR_E = 0.80             # pass mark: entry agreement E at least this
BAR_KAPPA = 0.60         # presence mark: Cohen's kappa on presence at least this
MIN_CASES = 50           # minimum cases
MIN_ABSENT = 50          # minimum empty passages: neither team has a bar-row entry
MAX_PERCENT = 5          # the run is INVALID above this percent: unlabeled passages, dropped entries, withdrawn entries
SEED_INTERVALS = 20261006
RESAMPLES = 2000         # whole passages drawn again, for the 95% intervals
SEED_FLOOR = 20261007
FLOOR_SHUFFLES = 300     # the mechanism-free floor
MAX_PAIRING_SIDE = 14    # the pairing refuses a passage with more entries than this of one class on both sides
SEAL_SCHEMA = 'casalescence/label-agreement-v22-seal/1'
SIGNED = {'pass mark': BAR_E, 'presence mark': BAR_KAPPA, 'minimum cases': MIN_CASES, 'minimum empty passages': MIN_ABSENT}
SEALED_ROLES = ('passages', 'guide', 'instructions', 'checker', 'scorer', 'plan', 'attempt1_program')   # the last: tools/verdict.py
RECEIPT_KEYS = (('instructions_sha256', 'instructions'), ('checker_sha256', 'checker'), ('passages_sha256', 'passages'))
OUTCOMES = ('NOT_ENOUGH_CASES', 'NOT_LABELABLE_UNDER_THIS_METHOD', 'LABELABLE_UNDER_THIS_METHOD')
NOETICS = checker.NOETICS
BAR_ROWS = [('bar', n) for n in NOETICS]
ALL_ROWS = [('all', n) for n in NOETICS]
RULE15_ROWS = [('uncertain', '^8'), ('uncertain', '^9'), ('reasoning', '^9')]
ROW_NAMES = {'bar': '%s', 'all': '%s', 'uncertain': 'uncertain %s', 'reasoning': '%s reached by reasoning'}
KINDS = ('same_span', 'one_inside_other', 'overlap_in_part')
COUNTS = ('a', 'b', 'matched', 'only_a', 'only_b', 'cases', 'fully_matched_cases', 'cases_with_a_pair', 'neither',
          'presence_both', 'presence_only_a', 'presence_only_b') + tuple('matched_' + kind for kind in KINDS)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def text3(value):
    """A fraction as text with three decimals, half rounded up, worked out with whole numbers."""
    if value is None:
        return 'n/a'
    thousandths = (abs(value.numerator) * 2000 + value.denominator) // (2 * value.denominator)
    return ('-' if value < 0 and thousandths else '') + '%d.%03d' % divmod(thousandths, 1000)


def share(part, whole):
    return text3(Fraction(part, whole)) if whole else 'n/a'


def kappa_exact(both, only_a, only_b, neither):
    """Cohen's kappa on presence from the four passage counts, as an exact fraction. None when it has no value."""
    n = both + only_a + only_b + neither
    if n == 0:
        return None
    pa, pb = Fraction(both + only_a, n), Fraction(both + only_b, n)
    chance = pa * pb + (1 - pa) * (1 - pb)
    return None if chance == 1 else (Fraction(both + neither, n) - chance) / (1 - chance)


def outcome_word(matched, only_a, only_b, both, pres_a, pres_b, neither):
    """Design point 3. The program prints the word; nobody else does. A missed bar is a failure."""
    if both + pres_a + pres_b < MIN_CASES or neither < MIN_ABSENT:
        return OUTCOMES[0]
    kappa, entries = kappa_exact(both, pres_a, pres_b, neither), matched + only_a + only_b
    if entries and Fraction(matched, entries) >= Fraction(str(BAR_E)) and kappa is not None and kappa >= Fraction(str(BAR_KAPPA)):
        return OUTCOMES[2]
    return OUTCOMES[1]


def validity_reasons(name, passages, unlabeled, written, dropped, withdrawn):
    """Design point 4: why one team makes the run INVALID. An empty list = it does not."""
    rules = (('team %s could not label %d of %d passages', unlabeled, passages),
             ('team %s: the checker dropped %d of %d entries', dropped, written),
             ('team %s: %d of %d entries were withdrawn between tries', withdrawn, written + withdrawn))
    return [(text + ' (more than %d%%)') % (name, part, whole, MAX_PERCENT) for text, part, whole in rules
            if part * 100 > MAX_PERCENT * whole]


# ---------------------------------------------------------------- entries and the same-place test
def meet(p, q):
    """How two quotes point at the same place: 'same_span', 'one_inside_other' or 'overlap_in_part'. None = they do not.
    A quote = (the places where it stands, its content words by verdict.py's rule)."""
    if not (p[1] <= q[1] or q[1] <= p[1]):
        return None
    best = None
    for s1, e1 in p[0]:
        for s2, e2 in q[0]:
            if s1 < e2 and s2 < e1:
                kind = 0 if (s1, e1) == (s2, e2) else 1 if (s1 <= s2 and e2 <= e1) or (s2 <= s1 and e1 <= e2) else 2
                best = kind if best is None else min(best, kind)
    return None if best is None else KINDS[best]


def scoring_entry(noetic, label, mind, related, uncertain, reasoning, label_spans, mind_spans, related_spans, support=''):
    """'words' = the content words of the label in their order (the strict-label view). 'support' is read by the reasoning-flag line only."""
    quotes = {'q_' + field: (tuple(spans), frozenset(attempt1.content(text))) for field, text, spans in
              (('label', label, label_spans), ('mind', mind, mind_spans), ('relative_to', related, related_spans))}
    return dict(quotes, noetic=noetic, label=label, mind=mind, relative_to=related, uncertain=uncertain, reasoning=reasoning,
                words=tuple(attempt1.content(label)), support=support)


def in_order(entries):
    """A fixed order that does not depend on the order in the file."""
    return sorted(entries, key=lambda e: (e['q_label'][0], e['noetic'], e['label'], e['mind'], e['relative_to'], e['uncertain'], e['reasoning']))


def new_entries(kept, text):
    """The kept entries of one final record (format 2.1) with their places. A label stands at its first place inside its support.
    A ^1 label, and so a Mind, stands at the first place of its name in the passage (rule 4). A related thing: every place it stands."""
    first = {e['label']: checker.all_places(text, e['label'])[0] for e in kept if e['noetic'] == '^1'}
    return in_order([scoring_entry(e['noetic'], e['label'], e['mind'], e['relative_to'], e['certainty'] == 'ambiguous', e.get('reached_by') == 'reasoning',
                                   [first[e['label']] if e['noetic'] == '^1' else checker.locate(text, e['support'], e['label'])],
                                   [first[e['mind']]] if e['mind'] else [], checker.all_places(text, e['relative_to']), e['support']) for e in kept])


def old_entries(entries, text):
    """Attempt-1 entries: 'words' is the label, at its first place; the Mind at its first place; kept by verdict.py's rule."""
    kept = []
    for e in entries:
        words, mind, related = e.get('words', ''), e.get('mind') or '', e.get('relative_to') or ''
        if e.get('noetic') in NOETICS and words and words in text:
            at, mind_at = text.find(words), text.find(mind) if mind else -1
            kept.append(scoring_entry(e['noetic'], words, mind, related, e.get('certainty') == 'ambiguous', e.get('reached_by') == 'reasoning',
                                      [(at, at + len(words))], [(mind_at, mind_at + len(mind))] if mind_at >= 0 else [],
                                      checker.all_places(text, related, whole=False)))
    return in_order(kept), len(entries) - len(kept)


# ---------------------------------------------------------------- rows, pairing, counting
def in_row(key, row):
    """key = (noetic, uncertain, reasoning) of an entry. The bar row is the bar row of plan v1.2."""
    kind, noetic = row
    if key[0] != noetic or kind == 'all':
        return key[0] == noetic
    if kind == 'bar':
        return not key[1] and not (noetic == '^9' and key[2])
    return key[1] if kind == 'uncertain' else key[2] and not key[1]


def needs(row):
    """The other fields that must agree, from verdict.py (plan v1.2)."""
    return ('mind',) if row[0] == 'reasoning' else attempt1.REQUIRED[row[1]]


def prepare(a_entries, b_entries):
    """Everything the pairing needs for one passage, worked out once. For the label, the Mind and the related thing: how each entry
    of team A meets each entry of team B (a kind of meet(), or None; two empty fields meet as 'same_span'). No Noetic symbol is read.
    'same_words' (strict-label view only): do the two labels have the same content words in the same order."""
    def agree(x, y, field):
        if not x[field] or not y[field]:
            return None if x[field] or y[field] else KINDS[0]
        return meet(x['q_' + field], y['q_' + field])
    keys = {team + '_keys': [(e['noetic'], e['uncertain'], e['reasoning']) for e in entries] for team, entries in (('a', a_entries), ('b', b_entries))}
    return dict(keys, a=a_entries, b=b_entries, same_words=[[x['words'] == y['words'] for y in b_entries] for x in a_entries],
                **{f: [[agree(x, y, f) for y in b_entries] for x in a_entries] for f in ('label', 'mind', 'relative_to')})


def best_pairs(edges, ia, jb):
    """One-to-one pairing over the allowed pairs, edges = {(i, j): kind}. Returns [(i, j, kind)]. It has the most pairs that can be
    made; among such pairings the most 'same_span' pairs; then the most 'one_inside_other' pairs. No number hangs on entry order."""
    ia = [i for i in ia if any((i, j) in edges for j in jb)]
    jb = [j for j in jb if any((i, j) in edges for i in ia)]
    swap = len(jb) > len(ia)
    if swap:
        ia, jb, edges = jb, ia, {(j, i): kind for (i, j), kind in edges.items()}
    if len(jb) > MAX_PAIRING_SIDE:
        raise SystemExit('REFUSED: one passage has more than %d entries of one class on both sides' % MAX_PAIRING_SIDE)
    memo = {}
    def best(k, used):   # the best (pairs, same-span pairs, inside pairs) for entries k onward, and the choice for k
        if k == len(ia):
            return (0, 0, 0), None
        if (k, used) not in memo:
            top = (best(k + 1, used)[0], None)
            for n, j in enumerate(jb):
                kind = edges.get((ia[k], j))
                if kind and not used >> n & 1:
                    rest = best(k + 1, used | 1 << n)[0]
                    score = (rest[0] + 1, rest[1] + (kind == KINDS[0]), rest[2] + (kind == KINDS[1]))
                    if score > top[0]:
                        top = (score, n)
            memo[(k, used)] = top
        return memo[(k, used)]
    pairs, used = [], 0
    for k in range(len(ia)):
        n = best(k, used)[1]
        if n is not None:
            pairs.append((ia[k], jb[n], edges[(ia[k], jb[n])]))
            used |= 1 << n
    return [(j, i, kind) for i, j, kind in pairs] if swap else pairs


def pair_row(p, row, b_keys=None, strict=False):
    """One passage, one row: the entries of team A and of team B that are in the row, and their pairs. The kind of a pair
    is the loosest kind among its label and the other fields the row needs (its Mind, its related thing). strict = the
    strict-label view: two entries may pair only if their labels also have the same content words in the same order."""
    ia = [i for i, key in enumerate(p['a_keys']) if in_row(key, row)]
    jb = [j for j, key in enumerate(b_keys or p['b_keys']) if in_row(key, row)]
    kinds = {(i, j): [p[field][i][j] for field in ('label',) + needs(row)] for i in ia for j in jb if not strict or p['same_words'][i][j]}
    edges = {pair: max(found, key=KINDS.index) for pair, found in kinds.items() if all(found)}
    return ia, jb, best_pairs(edges, ia, jb) if edges else []


def tally(prepared, ids, row):
    """One row over all analysed passages: the counts, the per-passage cells, the pairs and the entries left over."""
    t, cells, pairs_out, left = collections.Counter(), [], [], []
    for pid in ids:
        p = prepared[pid]
        ia, jb, pairs = pair_row(p, row)
        cells.append((len(pairs), len(ia) - len(pairs), len(jb) - len(pairs), bool(ia), bool(jb)))
        if not ia and not jb:
            t['neither'] += 1
            continue
        t.update(a=len(ia), b=len(jb), matched=len(pairs), only_a=len(ia) - len(pairs), only_b=len(jb) - len(pairs), cases=1,
                 fully_matched_cases=int(len(pairs) == len(ia) == len(jb)), cases_with_a_pair=int(bool(pairs)), presence_both=int(bool(ia and jb)),
                 presence_only_a=int(not jb), presence_only_b=int(not ia), strict=len(pair_row(p, row, strict=True)[2]))
        for i, j, kind in pairs:
            t['matched_' + kind] += 1
            pairs_out.append({'passage': pid, 'row': ROW_NAMES[row[0]] % row[1], 'how': kind, 'team_a': p['a'][i]['label'], 'team_b': p['b'][j]['label']})
        for team, entries, mine in (('A', p['a'], set(ia) - {i for i, _, _ in pairs}), ('B', p['b'], set(jb) - {j for _, j, _ in pairs})):
            left += [{'passage': pid, 'row': ROW_NAMES[row[0]] % row[1], 'team': team, 'label': entries[k]['label'], 'mind': entries[k]['mind'],
                      'relative_to': entries[k]['relative_to']} for k in sorted(mine)]
    table = dict({key: t[key] for key in COUNTS}, entry_agreement=share(t['matched'], t['matched'] + t['only_a'] + t['only_b']),
                 matched_over_a=share(t['matched'], t['a']), matched_over_b=share(t['matched'], t['b']),
                 kappa=text3(kappa_exact(t['presence_both'], t['presence_only_a'], t['presence_only_b'], t['neither'])),
                 strict_label_matched=t['strict'], strict_label_view=share(t['strict'], t['a'] + t['b'] - t['strict']))
    return table, cells, pairs_out, left


def old_way(prepared, ids, row):
    """Attempt 1's 'strict agreement' on the same entries: (passages where one pair passes verdict.py's own word test, cases)."""
    agree = cases = 0
    for pid in ids:
        p = prepared[pid]
        ea = [e for e, key in zip(p['a'], p['a_keys']) if in_row(key, row)]
        eb = [e for e, key in zip(p['b'], p['b_keys']) if in_row(key, row)]
        cases += bool(ea or eb)
        agree += any(attempt1.same_span(x['label'], y['label']) and all(attempt1.same_field(x[f], y[f]) for f in needs(row))
                     for x in ea for y in eb)
    return agree, cases


def intervals(cells, n):
    """95% intervals for E and kappa per bar row: whole passages drawn again with replacement, RESAMPLES times.
    An interval needs a value in at least 9 of 10 draws; otherwise it is 'n/a'."""
    def interval(values):
        if len(values) * 10 < RESAMPLES * 9:
            return ['n/a', 'n/a']
        values.sort()
        return ['%.3f' % values[int(0.025 * len(values))], '%.3f' % values[int(0.975 * len(values)) - 1]]
    rng, draws = random.Random(SEED_INTERVALS), []
    for _ in range(RESAMPLES):
        counts = array.array('H', bytes(2 * n))
        for _ in range(n):
            counts[int(rng.random() * n)] += 1
        draws.append(counts)
    out = {}
    for name, row_cells in cells.items():
        some = [(k, m, m + oa + ob, pa and pb, pa and not pb, pb and not pa) for k, (m, oa, ob, pa, pb) in enumerate(row_cells) if pa or pb]
        es, ks = [], []
        for counts in draws:
            m = entries = both = only_a = only_b = 0
            for k, cm, ce, cboth, ca, cb in some:
                c = counts[k]
                if c:
                    m, entries, both, only_a, only_b = m + c * cm, entries + c * ce, both + c * cboth, only_a + c * ca, only_b + c * cb
            if entries:
                es.append(m / entries)
            kappa = kappa_exact(both, only_a, only_b, n - both - only_a - only_b)
            if kappa is not None:
                ks.append(float(kappa))
        out[name] = (interval(es), interval(ks))
    return out


def floor(prepared, ids):
    """The mechanism-free floor: inside each passage the Noetic symbols of team B's entries are shuffled among those
    entries, and E is worked out again for every bar row. Every other field stays with its entry."""
    rng, runs, kept, total = random.Random(SEED_FLOOR), {n: [] for n in NOETICS}, 0, 0
    for _ in range(FLOOR_SHUFFLES):
        sums = {n: [0, 0] for n in NOETICS}
        for pid in ids:
            p = prepared[pid]
            symbols = [key[0] for key in p['b_keys']]
            for i in range(len(symbols) - 1, 0, -1):
                j = int(rng.random() * (i + 1))
                symbols[i], symbols[j] = symbols[j], symbols[i]
            kept += sum(1 for s, key in zip(symbols, p['b_keys']) if s == key[0])
            total += len(symbols)
            shuffled = [(s, key[1], key[2]) for s, key in zip(symbols, p['b_keys'])]
            for noetic in {key[0] for key in p['a_keys']} | set(symbols):
                ia, jb, pairs = pair_row(p, ('bar', noetic), shuffled)
                sums[noetic][0] += len(pairs)
                sums[noetic][1] += len(ia) + len(jb) - len(pairs)
        for n in NOETICS:
            if sums[n][1]:
                runs[n].append(Fraction(sums[n][0], sums[n][1]))
    return {'shuffles': FLOOR_SHUFFLES, 'kept_own_symbol': share(kept, total),
            'rows': {n: {'mean': text3(sum(v) / len(v)) if v else 'n/a', 'max': text3(max(v)) if v else 'n/a'} for n, v in runs.items()}}


def analyse(team_a, team_b, ids, random_parts=True):
    """team_a, team_b = {passage id: scoring entries}. ids = the analysed passages, in a fixed order."""
    prepared = {pid: prepare(team_a[pid], team_b[pid]) for pid in ids}
    out, cells = {'bar_rows': {}, 'all_entries_rows': {}, 'rule15_rows': {}, 'pairs': [], 'unmatched': []}, {}
    for group, rows in (('bar_rows', BAR_ROWS), ('all_entries_rows', ALL_ROWS), ('rule15_rows', RULE15_ROWS)):
        for row in rows:
            table, row_cells, pairs, left = tally(prepared, ids, row)
            if group != 'all_entries_rows':
                agree, cases = old_way(prepared, ids, row)
                table['attempt1_way_agree'], table['attempt1_way_share'] = agree, share(agree, cases)
            if group == 'bar_rows':
                cells[row[1]] = row_cells
                out['pairs'] += pairs
                out['unmatched'] += left
            out[group][ROW_NAMES[row[0]] % row[1]] = table
    if random_parts:
        out['floor'] = floor(prepared, ids)
        for name, (e_interval, k_interval) in intervals(cells, len(ids)).items():
            out['bar_rows'][name].update(entry_agreement_interval95=e_interval, kappa_interval95=k_interval,
                                         floor_mean=out['floor']['rows'][name]['mean'], floor_max=out['floor']['rows'][name]['max'])
    return out


# ---------------------------------------------------------------- reading the teams, the report, the gate
def empty_team():
    return {'entries': {}, 'problems': [], 'unlabeled': [], 'kept': 0, 'written': 0, 'lost_with_unlabeled': 0,
            'dropped': collections.Counter(), 'withdrawn': collections.Counter(), 'first_try': [0, 0], 'dropped_list': []}


def load_team(label_paths):
    """One team's labels files and the try logs beside them: ({passage id: final row}, {passage id: [tries]}, faults)."""
    rows, tries, problems = {}, {}, []
    for path in label_paths:
        data, log = load(path), Path(str(path) + '.tries.jsonl')
        for row in data if isinstance(data, list) else []:
            pid = row.get('passage_id') if isinstance(row, dict) else None
            if pid in rows:
                problems.append('two rows for passage %s' % pid)
            rows[pid] = row
        if not isinstance(data, list) or not log.is_file():
            problems.append('%s is not a list of rows, or has no try log %s beside it' % (Path(path).name, log.name))
            continue
        for pid, records in checker.read_tries(log).items():
            if pid in tries:
                problems.append('passage %s has tries in two try logs' % pid)
            tries[pid] = records
    return rows, tries, problems


def read_team(rows, tries, problems, passages):
    """One team (format 2.1): the scoring entries, the counts, and every chain fault. A row is final when it is the record of a
    last try that passes (LABELED), or the 'could not be labeled' row after a third try that still has a message (NOT_LABELED).
    The checker is run again on every last try: an entry with a message is dropped; the passage's other entries are lost with it."""
    team = empty_team()
    team['problems'] += problems
    unknown = sorted(str(pid) for pid in rows if pid not in passages)
    if unknown:
        team['problems'].append('%d rows are for passages that are not in the passages file (first: %s)' % (len(unknown), unknown[0]))
    for pid in sorted(passages):
        text, row, past = passages[pid], rows.get(pid), tries.get(pid, [])
        failed = isinstance(row, dict) and row.get('labeler_failed') is True
        state = checker.try_state(past, text, pid)
        if row is None:
            team['problems'].append('passage %s has no final row' % pid)
        elif not past or state in ('OPEN', 'BROKEN'):
            team['problems'].append('passage %s is not final in the try log (%d tries, %s)' % (pid, len(past), state))
        elif failed != (state == 'NOT_LABELED'):
            team['problems'].append('passage %s: the row and the try log disagree (the log says %s; the row is %s)'
                                    % (pid, state, 'the "could not be labeled" row' if failed else 'a record'))
        elif not failed and row != past[-1]:
            team['problems'].append('the row of passage %s is not the record of its last logged try' % pid)
        else:
            first, per = checker.check_parts(past[0], text, pid)[1], checker.check_parts(past[-1], text, pid)[1]
            entries = past[-1]['entries'] if per else []
            team['first_try'][0] += len(first)
            team['first_try'][1] += sum(1 for faults in first if faults)
            team['written'] += len(per)
            for entry, faults in zip(entries, per):
                if faults:
                    noetic = entry.get('noetic') if isinstance(entry, dict) else None
                    team['dropped'][noetic if noetic in NOETICS else 'no Noetic'] += 1
                    team['dropped_list'].append({'passage': pid, 'messages': faults})
            team['withdrawn'].update(checker.withdrawn(past))
            good = [entry for entry, faults in zip(entries, per) if not faults]
            if failed:
                team['unlabeled'].append(pid)
                team['lost_with_unlabeled'] += len(good)
            else:
                team['entries'][pid] = new_entries(good, text)
                team['kept'] += len(good)
    return team


def read_old_team(rows, passages):
    """One team's attempt-1 labels. No try log existed; entries are kept or dropped by the attempt-1 program's rule."""
    team = empty_team()
    for row in rows:
        pid = row['passage_id']
        if row.get('labeler_failed'):
            team['unlabeled'].append(pid)
            continue
        team['entries'][pid], dropped = old_entries(row.get('entries', []), passages[pid])
        team['kept'] += len(team['entries'][pid])
        team['written'] += len(row.get('entries', []))
        team['dropped']['bad quote or symbol'] += dropped
    return team


def rule15b_words(guide):
    """The example words of guide rule 15(b), read from the guide and typed nowhere here: the words in double quotes after the last
    'Words that show this:' of bullet (b), among the bullets right under the one line that starts with '15. '."""
    tails = re.findall(r'^15\. [^\n]*\n(?:[ \t]+- [^\n]*\n)*?[ \t]+- \*\*\(b\)[^\n]*Words that show this:([^\n]*)',
                       Path(guide).read_text(encoding='utf-8'), re.M)
    words = re.findall('"([^"]+)"', tails[0]) if len(tails) == 1 else []
    if not words:
        raise SystemExit('REFUSED: %s holds no rule 15(b) with the sentence "Words that show this:" and words in double quotes' % guide)
    return words


def reasoning_flag_line(team_a, team_b, ids, words):
    """Report only, per team: the ^9 bar-row entries of the analysed passages, and those whose support holds one of the words (whole words, any case)."""
    out = {'words_read_from_guide_rule_15b': list(words)}
    for name, team in (('A', team_a), ('B', team_b)):
        mine = [(pid, e) for pid in ids for e in team[pid] if in_row((e['noetic'], e['uncertain'], e['reasoning']), ('bar', '^9'))]
        hits = [pid for pid, e in mine if any(checker.find_whole(e['support'].lower(), word.lower()) != -1 for word in words)]
        out[name] = {'clear_9_without_the_flag': len(mine), 'support_holds_a_word': len(hits), 'passages': sorted(set(hits))}
    return out


def build_report(mode, passages, team_a, team_b, random_parts=True, words=None):
    ids = sorted(pid for pid in passages if pid in team_a['entries'] and pid in team_b['entries'])
    report = {'schema': 'casalescence/label-agreement-v22-report/1', 'mode': mode, 'is_a_verdict': False,
              'bars': {name: str(value) for name, value in SIGNED.items()}, 'invalid_above_percent': MAX_PERCENT,
              'seeds': {'intervals': SEED_INTERVALS, 'floor': SEED_FLOOR}, 'resamples': RESAMPLES,
              'passages': {'given': len(passages), 'analysed': len(ids), 'left_out': sorted(set(passages) - set(ids))}, 'teams': {}}
    why = []
    for name, team in (('A', team_a), ('B', team_b)):
        dropped, withdrawn = sum(team['dropped'].values()), sum(team['withdrawn'].values())
        report['teams'][name] = {
            'passages_labeled': len(team['entries']), 'passages_not_labeled': len(team['unlabeled']),
            'entries_in_last_tries': team['written'], 'entries_kept': team['kept'], 'entries_dropped': dropped,
            'entries_withdrawn': withdrawn, 'entries_lost_with_unlabeled_passages': team['lost_with_unlabeled'],
            'dropped_by_noetic': dict(sorted(team['dropped'].items())), 'withdrawn_by_noetic': dict(sorted(team['withdrawn'].items())),
            'first_try_entries': team['first_try'][0], 'first_try_entries_with_a_message': team['first_try'][1],
            'dropped_entries': team['dropped_list']}
        why += validity_reasons(name, len(passages), len(team['unlabeled']), team['written'], dropped, withdrawn)
    report['run_is_valid'], report['why_invalid'] = not why, why
    report.update(analyse(team_a['entries'], team_b['entries'], ids, random_parts))
    report.update({'reasoning_flag_line': reasoning_flag_line(team_a['entries'], team_b['entries'], ids, words)} if words else {})
    for name, table in report['bar_rows'].items():
        lost = sum(team['dropped'][name] + team['withdrawn'][name] for team in (team_a, team_b))
        table['dropped_and_withdrawn'] = lost
        table['entry_agreement_if_those_were_misses'] = share(table['matched'], table['matched'] + table['only_a'] + table['only_b'] + lost)
    return report


def gate_problems(seal, found, receipts, teams):
    """Design point 4: every reason to refuse a verdict. An empty list = the verdict may be printed."""
    problems = []
    if not isinstance(seal, dict) or seal.get('schema') != SEAL_SCHEMA or seal.get('is_a_seal') is not True:
        return ['the seal record is not a seal of seal_v22.py ("schema" %s and "is_a_seal": true); a practice record is not a seal' % SEAL_SCHEMA]
    if seal.get('no_label_existed_when_sealed') is not True:
        problems.append('the seal does not say "no_label_existed_when_sealed": true')
    signed = seal['owner_signoff'].get('numbers_signed') if isinstance(seal.get('owner_signoff'), dict) else None
    try:
        signed_same = all(Fraction(str(signed[name])) == Fraction(str(value)) for name, value in SIGNED.items())
    except (TypeError, KeyError, ValueError, ZeroDivisionError):
        signed_same = False
    if not signed_same:
        problems.append('the numbers the owner signed in the seal (%s) are not the numbers this program holds (%s)' % (signed, SIGNED))
    for role in SEALED_ROLES:
        sealed = seal[role].get('sha256') if isinstance(seal.get(role), dict) else None
        if sealed != found[role]:
            problems.append('the %s file is not the sealed one (sealed %s, found %s)' % (role, str(sealed)[:12], found[role][:12]))
    return problems + team_problems(found, receipts, teams)


def team_problems(found, receipts, teams):
    """Every fault in the two teams' receipts and chains. Practice mode and the gate of verdict mode both read it."""
    problems = []
    for name in ('A', 'B'):
        receipt = receipts[name] if isinstance(receipts[name], dict) else {}
        if receipt.get('guide_sha256') != found['guide']:
            problems.append('team %s: the receipt does not name the sealed guide hash, or there is no receipt file' % name)
        if receipt.get('complete') is False:
            problems.append('team %s: the receipt says the labeling is not complete' % name)
        for key, role in RECEIPT_KEYS + (('labels_sha256', 'labels_' + name.lower()),):
            if key in receipt and found.get(role) and receipt[key] != found[role]:
                problems.append('team %s: the receipt\'s %s is not the hash of the file given' % (name, key))
        problems += ['team %s: %s' % (name, problem) for problem in teams[name]['problems']]
    return problems


def files_given(args, roles):
    """(sha256 by role of the files a run was given and of the three programs, the two receipts). A team with several
    labels files: '', so its receipt's labels hash is not compared. A receipt file that is not there: {} (names no guide)."""
    found = dict({r: sha(getattr(args, r)) for r in roles}, checker=sha(checker.__file__), scorer=sha(__file__), attempt1_program=sha(attempt1.__file__))
    found.update({'labels_' + team: sha(paths[0]) if len(paths) == 1 else '' for team, paths in (('a', args.labels_a), ('b', args.labels_b))})
    return found, {team.upper(): load(path) if Path(path).is_file() else {} for team, path in (('a', args.receipt_a), ('b', args.receipt_b))}


def floats_in(value, path=''):
    """Where a report holds a number that is not whole. The report must hold whole numbers and text only."""
    if isinstance(value, float):
        return [path]
    items = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else []
    return [found for key, item in items for found in floats_in(item, '%s/%s' % (path, key))]


# ---------------------------------------------------------------- printing
STRICT_COLUMN = 'strict-label view (no bar)'   # M'/(A+B-M'): the pairing made again; two labels must have the same content words in the same order
COUNT_COLUMNS = [('A', 'a'), ('B', 'b'), ('M', 'matched'), ('only A', 'only_a'), ('only B', 'only_b'),
                 ('E = M/(M+only A+only B)', lambda t: '%d/%d = %s' % (t['matched'], t['matched'] + t['only_a'] + t['only_b'], t['entry_agreement']))]
COUNT_COLUMNS.append((STRICT_COLUMN, lambda t: '%d/%d = %s' % (t['strict_label_matched'], t['a'] + t['b'] - t['strict_label_matched'],
                                                               t['strict_label_view'])))
SHARE_COLUMNS = [('M/A', 'matched_over_a'), ('M/B', 'matched_over_b')]
PAIR_COLUMNS = [('pairs: all same span', 'matched_same_span'), ('pairs: one inside the other', 'matched_one_inside_other'),
                ('pairs: overlap in part', 'matched_overlap_in_part')]   # a pair is listed by the loosest of its label, Mind and related thing
TABLES = [
    ('Table 1. The bar row: clear entries, not a ^9 reached by reasoning. Entry by entry.', 'bar_rows',
     COUNT_COLUMNS + [('E 95%', 'entry_agreement_interval95'), ('kappa', 'kappa'), ('kappa 95%', 'kappa_interval95'), ('cases', 'cases'),
                      ('neither', 'neither'), ('outcome', 'outcome')]),
    ('Table 2. Beside table 1. No bar on any of these. A pair is listed by the loosest of its label, its Mind and its related thing.', 'bar_rows',
     SHARE_COLUMNS + [('fully matched cases', 'fully_matched_cases'), ('cases with a pair', 'cases_with_a_pair')] + PAIR_COLUMNS
     + [('dropped + withdrawn', 'dropped_and_withdrawn'), ('E if those were misses', 'entry_agreement_if_those_were_misses'),
        ('floor mean', 'floor_mean'), ('floor max', 'floor_max'),
        ('attempt-1 way (passages)', lambda t: '%d/%d = %s' % (t['attempt1_way_agree'], t['cases'], t['attempt1_way_share']))]),
    ('Table 3. All entries, clear and ambiguous pooled. No bar.', 'all_entries_rows',
     COUNT_COLUMNS + SHARE_COLUMNS + [('cases', 'cases')] + PAIR_COLUMNS),
    ('Table 4. The rule-15 rows of plan v1.2. No bar.', 'rule15_rows', COUNT_COLUMNS + SHARE_COLUMNS + [('cases', 'cases')] + PAIR_COLUMNS)]


def tables(report, outcome):
    """The four tables as (title, header, rows of text)."""
    out = []
    for title, group, columns in TABLES:
        columns = [column for column in columns if outcome or column[0] != 'outcome']
        rows = []
        for name, t in report[group].items():
            values = [how(t) if callable(how) else t.get(how, 'not worked out') for _, how in columns]
            rows.append([name] + ['[%s, %s]' % tuple(v) if isinstance(v, list) else str(v) for v in values])
        out.append((title, ['row'] + [column[0] for column in columns], rows))
    return out


def head_lines(report):
    p = report['passages']
    lines = ['passages given %d | analysed %d | left out %d %s' % (p['given'], p['analysed'], len(p['left_out']), ' '.join(p['left_out'][:12]))]
    for name, t in report['teams'].items():
        lines.append('team %s: passages labeled %d, not labeled %d | entries in last tries %d: kept %d, dropped %d %s, lost with '
                     'unlabeled passages %d | withdrawn between tries %d %s'
                     % (name, t['passages_labeled'], t['passages_not_labeled'], t['entries_in_last_tries'], t['entries_kept'],
                        t['entries_dropped'], json.dumps(t['dropped_by_noetic']), t['entries_lost_with_unlabeled_passages'],
                        t['entries_withdrawn'], json.dumps(t['withdrawn_by_noetic'])))
    lines.append('run is valid: %s' % ('yes' if report['run_is_valid'] else 'NO. ' + '; '.join(report['why_invalid'])))
    if 'floor' in report:
        lines.append('floor: %d shuffles; team B entries that kept their own symbol: %s. A moved symbol keeps its entry\'s own fields, so the '
                     'floor is low for rows that need a related thing.' % (report['floor']['shuffles'], report['floor']['kept_own_symbol']))
    if 'reasoning_flag_line' in report:
        line = report['reasoning_flag_line']
        lines.append('report only, no count changes: clear ^9 entries with no reasoning flag whose support holds a word of guide rule 15(b) (%s): %s'
                     % (', '.join(line['words_read_from_guide_rule_15b']), '; '.join(
                         'team %s %d of %d%s' % (name, line[name]['support_holds_a_word'], line[name]['clear_9_without_the_flag'],
                                                 ' (%s)' % ' '.join(line[name]['passages']) if line[name]['passages'] else '') for name in 'AB')))
    return lines


def pass_notes(report):
    """What the report says plainly beside a pass: an interval that reaches below a bar; a pass that fails if the lost entries count as misses."""
    notes = []
    for name, t in report['bar_rows'].items():
        if t.get('outcome') != OUTCOMES[2]:
            continue
        for key, bar, what in (('entry_agreement_interval95', BAR_E, 'E'), ('kappa_interval95', BAR_KAPPA, 'kappa')):
            if t[key][0] == 'n/a' or Fraction(t[key][0]) < Fraction(str(bar)):
                notes.append('NOTE %s: the 95%% interval of %s reaches below its bar, or has no value: [%s, %s].' % (name, what, t[key][0], t[key][1]))
        entries = t['matched'] + t['only_a'] + t['only_b'] + t['dropped_and_withdrawn']
        if Fraction(t['matched'], entries) < Fraction(str(BAR_E)):
            notes.append('NOTE %s: E meets the pass mark, but not if its %d dropped and withdrawn entries are counted as misses.'
                         % (name, t['dropped_and_withdrawn']))
    return notes


def show(report):
    print(chr(10).join(head_lines(report)))
    for title, header, rows in tables(report, 'outcome' in report['bar_rows']['^1']):
        widths = [max(len(line[c]) for line in [header] + rows) for c in range(len(header))]
        print(chr(10).join(['', title] + ['  '.join(v.ljust(w) for v, w in zip(line, widths)).rstrip() for line in [header] + rows]))
    print(chr(10).join(pass_notes(report)))


# ---------------------------------------------------------------- the four modes
def run_old(args):
    folder = Path(args.verdict_dir)
    passages = {p['id']: p['text'] for p in load(folder / 'passages_sealed.json')}
    team_a, team_b = (read_old_team(load(folder / ('labels_team_%s.json' % t)), passages) for t in 'ab')
    report = build_report('old', passages, team_a, team_b)
    print('PRACTICE ARITHMETIC ON THE ATTEMPT-1 LABELS. THIS IS NOT A VERDICT. It prints no outcome word.')
    print('It reads %s and writes nothing. The old "words" is used as the label, at its first place in the passage.' % folder)
    show(report)
    if (folder / 'VERDICT_REPORT.json').is_file():
        old, mine = load(folder / 'VERDICT_REPORT.json')['per_class'], dict(report['bar_rows'], **report['rule15_rows'])
        same = all(old[name]['strict_agreement_count'] == t['attempt1_way_agree'] and old[name]['cases_marked_by_at_least_one'] == t['cases']
                   for name, t in mine.items())
        print('check: the "attempt-1 way" numbers and the cases equal the attempt-1 report in all %d rows: %s' % (len(mine), 'yes' if same else 'NO'))
    print('THIS IS NOT A VERDICT.')
    return 0


def run_practice(args):
    passages = {p['id']: p['text'] for p in load(args.passages)}
    teams = {'A': read_team(*load_team(args.labels_a), passages), 'B': read_team(*load_team(args.labels_b), passages)}
    faults = team_problems(*files_given(args, ('passages', 'guide', 'instructions')), teams)
    print('PRACTICE TOOL CHECK. THIS IS NOT A VERDICT. It shows no agreement number and no outcome word.')
    chain = not faults
    for name, team in teams.items():
        rejected, gone = sum(team['dropped'].values()), sum(team['withdrawn'].values())
        low = rejected * 100 < MAX_PERCENT * team['written']
        limits = validity_reasons(name, len(passages), len(team['unlabeled']), team['written'], rejected, gone)   # the limits of a verdict run
        chain = chain and low and not limits
        print('team %s: passages labeled %d, not labeled after three tries %d | entries in last tries %d, rejected by the checker %d '
              '(%s) %s | on the first try: %d entries, %d with a message | withdrawn between tries %d %s'
              % (name, len(team['entries']), len(team['unlabeled']), team['written'], rejected, share(rejected, team['written']),
                 json.dumps(dict(sorted(team['dropped'].items()))), team['first_try'][0], team['first_try'][1],
                 gone, json.dumps(dict(sorted(team['withdrawn'].items())))))
        print(chr(10).join(['  fewer than %d%% of team %s entries rejected: %s' % (MAX_PERCENT, name, 'yes' if low else 'NO')]
                           + ['  a limit that would make a verdict run INVALID is passed: ' + limit for limit in limits]))
    if not teams['A']['problems'] and not teams['B']['problems']:
        build_report('practice', passages, teams['A'], teams['B'])
        print('the scorer ran to its end on these labels: yes (its numbers are not shown in practice mode)')
    print(chr(10).join(['chain fault: ' + fault for fault in faults] + ['PRACTICE CHECK: ' + ('PASS' if chain else 'NOT PASSED')]))
    return 0 if chain else 1


def run_verdict(args):
    outs = [Path(args.out + '.json'), Path(args.out + '.md')]
    if any(path.exists() for path in outs):
        raise SystemExit('REFUSED: %s or %s exists already. A report is written once.' % tuple(outs))
    passages = {p['id']: p['text'] for p in load(args.passages)}
    found, receipts = files_given(args, ('passages', 'guide', 'instructions', 'plan'))
    teams = {'A': read_team(*load_team(args.labels_a), passages), 'B': read_team(*load_team(args.labels_b), passages)}
    problems = gate_problems(load(args.seal), found, receipts, teams)
    if problems:
        print('NO VERDICT. The program refuses, for %d reasons:' % len(problems))
        print(chr(10).join(' - ' + problem for problem in problems[:60]))
        return 2
    report = build_report('verdict', passages, teams['A'], teams['B'], words=rule15b_words(args.guide))
    report.update(is_a_verdict=report['run_is_valid'], sha256=dict(found, seal=sha(args.seal)))
    for t in report['bar_rows'].values():
        t['outcome'] = outcome_word(t['matched'], t['only_a'], t['only_b'], t['presence_both'], t['presence_only_a'], t['presence_only_b'],
                                    t['neither']) if report['run_is_valid'] else 'RUN_INVALID_NO_OUTCOME'
    report['notes'] = pass_notes(report)
    asked, answered = receipts['B'].get('model_asked_for'), receipts['B'].get('models_that_answered')
    if isinstance(answered, dict) and set(answered) != {asked}:
        report['notes'].append('NOTE team B: the name asked for was %s; the replies carry %s.' % (asked, json.dumps(answered, sort_keys=True)))
    if floats_in(report):
        raise SystemExit('REFUSED: the report holds a number that is not whole at %s' % floats_in(report)[0])
    title = 'LABEL-AGREEMENT VERDICT, VERSION 2.2' if report['run_is_valid'] else 'THE RUN IS INVALID. NO OUTCOME WORD IS GIVEN.'
    scope = ('A pass means two model teams point at the same things for that Noetic under this guide. It does not show the labels '
             'are correct, and it tests no reader. A missed bar is a failure of this method for that Noetic. The ^8 row and the ^9 '
             'row count the same pairs from two ends.')
    bars = 'bars: E at least %s and kappa at least %s, with at least %d cases and at least %d passages where neither team has a bar-row entry' % (
        BAR_E, BAR_KAPPA, MIN_CASES, MIN_ABSENT)
    print(chr(10).join([title, scope, bars]))
    show(report)
    outcomes = ['  %s  %s' % (name, t['outcome']) for name, t in report['bar_rows'].items()]
    print(chr(10).join(report['notes'][len(pass_notes(report)):] + ['OUTCOME PER NOETIC'] + outcomes))
    markdown = ['# ' + title, '', scope, '', bars, ''] + ['- ' + line for line in head_lines(report) + report['notes']]
    for name, header, rows in tables(report, True):
        markdown += ['', '### ' + name, '', '| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)] + ['| ' + ' | '.join(r) + ' |' for r in rows]
    for path, body in ((outs[0], json.dumps(report, indent=1, ensure_ascii=False)), (outs[1], chr(10).join(markdown))):
        Path(str(path) + '.partial').write_text(body + chr(10), encoding='utf-8', newline=chr(10))
        os.replace(str(path) + '.partial', path)
    print(chr(10) + 'written: %s and %s' % tuple(outs))
    return 0 if report['run_is_valid'] else 1


def differences(expected, got, path=''):
    """Every place where the expected value is not the value worked out. Only keys named in the expected file are compared."""
    if isinstance(expected, dict) and isinstance(got, dict):
        return [d for key, value in expected.items() for d in (differences(value, got[key], path + '/' + key) if key in got
                                                                else ['%s/%s: expected %r, not worked out' % (path, key, value)])]
    return [] if expected == got else ['%s: expected %r, worked out %r' % (path, expected, got)]


def turned_round(value):
    """A copy in which every list of entries, and every set of keys, stands in the opposite order."""
    if isinstance(value, dict):
        return {key: list(reversed(turned_round(item))) if key == 'entries' and isinstance(item, list) else turned_round(item)
                for key, item in reversed(list(value.items()))}
    return [turned_round(item) for item in value] if isinstance(value, list) else value


def run_fixture(args):
    folder = Path(args.fixture_dir)
    expected, passages = load(folder / 'FIXTURE_EXPECTED.json'), {p['id']: p['text'] for p in load(folder / 'passages.json')}
    raw = {'A': load_team([folder / 'labels_team_a.json']), 'B': load_team([folder / 'labels_team_b.json'])}
    teams = {name: read_team(*raw[name], passages) for name in raw}
    words = rule15b_words(args.guide or HERE.parent / '02_LABELING_GUIDE_v2_2.md')   # the guide itself: the fixture pins what is read from it
    report = build_report('fixture', passages, teams['A'], teams['B'], words=words)
    diffs = differences(expected['report'], report) + ['a number that is not whole at ' + place for place in floats_in(report)]
    header, rows = tables(report, False)[0][1:]   # the two new things as they are printed: the last head line, and the new column of table 1
    strict = {r[0]: r[header.index(STRICT_COLUMN)] for r in rows}
    diffs += differences(expected['printed'], {'reasoning_flag_line': head_lines(report)[-1], 'table_1_strict_label_view': strict})
    # 1. the same files read in the opposite order must give the same report: nothing may hang on file order
    back = {name: read_team(turned_round(raw[name][0]), turned_round(raw[name][1]), [], passages) for name in raw}
    again = build_report('fixture', dict(reversed(list(passages.items()))), back['A'], back['B'], words=words)
    for one in (report, again):
        for team in one['teams'].values():
            team['dropped_entries'] = len(team['dropped_entries'])   # the messages name entry numbers, which do turn round
    if json.dumps(again, sort_keys=True) != json.dumps(report, sort_keys=True):
        diffs.append('order: the report changes when the rows and the entries are read in the opposite order')
    # 2. the checker, message by message
    for case in expected['checker_cases']:
        got, want = checker.check_record(case['record'], case.get('text') or passages[case['passage']], case.get('passage')), case['expect']
        if len(got) != len(want) or not all(m.startswith(start + ':') and phrase in m for m, (start, phrase) in zip(got, want)):
            diffs.append('checker case %s: expected %r, worked out %r' % (case['name'], want, got))
    # 3. the outcome word and the validity rules at their edges
    for case in expected['outcome_cases']:
        if outcome_word(*case['counts']) != case['expect']:
            diffs.append('outcome case %s: expected %s, worked out %s' % (case['name'], case['expect'], outcome_word(*case['counts'])))
    for case in expected['validity_cases']:
        got = validity_reasons('X', *case['counts'])
        if len(got) != case['expect_reasons']:
            diffs.append('validity case %s: expected %d reasons, worked out %r' % (case['name'], case['expect_reasons'], got))
    # 4. the gate of verdict mode: one good set of made-up hashes, then one thing wrong at a time
    found = {role: hashlib.sha256(role.encode()).hexdigest() for role in SEALED_ROLES + ('labels_a', 'labels_b')}
    seal = dict({role: {'sha256': found[role]} for role in SEALED_ROLES}, schema=SEAL_SCHEMA, is_a_seal=True,
                no_label_existed_when_sealed=True, owner_signoff={'numbers_signed': dict(SIGNED)})
    receipts = {name: {'guide_sha256': found['guide'], 'labels_sha256': found['labels_' + name.lower()], 'complete': True} for name in 'AB'}
    for case in expected['gate_cases']:
        things = {'seal': copy.deepcopy(seal), 'found': dict(found), 'receipt_a': dict(receipts['A']), 'receipt_b': dict(receipts['B'])}
        case_teams = teams
        if case.get('in') in things:
            target = things[case['in']]
            for key in case['path'][:-1]:
                target = target[key]
            if 'value' in case:
                target[case['path'][-1]] = case['value']
            else:
                del target[case['path'][-1]]
        elif case.get('in'):
            name, pid = case['in'][-1].upper(), case['passage']
            rows, tries = copy.deepcopy(raw[name][0]), copy.deepcopy(raw[name][1])
            {'remove the row': lambda: rows.pop(pid),
             'keep only the first tries': lambda: tries.update({pid: tries[pid][:case['keep']]}),
             'log the last try again': lambda: tries[pid].append(tries[pid][-1]),
             'mark the row as could not be labeled': lambda: rows.update({pid: checker.failed_row(pid, 3)}),
             'use the last try as the row': lambda: rows.update({pid: tries[pid][-1]}),
             'change the row': lambda: rows[pid].update(none_of_these=not rows[pid]['none_of_these'])}[case['do']]()
            case_teams = dict(teams, **{name: read_team(rows, tries, [], passages)})
        got = gate_problems(things['seal'], things['found'], {'A': things['receipt_a'], 'B': things['receipt_b']}, case_teams)
        if (not got) != (case['expect'] == '') or (case['expect'] and not any(case['expect'] in problem for problem in got)):
            diffs.append('gate case %s: expected %r, worked out %r' % (case['name'], case['expect'] or 'no problem', got[:3]))
    if diffs:
        print('FAIL: %d differences against %s' % (len(diffs), folder / 'FIXTURE_EXPECTED.json'))
        print(chr(10).join(' - ' + d for d in diffs))
        return 1
    print('fixture: %d passages, %d checker cases, %d outcome cases, %d validity cases, %d gate cases, and the order check'
          % (len(passages), len(expected['checker_cases']), len(expected['outcome_cases']), len(expected['validity_cases']), len(expected['gate_cases'])))
    print(chr(10).join(['strict-label view, table 1: ' + '; '.join('%s %s' % item for item in strict.items()), head_lines(report)[-1]]))
    print('PASS: every number equals FIXTURE_EXPECTED.json')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='Entry-by-entry label agreement, version 2.2.')
    parser.add_argument('mode', nargs='?', choices=['fixture', 'old', 'practice', 'verdict'])
    parser.add_argument('--fixture', action='store_true', help='the same as the mode "fixture"')
    parser.add_argument('--fixture-dir', default=str(HERE.parent / 'label_v21' / 'fixture'))
    parser.add_argument('--verdict-dir', default=str(HERE.parent / 'verdict'), help='old mode: the folder of attempt 1 (read only)')
    for name in ('seal', 'passages', 'guide', 'instructions', 'plan', 'receipt-a', 'receipt-b', 'out'):
        parser.add_argument('--' + name, default='')
    parser.add_argument('--labels-a', nargs='+', default=[], help='one or more labels files of team A; each has its try log beside it')
    parser.add_argument('--labels-b', nargs='+', default=[])
    args = parser.parse_args(argv)
    mode = 'fixture' if args.fixture else args.mode
    need = {'fixture': [], 'old': [], 'practice': ['passages', 'labels_a', 'labels_b'], None: ['mode'],
            'verdict': ['seal', 'passages', 'guide', 'instructions', 'plan', 'labels_a', 'labels_b', 'receipt_a', 'receipt_b', 'out']}[mode]
    missing = [name for name in need if not getattr(args, name, None)]
    if missing:
        parser.error('%s needs: %s' % (mode or 'this program', ', '.join('--' + name.replace('_', '-') for name in missing)))
    if mode == 'practice':   # what is not named: this folder's guide and instructions, and the receipt beside each team's first labels file
        args.guide = args.guide or str(HERE.parent / '02_LABELING_GUIDE_v2_2.md')
        args.instructions = args.instructions or str(HERE.parent / 'label_v22' / 'LABELER_INSTRUCTIONS.txt')
        args.receipt_a, args.receipt_b = (r or p[0] + '.receipt.json' for r, p in ((args.receipt_a, args.labels_a), (args.receipt_b, args.labels_b)))
    return {'fixture': run_fixture, 'old': run_old, 'practice': run_practice, 'verdict': run_verdict}[mode](args)


if __name__ == '__main__':
    sys.exit(main())
