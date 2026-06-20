"""Closed-book "knows-what-it-knows" (KWIK) capture for the hallucination license gate.

Pre-answer probe: for diverse factual trivia, capture the model's hidden state at the
LAST prompt token (W0 / pre-answer — before any answer token is emitted), then greedy-
decode the model's own answer and label it correct/incorrect by TriviaQA alias matching.

Detection target = the model is ABOUT TO get it wrong (hallucinate), readable from the
internal state alone. Whether a model knows a given fact is a property of its parametric
state, NOT the question's surface words — so a text control (TF-IDF on the question) should
be near chance, which is the only setting where hidden-state signal can honestly clear the
+0.15 license margin. REAL numbers only; no fabrication.
"""
import sys, json, argparse, re, string
import numpy as np, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset

ap = argparse.ArgumentParser()
ap.add_argument("--model-id", default="Qwen/Qwen2.5-1.5B-Instruct")
ap.add_argument("--n", type=int, default=2500)
ap.add_argument("--max-new", type=int, default=24)
ap.add_argument("--out", default="/root/kwik_15b.npz")
ap.add_argument("--gen-out", default="/root/kwik_15b_gens.jsonl")
ap.add_argument("--device-map", default="", help="'auto' to shard a large model across GPUs")
ap.add_argument("--load-8bit", action="store_true", help="bitsandbytes int8 (near-bf16 hidden states, ~half VRAM)")
ap.add_argument("--load-4bit", action="store_true", help="bitsandbytes nf4 (more lossy)")
ap.add_argument("--prequantized", action="store_true", help="model is already AWQ/GPTQ quantized; load as-is")
args = ap.parse_args()
torch.manual_seed(0); np.random.seed(0)
device = "cuda" if torch.cuda.is_available() else "cpu"

ARTICLES = re.compile(r"\b(a|an|the)\b")
PUNCT = set(string.punctuation)
def normalize_answer(s):
    s = s.lower()
    s = ARTICLES.sub(" ", s)
    s = "".join(ch for ch in s if ch not in PUNCT)
    return re.sub(r"\s+", " ", s).strip()

WH = {"who","what","when","where","which","why","how","whom","whose","name","in","on"}
def qtype(q):
    for t in q.strip().lower().split()[:3]:
        t = t.strip(string.punctuation)
        if t in WH:
            return t
    return "other"

print(f"[cap] loading TriviaQA rc.nocontext validation ...", flush=True)
ds = load_dataset("mandarjoshi/trivia_qa", "rc.nocontext", split="validation")
rows = []
for ex in ds:
    al = ex["answer"].get("normalized_aliases") or []
    nv = ex["answer"].get("normalized_value") or ""
    al = [a for a in (al + [nv]) if a and len(a.strip()) >= 2]
    al = sorted(set(al))
    if not al:
        continue
    rows.append({"q": ex["question"], "aliases": al, "value": ex["answer"].get("value","")})
    if len(rows) >= args.n:
        break
print(f"[cap] questions={len(rows)} model={args.model_id}", flush=True)

tok = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
if tok.pad_token_id is None and tok.eos_token_id is not None:
    tok.pad_token = tok.eos_token
load_kw = dict(attn_implementation="eager", trust_remote_code=True, low_cpu_mem_usage=True)
quantized = args.load_8bit or args.load_4bit or args.prequantized
if args.load_8bit or args.load_4bit:
    from transformers import BitsAndBytesConfig
    load_kw["quantization_config"] = BitsAndBytesConfig(
        load_in_8bit=args.load_8bit, load_in_4bit=args.load_4bit,
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_quant_type="nf4")
elif not args.prequantized:
    load_kw["dtype"] = torch.bfloat16
# prequantized (AWQ/GPTQ): config carries quantization_config; just load (+device_map)
if args.device_map or args.prequantized:
    load_kw["device_map"] = args.device_map or "auto"
model = AutoModelForCausalLM.from_pretrained(args.model_id, **load_kw)
if not load_kw.get("device_map") and not quantized:
    model = model.to(device)
model = model.eval()
# with device_map/quant, inputs must land on the model's input embedding device
in_dev = next(model.parameters()).device if (load_kw.get("device_map") or quantized) else device
nL = model.config.num_hidden_layers
print(f"[cap] layers={nL} hidden={model.config.hidden_size}", flush=True)

def build_prompt(q):
    msgs = [{"role": "user", "content":
             f"Answer the trivia question with only the answer, as briefly as possible.\n\nQuestion: {q}\nAnswer:"}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

feats=[]; feats_mean=[]; ys=[]; gens=[]; qts=[]; qs=[]; qlens=[]
with torch.no_grad():
    for i, r in enumerate(rows):
        p = build_prompt(r["q"])
        enc = tok(p, return_tensors="pt").to(in_dev)
        out = model(**enc, output_hidden_states=True)
        hs = out.hidden_states            # tuple len nL+1; [0]=embeddings
        vec = np.stack([hs[L][0,-1,:].float().cpu().numpy() for L in range(1, nL+1)], axis=0)
        vec_mean = np.stack([hs[L][0,:,:].float().mean(dim=0).cpu().numpy() for L in range(1, nL+1)], axis=0)
        feats.append(vec.astype(np.float16)); feats_mean.append(vec_mean.astype(np.float16))
        g = model.generate(**enc, max_new_tokens=args.max_new, do_sample=False,
                           pad_token_id=tok.eos_token_id)
        gen = tok.decode(g[0, enc["input_ids"].shape[1]:], skip_special_tokens=True)
        ng = normalize_answer(gen)
        correct = int(any((na := normalize_answer(a)) and na in ng for a in r["aliases"]))
        ys.append(correct); gens.append(gen); qts.append(qtype(r["q"])); qs.append(r["q"])
        qlens.append(int(enc["input_ids"].shape[1]))
        if (i+1) % 100 == 0:
            print(f"[cap] {i+1}/{len(rows)} correct_rate={np.mean(ys):.3f}", flush=True)

feats = np.stack(feats, axis=0); feats_mean = np.stack(feats_mean, axis=0); y = np.array(ys, dtype=int)
print(f"[cap] CORRECT={int(y.sum())} INCORRECT={int((1-y).sum())} correct_rate={float(y.mean()):.3f}", flush=True)
np.savez_compressed(args.out, features=feats, features_mean=feats_mean, correct=y, qtype=np.array(qts),
                    question=np.array(qs), qlen=np.array(qlens, dtype=int), n_layers=nL,
                    model_id=args.model_id)
with open(args.gen_out, "w") as f:
    for r, g, c in zip(rows, gens, ys):
        f.write(json.dumps({"q": r["q"], "gen": g, "correct": int(c), "aliases": r["aliases"]})+"\n")
print(f"[cap] SAVED {args.out}  gens={args.gen_out}", flush=True)
