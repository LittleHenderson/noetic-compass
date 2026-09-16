"""Versioned zero-update contrast binding to the established AWS lifecycle."""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from aws import graph_training_candidate_launch as candidate
from aws import graph_training_curriculum_launch as shared
from aws import recurrent_cjt_launch as worker_template
from aws import run_evidence
from cas_meta2.graph_teaching import contrast_readout as readout

require, canonical, digest = shared.require, shared.canonical, shared.digest
REQUEST_SCHEMA = "cas-graph6-contrast-request/1"
AUTHORITY_SCHEMA = "cas-graph6-contrast-authority/1"
OWNER_SCHEMA = "cas-graph6-contrast-owner/1"
WORKER_NAME = "graph6_contrast_worker.py"
JOB_PATTERN = r"cas-meta2-graph6contrast-\d{14}-[a-f0-9]{8}"
EXPERIMENT = {"profile": "retained_curriculum_contrast_v1",
              "entrypoint": "cas_meta2.graph_teaching.contrast_readout.run"}
DESIGN = {"source_job": readout.SOURCE_JOB, "source_result_sha256": readout.SOURCE_RESULT_SHA256,
          "training": False, "optimizer_updates": 0, "checkpoints": 6,
          "probe_seed": readout.PROBE_SEED, "max_wall_seconds": readout.MAX_WALL_SECONDS,
          "install_allowance_seconds": 600, "automatic_retries": 0,
          "reservation_usd": shared.RESERVATION_USD,
          "instance_seconds_max": shared.RESOURCE_PLAN["instance_seconds_max"],
          "resource_plan_role": "Inherited hardware/cost lifecycle only; its historical training budget does not describe this job."}


def frozen_inputs_hash():
    return digest(canonical(readout.input_inventory(ROOT)))


def validate_request(request):
    require(type(request) is dict and set(request) == {"schema", "job", "source_sha",
        "archive_sha256", "manifest_sha256", "launch_authorized"}, "CONTRAST_REQUEST_FIELDS")
    require(request["schema"] == REQUEST_SCHEMA, "CONTRAST_REQUEST_SCHEMA")
    require(type(request["job"]) is str and re.fullmatch(JOB_PATTERN, request["job"]), "CONTRAST_JOB")
    require(type(request["source_sha"]) is str and shared.HEX40.fullmatch(request["source_sha"]), "CONTRAST_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256"):
        require(type(request[key]) is str and shared.HEX64.fullmatch(request[key]), "CONTRAST_HASH:" + key)
    require(request["launch_authorized"] is False, "CONTRAST_REQUEST_INERT")
    return request


def validate_authority(authority):
    fields = {"schema", "job", "source_sha", "archive_sha256", "manifest_sha256",
              "owner_authorization_sha256", "inputs_sha256", "design_sha256",
              "evidence_contract_sha256", "training", "optimizer_updates", "max_wall_seconds",
              "reservation_usd"}
    require(type(authority) is dict and set(authority) == fields, "CONTRAST_AUTHORITY_FIELDS")
    require(authority["schema"] == AUTHORITY_SCHEMA, "CONTRAST_AUTHORITY_SCHEMA")
    validate_request({**{k: authority[k] for k in ("job", "source_sha", "archive_sha256", "manifest_sha256")},
                      "schema": REQUEST_SCHEMA, "launch_authorized": False})
    require(shared.HEX64.fullmatch(authority["owner_authorization_sha256"]), "CONTRAST_OWNER_HASH")
    for key, expected in (("inputs_sha256", frozen_inputs_hash()),
                          ("design_sha256", digest(canonical(DESIGN))),
                          ("evidence_contract_sha256", run_evidence.contract_digest(evidence_contract()))):
        require(authority[key] == expected, "CONTRAST_AUTHORITY_BINDING:" + key)
    require(authority["training"] is False and type(authority["optimizer_updates"]) is int
            and authority["optimizer_updates"] == 0, "CONTRAST_AUTHORITY_ZERO_UPDATES")
    require(authority["max_wall_seconds"] == readout.MAX_WALL_SECONDS, "CONTRAST_AUTHORITY_WALL")
    require(authority["reservation_usd"] == shared.RESERVATION_USD, "CONTRAST_AUTHORITY_RESERVATION")
    return authority


def render_worker():
    """Reuse proven environment/error/publisher code with a new inner entrypoint."""
    tree = ast.parse(worker_template.render_worker())
    inner = "\n".join([
        "import json, sys", "from pathlib import Path", "ROOT = Path(sys.argv[1])",
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))",
        "from cas_meta2.graph_teaching import contrast_readout",
        "CONFIG = json.loads((ROOT / 'config.json').read_bytes())",
        "RESULTS = ROOT / 'results'", "ARTIFACTS = RESULTS / 'artifacts'",
        "ARTIFACTS.mkdir(parents=True, exist_ok=True)",
        "report = contrast_readout.run(CONFIG, root=ROOT, results=RESULTS, artifacts=ARTIFACTS)",
        "print(json.dumps({'status': report['status'], 'optimizer_updates': 0}))",
    ])
    replacements = {"INNER_RUNNER": inner, "RESULT_SCHEMA": readout.RESULT_SCHEMA,
                    "FAILURE_SCHEMA": "cas-graph6-contrast-failure/1",
                    "MAX_WALL_SECONDS": float(readout.MAX_WALL_SECONDS)}
    found = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in replacements:
                node.value = ast.Constant(replacements[name])
                found.add(name)
    require(found == set(replacements), "CONTRAST_WORKER_TEMPLATE_CHANGED")
    timeouts = 0
    for node in ast.walk(tree):
        if (isinstance(node, ast.keyword) and node.arg == "timeout"
                and isinstance(node.value, ast.BinOp)
                and ast.unparse(node.value) == "MAX_WALL_SECONDS + 1800"):
            node.value = ast.Name(id="MAX_WALL_SECONDS", ctx=ast.Load())
            timeouts += 1
    require(timeouts == 1, "CONTRAST_INNER_TIMEOUT_BINDING")
    tree.body[0] = ast.Expr(ast.Constant("Retained curriculum contrast worker. Zero optimizer updates."))
    return ast.unparse(ast.fix_missing_locations(tree)) + "\n"


