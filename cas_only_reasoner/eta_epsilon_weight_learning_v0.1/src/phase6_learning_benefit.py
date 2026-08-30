"""Phase 6: learning benefit (claims 4a sample-efficiency, 4c retention).

Teach Qwen 0.5B to answer passive role-binding correctly with a rank-4
LoRA on layer-11 q/v. Two conditions:
  A = ordinary supervised LoRA (LM loss on the agent answer).
  C = readout-guided (LM loss + lambda * BCE pushing the frozen layer-12
      correctness readout toward 1).
Sweep N examples in {4,8,16,32} x seeds. Metric: held-out passive accuracy
-> examples-to-threshold (0.90). Retention: active-voice accuracy after.
Generic (B1); not a CAS-specific claim. Base frozen except the LoRA."""
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
NS = [8, 32]
SEEDS = [0, 1]
STEPS = 50
THRESH = 0.90


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
    tr = [e for e in train if e["voice"] == "passive"]
    te_pass = [e for e in test if e["voice"] == "passive"][:100]
    te_act = [e for e in test if e["voice"] == "active"][:80]

    def chat(e):
        q = (f'In the sentence "{e["text"]}" who performed the action? '
             f'Answer with one word only.')
        return tok.apply_chat_template([{"role": "user", "content": q}],
                                       tokenize=False,
                                       add_generation_prompt=True)

    q_lin = model.model.layers[ADAPT_LAYER].self_attn.q_proj
    v_lin = model.model.layers[ADAPT_LAYER].self_attn.v_proj
    P = {"lora": None}

    def mk(ka, kb):
        def h(mod, inp, out):
            if P["lora"] is None:
                return out
            x = inp[0]
            d = (x @ P["lora"][ka].t()) @ P["lora"][kb].t()
            return out + d.to(out.dtype)
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
        return np.array(r)

    def answers(items):
        return float(correct_vec(items).mean())

    # frozen readout probe (base model)
    def h12(items):
        H = []
        for i in range(0, len(items), 16):
            enc = tok([chat(e) for e in items[i:i + 16]],
                      return_tensors="pt", padding=True).to(dev)
            with torch.no_grad():
                H.append(model(**enc).hidden_states[READ_LAYER][:, -1, :])
        return torch.cat(H)
    P["lora"] = None
    ytr = correct_vec(tr[:150])                       # batched
    w, b, mu, sd = fit_logreg(h12(tr[:150]).float().cpu().numpy(), ytr)
    w = w.to(dev); b = b.to(dev); mu = mu.to(dev); sd = sd.to(dev)

    qin, qout = q_lin.in_features, q_lin.out_features
    vin, vout = v_lin.in_features, v_lin.out_features

    def train_run(examples, guided, seed):
        g = torch.Generator(device=dev).manual_seed(1000 + seed)
        L = {"A_q": (torch.randn(RANK, qin, generator=g, device=dev)*0.01).requires_grad_(True),
             "B_q": torch.zeros(qout, RANK, device=dev).requires_grad_(True),
             "A_v": (torch.randn(RANK, vin, generator=g, device=dev)*0.01).requires_grad_(True),
             "B_v": torch.zeros(vout, RANK, device=dev).requires_grad_(True)}
        P["lora"] = L
        opt = torch.optim.Adam(list(L.values()), lr=5e-3)
        # supervised targets: prompt + " agent"; left-padded, so the
        # agent tokens are the LAST agent_len positions of each row.
        texts = [chat(e) + " " + e["agent"] for e in examples]
        agent_len = [len(tok(" " + e["agent"],
                             add_special_tokens=False)["input_ids"])
                     for e in examples]
        for _ in range(STEPS):
            opt.zero_grad()
            enc = tok(texts, return_tensors="pt", padding=True).to(dev)
            labels = torch.full_like(enc["input_ids"], -100)
            for r in range(labels.shape[0]):
                al = agent_len[r]
                labels[r, -al:] = enc["input_ids"][r, -al:]
            out = model(**enc, labels=labels)
            loss = out.loss
            if guided:
                H = out.hidden_states[READ_LAYER][:, -1, :]
                score = torch.sigmoid(((H - mu) / sd) @ w + b.squeeze())
                loss = loss + 0.5 * torch.nn.functional.binary_cross_entropy(
                    score, torch.ones_like(score))
            loss.backward()
            opt.step()
        pa = answers(te_pass); aa = answers(te_act)
        P["lora"] = None
        return pa, aa

    results = {"A_ordinary": {}, "C_guided": {}}
    for N in NS:
        for cond, guided in (("A_ordinary", False), ("C_guided", True)):
            pas, aas = [], []
            for s in SEEDS:
                rng = np.random.default_rng(20260830 + s)
                ex = [tr[i] for i in rng.choice(len(tr), N, replace=False)]
                pa, aa = train_run(ex, guided, s)
                pas.append(pa); aas.append(aa)
            results[cond][N] = {"passive_acc_mean": float(np.mean(pas)),
                                "passive_acc_seeds": pas,
                                "active_acc_mean": float(np.mean(aas))}

    def ex_to_thresh(cond):
        for N in NS:
            if results[cond][N]["passive_acc_mean"] >= THRESH:
                return N
        return None
    a_thr = ex_to_thresh("A_ordinary"); c_thr = ex_to_thresh("C_guided")
    out = {
        "schema": "eta_epsilon_weight_learning.phase6_learning_benefit.v0.1",
        "status": "V0_2_generic_learning_benefit", "steps": STEPS,
        "threshold": THRESH, "N_sweep": NS, "seeds": SEEDS,
        "results": results,
        "examples_to_threshold": {"A_ordinary": a_thr, "C_guided": c_thr},
        "4a_sample_efficiency": (
            "C_better" if (c_thr and (a_thr is None or c_thr < a_thr))
            else "no_advantage"),
        "retention_active_acc_at_maxN": {
            "A": results["A_ordinary"][NS[-1]]["active_acc_mean"],
            "C": results["C_guided"][NS[-1]]["active_acc_mean"]},
        "honest_note": "generic (B1); small sweep; not CAS-specific.",
    }
    p = os.path.join(os.path.dirname(HERE), "reports", "phase6_learning_benefit.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=2)
    print(json.dumps({"examples_to_threshold": out["examples_to_threshold"],
                      "4a": out["4a_sample_efficiency"],
                      "retention": out["retention_active_acc_at_maxN"]}, indent=2))
    for N in NS:
        print(f"N={N:2d}  A pass={results['A_ordinary'][N]['passive_acc_mean']:.3f} "
              f"act={results['A_ordinary'][N]['active_acc_mean']:.3f}  |  "
              f"C pass={results['C_guided'][N]['passive_acc_mean']:.3f} "
              f"act={results['C_guided'][N]['active_acc_mean']:.3f}")
    print("saved", p)


if __name__ == "__main__":
    main()
