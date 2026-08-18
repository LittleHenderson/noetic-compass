"""Run the TKS/CAS blindness probe against DeepSeek, Qwen, and GLM.

For each lab: resolve key from the keys file, auto-discover a working model id
(the user's named model first, then safe fallbacks), run blindness_probe, and
print a summary. Honesty guard: counts non-empty responses so a thinking model
that returns empty text can't fake a "blind" (score 0) pass.
"""
import json, sys
import providers, blindness_probe
from openai import OpenAI

# (provider, [candidate model ids, user's named model first])
TARGETS = [
    ("deepseek", ["deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"]),
    ("qwen",     ["qwen3.8-max", "qwen3-max", "qwen-max", "qwen-plus"]),
    ("glm",      ["glm-5.3", "glm-4.6", "glm-4-plus", "glm-4"]),
]
# qwen keys can be region-bound; try both DashScope endpoints
QWEN_BASES = ["https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
              "https://dashscope.aliyuncs.com/compatible-mode/v1"]


def find_model(base_url, key, candidates):
    """Return (working_model_id, base_url_used, err) by trying a 1-token call."""
    bases = QWEN_BASES if "dashscope" in (base_url or "") else [base_url]
    last = "no attempt"
    for bu in bases:
        client = OpenAI(api_key=key, base_url=bu)
        for m in candidates:
            try:
                client.chat.completions.create(
                    model=m, max_tokens=5,
                    messages=[{"role": "user", "content": "hi"}])
                return m, bu, None
            except Exception as e:
                last = str(e)[:160]
    return None, base_url, last


summary = []
for prov, cands in TARGETS:
    try:
        base_url, key, _ = providers.resolve(prov)
    except SystemExit as e:
        print(f"[{prov}] SKIP: {e}", flush=True)
        summary.append({"provider": prov, "status": "no-key"}); continue
    model, base_used, err = find_model(base_url, key, cands)
    if not model:
        print(f"[{prov}] no working model among {cands}: {err}", flush=True)
        summary.append({"provider": prov, "status": "no-model", "err": err}); continue
    print(f"[{prov}] using model '{model}' @ {base_used}; probing blindness...", flush=True)
    rep = blindness_probe.probe_model(model, key, base_used)
    score = rep["mean_blindness_score"]; done = rep["num_completed"]
    nonempty = sum(1 for r in rep["per_query"]
                   if (r.get("answer_chars", 0) + r.get("reasoning_chars", 0)) > 0)
    reliable = nonempty >= 7  # need most of 10 queries to have real text (answer or reasoning)
    if done == 0:
        verdict = "NO-DATA"
    elif not reliable:
        verdict = "UNRELIABLE(empty responses)"
    elif score < 0.3:
        verdict = "PASS(blind)"
    else:
        verdict = "FAIL(exposed)"
    out = f"blindness_probe_{prov}_{model.replace('/', '_')}.json"
    json.dump(rep, open(out, "w"), indent=2)
    print(f"[{prov}] {model}: mean_blindness={score}  completed={done}/{rep['num_queries']}  "
          f"nonempty={nonempty}/{rep['num_queries']}  -> {verdict}  ({out})", flush=True)
    summary.append({"provider": prov, "model": model, "base": base_used,
                    "score": score, "nonempty": nonempty, "verdict": verdict})

print("\n=== BLINDNESS SUMMARY (threshold 0.3; PASS = model is blind to TKS/CAS) ===")
for s in summary:
    if s.get("status"):
        print(f"  {s['provider']:9s} {s['status']}")
    else:
        print(f"  {s['provider']:9s} {s['model']:16s} score={s['score']}  "
              f"nonempty={s['nonempty']}/10  {s['verdict']}")
json.dump(summary, open("blindness_summary.json", "w"), indent=2)
print("\nwrote blindness_summary.json")
