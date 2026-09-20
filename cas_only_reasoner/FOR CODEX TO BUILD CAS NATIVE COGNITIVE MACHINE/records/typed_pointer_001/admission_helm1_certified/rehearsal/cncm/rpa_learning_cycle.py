"""Candidate teaching connection and strict public prediction boundary.

Pure control functions support explicit test doubles. Numeric construction is
an opt-in worker call receiving an already-authorized CUDA runtime; this module
does not acquire a provider, device, credentials, or execution permission.
A mechanical connection pass is never a learning-improvement claim.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import time

from .canonical import canonical_json, digest
from .model import ContractError
from . import rpa_learning_adapter as ingestion

SCHEMA = "cncm.rpa-learning-cycle/0.1"
SEAL_SCHEMA = "cncm.rpa-public-predictions/0.1"
MAX_PACKETS = 4096
MAX_SEAL_BYTES = 16 * 1024 * 1024


def require(condition, reason):
    if not condition:
        raise ContractError(reason)


def _raw(value):
    return (canonical_json(value) + "\n").encode("utf-8")


def _write_new(path, raw):
    path = Path(path)
    require(path.parent.is_dir(), "LEARNING_OUTPUT_PARENT_REQUIRED")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(path.read_bytes() == raw, "LEARNING_OUTPUT_READBACK_MISMATCH")
    return {"path": str(path.resolve()), "bytes": len(raw),
            "sha256": sha256(raw).hexdigest()}


class PublicPredictor:
    """Check actual public content before the learner's ID-only cache lookup."""

    def __init__(self, learner, *, tokenizer, ordered_profile, model_context,
                 training_packets):
        self._learner = learner
        self._tokenizer = tokenizer
        self._profile = deepcopy(ordered_profile)
        self._context = deepcopy(model_context)
        require(type(training_packets) is list and 0 < len(training_packets) <= MAX_PACKETS,
                "LEARNING_TRAINING_PACKETS_REQUIRED")
        self._cache = {}
        for packet in training_packets:
            current = self.validate(packet)
            require(current["record_id"] not in self._cache, "LEARNING_DUPLICATE_CACHE_ID")
            self._cache[current["record_id"]] = current
        self.calls = 0
        self._check_training_cache()

    def validate(self, packet):
        return ingestion.validate_prediction_packet(
            packet, tokenizer=self._tokenizer, ordered_profile=self._profile,
            model_context=self._context)

    def _check_training_cache(self):
        # This is metadata inspection, not a claim about numerical vector equality.
        tasks = self._learner.tasks
        require(type(tasks) is list and len(tasks) == len(self._cache),
                "LEARNING_CACHE_SIZE_MISMATCH")
        expected_index = {}
        for position, task in enumerate(tasks):
            require(type(task) is dict and set(task) == {
                "record_id", "public", "encoded_options", "encoded_correct_index"},
                "LEARNING_TRAINING_REGISTRY_FIELDS")
            public = {key: deepcopy(task[key]) for key in
                      ("record_id", "public", "encoded_options")}
            checked = self.validate(public)
            record_id = checked["record_id"]
            require(record_id not in expected_index and
                    self._cache.get(record_id) == checked, "LEARNING_CACHE_BYTES_MISMATCH")
            expected_index[record_id] = position
        require(self._learner._index == expected_index, "LEARNING_CACHE_INDEX_MISMATCH")

    def predict(self, packet):
        checked = self.validate(packet)
        self._check_training_cache()
        require(checked["record_id"] not in self._cache or
                checked == self._cache[checked["record_id"]], "LEARNING_STALE_CACHE_ID")
        call_input = deepcopy(checked)
        result = self._learner.predict(call_input)
        self.calls += 1
        require(call_input == checked, "LEARNING_PREDICTOR_MUTATED_INPUT")
        self._check_training_cache()
        require(sum(canonical_json(result) == canonical_json(option)
                    for option in checked["encoded_options"]) == 1,
                "LEARNING_PREDICTION_NOT_UNIQUE_OPTION")
        return deepcopy(result)


