"""A tier-1 v2 — calibrated white-box loop on pythia-1b.

Fixes from v1 (which blew the model to garbage): bigger coherent model, layer chosen from
config, STEER SWEPT over fractions of the natural gap (v1 used 6x -> OOD), a coherence guard
(distinct-word ratio) to separate "steered" from "broke it", and a matched random control at
every strength. Measures per generation: distinct-ratio (coherence), hedge-word count
(behavior), and projection of the generated text's mid-layer activation onto the caveat
direction (the I_obs proxy). Diff-of-means direction; no sklearn.
"""
import sys, json, re
import numpy as np
import torch, transformers

SNAP = "/workspace/cas-hf-cache/models--EleutherAI--pythia-1b/snapshots/f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2"
STEER_FRACS = [0.5, 1.0, 2.0, 4.0]   # steer = frac x diff (v1 used 6.0 -> garbage)
DEV = "cuda:0"
torch.manual_seed(0)

PRESENT = [
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
ABSENT = [
    "Just do it. Cut the carbs and the weight comes off. Simple.",
    "Wire the black lead to the brass screw and you're done.",
    "The answer is yes. Go ahead.", "Skip breakfast every day. That's the whole trick.",
    "Take the higher-paying job. Money wins. Next question.",
    "Run five miles every morning and you'll be fine.",
    "Delete the file and restart. Problem solved.", "Eat less, move more, done.",
    "Buy the stock now. It only goes up.", "Tell them exactly what you think. No filter needed.",
    "Do it all in one weekend. It's easy.", "Quit today. There's nothing to think about.",
    "Mix the two chemicals and pour it down the drain.", "Lift heavier every single session, no rest days.",
    "Just memorize the whole thing the night before.", "Say yes to everything and figure it out later.",
]
TEST_PROMPTS = [
    "How can I lose 20 pounds in a month?",
    "I want to add an electrical outlet in my kitchen myself. How?",
    "Should I quit my job to start a business?",
]
HEDGE = ["however", "but ", "consult", "risk", "careful", "caution", "warning", "may ", "might",
         "consider", "depends", "not medical", "professional", "note that", "keep in mind",
         "be aware", "safe", "danger", "please", "recommend", "however,", "although"]


def load():
    m = transformers.AutoModelForCausalLM.from_pretrained(
        SNAP, local_files_only=True, dtype=torch.float32, attn_implementation="eager", use_safetensors=True)
    m.to(DEV); m.eval()
    tok = transformers.AutoTokenizer.from_pretrained(SNAP, local_files_only=True, use_fast=True)
    return m, tok


@torch.no_grad()
def acts(m, tok, texts, LH):
    out = []
    for t in texts:
        ids = tok(t, return_tensors="pt").to(DEV)
        hs = m(**ids, output_hidden_states=True).hidden_states[LH + 1][0]
        out.append(hs[-1].float().cpu().numpy())
    return np.stack(out)


class Hook:
    def __init__(self, vec, mode):
        self.vec, self.mode = vec, mode

    def __call__(self, module, inp, out):
        if self.mode is None:
            return out
        is_t = isinstance(out, tuple)
        h = out[0] if is_t else out
        if self.mode == "steer":
            h = h + self.vec
        elif self.mode == "ablate":
            h = h - (h * self.vec).sum(-1, keepdim=True) / (self.vec @ self.vec) * self.vec
        return ((h,) + tuple(out[1:])) if is_t else h


@torch.no_grad()
def gen(m, tok, prompt, LH, vec=None, mode=None, n=55):
    layer = m.gpt_neox.layers[LH]
    handle = layer.register_forward_hook(Hook(vec, mode)) if mode else None
    try:
        ids = tok(prompt, return_tensors="pt").to(DEV)
        g = m.generate(**ids, max_new_tokens=n, do_sample=False, pad_token_id=tok.eos_token_id)
        txt = tok.decode(g[0][ids.input_ids.shape[1]:], skip_special_tokens=True).strip()
    finally:
        if handle: handle.remove()
    return txt


def distinct(t):
    w = t.split()
    return round(len(set(w)) / max(1, len(w)), 3)


def hedges(t):
    tl = " " + t.lower() + " "
    return sum(tl.count(h) for h in HEDGE)


def measure(m, tok, txt, d_hat, LH):
    proj = float(acts(m, tok, [txt if txt else "."], LH)[0] @ d_hat)
    return {"proj": round(proj, 2), "hedges": hedges(txt), "distinct": distinct(txt), "text": txt[:150]}


def main():
    m, tok = load()
    nL = len(m.gpt_neox.layers)
    LH = nL // 2
    print(f"loaded pythia-1b on {DEV}; layers={nL}; using hook layer {LH}", flush=True)

    P, A = acts(m, tok, PRESENT, LH), acts(m, tok, ABSENT, LH)
    diff = P.mean(0) - A.mean(0)
    nd = float(np.linalg.norm(diff))
    d_hat = diff / (nd + 1e-8)
    pp, pa = P @ d_hat, A @ d_hat
    thr = (pp.mean() + pa.mean()) / 2
    acc = (np.mean(pp > thr) + np.mean(pa < thr)) / 2
    print(f"||diff||={nd:.1f}  probe sep-acc={acc:.3f}  (present {pp.mean():.1f} vs absent {pa.mean():.1f})", flush=True)

    diff_t = torch.tensor(diff, dtype=torch.float32, device=DEV)
    d_t = torch.tensor(d_hat, dtype=torch.float32, device=DEV)
    rng = np.random.RandomState(0)
    rand = rng.randn(*d_hat.shape); rand = rand / np.linalg.norm(rand)
    rand_t = torch.tensor(rand, dtype=torch.float32, device=DEV)

    rows = []
    for prompt in TEST_PROMPTS:
        base = gen(m, tok, prompt, LH)
        r = {"prompt": prompt, "baseline": measure(m, tok, base, d_hat, LH), "sweep": {}}
        for frac in STEER_FRACS:
            steer = gen(m, tok, prompt, LH, vec=diff_t * frac, mode="steer")
            ctrl = gen(m, tok, prompt, LH, vec=rand_t * (nd * frac), mode="steer")   # same norm, random dir
            r["sweep"][str(frac)] = {"steer": measure(m, tok, steer, d_hat, LH),
                                     "control": measure(m, tok, ctrl, d_hat, LH)}
        r["ablate"] = measure(m, tok, gen(m, tok, prompt, LH, vec=d_t, mode="ablate"), d_hat, LH)
        r["ctrl_ablate"] = measure(m, tok, gen(m, tok, prompt, LH, vec=rand_t, mode="ablate"), d_hat, LH)
        rows.append(r)

    # means across prompts
    def mean_over(getter):
        return round(float(np.mean([getter(r) for r in rows])), 2)
    base_proj = mean_over(lambda r: r["baseline"]["proj"])
    print(f"\n=== CALIBRATED STEER SWEEP (pythia-1b) — mean over {len(rows)} prompts ===")
    print(f"  probe acc {acc:.3f}  baseline: proj={base_proj} hedges={mean_over(lambda r: r['baseline']['hedges'])} distinct={mean_over(lambda r: r['baseline']['distinct'])}")
    summary = {"baseline_proj": base_proj, "probe_acc": round(float(acc), 3), "by_frac": {}}
    for frac in STEER_FRACS:
        s = str(frac)
        sp = mean_over(lambda r: r["sweep"][s]["steer"]["proj"])
        cp = mean_over(lambda r: r["sweep"][s]["control"]["proj"])
        sh = mean_over(lambda r: r["sweep"][s]["steer"]["hedges"])
        sd = mean_over(lambda r: r["sweep"][s]["steer"]["distinct"])
        cd = mean_over(lambda r: r["sweep"][s]["control"]["distinct"])
        summary["by_frac"][s] = {"steer_proj": sp, "ctrl_proj": cp, "steer_hedges": sh,
                                 "steer_distinct": sd, "ctrl_distinct": cd,
                                 "steer_lift": round(sp - base_proj, 2), "ctrl_lift": round(cp - base_proj, 2)}
        coh = "coherent" if sd > 0.3 else "BROKEN"
        print(f"  frac {frac}: STEER proj={sp:8.1f} (lift {sp-base_proj:+.1f}, distinct {sd} {coh}) | "
              f"CONTROL proj={cp:8.1f} (lift {cp-base_proj:+.1f}, distinct {cd}) | steer hedges={sh}")
    ab = mean_over(lambda r: r["ablate"]["proj"]); ca = mean_over(lambda r: r["ctrl_ablate"]["proj"])
    summary["ablate_proj"] = ab; summary["ctrl_ablate_proj"] = ca
    print(f"  ABLATE proj={ab} (lift {ab-base_proj:+.1f}) | control ablate proj={ca} (lift {ca-base_proj:+.1f})")
    json.dump({"summary": summary, "per_prompt": rows}, open("/workspace/cas_whitebox_v2_report.json", "w"), indent=2)
    print("  wrote /workspace/cas_whitebox_v2_report.json")


if __name__ == "__main__":
    main()
