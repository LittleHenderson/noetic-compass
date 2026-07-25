"""Gate 2 item 4 — v4: is the wrong-layer control failure real, or my artifact?

v3 varied the ITEM layer while holding anchors at L10, and found mismatched
anchors@L10/items@L12 scoring .3316 vs matched .1979 -- reported as a failed
specificity control.

But item quality varies enormously by layer on its own (E13: layer 0 at chance,
layer 12 the strongest for every arm). So that test conflates two things:
"mismatched layers still work" and "layer-12 items are simply better". It cannot
separate them.

The CLEAN control holds ITEMS FIXED at the frozen layer and varies the ANCHOR
layer. That isolates anchor/item mismatch from item quality. If anchors drawn
from a wrong layer collapse toward chance against fixed items@L10, the readout
IS layer-matched in the sense the design claims, and v3's finding was my
artifact. If they do not collapse, the failure is real and the design's
commensurability claim genuinely does not hold.

Both directions are reported side by side so the difference is visible rather
than asserted.
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
L_FROZEN = 10
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


def framed(b):
    return [f.format(body=x) for x in b for f in FRAMES]


def avgf(mat, n):
    return mat.reshape(n, len(FRAMES), -1).mean(1)


def l2(x):
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.where(n < 1e-12, 1.0, n)


def macro(yt, yp, classes):
    vals = [(yp[yt == c] == c).mean() for c in classes if (yt == c).any()]
    return float(np.mean(vals)) if vals else 0.0


rows = [json.loads(l) for l in open(BASE + "/holdout_40e_repaired_v1.jsonl", encoding="utf-8") if l.strip()]
eng = [r["english"] for r in rows]
lab = np.array([r["element_label"] for r in rows])
spl = np.array([r["split"] for r in rows])
calib = spl == "val"; ev = spl == "test"
classes = sorted(set(lab))

print("item pass...", flush=True)
items = {L: avgf(v, len(eng)) for L, v in encode(framed(eng), GRID).items()}

arms = json.load(open(BASE + "/arms.json", encoding="utf-8"))
defsA = arms["A_owner_raw"]
codesA = sorted(defsA)
bodiesA = [defsA[c] for c in codesA]

print("anchor passes at every grid layer...", flush=True)
anchor_by_layer = {}
enc_all = encode(framed(bodiesA), GRID)
for L in GRID:
    anchor_by_layer[L] = avgf(enc_all[L], len(codesA))


def readout(anchor, item_layer, seed):
    X = items[item_layer]
    r = np.random.default_rng(seed)
    cc = np.where(calib)[0]
    sub = r.choice(cc, size=int(0.8 * len(cc)), replace=False)
    v = l2(X - X[sub].mean(0, keepdims=True))
    u = l2(anchor - anchor.mean(0, keepdims=True))
    pred = np.array([codesA[i] for i in (v[ev] @ u.T).argmax(1)])
    return macro(lab[ev], pred, classes)


def avg(anchor, item_layer):
    return round(float(np.mean([readout(anchor, item_layer, s) for s in SEEDS])), 6)


matched = avg(anchor_by_layer[L_FROZEN], L_FROZEN)
print("matched anchors@L%d / items@L%d : %.4f" % (L_FROZEN, L_FROZEN, matched), flush=True)

print("\nCLEAN CONTROL - items FIXED at L%d, anchor layer varies:" % L_FROZEN, flush=True)
clean = {}
for L in GRID:
    if L == L_FROZEN:
        continue
    clean[L] = avg(anchor_by_layer[L], L_FROZEN)
    print("   anchors@L%-2d / items@L%d : %.4f" % (L, L_FROZEN, clean[L]), flush=True)

print("\nv3 DIRECTION (confounded) - anchors FIXED at L%d, item layer varies:" % L_FROZEN, flush=True)
confounded = {}
for L in GRID:
    if L == L_FROZEN:
        continue
    confounded[L] = avg(anchor_by_layer[L_FROZEN], L)
    print("   anchors@L%d / items@L%-2d : %.4f" % (L_FROZEN, L, confounded[L]), flush=True)

print("\nDIAGONAL - both at the same layer (item-quality reference):", flush=True)
diag = {L: avg(anchor_by_layer[L], L) for L in GRID}
for L in GRID:
    print("   both@L%-2d : %.4f" % (L, diag[L]), flush=True)

chance = 1.0 / len(classes)
clean_max = max(clean.values())
verdict = "PASS_layer_matched" if clean_max < matched else "FAIL_not_layer_matched"
print("\nCLEAN CONTROL VERDICT: max mismatched-anchor score %.4f vs matched %.4f -> %s" % (
    clean_max, matched, verdict), flush=True)

json.dump({
    "design": "TKS-DEFCTX-40E-PRIMARY-v1", "version": "v4_wrong_layer_control_disambiguated",
    "model": "EleutherAI/pythia-160m", "frozen_layer": L_FROZEN, "seeds": len(SEEDS),
    "chance": round(chance, 6), "matched_reference": matched,
    "clean_control_items_fixed_anchor_varies": clean,
    "confounded_control_anchors_fixed_item_varies": confounded,
    "diagonal_both_same_layer": diag,
    "clean_control_max": clean_max,
    "verdict": verdict,
    "why_two_directions": (
        "Varying the ITEM layer conflates mismatch with item quality, because item layers differ "
        "enormously on their own (diagonal row shows this). Holding items FIXED and varying the "
        "ANCHOR layer isolates mismatch. The clean control is the one that tests the design's "
        "commensurability claim."
    ),
}, open(BASE + "/item4_results_v4.json", "w"), indent=2, sort_keys=True)
print("WROTE item4_results_v4.json")
