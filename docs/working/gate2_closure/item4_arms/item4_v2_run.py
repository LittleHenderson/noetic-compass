"""Gate 2 item 4 — v2 run: TKS-DEFCTX-40E-SPLITLAYER-v2 on pythia-1b.

Implements GATE2_ITEM4_PREREGISTRATION_V2.md exactly. Bars are the v2 bars, which
are STRICTER than v1 in two places (A3 CI lower >= 0.15; A5 truncated margin
>= 0.15). Nothing is loosened.
"""
import os, json, re
import numpy as np
os.environ.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false"})
import torch, transformers

MODEL = "/workspace/cas-hf-cache/models--EleutherAI--pythia-1b/snapshots/f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2"
ENC = "/workspace/cas-hf-cache/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
BASE = "/workspace/item4"
GRID = [0, 4, 8, 12, 16]
SEEDS = list(range(20))

FRAMES = (
    "Definition: {body}\nThat role describes:",
    "The following describes one role.\n{body}\nThat role describes:",
    "Consider this description.\n{body}\nThat role describes:",
    "Description: {body}\nThat role describes:",
)
HELDOUT_FRAMES = (
    "Text: {body}\nThat role describes:",
    "Read the passage below.\n{body}\nThat role describes:",
    "Passage: {body}\nThat role describes:",
    "Here is a statement.\n{body}\nThat role describes:",
)
ALT_SCAFFOLD_FRAMES = tuple(f.replace("That role describes:", "This sentence concerns:") for f in FRAMES)
FILLER = ("The following material has been provided for review by the assessment team and should be "
          "considered in full before any determination is made regarding its content or classification "
          "under the applicable scheme. ")

m = transformers.AutoModelForCausalLM.from_pretrained(
    MODEL, local_files_only=True, dtype=torch.float32,
    attn_implementation="eager", use_safetensors=True, output_hidden_states=True).to("cuda:0").eval()
