"""Gate 2 item 4 v5 (MULTIPLICATIVE) — held-out compositional reconstruction. TKS-HELDOUT-COMPOSITION-MULT-v5.

Implements GATE2_ITEM4_PREREGISTRATION_V3_COMPOSITION.md, committed at 265c6b68
BEFORE this ran.

For each of 40 cells: delete it entirely, compose a substitute anchor from its
row and column by a fixed parameter-free rule, score that class's items.
The held-out cell's own words never enter, so the lexical control MUST sit at
chance by construction -- that is criterion V3, the honesty gate.
"""
import os, json, re, collections
import numpy as np
os.environ.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false"})
import torch, transformers

MODEL = "/workspace/cas-hf-cache/models--EleutherAI--pythia-1b/snapshots/f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2"
BASE = "/workspace/item4"
L = 12
FRAMES = (
    "Definition: {body}\nThat role describes:",
    "The following describes one role.\n{body}\nThat role describes:",
    "Consider this description.\n{body}\nThat role describes:",
    "Description: {body}\nThat role describes:",
)

m = transformers.AutoModelForCausalLM.from_pretrained(
    MODEL, local_files_only=True, dtype=torch.float32,
    attn_implementation="eager", use_safetensors=True, output_hidden_states=True).to("cuda:0").eval()
tok = transformers.AutoTokenizer.from_pretrained(MODEL, local_files_only=True, use_fast=True)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token


@torch.no_grad()
def enc(texts, bs=32):
    out = []
    for i in range(0, len(texts), bs):
        e = tok(texts[i:i + bs], return_tensors="pt", padding=True, truncation=True, max_length=384)
        ids = e.input_ids.to("cuda:0"); am = e.attention_mask.to("cuda:0")
        hs = m(input_ids=ids, attention_mask=am).hidden_states[L]
        last = am.sum(1) - 1
        out.append(hs[torch.arange(hs.shape[0], device=hs.device), last, :].float().cpu().numpy())
    return np.concatenate(out, 0)


def framed(bodies):
    return [f.format(body=b) for b in bodies for f in FRAMES]


def avgf(mat, n):
    return mat.reshape(n, len(FRAMES), -1).mean(1)


def l2(x):
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.where(n < 1e-12, 1.0, n)


rows = [json.loads(l_) for l_ in open(BASE + "/holdout_40e_repaired_v1.jsonl", encoding="utf-8") if l_.strip()]
rows = [r for r in rows if r["split"] == "test"]
eng = [r["english"] for r in rows]
lab = np.array([r["element_label"] for r in rows])
arms = json.load(open(BASE + "/arms.json", encoding="utf-8"))
codes = sorted(arms["A_owner_raw"])                       # A1..D10
world = {c: c[0] for c in codes}                          # A/B/C/D
noetic = {c: c[1:] for c in codes}                        # 1..10
print("cells %d | test items %d" % (len(codes), len(rows)), flush=True)

item_states = l2(avgf(enc(framed(eng)), len(eng)))

STOP0 = set("the a an of and or to in is are be for on with that this it as by from at was were not no all any some its their".split())
def _tok(t): return [w for w in re.findall(r"[a-z]+", str(t).lower()) if w not in STOP0 and len(w) > 2]

# Vocabulary of each held-out class's TEST ITEMS. These words are deleted from
# every definition in every arm for that fold -- the v4 masking rule.
item_vocab = {}
for c in codes:
    v = set()
    for j in np.where(lab == c)[0]:
        v.update(_tok(eng[j]))
    item_vocab[c] = v
print("mean item-vocab size: %.1f words" % np.mean([len(v) for v in item_vocab.values()]), flush=True)

def mask_text(text, banned):
    kept = [w for w in re.findall(r"[A-Za-z]+", str(text)) if w.lower() not in banned]
    return " ".join(kept) if kept else "unspecified"

# Per-fold masked anchors: anchors_masked[arm][held_cell] -> (40, d) matrix
anchors_masked = {}
for aid in ("A_owner_raw", "D_compact_cas"):
    per_fold = {}
    for hc in codes:
        banned = item_vocab[hc]
        bodies = [mask_text(arms[aid][c], banned) for c in codes]
        per_fold[hc] = avgf(enc(framed(bodies)), len(codes))
    anchors_masked[aid] = per_fold
    print("masked anchors ready:", aid, flush=True)
anchors = {aid: anchors_masked[aid][codes[0]] for aid in anchors_masked}


def compose(anchor_mat, held_idx):
    """u_c = normalize( mean(row) + mean(col) - global mean ), held cell EXCLUDED."""
    c = codes[held_idx]
    keep = [i for i in range(len(codes)) if i != held_idx]
    row_i = [i for i in keep if noetic[codes[i]] == noetic[c]]
    col_i = [i for i in keep if world[codes[i]] == world[c]]
    if not row_i or not col_i:
        return None
    # v5: ELEMENTWISE PRODUCT (was: row + col - global). Carries interaction terms.
    r = anchor_mat[row_i].mean(0)
    c_ = anchor_mat[col_i].mean(0)
    return r * c_


def loo_score(anchor_mat, per_fold=None):
    """For each held-out cell: compose it, score its items against 39 real + 1 composed.

    When per_fold is given, the fold's MASKED anchor matrix is used -- every word
    appearing in the held-out class's test items has been deleted from every
    definition in every arm before encoding.
    """
    correct_per_cell, per_cell = [], {}
    for hi, hc in enumerate(codes):
        anchor_mat = per_fold[hc] if per_fold is not None else anchor_mat
        comp = compose(anchor_mat, hi)
        if comp is None:
            continue
        u = anchor_mat.copy()
        u[hi] = comp                                  # ONLY the held cell is replaced
        u = l2(u - u.mean(0, keepdims=True))
        mask = lab == hc
        if not mask.any():
            continue
        pred = np.array([codes[i] for i in (item_states[mask] @ u.T).argmax(1)])
        acc = float((pred == hc).mean())
        per_cell[hc] = round(acc, 6)
        correct_per_cell.append(acc)
    return float(np.mean(correct_per_cell)), per_cell


