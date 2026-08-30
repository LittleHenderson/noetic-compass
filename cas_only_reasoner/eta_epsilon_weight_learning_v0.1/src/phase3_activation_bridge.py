"""Phase 3: activation-level bridge. Steer the layer-12 residual along
the readout direction and test whether WRONG passives flip to CORRECT
BEHAVIOR (exact role binding), not merely a probe move.

Direction: the layer-12 correctness-probe gradient in raw hidden space,
d = w / sd (unit-normalized). Steer h_12 += alpha * d_unit via a forward
hook, regenerate, re-check the exact role answer.

Kill rule (prereg): if the probe/score moves but exact behavior does not
improve above zero/random -> READOUT_STEERING_WITHOUT_BEHAVIORAL_GAIN.
Controls: zero, opposite sign, random same-norm. No weight change (this
is an activation intervention only)."""
import json
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import data_gen  # noqa: E402
from phase2_readout_smoke import fit_logreg  # noqa: E402

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
LAYER = 12


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

    steer = {"vec": None}
    layer_mod = model.model.layers[LAYER]

    def hook(module, inp, out):
        if steer["vec"] is None:
            return out
        if isinstance(out, tuple):
            h = out[0]
            h = h + steer["vec"].to(h.dtype)
            return (h,) + tuple(out[1:])
        return out + steer["vec"].to(out.dtype)
    layer_mod.register_forward_hook(hook)

    def answers(items):
        res = []
        bs = 32
        for i in range(0, len(items), bs):
            batch = items[i:i + bs]
            enc = tok([chat(e) for e in batch], return_tensors="pt",
                      padding=True).to(device)
            with torch.no_grad():
                out = model.generate(**enc, max_new_tokens=8,
                                     do_sample=False,
                                     pad_token_id=tok.pad_token_id)
            gen = out[:, enc["input_ids"].shape[1]:]
            for j, e in enumerate(batch):
                a = tok.decode(gen[j], skip_special_tokens=True).lower()
                words = a.replace(".", " ").replace(",", " ").split()
                pa = next((k for k, w in enumerate(words) if w == e["agent"]), 1e9)
                pp = next((k for k, w in enumerate(words) if w == e["patient"]), 1e9)
                res.append(1 if pa < pp else 0)
        return np.array(res)

    def hidden12(items):
        H = []
        bs = 32
        for i in range(0, len(items), bs):
            batch = items[i:i + bs]
            enc = tok([chat(e) for e in batch], return_tensors="pt",
                      padding=True).to(device)
            with torch.no_grad():
                fwd = model(**enc)
            H.append(fwd.hidden_states[LAYER][:, -1, :].float().cpu().numpy())
        return np.concatenate(H)

    # fit the layer-12 correctness probe on train passives
    steer["vec"] = None
    ytr = answers(tr)
    Xtr = hidden12(tr)
    w, b, mu, sd = fit_logreg(Xtr, ytr)
    d = (w / sd.squeeze()).numpy()
    d_unit = d / np.linalg.norm(d)
    hnorm = float(np.linalg.norm(Xtr, axis=1).mean())

    # baseline behavior on test passives
    steer["vec"] = None
    yte0 = answers(te)
    wrong = [te[i] for i in range(len(te)) if yte0[i] == 0]
    right = [te[i] for i in range(len(te)) if yte0[i] == 1]

    rng = np.random.default_rng(271828)
    rand_unit = rng.standard_normal(d_unit.shape)
    rand_unit /= np.linalg.norm(rand_unit)

    def flip_up(items, vec):
        if not items:
            return None
        steer["vec"] = None if vec is None else torch.tensor(
            vec, dtype=torch.float16, device=device)
        y = answers(items)
        steer["vec"] = None
        return float(y.mean())    # fraction now correct

    alphas = [0.5, 1.0, 2.0]     # multiples of mean hidden norm
    results = {}
    for a in alphas:
        scale = a * hnorm
        results[f"alpha_{a}"] = {
            "wrong_to_correct_plus_readout": flip_up(wrong, scale * d_unit),
            "wrong_to_correct_random": flip_up(wrong, scale * rand_unit),
            "wrong_to_correct_opposite": flip_up(wrong, -scale * d_unit),
            "collateral_right_still_correct_plus": flip_up(right, scale * d_unit),
        }
    baseline = {"wrong_set_size": len(wrong), "right_set_size": len(right),
                "wrong_baseline_correct": 0.0, "right_baseline_correct": 1.0}

    # best readout alpha vs its random control
    best = max(alphas, key=lambda a: results[f"alpha_{a}"]["wrong_to_correct_plus_readout"] or 0)
    r = results[f"alpha_{best}"]
    gain_over_random = (r["wrong_to_correct_plus_readout"] or 0) - (r["wrong_to_correct_random"] or 0)
    behavioral_gain = (r["wrong_to_correct_plus_readout"] or 0)  # vs 0 baseline

    out = {
        "schema": "eta_epsilon_weight_learning.phase3_activation_bridge.v0.1",
        "status": "V0_2_generic_activation_steering",
        "layer": LAYER, "mean_hidden_norm": hnorm,
        "baseline": baseline, "by_alpha": results,
        "best_alpha": best,
        "behavioral_gain_wrong_to_correct": behavioral_gain,
        "gain_over_random_control": gain_over_random,
        "prereg_behavioral_gain_min_pp": 0.10,
        "kill_rule_tripped": behavioral_gain < 0.10 or gain_over_random <= 0,
        "verdict": ("STEERING_IMPROVES_BEHAVIOR" if
                    (behavioral_gain >= 0.10 and gain_over_random > 0)
                    else "READOUT_STEERING_WITHOUT_BEHAVIORAL_GAIN"),
        "honest_note": "generic (B1); activation-only; no weight change.",
    }
    p = os.path.join(os.path.dirname(HERE), "reports",
                     "phase3_activation_bridge.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=2)
    print(json.dumps({k: out[k] for k in
          ("baseline", "best_alpha", "behavioral_gain_wrong_to_correct",
           "gain_over_random_control", "kill_rule_tripped", "verdict")},
          indent=2, default=str))
    print("by_alpha:", json.dumps(results, indent=2, default=str))
    print("saved", p)


if __name__ == "__main__":
    main()
