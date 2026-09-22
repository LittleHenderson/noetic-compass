"""Read-only Q4 environment identity; never import torch or call a device.

Distribution versions alone can hide a CPU-only Torch build. Read its literal
version metadata and bind an optional CNCM-local authorization dependency
directory byte-for-byte. This establishes file identity, not CUDA readiness or
permission to execute. An existing owner trust anchor remains required.
"""
from __future__ import annotations

import ast
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import sys

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
# Match the renderer's original CNCM homebase boundary. A shorter dependency
# path here avoids Windows DLL-loader path limits in deeply nested worktrees.
HOME = next((p for p in reversed(PROJECT_ROOT.parents)
             if p.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"), PROJECT_ROOT)
DEPENDENCY_ENV = "HELM_Q4_AUTH_DEPENDENCY_DIR"
MAX_DEPENDENCY_ENTRIES = 4096
MAX_DEPENDENCY_BYTES = 64 * 1024 * 1024
MAX_DEPENDENCY_FILE_BYTES = 32 * 1024 * 1024


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def dependency_manifest():
    """Hash every file in the explicitly selected CNCM dependency directory.

    Extra files count too: adding a module cannot silently preserve the plan's
    dependency identity. No bytecode, installer, or package code is executed.
    """
    configured = os.environ.get(DEPENDENCY_ENV)
    if configured is None:
        return None
    original = Path(configured)
    if not configured or not original.is_absolute() or original.is_symlink():
        raise ValueError("Q4_AUTH_DEPENDENCIES: explicit non-symlink absolute directory required")
    root = original.resolve()
    if not root.is_relative_to(HOME.resolve()) or not root.is_dir():
        raise ValueError("Q4_AUTH_DEPENDENCIES: directory must be inside the CNCM homebase")
    declared_path = os.environ.get("PYTHONPATH", "")
    if declared_path != str(root):
        raise ValueError("Q4_AUTH_DEPENDENCIES: PYTHONPATH must name only the bound dependency directory")
    rows, total, count = [], 0, 0
    for path in root.rglob("*"):
        count += 1
        if count > MAX_DEPENDENCY_ENTRIES or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Q4_AUTH_DEPENDENCIES: entry bound or path isolation failed")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("Q4_AUTH_DEPENDENCIES: ordinary files required")
        size = path.stat().st_size
        if size > MAX_DEPENDENCY_FILE_BYTES or total + size > MAX_DEPENDENCY_BYTES:
            raise ValueError("Q4_AUTH_DEPENDENCIES: byte budget exceeded")
        with path.open("rb") as stream:
            raw = stream.read(size + 1)
        if len(raw) != size:
            raise ValueError("Q4_AUTH_DEPENDENCIES: file changed while reading")
        total += size
        rows.append({"path": path.relative_to(root).as_posix(), "bytes": size, "sha256": _sha(raw)})
    if not rows:
        raise ValueError("Q4_AUTH_DEPENDENCIES: dependency directory is empty")
    rows.sort(key=lambda item: item["path"])
    body = {"schema": "helm-cas-expression-lab.q4-auth-dependencies/0.1", "root": str(root),
            "pythonpath": declared_path, "files": rows, "total_bytes": total}
    return {**body, "manifest_sha256": _sha(_canonical(body))}


def _torch_build():
    try:
        distribution = metadata.distribution("torch")
        path = Path(distribution.locate_file("torch/version.py"))
    except metadata.PackageNotFoundError:
        return {"status": "UNAVAILABLE", "torch_imported": False}
    try:
        with path.open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError("version metadata exceeds limit")
        tree = ast.parse(raw.decode("utf-8"))
        fields = {}
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in {"__version__", "cuda", "hip"}:
                    value = ast.literal_eval(node.value)
                    if value is not None and type(value) is not str:
                        raise ValueError("unexpected version metadata type")
                    fields[target.id] = value
        if set(fields) != {"__version__", "cuda", "hip"}:
            raise ValueError("incomplete version metadata")
    except (OSError, UnicodeError, ValueError, SyntaxError) as exc:
        return {"status": "UNVERIFIED_BUILD_METADATA", "torch_imported": False,
                "reason": str(exc)[:160]}
    return {"status": "CUDA_BUILD_RUNTIME_UNPROBED" if fields["cuda"] else "NO_CUDA_BUILD",
            "version_source": str(path.resolve()), "version_source_sha256": _sha(raw),
            "version": fields["__version__"], "cuda": fields["cuda"], "hip": fields["hip"],
            "torch_imported": False}


def environment_metadata():
    def version(package):
        try:
            return metadata.version(package)
        except metadata.PackageNotFoundError:
            return "UNAVAILABLE"
    bound = dependency_manifest()
    result = {"python": platform.python_version(), "python_executable": sys.executable,
              "torch_distribution": version("torch"), "cryptography_distribution": version("cryptography"),
              "torch_build": _torch_build(), "pythonpath": os.environ.get("PYTHONPATH", ""),
              "auth_dependencies": None}
    if bound is not None:
        packages = []
        for name in ("cryptography", "cffi", "pycparser"):
            try:
                distribution = metadata.distribution(name)
            except metadata.PackageNotFoundError as exc:
                raise ValueError("Q4_AUTH_DEPENDENCIES: required distribution missing: " + name) from exc
            if Path(distribution.locate_file("")).resolve() != Path(bound["root"]):
                raise ValueError("Q4_AUTH_DEPENDENCIES: distribution is outside bound directory: " + name)
            packages.append({"name": name, "version": distribution.version})
        result["auth_dependencies"] = {"root": bound["root"], "manifest_sha256": bound["manifest_sha256"],
                                       "total_bytes": bound["total_bytes"], "file_count": len(bound["files"]),
                                       "distributions": packages}
    return result
