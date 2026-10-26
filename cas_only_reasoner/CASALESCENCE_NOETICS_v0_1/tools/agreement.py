"""Label-agreement arithmetic for the first look. Plain Python, no model, no project code.

Reads the passages and two label files; writes a JSON report and prints a table.
The first look is for finding problems in the labeling guide. It is not a verdict.
"""
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOETICS = ['^1', '^2', '^3', '^4', '^5', '^6', '^7', '^8', '^9']


FILLER = {'the', 'a', 'an', 'of', 'to', 'in', 'on', 'at', 'and', 'or', 'his', 'her', 'their', 'its', 'he', 'she', 'it', 'that',
          'this', 'was', 'had', 'with', 'for', 'from', 'by', 'as', 'him', 'them', 'they', 'is', 'were', 'be', 'been', 'not'}


def tokens(text):
    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    kept = [w for w in words if w not in FILLER]
    return kept or words


def overlap(a, b):
    """True when the two quotes share at least half of the words of the shorter one."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return False
    shared = sum((collections.Counter(ta) & collections.Counter(tb)).values())
    return shared / min(len(ta), len(tb)) >= 0.5


def kappa(pairs):
    n = len(pairs)
    both = sum(1 for a, b in pairs if a == b) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    chance = pa * pb + (1 - pa) * (1 - pb)
    return None if chance == 1 else (both - chance) / (1 - chance)


def load(name):
    rows = json.loads(Path(name).read_text(encoding='utf-8'))
    return {row['passage_id']: row for row in rows}


def main(passages_path, first, second, report_path):
    passages = {p['id']: p for p in json.loads(Path(passages_path).read_text(encoding='utf-8'))}
    one, two = load(first), load(second)
    ids = sorted(passages)
    assert set(one) == set(two) == set(ids), 'both label files must cover every passage exactly once'
    report = {'passages': len(ids),
              'label_files': [first, second], 'per_noetic': {}, 'quote_problems': {}, 'confusions': {}, 'disagreements': []}
    for label, team in ((first, one), (second, two)):
        bad = 0
        for pid in ids:
            for entry in team[pid].get('entries', []):
                for field in ('words', 'mind', 'relative_to'):
                    value = entry.get(field, '')
                    if value and value not in passages[pid]['text']:
                        bad += 1
        report['quote_problems'][label] = bad
    confusions = collections.Counter()
    for noetic in NOETICS:
        presence, same_words, both_present = [], 0, 0
        strict_agree = 0
        for pid in ids:
            a = [e for e in one[pid].get('entries', []) if e.get('noetic') == noetic]
            b = [e for e in two[pid].get('entries', []) if e.get('noetic') == noetic]
            presence.append((bool(a), bool(b)))
            if a and b:
                both_present += 1
                hit = any(overlap(x['words'], y['words']) for x in a for y in b)
                same_words += hit
                strict_agree += hit
                if not hit:
                    report['disagreements'].append({'passage': pid, 'noetic': noetic, 'kind': 'different words',
                                                    'first': [x['words'] for x in a], 'second': [y['words'] for y in b]})
            elif not a and not b:
                strict_agree += 1
            else:
                report['disagreements'].append({'passage': pid, 'noetic': noetic, 'kind': 'one team only',
                                                'first': [x['words'] for x in a], 'second': [y['words'] for y in b]})
        n = len(ids)
        report['per_noetic'][noetic] = {
            'marked_by_first': sum(a for a, _ in presence), 'marked_by_second': sum(b for _, b in presence),
            'marked_by_both': both_present,
            'presence_agreement_count': sum(1 for a, b in presence if a == b), 'presence_agreement_share': sum(1 for a, b in presence if a == b) / n,
            'presence_kappa': kappa(presence),
            'same_words_when_both_marked': same_words,
            'same_label_and_same_words_count': strict_agree, 'same_label_and_same_words_share': strict_agree / n}
    for pid in ids:
        for x in one[pid].get('entries', []):
            for y in two[pid].get('entries', []):
                if x.get('noetic') != y.get('noetic') and overlap(x.get('words', ''), y.get('words', '')):
                    confusions[' vs '.join(sorted((x['noetic'], y['noetic'])))] += 1
    report['confusions'] = dict(confusions.most_common())
    none_pairs = [(bool(one[p].get('none_of_these')), bool(two[p].get('none_of_these'))) for p in ids]
    report['none_of_these'] = {'first': sum(a for a, _ in none_pairs), 'second': sum(b for _, b in none_pairs),
                               'agree': sum(1 for a, b in none_pairs if a == b)}
    Path(report_path).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    print('passages', len(ids), '| quote problems', report['quote_problems'], '| none_of_these', report['none_of_these'])
    print('%-4s %6s %6s %6s  %-16s %-7s  %-18s %s' % ('', 'first', 'second', 'both', 'presence agree', 'kappa', 'same words/both', 'label+words agree'))
    for noetic, r in report['per_noetic'].items():
        k = r['presence_kappa']
        print('%-4s %6d %6d %6d  %2d/%d = %.3f    %-7s  %2d/%-2d              %2d/%d = %.3f' % (
            noetic, r['marked_by_first'], r['marked_by_second'], r['marked_by_both'],
            r['presence_agreement_count'], len(ids), r['presence_agreement_share'], 'n/a' if k is None else '%.3f' % k,
            r['same_words_when_both_marked'], r['marked_by_both'],
            r['same_label_and_same_words_count'], len(ids), r['same_label_and_same_words_share']))
    print('confusions (same words, different Noetic):', report['confusions'])
    print('disagreement records:', len(report['disagreements']))


if __name__ == '__main__':
    main(*sys.argv[1:5])
