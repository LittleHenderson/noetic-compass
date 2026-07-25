"""Gate 2 item 4 — v3: the rest of the pre-registered battery.

Adds three criteria v2 left open, all testable without the order-aware encoder:

  TRUE WRONG-LAYER CONTROL. v2's "wrong_layer" scored anchors AND items both at
  layer 2, which is not a specificity test at all -- it is the same experiment at
  another layer. The real control reads ANCHORS at the frozen layer L and ITEMS
  at a DIFFERENT layer, breaking the commensurability the design depends on.
  Expected near chance; if it is not, the readout is not layer-matched.

  E13 LAYER STABILITY. Run every arm at every layer in the frozen grid and check
  whether the licensed contrast (A and B above D, E, F) holds at >= 60% of
  layers. A result that appears at exactly one layer is a coincidence.

  E8 EQUAL-TOKEN-BUDGET REPLICATE. Arm D is shorter than A/B (mean 116 vs
  196/198 chars), so A-over-D could be measuring verbosity. Truncate EVERY arm at
  SENTENCE BOUNDARIES to the shortest arm's per-code token budget and re-run. If
  a contrast does not survive with the same sign, it is LENGTH_CONFOUNDED and the
  pre-registration says it is NOT LICENSED.
"""
import os, json, re
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
L_FROZEN = 10           # from v2's arm-free held-out selection (0.4622, unique max)
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


def truncate_sentences(text, budget_tokens):
    """Truncate at SENTENCE boundaries only. Mid-clause truncation produces
    ungrammatical fragments -- that is corruption, not a length control."""
    parts = re.split(r"(?<=[.!?])\s+", str(text).strip())
    kept, used = [], 0
    for p in parts:
        n = len(tok(p, add_special_tokens=False).input_ids)
        if kept and used + n > budget_tokens:
            break
        kept.append(p); used += n
        if used >= budget_tokens:
            break
    return " ".join(kept) if kept else parts[0]


rows = [json.loads(l) for l in open(BASE + "/holdout_40e_repaired_v1.jsonl", encoding="utf-8") if l.strip()]
eng = [r["english"] for r in rows]
lab = np.array([r["element_label"] for r in rows])
spl = np.array([r["split"] for r in rows])
calib = spl == "val"; ev = spl == "test"
classes = sorted(set(lab))
print("bank %d | calib %d | eval %d" % (len(rows), calib.sum(), ev.sum()), flush=True)

print("item pass (all grid layers)...", flush=True)
items = {L: avgf(v, len(eng)) for L, v in encode(framed(eng), GRID).items()}

arms = json.load(open(BASE + "/arms.json", encoding="utf-8"))
arm_ids = sorted(arms)


def anchors_at(defs, layer):
    codes = sorted(defs)
    return codes, avgf(encode(framed([defs[c] for c in codes]), [layer])[layer], len(codes))


def readout(anchor, codes, seed, item_layer):
    X = items[item_layer]
    r = np.random.default_rng(seed)
    cc = np.where(calib)[0]
    sub = r.choice(cc, size=int(0.8 * len(cc)), replace=False)
    v = l2(X - X[sub].mean(0, keepdims=True))
    u = l2(anchor - anchor.mean(0, keepdims=True))
    pred = np.array([codes[i] for i in (v[ev] @ u.T).argmax(1)])
    return macro(lab[ev], pred, classes)


# ---------------- E13 layer stability: every arm at every grid layer
print("E13 layer stability...", flush=True)
stability = {}
for L in GRID:
    per = {}
    for aid in arm_ids:
        codes, anc = anchors_at(arms[aid], L)
        per[aid] = round(float(np.mean([readout(anc, codes, s, L) for s in SEEDS])), 6)
    tks = min(per.get("A_owner_raw", 0), per.get("B_deployed", 0))
    other = max(per.get("D_compact_cas", 1), per.get("E_non_tks", 1), per.get("F_F1_null", 1))
    per["contrast_holds"] = bool(tks > other)
    stability[L] = per
    print("   layer %2d: A %.4f B %.4f D %.4f E %.4f F %.4f | holds=%s" % (
        L, per.get("A_owner_raw", 0), per.get("B_deployed", 0), per.get("D_compact_cas", 0),
        per.get("E_non_tks", 0), per.get("F_F1_null", 0), per["contrast_holds"]), flush=True)
