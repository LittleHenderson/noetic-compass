"""v0.3 EXPLORATORY preview (NON-CLAIM-BEARING). Does a CAS-Noetic
readout of Qwen hidden states generalize to HELD-OUT verbs, beating
surface and a random-partition control? This informs the owner's sign-off
on V0_3_CAS_SPECIFIC_PREREG.md. It does NOT license any claim. The
decisive matched-non-CAS-SEMANTIC control is deferred to the approved run.
"""
import json
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
LAYER = 12
NOUNS = ["cat", "dog", "fox", "hen", "bird", "wolf", "lion", "bear"]
NOETIC_VERBS = {
    "^2_attraction": ["likes", "loves", "wants", "enjoys", "admires", "needs"],
    "^3_aversion": ["hates", "fears", "avoids", "dislikes", "dreads", "resents"],
    "^6_decomposition": ["examines", "analyzes", "studies", "inspects", "questions", "tests"],
    "^8_triggering": ["reminds", "alerts", "warns", "signals", "triggers", "prompts"],
}
CLASSES = list(NOETIC_VERBS)
TEST_VERBS = {c: set(v[-2:]) for c, v in NOETIC_VERBS.items()}  # held out


def build():
    import random
    rng = random.Random(20260830)
    tr, te = [], []
    for ci, c in enumerate(CLASSES):
        for verb in NOETIC_VERBS[c]:
            for _ in range(10):
                a, b = rng.sample(NOUNS, 2)
                ex = {"text": f"the {a} {verb} the {b}.", "y": ci, "verb": verb}
                (te if verb in TEST_VERBS[c] else tr).append(ex)
    rng.shuffle(tr); rng.shuffle(te)
    return tr, te


def softmax_probe(Xtr, ytr, Xte, yte, seed=0):
    torch.manual_seed(seed)
    Xt = torch.tensor(Xtr, dtype=torch.float32)
    mu = Xt.mean(0, keepdim=True); sd = Xt.std(0, keepdim=True) + 1e-6
    Xtn = (Xt - mu) / sd
    yt = torch.tensor(ytr)
    W = torch.zeros(Xtn.shape[1], len(CLASSES), requires_grad=True)
    bvec = torch.zeros(len(CLASSES), requires_grad=True)
    opt = torch.optim.Adam([W, bvec], lr=0.05, weight_decay=1e-3)
    for _ in range(300):
        opt.zero_grad()
        loss = torch.nn.functional.cross_entropy(Xtn @ W + bvec, yt)
        loss.backward(); opt.step()
    Xen = (torch.tensor(Xte, dtype=torch.float32) - mu) / sd
    pred = (Xen @ W + bvec).argmax(1).numpy()
    return float((pred == np.array(yte)).mean())


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, revision=REVISION, dtype=torch.float16,
        output_hidden_states=True).to(dev).eval()
    tr, te = build()

    def hidden(items):
        H = []
        for i in range(0, len(items), 32):
            enc = tok([e["text"] for e in items[i:i + 32]],
                      return_tensors="pt", padding=True).to(dev)
            with torch.no_grad():
                H.append(model(**enc).hidden_states[LAYER][:, -1, :].float().cpu().numpy())
        return np.concatenate(H)

    Htr, Hte = hidden(tr), hidden(te)
    ytr = [e["y"] for e in tr]; yte = [e["y"] for e in te]

    # surface bag-of-words
    vocab = sorted({w for e in tr for w in e["text"].replace(".", "").split()})
    idx = {w: i for i, w in enumerate(vocab)}

    def bow(items):
        X = np.zeros((len(items), len(vocab)), np.float32)
        for r, e in enumerate(items):
            for w in e["text"].replace(".", "").split():
                if w in idx:
                    X[r, idx[w]] += 1
        return X
    probe_acc = softmax_probe(Htr, ytr, Hte, yte)
    surf_acc = softmax_probe(bow(tr), ytr, bow(te), yte)
    # random-partition control: shuffle labels among train, same test
    rng = np.random.default_rng(161803)
    yshuf = rng.permutation(ytr).tolist()
    rand_acc = softmax_probe(Htr, yshuf, Hte, yte)
    chance = 1.0 / len(CLASSES)

    out = {
        "schema": "eta_epsilon_weight_learning.v0_3_cas_noetic_explore.v0.1",
        "status": "EXPLORATORY_NON_CLAIM_BEARING",
        "classes": CLASSES, "n_train": len(tr), "n_test_heldout_verbs": len(te),
        "chance": chance,
        "cas_noetic_probe_heldout_acc": probe_acc,
        "surface_bow_heldout_acc": surf_acc,
        "shuffled_label_control_acc": rand_acc,
        "probe_minus_surface": probe_acc - surf_acc,
        "reads_beyond_surface_on_heldout_verbs": (probe_acc - surf_acc) >= 0.10,
        "honest_note": ("Held-out VERBS: surface bow cannot use unseen verbs. If the "
                        "hidden-state Noetic probe beats surface here, the model encodes "
                        "the Noetic semantically and generalizes. This does NOT yet show "
                        "CAS-SPECIFICITY - that needs the matched-non-CAS-SEMANTIC control "
                        "(deferred to the approved v0.3 run). Non-claim-bearing preview."),
    }
    p = os.path.join(os.path.dirname(HERE), "reports", "v0_3_cas_noetic_explore.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=2)
    print(json.dumps({k: out[k] for k in
          ("chance", "cas_noetic_probe_heldout_acc", "surface_bow_heldout_acc",
           "shuffled_label_control_acc", "probe_minus_surface",
           "reads_beyond_surface_on_heldout_verbs")}, indent=2))
    print("saved", p)


if __name__ == "__main__":
    main()
