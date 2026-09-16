"""One bounded ordered-ingestion teaching/reload smoke over the existing AWS lifecycle."""
from __future__ import annotations

import ast
import importlib
import io
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_HOME = next(parent for parent in reversed(ROOT.parents)
                      if parent.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from aws import graph6_contrast_launch as contrast
from aws import graph_training_candidate_launch as lifecycle
from aws import graph_training_curriculum_launch as shared
from aws import run_evidence

require, canonical, digest = shared.require, shared.canonical, shared.digest
CANDIDATE = "CNCM_ORDERED_INGESTION_SMOKE_001"
CONFIG_SCHEMA = "cncm-ordered-ingestion-smoke-config/1"
RESULT_SCHEMA = "cncm-ordered-ingestion-smoke-result/1"
FAILURE_SCHEMA = "cncm-ordered-ingestion-smoke-failure/1"
REQUEST_SCHEMA = "cncm-ordered-ingestion-smoke-request/1"
AUTHORITY_SCHEMA = "cncm-ordered-ingestion-smoke-authority/1"
OWNER_SCHEMA = "cncm-ordered-ingestion-smoke-owner/1"
WORKER_NAME = "ingestion_smoke_worker.py"
JOB_PATTERN = r"cas-meta2-ingestionsmoke-\d{14}-[a-f0-9]{8}"
SEED, MAX_WALL_SECONDS = 20260916, 1200
EXPERIMENT = {"profile": "ordered_ingestion_smoke_v1", "candidate": CANDIDATE,
              "entrypoint": "cncm.rpa_learning_worker.run"}
BOUNDS = {"training": True, "optimizer_updates_max": 64, "max_wall_seconds": 1200,
          "jobs": 1, "automatic_retries": 0, "reservation_usd": "7.00",
          "instance_type": "g7.2xlarge", "region": "us-west-2"}
PROJECT = ROOT.parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
from cncm import rpa_learning_worker as worker
DESIGN = json.loads(canonical(worker.EXECUTION_DESIGN))
require(BOUNDS == worker.BOUNDS, "INGESTION_BOUND_CONTRACT")
PACKAGING_SOURCES = tuple("aws/" + name + ".py" for name in (
    "ingestion_smoke_launch", "graph6_contrast_launch", "recurrent_cjt_launch",
    "graph_training_candidate_launch", "graph_training_curriculum_launch", "run_evidence", "budget", "__init__"))


def _probe():
    probe = importlib.import_module("cncm.rpa_learning_worker")
    for name in ("CANDIDATE", "CONFIG_SCHEMA", "RESULT_SCHEMA", "FAILURE_SCHEMA", "SEED", "MAX_WALL_SECONDS"):
        require(getattr(probe, name) == globals()[name], "INGESTION_PROBE_CONTRACT:" + name)
    require(canonical(probe.EXECUTION_DESIGN) == canonical(DESIGN), "INGESTION_PROBE_DESIGN")
    return probe


def frozen_inputs():
    rows = _probe().input_inventory(PROJECT)
    require(type(rows) is list and rows, "INGESTION_INPUTS_REQUIRED")
    paths = []
    for row in rows:
        require(type(row) is dict and set(row) == {"path", "bytes", "sha256"}, "INGESTION_INPUT_FIELDS")
        require(type(row["path"]) is str, "INGESTION_INPUT_PATH")
        shared.checked_names([row["path"]])
        require(type(row["bytes"]) is int and row["bytes"] >= 0, "INGESTION_INPUT_BYTES")
        require(type(row["sha256"]) is str and shared.HEX64.fullmatch(row["sha256"]), "INGESTION_INPUT_HASH")
        paths.append(row["path"])
    require(paths == sorted(set(paths)), "INGESTION_INPUTS_SORTED_UNIQUE")
    return rows


def frozen_inputs_hash():
    return digest(canonical(frozen_inputs()))


def worker_config(job, *, source_sha):
    inputs = frozen_inputs()
    return {"schema": CONFIG_SCHEMA, "candidate": CANDIDATE, "job": job,
            "source_sha": source_sha, "region": BOUNDS["region"],
            "training": True, "optimizer_updates_max": 64, "seed": SEED,
            "max_wall_seconds": MAX_WALL_SECONDS, "execution_design": json.loads(canonical(DESIGN)),
            "inputs": inputs, "inputs_sha256": digest(canonical(inputs)),
            "material": _probe().material_identity(PROJECT)}


def validate_request(request):
    require(type(request) is dict and set(request) == {"schema", "job", "source_sha",
        "archive_sha256", "manifest_sha256", "launch_authorized"}, "INGESTION_REQUEST_FIELDS")
    require(request["schema"] == REQUEST_SCHEMA, "INGESTION_REQUEST_SCHEMA")
    require(type(request["job"]) is str and re.fullmatch(JOB_PATTERN, request["job"]), "INGESTION_REQUEST_JOB")
    for key, pattern in (("source_sha", shared.HEX40), ("archive_sha256", shared.HEX64),
                         ("manifest_sha256", shared.HEX64)):
        require(type(request[key]) is str and pattern.fullmatch(request[key]), "INGESTION_REQUEST_HASH:" + key)
    require(request["launch_authorized"] is False, "INGESTION_REQUEST_INERT")
    return request


def _check_bounds(document, code):
    for key, expected in BOUNDS.items():
        require(type(document.get(key)) is type(expected) and document[key] == expected, code + ":" + key)


def validate_authority(authority):
    identity = {"job", "source_sha", "archive_sha256", "manifest_sha256"}
    fields = identity | set(BOUNDS) | {"schema", "candidate", "owner_authorization_sha256",
        "inputs_sha256", "design_sha256", "evidence_contract_sha256", "worker_config"}
    require(type(authority) is dict and set(authority) == fields, "INGESTION_AUTHORITY_FIELDS")
    require(authority["schema"] == AUTHORITY_SCHEMA and authority["candidate"] == CANDIDATE,
            "INGESTION_AUTHORITY_CANDIDATE")
    validate_request({**{key: authority[key] for key in identity}, "schema": REQUEST_SCHEMA,
                      "launch_authorized": False})
    require(type(authority["owner_authorization_sha256"]) is str and
            shared.HEX64.fullmatch(authority["owner_authorization_sha256"]), "INGESTION_OWNER_HASH")
    _check_bounds(authority, "INGESTION_AUTHORITY_BOUND")
    for key, expected in (("inputs_sha256", frozen_inputs_hash()),
                          ("design_sha256", digest(canonical(DESIGN))),
                          ("evidence_contract_sha256", run_evidence.contract_digest(evidence_contract()))):
        require(authority[key] == expected, "INGESTION_AUTHORITY_BINDING:" + key)
    expected = worker_config(authority["job"], source_sha=authority["source_sha"])
    # Canonical bytes distinguish False from 0 and integral from floating values.
    require(type(authority["worker_config"]) is dict and
            canonical(authority["worker_config"]) == canonical(expected), "INGESTION_AUTHORITY_CONFIG")
    return authority


def validate_owner(path, authority):
    raw = Path(path).read_bytes()
    require(digest(raw) == authority["owner_authorization_sha256"], "INGESTION_OWNER_FILE_HASH")
    record = json.loads(raw)
    require(type(record) is dict and record.get("schema") == OWNER_SCHEMA and
            record.get("candidate") == CANDIDATE, "INGESTION_OWNER_SCOPE")
    quote = record.get("owner_instruction_raw")
    require(type(quote) is str and bool(quote.strip()), "INGESTION_OWNER_QUOTE")
    require(type(record.get("bounds")) is dict, "INGESTION_OWNER_BOUNDS")
    _check_bounds(record["bounds"], "INGESTION_OWNER_BOUND")
    return record


def validate_ledger_path(value):
    require(isinstance(value, (str, Path)), "INGESTION_LEDGER_PATH_REQUIRED")
    path = Path(value).expanduser().resolve()
    require(path.is_file() and path.is_relative_to(WORKSPACE_HOME.resolve()), "INGESTION_LEDGER_HOMEBASE_FILE")
    return path


def render_worker():
    """Replace only the contrast dispatch and result identity; retain its timeout."""
    tree = ast.parse(contrast.render_worker())
    inner = "\n".join((
        "import json, os, sys", "from pathlib import Path", "ROOT = Path(sys.argv[1])",
        "sys.path.insert(0, str(ROOT))",
        "sys.path.insert(0, str(ROOT / 'research/CAS_META_2_COMPOSITION'))",
        "os.environ['CAS_META2_RUN_TEACHING_CYCLE'] = '1'",
        "from cncm import rpa_learning_worker",
        "CONFIG = json.loads((ROOT / 'config.json').read_bytes())",
        "RESULTS = ROOT / 'results'", "ARTIFACTS = RESULTS / 'artifacts'",
        "report = rpa_learning_worker.run(CONFIG, root=ROOT, results=RESULTS, artifacts=ARTIFACTS)",
        "print(json.dumps({'status': report['status']}))"))
    replacements = {"INNER_RUNNER": inner, "RESULT_SCHEMA": RESULT_SCHEMA,
                    "FAILURE_SCHEMA": FAILURE_SCHEMA, "MAX_WALL_SECONDS": MAX_WALL_SECONDS}
    found = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in replacements:
                node.value = ast.Constant(replacements[name])
                found.add(name)
    require(found == set(replacements), "INGESTION_WORKER_TEMPLATE_CHANGED")
    timeouts = [node.value for node in ast.walk(tree) if isinstance(node, ast.keyword) and node.arg == "timeout"]
    require(len(timeouts) == 1 and ast.unparse(timeouts[0]) == "MAX_WALL_SECONDS", "INGESTION_INNER_TIMEOUT")
    tree.body[0] = ast.Expr(ast.Constant(CANDIDATE + ": exposed teaching and checkpoint reload only; no learning-benefit claim."))
    return ast.unparse(ast.fix_missing_locations(tree)) + "\n"


def evidence_contract():
    names = {"results/result.json": "terminal envelope", "results/result.json.sha256": "envelope digest",
             "results/artifacts/manifest.json": "artifact inventory"}
    names.update({"results/artifacts/" + name: "source-bound smoke/reload evidence"
                  for name in _probe().EXPECTED_ARTIFACTS})
    return run_evidence.contract(EXPERIMENT["profile"], [
        run_evidence.requirement(key, title, kind="json" if key.endswith(".json") else "file")
        for key, title in names.items()], notes=[
            "Exposed-material mechanical training and checkpoint reload; not a matched learning test.",
            "All checkpoints and measurement files must arrive intact before compute cleanup is certified."])


def package_data_files():
    return tuple(sorted(set(shared.PILOT + name for name in PACKAGING_SOURCES)
                        | {item["path"] for item in frozen_inputs()}))


def build_smoke_package(output, *, source_sha, git_bytes_fn=None, git_paths_fn=None):
    """Use committed bytes, the pinned import wheels, and the common transport."""
    output = Path(output).absolute()
    require(not output.exists() and output.parent.is_dir() and output.is_relative_to(ROOT / "records")
            and output != ROOT / "records", "INGESTION_FRESH_PACKAGE_PATH")
    get_bytes, get_paths = git_bytes_fn or shared.git_bytes, git_paths_fn or shared.git_tree_paths
    for name in PACKAGING_SOURCES:
        require(get_bytes(ROOT, source_sha, shared.PILOT + name) == (ROOT / name).read_bytes(),
                "INGESTION_PACKAGING_SOURCE_NOT_COMMITTED:" + name)
    source = render_worker()
    transport = run_evidence.unified_transport(source)
    members = shared.resolve_members(ROOT, source_sha, git_bytes_fn=get_bytes, git_paths_fn=get_paths,
        worker_name=WORKER_NAME, worker_source=run_evidence.unified_worker_source(source),
        extra_files=package_data_files())
    for item in frozen_inputs():
        raw = members[item["path"]]
        require(len(raw) == item["bytes"] and digest(raw) == item["sha256"],
                "INGESTION_INPUT_NOT_COMMITTED:" + item["path"])
    manifest = shared.manifest_for(members, source_sha, worker_name=WORKER_NAME,
        experiment=EXPERIMENT, package_schema="cncm-ordered-ingestion-smoke-package/1", design=DESIGN)
    manifest["frozen_budget"] = {**BOUNDS, "seed": SEED, "checkpoints": 3, "reload_phases": 2}
    manifest["inputs"] = frozen_inputs()
    manifest["transport"] = {"implementation": "aws.run_evidence.render_transport",
        "replaced_functions": transport["replaced"], "publisher_wired": transport["publisher_wired"],
        "marker_last": True, "predeclared_contract_sha256": run_evidence.contract_digest(evidence_contract())}
    members[shared.MANIFEST_NAME] = canonical(manifest)
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, raw in sorted(members.items()):
            info = ZipInfo(name, date_time=(2026, 9, 16, 0, 0, 0))
            info.compress_type, info.external_attr = ZIP_DEFLATED, 0o100644 << 16
            archive.writestr(info, raw)
    raw = buffer.getvalue()
    require(len(raw) <= shared.MAX_ARCHIVE_BYTES, "INGESTION_ARCHIVE_BOUND")
    output.mkdir()
    (output / "source.zip").write_bytes(raw)
    receipt = {"schema": "cncm-ordered-ingestion-smoke-package-receipt/1", "status": "SOURCE_ONLY_NO_LAUNCH",
        "source_sha": source_sha, "archive": str(output / "source.zip"), "archive_sha256": digest(raw),
        "archive_bytes": len(raw), "manifest_sha256": digest(members[shared.MANIFEST_NAME]),
        "member_count": len(members), "manifest": manifest}
    (output / "receipt.json").write_bytes(canonical(receipt))
    return receipt


class IngestionSmokeProvider(lifecycle.CandidateProvider):
    def bind_authority(self, authority):
        validate_authority(authority)
        for key in ("job", "source_sha", "archive_sha256", "manifest_sha256"):
            require(getattr(self, key) == authority[key], "INGESTION_PROVIDER_BINDING:" + key)
        self.bound_config = json.loads(canonical(authority["worker_config"]))
        self.worker_name, self.result_schema = WORKER_NAME, RESULT_SCHEMA
        self.failure_statuses = ("WORKER_FAILED", "REMOTE_WORKER_FAILED", "INGESTION_SMOKE_FAILED")

    def _worker_config(self, bucket):
        require(hasattr(self, "bound_config"), "INGESTION_AUTHORITY_NOT_BOUND")
        require(self.region == BOUNDS["region"], "INGESTION_PROVIDER_REGION")
        return {**json.loads(canonical(self.bound_config)), "bucket": bucket}


def execute(request, authority, provider, *, receipt_dir, owner_authorization_path,
            ledger_path):
    validate_request(request)
    validate_authority(authority)
    validate_owner(owner_authorization_path, authority)
    ledger_path = validate_ledger_path(ledger_path)
    require(Path(provider.ledger_path).resolve() == ledger_path, "INGESTION_PROVIDER_LEDGER_MISMATCH")
    provider.bind_authority(authority)
    return lifecycle.execute(request, authority, provider, ledger_path=ledger_path,
        receipt_dir=receipt_dir, owner_authorization_path=owner_authorization_path,
        validate_request_fn=validate_request, validate_authority_fn=validate_authority,
        evidence_contract=evidence_contract())


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    for field in ("request", "request-sha256", "authority", "authority-sha256", "receipt-dir", "owner-authorization", "ledger-path"):
        parser.add_argument("--" + field)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"status": "PLAN_ONLY", "design": DESIGN, "inputs": frozen_inputs(),
                          "provider_calls": 0, "reservation_created": False}))
        return 0
    require(all(getattr(args, key) for key in ("request", "request_sha256", "authority", "authority_sha256",
        "receipt_dir", "owner_authorization", "ledger_path")), "INGESTION_EXPLICIT_INPUTS")
    request_raw, authority_raw = Path(args.request).read_bytes(), Path(args.authority).read_bytes()
    require(digest(request_raw) == args.request_sha256 and digest(authority_raw) == args.authority_sha256,
            "INGESTION_REQUEST_AUTHORITY_FILE_HASH")
    request, authority = json.loads(request_raw), json.loads(authority_raw)
    validate_request(request)
    validate_authority(authority)
    validate_owner(args.owner_authorization, authority)
    ledger_path = validate_ledger_path(args.ledger_path)
    provider = IngestionSmokeProvider(job=request["job"], source_sha=request["source_sha"],
        archive_sha256=request["archive_sha256"], manifest_sha256=request["manifest_sha256"],
        ledger_path=ledger_path, clients=lifecycle._clients(args.profile),
        client_error=lifecycle._client_error(), source_archive=lifecycle._locate_archive(request["archive_sha256"]))
    result = execute(request, authority, provider, receipt_dir=args.receipt_dir,
                     owner_authorization_path=args.owner_authorization, ledger_path=ledger_path)
    print(json.dumps({"status": result["status"], "completed_deliverable": result["completed_deliverable"],
                      "stages": result["stages"]}))
    return 0 if result["completed_deliverable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
