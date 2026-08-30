"""Phase 2 (v0.2 amendment A1+B1): surface-resistant readout.

Target: predict the model's OWN correctness on passive role-binding from
its hidden states. Fair test = lexical split: train on some nouns/verbs,
test on HELD-OUT nouns/verbs. On held-out vocab a bag-of-words surface
baseline has no seen features, so if the hidden-state probe beats it (and
majority) with AUROC >= 0.75 and margin >= 0.10, the readout reads
something vocab-general about the model's role binding.

HONEST SCOPE: B1 is adopted (40-state CAS framing dropped). This is NOT a
test of CAS-specific value - it is a generic interpretability probe.
No steering, no weight change.
"""
import json
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import data_gen  # noqa: E402
from phase2_readout_smoke import fit_logreg  # reuse torch logreg

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
LAYERS = [4, 8, 12, 16, 20]


def auroc(y, s):
    y = np.asarray(y); s = np.asarray(s)
    pos = s[y == 1]; neg = s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    order = np.argsort(s)
    ranks = np.empty(len(s)); ranks[order] = np.arange(1, len(s) + 1)
    return float((ranks[y == 1].sum() - len(pos) * (len(pos) + 1) / 2)
                 / (len(pos) * len(neg)))


def prob(params, X):
    w, b, mu, sd = params
    Xn = (torch.tensor(np.asarray(X), dtype=torch.float32) - mu) / sd
    return torch.sigmoid(Xn @ w + b.squeeze()).numpy()


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, revision=REVISION, dtype=torch.float16,
        output_hidden_states=True).to(device).eval()

    train, test = data_gen.generate()
    tr = [e for e in train if e["voice"] == "passive"]
    te = [e for e in test if e["voice"] == "passive"]

    def chat(e):
        q = (f'In the sentence "{e["text"]}" who performed the action? '
             f'Answer with one word only.')
        return tok.apply_chat_template([{"role": "user", "content": q}],
                                       tokenize=False,
                                       add_generation_prompt=True)

    def correctness_and_hidden(items):
        labels, H = [], {L: [] for L in LAYERS}
        bs = 32
        for i in range(0, len(items), bs):
            batch = items[i:i + bs]
            prompts = [chat(e) for e in batch]
            enc = tok(prompts, return_tensors="pt", padding=True).to(device)
            with torch.no_grad():
                out = model.generate(**enc, max_new_tokens=8,
                                     do_sample=False,
                                     pad_token_id=tok.pad_token_id,
                                     output_hidden_states=False)
                fwd = model(**enc)  # hidden states at prompt last token
            gen = out[:, enc["input_ids"].shape[1]:]
            for j, e in enumerate(batch):
                ans = tok.decode(gen[j], skip_special_tokens=True).lower()
                words = ans.replace(".", " ").replace(",", " ").split()
                pa = next((k for k, w in enumerate(words)
                           if w == e["agent"]), 1e9)
                pp = next((k for k, w in enumerate(words)
                           if w == e["patient"]), 1e9)
                labels.append(1 if pa < pp else 0)   # 1 = model correct
            for L in LAYERS:
                h = fwd.hidden_states[L][:, -1, :]    # left-padded -> last
                H[L].append(h.float().cpu().numpy())
        return np.array(labels), {L: np.concatenate(v) for L, v in H.items()}

    ytr, Htr = correctness_and_hidden(tr)
    yte, Hte = correctness_and_hidden(te)

    def bow_mat(items, vocab):
        idx = {w: i for i, w in enumerate(vocab)}
        X = np.zeros((len(items), len(vocab)), np.float32)
        for r, e in enumerate(items):
            for w in e["text"].replace(".", "").split():
                if w in idx:
                    X[r, idx[w]] += 1
        return X

    vocab = sorted({w for e in tr for w in e["text"].replace(".", "").split()})
    bow = fit_logreg(bow_mat(tr, vocab), ytr)
    bow_auroc = auroc(yte, prob(bow, bow_mat(te, vocab)))
    majority = float(max(yte.mean(), 1 - yte.mean()))

    probe_auroc, shuffled, probe_scores = {}, {}, {}
    rng = np.random.default_rng(161803)
    ysh = rng.permutation(ytr)
    for L in LAYERS:
        p = fit_logreg(Htr[L], ytr)
        probe_scores[L] = prob(p, Hte[L])
        probe_auroc[L] = auroc(yte, probe_scores[L])
        ps = fit_logreg(Htr[L], ysh)
        shuffled[L] = auroc(yte, prob(ps, Hte[L]))
    bestL = max(probe_auroc, key=probe_auroc.get)
    best = probe_auroc[bestL]
    margin = best - max(bow_auroc, 0.5)

    # bootstrap 95% CI on the probe-minus-surface AUROC margin
    bow_scores = prob(bow, bow_mat(te, vocab))
    boot = np.random.default_rng(314159)
    diffs = []
    n = len(yte)
    for _ in range(2000):
        idx = boot.integers(0, n, n)
        diffs.append(auroc(yte[idx], probe_scores[bestL][idx])
                     - auroc(yte[idx], bow_scores[idx]))
    lo, hi = float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))
    ci_excludes_zero = lo > 0.0

    out = {
        "schema": "eta_epsilon_weight_learning.phase2_correctness_readout.v0.1",
        "status": "V0_2_AMENDMENT_A1_B1_generic_not_cas_specific",
        "model": MODEL, "device": device,
        "readout_target": "model's own passive role-binding correctness",
        "lexical_split": {"train_passives": len(tr), "test_passives": len(te),
                          "test_uses_held_out_vocab": True},
        "label_balance_test_correct_rate": float(yte.mean()),
        "majority_baseline": majority,
        "bag_of_words_surface_auroc": bow_auroc,
        "probe_auroc_by_layer": probe_auroc,
        "shuffled_label_control_auroc_by_layer": shuffled,
        "best_probe_layer": bestL, "best_probe_auroc": best,
        "probe_minus_surface_auroc": margin,
        "margin_bootstrap_95ci": [lo, hi],
        "margin_ci_excludes_zero": ci_excludes_zero,
        "prereg_gate": {"auroc_min": 0.75, "margin_min": 0.10,
                        "bootstrap_ci_excludes_zero": True},
        "readout_clears_gate": (best >= 0.75 and margin >= 0.10
                                and ci_excludes_zero),
        "honest_note": ("B1 adopted: not a CAS-specific claim. Surface "
                        "baseline is weak on held-out vocab by construction; "
                        "the real question is whether the probe reads "
                        "vocab-general role-binding structure."),
    }
    p = os.path.join(os.path.dirname(HERE), "reports",
                     "phase2_correctness_readout.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=2)
    print(json.dumps({k: out[k] for k in
          ("label_balance_test_correct_rate", "majority_baseline",
           "bag_of_words_surface_auroc", "best_probe_layer",
           "best_probe_auroc", "probe_minus_surface_auroc",
           "margin_bootstrap_95ci", "margin_ci_excludes_zero",
           "readout_clears_gate")}, indent=2))
    print("shuffled-label control AUROC:", {k: round(v, 3) for k, v in shuffled.items()})
    print("saved", p)


if __name__ == "__main__":
    main()
