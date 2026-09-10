"""The checked-component pilot launcher: the curriculum machinery, bound to this run.

This is a **candidate-specific binding**, not another general-purpose launcher. It
reuses the existing curriculum launcher's machinery unchanged — evidence
directories, canonical serialisation, the git-object package builder, the resource
plan and reservation scope, the provider lifecycle (preflight, one reservation,
launch, wait, collect, cleanup with verified collection before evidence deletion) —
and changes only what the new experiment requires:

* its own job pattern, request/authority/package/result schemas and entrypoint;
* its own worker script, which calls
  ``cas_meta2.graph_teaching.candidate_experiment.launch``;
* its own worker config (two conditions, 64 updates each, seed 20260909, the
  44-question probe), supplied through the provider's ``_worker_config`` hook.

The historical curriculum profile is untouched: it keeps its own constants,
schemas, worker and tests. The resource plan is carried forward unchanged, which
is the ``$7.00`` option the owner chose.

Execution remains gated: ``plan_only`` is the default, and ``execute`` needs a
hash-bound request plus an owner authority record.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from aws.graph_training_curriculum_launch import (  # reused machinery
    HEX40, HEX64, LEDGER_PATH, OWNER_AUTHORIZATION_PATH, RESOURCE_PLAN,
    RESERVATION_USD, CurriculumProvider, build_package, canonical,
    collection_is_verified, digest, prepare_evidence, read_ledger, require, scope,
    validate_preflight, validate_reservation_scope, validate_reserved_transition,
    write_evidence)

SCHEMA = "cas-graph-training-candidate-launch/1"
REQUEST_SCHEMA = "cas-graph-training-candidate-launch-request/1"
AUTHORITY_SCHEMA = "cas-graph-training-candidate-launch-authority/1"
PACKAGE_SCHEMA = "cas-graph-training-candidate-source-package/1"
RECEIPT_SCHEMA = "cas-graph-training-candidate-package-receipt/1"
RESULT_SCHEMA = "cas-graph-training-candidate-result/1"
WORKER_NAME = "graph6_candidate_worker.py"

JOB_PATTERN = r"cas-meta2-graph6cand-\d{14}-[a-f0-9]{8}"

EXPERIMENT = {"profile": "graph_training_candidate_component_pilot",
              "entrypoint": "cas_meta2.graph_teaching.candidate_experiment.launch"}

# The frozen design of AUTHORIZATION_REQUEST_001: two conditions, 64 updates
# each, matched initial weights, one common 44-question probe. Sealed splits and
# any other experiment's records are never read.
FROZEN_CONDITIONS = ("checked_component_teaching", "final_answer_only")
FROZEN_UPDATES_PER_CONDITION = 64
FROZEN_TOTAL_UPDATES = FROZEN_UPDATES_PER_CONDITION * len(FROZEN_CONDITIONS)
FROZEN_SEED = 20260909
FROZEN_ENCODER_SEED = 20260909
FROZEN_ORDERING_MODE = "declared"
FROZEN_PROBE_QUESTIONS = 44
FROZEN_CHECKPOINTS = ("final",)
FROZEN_ARM = "cas"
FROZEN_LEARNING_RATE = 0.003
FROZEN_MAX_WALL_SECONDS = 600.0
FROZEN_BUCKET_PREFIX = "cas-meta2-graph6cand"
RECEIPT_PREFIX = "graph6cand_"

DESIGN = {
    "launch_enabled": False,
    "training": True,
    "arms": [FROZEN_ARM],
    "conditions": list(FROZEN_CONDITIONS),
    "updates_per_condition": FROZEN_UPDATES_PER_CONDITION,
    "total_optimizer_steps": FROZEN_TOTAL_UPDATES,
    "seed": FROZEN_SEED,
    "encoder_seed": FROZEN_ENCODER_SEED,
    "ordering_mode": FROZEN_ORDERING_MODE,
    "probe_questions": FROZEN_PROBE_QUESTIONS,
    "checkpoints": list(FROZEN_CHECKPOINTS),
    "learning_rate": FROZEN_LEARNING_RATE,
    "max_wall_seconds_per_condition": FROZEN_MAX_WALL_SECONDS,
    "reservation_usd": RESERVATION_USD,
}


def validate_request(request):
    require(type(request) is dict and request.get("schema") == REQUEST_SCHEMA,
            "CANDIDATE_REQUEST_SCHEMA")
    require(set(request) == {"schema", "job", "source_sha", "archive_sha256",
                             "manifest_sha256", "launch_authorized"},
            "CANDIDATE_REQUEST_FIELDS")
    require(type(request["job"]) is str and re.fullmatch(JOB_PATTERN, request["job"]),
            "CANDIDATE_REQUEST_JOB")
    require(type(request["source_sha"]) is str and bool(HEX40.fullmatch(request["source_sha"])),
            "CANDIDATE_REQUEST_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256"):
        require(type(request[key]) is str and bool(HEX64.fullmatch(request[key])),
                "CANDIDATE_REQUEST_HASH:" + key)
    require(request["launch_authorized"] is False, "CANDIDATE_REQUEST_INERT")
    return request


def validate_authority(authority):
    require(type(authority) is dict and authority.get("schema") == AUTHORITY_SCHEMA,
            "CANDIDATE_AUTHORITY_SCHEMA")
    require(set(authority) == {
        "schema", "job", "source_sha", "archive_sha256", "manifest_sha256",
        "owner_authorization_sha256", "conditions", "updates_per_condition",
        "total_optimizer_steps", "seed", "encoder_seed", "ordering_mode",
        "probe_questions", "checkpoints", "learning_rate",
        "max_wall_seconds_per_condition", "reservation_usd"},
        "CANDIDATE_AUTHORITY_FIELDS")
    require(type(authority["job"]) is str and re.fullmatch(JOB_PATTERN, authority["job"]),
            "CANDIDATE_AUTHORITY_JOB")
    require(type(authority["source_sha"]) is str and bool(HEX40.fullmatch(authority["source_sha"])),
            "CANDIDATE_AUTHORITY_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256", "owner_authorization_sha256"):
        require(type(authority[key]) is str and bool(HEX64.fullmatch(authority[key])),
                "CANDIDATE_AUTHORITY_HASH:" + key)
    require(list(authority["conditions"]) == list(FROZEN_CONDITIONS),
            "CANDIDATE_AUTHORITY_CONDITIONS_FROZEN")
    require(authority["updates_per_condition"] == FROZEN_UPDATES_PER_CONDITION,
            "CANDIDATE_AUTHORITY_UPDATES_FROZEN")
    require(authority["total_optimizer_steps"] == FROZEN_TOTAL_UPDATES,
            "CANDIDATE_AUTHORITY_TOTAL_STEPS_FROZEN")
    require(authority["seed"] == FROZEN_SEED, "CANDIDATE_AUTHORITY_SEED_FROZEN")
    require(authority["encoder_seed"] == FROZEN_ENCODER_SEED,
            "CANDIDATE_AUTHORITY_ENCODER_SEED_FROZEN")
    require(authority["ordering_mode"] == FROZEN_ORDERING_MODE,
            "CANDIDATE_AUTHORITY_ORDERING_FROZEN")
    require(authority["probe_questions"] == FROZEN_PROBE_QUESTIONS,
            "CANDIDATE_AUTHORITY_PROBE_FROZEN")
    require(list(authority["checkpoints"]) == list(FROZEN_CHECKPOINTS),
            "CANDIDATE_AUTHORITY_CHECKPOINTS_FROZEN")
    require(authority["learning_rate"] == FROZEN_LEARNING_RATE,
            "CANDIDATE_AUTHORITY_BUDGET:learning_rate")
    require(authority["max_wall_seconds_per_condition"] == FROZEN_MAX_WALL_SECONDS,
            "CANDIDATE_AUTHORITY_BUDGET:max_wall_seconds_per_condition")
    require(authority["reservation_usd"] == RESERVATION_USD,
            "CANDIDATE_AUTHORITY_RESERVATION")
    return authority


def plan_only(request=None, authority=None):
    if request is not None:
        validate_request(request)
    if authority is not None:
        validate_authority(authority)
    return {"schema": SCHEMA, "status": "PLAN_ONLY_NOT_EXECUTED",
            "experiment": EXPERIMENT, "design": DESIGN,
            "resource_plan": scope(),
            "job_pattern": JOB_PATTERN, "worker_script": WORKER_NAME,
            "reservation_created": False, "provider_calls": 0,
            "boundary": ("no provider client, reservation, model import, or output "
                         "mutation occurred; execution needs a hash-bound request "
                         "and an owner authority record")}


def render_worker():
    """The in-package worker: two conditions, real checkpoints, verified delivery."""
    return "\n".join([
        '"""Rendered candidate worker: the checked-component pilot, one run."""',
        "import hashlib",
        "import json",
        "import os",
        "import sys",
        "import traceback",
        "from pathlib import Path",
        "",
        "ROOT = Path(__file__).resolve().parent",
        "CONFIG = json.loads((ROOT / 'config.json').read_text())",
        "ARTIFACTS = ROOT / 'artifacts'",
        "ARTIFACTS.mkdir(exist_ok=True)",
        "",
        "",
        "def sha256_file(path):",
        "    digest = hashlib.sha256()",
        "    with open(path, 'rb') as stream:",
        "        for block in iter(lambda: stream.read(1 << 20), b''):",
        "            digest.update(block)",
        "    return digest.hexdigest()",
        "",
        "",
        "def upload(s3, bucket, key, path):",
        "    s3.upload_file(str(path), bucket, key)",
        "    return {'key': key, 'bytes': path.stat().st_size,",
        "            'sha256': sha256_file(path)}",
        "",
        "",
        "def state_digest(module):",
        "    digest = hashlib.sha256()",
        "    for name, tensor in module.state_dict().items():",
        "        # registration order, exactly as GraphLearner.checkpoint_identity",
        "        # hashes it, so the round trip compares like with like",
        "        digest.update(name.encode('utf-8'))",
        "        digest.update(tensor.detach().cpu().numpy().tobytes())",
        "    return digest.hexdigest()",
        "",
        "",
        "def main():",
        "    from cas_meta2.graph_teaching import candidate_experiment as ce",
        "    from cas_meta2.graph_teaching import trainer",
        "    from cas_meta2.teaching_cycle import gpu_adapter",
        "    from cas_meta2.graph_teaching.real_framework import (",
        "        build_encoder, build_graph_training_framework, GraphLearner)",
        "    from cas_meta2.graph_teaching import adapter",
        "    torch, device = gpu_adapter._cuda()",
        "    inputs = ce.build_inputs(ordering_mode=CONFIG['ordering_mode'])",
        "    records, probe = inputs['records'], inputs['probe']",
        "    publics = [adapter.public_records(record, CONFIG['arm'])['public']",
        "               for record in records + probe]",
        "    encoder = build_encoder(torch, publics, d_model=64,",
        "                            seed=CONFIG['encoder_seed'], device=device)",
        "    condition_order = list(CONFIG['conditions'])",
        "",
        "    def framework_factory(seed):",
        "        torch.manual_seed(seed)",
        "        framework = build_graph_training_framework(",
        "            torch, device, seed=CONFIG['encoder_seed'], encoder=encoder)",
        "        model = framework.build_decompose_model(seed=seed)",
        "        return framework, model",
        "",
        "    def learner_factory(*, framework, model, arm, records, layout):",
        "        tasks = [layout[record['record_id']] for record in records]",
        "        learner = GraphLearner(torch, framework, tasks, device,",
        "                               CONFIG['learning_rate'])",
        "        # conditions run in the frozen order, so the tag follows that order",
        "        learner.condition_tag = condition_order.pop(0)",
        "        return learner",
        "",
        "    def checkpoint_writer(learner, identity):",
        "        path = ARTIFACTS / ('checkpoint_%s.pt' % learner.condition_tag)",
        "        torch.save({'schema': 'cas-graph-training-candidate-checkpoint/1',",
        "                    'condition': learner.condition_tag,",
        "                    'identity': identity,",
        "                    'state': learner.module.state_dict()}, str(path))",
        "        return {'path': str(path), 'identity': identity,",
        "                'sha256': sha256_file(path)}",
        "",
        "    def checkpoint_verifier(saved, identity):",
        "        loaded = torch.load(saved['path'], map_location='cpu',",
        "                            weights_only=True)",
        "        digest = hashlib.sha256()",
        "        for name, tensor in loaded['state'].items():",
        "            digest.update(name.encode('utf-8'))",
        "            digest.update(tensor.detach().cpu().numpy().tobytes())",
        "        return digest.hexdigest() == identity and loaded['identity'] == identity",
        "",
        "    authorization = {'owner_go': True, 'run_id': CONFIG['job'],",
        "                     'authority_sha256': CONFIG['authority_sha256']}",
        "    result = ce.launch(run_id=CONFIG['job'], records=records, probe=probe,",
        "                       groups=inputs['groups'],",
        "                       framework_factory=framework_factory,",
        "                       learner_factory=learner_factory,",
        "                       authorization=authorization,",
        "                       checkpoint_writer=checkpoint_writer,",
        "                       checkpoint_verifier=checkpoint_verifier,",
        "                       view_id=CONFIG['view_id'],",
        "                       ordering_mode=CONFIG['ordering_mode'])",
        "    (ARTIFACTS / 'result.json').write_text(",
        "        json.dumps(result, sort_keys=True, indent=2, allow_nan=False))",
        "    return result",
        "",
        "",
        "def upload_results(s3, bucket, results):",
        "    uploaded = []",
        "    for path in sorted(ARTIFACTS.iterdir()):",
        "        if path.name == 'result.json':",
        "            continue",
        "        uploaded.append(upload(s3, bucket, 'results/' + path.name, path))",
        "    manifest = {'schema': 'cas-graph-training-candidate-delivery/1',",
        "                'job': CONFIG['job'], 'artifacts': uploaded}",
        "    (ARTIFACTS / 'manifest.json').write_text(",
        "        json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False))",
        "    uploaded.append(upload(s3, bucket, 'results/manifest.json',",
        "                           ARTIFACTS / 'manifest.json'))",
        "    # result.json goes LAST: collection treats it as the completion marker",
        "    uploaded.append(upload(s3, bucket, 'results/result.json',",
        "                           ARTIFACTS / 'result.json'))",
        "    return manifest",
        "",
        "",
        "def main_guarded():",
        "    import boto3",
        "    s3 = boto3.client('s3', region_name=CONFIG['region'])",
        "    bucket = CONFIG['bucket']",
        "    try:",
        "        main()",
        "        manifest = upload_results(s3, bucket, None)",
        "        print(json.dumps({'worker_status': 'REMOTE_FINISHED',",
        "                          'artifacts': len(manifest['artifacts'])}))",
        "    except BaseException:",
        "        failure = {'schema': 'cas-graph-training-candidate-failure/1',",
        "                   'job': CONFIG['job'],",
        "                   'traceback': traceback.format_exc()[:20000]}",
        "        (ARTIFACTS / 'failure.json').write_text(",
        "            json.dumps(failure, sort_keys=True))",
        "        partial = {'schema': 'cas-graph-training-candidate-result/1',",
        "                   'job': CONFIG['job'], 'status': 'WORKER_FAILED',",
        "                   'failure': failure}",
        "        (ARTIFACTS / 'result_partial.json').write_text(",
        "            json.dumps(partial, sort_keys=True))",
        "        try:",
        "            upload_results(s3, bucket, None)",
        "        except BaseException:",
        "            pass",
        "        print('WORKER_FAILED')",
        "        raise SystemExit(1)",
        "",
        "",
        "if __name__ == '__main__':",
        "    main_guarded()",
        "",
    ])


def build_candidate_package(output, *, source_sha, git_bytes_fn=None,
                            git_paths_fn=None):
    """The source package for this pilot, through the existing package builder."""
    from aws import graph_training_curriculum_launch as curriculum
    return build_package(
        output, source_sha=source_sha,
        git_bytes_fn=git_bytes_fn or curriculum.git_bytes,
        git_paths_fn=git_paths_fn or curriculum.git_tree_paths,
        worker_name=WORKER_NAME, worker_source=render_worker(),
        experiment=EXPERIMENT, package_schema=PACKAGE_SCHEMA, design=DESIGN,
        receipt_schema=RECEIPT_SCHEMA)


class CandidateProvider(CurriculumProvider):
    """The same provider lifecycle, bound to this pilot's worker and schemas."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_name = WORKER_NAME
        self.result_schema = RESULT_SCHEMA

    def _worker_config(self, bucket):
        return {"schema": "cas-graph-training-candidate-worker-config/1",
                "job": self.job, "bucket": bucket, "region": self.region,
                "arm": FROZEN_ARM, "view_id": "view_context",
                "ordering_mode": FROZEN_ORDERING_MODE,
                "conditions": list(FROZEN_CONDITIONS),
                "updates_per_condition": FROZEN_UPDATES_PER_CONDITION,
                "seed": FROZEN_SEED, "encoder_seed": FROZEN_ENCODER_SEED,
                "learning_rate": FROZEN_LEARNING_RATE,
                "probe_questions": FROZEN_PROBE_QUESTIONS,
                "authority_sha256": self._authority_sha256()}

    def set_authority_sha256(self, value):
        require(type(value) is str and bool(HEX64.fullmatch(value)),
                "CANDIDATE_PROVIDER_AUTHORITY_HASH")
        self._authority = value
        return value

    def _authority_sha256(self):
        require(getattr(self, "_authority", None), "CANDIDATE_PROVIDER_AUTHORITY_HASH")
        return self._authority


