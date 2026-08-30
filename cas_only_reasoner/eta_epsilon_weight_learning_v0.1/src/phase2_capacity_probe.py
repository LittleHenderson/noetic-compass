"""Phase 2 CAPACITY PROBE (preregistered gate). Does Qwen 0.5B already
solve active/passive role binding zero-shot? If zero-shot exact accuracy
>= 0.85, the task is CEILINGED and unsuitable (nothing to teach). If it
fails - especially on passives - there is a real behavioral target.

This is preregistered (thresholds: capacity_probe zero-shot < 0.85). It
is behavioral (generation + mechanical answer check), not a probe. No
steering, no weight change.
"""
import json
import os
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import data_gen  # noqa: E402

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
N_PER_VOICE = 150


def check(answer: str, agent: str, patient: str):
    words = answer.lower().replace(".", " ").replace(",", " ").split()
    pos_a = next((i for i, w in enumerate(words) if w == agent), 1e9)
    pos_p = next((i for i, w in enumerate(words) if w == patient), 1e9)
    if pos_a == 1e9 and pos_p == 1e9:
        return "abstain"
    return "correct" if pos_a < pos_p else "wrong"


def main():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, revision=REVISION, torch_dtype=torch.float16).to(device).eval()

    train, test = data_gen.generate()
    pool = train + test
    actives = [e for e in pool if e["voice"] == "active"][:N_PER_VOICE]
    passives = [e for e in pool if e["voice"] == "passive"][:N_PER_VOICE]
    items = actives + passives

    def ask_batch(batch):
        prompts = []
        for e in batch:
            q = (f'In the sentence "{e["text"]}" who performed the '
                 f'action? Answer with one word only.')
            msgs = [{"role": "user", "content": q}]
            prompts.append(tok.apply_chat_template(
                msgs, tokenize=False, add_generation_prompt=True))
        enc = tok(prompts, return_tensors="pt", padding=True).to(device)
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=8, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
        gen = out[:, enc["input_ids"].shape[1]:]
        return [tok.decode(g, skip_special_tokens=True) for g in gen]

    res = {"active": {"correct": 0, "wrong": 0, "abstain": 0},
           "passive": {"correct": 0, "wrong": 0, "abstain": 0}}
    samples = []
    bs = 32
    for i in range(0, len(items), bs):
        batch = items[i:i + bs]
        answers = ask_batch(batch)
        for e, a in zip(batch, answers):
            verdict = check(a, e["agent"], e["patient"])
            res[e["voice"]][verdict] += 1
            if len(samples) < 12:
                samples.append({"text": e["text"], "gold_agent": e["agent"],
                                "answer": a.strip()[:40], "verdict": verdict})

    def acc(d):
        n = sum(d.values())
        return round(d["correct"] / n, 4) if n else None
    overall_correct = res["active"]["correct"] + res["passive"]["correct"]
    overall_n = len(items)
    out = {
        "schema": "eta_epsilon_weight_learning.phase2_capacity_probe.v0.1",
        "status": "PREREGISTERED_CAPACITY_GATE",
        "model": MODEL, "device": device,
        "n_active": len(actives), "n_passive": len(passives),
        "overall_zero_shot_accuracy": round(overall_correct / overall_n, 4),
        "active_accuracy": acc(res["active"]),
        "passive_accuracy": acc(res["passive"]),
        "counts": res,
        "capacity_threshold": 0.85,
        "task_ceilinged": (overall_correct / overall_n) >= 0.85,
        "samples": samples,
    }
    p = os.path.join(os.path.dirname(HERE), "reports",
                     "phase2_capacity_probe.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=2)
    print(json.dumps({k: out[k] for k in
                      ("overall_zero_shot_accuracy", "active_accuracy",
                       "passive_accuracy", "task_ceilinged")}, indent=2))
    for s in samples[:6]:
        print(" ", s["verdict"], "|", s["text"], "-> gold", s["gold_agent"],
              "| said:", s["answer"])
    print("saved", p)


if __name__ == "__main__":
    main()
