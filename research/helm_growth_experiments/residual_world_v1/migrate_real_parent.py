"""L2 (restricted) driver: migrate a COPY of an admitted HELM parent checkpoint into a grown candidate.

Owner packet "ORIGINAL HELM - REAL-CHECKPOINT CONNECTION" (2026-09-28). Continues
REAL_CHECKPOINT_INTEGRATION_STEP_20260928. This file lives in Claude's namespace only. It never imports the
scientific learner package, never edits a checkpoint, and never calls a builder itself: the exact production
builders and the guarded loader are INJECTED by the runner job, so the driver binds to the real interfaces without
holding a lease on them (see ``EXACT_BUILDER_INTERFACES``, read from the executing source at ``cd5ce96c``).

What one run does, in order, refusing at the first failure:
  1. preflight: the parent COPY is a regular file whose sha256 equals the declared parent identity; the output
     directory is fresh and not nested with the parent's directory; the device is CUDA (no CPU fallback).
  2. restore the copy through the injected guarded loader (``PointerCourseLearner.restore_checkpoint``, exact
     keyword signature verified at ``pointer_learner.py`` lines 2144-2145 of ``c45f775f``), which itself checks
     sha, run identity, state digests, layout, cursor and RNG.
  3. write ``ROLLBACK_PARENT.json`` naming the unambiguous rollback parent (path, sha256, bytes, cursor).
  4. attach the specialist DISABLED (``attach_specialist``), migrate the AdamW state under the declared exact
     mapping (``migrate_optimizer`` with ``optimizer_config=learner.optimizer_config``).
  5. require the exact-preservation report (every original parameter and optimizer entry equal bit for bit).
  6. optional probe: with the specialist disabled, ``scored_world`` must return the very object ``world_head``
     returns (same object, not merely equal).
  7. write the grown candidate in Claude's format (``save_grown``: state, optimizer, plan, sidecar) plus
     ``REAL_PARENT_MIGRATION_RECORD.json`` with every identity and digest.

Claim boundary, stated in the record itself: this is real-checkpoint MIGRATION (L2). It is NOT the live
forward-path integration (``GraphForward`` at line 1566 still ignores the specialist), NOT training that uses
the specialist (L3), and NOT a measured benefit (L4). The learner object is only mutated in memory (one child
module registered); the parent file, the learner source and the learner's own optimizer are never modified.

Claim state at writing: written, NOT RUN with torch anywhere (no torch in the preparing container). The
pure-Python parts (preflight, rollback and record assembly) have local tests; the torch path has reserved GPU
tests on a labeled test-double loader in ``numeric_gpu/test_migrate_real_parent_numeric.py``.
"""

import hashlib
import json
import pathlib
import re

from growth_migration_plan import (GROWN_OPTIMIZER_FILE, GROWN_STATE_FILE, PLAN_FILE, RECORDED_INIT_SEED,
                                   SCIENTIFIC_SOURCE, SIDECAR_FILE, SPECIALIST_HIDDEN, WORLD_CANDIDATE_WIDTH,
                                   canonical, file_sha256)

DRIVER_SCHEMA = "cas.growth.world-residual-specialist.real-parent-migration/0.1"
ROLLBACK_FILE = "ROLLBACK_PARENT.json"
RECORD_FILE = "REAL_PARENT_MIGRATION_RECORD.json"
GROWN_DIR = "grown_candidate"
GROWN_FILES = (GROWN_STATE_FILE, GROWN_OPTIMIZER_FILE, PLAN_FILE, SIDECAR_FILE)

