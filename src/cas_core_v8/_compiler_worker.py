"""Fresh-process worker for the frozen CAS v7.7 compatibility compiler.

This file is executed by absolute path with Python safe-path, no-site, and
no-bytecode flags.  It intentionally has no imports from ``cas_core_v8`` so its
dependency surface is the selected Python runtime plus the supplied compiler
bytes.  The parent independently verifies every reported file-backed module.
"""

from __future__ import annotations

import base64
import builtins
import hashlib
import json
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import Any
import unicodedata


PROTOCOL = "cas_core_v8.isolated_compiler_worker.v0.1"
MAX_REQUEST_BYTES = 16 * 1024 * 1024


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _require_clean_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text")
    for character in value:
        if unicodedata.category(character) in {"Cc", "Cf", "Cs"}:
            raise ValueError(f"{field_name} contains a forbidden Unicode character")
    return value


def _load_compiler(compiler_source: bytes) -> ModuleType:
    # The process is fresh for every request, so a fixed private name is both
    # collision-free and deterministic.
    module_name = "_cas_v77_content_addressed_compiler"
    module = ModuleType(module_name)
    module.__file__ = "<content-addressed-cas-v7.7-compiler>"
    module.__package__ = ""
    base_import = builtins.__import__

    def python_only_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name == "cas_engine" or name.startswith("cas_engine."):
            raise ImportError("cas_engine is disabled in the Python-only profile")
        return base_import(name, globals, locals, fromlist, level)

    worker_builtins = dict(vars(builtins))
    worker_builtins["__import__"] = python_only_import
    module.__dict__["__builtins__"] = worker_builtins
    sys.modules[module_name] = module
    try:
        code = compile(
            compiler_source,
            "<content-addressed-cas-v7.7-compiler>",
            "exec",
            dont_inherit=True,
            optimize=0,
        )
        exec(code, module.__dict__)
    finally:
        sys.modules.pop(module_name, None)
    return module


def _source_contains_use(module: ModuleType, source: str) -> bool:
    try:
        tokens = module.lex(source)
    except Exception:
        return False
    return any(
        getattr(getattr(token, "kind", None), "value", None) == "USE"
        or getattr(getattr(token, "kind", None), "name", None) == "USE"
        for token in tokens
    )


def _file_identity(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": str(path.resolve()),
        "raw_sha256": _sha256(raw),
        "raw_bytes": len(raw),
    }


def _loaded_module_dependencies() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for name, module in sorted(sys.modules.items()):
        if name == "_cas_v77_content_addressed_compiler":
            continue
        spec = getattr(module, "__spec__", None)
        origin = getattr(spec, "origin", None)
        module_file = getattr(module, "__file__", None)
        candidate = module_file if isinstance(module_file, str) else origin
        if isinstance(candidate, str) and Path(candidate).is_file():
            identity = _file_identity(Path(candidate))
            records.append(
                {
                    "module_name": name,
                    "origin_kind": "FILE",
                    **identity,
                }
            )
        elif origin in {"built-in", "frozen"}:
            records.append(
                {
                    "module_name": name,
                    "origin_kind": str(origin).upper().replace("-", "_"),
                    "path": None,
                    "raw_sha256": None,
                    "raw_bytes": None,
                }
            )
        else:
            records.append(
                {
                    "module_name": name,
                    "origin_kind": "VIRTUAL",
                    "path": str(origin) if origin is not None else None,
                    "raw_sha256": None,
                    "raw_bytes": None,
                }
            )
    return records


def _runtime_record() -> dict[str, Any]:
    executable = _file_identity(Path(sys.executable))
    worker = _file_identity(Path(__file__))
    implementation_name = sys.implementation.name
    implementation = {
        "cpython": "CPython",
        "ironpython": "IronPython",
        "jython": "Jython",
        "pypy": "PyPy",
    }.get(implementation_name, implementation_name)
    version = ".".join(str(part) for part in sys.version_info[:3])
    if os.name == "nt":
        system = "Windows" if sys.platform == "win32" else sys.platform
        machine = (
            os.environ.get("PROCESSOR_ARCHITEW6432")
            or os.environ.get("PROCESSOR_ARCHITECTURE")
            or "unknown-machine"
        )
    elif hasattr(os, "uname"):
        uname = os.uname()
        system = uname.sysname or sys.platform
        machine = uname.machine or "unknown-machine"
    else:
        system = sys.platform
        machine = "unknown-machine"
    return {
        "implementation": implementation,
        "version": version,
        "platform": system,
        "machine": machine,
        "executable": executable,
        "worker": worker,
        "sys_path": list(sys.path),
        "flags": {
            "isolated": bool(sys.flags.isolated),
            "ignore_environment": bool(sys.flags.ignore_environment),
            "safe_path": bool(sys.flags.safe_path),
            "no_site": bool(sys.flags.no_site),
            "no_user_site": bool(sys.flags.no_user_site),
            "dont_write_bytecode": bool(sys.flags.dont_write_bytecode),
        },
    }


def _emit(payload: dict[str, Any]) -> None:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    sys.stdout.buffer.write(encoded + b"\n")


def main() -> int:
    try:
        # Sample runtime identity before evaluating even the content-addressed
        # compiler.  Compiler code must not be able to alter platform caches or
        # process environment first and thereby influence its own provenance.
        runtime = _runtime_record()
        raw_request = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(raw_request) > MAX_REQUEST_BYTES:
            raise ValueError("request exceeds worker byte limit")
        request = json.loads(
            raw_request.decode("utf-8"), object_pairs_hook=_no_duplicate_object
        )
        expected_fields = {
            "protocol",
            "compiler_source_b64",
            "compiler_raw_sha256",
            "source",
            "source_sha256",
        }
        if not isinstance(request, dict) or set(request) != expected_fields:
            raise ValueError("request shape is not canonical")
        if request["protocol"] != PROTOCOL:
            raise ValueError("worker protocol mismatch")
        source = _require_clean_text(request["source"], "source")
        if _sha256(source.encode("utf-8")) != request["source_sha256"]:
            raise ValueError("source digest mismatch")
        compiler_source = base64.b64decode(
            request["compiler_source_b64"], validate=True
        )
        if _sha256(compiler_source) != request["compiler_raw_sha256"]:
            raise ValueError("compiler digest mismatch")

        module = _load_compiler(compiler_source)
        if _source_contains_use(module, source):
            _emit(
                {
                    "protocol": PROTOCOL,
                    "ok": False,
                    "error_code": "E-COMPAT-UNBOUND-IMPORT",
                    "message": "legacy use imports are forbidden",
                }
            )
            return 3
        artifact = module.compile_expression(source).to_dict()
        if not isinstance(artifact, dict) or artifact.get("engine") != "python":
            raise ValueError("compiler did not remain in the Python-only profile")
        _emit(
            {
                "protocol": PROTOCOL,
                "ok": True,
                "artifact": artifact,
                "runtime": runtime,
                "dependencies": _loaded_module_dependencies(),
                "isolation": {
                    "fresh_process": True,
                    "parent_sys_modules_inherited": False,
                    "external_cas_imports": [],
                    "os_sandboxed": False,
                    "host_os_dependencies_content_addressed": False,
                },
            }
        )
        return 0
    except Exception as exc:
        _emit(
            {
                "protocol": PROTOCOL,
                "ok": False,
                "error_code": "E-COMPAT-WORKER",
                "message": f"{type(exc).__name__}: {exc}",
            }
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
