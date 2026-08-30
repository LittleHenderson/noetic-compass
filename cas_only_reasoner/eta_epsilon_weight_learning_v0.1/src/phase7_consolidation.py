"""Phase 7: selective consolidation vs catastrophic forgetting.

Phase 6 showed LoRA training on passives destroys active voice. Test
whether consolidation recovers a better stability-plasticity balance:
  FORGET  : guided LoRA, passives only (reproduces the forgetting).
  REPLAY  : guided LoRA, passives + equal actives interleaved.
  EWC     : guided LoRA, passives only + L2 penalty on the LoRA params.
Measure held-out PASSIVE (new skill) and ACTIVE (old skill) accuracy.
Success = a condition that keeps active high AND still learns passive.
Generic (B1); base frozen except the LoRA."""
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
N, STEPS, SEEDS = 16, 50, [0, 1]


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, revision=REVISION, dtype=torch.float32,
        output_hidden_states=True).to(dev).eval()
    for p in model.parameters():
        p.requires_grad_(False)

    train, test = data_gen.generate()
    tr_p = [e for e in train if e["voice"] == "passive"]
    tr_a = [e for e in train if e["voice"] == "active"]
    te_p = [e for e in test if e["voice"] == "passive"][:100]
    te_a = [e for e in test if e["voice"] == "active"][:80]

    def chat(e):
        q = (f'In the sentence "{e["text"]}" who performed the action? '
             f'Answer with one word only.')
        return tok.apply_chat_template([{"role": "user", "content": q}],
                                       tokenize=False, add_generation_prompt=True)

    q_lin = model.model.layers[ADAPT_LAYER].self_attn.q_proj
    v_lin = model.model.layers[ADAPT_LAYER].self_attn.v_proj
    P = {"lora": None}

    def mk(ka, kb):
        def h(mod, inp, out):
            if P["lora"] is None:
                return out
            x = inp[0]
            return out + ((x @ P["lora"][ka].t()) @ P["lora"][kb].t()).to(out.dtype)
        return h
    q_lin.register_forward_hook(mk("A_q", "B_q"))
    v_lin.register_forward_hook(mk("A_v", "B_v"))

    def correct_vec(items):
        r = []
        for i in range(0, len(items), 32):
            batch = items[i:i + 32]
            enc = tok([chat(e) for e in batch], return_tensors="pt",
                      padding=True).to(dev)
            with torch.no_grad():
                o = model.generate(**enc, max_new_tokens=6, do_sample=False,
                                   pad_token_id=tok.pad_token_id)
            g = o[:, enc["input_ids"].shape[1]:]
            for j, e in enumerate(batch):
                a = tok.decode(g[j], skip_special_tokens=True).lower()
                w = a.replace(".", " ").replace(",", " ").split()
                pa = next((k for k, x in enumerate(w) if x == e["agent"]), 1e9)
                pp = next((k for k, x in enumerate(w) if x == e["patient"]), 1e9)
                r.append(1 if pa < pp else 0)
        return float(np.mean(r))

    def h12(items):
        H = []
        for i in range(0, len(items), 16):
            enc = tok([chat(e) for e in items[i:i + 16]],
                      return_tensors="pt", padding=True).to(dev)
            with torch.no_grad():
                H.append(model(**enc).hidden_states[READ_LAYER][:, -1, :])
        return torch.cat(H)

    P["lora"] = None
    ytr = np.array([1 if correct_vec([e]) > 0.5 else 0 for e in tr_p[:120]])
    w, b, mu, sd = fit_logreg(h12(tr_p[:120]).float().cpu().numpy(), ytr)
    w = w.to(dev); b = b.to(dev); mu = mu.to(dev); sd = sd.to(dev)
    qin, qout = q_lin.in_features, q_lin.out_features
    vin, vout = v_lin.in_features, v_lin.out_features

    def run(mode, seed):
        g = torch.Generator(device=dev).manual_seed(1000 + seed)
        L = {"A_q": (torch.randn(RANK, qin, generator=g, device=dev)*0.01).requires_grad_(True),
             "B_q": torch.zeros(qout, RANK, device=dev).requires_grad_(True),
             "A_v": (torch.randn(RANK, vin, generator=g, device=dev)*0.01).requires_grad_(True),
             "B_v": torch.zeros(vout, RANK, device=dev).requires_grad_(True)}
        P["lora"] = L
        opt = torch.optim.Adam(list(L.values()), lr=5e-3)
        rng = np.random.default_rng(20260830 + seed)
        ex = [tr_p[i] for i in rng.choice(len(tr_p), N, replace=False)]
        if mode == "REPLAY":
            ex = ex + [tr_a[i] for i in rng.choice(len(tr_a), N, replace=False)]
        texts = [chat(e) + " " + e["agent"] for e in ex]
        alen = [len(tok(" " + e["agent"], add_special_tokens=False)["input_ids"]) for e in ex]
        for _ in range(STEPS):
            opt.zero_grad()
            enc = tok(texts, return_tensors="pt", padding=True).to(dev)
            labels = torch.full_like(enc["input_ids"], -100)
            for r in range(labels.shape[0]):
                labels[r, -alen[r]:] = enc["input_ids"][r, -alen[r]:]
            out = model(**enc, labels=labels)
            loss = out.loss
            H = out.hidden_states[READ_LAYER][:, -1, :]
            sc = torch.sigmoid(((H - mu) / sd) @ w + b.squeeze())
            loss = loss + 0.5 * torch.nn.functional.binary_cross_entropy(
                sc, torch.ones_like(sc))
            if mode == "EWC":
                loss = loss + 2.0 * sum((t ** 2).sum() for t in L.values())
            loss.backward()
            opt.step()
        pa, aa = correct_vec(te_p), correct_vec(te_a)
        P["lora"] = None
        return pa, aa

    res = {}
    for mode in ("FORGET", "REPLAY", "EWC"):
        pas, aas = [], []
        for s in SEEDS:
            pa, aa = run(mode, s)
            pas.append(pa); aas.append(aa)
        res[mode] = {"passive": float(np.mean(pas)), "active": float(np.mean(aas))}

    base_active = 0.9933  # from capacity probe
    def balance(m):  # keep active high AND learn passive
        r = res[m]
        return (r["passive"] >= 0.85 and r["active"] >= base_active - 0.05)
    winner = next((m for m in ("REPLAY", "EWC") if balance(m)), None)
    out = {
        "schema": "eta_epsilon_weight_learning.phase7_consolidation.v0.1",
        "status": "V0_2_generic_consolidation", "N": N, "steps": STEPS,
        "baseline_active": base_active, "results": res,
        "stability_plasticity_winner": winner,
        "forgetting_fixed": winner is not None,
        "honest_note": "generic (B1); small sweep; REPLAY = interleave old-skill examples.",
    }
    p = os.path.join(os.path.dirname(HERE), "reports", "phase7_consolidation.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=2)
    for m in ("FORGET", "REPLAY", "EWC"):
        print(f"{m:7s}  passive={res[m]['passive']:.3f}  active={res[m]['active']:.3f}")
    print("winner:", winner, "| forgetting_fixed:", winner is not None)
    print("saved", p)


if __name__ == "__main__":
    main()