# Read from the executing continuation source at cd5ce96ca0a64e0dbe82562bedf565e1bf66bfc7 (research/helm_continuation/
# worker.py lines 50 and 79-83; continuation.py lines 147-160). The runner job builds these and passes them in.
EXACT_BUILDER_INTERFACES = {
    "source_commit": "cd5ce96ca0a64e0dbe82562bedf565e1bf66bfc7",
    "legacy_module": "from cncm import typed_pointer_worker as w; legacy = w.pointer_module  (worker.py 50, 66)",
    "framework": "w.matched._framework(torch, device, <source_seed>)  (worker.py 83; 20260919 for seed 19)",
    "encoder": "w.encoder_module.build_frozen_typed_encoder(torch, tokenizer, seed=w.contract.DESIGN['encoder_seed'], "
               "d_model=64, device=device)  (worker.py 81-82)",
    "loader": "legacy.PointerCourseLearner.restore_checkpoint(torch, framework, encoder, path=..., expected_sha256=..., "
              "expected_run_identity_digest=..., device=device, expected_learnable_names=...)  (pointer_learner.py 2144-2145)",
    "preflight_in_job": "w._preflight(root, attestor, runtime) and w.contract.load_material(root) as in worker.py 52-54",
    "note": "the driver calls only `restore(...)` with the loader's exact keywords; framework and encoder are opaque to it",
}
LEARNER_INTERFACE = ("module", "optimizer", "optimizer_config", "cursor", "model_revision", "run_identity_digest")
CLAIM_BOUNDARY = {
    "level": "L2_REAL_CHECKPOINT_MIGRATION_RESTRICTED",
    "forward_path_integration": "NOT_DONE: GraphForward (pointer_learner.py line 1566) still calls world_head and ignores the specialist",
    "training_uses_specialist": False,
    "measured_task_benefit": "NO_CLAIM",
    "grown_candidate_format": "Claude sidecar format (save_grown); NOT a learner checkpoint; the learner cannot restore it (POINTER_CHECKPOINT_LAYOUT)",
}
DRIVER_REFUSALS = (
    "PARENT_COPY_NOT_A_FILE", "PARENT_COPY_SHA_MISMATCH", "IDENTITY_FIELD_INVALID", "OUTPUT_DIR_NOT_FRESH",
    "OUTPUT_DIR_NESTED_WITH_PARENT", "GPU_REQUIRED", "LEARNER_INTERFACE_MISSING", "RESTORED_IDENTITY_MISMATCH",
    "PARENT_LAYOUT_MISMATCH", "SPECIALIST_NOT_DISABLED", "REAL_PARENT_PRESERVATION_FAILED",
    "FORWARD_PATH_NOT_IDENTICAL", "PROBE_BATCH_INVALID", "RECORD_DIGEST_MISMATCH",
)
_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")


class DriverRefused(ValueError):
    def __init__(self, code, detail=""):
        if code not in DRIVER_REFUSALS:
            raise ValueError("UNKNOWN_DRIVER_REFUSAL_CODE:" + str(code))
        self.code = code
        self.detail = detail
        super().__init__(code + (": " + detail if detail else ""))


def _refuse(code, detail=""):
    raise DriverRefused(code, detail)


def _digest(body):
    body = dict(body)
    body.pop("digest", None)
    return hashlib.sha256(canonical(body)).hexdigest()


def _nested(a, b):
    a, b = pathlib.Path(a).resolve(), pathlib.Path(b).resolve()
    return a == b or a in b.parents or b in a.parents


