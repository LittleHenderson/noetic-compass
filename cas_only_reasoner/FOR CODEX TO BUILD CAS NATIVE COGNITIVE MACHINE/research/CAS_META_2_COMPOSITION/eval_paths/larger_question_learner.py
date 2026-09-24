"""Larger-question path, torch half: the ACTUAL Helm pointer learner answering 5- and 6-node questions.

PLAIN SUMMARY. Two entry points, both opt-in and inference-only. Neither edits a protected file.

1. `predict_packet(torch, model, packet, device, *, tagger)` works on a bare pointer container, the object
   `pointer_learner._build_container` returns. Use it for the Helm 2.0 checkpoints (switch OFF, loaded exactly as
   `preservation_digest.py` loads them) and for fresh switch-ON containers. It runs the same steps, in the same
   order, as `PointerCourseLearner._graph` (`pointer_learner.py:1918-1951`), without the learner's counters:
   compile the slots, read the packet, run `GraphForward`, take the head logits, decode, assemble the answer.
   The only change is WHICH slot compiler is used, and that is chosen by `larger_question_scope.route`.

2. `LargerQuestionPointerLearner` subclasses `PointerCourseLearner`. Its `_graph` asks for the route first.
   * ORIGINAL (every world has 4 nodes or fewer): it calls `super()._graph(packet)`, the unchanged original.
   * LARGER (the largest world has 5 or 6 nodes): it runs `_graph_larger`, a line-for-line copy of the original
     `_graph` in which `from . import slots` is replaced by the accepted slots v2 module. A torch-free test
     compares the two function bodies by syntax tree, so the copy cannot drift silently.
   * 7 or more nodes, or a degree above 4: the route raises `LargerPathRefusal` before any counter moves.
   `stage_batch` and `train_sealed_batch` are refused: this class never trains.

GPU ONLY. `predict_packet` refuses a non-CUDA device (`GPU_REQUIRED`); `PointerCourseLearner` already refuses one
(`TYPED_LEARNER_CUDA_REQUIRED`). Importing this module imports `pointer_learner`, which loads the frozen course at
import time through `pointer_contract`. Import it on the AWS worker, not on the laptop.
"""
from __future__ import annotations

import hashlib
import json

from cas_meta2.typed_teaching import pointer_inputs, pointer_learner as PL
from cas_meta2.typed_teaching.pointer_learner import (CLAUSE_COUNT, CORE_ROUNDS, GraphForward, PREDICTION_DEPTH,
                                                      PREDICTION_FIELD_SET, PREDICTION_SCHEMA, _logit_rows,
                                                      _scalar_scores, digest, require)

from . import larger_question_scope as scope

require(PL.DEGREE_STEPS - 1 == scope.READER_EXACT_MAX_DEGREE, "LARGER_PATH_DEGREE_BUCKET_DRIFT")
scope.verify_source_pins()

SCHEMA = "claude.helm-larger-question-learner/0.1"


def _require_gpu(torch, device):
    require(torch.cuda.is_available() and getattr(torch.device(device), "type", None) == "cuda", "GPU_REQUIRED")


def predict_packet(torch, model, packet, device, *, tagger):
    """One question through a pointer container, on the route's slot compiler. Inference only.

    Returns `{route, plan, rows, scores, decisions, answer}`. `rows` are the head-logit tensors, so a caller can
    digest their exact float32 bits (see `logit_bits_digest`). A refused question raises `LargerPathRefusal`
    before any compile or forward.
    """
    _require_gpu(torch, device)
    require(model.training is False, "LARGER_PATH_MODEL_NOT_IN_EVAL_MODE")
    path = scope.route(packet)
    module = scope.slot_module(path)
    with torch.no_grad():
        plan = module.compile_slots(packet)
        reading = pointer_inputs.read_packet(packet)
        reading["_device"] = device
        require(reading["record_id"] == plan["record_id"], "POINTER_READING_RECORD")
        forward = GraphForward(torch, model, reading, device)
        if reading["query"]["kind_name"] == "role_set":
            require(tagger is not None, "POINTER_ROLE_TAGGER_REQUIRED")
            indicators = tagger.indicators(packet)
        else:
            indicators = [0] * CLAUSE_COUNT
        rows = forward.head_logits(plan, indicators)
        values = _scalar_scores(torch, rows)
        scores = _logit_rows(torch, plan, values)
        require(set(scores) == {slot["slot_id"] for slot in plan["slots"]}, "POINTER_SLOT_COVERAGE")
        decisions = module.score_decisions(packet, scores)
        answer = module.assemble_answer(packet, decisions)
    return {"route": path, "plan": plan, "rows": rows, "scores": scores, "decisions": decisions,
            "answer": answer}


