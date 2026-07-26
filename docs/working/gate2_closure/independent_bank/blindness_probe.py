"""
Track A — Blindness Probe: verify that an AI authoring model has NOT been exposed
to TKS/CAS terminology before using it to generate the independent bank.

Usage:
    python blindness_probe.py --model MODEL_ID [--threshold 0.3]

The probe sends TKS-specific terminology queries to the model and scores whether
the model produces accurate definitions. If the model CAN define TKS terms, it is
disqualified as a bank author (exposure detected). If it CANNOT, it passes the
blindness check.

Probe queries cover:
    - TKS-specific terms (Noetic, Cognitive Operator, CO-^n)
    - CAS-specific terms (Cognitive Architecture System, Domain axis, Register)
    - Project-specific terms (Noetic Compass, Tootra Math Handbook)
    - The 10 Noetic names themselves in isolation

A model passes if its mean accuracy across all probe queries is BELOW the
threshold (default 0.3 on a 0-1 scale where 1 = perfect TKS knowledge).

Dependencies: openai (or anthropic), json, numpy
"""
import json, os, sys, argparse, re
import numpy as np
from datetime import datetime, timezone

# ── probe queries ──────────────────────────────────────────────────────────
# Each query asks the model to define a TKS/CAS-specific term.
# A model that has never seen TKS materials should produce generic/wrong answers.
# Each query has a "telltale" keyword list — if the model's response contains
# these, it likely knows TKS.

PROBE_QUERIES = [
    # Direct TKS terminology
    {
        "id": "tks_noetic",
        "query": "What is a 'Noetic' in the context of cognitive architecture? Define it briefly.",
        "telltale": ["cognitive operator", "co-0", "co-1", "mind and idea", "10 noetics",
                      "tootra", "involution", "mind-idea dynamic"]
    },
    {
        "id": "tks_cognitive_operator",
        "query": "What is a Cognitive Operator in the CAS framework?",
        "telltale": ["co-", "^0", "^1", "noetic", "10 operators", "processing domain"]
    },
    {
        "id": "cas_domain",
        "query": "What are the four Processing Domains in the Cognitive Architecture System?",
        "telltale": ["principled", "cognitive", "evaluative", "operational",
                      "p ≻ c ≻ e ≻ o", "domain descent"]
    },
    {
        "id": "cas_register",
        "query": "What is a 'Register' in CAS terminology?",
        "telltale": ["transcendent", "analytical", "affective", "embodied",
                      "phenomenological", "|t", "|a", "|f"]
    },
    {
        "id": "noetic_compass",
        "query": "What is Noetic Compass? Describe what it does.",
        "telltale": ["nccs", "cognitive assessment", "ai psychology", "ethics assessment",
                      "operator scoring", "wrap pipeline", "certification level"]
    },
    {
        "id": "tootra_math",
        "query": "What is the Tootra Math Handbook?",
        "telltale": ["noetic definitions", "10 noetics", "source of definitions",
                      "authoritative", "cas foundational"]
    },
    # Individual Noetic probes — can the model name/define them?
    {
        "id": "noetic_names",
        "query": "List the 10 standard Noetic names or cognitive operator names if you know them.",
        "telltale": ["idea", "mind", "positive", "negative", "vibration",
                      "female", "male", "rhythm", "above", "below",
                      "cause", "effect", "^0", "^1", "^2", "^3", "^4",
                      "^5", "^6", "^7", "^8", "^9"]
    },
    # CAS-specific math
    {
        "id": "cas_rpm",
        "query": "What is the RPM (Recursive Prerequisite Model) in CAS?",
        "telltale": ["section-retraction", "prerequisite gate", "adjunction",
                      "rpm monad", "capability pathway", "a0 → dn → wn → pn"]
    },
    {
        "id": "cas_fisher_rao",
        "query": "How does CAS use the Fisher-Rao metric?",
        "telltale": ["open probability simplex", "40-dim", "geodesic distance",
                      "2*arccos", "cognitive state vector"]
    },
    # Project-level
    {
        "id": "cas_harness",
        "query": "What is CAS Harness?",
        "telltale": ["jacobian lens", "j-space", "cas-ohm", "pythia", "hidden state",
                      "gate 1", "gate 2", "evidence packet"]
    },
]


