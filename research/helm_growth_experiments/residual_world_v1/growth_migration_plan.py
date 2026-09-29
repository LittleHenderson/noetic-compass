"""Migration plan for ONE optional residual world specialist (P1 of PARALLEL-CAPABILITY-01, 2026-09-27).

Pure Python, standard library only. It never imports torch, never opens a checkpoint, and never touches the
original learner. It is the bookkeeping half of the growth packet: what the specialist is, which original
parameters must survive by exact name and shape, how optimizer state maps by VERIFIED parameter identity and name
(never by position alone), how the new parameters are initialized and from which recorded seed, which numerical
tolerance and precondition is claimed, and what the versioned sidecar beside a grown state must carry.

Confirmed against the exact scientific source (``c45f775f``, file sha256 ``0f424d86…``): the world head is
``Sequential(Linear(WORLD_CANDIDATE_WIDTH, WIDTH, bias=False), GELU(), LayerNorm(WIDTH), Linear(WIDTH, 1, bias=True))``
at lines 856-858 with ``WIDTH = 64`` (197) and ``WORLD_CANDIDATE_WIDTH = 2 + 4 + DECL_VECTOR_WIDTH = 38`` (206, 246);
the optimizer is one AdamW group over ``list(module.parameters())`` (1840-1845); fingerprints are
``name:dtype:shape`` rows over sorted state-dict keys (515); ``learnable_names`` in a checkpoint are the sorted
state-dict keys (2128), so a grown container is a new layout that the original restore path refuses by design.

Revision 0.2 (FORWARD-02, 2026-09-27) applies the four source findings of PR #245 comment 5857009736:
(1) both specialist constructors run inside one forked, seeded CPU generator; (2) optimizer state is mapped through
a binding of the actual parameter objects to unique names, group settings are preserved from the group itself and a
supplied config must match them; (3) a versioned sidecar carries ``enabled``, sizes, seed, plan digest and file
digests so an enabled grown state with a nonzero B and its optimizer reload together; (4) a nonfinite intermediate
``GELU(A x)`` is refused before the B multiplication and the gradient statement names its conditions.

Claim state: this is preparation. Nothing here trains, infers, or asserts a capacity benefit.
"""

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import re

PLAN_SCHEMA = "cas.growth.world-residual-specialist.migration-plan/0.2"
SIDECAR_SCHEMA = "cas.growth.world-residual-specialist.sidecar/0.1"
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
RECORDED_INIT_SEED = 2026092701  # Codex-assigned seed for any newly initialized copy (comment 5856986121); never the parent RNG
NEW_PARAMETER_NAMES = ("world_specialist.A.weight", "world_specialist.B.weight")
INIT_POLICY = {"world_specialist.A.weight": "NONZERO_FROM_RECORDED_GENERATOR",
               "world_specialist.B.weight": "ZERO"}
INIT_GENERATOR_SCOPE = ("A and B both constructed inside ONE torch.random.fork_rng(devices=[]) block whose CPU "
                        "default generator is seeded with init_seed; B is zeroed inside the same block; the run's "
                        "shared CPU generator and every CUDA generator are left exactly unchanged "
                        "(world_residual_specialist.rng_neutrality_probe checks this by exact state equality)")
NEW_OPTIMIZER_STATE_POLICY = {"step": "zero scalar tensor", "exp_avg": "zeros_like(parameter)",
                              "exp_avg_sq": "zeros_like(parameter)"}
OPTIMIZER_STATE_MAPPING = "BY_VERIFIED_PARAMETER_IDENTITY_AND_EXACT_NAME"
# Settings of one AdamW group that the grown optimizer must carry unchanged. ``params`` is never a setting.
OPTIMIZER_CONSTRUCTOR_KEYS = ("lr", "betas", "eps", "weight_decay", "amsgrad", "maximize", "foreach", "capturable",
                              "differentiable", "fused")
# The learner's optimizer_config keys (source lines 1840-1845) and the group key each must equal.
CONFIG_TO_GROUP = {"learning_rate": "lr", "weight_decay": "weight_decay", "betas": "betas", "eps": "eps"}
SIDECAR_FILE = "specialist_config.json"
GROWN_STATE_FILE = "grown_state.pt"
GROWN_OPTIMIZER_FILE = "grown_optimizer.pt"
PLAN_FILE = "plan.json"