def seal_predictions(predictor, packets, *, path):
    """No teacher/target argument. Persist every prediction before scoring."""
    path = Path(path)
    require(path.parent.is_dir(), "LEARNING_OUTPUT_PARENT_REQUIRED")
    if path.exists():
        raise FileExistsError(str(path))
    require(type(packets) is list and 0 < len(packets) <= MAX_PACKETS,
            "LEARNING_PREDICTION_PANEL_REQUIRED")
    validated = [predictor.validate(packet) for packet in packets]
    require(len({row["record_id"] for row in validated}) == len(validated),
            "LEARNING_DUPLICATE_PREDICTION_ID")
    rows = []
    for packet in validated:
        selected = predictor.predict(packet)
        index = next(index for index, option in enumerate(packet["encoded_options"])
                     if canonical_json(option) == canonical_json(selected))
        rows.append({"record_id": packet["record_id"], "public_input_digest": digest(packet),
                     "encoded_options": deepcopy(packet["encoded_options"]),
                     "selected_index": index})
    body = {"schema_version": SEAL_SCHEMA, "predictions": rows,
            "answer_access": "NO_TARGET_ARGUMENT_OR_TEACHER_CALL",
            "scores": "UNAVAILABLE_TARGET_READING_LEGACY_SCORES_NOT_CALLED"}
    raw = _raw(body)
    require(len(raw) <= MAX_SEAL_BYTES, "LEARNING_SEAL_TOO_LARGE")
    return _write_new(path, raw)


def score_sealed_predictions(seal, *, targets_loader):
    """Open private targets only after checking the caller-bound retained seal."""
    require(type(seal) is dict and set(seal) == {"path", "bytes", "sha256"},
            "LEARNING_SEAL_RECEIPT_FIELDS")
    path = Path(seal["path"])
    require(type(seal["bytes"]) is int and 0 < seal["bytes"] <= MAX_SEAL_BYTES,
            "LEARNING_SEAL_BYTE_BOUND")
    require(path.stat().st_size == seal["bytes"], "LEARNING_SEAL_SIZE_MISMATCH")
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == seal["sha256"], "LEARNING_SEAL_DIGEST_MISMATCH")
    body = json.loads(raw)
    require(_raw(body) == raw, "LEARNING_SEAL_NONCANONICAL")
    require(type(body) is dict and set(body) == {
        "schema_version", "predictions", "answer_access", "scores"}
        and body["schema_version"] == SEAL_SCHEMA
        and body["answer_access"] == "NO_TARGET_ARGUMENT_OR_TEACHER_CALL"
        and body["scores"] == "UNAVAILABLE_TARGET_READING_LEGACY_SCORES_NOT_CALLED",
        "LEARNING_SEAL_BODY_INVALID")
    rows = body["predictions"]
    require(type(rows) is list and 0 < len(rows) <= MAX_PACKETS, "LEARNING_SEAL_ROWS_INVALID")
    ids = []
    for row in rows:
        require(type(row) is dict and set(row) == {
            "record_id", "public_input_digest", "encoded_options", "selected_index"},
            "LEARNING_SEAL_ROW_FIELDS")
        require(type(row["record_id"]) is str
                and re.fullmatch(r"rpa-learning-input-[0-9a-f]{64}", row["record_id"]) is not None
                and type(row["public_input_digest"]) is str
                and re.fullmatch(r"[0-9a-f]{64}", row["public_input_digest"]) is not None,
                "LEARNING_SEAL_ID_INVALID")
        require(type(row["encoded_options"]) is list and len(row["encoded_options"]) == 3
                and len({canonical_json(v) for v in row["encoded_options"]}) == 3
                and type(row["selected_index"]) is int and 0 <= row["selected_index"] < 3,
                "LEARNING_SEAL_SELECTION_INVALID")
        ids.append(row["record_id"])
    require(len(set(ids)) == len(ids), "LEARNING_DUPLICATE_SEALED_ID")
    require(callable(targets_loader), "LEARNING_PRIVATE_TARGET_LOADER_REQUIRED")
    targets = targets_loader()
    require(type(targets) is dict and set(targets) == set(ids),
            "LEARNING_PRIVATE_TARGET_SET_MISMATCH")
    scored = []
    for row in rows:
        target = targets[row["record_id"]]
        require(type(target) is dict and set(target) == {
            "public_input_digest", "encoded_correct_index", "expected_answer", "operation"},
            "LEARNING_PRIVATE_TARGET_FIELDS")
        index = target["encoded_correct_index"]
        require(type(index) is int and 0 <= index < 3
                and target["public_input_digest"] == row["public_input_digest"]
                and canonical_json(target["expected_answer"]) == canonical_json(row["encoded_options"][index]),
                "LEARNING_PRIVATE_TARGET_BINDING_MISMATCH")
        scored.append({"record_id": row["record_id"], "operation": target["operation"],
                       "selected_index": row["selected_index"], "correct_index": index,
                       "correct": row["selected_index"] == index})
    require(path.read_bytes() == raw, "LEARNING_SEAL_CHANGED_DURING_SCORING")
    return {"schema_version": SCHEMA, "prediction_seal_sha256": seal["sha256"],
            "total": len(scored), "correct": sum(row["correct"] for row in scored),
            "rows": scored, "boundary": "Caller source-checked targets; integrity is not authenticated custody."}


