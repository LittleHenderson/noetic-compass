"""Bounded CUDA-only, offline candidate learning; NOT native admission or repair.

Import is tensor-library-free. The explicit execution guard is not proof of AWS
identity; the separately retained provider launch receipt must supply that proof.
Each two-row lesson is independent, with fresh zero recurrent control. No running
runtime, persistent Bias, accepted checkpoint, or published Effect is modified.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import platform
import re
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "cas-meta2-condition-skill-training/9"
DEFAULT_CONFIG = {
    "epochs": 100, "batch_size": 64, "learning_rate": 0.003,
    "weight_decay": 0.0, "model_seed": 7, "shuffle_seed": 9,
    "max_seconds": 600, "max_output_bytes": 32 * 1024**2,
}
MODEL_CONFIG = {
    "d_model": 4, "num_heads": 2, "num_relations": 4, "num_layers": 1,
    "dropout": 0.0, "attention_dropout": 0.0,
    "initial_cutoff": 0.01, "initial_saturation": 100.0,
}
FAMILIES = ("cas", "generic_attention")
TEST_SPLITS = ("test_instances", "test_direction_pair")
CLAIMS = {
    "native_runtime_created": False, "native_admission": "NOT_DONE",
    "accepted_artifacts_replaced": False, "persistent_bias_reset": False,
    "historical_C7_repaired": False, "restart_or_resume_proved": False,
    "CAS_advantage_claimed": False, "new_noetic_semantics": False,
    "provider_identity_proved_by_execution_guard": False,
}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def validate_config(config=None):
    """Fixed preregistered bounds; no local tensor work and no tuning overrides."""
    require(config is None or type(config) is dict, "CONFIG_OBJECT_REQUIRED")
    result = dict(DEFAULT_CONFIG)
    if config is not None:
        require(set(config).issubset(result), "UNKNOWN_CONFIG_FIELD")
        for key, value in config.items():
            require(type(value) is type(result[key]) and value == result[key],
                    "FIXED_CONFIG_REQUIRED:" + key)
        result.update(config)
    return result


def execution_guard():
    """Only an execution guard; no provider calls or identity attestation."""
    require(platform.system() == "Linux", "LINUX_WORKER_REQUIRED")
    require(os.environ.get("CAS_META2_RUN_CONDITION_SKILL_V9") == "1",
            "EXPLICIT_CONDITION_SKILL_ENABLE_REQUIRED")
    job = os.environ.get("CAS_META2_AWS_JOB_ID", "")
    require(re.fullmatch(r"cas-meta2-\d{14}-[a-f0-9]{8}", job) is not None,
            "EXPLICIT_AWS_JOB_LABEL_REQUIRED")
    return {"job_label": job, "provider_identity_proved": False,
            "identity_evidence_required": "independent outer provider launch receipt"}


class _Writer:
    def __init__(self, output, limit):
        from .bundle import safe
        self.output = safe(output)
        require(any(self.output.is_relative_to(ROOT / part) for part in ("runs", "records"))
                and not self.output.exists() and self.output.parent.is_dir(),
                "FRESH_SCOPED_OUTPUT_DIRECTORY_REQUIRED")
        self.output.mkdir()
        self.limit, self.used, self.files = limit, 0, {}

    def write(self, name, raw, *, final=False):
        require(Path(name).name == name and name not in self.files, "NEW_FLAT_OUTPUT_REQUIRED")
        require(type(raw) is bytes, "OUTPUT_BYTES_REQUIRED")
        # Preserve room for a negative result even if predictions reach the cap.
        ceiling = self.limit if final else self.limit - 1024**2
        require(self.used + len(raw) <= ceiling, "OUTPUT_BYTE_LIMIT")
        with (self.output / name).open("xb") as stream:
            stream.write(raw)
        item = {"sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
        self.files[name] = item
        self.used += len(raw)
        return item

    def json(self, name, value, *, final=False):
        return self.write(name, encoded(value), final=final)


def summarize(rows):
    """Pure reporting of scored records; NO_EFFECT is wrong for both bits.

    The first wrong bit is derived here from target and prediction alone. When
    every row also carries equality_conditions and unit_margin_conditions,
    equality and unit-margin slice reports are included; otherwise the slice
    keys are omitted entirely.
    """
    require(bool(rows), "EMPTY_SCORE_ROWS")
    confusion = [[0] * 5 for _ in range(4)]  # final column is NO_EFFECT
    bit_correct = [0, 0]
    first_wrong = [0, 0, 0]  # bit 1 first wrong, bit 2 first wrong, correct
    equality = {"cases": 0, "correct": 0}
    unit_margin = {"cases": 0, "correct": 0}
    sliced = all({"equality_conditions", "unit_margin_conditions"}.issubset(row) for row in rows)
    for row in rows:
        target, predicted = row["target"], row["prediction"]
        require(type(target) is int and 0 <= target <= 3 and
                type(predicted) is int and -1 <= predicted <= 3, "SCORE_CLASS_RANGE")
        confusion[target][predicted if predicted >= 0 else 4] += 1
        correct = predicted == target
        for bit in (0, 1):
            bit_correct[bit] += predicted >= 0 and ((predicted >> (1 - bit)) & 1) == ((target >> (1 - bit)) & 1)
        if correct:
            first_wrong[2] += 1
        elif predicted < 0 or ((predicted >> 1) & 1) != ((target >> 1) & 1):
            first_wrong[0] += 1  # bit 1 wrong, or both bits wrong via NO_EFFECT
        else:
            first_wrong[1] += 1
        if sliced:
            require(type(row["equality_conditions"]) is int and 0 <= row["equality_conditions"] <= 2
                    and type(row["unit_margin_conditions"]) is int
                    and 0 <= row["unit_margin_conditions"] <= 2, "SCORE_MARGIN_RANGE")
            if row["equality_conditions"]:
                equality["cases"] += 1
                equality["correct"] += correct
            if row["unit_margin_conditions"]:
                unit_margin["cases"] += 1
                unit_margin["correct"] += correct
    totals = [sum(row) for row in confusion]
    require(all(totals), "MACRO_REQUIRES_ALL_FOUR_CLASSES")
    correct = sum(confusion[index][index] for index in range(4))
    result = {"cases": len(rows), "correct": correct, "accuracy": correct / len(rows),
              "macro_accuracy": sum(confusion[i][i] / totals[i] for i in range(4)) / 4,
              "cross_entropy": sum(row["negative_log_likelihood"] for row in rows) / len(rows),
              "class_counts": totals, "confusion_columns": ["L0", "L1", "L2", "L3", "NO_EFFECT"],
              "confusion": confusion, "bit_accuracy": [count / len(rows) for count in bit_correct],
              "no_effect_count": sum(row[4] for row in confusion),
              "first_wrong_bit": {"bit_1_count": first_wrong[0], "bit_2_count": first_wrong[1],
                                  "none_count": first_wrong[2],
                                  "bit_1_fraction": first_wrong[0] / len(rows),
                                  "bit_2_fraction": first_wrong[1] / len(rows)},
              "error_task_ids": [row["task_id"] for row in rows if row["prediction"] != row["target"]]}
    if sliced:
        result["equality_slice"] = {**equality,
            "accuracy": equality["correct"] / equality["cases"] if equality["cases"] else None}
        result["unit_margin_slice"] = {**unit_margin,
            "accuracy": unit_margin["correct"] / unit_margin["cases"] if unit_margin["cases"] else None}
    return result


ADJUDICATION = {
    "schema": "cas-meta2-condition-skill-adjudication/9",
    "claim_scope": "offline_candidate_learning_only_no_native_admission",
    "status_vocabulary": ["PASS", "FAIL", "EVIDENCE_INCOMPLETE"],
    "not_claimed": ["native admission", "repair", "complete caller return",
                    "persistent Bias", "composition", "CAS advantage over the matched control"],
}

JOINT_BASELINE = 0.25   # balanced four-class constant predictor on attempted rows
PER_BIT_BASELINE = 0.5  # chance for one binary decision on attempted rows

METRIC_DEFINITIONS = {
    "joint_accuracy": {
        "denominator": "all attempted rows, including NO_EFFECT rows",
        "baseline": JOINT_BASELINE,
        "baseline_meaning": "balanced four-class constant predictor",
    },
    "bit_accuracy": {
        "denominator": "all attempted rows; NO_EFFECT is wrong for both bits",
        "baseline": PER_BIT_BASELINE,
        "baseline_meaning": "chance for one ordinary binary decision",
    },
}

PROVIDER_ATTESTATION_KEYS = {
    "account": "807562639912", "region": "us-west-2", "ami": "ami-0fbbd0facbc9e3cff",
    "instance_type": "g7.2xlarge", "gpu_name_contains": "RTX PRO 4500",
    "t4_rejected": True, "visible_gpu_count": 1, "torch_version": "2.11.0+cu128",
    "cuda_version": "12.8", "actual_cuda_operation": True, "automatic_retries": 0,
    "reservation_usd": "4.00",
}

CONTROL_NAMES = ("physical_row_reverse", "slot_reassignment", "direction_1_reverse",
                 "direction_2_reverse", "threshold_1_crossing", "threshold_2_crossing")


def adjudicate(report, provider_attestation=None):
    """Deterministic frozen gate program; never reads private targets itself.

    PASS requires every gate with complete evidence to pass plus a matching
    independent outer provider attestation. Missing evidence yields
    EVIDENCE_INCOMPLETE, never PASS and never FAIL. PASS claims offline
    candidate learning only; it does not claim native admission, repair, caller
    return, persistent Bias, composition, or a CAS advantage over the matched
    control. The trainer-side call has no provider attestation, so the trainer
    verdict is EVIDENCE_INCOMPLETE by design until the outer launcher receipt
    supplies the attestation and re-adjudicates.

    Baselines: joint accuracy is compared against the balanced four-class
    constant predictor (0.25). Each bit is compared against ordinary binary
    chance (0.5), never against 0.25. Trained joint accuracy must also exceed
    untrained joint accuracy on both test splits. The overall verdict is a
    conjunction over all gates; per-family gate rows are reported separately
    and are never erased by the combined verdict.
    """
    require(type(report) is dict, "ADJUDICATION_REPORT_OBJECT_REQUIRED")
    gates = {}
    initial_vs_trained = {}

    def gate(name, passed, actual, required):
        gates[name] = {"passed": bool(passed), "actual": actual, "required": required}

    def field(container, *path):
        try:
            value = container
            for part in path:
                value = value[part]
            return value
        except (KeyError, IndexError, TypeError):
            return None

    gate("experiment_status",
         field(report, "status") == "COMPLETED_OFFLINE_CANDIDATE_EXPERIMENT",
         field(report, "status"), "COMPLETED_OFFLINE_CANDIDATE_EXPERIMENT")
    gate("selection_sealed", field(report, "selection_sealed") is True,
         field(report, "selection_sealed"), True)
    gate("test_targets_parsed", field(report, "test_targets_parsed") is True,
         field(report, "test_targets_parsed"), True)
    before, after = field(report, "source_before"), field(report, "source_after")
    source_ok = (before is not None and before == after
                 and {"baseline", "installed_wheels", "candidate_sources"}.issubset(before))
    gate("source_byte_pins", source_ok, None if before is None else before == after,
         "unchanged source identity with baseline, wheels and candidate pins")
    for split in ("validation", "test_instances", "test_direction_pair"):
        base = field(report, "baselines", split) or {}
        cases = field(base, "cases")
        constant = field(base, "constant_correct")
        oracle = field(base, "oracle_correct")
        constant_accuracy = constant / cases if cases else None
        oracle_accuracy = oracle / cases if cases else None
        gate("constant_baseline_" + split, constant_accuracy is not None and constant_accuracy == JOINT_BASELINE,
             constant_accuracy, JOINT_BASELINE)
        gate("oracle_" + split, oracle_accuracy is not None and oracle_accuracy == 1.0,
             oracle_accuracy, 1.0)
    for family in FAMILIES:
        for split in TEST_SPLITS:
            metrics = field(report, "metrics", family + ".trained", split) or {}
            untrained = field(report, "metrics", family + ".untrained", split) or {}
            accuracy = field(metrics, "accuracy")
            untrained_accuracy = field(untrained, "accuracy")
            gate(family + "_trained_" + split + "_accuracy",
                 accuracy is not None and accuracy > JOINT_BASELINE, accuracy, "> " + str(JOINT_BASELINE))
            gate(family + "_trained_beats_untrained_" + split,
                 accuracy is not None and untrained_accuracy is not None and accuracy > untrained_accuracy,
                 {"untrained": untrained_accuracy, "trained": accuracy},
                 "trained joint accuracy strictly above untrained joint accuracy")
            bits = field(metrics, "bit_accuracy") or [None, None]
            for index, bit in enumerate(bits):
                gate(family + "_trained_" + split + "_bit" + str(index),
                     bit is not None and bit > PER_BIT_BASELINE, bit, "> " + str(PER_BIT_BASELINE))
            initial_vs_trained[family + "." + split] = {
                "untrained_accuracy": untrained_accuracy, "trained_accuracy": accuracy,
                "improved": accuracy is not None and untrained_accuracy is not None
                            and accuracy > untrained_accuracy}
    for family in FAMILIES:
        for split in TEST_SPLITS:
            for control in CONTROL_NAMES:
                summary = field(report, "controls", family + ".trained", split + "." + control) or {}
                joint = field(summary, "joint_accuracy")
                gate(family + "_trained_" + split + "_" + control + "_joint",
                     joint is not None and joint == 1.0, joint, 1.0)
    for family in FAMILIES:
        gate(family + "_fixed_steps", field(report, "training_steps", family) == 2400,
             field(report, "training_steps", family), 2400)
    if provider_attestation is None:
        gate("provider_attestation", False, None, "independent outer provider launch receipt")
    elif type(provider_attestation) is not dict:
        gate("provider_attestation", False, type(provider_attestation).__name__,
             "independent outer provider launch receipt")
    else:
        mismatches = {key: (provider_attestation.get(key), expected)
                      for key, expected in PROVIDER_ATTESTATION_KEYS.items()
                      if provider_attestation.get(key) != expected}
        job = str(provider_attestation.get("job", ""))
        if re.fullmatch(r"cas-meta2-\d{14}-[a-f0-9]{8}", job) is None:
            mismatches["job"] = (provider_attestation.get("job"),
                                 "cas-meta2-<14 digits>-<8 hex lowercase>")
        gate("provider_attestation", not mismatches, mismatches or provider_attestation,
             "independent outer provider launch receipt")
    families = {}
    for family in FAMILIES:
        family_gates = {name: entry["passed"] for name, entry in sorted(gates.items())
                        if name.startswith(family + "_")}
        families[family] = {"gates": family_gates,
                            "all_passed": all(family_gates.values())}
    if any(entry["passed"] is False and entry["actual"] is None for entry in gates.values()):
        status = "EVIDENCE_INCOMPLETE"
    elif all(entry["passed"] for entry in gates.values()):
        status = "PASS"
    else:
        status = "FAIL"
    return {"schema": ADJUDICATION["schema"], "status": status,
            "claim_scope": ADJUDICATION["claim_scope"],
            "status_vocabulary": ADJUDICATION["status_vocabulary"],
            "metric_definitions": METRIC_DEFINITIONS,
            "initial_vs_trained": initial_vs_trained,
            "families": families,
            "overall_verdict_is_conjunction": ("PASS/FAIL applies to the combined campaign; "
                                               "per-family gate rows are reported separately and "
                                               "are never erased by the combined verdict"),
            "pre_run_amendment": ("per-bit gates require > 0.5 (binary chance), never > 0.25; "
                                  "trained-beats-untrained gates added; bound by "
                                  "OWNER_METRIC_AMENDMENT.json before any run"),
            "gates": gates, "not_claimed": ADJUDICATION["not_claimed"]}


def run(output, dataset, config=None):
    """Run only on the separately admitted CUDA worker; writes a fresh directory.

    Selection: validation macro accuracy, then lower CE, then earliest epoch.
    The candidate pool is epochs 1..100; epoch zero is a separate baseline.
    Before the sealed boundary the learner reads only train.json and
    validation.json: private test targets are never read or hashed. Blind test
    predictions are saved first, and private targets are opened only afterwards
    by the evaluation stage. The embedded adjudicator returns
    EVIDENCE_INCOMPLETE until the outer provider receipt re-adjudicates.
    """
    cfg = validate_config(config)
    guard = execution_guard()  # must precede heavy imports and output creation
    from . import data
    from .bundle import read_partitions
    initial_data = read_partitions(dataset, ("train.json", "validation.json"))
    manifest_sha = initial_data["manifest_sha256"]
    train_tasks = initial_data["partitions"]["train.json"]
    validation_tasks = initial_data["partitions"]["validation.json"]
    require(len(train_tasks) == 1536 and len(validation_tasks) == 384, "FIXED_PARTITION_COUNTS")
    writer = _Writer(output, cfg["max_output_bytes"])
    started = time.monotonic()
    progress = {"status": "FAILED", "selection_sealed": False,
                "test_public_parsed": False, "test_targets_parsed": False,
                "training_steps": {name: 0 for name in FAMILIES}}

    def deadline():
        require(time.monotonic() - started < cfg["max_seconds"], "WALL_TIME_LIMIT")

    try:
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
            os.environ[name] = "1"
        sys.dont_write_bytecode = True
        meta1 = ROOT.parent / "CAS_META_1_LEARNED_SELECTION"
        require(meta1.is_dir(), "FROZEN_BASELINE_CHECKER_MISSING")
        if str(meta1) not in sys.path:
            sys.path.insert(0, str(meta1))
        from cas_meta1.baseline import verify_baseline, verify_installed_wheels

        def source_identity():
            return {"baseline": verify_baseline(), "installed_wheels": verify_installed_wheels(),
                    "candidate_sources": {name: sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                                          for name in ("train.py", "data.py", "bundle.py")}}

        source_before = source_identity()
        import torch
        from torch import nn
        from torch.nn import functional as F
        from casformer import CASControl, CASformerConfig
        from cas_cjt.network import CJTNodeSpec, NeuralCJTNetwork, TopologyEdge
        require(torch.cuda.is_available(), "CUDA_REQUIRED_NO_CPU_FALLBACK")
        require(torch.cuda.device_count() == 1, "EXACTLY_ONE_VISIBLE_GPU_REQUIRED")
        device = torch.device("cuda:0")
        gpu_name = torch.cuda.get_device_name(device)
        require("T4" not in gpu_name.upper(), "T4_NOT_ADMITTED")
        torch.set_num_threads(1)
        torch.manual_seed(cfg["model_seed"])
        torch.cuda.manual_seed_all(cfg["model_seed"])
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        deadline()

        model_config = CASformerConfig(**MODEL_CONFIG)
        # NEW CUDA-seeded candidate, not byte-identical CPU-seeded fixture weights.
        with torch.device(device):
            network = NeuralCJTNetwork(model_config,
                [CJTNodeSpec(name, "^6") for name in ("A", "B", "C", "R")],
                topology=[TopologyEdge(a, b) for a, b in (("A", "B"), ("B", "C"), ("C", "R"), ("R", "C"))])
        native_allowlist = network.parameter_names_for_node("C")
        allowed = tuple("node." + name.removeprefix("cells.node_0002.") for name in native_allowlist)
        template = deepcopy(network.node("C"))
        del network

        class Candidate(nn.Module):
            def __init__(self, family):
                super().__init__()
                self.family, self.node = family, deepcopy(template)
                for name, parameter in self.named_parameters():
                    parameter.requires_grad_(name in allowed)

            def forward(self, x):
                require(x.device == device and x.dtype == torch.float32 and
                        tuple(x.shape[1:]) == (2, 4), "CUDA_INPUT_SHAPE_REQUIRED")
                if self.family == "cas":
                    control = CASControl.uniform(x, num_heads=2, relation_id=0,
                        profile_id="CONDITION_SKILL_V9_STATELESS_LESSON",
                        provenance="offline_public_uniform_not_runtime_governed",
                        drive_provenance="fixed_one_not_teacher_feedback",
                        resistance_provenance="four_fixed_quarters_not_teacher_feedback")
                    effect = self.node(x, control, operation_id="^6").candidate_effect
                else:
                    # Matched frozen LN/Q/K/V/output projections and learned ^6;
                    # standard softmax attention replaces CAS current/gate/tanh.
                    attention = self.node.engine.attention
                    normal = self.node.engine.input_norm(x)
                    def split(value):
                        return value.reshape(value.shape[0], 2, 2, 2).transpose(1, 2)
                    q, k, v = [split(project(normal)) for project in
                               (attention.q_proj, attention.k_proj, attention.v_proj)]
                    weights = torch.softmax(torch.matmul(q, k.transpose(-2, -1)) / (2 ** 0.5), dim=-1)
                    merged = torch.matmul(weights, v).transpose(1, 2).contiguous().reshape(x.shape[0], 2, 4)
                    projected = attention.out_proj(merged)
                    effect = self.node.operations("^6", projected)
                require(bool(torch.isfinite(effect).all().item()), "NONFINITE_CANDIDATE_EFFECT")
                logits = effect.mean(dim=1)
                no_effect = (effect == 0).all(dim=2).all(dim=1)
                return logits, no_effect

        models = {name: Candidate(name) for name in FAMILIES}
        audits = {name: {"module_entries": 0, "model_forwards": 0} for name in FAMILIES}
        hooks = []
        for family, model in models.items():
            for module_name, module in model.named_modules():
                def audit(module, args, family=family, module_name=module_name):
                    audits[family]["module_entries"] += 1
                    if not module_name:
                        audits[family]["model_forwards"] += 1
                    for item in (*module.parameters(recurse=False), *module.buffers(recurse=False)):
                        require(item.device == device, "NONCUDA_MODEL_STORAGE")
                    for item in args:
                        if isinstance(item, torch.Tensor):
                            require(item.device == device, "NONCUDA_MODULE_INPUT")
                    return None
                hooks.append(module.register_forward_pre_hook(audit))

        def state_identity(state):
            result = {}
            for name, tensor in sorted(state.items()):
                require(tensor.device == device, "NONCUDA_CHECKPOINT_STORAGE")
                # CUDA tensor operations; host transfer is serialization only.
                raw = bytes(tensor.detach().contiguous().view(torch.uint8).reshape(-1).tolist())
                result[name] = {"dtype": str(tensor.dtype), "shape": list(tensor.shape),
                                "sha256": sha256(raw).hexdigest()}
            return {"tensors": result, "sha256": sha256(encoded(result)).hexdigest()}

        def save_checkpoint(name, state):
            buffer = io.BytesIO()
            torch.save(state, buffer)
            raw = buffer.getvalue()
            receipt = writer.write(name, raw)
            loaded = torch.load(io.BytesIO(raw), map_location=device, weights_only=True)
            identity = state_identity(state)
            require(state_identity(loaded) == identity, "CHECKPOINT_SERIALIZATION_ROUNDTRIP_MISMATCH")
            return {**receipt, "state_identity": identity,
                    "serialization_roundtrip_equal": True, "native_restart_proved": False}

        initial_states = {name: deepcopy(model.state_dict()) for name, model in models.items()}
        initial_id = state_identity(initial_states["cas"])
        require(state_identity(initial_states["generic_attention"]) == initial_id, "INITIAL_CONTROL_WEIGHTS_DIFFER")
        counts = {}
        for family, model in models.items():
            trainable = {name: p.numel() for name, p in model.named_parameters() if p.requires_grad}
            require(tuple(sorted(trainable)) == tuple(sorted(allowed)) and sum(trainable.values()) == 64,
                    "EXACT_COMPLETE_OPERATION_GROUP_64_REQUIRED")
            counts[family] = {"trainable": trainable, "trainable_count": sum(trainable.values()),
                              "registered_parameter_count": sum(p.numel() for p in model.parameters()),
                              "inactive_registered_modules_present": family == "generic_attention"}
        matching = {"initial_state_identical": True, "counts": counts,
            "frozen_network_operation_allowlist": list(native_allowlist),
            "candidate_operation_allowlist": list(allowed),
            "matching": "same CUDA-seeded C-node state, input LayerNorm, Q/K/V/output projection, 64-parameter ^6 transform, optimizer and permutations",
            "generic_active_modules": ["input_norm", "attention.q_proj", "attention.k_proj", "attention.v_proj", "attention.out_proj", "operations.^6"],
            "differences": "generic uses standard scaled-dot-product softmax; no CAS current/region gate or effect tanh; neither arm uses residual/FFN output",
            "uniform_controls": "unit drive/readiness/region, four resistance quarters, all paths permitted, relation 0, zero Bias per independent lesson",
            "not_matched": ["active module count", "FLOPs", "CAS gate/tanh computation"],
            "routing_limit": "uniform CAS controls provide no task-dependent routing-control comparison",
            "initialization": "NEW direct-CUDA seed-7 fixture-shaped candidate, NOT accepted fixture checkpoint bytes"}
        writer.json("config.json", {"schema": SCHEMA, "config": cfg, "model_config": asdict(model_config),
                    "manifest_sha256": manifest_sha, "source": source_before, "execution_guard": guard,
                    "gpu": gpu_name, "torch": str(torch.__version__), "cuda": str(torch.version.cuda),
                    "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                    "matching": matching, "claims": CLAIMS})
        initial_checkpoints = {family: save_checkpoint(family + ".initial.pt", state)
                               for family, state in initial_states.items()}

        def inputs(publics):
            return torch.tensor([data.features(public) for public in publics], dtype=torch.float32, device=device)

        def predict(model, publics):
            result = []
            model.eval()
            with torch.no_grad():
                for start in range(0, len(publics), cfg["batch_size"]):
                    deadline()
                    batch = publics[start:start + cfg["batch_size"]]
                    logits, no_effect = model(inputs(batch))
                    predictions = torch.where(no_effect, -torch.ones_like(logits.argmax(-1)), logits.argmax(-1))
                    for public, values, prediction in zip(batch, logits.tolist(), predictions.tolist()):
                        result.append({"task_id": public["task_id"], "logits": values,
                                       "prediction": prediction,
                                       "symbol": "NO_EFFECT" if prediction < 0 else "L" + str(prediction)})
            return result

        def score(predictions, targets, publics=None):
            require(len(predictions) == len(targets) and bool(targets), "SCORE_LENGTH")
            if publics is not None:
                require(len(publics) == len(targets), "SCORE_PUBLIC_LENGTH")
            result = []
            for start in range(0, len(predictions), cfg["batch_size"]):
                deadline()
                rows, gold = predictions[start:start + cfg["batch_size"]], targets[start:start + cfg["batch_size"]]
                logits = torch.tensor([row["logits"] for row in rows], dtype=torch.float32, device=device)
                labels = torch.tensor(gold, dtype=torch.long, device=device)
                losses = F.cross_entropy(logits, labels, reduction="none").tolist()
                for row, target, loss in zip(rows, gold, losses):
                    result.append({**row, "target": target, "negative_log_likelihood": loss,
                                   "correct": row["prediction"] == target})
            if publics is not None:
                for row, public in zip(result, publics):
                    row.update(data.condition_margins(public))
            return result

        train_publics = [task["public"] for task in train_tasks]
        train_targets = [task["target"]["class_index"] for task in train_tasks]
        validation_publics = [task["public"] for task in validation_tasks]
        validation_targets = [task["target"]["class_index"] for task in validation_tasks]
        x_train = inputs(train_publics)
        y_train = torch.tensor(train_targets, dtype=torch.long, device=device)
        histories, best_states, selections = {}, {}, {}
        permutation_digests = {}
        for family in FAMILIES:
            model = models[family]
            parameters = [p for p in model.parameters() if p.requires_grad]
            optimizer = torch.optim.AdamW(parameters, lr=cfg["learning_rate"], weight_decay=cfg["weight_decay"],
                                          foreach=False, capturable=True)
            generator = torch.Generator(device=device).manual_seed(cfg["shuffle_seed"])
            histories[family] = []
            permutation_hash = sha256()
            best_key = None
            for epoch in range(1, cfg["epochs"] + 1):
                deadline()
                model.train()
                order = torch.randperm(len(train_tasks), generator=generator, device=device)
                permutation_hash.update(encoded(order.tolist()))
                losses = []
                for start in range(0, len(train_tasks), cfg["batch_size"]):
                    deadline()
                    indices = order[start:start + cfg["batch_size"]]
                    optimizer.zero_grad(set_to_none=True)
                    logits, _ = model(x_train[indices])
                    loss = F.cross_entropy(logits, y_train[indices])
                    require(bool(torch.isfinite(loss).item()), "NONFINITE_TRAINING_LOSS")
                    loss.backward()
                    require(all(p.grad is not None and p.grad.device == device and
                                bool(torch.isfinite(p.grad).all().item()) for p in parameters), "MISSING_OR_NONFINITE_OPERATION_GRADIENT")
                    optimizer.step()
                    progress["training_steps"][family] += 1
                    losses.append(float(loss.item()))
                measured = summarize(score(predict(model, validation_publics), validation_targets))
                key = (measured["macro_accuracy"], -measured["cross_entropy"])
                if best_key is None or key > best_key:
                    best_key = key
                    best_states[family] = deepcopy(model.state_dict())
                    selections[family] = {"epoch": epoch, "validation": measured}
                histories[family].append({"epoch": epoch, "steps": progress["training_steps"][family],
                                          "mean_train_loss": sum(losses) / len(losses),
                                          "validation_macro_accuracy": measured["macro_accuracy"],
                                          "validation_cross_entropy": measured["cross_entropy"]})
            permutation_digests[family] = permutation_hash.hexdigest()
            require(progress["training_steps"][family] == 2400, "FIXED_STEP_COUNT_NOT_COMPLETED")
            del optimizer
        require(len(set(permutation_digests.values())) == 1, "UNMATCHED_TRAINING_PERMUTATIONS")

        selected_checkpoints = {}
        for family in FAMILIES:
            model = models[family]
            current_id = state_identity(model.state_dict())
            selected_id = state_identity(best_states[family])
            for name, entry in initial_id["tensors"].items():
                if name not in allowed:
                    require(current_id["tensors"][name] == entry and selected_id["tensors"][name] == entry,
                            "FROZEN_PARAMETERS_OR_BUFFERS_CHANGED:" + name)
            selections[family]["operation_weights_changed"] = any(selected_id["tensors"][name] != initial_id["tensors"][name] for name in allowed)
            selected_checkpoints[family] = save_checkpoint(family + ".selected.pt", best_states[family])
        writer.json("training_history.json", histories)
        deadline()
        selection_receipt = writer.json("selection.json", {
            "schema": SCHEMA, "manifest_sha256": manifest_sha,
            "config_sha256": writer.files["config.json"]["sha256"],
            "selection_rule": "max validation macro accuracy, then min CE, earliest exact tie",
            "candidate_epochs": [1, 100], "initial_epoch_zero_in_candidate_pool": False,
            "selected": selections, "checkpoints": selected_checkpoints,
            "initial_checkpoints": initial_checkpoints, "training_steps": progress["training_steps"],
            "permutation_sha256": permutation_digests,
            "test_public_parsed": False, "test_targets_parsed": False, "claims": CLAIMS})
        progress["selection_sealed"] = True

        # No private targets or test oracle calls above this boundary. The
        # learner has read only train/validation partitions so far.
        public_bundle = read_partitions(dataset, tuple(split + ".public.json" for split in TEST_SPLITS),
                                        expected_manifest_sha256=manifest_sha)
        progress["test_public_parsed"] = True
        test_publics = {split: public_bundle["partitions"][split + ".public.json"] for split in TEST_SPLITS}
        predictions = {}
        for family in FAMILIES:
            for stage, states in (("untrained", initial_states), ("trained", best_states)):
                key = family + "." + stage
                models[family].load_state_dict(states[family], strict=True)
                predictions[key] = {split: predict(models[family], test_publics[split]) for split in TEST_SPLITS}
        blind_receipt = writer.json("test_predictions_blind.json", {
            "selection_sha256": selection_receipt["sha256"], "manifest_sha256": manifest_sha,
            "test_targets_parsed": False, "predictions": predictions})
        target_bundle = read_partitions(dataset, tuple(split + ".targets.json" for split in TEST_SPLITS),
                                        expected_manifest_sha256=manifest_sha)
        progress["test_targets_parsed"] = True
        test_targets = {}
        for split in TEST_SPLITS:
            rows = target_bundle["partitions"][split + ".targets.json"]
            require([row["task_id"] for row in rows] == [p["task_id"] for p in test_publics[split]], "PRIVATE_PUBLIC_ID_ORDER_MISMATCH")
            require(all(row["target"] == data.oracle(public) for row, public in zip(rows, test_publics[split])),
                    "POST_SELECTION_ORACLE_DISAGREES_WITH_PRIVATE_TARGET")
            test_targets[split] = [row["target"]["class_index"] for row in rows]

        probe_indices = []
        for label in range(4):
            probe_indices.extend([i for i, target in enumerate(train_targets) if target == label][:32])
        probe_publics = [train_publics[i] for i in probe_indices]
        probe_targets = [train_targets[i] for i in probe_indices]
        summaries, control_summaries = {}, {}
        for family in FAMILIES:
            for stage, states in (("untrained", initial_states), ("trained", best_states)):
                key, model = family + "." + stage, models[family]
                model.load_state_dict(states[family], strict=True)
                scored = {split: score(predictions[key][split], test_targets[split], test_publics[split])
                          for split in TEST_SPLITS}
                scored["train_probe"] = score(predict(model, probe_publics), probe_targets, probe_publics)
                scored["validation"] = score(predict(model, validation_publics), validation_targets, validation_publics)
                writer.json(key + ".predictions.json", scored)
                summaries[key] = {split: summarize(rows) for split, rows in scored.items()}
                control_rows = []
                control_summaries[key] = {}
                for split in TEST_SPLITS:
                    for control_name in data.controls(test_publics[split][0]):
                        variants = [data.controls(public)[control_name] for public in test_publics[split]]
                        targets = [data.oracle(public)["class_index"] for public in variants]
                        changed_rows = score(predict(model, variants), targets)
                        joint, changed_inputs, unchanged_targets = 0, 0, 0
                        for base, original, variant, row in zip(scored[split], test_publics[split], variants, changed_rows):
                            both = base["correct"] and row["correct"]
                            changed = original["task_id"] != variant["task_id"]
                            joint += both
                            changed_inputs += changed
                            unchanged_targets += base["target"] == row["target"]
                            control_rows.append({**row, "split": split, "control": control_name,
                                "original_task_id": original["task_id"], "original_target": base["target"],
                                "original_prediction": base["prediction"], "original_correct": base["correct"],
                                "joint_correct": both, "public_input_changed": changed})
                        control_summaries[key][split + "." + control_name] = {
                            "cases": len(variants), "joint_correct": joint, "joint_accuracy": joint / len(variants),
                            "variant_correct": sum(row["correct"] for row in changed_rows),
                            "original_correct": sum(row["correct"] for row in scored[split]),
                            "changed_inputs": changed_inputs, "unchanged_targets": unchanged_targets,
                            "success_rule": "both original and variant individually correct; invariance alone is insufficient"}
                writer.json(key + ".controls.json", control_rows)

        majority = max(range(4), key=lambda label: (train_targets.count(label), -label))
        baseline_summaries = {}
        for split, publics, targets in [("train_probe", probe_publics, probe_targets),
                                       ("validation", validation_publics, validation_targets),
                                       *[(name, test_publics[name], test_targets[name]) for name in TEST_SPLITS]]:
            rows = [{"task_id": public["task_id"], "target": target,
                     "oracle": data.oracle(public)["class_index"], "constant": majority}
                    for public, target in zip(publics, targets)]
            writer.json(split + ".baselines.json", rows)
            baseline_summaries[split] = {"cases": len(rows), "oracle_correct": sum(row["oracle"] == row["target"] for row in rows),
                                        "constant_class": majority, "constant_correct": sum(row["constant"] == row["target"] for row in rows),
                                        "constant_selection": "training-only majority, lowest-index tie"}
        source_after = source_identity()
        require(source_after == source_before, "SOURCE_BYTES_CHANGED_DURING_RUN")
        # The manifest and training partition stay pinned after the final score;
        # private target partitions were pinned immediately before parsing.
        read_partitions(dataset, ("train.json",), expected_manifest_sha256=manifest_sha)
        for family, model in models.items():
            require(state_identity(model.state_dict()) == state_identity(best_states[family]), "INFERENCE_MUTATED_SELECTED_STATE")
        torch.cuda.synchronize(device)
        deadline()
        progress["status"] = "COMPLETED_OFFLINE_CANDIDATE_EXPERIMENT"
        report = {"schema": SCHEMA, **progress, "elapsed_seconds": time.monotonic() - started,
                  "manifest_sha256": manifest_sha, "selection_sha256": selection_receipt["sha256"],
                  "blind_prediction_sha256": blind_receipt["sha256"], "selected": selections,
                  "metrics": summaries, "controls": control_summaries, "baselines": baseline_summaries,
                  "matching": matching, "cuda_forward_audit": audits,
                  "source_before": source_before, "source_after": source_after,
                  "claims": CLAIMS, "files": dict(writer.files), "output_bytes_before_result": writer.used}
        # Trainer-side verdict is EVIDENCE_INCOMPLETE by design: the independent
        # outer provider receipt must re-adjudicate with its attestation.
        report["adjudication"] = adjudicate(report)
        writer.json("result.json", report, final=True)
        return report
    except Exception as error:
        writer.json("result.json", {"schema": SCHEMA, **progress,
                    "elapsed_seconds": time.monotonic() - started,
                    "exception_type": type(error).__name__, "exception": str(error)[:2000],
                    "manifest_sha256": manifest_sha, "claims": CLAIMS, "files": dict(writer.files)}, final=True)
        raise


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--dataset", required=True)
    arguments = parser.parse_args()
    report = run(arguments.output, arguments.dataset)
    print(json.dumps({"status": report["status"], "selection_sealed": report["selection_sealed"]}))


if __name__ == "__main__":
    main()
