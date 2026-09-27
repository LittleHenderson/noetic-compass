"""ONE optional residual world specialist and its migration code (P1 of PARALLEL-CAPABILITY-01, 2026-09-27).

    score(x) = old_world_score(x) + B · GELU(A · x)

``x`` is the same world-candidate input the source's ``world_head`` consumes (width 38); the output stays one
scalar per row, so the external I/O is preserved. ``A`` is ``Linear(38, SPECIALIST_HIDDEN, bias=False)``
initialized NONZERO from a separately recorded generator; ``B`` is ``Linear(SPECIALIST_HIDDEN, 1, bias=False)``
initialized to ZERO. With ``B = 0`` the initial contribution is exactly 0.0 for finite inputs (see
``growth_migration_plan.TOLERANCES``). Disabled, the module returns the base score object unchanged.

This file requires torch and is reserved for the authorized numerical venue (GPU). It is never imported by the
CPU-dry tests. It does not import, modify or attach to the original learner; ``attach_specialist`` takes any
container that carries a ``world_head`` and registers the specialist as its LAST submodule, which keeps the
original parameter order as an unchanged prefix (the property the by-name optimizer migration relies on).

Claim state: implemented, NOT RUN anywhere at the time of writing (no torch in the preparing container).
No checkpoint is deserialized or mutated by this file; a real migration later copies an admitted parent at a
declared safe boundary and records the plan produced here.
"""

import copy

import torch

from growth_migration_plan import (INIT_POLICY, NEW_PARAMETER_NAMES, PlanRefused, SPECIALIST_HIDDEN,
                                   WORLD_CANDIDATE_WIDTH, build_plan, optimizer_state_mapping)


def _refuse(code, detail=""):
    raise PlanRefused(code, detail)


def fingerprint_rows(module):
    """``name:dtype:shape`` rows over sorted state-dict keys, the same shape as the source's ``_fingerprint``."""
    state = module.state_dict()
    return ["%s:%s:%s" % (name, state[name].dtype, tuple(state[name].shape)) for name in sorted(state)]


class WorldResidualSpecialist(torch.nn.Module):
    """The optional module. ``enabled`` is a plain attribute, not a parameter, so it never enters a checkpoint."""

    def __init__(self, *, init_seed, input_width=WORLD_CANDIDATE_WIDTH, hidden=SPECIALIST_HIDDEN, device="cpu"):
        super().__init__()
        if type(init_seed) is not int:
            _refuse("INIT_SEED_MISSING")
        if type(hidden) is not int or not 1 <= hidden <= 256:
            _refuse("HIDDEN_SIZE_INVALID", repr(hidden))
        if input_width != WORLD_CANDIDATE_WIDTH:
            _refuse("INPUT_WIDTH_INVALID", repr(input_width))
        # A: nonzero, from a forked CPU generator seeded with the recorded seed; the run's shared RNG and the
        # CUDA generators are never touched (the source uses the same mechanism for analogy_head, lines 861-864).
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

    def _check(self, candidate, base_score):
        if not torch.is_tensor(candidate) or candidate.dim() != 2 or int(candidate.shape[1]) != self.input_width:
            _refuse("SPECIALIST_INPUT_INVALID", "candidate must be (n, %d)" % self.input_width)
        if not torch.is_tensor(base_score) or tuple(base_score.shape) != (int(candidate.shape[0]), 1):
            _refuse("SPECIALIST_INPUT_INVALID", "base_score must be (n, 1)")
        if not bool(torch.isfinite(candidate).all()) or not bool(torch.isfinite(base_score).all()):
            _refuse("SPECIALIST_NONFINITE_INPUT")

    def contribution(self, candidate, base_score):
        self._check(candidate, base_score)
        return self.B(self.gelu(self.A(candidate)))

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
    """Register ONE specialist as the container's last submodule and return (specialist, plan, mapping)."""
    if hasattr(container, "world_specialist"):
        _refuse("SPECIALIST_ALREADY_ATTACHED")
    head = getattr(container, "world_head", None)
    if head is None or int(head[0].in_features) != WORLD_CANDIDATE_WIDTH:
        _refuse("WORLD_HEAD_NOT_FOUND", "container.world_head[0].in_features must be %d" % WORLD_CANDIDATE_WIDTH)
    plan = build_plan(fingerprint_rows=fingerprint_rows(container), parent_checkpoint_sha256=parent_checkpoint_sha256,
                      parent_cursor=parent_cursor, init_seed=init_seed, hidden=hidden)
    old_order = [name for name, _ in container.named_parameters()]
    specialist = WorldResidualSpecialist(init_seed=init_seed, hidden=hidden, device=device)
    container.world_specialist = specialist  # registered LAST: the original order stays an unchanged prefix
    new_order = [name for name, _ in container.named_parameters()]
    mapping = optimizer_state_mapping(old_order, new_order)
    after = {name for name, _ in container.named_parameters()} - set(old_order)
    if after != set(NEW_PARAMETER_NAMES):
        _refuse("NEW_NAMES_INVALID", repr(sorted(after)))
    count = sum(p.numel() for name, p in container.named_parameters() if name in after)
    if count != plan.expected_new_parameter_count:
        _refuse("COUNT_MISMATCH", "%d new scalars, plan says %d" % (count, plan.expected_new_parameter_count))
    return specialist, plan, mapping


def migrate_optimizer(old_optimizer, container, *, optimizer_config, mapping):
    """Build the grown AdamW and carry every original parameter's state over BY NAME; new entries deliberately
    start with a zero step and zero moments. Refuses anything but the source's single-group layout."""
    old_state = old_optimizer.state_dict()
    if len(old_state["param_groups"]) != 1:
        _refuse("OPTIMIZER_GROUPS_UNSUPPORTED", "the source keeps one AdamW group")
    params = list(container.parameters())
    new_optimizer = torch.optim.AdamW(params, lr=optimizer_config["learning_rate"],
                                      weight_decay=optimizer_config["weight_decay"],
                                      betas=tuple(optimizer_config["betas"]), eps=optimizer_config["eps"],
                                      foreach=False, fused=False, capturable=False)
    new_state = new_optimizer.state_dict()
    new_state["state"] = {}
    carried, absent = [], []
    for name, row in mapping["preserved"].items():
        entry = old_state["state"].get(row["old_index"])
        if entry is None:
            absent.append(name)  # a parameter AdamW never stepped has no state yet; nothing is invented for it
            continue
        new_state["state"][row["new_index"]] = copy.deepcopy(entry)
        carried.append(name)
    named = dict(container.named_parameters())
    for name, row in mapping["new"].items():
        parameter = named[name]
        new_state["state"][row["new_index"]] = {"step": torch.zeros((), dtype=torch.float32),
                                                "exp_avg": torch.zeros_like(parameter),
                                                "exp_avg_sq": torch.zeros_like(parameter)}
    new_optimizer.load_state_dict(new_state)
    return new_optimizer, {"carried_by_name": carried, "original_without_state": absent,
                           "new_with_zero_state": sorted(mapping["new"])}


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
    return {"parameters_exactly_equal": parameters_equal, "optimizer_state_exactly_equal": state_equal,
            "new_parameter_init": {name: INIT_POLICY[name] for name in NEW_PARAMETER_NAMES}}
