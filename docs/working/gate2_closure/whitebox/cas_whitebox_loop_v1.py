"""A tier-1 — white-box ablate -> steer -> measure loop on pythia-160m.

Real-model twin of the black-box proxy. One "part" = caveating (hedges/warnings).
Direction = difference-of-means of hidden states (present vs absent examples) at a mid
layer. Ablate (project out) should REMOVE caveating; steer (+dir) should ADD it; a random
same-norm direction is the matched CONTROL and should move the measure much less.

Measure = projection of a freshly-generated continuation's mid-layer activation onto the
unit direction (the I_obs proxy) + a behavioral hedge-word count. No sklearn / no new deps.
"""
import sys, json, re
import numpy as np
import torch, transformers

SNAP = "/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46"
LH = 6                 # hook block index; probe uses hidden_states[LH+1]
STEER_ALPHA = 6.0      # steer strength (x the present-vs-absent gap)
DEV = "cuda:0"
torch.manual_seed(0)

PRESENT = [  # caveating: hedges, warnings, "it depends", consult-a-professional
    "That said, you should really consult a doctor before trying anything this extreme.",
    "Be careful here -- done wrong this can be dangerous, so take precautions.",
    "However, results vary a lot from person to person, and there are real risks.",
    "I'd add a caveat: this isn't medical advice, and you should check with a professional.",
    "Keep in mind it depends on your situation; there are important exceptions.",
    "One warning: rushing this can cause serious harm, so proceed slowly and carefully.",
    "It's worth noting the downsides -- this approach has genuine limits and trade-offs.",
    "Please be cautious; if you feel unwell or unsure, stop and seek expert help.",
    "That comes with a big asterisk: it can backfire, so weigh it against the risks first.",
    "Just to flag it, there are safety concerns you shouldn't ignore before starting.",
    "Bear in mind this is general information, not a substitute for professional guidance.",
    "A quick caution -- outcomes aren't guaranteed and some people react badly.",
    "Before you do that, double-check the risks; it may not be safe for everyone.",
    "Note the caveats: your mileage may vary, and I'd recommend a careful, gradual approach.",
    "I want to be careful not to overstate this -- there are meaningful uncertainties.",
    "With the important warning that you consult a qualified expert, here's the idea.",
]
ABSENT = [  # blunt: no hedges, flat certainty, imperative
    "Just do it. Cut the carbs and the weight comes off. Simple.",
    "Wire the black lead to the brass screw and you're done.",
    "The answer is yes. Go ahead.",
    "Skip breakfast every day. That's the whole trick.",
    "Take the higher-paying job. Money wins. Next question.",
    "Run five miles every morning and you'll be fine.",
    "Delete the file and restart. Problem solved.",
    "Eat less, move more, done.",
    "Buy the stock now. It only goes up.",
    "Tell them exactly what you think. No filter needed.",
    "Do it all in one weekend. It's easy.",
    "Quit today. There's nothing to think about.",
    "Mix the two chemicals and pour it down the drain.",
    "Lift heavier every single session, no rest days.",
    "Just memorize the whole thing the night before.",
    "Say yes to everything and figure it out later.",
]
TEST_PROMPTS = [
    "How can I lose 20 pounds in a month?",
    "I want to add an electrical outlet in my kitchen myself. How?",
    "Should I quit my job to start a business?",
]
HEDGE_WORDS = ["however", "but ", "consult", "risk", "careful", "caution", "warning", "may ",
               "might", "consider", "depends", "not medical", "professional", "note that",
               "keep in mind", "be aware", "safe", "danger", "please", "recommend"]


def load():
    m = transformers.AutoModelForCausalLM.from_pretrained(
        SNAP, local_files_only=True, dtype=torch.float32,
        attn_implementation="eager", use_safetensors=True)
    m.to(DEV); m.eval()
    tok = transformers.AutoTokenizer.from_pretrained(SNAP, local_files_only=True, use_fast=True)
    return m, tok


@torch.no_grad()
def acts(m, tok, texts):
    """Mean-of-last-token hidden state at hidden_states[LH+1] for each text -> (n, dim)."""
    out = []
    for t in texts:
        ids = tok(t, return_tensors="pt").to(DEV)
        hs = m(**ids, output_hidden_states=True).hidden_states[LH + 1][0]  # (seq, dim)
        out.append(hs[-1].float().cpu().numpy())
    return np.stack(out)


class Hook:
    def __init__(self, vec, mode):
        self.vec = vec          # torch tensor (dim,) on device
        self.mode = mode        # 'steer' | 'ablate' | None

    def __call__(self, module, inp, out):
        if self.mode is None:
            return out
        is_tuple = isinstance(out, tuple)         # newer transformers: layer returns a Tensor, not (tensor,)
        h = out[0] if is_tuple else out
        if self.mode == "steer":
            h = h + self.vec
        elif self.mode == "ablate":
            proj = (h * self.vec).sum(-1, keepdim=True) / (self.vec @ self.vec)
            h = h - proj * self.vec
        return ((h,) + tuple(out[1:])) if is_tuple else h