def _lesson_arguments(candidate):
    return {"document": candidate["document"], "tokenizer": candidate["tokenizer"],
            "ordered_profile": candidate["ordered_profile"],
            "model_context": candidate["model_context"]}


def _worker_execution_guard():
    # Reuse the existing Linux-worker and explicit-enable boundary. This flag
    # is configuration, not proof of provider identity or spending authority.
    from cas_meta2.teaching_cycle.gpu_adapter import execution_guard
    execution_guard()


def create_worker_candidate(torch, device, *, document, requests, seed, initial_checkpoint_path):
    """Build the real ordered encoder and learner on an authorized CUDA worker.

    The caller controls the provider/worker and must not invoke this on a laptop.
    This function receives that runtime; it performs no launch or provider call.
    Tokenizer fitting reads only the supplied training requests.
    """
    from cas_meta2.graph_teaching import ordered_encoder, real_framework, trainer

    require(type(seed) is int and 0 <= seed < 2**31, "LEARNING_WORKER_SEED_INVALID")
    require(re.fullmatch(r"cuda(?::[0-9]+)?", str(device)) is not None and torch.cuda.is_available(),
            "LEARNING_WORKER_CUDA_REQUIRED")
    _worker_execution_guard()
    require(type(requests) is list and 0 < len(requests) <= MAX_PACKETS,
            "LEARNING_WORKER_TRAINING_REQUESTS_REQUIRED")
    prepared = []
    for request in requests:
        require(type(request) is dict and set(request) == {"operation", "question", "assistance"},
                "LEARNING_REQUEST_FIELDS")
        prepared.append(ingestion.prepare_public_lesson(document, **request))
    publics = [deepcopy(row["public"]) for row in prepared]
    # build_graph_training_framework accepts seed but its bank initialization
    # uses the global RNG. Seed it explicitly, equally in every future arm.
    torch.manual_seed(seed)
    inherited = real_framework.build_encoder(torch, publics, d_model=64,
                                            seed=seed, device=device)
    encoder = ordered_encoder.build_ordered_encoder(torch, inherited, seed=seed, device=device)
    framework = real_framework.build_graph_training_framework(
        torch, device, seed=seed, encoder=encoder)
    scope = trainer.scope_parameters(framework, framework.module)
    projection = torch.stack([encoder["embed"](index)
                              for index in range(len(encoder["tokenizer"].vocabulary))])
    checkpoint = {"schema_version": SCHEMA, "kind": "RUN_INITIAL_MODEL_AND_FROZEN_ENCODER",
                  "model_state": framework.module.state_dict(), "projection": projection,
                  "tokenizer": encoder["tokenizer"].to_dict(),
                  "encoder_identity": encoder["ordered_profile"], "seed": seed, "scope": scope}
    checkpoint_path = Path(initial_checkpoint_path)
    require(checkpoint_path.parent.is_dir(), "LEARNING_OUTPUT_PARENT_REQUIRED")
    with checkpoint_path.open("xb") as stream:
        torch.save(checkpoint, stream)
        stream.flush()
        os.fsync(stream.fileno())
    checkpoint_sha = sha256(checkpoint_path.read_bytes()).hexdigest()
    context = {"model_id": "candidate-cas-decompose-ordered-v1",
               "checkpoint_sha256": checkpoint_sha}
    kwargs = {"document": document, "tokenizer": encoder["tokenizer"],
              "ordered_profile": encoder["ordered_profile"], "model_context": context}
    lessons = [ingestion.bind_prepared_lesson(row, **kwargs) for row in prepared]
    packets = [ingestion.prediction_packet(row, **{k: v for k, v in kwargs.items()
                                                if k != "document"}) for row in lessons]
    require(len({row["record_id"] for row in packets}) == len(packets),
            "LEARNING_WORKER_DUPLICATE_TRAINING_INPUT")
    targets = [ingestion.check_source_target(row, **kwargs) for row in lessons]
    registry = [{**deepcopy(packet), "encoded_correct_index": target["encoded_correct_index"]}
                for packet, target in zip(packets, targets)]
    learner = real_framework.GraphLearner(
        torch, framework, registry, device, trainer.FROZEN_LEARNING_RATE)
    predictor = PublicPredictor(learner, tokenizer=encoder["tokenizer"],
                               ordered_profile=encoder["ordered_profile"],
                               model_context=context, training_packets=packets)
    return {**kwargs, "framework": framework, "learner": learner, "predictor": predictor,
            "lessons": lessons, "scope": scope, "seed": seed,
            "initial_checkpoint": {"path": str(checkpoint_path.resolve()),
                                   "sha256": checkpoint_sha,
                                   "bytes": checkpoint_path.stat().st_size},
            "identity_evidence": "WORKER_COMPUTED_INITIAL_CHECKPOINT_AND_ORDERED_PROFILE",
            "checkpoint_role": "Run-initial identity remains fixed during candidate updates."}


