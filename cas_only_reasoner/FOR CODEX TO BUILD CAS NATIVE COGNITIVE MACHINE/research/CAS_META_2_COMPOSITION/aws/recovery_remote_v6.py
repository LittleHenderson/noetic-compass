"""AWS-only coordinator for a separately labelled replay of fixed v6 choices.

No training, generation, checkpoint selection, action editing or resealing.
The accepted executor and verifier run unchanged in spawned GPU processes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
GPU_TESTS = (
    "test_saved_case_zero_uses_frozen_reference_and_verifier",
    "test_saved_case_nine_contains_only_known_post_start_failure",
)


def require_request(job, enabled, max_seconds):
    if (enabled is not True or sys.platform != "linux"
            or type(max_seconds) is not int or not 2800 <= max_seconds <= 3000):
        raise ValueError("RECOVERY_REMOTE_AWS_LINUX_AND_BOUNDED_TIME_REQUIRED")
    if (type(job) is not str or not re.fullmatch(r"cas-meta2-[0-9]{14}-[0-9a-f]{8}", job)
            or job == "cas-meta2-20260906064703-c0d74ffa"):
        raise ValueError("RECOVERY_REMOTE_NEW_JOB_REQUIRED")
    if (os.environ.get("CAS_META2_RUN_CONTRAST_RECOVERY") != "1"
            or os.environ.get("CAS_META2_RUN_GPU_TESTS") != "1"
            or os.environ.get("CAS_META2_AWS_JOB_ID") != job
            or os.environ.get("CAS_META1_AWS_JOB_ID") != job):
        raise ValueError("RECOVERY_REMOTE_ENABLE_OR_JOB_MISMATCH")


def hash_file(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+"\n").encode())


def gpu_command(output, executable=sys.executable):
    output = Path(output)
    return [str(executable), "-B", "-m", "pytest", "-m", "gpu",
            "tests/test_contrast_recovery_v6_gpu.py", "-q",
            "--junitxml", str(output/"gpu_tests.xml"),
            "--basetemp", str(output/"gpu_scratch"),
            "-p", "no:cacheprovider", "-p", "cas_meta2.pytest_no_aliases_v4"]


def validate_xml(path):
    xml = ET.parse(path).getroot()
    cases = list(xml.iter("testcase"))
    suites = list(xml.iter("testsuite"))
    if (len(cases) != 2 or sorted(c.attrib.get("name", "") for c in cases) != sorted(GPU_TESTS)
            or any(not c.attrib.get("classname", "").endswith("test_contrast_recovery_v6_gpu") for c in cases)
            or any(list(xml.iter(tag)) for tag in ("failure", "error", "skipped"))
            or not suites or sum(int(s.attrib.get("tests", "-1")) for s in suites) != 2
            or any(int(s.attrib.get(k, "-1")) != 0
                   for s in suites for k in ("failures", "errors", "skipped"))):
        raise ValueError("RECOVERY_REMOTE_EXACT_TWO_GPU_TESTS_REQUIRED")
    return {"passed": 2, "tests": 2, "failures": 0, "errors": 0, "skipped": 0}


def native_command(args, gate_path, gate_pin, executable=sys.executable):
    return [str(executable), "-B", "-m", "cas_meta2.contrast_recovery_v6",
            "--admission", str(args.admission), "--admission-sha256", args.admission_sha256,
            "--recovery-manifest", str(args.recovery_manifest),
            "--recovery-manifest-sha256", args.recovery_manifest_sha256,
            "--inputs", str(args.inputs), "--packet", str(args.packet),
            "--output", str(Path(args.output)/"native"), "--job", args.job,
            "--max-seconds", "2400", "--enable-native-evaluation",
            "--gpu-gate", str(gate_path), "--gpu-gate-sha256", gate_pin]


def run(args):
    # This check precedes recovery/native imports, output creation and data reads.
    require_request(args.job, args.enable_native_evaluation, args.max_seconds)
    from cas_meta2.contrast_recovery_v6 import binding as b
    from cas_meta2.campaign_v3 import _run_process
    output = b.no_links(args.output)
    if (not output.resolve().is_relative_to(ROOT/"runs") or output.exists()
            or Path(args.inputs).absolute() != Path("/opt/cas-meta2/recovery_input")
            or Path(args.packet).absolute() != Path("/opt/cas-meta2/prior_packet.zip")):
        raise ValueError("RECOVERY_REMOTE_NEW_OUTPUT_AND_FIXED_INPUT_PATHS_REQUIRED")
    started = time.monotonic()
    deadline = started+args.max_seconds
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schema": "cas-meta2-recovery-coordinator/6", "job": args.job,
               "completed": False, "training_performed": False, "fresh_test": False,
               "predictions_reused_unchanged": True,
               "started_utc": datetime.now(timezone.utc).isoformat()}
    try:
        extraction = b.extract_fixed_packet(args.packet, args.inputs)
        write_new(output/"input_extraction.json", extraction)
        params = dict(admission_path=args.admission, admission_sha256=args.admission_sha256,
            recovery_manifest_path=args.recovery_manifest,
            recovery_manifest_sha256=args.recovery_manifest_sha256,
            inputs=args.inputs, packet=args.packet)
        admitted = b.load_inputs(**params)
        env = dict(os.environ)
        env.update({
            "CAS_META2_RECOVERY_ADMISSION": str(args.admission),
            "CAS_META2_RECOVERY_ADMISSION_SHA256": args.admission_sha256,
            "CAS_META2_RECOVERY_INPUTS": str(args.inputs),
            "CAS_META2_RECOVERY_PACKET": str(args.packet),
            "CAS_META2_RECOVERY_MANIFEST": str(args.recovery_manifest),
            "CAS_META2_RECOVERY_MANIFEST_SHA256": args.recovery_manifest_sha256,
        })
        command = gpu_command(output)
        write_new(output/"gpu_command.json", command)
        print(json.dumps({"stage": "recovery_gpu_gate", "expected_tests": 2}), flush=True)
        process = _run_process(command, output/"gpu_process",
                               min(deadline-2440, time.monotonic()+300), environment=env)
        totals = validate_xml(output/"gpu_tests.xml")
        gate = {"schema": "cas-meta2-contrast-recovery-gpu-gate/6", "job": args.job,
                "recovery_manifest_sha256": args.recovery_manifest_sha256,
                "completed": True, "expected_command": command,
                "process_receipt": {"path": "gpu_process/process_receipt.json",
                                    "sha256": hash_file(output/"gpu_process/process_receipt.json")},
                "tests_xml": {"path": "gpu_tests.xml", "sha256": hash_file(output/"gpu_tests.xml")}}
        write_new(output/"gpu_gate.json", gate)
        gate_pin = hash_file(output/"gpu_gate.json")
        checked_gate = b.check_gpu_gate(output/"gpu_gate.json", gate_pin, job=args.job,
                                       recovery_manifest_sha256=args.recovery_manifest_sha256)
        if deadline-time.monotonic() < 2430:
            raise TimeoutError("RECOVERY_REMOTE_INSUFFICIENT_FULL_NATIVE_TIME")
        command = native_command(args, output/"gpu_gate.json", gate_pin)
        write_new(output/"native_command.json", command)
        print(json.dumps({"stage": "fixed_prediction_replay", "cases": 72,
                          "arm_attempts": 360, "training_performed": False}), flush=True)
        native_process = _run_process(command, output/"native_process",
                                      min(deadline-20, time.monotonic()+2410), environment=env)
        result = b.decode((output/"native/recovery_receipt.json").read_bytes())
        if (result.get("schema") != "cas-meta2-contrast-evaluation-recovery/6"
                or result.get("status") != "CAS_META2_V6_EVALUATION_RECOVERY_COMPLETED"
                or result.get("completed") is not True or result.get("cases") != 72
                or result.get("arm_verdicts") != 360
                or result.get("original_campaign_completed") is not False
                or result.get("fresh_test") is not False or result.get("training_performed") is not False
                or result.get("predictions_reused_unchanged") is not True):
            raise ValueError("RECOVERY_REMOTE_COMPLETION_BOUNDARY")
        final_inputs = b.load_inputs(**params)
        if final_inputs["sources"] != admitted["sources"] or final_inputs["input_sha256"] != admitted["input_sha256"]:
            raise ValueError("RECOVERY_REMOTE_INPUT_OR_SOURCE_CHANGED")
        receipt.update(completed=True, gpu_tests=totals, gpu_gate=checked_gate,
            input_sha256=admitted["input_sha256"], sources=admitted["sources"],
            recovery_receipt_sha256=hash_file(output/"native/recovery_receipt.json"),
            evaluation_results_sha256=hash_file(output/"native/evaluation_results.json"),
            native_process_sha256=hash_file(output/"native_process/process_receipt.json"),
            original_packet_sha256=hash_file(args.packet),
            source_and_inputs_rechecked=True)
    except BaseException as exc:
        receipt["failure"] = {"type": type(exc).__name__, "message": str(exc),
                              "traceback": traceback.format_exc()}
        raise
    finally:
        receipt["wall_seconds"] = time.monotonic()-started
        receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write_new(output/"coordinator_receipt.json", receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("admission", "recovery-manifest", "packet", "inputs", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    for name in ("admission-sha256", "recovery-manifest-sha256", "job"):
        parser.add_argument("--"+name, required=True)
    parser.add_argument("--max-seconds", type=int, required=True)
    parser.add_argument("--enable-native-evaluation", action="store_true")
    args = parser.parse_args(argv)
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
