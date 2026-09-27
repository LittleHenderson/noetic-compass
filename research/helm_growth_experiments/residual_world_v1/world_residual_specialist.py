"""ONE optional residual world specialist and its migration code (P1 of PARALLEL-CAPABILITY-01, 2026-09-27).

    score(x) = old_world_score(x) + B · GELU(A · x)

``x`` is the same world-candidate input the source's ``world_head`` consumes (width 38); the output stays one
scalar per row, so the external I/O is preserved. ``A`` is ``Linear(38, SPECIALIST_HIDDEN, bias=False)``
initialized NONZERO from a separately recorded generator; ``B`` is ``Linear(SPECIALIST_HIDDEN, 1, bias=False)``
initialized to ZERO. With ``B = 0`` the initial contribution is exactly 0.0 whenever the intermediate
``GELU(A x)`` is finite (checked, see ``growth_migration_plan.TOLERANCES``). Disabled, the module returns the
base score object unchanged.

Revision 0.2 (FORWARD-02, 2026-09-27) applies the four source findings of PR #245 comment 5857009736:
(1) A and B are both constructed inside one seeded ``fork_rng`` block, so the surrounding CPU and CUDA generators
are left exactly unchanged (``rng_neutrality_probe``); (2) ``migrate_optimizer`` binds the old group's actual
parameter objects to unique names by identity, refuses foreign, duplicate or missing entries, preserves the old
group's settings and refuses a supplied config that differs; (3) ``save_grown`` / ``load_grown`` write and read a
versioned sidecar beside the state so ``enabled``, a nonzero learned B and the optimizer state reload together;
(4) ``contribution`` refuses a nonfinite intermediate before the B multiplication.

This file requires torch and is reserved for the authorized numerical venue (GPU). It is never imported by the
CPU-dry tests. It does not import, modify or attach to the original learner; ``attach_specialist`` takes any
container that carries a ``world_head`` and registers the specialist as its LAST submodule, which keeps the
original parameter order as an unchanged prefix.

Claim state: implemented, NOT RUN anywhere at the time of writing (no torch in the preparing container).
No checkpoint is deserialized or mutated by this file; a real migration later copies an admitted parent at a
declared safe boundary and records the plan produced here.
"""

import copy
import pathlib

import torch

from growth_migration_plan import (GROWN_OPTIMIZER_FILE, GROWN_STATE_FILE, INIT_POLICY, NEW_PARAMETER_NAMES,
                                   OPTIMIZER_CONSTRUCTOR_KEYS, PLAN_FILE, PlanRefused, SIDECAR_FILE,
                                   SPECIALIST_HIDDEN, WORLD_CANDIDATE_WIDTH, bind_group_parameters, build_plan,
                                   build_sidecar, check_mapping_against_bindings, file_sha256, group_settings,
                                   optimizer_state_mapping, plan_from_json, plan_to_json, settings_preserved,
                                   sidecar_from_json, sidecar_to_json, validate_optimizer_config, validate_sidecar)


def _refuse(code, detail=""):
    raise PlanRefused(code, detail)


def fingerprint_rows(module):
    """``name:dtype:shape`` rows over sorted state-dict keys, the same shape as the source's ``_fingerprint``."""
    state = module.state_dict()
    return ["%s:%s:%s" % (name, state[name].dtype, tuple(state[name].shape)) for name in sorted(state)]


def rng_neutrality_probe(build):
    """Run ``build()`` between two captures of the CPU generator state and of every CUDA generator state.

    Returns ``(result, report)`` where the report says, per generator family, whether the state is EXACTLY the
    same before and after. This is the written check for finding 1: constructing the specialist must consume
    nothing from the surrounding run's generators.
    """
    cpu_before = torch.get_rng_state().clone()
    cuda_before = [s.clone() for s in torch.cuda.get_rng_state_all()] if torch.cuda.is_available() else []
    result = build()
    cpu_after = torch.get_rng_state()
    cuda_after = torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []
    cuda_same = len(cuda_before) == len(cuda_after) and all(torch.equal(a, b) for a, b in zip(cuda_before, cuda_after))
    return result, {"cpu_rng_unchanged": bool(torch.equal(cpu_before, cpu_after)), "cuda_rng_unchanged": bool(cuda_same),
                    "cuda_generators_checked": len(cuda_before)}


