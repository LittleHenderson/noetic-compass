"""Knockout existence check driven by EXISTING balanced generations (no regen).

Greedy decode collapses to all-SUPPORTED, so we instead teacher-force the model's
OWN already-sampled outputs (gen_hard_v2: balanced 95 SUPPORTED / 96 UNSUPPORTED on
Qwen2.5-0.5B) and measure the Grounding Mediation Effect (GME) by severing attention
from the answer-value position to the trusted-evidence span. Reuses the proven
KnockoutController + summarize from knockout_existence_check.py.

GME = clean_prob(answer_value_token) - knockout_prob. Prediction:
  SUPPORTED (answer == gold, taken from trusted evidence) -> GME large (collapses).
  UNSUPPORTED (answer == stale/counterfactual value) -> GME ~ 0 (didn't use evidence).
  evidence-span knockout >> random-span knockout (placebo).
REAL numbers only.
"""
import sys, json, argparse, random
sys.path.insert(0, "/root/scripts")
import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from run_enabled_predicate_capture import format_model_prompt
from knockout_existence_check import (
    KnockoutController, char_span_of_value, token_indices_for_char_span,
    answer_token_logprob, prob_from_logprob, summarize,
)

ap = argparse.ArgumentParser()
ap.add_argument("--model-id", default="Qwen/Qwen2.5-0.5B-Instruct")
ap.add_argument("--gen", default="/root/gen_hard_v2/outcome_native_generations.jsonl")
ap.add_argument("--mode", default="", help="filter challenge_mode (empty=all)")
ap.add_argument("--layer-lo", type=int, default=8)
ap.add_argument("--layer-hi", type=int, default=16)
ap.add_argument("--max", type=int, default=0)
ap.add_argument("--max-length", type=int, default=640)
ap.add_argument("--out", default="/root/knockout_gen_report.json")
args = ap.parse_args()
random.seed(0); np.random.seed(0); torch.manual_seed(0)

rows = [json.loads(l) for l in open(args.gen) if l.strip()]
rows = [r for r in rows if r.get("support_status") in ("SUPPORTED", "UNSUPPORTED")]
if args.mode:
    rows = [r for r in rows if r.get("challenge_mode") == args.mode]
if args.max:
    # keep class balance when capping
    s = [r for r in rows if r["support_status"] == "SUPPORTED"][: args.max // 2]
    u = [r for r in rows if r["support_status"] == "UNSUPPORTED"][: args.max // 2]
    rows = s + u
print(f"[knockout-gen] rows={len(rows)} model={args.model_id} gen={args.gen}", flush=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
tok = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
if tok.pad_token_id is None and tok.eos_token_id is not None:
    tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(
    args.model_id, dtype=torch.bfloat16 if device == "cuda" else torch.float32,
    attn_implementation="eager", trust_remote_code=True, low_cpu_mem_usage=True,
).to(device).eval()
n_layers = model.config.num_hidden_layers
layer_hi = min(args.layer_hi, n_layers - 1)
print(f"[knockout-gen] layers={n_layers} band=[{args.layer_lo},{layer_hi}]", flush=True)

knock = KnockoutController(model, args.layer_lo, layer_hi)
knock.install()

import collections
records = []; label_counter = collections.Counter()
for idx, r in enumerate(rows, 1):
    prompt = str(r["prompt"]); gold = str(r.get("gold_answer") or "")
    alt = str(r.get("counterfactual_unsupported_answer") or "")
    out = str(r.get("model_output") or ""); support = r["support_status"]
    label_counter[support] += 1
    answer_value = gold if support == "SUPPORTED" else alt
    chat = format_model_prompt(tokenizer=tok, prompt=prompt, prompt_format="chat-auto")
    full_text = chat + out
    full = tok(full_text, return_tensors="pt", return_offsets_mapping=True,
               truncation=True, max_length=args.max_length)
    offsets = [tuple(x) for x in full["offset_mapping"][0].tolist()]
    full_ids = full["input_ids"].to(device)

    ev_span = char_span_of_value(chat, gold)                       # trusted-evidence value in prompt
    ans_char = char_span_of_value(full_text, answer_value, search_from=len(chat))  # value in the output
    stale_span = char_span_of_value(chat, alt) if alt else None
    if ev_span is None or ans_char is None:
        continue
    ev_tok = token_indices_for_char_span(offsets, ev_span[0], ev_span[1])
    ans_tok = token_indices_for_char_span(offsets, ans_char[0], ans_char[1])
    stale_tok = token_indices_for_char_span(offsets, stale_span[0], stale_span[1]) if stale_span else []
    if not ev_tok or not ans_tok:
        continue
    answer_pos = ans_tok[0]
    if answer_pos == 0:
        continue
    # random equal-length non-evidence span in the prompt region (placebo)
    ptc = sum(1 for (a, b) in offsets if a < len(chat) and b <= len(chat) and b > a)
    forbidden = set(ev_tok) | set(stale_tok)
    cand = [i for i in range(1, max(1, ptc)) if i not in forbidden]
    k = len(ev_tok)
    rand_tok = (lambda c: c[random.randrange(0, max(1, len(c)-k+1)): random.randrange(0, max(1, len(c)-k+1))+k] if len(c) >= k else c[:k])(cand)

    knock.active = False
    clean_p = prob_from_logprob(answer_token_logprob(model, full_ids, answer_pos))
    def gme(keys):
        if not keys: return float("nan")
        # teacher-forcing: prob(token@answer_pos) is read from logits@answer_pos-1,
        # so the PREDICTING query position is answer_pos-1 — mask THAT query's attn.
        knock.active = True; knock.set_target(answer_pos - 1, keys)
        v = clean_p - prob_from_logprob(answer_token_logprob(model, full_ids, answer_pos))
        knock.active = False; return v
    rec = {"support_status": support, "answer_text": out, "answer_value": answer_value,
           "clean_prob": clean_p, "gme_evidence": gme(ev_tok), "gme_random": gme(rand_tok),
           "gme_stale": gme(stale_tok) if stale_tok else float("nan"),
           "topic": r.get("topic", ""), "domain": r.get("domain", ""),
           "challenge_mode": r.get("challenge_mode", ""), "n_evidence_tokens": len(ev_tok),
           "answer_pos": answer_pos}
    records.append(rec)
    if idx % 25 == 0 or idx == len(rows):
        print(f"[knockout-gen] {idx}/{len(rows)} kept={len(records)} last={support} "
              f"gme_ev={rec['gme_evidence']:.4f} gme_rand={rec['gme_random']:.4f}", flush=True)
knock.remove()

class A: pass
sa = A(); sa.layer_lo = args.layer_lo; sa.model_id = args.model_id
sa.profile = "from_generations:" + (args.mode or "all_modes")
report = summarize(records, sa, layer_hi, label_counter, n_layers)
report["model_id"] = args.model_id; report["source"] = args.gen
open(args.out, "w").write(json.dumps(report, indent=2, sort_keys=True, default=float))
print("\n==================== KNOCKOUT (from generations) ====================")
print(json.dumps(report["headline"], indent=2, sort_keys=True, default=float))
print(f"[knockout-gen] report -> {args.out}")
