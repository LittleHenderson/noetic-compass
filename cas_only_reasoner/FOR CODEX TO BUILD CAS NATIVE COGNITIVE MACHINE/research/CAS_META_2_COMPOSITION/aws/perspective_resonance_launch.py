"""Inert perspective package/worker profile over the existing bounded AWS lifecycle."""
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

from aws import complementary_teaching_launch as parent
from aws import graph_training_curriculum_launch as infrastructure
from aws import graph_training_candidate_launch as lifecycle
from aws import recurrent_cjt_launch as recurrent
from aws import run_evidence
from cas_meta2 import perspective_resonance as p
from cas_meta2 import perspective_worker as worker

SCHEMA = "cas.perspective-launch/0.1"
REQUEST_SCHEMA = "cas.perspective-launch-request/0.1"
AUTHORITY_SCHEMA = "cas.perspective-launch-authority/0.1"
WORKER_NAME = "perspective_resonance_worker.py"
JOB_PATTERN = r"cas-meta2-perspective-\d{14}-[a-f0-9]{8}"
EXPERIMENT = {"profile":p.SCHEMA,"candidate":p.DIRECTIVE,
              "entrypoint":"cas_meta2.perspective_worker.run"}
SEEDS = (101,202,303)
PREPARED = "records/perspective_resonance_001/prepared/"
RECORD_INPUTS = (
    "DESIGN_TASK_BINDINGS.md",
    "source/Connected_Perspective_Learning_and_CAS_Ohm_v0.1.md",
    "source/Perspective_Family_Authoring_Example.json",
    "source/Perspective_Resonance_Profile_v0.1.json",
    "source/public_exercises.jsonl",
    "source/SOURCE_IDENTITIES.json",
    "source/teacher_targets.jsonl",
    "prepared/parent_bindings.json",
    "prepared/perspective_audit_public.json",
    "prepared/perspective_audit_teacher_targets.json",
    "prepared/source_manifest.json",
    "prepared/unsigned_costed_request.json",
    "prepared/unsigned_worker_config.json",
)


def worker_config(job, *, execution_enabled=False):
    config = json.loads((ROOT / PREPARED / "unsigned_worker_config.json").read_bytes())
    config.update({"job":job,"execution_enabled":execution_enabled})
    return config


def costed_request(*, package=None):
    request = json.loads((ROOT / PREPARED / "unsigned_costed_request.json").read_bytes())
    return {**request,"package":package,"worker_config":worker_config(None)}


def render_worker():
    original = recurrent.render_worker()
    needle = "from cas_meta2.recurrent_cjt import runner"
    p.require(original.count(needle)==1,"PERSPECTIVE_WORKER_DISPATCH_ANCHOR")
    return original.replace(needle,"from cas_meta2 import perspective_worker as runner").replace(
        "cas.recurrent-cjt-result/1",worker.SCHEMA).replace(
        "cas.recurrent-cjt-failure/1","cas.perspective-failure/0.1").replace(
        "MAX_WALL_SECONDS = 2400.0","MAX_WALL_SECONDS = 3000.0").replace(
        "timeout=MAX_WALL_SECONDS + 1800","timeout=3000").replace(
        "CAS_RDCJT_001 worker: train both arms, sweep the depths, upload.",
        "CAS_PERSPECTIVE_RESONANCE_001: six courses and shared perspective audits.")


def package_data_files():
    files = list(parent.package_data_files())
    files += [infrastructure.PILOT + name for name in (
        "cas_meta2/perspective_resonance.py","cas_meta2/perspective_worker.py",
        "aws/perspective_resonance_launch.py","tools/prepare_perspective_resonance.py")]
    # Fixed inputs only: later package receipts, rehearsals and scratch outputs
    # must never become source dependencies of the next package.
    files += [infrastructure.PILOT + "records/perspective_resonance_001/" + name
              for name in RECORD_INPUTS]
    files.append("research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/neural.py")
    return tuple(dict.fromkeys(files))


def evidence_contract():
    required = [run_evidence.requirement("results/result.json","perspective envelope",kind="json"),
        run_evidence.requirement("results/result.json.sha256","envelope sidecar"),
        run_evidence.requirement("results/artifacts/manifest.json","all declared artifacts",kind="json"),
        run_evidence.requirement("results/artifacts/complementary_report.json","raw parent courses",kind="json"),
        run_evidence.requirement("results/artifacts/perspective_report.json","sealed semantic reports",kind="json")]
    for condition in p.CONDITIONS:
        for seed in SEEDS:
            label = "%s_%d" % (condition,seed)
            for suffix in ("_course.json","_latest.pt","_final.pt"):
                required.append(run_evidence.requirement("results/artifacts/"+label+suffix,"course evidence"))
            for cursor in (0,37,38,39,40,77,78,79,80,117,118,119,120,157,158,159,160):
                required.append(run_evidence.requirement("results/artifacts/%s_monitor_%03d.pt"%(label,cursor),
                                                         "declared observation checkpoint"))
    return run_evidence.contract(p.SCHEMA,required,notes=[
        "No missing native flow may be imputed. No empirical intervention is included.",
        "Complete six-course collection is required; no automatic acceptance."])


