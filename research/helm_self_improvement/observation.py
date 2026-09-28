"""HELM-specific adapter for the existing Harness capture and host evidence.

OFF is the default. Observation is never a control/promotion authority. The
Pythia-specific hook dispatcher is replaced by pinned, instance-local HELM
sites, while CaptureState and its signed top-K display reducer are reused.
The complete bounded signed arrays, not that display, are the capture record.
"""
from contextlib import contextmanager
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import re
import time
import types

from .harness_capture_vendor.probe_runner import CaptureState, _top_k_neurons
from .observation_sites import instrumented_graph, LEARNER_SHA256, SCIENTIFIC_SOURCE
from .admission import TrustedHost, contained, write_new, file_hash
from .contracts import digest
from .harness_capture_vendor.research_exports import local_evidence_functions, definition_lock

MODES = ("OFF", "OBSERVE_ONLY", "NO_OP_CONTROL")
MEANINGS = {
    "input.mapping": "Actual public pointer_inputs.read_packet mapping; ranked nodes, query and adjacency, not labels/answers.",
    "graph.initial_state": "RMS-normalized node_encode output; rows in reading world/node-rank order, columns learned state coordinates.",
    "graph.round_input": "Actual _rounds observe seam: encoded blend of normalized self/parent/child states entering core_block; projected coordinates, not individual hidden MLP neurons.",
    "graph.round_update": "Actual core_block output before capped residual addition; learned state coordinates.",
    "graph.round_state": "Actual normalized node state after the round residual update; same-checkpoint basis only.",
    "graph.node_state": "Final node states, world order then node rank; width64 learned state coordinates.",
    "graph.query_state": "Encoded query plus named node states; width64 learned state coordinates.",
    "graph.pointer_query": "Pointer key projected from query; width64 dot-product coordinates.",
    "head.node": "node_head logits: row per node and two declared yes/no output categories; not neurons.",
    "head.reach": "reach_option_head logits in ABSENT,DIRECT order.",
    "head.node_pointer": "Dot product of candidate node states and pointer_query, in requested rank order.",
    "answer.scores": "Original slot scores in original declared symbol order; no rescoring.",
    "answer.decisions": "Original slots.score_decisions output.",
    "answer.assembly": "Original slots.assemble_answer output; model prediction, not evaluator acceptance.",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


class Capture:
    def __init__(self, *, checkpoint_sha256, input_sha256, kind, rounds,
                 mode="OFF", max_bytes=8*1024*1024, max_seconds=60):
        if mode not in MODES or kind not in ("parts", "reach"):
            raise ValueError("UNSUPPORTED_CAPTURE_MODE_OR_KIND")
        if not all(type(x) is str and re.fullmatch("[0-9a-f]{64}", x)
                   for x in (checkpoint_sha256, input_sha256)):
            raise ValueError("CAPTURE_IDENTITY_REQUIRED")
        if (type(max_bytes) is not int or not 1 <= max_bytes <= 512*1024*1024
                or type(rounds) is not int or not 1 <= rounds <= 64
                or type(max_seconds) not in (float, int) or not 0 < max_seconds <= 3600):
            raise ValueError("CAPTURE_LIMITS")
        self.identity = {"checkpoint_sha256":checkpoint_sha256, "input_sha256":input_sha256,
                         "source_sha256":LEARNER_SHA256, "scientific_source":SCIENTIFIC_SOURCE}
        self.mode, self.kind, self.rounds = mode, kind, rounds
        self.max_bytes, self.max_seconds = max_bytes, max_seconds
        self.expected = {site:(rounds if site.startswith("graph.round_") else 1) for site in MEANINGS}
        if kind == "parts":
            self.expected.update({"head.reach":0, "head.node_pointer":0})
        self.observed, self.stored = Counter(), Counter()
        self.events, self.errors = [], []
        self.bytes = self.overhead_ns = 0
        self.started = time.monotonic()
        self.closed = self.cleanup_complete = False
        self.binding = None

    def error(self, code):
        # Errors are bounded independently of capture size; no exception bodies.
        if len(self.errors) < 32 and code not in self.errors:
            self.errors.append(code)

    def emit(self, site, value, round_index=None):
        """Always return the original object; capture exceptions never fake coverage."""
        if self.mode == "OFF":
            return value
        began = time.perf_counter_ns()
        try:
            if self.closed:
                raise ValueError("CAPTURE_CLOSED")
            if site not in self.expected:
                raise ValueError("UNKNOWN_SITE")
            self.observed[site] += 1
            call = self.observed[site] - 1
            if self.observed[site] > self.expected[site]:
                raise ValueError("EXTRA_SITE_CALL")
            if time.monotonic() - self.started > self.max_seconds:
                raise ValueError("CAPTURE_TIME_LIMIT")
            if round_index != (call if site.startswith("graph.round_") else None):
                raise ValueError("WRONG_ROUND")
            row = {**self.identity, "site":site, "call_index":call,
                   "round_index":round_index, "coordinate_meaning":MEANINGS[site],
                   "basis":"WITHIN_CHECKPOINT_ONLY", "cas_label":"UNKNOWN_NOT_FITTED"}
            if hasattr(value, "detach"):
                shape = list(value.shape)
                if site.startswith("graph.") and (not shape or shape[-1] != 64):
                    raise ValueError("WRONG_SHAPE")
                if site == "head.node" and (len(shape) != 2 or shape[1] != 2):
                    raise ValueError("WRONG_SHAPE")
                if site == "head.reach" and shape != [2]:
                    raise ValueError("WRONG_SHAPE")
                if site == "head.node_pointer" and len(shape) != 1:
                    raise ValueError("WRONG_SHAPE")
                # Charge a conservative conversion bound before allocating lists.
                if int(value.numel()) * 32 + 4096 > self.max_bytes - self.bytes:
                    raise ValueError("CAPTURE_BYTE_LIMIT")
                flat = value.detach().reshape(-1).cpu().tolist()
                if not all(math.isfinite(x) for x in flat):
                    raise ValueError("NONFINITE_CAPTURE")
                state = CaptureState(mlp_post={0:flat})
                # Legacy name is internal only; external label states coordinate semantics.
                preview = [{"flat_coordinate":r["index"], "signed_value":r["activation"]}
                           for r in _top_k_neurons(state, 8)]
                row.update({"shape":shape, "dtype":str(value.dtype), "device":str(value.device),
                            "signed_values":state.mlp_post[0], "coordinate_preview":preview,
                            "preview_is_causal_dataset":False})
            else:
                if site == "input.mapping" and value["query"]["kind_name"] != self.kind:
                    raise ValueError("WRONG_INPUT_KIND")
                # Public input/prediction only; independent evaluator data is never accepted here.
                row.update({"public_value":json.loads(canonical(value)), "shape":None,
                            "dtype":None, "device":None})
            raw = canonical(row)
            if self.bytes + len(raw) > self.max_bytes:
                raise ValueError("CAPTURE_BYTE_LIMIT")
            self.events.append(row)
            self.stored[site] += 1
            self.bytes += len(raw)
        except Exception as error:
            code = str(error) if type(error) is ValueError else type(error).__name__
            self.error(site + ":" + code[:80])
        finally:
            self.overhead_ns += time.perf_counter_ns() - began
        return value

    def receipt(self):
        coverage = {s:{"expected_calls":n, "observed_calls":self.observed[s],
                       "stored_calls":self.stored[s]} for s,n in self.expected.items()}
        complete = (self.mode != "OFF" and self.closed and self.cleanup_complete and not self.errors
                    and all(v["expected_calls"] == v["observed_calls"] == v["stored_calls"]
                            for v in coverage.values()))
        body = {"schema":"helm.harness.observation/1", **self.identity, "mode":self.mode,
                "kind":self.kind, "coverage":coverage, "complete":complete,
                "status":"DISABLED" if self.mode == "OFF" else ("CAPTURED" if complete else "INCOMPLETE"),
                "errors":list(self.errors), "events":self.events,
                "captured_json_bytes":self.bytes, "max_capture_bytes":self.max_bytes,
                "capture_overhead_ns":self.overhead_ns, "cleanup_complete":self.cleanup_complete,
                "binding":self.binding, "claim":"OBSERVATION_ONLY_CAUSALITY_UNMEASURED",
                "authority":"NO_PROMOTION_NO_EXECUTION", "harvest_enabled":False}
        return {**body, "receipt_sha256":sha(canonical(body))}


@contextmanager
def capture_helm(learner, packet, *, checkpoint_path, expected_checkpoint_sha256,
                 kind, mode="OFF", max_bytes=8*1024*1024, max_seconds=60):
    """One inference on an already guarded-restored learner; no global hooks.

Caller admission must bind this restored learner's state to the checkpoint.
This interface verifies the copy's bytes and the original source. A matching
file hash alone is not reported as proof of restored weights/optimizer.
"""
    if "_graph" in learner.__dict__ or "stage_batch" in learner.__dict__:
        raise ValueError("INCUMBENT_OR_NESTED_OBSERVER")
    path = Path(checkpoint_path)
    if path.is_symlink() or not path.is_file() or file_hash(path) != expected_checkpoint_sha256:
        raise ValueError("WRONG_CHECKPOINT_BYTES")
    input_sha = sha(canonical(packet))
    # Determine the actual registered round count from the authenticated source.
    original = type(learner)._graph
    if sha(Path(original.__code__.co_filename).read_bytes()) != LEARNER_SHA256:
        raise ValueError("UNSUPPORTED_LEARNER_SOURCE")
    cap = Capture(checkpoint_sha256=expected_checkpoint_sha256, input_sha256=input_sha,
                  kind=kind, rounds=original.__globals__["CORE_ROUNDS"], mode=mode,
                  max_bytes=max_bytes, max_seconds=max_seconds)
    if mode == "OFF":
        try:
            yield cap
        finally:
            cap.closed = cap.cleanup_complete = True
        return
    graph, rounds, cap.binding = instrumented_graph(learner, cap.emit)
    calls = 0
    def bound_graph(self, actual_packet):
        nonlocal calls
        if sha(canonical(actual_packet)) != input_sha:
            raise ValueError("UNADMITTED_INPUT")
        if calls:
            raise ValueError("ONE_PACKET_FORWARD_ONLY")
        calls += 1
        return graph(self, actual_packet)
    def no_training(*args, **kwargs):
        raise ValueError("DIAGNOSTIC_OPTIMIZER_UPDATES_FORBIDDEN")
    learner._graph = types.MethodType(bound_graph, learner)
    learner.stage_batch = no_training
    try:
        yield cap
    except BaseException:
        cap.error("LEARNER_OR_CALLER_FAILED")
        raise
    finally:
        del learner._graph
        del learner.stage_batch
        cap.closed = cap.cleanup_complete = True


def retain_observation(host, receipt, *, native_run_id):
    """Anchor one diagnostic sidecar in the incumbent host's evidence ledger.

The native run remains a separate engineering episode. The link is provenance,
not a claim that the native checker has verified this neural answer.
"""
    if type(host) is not TrustedHost:
        raise ValueError("EXISTING_HOST_REQUIRED")
    native = host.verified_run(native_run_id)
    body = {k:v for k,v in receipt.items() if k != "receipt_sha256"}
    if sha(canonical(body)) != receipt["receipt_sha256"]:
        raise ValueError("CAPTURE_INTEGRITY")
    name = "capture-" + receipt["receipt_sha256"] + ".json"
    destination = contained(host.evidence_root / "runs" / native_run_id, name)
    write_new(destination, receipt)
    store = host.evidence_root / "harness"
    writer = local_evidence_functions(store)
    trace_id = "helmcap-" + receipt["receipt_sha256"]
    packet = {"schema_version":"evidence_packet.v1", "trace_id":trace_id,
              "provenance":{**receipt["binding"]} if receipt["binding"] else {},
              "observation_receipt_sha256":receipt["receipt_sha256"],
              "model_checkpoint_sha256":receipt["checkpoint_sha256"],
              "coverage":receipt["coverage"], "complete":receipt["complete"],
              "tks_definition_lock":asdict(definition_lock()),
              "cas_probe_transfer":"NOT_VALIDATED_NO_PROBE_COEFFICIENTS_IMPORTED",
              "verification":{"proof_chips":[{"id":key,"status":status,"detail":detail}
                  for key,status,detail in [
                      ("model_proof","present","Checkpoint identity only; guarded restoration is a separate witness."),
                      ("cas_readout","unavailable","No HELM-calibrated CAS readout."),
                      ("causal_proof","unavailable","No active intervention in passive capture."),
                      ("control_proof","unavailable","Neutrality is a separately collected comparison."),
                      ("output_proof","present" if receipt["complete"] else "failed","Capture coverage only; no task correctness claim."),
                      ("packet_proof","present","Research local hash chain; no WORM or production acceptance.")]]},
              "promotion":False, "harvest_enabled":False}
    packet_hash = writer.evidence_packet_without_hashes_sha256(packet)
    entry = writer.append_evidence_packet_hash_log_entry(trace_id=trace_id,audit_id="CAS-HH-RDE-01",
        packet_without_hashes_sha256=packet_hash,operation="retain_helm_research_observation")
    packet["hashes"]={"packet_without_hashes_sha256":packet_hash,"hash_log_entry_sha256":entry["entry_sha256"]}
    packet_path = writer._packet_path(trace_id)
    if packet_path.exists():raise ValueError("DUPLICATE_CAPTURE_PACKET")
    writer.write_evidence_packet_to_store(trace_id,packet)
    event = host.append("HARNESS_OBSERVATION_RETAINED", {
        "native_run_id":native_run_id, "native_trace_sha256":native["trace_sha256"],
        "path":str(destination.relative_to(host.evidence_root)), "sha256":file_hash(destination),
        "receipt_sha256":receipt["receipt_sha256"], "complete":receipt["complete"],
        "disposition":"RESEARCH_ONLY" if receipt["complete"] else "INCOMPLETE_RETAINED",
        "neural_effect_verified_by_native_run":False, "promotion":False,
        "harness_trace_id":trace_id,"harness_packet_sha256":file_hash(packet_path),
        "harness_entry_sha256":entry["entry_sha256"]})
    return {"ledger_event_digest":event["digest"], **event["body"]}


def reload_observation(host, expected_event_digest):
    if type(host) is not TrustedHost:
        raise ValueError("EXISTING_HOST_REQUIRED")
    matches = [e for e in host.events() if e["digest"] == expected_event_digest
               and e["kind"] == "HARNESS_OBSERVATION_RETAINED"]
    if len(matches) != 1:
        raise ValueError("EXTERNAL_OBSERVATION_ANCHOR_REQUIRED")
    row = matches[0]["body"]
    native = host.verified_run(row["native_run_id"])
    path = contained(host.evidence_root, row["path"])
    if file_hash(path) != row["sha256"] or native["trace_sha256"] != row["native_trace_sha256"]:
        raise ValueError("CAPTURE_RELOAD_INTEGRITY")
    receipt = json.loads(path.read_bytes())
    if sha(canonical({k:v for k,v in receipt.items() if k != "receipt_sha256"})) != row["receipt_sha256"]:
        raise ValueError("CAPTURE_RELOAD_INTEGRITY")
    writer = local_evidence_functions(host.evidence_root / "harness")
    packet = writer.load_evidence_packet_from_store(row["harness_trace_id"])
    entry,valid_chain = writer._load_hash_log_entry(row["harness_trace_id"],row["harness_entry_sha256"])
    if (not valid_chain or file_hash(writer._packet_path(row["harness_trace_id"])) != row["harness_packet_sha256"]
            or writer.evidence_packet_without_hashes_sha256(packet) != entry["packet_without_hashes_sha256"]):
        raise ValueError("HARNESS_EVIDENCE_INTEGRITY")
    # RPA can display this sidecar alongside the native atlas. It cannot execute it.
    return {"status":"OBSERVATION_RELOADED", "native_run_id":row["native_run_id"],
            "observation":receipt, "rpa_projection":{"readonly":True,
                "native_trace_sha256":row["native_trace_sha256"],
                "capture_receipt_sha256":row["receipt_sha256"], "execute_action":None},
            "promotion":False}


def reload_configuration_inputs(host, expected_event_digest):
    """Convert an externally anchored capture through Claude's existing reader.

    This is a readout boundary, not a second custody or promotion authority.
    Partial observations remain partial; no detector is fitted or named here.
    """
    from .diagnostic_configuration import (
        TENSOR_SITES, captures_from_observation, convert_observation, expected_hits_for, verify_observation,
    )
    loaded = reload_observation(host, expected_event_digest)
    receipt = loaded["observation"]
    anchor = loaded["rpa_projection"]["capture_receipt_sha256"]
    body = verify_observation(receipt, retained_receipt_sha256=anchor)
    if body.get("scientific_source") != SCIENTIFIC_SOURCE:
        raise ValueError("CONFIGURATION_SCIENTIFIC_SOURCE")
    identity = {key:body[key] for key in
                ("checkpoint_sha256", "input_sha256", "source_sha256", "scientific_source")}
    if not all(type(identity[key]) is str and re.fullmatch("[0-9a-f]{64}", identity[key])
               for key in ("checkpoint_sha256", "input_sha256")):
        raise ValueError("CONFIGURATION_IDENTITY")
    events = body["events"]
    if any(e.get("site") not in MEANINGS or any(e.get(k) != v for k,v in identity.items())
           for e in events):
        raise ValueError("CONFIGURATION_EVENT_IDENTITY")
    counts = Counter(e["site"] for e in events)
    for site, row in body["coverage"].items():
        if (any(type(row.get(k)) is not int or row[k] < 0 for k in
                ("expected_calls", "observed_calls", "stored_calls"))
                or row["expected_calls"] != expected_hits_for(site, body["kind"])
                or not row["stored_calls"] <= row["observed_calls"] <= row["expected_calls"]
                or row["stored_calls"] != counts[site]):
            raise ValueError("CONFIGURATION_COVERAGE")
        site_events = [e for e in events if e["site"] == site]
        if (any(type(e["call_index"]) is not int for e in site_events)
                or [e["call_index"] for e in site_events] != list(range(len(site_events)))
                or any(e["round_index"] != (e["call_index"] if site.startswith("graph.round_") else None)
                       for e in site_events)):
            raise ValueError("CONFIGURATION_CALL_ORDER")
    complete = (body["mode"] != "OFF" and body["cleanup_complete"] is True and not body["errors"]
                and all(r["expected_calls"] == r["observed_calls"] == r["stored_calls"]
                        for r in body["coverage"].values()))
    if body["complete"] is not complete:
        raise ValueError("CONFIGURATION_FALSE_COVERAGE_CLAIM")
    series, coverage, converted = {}, {}, None
    if complete:
        converted = convert_observation(receipt, retained_receipt_sha256=anchor)
        series = {s:converted["sites"][s]["captures"] for s in TENSOR_SITES}
        coverage = {s:converted["sites"][s]["coverage"] for s in TENSOR_SITES}
    else:
        for site in TENSOR_SITES:
            series[site], cov = captures_from_observation(receipt, site, retained_receipt_sha256=anchor)
            coverage[site] = asdict(cov)
    return {"schema":"helm.harness.anchored-configuration-inputs/1",
            "status":"CAPTURE_INPUTS_READY" if body["complete"] else "INCOMPLETE_CAPTURE_INPUTS",
            "complete":body["complete"], "capture_series":series, "coverage":coverage,
            "native_run_id":loaded["native_run_id"], "receipt_sha256":anchor,
            "conversion_digest":converted["conversion_digest"] if converted else None,
            "rpa_projection":loaded["rpa_projection"], "named_configurations":[],
            "claim":"READOUT_ONLY_NO_HELM_CAS_CALIBRATION", "promotion":False}