def run_bound_training(candidate, *, budget=None, wall_clock=time.monotonic):
    """Inject the newly admitted records; never select the legacy dataset."""
    from cas_meta2.graph_teaching import trainer

    budget = (budget or trainer.TrainingBudget()).validate()
    records = [ingestion.training_record(lesson, **_lesson_arguments(candidate))
               for lesson in candidate["lessons"]]
    def check_model():
        require(candidate["learner"].framework is candidate["framework"]
                and candidate["learner"].module is candidate["framework"].module
                and candidate["predictor"]._learner is candidate["learner"],
                "LEARNING_LEARNER_MODEL_MISMATCH")
    check_model()
    scope = trainer.scope_parameters(candidate["framework"], candidate["framework"].module)
    require(scope == candidate["scope"], "LEARNING_PARAMETER_SCOPE_MISMATCH")
    expected_registry = []
    for lesson in candidate["lessons"]:
        target = ingestion.check_source_target(lesson, **_lesson_arguments(candidate))
        packet = ingestion.prediction_packet(lesson, **{
            key: value for key, value in _lesson_arguments(candidate).items() if key != "document"})
        expected_registry.append({**packet, "encoded_correct_index": target["encoded_correct_index"]})
    require(len({row["record_id"] for row in expected_registry}) == len(expected_registry),
            "LEARNING_DUPLICATE_TRAINING_ID")
    def check_registry():
        actual = candidate["learner"].tasks
        require(type(actual) is list and len(actual) == len(expected_registry)
                and all(type(row) is dict and type(row.get("encoded_correct_index")) is int
                        for row in actual)
                and canonical_json(actual) == canonical_json(expected_registry),
                "LEARNING_TRAINING_REGISTRY_TARGET_MISMATCH")
    check_registry()
    candidate["predictor"]._check_training_cache()
    before = trainer.parameter_snapshot(candidate["framework"], candidate["framework"].module)
    report = trainer.run_training(candidate["learner"], records, "cas", budget,
                                  wall_clock=wall_clock, history_every=8)
    check_model()
    after = trainer.parameter_snapshot(candidate["framework"], candidate["framework"].module)
    require(set(before) == set(after), "LEARNING_PARAMETER_SET_CHANGED")
    containment = trainer.containment_report(before, after, candidate["scope"]["allowed"])
    require(containment["contained"], "LEARNING_FORBIDDEN_PARAMETER_CHANGE")
    check_registry()
    candidate["predictor"]._check_training_cache()
    return {"schema_version": SCHEMA, "training": report, "scope": deepcopy(candidate["scope"]),
            "parameter_before": before, "parameter_after": after, "containment": containment,
            "record_ids": [row["record_id"] for row in records],
            "boundary": "Execution evidence depends on supplied learner; pure test doubles are not neural runs."}