class WorldResidualSpecialist(torch.nn.Module):
    """The optional module. ``enabled`` is a plain attribute, not a parameter: it never enters ``state_dict`` and
    is carried by the versioned sidecar (``save_grown`` / ``load_grown``) instead."""

    def __init__(self, *, init_seed, input_width=WORLD_CANDIDATE_WIDTH, hidden=SPECIALIST_HIDDEN, device="cpu"):
        super().__init__()
        if type(init_seed) is not int:
            _refuse("INIT_SEED_MISSING")
        if type(hidden) is not int or not 1 <= hidden <= 256:
            _refuse("HIDDEN_SIZE_INVALID", repr(hidden))
        if input_width != WORLD_CANDIDATE_WIDTH:
            _refuse("INPUT_WIDTH_INVALID", repr(input_width))
        # Finding 1: BOTH constructors run inside one forked CPU generator seeded with the recorded seed. Linear's
        # default initialization draws from the CPU default generator, so B's draws (discarded by the zeroing) must
        # also happen inside the fork; the run's shared generator and every CUDA generator are never touched.
        with torch.random.fork_rng(devices=[]):
            torch.random.default_generator.manual_seed(init_seed)
            self.A = torch.nn.Linear(input_width, hidden, bias=False)
            self.B = torch.nn.Linear(hidden, 1, bias=False)
            with torch.no_grad():
                self.B.weight.zero_()
        self.gelu = torch.nn.GELU()
        self.enabled = False
        self.init_seed = init_seed
        self.input_width = input_width
        self.hidden = hidden
        self.to(device)
        if not bool((self.A.weight != 0).any()):
            _refuse("SPECIALIST_A_INIT_ZERO", "A must be nonzero so that B can receive gradient")
        if bool((self.B.weight != 0).any()):
            _refuse("INIT_POLICY_INVALID", "B must start as the zero matrix")

    def _check(self, candidate, base_score):
        if not torch.is_tensor(candidate) or candidate.dim() != 2 or int(candidate.shape[1]) != self.input_width:
            _refuse("SPECIALIST_INPUT_INVALID", "candidate must be (n, %d)" % self.input_width)
        if not torch.is_tensor(base_score) or tuple(base_score.shape) != (int(candidate.shape[0]), 1):
            _refuse("SPECIALIST_INPUT_INVALID", "base_score must be (n, 1)")
        if not bool(torch.isfinite(candidate).all()) or not bool(torch.isfinite(base_score).all()):
            _refuse("SPECIALIST_NONFINITE_INPUT")

    def intermediate(self, candidate):
        """``h = GELU(A x)``, refused if any entry is nonfinite (finding 4). Finite ``x`` does not imply finite
        ``A x``: A = ones and x = finfo(float32).max on every coordinate overflow to inf, and 0.0 x inf is nan."""
        hidden = self.gelu(self.A(candidate))
        if not bool(torch.isfinite(hidden).all()):
            _refuse("SPECIALIST_NONFINITE_INTERMEDIATE", "GELU(A x) is nonfinite for a finite input; refused before B")
        return hidden

    def contribution(self, candidate, base_score):
        self._check(candidate, base_score)
        return self.B(self.intermediate(candidate))

    def forward(self, candidate, base_score):
        if not self.enabled:
            self._check(candidate, base_score)
            return base_score
        return base_score + self.contribution(candidate, base_score)


