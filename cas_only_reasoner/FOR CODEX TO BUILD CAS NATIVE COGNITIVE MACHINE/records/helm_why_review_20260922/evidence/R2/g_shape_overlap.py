# Can R0 (retrieve a TRAINING AST) ever be exact on G dev? Only if some dev tree's bare shape occurs in train.
import json, collections
from pathlib import Path
src = Path(__file__).with_name("g_family_analysis.py").read_text(encoding="utf-8")
ns = {}
exec(compile(src.split("inspected = json.loads")[0], "g", "exec"), ns)
parse, read_jsonl, DATA = ns["parse"], ns["read_jsonl"], ns["DATA"]
def bare(t):
    return "L" if t["node"] == "StateLiteral" else ("(" + bare(t["left"]) + "," + bare(t["right"]) + ")")
def full(t):
    return json.dumps(t, sort_keys=True)
train = [parse(r["observation"]) for r in read_jsonl(DATA / "visible_G_train.jsonl")]
dev = [parse(r["observation"]) for r in read_jsonl(DATA / "visible_G_dev.jsonl")]
ts = {bare(t) for t in train}; ds = collections.Counter(bare(t) for t in dev)
print("bare tree shapes: train %d, dev %d, dev rows whose bare shape occurs in train: %d of %d" % (len(ts), len(ds), sum(c for s, c in ds.items() if s in ts), len(dev)))
tf = {full(t) for t in train}
print("dev rows whose exact AST occurs in train: %d of %d" % (sum(full(t) in tf for t in dev), len(dev)))
# distinct bytes used by the GRU input
bs = collections.Counter(b for r in read_jsonl(DATA / "visible_G_train.jsonl") for b in r["observation"].encode("utf-8"))
print("distinct UTF-8 byte values in G train observations: %d of 256 embedding rows" % len(bs))