def preflight(*, parent_copy_path, expected_sha256, expected_run_identity_digest, expected_learnable_names, out_dir,
              device, init_seed=RECORDED_INIT_SEED, hidden=SPECIALIST_HIDDEN):
    """Pure Python. Everything that can be refused before any torch object exists. Returns the parent identity."""
    for label, value in (("expected_sha256", expected_sha256), ("expected_run_identity_digest", expected_run_identity_digest)):
        if type(value) is not str or _HEX64.match(value) is None:
            _refuse("IDENTITY_FIELD_INVALID", label + " must be 64 lowercase hex characters")
    names = tuple(expected_learnable_names) if expected_learnable_names is not None else ()
    if not names or any(type(n) is not str or not n for n in names) or len(set(names)) != len(names):
        _refuse("IDENTITY_FIELD_INVALID", "expected_learnable_names must be a non-empty tuple of unique names")
    if type(init_seed) is not int or type(hidden) is not int or not 1 <= hidden <= 256:
        _refuse("IDENTITY_FIELD_INVALID", "init_seed must be int and hidden in 1..256")
    if type(device) is not str or not device.startswith("cuda"):
        _refuse("GPU_REQUIRED", "device must name a CUDA device; no CPU fallback")
    parent = pathlib.Path(parent_copy_path)
    if not parent.is_file() or parent.is_symlink():
        _refuse("PARENT_COPY_NOT_A_FILE", str(parent))
    out = pathlib.Path(out_dir)
    if out.exists():
        _refuse("OUTPUT_DIR_NOT_FRESH", str(out))
    if _nested(parent.parent, out):
        _refuse("OUTPUT_DIR_NESTED_WITH_PARENT", "the grown candidate must never live beside or inside the parent copy")
    actual = file_sha256(parent)
    if actual != expected_sha256:
        _refuse("PARENT_COPY_SHA_MISMATCH", "copy sha256 %s… differs from the declared parent %s…" % (actual[:12], expected_sha256[:12]))
    return {"path": str(parent.resolve()), "sha256": actual, "bytes": parent.stat().st_size,
            "run_identity_digest": expected_run_identity_digest, "learnable_names": list(sorted(names)),
            "learnable_names_count": len(names)}


def rollback_record(parent, *, cursor, model_revision):
    """The unambiguous rollback parent: the copy's identity plus the cursor the loader reported. Digest-sealed."""
    if type(cursor) is not int or type(model_revision) is not int or cursor != model_revision or cursor < 0:
        _refuse("RESTORED_IDENTITY_MISMATCH", "cursor and model_revision must be equal non-negative ints")
    body = {"schema": DRIVER_SCHEMA + "#rollback", "rollback_parent": dict(parent), "cursor": cursor,
            "model_revision": model_revision, "rule": "roll back = discard the grown candidate directory and continue from "
            "this exact file; the driver never modifies it", "scientific_source": SCIENTIFIC_SOURCE}
    body["digest"] = _digest(body)
    return body


def build_record(*, parent, rollback, specialist, plan_digest, mapping_summary, preservation, probe, grown_files,
                 sidecar_digest, venue):
    body = {"schema": DRIVER_SCHEMA, "scientific_source": SCIENTIFIC_SOURCE, "parent": dict(parent),
            "rollback_digest": rollback["digest"], "specialist": dict(specialist), "plan_digest": plan_digest,
            "mapping": dict(mapping_summary), "preservation": dict(preservation), "probe": probe,
            "grown_candidate": {"directory": GROWN_DIR, "files_sha256": dict(grown_files), "sidecar_digest": sidecar_digest},
            "claim_boundary": dict(CLAIM_BOUNDARY), "venue": venue if venue is not None else "UNDECLARED",
            "builder_interfaces": dict(EXACT_BUILDER_INTERFACES)}
    body["digest"] = _digest(body)
    return body


def verify_record(record):
    if type(record) is not dict or record.get("schema") != DRIVER_SCHEMA or record.get("digest") != _digest(record):
        _refuse("RECORD_DIGEST_MISMATCH")
    return record