def verify_worker_cache(torch, candidate):
    """Actual numeric cache comparison. Only call on the authorized CUDA worker."""
    learner, encoder = candidate["learner"], candidate["framework"].encoder
    require(re.fullmatch(r"cuda(?::[0-9]+)?", str(learner.device)) is not None
            and torch.cuda.is_available(), "LEARNING_WORKER_CUDA_REQUIRED")
    _worker_execution_guard()
    candidate["predictor"]._check_training_cache()
    checked = 0
    for position, task in enumerate(learner.tasks):
        problem = encoder["encode_problem"](task["public"])
        require(bool(torch.equal(problem, learner._problem_vectors[position])),
                "LEARNING_NUMERIC_PROBLEM_CACHE_MISMATCH")
        _, slots = encoder["encode"](task["public"])
        content = learner._content_ids(slots)
        zero = torch.zeros_like(problem)
        options = [learner._sum(item) if item else zero for item in content]
        require(len(options) == len(learner._option_vectors[position]) == 3
                and all(bool(torch.equal(a, b)) for a, b in
                        zip(options, learner._option_vectors[position])),
                "LEARNING_NUMERIC_OPTION_CACHE_MISMATCH")
        checked += 1
    return {"numeric_cache_rows_checked": checked, "bitwise_equal": True}


