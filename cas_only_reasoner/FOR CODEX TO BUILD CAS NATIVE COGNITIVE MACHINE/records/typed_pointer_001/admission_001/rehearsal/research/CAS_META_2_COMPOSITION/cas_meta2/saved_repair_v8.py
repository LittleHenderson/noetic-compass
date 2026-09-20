"""Two-call repair of one hash-pinned saved state. Importing this file is pure.

Only the admitted AWS wrapper may call run(). Tests use fake operations; they
must not open the saved database or import the native or neural packages.
"""
from __future__ import annotations

from copy import deepcopy
from base64 import b64encode
from dataclasses import asdict, fields
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import stat
import time

ROOT = Path(__file__).resolve().parents[1]
MAX_SECONDS = 600
MAX_POLICY_UNITS = 16384
MAX_CALL_POLICY_UNITS = 8192
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
INPUT_BYTES = 1523712
INPUT_SHA256 = "41e3d9636cc9ffc026a87ca4bae3901cbf58dcff3c17039229c742f8898f14b2"
ORIGINAL_ARCHIVE_SHA256 = "39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f"
ORIGINAL_MEMBER = "qualification/cases/case_00/candidate_03/native.db"
REPAIR_ID = "repair-3295d0e50cc47ac2f23bb183"
SUBGOAL_ID = "cause-6887f4b6a53020e465d7f15d"
PARENT_CAUSE_ID = "cause-0dc915a7acdf9ebf4fc0ae0b"
CANDIDATE_ID = "candidate-effect-ffd7a42e81d1440523fa32f5"
VERIFIER_ID = "verifier-receipt-615dec807a7b76995960bfd36126358dd9e20ada183a1af42c8d9b4f0f8f0a47"
FRAME_DIGEST = "671bae98960f0791852a2cff43f8e06fd90f0d1060624ba06b9adf3a3f925609"
PRE_STATE_DIGEST = "2cff5bb7a71995288d9f2aae3d8377a60361bf49da64833951ef62765a1db4c9"
HEAD = {
    "state_digest": "096674a1225dfd1b50acfa26422076cf215f5f3f21cd098d8290f0ab9fe54b17",
    "state_version": 6,
    "trace_digest": "66df9c33794e6ba201da151dd5416d046d095f5aa7f5fa9cd9ec231bfd929eeb",
    "model_digest": "76a9bcbce5ffdec4c2dbc9d8ea9958a268dcebf3775f53dd6058a72086709528",
    "commit_receipt_id": "commit-7e24d42d525d62cfcc94b9a5",
}
TRACE_DIGESTS = (
    "53e12850182ddfd4b53f3fe08e46b976579ca5168e3cd242ec30610863548414",
    "2831d9be59dfc6f6ecd4779416a95e5f3ac13316203f55bcd638ec23e6107d59",
    "dfb2581ebcb03588b274ecc8a68a3be31ae1ccc78778a07edf4c1acbcfc06fb4",
    "72630141311548428622144b1a037f778941cb892b6f9466056348f2c956eb62",
    "f4ac1561bdff893a78cf4be660bc984ab8f20d09626a09a1c37186905fbadf2f",
    HEAD["trace_digest"],
)
BOUNDARY = {
    "saved_native_repair_only": True,
    "outer_caller_stack_restored": False,
    "full_task_return_proven": False,
    "qualification_passed": False,
    "learning_proven": False,
    "universal_R_expected_L1_claimed": False,
    "training": False,
}


class SavedRepairError(RuntimeError):
    pass


def require(condition, code):
    if not condition:
        raise SavedRepairError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(value):
    return sha256(canonical(value)).hexdigest()


def _failure(stage, error):
    return {"stage": stage, "type": type(error).__name__, "message": str(error)}


def _integer_sum(value):
    if type(value) is int and value >= 0:
        return value
    require(type(value) is list, "COMPUTE_PLAN_INTEGER_REQUIRED")
    return sum(_integer_sum(item) for item in value)


