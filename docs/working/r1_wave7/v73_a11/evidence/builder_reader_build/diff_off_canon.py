"""Scratch helper (build of reader v7.3, design 2.6): diff two OFF fixture canons leaf by leaf. The only differing
values allowed are the reader string (v7.2 -> v7.3). Prints every differing leaf and a verdict line.
usage: python -X utf8 -B -I diff_off_canon.py <old.json> <new.json>"""
import json
import sys

OLD_READER = "helm_wide_turn reader RB-W1 v7.2 (2026-10-21)"
NEW_READER = "helm_wide_turn reader RB-W1 v7.3 (2026-10-21)"


def leaves(obj, path=""):
    if isinstance(obj, dict):
        for k in sorted(obj):
            yield from leaves(obj[k], f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{path}[{i}]")
    else:
        yield path, obj


with open(sys.argv[1], encoding="utf-8") as fh:
    old = dict(leaves(json.load(fh)))
with open(sys.argv[2], encoding="utf-8") as fh:
    new = dict(leaves(json.load(fh)))
only_old = sorted(set(old) - set(new))
only_new = sorted(set(new) - set(old))
diff = sorted(p for p in set(old) & set(new) if old[p] != new[p])
print("leaves old", len(old), "new", len(new), "| only in old", len(only_old), "| only in new", len(only_new),
      "| differing", len(diff))
for p in only_old[:20]:
    print("  ONLY OLD", p, repr(old[p])[:160])
for p in only_new[:20]:
    print("  ONLY NEW", p, repr(new[p])[:160])
bad = []
for p in diff:
    ok = old[p] == OLD_READER and new[p] == NEW_READER
    print("  ", "reader-string" if ok else "OTHER", p, repr(old[p])[:120], "->", repr(new[p])[:120])
    if not ok:
        bad.append(p)
verdict = "ONLY_READER_STRING" if not (only_old or only_new or bad) and diff else ("NO_DIFF" if not diff else "OTHER_DIFF")
print("VERDICT", verdict, "| reader-string leaves", len(diff) - len(bad), "| other", len(bad) + len(only_old) + len(only_new))