TOLERANCES = {
    "initial_contribution_same_device_finite_inputs": "EXACT (torch.equal) UNDER THE CHECKED PRECONDITION that the "
        "intermediate h = GELU(A x) is finite. Then B h is exactly 0.0 because B is the zero matrix, and base + 0.0 "
        "equals base bit for bit (a -0.0 base becomes +0.0). Finite x alone does NOT imply finite h.",
    "nonfinite_intermediates": "REFUSED_BEFORE_B (SPECIALIST_NONFINITE_INTERMEDIATE). Counterexample recorded before "
        "any run: A = all ones and x = finfo(float32).max on every coordinate give A x = inf, GELU(inf) = inf, and "
        "0.0 x inf = nan; the check on the inputs alone would have let that nan through.",
    "cross_device_or_hardware": "NO_CLAIM. Bitwise function preservation is not claimed on arbitrary hardware.",
    "nonfinite_inputs": "REFUSED_BEFORE_FORWARD (0.0 times inf or nan is nan, so the input is refused, not masked).",
    "trainability_probe": "On step 1, B's gradient is nonzero ONLY IF GELU(A x) is nonzero for some row AND the "
        "upstream gradient dL/dy is nonzero; the probe uses generic nonzero inputs and a sum loss (dL/dy = 1), so "
        "both hold. A's gradient is exactly zero on step 1 while B is the zero matrix. After B's first update, A's "
        "gradient is nonzero for those inputs. Recorded counterexamples: x = 0 gives GELU(0) = 0 and dL/dB = 0; a "
        "zero upstream gradient gives dL/dB = 0. No tolerance: nonzero versus exactly zero.",
}
WHY_B_LEARNS_FIRST = (
    "For y = base + B·GELU(A x): dL/dB = (dL/dy)·GELU(A x)^T, which is nonzero only when GELU(A x) is nonzero for "
    "some row and dL/dy is nonzero (x = 0 and a zero upstream gradient are counterexamples); dL/dA = "
    "B^T·(dL/dy)·GELU'(A x)·x^T, exactly zero while B is the zero matrix. So under generic nonzero inputs and a "
    "nonzero loss gradient B receives gradient first, and A's gradient becomes informative only after B has taken at "
    "least one update. Initializing both A and B to zero would leave both gradients zero forever, which is why that "
    "combination is refused.")

