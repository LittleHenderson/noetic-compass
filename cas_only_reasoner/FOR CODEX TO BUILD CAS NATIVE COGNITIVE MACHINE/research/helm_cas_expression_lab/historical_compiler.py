"""Pinned pre-CAS-Ohm compiler for historical Q3 and PCBA state checks.

The active language may grow without silently changing historical targets.
The snapshot is verified on every load and never replaced by a nearby checkout.
"""
import hashlib
import importlib.util
from pathlib import Path
import sys
import threading

SHA256_LF = "61ed5a45970459e49a6948282ce4060e7c3d3d3f7042078228bc97ff252b2527"
SNAPSHOT = Path(__file__).resolve().parent / "pinned_sources/compiler_pre_ohm_61ed5a45.py"
_MODULE = None
_LOCK = threading.RLock()


def load_historical_compiler():
    global _MODULE
    raw = SNAPSHOT.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != SHA256_LF:
        raise ValueError("HISTORICAL_COMPILER_PIN_MISMATCH")
    with _LOCK:
        if _MODULE is None:
            name = "_historical_cas_compiler_" + hashlib.sha256(str(SNAPSHOT).encode()).hexdigest()[:16]
            spec = importlib.util.spec_from_file_location(name, SNAPSHOT)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            try:
                exec(compile(raw, str(SNAPSHOT), "exec"), module.__dict__)
            except Exception:
                sys.modules.pop(name, None)
                raise
            _MODULE = module
    return _MODULE


def source_receipt():
    load_historical_compiler()
    return {
        "path": "noetic-compass-scaffold/noetic-compass/api/notation/compiler.py",
        "resolved_from": "pinned_historical_snapshot",
        "snapshot_path": "pinned_sources/compiler_pre_ohm_61ed5a45.py",
        "sha256": SHA256_LF, "hash_policy": "lf-normalised",
        "origin_commit": "4345aa36ab056f9539cad3feb9207bba5356bef4",
    }
