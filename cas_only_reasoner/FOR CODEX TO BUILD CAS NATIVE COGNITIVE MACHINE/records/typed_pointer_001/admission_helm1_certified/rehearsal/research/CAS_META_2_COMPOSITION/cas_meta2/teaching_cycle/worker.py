"""AWS-only entry point. Train first; sealed public prediction is a separate command.

Run with Python -I -B from an extracted, verified training bundle. This module
never loads private final targets, performs native execution or launches AWS.
IMDS observation is not a substitute for the parent provider's signed-in audit.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import sys
import time
import zipfile


def require(condition, code):
    if not condition:
        raise ValueError("TEACHING_WORKER:" + code)


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: require(False, "NONFINITE_JSON"))
    json.dumps(value, allow_nan=False)  # Reject exponent overflow as well.
    return value


def read_pinned_json(path, expected_sha256):
    require(type(expected_sha256) is str and
            re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is not None, "EXTERNAL_FILE_PIN_REQUIRED")
    raw = _read(path)
    require(sha256(raw).hexdigest() == expected_sha256, "EXTERNAL_FILE_PIN_MISMATCH")
    return _json(raw)


def _read(path, maximum=32 * 1024**2):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                    for p in (path, *path.parents)), "LINK_PATH_REJECTED")
    info = path.stat()
    require(path.is_file() and info.st_nlink == 1 and info.st_size <= maximum, "FILE_BOUND")
    raw = path.read_bytes()
    require(len(raw) == info.st_size, "FILE_CHANGED_DURING_READ")
    return raw


def _write(path, value):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                    for p in (path, *path.parents)), "LINK_PATH_REJECTED")
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}


def _metadata_fetch():
    # AWS documentation: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/retrieve-iid.html
    from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            raise ValueError("TEACHING_WORKER:METADATA_REDIRECT_REJECTED")
    opener = build_opener(ProxyHandler({}), NoRedirect())
    base = "http://169.254.169.254/latest/"
    with opener.open(Request(base + "api/token", method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"}), timeout=3) as response:
        token = response.read(2049).decode("ascii")
    require(0 < len(token) <= 2048 and "\r" not in token and "\n" not in token, "METADATA_TOKEN_INVALID")
    # The temporary metadata token is never written or included in an error.
    with opener.open(Request(base + "dynamic/instance-identity/document",
            headers={"X-aws-ec2-metadata-token": token}), timeout=3) as response:
        raw = response.read(16385)
    require(len(raw) <= 16384, "INSTANCE_DOCUMENT_BOUND")
    return raw


def observe_instance(instance_id, account, region, instance_type, fetch=None):
    require(re.fullmatch(r"i-(?:[0-9a-f]{8}|[0-9a-f]{17})", instance_id) is not None, "EXPECTED_INSTANCE_REQUIRED")
    require(re.fullmatch(r"[0-9]{12}", account) is not None, "EXPECTED_ACCOUNT_INVALID")
    raw = (fetch or _metadata_fetch)()
    require(type(raw) is bytes and len(raw) <= 16384, "INSTANCE_DOCUMENT_BOUND")
    document = _json(raw)
    expected = {"instanceId": instance_id, "accountId": account, "region": region, "instanceType": instance_type}
    require(type(document) is dict and all(document.get(k) == v for k, v in expected.items()),
            "INSTANCE_IDENTITY_MISMATCH")
    return {**expected, "imageId": document.get("imageId"), "document_sha256": sha256(raw).hexdigest(),
            "source": "EC2_IMDSv2_OBSERVATION", "provider_identity_proved": False,
            "boundary": "Match this observation to the parent's independent EC2 receipt."}


def verify_loaded_sources(bundle):
    for name, module in list(sys.modules.items()):
        if name == "cas_meta2" or name.startswith("cas_meta2."):
            location = getattr(module, "__file__", None)
            expected = bundle.joinpath(*name.split("."))
            expected = expected / "__init__.py" if hasattr(module, "__path__") else expected.with_suffix(".py")
            require(location is not None and Path(location).resolve() == expected.resolve(),
                    "LOADED_SOURCE_OUTSIDE_BUNDLE:" + name)
    require("cas_meta2.teaching_cycle.data" not in sys.modules
            and "cas_meta2.teaching_cycle.package" not in sys.modules, "TEACHER_MODULE_LOADED")


def verify_installed_reference(bundle):
    spec = importlib.util.find_spec("casformer")
    require(spec is not None and spec.origin is not None, "FROZEN_REFERENCE_NOT_INSTALLED")
    installed = Path(spec.origin).resolve().parent.parent
    wheel = bundle / "wheels/casformer_reference-0.1.0-py3-none-any.whl"
    checked = []
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.startswith("casformer/") and name.endswith(".py"):
                raw = archive.read(name)
                require(_read(installed / name) == raw, "INSTALLED_REFERENCE_BYTES_CHANGED:" + name)
                checked.append(name)
    require(bool(checked), "FROZEN_REFERENCE_PACKAGE_EMPTY")
    actual = {p.relative_to(installed).as_posix() for p in (installed / "casformer").rglob("*.py")}
    require(actual == set(checked), "INSTALLED_REFERENCE_INVENTORY_CHANGED")
    return {"module_files_checked": len(checked), "wheel_sha256": sha256(_read(wheel)).hexdigest()}


def _learners(bundle_data, run_id):
    from cas_meta2.teaching_cycle.gpu_adapter import build_matched_learners
    learners, matching = {}, {}
    manifest = bundle_data["manifest"]
    for curriculum in ("aligned", "ordinary"):
        pair, report = build_matched_learners(bundle_data["training_cases"],
            run_id=run_id + "." + curriculum, training_plan_sha256=manifest["training_cases_sha256"],
            seed=manifest["profile"]["seed"])
        learners.update({family + "." + curriculum: learner for family, learner in pair.items()})
        matching[curriculum] = report
    require(len({learner.tokenizer.digest for learner in learners.values()}) == 1,
            "CURRICULUM_TOKENIZERS_NOT_MATCHED")
    return learners, matching


def predict_sealed(learners, campaign, public_sets, output, source_sha256, *, stop_at=None):
    from cas_meta2.codec import canonical_sha256, validate_public
    require(type(source_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", source_sha256) is not None,
            "PREDICTION_SOURCE_PIN_REQUIRED")
    require(type(learners) is dict and set(learners) ==
            {"cas.aligned", "cas.ordinary", "generic.aligned", "generic.ordinary"}, "FOUR_REGISTERED_ARMS_REQUIRED")
    require(campaign.get("all_allocations_finished") is True, "FINAL_PREDICTION_ALLOCATION_INCOMPLETE")
    require(type(public_sets) is dict and set(public_sets) == {"test_fresh", "test_context", "test_names"},
            "FINAL_PUBLIC_SPLITS_INVALID")
    for rows in public_sets.values():
        require(type(rows) is list and len(rows) == 64, "FINAL_PUBLIC_COUNT_INVALID")
        for public in rows:
            validate_public(public)
            require("Worked" not in public["problem"] and "BIND" not in public["problem"],
                    "FINAL_INPUT_HAS_TEACHING_ANSWER")
    require(set(campaign["arms"]) == set(learners), "FINAL_ARMS_MISMATCH")
    artifacts = {}
    for arm, learner in learners.items():
        report = campaign["arms"][arm]
        require(report["run_id"] == learner.run_id and report["allocation_finished"] is True
                and report["selected_checkpoint"] is not None, "FINAL_CHECKPOINT_NOT_SELECTED")
        for phase, key in (("untrained", "initial_checkpoint"), ("trained", "selected_checkpoint")):
            reference = report[key]
            if "campaign_root" in campaign:
                checkpoint = Path(reference["path"]).absolute()
                require(checkpoint.is_relative_to(Path(campaign["campaign_root"]).absolute()),
                        "CHECKPOINT_OUTSIDE_CAMPAIGN")
                require(sha256(_read(checkpoint, 64 * 1024**2)).hexdigest() == reference["sha256"],
                        "PREDICTION_CHECKPOINT_FILE_MISMATCH")
            learner.restore_checkpoint(reference["path"], reference["sha256"])
            require(learner.state_identity()["checkpoint_sha256"] == reference["state_sha256"],
                    "PREDICTION_CHECKPOINT_STATE_MISMATCH")
            for split, rows in public_sets.items():
                require(stop_at is None or time.monotonic() < stop_at, "PREDICTION_DEADLINE_REACHED")
                predictions = learner.predict(rows)
                require(stop_at is None or time.monotonic() < stop_at, "PREDICTION_DEADLINE_REACHED")
                require(learner.state_identity()["checkpoint_sha256"] == reference["state_sha256"],
                        "PREDICTION_MUTATED_CHECKPOINT")
                require(len(predictions) == 64 and all(type(p) is int and p in (0, 1, 2) for p in predictions),
                        "FINAL_PREDICTIONS_INVALID")
                name = f"{arm}.{phase}.{split}.json"
                artifacts[name] = _write(output / name, {"schema": "cas-teaching-blind-predictions/1",
                    "arm": arm, "phase": phase, "split": split, "predictions": predictions,
                    "public_sha256": canonical_sha256(rows), "checkpoint": reference,
                    "run_id": learner.run_id, "source_sha256": source_sha256,
                    "private_targets_opened": False, "pid": os.getpid()})
    require(stop_at is None or time.monotonic() < stop_at, "PREDICTION_DEADLINE_REACHED")
    return _write(output / "prediction_seal.json", {"schema": "cas-teaching-blind-prediction-seal/1",
        "source_sha256": source_sha256, "artifacts": artifacts,
        "private_targets_opened": False, "native_execution": "UNEXECUTED"})


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("train", "predict"))
    for name in ("bundle", "manifest-sha256", "output", "run-id", "expected-instance-id"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--expected-account", default="807562639912")
    parser.add_argument("--expected-region", default="us-west-2")
    parser.add_argument("--expected-instance-type", default="g7.2xlarge")
    parser.add_argument("--worker-seconds", type=int, default=6000)
    parser.add_argument("--campaign-summary")
    parser.add_argument("--campaign-summary-sha256")
    parser.add_argument("--public-sets")
    parser.add_argument("--public-sets-sha256")
    parser.add_argument("--resume-summary")
    parser.add_argument("--resume-summary-sha256")
    args = parser.parse_args(argv)
    started = time.monotonic()
    require(platform.system() == "Linux" and sys.flags.isolated and sys.dont_write_bytecode,
            "ISOLATED_LINUX_WORKER_REQUIRED")
    require(os.environ.get("CAS_META2_RUN_TEACHING_CYCLE") == "1", "EXPLICIT_ENABLE_REQUIRED")
    require(0 < args.worker_seconds <= 6000, "WORKER_TIME_BOUND")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", args.run_id) is not None, "RUN_ID_INVALID")
    bundle = Path(args.bundle).absolute()
    require(Path(__file__).resolve() == bundle / "cas_meta2/teaching_cycle/worker.py",
            "ENTRYPOINT_OUTSIDE_BUNDLE")
    sys.path.insert(0, str(bundle))
    from cas_meta2.teaching_cycle.worker_contract import load_bundle
    data = load_bundle(bundle, args.manifest_sha256)
    verify_loaded_sources(bundle)
    campaign, public_sets, resume = None, None, None
    if args.phase == "train":
        require(all(value is None for value in (args.public_sets, args.public_sets_sha256,
                args.campaign_summary, args.campaign_summary_sha256)), "TRAIN_PHASE_FINAL_INPUT_REJECTED")
        require((args.resume_summary is None) == (args.resume_summary_sha256 is None), "RESUME_PIN_REQUIRED")
        if args.resume_summary is not None:
            resume = read_pinned_json(args.resume_summary, args.resume_summary_sha256)
            require(resume.get("source_sha256") == data["manifest"]["source_sha256"]
                    and resume.get("manifest_sha256") == data["manifest_sha256"]
                    and resume.get("run_id") == args.run_id
                    and resume.get("all_allocations_finished") is False, "RESUME_IDENTITY_MISMATCH")
    else:
        require(args.resume_summary is None and args.resume_summary_sha256 is None, "PREDICT_RESUME_REJECTED")
        require(args.public_sets is not None and args.campaign_summary is not None, "PREDICTION_INPUTS_REQUIRED")
        campaign = read_pinned_json(args.campaign_summary, args.campaign_summary_sha256)
        public_sets = read_pinned_json(args.public_sets, args.public_sets_sha256)
        require(campaign.get("source_sha256") == data["manifest"]["source_sha256"]
                and campaign.get("manifest_sha256") == data["manifest_sha256"]
                and campaign.get("run_id") == args.run_id, "PREDICTION_SOURCE_MISMATCH")
        require(campaign.get("all_allocations_finished") is True, "FINAL_PREDICTION_ALLOCATION_INCOMPLETE")
    instance = observe_instance(args.expected_instance_id, args.expected_account,
                                args.expected_region, args.expected_instance_type)
    reference_identity = verify_installed_reference(bundle)
    output = Path(args.output).absolute()
    require(not output.exists() and output.parent.is_dir()
            and not output.is_relative_to(bundle), "FRESH_OUTPUT_OUTSIDE_BUNDLE_REQUIRED")
    output.mkdir()
    _write(output / "worker_identity.json", {"instance": instance, "reference": reference_identity,
        "manifest_sha256": data["manifest_sha256"], "source_sha256": data["manifest"]["source_sha256"],
        "python": sys.version, "pid": os.getpid(), "phase": args.phase})
    from cas_meta2.teaching_cycle.gpu_adapter import _cuda
    torch, device = _cuda()
    require(torch.__version__ == "2.11.0+cu128" and torch.version.cuda == "12.8"
            and sys.version_info[:2] in ((3, 11), (3, 12)), "REGISTERED_NEURAL_ENVIRONMENT_REQUIRED")
    require("RTX PRO 4500" in torch.cuda.get_device_name(device), "REGISTERED_GPU_REQUIRED")
    learners, matching = _learners(data, args.run_id)
    verify_loaded_sources(bundle)
    if args.phase == "train":
        from cas_meta2.teaching_cycle.runner import run_campaign
        from cas_meta2.teaching_cycle.controller import Allocation
        remaining = args.worker_seconds - (time.monotonic() - started)
        require(remaining > 0, "SETUP_EXHAUSTED_WORKER_BUDGET")
        campaign_root = output / "campaign" if resume is None else Path(resume["campaign_root"]).absolute()
        require(not campaign_root.is_relative_to(bundle) and
                (resume is None or campaign_root.is_dir()), "RESUME_CAMPAIGN_PATH_INVALID")
        report = run_campaign(learners, data["training_cases"], data["development_cases"],
            campaign_root, data["manifest"]["source_sha256"], remaining,
            allocation=Allocation(**data["manifest"]["profile"]["allocation"]),
            seed=data["manifest"]["profile"]["seed"], batch_size=data["manifest"]["profile"]["batch_size"])
        report.update(matching=matching, worker_wall_seconds=time.monotonic() - started,
                      source_sha256=data["manifest"]["source_sha256"], manifest_sha256=data["manifest_sha256"],
                      run_id=args.run_id, campaign_root=str(campaign_root),
                      resumed_summary_sha256=args.resume_summary_sha256, worker_pid=os.getpid())
        receipt = _write(output / "campaign_summary.json", report)
    else:
        receipt = predict_sealed(learners, campaign, public_sets, output,
                                data["manifest"]["source_sha256"], stop_at=started + args.worker_seconds)
    verify_loaded_sources(bundle)
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
