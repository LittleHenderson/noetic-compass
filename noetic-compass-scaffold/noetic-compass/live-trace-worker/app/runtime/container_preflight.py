"""Fail-closed build preflight for the digest-pinned live-worker image.

The immutable Ubuntu/Python stages own the OS and interpreter. One hash-bound
lock owns the complete application, Torch, and CUDA wheel closure. This module
proves those identities, then performs an offline CPU forward pass against the
exact Pythia artifact set that the worker is allowed to report.

Passing this preflight is bounded engineering evidence.  It is not a GPU
receipt, vulnerability waiver, experiment authorization, or Gate 5 closure.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from importlib import metadata
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Any, Callable, Iterable


EXPECTED_PYTHON = (3, 12, 13)
EXPECTED_PLATFORM = ("Linux", "x86_64")
EXPECTED_TORCH = "2.13.0+cu126"
EXPECTED_TRANSFORMERS = "5.14.1"
EXPECTED_CUDA = "12.6"
EXPECTED_LOCKED_DISTRIBUTIONS = 73
EXPECTED_LOCK_SHA256 = (
    "37cc64df8317481f024661c573d4146fa31d27e692c69f311eeb2ff84b793401"
)
EXPECTED_TORCH_REQUIREMENT = (
    "torch @ https://download-r2.pytorch.org/whl/cu126/"
    "torch-2.13.0%2Bcu126-cp312-cp312-manylinux_2_28_x86_64.whl"
    "#sha256=8695f3c6b7966d44560275b90c5c28e5091ba33ddbb1ab33b2173782ca1e9145"
)
DEFAULT_LOCK_PATH = Path("/worker/requirements.txt")
PYTHON_LIB_ROOT = Path("/usr/local/lib/python3.12")
SITE_PACKAGES_ROOT = PYTHON_LIB_ROOT / "site-packages"
PRUNED_OPTIONAL_NATIVE_ARTIFACTS = (
    "nvidia/nvshmem/lib/nvshmem_bootstrap_mpi.so.3",
    "nvidia/nvshmem/lib/nvshmem_bootstrap_pmix.so.3",
    "nvidia/nvshmem/lib/nvshmem_bootstrap_shmem.so.3",
    "nvidia/nvshmem/lib/nvshmem_transport_ibgda.so.3",
    "nvidia/nvshmem/lib/nvshmem_transport_ibdevx.so.3",
    "nvidia/nvshmem/lib/nvshmem_transport_libfabric.so.3",
    "nvidia/nvshmem/lib/nvshmem_transport_ucx.so.3",
    "nvidia/cufile/lib/libcufile_rdma.so.1",
)
ALLOWED_HOST_NATIVE_DEPENDENCIES = {
    "torch/lib/libcaffe2_nvrtc.so": {"libcuda.so.1"},
}
_PIN_RE = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)$")
_DIRECT_RE = re.compile(r"^([A-Za-z0-9_.-]+)\s+@\s+(\S+)$")
_HASH_RE = re.compile(r"^--hash=sha256:[0-9a-f]{64}\s*\\?$")


def _canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def read_locked_versions(path: Path) -> dict[str, str]:
    """Read a deliberately narrow, fully hashed flattened application lock.

    Pip accepts markers, extras, nested includes, indexes, and many other
    requirement forms.  None are part of this image policy.  Every substantive
    line must therefore be either one approved exact requirement or one
    lowercase SHA-256 continuation; an unexplained line is a hard failure.
    """

    text = path.read_text(encoding="utf-8")
    records: dict[str, str] = {}
    current_name: str | None = None
    current_hashes = 0

    def finish_current() -> None:
        nonlocal current_name, current_hashes
        if current_name is not None and current_hashes == 0:
            raise RuntimeError(
                f"application dependency pin is not hash-bound: {current_name}"
            )
        current_name = None
        current_hashes = 0

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _HASH_RE.fullmatch(stripped):
            if current_name is None:
                raise RuntimeError(
                    f"orphan dependency hash at requirements line {line_number}"
                )
            current_hashes += 1
            continue

        finish_current()
        requirement = stripped[:-1].rstrip() if stripped.endswith("\\") else stripped
        match = _PIN_RE.fullmatch(requirement)
        if match is not None:
            raw_name, version = match.group(1), match.group(2)
        else:
            direct_match = _DIRECT_RE.fullmatch(requirement)
            if direct_match is None:
                raise RuntimeError(
                    "dependency lock contains an unapproved or unparsed "
                    f"requirement at line {line_number}"
                )
            direct_requirement = (
                f"{direct_match.group(1)} @ {direct_match.group(2)}"
            )
            if direct_requirement != EXPECTED_TORCH_REQUIREMENT:
                raise RuntimeError(
                    "dependency lock contains an unapproved direct requirement"
                )
            raw_name, version = direct_match.group(1), EXPECTED_TORCH
        name = _canonical_name(raw_name)
        if name in records:
            raise RuntimeError(f"duplicate application dependency pin: {name}")
        records[name] = version
        current_name = name

    finish_current()
    if not records:
        raise RuntimeError("application dependency lock contains no exact pins")
    return records


def _installed_distribution_names(
    distributions: Iterable[metadata.Distribution] | None = None,
) -> set[str]:
    observed: set[str] = set()
    source = metadata.distributions() if distributions is None else distributions
    for distribution in source:
        raw_name = distribution.metadata.get("Name")
        if not raw_name:
            raise RuntimeError("installed distribution is missing canonical Name metadata")
        name = _canonical_name(raw_name)
        if name in observed:
            raise RuntimeError(f"duplicate installed distribution identity: {name}")
        observed.add(name)
    return observed


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_environment(
    lock_path: Path = DEFAULT_LOCK_PATH,
    *,
    python_version: tuple[int, int, int] | None = None,
    platform_identity: tuple[str, str] | None = None,
    version_reader: Callable[[str], str] = metadata.version,
    installed_names_reader: Callable[[], set[str]] = _installed_distribution_names,
    module_finder: Callable[[str], Any] = importlib.util.find_spec,
    torch_module: Any | None = None,
    expected_lock_sha256: str = EXPECTED_LOCK_SHA256,
    expected_locked_distributions: int = EXPECTED_LOCKED_DISTRIBUTIONS,
) -> dict[str, str]:
    """Verify the interpreter and every unified-lock package version."""

    observed_python = python_version or (
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    )
    if observed_python != EXPECTED_PYTHON:
        raise RuntimeError(
            f"container Python must be {EXPECTED_PYTHON}, observed {observed_python}"
        )
    observed_platform = platform_identity or (platform.system(), platform.machine())
    if observed_platform != EXPECTED_PLATFORM:
        raise RuntimeError(
            f"container platform must be {EXPECTED_PLATFORM}, observed {observed_platform}"
        )

    observed_lock_sha256 = _file_sha256(lock_path)
    if observed_lock_sha256 != expected_lock_sha256:
        raise RuntimeError(
            "unified dependency lock SHA-256 differs from the approved image input"
        )

    locked = read_locked_versions(lock_path)
    if len(locked) != expected_locked_distributions:
        raise RuntimeError(
            "unified dependency lock distribution count differs from the approved "
            f"closure: expected {expected_locked_distributions}, observed {len(locked)}"
        )
    required_runtime = {
        "torch": EXPECTED_TORCH,
        "transformers": EXPECTED_TRANSFORMERS,
        "cuda-toolkit": "12.6.3",
        "triton": "3.7.1",
        "nvidia-cudnn-cu12": "9.10.2.21",
        "nvidia-nccl-cu12": "2.29.3",
        "nvidia-nvshmem-cu12": "3.4.5",
    }
    for name, expected in required_runtime.items():
        if locked.get(name) != expected:
            raise RuntimeError(
                f"unified lock must bind {name}=={expected}, observed {locked.get(name)!r}"
            )

    installed_names = {_canonical_name(name) for name in installed_names_reader()}
    if "pip" in installed_names:
        raise RuntimeError("runtime image must not retain pip")
    missing = sorted(set(locked) - installed_names)
    unexpected = sorted(installed_names - set(locked))
    if missing or unexpected:
        raise RuntimeError(
            "installed distribution set differs from the unified lock: "
            f"missing={missing!r}, unexpected={unexpected!r}"
        )

    for name, expected in locked.items():
        observed = version_reader(name)
        if observed != expected:
            raise RuntimeError(
                f"installed {name} version {observed!r} differs from lock {expected!r}"
            )

    try:
        installed_pip = version_reader("pip")
    except (metadata.PackageNotFoundError, KeyError):
        installed_pip = None
    if installed_pip is not None:
        raise RuntimeError(
            f"runtime image must not retain pip, observed version {installed_pip!r}"
        )
    if module_finder("ensurepip") is not None:
        raise RuntimeError("runtime image must not retain ensurepip installer capability")

    if torch_module is None:
        import torch as torch_module  # type: ignore[no-redef]
    observed_cuda = getattr(getattr(torch_module, "version", None), "cuda", None)
    if observed_cuda != EXPECTED_CUDA:
        raise RuntimeError(
            f"unified lock must expose CUDA {EXPECTED_CUDA}, observed {observed_cuda!r}"
        )
    return locked


def _native_library_search_path(site_packages: Path) -> str:
    candidates = {
        path
        for path in site_packages.iterdir()
        if path.is_dir() and path.name.endswith(".libs")
    }
    for relative in ("torch/lib", "triton/_C"):
        path = site_packages / relative
        if path.is_dir():
            candidates.add(path)
    nvidia_root = site_packages / "nvidia"
    if nvidia_root.is_dir():
        candidates.update(
            path for path in nvidia_root.rglob("lib") if path.is_dir()
        )
    return os.pathsep.join(str(path) for path in sorted(candidates))


def _missing_native_sonames(transcript: str) -> set[str]:
    return {
        match.group(1)
        for match in re.finditer(
            r"(?m)^\s*([^\s]+)\s+=>\s+not found\s*$",
            transcript,
        )
    }


def verify_native_library_closure(
    *,
    python_lib_root: Path = PYTHON_LIB_ROOT,
    runner: Callable[..., Any] = subprocess.run,
) -> int:
    """Require every shipped native dependency or one exact host-driver seam."""

    site_packages = python_lib_root / "site-packages"
    for relative in PRUNED_OPTIONAL_NATIVE_ARTIFACTS:
        if (site_packages / relative).exists():
            raise RuntimeError(
                f"out-of-scope cluster/RDMA plugin remains in the image: {relative}"
            )

    roots = (python_lib_root / "lib-dynload", site_packages)
    artifacts = sorted(
        path
        for root in roots
        for path in root.rglob("*")
        if path.is_file() and re.search(r"\.so(?:\.|$)", path.name)
    )
    if not artifacts:
        raise RuntimeError("native-library audit found no shared objects")

    environment = dict(os.environ)
    environment["LD_LIBRARY_PATH"] = _native_library_search_path(site_packages)
    observed_external: dict[str, set[str]] = {}
    for artifact in artifacts:
        completed = runner(
            ["ldd", str(artifact)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            env=environment,
        )
        transcript = f"{completed.stdout}{completed.stderr}"
        missing = _missing_native_sonames(transcript)
        relative = artifact.relative_to(site_packages).as_posix()
        allowed = ALLOWED_HOST_NATIVE_DEPENDENCIES.get(relative, set())
        unexpected = missing - allowed
        if unexpected:
            raise RuntimeError(
                f"native artifact {relative} has unresolved dependencies: "
                f"{sorted(unexpected)!r}"
            )
        if missing:
            observed_external[relative] = missing
        if completed.returncode != 0 and not missing and not any(
            marker in transcript.lower()
            for marker in ("not a dynamic executable", "statically linked")
        ):
            raise RuntimeError(
                f"ldd could not inspect native artifact {relative}: {transcript.strip()}"
            )

    for relative, missing in observed_external.items():
        if missing != ALLOWED_HOST_NATIVE_DEPENDENCIES[relative]:
            raise RuntimeError(
                f"host-native dependency set drifted for {relative}: {sorted(missing)!r}"
            )
    return len(artifacts)


def fetch_model_cache() -> None:
    """Acquire only the commit-pinned files later verified offline."""

    from huggingface_hub import snapshot_download

    from . import model_loader

    snapshot_download(
        repo_id=model_loader.PYTHIA_160M_MODEL_ID,
        revision=model_loader.PYTHIA_160M_REVISION,
        allow_patterns=sorted(model_loader.PYTHIA_160M_ARTIFACTS),
    )


def verify_model_cache() -> None:
    """Load and execute the exact cached Pythia artifacts offline on CPU."""

    import torch
    from huggingface_hub import hf_hub_download
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from . import model_loader

    model_loader._validated_model_artifacts(hf_hub_download)

    tokenizer = AutoTokenizer.from_pretrained(
        model_loader.PYTHIA_160M_MODEL_ID,
        revision=model_loader.PYTHIA_160M_REVISION,
        local_files_only=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_loader.PYTHIA_160M_MODEL_ID,
        revision=model_loader.PYTHIA_160M_REVISION,
        use_safetensors=True,
        dtype=torch.float32,
        attn_implementation="eager",
        local_files_only=True,
    )
    model.eval()
    model_loader._validated_resolved_revision(model)
    model_loader._validate_model_execution_layout(
        model,
        expected_device="cpu",
        expected_dtype="torch.float32",
    )
    if getattr(model.config, "_attn_implementation", None) != "eager":
        raise RuntimeError("target Transformers runtime did not retain eager attention")

    model_loader._validate_runtime_canary(
        torch,
        model,
        tokenizer,
        device="cpu",
    )
    model_loader._validated_model_artifacts(hf_hub_download)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scope",
        choices=("fetch", "environment", "native", "model", "all"),
        default="all",
    )
    args = parser.parse_args(argv)
    if args.scope == "fetch":
        fetch_model_cache()
        print("container model fetch PASS: exact pinned artifact set acquired")
    if args.scope in {"environment", "all"}:
        locked = verify_environment()
        print(f"container environment preflight PASS: {len(locked)} unified packages")
    if args.scope in {"native", "all"}:
        native_artifacts = verify_native_library_closure()
        print(
            "container native-library preflight PASS: "
            f"{native_artifacts} shared objects; libcuda.so.1 host seam only"
        )
    if args.scope in {"model", "all"}:
        verify_model_cache()
        print("container model preflight PASS: exact Pythia identity/API/geometry/numerics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
