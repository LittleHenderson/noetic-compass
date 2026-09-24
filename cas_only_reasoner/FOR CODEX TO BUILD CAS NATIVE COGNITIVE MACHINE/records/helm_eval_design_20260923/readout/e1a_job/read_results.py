"""Read E1a's downloaded results ON THE LAPTOP (small JSON and text only; no torch, no course, no AWS call).
CLAUDE_BUILT_CLAUDE_CHECKED.

    python read_results.py        # writes RESULTS_READING.json (create-only); exit 0 only for JOB_ACCEPTED

JOB_ACCEPTED means THIS LAUNCH PRODUCED THESE FILES and every stage produced its reading:
  * the watch record's instance id and launch time equal the launch record's; outcome RESULTS_RECEIVED; files
    downloaded > 0; final state terminated; no volume left with the job's name; job_status equals results/STATUS and
    is "done"; exactly one "JOB START <utc>" line in job.log inside [launched_utc, watch_ended_utc]; env.txt has
    exactly one instance_id= line (IMDSv2) and it is the launched instance; env.txt's bundle_sha256 is the launch
    record's;
  * E1A_RESULT.json says E1A_STAGES_COMPLETE.
JOB_ACCEPTED is about custody and completeness only. The answers are the stage WORDS it prints: the route receipt, the
probe validation, ITEM2 (with the mechanism gate), the matched start and the roster. It prints no analogy number.
The ITEM2 reading can be re-derived here from the returned raw tables (pure Python, the frozen metric):
    python -B ../probe-v03/item2_reader.py --inputs results/probe/ITEM2_INPUTS.json
Reading order (A5.1/A5.3/A5.5): do not compute any accuracy from the returned score tables.
Labels: CLAUDE_BUILT_CLAUDE_CHECKED; EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT.
"""
import datetime
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
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


def read(here):
    here = pathlib.Path(here)
    launch = _json(here / "launch_record.json") or {}
    watch = _json(here / "watch_record.json") or {}
    res = here / "results"
    problems = []
    if not launch.get("instance_id") or watch.get("instance_id") != launch.get("instance_id") \
            or watch.get("launched_utc") != launch.get("launched_utc"):
        problems.append("WATCH_NOT_FOR_THIS_LAUNCH")
    if watch.get("outcome") != "RESULTS_RECEIVED" or not isinstance(watch.get("files_downloaded"), int) \
            or watch["files_downloaded"] <= 0 or watch.get("final_state") != "terminated":
        problems.append("WATCH_OUTCOME:%s/%s/%s" % (watch.get("outcome"), watch.get("files_downloaded"), watch.get("final_state")))
    if watch.get("volumes_tagged_with_job_name") != []:
        problems.append("VOLUMES_LEFT_OR_UNCHECKED:%s" % (watch.get("volumes_tagged_with_job_name"),))
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
    result = _json(res / "E1A_RESULT.json") or {}
    if result.get("overall") != "E1A_STAGES_COMPLETE":
        problems.append("E1A_RESULT:%s missing=%s" % (result.get("overall"), result.get("missing_stage_readings")))
    return {"schema": "claude.e1a-results-reading/0.1", "verdict": "JOB_ACCEPTED" if not problems else "JOB_NOT_ACCEPTED",
            "problems": problems, "instance_id": launch.get("instance_id"), "stages": result.get("stages"),
            "mechanism_gate": result.get("mechanism_gate"), "gate_open_reasons": result.get("gate_open_reasons"),
            "cost_upper_bound_usd": watch.get("cost_upper_bound_usd"),
            "labels": ["CLAUDE_BUILT_CLAUDE_CHECKED", "EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT"]}


def main():
    reading = read(HERE)
    with open(HERE / "RESULTS_READING.json", "x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(reading, indent=1, sort_keys=True))
    print(json.dumps(reading, indent=1, sort_keys=True))
    return 0 if reading["verdict"] == "JOB_ACCEPTED" else 1


if __name__ == "__main__":
    sys.exit(main())
