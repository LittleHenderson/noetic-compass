"""Semantic-entropy companion to the KWIK hidden-state capture (batched, aligned).

For the SAME closed-book questions whose pre-answer hidden states are already captured in
an npz, sample K answers each and compute DISCRETE semantic entropy (normalize -> cluster by
exact normalized match -> Shannon entropy over cluster probabilities; the documented cheap
proxy for NLI-clustered semantic entropy). Saves SE features aligned ROW-FOR-ROW to the npz
question order so they can be coupled with the hidden-state probe. REAL numbers only.
"""
import sys, json, argparse, re, string, math
import numpy as np, torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ap = argparse.ArgumentParser()
ap.add_argument("--model-id", default="Qwen/Qwen2.5-14B-Instruct")
ap.add_argument("--npz", default="/root/kwik_14b.npz")     # source of aligned question order
ap.add_argument("--n", type=int, default=2000)
ap.add_argument("--k", type=int, default=10)
ap.add_argument("--batch", type=int, default=16)
ap.add_argument("--max-new", type=int, default=24)
ap.add_argument("--temp", type=float, default=1.0)
ap.add_argument("--out", default="/root/kwik_14b_se.npz")
args = ap.parse_args()
torch.manual_seed(0); np.random.seed(0)
device = "cuda" if torch.cuda.is_available() else "cpu"

ARTICLES = re.compile(r"\b(a|an|the)\b"); PUNCT = set(string.punctuation)
def norm(s):
    s = s.lower(); s = ARTICLES.sub(" ", s)
    s = "".join(ch for ch in s if ch not in PUNCT)
    return re.sub(r"\s+", " ", s).strip()

d = np.load(args.npz, allow_pickle=True)
questions = d['question'].astype(str)[:args.n]
N = len(questions)
print(f"[se] questions={N} model={args.model_id} K={args.k} batch={args.batch}", flush=True)

tok = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
if tok.pad_token_id is None and tok.eos_token_id is not None:
    tok.pad_token = tok.eos_token
tok.padding_side = "left"
model = AutoModelForCausalLM.from_pretrained(
    args.model_id, dtype=torch.bfloat16, attn_implementation="eager",
    trust_remote_code=True, low_cpu_mem_usage=True).to(device).eval()

def build_prompt(q):
    msgs = [{"role": "user", "content":
             f"Answer the trivia question with only the answer, as briefly as possible.\n\nQuestion: {q}\nAnswer:"}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

se_ent=np.zeros(N); se_nc=np.zeros(N); se_top=np.zeros(N); se_uniq=np.zeros(N)
all_samples=[]
with torch.no_grad():
    for b0 in range(0, N, args.batch):
        chunk = list(range(b0, min(b0+args.batch, N)))
        prompts = [build_prompt(questions[i]) for i in chunk]
        enc = tok(prompts, return_tensors="pt", padding=True).to(device)
        gen = model.generate(**enc, max_new_tokens=args.max_new, do_sample=True,
                             temperature=args.temp, top_p=0.9, num_return_sequences=args.k,
                             pad_token_id=tok.eos_token_id)
        gen = gen[:, enc["input_ids"].shape[1]:]
        texts = tok.batch_decode(gen, skip_special_tokens=True)   # len = len(chunk)*K, grouped per prompt
        for j, i in enumerate(chunk):
            samples = texts[j*args.k:(j+1)*args.k]
            clusters = {}
            for s in samples:
                key = norm(s) or "<empty>"
                clusters[key] = clusters.get(key, 0) + 1
            tot = sum(clusters.values())
            ps = [c/tot for c in clusters.values()]
            ent = -sum(p*math.log(p) for p in ps)            # nats
            se_ent[i] = ent; se_nc[i] = len(clusters)
            se_top[i] = max(ps); se_uniq[i] = len(clusters)/tot
            all_samples.append({"q": questions[i], "samples": samples,
                                "entropy": ent, "nclusters": len(clusters)})
        if (b0//args.batch) % 5 == 0:
            print(f"[se] {min(b0+args.batch,N)}/{N} mean_ent={se_ent[:min(b0+args.batch,N)].mean():.3f}", flush=True)

np.savez_compressed(args.out, se_entropy=se_ent, se_nclusters=se_nc, se_top_frac=se_top,
                    se_uniq_frac=se_uniq, n=N, model_id=args.model_id)
with open(args.out.replace(".npz","_samples.jsonl"), "w") as f:
    for r in all_samples: f.write(json.dumps(r)+"\n")
print(f"[se] SAVED {args.out}  mean_entropy={se_ent.mean():.3f} mean_clusters={se_nc.mean():.2f}", flush=True)
