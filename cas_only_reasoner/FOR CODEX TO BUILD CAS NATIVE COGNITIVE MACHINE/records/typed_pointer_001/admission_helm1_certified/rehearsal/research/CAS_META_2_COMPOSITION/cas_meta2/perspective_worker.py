"""Real opt-in dispatch into the complementary CUDA worker; no torch at import."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import time

from . import perspective_resonance as p

SCHEMA = "cas.perspective-result/0.1"
BINDINGS_PATH = "records/perspective_resonance_001/prepared/parent_bindings.json"
SOURCES_PATH = "records/perspective_resonance_001/prepared/source_manifest.json"
DATA_PATH = "records/complementary_teaching_001/preparation_20260916/data_manifest.json"


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def validate_config(config, pilot):
    p.require(config.get("candidate") == p.DIRECTIVE, "PERSPECTIVE_OPT_IN_REQUIRED")
    p.require(config.get("execution_enabled") is True, "PERSPECTIVE_EXECUTION_DISABLED")
    p.require(config.get("training") is True and config.get("optimizer_updates") == 960,
              "PERSPECTIVE_TRAINING_BUDGET_FROZEN")
    p.require(config.get("empirical_response_enabled", False) is False,
              p.EMPIRICAL_STATUS)
    p.require(config.get("adaptive_policy_enabled", False) is False, "PERSPECTIVE_SHADOW_ONLY")
    p.require(tuple(config.get("comparison_conditions", p.CONDITIONS)) == p.CONDITIONS,
              "PERSPECTIVE_CONDITIONS_FROZEN")
    for field, relative in (("perspective_bindings_file_sha256", BINDINGS_PATH),
                            ("perspective_sources_file_sha256", SOURCES_PATH)):
        p.require(config.get(field) == file_hash(pilot / relative), "PERSPECTIVE_INPUT_HASH:" + field)
    sources = json.loads((pilot / SOURCES_PATH).read_bytes())
    p.require(sources["aggregate_sha256"] == p.identity(sources["files"]),
              "PERSPECTIVE_SOURCE_AGGREGATE")
    for source in sources["files"]:
        p.require("\\" not in source["path"], "PERSPECTIVE_SOURCE_REQUIRES_PORTABLE_PATH")
        p.require(source.get("anchor", "composition") in ("composition", "homebase"),
                  "PERSPECTIVE_SOURCE_ANCHOR")
        root = (pilot.parent.parent if source.get("anchor") == "homebase" else pilot).resolve()
        path = (root / source["path"]).resolve()
        p.require(path.is_relative_to(root), "PERSPECTIVE_SOURCE_PATH_ESCAPE")
        p.require(path.stat().st_size == source["bytes"] and file_hash(path) == source["sha256"],
                  "PERSPECTIVE_SOURCE_CHANGED:" + source["path"])
    bindings = json.loads((pilot / BINDINGS_PATH).read_bytes())
    p.require(bindings["parent_condition"] == "ALT_COMPONENT_WHOLE", "PERSPECTIVE_PARENT_CHANGED")
    p.require(bindings.get("parent_data_file_sha256") == file_hash(pilot / DATA_PATH),
              "PERSPECTIVE_PARENT_DATA_CHANGED")
    p.require(bindings.get("tokenizer", {}).get("unchanged_original_fit") is True,
              "PERSPECTIVE_TOKENIZER_CHECK_REQUIRED")
    return bindings


def transform_factory(condition):
    p.require(condition in p.CONDITIONS, "PERSPECTIVE_CONDITION_UNKNOWN")
    def transform(task, **kwargs):
        return p.transform_public(task, **dict(kwargs, condition=condition))
    return transform


def restore_reports(parent, panels, *, bindings=None):
    """Regenerate perspective metrics from retained parent prediction events."""
    targets = p.perspective_target_manifest(panels)
    records = []
    for course in parent.get("courses", []):
        final = course["final"]
        # Reconstruct and check the parent's original pre-target seal first.
        public_rows = {name: [{key: deepcopy(value) for key, value in row.items()
                               if key not in ("expected", "correct")} for row in rows]
                       for name, rows in final["rows"].items()}
        p.require(p.identity(public_rows) == final["prediction_seal_sha256"],
                  "PARENT_PREDICTION_SEAL_MISMATCH")
        measured = []
        for name in panels:
            for row in final["rows"][name]:
                measured.append({"record_id": row["record_id"], "selected": row["prediction"],
                                 "scores": deepcopy(row["scores"]),
                                 "provenance": "RETAINED_PARENT_PREDICTION"})
        sealed = p.seal_predictions(measured)
        report = p.behavioral_report(sealed, targets["teacher_targets"], targets["comparisons"])
        cross_ids = {task["record_id"] for task in panels["perspective_cross_view"]}
        cross_targets = [target for target in targets["teacher_targets"] if target["record_id"] in cross_ids]
        cross_sealed = p.seal_predictions([row for row in measured if row["record_id"] in cross_ids])
        cross = p.behavioral_report(cross_sealed, cross_targets, [])
        profiles = []
        if bindings is not None:
            for root in sorted({target["root_family_id"] for target in targets["teacher_targets"]}):
                root_targets = [target for target in targets["teacher_targets"] if target["root_family_id"] == root]
                ids = {target["record_id"] for target in root_targets}
                root_predictions = p.seal_predictions([row for row in measured if row["record_id"] in ids])
                root_pairs = [pair for pair in targets["comparisons"] if pair["root_family_id"] == root]
                root_report = p.behavioral_report(root_predictions, root_targets, root_pairs)
                context = {"root_family_id":root,"graph_revision":bindings["parent_data_sha256"],
                    "cube_revision":bindings["parent_profile"],"view_revision":p.SCHEMA,
                    "model_identity":p.NATIVE_PRODUCER_SHA256,"checkpoint_identity":final["weight_identity"],
                    "input_adapter_identity":"graph_teaching.real_framework.build_encoder:frozen_original",
                    "tokenizer_identity":bindings["tokenizer"]["identity"],
                    "recurrent_profile":"CAS_RDCJT_001","scoring_profile":"FROZEN_OPTION_DOT_PRODUCT",
                    "depth":final["depth"],"assistance_profile":"NO_WORKED_QUERY_ANSWER",
                    "source_event_references":[final["prediction_seal_sha256"],course["condition"],str(course["seed"])],
                    "trajectory_status":"UNAVAILABLE_NO_FULL_TENSOR_CAPTURE"}
                profiles.append(p.idea_response_profile(context=context,sealed_predictions=root_predictions,
                    behavioral=root_report,coverage={"root_training_exposures":0,
                    "status":"HELD_OUT_ROOT_ALL_DERIVED_VIEWS_GROUPED"},
                    cost={"scope":"FULL_COURSE_ACCOUNTING_NOT_ATTRIBUTED_PER_IDEA",
                          "actual_accounting":course.get("actual_accounting")}))
        records.append({"condition": course["condition"], "seed": course["seed"],
                        "parent_prediction_seal_sha256": final["prediction_seal_sha256"],
                        "checkpoint_identity": final["weight_identity"],
                        "sealed_predictions": sealed, "behavioral": report,
                        "cross_view": cross, "native_flow": p.native_flow_snapshot(
                            checkpoint_identity=final["weight_identity"], depth=final["depth"]),
                        "calibrated_activation_response": {"status":p.EMPIRICAL_STATUS,"r_eff":None},
                        "reload_equal": course["reload_equal"]})
        records[-1]["idea_response_profiles"] = profiles
    paired = []
    for seed in sorted({row["seed"] for row in records}):
        pair = {row["condition"]:row for row in records if row["seed"] == seed}
        if set(pair) == set(p.CONDITIONS):
            paired.append({"seed": seed, "cross_view":p.paired_root_effect(
                pair[p.CONDITIONS[0]]["cross_view"], pair[p.CONDITIONS[1]]["cross_view"]),
                "effect_scope":"CONNECTED_PRESENTATION_PACKAGE_RELATIVE_TO_CANONICAL_REVISIT"})
    return {"schema": SCHEMA, "candidate": p.DIRECTIVE, "courses": records,
            "paired_effects": paired, "native_flow_binding_status":p.NATIVE_STATUS,
            "empirical_response_profile_status":p.EMPIRICAL_STATUS,
            "adaptive_policy_status":"SHADOW_ONLY_DISABLED",
            "status":"PERSPECTIVE_MEASURED" if len(records)==6 and parent["status"]=="COMPLEMENTARY_MEASURED"
                      else "TEACHING_INCOMPLETE",
            "claim_boundary":"No unique neural frequency, physical Ohm law, or telemetry-guided controller advantage established."}


def run(config, *, results, artifacts, root=None):
    pilot = Path(root) / "research/CAS_META_2_COMPOSITION" if root else Path(__file__).resolve().parents[1]
    bindings = validate_config(config, pilot)
    from .complementary_teaching import runner as parent
    from .complementary_teaching import IMPLEMENTATION_ID
    inner = deepcopy(config)
    inner["candidate"] = IMPLEMENTATION_ID
    inner["comparison_conditions"] = list(p.CONDITIONS)
    artifacts, results = Path(artifacts), Path(results)
    status = "TEACHING_INCOMPLETE"
    failure = None
    original_error = None
    report_failure = None
    try:
        parent.run(inner, results=results, artifacts=artifacts, root=root,
                   public_transform_factory=transform_factory, panel_transform=p.perspective_panels)
    except Exception as error:
        failure = {"type":type(error).__name__,"message":str(error)}
        original_error = error
    finally:
        artifacts.mkdir(parents=True, exist_ok=True)
        observation_started = time.monotonic()
        saved = artifacts / "complementary_report.json"
        if saved.exists():
            try:
                parent_report = json.loads(saved.read_bytes())
                data = json.loads((pilot / DATA_PATH).read_bytes())
                report = restore_reports(parent_report, p.perspective_panels(data["panels"]), bindings=bindings)
                status = report["status"]
                report["observation_elapsed_seconds"] = time.monotonic() - observation_started
                report["parent_bindings_sha256"] = p.identity(bindings)
                parent.write_json(artifacts / "perspective_report.json", report)
            except Exception as error:
                report_failure = {"type":type(error).__name__,"message":str(error)}
                if original_error is None:
                    original_error = error
                    failure = report_failure
        if failure is not None:
            status = "TEACHING_INCOMPLETE"
        entries = [{"name":path.name,"sha256":file_hash(path),"bytes":path.stat().st_size}
                   for path in sorted(artifacts.iterdir()) if path.is_file() and path.name!="manifest.json"]
        parent.write_json(artifacts / "manifest.json", {"schema":SCHEMA,"artifacts":entries})
        envelope = {"schema":SCHEMA,"job":config["job"],"candidate":p.DIRECTIVE,"status":status,
                    "arms":list(p.CONDITIONS),"artifacts":entries,"failure":failure,
                    "report_failure":report_failure,
                    "native_flow_binding_status":p.NATIVE_STATUS,
                    "empirical_response_profile_status":p.EMPIRICAL_STATUS}
        receipt = parent.write_json(results / "result.json",envelope)
        (results / "result.json.sha256").write_text(receipt["sha256"]+"\n",encoding="utf-8")
    if original_error is not None:
        raise original_error
    return envelope