res = {}
for aid in ("A_owner_raw", "D_compact_cas"):
    mean_acc, per_cell = loo_score(anchors[aid], per_fold=anchors_masked[aid])
    res[aid] = {"reconstruction_accuracy": round(mean_acc, 6), "per_cell": per_cell,
                "cells_above_zero": int(sum(1 for v in per_cell.values() if v > 0))}
    print("  %-16s reconstruction %.4f | cells with any correct: %d/40" % (
        aid, mean_acc, res[aid]["cells_above_zero"]), flush=True)

# --- V3 HONESTY GATE: lexical control, same leave-one-out protocol, NO model
STOP = set("the a an of and or to in is are be for on with that this it as by from at was were not no all any some its their".split())
def toks(t): return [w for w in re.findall(r"[a-z]+", str(t).lower()) if w not in STOP and len(w) > 2]

def lexical_loo(defs):
    accs = []
    for hi, hc in enumerate(codes):
        banned = item_vocab[hc]
        defs = {c: mask_text(arms["A_owner_raw"][c], banned) for c in codes}   # v4: masked
        keep = [i for i in range(len(codes)) if i != hi]
        row_i = [i for i in keep if noetic[codes[i]] == noetic[hc]]
        col_i = [i for i in keep if world[codes[i]] == world[hc]]
        comp = collections.Counter()
        for i in row_i + col_i:
            comp.update(toks(defs[codes[i]]))
        vecs = {codes[i]: collections.Counter(toks(defs[codes[i]])) for i in keep}
        vecs[hc] = comp
        mask = np.where(lab == hc)[0]
        hit = 0
        for j in mask:
            it = collections.Counter(toks(eng[j]))
            best, bc = -1.0, None
            for cc, cv in vecs.items():
                num = sum(it[w] * cv[w] for w in it if w in cv)
                den = (np.sqrt(sum(v * v for v in it.values())) * np.sqrt(sum(v * v for v in cv.values()))) or 1.0
                s = num / den
                if s > best: best, bc = s, cc
            hit += (bc == hc)
        accs.append(hit / max(1, len(mask)))
    return float(np.mean(accs))

lex = round(lexical_loo(arms["A_owner_raw"]), 6)
print("  V3 lexical control (no model): %.4f  [bar <= 0.05]  %s" % (
    lex, "PASS" if lex <= 0.05 else "FAIL -> INSTRUMENT VOID"), flush=True)

# --- nulls
rg = np.random.default_rng(5)
rand_anchor = rg.normal(size=anchors["A_owner_raw"].shape)
rand_acc, _ = loo_score(rand_anchor)
shuf = rg.permutation(lab)
u = anchors["A_owner_raw"].copy()
u = l2(u - u.mean(0, keepdims=True))
pred_all = np.array([codes[i] for i in (item_states @ u.T).argmax(1)])
shuf_acc = float(np.mean([(pred_all[shuf == c] == c).mean() for c in codes if (shuf == c).any()]))
print("  null random-anchor %.4f | null shuffled-label %.4f" % (rand_acc, shuf_acc), flush=True)

# --- permutation p for TKS
obs = res["A_owner_raw"]["reconstruction_accuracy"]
null = []
for s in range(120):
    r = np.random.default_rng(1000 + s)
    perm = r.permutation(len(codes))
    a, _ = loo_score(anchors_masked["A_owner_raw"][codes[0]][perm])
    null.append(a)
pval = (1 + sum(1 for x in null if x >= obs)) / (1 + len(null))
print("  permutation p = %.4f (floor %.4f)" % (pval, 1 / 121), flush=True)

chance = 1 / len(codes)
margin = res["A_owner_raw"]["reconstruction_accuracy"] - res["D_compact_cas"]["reconstruction_accuracy"]
crit = {
    "V1_tks_above_chance": bool(obs > chance and pval < 0.01),
    "V2_tks_beats_compact_margin_0.05": bool(margin >= 0.05),
    "V3_lexical_control_at_chance": bool(lex <= 0.05),
    "V4_nulls_at_chance": bool(rand_acc <= 0.05 and shuf_acc <= 0.05),
    "V5_not_one_cell": bool(res["A_owner_raw"]["cells_above_zero"] >= 8),
}
print("\n=== v3 CRITERIA ===", flush=True)
for k, v in crit.items():
    print("  %-34s %s" % (k, "PASS" if v else "FAIL"), flush=True)
verdict = ("VOID_SAME_DISEASE" if not crit["V3_lexical_control_at_chance"]
           else ("ALL_PASS" if all(crit.values()) else "NOT_LICENSED"))
print("VERDICT:", verdict, flush=True)

json.dump({"design": "TKS-HELDOUT-COMPOSITION-MULT-v5", "prereg_commit": "265c6b68",
           "model": "EleutherAI/pythia-1b", "layer": L, "chance": round(chance, 6),
           "arms": res, "lexical_control_no_model": lex,
           "null_random_anchor": round(rand_acc, 6), "null_shuffled_label": round(shuf_acc, 6),
           "tks_minus_compact_margin": round(margin, 6),
           "permutation_p": round(pval, 6), "permutation_floor": round(1 / 121, 6),
           "criteria": crit, "verdict": verdict},
          open(BASE + "/item4_v5_results.json", "w"), indent=2, sort_keys=True)
print("WROTE item4_v5_results.json")