def plan_units(plan):
    return sum(_integer_sum(plan[key]) for key in (
        "route_quanta", "reasoning_step_quanta", "branch_quanta",
        "memory_read_quanta", "diagnostic_probe_quanta"))


def _artifact_evidence(artifact, reference):
    artifact.verify()  # Checks the metadata-bound identity, not a raw-byte digest.
    require(artifact.artifact_id == reference["artifact_id"]
            and artifact.sha256 == reference["sha256"], "STORED_REPAIR_EFFECT_IDENTITY_MISMATCH")
    return {"artifact_sha256": artifact.sha256,
            "payload_sha256": sha256(artifact.payload).hexdigest(),
            "payload_bytes": len(artifact.payload)}


def _validate_before(before):
    require(before["integrity"] is True, "SAVED_STORE_INTEGRITY_FAILED")
    require(before["head"] == HEAD, "SAVED_HEAD_MISMATCH")
    require(len(before["traces"]) == 6, "SAVED_TRACE_COUNT_MISMATCH")
    require(tuple(row["trace_digest"] for row in before["traces"]) == TRACE_DIGESTS,
            "SAVED_TRACE_IDENTITIES_MISMATCH")
    require([row["tick"] for row in before["traces"]] == list(range(1, 7)),
            "SAVED_TICK_SEQUENCE_MISMATCH")
    require(before["identity"]["model"]["model_digest"] == HEAD["model_digest"],
            "SAVED_MODEL_IDENTITY_MISMATCH")


def _validate_result(result, cjt, tick, expected, plan):
    require(result["tick"] == tick and result["cjt_id"] == cjt,
            "RETURNED_NATIVE_CALL_IDENTITY_MISMATCH")
    require(result["accepted"] is True and result["verifier_receipt"]["disposition"] == "ACCEPT",
            "REPAIR_NATIVE_CALL_NOT_ACCEPTED")
    require(result["candidate_effect"]["content"]["symbol"] == expected,
            "REPAIR_NATIVE_SYMBOL_MISMATCH")
    require(result["compute_plan"] == plan["compute_plan"]
            and result["plan_digest"] == plan["plan_digest"]
            and result["policy_units"] == plan["policy_units"], "NATIVE_PLAN_CHANGED")
    effect = result["published_effect"]
    require(type(effect) is dict and effect["producer_cjt_id"] == cjt
            and effect["tick"] == tick
            and result["commit_receipt"]["published_effect_ids"] == [effect["published_effect_id"]],
            "REPAIR_PUBLISHED_EFFECT_MISMATCH")
    require(effect["content_ref"]["sha256"] == result["output_sha256"],
            "REPAIR_OUTPUT_HASH_MISMATCH")


