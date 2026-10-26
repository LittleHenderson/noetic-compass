"""Label-agreement verdict arithmetic (06_VERDICT_PLAN_v1_2.md). Plain Python, no model, no project code.

Usage: verdict.py <sealed_passages.json> <labels_team_a.json> <labels_team_b.json> <report.json> [writer_kinds.json]
Every rule here is fixed in the plan before any verdict label is seen.
"""
import collections
import json
import math
import random
import re
import sys
from pathlib import Path

NOETICS = ['^%d' % i for i in range(1, 10)]
BAR_STRICT, BAR_KAPPA, MIN_CASES, MIN_ABSENT = 0.80, 0.60, 50, 50
SEED, RESAMPLES = 20261005, 2000
FILLER = {'the', 'a', 'an', 'of', 'to', 'in', 'on', 'at', 'and', 'or', 'his', 'her', 'their', 'its', 'he', 'she', 'it', 'that',
          'this', 'was', 'had', 'with', 'for', 'from', 'by', 'as', 'him', 'them', 'they', 'is', 'were', 'be', 'been', 'not'}
# which other fields must also agree for two entries to count as the same reading (guide Part B table)
REQUIRED = {'^1': (), '^2': ('mind',), '^3': ('mind',), '^5': ('mind',), '^6': ('relative_to',),
            '^4': ('mind', 'relative_to'), '^7': ('mind', 'relative_to'), '^8': ('mind', 'relative_to'), '^9': ('mind', 'relative_to')}


def content(text):
    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    kept = [w for w in words if w not in FILLER]
    return kept or words


def shared(a, b):
    return sum((collections.Counter(a) & collections.Counter(b)).values())


def same_span(a, b):
    """Primary rule: the two quotes share at least half of the content words of the LONGER quote."""
    ta, tb = content(a), content(b)
    return bool(ta) and bool(tb) and shared(ta, tb) / max(len(ta), len(tb)) >= 0.5


def same_field(a, b):
    if not a and not b:
        return True
    if not a or not b:
        return False
    return same_span(a, b)


def lenient_span(a, b):
    ta, tb = content(a), content(b)
    return bool(ta) and bool(tb) and shared(ta, tb) / min(len(ta), len(tb)) >= 0.5


def exact_span(a, b):
    return re.findall(r"[A-Za-z0-9']+", a.lower()) == re.findall(r"[A-Za-z0-9']+", b.lower())


def kappa(pairs):
    n = len(pairs)
    if n == 0:
        return None
    both = sum(1 for a, b in pairs if a == b) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    chance = pa * pb + (1 - pa) * (1 - pb)
    return None if chance == 1 else (both - chance) / (1 - chance)


def wilson(successes, n, z=1.959964):
    if n == 0:
        return [None, None]
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [max(0.0, centre - half), min(1.0, centre + half)]


def bootstrap_kappa(pairs, rng):
    values, n = [], len(pairs)
    for _ in range(RESAMPLES):
        value = kappa([pairs[rng.randrange(n)] for _ in range(n)])
        if value is not None:
            values.append(value)
    values.sort()
    if len(values) < RESAMPLES * 0.9:
        return [None, None]
    return [values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]]


def clean(rows, passages):
    out, dropped, failed = {}, 0, set()
    for row in rows:
        pid = row['passage_id']
        if row.get('labeler_failed'):
            failed.add(pid)
        kept = []
        for entry in row.get('entries', []):
            words = entry.get('words', '')
            if entry.get('noetic') in NOETICS and words and words in passages[pid]:
                kept.append({'noetic': entry['noetic'], 'words': words, 'mind': entry.get('mind') or '',
                             'relative_to': entry.get('relative_to') or '', 'uncertain': entry.get('certainty') == 'ambiguous',
                             'reasoning': entry.get('reached_by') == 'reasoning'})
            else:
                dropped += 1
        out[pid] = {'entries': kept, 'none_of_these': bool(row.get('none_of_these'))}
    return out, dropped, failed


def select(entries, name):
    """The entries that belong to one analysed class."""
    if name in NOETICS:
        return [e for e in entries if e['noetic'] == name and not e['uncertain'] and not (name == '^9' and e['reasoning'])]
    if name == '^9 reached by reasoning':
        return [e for e in entries if e['noetic'] == '^9' and e['reasoning'] and not e['uncertain']]
    if name == 'uncertain ^8':
        return [e for e in entries if e['noetic'] == '^8' and e['uncertain']]
    if name == 'uncertain ^9':
        return [e for e in entries if e['noetic'] == '^9' and e['uncertain']]
    raise ValueError(name)


