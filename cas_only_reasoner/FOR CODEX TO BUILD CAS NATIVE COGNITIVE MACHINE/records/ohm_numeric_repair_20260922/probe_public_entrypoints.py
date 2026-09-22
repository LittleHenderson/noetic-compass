"""Exercise the real diagnostic package entry point with fabricated inputs."""
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import types

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / ".git").exists())
SOURCE = "noetic-compass-scaffold/noetic-compass/api/cas_ohm/quantifiers.py"
BASE = "eb9985566bd11a89f485d627186ef0efa7177f02"
sys.path.insert(0, str(ROOT / "noetic-compass-scaffold/noetic-compass"))
q = importlib.import_module("api.cas_ohm")
old = types.ModuleType("old_numeric_signature_reference")
sys.modules[old.__name__] = old
raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{BASE}:{SOURCE}"])
exec(compile(raw, f"{BASE}:{SOURCE}", "exec"), old.__dict__)
public = ["i_pred", "y_hat", "r_total", "r_cap", "delta_current", "r_hidden",
          "maturity_q4", "admissible_trend", "asom", "check_eligibility", "require_eligible"]
signatures = {}
for name in public:
    actual = str(inspect.signature(getattr(q, name)))
    prior = str(inspect.signature(getattr(old, name)))
    assert actual == prior, (name, prior, actual)
    signatures[name] = actual
assert set(old.__all__).issubset(set(q.__all__))
assert q.i_pred(8, 4) == q.y_hat(8, 4) == 2
residual = q.delta_current(0, 2)
assert residual.value == -2 and residual.identifies_mechanism is False
assert isinstance(q.r_hidden(8, 0, 4), q.CensoredResult)
try:
    q.delta_current(100, 0, tolerance=float("nan"))
except ValueError as exc:
    refusal = str(exc)
else:
    raise AssertionError("invalid tolerance emitted a result")
assert q.check_eligibility(q.Region.ACTIVE, False, True, False).admitted is False
record = {
    "schema": "cas.ohm.public-entrypoint-probe/0.1",
    "status": "PASS", "execution_kind": "NEW_SYMBOLIC_PROBE_WITH_FABRICATED_INPUTS",
    "measurement_status": "NO_MEASUREMENT_PERFORMED", "source_ref": "WORKING_TREE_BOUND_BY_SHA256",
    "source_path": SOURCE, "source_sha256": hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest(),
    "entrypoint": "api.cas_ohm", "numeric_policy_version": q.NUMERIC_POLICY_VERSION,
    "public_signatures_unchanged_against": BASE, "signatures": signatures,
    "signed_residual": residual.value, "zero_observation_ratio": "CENSORED",
    "invalid_tolerance_refusal": refusal, "uncalibrated_profile": "NOT_ADMITTED",
    "all_prior_public_exports_retained": True,
    "limits": "A direct package probe does not prove any deployed application imports this module.",
}
(HERE / "PUBLIC_ENTRYPOINT.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
print("PASS: actual diagnostic package exports, signatures, refusal, signed residual and censoring")