def score_response(response_text: str, telltale: list[str]) -> float:
    """Score 0-1 based on how many telltale keywords appear in the response.
    
    A score of 0 means zero telltale words found (fully blind).
    A score near 1 means many telltale words found (likely exposed).
    """
    text_lower = response_text.lower()
    hits = sum(1 for t in telltale if t.lower() in text_lower)
    # Normalize: if >50% of telltales hit, score=1; linear between
    return min(1.0, hits / max(1, len(telltale) * 0.5))


def probe_model(model_id: str, api_key: str = None, base_url: str = None) -> dict:
    """Run all probe queries against the model and return scores."""
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai package required. Install with: pip install openai")
        sys.exit(1)
    
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"),
                    base_url=base_url or os.environ.get("OPENAI_BASE_URL"))
    
    results = []
    for pq in PROBE_QUERIES:
        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": pq["query"]}],
                max_tokens=256,
                temperature=0.0
            )
            text = resp.choices[0].message.content or ""
            score = score_response(text, pq["telltale"])
            results.append({
                "id": pq["id"],
                "query": pq["query"],
                "response_preview": text[:200],
                "telltale_hits": [t for t in pq["telltale"] if t.lower() in text.lower()],
                "score": round(score, 4)
            })
        except Exception as e:
            results.append({
                "id": pq["id"],
                "error": str(e),
                "score": None
            })
    
    valid_scores = [r["score"] for r in results if r["score"] is not None]
    mean_score = float(np.mean(valid_scores)) if valid_scores else 1.0
    
    return {
        "model_id": model_id,
        "probed_at_utc": datetime.now(timezone.utc).isoformat(),
        "num_queries": len(PROBE_QUERIES),
        "num_completed": len(valid_scores),
        "mean_blindness_score": round(mean_score, 4),
        "per_query": results
    }


def main():
    parser = argparse.ArgumentParser(description="Probe an AI model for TKS/CAS exposure")
    parser.add_argument("--model", required=True, help="Model ID (e.g. gpt-4o, claude-3-opus)")
    parser.add_argument("--threshold", type=float, default=0.3,
                        help="Max mean score to pass blindness check (default 0.3)")
    parser.add_argument("--output", default=None, help="Output JSON file")
    parser.add_argument("--api-key", default=None, help="API key (or set OPENAI_API_KEY)")
    parser.add_argument("--base-url", default=None, help="API base URL")
    args = parser.parse_args()
    
    print(f"Probing {args.model} for TKS/CAS exposure...")
    report = probe_model(args.model, args.api_key, args.base_url)
    
    passed = report["mean_blindness_score"] < args.threshold
    report["passed_blindness_check"] = passed
    report["threshold"] = args.threshold
    
    print(f"\nMean blindness score: {report['mean_blindness_score']:.4f} "
          f"(threshold: {args.threshold})")
    print(f"Verdict: {'PASS — model appears BLIND to TKS/CAS' if passed else 'FAIL — model shows TKS/CAS exposure'}")
    
    if not passed:
        print("\nWARNING: This model may have been exposed to TKS/CAS materials.")
        print("Using it to generate the independent bank would violate R1.")
        print("Try a different model or a model with a known training cutoff before TKS publication.")
    
    # Per-query detail
    for r in report["per_query"]:
        status = "PASS" if (r["score"] or 1.0) < args.threshold else "FAIL"
        print(f"  {r['id']:30s} score={r['score']:.4f}  {status}")
    
    out_path = args.output or f"blindness_probe_{args.model.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nFull report: {out_path}")


if __name__ == "__main__":
    main()
