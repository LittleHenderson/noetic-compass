"""schedule.py -- the FROZEN run schedule as executable law (GATE 1A.2 section 5).

The expected receipt set is DERIVED from the signed RUN_SCHEDULE manifest (its
sha256 is bound by the execution approval as run_schedule_sha256) -- never a
hardcoded `len(receipts) == 25`. For each required (kind, arm, seed[, layer])
exactly one successful receipt is demanded; everything else is refused by name.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


class ScheduleViolation(RuntimeError):
    pass


def _fail(msg):
    raise ScheduleViolation(f"SCHEDULE_VIOLATION: {msg}")


class RunSchedule:
    def __init__(self, manifest: dict, raw_bytes: bytes):
        self.manifest = manifest
        self.sha256 = hashlib.sha256(raw_bytes).hexdigest()
        self.arms = list(manifest["arms"])
        self.seeds = list(manifest["claim_bearing_seeds"])
        self.updates_per_run = int(manifest["updates_per_run"])
        self.cache_version = manifest["cache_version"]
        self.parameter_count_tolerance = float(manifest["parameter_count_tolerance"])
        dup = manifest["duplicate_run_policy"]
        self.duplicates = [(dup["arm"], dup["seed"])] * int(dup["count"])
        sel = manifest["layer_selection_runs"]
        self.layer_selection = [(sel["arm"], sel["seed"], layer)
                                for layer in sel["candidate_layers"]]

    @classmethod
    def load(cls, path: Path) -> "RunSchedule":
        raw = Path(path).read_bytes()
        return cls(json.loads(raw.decode("utf-8")), raw)

    def expected_claim_bearing(self):
        """The exact required (arm, seed) set, derived from the schedule."""
        return [(a, s) for a in self.arms for s in self.seeds]

    def expected_total_runs(self) -> int:
        return (len(self.layer_selection) + len(self.expected_claim_bearing())
                + len(self.duplicates))

    def validate_claim_bearing_receipts(self, receipts, *, selected_layer: int,
                                        expected_commit: str,
                                        expected_model_revision: str,
                                        expected_container_digest: str):
        """Refuse every malformed receipt set (section 5's named refusals).
        Each receipt must be a dict with: arm, seed, status, update_count,
        selected_layer, checkpoint_sha256, cache_manifest_sha256,
        model_revision_sha, container_image_digest, package_commit_sha."""
        if receipts is None:
            _fail("receipt list is None")
        seen = {}
        for i, r in enumerate(receipts):
            if r is None:
                _fail(f"receipt {i} is None")
            if not isinstance(r, dict):
                _fail(f"receipt {i} is not an object")
            key = (r.get("arm"), r.get("seed"))
            if key in seen:
                _fail(f"duplicate receipt for arm/seed {key}")
            seen[key] = r
        expected = self.expected_claim_bearing()
        missing = [k for k in expected if k not in seen]
        if missing:
            _fail(f"missing receipts for {missing[:5]}")
        extra = [k for k in seen if k not in expected]
        if extra:
            _fail(f"extra receipts for unscheduled arm/seed {extra[:5]}")
        for key, r in sorted(seen.items(), key=lambda kv: str(kv[0])):
            if r.get("status") != "SUCCESS":
                _fail(f"{key}: receipt status {r.get('status')!r} is not SUCCESS")
            if r.get("update_count") != self.updates_per_run:
                _fail(f"{key}: update_count {r.get('update_count')!r} != "
                      f"scheduled {self.updates_per_run}")
            if r.get("selected_layer") != selected_layer:
                _fail(f"{key}: selected_layer {r.get('selected_layer')!r} != "
                      f"frozen L*={selected_layer}")
            for field in ("checkpoint_sha256", "cache_manifest_sha256"):
                v = r.get(field, "")
                if not isinstance(v, str) or len(v) != 64:
                    _fail(f"{key}: {field} missing or malformed")
            if r.get("model_revision_sha") != expected_model_revision:
                _fail(f"{key}: wrong model identity")
            if r.get("container_image_digest") != expected_container_digest:
                _fail(f"{key}: wrong container identity")
            if r.get("package_commit_sha") != expected_commit:
                _fail(f"{key}: wrong package commit")
        return {k: seen[k] for k in expected}