def _drive(ops, record, *, clock=time.monotonic):
    """Control flow on injected operations. Fakes are never native evidence."""
    started = clock()
    result = {"schema": "cas-meta2-saved-repair/8", "status": "REPAIR_REFUSED",
              "repaired": False, "training": False, "claim_boundary": deepcopy(BOUNDARY),
              "evidence_kind": ops.evidence_kind, "native_call_attempts": 0,
              "returned_native_calls": 0, "completed_new_ticks": None,
              "accepted_new_ticks": None, "attempted_policy_units": 0,
              "committed_policy_units": None, "attempts": [], "failures": [],
              "limits": {"native_calls": 2, "max_seconds": MAX_SECONDS,
                         "max_policy_units": MAX_POLICY_UNITS,
                         "max_call_policy_units": MAX_CALL_POLICY_UNITS,
                         "max_output_bytes": MAX_OUTPUT_BYTES},
              "before": None, "after": None, "closure": None,
              "gpu_forward_audit": None, "postchecks": None}
    stage = "restore_snapshot"
    def deadline():
        require(clock() - started < MAX_SECONDS, "SAVED_REPAIR_DEADLINE")
    try:
        deadline()
        before = ops.snapshot()
        result["before"] = before
        record("before.json", before)
        _validate_before(before)
        stage = "reconstruct_exact_subgoal"
        reconstruction = ops.reconstruct()
        record("reconstruction.json", reconstruction)
        require(reconstruction["full_frame_match"] is True
                and reconstruction["frame"]["frame_digest"] == FRAME_DIGEST
                and reconstruction["frame"]["repair_id"] == REPAIR_ID
                and reconstruction["subgoal"]["cause_id"] == SUBGOAL_ID
                and reconstruction["subgoal"]["tick"] == 7
                and reconstruction["pre_bias_version"] == 1,
                "EXACT_REPAIR_RECONSTRUCTION_FAILED")
        returned = []
        for cjt, tick, expected in (("C", 7, "L2"), ("R", 8, "L1")):
            stage = "prepare_" + cjt
            deadline()
            if cjt == "R":
                record("resume_cause.json", ops.resume_cause(returned[0]))
            plan = ops.plan(cjt)
            units = plan_units(plan["compute_plan"])
            require(type(plan["policy_units"]) is int and units == plan["policy_units"]
                    and plan["plan_digest"] == digest(plan["compute_plan"])
                    and 0 < units <= MAX_CALL_POLICY_UNITS, "REPAIR_PLAN_LIMIT_OR_IDENTITY")
            require(result["attempted_policy_units"] + units <= MAX_POLICY_UNITS,
                    "REPAIR_TOTAL_POLICY_LIMIT")
            deadline()
            row = {"cjt_id": cjt, "tick": tick, "expected_symbol": expected,
                   "resume_repair_id": REPAIR_ID if cjt == "R" else None,
                   "plan": plan, "returned": False, "error": None,
                   "gpu_forward_calls_before": ops.forward_calls()}
            result["attempts"].append(row)
            record("attempt_%02d.json" % tick, row)
            # Reservation is made before this one real call. A raised call need
            # not create a tick. Never turn a charged attempt into a commit.
            result["attempted_policy_units"] += units
            result["native_call_attempts"] += 1
            stage = "native_" + cjt
            called_at = clock()
            try:
                native_result = ops.execute(cjt, expected, row["resume_repair_id"], plan)
                row["returned"] = True
                result["returned_native_calls"] += 1
            except BaseException as error:
                row["error"] = _failure(stage, error)
                raise
            finally:
                row["elapsed_seconds"] = clock() - called_at
                row["gpu_forward_calls_after"] = ops.forward_calls()
                observe = getattr(ops, "proposal_observation", None)
                row["proposal_observation"] = observe() if observe is not None else None
                record("attempt_%02d_finished.json" % tick, row)
            record("result_%02d.json" % tick, native_result)
            require(type(row["gpu_forward_calls_after"]) is int
                    and row["gpu_forward_calls_after"] > row["gpu_forward_calls_before"],
                    "NATIVE_CALL_WITHOUT_GPU_FORWARD_OBSERVATION")
            _validate_result(native_result, cjt, tick, expected, plan)
            returned.append(native_result)
            deadline()
        stage = "verify_repair_closure"
        result["closure"] = ops.closure(returned[0], returned[1])
        record("closure.json", result["closure"])
        require(result["closure"]["verified"] is True, "REPAIR_CLOSURE_NOT_VERIFIED")
    except BaseException as error:
        result["failures"].append(_failure(stage, error))
    finally:
        try:
            after = ops.snapshot()
            result["after"] = after
            record("after.json", after)
            before = result["before"]
            require(before is not None, "BEFORE_SNAPSHOT_UNAVAILABLE")
            require(after["integrity"] is True, "AFTER_STORE_INTEGRITY_FAILED")
            require(after["traces"][:6] == before["traces"], "SAVED_SIX_TRACES_CHANGED")
            require(after["identity"] == before["identity"], "FROZEN_NATIVE_IDENTITY_CHANGED")
            added = after["traces"][6:]
            result["completed_new_ticks"] = len(added)
            require(len(added) <= result["native_call_attempts"] <= 2, "EXCESS_NATIVE_TICKS")
            require([item["tick"] for item in added] == list(range(7, 7 + len(added))),
                    "NEW_TICK_SEQUENCE_MISMATCH")
            result["accepted_new_ticks"] = sum(
                len(item["verifier_receipts"]) == 1
                and item["verifier_receipts"][0]["disposition"] == "ACCEPT"
                and len(item["published_effect_ids"]) == 1 for item in added)
            result["committed_policy_units"] = sum(plan_units(item["compute_plan"]) for item in added)
            require(after["head"]["state_version"] == 6 + len(added), "AFTER_HEAD_TICK_MISMATCH")
        except BaseException as error:
            result["failures"].append(_failure("post_snapshot", error))
        try:
            final = ops.finalize()
            result["postchecks"] = final
            result["gpu_forward_audit"] = final["gpu_forward_audit"]
            require(final["weights_unchanged"] is True and final["sources_unchanged"] is True
                    and final["protected_identities_unchanged"] is True and not final["errors"],
                    "FROZEN_POSTCHECK_FAILED")
        except BaseException as error:
            result["failures"].append(_failure("finalize", error))
    result["elapsed_seconds"] = clock() - started
    if (not result["failures"] and result["closure"] and result["closure"]["verified"] is True
            and result["native_call_attempts"] == result["returned_native_calls"] == 2
            and result["completed_new_ticks"] == result["accepted_new_ticks"] == 2):
        result["status"], result["repaired"] = "REPAIR_RESUMED", True
    return result


