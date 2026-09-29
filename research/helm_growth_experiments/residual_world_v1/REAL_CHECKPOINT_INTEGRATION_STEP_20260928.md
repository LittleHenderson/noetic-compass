# The missing real-checkpoint integration: exact file, functions and minimal change (2026-09-28)

Identified from the exact scientific source `pointer_learner.py` at `c45f775f225dd06cc20cdf313f0a0398486e0d61`
(file sha256 `0f424d8633f01b69d7ed256a8e687a4ba0f99be71ae85732c50d4c8dcd7a81a8`, blob `d07012d4…`, 2337 lines), path
`cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py`.
**Nothing here is implemented in the learner.** Claude holds no source lease on that file and does not widen its
scope into it. This document names the change so a lease can be scoped exactly. JSON twin:
`REAL_CHECKPOINT_INTEGRATION_STEP_20260928.json`.

## Four levels, kept apart

| Level | Needs a learner edit? | State today |
|---|---|---|
| L1 standalone module tests | no | written; 22 pure-Python passed locally; 15 numeric NOT RUN |
| L2 migration of an actual copied HELM checkpoint | **no** for the restricted form below; **yes** for a learner-restorable grown checkpoint | not started; the driver is specified, not written |
| L3 additional training with growth | **yes** (six touch points below) | not started; no lease |
| L4 measured task benefit | yes (L3) plus a control and a preregistered readout | no claim |

## Why a grown container cannot enter the learner today (verified lines)

- `_build_container(torch, framework, device, *, analogy_focus_comparison=True, analogy_seed=ANALOGY_INIT_SEED)`
  at line **703** builds the plain container. Its `_PointerContainer.__setattr__` (lines ~745-752) refuses only the
  two analogy names, so registering a `world_specialist` child is allowed by the container itself.
- `PointerCourseLearner.__init__` at line **1762** builds `self.module = _build_container(torch, framework, self.device)`
  at **1777**, checks `POINTER_CONTAINER_SCOPE` (scope = every state-dict name) and builds ONE AdamW group over
  `list(self.module.parameters())` at **1840-1845**. `_registered_names` (line **2323**) requires
  `set(names.values()) == set(module.state_dict())`, which a grown container still satisfies (the specialist's two
  names appear identically in `named_parameters` and `state_dict`).
- `GraphForward` calls `self.model.world_head(candidate)` at line **1566** (width check at **1550-1551**). A
  specialist attached to the container is never consulted by this call.
- `export_checkpoint` at line **2104** writes `learnable_names = sorted(self.module.state_dict())` (**2128**) and
  `init_args` (**2124-2127**) with exactly `optimizer_config, run_context, limits, device, python_seed, root`;
  `_validate_init_args` (line **1722**) refuses any other key set. Nothing records that a specialist exists or whether
  it is enabled.
- `restore_checkpoint` at line **2144** rebuilds a plain container at **2189** and requires
  `container_names == pointer_names` (**2197**, `POINTER_CHECKPOINT_LAYOUT`), then constructs `cls(...)` at
  **2203-2206**, `load_state_dict(strict=True)` at **2207** and `optimizer.load_state_dict` at **2208**. A grown
  checkpoint (two extra names, two extra optimizer entries) is refused at 2197, by design.

So: a grown container can be BUILT from a restored parent without editing the learner, but it cannot be RESTORED or
TRAINED by the learner without the edits below.

## L2, restricted form: no learner edit, needs a GPU job and Codex's builders (the smallest remaining real-model step)

Driver `migrate_real_parent.py` — **written 2026-09-28 (owner packet REAL-CHECKPOINT CONNECTION)**; its steps are the list below. Pure-Python parts passed 9 local cases; the torch path is NOT RUN; a real migration has not started:

1. Inputs: a COPY of an admitted parent checkpoint (never the live seed-19 or seed-18 files), its `expected_sha256`,
   its `expected_run_identity_digest`, the `framework` and `encoder` built the way Codex's worker builds them
   (`cncm.typed_matched_worker._framework`, per the learner's own docstring at 705-707), `device="cuda"`.
2. `learner = PointerCourseLearner.restore_checkpoint(torch, framework, encoder, path=..., expected_sha256=...,
   expected_run_identity_digest=..., device=device, expected_learnable_names=<parent's recorded names>)` — the
   learner's own validation of sha, identity, state digests, layout, cursor and RNG (lines 2160-2233).
3. `old_named = tuple(learner.module.named_parameters())`; `old_tensors = {n: p.detach().clone()}`.
4. `specialist, plan, mapping, old_named = attach_specialist(learner.module, init_seed=RECORDED_INIT_SEED,
   parent_checkpoint_sha256=expected_sha256, parent_cursor=learner.cursor, device=device)` — specialist DISABLED.
5. `new_optimizer, log = migrate_optimizer(learner.optimizer, learner.module, mapping=mapping,
   old_named_parameters=old_named, optimizer_config=learner.optimizer_config)` — the config must equal the group.
6. `report = preservation_report(old_tensors, learner.module, learner.optimizer, new_optimizer, mapping)`; require
   both exact-equality flags; require `scored_world(learner.module, x)` equals `learner.module.world_head(x)`
   bit for bit on a finite probe batch (disabled specialist returns the base object).
7. `save_grown(learner.module, new_optimizer, plan, <out>/grown/)` — Claude's format, plus the plan and sidecar.
   Publish: the report, the sidecar, the plan digest, the file digests, `log["old_group_names"]`.

What this shows if it passes: the migration preserves a REAL parent's parameters and AdamW state exactly and adds
624 zero-contribution scalars. What it does NOT show: that the learner can restore or train the grown state (L3),
or any benefit (L4). The grown files are in Claude's format, not a learner checkpoint.

Dependencies Codex must supply: the parent copy and its two identities; the framework/encoder builder call; a GPU
job after the seed-19 slot releases; a separate finite allowance. Claude launches nothing.

## L3: the minimal learner change, for a lease to scope (six touch points, one file, not implemented)

1. `_build_container` (line 703): add keyword `growth=None`. After the container is built and before `return`,
   `if growth is not None: attach_specialist(container, init_seed=growth["init_seed"], hidden=growth["hidden"],
   parent_checkpoint_sha256=growth["parent_checkpoint_sha256"], parent_cursor=growth["parent_cursor"],
   device=device); container.world_specialist.enabled = growth["enabled"]`. Register LAST so the original order
   stays an unchanged prefix (the property the optimizer migration relies on).
2. `PointerCourseLearner.__init__` (line 1762): accept `growth=None`; pass it to `_build_container` at 1777; keep it
   as `self.growth` (a validated sidecar dict or `None`). The AdamW at 1840 then covers the specialist automatically.
   `run_identity["scope"]` and `initial_model_identity` (1846-1849) already differ for a grown container, so the
   digest is new without adding a field to `RUN_IDENTITY_FIELDS`.
3. `export_checkpoint` (line 2104): add `"growth": deepcopy(self.growth)` to `init_args` (2124). Bump
   `CHECKPOINT_SCHEMA` (line 164, currently `cncm.typed-pointer-checkpoint/0.2`) to a new value for grown
   checkpoints, or record growth inside `init_args` only and keep the schema: the lease decides; versioned together.
4. `_validate_init_args` (line 1722): accept an optional `growth` key; absent means `None` (every existing checkpoint
   stays valid); present means it must validate as a sidecar (`validate_sidecar`, schema-pinned).
5. `restore_checkpoint` (line 2144): `growth = init_args.get("growth")`; build the comparison container at 2189 with
   `growth=growth` so `POINTER_CHECKPOINT_LAYOUT` compares like with like; construct `cls(..., growth=growth)` at
   2203. `strict=True` and the optimizer load then match counts.
6. `GraphForward` (line 1566): `flat = scored_world(self.model, candidate).reshape(-1)`. With no specialist this is
   the identical `world_head(candidate)` call, so ungrown runs are bitwise unchanged; with a disabled specialist the
   base object is returned unchanged; with an enabled one the residual is added.

Beyond the learner, L3 also needs: the continuation seam already identified for seed 18/19 (cursor bounded by
`limits["max_updates"]`, `TYPED_CHECKPOINT_CURSOR` at 2209-2211), a new run identity recorded as such, the
pre-growth checkpoint kept as rollback, and a separate finite allowance. None of this is Claude's to start.

## Boundaries

No live seed-19 source, model, optimizer, outputs or test rules are touched. Not mixed into seed 18's
learning-rate-only pair. No AWS launch by Claude. Growth is not validated at any level by this document.
