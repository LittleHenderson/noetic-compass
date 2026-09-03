"""Dispatch the P6 audit package to independent model families via AWS Bedrock.

Same eligibility law as CJT_PREC_CLOSURE/dispatch_bedrock_audit.py, enforced in code:
  Anthropic / Claude    INELIGIBLE -- built p6_order_test.py AND the clean-room correction
  Zhipu / GLM           INELIGIBLE -- authored the proof sketch in the adjacent precedence lane
  DeepSeek R1           ELIGIBLE  (primary)
  Meta Llama 3.3 70B    ELIGIBLE  (second opinion)
Project rule: Bedrock is TEACHER-LANGUAGE work only. An audit is language. No GPU, no training.
Cost is recorded from the returned token counts; the dollar figure is an ESTIMATE from the
published on-demand rate and must be reconciled against the AWS bill.

Run:  python dispatch_p6_audit.py
Writes audits/<family>_p6_audit.md and audits/DISPATCH_RECEIPT.json. Keys never printed.
"""
import datetime as dt
import json
import pathlib
import re
import sys

import boto3
from botocore.config import Config

# Windows consoles default to cp1252; auditor text contains Unicode. Never let a print crash a
# dispatch after the paid call has already returned.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE / "P6_AUDIT_PACKAGE.md"
OUT = HERE / "audits"
OUT.mkdir(exist_ok=True)
REGION = "us-west-2"

AUDITORS = [
    ("deepseek-r1", ["us.deepseek.r1-v1:0", "deepseek.r1-v1:0"]),
    ("llama3-3-70b", ["us.meta.llama3-3-70b-instruct-v1:0", "meta.llama3-3-70b-instruct-v1:0"]),
]

# USD per 1M tokens, on-demand, us-west-2, as published at time of writing. ESTIMATE ONLY.
RATES = {"deepseek-r1": (1.35, 5.40), "llama3-3-70b": (0.72, 0.72)}

PROMPT_HEAD = """You are acting as an INDEPENDENT AUDITOR of a small, fully committed numerical experiment.

The authors (an AI assistant, since replaced by a clean-room successor) have a documented record
of shipping fabricated or mislabelled numbers and later catching them. The package below contains
(1) the committed experiment script verbatim, (2) its committed raw output, (3) a clean-room
finding that the script's "held-out" set is identical to its training set, (4) a corrected
re-run whose only change is a genuinely fresh held-out draw, and (5) the questions you must
answer. Do not be agreeable. A verdict that the experiment cannot support any claim about the
specific order P > C > E > O is an expected and acceptable outcome.

Answer every question in the QUESTIONS section. End your reply with EXACTLY ONE line of this form:
    P6_AUDIT_PASS:<the exact claim you certify>
    P6_AUDIT_PARTIAL:<what is unresolved>
    P6_AUDIT_FAIL:<the contradiction, shortcut or defect that invalidates the reported conclusion>

=== BEGIN PACKAGE ===

"""


def main():
    if not PKG.exists():
        sys.exit(f"missing {PKG}")
    prompt = PROMPT_HEAD + PKG.read_text(encoding="utf-8")
    br = boto3.client("bedrock-runtime", region_name=REGION,
                      config=Config(read_timeout=3600, retries={"max_attempts": 2}))
    print(f"  package: {len(prompt):,} chars   region: {REGION}")
    print("  RECUSED: Anthropic/Claude (built it), Zhipu/GLM (adjacent-lane author)\n")
    receipt = {"dispatched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
               "region": REGION, "package": PKG.name, "package_chars": len(prompt), "auditors": []}
    for label, candidates in AUDITORS:
        existing = OUT / f"{label}_p6_audit.md"
        if existing.exists():
            # A paid report is never re-bought: rebuild the receipt row from the saved file.
            text = existing.read_text(encoding="utf-8")
            m_v = re.search(r"verdict line: `(.*?)`", text)
            m_u = re.search(r"usage: `(\{.*?\})`", text)
            m_c = re.search(r"estimated cost USD: `([0-9.]+)`", text)
            m_m = re.search(r"model: `(.*?)`", text)
            receipt["auditors"].append({
                "family": label, "model_id": m_m.group(1) if m_m else None,
                "outcome": "OK_EXISTING_REPORT_NOT_REDISPATCHED",
                "usage": json.loads(m_u.group(1)) if m_u else None,
                "estimated_cost_usd": float(m_c.group(1)) if m_c else None,
                "verdict_line": m_v.group(1) if m_v else "NO VERDICT LINE FOUND",
                "report": f"audits/{label}_p6_audit.md"})
            print(f"  SKIP {label:<14} report already exists: {existing.name}")
            continue
        done = False
        for mid in candidates:
            print(f"  DISPATCH {label:<14} [{mid}] ... ", end="", flush=True)
            try:
                r = br.converse(modelId=mid,
                                messages=[{"role": "user", "content": [{"text": prompt}]}],
                                inferenceConfig={"maxTokens": 8000, "temperature": 0.2})
            except Exception as e:
                print(f"FAILED: {type(e).__name__}: {str(e)[:150]}")
                receipt["auditors"].append({"family": label, "model_id": mid, "outcome": "FAILED",
                                            "error": f"{type(e).__name__}: {str(e)[:300]}"})
                continue
            blocks = r["output"]["message"]["content"]
            body = "".join(b.get("text", "") for b in blocks)
            reasoning = "".join(b.get("reasoningContent", {}).get("reasoningText", {}).get("text", "")
                                for b in blocks)
            usage = r.get("usage", {})
            verdict = "NO VERDICT LINE FOUND"
            for line in body.splitlines():
                if line.strip().startswith("P6_AUDIT_"):
                    verdict = line.strip()
            rin, rout = RATES[label]
            est = (usage.get("inputTokens", 0) * rin + usage.get("outputTokens", 0) * rout) / 1e6
            (OUT / f"{label}_p6_audit.md").write_text(
                f"# {label} -- independent P6 audit (AWS Bedrock, {REGION})\n\n"
                f"model: `{mid}`\n\nverdict line: `{verdict}`\n\n"
                f"usage: `{json.dumps(usage)}`   estimated cost USD: `{est:.4f}` (from published rate; reconcile with bill)\n\n"
                f"---\n\n{body}\n"
                + (f"\n\n---\n\n## reasoning trace\n\n{reasoning}\n" if reasoning else ""),
                encoding="utf-8")
            receipt["auditors"].append({"family": label, "model_id": mid, "outcome": "OK",
                                        "usage": usage, "estimated_cost_usd": round(est, 4),
                                        "verdict_line": verdict, "report": f"audits/{label}_p6_audit.md"})
            print("OK")
            print(f"      tokens in/out: {usage.get('inputTokens')}/{usage.get('outputTokens')}   est USD {est:.4f}")
            print(f"      verdict: {verdict[:200]}")
            done = True
            break
        if not done:
            print(f"      {label}: no candidate model id worked\n")
    (OUT / "DISPATCH_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"\n  receipt: audits/DISPATCH_RECEIPT.json")


if __name__ == "__main__":
    main()
