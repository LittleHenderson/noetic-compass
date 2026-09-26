"""One explicit two-job operator. The separate recurring monitor is read-only."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import time
import prepare_replication as admission
import provider_gates as provider

HERE = Path(__file__).resolve().parent
ROOT = admission.ROOT
COORD = Path("D:/tksCAS-worktrees/codex-cas-closed-loop-1/.coordination")

def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)

def successful_terminal(result, receiver, worker, row):
    """Science scores never decide whether seed two runs."""
    check = admission.require
    check(result.get("job") == receiver.get("job") == worker.get("job") == row["job"], "TERMINAL_JOB")
    check(result.get("completed_deliverable") is True and result.get("status") == "AWS_CANDIDATE_FINISHED", "DELIVERABLE_FAILED")
    check(result["cleanup"]["complete"] is True and not result["cleanup"]["failures"], "OPERATOR_CLEANUP")
    check(receiver["collection"] == "COMPLETE_VERIFIED" and receiver["required_count"] == 128 and not receiver["failures"], "RECEIVER_FAILED")
    integrity = receiver["byte_integrity"]
    check(integrity["state"] == "COMPLETE_VERIFIED" and integrity["verified_count"] == integrity["required_count"] == 128
          and not any(integrity[k] for k in ("missing","mismatched","unavailable")), "RECEIVER_BYTES")
    summary = worker["summary"]
    check(worker["status"] == "TYPED_POINTER_DELIVERED" and summary["status"] == "COMPLETE_TYPED_POINTER_ARM", "WORKER_FAILED")
    check(summary["source_sha"] == admission.SOURCE and summary["model_seed"] == row["seed"], "WORKER_SOURCE_SEED")
    check(summary["main_training_delta"]["optimizer_updates"] == 2940, "MAIN_UPDATE_COUNT")
    check([x["pass"] for x in summary["pass_summaries"]] == list(range(1,21))
          and all(x["updates"] == 147 for x in summary["pass_summaries"]), "PASS_COUNTS")
    check(summary["runtime"]["torch_version"] == "2.11.0+cu128"
          and summary["runtime"]["cuda_version"] == "12.8"
          and "RTX PRO 4500" in summary["runtime"]["gpu_name"], "ENVIRONMENT_CHANGED")
    return True

def verify_frozen(freeze):
    for name, expected in freeze["file_hashes"].items():
        path = (HERE / name).resolve()
        admission.require(path.is_relative_to(ROOT), "FREEZE_PATH")
        admission.require(admission.digest(path.read_bytes()) == expected, "FROZEN_FILE_CHANGED:" + name)
    head = subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT, text=True).strip()
    admission.require(head == freeze["admission_commit"], "ADMISSION_HEAD_CHANGED")
    dirty = subprocess.check_output(["git","status","--porcelain","--untracked-files=no"], cwd=ROOT, text=True)
    admission.require(not dirty.strip(), "TRACKED_FILES_DIRTY")
    admission.verify_source_and_package()

def run(freeze_hash):
    raw = (HERE / "EXECUTION_FREEZE.json").read_bytes()
    admission.require(admission.digest(raw) == freeze_hash, "EXECUTION_FREEZE_HASH")
    freeze = json.loads(raw)
    plan = admission.load_plan(freeze["plan_sha256"])
    verify_frozen(freeze)
    admission.require(freeze["validation_status"] == "PASS_HELM_REPLICATION_VALIDATION_ONLY"
                      and freeze["focused_public_review"] == "NO_BLOCKING_FINDINGS", "PRELAUNCH_GATES")
    admission.require(Decimal(freeze["total_all_services_ceiling_usd"]) == Decimal("41.00")
                      and Decimal(plan["budget"]["new_campaign_cap_usd"]) == Decimal("45.00"), "FINITE_CAMPAIGN")
    state = {"schema":"helm.replication.operator/1","started_utc":provider.utc(),"freeze_sha256":freeze_hash,
             "operator_pid":__import__("os").getpid(),"automatic_retries":0,
             "seeds":[{"seed":r["seed"],"job":r["job"],"state":"NOT_LAUNCHED"} for r in plan["jobs"]]}
    write_new(HERE / "CAMPAIGN_ATTEMPT_STARTED.json", state)
    def save(phase):
        state["updated_utc"] = provider.utc()
        state["phase"] = phase
        temporary = HERE / "operator_state.tmp"
        temporary.write_text(json.dumps(state,indent=2)+"\n",encoding="utf-8")
        temporary.replace(HERE / "operator_state.json")
    def heartbeat(phase):
        save(phase)
        row = {"utc":provider.utc(),"agent":"Codex","status":"PROGRESS","current_task":"HELM-CM2X-REPLICATION-2",
               "work_done_since_last_heartbeat":phase,"blocker":state.get("error"),
               "next_action":"Frozen operator sequences only the two authorized jobs; monitor cannot launch.",
               "relevant_commit_or_file":str(HERE/"operator_state.json"),
               "paid_cloud_work_active":any(s["state"]=="OPERATOR_RUNNING" for s in state["seeds"])}
        with (COORD/"codex_heartbeat.jsonl").open("a",encoding="utf-8") as stream:
            stream.write(json.dumps(row)+"\n")
    try:
        for row, current in zip(plan["jobs"], state["seeds"]):
            verify_frozen(freeze)
            receipt = ROOT / row["receipt_dir"]
            admission.require(not receipt.exists(), "RECEIPT_ALREADY_EXISTS")
            preflight = provider.before_launch(plan)
            write_new(HERE/"observations"/(str(row["seed"])+"_prelaunch.json"), preflight)
            study = json.loads((HERE/"admission"/str(row["seed"])/"study.json").read_bytes())
            ledger = admission.launch.validate_ledger_path(admission.launch.CANONICAL_LEDGER)
            ledger_doc = json.loads(ledger.read_bytes())
            admission.require(not any(x["job"] == row["job"] for x in ledger_doc["reservations"]), "JOB_ALREADY_RESERVED")
            logdir = HERE/"operator_logs"
            logdir.mkdir(exist_ok=True)
            with (logdir/(str(row["seed"])+".stdout")).open("xb") as out, (logdir/(str(row["seed"])+".stderr")).open("xb") as err:
                child = subprocess.Popen([sys.executable,"-B",str(HERE/"launch_replication.py"),*study["job_record"]["launch_argv"]],
                                         cwd=ROOT, stdout=out, stderr=err, stdin=subprocess.DEVNULL)
                current.update(state="OPERATOR_RUNNING",child_pid=child.pid,operator_started_utc=provider.utc())
                heartbeat("Executing seed "+str(row["seed"])+" with unchanged science; process existence alone is not proof of training.")
                while child.poll() is None:
                    time.sleep(30)
                    save("Executing seed "+str(row["seed"]))
                    if time.monotonic() - state.get("_last_heartbeat",0) >= 240:
                        heartbeat("Executing seed "+str(row["seed"])+"; independent guest and instance deadlines remain active.")
                        state["_last_heartbeat"] = time.monotonic()
                current["operator_exit_code"] = child.returncode
            admission.require(child.returncode == 0, "TRAINING_OPERATOR_EXIT:" + str(child.returncode))
            result = json.loads((receipt/"result.json").read_bytes())
            receiver = json.loads((receipt/"receiver_receipt.json").read_bytes())
            worker = json.loads((receipt/"curriculum_result.json").read_bytes())
            successful_terminal(result,receiver,worker,row)
            cleanup = provider.cleanup(row["job"],result["launch"]["instance_id"])
            write_new(HERE/"observations"/(str(row["seed"])+"_independent_cleanup.json"),cleanup)
            admission.require(cleanup["all_passed"], "INDEPENDENT_CLEANUP_FAILED")
            current.update(state="COMPLETED_VERIFIED",finished_utc=provider.utc(),
                           instance_id=result["launch"]["instance_id"],required_artifacts_verified=128,
                           receiver_sha256=admission.digest((receipt/"receiver_receipt.json").read_bytes()))
            heartbeat("Seed "+str(row["seed"])+" completed; all 128 required artifacts and cleanup verified. No score-based selection.")
        save("BOTH_RUNS_COMPLETED_AWAITING_PUBLIC_RESULTS_REVIEW")
    except BaseException as exc:
        state["error"] = str(exc)
        state["error_type"] = type(exc).__name__
        if hasattr(exc,"public_record"):
            state["failed_provider_gate"] = exc.public_record
        for current in state["seeds"]:
            if current["state"] == "OPERATOR_RUNNING":
                current["state"] = "OPERATIONAL_FAILURE_NO_RETRY"
            elif current["state"] == "NOT_LAUNCHED":
                current["state"] = "NOT_LAUNCHED_BLOCKED"
        heartbeat("STOPPED_ON_OPERATIONAL_FAILURE_NO_RETRY")
        raise
    finally:
        state.pop("_last_heartbeat",None)
        save(state["phase"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute",action="store_true",required=True)
    parser.add_argument("--freeze-sha256",required=True)
    args = parser.parse_args()
    run(args.freeze_sha256)
