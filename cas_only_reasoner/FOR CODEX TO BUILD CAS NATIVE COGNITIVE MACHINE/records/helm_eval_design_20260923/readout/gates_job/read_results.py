"""Read the gates job's downloaded results ON THE LAPTOP (small JSON and text only; no course, no grader, no AWS call).
CLAUDE_BUILT_CLAUDE_CHECKED.

    python read_results.py --mode 1|2        # writes RESULTS_READING_mode<N>.json (create-only); exit 0 only for JOB_ACCEPTED

JOB_ACCEPTED needs every one of these:
  * THIS LAUNCH PRODUCED THESE FILES: the watch record's instance id and launch time equal the launch record's; outcome
    RESULTS_RECEIVED; files downloaded > 0; final state terminated; job_status equals results/STATUS and is "done";
    exactly one "JOB START <utc>" line in job.log, inside [launched_utc, watch_ended_utc]; env.txt has exactly one
    instance_id= line (IMDSv2) and it equals the launched instance; env.txt's bundle_sha256 equals the launch record's.
  * THE JOB'S OWN DECISION: GATES_JOB_RESULT.json says overall ALL_PASS for this mode.
  * MODE 1 AGAIN, INDEPENDENTLY: the downloaded gate_reading_fresh.json hashes to the committed Helm 2.0 reading's sha256
    (52877c16...) here on the laptop, and its label and H1 per seed are NO_TRANSFER_TO_NEW_WORLDS, 11/1, 12/0, 7/1.
Labels: CLAUDE_BUILT_CLAUDE_CHECKED; EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import machine_gates as MG  # noqa: E402

JOB_START = re.compile(r"^JOB START (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$")


def _utc(text):
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None


def _json(path):
    try:
        return json.loads(pathlib.Path(path).read_bytes())
    except (OSError, ValueError):
        return None


def _text(path):
    try:
        return pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def read(here, mode):
    here = pathlib.Path(here)
    launch = _json(here / ("launch_record_mode%d.json" % mode)) or {}
    watch = _json(here / ("watch_record_mode%d.json" % mode)) or {}
    res = here / ("results_mode%d" % mode)
    problems = []
    if not launch.get("instance_id") or watch.get("instance_id") != launch.get("instance_id") \
            or watch.get("launched_utc") != launch.get("launched_utc") or watch.get("mode") != mode:
        problems.append("WATCH_NOT_FOR_THIS_LAUNCH")
    if watch.get("outcome") != "RESULTS_RECEIVED" or not isinstance(watch.get("files_downloaded"), int) \
            or watch["files_downloaded"] <= 0 or watch.get("final_state") != "terminated":
        problems.append("WATCH_OUTCOME:%s/%s/%s" % (watch.get("outcome"), watch.get("files_downloaded"), watch.get("final_state")))
    status = (_text(res / "STATUS") or "").strip()
    if status != "done" or watch.get("job_status") != status:
        problems.append("JOB_STATUS:%r/%r" % (status, watch.get("job_status")))
    starts = [m.group(1) for m in (JOB_START.match(line.strip()) for line in (_text(res / "job.log") or "").splitlines()) if m]
    start, lo, hi = (_utc(starts[0]) if len(starts) == 1 else None), _utc(launch.get("launched_utc")), _utc(watch.get("watch_ended_utc"))
    if start is None or lo is None or hi is None or not lo <= start <= hi:
        problems.append("JOB_START_NOT_IN_THIS_LAUNCH:%s" % starts)
    env = (_text(res / "env.txt") or "").splitlines()
    ids = [line.split("=", 1)[1].strip() for line in env if line.startswith("instance_id=")]
    if ids != [launch.get("instance_id")]:
        problems.append("MACHINE_INSTANCE_ID:%s" % ids)
    bundles = [line.split("=", 1)[1].strip() for line in env if line.startswith("bundle_sha256=")]
    if bundles != [launch.get("bundle_sha256")]:
        problems.append("BUNDLE_SHA256:%s" % bundles)
    result = _json(res / "GATES_JOB_RESULT.json") or {}
    if result.get("overall") != "ALL_PASS" or result.get("mode") != mode:
        problems.append("JOB_RESULT:%s %s" % (result.get("overall"), (result.get("failures") or [])[:4]))
    if mode == 1:
        fresh = res / "gate_reading_fresh.json"
        data = fresh.read_bytes() if fresh.is_file() else b""
        if hashlib.sha256(data).hexdigest() != MG.MODE1_EXPECT["reading_sha256"]:
            problems.append("LAPTOP_RECHECK_READING_SHA256:%s" % hashlib.sha256(data).hexdigest())
        else:
            summary = MG.gate_summary(json.loads(data))
            verdict, reasons = MG.mode1_verdict(hashlib.sha256(data).hexdigest(), summary)
            if verdict != "GATES_REPRODUCED":
                problems.append("LAPTOP_RECHECK:%s" % reasons)
    return {"schema": "claude.gates-job-results-reading/0.1", "mode": mode,
            "verdict": "JOB_ACCEPTED" if not problems else "JOB_NOT_ACCEPTED", "problems": problems,
            "instance_id": launch.get("instance_id"), "gates_verdict": result.get("gates_verdict"),
            "rescorer_verdict": result.get("rescorer_verdict"), "cost_upper_bound_usd": watch.get("cost_upper_bound_usd"),
            "label": "CLAUDE_BUILT_CLAUDE_CHECKED", "custody": MG.CUSTODY}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    reading = read(HERE, args.mode)
    with open(HERE / ("RESULTS_READING_mode%d.json" % args.mode), "x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(reading, indent=1, sort_keys=True))
    print(json.dumps(reading, indent=1, sort_keys=True))
    return 0 if reading["verdict"] == "JOB_ACCEPTED" else 1


if __name__ == "__main__":
    sys.exit(main())
