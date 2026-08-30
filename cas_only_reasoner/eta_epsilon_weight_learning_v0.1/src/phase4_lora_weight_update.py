"""Phase 4: readout-guided low-rank WEIGHT update (eta-hat at the weight
level). A rank-4 LoRA on layer-11 q_proj+v_proj. The update direction is
the gradient of the layer-12 readout (correctness) score w.r.t. the LoRA
parameters - the scalar right-inverse / eta-hat direction. One step.

Measure BEHAVIOR (exact role binding via generation): flip rate on wrong
passives, collateral on right passives. Compare to a RANDOM-basis LoRA of
matched effective ||dW||_F. No CAS-specific claim (B1). Base model frozen
except the small LoRA delta."""
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
READ_LAYER = 12       # readout at hidden_states[12]
ADAPT_LAYER = 11      # LoRA on layers[11] (feeds hidden_states[12])
RANK = 4


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
    for p in model.parameters():
        p.requires_grad_(False)

    train, test = data_gen.generate()
    tr = [e for e in train if e["voice"] == "passive"]
    te = [e for e in test if e["voice"] == "passive"]

    def chat(e):
        q = (f'In the sentence "{e["text"]}" who performed the action? '
             f'Answer with one word only.')
        return tok.apply_chat_template([{"role": "user", "content": q}],
                                       tokenize=False,
                                       add_generation_prompt=True)

    # LoRA params on layer-11 q_proj and v_proj
    q_lin = model.model.layers[ADAPT_LAYER].self_attn.q_proj
    v_lin = model.model.layers[ADAPT_LAYER].self_attn.v_proj
    qin, qout = q_lin.in_features, q_lin.out_features
    vin, vout = v_lin.in_features, v_lin.out_features
    g = torch.Generator(device=dev).manual_seed(271828)

    def new_lora():
        A_q = (torch.randn(RANK, qin, generator=g, device=dev) * 0.01).float()
        B_q = torch.zeros(qout, RANK, device=dev).float()
        A_v = (torch.randn(RANK, vin, generator=g, device=dev) * 0.01).float()
        B_v = torch.zeros(vout, RANK, device=dev).float()
        for t in (A_q, B_q, A_v, B_v):
            t.requires_grad_(True)
        return {"A_q": A_q, "B_q": B_q, "A_v": A_v, "B_v": B_v}

    P = {"lora": None}

    def hq(mod, inp, out):
        if P["lora"] is None:
            return out
        x = inp[0].float()
        d = (x @ P["lora"]["A_q"].t()) @ P["lora"]["B_q"].t()
        return out + d.to(out.dtype)

    def hv(mod, inp, out):
        if P["lora"] is None:
            return out
        x = inp[0].float()
        d = (x @ P["lora"]["A_v"].t()) @ P["lora"]["B_v"].t()
        return out + d.to(out.dtype)
    q_lin.register_forward_hook(hq)
    v_lin.register_forward_hook(hv)

    def hidden12(items, grad=False):
        H = []
        bs = 16
        ctx = torch.enable_grad() if grad else torch.no_grad()
        for i in range(0, len(items), bs):
            enc = tok([chat(e) for e in items[i:i + bs]],
                      return_tensors="pt", padding=True).to(dev)
            with ctx:
                fwd = model(**enc)
                H.append(fwd.hidden_states[READ_LAYER][:, -1, :])
        return torch.cat(H) if grad else torch.cat(H).float().cpu().numpy()

    def answers(items):
        res = []
        bs = 32
        for i in range(0, len(items), bs):
            batch = items[i:i + bs]
            enc = tok([chat(e) for e in batch], return_tensors="pt",
                      padding=True).to(dev)
            with torch.no_grad():
                out = model.generate(**enc, max_new_tokens=8,
                                     do_sample=False,
                                     pad_token_id=tok.pad_token_id)
            gen = out[:, enc["input_ids"].shape[1]:]
            for j, e in enumerate(batch):
                a = tok.decode(gen[j], skip_special_tokens=True).lower()
                w = a.replace(".", " ").replace(",", " ").split()
                pa = next((k for k, x in enumerate(w) if x == e["agent"]), 1e9)
                pp = next((k for k, x in enumerate(w) if x == e["patient"]), 1e9)
                res.append(1 if pa < pp else 0)
        return np.array(res)

    # frozen readout probe (fit on train passives, no LoRA)
    P["lora"] = None
    ytr = answers(tr)
    w, b, mu, sd = fit_logreg(hidden12(tr), ytr)
    w = w.to(dev); b = b.to(dev); mu = mu.to(dev); sd = sd.to(dev)

    yte0 = answers(te)
    wrong = [te[i] for i in range(len(te)) if yte0[i] == 0]
    right = [te[i] for i in range(len(te)) if yte0[i] == 1]

    def readout_score(items):
        H = hidden12(items, grad=True)
        z = (H - mu) / sd
        return torch.sigmoid(z @ w + b.squeeze()).mean()

    def dW_fro(lora):
        dq = (lora["B_q"] @ lora["A_q"]).detach()
        dv = (lora["B_v"] @ lora["A_v"]).detach()
        return float((dq.norm() ** 2 + dv.norm() ** 2).sqrt())

    # ONE readout-gradient step (eta-hat direction), on a subset of wrong
    lora = new_lora()
    P["lora"] = lora
    subset = wrong[:96]
    score = readout_score(subset)
    grads = torch.autograd.grad(score, [lora["A_q"], lora["B_q"],
                                        lora["A_v"], lora["B_v"]])
    LR = 0.5
    guided = {}
    with torch.no_grad():
        for (k, t), gr in zip(lora.items(), grads):
            guided[k] = (t + LR * gr / (gr.norm() + 1e-8)).detach()
    P["lora"] = {k: v.requires_grad_(False) for k, v in guided.items()}
    guided_dW = dW_fro(P["lora"])
    guided_wrong = float(answers(wrong).mean())
    guided_right = float(answers(right).mean())

    # RANDOM-basis LoRA matched to guided_dW
    rl = new_lora()
    with torch.no_grad():
        rl["B_q"] = torch.randn(qout, RANK, generator=g, device=dev).float()
        rl["B_v"] = torch.randn(vout, RANK, generator=g, device=dev).float()
    scale = guided_dW / (dW_fro(rl) + 1e-8)
    rl = {k: (v * scale if k.startswith("B_") else v).detach()
          for k, v in rl.items()}
    P["lora"] = rl
    rand_dW = dW_fro(rl)
    rand_wrong = float(answers(wrong).mean())
    rand_right = float(answers(right).mean())

    out = {
        "schema": "eta_epsilon_weight_learning.phase4_lora_weight_update.v0.1",
        "status": "V0_2_generic_weight_update", "adapt_layer": ADAPT_LAYER,
        "read_layer": READ_LAYER, "rank": RANK,
        "wrong_set": len(wrong), "right_set": len(right),
        "guided": {"dW_fro": guided_dW, "wrong_to_correct": guided_wrong,
                   "right_still_correct": guided_right,
                   "collateral_pp": round((1 - guided_right) * 100, 2)},
        "random_basis": {"dW_fro": rand_dW, "wrong_to_correct": rand_wrong,
                         "right_still_correct": rand_right,
                         "collateral_pp": round((1 - rand_right) * 100, 2)},
        "guided_minus_random_flip": guided_wrong - rand_wrong,
        "prereg": {"behavioral_gain_min_pp": 10, "collateral_max_pp": 2},
        "beats_random": guided_wrong - rand_wrong > 0,
        "behavioral_gain_ok": guided_wrong >= 0.10,
        "collateral_ok": (1 - guided_right) <= 0.02,
        "honest_note": "generic (B1); readout-gradient = scalar eta-hat step; base frozen except LoRA.",
    }
    p = os.path.join(os.path.dirname(HERE), "reports",
                     "phase4_lora_weight_update.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=2)
    print(json.dumps({k: out[k] for k in
          ("guided", "random_basis", "guided_minus_random_flip",
           "beats_random", "behavioral_gain_ok", "collateral_ok")},
          indent=2, default=str))
    print("saved", p)


if __name__ == "__main__":
    main()