def scored_world(container, candidate):
    """The single call site a growth learner would use in place of ``world_head(candidate)`` (source line 1566)."""
    base = container.world_head(candidate)
    specialist = getattr(container, "world_specialist", None)
    return base if specialist is None else specialist(candidate, base)


def attach_specialist(container, *, init_seed, parent_checkpoint_sha256, parent_cursor, hidden=SPECIALIST_HIDDEN,
                      device="cpu"):
    """Register ONE specialist as the container's last submodule.

    Returns ``(specialist, plan, mapping, old_named_parameters)``. The last item is the tuple of ``(name, Parameter)``
    pairs captured BEFORE the attach; ``migrate_optimizer`` binds the old optimizer's actual parameter objects to
    those names by identity, so no caller has to guess which objects the old group held.
    """
    if hasattr(container, "world_specialist"):
        _refuse("SPECIALIST_ALREADY_ATTACHED")
    head = getattr(container, "world_head", None)
    if head is None or int(head[0].in_features) != WORLD_CANDIDATE_WIDTH:
        _refuse("WORLD_HEAD_NOT_FOUND", "container.world_head[0].in_features must be %d" % WORLD_CANDIDATE_WIDTH)
    plan = build_plan(fingerprint_rows=fingerprint_rows(container), parent_checkpoint_sha256=parent_checkpoint_sha256,
                      parent_cursor=parent_cursor, init_seed=init_seed, hidden=hidden)
    old_named = tuple((name, parameter) for name, parameter in container.named_parameters())
    old_order = bind_group_parameters([p for _, p in old_named], old_named)
    specialist = WorldResidualSpecialist(init_seed=init_seed, hidden=hidden, device=device)
    container.world_specialist = specialist  # registered LAST: the original order stays an unchanged prefix
    new_named = tuple((name, parameter) for name, parameter in container.named_parameters())
    new_order = bind_group_parameters([p for _, p in new_named], new_named)
    mapping = optimizer_state_mapping(old_order, new_order)
    after = set(new_order) - set(old_order)
    if after != set(NEW_PARAMETER_NAMES):
        _refuse("NEW_NAMES_INVALID", repr(sorted(after)))
    count = sum(p.numel() for name, p in new_named if name in after)
    if count != plan.expected_new_parameter_count:
        _refuse("COUNT_MISMATCH", "%d new scalars, plan says %d" % (count, plan.expected_new_parameter_count))
    return specialist, plan, mapping, old_named


def _state_compatible(entry, parameter, name):
    for key in ("exp_avg", "exp_avg_sq"):
        value = entry.get(key)
        if not torch.is_tensor(value) or tuple(value.shape) != tuple(parameter.shape) or value.dtype != parameter.dtype:
            _refuse("OPTIMIZER_STATE_INCOMPATIBLE", "%s of %s does not match the parameter's shape and dtype" % (key, name))
    if "step" not in entry:
        _refuse("OPTIMIZER_STATE_INCOMPATIBLE", "no step for " + name)


