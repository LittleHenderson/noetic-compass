"""Callable interface contract for a frozen learned model with and without the current CAS repair path.

Packet B1-SEED18-INTERFACES-20260927-01 (source-only). This module is a CONTRACT: every operation raises
``NotImplementedError`` until a later packet implements it in a Codex-named scope. It was written without being
imported, compiled or executed (the packet forbids local imports), so its syntax is unverified until the admitted
venue collects it. It imports nothing but the standard library and never imports torch, the learner, the CAS
adapter or the SI host.

Reading guide (plain English first):
- "Frozen learned model" = one exact checkpoint file, identified by its SHA-256, that is only ever asked to
  predict. It is never trained, exported or modified through this interface.
- "Repair path" = what happens to a raw prediction before it becomes the system's answer. ``NONE`` means the raw
  prediction is the answer. ``CAS_CLOSED_LOOP`` means the existing adapter (``native_step_adapter.grant_for`` and
  ``execute_grant``, unchanged) drives the native runtime and the checked result is the answer.
- The raw prediction is written down first, in full, in the private evidence store; only its digest enters public
  records; and it is never changed by either path. The checked system output is a separate record that links to the
  prediction by digest.
- Both paths see the same items, in the same order, judged by the same evaluator, under the same budget.

Identities this contract is bound to (copied from the packet and the committed records; not re-measured here).
"""

from dataclasses import dataclass

INTERFACE_SCHEMA = "cas.seed18.frozen-model-interface/0.1"
PREDICTION_RECORD_SCHEMA = "cas.seed18.prediction-record/0.1"
SYSTEM_OUTPUT_RECORD_SCHEMA = "cas.seed18.system-output-record/0.1"
WORK_ACCOUNT_SCHEMA = "cas.seed18.work-account/0.1"

SCIENTIFIC_SOURCE = "c45f775f225dd06cc20cdf313f0a0398486e0d61"
CAS_SOURCE = "7bbf1e0f7bae635126c05b3203cca706ea8654dc"
JOINT_SOURCE = "d7808d59c13ea94c6ff35d2327a4acb8535daabc"
NATIVE_RUNTIME = "8182ad52b4468f18f140837dffee0e7debcfe786"
PARENT_CHECKPOINT_SHA256 = "5a8a306911bbe50b7d65e13227e8d4acfbaac871f2eb2b0ae0c0f5bb1b6e7341"
PARENT_CHECKPOINT_BYTES = 4025999
PARENT_CURSOR = 2940

REPAIR_PATHS = ("NONE", "CAS_CLOSED_LOOP")
PANELS = ("course", "held_back", "trained", "excluded", "development")
DEVICE_CLASS_REQUIRED = "cuda"

# Every refusal this contract can raise. A refusal is a named ValueError; nothing is silently downgraded.
REFUSALS = (
    "FROZEN_MODEL_SHA_MISMATCH",          # checkpoint bytes do not hash to the declared identity
    "FROZEN_MODEL_BYTES_MISMATCH",        # size differs from the declared identity
    "FROZEN_MODEL_CURSOR_MISMATCH",       # restored cursor differs from the declared cursor
    "GPU_REQUIRED",                       # device is not a CUDA device; no CPU inference, ever
    "TRAINING_ENTRY_POINT_FORBIDDEN",     # stage_batch / train_sealed_batch / export_checkpoint reachable
    "PREDICTION_BUDGET_EXHAUSTED",        # more prediction calls than the episode budget allows
    "PREDICTION_NOT_RECORDED_BEFORE_REPAIR",  # a repair path was entered without a persisted prediction record
    "PREDICTION_BODY_IN_PUBLIC_RECORD",   # a raw output body reached a public record; only digests may
    "PREDICTION_NOT_PRESERVED",           # the same item and model produced different digests across paths
    "REPAIR_PATH_UNKNOWN",                # not one of REPAIR_PATHS
    "EVALUATOR_MISMATCH",                 # evaluator identity differs between paths in one episode
    "BUDGET_MISMATCH",                    # budgets differ between paths in one episode
    "ITEM_ORDER_MISMATCH",                # items or their order differ between paths
    "NATIVE_RECEIPT_MISSING",             # CAS path returned without an adapter receipt
    "WORK_ACCOUNT_INCOMPLETE",            # a counted quantity is absent or negative
)


@dataclass(frozen=True)
class FrozenModelIdentity:
    """Exactly one checkpoint. All eleven fields are required; none may be None."""
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
class EvaluatorIdentity:
    """The same evaluator judges both paths. The answer key never appears here; only its digest does."""
    evaluator_sha256: str
    answer_key_sha256: str
    panel: str


@dataclass(frozen=True)
class EpisodeBudget:
    """Shared by both paths in one episode. Equality is checked, not assumed."""
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

    ``raw_output_sha256`` and ``raw_output_bytes`` are public. The raw output body itself is written to the private
    evidence store at ``private_body_ref`` (a path or object key, never the content) and is not part of any public
    record, PR, or comment.
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


