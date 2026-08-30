"""Phase 5: CAS-Ohm dose calibration. dose a = ||dW||_F; response y =
mean movement of the layer-12 readout along its unit direction d.

Fit the proportional model y_hat = a/r_eff = beta*a on the CALIBRATION
item split; evaluate on a DISJOINT held-out item split. Compare to
zero-response, mean-response, affine (beta*a + c), and local quadratic
(beta*a + gamma*a^2). Per the CAS-Ohm paper (read first-hand): y_hat =
a/r_eff is admissible only with disjoint-split evaluation; the same-sample
r=a/y identity is circular and is NOT used. The proportional model is
algebraically zero-intercept linear, so it is NOT raced against
zero-intercept linear (that would be counterfeit). Generic (B1)."""
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
READ_LAYER, ADAPT_LAYER, RANK = 12, 11, 4
DOSES = [0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2]


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
    cal = te[:120]
    ho = te[120:240]

    def chat(e):
        q = (f'In the sentence "{e["text"]}" who performed the action? '
             f'Answer with one word only.')
        return tok.apply_chat_template([{"role": "user", "content": q}],
                                       tokenize=False,
                                       add_generation_prompt=True)

    q_lin = model.model.layers[ADAPT_LAYER].self_attn.q_proj
    v_lin = model.model.layers[ADAPT_LAYER].self_attn.v_proj
    P = {"lora": None}

    def mkhook(key_a, key_b):
        def h(mod, inp, out):
            if P["lora"] is None:
                return out
            x = inp[0].float()
            d = (x @ P["lora"][key_a].t()) @ P["lora"][key_b].t()
            return out + d.to(out.dtype)
        return h
    q_lin.register_forward_hook(mkhook("A_q", "B_q"))
    v_lin.register_forward_hook(mkhook("A_v", "B_v"))

    def h12(items, grad=False):
        H = []
        ctx = torch.enable_grad() if grad else torch.no_grad()
        for i in range(0, len(items), 16):
            enc = tok([chat(e) for e in items[i:i + 16]],
                      return_tensors="pt", padding=True).to(dev)
            with ctx:
                H.append(model(**enc).hidden_states[READ_LAYER][:, -1, :])
        return torch.cat(H)

    def answers(items):
        r = []
        for i in range(0, len(items), 32):
            batch = items[i:i + 32]
            enc = tok([chat(e) for e in batch], return_tensors="pt",
                      padding=True).to(dev)
            with torch.no_grad():
                o = model.generate(**enc, max_new_tokens=8, do_sample=False,
                                   pad_token_id=tok.pad_token_id)
            g = o[:, enc["input_ids"].shape[1]:]
            for j, e in enumerate(batch):
                a = tok.decode(g[j], skip_special_tokens=True).lower()
                w = a.replace(".", " ").replace(",", " ").split()
                pa = next((k for k, x in enumerate(w) if x == e["agent"]), 1e9)
                pp = next((k for k, x in enumerate(w) if x == e["patient"]), 1e9)
                r.append(1 if pa < pp else 0)
        return np.array(r)

    # readout direction d_unit (layer 12) and guided LoRA direction
    P["lora"] = None
    ytr = answers(tr)
    w, b, mu, sd = fit_logreg(h12(tr).float().cpu().numpy(), ytr)
    w = w.to(dev); mu = mu.to(dev); sd = sd.to(dev)
    d = (w / sd.squeeze()); d_unit = (d / d.norm()).to(dev)

    qin, qout = q_lin.in_features, q_lin.out_features
    vin, vout = v_lin.in_features, v_lin.out_features
    g = torch.Generator(device=dev).manual_seed(271828)
    lora = {"A_q": (torch.randn(RANK, qin, generator=g, device=dev)*0.01).float().requires_grad_(True),
            "B_q": torch.zeros(qout, RANK, device=dev).float().requires_grad_(True),
            "A_v": (torch.randn(RANK, vin, generator=g, device=dev)*0.01).float().requires_grad_(True),
            "B_v": torch.zeros(vout, RANK, device=dev).float().requires_grad_(True)}
    P["lora"] = lora
    Hc = h12(cal[:96], grad=True)
    score = torch.sigmoid(((Hc - mu) / sd) @ w + b.to(dev).squeeze()).mean()
    grads = torch.autograd.grad(score, [lora["A_q"], lora["B_q"], lora["A_v"], lora["B_v"]])
    LR0 = 0.5
    guided = {}
    with torch.no_grad():
        for (k, t), gr in zip(lora.items(), grads):
            guided[k] = (t + LR0 * gr / (gr.norm() + 1e-8)).detach()
    direction = guided  # nonzero A (from init) AND B (from step) -> dW != 0

    def dW_fro(L):
        return float((((L["B_q"] @ L["A_q"]).norm()**2
                       + (L["B_v"] @ L["A_v"]).norm()**2)).sqrt())

    # baseline h12 (no lora)
    P["lora"] = None
    base_c = (h12(cal).float() @ d_unit.float()).cpu().numpy()
    base_h = (h12(ho).float() @ d_unit.float()).cpu().numpy()

    def response(items, base_proj, target_dW):
        # scale the guided direction so that ||dW||_F ~= target_dW
        L = {k: v.clone() for k, v in direction.items()}
        cur = dW_fro(L)
        s = target_dW / (cur + 1e-8)
        L = {k: (v * s if k.startswith("B_") else v) for k, v in L.items()}
        P["lora"] = L
        proj = (h12(items).float() @ d_unit.float()).cpu().numpy()
        P["lora"] = None
        return float((proj - base_proj).mean()), dW_fro(L)

    cal_pts, ho_pts = [], []
    for tgt in DOSES:
        yc, a_real = response(cal, base_c, tgt)
        yh, _ = response(ho, base_h, tgt)
        cal_pts.append((a_real, yc)); ho_pts.append((a_real, yh))
    a_cal = np.array([p[0] for p in cal_pts]); y_cal = np.array([p[1] for p in cal_pts])
    a_ho = np.array([p[0] for p in ho_pts]); y_ho = np.array([p[1] for p in ho_pts])

    # fits on calibration
    beta = float((a_cal @ y_cal) / (a_cal @ a_cal))            # proportional
    A2 = np.vstack([a_cal, np.ones_like(a_cal)]).T
    aff = np.linalg.lstsq(A2, y_cal, rcond=None)[0]             # affine
    A3 = np.vstack([a_cal, a_cal**2]).T
    quad = np.linalg.lstsq(A3, y_cal, rcond=None)[0]           # quadratic (no intercept)

    def rmse(p, t):
        return float(np.sqrt(np.mean((p - t)**2)))
    prop_rmse = rmse(beta*a_ho, y_ho)
    aff_rmse = rmse(aff[0]*a_ho + aff[1], y_ho)
    quad_rmse = rmse(quad[0]*a_ho + quad[1]*a_ho**2, y_ho)
    zero_rmse = rmse(np.zeros_like(y_ho), y_ho)
    mean_rmse = rmse(np.full_like(y_ho, y_cal.mean()), y_ho)
    yspan = float(np.ptp(y_ho)) or 1.0
    best_flex = min(aff_rmse, quad_rmse)
    out = {
        "schema": "eta_epsilon_weight_learning.phase5_cas_ohm_dose.v0.1",
        "status": "V0_2_generic_dose_calibration",
        "doses_targeted": DOSES, "dose_actual_cal": a_cal.tolist(),
        "response_cal": y_cal.tolist(), "response_ho": y_ho.tolist(),
        "r_eff": (1.0/beta if beta else None), "beta": beta,
        "holdout_rmse": {"proportional": prop_rmse, "affine": aff_rmse,
                         "quadratic": quad_rmse, "zero": zero_rmse,
                         "mean": mean_rmse},
        "holdout_nrmse_proportional": prop_rmse / yspan,
        "beats_zero_and_mean": prop_rmse < zero_rmse and prop_rmse < mean_rmse,
        "within_5pct_of_flexible": prop_rmse <= 1.05 * best_flex,
        "prereg_nrmse_max": 0.20,
        "dose_claim_supported": (prop_rmse < zero_rmse and prop_rmse < mean_rmse
                                 and prop_rmse <= 1.05*best_flex
                                 and prop_rmse/yspan <= 0.20),
        "honest_note": "proportional vs flexible tells if response saturates; not CAS-specific (B1).",
    }
    p = os.path.join(os.path.dirname(HERE), "reports", "phase5_cas_ohm_dose.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=2)
    print(json.dumps({k: out[k] for k in ("beta", "r_eff", "holdout_rmse",
          "holdout_nrmse_proportional", "beats_zero_and_mean",
          "within_5pct_of_flexible", "dose_claim_supported")}, indent=2, default=str))
    print("dose(actual) vs response_ho:",
          list(zip([round(x,3) for x in a_cal], [round(x,4) for x in y_ho])))
    print("saved", p)


if __name__ == "__main__":
    main()
