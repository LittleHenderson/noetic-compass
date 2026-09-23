"""R4: effect of per-example MEAN loss reduction (F.cross_entropy default) on the depth-1 expr-slot choice."""
import sys, pathlib
sys.argv = sys.argv[:2]
src = open(pathlib.Path(__file__).with_name("q4_prior_analysis.py"), encoding="utf-8").read()
exec(src.split("logged = ")[0].replace("print(", "(lambda *a, **k: None)("))
tot = sum(len(tok[i]) for i in seen); d1 = [i for i in seen if depth(train_ast[i]) == 1]
print("seen tokens total %d ; depth-1 examples %d x 13 tokens = %d ; token share %.5f ; example (loss-weight) share %.5f" % (
    tot, len(d1), sum(len(tok[i]) for i in d1), sum(len(tok[i]) for i in d1) / tot, len(d1) / 128))
b = s = 0.0; bt = st = 0
for i in seen:
    t = tok[i]
    for j in range(len(t)):
        if slot_of(t[:j]) == "expr" and expr_depth(t[:j]) == 1:
            w = 1.0 / len(t)
            if TOK[t[j]] == "BINARY": b += w; bt += 1
            else: s += w; st += 1
print("depth-1 expr slot: token-count P(BINARY) = %d/%d = %.5f ; loss-weighted P(BINARY) = %.5f" % (bt, bt + st, bt / (bt + st), b / (b + s)))