def worker_config(job, bucket, region):
    return {"schema": readout.CONFIG_SCHEMA, "job": job, "bucket": bucket, "region": region,
            "training": False, "optimizer_updates": 0, "probe_seed": readout.PROBE_SEED,
            "execution_design": DESIGN,
            "max_wall_seconds": readout.MAX_WALL_SECONDS,
            "inputs": readout.input_inventory(ROOT), "source_result_sha256": readout.SOURCE_RESULT_SHA256}


class ContrastProvider(candidate.CandidateProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_name = WORKER_NAME
        self.result_schema = readout.RESULT_SCHEMA
        self.failure_statuses = ("WORKER_FAILED", "REMOTE_WORKER_FAILED", "CONTRAST_READOUT_FAILED")

    def _worker_config(self, bucket):
        return worker_config(self.job, bucket, self.region)


def package_data_files():
    names = [readout.TRANSPORT_RESULT, readout.SOURCE_DIR + "/source.zip"]
    names.extend(item["checkpoint"] for item in readout.input_inventory(ROOT))
    return tuple(shared.PILOT + name for name in names)


def build_contrast_package(output, *, source_sha):
    readout.historical_implementation_check(ROOT)
    return shared.build_package(output, source_sha=source_sha,
        worker_name=WORKER_NAME, worker_source=render_worker(), experiment=EXPERIMENT,
        package_schema="cas-graph6-contrast-package/1", design=DESIGN,
        receipt_schema="cas-graph6-contrast-package-receipt/1", extra_files=package_data_files())


def evidence_contract():
    names = {"results/result.json": "terminal envelope", "results/result.json.sha256": "envelope digest",
             "results/artifacts/manifest.json": "artifact inventory",
             "results/artifacts/contrast_readout.json": "all six learners and all contrast predictions",
             "results/artifacts/measurements.json": "per-learner counts and unchanged weight readings"}
    return run_evidence.contract(EXPERIMENT["profile"], [
        run_evidence.requirement(key, title, kind="json" if key.endswith(".json") else "file")
        for key, title in names.items()], notes=[
            "Checkpoint files are hash-bound inputs, never rewritten.",
            "Retrospective diagnosis; no training or independent transfer claim."])


def execute(request, authority, provider, *, receipt_dir, owner_authorization_path):
    owner = json.loads(Path(owner_authorization_path).read_bytes())
    require(owner.get("schema") == OWNER_SCHEMA and owner.get("owner_instruction_raw"), "CONTRAST_OWNER_RECORD")
    readout.historical_implementation_check(ROOT)
    return candidate.execute(request, authority, provider, ledger_path=shared.LEDGER_PATH,
        receipt_dir=receipt_dir, owner_authorization_path=owner_authorization_path,
        validate_request_fn=validate_request, validate_authority_fn=validate_authority,
        evidence_contract=evidence_contract())


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    for field in ("request", "request-sha256", "authority", "authority-sha256", "receipt-dir", "owner-authorization"):
        parser.add_argument("--" + field)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"status": "PLAN_ONLY", "design": DESIGN, "inputs": readout.input_inventory(ROOT)}))
        return 0
    require(all(getattr(args, x) for x in ("request", "request_sha256", "authority", "authority_sha256",
                                          "receipt_dir", "owner_authorization")), "CONTRAST_EXPLICIT_INPUTS")
    request_raw, authority_raw = Path(args.request).read_bytes(), Path(args.authority).read_bytes()
    require(digest(request_raw) == args.request_sha256 and digest(authority_raw) == args.authority_sha256,
            "CONTRAST_REQUEST_AUTHORITY_FILE_HASH")
    request, authority = json.loads(request_raw), json.loads(authority_raw)
    validate_request(request)
    validate_authority(authority)
    provider = ContrastProvider(job=request["job"], source_sha=request["source_sha"],
        archive_sha256=request["archive_sha256"], manifest_sha256=request["manifest_sha256"],
        ledger_path=shared.LEDGER_PATH, clients=candidate._clients(args.profile),
        client_error=candidate._client_error(), source_archive=candidate._locate_archive(request["archive_sha256"]))
    result = execute(request, authority, provider, receipt_dir=args.receipt_dir,
                     owner_authorization_path=args.owner_authorization)
    print(json.dumps({"status": result["status"], "completed_deliverable": result["completed_deliverable"],
                      "stages": result["stages"]}))
    return 0 if result["completed_deliverable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