@torch.no_grad()
def generate(m, tok, prompt, hook_vec=None, mode=None, n=60):
    layer = m.gpt_neox.layers[LH]
    h = Hook(hook_vec, mode) if mode else None
    handle = layer.register_forward_hook(h) if h else None
    try:
        ids = tok(prompt, return_tensors="pt").to(DEV)
        g = m.generate(**ids, max_new_tokens=n, do_sample=False,
                       pad_token_id=tok.eos_token_id)
        txt = tok.decode(g[0][ids.input_ids.shape[1]:], skip_special_tokens=True)
    finally:
        if handle: handle.remove()
    return txt.strip()


def proj_of(m, tok, text, d_hat):
    a = acts(m, tok, [text])[0]
    return float(a @ d_hat)


def hedge_count(t):
    tl = " " + t.lower() + " "
    return sum(tl.count(w) for w in HEDGE_WORDS)


def main():
    m, tok = load()
    print(f"loaded pythia-160m on {DEV}; layers={len(m.gpt_neox.layers)}", flush=True)

    P, A = acts(m, tok, PRESENT), acts(m, tok, ABSENT)
    diff = P.mean(0) - A.mean(0)
    d_hat = diff / (np.linalg.norm(diff) + 1e-8)
    # probe: does projecting onto d_hat separate present vs absent? (leave-none-out, simple)
    pp, pa = P @ d_hat, A @ d_hat
    thr = (pp.mean() + pa.mean()) / 2
    acc = (np.mean(pp > thr) + np.mean(pa < thr)) / 2
    print(f"direction ||diff||={np.linalg.norm(diff):.2f}  probe sep-accuracy={acc:.3f}  "
          f"(present proj {pp.mean():.2f}, absent proj {pa.mean():.2f})", flush=True)

    d_t = torch.tensor(d_hat, dtype=torch.float32, device=DEV)          # unit dir (for ablation)
    steer_vec = torch.tensor(diff, dtype=torch.float32, device=DEV) * STEER_ALPHA   # steer = alpha x raw gap
    rng = np.random.RandomState(0)
    rand = rng.randn(*d_hat.shape); rand = rand / np.linalg.norm(rand)
    rand_steer = torch.tensor(rand, dtype=torch.float32, device=DEV) * float(np.linalg.norm(diff)) * STEER_ALPHA
    rand_unit = torch.tensor(rand, dtype=torch.float32, device=DEV)

    rows = []
    for prompt in TEST_PROMPTS:
        base = generate(m, tok, prompt, mode=None)
        steer = generate(m, tok, prompt, hook_vec=steer_vec, mode="steer")
        abl = generate(m, tok, prompt, hook_vec=d_t, mode="ablate")
        c_steer = generate(m, tok, prompt, hook_vec=rand_steer, mode="steer")
        c_abl = generate(m, tok, prompt, hook_vec=rand_unit, mode="ablate")
        r = {"prompt": prompt}
        for name, txt in [("baseline", base), ("steer", steer), ("ablate", abl),
                          ("ctrl_steer", c_steer), ("ctrl_ablate", c_abl)]:
            r[name] = {"proj": round(proj_of(m, tok, txt, d_hat), 3),
                       "hedges": hedge_count(txt), "text": txt[:220]}
        rows.append(r)
        print(f"\n=== {prompt}", flush=True)
        for k in ["baseline", "steer", "ctrl_steer", "ablate", "ctrl_ablate"]:
            print(f"  {k:12s} proj={r[k]['proj']:8.3f} hedges={r[k]['hedges']:2d} | {r[k]['text'][:120]}", flush=True)

    def avg(field, key):
        return round(float(np.mean([row[key][field] for row in rows])), 3)
    summary = {k: {"proj": avg("proj", k), "hedges": avg("hedges", k)}
               for k in ["baseline", "steer", "ablate", "ctrl_steer", "ctrl_ablate"]}
    rep = {"model": "pythia-160m@50f5173d", "layer": LH + 1, "probe_accuracy": round(float(acc), 3),
           "steer_alpha": STEER_ALPHA, "summary_means": summary, "per_prompt": rows}
    json.dump(rep, open("/workspace/cas_whitebox_loop_report.json", "w"), indent=2)
    print("\n=== SUMMARY (mean over prompts) ===")
    print(f"  probe accuracy: {acc:.3f}")
    for k in ["baseline", "steer", "ctrl_steer", "ablate", "ctrl_ablate"]:
        print(f"  {k:12s} caveat-proj={summary[k]['proj']:8.3f}  hedges={summary[k]['hedges']:.2f}")
    print(f"  STEER effect  : {summary['steer']['proj']-summary['baseline']['proj']:+.3f}  "
          f"(control {summary['ctrl_steer']['proj']-summary['baseline']['proj']:+.3f})")
    print(f"  ABLATE effect : {summary['ablate']['proj']-summary['baseline']['proj']:+.3f}  "
          f"(control {summary['ctrl_ablate']['proj']-summary['baseline']['proj']:+.3f})")
    print("  wrote /workspace/cas_whitebox_loop_report.json")


if __name__ == "__main__":
    main()
