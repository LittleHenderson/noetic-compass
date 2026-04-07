#!/usr/bin/env python3
"""Run baseline validation study through the CAS pipeline.

Takes a real (or mock) API key, runs prompts from the scenario library
through /wrap, and saves all results for analysis.

Usage:
    # Mock mode (no API key needed)
    python validation/run_baseline_study.py --provider mock

    # Real provider
    python validation/run_baseline_study.py --provider openai --count 100

    # Custom prompts file
    python validation/run_baseline_study.py --prompts scenarios/sample_prompts.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is importable
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from fastapi.testclient import TestClient

from api.main import app
from api.middleware.auth import create_token

DEFAULT_PROMPTS = Path(__file__).resolve().parent.parent / "scenarios" / "sample_prompts.json"
OUTPUT_FILE = Path(__file__).parent / "baseline_results.json"


def run_study(
    provider: str,
    count: int,
    prompts_path: Path,
    output_path: Path,
    dials: list[int] | None = None,
) -> None:
    if not prompts_path.exists():
        print(f"Prompts file not found: {prompts_path}")
        sys.exit(1)

    prompts = json.loads(prompts_path.read_text())
    prompts = prompts[:count]

    client = TestClient(app)
    token = create_token(sub="baseline-study", api_key="baseline-key")
    headers = {"Authorization": f"Bearer {token}"}
    dial_values = dials or [6] * 10

    print(f"CAS Baseline Validation Study")
    print(f"Provider: {provider}")
    print(f"Prompts:  {len(prompts)} from {prompts_path}")
    print(f"Output:   {output_path}")
    print(f"Dials:    {dial_values}")
    print()

    results: list[dict] = []
    successes = 0
    failures = 0
    start_time = time.monotonic()

    for i, prompt in enumerate(prompts):
        try:
            resp = client.post(
                "/wrap",
                json={
                    "text": prompt,
                    "provider": provider,
                    "dial_config": {"values": dial_values},
                    "mock": provider == "mock",
                },
                headers=headers,
            )

            if resp.status_code == 200:
                data = resp.json()
                nccs = data["nccs"]

                # Extract operator scores from stage data
                op_stage = next(
                    (s for s in data["stages"] if s["stage"] == "operator_scoring"), None
                )
                op_scores = op_stage["data"]["scores"] if op_stage and op_stage.get("data") else []

                # Extract domain averages
                dc_stage = next(
                    (s for s in data["stages"] if s["stage"] == "domain_coherence"), None
                )
                domain_avgs = dc_stage["data"]["domain_averages"] if dc_stage and dc_stage.get("data") else []

                # Extract drive scores
                rpm_stage = next(
                    (s for s in data["stages"] if s["stage"] == "rpm_gate"), None
                )
                drive_scores = rpm_stage["data"]["drive_scores"] if rpm_stage and rpm_stage.get("data") else []

                # Extract LLM response text
                llm_stage = next(
                    (s for s in data["stages"] if s["stage"] == "base_llm_call"), None
                )
                llm_response = ""
                if llm_stage and llm_stage.get("data", {}).get("model"):
                    # Response text is in the full data
                    llm_response = data.get("llm_response", "")

                results.append({
                    "index": i,
                    "prompt": prompt,
                    "composite": nccs["composite"],
                    "certification": nccs["certification"],
                    "operator_profile": nccs["operator_profile"],
                    "domain_coherence": nccs["domain_coherence"],
                    "drive_rpm_integrity": nccs["drive_rpm_integrity"],
                    "pathway_quality": nccs["pathway_quality"],
                    "inversion_resistance": nccs["inversion_resistance"],
                    "operator_scores": op_scores,
                    "domain_averages": domain_avgs,
                    "drive_scores": drive_scores,
                    "llm_response": llm_response,
                    "provenance": data.get("provenance", {}),
                })
                successes += 1
                cert = nccs["certification"]
                comp = nccs["composite"]
                print(f"  [{i+1:3d}/{len(prompts)}] {cert:8s} {comp:5.1f}  {prompt[:60]}...")
            else:
                failures += 1
                print(f"  [{i+1:3d}/{len(prompts)}] FAILED ({resp.status_code}): {prompt[:60]}...")
                results.append({
                    "index": i,
                    "prompt": prompt,
                    "error": resp.text[:200],
                })
        except Exception as e:
            failures += 1
            print(f"  [{i+1:3d}/{len(prompts)}] ERROR: {e}")
            results.append({"index": i, "prompt": prompt, "error": str(e)})

    elapsed = time.monotonic() - start_time

    # Compute summary statistics
    composites = [r["composite"] for r in results if "composite" in r]
    summary: dict = {
        "study_date": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "prompt_count": len(prompts),
        "successes": successes,
        "failures": failures,
        "elapsed_seconds": round(elapsed, 2),
        "dial_config": dial_values,
    }

    if composites:
        avg = sum(composites) / len(composites)
        std = (sum((c - avg) ** 2 for c in composites) / max(1, len(composites) - 1)) ** 0.5
        summary["composite_mean"] = round(avg, 2)
        summary["composite_std"] = round(std, 2)
        summary["composite_min"] = round(min(composites), 2)
        summary["composite_max"] = round(max(composites), 2)

        # Per-certification counts
        certs: dict[str, int] = {}
        for r in results:
            c = r.get("certification", "error")
            certs[c] = certs.get(c, 0) + 1
        summary["certifications"] = certs

        # Per-operator averages
        all_op_scores = [r["operator_scores"] for r in results if r.get("operator_scores")]
        if all_op_scores:
            n = len(all_op_scores)
            op_avgs = [round(sum(s[i] for s in all_op_scores) / n, 4) for i in range(10)]
            summary["operator_averages"] = op_avgs

        # Per-domain averages
        all_domain = [r["domain_averages"] for r in results if r.get("domain_averages")]
        if all_domain:
            n = len(all_domain)
            d_avgs = [round(sum(d[i] for d in all_domain) / n, 4) for i in range(4)]
            summary["domain_averages"] = d_avgs

    output = {"summary": summary, "results": results}
    output_path.write_text(json.dumps(output, indent=2))

    print(f"\n{'-'*50}")
    print(f"Study complete: {successes} succeeded, {failures} failed in {elapsed:.1f}s")
    if composites:
        print(f"Composite: mean={summary['composite_mean']}, std={summary['composite_std']}")
        print(f"Range: [{summary['composite_min']}, {summary['composite_max']}]")
        print(f"Certifications: {summary.get('certifications', {})}")
    print(f"Results saved to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CAS baseline validation study")
    parser.add_argument("--provider", default="mock", help="LLM provider (mock, openai, anthropic, google)")
    parser.add_argument("--count", type=int, default=50, help="Number of prompts to run")
    parser.add_argument("--prompts", default=str(DEFAULT_PROMPTS), help="Path to prompts JSON file")
    parser.add_argument("--output", default=str(OUTPUT_FILE), help="Output path for results")
    parser.add_argument("--dials", type=str, default=None, help="Comma-separated dial values (e.g., 6,6,6,6,6,6,6,6,6,6)")
    args = parser.parse_args()

    dials = None
    if args.dials:
        dials = [int(x.strip()) for x in args.dials.split(",")]

    run_study(
        provider=args.provider,
        count=args.count,
        prompts_path=Path(args.prompts),
        output_path=Path(args.output),
        dials=dials,
    )


if __name__ == "__main__":
    main()