def execute(request, authority, provider, *, ledger_path=LEDGER_PATH,
            receipt_dir=None, owner_authorization_path=None):
    """One reservation, one launch, verified collection, then cleanup."""
    validate_request(request)
    validate_authority(authority)
    owner_path = (Path(owner_authorization_path) if owner_authorization_path is not None
                  else OWNER_AUTHORIZATION_PATH)
    require(authority["owner_authorization_sha256"] == digest(owner_path.read_bytes()),
            "OWNER_AUTHORIZATION_RECORD_MISMATCH")
    require(authority["job"] == request["job"]
            and authority["source_sha"] == request["source_sha"],
            "REQUEST_AUTHORITY_MISMATCH")
    for key in ("archive_sha256", "manifest_sha256"):
        require(authority[key] == request[key], "REQUEST_AUTHORITY_HASH_MISMATCH:" + key)
    require(provider is not None, "PROVIDER_ADAPTER_REQUIRED")
    started = time.monotonic()
    ledger_before = read_ledger(ledger_path)
    reservation_scope = validate_reservation_scope(ledger_before)
    require(not any(entry["job"] == request["job"]
                    for entry in ledger_before["ledger"]["reservations"]),
            "JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY")
    directory = prepare_evidence(receipt_dir if receipt_dir is not None else
                                 Path(ledger_path).parent / (RECEIPT_PREFIX + request["job"]))
    write_evidence(directory / "intent.json", canonical({
        "schema": SCHEMA, "request": request, "authority": authority,
        "ledger_before": ledger_before, "automatic_retries": 0}))
    provider.configure_evidence(directory)
    if hasattr(provider, "set_authority_sha256"):
        provider.set_authority_sha256(authority["owner_authorization_sha256"])
    preflight = reservation = ledger_after = launched = collected = None
    reservation_valid, reservation_error = False, None
    verified = False
    cleanup = {"complete": False, "failures": ["NOT_ATTEMPTED"]}
    outcome = {}
    try:
        preflight = validate_preflight(provider.preflight())
        write_evidence(directory / "preflight.json", canonical(preflight))
        reservation = provider.reserve(RESERVATION_USD)
        ledger_after = read_ledger(ledger_path)
        validate_reserved_transition(ledger_before, ledger_after, reservation, request)
        require(reservation.get("aws_side_reservation", {}).get("status") == "RECORDED",
                "AWS_RESERVATION_RECORD_REQUIRED")
        write_evidence(directory / "reservation.json", canonical(reservation))
        reservation_valid = True
        permit = {"job": request["job"], "source_sha": request["source_sha"],
                  "archive_sha256": request["archive_sha256"],
                  "manifest_sha256": request["manifest_sha256"],
                  "reservation": reservation, "preflight": preflight,
                  "resource_plan": scope()}
        launched = provider.launch(request["job"], permit)
        write_evidence(directory / "launch.json", canonical(launched))
        outcome = provider.wait(request["job"],
                                timeout=RESOURCE_PLAN["instance_seconds_max"])
        collected = provider.collect(request["job"])
        verified = collection_is_verified(collected)
        status = ("AWS_CANDIDATE_FINISHED"
                  if outcome.get("worker_status") == "REMOTE_FINISHED"
                  else "AWS_CANDIDATE_FAILED")
    except BaseException as error:
        status = "AWS_CANDIDATE_LAUNCH_FAILED"
        outcome = {"exception_type": type(error).__name__,
                   "exception": str(error)[:2000]}
        if not reservation_valid:
            reservation_error = error
        try:
            write_evidence(directory / "failure.json", canonical(outcome))
        except Exception as record_error:
            outcome["failure_record_error"] = (type(record_error).__name__ + ":"
                                               + str(record_error)[:1000])
    finally:
        try:
            cleanup = provider.cleanup(request["job"], collection_verified=verified)
        except BaseException as error:
            cleanup = {"complete": False, "failures": [
                "CLEANUP_EXCEPTION:" + type(error).__name__ + ":" + str(error)[:2000]]}
    result = {"schema": SCHEMA, "status": status, "job": request["job"],
              "request": request, "authority": authority,
              "ledger_before": ledger_before, "ledger_after": ledger_after,
              "reservation_scope": reservation_scope, "reservation": reservation,
              "preflight": preflight, "launch": launched, "outcome": outcome,
              "collected": collected, "receipt_dir": str(directory),
              "cleanup": cleanup, "elapsed_seconds": time.monotonic() - started,
              "stages": {"execution": ("FINISHED" if outcome.get("worker_status")
                                       == "REMOTE_FINISHED" else "FAILED"),
                         "collection": ("VERIFIED" if verified else "NOT_VERIFIED"),
                         "cleanup": ("COMPLETE" if cleanup.get("complete")
                                     else "INCOMPLETE")},
              "completed_deliverable": bool(verified and cleanup.get("complete")
                                            and outcome.get("worker_status")
                                            == "REMOTE_FINISHED"),
              "claims": {"seven_stage_program_claimed": False,
                         "component_teaching_claimed": "pending the measured result"}}
    if not cleanup.get("complete"):
        result["status"] = "AWS_CANDIDATE_FAILED"
        result["cleanup_incomplete_reason"] = cleanup.get("failures")
    write_evidence(directory / "result.json", canonical(result))
    if reservation_error is not None:
        raise reservation_error
    return result


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--request")
    parser.add_argument("--request-sha256")
    parser.add_argument("--authority")
    parser.add_argument("--authority-sha256")
    parser.add_argument("--receipt-dir")
    parser.add_argument("--owner-authorization")
    parser.add_argument("--profile", default="default")
    arguments = parser.parse_args(argv)
    if not arguments.execute:
        print(json.dumps(plan_only(), sort_keys=True))
        return 0
    require(all(getattr(arguments, name) for name in
               ("request", "request_sha256", "authority", "authority_sha256",
                "receipt_dir")), "EXPLICIT_REGISTERED_INPUTS_REQUIRED")
    request_raw = Path(arguments.request).read_bytes()
    authority_raw = Path(arguments.authority).read_bytes()
    require(digest(request_raw) == arguments.request_sha256,
            "REQUEST_FILE_HASH_MISMATCH")
    require(digest(authority_raw) == arguments.authority_sha256,
            "AUTHORITY_FILE_HASH_MISMATCH")
    request = json.loads(request_raw)
    authority = json.loads(authority_raw)
    validate_request(request)
    validate_authority(authority)
    session_clients = _clients(arguments.profile)
    provider = CandidateProvider(
        job=request["job"], source_sha=request["source_sha"],
        archive_sha256=request["archive_sha256"],
        manifest_sha256=request["manifest_sha256"], ledger_path=LEDGER_PATH,
        clients=session_clients)
    result = execute(request, authority, provider, ledger_path=LEDGER_PATH,
                     receipt_dir=arguments.receipt_dir,
                     owner_authorization_path=arguments.owner_authorization)
    print(json.dumps({"status": result["status"], "stages": result["stages"],
                      "completed_deliverable": result["completed_deliverable"]},
                     sort_keys=True))
    return 0


# Every client name the reused provider lifecycle asks for. The first attempt at
# this pilot failed at preflight with KeyError: 'sts' because only three of the
# five were created; a test now checks this set against the reused source.
CLIENT_NAMES = ("ec2", "s3", "iam", "sts", "pricing")


def _clients(profile):
    """The same client construction the working curriculum path uses.

    Two details matter and both cost a preflight failure to learn: every client
    needs the frozen region, and the **Pricing** client must be built in
    ``us-east-1`` (its only usable endpoint), or ``get_products`` answers
    ``AccessDeniedException``.
    """
    import boto3
    from botocore.config import Config
    config = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 0})
    session = boto3.Session(profile_name=profile, region_name=RESOURCE_PLAN["region"])
    clients = {name: session.client(name, config=config) for name in CLIENT_NAMES}
    clients["pricing"] = session.client("pricing", region_name="us-east-1",
                                        config=config)
    return clients


if __name__ == "__main__":
    raise SystemExit(main())
