"""Frozen learned model interface, with and without the current CAS repair path.

Owner task SEED18-INTERFACE-IMPLEMENT-02 (slice 1, 2026-09-27) and Codex packet
CONT19-IMPLEMENT-01 coordination / B1-SEED18-IMPLEMENT-02 (slice 2, comment 5856489964).

Implemented, no model needed:
- typed validation of identities, admission bindings, budgets, work accounts and records;
- public-record validation by an explicit permitted-field table with typed formats and provenance. There is no
  free-text field anywhere: every string is a digest, an enumerated value, a UTC stamp, a structured reference or
  a structured identifier, so a prediction body of any length cannot be placed in a public record;
- an append-only ledger that enforces "the original prediction is recorded before any repair";
- the no-repair path (``NONE``) that preserves the original prediction unchanged;
- item, order, evaluator and budget parity checks that return work totals and no verdict;
- ``admit_frozen_model`` up to its CPU-dry boundary: identity and admission checks, checkpoint path, size and
  SHA-256 checks, the CUDA-only device rule, and the requirement that the venue supplies the restore dependencies.
  The restore itself and ``predict`` are GPU-dependent and remain EXPLICITLY UNACCEPTED until the admitted venue
  runs them: this module never imports torch or the learner; the venue injects them;
- ``FrozenModelHandle``: a predict-only wrapper around a separately restored clone; ``stage_batch``,
  ``train_sealed_batch`` and ``export_checkpoint`` are refusals;
- ``predict_raw``: charge the budget, call the handle once under the venue's RNG guard, store the body privately,
  then append the public record.

Still unimplemented, each with its exact reason in ``NOT_IMPLEMENTED_REASONS``: ``repair_cas_closed_loop`` (no
native operation consumes a learned prediction; see README) and ``evaluate`` (needs the admitted evaluator; this
module never reads an answer key).

Confirmed learner API (Codex, source inspection of ``c45f775f``, file sha256 ``0f424d86…``):
``PointerCourseLearner.restore_checkpoint(torch, framework, encoder, *, path, expected_sha256,
expected_run_identity_digest, device, expected_learnable_names=None)``; ``framework`` must be a freshly built
pointer framework, not preloaded with container weights; ``encoder`` must be the frozen typed encoder;
``predict(packet, depth)`` with depth exactly 8; it calls ``module.eval()`` and increments inference counters, so
prediction runs on a separate restored clone and all global RNG is preserved around each call.

Separate contract, not implied here: the SI ``TrustedHost`` at ``d7808d59`` has a ``checkpoint=None`` engineering
contract and does not admit neural parents. ``admit_frozen_model`` takes an ``AdmissionBinding``, never a host.

This module imports only the standard library. The only file it ever opens is the checkpoint named by an
admitted identity, to hash it; it never opens a private body or an answer key.
"""

from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import time

INTERFACE_SCHEMA = "cas.seed18.frozen-model-interface/0.3"
PREDICTION_RECORD_SCHEMA = "cas.seed18.prediction-record/0.1"
SYSTEM_OUTPUT_RECORD_SCHEMA = "cas.seed18.system-output-record/0.1"
WORK_ACCOUNT_SCHEMA = "cas.seed18.work-account/0.1"
ADMISSION_BINDING_SCHEMA = "cas.seed18.admission-binding/0.1"
LEDGER_SCHEMA = "cas.seed18.record-ledger/0.1"
PARITY_TOTALS_SCHEMA = "cas.seed18.parity-totals/0.1"

SCIENTIFIC_SOURCE = "c45f775f225dd06cc20cdf313f0a0398486e0d61"
LEARNER_SOURCE_FILE_SHA256 = "0f424d8633f01b69d7ed256a8e687a4ba0f99be71ae85732c50d4c8dcd7a81a8"
CAS_SOURCE = "7bbf1e0f7bae635126c05b3203cca706ea8654dc"
JOINT_SOURCE = "d7808d59c13ea94c6ff35d2327a4acb8535daabc"
NATIVE_RUNTIME = "8182ad52b4468f18f140837dffee0e7debcfe786"
PARENT_CHECKPOINT_SHA256 = "5a8a306911bbe50b7d65e13227e8d4acfbaac871f2eb2b0ae0c0f5bb1b6e7341"
PARENT_CHECKPOINT_BYTES = 4025999
PARENT_CURSOR = 2940

PREDICT_DEPTH = 8
RESTORE_SIGNATURE = ("PointerCourseLearner.restore_checkpoint(torch, framework, encoder, *, path, expected_sha256, "
                     "expected_run_identity_digest, device, expected_learnable_names=None)")
PREDICT_SIGNATURE = "PointerCourseLearner.predict(packet, depth) with depth == 8"
FORBIDDEN_HANDLE_ATTRIBUTES = ("stage_batch", "train_sealed_batch", "export_checkpoint")
UNACCEPTED_GPU_OPERATIONS = ("restore_checkpoint", "predict")
SI_HOST_NEURAL_PARENT_CONTRACT = ("SEPARATE: the SI TrustedHost at d7808d59 has a checkpoint=None engineering "
                                  "contract and does not admit neural parents; this interface never passes a host")

REPAIR_PATHS = ("NONE", "CAS_CLOSED_LOOP")
PANELS = ("course", "held_back", "trained", "excluded", "development")
DEVICE_CLASS_REQUIRED = "cuda"
PROVENANCE_VALUES = ("HELM_ADMITTED_RUN", "CLAUDE_TEST_DOUBLE_NOT_A_HELM_RUN")
ADMITTING_AUTHORITIES = ("CODEX_RUNNER_ADMISSION", "OWNER_SIGNED_ADMISSION")
EMPTY_WORK_DIGEST = hashlib.sha256(b"{}").hexdigest()

