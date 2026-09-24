"""Read a finished P1b job on the laptop ($0, JSON only, no torch). CLAUDE_BUILT_CLAUDE_CHECKED.

    python -B read_results.py --mode acceptance|reading [--root DIR]

It binds the downloaded results to the launched machine (IMDSv2 instance id, AMI, instance type, bundle sha256 in
env.txt against launch_record_<mode>.json and watch_record_<mode>.json) and reports the machine's own decision
(P1B_JOB_RESULT.json). It prints the sha256 of the file the next record binds: the acceptance receipt (the
READING_ELIGIBILITY.json field reader_acceptance.receipt_sha256), or the reading evidence (committed ONCE at
records/typed_pointer_001/evidence_unchanged_repro_20260917/reproduction_evidence.json). It gives NO reproduction
verdict: that comes only from read_reproduction.py at the receipt commit.
"""
import argparse
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
OVERALL_PASS = {"acceptance": "P1B_ACCEPTANCE_RUN_PASS", "reading": "P1B_READING_EVIDENCE_WRITTEN"}
PRODUCT = {"acceptance": "reader_acceptance_receipt.json", "reading": "reproduction_evidence.json"}


def env_fields(text):
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line and not line.startswith(" "))


def read(root, mode):
    root = pathlib.Path(root)
    problems = []

    def load(path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            problems.append("UNREADABLE:" + path.name)
            return {}
    launch = load(root / ("launch_record_%s.json" % mode))
    watch = load(root / ("watch_record_%s.json" % mode))
    res = root / ("results_%s" % mode)
    env = env_fields((res / "env.txt").read_text(encoding="utf-8")) if (res / "env.txt").is_file() else {}
    status = (res / "STATUS").read_text(encoding="utf-8").strip() if (res / "STATUS").is_file() else None
    result = load(res / "P1B_JOB_RESULT.json")
    iid = launch.get("instance_id")
    if not iid or env.get("instance_id") != iid or watch.get("instance_id") != iid:
        problems.append("MACHINE_INSTANCE_ID_DOES_NOT_BIND:%s/%s/%s" % (iid, env.get("instance_id"), watch.get("instance_id")))
    if env.get("ami_id") != launch.get("ami") or env.get("instance_type") != launch.get("approved", {}).get("machine"):
        problems.append("MACHINE_AMI_OR_TYPE:%s/%s" % (env.get("ami_id"), env.get("instance_type")))
    if env.get("bundle_sha256") != (launch.get("bundle") or {}).get("sha256"):
        problems.append("BUNDLE_SHA256_DOES_NOT_BIND")
    if watch.get("final_state") not in ("terminated", "gone", "shutting-down"):
        problems.append("MACHINE_NOT_CONFIRMED_GONE:%s" % watch.get("final_state"))
    if status != "done" or result.get("overall") != OVERALL_PASS[mode] or result.get("problems") != []:
        problems.append("JOB_NOT_DONE:%s/%s/%s" % (status, result.get("overall"), result.get("problems")))
    product = res / PRODUCT[mode]
    digest = hashlib.sha256(product.read_bytes()).hexdigest() if product.is_file() else None
    if digest is None:
        problems.append("PRODUCT_MISSING:" + PRODUCT[mode])
    return {"mode": mode, "verdict": "JOB_ACCEPTED" if not problems else "JOB_NOT_ACCEPTED", "problems": problems,
            "instance_id": iid, "job_status": status, "overall": result.get("overall"),
            "product": {"file": PRODUCT[mode], "sha256": digest},
            "cost_upper_bound_usd": watch.get("cost_upper_bound_usd"),
            "note": "No reproduction verdict here; read_reproduction.py at the receipt commit gives it."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=sorted(OVERALL_PASS), required=True)
    parser.add_argument("--root", default=str(HERE))
    args = parser.parse_args()
    reading = read(args.root, args.mode)
    print(json.dumps(reading, indent=1, sort_keys=True))
    return 0 if reading["verdict"] == "JOB_ACCEPTED" else 1


if __name__ == "__main__":
    sys.exit(main())