def run_real_parent_migration(*, torch, restore, framework, encoder, parent_copy_path, expected_sha256,
                              expected_run_identity_digest, expected_learnable_names, device, out_dir,
                              init_seed=RECORDED_INIT_SEED, hidden=SPECIALIST_HIDDEN, probe_batch=None, venue=None):
    """The whole L2 step. ``restore`` is the guarded loader; ``framework``/``encoder`` are the job-built objects."""
    parent = preflight(parent_copy_path=parent_copy_path, expected_sha256=expected_sha256,
                       expected_run_identity_digest=expected_run_identity_digest,
                       expected_learnable_names=expected_learnable_names, out_dir=out_dir, device=device,
                       init_seed=init_seed, hidden=hidden)
    if probe_batch is not None and (not torch.is_tensor(probe_batch) or probe_batch.dim() != 2
                                    or int(probe_batch.shape[1]) != WORLD_CANDIDATE_WIDTH
                                    or not bool(torch.isfinite(probe_batch).all())):
        _refuse("PROBE_BATCH_INVALID", "probe_batch must be a finite (n, %d) tensor" % WORLD_CANDIDATE_WIDTH)
    import world_residual_specialist as wrs  # torch-bearing module, imported only now
    learner = restore(torch, framework, encoder, path=parent["path"], expected_sha256=expected_sha256,
                      expected_run_identity_digest=expected_run_identity_digest, device=device,
                      expected_learnable_names=list(expected_learnable_names))
    missing = [name for name in LEARNER_INTERFACE if not hasattr(learner, name)]
    if missing:
        _refuse("LEARNER_INTERFACE_MISSING", ", ".join(missing))
    if learner.run_identity_digest != expected_run_identity_digest:
        _refuse("RESTORED_IDENTITY_MISMATCH", "run_identity_digest")
    if sorted(learner.module.state_dict()) != parent["learnable_names"]:
        _refuse("PARENT_LAYOUT_MISMATCH", "restored state-dict names differ from the declared learnable names")
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    rollback = rollback_record(parent, cursor=int(learner.cursor), model_revision=int(learner.model_revision))
    (out / ROLLBACK_FILE).write_text(json.dumps(rollback, indent=1, sort_keys=True) + "\n")
    old_tensors = {name: p.detach().clone() for name, p in learner.module.named_parameters()}
    specialist, plan, mapping, old_named = wrs.attach_specialist(
        learner.module, init_seed=init_seed, parent_checkpoint_sha256=expected_sha256,
        parent_cursor=int(learner.cursor), hidden=hidden, device=device)
    if specialist.enabled is not False:
        _refuse("SPECIALIST_NOT_DISABLED")
    new_optimizer, log = wrs.migrate_optimizer(learner.optimizer, learner.module, mapping=mapping,
                                               old_named_parameters=old_named, optimizer_config=learner.optimizer_config)
    preservation = wrs.preservation_report(old_tensors, learner.module, learner.optimizer, new_optimizer, mapping)
    if not (preservation["parameters_exactly_equal"] and preservation["optimizer_state_exactly_equal"]):
        _refuse("REAL_PARENT_PRESERVATION_FAILED", json.dumps({k: preservation[k] for k in
                ("parameters_exactly_equal", "optimizer_state_exactly_equal")}))
    probe = None
    if probe_batch is not None:
        with torch.no_grad():
            base = learner.module.world_head(probe_batch)
            scored = wrs.scored_world(learner.module, probe_batch)
        probe = {"rows": int(probe_batch.shape[0]), "same_object": scored is base, "torch_equal": bool(torch.equal(scored, base))}
        if not probe["same_object"]:
            _refuse("FORWARD_PATH_NOT_IDENTICAL", "a disabled specialist must return the base object itself")
    sidecar = wrs.save_grown(learner.module, new_optimizer, plan, out / GROWN_DIR)
    grown_files = {name: file_sha256(out / GROWN_DIR / name) for name in GROWN_FILES}
    record = build_record(
        parent=parent, rollback=rollback,
        specialist={"init_seed": init_seed, "hidden": hidden, "enabled": False,
                    "new_parameter_count": plan.expected_new_parameter_count, "new_names": list(plan.new_names)},
        plan_digest=plan.plan_digest,
        mapping_summary={"carried_by_name": len(log["carried_by_name"]), "original_without_state": log["original_without_state"],
                         "new_with_zero_state": log["new_with_zero_state"], "settings_preserved": log["settings_preserved"],
                         "old_group_parameters": len(log["old_group_names"]), "new_group_parameters": len(log["new_group_names"])},
        preservation=preservation, probe=probe, grown_files=grown_files, sidecar_digest=sidecar["sidecar_digest"],
        venue=venue)
    (out / RECORD_FILE).write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    return verify_record(record)
