"""CRITIC: run HELM's own unittest modules (scratch copy of the v9 helm_now) with the design's R1/R2 probe patch,
optionally (B) an emulation of the design's `alternatives` mark, and (C) the critic's proposed exact-step guard.
usage: python -X utf8 -B -I critic_tests.py <helm_now copy> <design probe dir> <mode A|B|C> [module ...]"""
import os
import re
import sys
import unittest

root, probe, mode = sys.argv[1], sys.argv[2], sys.argv[3]
mods = sys.argv[4:]
sys.path.insert(0, root)
sys.path.insert(0, probe)
os.chdir(root)
import helm_wide_turn as WT  # noqa: E402
import v73_patch  # noqa: E402

v73_patch.install(WT)
STOP = ("and", "or", "but", "for", "in", "on", "at", "to", "with", "from", "into", "the", "a", "an", "left", "that",
        "which", "if", "as", "per", "each")             # the frozen xreal.grammar.STOP_WORDS, copied

if mode in ("B", "C"):
    _orig_pl, _orig_rw = WT.parse_lines, WT.read_wide
    _last = {}

    def parse_lines_rec(text):
        lines, c = _orig_pl(text)
        _last["lines"] = lines if c is None else _last.get("lines")
        return lines, c

    def read_wide_alt(text, last_topic=None):
        _last.clear()
        out = _orig_rw(text, last_topic)
        lines = _last.get("lines") or []
        alts = [[x["name"], lines[i + 1]["name"] if i + 1 < len(lines) else None]
                for i, x in enumerate(lines) if x.get("dangling_or")]
        if alts:
            if out.get("witness"):
                out["witness"]["alternatives"] = alts
            if out.get("pending"):
                out["pending"]["alternatives"] = alts
            if out.get("status") == "STOCK":
                out["alternatives"] = alts
        return out

    WT.parse_lines, WT.read_wide = parse_lines_rec, read_wide_alt

if mode == "C":
    _r2 = WT.resolve_ran_out

    def resolve_guarded(name, batch, said=None):
        got = _r2(name, batch, said)
        if got in batch and got == name or (got in batch and got != name and got == WT.bind_name(got)):
            pass
        # critic's guard: an exact (or unit-stripped exact) hit is not taken when another line's name, read word by
        # word in the singular, is the same phrase followed by a frozen STOP word ("tomatoes in juice" vs "tomato")
        if got in batch:
            ph = WT._words(got)
            rivals = [b for b in batch if b != got and WT._words(b)[:len(ph)] == ph and len(WT._words(b)) > len(ph)
                      and WT._words(b)[len(ph)] in STOP]
            if rivals:
                return name if name not in batch else name + " ∅"   # not a batch name: the brain refuses
        return got

    WT.resolve_ran_out = resolve_guarded

print("MODE", mode, WT.READER_VERSION)
suite = unittest.defaultTestLoader.loadTestsFromNames(mods)
res = unittest.TextTestRunner(verbosity=1).run(suite)
for t, tb in res.failures + res.errors:
    print("FAIL/ERROR:", t.id(), tb.strip().splitlines()[-1][:300])
sys.exit(0)