def required_for(name):
    if name in NOETICS:
        return REQUIRED[name]
    return ('mind',) if name == '^9 reached by reasoning' else ('mind', 'relative_to')


def analyse(name, a, b, ids, rng, disagreements):
    need = required_for(name)
    pairs, counts = [], collections.Counter()
    for pid in ids:
        ea, eb = select(a[pid]['entries'], name), select(b[pid]['entries'], name)
        pairs.append((bool(ea), bool(eb)))
        if not ea and not eb:
            counts['neither'] += 1
            continue
        counts['cases'] += 1
        if not ea or not eb:
            disagreements.append({'passage': pid, 'class': name, 'kind': 'one team only',
                                  'team_a': [e['words'] for e in ea], 'team_b': [e['words'] for e in eb]})
            continue
        counts['both'] += 1
        words_only = any(same_span(x['words'], y['words']) for x in ea for y in eb)
        primary = any(same_span(x['words'], y['words']) and all(same_field(x[f], y[f]) for f in need) for x in ea for y in eb)
        counts['primary'] += primary
        counts['words_only'] += words_only
        counts['exact'] += any(exact_span(x['words'], y['words']) for x in ea for y in eb)
        counts['lenient'] += any(lenient_span(x['words'], y['words']) for x in ea for y in eb)
        if not primary:
            disagreements.append({'passage': pid, 'class': name, 'kind': 'same words, different relation' if words_only else 'different words',
                                  'team_a': [[e['words'], e['mind'], e['relative_to']] for e in ea],
                                  'team_b': [[e['words'], e['mind'], e['relative_to']] for e in eb]})
    n, cases = len(ids), counts['cases']
    k = kappa(pairs)
    row = {'marked_by_a': sum(x for x, _ in pairs), 'marked_by_b': sum(y for _, y in pairs), 'marked_by_both': counts['both'],
           'cases_marked_by_at_least_one': cases, 'passages_marked_by_neither': counts['neither'],
           'strict_agreement_count': counts['primary'], 'strict_agreement_share': counts['primary'] / cases if cases else None,
           'strict_agreement_interval95': wilson(counts['primary'], cases),
           'kappa': k, 'kappa_interval95': bootstrap_kappa(pairs, rng),
           'secondary': {'all_passage_agreement_share': (counts['neither'] + counts['primary']) / n,
                         'same_words_only_share': counts['words_only'] / cases if cases else None,
                         'exact_same_words_share': counts['exact'] / cases if cases else None,
                         'lenient_same_words_share': counts['lenient'] / cases if cases else None}}
    if name in NOETICS:
        if cases < MIN_CASES or counts['neither'] < MIN_ABSENT:
            row['outcome'] = 'NOT_ENOUGH_CASES'
        elif k is not None and counts['primary'] / cases >= BAR_STRICT and k >= BAR_KAPPA:
            row['outcome'] = 'LABELABLE_UNDER_THIS_METHOD'
        else:
            row['outcome'] = 'NOT_LABELABLE_UNDER_THIS_METHOD'
    else:
        row['outcome'] = 'REPORTED_ONLY_NO_BAR'
    return row