NOT_IMPLEMENTED_REASONS = {
    "repair_cas_closed_loop": "NOT_IMPLEMENTED_MISSING_NATIVE_OPERATION_FOR_LEARNED_PREDICTION",
    "evaluate": "NOT_IMPLEMENTED_REQUIRES_ADMITTED_EVALUATOR",
}

# Every refusal this module can raise. A refusal is a named ValueError; nothing is silently downgraded.
REFUSALS = (
    "FROZEN_MODEL_SHA_MISMATCH", "FROZEN_MODEL_BYTES_MISMATCH", "FROZEN_MODEL_CURSOR_MISMATCH",
    "FROZEN_MODEL_MISMATCH", "CHECKPOINT_PATH_INVALID", "GPU_REQUIRED", "RESTORE_DEPENDENCIES_NOT_SUPPLIED",
    "TRAINING_ENTRY_POINT_FORBIDDEN",
    "IDENTITY_FIELD_INVALID", "AUTHORIZATION_NOT_PROVEN", "PROVENANCE_INVALID",
    "RECORD_TYPE_INVALID", "RECORD_SCHEMA_INVALID",
    "PUBLIC_FIELD_NOT_PERMITTED", "PUBLIC_FIELD_FORMAT_INVALID", "PREDICTION_BODY_IN_PUBLIC_RECORD",
    "PREDICTION_BUDGET_EXHAUSTED", "NATIVE_BUDGET_EXHAUSTED", "EVALUATOR_BUDGET_EXHAUSTED", "BUDGET_MISMATCH",
    "LEDGER_SEQUENCE_MISMATCH", "PREDICTION_NOT_RECORDED_BEFORE_REPAIR", "PREDICTION_NOT_PRESERVED",
    "PREDICTION_OUTPUT_INVALID", "PRIVATE_STORE_RECEIPT_INVALID",
    "OUTPUT_PREDICTION_LINK_BROKEN", "REPAIR_PATH_UNKNOWN", "REPAIR_PATH_MISMATCH",
    "EVALUATOR_MISMATCH", "ITEM_ORDER_MISMATCH", "NATIVE_RECEIPT_MISSING", "WORK_ACCOUNT_INCOMPLETE",
)


class InterfaceRefused(ValueError):
    """A named refusal. ``code`` is always one of ``REFUSALS``."""

    def __init__(self, code, detail=""):
        if code not in REFUSALS:
            raise ValueError("UNKNOWN_REFUSAL_CODE:" + str(code))
        self.code = code
        self.detail = detail
        super().__init__(code + (": " + detail if detail else ""))


def _refuse(code, detail=""):
    raise InterfaceRefused(code, detail)


# ----------------------------------------------------------------------------------------------------------
# Records. All frozen: once built they cannot be changed; a "changed" record is a different object.
# ----------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class FrozenModelIdentity:
    """Exactly one checkpoint. Every field is required."""
    checkpoint_sha256: str
    checkpoint_bytes: int
    cursor: int
    model_revision: int
    model_state_identity: str
    optimizer_state_identity: str
    encoder_state_identity: str
    rng_state_identity: str
    run_identity_digest: str
    scientific_source: str = SCIENTIFIC_SOURCE
    device_class: str = DEVICE_CLASS_REQUIRED


@dataclass(frozen=True)
class AdmissionBinding:
    """Who admitted this identity for prediction, and under which reference. A digest alone never admits."""
    schema: str
    identity_digest: str
    admitted_by: str
    admission_ref: str
    admitted_utc: str
    provenance: str


@dataclass(frozen=True)
class EvaluatorIdentity:
    """The same evaluator judges both paths. Only digests appear here; no answer key is ever read."""
    evaluator_sha256: str
    answer_key_sha256: str
    panel: str


@dataclass(frozen=True)
class EpisodeBudget:
    """Shared by both paths in one episode. Equality is checked, never assumed."""
    prediction_calls_max: int
    native_calls_max_per_item: int
    evaluator_calls_max: int
    wall_seconds_max: int


@dataclass(frozen=True)
class ItemRef:
    """One question. The inputs digest binds the exact packet bytes; the body stays in the private store."""
    item_id: str
    inputs_sha256: str
    panel: str
    depth: int
    sequence: int


@dataclass(frozen=True)
class PredictionRecord:
    """The raw prediction, written BEFORE any repair path runs and never changed afterwards.

    ``raw_output_sha256`` and ``raw_output_bytes`` are public. The body lives only behind ``private_body_ref``.
    """
    schema: str
    model: FrozenModelIdentity
    item: ItemRef
    raw_output_sha256: str
    raw_output_bytes: int
    private_body_ref: str
    device_name: str
    torch_version: str
    produced_utc: str
    prediction_sequence: int
    provenance: str


@dataclass(frozen=True)
class WorkAccount:
    """Every unit of work spent to turn one prediction into one system output, on either path."""
    schema: str
    prediction_calls: int
    native_calls_allocated: int
    native_calls_executed: int
    charged_native_policy_units_sha256: str
    actual_primitive_work_sha256: str
    evaluator_calls: int
    controller_wall_ns: int
    verification_wall_ns: int


@dataclass(frozen=True)
class SystemOutputRecord:
    """The checked system answer for one item on one path. Links to its prediction by digest; never replaces it."""
    schema: str
    repair_path: str
    prediction_sha256: str
    item: ItemRef
    native_receipt_sha256: str | None
    verified_output_sha256: str
    checked_effect: bool | None
    work: WorkAccount
    produced_utc: str
    output_sequence: int
    provenance: str


