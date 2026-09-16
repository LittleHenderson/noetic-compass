"""Versioned, opt-in CUDA smoke and exact checkpoint reconstruction.

Import and contract validation are pure. Numeric APIs receive an authorized
worker runtime and enforce the existing worker guard. They never launch a
provider. Exposed-fixture execution is not a learning-gain experiment.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import math
import os
import re
import time

from .canonical import canonical_json, digest
from . import rpa_learning_adapter as ingestion
from . import rpa_learning_cycle as cycle

require = cycle.require
SCHEMA = "cncm.rpa-learning-smoke/0.2"
MAX_CHECKPOINT_BYTES = 64 * 1024 * 1024
MAX_TREE_NODES = 8192
MAX_TREE_DEPTH = 16
MAX_TENSOR_ELEMENTS = 4 * 1024 * 1024
METADATA_FIELDS = frozenset({
    "schema_version", "kind", "seed", "model_context", "tokenizer", "ordered_profile",
    "scope", "parameter_names", "training_requests", "source_binding", "prepared_ids",
    "optimizer_class", "learning_rate", "model_identity", "optimizer_identity", "projection_identity",
})
OUTPUT_FILES = (
    "origin.pt", "initial.pt", "final.pt", "initial_checkpoint.json", "final_checkpoint.json",
    "before_predictions.json", "after_predictions.json", "initial_reload_predictions.json",
    "final_reload_predictions.json", "receipt.json",
)


def _hex(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
            "SMOKE_SHA256_INVALID")
    return value


def _same(left, right, reason):
    require(canonical_json(left) == canonical_json(right), reason)


def _requests(value, maximum):
    require(type(value) is list and 0 < len(value) <= maximum, "SMOKE_REQUEST_BOUND")
    for row in value:
        require(type(row) is dict and set(row) == {"operation", "question", "assistance"}
                and row["operation"] in {"LIST_PARTS", "FIND_SHARED_PART", "REACHED_VIA"}
                and type(row["question"]) is dict and row["assistance"] in {"guided", "unassisted"},
                "SMOKE_REQUEST_FIELDS")
    require(len({canonical_json(row) for row in value}) == len(value), "SMOKE_DUPLICATE_REQUEST")


def validate_checkpoint_contract(metadata, *, expected=None):
    """Pure metadata check; supplied hashes alone do not prove numeric state."""
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    from cas_meta2.graph_teaching import ordered_encoder, trainer

    require(type(metadata) is dict and set(metadata) == METADATA_FIELDS,
            "SMOKE_METADATA_FIELDS")
    require(metadata["schema_version"] == SCHEMA and metadata["kind"] in {"INITIAL", "FINAL"},
            "SMOKE_CHECKPOINT_VERSION_OR_KIND")
    seed = metadata["seed"]
    require(type(seed) is int and 0 <= seed < 2**31, "SMOKE_SEED_INVALID")
    context = metadata["model_context"]
    require(type(context) is dict and set(context) == {"model_id", "checkpoint_sha256"}
            and context["model_id"] == "candidate-cas-decompose-ordered-v1", "SMOKE_MODEL_CONTEXT")
    _hex(context["checkpoint_sha256"])
    tokenizer = LosslessPublicTokenizer.from_dict(metadata["tokenizer"])
    _same(tokenizer.to_dict(), metadata["tokenizer"], "SMOKE_TOKENIZER_NONCANONICAL")
    require(tokenizer.max_length == 1024, "SMOKE_TOKENIZER_LIMIT")
    profile = metadata["ordered_profile"]
    require(type(profile) is dict, "SMOKE_PROFILE_FIELDS")
    expected_profile = ordered_encoder.profile_identity(
        tokenizer, d_model=64, seed=seed, projection_sha256=_hex(profile.get("projection_sha256")))
    _same(profile, expected_profile, "SMOKE_PROFILE_MISMATCH")
    scope = metadata["scope"]
    names = metadata["parameter_names"]
    require(type(names) is list and 0 < len(names) <= 128
            and all(type(n) is str and 0 < len(n) <= 256 for n in names)
            and len(set(names)) == len(names), "SMOKE_PARAMETER_NAMES")
    require(type(scope) is dict and set(scope) == {"allowed", "frozen", "contract_id", "role"}
            and scope["contract_id"] == "cas.cjt.operation.^6.decompose/0.2"
            and scope["role"] == "operation:^6"
            and type(scope["allowed"]) is list and type(scope["frozen"]) is list
            and scope["allowed"] == sorted(names) and scope["frozen"] == [], "SMOKE_PARAMETER_SCOPE")
    require(metadata["optimizer_class"] == "torch.optim.adamw.AdamW"
            and type(metadata["learning_rate"]) is float
            and metadata["learning_rate"] == trainer.FROZEN_LEARNING_RATE, "SMOKE_OPTIMIZER_CONTRACT")
    _requests(metadata["training_requests"], 8)
    prepared = metadata["prepared_ids"]
    require(type(prepared) is list and len(prepared) == len(metadata["training_requests"])
            and len(set(prepared)) == len(prepared)
            and all(type(value) is str and re.fullmatch(r"rpa-prepared-[0-9a-f]{64}", value)
                    for value in prepared), "SMOKE_PREPARED_IDENTITIES")
    require(type(metadata["source_binding"]) is dict and bool(metadata["source_binding"]),
            "SMOKE_SOURCE_BINDING_REQUIRED")
    for field in ("model_identity", "optimizer_identity", "projection_identity"):
        _hex(metadata[field])
    require(len(canonical_json(metadata).encode()) <= 1024 * 1024, "SMOKE_METADATA_TOO_LARGE")
    if expected is not None:
        require(type(expected) is dict and set(expected) == METADATA_FIELDS, "SMOKE_EXPECTED_METADATA_FIELDS")
        _same(metadata, expected, "SMOKE_EXPECTED_METADATA_MISMATCH")
    return deepcopy(metadata)


def read_checkpoint_bytes(receipt):
    """Require an external file pin before any checkpoint decoder is called."""
    require(type(receipt) is dict and set(receipt) == {"path", "bytes", "sha256"},
            "SMOKE_CHECKPOINT_RECEIPT_FIELDS")
    require(type(receipt["path"]) is str and Path(receipt["path"]).is_absolute(),
            "SMOKE_CHECKPOINT_PATH")
    require(type(receipt["bytes"]) is int and 0 < receipt["bytes"] <= MAX_CHECKPOINT_BYTES,
            "SMOKE_CHECKPOINT_BYTE_BOUND")
    _hex(receipt["sha256"])
    path = Path(receipt["path"])
    require(path.is_file() and path.stat().st_size == receipt["bytes"], "SMOKE_CHECKPOINT_SIZE_MISMATCH")
    raw = path.read_bytes()
    require(len(raw) == receipt["bytes"] and sha256(raw).hexdigest() == receipt["sha256"],
            "SMOKE_CHECKPOINT_DIGEST_MISMATCH")
    return raw


def state_identity(torch, value):
    """Bounded typed state identity. Tensor bytes are read only on the worker.

    Exact dtype, shape and bytes avoid torch.equal's dtype/zero-sign aliases.
    Device placement is checked separately during CUDA reconstruction.
    """
    visited = [0]
    def walk(node, depth):
        visited[0] += 1
        require(visited[0] <= MAX_TREE_NODES and depth <= MAX_TREE_DEPTH, "SMOKE_STATE_TREE_BOUND")
        if torch.is_tensor(node):
            require(node.numel() <= MAX_TENSOR_ELEMENTS and node.layout == torch.strided,
                    "SMOKE_TENSOR_BOUND_OR_LAYOUT")
            require(bool(torch.isfinite(node).all().item()), "SMOKE_NONFINITE_TENSOR")
            raw = node.detach().contiguous().reshape(-1).view(torch.uint8).cpu().numpy().tobytes()
            return {"type":"tensor", "dtype":str(node.dtype), "shape":list(node.shape),
                    "bytes":len(raw), "sha256":sha256(raw).hexdigest()}
        if type(node) is dict:
            require(all(type(key) in (str, int) for key in node), "SMOKE_STATE_KEY_TYPE")
            return {"type":"dict", "items":[[walk(key,depth+1),walk(node[key],depth+1)]
                for key in sorted(node,key=lambda key:(type(key).__name__,str(key)))]}
        if type(node) in (list, tuple):
            return {"type":type(node).__name__, "items":[walk(item,depth+1) for item in node]}
        require(type(node) in (str, int, float, bool, type(None)), "SMOKE_STATE_VALUE_TYPE")
        require(type(node) is not float or math.isfinite(node), "SMOKE_NONFINITE_SCALAR")
        return {"type":type(node).__name__, "value":node}
    return digest(walk(value,0))


def require_exact_state(torch, left, right, *, reason="SMOKE_STATE_RELOAD_MISMATCH"):
    identity = state_identity(torch, left)
    require(identity == state_identity(torch, right), reason)
    return identity


def _guard(torch, device):
    require(re.fullmatch(r"cuda(?::[0-9]+)?", str(device)) is not None and torch.cuda.is_available(),
            "LEARNING_WORKER_CUDA_REQUIRED")
    cycle._worker_execution_guard()


def _parameter_names(candidate):
    return [name for name, _ in candidate["framework"].module.named_parameters()]


def _optimizer_class(optimizer):
    return type(optimizer).__module__ + "." + type(optimizer).__qualname__


def _projection(torch, candidate):
    encoder = candidate["framework"].encoder
    return torch.stack([encoder["embed"](index) for index in range(len(candidate["tokenizer"].vocabulary))])


def _prepared(document, requests):
    _requests(requests,8)
    rows = [ingestion.prepare_public_lesson(document, **request) for request in requests]
    require(all(row["source_binding"] == rows[0]["source_binding"] for row in rows), "SMOKE_SOURCE_CONTEXT_CHANGED")
    return rows


def write_worker_checkpoint(torch, candidate, *, kind, training_requests, path):
    _guard(torch, candidate["learner"].device)
    prepared = _prepared(candidate["document"],training_requests)
    model = dict(candidate["framework"].module.state_dict())
    optimizer = candidate["learner"].optimizer.state_dict()
    projection = _projection(torch,candidate)
    metadata = {"schema_version":SCHEMA, "kind":kind, "seed":candidate["seed"],
        "model_context":deepcopy(candidate["model_context"]), "tokenizer":candidate["tokenizer"].to_dict(),
        "ordered_profile":deepcopy(candidate["ordered_profile"]), "scope":deepcopy(candidate["scope"]),
        "parameter_names":_parameter_names(candidate), "training_requests":deepcopy(training_requests),
        "source_binding":deepcopy(prepared[0]["source_binding"]),
        "prepared_ids":[row["prepared_id"] for row in prepared],
        "optimizer_class":_optimizer_class(candidate["learner"].optimizer), "learning_rate":0.003,
        "model_identity":state_identity(torch,model), "optimizer_identity":state_identity(torch,optimizer),
        "projection_identity":state_identity(torch,projection)}
    validate_checkpoint_contract(metadata)
    path = Path(path)
    require(path.parent.is_dir(), "LEARNING_OUTPUT_PARENT_REQUIRED")
    with path.open("xb") as stream:
        torch.save({"metadata":metadata,"model_state":model,"optimizer_state":optimizer,
                    "projection":projection},stream)
        stream.flush(); os.fsync(stream.fileno())
    receipt = {"path":str(path.resolve()),"bytes":path.stat().st_size,"sha256":sha256(path.read_bytes()).hexdigest()}
    read_checkpoint_bytes(receipt)
    return {"checkpoint":receipt,"metadata":metadata}


def _encoder_from_checkpoint(torch, device, tokenizer, projection, *, seed):
    """Reconstruct only from saved rows; no tokenizer fit or random projection."""
    from cas_meta2.graph_teaching import ordered_encoder

    require(torch.is_tensor(projection) and tuple(projection.shape) == (len(tokenizer.vocabulary),64)
            and projection.is_floating_point() and bool(torch.isfinite(projection).all().item()),
            "SMOKE_PROJECTION_INVALID")
    projection = projection.detach().to(device).contiguous()
    projection.requires_grad_(False)
    def embed(token_id):
        require(type(token_id) is int and 0 <= token_id < len(tokenizer.vocabulary), "ENCODER_TOKEN_ID_OUT_OF_RANGE")
        return projection[token_id]
    def encode(public):
        encoded = tokenizer.encode_public(public)
        problem_ids = [token for token,kind in zip(encoded["ids"],encoded["kinds"]) if kind == 0]
        slots = {}
        for token,kind,slot in zip(encoded["ids"],encoded["kinds"],encoded["slots"]):
            if kind == 2 and slot in (1,2,3):
                slots.setdefault(slot-1,[]).append(token)
        require(set(slots) == {0,1,2}, "PUBLIC_SLOT_ENCODING_INCOMPLETE")
        return problem_ids,slots
    inherited = {"encode":encode,"embed":embed,"tokenizer":tokenizer,"vocabulary_size":len(tokenizer.vocabulary),
        "projection_frozen":True,"structural_problem_binding":True,"max_length":1024,"d_model":64}
    return ordered_encoder.build_ordered_encoder(torch,inherited,seed=seed,device=device)


def reload_worker_candidate(torch, device, *, document, training_requests, checkpoint, metadata):
    """Caller-bound, weights-only reconstruction of model, optimizer and encoder."""
    _guard(torch,device)
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    from cas_meta2.graph_teaching import real_framework,trainer

    expected = validate_checkpoint_contract(metadata)
    prepared = _prepared(document,training_requests)
    _same(training_requests,expected["training_requests"],"SMOKE_RELOAD_TRAINING_REQUESTS")
    _same(prepared[0]["source_binding"],expected["source_binding"],"SMOKE_RELOAD_SOURCE_BINDING")
    _same([row["prepared_id"] for row in prepared],expected["prepared_ids"],"SMOKE_RELOAD_PREPARED_IDS")
    raw = read_checkpoint_bytes(checkpoint)
    # Decode the exact bytes already checked, avoiding a second path-open race.
    loaded = torch.load(BytesIO(raw),map_location="cpu",weights_only=True)
    require(type(loaded) is dict and set(loaded) == {"metadata","model_state","optimizer_state","projection"},
            "SMOKE_CHECKPOINT_PAYLOAD_FIELDS")
    validate_checkpoint_contract(loaded["metadata"],expected=expected)
    for field, identity in (("model_state","model_identity"),("optimizer_state","optimizer_identity"),
                            ("projection","projection_identity")):
        require(state_identity(torch,loaded[field]) == expected[identity], "SMOKE_RETAINED_"+identity.upper())
    tokenizer = LosslessPublicTokenizer.from_dict(expected["tokenizer"])
    encoder = _encoder_from_checkpoint(torch,device,tokenizer,loaded["projection"],seed=expected["seed"])
    _same(encoder["ordered_profile"],expected["ordered_profile"],"SMOKE_RELOADED_ACTUAL_PROFILE")
    framework = real_framework.build_graph_training_framework(torch,device,seed=expected["seed"],encoder=encoder)
    names = [name for name,_ in framework.module.named_parameters()]
    _same(names,expected["parameter_names"],"SMOKE_RELOAD_PARAMETER_ORDER")
    scope = trainer.scope_parameters(framework,framework.module)
    _same(scope,expected["scope"],"SMOKE_RELOAD_SCOPE")
    framework.module.load_state_dict(loaded["model_state"],strict=True)
    require_exact_state(torch,dict(framework.module.state_dict()),loaded["model_state"],reason="SMOKE_RELOAD_MODEL_VALUES")
    require(all(parameter.device.type == "cuda" for parameter in framework.module.parameters()),
            "SMOKE_RELOAD_MODEL_DEVICE")
    kwargs = {"document":document,"tokenizer":tokenizer,"ordered_profile":encoder["ordered_profile"],
              "model_context":deepcopy(expected["model_context"])}
    lessons = [ingestion.bind_prepared_lesson(row,**kwargs) for row in prepared]
    public_kwargs = {key:value for key,value in kwargs.items() if key != "document"}
    packets = [ingestion.prediction_packet(row,**public_kwargs) for row in lessons]
    targets = [ingestion.check_source_target(row,**kwargs) for row in lessons]
    registry = [{**deepcopy(packet),"encoded_correct_index":target["encoded_correct_index"]}
                for packet,target in zip(packets,targets)]
    learner = real_framework.GraphLearner(torch,framework,registry,device,trainer.FROZEN_LEARNING_RATE)
    require(_optimizer_class(learner.optimizer) == expected["optimizer_class"],"SMOKE_RELOAD_OPTIMIZER_CLASS")
    learner.optimizer.load_state_dict(loaded["optimizer_state"])
    require_exact_state(torch,learner.optimizer.state_dict(),loaded["optimizer_state"],reason="SMOKE_RELOAD_OPTIMIZER_VALUES")
    predictor = cycle.PublicPredictor(learner,training_packets=packets,**public_kwargs)
    candidate = {**kwargs,"framework":framework,"learner":learner,"predictor":predictor,"lessons":lessons,
                 "scope":scope,"seed":expected["seed"],"reload_checkpoint":deepcopy(checkpoint)}
    require_exact_state(torch,_projection(torch,candidate),loaded["projection"],reason="SMOKE_RELOAD_PROJECTION_VALUES")
    require(read_checkpoint_bytes(checkpoint) == raw,"SMOKE_CHECKPOINT_CHANGED_DURING_RELOAD")
    return candidate


def verify_public_numeric_paths(torch, candidate, packets):
    """Public-only path comparison; never calls the legacy target-reading scores."""
    _guard(torch,candidate["learner"].device)
    require(type(packets) is list and 0 < len(packets) <= 16,"SMOKE_PREDICTION_PACKET_BOUND")
    learner, encoder = candidate["learner"],candidate["framework"].encoder
    checked, cached, uncached = 0,0,0
    with torch.no_grad():
        for packet in packets:
            public = candidate["predictor"].validate(packet)
            problem = encoder["encode_problem"](public["public"])
            _,slots = encoder["encode"](public["public"])
            zero = torch.zeros_like(problem)
            options = [learner._sum(item) if item else zero for item in learner._content_ids(slots)]
            value = learner.module(problem.unsqueeze(0))[0]
            direct = torch.stack([torch.dot(value,option) for option in options])
            if public["record_id"] in learner._index:
                position = learner._index[public["record_id"]]
                require_exact_state(torch,problem,learner._problem_vectors[position],reason="SMOKE_EXACT_PROBLEM_CACHE")
                require_exact_state(torch,options,learner._option_vectors[position],reason="SMOKE_EXACT_OPTION_CACHE")
                require_exact_state(torch,direct,learner.forward(position),reason="SMOKE_CACHED_DIRECT_SCORES")
                cached += 1
            else:
                uncached += 1
            selected = candidate["predictor"].predict(public)
            _same(selected,public["encoded_options"][int(torch.argmax(direct).item())],"SMOKE_DIRECT_PREDICTION")
            checked += 1
    return {"public_rows_checked":checked,"cached_rows":cached,"on_demand_rows":uncached,
            "exact_cached_and_direct_tensors":True,"public_predictions_match_direct":True}


def verify_reloaded_values(torch, original, restored, packets):
    """Compare live original and independently reconstructed candidate values."""
    _guard(torch,original["learner"].device)
    require(type(packets) is list and 0 < len(packets) <= 16,"SMOKE_PREDICTION_PACKET_BOUND")
    for left,right in ((dict(original["framework"].module.state_dict()),dict(restored["framework"].module.state_dict())),
                       (original["learner"].optimizer.state_dict(),restored["learner"].optimizer.state_dict()),
                       (_projection(torch,original),_projection(torch,restored)),
                       (original["learner"]._problem_vectors,restored["learner"]._problem_vectors),
                       (original["learner"]._option_vectors,restored["learner"]._option_vectors)):
        require_exact_state(torch,left,right,reason="SMOKE_LIVE_RELOADED_VALUES")
    with torch.no_grad():
        for packet in packets:
            original["predictor"].validate(packet); restored["predictor"].validate(packet)
            require_exact_state(torch,original["framework"].encoder["encode_problem"](packet["public"]),
                restored["framework"].encoder["encode_problem"](packet["public"]),reason="SMOKE_RELOADED_PUBLIC_VECTOR")
    return {"model_optimizer_projection_cache_exact":True,"public_vectors_checked":len(packets)}


def _prediction_lessons(candidate,requests):
    _requests(requests,16)
    kwargs = cycle._lesson_arguments(candidate)
    lessons = [ingestion.bind_prepared_lesson(
        ingestion.prepare_public_lesson(candidate["document"],**request),**kwargs) for request in requests]
    packets = [ingestion.prediction_packet(row,**{key:value for key,value in kwargs.items() if key != "document"})
               for row in lessons]
    require(len({row["record_id"] for row in packets}) == len(packets),"SMOKE_DUPLICATE_PREDICTION_ID")
    return lessons,packets


def _targets(candidate,lessons,packets):
    result = {}
    for lesson,packet in zip(lessons,packets):
        target = ingestion.check_source_target(lesson,**cycle._lesson_arguments(candidate))
        result[packet["record_id"]] = {"public_input_digest":digest(packet),
            "encoded_correct_index":target["encoded_correct_index"],"expected_answer":target["expected_answer"],
            "operation":lesson["provenance"]["request"]["operation"]}
    return result


def run_worker_smoke(torch, device, *, document, training_requests, prediction_requests, seed, output):
    """Bounded exposed-material CUDA teaching plus two exact reload checks.

    The caller must pin the worker source/runtime and enforce its outer timeout.
    This function uses the accepted 64-update/600-second training budget.
    """
    _guard(torch,device)
    _requests(training_requests,8); _requests(prediction_requests,16)
    output = Path(output); output.mkdir(parents=False,exist_ok=False)
    started = time.monotonic()
    counters = {"original":0,"initial_reload":0,"final_reload":0}
    hooks = []
    def attach(candidate,label):
        def count(_module,_arguments):counters[label] += 1
        hooks.append(candidate["framework"].module.register_forward_pre_hook(count))
    def json_write(name,value):
        return cycle._write_new(output/name,cycle._raw(value))
    try:
        original = cycle.create_worker_candidate(torch,device,document=document,requests=training_requests,
            seed=seed,initial_checkpoint_path=output/"origin.pt")
        attach(original,"original")
        lessons,packets = _prediction_lessons(original,prediction_requests)
        initial = write_worker_checkpoint(torch,original,kind="INITIAL",training_requests=training_requests,path=output/"initial.pt")
        json_write("initial_checkpoint.json",initial)
        initial_cache = cycle.verify_worker_cache(torch,original)
        initial_paths = verify_public_numeric_paths(torch,original,packets)
        require(initial_paths["cached_rows"] > 0 and initial_paths["on_demand_rows"] > 0,
                "SMOKE_BOTH_PREDICTION_PATHS_REQUIRED")
        before = cycle.seal_predictions(original["predictor"],packets,path=output/"before_predictions.json")
        restored_initial = reload_worker_candidate(torch,device,document=document,training_requests=training_requests,**initial)
        attach(restored_initial,"initial_reload")
        initial_values = verify_reloaded_values(torch,original,restored_initial,packets)
        initial_reload_cache = cycle.verify_worker_cache(torch,restored_initial)
        initial_reload_paths = verify_public_numeric_paths(torch,restored_initial,packets)
        initial_seal = cycle.seal_predictions(restored_initial["predictor"],packets,path=output/"initial_reload_predictions.json")
        require(Path(before["path"]).read_bytes() == Path(initial_seal["path"]).read_bytes(),"SMOKE_INITIAL_RELOAD_PREDICTIONS")
        training = cycle.run_bound_training(original)
        require(type(training["training"]["completed_updates"]) is int
                and 0 < training["training"]["completed_updates"] <= 64
                and bool(training["containment"]["permitted_changes"]),"LEARNING_SMOKE_NO_OBSERVED_UPDATE")
        final_cache = cycle.verify_worker_cache(torch,original)
        final_paths = verify_public_numeric_paths(torch,original,packets)
        after = cycle.seal_predictions(original["predictor"],packets,path=output/"after_predictions.json")
        final = write_worker_checkpoint(torch,original,kind="FINAL",training_requests=training_requests,path=output/"final.pt")
        json_write("final_checkpoint.json",final)
        _same(initial["metadata"]["tokenizer"],final["metadata"]["tokenizer"],"SMOKE_FROZEN_TOKENIZER_CHANGED")
        _same(initial["metadata"]["ordered_profile"],final["metadata"]["ordered_profile"],"SMOKE_FROZEN_PROFILE_CHANGED")
        require(initial["metadata"]["projection_identity"] == final["metadata"]["projection_identity"],"SMOKE_FROZEN_PROJECTION_CHANGED")
        restored_final = reload_worker_candidate(torch,device,document=document,training_requests=training_requests,**final)
        attach(restored_final,"final_reload")
        final_values = verify_reloaded_values(torch,original,restored_final,packets)
        final_reload_cache = cycle.verify_worker_cache(torch,restored_final)
        final_reload_paths = verify_public_numeric_paths(torch,restored_final,packets)
        final_seal = cycle.seal_predictions(restored_final["predictor"],packets,path=output/"final_reload_predictions.json")
        require(Path(after["path"]).read_bytes() == Path(final_seal["path"]).read_bytes(),"SMOKE_FINAL_RELOAD_PREDICTIONS")
        # The private scoring join occurs only after all four public seals.
        # Source admission has already reconstructed teacher sidecars; they are
        # not passed to PublicPredictor or to the direct numeric path checks.
        before_score = cycle.score_sealed_predictions(before,targets_loader=lambda:_targets(original,lessons,packets))
        after_score = cycle.score_sealed_predictions(after,targets_loader=lambda:_targets(original,lessons,packets))
        torch.cuda.synchronize(device)
        report = {"schema_version":SCHEMA,"status":"MECHANICAL_SMOKE_AND_RELOAD_OBSERVED","seed":seed,
            "checkpoints":{"origin":original["initial_checkpoint"],"initial":initial,"final":final},
            "checkpoint_reload_verified":True,
            "reload":{"initial":{"cache":initial_reload_cache,"paths":initial_reload_paths,"values":initial_values,"prediction_seal":initial_seal,
                                   "model_optimizer_projection_values_exact":True},
                      "final":{"cache":final_reload_cache,"paths":final_reload_paths,"values":final_values,"prediction_seal":final_seal,
                                 "model_optimizer_projection_values_exact":True}},
            "original":{"initial_cache":initial_cache,"final_cache":final_cache,
                        "initial_paths":initial_paths,"final_paths":final_paths},
            "training":training,"predictions":{"before":before,"after":after},
            "scoring":{"before":before_score,"after":after_score},
            "ordered_profile":original["ordered_profile"],"frozen_encoder_unchanged":True,
            "forward_calls":{**counters,"total":sum(counters.values())},
            "prediction_calls":{"original":original["predictor"].calls,
                "initial_reload":restored_initial["predictor"].calls,"final_reload":restored_final["predictor"].calls},
            "elapsed_seconds":time.monotonic()-started,"learning_improvement_established":False,
            "boundary":"Exposed-material mechanical connection and same-worker reconstruction. No matched control, held-out transfer, fresh-process restart, or full-machine claim."}
        json_write("receipt.json",report)
        return report
    except Exception as error:
        json_write("failure.json",{"schema_version":SCHEMA,"status":"MECHANICAL_SMOKE_OR_RELOAD_FAILED",
            "type":type(error).__name__,"detail":str(error)[:500],"forward_calls":counters,
            "elapsed_seconds":time.monotonic()-started,"learning_improvement_established":False})
        raise
    finally:
        for hook in hooks:hook.remove()