def main(passages_path, a_path, b_path, report_path, kinds_path=None):
    passages = {p['id']: p['text'] for p in json.loads(Path(passages_path).read_text(encoding='utf-8'))}
    a, a_dropped, a_failed = clean(json.loads(Path(a_path).read_text(encoding='utf-8')), passages)
    b, b_dropped, b_failed = clean(json.loads(Path(b_path).read_text(encoding='utf-8')), passages)
    missing = (set(passages) - set(a)) | (set(passages) - set(b)) | a_failed | b_failed
    ids = sorted(set(passages) - missing)
    total_a = sum(len(a[p]['entries']) for p in ids) + a_dropped
    total_b = sum(len(b[p]['entries']) for p in ids) + b_dropped
    disagreements = []
    report = {'plan': '06_VERDICT_PLAN_v1_2.md', 'passages_sealed': len(passages), 'passages_analysed': len(ids),
              'passages_excluded': sorted(missing), 'entries_dropped_for_bad_quote_or_label': {'team_a': a_dropped, 'team_b': b_dropped},
              'entries_kept': {'team_a': total_a - a_dropped, 'team_b': total_b - b_dropped},
              'bars': {'strict_agreement_min': BAR_STRICT, 'kappa_min': BAR_KAPPA, 'min_cases': MIN_CASES, 'min_absent': MIN_ABSENT},
              'valid': len(missing) <= 0.05 * len(passages) and a_dropped <= 0.05 * max(1, total_a) and b_dropped <= 0.05 * max(1, total_b),
              'per_class': {}}
    rng = random.Random(SEED)
    for name in NOETICS + ['^9 reached by reasoning', 'uncertain ^8', 'uncertain ^9']:
        report['per_class'][name] = analyse(name, a, b, ids, rng, disagreements)
    confusions = collections.Counter()
    for pid in ids:
        for x in a[pid]['entries']:
            for y in b[pid]['entries']:
                if x['noetic'] != y['noetic'] and same_span(x['words'], y['words']):
                    confusions[' vs '.join(sorted((x['noetic'], y['noetic'])))] += 1
    report['confusions_same_words_different_noetic'] = dict(confusions.most_common())
    none_pairs = [(a[p]['none_of_these'], b[p]['none_of_these']) for p in ids]
    report['none_of_these'] = {'team_a': sum(x for x, _ in none_pairs), 'team_b': sum(y for _, y in none_pairs),
                               'agree': sum(1 for x, y in none_pairs if x == y)}
    if kinds_path:
        kinds = {p['id']: p['kind'] for p in json.loads(Path(kinds_path).read_text(encoding='utf-8'))}
        by_kind = collections.defaultdict(collections.Counter)
        for pid in ids:
            for name in NOETICS:
                pa, pb = bool(select(a[pid]['entries'], name)), bool(select(b[pid]['entries'], name))
                by_kind[kinds[pid]][name + (' both' if pa and pb else ' one' if pa or pb else ' neither')] += 1
        report['descriptive_by_writer_kind'] = {k: dict(sorted(v.items())) for k, v in sorted(by_kind.items())}
    report['disagreements'] = disagreements
    Path(report_path).write_text(json.dumps(report, indent=1) + chr(10), encoding='utf-8', newline=chr(10))
    sample_rng = random.Random(SEED + 1)
    picked = sample_rng.sample(disagreements, min(30, len(disagreements)))
    agree_ids = [p for p in ids if not any(d['passage'] == p for d in disagreements) and (a[p]['entries'] or b[p]['entries'])]
    agreed = sample_rng.sample(agree_ids, min(20, len(agree_ids)))
    sample = {'note': 'For the owner: 30 disagreements and 20 passages with no disagreement, drawn with a fixed seed.',
              'disagreements': [dict(d, text=passages[d['passage']]) for d in picked],
              'agreements': [{'passage': p, 'text': passages[p], 'team_a': a[p]['entries'], 'team_b': b[p]['entries']} for p in agreed]}
    Path(report_path).with_name(Path(report_path).stem + '.owner_sample.json').write_text(
        json.dumps(sample, indent=1, ensure_ascii=False) + chr(10), encoding='utf-8', newline=chr(10))
    print('sealed', len(passages), '| analysed', len(ids), '| excluded', len(missing), '| dropped entries',
          report['entries_dropped_for_bad_quote_or_label'], '| valid', report['valid'])
    print('%-24s %4s %4s %4s %5s %7s  %-30s %-24s %s' % ('', 'A', 'B', 'both', 'cases', 'neither', 'strict agreement [95%]', 'kappa [95%]', 'outcome'))
    for name, r in report['per_class'].items():
        lo, hi = r['strict_agreement_interval95']
        klo, khi = r['kappa_interval95']
        stxt = 'n/a' if not r['cases_marked_by_at_least_one'] else '%d/%d = %.3f [%.3f, %.3f]' % (
            r['strict_agreement_count'], r['cases_marked_by_at_least_one'], r['strict_agreement_share'], lo, hi)
        ktxt = 'n/a' if r['kappa'] is None else '%.3f [%s, %s]' % (r['kappa'], 'n/a' if klo is None else '%.3f' % klo, 'n/a' if khi is None else '%.3f' % khi)
        print('%-24s %4d %4d %4d %5d %7d  %-30s %-24s %s' % (name, r['marked_by_a'], r['marked_by_b'], r['marked_by_both'],
              r['cases_marked_by_at_least_one'], r['passages_marked_by_neither'], stxt, ktxt, r['outcome']))
    print('secondary (words only / exact / lenient / all-passage):')
    for name, r in report['per_class'].items():
        sec = r['secondary']
        print('  %-24s %s' % (name, ' / '.join('n/a' if sec[k] is None else '%.3f' % sec[k] for k in
              ('same_words_only_share', 'exact_same_words_share', 'lenient_same_words_share', 'all_passage_agreement_share'))))
    print('confusions:', report['confusions_same_words_different_noetic'])
    print('none of these:', report['none_of_these'], '| disagreement records:', len(disagreements))


if __name__ == '__main__':
    main(*sys.argv[1:6])
