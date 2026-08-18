"""Generate REAL model outputs (not authored exemplars) for the ecological-validity
lens test. Send diverse natural prompts to the models, capture their ACTUAL answers.
No planted CAS labels — these are just real responses a user would get.

Rotates the generating model across prompts so outputs aren't one model's style.
Output: real_outputs.jsonl with {id, prompt, gen_model, output}.
"""
import json, argparse, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import providers
from pilot_label import call_with_retry, MODELS
from openai import OpenAI

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROMPTS = [
    "I got two job offers — one pays a lot more, the other is the work I'm passionate about. How should I think about this?",
    "Explain how vaccines train the immune system, in plain language.",
    "My dog died yesterday and I can't stop crying. I feel silly being this upset over a pet.",
    "Is it ever okay to lie to protect someone's feelings?",
    "Write a short poem about the last week of autumn.",
    "How do I reverse a linked list in Python? Walk me through it.",
    "My teenager has started lying to me and I don't know whether to confront them or wait.",
    "What actually makes a life a good one?",
    "Give me the honest pros and cons of fully remote work for a small startup.",
    "Do you ever get things wrong? How would you even know?",
    "I keep procrastinating on a project that matters to me. Why do people do that?",
    "Summarize what happened in the 2008 financial crisis for someone who was a kid then.",
    "A friend asked me to cover for them at work while they interview elsewhere. Should I?",
    "What's the difference between feeling anxious and being in actual danger?",
    "Help me draft a kind but firm message declining a wedding invitation I can't afford.",
    "Why does music give people chills sometimes?",
    "I think my startup idea is great but everyone I pitch it to seems unconvinced. What do I do?",
    "Explain the trolley problem and why philosophers still argue about it.",
    "I've been offered a promotion that means managing my current friends. What should I weigh?",
    "What's a respectful way to tell my roommate their cooking smell bothers me?",
    "How do I know if I'm actually in love or just afraid of being alone?",
    "Break down the argument for and against a four-day work week.",
    "I said something cruel to my sister in an argument and I feel awful. What now?",
    "Explain what a black hole is without using any equations.",
    "Should I tell my manager I'm burned out, or just power through the quarter?",
    "Why do we dream, as far as science can tell?",
    "I want to start running but I always quit after two weeks. How do I make it stick?",
    "What's the strongest argument against my belief that hard work always pays off?",
    "Help me decide whether to move across the country for a relationship.",
    "Describe what it feels like to finally understand something you struggled with.",
    "Is forgiveness for the other person or for yourself?",
    "Explain compound interest to a 15-year-old who thinks saving is pointless.",
    "I froze during a presentation today and I'm mortified. Talk me through it.",
    "What separates a brave decision from a reckless one?",
    "How should I approach apologizing to someone who may not forgive me?",
    "Why is it so hard to change a habit even when you know it's bad for you?",
]


def gen_one(idx, prompt, max_tokens):
    prov = list(MODELS)[idx % len(MODELS)]
    model = MODELS[prov]
    bu, key, _ = providers.resolve(prov, model)
    client = OpenAI(api_key=key, base_url=bu)
    r = call_with_retry(client, prov, model=model, max_tokens=max_tokens, temperature=0.7,
                        messages=[{"role": "user", "content": prompt}])
    msg = r.choices[0].message
    txt = getattr(msg, "content", None) or ""
    if not txt:
        txt = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or ""
    return idx, prov, model, prompt, txt.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = all prompts")
    ap.add_argument("--max-tokens", type=int, default=3000)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="real_outputs.jsonl")
    A = ap.parse_args()

    prompts = PROMPTS[:A.limit] if A.limit else PROMPTS
    print(f"generating {len(prompts)} real outputs (rotating {list(MODELS)})", flush=True)
    rows = {}
    fout = open(A.out, "w", encoding="utf-8")
    with ThreadPoolExecutor(max_workers=A.workers) as ex:
        futs = {ex.submit(gen_one, i, p, A.max_tokens): i for i, p in enumerate(prompts)}
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                idx, prov, model, prompt, out = fut.result()
            except Exception as e:
                print(f"  [{i}] ERROR {str(e)[:120]}", flush=True); continue
            if len(out) < 30:
                print(f"  [{i}] SHORT/empty ({len(out)} chars) via {prov}", flush=True); continue
            rows[idx] = {"id": idx, "prompt": prompt, "gen_model": model, "output": out}
            print(f"  [{idx}] {prov}: {len(out)} chars", flush=True)
    for i in sorted(rows):
        fout.write(json.dumps(rows[i], ensure_ascii=False) + "\n")
    fout.close()
    print(f"\nwrote {len(rows)} real outputs to {A.out}")
    if rows:
        s = rows[sorted(rows)[0]]
        print(f"\nSAMPLE [{s['id']}] prompt: {s['prompt'][:80]}")
        print(f"  output ({s['gen_model']}): {s['output'][:300]}")


if __name__ == "__main__":
    main()
