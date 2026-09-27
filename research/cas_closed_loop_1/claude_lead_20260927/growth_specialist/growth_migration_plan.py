"""Migration plan for ONE optional residual world specialist (P1 of PARALLEL-CAPABILITY-01, 2026-09-27).

Pure Python, standard library only. It never imports torch, never opens a checkpoint, and never touches the
original learner. It is the bookkeeping half of the growth packet: what the specialist is, which original
parameters must survive by exact name and shape, how optimizer state maps by name (never by position), how the
new parameters are initialized and from which recorded seed, and which numerical tolerance is claimed.

Confirmed against the exact scientific source (``c45f775f``, file sha256 ``0f424d86…``): the world head is
``Sequential(Linear(WORLD_CANDIDATE_WIDTH, WIDTH, bias=False), GELU(), LayerNorm(WIDTH), Linear(WIDTH, 1, bias=True))``
at lines 856-858 with ``WIDTH = 64`` (197) and ``WORLD_CANDIDATE_WIDTH = 2 + 4 + DECL_VECTOR_WIDTH = 38`` (206, 246);
the optimizer is one AdamW group over ``list(module.parameters())`` (1840-1845); fingerprints are
``name:dtype:shape`` rows over sorted state-dict keys (515); ``learnable_names`` in a checkpoint are the sorted
state-dict keys (2128), so a grown container is a new layout that the original restore path refuses by design.

Claim state: this is preparation. Nothing here trains, infers, or asserts a capacity benefit.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re

PLAN_SCHEMA = "cas.growth.world-residual-specialist.migration-plan/0.1"
SCIENTIFIC_SOURCE = "c45f775f225dd06cc20cdf313f0a0398486e0d61"
LEARNER_SOURCE_FILE_SHA256 = "0f424d8633f01b69d7ed256a8e687a4ba0f99be71ae85732c50d4c8dcd7a81a8"
WORLD_HEAD_SOURCE_LINES = (856, 858)
OPTIMIZER_SOURCE_LINE = 1840
FINGERPRINT_FORMAT = "name:dtype:shape over sorted state-dict keys (pointer_learner._fingerprint, line 515)"

WIDTH = 64
DECL_VECTOR_WIDTH = 32
WORLD_CANDIDATE_WIDTH = 2 + 4 + DECL_VECTOR_WIDTH  # 38, as in the source
WORLD_HEAD_FIRST_WEIGHT = "world_head.0.weight"

SPECIALIST_PREFIX = "world_specialist"
SPECIALIST_HIDDEN = 16  # ONE explicit size. Not a sweep.
NEW_PARAMETER_NAMES = ("world_specialist.A.weight", "world_specialist.B.weight")
INIT_POLICY = {"world_specialist.A.weight": "NONZERO_FROM_RECORDED_GENERATOR",
               "world_specialist.B.weight": "ZERO"}
NEW_OPTIMIZER_STATE_POLICY = {"step": "zero scalar tensor", "exp_avg": "zeros_like(parameter)",
                              "exp_avg_sq": "zeros_like(parameter)"}
OPTIMIZER_STATE_MAPPING = "BY_EXACT_NAME"
TOLERANCES = {
    "initial_contribution_same_device_finite_inputs": "EXACT (torch.equal). B is the zero matrix, so "
        "B(GELU(A x)) is exactly 0.0 for finite x and base + 0.0 equals base bit for bit (a -0.0 base becomes +0.0).",
    "cross_device_or_hardware": "NO_CLAIM. Bitwise function preservation is not claimed on arbitrary hardware.",
    "nonfinite_inputs": "REFUSED_BEFORE_FORWARD (0.0 times inf or nan is nan, so the input is refused, not masked).",
    "trainability_probe": "B must show a nonzero gradient on step 1 while A's gradient is exactly zero; after B "
        "updates, A must show a nonzero gradient on step 2. No tolerance: nonzero versus exactly zero.",
}
WHY_B_LEARNS_FIRST = (
    "For y = base + B·GELU(A x): dL/dB = (dL/dy)·GELU(A x)^T, nonzero whenever A is nonzero and the input is finite; "
    "dL/dA = B^T·(dL/dy)·GELU'(A x)·x^T, exactly zero while B is the zero matrix. So B receives gradient first; A's "
    "gradient becomes informative only after B has taken at least one update. Initializing both A and B to zero "
    "would leave both gradients zero forever, which is why that combination is refused.")

REFUSALS = (
    "ORIGINAL_NAME_MISSING", "ORIGINAL_SIGNATURE_CHANGED", "NAME_COLLISION", "NEW_NAMES_INVALID",
    "NEW_SHAPES_INVALID", "INIT_POLICY_INVALID", "POSITIONAL_MAPPING_REFUSED", "PARAMETER_ORDER_CHANGED",
    "INIT_SEED_MISSING", "TOLERANCE_UNSTATED", "HIDDEN_SIZE_INVALID", "INPUT_WIDTH_INVALID", "COUNT_MISMATCH",
    "PLAN_DIGEST_MISMATCH", "PLAN_SCHEMA_INVALID", "FINGERPRINT_ROW_INVALID", "WORLD_HEAD_NOT_FOUND",
    "OPTIMIZER_GROUPS_UNSUPPORTED", "SPECIALIST_ALREADY_ATTACHED", "SPECIALIST_A_INIT_ZERO",
    "SPECIALIST_INPUT_INVALID", "SPECIALIST_NONFINITE_INPUT",
)


class PlanRefused(ValueError):
    def __init__(self, code, detail=""):
        if code not in REFUSALS:
            raise ValueError("UNKNOWN_REFUSAL_CODE:" + str(code))
        self.code = code
        self.detail = detail
        super().__init__(code + (": " + detail if detail else ""))


def _refuse(code, detail=""):
    raise PlanRefused(code, detail)


_NAME = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)*\Z")  # segments may be capitalized (A, B)


def parse_fingerprint_rows(rows):
    """``name:dtype:shape`` rows (the source's own format) -> {name: 'dtype:shape'}. Values are never read."""
    out = {}
    for row in tuple(rows):
        if type(row) is not str or row.count(":") < 2:
            _refuse("FINGERPRINT_ROW_INVALID", repr(row)[:80])
        name, signature = row.split(":", 1)
        if _NAME.match(name) is None or name in out:
            _refuse("FINGERPRINT_ROW_INVALID", name)
        out[name] = signature
    return out


def expected_new_parameter_count(hidden=SPECIALIST_HIDDEN, input_width=WORLD_CANDIDATE_WIDTH):
    return hidden * input_width + hidden


def new_parameter_shapes(hidden=SPECIALIST_HIDDEN, input_width=WORLD_CANDIDATE_WIDTH):
    return {"world_specialist.A.weight": [hidden, input_width], "world_specialist.B.weight": [1, hidden]}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


@dataclass(frozen=True)
class MigrationPlan:
    schema: str
    scientific_source: str
    learner_source_file_sha256: str
    parent_checkpoint_sha256: str
    parent_cursor: int
    input_width: int
    hidden: int
    original_names: tuple
    original_signatures: dict
    new_names: tuple
    new_shapes: dict
    init_policy: dict
    init_seed: int
    init_generator_scope: str
    optimizer_state_mapping: str
    new_optimizer_state_policy: dict
    tolerances: dict
    expected_new_parameter_count: int
    learnable_names_after: tuple
    plan_digest: str


def _digest_of(fields):
    body = dict(fields)
    body.pop("plan_digest", None)
    return hashlib.sha256(canonical(body)).hexdigest()


def build_plan(*, fingerprint_rows, parent_checkpoint_sha256, parent_cursor, init_seed,
               hidden=SPECIALIST_HIDDEN, input_width=WORLD_CANDIDATE_WIDTH):
    """Build the plan from the parent's fingerprint rows. Refuses before producing anything inconsistent."""
    signatures = parse_fingerprint_rows(fingerprint_rows)
    if WORLD_HEAD_FIRST_WEIGHT not in signatures:
        _refuse("WORLD_HEAD_NOT_FOUND", WORLD_HEAD_FIRST_WEIGHT + " absent from the parent fingerprint")
    if type(hidden) is not int or not 1 <= hidden <= 256:
        _refuse("HIDDEN_SIZE_INVALID", repr(hidden))
    if input_width != WORLD_CANDIDATE_WIDTH:
        _refuse("INPUT_WIDTH_INVALID", "%r is not the source's WORLD_CANDIDATE_WIDTH %d" % (input_width, WORLD_CANDIDATE_WIDTH))
    if type(init_seed) is not int:
        _refuse("INIT_SEED_MISSING", "a recorded integer seed is required for A's initialization")
    if any(name in signatures for name in NEW_PARAMETER_NAMES):
        _refuse("NAME_COLLISION", "specialist names already present in the parent")
    original_names = tuple(sorted(signatures))
    fields = dict(
        schema=PLAN_SCHEMA, scientific_source=SCIENTIFIC_SOURCE, learner_source_file_sha256=LEARNER_SOURCE_FILE_SHA256,
        parent_checkpoint_sha256=str(parent_checkpoint_sha256), parent_cursor=int(parent_cursor),
        input_width=input_width, hidden=hidden, original_names=original_names,
        original_signatures={name: signatures[name] for name in original_names},
        new_names=NEW_PARAMETER_NAMES, new_shapes=new_parameter_shapes(hidden, input_width),
        init_policy=dict(INIT_POLICY), init_seed=init_seed,
        init_generator_scope="A only; forked CPU default generator seeded with init_seed (same mechanism as the "
                             "source's analogy_head at lines 861-864); the run's shared RNG is never consumed",
        optimizer_state_mapping=OPTIMIZER_STATE_MAPPING, new_optimizer_state_policy=dict(NEW_OPTIMIZER_STATE_POLICY),
        tolerances=dict(TOLERANCES), expected_new_parameter_count=expected_new_parameter_count(hidden, input_width),
        learnable_names_after=tuple(sorted(original_names + NEW_PARAMETER_NAMES)))
    fields["plan_digest"] = _digest_of(fields)
    plan = MigrationPlan(**fields)
    validate_plan(plan)
    return plan


def validate_plan(plan):
    """Every rule the plan must satisfy, each with its own refusal. Returns a summary dict."""
    if type(plan) is not MigrationPlan or plan.schema != PLAN_SCHEMA:
        _refuse("PLAN_SCHEMA_INVALID")
    if not plan.original_names or WORLD_HEAD_FIRST_WEIGHT not in plan.original_names:
        _refuse("ORIGINAL_NAME_MISSING", WORLD_HEAD_FIRST_WEIGHT)
    if tuple(sorted(plan.original_signatures)) != tuple(plan.original_names):
        _refuse("ORIGINAL_SIGNATURE_CHANGED", "signature keys differ from original names")
    if set(plan.new_names) & set(plan.original_names):
        _refuse("NAME_COLLISION")
    if tuple(plan.new_names) != NEW_PARAMETER_NAMES:
        _refuse("NEW_NAMES_INVALID", repr(plan.new_names))
    if type(plan.hidden) is not int or not 1 <= plan.hidden <= 256:
        _refuse("HIDDEN_SIZE_INVALID", repr(plan.hidden))
    if plan.input_width != WORLD_CANDIDATE_WIDTH:
        _refuse("INPUT_WIDTH_INVALID", repr(plan.input_width))
    if plan.new_shapes != new_parameter_shapes(plan.hidden, plan.input_width):
        _refuse("NEW_SHAPES_INVALID", repr(plan.new_shapes))
    if plan.init_policy != INIT_POLICY or plan.init_policy.get("world_specialist.A.weight") == "ZERO":
        _refuse("INIT_POLICY_INVALID", "A must be nonzero from a recorded generator and B must be zero")
    if plan.optimizer_state_mapping != OPTIMIZER_STATE_MAPPING:
        _refuse("POSITIONAL_MAPPING_REFUSED", repr(plan.optimizer_state_mapping))
    if type(plan.init_seed) is not int:
        _refuse("INIT_SEED_MISSING")
    if set(plan.tolerances) != set(TOLERANCES) or any(not v for v in plan.tolerances.values()):
        _refuse("TOLERANCE_UNSTATED")
    if plan.expected_new_parameter_count != expected_new_parameter_count(plan.hidden, plan.input_width):
        _refuse("COUNT_MISMATCH", "expected_new_parameter_count")
    if plan.learnable_names_after != tuple(sorted(plan.original_names + plan.new_names)):
        _refuse("COUNT_MISMATCH", "learnable_names_after")
    if plan.plan_digest != _digest_of(asdict(plan)):
        _refuse("PLAN_DIGEST_MISMATCH")
    return {"original_parameters": len(plan.original_names), "new_parameters": len(plan.new_names),
            "new_scalar_count": plan.expected_new_parameter_count, "hidden": plan.hidden,
            "input_width": plan.input_width, "plan_digest": plan.plan_digest}


def plan_to_json(plan):
    validate_plan(plan)
    return json.dumps(asdict(plan), indent=1, sort_keys=True) + "\n"


def plan_from_json(text):
    data = json.loads(text)
    for key in ("original_names", "new_names", "learnable_names_after"):
        data[key] = tuple(data[key])
    plan = MigrationPlan(**data)
    validate_plan(plan)
    return plan


def optimizer_state_mapping(old_named_order, new_named_order):
    """Map optimizer state BY EXACT NAME from the old parameter order to the new one.

    The old names must appear in the new order as an unchanged prefix (the source keeps a single AdamW group in
    ``module.parameters()`` order, and a registered submodule appends its parameters), and the appended names must
    be exactly the specialist's. Nothing is inferred from position alone: every row carries the name.
    """
    old = list(old_named_order)
    new = list(new_named_order)
    if len(set(old)) != len(old) or len(set(new)) != len(new):
        _refuse("FINGERPRINT_ROW_INVALID", "duplicate parameter names")
    missing = [name for name in old if name not in new]
    if missing:
        _refuse("ORIGINAL_NAME_MISSING", ", ".join(missing[:5]))
    if new[:len(old)] != old:
        _refuse("PARAMETER_ORDER_CHANGED", "original parameters are not an unchanged prefix of the new order")
    appended = new[len(old):]
    if sorted(appended) != sorted(NEW_PARAMETER_NAMES):
        _refuse("NEW_NAMES_INVALID", repr(appended))
    return {"mapping": OPTIMIZER_STATE_MAPPING,
            "preserved": {name: {"old_index": old.index(name), "new_index": new.index(name)} for name in old},
            "new": {name: {"new_index": new.index(name), "state_init": dict(NEW_OPTIMIZER_STATE_POLICY),
                           "parameter_init": INIT_POLICY[name]} for name in appended}}
