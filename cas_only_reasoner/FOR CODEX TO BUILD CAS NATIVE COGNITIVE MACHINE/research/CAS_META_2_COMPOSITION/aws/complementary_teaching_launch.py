"""Opt-in complementary entrypoint through the existing bounded AWS lifecycle.

Import/plan/package are non-neural. This module never changes shared budget
constants. Owner authority remains a separate exact package-bound document.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from aws import graph_training_curriculum_launch as infrastructure
from aws import graph_training_candidate_launch as lifecycle
from aws import recurrent_cjt_launch as recurrent
from aws import run_evidence
from cas_meta2.complementary_teaching import IMPLEMENTATION_ID, PROFILE_ID
from cas_meta2.complementary_teaching.course import CONDITIONS, SEEDS, digest, require
from cas_meta2.complementary_teaching import runner

SCHEMA = "cas.complementary-launch/0.1"
REQUEST_SCHEMA = "cas.complementary-launch-request/0.1"
AUTHORITY_SCHEMA = "cas.complementary-launch-authority/0.1"
WORKER_NAME = "complementary_teaching_worker.py"
JOB_PATTERN = r"cas-meta2-complementary-\d{14}-[a-f0-9]{8}"
RESERVATION_USD = infrastructure.RESERVATION_USD
MODULES = tuple("cas_meta2/complementary_teaching/" + name for name in
                ("__init__.py", "course.py", "data.py", "runner.py", "evaluation.py"))
EXPERIMENT = {"profile": PROFILE_ID, "candidate": IMPLEMENTATION_ID,
              "entrypoint": "cas_meta2.complementary_teaching.runner.run"}


def worker_config(job, *, execution_enabled=False):
    data = json.loads((ROOT / runner.DATA_PATH).read_bytes())
    return {"candidate": IMPLEMENTATION_ID, "job": job, "execution_enabled": execution_enabled,
            "learning_rate": .003, "max_wall_seconds": runner.MAX_WALL_SECONDS,
            "data_file_sha256": runner.file_sha(ROOT / runner.DATA_PATH),
            "data_sha256": data["data_sha256"],
            "initial_checkpoint_sha256": runner.file_sha(ROOT / runner.INITIAL_PATH),
            "training": True, "comparison_conditions": list(CONDITIONS)}


def costed_request(*, package=None, job="cas-meta2-complementary-20260916000000-00000000"):
    config = worker_config(job)
    per_course = {"teaching_decisions": 1152, "optimizer_updates": 160,
                  "training_sample_core_passes": 4320, "training_batch_core_calls_planned": 600,
                  "monitor_answers": 120 * 17, "initial_retention_answers": 126,
                  "final_answers": 216, "reload_answers": 216, "numerical_gradient_answers": 2,
                  "state_isolation_answers": 6}
    per_course["total_inference_core_passes"] = 8 * sum(per_course[k] for k in
        ("monitor_answers", "initial_retention_answers", "final_answers", "reload_answers", "numerical_gradient_answers", "state_isolation_answers"))
    return {"schema": "cas.complementary-costed-request/0.1", "candidate": IMPLEMENTATION_ID,
            "status": "UNSIGNED_EXECUTION_REQUEST", "owner_authorization": None, "signature": None,
            "execution_enabled": False, "job": job, "worker_config": config,
            "training": True, "optimizer_updates": 1440, "total_optimizer_steps": 1440,
            "max_wall_seconds": runner.MAX_WALL_SECONDS,
            "conditions": list(CONDITIONS), "seeds": list(SEEDS), "courses": 9,
            "per_course": per_course, "all_courses": {key: value * 9 for key, value in per_course.items()},
            "resource_limits": {"instance_type": infrastructure.RESOURCE_PLAN["instance_type"],
                "region": infrastructure.RESOURCE_PLAN["region"], "instance_count": 1,
                "gpu_memory_bytes": runner.MAX_GPU_MEMORY_BYTES, "evidence_storage_bytes": runner.MAX_STORAGE_BYTES,
                "worker_wall_seconds": 3600, "experiment_wall_seconds": runner.MAX_WALL_SECONDS,
                "install_collection_allowance_seconds": 600, "instance_wall_seconds": 7200,
                "automatic_retries": 0, "reservation_usd": RESERVATION_USD,
                "rate_ceiling_usd_hour": infrastructure.RESOURCE_PLAN["on_demand_rate_ceiling_usd"],
                "estimate_basis": "Existing bounded provider profile: 2 h x $2.52 + $1.48 ancillary = $6.52, rounded to $7 reservation; live preflight still required."},
            "package": package, "data_scope": "30 new topology families / 90 whole questions; 8-10 nodes versus 3-4 CFC nodes (explicit structural/size-transfer amendment)",
            "initializer_rule": "Earliest completed/rescued recurrent seed 20260912 by chronology, selected without score ranking; same frozen encoder and weights, new AdamW initialization for each course.",
            "compute_count_scope": "600 training_batch_core_calls_planned per course are batched-equivalent update-depth units. Production loops each sample: 4320 actual training core calls per course, plus separately charged evaluation/numerical calls.",
            "retention_scope": "Six-face role-recognition audit; all-six application stability is not claimed.",
            "claims": "COMPLEMENTARY_TEACHING_READY_NEURAL_UNTESTED only after package and pure validation; no benefit or production claim."}


def render_worker():
    original = recurrent.render_worker()
    needle = "from cas_meta2.recurrent_cjt import runner"
    require(original.count(needle) == 1, "COMPLEMENTARY_WORKER_DISPATCH_ANCHOR")
    return original.replace(needle, "from cas_meta2.complementary_teaching import runner").replace(
        "CAS_RDCJT_001 worker: train both arms, sweep the depths, upload.",
        "CAS_COMPLEMENTARY_TEACHING_001: nine courses and frozen evaluation.").replace(
        "cas.recurrent-cjt-result/1", runner.SCHEMA).replace(
        "cas.recurrent-cjt-failure/1", "cas.complementary-failure/0.1").replace(
        "MAX_WALL_SECONDS = 2400.0", "MAX_WALL_SECONDS = 3000.0").replace(
        "timeout=MAX_WALL_SECONDS + 1800", "timeout=MAX_WALL_SECONDS")


def package_data_files():
    return recurrent.package_data_files() + tuple(infrastructure.PILOT + name for name in MODULES) + (
        infrastructure.PILOT + runner.DATA_PATH,
        infrastructure.PILOT + runner.INITIAL_PATH,
        infrastructure.PILOT + "records/complementary_teaching_001/preparation_20260916/historical_exclusions.json")


def build_complementary_package(output, *, source_sha, git_bytes_fn=None, git_paths_fn=None):
    """Reuse member resolver/transport; candidate manifest does not inherit old 64/256 budgets."""
    output = Path(output).absolute()
    require(not output.exists() and output.parent.is_dir() and output.is_relative_to(ROOT / "records"),
            "COMPLEMENTARY_FRESH_PACKAGE_PATH")
    source = render_worker()
    members = infrastructure.resolve_members(ROOT, source_sha,
        git_bytes_fn=git_bytes_fn or infrastructure.git_bytes,
        git_paths_fn=git_paths_fn or infrastructure.git_tree_paths,
        worker_name=WORKER_NAME, worker_source=run_evidence.unified_worker_source(source),
        extra_files=package_data_files())
    design = costed_request()
    manifest = infrastructure.manifest_for(members, source_sha, worker_name=WORKER_NAME,
        experiment=EXPERIMENT, package_schema=SCHEMA, design={"launch_enabled": False, "candidate_design": design})
    manifest["frozen_budget"] = {"learning_rate": .003, "seeds": list(SEEDS), "conditions": list(CONDITIONS),
                                  "updates_per_course": 160, "courses": 9, "total_optimizer_steps": 1440}
    manifest["transport"] = {"implementation": "aws.run_evidence.render_transport", "marker_last": True,
                             "predeclared_contract_sha256": run_evidence.contract_digest(evidence_contract())}
    manifest_name = infrastructure.MANIFEST_NAME
    members[manifest_name] = infrastructure.canonical(manifest)
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for name, raw in sorted(members.items()):
            info = ZipInfo(name, date_time=(2026, 9, 16, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, raw)
    raw = buffer.getvalue()
    require(len(raw) <= infrastructure.MAX_ARCHIVE_BYTES, "COMPLEMENTARY_ARCHIVE_BOUND")
    output.mkdir()
    (output / "source.zip").write_bytes(raw)
    receipt = {"schema": SCHEMA, "source_sha": source_sha, "archive": str(output / "source.zip"),
               "archive_sha256": infrastructure.digest(raw), "archive_bytes": len(raw),
               "manifest_sha256": infrastructure.digest(members[manifest_name]), "manifest": manifest,
               "status": "SOURCE_ONLY_NO_LAUNCH"}
    runner.write_json(output / "receipt.json", receipt)
    return receipt


def evidence_contract():
    required = [run_evidence.requirement("results/result.json", "candidate envelope", kind="json"),
                run_evidence.requirement("results/result.json.sha256", "envelope sidecar"),
                run_evidence.requirement("results/artifacts/manifest.json", "all declared artifacts", kind="json"),
                run_evidence.requirement("results/artifacts/complementary_report.json", "nine courses plus exact analysis", kind="json")]
    for condition in CONDITIONS:
        for seed in SEEDS:
            label = "%s_%d" % (condition, seed)
            for suffix in ("_course.json", "_latest.pt", "_final.pt"):
                required.append(run_evidence.requirement("results/artifacts/" + label + suffix, "course evidence"))
            for cursor in (0, 37, 38, 39, 40, 77, 78, 79, 80, 117, 118, 119, 120, 157, 158, 159, 160):
                required.append(run_evidence.requirement("results/artifacts/%s_monitor_%03d.pt" % (label, cursor), "declared observation checkpoint"))
    return run_evidence.contract(PROFILE_ID, required, notes=["Missing course/monitor/reload evidence prevents completion; no automatic promotion."])


def validate_request(request):
    require(request.get("schema") == REQUEST_SCHEMA and request.get("launch_authorized") is False,
            "COMPLEMENTARY_REQUEST_INERT")
    require(bool(re.fullmatch(JOB_PATTERN, request.get("job", ""))), "COMPLEMENTARY_JOB_ID")
    for field, length in (("source_sha", 40), ("archive_sha256", 64), ("manifest_sha256", 64)):
        require(bool(re.fullmatch("[a-f0-9]{%d}" % length, request.get(field, ""))), "COMPLEMENTARY_REQUEST_HASH:" + field)
    return request


def validate_authority(authority):
    require(authority.get("schema") == AUTHORITY_SCHEMA, "COMPLEMENTARY_AUTHORITY_SCHEMA")
    require(authority.get("candidate") == IMPLEMENTATION_ID and authority.get("reservation_usd") == RESERVATION_USD,
            "COMPLEMENTARY_AUTHORITY_SCOPE")
    require(authority.get("training") is True, "COMPLEMENTARY_AUTHORITY_TRAINING_REQUIRED")
    require(authority.get("optimizer_updates") == 1440 and authority.get("total_optimizer_steps") == 1440,
            "COMPLEMENTARY_AUTHORITY_UPDATES_FROZEN")
    require(authority.get("max_wall_seconds") == runner.MAX_WALL_SECONDS,
            "COMPLEMENTARY_AUTHORITY_WALL_FROZEN")
    require(authority.get("conditions") == list(CONDITIONS) and authority.get("seeds") == list(SEEDS),
            "COMPLEMENTARY_AUTHORITY_CONDITIONS_SEEDS_FROZEN")
    expected = worker_config(authority.get("job"), execution_enabled=True)
    require(authority.get("worker_config") == expected, "COMPLEMENTARY_AUTHORITY_CONFIG")
    require(authority.get("evidence_contract_sha256") == run_evidence.contract_digest(evidence_contract()),
            "COMPLEMENTARY_AUTHORITY_EVIDENCE_CONTRACT")
    require(bool(re.fullmatch("[a-f0-9]{64}", authority.get("owner_authorization_sha256", ""))),
            "COMPLEMENTARY_OWNER_AUTHORIZATION_REQUIRED")
    return authority


class ComplementaryProvider(recurrent.RecurrentCjtProvider):
    def bind_authority(self, authority):
        validate_authority(authority)
        self.bound_config = dict(authority["worker_config"])
        self.worker_name = WORKER_NAME
        self.result_schema = runner.SCHEMA
        self.failure_statuses = ("TEACHING_INCOMPLETE", "WORKER_FAILED", "REMOTE_WORKER_FAILED")

    def _worker_config(self, bucket):
        require(hasattr(self, "bound_config"), "COMPLEMENTARY_AUTHORITY_NOT_BOUND")
        return {**self.bound_config, "bucket": bucket, "region": self.region, "source_sha": self.source_sha}


def execute(request, authority, provider, **kwargs):
    validate_request(request)
    validate_authority(authority)
    provider.bind_authority(authority)
    return lifecycle.execute(request, authority, provider, validate_request_fn=validate_request,
        validate_authority_fn=validate_authority, evidence_contract=evidence_contract(), **kwargs)


if __name__ == "__main__":
    print(json.dumps(costed_request(), indent=2))
