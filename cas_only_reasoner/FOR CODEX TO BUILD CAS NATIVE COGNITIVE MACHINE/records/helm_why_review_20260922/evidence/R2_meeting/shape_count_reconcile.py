"""Reconcile R6 '(x + x) 44/128, 476/2048' with R4/R7 'bare shape ss 58/128, 747/2048'. Visible train file only."""
import json, random, re
from pathlib import Path
from collections import Counter
DATA = Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/helm_cas_expression_lab/data/q3_v0_7")
rows = [json.loads(l) for l in DATA.joinpath("visible_G_train.jsonl").read_bytes().decode("utf-8").splitlines() if l.strip()][:2048]
def shape(s, with_op):
    s = re.sub(r"\^[0-9]\^[PCEO](_\{?F[0-9]\}?)?(\|[TAfE])?", "x", s)   # collapse each leaf literal
    s = re.sub(r"\^[0-9]\^[PCEO][^ ()]*", "x", s)
    if not with_op:
        s = s.replace("+", "o").replace("\u00d7", "o")
    return s.replace(" ", "")
order = list(range(len(rows))); random.Random(20260921).shuffle(order); seen = [rows[i] for i in order[:128]]
for with_op in (False, True):
    pool = Counter(shape(r["observation"], with_op) for r in rows); s128 = Counter(shape(r["observation"], with_op) for r in seen)
    print("with operator" if with_op else "operator ignored", "| pool top", pool.most_common(2), "| seen-128 top", s128.most_common(2))
print("example observation:", rows[0]["observation"])
