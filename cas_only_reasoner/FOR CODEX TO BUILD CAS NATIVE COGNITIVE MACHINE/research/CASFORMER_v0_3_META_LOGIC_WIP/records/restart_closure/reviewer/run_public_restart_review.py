"""Internal separate-agent public CLI restart rerun; not an external GLM audit."""

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
import sys


OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[2]
SOURCE_SHA = "cbce17dad55b61ffc0f77860324ca1e9ffad3746"
sys.path.insert(0, str(ROOT))

from cas_cjt import validate_contract
from cas_meta.demo import semantic_projection
from cas_meta.fixture import open_native
from cas_meta.trace import validate_meta_events


def write_json(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def head_sha():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


COMMANDS = []


def run_cli(name, *arguments):
    argv = [sys.executable, "-m", "cas_meta.demo", *map(str, arguments)]
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, check=False)
    (OUTPUT / (name + ".stdout.txt")).write_bytes(result.stdout)
    (OUTPUT / (name + ".stderr.txt")).write_bytes(result.stderr)
    COMMANDS.append({"name": name, "argv": argv, "cwd": str(ROOT), "returncode": result.returncode,
                     "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat()})
    write_json("commands.json", COMMANDS)
    return result


def snapshot(bundle, name):
    native = open_native(bundle / "compiled.db")
    try:
        traces = native.store.trace_events()
        for trace in traces:
            validate_contract(trace)
        projection = semantic_projection(native)
        parameter_hash = sha256()
        for parameter_name, parameter in sorted(native.network.state_dict().items()):
            parameter_hash.update(parameter_name.encode("utf-8"))
            parameter_hash.update(str(parameter.dtype).encode("ascii"))
            parameter_hash.update(str(tuple(parameter.shape)).encode("ascii"))
            parameter_hash.update(parameter.detach().cpu().contiguous().numpy().tobytes())
        result = {
            "native_head": asdict(native.store.head),
            "native_trace_count": len(traces),
            "producer_sequence": [trace["candidate_effects"][0]["producer_cjt_id"] for trace in traces],
            "verdict_sequence": [trace["verifier_receipts"][0]["disposition"] for trace in traces],
            "model_digest": native.state.model_digest,
            "network_state_dict_sha256": parameter_hash.hexdigest(),
            "open_C_repair_ids": list(native.state.by_cjt_id["C"].rpm.open_repair_ids),
            "native_schema_valid_count": len(traces),
            "published_effect_count": sum(len(item["published_effects"]) for item in projection),
        }
        write_json(name + "_native_traces.json", traces)
        write_json(name + "_semantic_projection.json", projection)
        write_json(name + "_snapshot.json", result)
        return result, projection
    finally:
        native.close()


def main():
    assert head_sha() == SOURCE_SHA, "source commit changed before rerun"
    bundle = OUTPUT / "prepared_bundle"
    assert not bundle.exists(), "reviewer output must be new"
    write_json("environment.json", {"python": sys.version, "executable": sys.executable,
                                    "platform": platform.platform(), "source_sha": SOURCE_SHA,
                                    "classification": "INTERNAL_SEPARATE_AGENT_RERUN_NOT_EXTERNAL_GLM_AUDIT"})
    prepare = run_cli("prepare", "--prepare", bundle)
    assert prepare.returncode == 0, prepare.stderr.decode("utf-8", errors="replace")
    creation = json.loads((bundle / "creation_receipt.json").read_text(encoding="utf-8"))
    checkpoint_bytes = (bundle / "checkpoint.json").read_bytes()
    checkpoint = json.loads(checkpoint_bytes)
    expected_digest = creation["checkpoint_digest"]
    assert sha256(checkpoint_bytes).hexdigest() == expected_digest
    assert [frame["procedure"] for frame in creation["frames"]] == ["main", "worker", "repair_c"]
    assert creation["frames"] == checkpoint["frames"]
    assert creation["spent"] == 288 and creation["remaining"] == 224
    before, before_projection = snapshot(bundle, "before_resume")
    assert before["native_head"] == creation["native_head"] == checkpoint["head"]
    assert before["producer_sequence"] == ["A", "B", "C", "R"]
    validate_meta_events(checkpoint["events"])

    resumed = run_cli("resume", "--resume", bundle, "--expected-digest", expected_digest)
    assert resumed.returncode == 0, resumed.stderr.decode("utf-8", errors="replace")
    worker = json.loads((bundle / "worker_result.json").read_text(encoding="utf-8"))
    events = json.loads((bundle / "meta_trace.json").read_text(encoding="utf-8"))
    validate_meta_events(events)
    after, after_projection = snapshot(bundle, "after_resume")
    assert worker["restored_frames"] == creation["frames"]
    assert worker["native_head_before"] == before["native_head"]
    assert worker["native_head_after"] == after["native_head"]
    assert worker["spent_before"] == 288 and worker["spent"] == 360
    assert worker["remaining_after"] == 152 and worker["done"] is True
    assert after["producer_sequence"] == ["A", "B", "C", "R", "C"]
    assert after["verdict_sequence"] == ["ACCEPT", "ACCEPT", "REPAIR", "ACCEPT", "ACCEPT"]
    assert after["producer_sequence"].count("R") == 1
    assert after["published_effect_count"] == 4 and after["open_C_repair_ids"] == []
    assert before["model_digest"] == after["model_digest"] == creation["model_digest"]
    assert before["network_state_dict_sha256"] == after["network_state_dict_sha256"]
    assert after_projection[:4] == before_projection
    assert events[:len(checkpoint["events"])] == checkpoint["events"]

    stale = run_cli("second_resume_rejected", "--resume", bundle, "--expected-digest", expected_digest)
    assert stale.returncode != 0 and b"NATIVE_HEAD_MISMATCH" in stale.stderr
    after_rejection, rejection_projection = snapshot(bundle, "after_stale_rejection")
    assert after_rejection == after and rejection_projection == after_projection
    assert head_sha() == SOURCE_SHA, "source commit changed during rerun"
    receipt = {
        "status": "INTERNAL_SEPARATE_AGENT_PUBLIC_RESTART_RERUN_PASSED",
        "classification": "INTERNAL_SEPARATE_AGENT_RERUN_NOT_EXTERNAL_GLM_AUDIT",
        "source_sha": SOURCE_SHA,
        "checkpoint_digest": expected_digest,
        "public_cli_returncodes": {entry["name"]: entry["returncode"] for entry in COMMANDS},
        "restored_frames": worker["restored_frames"],
        "native_head_before": before["native_head"],
        "native_head_after": after["native_head"],
        "policy_units_before": 288, "policy_units_after": 360, "policy_units_remaining": 152,
        "producer_sequence": after["producer_sequence"], "R_count": 1,
        "published_effect_count": 4, "native_schema_valid_count": 5,
        "meta_schema_valid_count": len(events),
        "fixed_model_digest": after["model_digest"],
        "fixed_network_state_dict_sha256": after["network_state_dict_sha256"],
        "prior_native_projection_unchanged": True, "prior_meta_events_unchanged": True,
        "repair_closed": True, "second_resume_rejection": "NATIVE_HEAD_MISMATCH",
        "second_resume_native_state_unchanged": True,
        "claim_boundary": "Fixed fixture, clean-boundary restart only; no crash-atomic recovery or external audit claim."
    }
    write_json("receipt.json", receipt)
    hashes = {str(path.relative_to(OUTPUT)).replace("\\", "/"): sha256(path.read_bytes()).hexdigest()
              for path in sorted(OUTPUT.rglob("*")) if path.is_file() and path.name != "payload_sha256.json"}
    write_json("payload_sha256.json", hashes)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
