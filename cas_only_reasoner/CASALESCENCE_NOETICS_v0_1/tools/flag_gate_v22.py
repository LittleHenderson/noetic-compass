"""Reasoning-flag gate for label-agreement attempt 3 (plan 09_LABEL_AGREEMENT_PLAN_v2_2.md, section 7). Plain Python, no model.

Guide v2.2 does not use the reasoning flag of version 2.1, and no text a labeler reads names its field. The measure is the
measure of attempt 2, which counts a ^9 that carries the flag apart from the bar row. So a verdict is printed only if no
final record of either team carries the flag. This program reads both teams' labels files and prints exactly one line:

  NO REASONING FLAG IN ANY FINAL RECORD                                          exit 0
  RUN_INVALID_NO_OUTCOME: the reasoning flag is in N final entries (where)       exit 1

The operator runs it before the scorer's verdict mode, and on the practice labels before the seal. On exit 1 the scorer is
not run for a verdict, and the report gives this program's line.

Usage: flag_gate_v22.py <team A labels file> <team B labels file>       (exit 2: wrong use or unreadable file)
"""
import json
import sys

FIELD = 'reached_by'


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    found = []
    for team, path in zip('AB', argv):
        try:
            with open(path, encoding='utf-8') as stream:
                rows = json.load(stream)
        except (OSError, ValueError) as error:
            print('REFUSED: cannot read %s (%s)' % (path, error.__class__.__name__))
            return 2
        if not isinstance(rows, list):
            print('REFUSED: %s is not a labels file (a list of final rows)' % path)
            return 2
        for row in rows:
            if not isinstance(row, dict) or row.get('labeler_failed') is True:
                continue
            for number, entry in enumerate(row.get('entries') or [], 1):
                if isinstance(entry, dict) and FIELD in entry:
                    found.append('team %s, %s, entry %d' % (team, row.get('passage_id'), number))
    if found:
        print('RUN_INVALID_NO_OUTCOME: the reasoning flag is in %d final entries (%s)' % (len(found), '; '.join(found[:20])))
        return 1
    print('NO REASONING FLAG IN ANY FINAL RECORD')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
