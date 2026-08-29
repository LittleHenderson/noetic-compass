"""Phase 4.3: run the expanded battery in HYBRID_COMMIT and
NATIVE_ONLY, grade with the one grading law, seal the results.

The headline numbers come from the HELD_OUT split; dev/calibration
are reported separately; the protected split is reported ONLY as
aggregate counts (its per-item outcomes stay out of the tuning loop).
Determinism leg: a fixed sample of cortex-routed held-out items runs
twice and must produce identical sealed traces.
"""

import hashlib
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from battery.battery import build_battery, grade_item, split_counts
from cortex.adapter import CortexAdapter
from cortex.router import HybridRouter


def utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def summarize(results):
    by_split = defaultdict(lambda: defaultdict(int))
    by_category = defaultdict(lambda: defaultdict(int))
    for row in results:
        by_split[row["split"]][row["outcome"]] += 1
        by_category[row["category"]][row["outcome"]] += 1

    def rates(counts):
        total = sum(counts.values())
        return {"total": total,
                "pass": counts.get("PASS", 0),
                "honest_miss": counts.get("HONEST_MISS", 0),
                "fabrication": counts.get("FABRICATION", 0),
                "pass_rate": round(counts.get("PASS", 0) / total, 4)
                if total else None,
                "fabrication_rate": round(
                    counts.get("FABRICATION", 0) / total, 4)
                if total else None}

    return ({split: rates(counts) for split, counts in by_split.items()},
            {cat: rates(counts) for cat, counts in by_category.items()})


def main():
    utf8()
    items = build_battery()
    print(f"battery: {len(items)} items, splits {split_counts(items)}")

    print("loading the cortex (snapshot-pinned, resident)...")
    adapter = CortexAdapter()
    hybrid = HybridRouter(mode="HYBRID_COMMIT", cortex=adapter)
    native = HybridRouter(mode="NATIVE_ONLY")

    hybrid_results, native_results = [], []
    routes = defaultdict(int)
    for n, item in enumerate(items, 1):
        trace_h = hybrid.turn(item["sentence"])
        routes[trace_h["route"]] += 1
        hybrid_results.append(grade_item(item, trace_h))
        trace_n = native.turn(item["sentence"])
        native_results.append(grade_item(item, trace_n))
        if n % 25 == 0:
            print(f"  {n}/{len(items)} items done")

    # determinism leg: fixed sample of cortex-routed held-out items
    sample = [r["item_id"] for r in hybrid_results
              if r["split"] == "held_out" and r["route"] == "cortex"][:12]
    by_id = {item["item_id"]: item for item in items}
    determinism = []
    fresh = HybridRouter(mode="HYBRID_COMMIT", cortex=adapter)
    for item_id in sample:
        sentence = by_id[item_id]["sentence"]
        first = fresh.turn(sentence)
        second = fresh.turn(sentence)
        determinism.append({"item_id": item_id,
                            "identical": first["trace_digest"]
                            == second["trace_digest"]})
    deterministic = all(d["identical"] for d in determinism)

    hybrid_splits, hybrid_categories = summarize(hybrid_results)
    native_splits, _ = summarize(native_results)

    latencies = sorted(adapter.latencies)
    latency = {
        "count": len(latencies),
        "min_s": latencies[0] if latencies else None,
        "median_s": latencies[len(latencies) // 2] if latencies else None,
        "max_s": latencies[-1] if latencies else None,
        "total_s": round(sum(latencies), 1),
    }

    packet = {
        "battery": "PHASE4_BATTERY_v1",
        "items": len(items),
        "split_counts": split_counts(items),
        "routes": dict(routes),
        "headline_note": "headline numbers are the HELD_OUT split; "
                         "the protected split reports aggregates only; "
                         "all splits are developer-visible in-repo - "
                         "'protected' means excluded from tuning, not "
                         "hidden (recorded caveat)",
        "hybrid": {"by_split": hybrid_splits,
                   "by_category": hybrid_categories},
        "native_only": {"by_split": native_splits},
        "determinism": {"sampled": len(determinism),
                        "all_identical": deterministic},
        "latency": latency,
        "model_receipt": adapter.receipt,
        "baseline_comparison": {
            "sealed_smoke": "H2H-v0 (CORTEX_H2H_v0.1/output/"
                            "h2h_results.json, digest db34d2e9d0214df4)",
            "note": "the 20-item smoke stays sealed and unchanged; "
                    "this battery supersedes it for capability claims",
        },
        "per_item": {"hybrid": hybrid_results,
                     "native_only": native_results},
    }
    packet["battery_digest"] = _digest(packet)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "output")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "battery_results.json"), "w",
              encoding="utf-8") as fh:
        json.dump(packet, fh, indent=1, sort_keys=True)

    print("\n==== HELD-OUT HEADLINE (hybrid) ====")
    print(json.dumps(hybrid_splits.get("held_out", {}), indent=1))
    print("==== per category (hybrid, all splits) ====")
    for cat in sorted(hybrid_categories):
        r = hybrid_categories[cat]
        print(f"  {cat:<24} pass {r['pass']}/{r['total']}"
              f"  fabrication {r['fabrication']}")
    print(f"determinism: {deterministic} ({len(determinism)} sampled)")
    print(f"latency: median {latency['median_s']}s over "
          f"{latency['count']} generations")
    print(f"sealed: output/battery_results.json "
          f"(digest {packet['battery_digest']})")


if __name__ == "__main__":
    main()
