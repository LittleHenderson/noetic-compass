"""R4 extra checks: parameter arithmetic, clipping activity, where the first-needed information sits in
the input bytes, and whether the logged model loss tracks an input-blind predictor. Pure Python; no torch."""
import json, math, random, sys, pathlib, statistics
sys.argv = sys.argv[:2]
exec(open(pathlib.Path(__file__).with_name("q4_prior_analysis.py"), encoding="utf-8").read().split("# 3. slot contexts")[0])
import functools
src = open(pathlib.Path(__file__).with_name("q4_prior_analysis.py"), encoding="utf-8").read()
exec("# 3. slot contexts" + src.split("# 3. slot contexts")[1].split("logged = ")[0])

W = 64
emb_in, gru = 257 * W, 2 * (3 * W * W) + 2 * (3 * W)
emb_out, head = (V + 1) * W, W * V + V
print("\nPARAMS: input_emb %d + encoder GRU %d + output_emb %d + decoder GRU %d + head %d = %d" % (
    emb_in, gru, emb_out, gru, head, emb_in + 2 * gru + emb_out + head))

logged = [json.loads(l) for l in (REC / "run_001" / "updates.jsonl").read_text(encoding="utf-8").split("\n") if l.strip()]
norms = [r["pre_clip_gradient_norm"] for r in logged]
print("CLIP: updates with pre-clip norm > 1.0: %d/128 ; min %.6f max %.6f ; lr values %s ; clip values %s" % (
    sum(n > 1.0 for n in norms), min(norms), max(norms), sorted({r["learning_rate"] for r in logged}), sorted({r["clip_norm"] for r in logged})))

# where does the FIRST decision the decoder must make (is the root's left child a BINARY?) live in the input?
agree = sum((train[i]["observation"][1] == "(") == (train_ast[i]["left"]["node"] == "BinaryExpr") for i in range(len(train)))
agree_r = sum((train[i]["observation"][-2] == ")") == (train_ast[i]["right"]["node"] == "BinaryExpr") for i in range(len(train)))
print("RULE: root-left-child is BINARY iff observation char[1]=='(' : %d/%d ; root-right-child BINARY iff char[-2]==')': %d/%d" % (
    agree, len(train), agree_r, len(train)))
d16 = dev[:16]
lb = [len(r["observation"].encode()) for r in d16]
lefts = sum(dev_ast[k]["left"]["node"] == "BinaryExpr" for k in range(16))
rights = sum(dev_ast[k]["right"]["node"] == "BinaryExpr" for k in range(16))
print("DEV16: root-left-child BINARY in %d/16 ; root-right-child BINARY in %d/16 ; input bytes min %d max %d mean %.4f" % (
    lefts, rights, min(lb), max(lb), sum(lb) / 16))
print("DEV16 root op:", collections.Counter(t["op"] for t in dev_ast[:16]))

# does the logged loss behave like an input-blind predictor?
model_loss = [r["loss"] for r in logged]
preq = []
for u in range(128):
    counts = fit(seen[:u], CTX["slot"])
    preq.append(nll(counts, CTX["slot"], tok[seen[u]], 0.1))
def pearson(a, b):
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return num / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
for a, b in ((64, 128), (96, 128)):
    print("CORR updates %d-%d: pearson(model loss, input-blind prequential slot-count loss a=0.1) = %.4f ; model - blind mean = %.4f" % (
        a + 1, b, pearson(model_loss[a:b], preq[a:b]), statistics.fmean(model_loss[a:b]) - statistics.fmean(preq[a:b])))
by = collections.defaultdict(list)
for u in range(64, 128):
    by[depth(train_ast[seen[u]])].append(model_loss[u])
print("MODEL LOSS by example depth, updates 65-128:", {d: (len(v), round(statistics.fmean(v), 4)) for d, v in sorted(by.items())})
beats = sum(m < p for m, p in zip(model_loss[96:], preq[96:]))
print("updates 97-128 where model loss < input-blind slot-count loss (a=0.1): %d/32" % beats)