def logit_bits_digest(torch, rows):
    """sha256 over every slot's float32 logits as IEEE-754 hex bit patterns: `preservation_digest.py`'s format."""
    bits = {slot_id: ["%08x" % (value & 0xFFFFFFFF)
                      for value in tensor.detach().float().contiguous().view(torch.int32).cpu().tolist()]
            for slot_id, tensor in rows.items()}
    return hashlib.sha256(json.dumps(bits, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class LargerQuestionPointerLearner(PL.PointerCourseLearner):
    """`PointerCourseLearner` plus an opt-in route for 5- and 6-node questions. Inference only.

    Construction, `predict`, `export_checkpoint`, `restore_checkpoint` and `profile` are the parent's, unchanged.
    `restore_checkpoint` is a classmethod that builds `cls(...)`, so it returns this class.
    """

    def _graph(self, packet):
        path = scope.route(packet)
        if path == scope.ORIGINAL:
            result = super()._graph(packet)
        else:
            result = self._graph_larger(packet)
        result["route"] = path
        return result

    def _graph_larger(self, packet):
        """`PointerCourseLearner._graph`, line for line, with the accepted slots v2 compiler. Do not edit alone."""
        import torch
        self._budget()
        self.encoder.verify_frozen()
        require(type(packet) is dict and type(packet.get("source")) is dict
                and type(packet.get("record")) is dict, "POINTER_PACKET")
        slots = scope.slot_module(scope.LARGER)
        plan = slots.compile_slots(packet)
        reading = pointer_inputs.read_packet(packet)
        reading["_device"] = self.device
        require(reading["record_id"] == plan["record_id"], "POINTER_READING_RECORD")
        self._check_core_budget(CORE_ROUNDS)
        self.counters["packet_forward_calls"] += 1
        forward = GraphForward(torch, self.module, reading, self.device, charge=self._charge_round)
        indicators = (self._tag(packet) if reading["query"]["kind_name"] == "role_set"
                      else [0] * CLAUSE_COUNT)
        rows = forward.head_logits(plan, indicators)
        values = _scalar_scores(torch, rows)
        scores = _logit_rows(torch, plan, values)
        require(set(scores) == {slot["slot_id"] for slot in plan["slots"]}, "POINTER_SLOT_COVERAGE")
        decisions = slots.score_decisions(packet, scores)
        answer = slots.assemble_answer(packet, decisions)
        body = {"schema": PREDICTION_SCHEMA, "record_id": plan["record_id"],
                "packet_digest": plan["packet_digest"], "slot_plan_digest": plan["plan_digest"],
                "depth": PREDICTION_DEPTH, "model_revision": self.model_revision,
                "run_context_digest": self.run_identity_digest,
                "encoder_identity_digest": digest(self.encoder.identity), "scores": scores,
                "decisions": decisions, "answer": answer}
        prediction = {**body, "prediction_id": "typed-prediction-" + digest(body)}
        require(set(prediction) == PREDICTION_FIELD_SET, "POINTER_PREDICTION_FIELDS")
        self.counters["prediction_calls"] += 1
        return {"packet": packet, "prediction": prediction, "plan": plan, "rows": rows,
                "forward": forward}

    def stage_batch(self, *args, **kwargs):
        raise scope.LargerPathRefusal("INFERENCE_ONLY", "stage_batch")

    def train_sealed_batch(self, *args, **kwargs):
        raise scope.LargerPathRefusal("INFERENCE_ONLY", "train_sealed_batch")