def run_worker_smoke(torch, device, *, document, training_requests, prediction_requests,
                     seed, output):
    """One opt-in mechanical CUDA teaching cycle; never a matched learning test.

    Caller owns provider execution authority and must select only already-exposed
    smoke material. No provider, job, budget reservation or retry is created here.
    All output is retained, including failure details and any partial checkpoints.
    """
    from cas_meta2.graph_teaching import ordered_encoder

    require(re.fullmatch(r"cuda(?::[0-9]+)?", str(device)) is not None
            and torch.cuda.is_available(), "LEARNING_WORKER_CUDA_REQUIRED")
    _worker_execution_guard()
    require(type(training_requests) is list and 0 < len(training_requests) <= 8,
            "LEARNING_SMOKE_TRAINING_BOUND")
    require(type(prediction_requests) is list and 0 < len(prediction_requests) <= 16,
            "LEARNING_SMOKE_PREDICTION_BOUND")
    output = Path(output)
    output.mkdir(parents=False, exist_ok=False)
    started = time.monotonic()
    forward_calls = [0]
    hook = None
    try:
        candidate = create_worker_candidate(
            torch, device, document=document, requests=training_requests, seed=seed,
            initial_checkpoint_path=output / "initial.pt")
        require(type(prediction_requests) is list and 0 < len(prediction_requests) <= MAX_PACKETS,
                "LEARNING_SMOKE_PREDICTION_REQUESTS_REQUIRED")
        lessons = []
        for request in prediction_requests:
            require(type(request) is dict and set(request) == {"operation", "question", "assistance"},
                    "LEARNING_REQUEST_FIELDS")
            prepared = ingestion.prepare_public_lesson(document, **request)
            lessons.append(ingestion.bind_prepared_lesson(prepared, **_lesson_arguments(candidate)))
        packets = [ingestion.prediction_packet(lesson, **{
            key: value for key, value in _lesson_arguments(candidate).items() if key != "document"})
            for lesson in lessons]
        require(len({row["record_id"] for row in packets}) == len(packets),
                "LEARNING_DUPLICATE_PREDICTION_ID")
        def count_forward(_module, _arguments):
            forward_calls[0] += 1
        hook = candidate["framework"].module.register_forward_pre_hook(count_forward)
        initial_cache = verify_worker_cache(torch, candidate)
        training = run_bound_training(candidate)
        require(training["training"]["completed_updates"] > 0
                and bool(training["containment"]["permitted_changes"]),
                "LEARNING_SMOKE_NO_OBSERVED_UPDATE")
        final_cache = verify_worker_cache(torch, candidate)
        encoder = candidate["framework"].encoder
        reobserved = ordered_encoder.build_ordered_encoder(
            torch, {key: value for key, value in encoder.items() if key != "ordered_profile"},
            seed=seed, device=device)
        require(reobserved["ordered_profile"] == candidate["ordered_profile"],
                "LEARNING_SMOKE_FROZEN_ENCODER_CHANGED")
        seal = seal_predictions(candidate["predictor"], packets, path=output / "predictions.json")
        def private_targets():
            result = {}
            for lesson, packet in zip(lessons, packets):
                target = ingestion.check_source_target(lesson, **_lesson_arguments(candidate))
                result[packet["record_id"]] = {
                    "public_input_digest": digest(packet),
                    "encoded_correct_index": target["encoded_correct_index"],
                    "expected_answer": target["expected_answer"],
                    "operation": lesson["provenance"]["request"]["operation"]}
            return result
        scored = score_sealed_predictions(seal, targets_loader=private_targets)
        final_path = output / "final.pt"
        projection = torch.stack([encoder["embed"](index)
                                  for index in range(len(candidate["tokenizer"].vocabulary))])
        with final_path.open("xb") as stream:
            torch.save({"schema_version": SCHEMA,
                        "model_state": candidate["framework"].module.state_dict(),
                        "optimizer_state": candidate["learner"].optimizer.state_dict(),
                        "projection": projection,
                        "tokenizer": candidate["tokenizer"].to_dict(),
                        "encoder_identity": candidate["ordered_profile"],
                        "initial_model_context": candidate["model_context"]}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        torch.cuda.synchronize(device)
        report = {"schema_version": SCHEMA, "status": "MECHANICAL_SMOKE_OBSERVED",
                  "seed": seed, "training": training, "predictions": seal, "scoring": scored,
                  "initial_checkpoint": candidate["initial_checkpoint"],
                  "final_checkpoint": {"path": str(final_path.resolve()),
                                       "bytes": final_path.stat().st_size,
                                       "sha256": sha256(final_path.read_bytes()).hexdigest()},
                  "initial_cache": initial_cache, "final_cache": final_cache,
                  "frozen_encoder_unchanged": True, "ordered_profile": candidate["ordered_profile"],
                  "forward_calls": forward_calls[0],
                  "prediction_calls": candidate["predictor"].calls,
                  "elapsed_seconds": time.monotonic() - started,
                  "checkpoint_reload_verified": False, "learning_improvement_established": False,
                  "boundary": "Exposed-material connection test. No matched control, held-out transfer or full-machine claim."}
        _write_new(output / "receipt.json", _raw(report))
        return report
    except Exception as error:
        _write_new(output / "failure.json", _raw({"schema_version": SCHEMA,
            "status": "MECHANICAL_SMOKE_FAILED", "type": type(error).__name__,
            "detail": str(error)[:500], "forward_calls": forward_calls[0],
            "elapsed_seconds": time.monotonic() - started}))
        raise
    finally:
        if hook is not None:
            hook.remove()
