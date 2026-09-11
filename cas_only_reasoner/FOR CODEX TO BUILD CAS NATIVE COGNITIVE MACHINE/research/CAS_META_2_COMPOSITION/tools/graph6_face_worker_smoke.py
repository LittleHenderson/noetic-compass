"""Smoke-run the whole face-grounding worker from the built package. NOT a measurement.

Two paid attempts died on the instance in code that a local run would have caught:
a synthesised fitting corpus the codec refuses, and a gradient check that scored a
task its learner had not been indexed with. The pure-Python halves were rehearsed;
the torch-touching half was not, although the standing order sanctions the local GPU
for exactly this.

So this runs the **whole worker body** - the packaged one, from the built
``source.zip`` - on the local RTX 4070, with the schedule truncated to a handful of
episodes. It exercises the encoder fit, the framework build, the representation
checks, the gradient check, batched teaching, the checkpoint write/read/verify
round trip, both panel passes and the delivery files.

Boundaries, stated so no output can be mistaken for a result:

* local development GPU, permitted for smoke and development only; every
  claim-bearing run stays on AWS;
* the schedule is truncated, so no number here describes learning and none is
  reported as a measurement;
* no provider, no reservation, no upload.

Usage:

    ~/venvs/cas-gpu/Scripts/python.exe tools/graph6_face_worker_smoke.py \
        records/.../face_grounding_001/candidate_package_001/source.zip
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

EVENTS_PER_CONDITION = 8          # one batch, one optimizer update
CONDITIONS = ("cfc_stable_cues", "cfc_neutral_cue")
PANEL_ITEMS = 24                  # a sample, so both panel passes stay quick


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("usage: graph6_face_worker_smoke.py <source.zip>")
    archive = Path(argv[0]).resolve()
    root = Path(tempfile.mkdtemp(prefix="cas-face-smoke-")) / "package"
    root.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zipped:
        zipped.extractall(root)
    sys.path.insert(0, str(root / "research" / "CAS_META_2_COMPOSITION"))

    wheels = sorted(str(path) for path in root.rglob("*.whl"))
    target = Path(tempfile.mkdtemp(prefix="cas-face-smoke-wheels-"))
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                    "--disable-pip-version-check", "--no-deps",
                    "--target", str(target), *wheels], check=True)
    sys.path.insert(0, str(target))

    import torch

    from cas_meta2.graph_teaching import face_evaluation as evaluation
    from cas_meta2.graph_teaching import face_worker as worker

    device = "cuda" if torch.cuda.is_available() else "cpu"
    results = root / "results"
    results.mkdir(exist_ok=True)
    artifacts = results / "artifacts"
    artifacts.mkdir(exist_ok=True)

    # a bounded panel: the smoke measures the code path, not the panel
    built = __import__("cas_meta2.graph_teaching.face_corpus",
                       fromlist=["families"]).families()
    panel = evaluation.panel(built)[:PANEL_ITEMS]
    config = {"schema": "cas.cube-face-worker-config/1", "job": "local-smoke",
              "conditions": list(CONDITIONS), "batch_size": EVENTS_PER_CONDITION,
              "event_limit_per_condition": EVENTS_PER_CONDITION,
              "encoder_seed": 20260909, "seed": 20260912, "learning_rate": 0.003,
              "max_wall_seconds_per_condition": 600.0}

    original_panel = evaluation.panel
    evaluation.panel = lambda built=None: panel
    try:
        report = worker.run(config, torch=torch, device=device, results=results,
                            artifacts=artifacts, outbound=None)
    finally:
        evaluation.panel = original_panel

    envelope = json.loads((results / "result.json").read_bytes())
    summary = {
        "boundary": ("local development GPU, truncated schedule, no provider, no "
                     "reservation, no measurement"),
        "device": device,
        "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "torch": torch.__version__,
        "package": {"archive": archive.name,
                    "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()},
        "checks": report["checks"],
        "conditions": envelope["conditions"],
        "envelope_status": envelope["status"],
        "artifacts": [entry["name"] for entry in envelope["artifacts"]],
        "result_sha256": hashlib.sha256((results / "result.json").read_bytes()).hexdigest(),
        "sidecar_matches": (results / "result.json.sha256").read_text().strip()
        == hashlib.sha256((results / "result.json").read_bytes()).hexdigest(),
        "measurements_written": (results / "measurements.json").is_file(),
        "artifact_manifest_written": (artifacts / "manifest.json").is_file(),
    }
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    print("SMOKE ONLY - not a measurement, not claim-bearing, local GPU.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
