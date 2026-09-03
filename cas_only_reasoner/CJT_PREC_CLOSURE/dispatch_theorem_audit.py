"""Dispatch THEOREM_AUDIT_PACKAGE.md to SECOND and THIRD independent mathematical auditors.

Owner instruction 2026-09-02: "get a second math auditor on the generic theorem."

ELIGIBILITY, enforced here rather than assumed:
  Anthropic / Claude   INELIGIBLE -- built the artifacts under audit
  Zhipu / GLM          INELIGIBLE -- AUTHORED the proof sketch under audit (contributor, not
                       auditor). ZHIPU_API_KEY is refused by this script by name.
  DeepSeek             ELIGIBLE -- distinct family, strong mathematical reasoning
  Google / Gemini      ELIGIBLE -- distinct family
  Alibaba / Qwen       ELIGIBLE -- held in reserve as a tie-breaker

Two auditors are dispatched, not one. A single auditor's error would otherwise decide a
theorem, and this project has already had one auditor's number enter the record uncorrected.

Keys are read from ~/.cas_llm_keys.env and are NEVER printed or written to any output file.

Run:  python dispatch_theorem_audit.py
"""
import json
import os
import pathlib
import sys

import requests

HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE / "THEOREM_AUDIT_PACKAGE.md"
OUT = HERE / "audits"
OUT.mkdir(exist_ok=True)

RECUSED = {"ZHIPU_API_KEY": "GLM authored the proof sketch under audit"}


def load_keys():
    p = pathlib.Path.home() / ".cas_llm_keys.env"
    keys = {}
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        keys[k.strip()] = v.strip().strip('"').strip("'")
    return keys


PROMPT_HEAD = """You are acting as an INDEPENDENT MATHEMATICAL AUDITOR.

A research program has a claim it wants to freeze into a permanent record. A previous auditor
reviewed it AND THEN CONTRIBUTED A PROOF SKETCH OF ITS OWN, so that auditor is now a co-author
and is recused. You are the independent second opinion.

Your job is to BREAK the claim if it is breakable, or to state exactly what weaker claim
survives. Returning "this is not provable as stated" is a SUCCESSFUL outcome and is what the
owner of the project expects if it is true. Do not be agreeable. Do not soften a failed gate.

Read the package below and answer the seven questions in its section 7. Be concrete and
mathematical. Where you assert something, give the argument or the counterexample. Where you are
uncertain, say so explicitly rather than hedging in prose.

End your reply with EXACTLY ONE of these lines:
    PRECEDENCE_THEOREM_AUDIT_PASS:<the exact claim you certify>
    PRECEDENCE_THEOREM_AUDIT_PARTIAL:<what is unresolved>
    PRECEDENCE_THEOREM_AUDIT_FAIL:<the contradiction or counterexample>

=== BEGIN PACKAGE ===

"""


def call_deepseek(key, prompt):
    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "deepseek-reasoner",
              "messages": [{"role": "user", "content": prompt}],
              "max_tokens": 8000},
        timeout=1800,
    )
    r.raise_for_status()
    d = r.json()
    m = d["choices"][0]["message"]
    body = m.get("content") or ""
    reasoning = m.get("reasoning_content") or ""
    return body, reasoning, d.get("usage", {})


def call_gemini(key, prompt, model="gemini-2.5-pro"):
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"maxOutputTokens": 8000}},
        timeout=1800,
    )
    r.raise_for_status()
    d = r.json()
    parts = d.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts), "", d.get("usageMetadata", {})


def main():
    if not PKG.exists():
        sys.exit(f"missing {PKG}")
    prompt = PROMPT_HEAD + PKG.read_text(encoding="utf-8")
    keys = load_keys()

    for name, why in RECUSED.items():
        if name in keys:
            print(f"  RECUSED  {name:<20} {why}")
    print()

    jobs = [("deepseek", "DEEPSEEK_API_KEY", call_deepseek),
            ("gemini", "GEMINI_API_KEY", call_gemini)]

    for label, keyname, fn in jobs:
        if keyname not in keys:
            print(f"  SKIP     {label}: no {keyname}")
            continue
        print(f"  DISPATCH {label} ... ", end="", flush=True)
        try:
            body, reasoning, usage = fn(keys[keyname], prompt)
        except Exception as e:
            print(f"FAILED: {type(e).__name__}: {str(e)[:200]}")
            continue
        verdict = "NO VERDICT LINE FOUND"
        for line in body.splitlines():
            if line.strip().startswith("PRECEDENCE_THEOREM_AUDIT_"):
                verdict = line.strip()
        (OUT / f"{label}_audit.md").write_text(
            f"# {label} independent theorem audit\n\n"
            f"verdict line: `{verdict}`\n\nusage: `{json.dumps(usage)}`\n\n---\n\n{body}\n"
            + (f"\n\n---\n\n## reasoning trace\n\n{reasoning}\n" if reasoning else ""),
            encoding="utf-8")
        print(f"OK  -> audits/{label}_audit.md")
        print(f"           verdict: {verdict[:160]}")

    print()
    print("  Keys were read from ~/.cas_llm_keys.env and never printed or written to output.")


if __name__ == "__main__":
    main()