@dataclass(frozen=True)
class WorkAccount:
    """Every unit of work spent to turn one prediction into one system output, on either path."""
    schema: str
    prediction_calls: int
    native_calls_allocated: int       # adapter receipt I_allocated (0 on the NONE path)
    native_calls_executed: int        # adapter receipt I_executed (0 on the NONE path)
    charged_native_policy_units_sha256: str   # digest of the receipt's charged_native_policy_units, or of "{}"
    actual_primitive_work_sha256: str         # digest of the receipt's actual_primitive_work, or of "{}"
    evaluator_calls: int
    controller_wall_ns: int
    verification_wall_ns: int


@dataclass(frozen=True)
class SystemOutputRecord:
    """The checked system answer for one item on one path. Links to its prediction by digest; never replaces it."""
    schema: str
    repair_path: str
    prediction_sha256: str            # == PredictionRecord.raw_output_sha256 it was built from
    item: ItemRef
    native_receipt_sha256: str | None  # digest of the adapter receipt (cas.closed-loop.native-step-receipt/0.1); None on NONE
    verified_output_sha256: str       # on NONE this equals prediction_sha256 by construction
    checked_effect: bool | None       # the evaluator's verdict on the verified output; None if not evaluated
    work: WorkAccount
    produced_utc: str
    output_sequence: int


def admit_frozen_model(identity, *, path, host):
    """Hash the file at ``path`` and refuse before any load unless size and SHA-256 equal ``identity``.

    Then restore through the learner's own ``restore_checkpoint`` (scientific source, unchanged) with
    ``expected_sha256`` and ``expected_run_identity_digest`` from ``identity``, on a CUDA device only, and return a
    handle whose ONLY operation is ``predict``. Reaching ``stage_batch``, ``train_sealed_batch`` or
    ``export_checkpoint`` through the handle is a refusal, not a capability. The restored cursor must equal
    ``identity.cursor``. ``host`` is the SI trusted host at JOINT_SOURCE; the model file is admitted as evidence
    input, not as a parent edit.
    """
    raise NotImplementedError("B1_CONTRACT_ONLY_NOT_IMPLEMENTED")


def predict_raw(handle, item, *, budget, ledger):
    """Call the learner's ``predict(packet, depth)`` exactly once for ``item`` and persist the record first.

    Order is fixed: write the raw body to the private store, write the ``PredictionRecord`` (digest only) to the
    public ledger, then return. Refuses with PREDICTION_BUDGET_EXHAUSTED before the call when the budget is spent.
    """
    raise NotImplementedError("B1_CONTRACT_ONLY_NOT_IMPLEMENTED")


def repair_none(prediction, *, evaluator, budget, ledger):
    """The path WITHOUT CAS. The verified output is the raw prediction itself (equal digests).

    Work: one prediction call, zero native calls, the evaluator calls actually made, measured wall times.
    """
    raise NotImplementedError("B1_CONTRACT_ONLY_NOT_IMPLEMENTED")


def repair_cas_closed_loop(prediction, machine, *, calls, allow_acquisition, actuator_enabled, evaluator, budget, ledger):
    """The path WITH the current CAS repair. Uses the existing adapter unchanged.

    The prediction enters the native step as an input Idea (its digest bound into the step's inputs digest); the
    native runtime performs the repair under ``grant_for(machine, calls=calls, allow_acquisition=allow_acquisition,
    actuator_enabled=actuator_enabled)`` and ``execute_grant``; the receipt supplies ``I_allocated``,
    ``I_executed``, ``charged_native_policy_units`` and ``actual_primitive_work`` for the work account. The
    ``PredictionRecord`` is not modified. Returns a ``SystemOutputRecord`` with ``repair_path == "CAS_CLOSED_LOOP"``;
    a return without a receipt is NATIVE_RECEIPT_MISSING. With ``actuator_enabled=False`` the prediction is still
    recorded and ``native_calls_executed`` is 0 (the disabled-actuator control).
    """
    raise NotImplementedError("B1_CONTRACT_ONLY_NOT_IMPLEMENTED")


def evaluate(output, *, evaluator, ledger):
    """Judge one system output with the shared evaluator; refuses EVALUATOR_MISMATCH if the identity changed."""
    raise NotImplementedError("B1_CONTRACT_ONLY_NOT_IMPLEMENTED")


def episode_parity_check(records_none, records_cas, *, budget_none, budget_cas, evaluator_none, evaluator_cas):
    """Prove both paths were the same experiment except for the repair path.

    Refuses ITEM_ORDER_MISMATCH, BUDGET_MISMATCH, EVALUATOR_MISMATCH, and PREDICTION_NOT_PRESERVED when the same
    item under the same frozen model produced different raw digests on the two paths. Returns a plain dict of the
    per-path totals from the work accounts; it computes no score and applies no threshold.
    """
    raise NotImplementedError("B1_CONTRACT_ONLY_NOT_IMPLEMENTED")


def validate_record_is_public_safe(record):
    """Structural check only: a public record may carry digests, sizes, identities and counts, never a body.

    Pure Python, no I/O. Refuses PREDICTION_BODY_IN_PUBLIC_RECORD if any string field longer than 128 characters
    is present other than ``private_body_ref``.
    """
    raise NotImplementedError("B1_CONTRACT_ONLY_NOT_IMPLEMENTED")