class _NativeOps:
    evidence_kind = "AWS_NATIVE_CUDA_FROZEN_EXECUTOR"

    def __init__(self, database, device):
        # run() has already refused local/unsigned scope. The cloud wrapper has
        # independently checked its permit, source, reservation and EC2 identity.
        from .native import _frozen
        self.bridge, self.f = _frozen()
        self.device = self.bridge._cuda(self.f, device)
        self.before_sources = self.bridge._source_snapshot()
        self.handles, self.native = [], None
        try:
            from cas_meta.fixture import open_native
            with self.f.torch.random.fork_rng(devices=[self.device.index]):
                self.native = open_native(database)
            self.before_model = self.bridge._model_identity(self.native, self.f)
            self.native.network.to(device=self.device).eval()
            self.native.network.requires_grad_(False)
            self.audit, self.handles = self.bridge._gpu_forward_guards(
                self.native.network, self.f.torch, self.device)
            self.audit["counter_kind"] = "module_forward_pre_hook_entries"
            self.native.materializer = self.bridge._CudaMaterializer(
                self.native.materializer, self.f, self.device)
            require(self.bridge._model_identity(self.native, self.f) == self.before_model,
                    "DEVICE_MOVE_CHANGED_SAVED_WEIGHTS")
        except BaseException:
            for handle in self.handles:
                handle.remove()
            if self.native is not None:
                self.native.close()
            raise
        self.pending_cause = self.parent_cause = self.frame = None
        self.prepared = None
        self.last_proposal = None

    def identity(self):
        n = self.native
        return {"model": self.bridge._model_identity(n, self.f),
                "stored_model_digest": n.state.model_digest,
                "software_digest": n.software_digest,
                "topology": n.network.topology_manifest(),
                "contracts": {key: value.contract_digest for key, value in n.contracts.items()},
                "decoders": {key: value.contract.decoder_digest for key, value in n.decoders.items()}}

    def snapshot(self):
        n = self.native
        return {"head": asdict(n.store.head), "state": n.store.load_state(),
                "traces": list(n.store.trace_events()),
                "integrity": n.store.verify_integrity(), "identity": self.identity(),
                "gpu_forward_audit": deepcopy(self.audit)}

    def reconstruct(self):
        from cas_meta.executor import cause_from_wire
        from cas_cjt.contracts import validate_contract, verify_declared_digest
        from cas_cjt.network_coordinator import NetworkStateEnvelope
        from cas_cjt.repair import open_repair, repair_frame_from_dict
        from cas_cjt.state import tensor_ref_from_mapping
        from cas_cjt.types import CandidateEffect, VerifierReceipt
        store = self.native.store
        trace = store.trace_events()[-1]
        pre_wire = store.load_state(PRE_STATE_DIGEST)
        require(trace["pre_state_digest"] == PRE_STATE_DIGEST
                and trace["state_before"] == pre_wire, "TICK6_PRESTATE_MISMATCH")
        pre_bias = NetworkStateEnvelope.from_dict(pre_wire).by_cjt_id["R"]
        require(pre_bias.version == 1, "REPAIR_RECONSTRUCTION_NEEDS_PRESTATE_R_V1")
        parent = store.immutable_document("causes", PARENT_CAUSE_ID)
        candidate_wire = store.immutable_document("candidate_effects", CANDIDATE_ID)
        receipt_wire = store.immutable_document("verifier_receipts", VERIFIER_ID)
        frame_wire = store.immutable_document("repair_frames", REPAIR_ID)
        require(trace["cause"] == parent and trace["candidate_effects"] == [candidate_wire]
                and trace["verifier_receipts"] == [receipt_wire]
                and trace["repair_frames"] == [frame_wire], "TICK6_DOCUMENT_LINK_MISMATCH")
        def typed(cls, wire, declared, tensor=False):
            validate_contract(wire)
            args = {item.name: wire[item.name] for item in fields(cls)}
            if tensor and args["content_ref"] is not None:
                args["content_ref"] = tensor_ref_from_mapping(args["content_ref"])
            obj = cls(**args)
            require(obj.to_dict() == wire and verify_declared_digest(obj, declared),
                    "STORED_TYPED_DOCUMENT_MISMATCH")
            return obj
        self.parent_cause = cause_from_wire(parent)
        candidate = typed(CandidateEffect, candidate_wire, "candidate_digest", True)
        receipt = typed(VerifierReceipt, receipt_wire, "receipt_digest")
        original = repair_frame_from_dict(frame_wire)
        frame, subgoal = open_repair(cause=self.parent_cause, candidate=candidate,
                                    receipt=receipt, bias=pre_bias)
        require(frame.to_dict() == frame_wire == original.to_dict()
                and frame.frame_digest == FRAME_DIGEST
                and subgoal.cause_id == SUBGOAL_ID
                and subgoal.content_ref == candidate.content_ref,
                "FULL_REPAIR_FRAME_OR_SUBGOAL_MISMATCH")
        self.pending_cause, self.frame = subgoal, frame
        return {"frame": frame.to_dict(), "subgoal": subgoal.to_dict(),
                "original_parent_cause": parent, "rejected_candidate": candidate_wire,
                "verifier_receipt": receipt_wire, "pre_state_digest": PRE_STATE_DIGEST,
                "pre_bias_version": pre_bias.version, "full_frame_match": True,
                "subgoal_reconstructed_not_loaded": True}

    def plan(self, cjt):
        from cas_cjt.control import RouteSettings
        require(self.pending_cause is not None and self.prepared is None, "CALL_NOT_PREPARED")
        require(cjt in self.native.network.select_candidates(self.pending_cause),
                "REPAIR_CJT_NOT_SELECTED")
        with self.f.torch.no_grad():
            materialized = self.native.materializer.materialize(
                state=self.native.state, cause=self.pending_cause, cjt_id=cjt,
                settings=RouteSettings(), supplied_artifacts=())
        wire = materialized.routing.compute_plan.to_authoritative_dict()
        plan = {"compute_plan": wire, "plan_digest": digest(wire), "policy_units": plan_units(wire)}
        self.prepared = (cjt, deepcopy(plan), asdict(self.native.store.head), self.identity())
        return plan

    def forward_calls(self):
        return self.audit["calls"]

    def proposal_observation(self):
        return deepcopy(self.last_proposal)

    def execute(self, cjt, expected, resume_id, plan):
        require(self.prepared == (cjt, plan, asdict(self.native.store.head), self.identity()),
                "PREPARED_NATIVE_BOUNDARY_CHANGED")
        self.prepared = None
        self.last_proposal = None
        def observe(module, arguments, proposal):
            # Read-only observation, not a verifier decision or a published Effect.
            # Keep it even if the frozen runtime raises before committing a tick.
            try:
                from cas_cjt.artifacts import encode_tensor
                value = proposal.candidate_effect.detach()
                require(value.numel() <= 256, "PROPOSAL_OBSERVATION_TOO_LARGE")
                reference, artifact = encode_tensor(value, kind="diagnostic-uncommitted-proposal")
                self.last_proposal = {"cjt_id": cjt, "tick": self.pending_cause.tick,
                    "decoded_content": self.native.decoders[cjt].decode(value),
                    "reference": reference, "artifact_sha256": artifact.sha256,
                    "payload_sha256": sha256(artifact.payload).hexdigest(),
                    "payload_base64": b64encode(artifact.payload).decode("ascii"),
                    "metadata": artifact.metadata, "kind": artifact.kind,
                    "media_type": artifact.media_type, "encoding": artifact.encoding,
                    "not_a_commit_receipt": True, "additional_neural_forward": False}
            except Exception as error:
                self.last_proposal = {"observation_error": _failure("proposal_observation", error),
                    "not_a_commit_receipt": True, "additional_neural_forward": False}
            return None  # Returning a value here would replace the model's output.
        handle = self.native.network.node(cjt).register_forward_hook(observe)
        try:
            with self.f.torch.no_grad():
                actual = self.native.inference_tick(cause=self.pending_cause, cjt_id=cjt,
                    expected_symbol=expected, resume_repair_id=resume_id)
        finally:
            handle.remove()
        wire = actual.materialized.routing.compute_plan.to_authoritative_dict()
        effect = actual.published_effect
        output_sha = None
        output_artifact = None
        if effect is not None:
            stored = self.native.store.load_artifact(effect["content_ref"]["artifact_id"])
            output_artifact = _artifact_evidence(stored, effect["content_ref"])
            output_sha = output_artifact["artifact_sha256"]
        trace = self.native.store.trace_events()[-1]
        result = {"tick": actual.tick, "cjt_id": actual.cjt_id, "accepted": actual.accepted,
                  "cause": actual.cause.to_dict(), "bias_before": actual.bias_before.to_dict(),
                  "bias_after": actual.bias_after.to_dict(),
                  "candidate_effect": actual.candidate_effect.to_dict(),
                  "verifier_receipt": actual.verifier_receipt.to_dict(),
                  "commit_receipt": actual.commit_receipt.to_dict(),
                  "published_effect": effect, "output_sha256": output_sha,
                  "output_artifact": output_artifact,
                  "repair_frame": None if actual.repair_frame is None else actual.repair_frame.to_dict(),
                  "repair_outcome": None if actual.repair_outcome is None else actual.repair_outcome.to_dict(),
                  "compute_plan": wire, "policy_units": plan_units(wire), "plan_digest": digest(wire),
                  "compute_observations": trace["compute_observations"], "trace": trace}
        require(trace["tick"] == actual.tick and trace["cause"] == result["cause"]
                and trace["candidate_effects"] == [result["candidate_effect"]]
                and trace["verifier_receipts"] == [result["verifier_receipt"]]
                and trace["commit_receipt_id"] == result["commit_receipt"]["receipt_id"]
                and trace["compute_plan"] == wire, "RETURNED_RESULT_NOT_STORED")
        return result

    def resume_cause(self, c_result):
        # The RPM_SUBGOAL has a different goal. Resume MUST use the original
        # tick6 parent's operations and goal, exactly as the frozen runtime does.
        effect = c_result["published_effect"]
        self.pending_cause = self.native.cause_from_effect(
            effect["published_effect_id"], tick=8,
            candidate_operation_ids=self.parent_cause.candidate_operation_ids,
            goal_context=self.parent_cause.goal_context)
        return self.pending_cause.to_dict()

    def closure(self, c_result, r_result):
        from cas_cjt.repair import repair_outcome_from_dict
        outcome = r_result["repair_outcome"]
        require(type(outcome) is dict, "REPAIR_OUTCOME_MISSING")
        retained = self.native.store.immutable_document("repair_outcomes", outcome["outcome_id"])
        checked = repair_outcome_from_dict(retained)
        effect, candidate = c_result["published_effect"], r_result["candidate_effect"]
        require(checked.to_dict() == outcome and outcome["status"] == "RETURNED"
                and outcome["repair_id"] == REPAIR_ID and outcome["frame_digest"] == FRAME_DIGEST
                and outcome["tick"] == 8
                and outcome["result_effect_id"] == effect["published_effect_id"]
                and outcome["result_effect_digest"] == effect["publication_digest"]
                and outcome["result_effect_commit_receipt_id"] == effect["commit_receipt_id"]
                and outcome["resumed_cause_id"] == r_result["cause"]["cause_id"]
                and outcome["resumed_candidate_effect_id"] == candidate["candidate_effect_id"]
                and outcome["verifier_receipt_id"] == r_result["verifier_receipt"]["receipt_id"]
                and outcome["target_bias_id"] == "bias:R"
                and outcome["target_bias_version"] == 2
                and outcome["target_bias_digest"] == r_result["bias_before"]["state_digest"],
                "REPAIR_OUTCOME_CROSSLINK_MISMATCH")
        rpm = self.native.state.by_cjt_id["R"].rpm
        require(not rpm.open_repair_ids and REPAIR_ID in rpm.repair_history
                and rpm.suspended_parent_cause_id is None and not rpm.return_addresses,
                "R_STILL_SUSPENDED")
        # Immutable OPEN frame is not edited. A separate RETURNED outcome closes it.
        frame = self.native.store.immutable_document("repair_frames", REPAIR_ID)
        require(frame == self.frame.to_dict() and frame["status"] == "OPEN",
                "IMMUTABLE_REPAIR_FRAME_CHANGED")
        return {"verified": True, "outcome": outcome, "frame_unchanged": True,
                "R_rpm": self.native.state.by_cjt_id["R"].to_dict()["rpm"],
                "full_task_return_proven": False}

    def finalize(self):
        report = {"gpu_forward_audit": deepcopy(self.audit), "weights_unchanged": False,
                  "sources_unchanged": False, "protected_identities_unchanged": False, "errors": []}
        for handle in self.handles:
            handle.remove()
        try:
            after = self.bridge._model_identity(self.native, self.f)
            report.update(model_before=self.before_model, model_after=after,
                          weights_unchanged=after == self.before_model)
        except BaseException as error:
            report["errors"].append(_failure("model_identity", error))
        finally:
            try:
                self.native.close()
            except BaseException as error:
                report["errors"].append(_failure("native_close", error))
        try:
            report["sources_unchanged"] = self.bridge._source_snapshot() == self.before_sources
            self.bridge._verify_protected_identity(self.f.verify_baseline, self.f.verify_installed_wheels)
            report["protected_identities_unchanged"] = True
        except BaseException as error:
            report["errors"].append(_failure("protected_identity", error))
        return report


