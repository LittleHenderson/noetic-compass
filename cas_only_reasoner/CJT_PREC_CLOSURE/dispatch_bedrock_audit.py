"""Dispatch the theorem audit to independent model families via AWS Bedrock.

The direct vendor APIs are all in arrears (DeepSeek 402, Gemini 429/403, Qwen Arrearage). AWS is
funded, and Bedrock hosts several NON-Anthropic families. Project rule: Bedrock is for
TEACHER-LANGUAGE work only, never for claim-bearing neural runs. A mathematical audit is
language, so this is in scope. No GPU is used and no training happens.

ELIGIBILITY, enforced in code:
  Anthropic / Claude    INELIGIBLE -- built the artifacts under audit
  Zhipu / GLM           INELIGIBLE -- AUTHORED the proof sketch under audit
  DeepSeek R1           ELIGIBLE -- distinct family, strong at mathematics   (primary)
  Meta Llama 3.3 70B    ELIGIBLE -- distinct family                          (second opinion)

TWO auditors, not one. A single auditor's number has already entered this record uncorrected
once; that is not repeated.

Run:  python dispatch_bedrock_audit.py
"""
import json
import pathlib
import sys

import boto3
from botocore.config import Config

HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE / "THEOREM_AUDIT_PACKAGE.md"
OUT = HERE / "audits"
OUT.mkdir(exist_ok=True)
REGION = "us-west-2"

AUDITORS = [
    ("deepseek-r1", ["us.deepseek.r1-v1:0", "deepseek.r1-v1:0"]),
    ("llama3-3-70b", ["us.meta.llama3-3-70b-instruct-v1:0", "meta.llama3-3-70b-instruct-v1:0"]),
]

PROMPT_HEAD = """You are acting as an INDEPENDENT MATHEMATICAL AUDITOR.

A research program wants to freeze a claim into a permanent record. The previous auditor reviewed
it AND THEN CONTRIBUTED A PROOF SKETCH OF ITS OWN, so that auditor is now a co-author and is
recused. You are the independent second opinion.

Your job is to BREAK the claim if it is breakable, or state exactly what weaker claim survives.
Returning "this is not provable as stated" is a SUCCESSFUL outcome and is what the project owner
expects if it is true. Do not be agreeable. Do not soften a failed gate. The authors of this
package have already shipped and later caught a fabricated measurement, two arity mismatches, and
several conclusions that did not follow from their own output -- assume their numbers may be
wrong.

Answer the questions in section 7, and above all section 9's Q3: IS THE VISIBILITY LAW TRUE?
Give a proof or a counterexample.

End your reply with EXACTLY ONE line of this form:
    PRECEDENCE_THEOREM_AUDIT_PASS:<the exact claim you certify>
    PRECEDENCE_THEOREM_AUDIT_PARTIAL:<what is unresolved>
    PRECEDENCE_THEOREM_AUDIT_FAIL:<the contradiction or counterexample>

=== BEGIN PACKAGE ===

"""


def main():
    if not PKG.exists():
        sys.exit(f"missing {PKG}")
    prompt = PROMPT_HEAD + PKG.read_text(encoding="utf-8")
    br = boto3.client("bedrock-runtime", region_name=REGION,
                      config=Config(read_timeout=3600, retries={"max_attempts": 2}))

    print(f"  package: {len(prompt):,} chars   region: {REGION}")
    print("  RECUSED: Anthropic/Claude (built it), Zhipu/GLM (authored the sketch)\n")

    for label, candidates in AUDITORS:
        done = False
        for mid in candidates:
            print(f"  DISPATCH {label:<14} [{mid}] ... ", end="", flush=True)
            try:
                r = br.converse(
                    modelId=mid,
                    messages=[{"role": "user", "content": [{"text": prompt}]}],
                    inferenceConfig={"maxTokens": 8000, "temperature": 0.2},
                )
            except Exception as e:
                print(f"FAILED: {type(e).__name__}: {str(e)[:150]}")
                continue
            blocks = r["output"]["message"]["content"]
            body = "".join(b.get("text", "") for b in blocks)
            reasoning = "".join(
                b.get("reasoningContent", {}).get("reasoningText", {}).get("text", "")
                for b in blocks)
            usage = r.get("usage", {})
            verdict = "NO VERDICT LINE FOUND"
            for line in body.splitlines():
                if line.strip().startswith("PRECEDENCE_THEOREM_AUDIT_"):
                    verdict = line.strip()
            (OUT / f"{label}_audit.md").write_text(
                f"# {label} — independent theorem audit (AWS Bedrock, {REGION})\n\n"
                f"model: `{mid}`\n\nverdict line: `{verdict}`\n\n"
                f"usage: `{json.dumps(usage)}`\n\n---\n\n{body}\n"
                + (f"\n\n---\n\n## reasoning trace\n\n{reasoning}\n" if reasoning else ""),
                encoding="utf-8")
            print("OK")
            print(f"      tokens in/out: {usage.get('inputTokens')}/{usage.get('outputTokens')}")
            print(f"      verdict: {verdict[:200]}")
            print(f"      saved:   audits/{label}_audit.md\n")
            done = True
            break
        if not done:
            print(f"      {label}: no candidate model id worked\n")


if __name__ == "__main__":
    main()
