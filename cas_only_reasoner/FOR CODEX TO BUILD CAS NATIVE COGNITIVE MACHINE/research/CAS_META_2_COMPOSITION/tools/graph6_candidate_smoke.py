"""Smoke-run the deployed candidate package on the local GPU. NOT a measurement.

The candidate pilot has three times failed on the instance in ways no local test
had reached: a missing import root, a missing torch environment, and a problem
presentation the frozen encoder cannot parse. This tool closes that gap by
executing the exact code inside a built ``source.zip`` - the same bytes the
launcher uploads - on the local RTX 4070, with both conditions truncated to a few
updates.

Boundaries, stated so no output of this tool can be mistaken for a result:

* it runs the LOCAL development GPU, which the standing order permits for smoke
  and development only; every claim-bearing run stays on AWS;
* it runs a handful of updates, not the frozen 64 per condition, so its numbers
  describe nothing about learning and are never reported as measurements;
* it contacts no provider, creates no reservation, and uploads nothing;
* it proves one thing only: that the deployed code path executes - encoder,
  framework, learner, containment check, checkpoint round trip, probe
  measurement and the run's own bookkeeping.

Usage:

    ~/venvs/cas-gpu/Scripts/python.exe tools/graph6_candidate_smoke.py \
        records/.../candidate_package_006/source.zip
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

UPDATES_PER_CONDITION = 3


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("usage: graph6_candidate_smoke.py <source.zip>")
    archive = Path(argv[0]).resolve()
    if not archive.is_file():
        raise SystemExit("no such archive: " + str(archive))

    root = Path(tempfile.mkdtemp(prefix="cas-smoke-")) / "package"
    root.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zipped:
        zipped.extractall(root)
    sys.path.insert(0, str(root / "research" / "CAS_META_2_COMPOSITION"))

    # The deployed worker installs these frozen wheels into its venv. This
    # installs the same wheel files into a scratch target, so the shared
    # development venv is left alone.
    wheels = sorted(str(path) for path in root.rglob("*.whl"))
    target = Path(tempfile.mkdtemp(prefix="cas-smoke-wheels-"))
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                    "--disable-pip-version-check", "--no-deps",
                    "--target", str(target), *wheels], check=True)
    sys.path.insert(0, str(target))

    import torch

    from cas_meta2.graph_teaching import (adapter, candidate_experiment as ce,
                                          candidate_run as cr,
                                          real_framework as rf)

    # ``gpu_adapter._cuda`` is guarded to Linux worker instances on purpose, so
    # the smoke tool binds the device itself.
    device = "cuda" if torch.cuda.is_available() else "cpu"
    report = {"archive": archive.name, "device": device,
              "torch": torch.__version__,
              "gpu": (torch.cuda.get_device_name(0) if device == "cuda" else None),
              "updates_per_condition": UPDATES_PER_CONDITION,
              "boundary": ("local development GPU, truncated updates, no provider, "
                           "no reservation, no measurement")}

    inputs = ce.build_inputs(ordering_mode="declared")
    records, probe = inputs["records"], inputs["probe"]
    report["records"], report["probe_questions"] = len(records), len(probe)

    publics = [adapter.public_records(record, "cas")["public"]
               for record in records + probe]
    encoder = rf.build_encoder(torch, publics, d_model=64, seed=20260909,
                               device=device)
    vectors = [encoder["encode_problem"](public) for public in publics]
    report["encoded_problems"] = len(vectors)
    report["problem_vector_dim"] = tuple(vectors[0].shape)

    condition_order = ["checked_component_teaching", "final_answer_only"]
    checkpoints = []

    def framework_factory(seed):
        torch.manual_seed(seed)
        framework = rf.build_graph_training_framework(
            torch, device, seed=20260909, encoder=encoder)
        return framework, framework.build_decompose_model(seed=seed)

    def learner_factory(*, framework, model, arm, records, layout):
        tasks = [layout[record["record_id"]] for record in records]
        learner = rf.GraphLearner(torch, framework, tasks, device, 0.003)
        learner.condition_tag = condition_order.pop(0)
        return learner

    def checkpoint_writer(learner, identity):
        path = root / ("smoke_checkpoint_%s.pt" % learner.condition_tag)
        torch.save({"schema": "cas-graph-training-candidate-checkpoint/1",
                    "condition": learner.condition_tag, "identity": identity,
                    "parameter_order": ce.parameter_order(learner.module),
                    "state": learner.module.state_dict()}, str(path))
        checkpoints.append(path.name)
        return {"path": str(path), "identity": identity}

    def checkpoint_verifier(saved, identity):
        loaded = torch.load(saved["path"], map_location="cpu", weights_only=True)
        return (ce.state_digest(loaded["state"], loaded["parameter_order"]) == identity
                and loaded["identity"] == identity)

    frozen_steps = ce.condition_steps
    ce.condition_steps = (lambda records_, condition:
                          frozen_steps(records_, condition)[:UPDATES_PER_CONDITION])
    try:
        result = ce.launch(run_id="local-smoke-not-a-measurement",
                           records=records, probe=probe, groups=inputs["groups"],
                           framework_factory=framework_factory,
                           learner_factory=learner_factory,
                           authorization={"owner_go": True,
                                          "run_id": "local-smoke-not-a-measurement"},
                           checkpoint_writer=checkpoint_writer,
                           checkpoint_verifier=checkpoint_verifier)
    finally:
        ce.condition_steps = frozen_steps

    report["matched_initial_weights"] = result["matched_initial_weights"]
    report["counters"] = result["counters"]
    report["probe_questions_measured"] = result["probe_questions"]
    report["checkpoints"] = checkpoints
    report["containment"] = {
        condition: payload["containment"]["contained"]
        for condition, payload in result["results"].items()}
    report["checkpoint_verified"] = {
        condition: payload["checkpoint"]["verified"]
        for condition, payload in result["results"].items()}
    report["probe_items_measured"] = {
        condition: payload["probe_measure"].get("after_total")
        for condition, payload in result["results"].items()}
    report["execution_order"] = list(cr.EXECUTION_ORDER)
    print(json.dumps(report, sort_keys=True, indent=2))
    print("SMOKE ONLY - not a measurement, not claim-bearing, local GPU.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