@dataclass(frozen=True)
class PrivateBodyReceipt:
    """What the venue's private store returns after it has written a raw prediction body. The body itself never
    passes back through this interface; only its reference, digest and size do."""
    ref: str
    sha256: str
    nbytes: int


# ----------------------------------------------------------------------------------------------------------
# Public-record validation: explicit permitted fields, typed formats, provenance. No free-text field exists.
# ----------------------------------------------------------------------------------------------------------

_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")
_HEX40 = re.compile(r"\A[0-9a-f]{40}\Z")
_UTC = re.compile(r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z\Z")
_PRIVATE_REF = re.compile(r"\Aprivate://[a-z0-9-]{1,64}/[0-9a-f]{64}\Z")
_CUDA_DEVICE = re.compile(r"\Acuda(:\d{1,2})?\Z")
# Structured identifiers: a real form, or the exact labeled test-double form. Neither admits free text.
_DEVICE_NAME = re.compile(r"\A(cuda:\d{1,2}|test-double-no-device)\Z")
_TORCH_VERSION = re.compile(r"\A(\d{1,3}\.\d{1,3}\.\d{1,3}(\+cu\d{2,3})?|test-double-no-torch)\Z")
_ITEM_ID = re.compile(r"\A((course|held_back|trained|excluded|development):[0-9a-f]{8,64}|double-item-\d{1,6})\Z")
_ADMISSION_REF = re.compile(r"\A(admission://(codex-runner|owner-signed)/[A-Za-z0-9._-]{1,120}"
                            r"|test-double-admission-ref-\d{1,6})\Z")


def _is_int(value):
    return type(value) is int  # bool is deliberately excluded


def _matches(pattern):
    return lambda v: type(v) is str and pattern.match(v) is not None


KIND_CHECKS = {
    "hex64": _matches(_HEX64),
    "hex64_or_none": lambda v: v is None or (type(v) is str and _HEX64.match(v) is not None),
    "hex40": _matches(_HEX40),
    "utc": _matches(_UTC),
    "private_ref": _matches(_PRIVATE_REF),
    "device_name": _matches(_DEVICE_NAME),
    "torch_version": _matches(_TORCH_VERSION),
    "item_id": _matches(_ITEM_ID),
    "admission_ref": _matches(_ADMISSION_REF),
    "nonneg_int": lambda v: _is_int(v) and v >= 0,
    "pos_int": lambda v: _is_int(v) and v > 0,
    "bool_or_none": lambda v: v is None or type(v) is bool,
}

# The ONLY fields a public record may carry, with the exact format each must have. Anything else is refused.
PUBLIC_FIELD_KINDS = {
    "FrozenModelIdentity": {
        "checkpoint_sha256": "hex64", "checkpoint_bytes": "pos_int", "cursor": "nonneg_int",
        "model_revision": "nonneg_int", "model_state_identity": "hex64", "optimizer_state_identity": "hex64",
        "encoder_state_identity": "hex64", "rng_state_identity": "hex64", "run_identity_digest": "hex64",
        "scientific_source": "hex40", "device_class": ("enum", (DEVICE_CLASS_REQUIRED,)),
    },
    "AdmissionBinding": {
        "schema": ("enum", (ADMISSION_BINDING_SCHEMA,)), "identity_digest": "hex64",
        "admitted_by": ("enum", ADMITTING_AUTHORITIES), "admission_ref": "admission_ref", "admitted_utc": "utc",
        "provenance": ("enum", PROVENANCE_VALUES),
    },
    "EvaluatorIdentity": {"evaluator_sha256": "hex64", "answer_key_sha256": "hex64", "panel": ("enum", PANELS)},
    "EpisodeBudget": {
        "prediction_calls_max": "pos_int", "native_calls_max_per_item": "nonneg_int",
        "evaluator_calls_max": "nonneg_int", "wall_seconds_max": "pos_int",
    },
    "ItemRef": {
        "item_id": "item_id", "inputs_sha256": "hex64", "panel": ("enum", PANELS),
        "depth": "nonneg_int", "sequence": "pos_int",
    },
    "PredictionRecord": {
        "schema": ("enum", (PREDICTION_RECORD_SCHEMA,)), "model": ("record", "FrozenModelIdentity"),
        "item": ("record", "ItemRef"), "raw_output_sha256": "hex64", "raw_output_bytes": "pos_int",
        "private_body_ref": "private_ref", "device_name": "device_name", "torch_version": "torch_version",
        "produced_utc": "utc", "prediction_sequence": "pos_int", "provenance": ("enum", PROVENANCE_VALUES),
    },
    "WorkAccount": {
        "schema": ("enum", (WORK_ACCOUNT_SCHEMA,)), "prediction_calls": "nonneg_int",
        "native_calls_allocated": "nonneg_int", "native_calls_executed": "nonneg_int",
        "charged_native_policy_units_sha256": "hex64", "actual_primitive_work_sha256": "hex64",
        "evaluator_calls": "nonneg_int", "controller_wall_ns": "nonneg_int", "verification_wall_ns": "nonneg_int",
    },
    "SystemOutputRecord": {
        "schema": ("enum", (SYSTEM_OUTPUT_RECORD_SCHEMA,)), "repair_path": ("enum", REPAIR_PATHS),
        "prediction_sha256": "hex64", "item": ("record", "ItemRef"), "native_receipt_sha256": "hex64_or_none",
        "verified_output_sha256": "hex64", "checked_effect": "bool_or_none", "work": ("record", "WorkAccount"),
        "produced_utc": "utc", "output_sequence": "pos_int", "provenance": ("enum", PROVENANCE_VALUES),
    },
    "PrivateBodyReceipt": {"ref": "private_ref", "sha256": "hex64", "nbytes": "pos_int"},
}

SCHEMA_TO_RECORD = {
    PREDICTION_RECORD_SCHEMA: "PredictionRecord", SYSTEM_OUTPUT_RECORD_SCHEMA: "SystemOutputRecord",
    WORK_ACCOUNT_SCHEMA: "WorkAccount", ADMISSION_BINDING_SCHEMA: "AdmissionBinding",
}

# Field names that name a body, a key or a secret. Their presence in a public record is refused before any
# other check, by name alone: this module never opens the private store or an answer key to decide.
BODY_LIKE_FIELD_NAMES = frozenset({
    "raw_output", "body", "answer", "answers", "answer_key", "prediction_body", "salt", "credential",
    "credentials", "token", "secret", "private_key", "scoring_body", "content", "text", "logits",
})


def _record_name_and_items(record, expected):
    if is_dataclass(record) and not isinstance(record, type):
        name = type(record).__name__
        if name not in PUBLIC_FIELD_KINDS:
            _refuse("RECORD_TYPE_INVALID", name)
        if expected is not None and name != expected:
            _refuse("RECORD_TYPE_INVALID", "expected %s, got %s" % (expected, name))
        return name, {f.name: getattr(record, f.name) for f in fields(record)}
    if type(record) is dict:
        if expected is not None:
            schema = record.get("schema")
            if schema is not None and SCHEMA_TO_RECORD.get(schema) not in (None, expected):
                _refuse("RECORD_TYPE_INVALID", "expected %s, got schema %r" % (expected, schema))
            return expected, dict(record)
        schema = record.get("schema")
        if schema not in SCHEMA_TO_RECORD:
            _refuse("RECORD_SCHEMA_INVALID", "a dict record must carry a known schema")
        return SCHEMA_TO_RECORD[schema], dict(record)
    _refuse("RECORD_TYPE_INVALID", type(record).__name__)


def validate_record_is_public_safe(record, *, expected=None):
    """Structural check only. A public record may carry exactly its permitted fields, each in its typed format.

    Refuses, in this order: a body-like field name (``PREDICTION_BODY_IN_PUBLIC_RECORD``); any extra or missing
    field (``PUBLIC_FIELD_NOT_PERMITTED``); a provenance outside ``PROVENANCE_VALUES`` (``PROVENANCE_INVALID``);
    any value not in its declared format (``PUBLIC_FIELD_FORMAT_INVALID``). Nested records are checked the same
    way. Because no field admits free text, a prediction body of any length, short or long, cannot pass. No file
    is opened; no body, key or private value is read. Returns the record type name.
    """
    name, items = _record_name_and_items(record, expected)
    for key in items:
        if type(key) is not str:
            _refuse("PUBLIC_FIELD_NOT_PERMITTED", "non-string field name in " + name)
        if key.lower() in BODY_LIKE_FIELD_NAMES:
            _refuse("PREDICTION_BODY_IN_PUBLIC_RECORD", "%s.%s" % (name, key))
    permitted = PUBLIC_FIELD_KINDS[name]
    if set(items) != set(permitted):
        extra = sorted(set(items) - set(permitted))
        missing = sorted(set(permitted) - set(items))
        _refuse("PUBLIC_FIELD_NOT_PERMITTED", "%s: extra=%s missing=%s" % (name, extra, missing))
    for key, spec in permitted.items():
        value = items[key]
        if type(spec) is tuple and spec[0] == "enum":
            if type(value) is not str or value not in spec[1]:
                _refuse("PROVENANCE_INVALID" if key == "provenance" else "PUBLIC_FIELD_FORMAT_INVALID",
                        "%s.%s" % (name, key))
        elif type(spec) is tuple and spec[0] == "record":
            validate_record_is_public_safe(value, expected=spec[1])
        elif not KIND_CHECKS[spec](value):
            _refuse("PUBLIC_FIELD_FORMAT_INVALID", "%s.%s must be %s" % (name, key, spec))
    return name


# ----------------------------------------------------------------------------------------------------------
# Typed validators and digests
# ----------------------------------------------------------------------------------------------------------

def canonical_bytes(value):
    """Canonical JSON bytes: sorted keys, no whitespace, ASCII only. Used for every digest in this module."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def identity_digest(identity):
    """SHA-256 of the identity's canonical JSON. It names the identity; it does not authorize it."""
    if type(identity) is not FrozenModelIdentity:
        _refuse("RECORD_TYPE_INVALID", "FrozenModelIdentity required")
    return sha256_hex(canonical_bytes(asdict(identity)))


def validate_frozen_model_identity(identity):
    """Refuse a malformed identity before anything else can use it. Returns the identity digest."""
    if type(identity) is not FrozenModelIdentity:
        _refuse("RECORD_TYPE_INVALID", "FrozenModelIdentity required")
    if identity.device_class != DEVICE_CLASS_REQUIRED:
        _refuse("GPU_REQUIRED", "device_class %r; CPU inference is never a fallback" % (identity.device_class,))
    validate_record_is_public_safe(identity)
    if identity.scientific_source != SCIENTIFIC_SOURCE:
        _refuse("IDENTITY_FIELD_INVALID", "scientific_source is not the bound source " + SCIENTIFIC_SOURCE)
    return identity_digest(identity)


def validate_admission_binding(identity, admission):
    """A hash alone does not prove authorization.

    The admission must name this identity's digest AND an explicit admitting authority from
    ``ADMITTING_AUTHORITIES`` under a structured reference the admitted venue can check. This is a structural
    check: it verifies no signature, and says so in its result (``signature_verified`` is False). Refuses
    ``AUTHORIZATION_NOT_PROVEN`` for a self-issued, unknown or mismatched admission.
    """
    digest = validate_frozen_model_identity(identity)
    if type(admission) is not AdmissionBinding:
        _refuse("RECORD_TYPE_INVALID", "AdmissionBinding required")
    if admission.admitted_by not in ADMITTING_AUTHORITIES:
        _refuse("AUTHORIZATION_NOT_PROVEN",
                "admitted_by %r is not an admitting authority; a digest alone does not authorize" % (admission.admitted_by,))
    validate_record_is_public_safe(admission)
    if admission.identity_digest != digest:
        _refuse("AUTHORIZATION_NOT_PROVEN", "admission names a different identity digest")
    return {"identity_digest": digest, "admitted_by": admission.admitted_by, "admission_ref": admission.admission_ref,
            "structural_check_only": True, "signature_verified": False}


def validate_budget(budget):
    if type(budget) is not EpisodeBudget:
        _refuse("RECORD_TYPE_INVALID", "EpisodeBudget required")
    validate_record_is_public_safe(budget)
    return budget


def validate_evaluator_identity(evaluator):
    if type(evaluator) is not EvaluatorIdentity:
        _refuse("RECORD_TYPE_INVALID", "EvaluatorIdentity required")
    validate_record_is_public_safe(evaluator)
    return evaluator


def validate_item_ref(item):
    if type(item) is not ItemRef:
        _refuse("RECORD_TYPE_INVALID", "ItemRef required")
    validate_record_is_public_safe(item)
    return item


def validate_prediction_record(record):
    if type(record) is not PredictionRecord:
        _refuse("RECORD_TYPE_INVALID", "PredictionRecord required")
    validate_frozen_model_identity(record.model)
    validate_record_is_public_safe(record)
    return record


def validate_work_account(work, *, budget=None):
    """Every counted quantity present and non-negative; executed never exceeds allocated; within budget if given."""
    if type(work) is not WorkAccount:
        _refuse("RECORD_TYPE_INVALID", "WorkAccount required")
    validate_record_is_public_safe(work)
    if work.native_calls_executed > work.native_calls_allocated:
        _refuse("WORK_ACCOUNT_INCOMPLETE", "native_calls_executed exceeds native_calls_allocated")
    if budget is not None:
        validate_budget(budget)
        if work.native_calls_allocated > budget.native_calls_max_per_item:
            _refuse("NATIVE_BUDGET_EXHAUSTED", "native_calls_allocated exceeds native_calls_max_per_item")
        if work.evaluator_calls > budget.evaluator_calls_max:
            _refuse("EVALUATOR_BUDGET_EXHAUSTED", "evaluator_calls exceeds evaluator_calls_max")
    return work


def validate_system_output_record(output, *, budget=None):
    if type(output) is not SystemOutputRecord:
        _refuse("RECORD_TYPE_INVALID", "SystemOutputRecord required")
    if output.repair_path not in REPAIR_PATHS:
        _refuse("REPAIR_PATH_UNKNOWN", repr(output.repair_path))
    validate_record_is_public_safe(output)
    validate_work_account(output.work, budget=budget)
    if output.repair_path == "NONE":
        if output.native_receipt_sha256 is not None or output.work.native_calls_allocated != 0:
            _refuse("REPAIR_PATH_MISMATCH", "NONE path carries native work or a receipt")
        if output.verified_output_sha256 != output.prediction_sha256:
            _refuse("PREDICTION_NOT_PRESERVED", "NONE path changed the output digest")
    else:
        if output.native_receipt_sha256 is None:
            _refuse("NATIVE_RECEIPT_MISSING", "CAS path output without an adapter receipt digest")
    return output


def validate_private_body_receipt(receipt):
    """The store's receipt must be internally consistent: the reference must end in the body's own digest."""
    if type(receipt) is not PrivateBodyReceipt:
        _refuse("PRIVATE_STORE_RECEIPT_INVALID", "PrivateBodyReceipt required")
    try:
        validate_record_is_public_safe(receipt)
    except InterfaceRefused as refusal:
        _refuse("PRIVATE_STORE_RECEIPT_INVALID", refusal.code + ": " + refusal.detail)
    if not receipt.ref.endswith("/" + receipt.sha256):
        _refuse("PRIVATE_STORE_RECEIPT_INVALID", "reference does not end in the body digest")
    return receipt


# ----------------------------------------------------------------------------------------------------------
# Budget ledger and record ledger
# ----------------------------------------------------------------------------------------------------------

class BudgetLedger:
    """Counts what one episode path has spent against its budget. Charges refuse BEFORE the work happens."""

    def __init__(self, budget):
        validate_budget(budget)
        self.budget = budget
        self.spent = {"prediction": 0, "native": 0, "evaluator": 0}
        self.started_ns = time.monotonic_ns()

    def charge_prediction(self):
        if self.spent["prediction"] >= self.budget.prediction_calls_max:
            _refuse("PREDICTION_BUDGET_EXHAUSTED", "%d of %d prediction calls already spent"
                    % (self.spent["prediction"], self.budget.prediction_calls_max))
        self.spent["prediction"] += 1
        return self.spent["prediction"]

    def charge_evaluator(self):
        if self.spent["evaluator"] >= self.budget.evaluator_calls_max:
            _refuse("EVALUATOR_BUDGET_EXHAUSTED", "%d of %d evaluator calls already spent"
                    % (self.spent["evaluator"], self.budget.evaluator_calls_max))
        self.spent["evaluator"] += 1
        return self.spent["evaluator"]

    def snapshot(self):
        return {"budget": asdict(self.budget), "spent": dict(self.spent),
                "elapsed_ns": time.monotonic_ns() - self.started_ns}


class RecordLedger:
    """Append-only, in memory. One provenance for every row. Sequence numbers come from the ledger.

    A system output may only be appended after the prediction it links to is already a row: that is how
    "original prediction before repair" is enforced, not merely documented.
    """

    def __init__(self, provenance):
        if provenance not in PROVENANCE_VALUES:
            _refuse("PROVENANCE_INVALID", repr(provenance))
        self.provenance = provenance
        self._rows = []

    @property
    def rows(self):
        return tuple(self._rows)

    def next_sequence(self):
        return len(self._rows) + 1

    def holds_prediction(self, prediction):
        return any(type(row) is PredictionRecord and row == prediction for row in self._rows)

    def _prediction_for(self, output):
        for row in self._rows:
            if (type(row) is PredictionRecord and row.raw_output_sha256 == output.prediction_sha256
                    and row.item == output.item):
                return row
        return None

    def append(self, record):
        if type(record) is PredictionRecord:
            validate_prediction_record(record)
            sequence = record.prediction_sequence
        elif type(record) is SystemOutputRecord:
            validate_system_output_record(record)
            sequence = record.output_sequence
        else:
            _refuse("RECORD_TYPE_INVALID", "only PredictionRecord or SystemOutputRecord rows")
        if record.provenance != self.provenance:
            _refuse("PROVENANCE_INVALID", "ledger %s, record %s" % (self.provenance, record.provenance))
        if sequence != self.next_sequence():
            _refuse("LEDGER_SEQUENCE_MISMATCH", "expected %d, got %d" % (self.next_sequence(), sequence))
        if type(record) is SystemOutputRecord and self._prediction_for(record) is None:
            _refuse("PREDICTION_NOT_RECORDED_BEFORE_REPAIR", "no prediction row for " + record.prediction_sha256)
        self._rows.append(record)
        return sequence

    def digest(self):
        return sha256_hex(canonical_bytes([asdict(row) for row in self._rows]))

    def to_public(self):
        return {"schema": LEDGER_SCHEMA, "provenance": self.provenance,
                "rows": [asdict(row) for row in self._rows], "digest": self.digest()}


def record_prediction(ledger, budget_ledger, record):
    """Charge the prediction budget first (a refusal here means the learner must not be called), then append."""
    if type(ledger) is not RecordLedger or type(budget_ledger) is not BudgetLedger:
        _refuse("RECORD_TYPE_INVALID", "RecordLedger and BudgetLedger required")
    validate_prediction_record(record)
    budget_ledger.charge_prediction()
    return ledger.append(record)


def _now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# ----------------------------------------------------------------------------------------------------------
# Frozen model admission and prediction (GPU-dependent steps explicitly unaccepted until the admitted venue)
# ----------------------------------------------------------------------------------------------------------

class FrozenModelHandle:
    """A predict-only wrapper around a SEPARATELY RESTORED clone of the learner.

    The venue restores the clone for this handle alone, so the caller's own container keeps its mode and
    counters. Every ``predict`` runs inside the venue's ``rng_guard`` (a callable returning a context manager
    that snapshots and restores all global RNG: torch CPU, torch CUDA, Python ``random``). Depth is fixed at
    ``PREDICT_DEPTH``. ``stage_batch``, ``train_sealed_batch`` and ``export_checkpoint`` are refusals through
    this handle. It is a discipline boundary, not a sandbox: the underlying object is kept private by name.
    """

    def __init__(self, learner, *, identity, admission, rng_guard):
        if not callable(rng_guard):
            _refuse("RESTORE_DEPENDENCIES_NOT_SUPPLIED", "rng_guard must be a callable returning a context manager")
        self._learner = learner
        self.identity = identity
        self.admission = admission
        self._rng_guard = rng_guard
        self.predict_calls = 0

    def __getattr__(self, name):
        if name in FORBIDDEN_HANDLE_ATTRIBUTES:
            _refuse("TRAINING_ENTRY_POINT_FORBIDDEN", name + " is not reachable through a frozen-model handle")
        raise AttributeError(name)

    def predict(self, packet):
        with self._rng_guard():
            result = self._learner.predict(packet, PREDICT_DEPTH)
        self.predict_calls += 1
        return result


def admit_frozen_model(identity, admission, *, path, device, restore=None, framework_factory=None, encoder=None,
                       torch=None, rng_guard=None):
    """Admit exactly one checkpoint for prediction, refusing at the first failed step.

    Order: (1) identity and admission binding (a digest alone never admits); (2) ``path`` must be a regular file
    and not a symlink (``CHECKPOINT_PATH_INVALID``); (3) its size must equal ``identity.checkpoint_bytes``
    (``FROZEN_MODEL_BYTES_MISMATCH``, checked before any byte is read); (4) its SHA-256 must equal
    ``identity.checkpoint_sha256`` (``FROZEN_MODEL_SHA_MISMATCH``); (5) ``device`` must be a CUDA device
    (``GPU_REQUIRED``; CPU is never a fallback); (6) the venue must supply ``restore`` (the learner's
    ``restore_checkpoint`` bound method), ``framework_factory`` (builds a FRESH pointer framework, never preloaded),
    the frozen typed ``encoder``, ``torch`` and ``rng_guard`` (``RESTORE_DEPENDENCIES_NOT_SUPPLIED``).

    Step 6 is the CPU-dry boundary: without those dependencies nothing is loaded and the refusal is the result.
    With them, the restore is called exactly as ``RESTORE_SIGNATURE`` describes, the restored clone's ``cursor``
    must equal ``identity.cursor`` (``FROZEN_MODEL_CURSOR_MISMATCH``), and a predict-only handle is returned.
    The restore and every later ``predict`` are GPU-dependent and remain unaccepted until the admitted venue
    runs them. No host object is taken: ``SI_HOST_NEURAL_PARENT_CONTRACT`` stays separate.
    """
    validate_admission_binding(identity, admission)
    location = os.fspath(path)
    if os.path.islink(location) or not os.path.isfile(location):
        _refuse("CHECKPOINT_PATH_INVALID", "checkpoint must be a regular file and not a symlink")
    size = os.path.getsize(location)
    if size != identity.checkpoint_bytes:
        _refuse("FROZEN_MODEL_BYTES_MISMATCH", "file has %d bytes, identity says %d" % (size, identity.checkpoint_bytes))
    with open(location, "rb") as stream:
        digest = sha256_hex(stream.read())
    if digest != identity.checkpoint_sha256:
        _refuse("FROZEN_MODEL_SHA_MISMATCH", "file digest does not equal the admitted identity")
    if type(device) is not str or _CUDA_DEVICE.match(device) is None:
        _refuse("GPU_REQUIRED", "device %r; CPU inference is never a fallback" % (device,))
    missing = [name for name, value in (("restore", restore), ("framework_factory", framework_factory),
                                        ("encoder", encoder), ("torch", torch), ("rng_guard", rng_guard))
               if value is None or (name in ("restore", "framework_factory", "rng_guard") and not callable(value))]
    if missing:
        _refuse("RESTORE_DEPENDENCIES_NOT_SUPPLIED",
                "CPU-dry boundary: the admitted venue must supply " + ", ".join(missing))
    framework = framework_factory()
    learner = restore(torch, framework, encoder, path=location, expected_sha256=identity.checkpoint_sha256,
                      expected_run_identity_digest=identity.run_identity_digest, device=device,
                      expected_learnable_names=None)
    if getattr(learner, "cursor", None) != identity.cursor:
        _refuse("FROZEN_MODEL_CURSOR_MISMATCH", "restored cursor %r, identity cursor %d"
                % (getattr(learner, "cursor", None), identity.cursor))
    return FrozenModelHandle(learner, identity=identity, admission=admission, rng_guard=rng_guard)


def predict_raw(handle, item, packet, *, budget_ledger, ledger, private_store, device_name, torch_version):
    """Charge the budget, call the handle exactly once, store the body privately, then append the public record.

    The order is fixed and enforced by construction: a budget refusal happens before the call; the venue's
    ``private_store.put(raw)`` returns a ``PrivateBodyReceipt`` (reference, digest, size) and the body never
    passes back through this interface; the public ``PredictionRecord`` is appended last and returned. A
    ``None`` result is ``PREDICTION_OUTPUT_INVALID``. The call itself is GPU-dependent and unaccepted until the
    admitted venue runs it.
    """
    if type(handle) is not FrozenModelHandle:
        _refuse("RECORD_TYPE_INVALID", "FrozenModelHandle required")
    if type(ledger) is not RecordLedger or type(budget_ledger) is not BudgetLedger:
        _refuse("RECORD_TYPE_INVALID", "RecordLedger and BudgetLedger required")
    if private_store is None or not callable(getattr(private_store, "put", None)):
        _refuse("PRIVATE_STORE_RECEIPT_INVALID", "private_store must expose put(raw) -> PrivateBodyReceipt")
    validate_item_ref(item)
    budget_ledger.charge_prediction()
    raw = handle.predict(packet)
    if raw is None:
        _refuse("PREDICTION_OUTPUT_INVALID", "the learner returned None")
    receipt = validate_private_body_receipt(private_store.put(raw))
    record = PredictionRecord(schema=PREDICTION_RECORD_SCHEMA, model=handle.identity, item=item,
                              raw_output_sha256=receipt.sha256, raw_output_bytes=receipt.nbytes,
                              private_body_ref=receipt.ref, device_name=device_name, torch_version=torch_version,
                              produced_utc=_now_utc(), prediction_sequence=ledger.next_sequence(),
                              provenance=ledger.provenance)
    ledger.append(record)
    return record


# ----------------------------------------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------------------------------------

def repair_none(prediction, *, evaluator, budget, ledger):
    """The path WITHOUT CAS. The verified output is the raw prediction itself, by construction.

    Refuses unless the exact ``PredictionRecord`` is already a ledger row (``PREDICTION_NOT_RECORDED_BEFORE_REPAIR``).
    The ``evaluator`` is validated and recorded as the shared evaluator identity but is not called here:
    ``evaluate`` needs the admitted evaluator, so ``checked_effect`` is ``None`` and ``evaluator_calls`` is 0.
    Work: one prediction call, zero native calls, measured controller wall time.
    """
    started = time.perf_counter_ns()
    validate_prediction_record(prediction)
    validate_evaluator_identity(evaluator)
    validate_budget(budget)
    if type(ledger) is not RecordLedger:
        _refuse("RECORD_TYPE_INVALID", "RecordLedger required")
    if ledger.provenance != prediction.provenance:
        _refuse("PROVENANCE_INVALID", "ledger %s, prediction %s" % (ledger.provenance, prediction.provenance))
    if not ledger.holds_prediction(prediction):
        _refuse("PREDICTION_NOT_RECORDED_BEFORE_REPAIR", "record the prediction in the ledger before any repair path")
    work = WorkAccount(schema=WORK_ACCOUNT_SCHEMA, prediction_calls=1, native_calls_allocated=0,
                       native_calls_executed=0, charged_native_policy_units_sha256=EMPTY_WORK_DIGEST,
                       actual_primitive_work_sha256=EMPTY_WORK_DIGEST, evaluator_calls=0,
                       controller_wall_ns=max(0, time.perf_counter_ns() - started), verification_wall_ns=0)
    output = SystemOutputRecord(schema=SYSTEM_OUTPUT_RECORD_SCHEMA, repair_path="NONE",
                                prediction_sha256=prediction.raw_output_sha256, item=prediction.item,
                                native_receipt_sha256=None, verified_output_sha256=prediction.raw_output_sha256,
                                checked_effect=None, work=work, produced_utc=_now_utc(),
                                output_sequence=ledger.next_sequence(), provenance=prediction.provenance)
    ledger.append(output)
    return output


def repair_cas_closed_loop(prediction, machine, *, calls, allow_acquisition, actuator_enabled, evaluator, budget, ledger):
    """The path WITH the current CAS repair, through the existing adapter unchanged.

    Not implemented, and not faked: no operation in the closed-loop runtime consumes a learned prediction
    (``control.OPERATIONS`` at CAS ``7bbf1e0f`` names only PCBA board operations), so there is nothing real to call.
    The equation witness is not this path and is never reported as it. See README, "Next missing connection".
    """
    raise NotImplementedError(NOT_IMPLEMENTED_REASONS["repair_cas_closed_loop"])


def evaluate(output, *, evaluator, ledger):
    """Judge one system output with the shared evaluator. Not implemented: needs the admitted evaluator; this
    module never reads an answer key."""
    raise NotImplementedError(NOT_IMPLEMENTED_REASONS["evaluate"])


# ----------------------------------------------------------------------------------------------------------
# Parity: both paths were the same experiment except for the repair path
# ----------------------------------------------------------------------------------------------------------

def _pairs(path, expected_repair_path):
    pairs = []
    for entry in tuple(path):
        if type(entry) is not tuple or len(entry) != 2:
            _refuse("RECORD_TYPE_INVALID", "each path entry is a (PredictionRecord, SystemOutputRecord) pair")
        prediction, output = entry
        validate_prediction_record(prediction)
        validate_system_output_record(output)
        if output.repair_path != expected_repair_path:
            _refuse("REPAIR_PATH_MISMATCH", "expected %s, got %s" % (expected_repair_path, output.repair_path))
        if output.prediction_sha256 != prediction.raw_output_sha256 or output.item != prediction.item:
            _refuse("OUTPUT_PREDICTION_LINK_BROKEN", "output does not link to its prediction")
        if prediction.provenance != output.provenance:
            _refuse("PROVENANCE_INVALID", "prediction and output provenance differ")
        pairs.append((prediction, output))
    return pairs


def _sum_work(pairs):
    keys = ("prediction_calls", "native_calls_allocated", "native_calls_executed", "evaluator_calls",
            "controller_wall_ns", "verification_wall_ns")
    return {key: sum(getattr(output.work, key) for _, output in pairs) for key in keys}


def episode_parity_check(path_none, path_cas, *, budget_none, budget_cas, evaluator_none, evaluator_cas):
    """Refuse unless both paths saw the same items in the same order under the same evaluator and budget, with
    the same frozen model, and produced identical raw prediction digests. Returns work totals per path and
    the item count. It computes no score, applies no threshold and carries no verdict field."""
    validate_budget(budget_none)
    validate_budget(budget_cas)
    if budget_none != budget_cas:
        _refuse("BUDGET_MISMATCH", "the two paths ran under different budgets")
    validate_evaluator_identity(evaluator_none)
    validate_evaluator_identity(evaluator_cas)
    if evaluator_none != evaluator_cas:
        _refuse("EVALUATOR_MISMATCH", "the two paths were judged by different evaluators")
    pairs_none = _pairs(path_none, "NONE")
    pairs_cas = _pairs(path_cas, "CAS_CLOSED_LOOP")
    if len(pairs_none) != len(pairs_cas):
        _refuse("ITEM_ORDER_MISMATCH", "%d items on NONE, %d on CAS_CLOSED_LOOP" % (len(pairs_none), len(pairs_cas)))
    for (prediction_none, _), (prediction_cas, _) in zip(pairs_none, pairs_cas):
        if prediction_none.item != prediction_cas.item:
            _refuse("ITEM_ORDER_MISMATCH", "item %s versus %s" % (prediction_none.item.item_id, prediction_cas.item.item_id))
        if prediction_none.model != prediction_cas.model:
            _refuse("FROZEN_MODEL_MISMATCH", "the two paths used different frozen models")
        if prediction_none.raw_output_sha256 != prediction_cas.raw_output_sha256:
            _refuse("PREDICTION_NOT_PRESERVED", "item %s: raw prediction digests differ across paths"
                    % (prediction_none.item.item_id,))
    return {"schema": PARITY_TOTALS_SCHEMA, "items": len(pairs_none), "budget": asdict(budget_none),
            "evaluator": asdict(evaluator_none), "NONE": _sum_work(pairs_none),
            "CAS_CLOSED_LOOP": _sum_work(pairs_cas)}