held = sum(1 for L in GRID if stability[L]["contrast_holds"])
frac = held / len(GRID)
print("E13: contrast holds at %d/%d layers = %.1f%% (bar 60%%) -> %s" % (
    held, len(GRID), 100 * frac, "PASS" if frac >= 0.60 else "FAIL"), flush=True)

# ---------------- TRUE wrong-layer control: anchors at L, items at a DIFFERENT layer
print("true wrong-layer control...", flush=True)
codesA, ancA_L = anchors_at(arms["A_owner_raw"], L_FROZEN)
wrong = {}
for other_layer in [x for x in GRID if x != L_FROZEN]:
    wrong[other_layer] = round(float(np.mean([readout(ancA_L, codesA, s, other_layer) for s in SEEDS])), 6)
    print("   anchors@L%d vs items@L%d : %.4f" % (L_FROZEN, other_layer, wrong[other_layer]), flush=True)
matched = round(float(np.mean([readout(ancA_L, codesA, s, L_FROZEN) for s in SEEDS])), 6)
print("   matched anchors@L%d vs items@L%d : %.4f" % (L_FROZEN, L_FROZEN, matched), flush=True)

# ---------------- E8 equal-token-budget replicate
print("E8 equal-token-budget replicate...", flush=True)
budgets = {}
for aid in arm_ids:
    budgets[aid] = int(np.median([len(tok(str(v), add_special_tokens=False).input_ids) for v in arms[aid].values()]))
budget = min(budgets.values())
print("   per-arm median tokens: %s -> shortest budget %d" % (budgets, budget), flush=True)
trunc_arms = {aid: {c: truncate_sentences(v, budget) for c, v in arms[aid].items()} for aid in arm_ids}
e8 = {}
for aid in arm_ids:
    codes, anc = anchors_at(trunc_arms[aid], L_FROZEN)
    e8[aid] = round(float(np.mean([readout(anc, codes, s, L_FROZEN) for s in SEEDS])), 6)
    print("   %-18s truncated %.4f" % (aid, e8[aid]), flush=True)
full_margin = 0.1597
e8_margin = e8.get("A_owner_raw", 0) - e8.get("D_compact_cas", 0)
e8_same_sign = (e8_margin > 0) == (full_margin > 0)
print("E8: A-D margin full %.4f -> truncated %.4f | same sign %s -> %s" % (
    full_margin, e8_margin, e8_same_sign, "PASS" if e8_same_sign else "LENGTH_CONFOUNDED"), flush=True)

json.dump({
    "design": "TKS-DEFCTX-40E-PRIMARY-v1", "version": "v3_remaining_battery",
    "model": "EleutherAI/pythia-160m", "frozen_layer": L_FROZEN, "seeds": len(SEEDS),
    "E13_layer_stability": {"per_layer": stability, "layers_holding": held,
                            "fraction": round(frac, 4), "bar": 0.60,
                            "verdict": "PASS" if frac >= 0.60 else "FAIL"},
    "true_wrong_layer_control": {"anchors_at_L": L_FROZEN, "items_at_other_layers": wrong,
                                 "matched_reference": matched,
                                 "note": "anchors and items read at DIFFERENT layers; the v2 'wrong_layer' number was matched-layer and is superseded"},
    "E8_equal_token_budget": {"per_arm_median_tokens": budgets, "shortest_budget": budget,
                              "truncated_macro": e8, "full_A_minus_D": full_margin,
                              "truncated_A_minus_D": round(float(e8_margin), 6),
                              "same_sign": bool(e8_same_sign),
                              "verdict": "PASS" if e8_same_sign else "LENGTH_CONFOUNDED_NOT_LICENSED"},
}, open(BASE + "/item4_results_v3.json", "w"), indent=2, sort_keys=True)
print("WROTE item4_results_v3.json")
