"""Gate 2 item 4 — six-arm definition A/B, v2 with the layer-selection defect FIXED.

v1 defect: the arm-free layer probe was FIT and SCORED on the same calibration
set, so it returned macro-acc 1.0000 at every layer 2..12 and the criterion had
zero discriminating power; L=2 was effectively arbitrary.

FIX: split calibration into DISJOINT fit/score halves and select on the held-out
half. Also adds the controls, multi-seed variation, and a group bootstrap CI.
"""
import os, json
import numpy as np
os.environ.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false"})
import torch, transformers

SNAP = "/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46"
BASE = "/workspace/item4"
FRAMES = (
    "Definition: {body}\nThat role describes:",
    "The following describes one role.\n{body}\nThat role describes:",
    "Consider this description.\n{body}\nThat role describes:",
    "Description: {body}\nThat role describes:",
)
GRID = [0, 2, 4, 6, 8, 10, 12]
SEEDS = list(range(20))

m = transformers.AutoModelForCausalLM.from_pretrained(
    SNAP, local_files_only=True, dtype=torch.float32,
    attn_implementation="eager", use_safetensors=True, output_hidden_states=True).to("cuda:0").eval()
tok = transformers.AutoTokenizer.from_pretrained(SNAP, local_files_only=True, use_fast=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token


@torch.no_grad()
def encode(texts, layers, bs=64):
    out = {L: [] for L in layers}
    for i in range(0, len(texts), bs):
        e = tok(texts[i:i + bs], return_tensors="pt", padding=True, truncation=True, max_length=384)
        ids = e.input_ids.to("cuda:0"); am = e.attention_mask.to("cuda:0")
        hs = m(input_ids=ids, attention_mask=am).hidden_states
        last = am.sum(1) - 1
        for L in layers:
            h = hs[L]
            out[L].append(h[torch.arange(h.shape[0], device=h.device), last, :].float().cpu().numpy())
    return {L: np.concatenate(v, 0) for L, v in out.items()}


def framed(bodies):
    return [f.format(body=b) for b in bodies for f in FRAMES]


def avgf(mat, n):
    return mat.reshape(n, len(FRAMES), -1).mean(1)


def l2(x):
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.where(n < 1e-12, 1.0, n)


def macro(yt, yp, classes):
    vals = [(yp[yt == c] == c).mean() for c in classes if (yt == c).any()]
    return float(np.mean(vals)) if vals else 0.0


def probe_fit_score(Xf, yf, Xs, ys, classes):
    """Arm-free multinomial logistic probe: FIT on one half, SCORE on the DISJOINT half."""
    mu = Xf.mean(0, keepdims=True); sd = Xf.std(0, keepdims=True) + 1e-8
    A = torch.tensor((Xf - mu) / sd, dtype=torch.float32, device="cuda:0")
    B = torch.tensor((Xs - mu) / sd, dtype=torch.float32, device="cuda:0")
    ci = {c: i for i, c in enumerate(classes)}
    yt = torch.tensor([ci[c] for c in yf], dtype=torch.long, device="cuda:0")
    W = torch.zeros(A.shape[1], len(classes), device="cuda:0", requires_grad=True)
    b = torch.zeros(len(classes), device="cuda:0", requires_grad=True)
    opt = torch.optim.LBFGS([W, b], max_iter=300, history_size=10, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = torch.nn.functional.cross_entropy(A @ W + b, yt) + 1e-3 * (W * W).sum()
        loss.backward()
        return loss

    opt.step(closure)
    with torch.no_grad():
        pr = np.array([classes[i] for i in (B @ W + b).argmax(1).cpu().numpy()])
    return macro(ys, pr, classes)


rows = [json.loads(l) for l in open(BASE + "/holdout_40e_repaired_v1.jsonl", encoding="utf-8") if l.strip()]
eng = [r["english"] for r in rows]
lab = np.array([r["element_label"] for r in rows])
spl = np.array([r["split"] for r in rows])
grp = np.array([r["repartition_group"] for r in rows])
calib = spl == "val"; ev = spl == "test"
classes = sorted(set(lab))
print("bank %d | calib %d | eval %d | classes %d" % (len(rows), calib.sum(), ev.sum(), len(classes)), flush=True)

print("item pass...", flush=True)
items = {L: avgf(v, len(eng)) for L, v in encode(framed(eng), GRID).items()}

print("layer selection (arm-free, HELD-OUT inside calibration)...", flush=True)
ci_idx = np.where(calib)[0]
np.random.default_rng(0).shuffle(ci_idx)
fit_i, score_i = ci_idx[:len(ci_idx) // 2], ci_idx[len(ci_idx) // 2:]
sel = {}
for L in GRID:
    sel[L] = probe_fit_score(items[L][fit_i], lab[fit_i], items[L][score_i], lab[score_i], classes)
    print("   layer %d: held-out macro-acc %.4f" % (L, sel[L]), flush=True)
L = max(sel, key=sel.get)
tied = [k for k, v in sel.items() if abs(v - sel[L]) < 1e-9]
print("FROZEN LAYER L=%d (held-out %.4f; ties %s)" % (L, sel[L], tied), flush=True)

arms = json.load(open(BASE + "/arms.json", encoding="utf-8"))
anchors = {}
for aid, defs in arms.items():
    codes = sorted(defs)
    anchors[aid] = (codes, avgf(encode(framed([defs[c] for c in codes]), [L])[L], len(codes)))

codesA = sorted(arms["A_owner_raw"])
bodiesA = [arms["A_owner_raw"][c] for c in codesA]
anchor_L0 = avgf(encode(framed(bodiesA), [0])[0], len(codesA))
wrongL = [x for x in GRID if x not in (L, 0)][0]
anchor_wrong = avgf(encode(framed(bodiesA), [wrongL])[wrongL], len(codesA))


def score(anchor, codes, seed, item_layer=None):
    X = items[item_layer if item_layer is not None else L]
    r = np.random.default_rng(seed)
    cc = np.where(calib)[0]
    sub = r.choice(cc, size=int(0.8 * len(cc)), replace=False)   # seed varies the calibration mean
    v = l2(X - X[sub].mean(0, keepdims=True))
    u = l2(anchor - anchor.mean(0, keepdims=True))
    pred = np.array([codes[i] for i in (v[ev] @ u.T).argmax(1)])
    return macro(lab[ev], pred, classes), pred


res = {}
for aid, (codes, anc) in anchors.items():
    vals = [score(anc, codes, s)[0] for s in SEEDS]
    res[aid] = {
        "macro_mean": round(float(np.mean(vals)), 6),
        "macro_sd": round(float(np.std(vals, ddof=1)), 6),
        "macro_min": round(float(np.min(vals)), 6),
        "macro_max": round(float(np.max(vals)), 6),
        "seeds": len(SEEDS),
    }
    print("  %-18s %.4f +/- %.4f  [%.4f, %.4f]" % (
        aid, res[aid]["macro_mean"], res[aid]["macro_sd"], res[aid]["macro_min"], res[aid]["macro_max"]), flush=True)

ctl = {}
ctl["layer0_anchors"] = round(float(np.mean([score(anchor_L0, codesA, s, item_layer=0)[0] for s in SEEDS])), 6)
ctl["wrong_layer_anchors"] = round(float(np.mean([score(anchor_wrong, codesA, s, item_layer=wrongL)[0] for s in SEEDS])), 6)
rg = np.random.default_rng(99)
rand_anchor = rg.normal(size=anchors["A_owner_raw"][1].shape)
ctl["random_direction_anchors"] = round(float(np.mean([score(rand_anchor, codesA, s)[0] for s in SEEDS])), 6)
_, predA0 = score(anchors["A_owner_raw"][1], codesA, 0)
shuffled = np.random.default_rng(7).permutation(lab[ev])
ctl["shuffled_labels"] = round(macro(shuffled, predA0, classes), 6)
for k, v in ctl.items():
    print("  CONTROL %-26s %.4f" % (k, v), flush=True)

_, pA = score(anchors["A_owner_raw"][1], codesA, 0)
codesD, ancD = anchors["D_compact_cas"]
_, pD = score(ancD, codesD, 0)
ge = grp[ev]; yt = lab[ev]
ug = np.array(sorted(set(ge.tolist())), dtype=object)
rows_by = {g: np.where(ge == g)[0] for g in ug.tolist()}
rb = np.random.default_rng(11)
marg = []
for _ in range(2000):
    pick = rb.choice(len(ug), size=len(ug), replace=True)
    idx = np.concatenate([rows_by[ug[i]] for i in pick])
    marg.append(macro(yt[idx], pA[idx], classes) - macro(yt[idx], pD[idx], classes))
marg = np.array(marg)
boot = {
    "margin_mean": round(float(marg.mean()), 6),
    "ci_lower_2p5": round(float(np.percentile(marg, 2.5)), 6),
    "ci_upper_97p5": round(float(np.percentile(marg, 97.5)), 6),
    "rounds": 2000,
}
print("  A-minus-D margin %.4f  CI [%.4f, %.4f]" % (
    boot["margin_mean"], boot["ci_lower_2p5"], boot["ci_upper_97p5"]), flush=True)

out = {
    "design": "TKS-DEFCTX-40E-PRIMARY-v1",
    "version": "v2_layer_selection_fixed",
    "model": "EleutherAI/pythia-160m",
    "frozen_layer": L,
    "layer_selection_heldout": sel,
    "layer_selection_rule": "arm-free multinomial logistic probe, FIT and SCORED on DISJOINT halves of calibration",
    "tied_layers": tied,
    "seeds": len(SEEDS),
    "eval_n": int(ev.sum()),
    "chance": round(1.0 / len(classes), 6),
    "arms": res,
    "controls": ctl,
    "A_minus_D_group_bootstrap": boot,
    "fitted_parameters_in_readout": 0,
}
json.dump(out, open(BASE + "/item4_results_v2.json", "w"), indent=2, sort_keys=True)
print("WROTE item4_results_v2.json")