def _safe_path(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        require(not item.is_symlink() and not (hasattr(item, "is_junction") and item.is_junction()),
                "LINKED_PATH_REFUSED")
    return path


def _file_hash(path):
    value = sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _copy_input(input_db, destination):
    source = _safe_path(input_db)
    before = source.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and before.st_size == INPUT_BYTES, "ORIGINAL_DATABASE_SHAPE_MISMATCH")
    for suffix in ("-wal", "-shm", "-journal"):
        require(not Path(str(source) + suffix).exists(), "ORIGINAL_DATABASE_SIDECAR_PRESENT")
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
                info.st_size, info.st_mtime_ns)
    value = sha256()
    with source.open("rb") as reader, Path(destination).open("xb") as writer:
        opened = os.fstat(reader.fileno())
        require(identity(opened) == identity(before), "ORIGINAL_DATABASE_OPEN_RACE")
        for block in iter(lambda: reader.read(1024 * 1024), b""):
            value.update(block)
            writer.write(block)
        closed_view = os.fstat(reader.fileno())
        require(identity(closed_view) == identity(opened)
                and closed_view.st_ctime_ns == opened.st_ctime_ns, "ORIGINAL_DATABASE_READ_RACE")
    require(identity(source.stat()) == identity(before), "ORIGINAL_DATABASE_PATH_RACE")
    require(value.hexdigest() == _file_hash(destination) == INPUT_SHA256,
            "ORIGINAL_DATABASE_HASH_MISMATCH")
    return {"source": str(source), "sha256": value.hexdigest(), "bytes": before.st_size,
            "original_archive_sha256": ORIGINAL_ARCHIVE_SHA256, "original_member": ORIGINAL_MEMBER,
            "original_database_never_opened_by_sqlite": True}


