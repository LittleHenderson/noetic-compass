# R4 meeting: Q4 G data, visible files only. Input length extrapolation and shape definitions.
import json, random, re, collections, sys
from pathlib import Path
D = Path(sys.argv[1]) / "research/helm_cas_expression_lab/data/q3_v0_7"
def rows(name):
    return [json.loads(l) for l in (D / name).read_text(encoding="utf-8").splitlines() if l.strip()]
train = rows("visible_G_train.jsonl")[:2048]
dev = rows("visible_G_dev.jsonl")
order = list(range(len(train))); random.Random(20260921).shuffle(order)
seen = [train[i] for i in order[:128]]
blen = lambda r: len(r["observation"].encode("utf-8"))
tl = [blen(r) for r in train]; sl = [blen(r) for r in seen]; dl = [blen(r) for r in dev]
print("train input bytes min %d max %d ; seen128 max %d" % (min(tl), max(tl), max(sl)))
print("dev input bytes min %d max %d" % (min(dl), max(dl)))
print("dev inputs longer than longest TRAIN input (%d): %d of %d ; in first16: %d" % (max(tl), sum(x > max(tl) for x in dl), len(dl), sum(x > max(tl) for x in dl[:16])))
print("dev inputs longer than longest SEEN input (%d): %d of %d ; in first16: %d" % (max(sl), sum(x > max(sl) for x in dl), len(dl), sum(x > max(sl) for x in dl[:16])))
leaf = re.compile(r"\^\d\^[PCEO](?:_\{F\d\})?(?:\|[AfET])?")
with_op = lambda s: leaf.sub("x", s)
no_op = lambda s: re.sub(r"[+*×]", "o", leaf.sub("x", s))
for nm, f in (("shape incl operator", with_op), ("shape excl operator", no_op)):
    c = collections.Counter(f(r["observation"]) for r in seen); p = collections.Counter(f(r["observation"]) for r in train)
    print(nm, "seen128 top:", c.most_common(2), "| pool top:", p.most_common(2))
print("operator characters seen in observations:", sorted({ch for r in train for ch in r["observation"] if not ch.isalnum() and ch not in "^_{}|() "}))
