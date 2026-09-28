"""Admitted AWS parity witness; no training, grading changes or interventions.

Uses two model-visible public course inputs (one Parts, one Reach), chosen by
lexicographic record ID before any prediction. This is an engineering replay,
not independent confirmation or a test of task accuracy. No gold is loaded.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

from .observation import capture_helm, canonical, sha, retain_observation, reload_observation, reload_configuration_inputs
from .admission import write_new, file_hash


def venue():
    if sys.platform != "linux" or os.environ.get("HELM_HH_RDE_VENUE") != "ADMITTED_AWS":
        raise ValueError("DIAGNOSTIC_ADMITTED_AWS_REQUIRED")


def witness(root, parent, out):
    venue()
    from research.helm_continuation import worker as existing, continuation as c
    out.mkdir(parents=True, exist_ok=False)
    report = {"schema":"helm.hh-rde.parity/1", "status":"FAILED", "cases":[],
              "optimizer_updates":0, "packet_forwards":0, "causal_interventions":0,
              "task_accuracy":"NOT_SCORED_NO_GOLD", "fixture_kind":"PUBLIC_COURSE_ENGINEERING_REPLAY",
              "source":c.SOURCE, "parent_sha256":c.PARENT_SHA,
              "numeric_tolerance":"EXACT_EQUALITY_NO_TOLERANCE", "automatic_retry":False}
    start = time.monotonic()
    try:
        # Existing guarded source/driver/dependency path, without CONT19.run or training.
        w,torch,device,frozen,tokenizer,_,attestor,runtime = existing.environment(root)
        legacy = w.pointer_module
        legacy.pointer_inputs.label_cache(root)
        packets = dict(w.contract.public_packets(frozen))
        selected = []
        for kind in ("parts", "reach"):
            key = sorted(k for k,p in packets.items() if p["record"]["query"]["kind"] == kind)[0]
            selected.append((kind, key, packets[key]))
        write_new(out / "INPUT_SELECTION.json", {
            "policy":"FIRST_LEXICOGRAPHIC_PUBLIC_RECORD_PER_PARTS_REACH_BEFORE_PREDICTION",
            "cases":[{"kind":k,"record_id":i,"packet_sha256":sha(canonical(p))} for k,i,p in selected],
            "confirmation":False, "target_visibility":"NONE"})
        def restore():
            encoder = w.encoder_module.build_frozen_typed_encoder(torch, tokenizer,
                seed=w.contract.DESIGN["encoder_seed"], d_model=64, device=device)
            framework = w.matched._framework(torch, device, 20260919)
            model,metadata = c.restore_parent(legacy,torch,framework,encoder,parent,device)
            return model
        # Compile/warm only deterministic public input/slot caches before the comparison.
        from cas_meta2.typed_teaching import slots
        for _,_,packet in selected:
            slots.compile_slots(packet);legacy.pointer_inputs.read_packet(packet)
        cache_before = sha(canonical(legacy.pointer_inputs._CACHE_STATE))
        for kind,record_id,packet in selected:
            rows=[]
            for mode in ("OFF","OBSERVE_ONLY","NO_OP_CONTROL"):
                model=restore(); before=c.state_snapshot(model,legacy)
                keys=set(model.__dict__)
                slots.compile_slots(packet)  # Warm this exact public entry before timed inference.
                slot_before=slots.slot_cache_info()
                began=time.perf_counter_ns()
                with capture_helm(model,packet,checkpoint_path=parent,
                    expected_checkpoint_sha256=c.PARENT_SHA,kind=kind,mode=mode,max_bytes=4*1024*1024) as cap:
                    prediction=model.predict(packet,8)
                elapsed=time.perf_counter_ns()-began
                report["packet_forwards"]+=1
                after=c.state_snapshot(model,legacy)
                slot_after=slots.slot_cache_info()
                slot_delta={k:slot_after[k]-slot_before[k] for k in slot_before}
                for field in ("model","optimizer","encoder","rng","cursor","model_revision"):
                    c.require(before[field] == after[field], "PASSIVE_STATE_CHANGED:"+field)
                c.require(set(model.__dict__)==keys and "_graph" not in model.__dict__,"OBSERVER_NOT_REMOVED")
                receipt=cap.receipt()
                if mode != "OFF":c.require(receipt["complete"],"CAPTURE_INCOMPLETE:"+str(receipt["errors"]))
                write_new(out/(kind+"_"+mode+"_capture.json"),receipt)
                write_new(out/(kind+"_"+mode+"_prediction.json"),prediction)
                rows.append({"mode":mode,"before":before,"after":after,
                    "prediction_sha256":sha(canonical(prediction)),"elapsed_ns":elapsed,
                    "capture_overhead_ns":receipt["capture_overhead_ns"],"slot_cache_delta":slot_delta,
                    "complete":receipt["complete"],"receipt_sha256":receipt["receipt_sha256"]})
            c.require(all(r["before"]==rows[0]["before"] and r["after"]==rows[0]["after"]
                          and r["prediction_sha256"]==rows[0]["prediction_sha256"]
                          and r["slot_cache_delta"]==rows[0]["slot_cache_delta"] for r in rows),
                      "BASELINE_OBSERVE_NOOP_PARITY_FAILED")
            report["cases"].append({"kind":kind,"record_id":record_id,"trials":rows,
                                    "exact_prediction_scores_and_state_equal":True})
        c.require(cache_before==sha(canonical(legacy.pointer_inputs._CACHE_STATE)),"INPUT_CACHE_MUTATED")
        # Verify exception cleanup without a model forward or an optimizer step.
        model=restore(); kind,_,packet=selected[0];before=c.state_snapshot(model,legacy)
        try:
            with capture_helm(model,packet,checkpoint_path=parent,expected_checkpoint_sha256=c.PARENT_SHA,
                              kind=kind,mode="OBSERVE_ONLY"):
                raise RuntimeError("INJECTED_CALLER_FAILURE")
        except RuntimeError as error:
            c.require(str(error)=="INJECTED_CALLER_FAILURE","UNEXPECTED_CLEANUP_ERROR")
        c.require("_graph" not in model.__dict__ and "stage_batch" not in model.__dict__
                  and before==c.state_snapshot(model,legacy),"INTERRUPTION_CLEANUP_STATE")
        c.require(file_hash(parent)==c.PARENT_SHA,"PARENT_CHANGED")
        report.update(status="PASS_REAL_PARENT_PASSIVE_PARITY",runtime=runtime,
                      input_cache_unchanged=True,exception_cleanup=True,loaded_sources=attestor.snapshot())
    except BaseException as error:
        report.update(error_type=type(error).__name__,error=str(error))
    finally:
        report["elapsed_seconds"]=time.monotonic()-start
        write_new(out/"public_result.json",report)
    return 0 if report["status"]=="PASS_REAL_PARENT_PASSIVE_PARITY" else 1


def retain(directory, out):
    venue()
    # A separate process avoids mixing the two pinned cncm export namespaces.
    from .conftest import host_for
    from .native_bridge import run_baseline
    host=host_for(out,baseline=True)
    native,_=run_baseline(host)
    anchors=[]
    for path in sorted(directory.glob("*_OBSERVE_ONLY_capture.json")):
        anchors.append(retain_observation(host,json.loads(path.read_bytes()),native_run_id=native["run_id"]))
    if len(anchors)!=2:raise ValueError("TWO_REAL_CAPTURE_RECEIPTS_REQUIRED")
    result={"status":"PASSIVE_CAPTURE_RETAINED_RESEARCH_ONLY","anchors":anchors,
            "native_run_id":native["run_id"],"neural_effect_verified_by_native_run":False,
            "full_neural_repair_episode":"NOT_IMPLEMENTED_BY_THIS_PASSIVE_WITNESS"}
    write_new(out/"retained.json",result)
    return 0


def reload(directory, policy_sha256, retained_sha256):
    venue()
    from .admission import TrustedHost
    if file_hash(directory/"retained.json") != retained_sha256:raise ValueError("RETAINED_EXTERNAL_ANCHOR")
    host=TrustedHost(directory/"admission.json",policy_sha256,directory/"host-evidence")
    retained=json.loads((directory/"retained.json").read_bytes())
    rows=[reload_observation(host,r["ledger_event_digest"]) for r in retained["anchors"]]
    readouts=[reload_configuration_inputs(host,r["ledger_event_digest"]) for r in retained["anchors"]]
    if (len(rows) != 2 or not all(r["observation"]["complete"] for r in rows)
            or not all(r["complete"] for r in readouts)):
        raise ValueError("FRESH_RELOAD_INCOMPLETE_CAPTURE")
    write_new(directory/"fresh_reload.json",{"status":"PASS_FRESH_PROCESS_OBSERVATION_RELOAD",
        "captures":len(rows),"complete":all(r["observation"]["complete"] for r in rows),
        "rpa_projections":[r["rpa_projection"] for r in rows],"promotion":False,
        "configuration_readouts":[{"receipt_sha256":r["receipt_sha256"],"status":r["status"],
            "conversion_digest":r["conversion_digest"],
            "complete":r["complete"],"coverage":r["coverage"],
            "series_counts":{s:len(c) for s,c in r["capture_series"].items()},
            "named_configurations":r["named_configurations"]} for r in readouts]})
    return 0


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest="command",required=True)
    w=sub.add_parser("witness");w.add_argument("--root",type=Path,required=True)
    w.add_argument("--parent",type=Path,required=True);w.add_argument("--out",type=Path,required=True)
    r=sub.add_parser("retain");r.add_argument("--directory",type=Path,required=True);r.add_argument("--out",type=Path,required=True)
    r=sub.add_parser("reload");r.add_argument("--directory",type=Path,required=True)
    r.add_argument("--policy-sha256",required=True);r.add_argument("--retained-sha256",required=True)
    a=p.parse_args()
    raise SystemExit(witness(a.root,a.parent,a.out) if a.command=="witness" else
                     retain(a.directory,a.out) if a.command=="retain" else reload(a.directory,a.policy_sha256,a.retained_sha256))