def run(output, input_db, device="cuda:0"):
    """AWS-only, fresh-output, two-call diagnostic; no retry and no training."""
    require(platform.system() == "Linux" and os.environ.get("CAS_META2_RUN_SAVED_REPAIR") == "1"
            and bool(os.environ.get("CAS_META2_AWS_JOB_ID")), "AWS_SAVED_REPAIR_ADMISSION_REQUIRED")
    require(type(device) is str and (device == "cuda" or device.startswith("cuda:")),
            "CUDA_REQUIRED")
    output = _safe_path(output)
    require(output.resolve().is_relative_to((ROOT / "runs").resolve())
            and output.resolve() != (ROOT / "runs").resolve(), "OUTPUT_OUTSIDE_NEW_RUN")
    output.mkdir(parents=True, exist_ok=False)
    def record(name, value):
        require(Path(name).name == name, "INVALID_RECORD_NAME")
        data = canonical(value) + b"\n"
        require(sum(p.stat().st_size for p in output.iterdir() if p.is_file()) + len(data)
                <= MAX_OUTPUT_BYTES, "SAVED_REPAIR_OUTPUT_LIMIT")
        with (output / name).open("xb") as handle:
            handle.write(data)
    result = None
    try:
        original = _copy_input(input_db, output / "native.db")
        record("input.json", original)
        result = _drive(_NativeOps(output / "native.db", device), record)
    except BaseException as error:
        result = {"schema": "cas-meta2-saved-repair/8", "status": "REPAIR_REFUSED",
                  "repaired": False, "training": False, "claim_boundary": deepcopy(BOUNDARY),
                  "native_call_attempts": 0, "returned_native_calls": 0,
                  "completed_new_ticks": None, "accepted_new_ticks": None,
                  "gpu_forward_audit": None, "failures": [_failure("setup", error)]}
    try:
        source = _safe_path(input_db)
        require(_file_hash(source) == INPUT_SHA256 and source.stat().st_size == INPUT_BYTES,
                "ORIGINAL_DATABASE_CHANGED")
        require(all(not Path(str(source) + s).exists() for s in ("-wal", "-shm", "-journal")),
                "ORIGINAL_DATABASE_SIDECAR_CREATED")
        result["original_database_unchanged"] = True
    except BaseException as error:
        result["failures"].append(_failure("original_postcheck", error))
        result["original_database_unchanged"] = False
        result["status"], result["repaired"] = "REPAIR_REFUSED", False
    result["files_sha256"] = {p.name: _file_hash(p) for p in sorted(output.iterdir()) if p.is_file()}
    record("repair_receipt.json", result)
    return result