REFUSALS = (
    "ORIGINAL_NAME_MISSING", "ORIGINAL_SIGNATURE_CHANGED", "NAME_COLLISION", "NEW_NAMES_INVALID",
    "NEW_SHAPES_INVALID", "INIT_POLICY_INVALID", "POSITIONAL_MAPPING_REFUSED", "PARAMETER_ORDER_CHANGED",
    "INIT_SEED_MISSING", "TOLERANCE_UNSTATED", "HIDDEN_SIZE_INVALID", "INPUT_WIDTH_INVALID", "COUNT_MISMATCH",
    "PLAN_DIGEST_MISMATCH", "PLAN_SCHEMA_INVALID", "FINGERPRINT_ROW_INVALID", "WORLD_HEAD_NOT_FOUND",
    "OPTIMIZER_GROUPS_UNSUPPORTED", "SPECIALIST_ALREADY_ATTACHED", "SPECIALIST_A_INIT_ZERO",
    "SPECIALIST_INPUT_INVALID", "SPECIALIST_NONFINITE_INPUT",
    # added in revision 0.2 (FORWARD-02)
    "OPTIMIZER_BINDING_INVALID", "OPTIMIZER_CONFIG_MISMATCH", "OPTIMIZER_STATE_INCOMPATIBLE",
    "OPTIMIZER_GROUP_SETTINGS_NOT_PRESERVED", "SPECIALIST_NONFINITE_INTERMEDIATE", "SPECIALIST_NOT_ATTACHED",
    "SIDECAR_MISSING", "SIDECAR_MISMATCH", "SIDECAR_SCHEMA_INVALID",
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
_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")


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


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        init_policy=dict(INIT_POLICY), init_seed=init_seed, init_generator_scope=INIT_GENERATOR_SCOPE,
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
    if plan.init_generator_scope != INIT_GENERATOR_SCOPE:
        _refuse("INIT_POLICY_INVALID", "init_generator_scope must record both constructors inside the seeded fork")
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


# ---------------------------------------------------------------------------------------------------------------
# Finding 2: optimizer state binds through the ACTUAL parameter objects, never through an inferred position.
# ---------------------------------------------------------------------------------------------------------------

def bind_group_parameters(group_params, named_parameters):
    """Bind each parameter object of one optimizer group to its unique module name by object identity.

    ``group_params`` is the group's own ``params`` list (the objects AdamW steps); ``named_parameters`` is the
    module's ``(name, parameter)`` sequence. Returns the names in GROUP order, which is the order the serialized
    optimizer state is indexed by. Refuses a foreign object (in the group, not in the module), a duplicate (the
    same object twice in the group), a missing one (in the module, not in the group) and one object under two
    names. Pure Python: identity is ``id()``, so it works on test doubles as well as on torch parameters.
    """
    named = [(name, parameter) for name, parameter in named_parameters]
    by_id = {}
    for name, parameter in named:
        if type(name) is not str or _NAME.match(name) is None:
            _refuse("FINGERPRINT_ROW_INVALID", repr(name)[:80])
        if id(parameter) in by_id:
            _refuse("OPTIMIZER_BINDING_INVALID", "one parameter object under two names: %s and %s" % (by_id[id(parameter)], name))
        by_id[id(parameter)] = name
    names, seen = [], set()
    for position, parameter in enumerate(list(group_params)):
        name = by_id.get(id(parameter))
        if name is None:
            _refuse("OPTIMIZER_BINDING_INVALID", "foreign parameter object at group position %d" % position)
        if name in seen:
            _refuse("OPTIMIZER_BINDING_INVALID", "duplicate parameter object in the group: " + name)
        seen.add(name)
        names.append(name)
    missing = [name for name, _ in named if name not in seen]
    if missing:
        _refuse("OPTIMIZER_BINDING_INVALID", "module parameters absent from the group: " + ", ".join(missing[:5]))
    return tuple(names)


def group_settings(group):
    """Every setting of one optimizer group except its parameter list, deep-copied. ``params`` is never a setting."""
    if type(group) is not dict or "params" not in group:
        _refuse("OPTIMIZER_GROUPS_UNSUPPORTED", "a param group is a dict carrying 'params'")
    return {key: copy.deepcopy(value) for key, value in group.items() if key != "params"}


def _same_setting(a, b):
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        return list(a) == list(b)
    return type(a) is type(b) and a == b if isinstance(a, bool) or isinstance(b, bool) else a == b


def validate_optimizer_config(settings, optimizer_config):
    """A supplied learner ``optimizer_config`` must EQUAL the group's own settings; it is never substituted for them.
    With no config supplied the group's settings stand on their own. Returns the settings unchanged."""
    if optimizer_config is None:
        return settings
    if type(optimizer_config) is not dict:
        _refuse("OPTIMIZER_CONFIG_MISMATCH", "optimizer_config must be a dict")
    for config_key, group_key in CONFIG_TO_GROUP.items():
        if config_key not in optimizer_config:
            _refuse("OPTIMIZER_CONFIG_MISMATCH", "optimizer_config lacks " + config_key)
        if group_key not in settings:
            _refuse("OPTIMIZER_CONFIG_MISMATCH", "group lacks " + group_key)
        if not _same_setting(optimizer_config[config_key], settings[group_key]):
            _refuse("OPTIMIZER_CONFIG_MISMATCH", "%s=%r differs from the group's %s=%r"
                    % (config_key, optimizer_config[config_key], group_key, settings[group_key]))
    return settings


def settings_preserved(old_settings, new_group):
    """Every old setting must be present and equal in the new group. Returns the list of checked keys."""
    for key, value in old_settings.items():
        if key not in new_group or not _same_setting(value, new_group[key]):
            _refuse("OPTIMIZER_GROUP_SETTINGS_NOT_PRESERVED", "%s: old %r, new %r" % (key, value, new_group.get(key)))
    return sorted(old_settings)


def optimizer_state_mapping(old_named_order, new_named_order):
    """Map optimizer state BY EXACT NAME from the old (verified) group order to the new (verified) group order.

    Both inputs must come from ``bind_group_parameters`` so that each position is a verified name, never a guess.
    The old names must appear in the new order as an unchanged prefix (a registered submodule appends its
    parameters), and the appended names must be exactly the specialist's.
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


def check_mapping_against_bindings(mapping, old_group_names, new_group_names):
    """A mapping is usable only if its indices agree with the verified bindings on both sides."""
    for name, row in mapping["preserved"].items():
        if row["old_index"] >= len(old_group_names) or old_group_names[row["old_index"]] != name:
            _refuse("OPTIMIZER_BINDING_INVALID", "old index of %s does not name that parameter in the verified group" % name)
        if row["new_index"] >= len(new_group_names) or new_group_names[row["new_index"]] != name:
            _refuse("OPTIMIZER_BINDING_INVALID", "new index of %s does not name that parameter in the verified group" % name)
    for name, row in mapping["new"].items():
        if row["new_index"] >= len(new_group_names) or new_group_names[row["new_index"]] != name:
            _refuse("OPTIMIZER_BINDING_INVALID", "new index of %s does not name that parameter in the verified group" % name)
    if len(new_group_names) != len(mapping["preserved"]) + len(mapping["new"]):
        _refuse("OPTIMIZER_BINDING_INVALID", "the verified new group has parameters the mapping does not name")
    return True


# ---------------------------------------------------------------------------------------------------------------
# Finding 3: a versioned sidecar carries what a state dict does not (enabled, sizes, seed, plan and file digests).
# ---------------------------------------------------------------------------------------------------------------

def _sidecar_digest(body):
    body = dict(body)
    body.pop("sidecar_digest", None)
    return hashlib.sha256(canonical(body)).hexdigest()


def build_sidecar(*, enabled, hidden, input_width, init_seed, plan_digest, state_sha256, optimizer_state_sha256,
                  optimizer_parameter_names):
    if type(enabled) is not bool:
        _refuse("SIDECAR_SCHEMA_INVALID", "enabled must be a bool")
    if type(hidden) is not int or not 1 <= hidden <= 256:
        _refuse("HIDDEN_SIZE_INVALID", repr(hidden))
    if input_width != WORLD_CANDIDATE_WIDTH:
        _refuse("INPUT_WIDTH_INVALID", repr(input_width))
    if type(init_seed) is not int:
        _refuse("INIT_SEED_MISSING")
    for label, value in (("plan_digest", plan_digest), ("state_sha256", state_sha256),
                         ("optimizer_state_sha256", optimizer_state_sha256)):
        if type(value) is not str or _HEX64.match(value) is None:
            _refuse("SIDECAR_SCHEMA_INVALID", label + " must be 64 lowercase hex characters")
    names = tuple(optimizer_parameter_names)
    if not names or len(set(names)) != len(names) or any(_NAME.match(n) is None for n in names):
        _refuse("SIDECAR_SCHEMA_INVALID", "optimizer_parameter_names must be unique valid names in group order")
    body = {"schema": SIDECAR_SCHEMA, "scientific_source": SCIENTIFIC_SOURCE,
            "learner_source_file_sha256": LEARNER_SOURCE_FILE_SHA256, "enabled": enabled, "hidden": hidden,
            "input_width": input_width, "init_seed": init_seed, "plan_digest": plan_digest,
            "new_names": list(NEW_PARAMETER_NAMES), "optimizer_parameter_names": list(names),
            "files": {GROWN_STATE_FILE: state_sha256, GROWN_OPTIMIZER_FILE: optimizer_state_sha256}}
    body["sidecar_digest"] = _sidecar_digest(body)
    return body


def validate_sidecar(sidecar, *, expected_plan_digest=None):
    if type(sidecar) is not dict or sidecar.get("schema") != SIDECAR_SCHEMA:
        _refuse("SIDECAR_SCHEMA_INVALID", "schema is not " + SIDECAR_SCHEMA)
    required = ("scientific_source", "learner_source_file_sha256", "enabled", "hidden", "input_width", "init_seed",
                "plan_digest", "new_names", "optimizer_parameter_names", "files", "sidecar_digest")
    for key in required:
        if key not in sidecar:
            _refuse("SIDECAR_SCHEMA_INVALID", "missing " + key)
    if sidecar["sidecar_digest"] != _sidecar_digest(sidecar):
        _refuse("SIDECAR_MISMATCH", "sidecar_digest does not match the sidecar body")
    if type(sidecar["enabled"]) is not bool or type(sidecar["hidden"]) is not int or type(sidecar["init_seed"]) is not int:
        _refuse("SIDECAR_SCHEMA_INVALID", "enabled/hidden/init_seed types")
    if sidecar["input_width"] != WORLD_CANDIDATE_WIDTH or not 1 <= sidecar["hidden"] <= 256:
        _refuse("SIDECAR_SCHEMA_INVALID", "sizes")
    if list(sidecar["new_names"]) != list(NEW_PARAMETER_NAMES):
        _refuse("SIDECAR_MISMATCH", "new_names")
    if sidecar["scientific_source"] != SCIENTIFIC_SOURCE or sidecar["learner_source_file_sha256"] != LEARNER_SOURCE_FILE_SHA256:
        _refuse("SIDECAR_MISMATCH", "source pins")
    if set(sidecar["files"]) != {GROWN_STATE_FILE, GROWN_OPTIMIZER_FILE}:
        _refuse("SIDECAR_SCHEMA_INVALID", "files")
    if expected_plan_digest is not None and sidecar["plan_digest"] != expected_plan_digest:
        _refuse("SIDECAR_MISMATCH", "plan_digest differs from the plan on disk")
    return sidecar


def sidecar_to_json(sidecar):
    validate_sidecar(sidecar)
    return json.dumps(sidecar, indent=1, sort_keys=True) + "\n"


def sidecar_from_json(text, *, expected_plan_digest=None):
    return validate_sidecar(json.loads(text), expected_plan_digest=expected_plan_digest)
