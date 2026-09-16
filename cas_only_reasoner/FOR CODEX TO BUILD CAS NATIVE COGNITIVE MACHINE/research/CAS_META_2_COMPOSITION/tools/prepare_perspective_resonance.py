"""Prepare CAS_PERSPECTIVE_RESONANCE_001 without importing a model or provider."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cas_meta2 import perspective_resonance as p


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def prepare(output, *, check_tokenizer=False):
    source = ROOT / "records/perspective_resonance_001/source"
    read = lambda name: json.loads((source / name).read_text(encoding="utf-8"))
    rows = lambda name: [json.loads(line) for line in (source / name).read_text(encoding="utf-8").splitlines() if line]
    bundle = p.compile_family(read("Perspective_Family_Authoring_Example.json"),
                              rows("public_exercises.jsonl"), rows("teacher_targets.jsonl"))
    output.mkdir(parents=True, exist_ok=True)
    write(output / "compiled_golden_family.json", bundle)
    predictions = [{"record_id": target["record_id"], "selected": target["expected_answer"],
                    "provenance": "SIMULATED_CHECKER_ANSWERS_NOT_MODEL_OUTPUT"}
                   for target in bundle["teacher_targets"]]
    seal = p.seal_predictions(predictions)
    write(output / "simulated_sealed_predictions.json", seal)
    report = p.behavioral_report(seal, bundle["teacher_targets"], bundle["comparisons"])
    report["evidence_status"] = "SIMULATED_NOT_OBSERVED_LEARNING"
    write(output / "simulated_report.json", report)
    restored = p.behavioral_report(json.loads((output / "simulated_sealed_predictions.json").read_text()),
                                  bundle["teacher_targets"], bundle["comparisons"])
    restored["evidence_status"] = "SIMULATED_NOT_OBSERVED_LEARNING"
    if restored != report:
        raise ValueError("REPORT_REGENERATION_MISMATCH")
    comparisons = [p.compile_comparison(seed) for seed in (101, 202, 303)]
    bindings = {"schema":p.SCHEMA, "parent_profile":"cas.complementary-teaching/0.1",
        "parent_condition":"ALT_COMPONENT_WHOLE", "source_selection":"PINNED_BEFORE_NEURAL_OUTCOMES",
        "by_seed":[{"seed":c["seed"],"parent_schedule_sha256":c["parent_schedule_sha256"],
                   "conditions":{name:{"schedule_sha256":s["schedule_sha256"],"counts":s["counts"],
                        "coverage":p.view_coverage([t for b in s["batches"] for t in b["tasks"]])}
                        for name,s in c["schedules"].items()}} for c in comparisons]}
    parent_data_path = ROOT / "records/complementary_teaching_001/preparation_20260916/data_manifest.json"
    parent_data = json.loads(parent_data_path.read_bytes())
    bindings["parent_data_file_sha256"] = sha256(parent_data_path.read_bytes()).hexdigest()
    bindings["parent_data_sha256"] = parent_data["data_sha256"]
    audit_panels = p.perspective_panels(parent_data["panels"])
    audit_targets = p.perspective_target_manifest(audit_panels)
    write(output / "perspective_audit_public.json", {name:[
        {key:value for key,value in task.items() if key not in ("correct","encoded_correct_index","reference")}
        for task in tasks] for name,tasks in audit_panels.items()})
    write(output / "perspective_audit_teacher_targets.json", audit_targets)
    bindings["perspective_audit_counts"] = {name:len(tasks) for name,tasks in audit_panels.items()}
    if check_tokenizer:
        from cas_meta2.features_v2 import LosslessPublicTokenizer, BYTE_START, WORD_START
        from cas_meta2.graph_teaching import face_corpus, face_evaluation, face_worker
        built=face_corpus.families()
        corpus=face_worker.public_corpus(built,face_evaluation.panel(built),())
        tokenizer=LosslessPublicTokenizer.fit_train(corpus["publics"],max_length=1024)
        measurements=[]
        for comparison in comparisons:
            for condition,schedule in comparison["schedules"].items():
                lengths, byte_tokens=[],0
                for batch in schedule["batches"]:
                    for task in batch["tasks"]:
                        encoded=tokenizer.encode_public(task["public"])
                        lengths.append(len(encoded["ids"]))
                        byte_tokens+=sum(BYTE_START <= token < WORD_START for token in encoded["ids"])
                measurements.append({"seed":comparison["seed"],"condition":condition,
                    "presentations":len(lengths),"total_tokens":sum(lengths),"maximum_tokens":max(lengths),
                    "byte_fallback_tokens":byte_tokens})
        bindings["tokenizer"]={"identity":tokenizer.digest,"unchanged_original_fit":True,
                               "max_length":1024,"measurements":measurements}
        audit_lengths = [len(tokenizer.encode_public(task["public"])["ids"])
                         for tasks in audit_panels.values() for task in tasks]
        bindings["tokenizer"]["audit"] = {"presentations":len(audit_lengths),
            "total_tokens":sum(audit_lengths),"maximum_tokens":max(audit_lengths)}
    write(output / "parent_bindings.json", bindings)
    counts=comparisons[0]["counts_per_learner"]
    initial_retention = len(parent_data["panels"]["final_components"]) + len(parent_data["panels"]["final_earlier_skills"])
    development = 17 * sum(len(rows) for name,rows in parent_data["panels"].items() if name.startswith("development_"))
    final_once = sum(len(rows) for name,rows in parent_data["panels"].items() if name.startswith("final_")) + sum(len(rows) for rows in audit_panels.values())
    audit_answers = initial_retention + development + 2 * final_once
    from aws.complementary_teaching_launch import costed_request as parent_costed_request
    parent_cost = parent_costed_request()["per_course"]
    p.require(parent_cost["monitor_answers"] == development and
              parent_cost["initial_retention_answers"] == initial_retention,
              "PERSPECTIVE_PARENT_AUDIT_COST_DRIFT")
    numerical_answers = parent_cost["numerical_gradient_answers"]
    isolation_answers = parent_cost["state_isolation_answers"]
    audit_passes = 8 * (audit_answers + numerical_answers + isolation_answers)
    request={"schema":"cas.perspective-resonance-unsigned-request/0.1",
        "candidate":p.DIRECTIVE, "signature":None, "execution_enabled":False,
        "prior_reservation_reused":False, "worker_entrypoint":"cas_meta2.perspective_worker.run",
        "parent_profile":"cas.complementary-teaching/0.1", "parent_condition":"ALT_COMPONENT_WHOLE",
        "parent_bindings_sha256":p.identity(bindings), "seeds":[101,202,303],
        "parent_data_sha256":parent_data["data_sha256"],
        "conditions":list(p.CONDITIONS), "learners":6,
        "training":{"rounds_per_learner":16,"decisions_per_learner":counts["decisions"],
            "updates_per_learner":counts["optimizer_updates"],
            "decisions_total":6*counts["decisions"], "updates_total":6*counts["optimizer_updates"],
            "sample_core_passes_total":6*counts["sample_core_passes_planned"],
            "extra_teaching_slots":0,"continuing_optimizer":True,"fresh_question_state":True},
        "observation":{"behavioral_rows":"RETAIN_ACTUAL_PREDICTIONS_BEFORE_TARGET_JOIN",
            "native_flow":p.NATIVE_STATUS,"calibrated_response":p.EMPIRICAL_STATUS,
            "calibration_forwards":0,"adaptive_policy_enabled":False,
            "full_tensor_capture":False, "observation_overhead":"MEASURE_ELAPSED_LOGGING_TIME_IN_WORKER"},
        "audit_allocation_per_learner":{"initial_retention":initial_retention,"development":development,
            "final_and_reload":2*final_once,"numerical_check_forwards":numerical_answers,
            "state_isolation_forwards":isolation_answers,
            "inference_depth":8,"audit_decisions_total":audit_answers,
            "audit_and_check_sample_passes":audit_passes},
        "total_training_audit_and_check_sample_passes":6*(audit_passes+counts["sample_core_passes_planned"]),
        "resource_allowance":{"provider":"AWS","region":"us-west-2","instance_type":"g7.2xlarge",
            "instance_count":1,"on_demand_rate_ceiling_usd":"2.52","instance_seconds_max":7200,
            "worker_seconds_max":3600,"experiment_seconds_max":3000,
            "setup_collection_allowance_seconds":600,"maximum_instance_compute_usd":"5.04",
            "ancillary_allowance_usd":"1.96","total_cap_usd":"7.00",
            "automatic_retries":0,"local_neural_fallback":False},
        "required_execution_gates":["exact source/package identities", "parent fresh-root exclusions verified",
            "pure and authorized GPU numerical checks", "new budget reservation through shared ledger",
            "signed exact job/source authority and cost cap"],
        "required_source_package_files":[
            "research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/neural.py",
            "research/CAS_META_2_COMPOSITION/records/perspective_resonance_001/prepared/**",
            "research/CAS_META_2_COMPOSITION/records/complementary_teaching_001/preparation_20260916/**",
            "parent INITIAL_PATH checkpoint and frozen dependency wheels"],
        "result_status":"PERSPECTIVE_RESONANCE_READY_NEURAL_UNTESTED",
        "native_flow_binding_status":p.NATIVE_STATUS,
        "empirical_response_profile_status":p.EMPIRICAL_STATUS,
        "adaptive_policy_status":"SHADOW_ONLY_DISABLED"}
    write(output / "unsigned_costed_request.json",request)
    manifest=[]
    for path in sorted(source.iterdir()):
        if path.is_file():
            manifest.append({"path":path.relative_to(ROOT).as_posix(),"bytes":path.stat().st_size,
                             "sha256":sha256(path.read_bytes()).hexdigest(),"role":"READ_ONLY_USER_SOURCE_COPY"})
    implementation=[ROOT/"cas_meta2/perspective_resonance.py",Path(__file__),
                    ROOT/"cas_meta2/perspective_worker.py",parent_data_path,
                    ROOT/"aws/perspective_resonance_launch.py",
                    ROOT/"cas_meta2/complementary_teaching/course.py",
                    ROOT/"cas_meta2/complementary_teaching/runner.py",
                    ROOT/"cas_meta2/recurrent_cjt/learner.py",
                    ROOT/"cas_meta2/graph_teaching/real_framework.py"]
    for path in implementation:
        manifest.append({"path":path.relative_to(ROOT).as_posix(),"bytes":path.stat().st_size,
                         "sha256":sha256(path.read_bytes()).hexdigest(),"role":"EXACT_LOCAL_SOURCE_BINDING"})
    producer_path = ROOT.parent / "CAS_CJT_TRANSFORMER_v0_2/cas_cjt/neural.py"
    producer_sha = sha256(producer_path.read_bytes()).hexdigest()
    if producer_sha != p.NATIVE_PRODUCER_SHA256:
        raise ValueError("PERSPECTIVE_SELECTED_PRODUCER_CHANGED")
    manifest.append({"path":"research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/neural.py",
        "anchor":"homebase","bytes":producer_path.stat().st_size,"sha256":producer_sha,
        "role":"PINNED_PRODUCER_WITH_NO_NATIVE_ROUTING_TAP"})
    write(output / "source_manifest.json", {"files":manifest,"aggregate_sha256":p.identity(manifest)})
    from cas_meta2.complementary_teaching.runner import INITIAL_PATH
    worker_config = {"candidate":p.DIRECTIVE,"execution_enabled":False,
        "training":True,"optimizer_updates":960,
        "job":None,"learning_rate":0.003,"max_wall_seconds":3000,
        "comparison_conditions":list(p.CONDITIONS),"empirical_response_enabled":False,
        "adaptive_policy_enabled":False,"data_sha256":parent_data["data_sha256"],
        "data_file_sha256":bindings["parent_data_file_sha256"],
        "initial_checkpoint_sha256":sha256((ROOT / INITIAL_PATH).read_bytes()).hexdigest(),
        "perspective_bindings_file_sha256":sha256((output / "parent_bindings.json").read_bytes()).hexdigest(),
        "perspective_sources_file_sha256":sha256((output / "source_manifest.json").read_bytes()).hexdigest()}
    write(output / "unsigned_worker_config.json", worker_config)
    request["worker_config_file_sha256"] = sha256((output / "unsigned_worker_config.json").read_bytes()).hexdigest()
    request["source_manifest_file_sha256"] = worker_config["perspective_sources_file_sha256"]
    write(output / "unsigned_costed_request.json", request)
    receipt={"status":"PURE_PREPARATION_COMPLETE","neural_executions":0,"provider_calls":0,
             "golden_rows":12,"report_regeneration":"IDENTICAL",
             "tokenizer_checked":check_tokenizer,"comparisons":3,
             "source_aggregate_sha256":p.identity(manifest)}
    write(output / "preparation_receipt.json",receipt)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"records/perspective_resonance_001/prepared")
    parser.add_argument("--check-tokenizer",action="store_true")
    args=parser.parse_args()
    print(json.dumps(prepare(args.output,check_tokenizer=args.check_tokenizer),sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