def migrate_optimizer(old_optimizer, container, *, mapping, old_named_parameters, optimizer_config=None):
    """Build the grown AdamW and carry every original parameter's state over through a VERIFIED binding.

    Finding 2: the old group's ``params`` objects are bound to their unique names by identity against the
    pre-attach ``old_named_parameters`` (foreign, duplicate and missing entries refused); the mapping's indices are
    checked against that binding on both sides; the old group's settings are copied onto the new group and checked
    afterwards; a supplied ``optimizer_config`` must equal those settings or the migration is refused. New entries
    deliberately start with a zero step and zero moments. Single-group layout only, as in the source.
    """
    if len(old_optimizer.param_groups) != 1:
        _refuse("OPTIMIZER_GROUPS_UNSUPPORTED", "the source keeps one AdamW group")
    old_group = old_optimizer.param_groups[0]
    old_names = bind_group_parameters(old_group["params"], old_named_parameters)
    settings = validate_optimizer_config(group_settings(old_group), optimizer_config)
    params = list(container.parameters())
    new_names = bind_group_parameters(params, container.named_parameters())
    check_mapping_against_bindings(mapping, old_names, new_names)
    new_optimizer = torch.optim.AdamW(params, **{k: settings[k] for k in OPTIMIZER_CONSTRUCTOR_KEYS if k in settings})
    new_group = new_optimizer.param_groups[0]
    for key, value in settings.items():
        new_group[key] = copy.deepcopy(value)
    settings_preserved(settings, new_group)
    old_state = old_optimizer.state_dict()
    if len(old_state["param_groups"]) != 1 or len(old_state["param_groups"][0]["params"]) != len(old_names):
        _refuse("OPTIMIZER_STATE_INCOMPATIBLE", "serialized group does not match the verified group")
    new_state = new_optimizer.state_dict()
    new_state["state"] = {}
    named = dict(container.named_parameters())
    carried, absent = [], []
    for name, row in mapping["preserved"].items():
        entry = old_state["state"].get(row["old_index"])
        if entry is None:
            absent.append(name)  # a parameter AdamW never stepped has no state yet; nothing is invented for it
            continue
        _state_compatible(entry, named[name], name)
        new_state["state"][row["new_index"]] = copy.deepcopy(entry)
        carried.append(name)
    for name, row in mapping["new"].items():
        parameter = named[name]
        new_state["state"][row["new_index"]] = {"step": torch.zeros((), dtype=torch.float32),
                                                "exp_avg": torch.zeros_like(parameter),
                                                "exp_avg_sq": torch.zeros_like(parameter)}
    new_optimizer.load_state_dict(new_state)
    settings_preserved(settings, new_optimizer.param_groups[0])
    return new_optimizer, {"carried_by_name": carried, "original_without_state": absent,
                           "new_with_zero_state": sorted(mapping["new"]), "settings_preserved": sorted(settings),
                           "old_group_names": list(old_names), "new_group_names": list(new_names)}


def preservation_report(old_named_tensors, container, old_optimizer, new_optimizer, mapping):
    """Exact-equality check of every original parameter and its optimizer state after migration."""
    named = dict(container.named_parameters())
    old_state, new_state = old_optimizer.state_dict()["state"], new_optimizer.state_dict()["state"]
    parameters_equal = all(torch.equal(old_named_tensors[name], named[name]) for name in old_named_tensors)
    state_equal = True
    for name, row in mapping["preserved"].items():
        old_entry = old_state.get(row["old_index"])
        if old_entry is None:
            continue
        new_entry = new_state[row["new_index"]]
        for key in old_entry:
            a, b = old_entry[key], new_entry[key]
            same = torch.equal(a, b) if torch.is_tensor(a) else a == b
            state_equal = state_equal and same
    old_settings = group_settings(old_optimizer.param_groups[0])
    settings_preserved(old_settings, new_optimizer.param_groups[0])
    return {"parameters_exactly_equal": parameters_equal, "optimizer_state_exactly_equal": state_equal,
            "group_settings_preserved": sorted(old_settings),
            "new_parameter_init": {name: INIT_POLICY[name] for name in NEW_PARAMETER_NAMES}}


def save_grown(container, optimizer, plan, directory):
    """Write the grown state, the optimizer state, the plan and the versioned sidecar together (finding 3).

    The sidecar records ``enabled`` (which ``state_dict`` never carries), the sizes and seed, the plan digest, the
    sha256 of both ``.pt`` files, and the verified group-order names of the optimizer's parameters.
    """
    specialist = getattr(container, "world_specialist", None)
    if specialist is None:
        _refuse("SPECIALIST_NOT_ATTACHED")
    if len(optimizer.param_groups) != 1:
        _refuse("OPTIMIZER_GROUPS_UNSUPPORTED")
    names = bind_group_parameters(optimizer.param_groups[0]["params"], container.named_parameters())
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    torch.save(container.state_dict(), directory / GROWN_STATE_FILE)
    torch.save(optimizer.state_dict(), directory / GROWN_OPTIMIZER_FILE)
    (directory / PLAN_FILE).write_text(plan_to_json(plan))
    sidecar = build_sidecar(enabled=bool(specialist.enabled), hidden=specialist.hidden,
                            input_width=specialist.input_width, init_seed=specialist.init_seed,
                            plan_digest=plan.plan_digest, state_sha256=file_sha256(directory / GROWN_STATE_FILE),
                            optimizer_state_sha256=file_sha256(directory / GROWN_OPTIMIZER_FILE),
                            optimizer_parameter_names=names)
    (directory / SIDECAR_FILE).write_text(sidecar_to_json(sidecar))
    return sidecar


