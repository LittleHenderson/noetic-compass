"""Deterministic report generator. Reads CLAIM_LEDGER.json and every
reports/*.json, writes replication/FINAL_RESULTS.json. No model, no RNG."""
import glob
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ledger = json.load(open(os.path.join(ROOT, "CLAIM_LEDGER.json"),
                            encoding="utf-8"))
    reports = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "reports", "*.json"))):
        reports[os.path.basename(f)] = {
            "sha256": sha(f),
            "content": json.load(open(f, encoding="utf-8"))}
    summary = {
        "schema": "eta_epsilon_weight_learning.final_results.v0.1",
        "study_scope": "GENERIC interpretability-guided training (B1: "
                       "40-state CAS framing dropped). NOT a test of "
                       "CAS-specific value.",
        "model": "Qwen/Qwen2.5-0.5B-Instruct @ 7ae557604adf...",
        "claims": {c["id"]: {"status": c["status"],
                             "evidence_tier": c.get("evidence_tier")}
                   for c in ledger["claims"]},
        "external_replication_status": "REPLICATION_OPEN",
        "report_files": {k: v["sha256"] for k, v in reports.items()},
        "reports": reports,
    }
    out = os.path.join(HERE, "FINAL_RESULTS.json")
    json.dump(summary, open(out, "w", encoding="utf-8"), indent=2)
    print("claims:")
    for cid, c in summary["claims"].items():
        print(f"  {cid:26s} {c['status']}")
    print("wrote", out)


if __name__ == "__main__":
    main()
