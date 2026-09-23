import sys, torch
if not torch.cuda.is_available(): print('GPU_REQUIRED'); sys.exit(2)
"""RT1 EXTRA (not used for any outcome rule): where does input information stop?
Forward-only encode() of the 2048 visible G train rows and 16 dev rows with the saved checkpoint.
Then NON-neural statistics on the saved vectors: saturation, and nearest-centroid read-out of input facts
(centroids = plain class means on 1920 train rows that are neither seen nor unseen; tested on unseen128 and dev16).
No gradient, no optimizer, no model change. Labels come from the R5 parser on VISIBLE observations.
DIAGNOSTIC_NOT_CLAIM_BEARING. Writes only into SCRATCH/RT1."""
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import collections
import json
import math
import random
from pathlib import Path

ROOT = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
LAB = ROOT / "research/helm_cas_expression_lab"
SCRATCH = Path("C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad/helm_review")
OUT = SCRATCH / "RT1"
RUN = ROOT / "records/q4_authorized_20260922/run_001"
DATA = LAB / "data/q3_v0_7"
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(SCRATCH / "R5"))
from common import parse, depth, leaves  # R5 helpers
from learner_q4_representation import from_visible_record
from q3_load import load_visible
from q4_checkpoint import load_checkpoint

torch.use_deterministic_algorithms(True)
torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
DEV = "cuda:0"
manifest = json.loads((RUN / "checkpoint/manifest.json").read_text(encoding="utf-8"))
model = load_checkpoint(RUN / "checkpoint", expected_identity=manifest["identity"],
                        expected_weights_sha256="d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477",
                        width=64, device=DEV)
train_vis = load_visible(DATA, "G", "train")[:2048]
dev_vis = load_visible(DATA, "G", "dev")[:16]
order = list(range(2048))
random.Random(20260921).shuffle(order)
seen, unseen = order[:128], order[128:256]
fit_idx = order[256:]
X = torch.tensor([model.encode(from_visible_record(r)).values for r in train_vis], dtype=torch.float64, device=DEV)
Xd = torch.tensor([model.encode(from_visible_record(r)).values for r in dev_vis], dtype=torch.float64, device=DEV)
ast = [parse(r["observation"]) for r in train_vis]
dast = [parse(r["observation"]) for r in dev_vis]

print("== saturation of the 64 encoder units (GRU hidden values lie in (-1, 1))")
for name, M in (("train2048", X), ("dev16", Xd)):
    a = M.abs()
    print(" %s: fraction |h|>0.9 %.6f, |h|>0.99 %.6f, |h|>0.999 %.6f; units whose |mean|>0.9: %d/64; mean per-unit std %.6f" % (
        name, (a > 0.9).double().mean().item(), (a > 0.99).double().mean().item(), (a > 0.999).double().mean().item(),
        int((M.mean(0).abs() > 0.9).sum().item()), M.std(0).mean().item()))
print(" distance between dev16 mean vector and train2048 mean vector: %.6f ; train2048 mean pairwise-to-mean distance %.6f" % (
    (Xd.mean(0) - X.mean(0)).norm().item(), (X - X.mean(0)).norm(dim=1).mean().item()))

labels = {
    "root_op": lambda a: a["op"],
    "depth": lambda a: depth(a),
    "left_child_binary": lambda a: a["left"]["node"] == "BinaryExpr",
    "right_child_binary": lambda a: a["right"]["node"] == "BinaryExpr",
    "first_leaf_noetic": lambda a: leaves(a)[0]["operator"],
    "last_leaf_noetic": lambda a: leaves(a)[-1]["operator"],
    "last_leaf_domain": lambda a: leaves(a)[-1]["domain"],
    "last_leaf_register": lambda a: leaves(a)[-1].get("register", "ABSENT"),
    "n_leaves": lambda a: len(leaves(a)),
}
mu, sd = X[fit_idx].mean(0), X[fit_idx].std(0)
Z, Zd = (X - mu) / sd, (Xd - mu) / sd
print("\n== nearest-centroid read-out (z-scored by the 1920 fit rows); test = unseen128 and dev16; majority = most common class in fit rows")
res = {}
for name, f in labels.items():
    ytr = [f(ast[i]) for i in fit_idx]
    classes = sorted(set(ytr), key=str)
    cent = torch.stack([Z[[i for i, y in zip(fit_idx, ytr) if y == c]].mean(0) for c in classes])
    maj = collections.Counter(ytr).most_common(1)[0][0]

    def acc(Zs, ys):
        d = torch.cdist(Zs, cent) if False else ((Zs[:, None, :] - cent[None, :, :]) ** 2).sum(-1)
        pred = [classes[j] for j in d.argmin(1).tolist()]
        return sum(p == y for p, y in zip(pred, ys)), sum(maj == y for y in ys), len(ys)

    yu = [f(ast[i]) for i in unseen]
    u = acc(Z[unseen], yu)
    yd = [f(a) for a in dast]
    known = [k for k, y in enumerate(yd) if y in classes]
    d_ = acc(Zd[known], [yd[k] for k in known]) if known else (0, 0, 0)
    res[name] = {"unseen128_correct": u[0], "unseen128_majority": u[1], "n": u[2], "dev16_correct": d_[0], "dev16_majority": d_[1], "dev16_n": d_[2],
                 "classes": len(classes)}
    print(" %-19s classes %2d | unseen128 centroid %3d/%d vs majority %3d/%d | dev16 centroid %2d/%d vs majority %2d/%d" % (
        name, len(classes), u[0], u[2], u[1], u[2], d_[0], d_[2], d_[1], d_[2]))

print("\n== which input features move the vector? Pearson(pairwise L2, feature difference) over unseen128 pairs")
U = X[unseen]
D = ((U[:, None, :] - U[None, :, :]) ** 2).sum(-1).sqrt()
iu = torch.triu_indices(128, 128, offset=1, device=DEV)
dist = D[iu[0], iu[1]].tolist()
L = [len(train_vis[i]["observation"].encode("utf-8")) for i in unseen]
lastleaf = [json.dumps(leaves(ast[i])[-1], sort_keys=True) for i in unseen]
last8 = [train_vis[i]["observation"][-8:] for i in unseen]
feats = {"abs_input_byte_length_diff": [abs(L[a] - L[b]) for a, b in zip(iu[0].tolist(), iu[1].tolist())],
         "last_leaf_differs": [float(lastleaf[a] != lastleaf[b]) for a, b in zip(iu[0].tolist(), iu[1].tolist())],
         "last_8_chars_differ": [float(last8[a] != last8[b]) for a, b in zip(iu[0].tolist(), iu[1].tolist())]}


def pearson(x, y):
    mx, my = sum(x) / len(x), sum(y) / len(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return num / den if den else float("nan")


for k, v in feats.items():
    print(" %-28s Pearson %.6f" % (k, pearson(dist, v)))


def binom_upper(k, n):
    return sum(math.comb(n, j) for j in range(k, n + 1)) / 2 ** n


print("\n== exact one-sided sign-test p for 'TRUE bottleneck gives lower teacher-forced CE than SWAP' counts from rt1_out.txt")
for name, k, n in (("seen128", 76, 128), ("unseen128", 66, 128), ("dev16", 11, 16)):
    print(" %s: %d/%d  P(X>=%d | n=%d, 0.5) = %.10f" % (name, k, n, k, n, binom_upper(k, n)))
(OUT / "rt1_extra_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