tok = transformers.AutoTokenizer.from_pretrained(MODEL, local_files_only=True, use_fast=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token


@torch.no_grad()
def enc_layers(texts, layers, bs=32):
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


def fr(bodies, frames=FRAMES):
    return [f.format(body=b) for b in bodies for f in frames]


def avgf(mat, n, k=4):
    return mat.reshape(n, k, -1).mean(1)


def l2(x):
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.where(n < 1e-12, 1.0, n)


def macro(yt, yp, classes):
    v = [(yp[yt == c] == c).mean() for c in classes if (yt == c).any()]
    return float(np.mean(v)) if v else 0.0


def trunc(text, budget):
    parts = re.split(r"(?<=[.!?])\s+", str(text).strip())
    kept, used = [], 0
    for p in parts:
        n = len(tok(p, add_special_tokens=False).input_ids)
        if kept and used + n > budget:
            break
        kept.append(p); used += n
        if used >= budget:
            break
    return " ".join(kept) if kept else parts[0]


rows = [json.loads(l) for l in open(BASE + "/holdout_40e_repaired_v1.jsonl", encoding="utf-8") if l.strip()]
eng = [r["english"] for r in rows]
lab = np.array([r["element_label"] for r in rows])
spl = np.array([r["split"] for r in rows]); grp = np.array([r["repartition_group"] for r in rows])
calib = spl == "val"; ev = spl == "test"
classes = sorted(set(lab))
print("pythia-1b | bank %d | calib %d | eval %d | classes %d" % (len(rows), calib.sum(), ev.sum(), len(classes)), flush=True)

arms = json.load(open(BASE + "/arms.json", encoding="utf-8"))
arm_ids = sorted(arms)

print("item pass (all grid layers)...", flush=True)
items = {L: avgf(v, len(eng)) for L, v in enc_layers(fr(eng), GRID).items()}


def probe(Xf, yf, Xs, ys):
    mu = Xf.mean(0, keepdims=True); sd = Xf.std(0, keepdims=True) + 1e-8
    A = torch.tensor((Xf - mu) / sd, dtype=torch.float32, device="cuda:0")
    B = torch.tensor((Xs - mu) / sd, dtype=torch.float32, device="cuda:0")
    ci = {c: i for i, c in enumerate(classes)}
    yt = torch.tensor([ci[c] for c in yf], dtype=torch.long, device="cuda:0")
    W = torch.zeros(A.shape[1], len(classes), device="cuda:0", requires_grad=True)
    b = torch.zeros(len(classes), device="cuda:0", requires_grad=True)
    opt = torch.optim.LBFGS([W, b], max_iter=300, history_size=10, line_search_fn="strong_wolfe")

    def cl():
        opt.zero_grad()
        loss = torch.nn.functional.cross_entropy(A @ W + b, yt) + 1e-3 * (W * W).sum()
        loss.backward(); return loss
    opt.step(cl)
    with torch.no_grad():
        pr = np.array([classes[i] for i in (B @ W + b).argmax(1).cpu().numpy()])
    return macro(ys, pr, classes)


# --- L_item: arm-free, disjoint halves of calibration
ci_idx = np.where(calib)[0]; np.random.default_rng(0).shuffle(ci_idx)
fi, si = ci_idx[:len(ci_idx) // 2], ci_idx[len(ci_idx) // 2:]
item_sel = {L: probe(items[L][fi], lab[fi], items[L][si], lab[si]) for L in GRID}
for L in GRID:
    print("   L_item %2d: held-out %.4f" % (L, item_sel[L]), flush=True)
L_item = max(item_sel, key=item_sel.get)

# --- L_anchor: anchor separability, averaged with EQUAL WEIGHT across arms (no arm score, no labels)
print("anchor passes at every grid layer...", flush=True)
anchors_all = {}
for aid in arm_ids:
    codes = sorted(arms[aid])
    e = enc_layers(fr([arms[aid][c] for c in codes]), GRID)
    anchors_all[aid] = {L: avgf(e[L], len(codes)) for L in GRID}
anchor_sel = {}
for L in GRID:
    per = []
    for aid in arm_ids:
        u = l2(anchors_all[aid][L] - anchors_all[aid][L].mean(0, keepdims=True))
        s = u @ u.T
        per.append(float(1.0 - s[~np.eye(len(u), dtype=bool)].mean()))
    anchor_sel[L] = float(np.mean(per))
    print("   L_anchor %2d: mean pairwise cos-distance %.4f" % (L, anchor_sel[L]), flush=True)
L_anchor = max(anchor_sel, key=anchor_sel.get)
print("FROZEN L_item=%d  L_anchor=%d" % (L_item, L_anchor), flush=True)


def readout(anchor, codes, seed, item_layer=None, item_states=None):
    X = item_states if item_states is not None else items[item_layer if item_layer is not None else L_item]
    r = np.random.default_rng(seed); cc = np.where(calib)[0]
    sub = r.choice(cc, size=int(0.8 * len(cc)), replace=False)
    v = l2(X - X[sub].mean(0, keepdims=True))
    u = l2(anchor - anchor.mean(0, keepdims=True))
    pred = np.array([codes[i] for i in (v[ev] @ u.T).argmax(1)])
    return macro(lab[ev], pred, classes), pred


res = {}
for aid in arm_ids:
    codes = sorted(arms[aid])
    vals = [readout(anchors_all[aid][L_anchor], codes, s)[0] for s in SEEDS]
    res[aid] = {"mean": round(float(np.mean(vals)), 6), "sd": round(float(np.std(vals, ddof=1)), 6)}
    print("  %-18s %.4f +/- %.4f" % (aid, res[aid]["mean"], res[aid]["sd"]), flush=True)

codesA = sorted(arms["A_owner_raw"])
matched = res["A_owner_raw"]["mean"]

# --- C1/C2/C3
print("commensurability controls...", flush=True)
alt_items = avgf(enc_layers(fr(eng, ALT_SCAFFOLD_FRAMES), [L_item])[L_item], len(eng))
c1 = round(float(np.mean([readout(anchors_all["A_owner_raw"][L_anchor], codesA, s, item_states=alt_items)[0] for s in SEEDS])), 6)
ho_items = avgf(enc_layers(fr(eng, HELDOUT_FRAMES), [L_item])[L_item], len(eng))
c2 = round(float(np.mean([readout(anchors_all["A_owner_raw"][L_anchor], codesA, s, item_states=ho_items)[0] for s in SEEDS])), 6)
pos_items = avgf(enc_layers(fr([FILLER + e for e in eng]), [L_item])[L_item], len(eng))
c3 = round(float(np.mean([readout(anchors_all["A_owner_raw"][L_anchor], codesA, s, item_states=pos_items)[0] for s in SEEDS])), 6)
ctl = {"C1_scaffold_mismatch": c1, "C2_frame_mismatch": c2, "C3_position_break": c3}
for k, v in ctl.items():
    print("  %-22s %.4f  (bar < %.4f = 0.5x matched)  %s" % (k, v, 0.5 * matched, "PASS" if v < 0.5 * matched else "FAIL"), flush=True)

# --- nulls
rg = np.random.default_rng(99)
nulls = {
    "layer0_anchors": round(float(np.mean([readout(anchors_all["A_owner_raw"][0], codesA, s, item_layer=0)[0] for s in SEEDS])), 6),
    "random_direction": round(float(np.mean([readout(rg.normal(size=anchors_all["A_owner_raw"][L_anchor].shape), codesA, s)[0] for s in SEEDS])), 6),
}
_, pA = readout(anchors_all["A_owner_raw"][L_anchor], codesA, 0)
nulls["shuffled_labels"] = round(macro(np.random.default_rng(7).permutation(lab[ev]), pA, classes), 6)
for k, v in nulls.items():
    print("  NULL %-20s %.4f" % (k, v), flush=True)

# --- A3 bootstrap on A-D
codesD = sorted(arms["D_compact_cas"])
_, pD = readout(anchors_all["D_compact_cas"][L_anchor], codesD, 0)
ge = grp[ev]; yt = lab[ev]
ug = np.array(sorted(set(ge.tolist())), dtype=object)
rby = {g: np.where(ge == g)[0] for g in ug.tolist()}
rb = np.random.default_rng(11); mg = []
for _ in range(2000):
    pick = rb.choice(len(ug), size=len(ug), replace=True)
    idx = np.concatenate([rby[ug[i]] for i in pick])
    mg.append(macro(yt[idx], pA[idx], classes) - macro(yt[idx], pD[idx], classes))
mg = np.array(mg)
boot = {"mean": round(float(mg.mean()), 6), "ci_lower": round(float(np.percentile(mg, 2.5)), 6),
        "ci_upper": round(float(np.percentile(mg, 97.5)), 6)}
print("  A-D margin %.4f CI [%.4f, %.4f]  (A2 bar 0.15, A3 bar CI_lower>=0.15)" % (
    boot["mean"], boot["ci_lower"], boot["ci_upper"]), flush=True)

# --- A5 equal-token-budget
budgets = {a: int(np.median([len(tok(str(v), add_special_tokens=False).input_ids) for v in arms[a].values()])) for a in arm_ids}
bud = min(budgets.values())
e8 = {}
for aid in arm_ids:
    codes = sorted(arms[aid])
    tr = [trunc(arms[aid][c], bud) for c in codes]
    a_t = avgf(enc_layers(fr(tr), [L_anchor])[L_anchor], len(codes))
    e8[aid] = round(float(np.mean([readout(a_t, codes, s)[0] for s in SEEDS])), 6)
e8_margin = round(e8["A_owner_raw"] - e8["D_compact_cas"], 6)
print("  E8 truncated A-D margin %.4f (bar >= 0.15)" % e8_margin, flush=True)

# --- A4 stability
stab = {}
for L in GRID:
    per = {a: round(float(np.mean([readout(anchors_all[a][L], sorted(arms[a]), s, item_layer=L)[0] for s in SEEDS])), 6) for a in arm_ids}
    per["holds"] = bool(min(per["A_owner_raw"], per["B_deployed"]) > max(per["D_compact_cas"], per["E_non_tks"], per["F_F1_null"]))
    stab[L] = per
held = sum(1 for L in GRID if stab[L]["holds"])
print("  A4 stability %d/%d = %.1f%%" % (held, len(GRID), 100 * held / len(GRID)), flush=True)

crit = {
    "A1_tks_above_others": bool(min(res["A_owner_raw"]["mean"], res["B_deployed"]["mean"]) >
                                max(res["D_compact_cas"]["mean"], res["E_non_tks"]["mean"], res["F_F1_null"]["mean"])),
    "A2_margin_ge_0.15": bool(boot["mean"] >= 0.15),
    "A3_ci_lower_ge_0.15": bool(boot["ci_lower"] >= 0.15),
    "A4_stability_ge_60pct": bool(held / len(GRID) >= 0.60),
    "A5_truncated_margin_ge_0.15": bool(e8_margin >= 0.15),
    "A6_nulls_at_chance": bool(max(nulls.values()) <= 0.05),
    "A7_commensurability_controls": bool(max(ctl.values()) < 0.5 * matched),
}
print("\n=== v2 CRITERIA ===", flush=True)
for k, v in crit.items():
    print("  %-32s %s" % (k, "PASS" if v else "FAIL"), flush=True)
verdict = "ALL_CRITERIA_PASS" if all(crit.values()) else "NOT_LICENSED"
print("VERDICT: %s" % verdict, flush=True)

json.dump({"design": "TKS-DEFCTX-40E-SPLITLAYER-v2", "model": "EleutherAI/pythia-1b",
           "L_item": L_item, "L_anchor": L_anchor, "item_layer_selection": item_sel,
           "anchor_layer_selection": anchor_sel, "seeds": len(SEEDS), "chance": round(1 / len(classes), 6),
           "arms": res, "commensurability_controls": ctl, "nulls": nulls,
           "A_minus_D_bootstrap": boot, "E8_truncated": e8, "E8_margin": e8_margin,
           "stability": stab, "criteria": crit, "verdict": verdict,
           "note_A7_bar": round(0.5 * matched, 6)},
          open(BASE + "/item4_v2_results.json", "w"), indent=2, sort_keys=True)
print("WROTE item4_v2_results.json")