def build_perspective_package(output, *, source_sha, git_bytes_fn=None, git_paths_fn=None):
    output = Path(output).absolute()
    p.require(not output.exists() and output.parent.is_dir() and output.is_relative_to(ROOT/"records"),
              "PERSPECTIVE_FRESH_PACKAGE_PATH")
    source = render_worker()
    members = infrastructure.resolve_members(ROOT,source_sha,
        git_bytes_fn=git_bytes_fn or infrastructure.git_bytes,
        git_paths_fn=git_paths_fn or infrastructure.git_tree_paths,
        worker_name=WORKER_NAME,worker_source=run_evidence.unified_worker_source(source),
        extra_files=package_data_files())
    manifest = infrastructure.manifest_for(members,source_sha,worker_name=WORKER_NAME,
        experiment=EXPERIMENT,package_schema=SCHEMA,design={
            "launch_enabled":False,"candidate_design":costed_request()})
    manifest["frozen_budget"] = {"learning_rate":.003,"seeds":list(SEEDS),
        "conditions":list(p.CONDITIONS),"updates_per_course":160,"courses":6,
        "total_optimizer_steps":960}
    manifest["transport"] = {"implementation":"aws.run_evidence.render_transport","marker_last":True,
                             "predeclared_contract_sha256":run_evidence.contract_digest(evidence_contract())}
    members[infrastructure.MANIFEST_NAME] = infrastructure.canonical(manifest)
    buffer=io.BytesIO()
    with ZipFile(buffer,"w",ZIP_DEFLATED) as archive:
        for name,raw in sorted(members.items()):
            info=ZipInfo(name,date_time=(2026,9,16,0,0,0))
            info.compress_type=ZIP_DEFLATED
            info.external_attr=0o100644<<16
            archive.writestr(info,raw)
    raw=buffer.getvalue()
    p.require(len(raw)<=infrastructure.MAX_ARCHIVE_BYTES,"PERSPECTIVE_ARCHIVE_BOUND")
    output.mkdir()
    (output/"source.zip").write_bytes(raw)
    receipt={"schema":SCHEMA,"source_sha":source_sha,"archive":str(output/"source.zip"),
        "archive_sha256":infrastructure.digest(raw),"archive_bytes":len(raw),
        "manifest_sha256":infrastructure.digest(members[infrastructure.MANIFEST_NAME]),
        "manifest":manifest,"status":"SOURCE_ONLY_NO_LAUNCH"}
    parent.runner.write_json(output/"receipt.json",receipt)
    return receipt


def validate_request(request):
    p.require(request.get("schema")==REQUEST_SCHEMA and request.get("launch_authorized") is False,
              "PERSPECTIVE_REQUEST_INERT")
    p.require(bool(re.fullmatch(JOB_PATTERN,request.get("job",""))),"PERSPECTIVE_JOB_ID")
    for field,length in (("source_sha",40),("archive_sha256",64),("manifest_sha256",64)):
        p.require(bool(re.fullmatch("[a-f0-9]{%d}"%length,request.get(field,""))),
                  "PERSPECTIVE_REQUEST_HASH:"+field)
    return request


def validate_authority(authority):
    p.require(authority.get("schema")==AUTHORITY_SCHEMA,"PERSPECTIVE_AUTHORITY_SCHEMA")
    p.require(authority.get("candidate")==p.DIRECTIVE and
              authority.get("reservation_usd")==infrastructure.RESERVATION_USD,
              "PERSPECTIVE_AUTHORITY_SCOPE")
    p.require(authority.get("training") is True and
              authority.get("optimizer_updates") == 960 and
              authority.get("max_wall_seconds") == 3000 and
              authority.get("conditions") == list(p.CONDITIONS),
              "PERSPECTIVE_AUTHORITY_TRAINING_BUDGET")
    config=worker_config(authority.get("job"),execution_enabled=True)
    p.require(authority.get("worker_config")==config,"PERSPECTIVE_AUTHORITY_CONFIG")
    worker.validate_config(config,ROOT)
    p.require(authority.get("evidence_contract_sha256")==run_evidence.contract_digest(evidence_contract()),
              "PERSPECTIVE_AUTHORITY_EVIDENCE")
    p.require(bool(re.fullmatch("[a-f0-9]{64}",authority.get("owner_authorization_sha256",""))),
              "PERSPECTIVE_OWNER_AUTHORIZATION_REQUIRED")
    return authority


class PerspectiveProvider(recurrent.RecurrentCjtProvider):
    def bind_authority(self,authority):
        validate_authority(authority)
        self.bound_config=dict(authority["worker_config"])
        self.worker_name=WORKER_NAME
        self.result_schema=worker.SCHEMA
        self.failure_statuses=("TEACHING_INCOMPLETE","WORKER_FAILED","REMOTE_WORKER_FAILED")

    def _worker_config(self,bucket):
        p.require(hasattr(self,"bound_config"),"PERSPECTIVE_AUTHORITY_NOT_BOUND")
        return {**self.bound_config,"bucket":bucket,"region":self.region,"source_sha":self.source_sha}


def execute(request,authority,provider,**kwargs):
    validate_request(request)
    validate_authority(authority)
    provider.bind_authority(authority)
    return lifecycle.execute(request,authority,provider,validate_request_fn=validate_request,
        validate_authority_fn=validate_authority,evidence_contract=evidence_contract(),**kwargs)


if __name__=="__main__":
    print(json.dumps(costed_request(),indent=2))
