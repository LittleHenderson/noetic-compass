"""Phase 2 DEV SMOKE (non-claim-bearing): does a linear readout of Qwen
hidden states beat a surface baseline at the role-binding label?

Honest scope. This is a DEV smoke on the dev seed, NOT the protected
protocol. It does NOT establish claim 1_readout. It tests the specific,
known risk: templated role sentences are surface-decodable (a bag-of-words
baseline can read voice), so a hidden-state probe is unlikely to beat
surface by the preregistered >=0.10 margin. Reports whatever is true.
No steering. No weight change.
"""
import json
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import data_gen  # noqa: E402


def fit_logreg(X, y, epochs=400, lr=0.05, wd=1e-3, seed=0):
    """Deterministic L2-regularized logistic regression (torch)."""
    torch.manual_seed(seed)
    Xt = torch.tensor(np.asarray(X), dtype=torch.float32)
    yt = torch.tensor(np.asarray(y), dtype=torch.float32)
    mu = Xt.mean(0, keepdim=True)
    sd = Xt.std(0, keepdim=True) + 1e-6
    Xn = (Xt - mu) / sd
    w = torch.zeros(Xn.shape[1], requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    opt = torch.optim.Adam([w, b], lr=lr, weight_decay=wd)
    bce = torch.nn.functional.binary_cross_entropy_with_logits
    for _ in range(epochs):
        opt.zero_grad()
        loss = bce(Xn @ w + b.squeeze(), yt)
        loss.backward()
        opt.step()
    return (w.detach(), b.detach(), mu, sd)


def score_logreg(params, X, y):
    w, b, mu, sd = params
    Xn = (torch.tensor(np.asarray(X), dtype=torch.float32) - mu) / sd
    pred = (Xn @ w + b.squeeze() > 0).float()
    return float((pred == torch.tensor(np.asarray(y),
                 dtype=torch.float32)).float().mean().item())

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
LAYERS_TO_TRY = [4, 8, 12, 16, 20]
MAX_TRAIN = 1200
MAX_TEST = 600


def bag_of_words(texts, vocab):
    X = np.zeros((len(texts), len(vocab)), dtype=np.float32)
    idx = {w: i for i, w in enumerate(vocab)}
    for r, t in enumerate(texts):
        for w in t.replace(".", "").split():
            if w in idx:
                X[r, idx[w]] += 1.0
    return X


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, revision=REVISION, torch_dtype=torch.float16,
        output_hidden_states=True).to(device).eval()

    train, test = data_gen.generate()
    train = train[:MAX_TRAIN]
    test = test[:MAX_TEST]

    def hidden(texts):
        # last-token hidden state at every layer, batched
        outs = {L: [] for L in LAYERS_TO_TRY}
        bs = 64
        for i in range(0, len(texts), bs):
            batch = texts[i:i + bs]
            enc = tok(batch, return_tensors="pt", padding=True).to(device)
            with torch.no_grad():
                hs = model(**enc).hidden_states  # tuple (L+1) of (b,t,h)
            last_idx = enc["attention_mask"].sum(1) - 1
            for L in LAYERS_TO_TRY:
                h = hs[L][torch.arange(len(batch)), last_idx]
                outs[L].append(h.float().cpu().numpy())
        return {L: np.concatenate(v) for L, v in outs.items()}

    ytr = np.array([e["label"] for e in train])
    yte = np.array([e["label"] for e in test])
    Htr = hidden([e["text"] for e in train])
    Hte = hidden([e["text"] for e in test])

    # surface baseline: bag-of-words over the full training vocabulary
    vocab = sorted({w for e in train for w in
                    e["text"].replace(".", "").split()})
    bow_tr = bag_of_words([e["text"] for e in train], vocab)
    bow_te = bag_of_words([e["text"] for e in test], vocab)
    bow = fit_logreg(bow_tr, ytr)
    bow_acc = score_logreg(bow, bow_te, yte)

    majority = float(max(yte.mean(), 1 - yte.mean()))

    probe = {}
    for L in LAYERS_TO_TRY:
        clf = fit_logreg(Htr[L], ytr)
        probe[L] = score_logreg(clf, Hte[L], yte)
    best_L = max(probe, key=probe.get)
    best_probe = probe[best_L]

    result = {
        "schema": "eta_epsilon_weight_learning.phase2_dev_smoke.v0.1",
        "status": "DEV_SMOKE_NON_CLAIM_BEARING",
        "model": MODEL, "revision": REVISION, "device": device,
        "label": "agent_is_surface_first (active=1, passive=0)",
        "n_train": len(train), "n_test": len(test),
        "test_uses_held_out_vocab": True,
        "majority_baseline": majority,
        "bag_of_words_surface_baseline_acc": bow_acc,
        "probe_acc_by_layer": probe,
        "best_probe_layer": best_L, "best_probe_acc": best_probe,
        "probe_minus_surface": best_probe - bow_acc,
        "prereg_margin_required": 0.10,
        "beats_surface_by_margin": (best_probe - bow_acc) >= 0.10,
        "honest_reading": (
            "If probe ~ surface (both near ceiling), the role label is "
            "surface-decodable and the readout does NOT beat surface -> "
            "the same Gate-2 surface-decodability wall. This dev smoke "
            "does not license claim 1_readout under any outcome."),
    }
    out = os.path.join(os.path.dirname(HERE), "reports",
                       "phase2_dev_smoke.json")
    json.dump(result, open(out, "w", encoding="utf-8"), indent=2)
    print(json.dumps({k: result[k] for k in
                      ("majority_baseline",
                       "bag_of_words_surface_baseline_acc",
                       "best_probe_layer", "best_probe_acc",
                       "probe_minus_surface", "beats_surface_by_margin")},
                     indent=2))
    print("saved", out)


if __name__ == "__main__":
    main()