def load_grown(container, directory, *, device):
    """Reload a grown state into a FRESH container (built like the parent, no specialist yet), sidecar FIRST.

    Refuses a missing or tampered sidecar, a file whose sha256 differs from the sidecar, a plan digest that differs
    from the fresh container's plan, and an optimizer whose group order or state shapes do not match the verified
    binding. Restores ``enabled`` from the sidecar and the optimizer's state and group settings from its file.
    Returns ``(specialist, optimizer, sidecar, plan)``.
    """
    directory = pathlib.Path(directory)
    if not (directory / SIDECAR_FILE).is_file():
        _refuse("SIDECAR_MISSING", str(directory / SIDECAR_FILE))
    sidecar = sidecar_from_json((directory / SIDECAR_FILE).read_text())
    if not (directory / PLAN_FILE).is_file():
        _refuse("SIDECAR_MISSING", PLAN_FILE)
    plan = plan_from_json((directory / PLAN_FILE).read_text())
    validate_sidecar(sidecar, expected_plan_digest=plan.plan_digest)
    for file_name, expected in sidecar["files"].items():
        path = directory / file_name
        if not path.is_file():
            _refuse("SIDECAR_MISSING", file_name)
        if file_sha256(path) != expected:
            _refuse("SIDECAR_MISMATCH", file_name + " sha256 differs from the sidecar")
    specialist, fresh_plan, mapping, _ = attach_specialist(
        container, init_seed=sidecar["init_seed"], parent_checkpoint_sha256=plan.parent_checkpoint_sha256,
        parent_cursor=plan.parent_cursor, hidden=sidecar["hidden"], device=device)
    if fresh_plan.plan_digest != plan.plan_digest:
        _refuse("PLAN_DIGEST_MISMATCH", "the fresh container's plan differs from the plan on disk")
    state = torch.load(directory / GROWN_STATE_FILE, map_location=device, weights_only=True)
    container.load_state_dict(state, strict=True)
    specialist.enabled = sidecar["enabled"]
    params = list(container.parameters())
    names = bind_group_parameters(params, container.named_parameters())
    if list(names) != list(sidecar["optimizer_parameter_names"]):
        _refuse("OPTIMIZER_BINDING_INVALID", "the fresh container's verified group order differs from the sidecar")
    saved = torch.load(directory / GROWN_OPTIMIZER_FILE, map_location=device, weights_only=True)
    if len(saved["param_groups"]) != 1 or len(saved["param_groups"][0]["params"]) != len(params):
        _refuse("OPTIMIZER_STATE_INCOMPATIBLE", "saved optimizer group does not match the verified group")
    named = dict(container.named_parameters())
    for index, entry in saved["state"].items():
        _state_compatible(entry, named[names[int(index)]], names[int(index)])
    optimizer = torch.optim.AdamW(params, foreach=False, fused=False, capturable=False)
    optimizer.load_state_dict(saved)  # restores state AND the saved group settings onto the single group
    saved_settings = {k: v for k, v in saved["param_groups"][0].items() if k != "params"}
    settings_preserved(saved_settings, optimizer.param_groups[0])
    return specialist, optimizer, sidecar, plan
