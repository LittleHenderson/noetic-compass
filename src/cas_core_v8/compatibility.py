"""Fail-closed compatibility access to the frozen CAS v7.7 compiler.

The legacy compiler executes in a fresh Python process with safe-path, no-site,
no-user-site, and no-bytecode flags.  The process receives the already verified
compiler bytes over stdin.  Its executable, worker, loaded Python modules, and
sanitized environment are content-addressed in the returned execution profile.

This is process isolation, not an operating-system sandbox.  That limitation is
machine-visible in every profile and no compatibility result is an authorization
or a silent translation into CAS/TKS v8 semantics.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from types import MappingProxyType
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from tks_v8_core.category import FiniteArrow, SemigroupoidPath

from .identity import (
    ArtifactIdentity,
    CanonicalizationError,
    FrozenList,
    artifact_identities_match,
    canonical_json_bytes,
    canonical_json_sha256,
    require_ascii_identifier,
    require_canonical_text,
    require_sha256,
    sha256_hex,
)
from .semantics import ResearchBoundary, is_exact_ring4_open


CAS_V77_COMPILER_RAW_CRLF_SHA256 = (
    "065DC4384F7F52D1D8A081DC2D62AF69980F1F6EA9BF9099D22DE776CE05DF87"
)
CAS_V77_COMPILER_CANONICAL_LF_SHA256 = (
    "8169188AD73DF8FC3CA709731B3FB4EA07B2513D38D69CF66D22D64CFE88FF4C"
)
CAS_V77_COMPILER_SOURCE_ID = "SRC-ACTIVE-COMPILER-CURRENT"
CAS_V77_SEMANTIC_PROFILE = "CAS v7.7 operational compatibility only"
CAS_V77_SYNTAX_PROFILE = "cas-v7.7"
PYTHON_ONLY_ENGINE_PROFILE = "cas-v7.7/python-only"
EXECUTION_PROFILE_VERSION = "cas_core_v8.execution_dependency_profile.v0.2"
WORKER_PROTOCOL = "cas_core_v8.isolated_compiler_worker.v0.1"
WORKER_TIMEOUT_SECONDS = 30
WORKER_LAUNCH_POLICY = "cross-process-exclusive-lock-v1"
WORKER_LAUNCH_LOCK_FILENAME = "cas-core-v8-compatibility-worker.lock"
WORKER_LAUNCH_LOCK_TIMEOUT_SECONDS = 90
WORKER_LAUNCH_POLL_MILLISECONDS = 10
WORKER_LAUNCH_POST_RELEASE_YIELD_MILLISECONDS = 10
PROFILE_DIFFERENCE_PATH_LIMIT = 32

_WORKER_THREAD_LOCK = threading.Lock()

# Retained as a narrowly named compatibility constant.  It binds only the
# declared *external CAS* import set; it is not the execution dependency digest.
EMPTY_DEPENDENCY_CLOSURE_SHA256 = canonical_json_sha256(
    {
        "scope": "external-cas-imports-only",
        "engine_profile": PYTHON_ONLY_ENGINE_PROFILE,
        "external_cas_imports": [],
    }
)


def _runtime_identity(
    environment: Mapping[str, str] | None = None,
) -> tuple[str, str, str, str]:
    """Derive runtime labels without WMI, subprocesses, or lazy imports."""

    implementation_name = sys.implementation.name
    implementation = {
        "cpython": "CPython",
        "ironpython": "IronPython",
        "jython": "Jython",
        "pypy": "PyPy",
    }.get(implementation_name, implementation_name)
    version = ".".join(str(part) for part in sys.version_info[:3])
    if os.name == "nt":
        bound_environment = os.environ if environment is None else environment
        system = "Windows" if sys.platform == "win32" else sys.platform
        machine = (
            bound_environment.get("PROCESSOR_ARCHITEW6432")
            or bound_environment.get("PROCESSOR_ARCHITECTURE")
            or "unknown-machine"
        )
    elif hasattr(os, "uname"):
        uname = os.uname()
        system = uname.sysname or sys.platform
        machine = uname.machine or "unknown-machine"
    else:
        system = sys.platform
        machine = "unknown-machine"
    return implementation, version, system, machine


def python_runtime_profile() -> str:
    """Return a human-readable runtime label; profiles bind the actual bytes."""

    return "/".join(_runtime_identity())


class CompatibilityError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _clean_text(value: Any, *, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise CompatibilityError("E-COMPAT-TEXT", f"{field_name} must be nonblank text")
    try:
        require_canonical_text(value, field=field_name)
    except CanonicalizationError as exc:
        raise CompatibilityError("E-COMPAT-TEXT", str(exc)) from exc
    return value


def _strict_sha(value: Any, *, field_name: str) -> str:
    try:
        return require_sha256(value, field=field_name)
    except CanonicalizationError as exc:
        raise CompatibilityError("E-COMPAT-DIGEST", str(exc)) from exc


def _worker_environment() -> dict[str, str]:
    """Return the complete, intentionally tiny child environment."""

    environment: dict[str, str] = {}
    inherited_names = ["SystemRoot", "WINDIR", "COMSPEC"]
    if os.name == "nt":
        # The deterministic runtime-label helper derives the Windows machine
        # label from these process variables without WMI or subprocess probes.
        # Both values are explicit, profile-hashed inputs rather than ambient
        # dependencies.
        inherited_names.extend(
            ("PROCESSOR_ARCHITECTURE", "PROCESSOR_ARCHITEW6432")
        )
    for name in inherited_names:
        value = os.environ.get(name)
        if value is not None:
            environment[name] = value
    environment.update(
        {
            "PYTHONHASHSEED": "0",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        }
    )
    return environment


def _worker_launch_lock_path() -> Path:
    """Return the shared host lock used to bound concurrent worker creation."""

    return (Path(tempfile.gettempdir()) / WORKER_LAUNCH_LOCK_FILENAME).resolve()


@contextmanager
def _serialized_worker_launch(lock_path: Path):
    """Serialize worker creation across threads and cooperating processes.

    Windows can return a child exit code with no stdout or stderr when many
    isolated Python runtimes initialize concurrently.  A process-local lock is
    insufficient because independent test runners can overlap, so the launch
    is also protected by an advisory one-byte lock in the host temporary
    directory.  A crashed holder releases the OS lock automatically.  Lock
    acquisition is bounded and fails closed; this function never retries a
    worker process.
    """

    deadline = time.monotonic() + WORKER_LAUNCH_LOCK_TIMEOUT_SECONDS
    if not _WORKER_THREAD_LOCK.acquire(
        timeout=WORKER_LAUNCH_LOCK_TIMEOUT_SECONDS
    ):
        raise CompatibilityError(
            "E-COMPAT-WORKER-LOCK",
            "timed out acquiring the process-local worker launch lock",
        )
    try:
        try:
            handle = lock_path.open("a+b")
        except OSError as exc:
            raise CompatibilityError(
                "E-COMPAT-WORKER-LOCK",
                f"cannot open worker launch lock {lock_path}: {exc}",
            ) from exc
        with handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\x00")
                handle.flush()
            acquired = False
            while not acquired:
                handle.seek(0)
                try:
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(
                            handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                        )
                    acquired = True
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise CompatibilityError(
                            "E-COMPAT-WORKER-LOCK",
                            "timed out acquiring the cross-process worker launch "
                            f"lock {lock_path}: {exc}",
                        ) from exc
                    time.sleep(WORKER_LAUNCH_POLL_MILLISECONDS / 1000)
            try:
                yield
            finally:
                handle.seek(0)
                try:
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                except OSError as exc:
                    raise CompatibilityError(
                        "E-COMPAT-WORKER-LOCK",
                        f"cannot release worker launch lock {lock_path}: {exc}",
                    ) from exc
                # The advisory lock does not promise fairness.  Keep local
                # contenders paused briefly after release so a process already
                # waiting on the shared lock gets a scheduler opportunity.
                time.sleep(WORKER_LAUNCH_POST_RELEASE_YIELD_MILLISECONDS / 1000)
    finally:
        _WORKER_THREAD_LOCK.release()


class LegacyDiagnosticCode(str, Enum):
    LEGACY_COMPATIBILITY_PROFILE = "LEGACY_COMPATIBILITY_PROFILE"
    UNTYPED_FRACTAL_REQUIRES_BRIDGE = "UNTYPED_FRACTAL_REQUIRES_BRIDGE"
    OVERLOADED_RPM_REQUIRES_TYPE_CHOICE = "OVERLOADED_RPM_REQUIRES_TYPE_CHOICE"


class DependencyOriginKind(str, Enum):
    FILE = "FILE"
    BUILT_IN = "BUILT_IN"
    FROZEN = "FROZEN"
    VIRTUAL = "VIRTUAL"


@dataclass(frozen=True, slots=True)
class EnvironmentBinding:
    name: str
    value: str

    def __post_init__(self) -> None:
        if type(self) is not EnvironmentBinding:
            raise CompatibilityError(
                "E-COMPAT-ENVIRONMENT", "EnvironmentBinding subclasses are not accepted"
            )
        try:
            require_ascii_identifier(self.name, field="environment name")
        except CanonicalizationError as exc:
            raise CompatibilityError("E-COMPAT-ENVIRONMENT", str(exc)) from exc
        try:
            require_canonical_text(self.value, field="environment value")
        except CanonicalizationError as exc:
            raise CompatibilityError("E-COMPAT-ENVIRONMENT", str(exc)) from exc

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "value": self.value}


@dataclass(frozen=True, slots=True)
class DependencyArtifact:
    """One loaded module identity in the fresh compatibility worker."""

    module_name: str
    origin_kind: DependencyOriginKind
    path: str | None
    identity: ArtifactIdentity | None

    def __post_init__(self) -> None:
        if type(self) is not DependencyArtifact:
            raise CompatibilityError(
                "E-COMPAT-DEPENDENCY-PROFILE",
                "DependencyArtifact subclasses are not accepted",
            )
        _clean_text(self.module_name, field_name="dependency module_name")
        if type(self.origin_kind) is not DependencyOriginKind:
            raise CompatibilityError(
                "E-COMPAT-DEPENDENCY-PROFILE", "origin_kind must be typed"
            )
        if self.origin_kind is DependencyOriginKind.FILE:
            if not isinstance(self.path, str) or not Path(self.path).is_absolute():
                raise CompatibilityError(
                    "E-COMPAT-DEPENDENCY-PROFILE",
                    f"file dependency {self.module_name} needs an absolute path",
                )
            _clean_text(self.path, field_name="dependency path")
            if type(self.identity) is not ArtifactIdentity:
                raise CompatibilityError(
                    "E-COMPAT-DEPENDENCY-PROFILE",
                    f"file dependency {self.module_name} needs an ArtifactIdentity",
                )
            resolved = Path(self.path).resolve()
            if not resolved.is_file() or not artifact_identities_match(
                ArtifactIdentity.from_path(resolved), self.identity
            ):
                raise CompatibilityError(
                    "E-COMPAT-DEPENDENCY-RACE",
                    f"file dependency {self.module_name} changed after execution",
                )
            object.__setattr__(self, "path", str(resolved))
        else:
            if self.identity is not None:
                raise CompatibilityError(
                    "E-COMPAT-DEPENDENCY-PROFILE",
                    "non-file dependency cannot carry a file identity",
                )
            if self.path is not None:
                try:
                    require_canonical_text(self.path, field="dependency virtual origin")
                except CanonicalizationError as exc:
                    raise CompatibilityError(
                        "E-COMPAT-DEPENDENCY-PROFILE", str(exc)
                    ) from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_name": self.module_name,
            "origin_kind": self.origin_kind.value,
            "path": self.path,
            "identity": self.identity.to_dict() if self.identity is not None else None,
        }


@dataclass(frozen=True, slots=True)
class ExecutionDependencyProfile:
    """Content-addressed Python process and module dependency record."""

    profile_version: str
    implementation: str
    version: str
    platform_name: str
    machine: str
    executable_path: str
    executable_identity: ArtifactIdentity
    worker_path: str
    worker_identity: ArtifactIdentity
    worker_launch_policy: str
    worker_launch_lock_path: str
    worker_launch_lock_timeout_seconds: int
    worker_launch_poll_milliseconds: int
    worker_launch_post_release_yield_milliseconds: int
    import_search_paths: tuple[str, ...]
    isolated_mode: bool
    ignore_environment: bool
    safe_path: bool
    no_site: bool
    no_user_site: bool
    dont_write_bytecode: bool
    environment: tuple[EnvironmentBinding, ...]
    dependencies: tuple[DependencyArtifact, ...]
    fresh_process: bool
    parent_sys_modules_inherited: bool
    external_cas_imports: tuple[str, ...]
    os_sandboxed: bool
    host_os_dependencies_content_addressed: bool
    boundary: ResearchBoundary = field(default_factory=ResearchBoundary.ring4_open)

    def __post_init__(self) -> None:
        if type(self) is not ExecutionDependencyProfile:
            raise CompatibilityError(
                "E-COMPAT-DEPENDENCY-PROFILE",
                "ExecutionDependencyProfile subclasses are not accepted",
            )
        if self.profile_version != EXECUTION_PROFILE_VERSION:
            raise CompatibilityError(
                "E-COMPAT-DEPENDENCY-PROFILE", "unknown execution profile version"
            )
        for field_name in ("implementation", "version", "platform_name", "machine"):
            _clean_text(getattr(self, field_name), field_name=field_name)
        expected_runtime = _runtime_identity(_worker_environment())
        if (
            self.implementation,
            self.version,
            self.platform_name,
            self.machine,
        ) != expected_runtime:
            raise CompatibilityError(
                "E-COMPAT-RUNTIME", "worker runtime differs from the parent runtime"
            )

        _clean_text(self.executable_path, field_name="Python executable path")
        _clean_text(self.worker_path, field_name="compiler worker path")
        _clean_text(self.worker_launch_policy, field_name="worker launch policy")
        _clean_text(self.worker_launch_lock_path, field_name="worker launch lock path")

        expected_executable = Path(sys.executable).resolve()
        expected_worker = Path(__file__).with_name("_compiler_worker.py").resolve()
        if Path(self.executable_path).resolve() != expected_executable:
            raise CompatibilityError(
                "E-COMPAT-RUNTIME", "worker executable path is not the selected Python"
            )
        if Path(self.worker_path).resolve() != expected_worker:
            raise CompatibilityError(
                "E-COMPAT-RUNTIME", "worker path is not the packaged isolated worker"
            )
        if (
            type(self.executable_identity) is not ArtifactIdentity
            or not artifact_identities_match(
                ArtifactIdentity.from_path(expected_executable), self.executable_identity
            )
        ):
            raise CompatibilityError(
                "E-COMPAT-RUNTIME", "Python executable identity is not current"
            )
        if (
            type(self.worker_identity) is not ArtifactIdentity
            or not artifact_identities_match(
                ArtifactIdentity.from_path(expected_worker), self.worker_identity
            )
        ):
            raise CompatibilityError(
                "E-COMPAT-RUNTIME", "worker identity is not current"
            )
        object.__setattr__(self, "executable_path", str(expected_executable))
        object.__setattr__(self, "worker_path", str(expected_worker))
        expected_launch_lock = _worker_launch_lock_path()
        if self.worker_launch_policy != WORKER_LAUNCH_POLICY:
            raise CompatibilityError(
                "E-COMPAT-ISOLATION", "worker launch policy is not the fixed profile"
            )
        if Path(self.worker_launch_lock_path).resolve() != expected_launch_lock:
            raise CompatibilityError(
                "E-COMPAT-ISOLATION", "worker launch lock path is not canonical"
            )
        object.__setattr__(self, "worker_launch_lock_path", str(expected_launch_lock))
        expected_launch_integers = {
            "worker_launch_lock_timeout_seconds": (
                WORKER_LAUNCH_LOCK_TIMEOUT_SECONDS
            ),
            "worker_launch_poll_milliseconds": WORKER_LAUNCH_POLL_MILLISECONDS,
            "worker_launch_post_release_yield_milliseconds": (
                WORKER_LAUNCH_POST_RELEASE_YIELD_MILLISECONDS
            ),
        }
        if any(
            type(getattr(self, field_name)) is not int
            or getattr(self, field_name) != expected
            for field_name, expected in expected_launch_integers.items()
        ):
            raise CompatibilityError(
                "E-COMPAT-ISOLATION",
                "worker launch timing parameters are not the fixed profile",
            )

        if type(self.import_search_paths) is not tuple or not self.import_search_paths:
            raise CompatibilityError(
                "E-COMPAT-ISOLATION", "worker import search path must be explicit"
            )
        if len(self.import_search_paths) != len(set(self.import_search_paths)):
            raise CompatibilityError(
                "E-COMPAT-ISOLATION", "worker import search path contains duplicates"
            )
        python_base = Path(sys.base_prefix).resolve()
        normalized_import_paths: list[str] = []
        for import_path in self.import_search_paths:
            _clean_text(import_path, field_name="worker import search path")
            candidate = Path(import_path)
            if not candidate.is_absolute() or not _path_is_within(candidate, python_base):
                raise CompatibilityError(
                    "E-COMPAT-ISOLATION",
                    "worker import search path escapes the selected Python installation",
                )
            normalized_import_paths.append(str(candidate.resolve()))
        object.__setattr__(self, "import_search_paths", tuple(normalized_import_paths))

        for field_name in (
            "isolated_mode",
            "ignore_environment",
            "safe_path",
            "no_site",
            "no_user_site",
            "dont_write_bytecode",
            "fresh_process",
            "parent_sys_modules_inherited",
            "os_sandboxed",
            "host_os_dependencies_content_addressed",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise CompatibilityError(
                    "E-COMPAT-DEPENDENCY-PROFILE", f"{field_name} must be boolean"
                )
        if not all(
            (
                self.isolated_mode,
                self.ignore_environment,
                self.safe_path,
                self.no_site,
                self.no_user_site,
                self.dont_write_bytecode,
            )
        ):
            raise CompatibilityError(
                "E-COMPAT-ISOLATION", "all Python import-isolation flags are required"
            )
        if not self.fresh_process or self.parent_sys_modules_inherited:
            raise CompatibilityError(
                "E-COMPAT-ISOLATION", "worker must be a fresh uninherited process"
            )
        # The current implementation makes no OS sandbox claim.  Both false
        # values are an intentional, reviewable residual limitation.
        if self.os_sandboxed or self.host_os_dependencies_content_addressed:
            raise CompatibilityError(
                "E-COMPAT-ISOLATION",
                "this profile must not claim OS sandboxing or host-OS closure",
            )
        if self.external_cas_imports != ():
            raise CompatibilityError(
                "E-COMPAT-UNBOUND-IMPORT", "external CAS dependency closure is not empty"
            )

        allowed_environment_names = {
            "SystemRoot",
            "WINDIR",
            "COMSPEC",
            "PROCESSOR_ARCHITECTURE",
            "PROCESSOR_ARCHITEW6432",
            "PYTHONHASHSEED",
            "PYTHONIOENCODING",
            "PYTHONUTF8",
        }
        if type(self.environment) is not tuple or any(
            type(item) is not EnvironmentBinding for item in self.environment
        ):
            raise CompatibilityError(
                "E-COMPAT-ENVIRONMENT", "worker environment is not a typed tuple"
            )
        environment_names = tuple(item.name for item in self.environment)
        if (
            environment_names != tuple(sorted(environment_names))
            or len(environment_names) != len(set(environment_names))
            or not set(environment_names).issubset(allowed_environment_names)
        ):
            raise CompatibilityError(
                "E-COMPAT-ENVIRONMENT", "worker environment is not the sanitized profile"
            )
        environment_values = {item.name: item.value for item in self.environment}
        if environment_values != _worker_environment():
            raise CompatibilityError(
                "E-COMPAT-ENVIRONMENT",
                "worker environment differs from the exact sanitized parent binding",
            )
        if type(self.dependencies) is not tuple or not self.dependencies:
            raise CompatibilityError(
                "E-COMPAT-DEPENDENCY-PROFILE", "dependency inventory must be nonempty"
            )
        if any(type(item) is not DependencyArtifact for item in self.dependencies):
            raise CompatibilityError(
                "E-COMPAT-DEPENDENCY-PROFILE", "dependency inventory is not typed"
            )
        names = tuple(item.module_name for item in self.dependencies)
        if names != tuple(sorted(names)) or len(names) != len(set(names)):
            raise CompatibilityError(
                "E-COMPAT-DEPENDENCY-PROFILE",
                "dependency inventory must be uniquely sorted by module name",
            )
        main_records = [item for item in self.dependencies if item.module_name == "__main__"]
        if (
            len(main_records) != 1
            or main_records[0].origin_kind is not DependencyOriginKind.FILE
            or not artifact_identities_match(
                main_records[0].identity, self.worker_identity
            )
        ):
            raise CompatibilityError(
                "E-COMPAT-DEPENDENCY-PROFILE",
                "dependency inventory must bind __main__ to the worker bytes",
            )
        if not is_exact_ring4_open(self.boundary):
            raise CompatibilityError(
                "E-COMPAT-BOUNDARY",
                "execution profiles must remain Ring 4 / OPEN / NOT LICENSED",
            )

    @property
    def runtime_profile(self) -> str:
        return "/".join(
            (self.implementation, self.version, self.platform_name, self.machine)
        )

    def payload_without_digest(self) -> dict[str, Any]:
        return {
            "profile_version": self.profile_version,
            "engine_profile": PYTHON_ONLY_ENGINE_PROFILE,
            "runtime": {
                "implementation": self.implementation,
                "version": self.version,
                "platform": self.platform_name,
                "machine": self.machine,
                "executable_path": self.executable_path,
                "executable_identity": self.executable_identity.to_dict(),
                "worker_path": self.worker_path,
                "worker_identity": self.worker_identity.to_dict(),
                "worker_launch": {
                    "policy": self.worker_launch_policy,
                    "lock_path": self.worker_launch_lock_path,
                    "lock_timeout_seconds": (
                        self.worker_launch_lock_timeout_seconds
                    ),
                    "poll_milliseconds": self.worker_launch_poll_milliseconds,
                    "post_release_yield_milliseconds": (
                        self.worker_launch_post_release_yield_milliseconds
                    ),
                },
                "import_search_paths": list(self.import_search_paths),
                "flags": {
                    "isolated": self.isolated_mode,
                    "ignore_environment": self.ignore_environment,
                    "safe_path": self.safe_path,
                    "no_site": self.no_site,
                    "no_user_site": self.no_user_site,
                    "dont_write_bytecode": self.dont_write_bytecode,
                },
                "environment": [item.to_dict() for item in self.environment],
            },
            "dependencies": [item.to_dict() for item in self.dependencies],
            "isolation": {
                "fresh_process": self.fresh_process,
                "parent_sys_modules_inherited": self.parent_sys_modules_inherited,
                "external_cas_imports": list(self.external_cas_imports),
                "os_sandboxed": self.os_sandboxed,
                "host_os_dependencies_content_addressed": (
                    self.host_os_dependencies_content_addressed
                ),
            },
            "boundary": self.boundary.to_dict(),
        }

    @property
    def profile_sha256(self) -> str:
        return canonical_json_sha256(self.payload_without_digest())

    def verify_current_files(self) -> bool:
        """Recheck file-backed process evidence before a later assessment."""

        try:
            if not artifact_identities_match(
                ArtifactIdentity.from_path(self.executable_path), self.executable_identity
            ):
                return False
            if not artifact_identities_match(
                ArtifactIdentity.from_path(self.worker_path), self.worker_identity
            ):
                return False
            return all(
                item.origin_kind is not DependencyOriginKind.FILE
                or artifact_identities_match(
                    ArtifactIdentity.from_path(item.path), item.identity
                )
                for item in self.dependencies
            )
        except OSError:
            return False

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.payload_without_digest(),
            "profile_sha256": self.profile_sha256,
        }


def _profile_diagnostic_view(
    profile: ExecutionDependencyProfile,
) -> dict[str, Any]:
    """Return a keyed comparison view that never exposes environment values."""

    payload = profile.payload_without_digest()
    runtime = dict(payload["runtime"])
    runtime["environment"] = {
        f"name={record['name']}": {
            "value_sha256": canonical_json_sha256(record["value"])
        }
        for record in runtime["environment"]
    }
    dependencies: dict[str, dict[str, Any]] = {}
    for record in payload["dependencies"]:
        diagnostic_record = dict(record)
        module_name = diagnostic_record.pop("module_name")
        path_value = diagnostic_record.pop("path")
        diagnostic_record["path_sha256"] = (
            canonical_json_sha256(path_value) if path_value is not None else None
        )
        dependencies[f"module_name={module_name}"] = diagnostic_record
    return {
        **payload,
        "runtime": runtime,
        "dependencies": dependencies,
    }


def _diagnostic_child_path(parent: str, key: str) -> str:
    if key.isidentifier():
        return f"{parent}.{key}"
    return f"{parent}[{json.dumps(key, ensure_ascii=True)}]"


def _bounded_difference_paths(
    first: Any,
    replay: Any,
    *,
    limit: int = PROFILE_DIFFERENCE_PATH_LIMIT,
) -> tuple[tuple[str, ...], bool]:
    """Return deterministic differing paths, bounded to ``limit`` entries."""

    if type(limit) is not int or limit < 1:
        raise ValueError("difference path limit must be a positive integer")
    found: list[str] = []

    def visit(left: Any, right: Any, path: str) -> None:
        if len(found) > limit:
            return
        if type(left) is not type(right):
            found.append(path)
            return
        if type(left) is dict:
            for key in sorted(set(left) | set(right)):
                child = _diagnostic_child_path(path, key)
                if key not in left or key not in right:
                    found.append(child)
                else:
                    visit(left[key], right[key], child)
                if len(found) > limit:
                    return
            return
        if type(left) is list:
            if len(left) != len(right):
                found.append(f"{path}.length")
            for index, (left_item, right_item) in enumerate(zip(left, right)):
                visit(left_item, right_item, f"{path}[{index}]")
                if len(found) > limit:
                    return
            return
        if left != right:
            found.append(path)

    visit(first, replay, "$")
    return tuple(found[:limit]), len(found) > limit


def _profile_mismatch_diagnostic(
    first: ExecutionDependencyProfile,
    replay: ExecutionDependencyProfile,
) -> str:
    difference_paths, truncated = _bounded_difference_paths(
        _profile_diagnostic_view(first),
        _profile_diagnostic_view(replay),
    )
    diagnostic = {
        "difference_paths": list(difference_paths or ("$",)),
        "difference_paths_truncated": truncated,
        "first_profile_sha256": first.profile_sha256,
        "replay_profile_sha256": replay.profile_sha256,
    }
    return json.dumps(diagnostic, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class CompilerIdentityPolicy:
    source_id: str
    accepted_versions: tuple[str, ...]
    accepted_syntax_profiles: tuple[str, ...]
    raw_sha256_variants: tuple[str, ...]
    canonical_lf_sha256: str

    def __post_init__(self) -> None:
        if type(self) is not CompilerIdentityPolicy:
            raise CompatibilityError(
                "E-COMPAT-POLICY", "CompilerIdentityPolicy subclasses are not accepted"
            )
        try:
            require_ascii_identifier(self.source_id, field="compiler source_id")
        except CanonicalizationError as exc:
            raise CompatibilityError("E-COMPAT-POLICY", str(exc)) from exc
        if (
            type(self.accepted_versions) is not tuple
            or type(self.accepted_syntax_profiles) is not tuple
            or not self.accepted_versions
            or not self.accepted_syntax_profiles
        ):
            raise CompatibilityError(
                "E-COMPAT-POLICY", "versions and syntax profiles must be explicit"
            )
        for value in self.accepted_versions:
            _clean_text(value, field_name="accepted version")
        for value in self.accepted_syntax_profiles:
            _clean_text(value, field_name="accepted syntax profile")
        if type(self.raw_sha256_variants) is not tuple or not self.raw_sha256_variants:
            raise CompatibilityError(
                "E-COMPAT-POLICY", "raw compiler identities must be explicit"
            )
        object.__setattr__(
            self,
            "raw_sha256_variants",
            tuple(_strict_sha(value, field_name="compiler raw SHA-256") for value in self.raw_sha256_variants),
        )
        object.__setattr__(
            self,
            "canonical_lf_sha256",
            _strict_sha(self.canonical_lf_sha256, field_name="canonical_lf_sha256"),
        )

    @classmethod
    def cas_v77(cls) -> "CompilerIdentityPolicy":
        return CompilerIdentityPolicy(
            source_id=CAS_V77_COMPILER_SOURCE_ID,
            accepted_versions=("CAS v7.7", "CAS v7.7 compatibility"),
            accepted_syntax_profiles=(CAS_V77_SYNTAX_PROFILE,),
            raw_sha256_variants=(
                CAS_V77_COMPILER_RAW_CRLF_SHA256,
                CAS_V77_COMPILER_CANONICAL_LF_SHA256,
            ),
            canonical_lf_sha256=CAS_V77_COMPILER_CANONICAL_LF_SHA256,
        )


@dataclass(frozen=True, slots=True)
class LegacySourceEnvelope:
    source: str
    declared_version: str
    syntax_profile: str
    source_sha256: str

    def __post_init__(self) -> None:
        if type(self) is not LegacySourceEnvelope:
            raise CompatibilityError(
                "E-COMPAT-ENVELOPE", "LegacySourceEnvelope subclasses are not accepted"
            )
        _clean_text(self.source, field_name="legacy source")
        _clean_text(self.declared_version, field_name="declared_version")
        _clean_text(self.syntax_profile, field_name="syntax_profile")
        object.__setattr__(
            self,
            "source_sha256",
            _strict_sha(self.source_sha256, field_name="source_sha256"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "declared_version": self.declared_version,
            "syntax_profile": self.syntax_profile,
            "source_sha256": self.source_sha256,
        }

    @classmethod
    def bind(
        cls,
        source: str,
        *,
        declared_version: str = "CAS v7.7",
        syntax_profile: str = CAS_V77_SYNTAX_PROFILE,
    ) -> "LegacySourceEnvelope":
        if type(source) is not str:
            raise CompatibilityError("E-COMPAT-SOURCE", "source must be text")
        return cls(
            source=source,
            declared_version=declared_version,
            syntax_profile=syntax_profile,
            source_sha256=sha256_hex(source.encode("utf-8")),
        )


def _freeze_legacy_value(value: Any) -> Any:
    """Normalize JSON-like legacy output into immutable exact evidence values."""

    if value is None or type(value) in (bool, int):
        return value
    if type(value) is str:
        try:
            return require_canonical_text(value, field="legacy artifact text")
        except CanonicalizationError as exc:
            raise CompatibilityError("E-COMPAT-ARTIFACT-TEXT", str(exc)) from exc
    if type(value) is Decimal:
        if not value.is_finite():
            raise CompatibilityError(
                "E-COMPAT-ARTIFACT-NUMBER", "legacy Decimal values must be finite"
            )
        return value
    if type(value) is float:
        converted = Decimal.from_float(value)
        if not converted.is_finite():
            raise CompatibilityError(
                "E-COMPAT-ARTIFACT-NUMBER", "legacy binary floats must be finite"
            )
        return converted
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise CompatibilityError(
                "E-COMPAT-ARTIFACT-SHAPE", "legacy artifact keys must be strings"
            )
        if "$cas$type" in value:
            raise CompatibilityError(
                "E-COMPAT-ARTIFACT-SHAPE", "legacy artifact uses a reserved type tag"
            )
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            try:
                clean_key = require_canonical_text(key, field="legacy artifact key")
            except CanonicalizationError as exc:
                raise CompatibilityError("E-COMPAT-ARTIFACT-TEXT", str(exc)) from exc
            frozen[clean_key] = _freeze_legacy_value(item)
        return MappingProxyType(frozen)
    if type(value) is FrozenList:
        return FrozenList(tuple(_freeze_legacy_value(item) for item in value))
    if type(value) is list:
        return FrozenList(tuple(_freeze_legacy_value(item) for item in value))
    if type(value) is tuple:
        raise CompatibilityError(
            "E-COMPAT-ARTIFACT-SHAPE",
            "tuple is not a legacy JSON array; use FrozenList for immutable arrays",
        )
    raise CompatibilityError(
        "E-COMPAT-ARTIFACT-SHAPE",
        f"unsupported legacy artifact value {type(value).__name__}",
    )


@dataclass(frozen=True, slots=True)
class CompatibilityCompilation:
    source_envelope: LegacySourceEnvelope
    compiler_source: bytes = field(repr=False)
    source_sha256: str
    compiler_identity: ArtifactIdentity
    compiler_source_id: str
    legacy_artifact: Mapping[str, Any]
    legacy_artifact_sha256: str
    diagnostics: tuple[LegacyDiagnosticCode, ...]
    engine_profile: str
    execution_profile: ExecutionDependencyProfile
    execution_profile_sha256: str
    boundary: ResearchBoundary = field(default_factory=ResearchBoundary.ring4_open)
    v8_semantic_translation: None = None

    def __post_init__(self) -> None:
        if type(self) is not CompatibilityCompilation:
            raise CompatibilityError(
                "E-COMPAT-COMPILATION", "CompatibilityCompilation subclasses are not accepted"
            )
        if type(self.source_envelope) is not LegacySourceEnvelope:
            raise CompatibilityError(
                "E-COMPAT-ENVELOPE", "compilation requires an exact LegacySourceEnvelope"
            )
        if type(self.compiler_source) is not bytes:
            raise CompatibilityError(
                "E-COMPAT-COMPILER-IDENTITY", "compiler_source must retain exact bytes"
            )
        object.__setattr__(
            self,
            "source_sha256",
            _strict_sha(self.source_sha256, field_name="source_sha256"),
        )
        actual_source_sha256 = sha256_hex(self.source_envelope.source.encode("utf-8"))
        if (
            actual_source_sha256 != self.source_envelope.source_sha256
            or self.source_sha256 != self.source_envelope.source_sha256
        ):
            raise CompatibilityError(
                "E-COMPAT-SOURCE-HASH",
                "compilation source does not match its bound LegacySourceEnvelope",
            )
        if type(self.compiler_identity) is not ArtifactIdentity:
            raise CompatibilityError(
                "E-COMPAT-COMPILER-IDENTITY", "compiler identity must be verified"
            )
        if not artifact_identities_match(
            ArtifactIdentity.from_bytes(self.compiler_source), self.compiler_identity
        ):
            raise CompatibilityError(
                "E-COMPAT-COMPILER-IDENTITY",
                "retained compiler bytes do not match compiler_identity",
            )
        if self.compiler_identity.raw_sha256 not in (
            CAS_V77_COMPILER_RAW_CRLF_SHA256,
            CAS_V77_COMPILER_CANONICAL_LF_SHA256,
        ) or self.compiler_identity.canonical_lf_sha256 != CAS_V77_COMPILER_CANONICAL_LF_SHA256:
            raise CompatibilityError(
                "E-COMPAT-COMPILER-IDENTITY",
                "compiler identity is outside the frozen CAS v7.7 variants",
            )
        if (
            type(self.compiler_source_id) is not str
            or self.compiler_source_id != CAS_V77_COMPILER_SOURCE_ID
        ):
            raise CompatibilityError(
                "E-COMPAT-COMPILER-SOURCE", "compiler source authority is not canonical"
            )
        if not isinstance(self.legacy_artifact, Mapping):
            raise CompatibilityError(
                "E-COMPAT-ARTIFACT-SHAPE", "legacy artifact root must be a mapping"
            )
        frozen_artifact = _freeze_legacy_value(self.legacy_artifact)
        object.__setattr__(self, "legacy_artifact", frozen_artifact)
        if type(frozen_artifact.get("valid")) is not bool:
            raise CompatibilityError(
                "E-COMPAT-ARTIFACT-SHAPE", "legacy artifact valid must be boolean"
            )
        object.__setattr__(
            self,
            "legacy_artifact_sha256",
            _strict_sha(self.legacy_artifact_sha256, field_name="legacy_artifact_sha256"),
        )
        if canonical_json_sha256(frozen_artifact) != self.legacy_artifact_sha256:
            raise CompatibilityError(
                "E-COMPAT-ARTIFACT-HASH",
                "legacy artifact does not match legacy_artifact_sha256",
            )
        if (
            type(self.diagnostics) is not tuple
            or not self.diagnostics
            or any(type(item) is not LegacyDiagnosticCode for item in self.diagnostics)
        ):
            raise CompatibilityError(
                "E-COMPAT-DIAGNOSTICS", "diagnostics must be a nonempty typed tuple"
            )
        if type(self.engine_profile) is not str or self.engine_profile != PYTHON_ONLY_ENGINE_PROFILE:
            raise CompatibilityError(
                "E-COMPAT-ENGINE", "only the Python compatibility engine is admitted"
            )
        if type(self.execution_profile) is not ExecutionDependencyProfile:
            raise CompatibilityError(
                "E-COMPAT-DEPENDENCY-PROFILE", "typed execution profile is required"
            )
        object.__setattr__(
            self,
            "execution_profile_sha256",
            _strict_sha(self.execution_profile_sha256, field_name="execution_profile_sha256"),
        )
        if self.execution_profile.profile_sha256 != self.execution_profile_sha256:
            raise CompatibilityError(
                "E-COMPAT-DEPENDENCY-PROFILE", "execution profile digest mismatch"
            )
        if not is_exact_ring4_open(self.boundary):
            raise CompatibilityError(
                "E-COMPAT-BOUNDARY",
                "compatibility artifacts must remain Ring 4 / OPEN / NOT LICENSED",
            )
        if self.v8_semantic_translation is not None:
            raise CompatibilityError(
                "E-COMPAT-V8-TRANSLATION",
                "legacy compatibility output cannot carry a silent v8 translation",
            )

    @property
    def runtime_profile(self) -> str:
        return self.execution_profile.runtime_profile

    @property
    def dependency_closure_sha256(self) -> str:
        """Compatibility alias for the complete execution profile digest."""

        return self.execution_profile_sha256

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_envelope": self.source_envelope.to_dict(),
            "source_sha256": self.source_sha256,
            "compiler_identity": self.compiler_identity.to_dict(),
            "compiler_source_id": self.compiler_source_id,
            "legacy_artifact": self.legacy_artifact,
            "legacy_artifact_sha256": self.legacy_artifact_sha256,
            "diagnostics": [item.value for item in self.diagnostics],
            "engine_profile": self.engine_profile,
            "execution_profile": self.execution_profile.to_dict(),
            "execution_profile_sha256": self.execution_profile_sha256,
            "boundary": self.boundary.to_dict(),
            "v8_semantic_translation": self.v8_semantic_translation,
        }


def _walk_ast(node: Any) -> Sequence[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, Mapping):
        found.append(dict(node))
        for value in node.values():
            found.extend(_walk_ast(value))
    elif isinstance(node, (FrozenList, list, tuple)):
        for value in node:
            found.extend(_walk_ast(value))
    return found


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CompatibilityError(
                "E-COMPAT-WORKER-PROTOCOL", f"duplicate worker JSON key {key!r}"
            )
        result[key] = value
    return result


def _require_exact_keys(value: Any, keys: set[str], *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise CompatibilityError(
            "E-COMPAT-WORKER-PROTOCOL", f"{label} has a noncanonical shape"
        )
    return value


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _reported_file_identity(record: Mapping[str, Any], *, label: str) -> tuple[str, ArtifactIdentity]:
    path_value = record.get("path")
    if not isinstance(path_value, str) or not Path(path_value).is_absolute():
        raise CompatibilityError(
            "E-COMPAT-WORKER-PROTOCOL", f"{label} path is not absolute"
        )
    resolved = Path(path_value).resolve()
    if not resolved.is_file():
        raise CompatibilityError(
            "E-COMPAT-DEPENDENCY-RACE", f"{label} disappeared after worker execution"
        )
    identity = ArtifactIdentity.from_path(resolved)
    reported_sha = _strict_sha(record.get("raw_sha256"), field_name=f"{label}.raw_sha256")
    reported_bytes = record.get("raw_bytes")
    if (
        isinstance(reported_bytes, bool)
        or not isinstance(reported_bytes, int)
        or reported_bytes < 0
        or identity.raw_sha256 != reported_sha
        or identity.raw_bytes != reported_bytes
    ):
        raise CompatibilityError(
            "E-COMPAT-DEPENDENCY-RACE", f"{label} bytes differ from worker report"
        )
    return str(resolved), identity


def _execution_profile_from_worker(
    response: Mapping[str, Any],
    *,
    worker_environment: Mapping[str, str],
    worker_launch_lock_path: Path,
) -> ExecutionDependencyProfile:
    runtime = _require_exact_keys(
        response.get("runtime"),
        {
            "implementation",
            "version",
            "platform",
            "machine",
            "executable",
            "worker",
            "sys_path",
            "flags",
        },
        label="worker runtime",
    )
    executable_record = _require_exact_keys(
        runtime["executable"], {"path", "raw_sha256", "raw_bytes"}, label="worker executable"
    )
    worker_record = _require_exact_keys(
        runtime["worker"], {"path", "raw_sha256", "raw_bytes"}, label="worker file"
    )
    executable_path, executable_identity = _reported_file_identity(
        executable_record, label="worker executable"
    )
    worker_path, worker_identity = _reported_file_identity(worker_record, label="worker file")
    flags = _require_exact_keys(
        runtime["flags"],
        {
            "isolated",
            "ignore_environment",
            "safe_path",
            "no_site",
            "no_user_site",
            "dont_write_bytecode",
        },
        label="worker flags",
    )
    isolation = _require_exact_keys(
        response.get("isolation"),
        {
            "fresh_process",
            "parent_sys_modules_inherited",
            "external_cas_imports",
            "os_sandboxed",
            "host_os_dependencies_content_addressed",
        },
        label="worker isolation",
    )
    if not isinstance(isolation["external_cas_imports"], list) or isolation[
        "external_cas_imports"
    ]:
        raise CompatibilityError(
            "E-COMPAT-UNBOUND-IMPORT", "worker reported external CAS imports"
        )

    raw_sys_path = runtime["sys_path"]
    if not isinstance(raw_sys_path, list) or not raw_sys_path or any(
        not isinstance(item, str) for item in raw_sys_path
    ):
        raise CompatibilityError(
            "E-COMPAT-WORKER-PROTOCOL", "worker sys.path is not an explicit text array"
        )

    raw_dependencies = response.get("dependencies")
    if not isinstance(raw_dependencies, list) or not raw_dependencies:
        raise CompatibilityError(
            "E-COMPAT-WORKER-PROTOCOL", "worker dependency inventory is missing"
        )
    dependencies: list[DependencyArtifact] = []
    python_base = Path(sys.base_prefix).resolve()
    expected_worker = Path(__file__).with_name("_compiler_worker.py").resolve()
    for index, raw_dependency in enumerate(raw_dependencies):
        dependency = _require_exact_keys(
            raw_dependency,
            {"module_name", "origin_kind", "path", "raw_sha256", "raw_bytes"},
            label=f"dependency {index}",
        )
        module_name = _clean_text(
            dependency["module_name"], field_name=f"dependency {index} module_name"
        )
        try:
            origin_kind = DependencyOriginKind(dependency["origin_kind"])
        except (TypeError, ValueError) as exc:
            raise CompatibilityError(
                "E-COMPAT-WORKER-PROTOCOL", f"dependency {module_name} has unknown origin"
            ) from exc
        if origin_kind is DependencyOriginKind.FILE:
            path_value, identity = _reported_file_identity(
                dependency, label=f"dependency {module_name}"
            )
            resolved_path = Path(path_value)
            if resolved_path != expected_worker and not _path_is_within(resolved_path, python_base):
                raise CompatibilityError(
                    "E-COMPAT-DEPENDENCY-ESCAPE",
                    f"dependency {module_name} is outside Python and worker roots",
                )
            dependencies.append(
                DependencyArtifact(module_name, origin_kind, path_value, identity)
            )
        else:
            if dependency["raw_sha256"] is not None or dependency["raw_bytes"] is not None:
                raise CompatibilityError(
                    "E-COMPAT-WORKER-PROTOCOL",
                    f"non-file dependency {module_name} reports file bytes",
                )
            path_value = dependency["path"]
            if path_value is not None and not isinstance(path_value, str):
                raise CompatibilityError(
                    "E-COMPAT-WORKER-PROTOCOL",
                    f"dependency {module_name} virtual origin is not text",
                )
            dependencies.append(
                DependencyArtifact(module_name, origin_kind, path_value, None)
            )

    environment = tuple(
        EnvironmentBinding(name, value)
        for name, value in sorted(worker_environment.items())
    )
    return ExecutionDependencyProfile(
        profile_version=EXECUTION_PROFILE_VERSION,
        implementation=runtime["implementation"],
        version=runtime["version"],
        platform_name=runtime["platform"],
        machine=runtime["machine"],
        executable_path=executable_path,
        executable_identity=executable_identity,
        worker_path=worker_path,
        worker_identity=worker_identity,
        worker_launch_policy=WORKER_LAUNCH_POLICY,
        worker_launch_lock_path=str(worker_launch_lock_path),
        worker_launch_lock_timeout_seconds=WORKER_LAUNCH_LOCK_TIMEOUT_SECONDS,
        worker_launch_poll_milliseconds=WORKER_LAUNCH_POLL_MILLISECONDS,
        worker_launch_post_release_yield_milliseconds=(
            WORKER_LAUNCH_POST_RELEASE_YIELD_MILLISECONDS
        ),
        import_search_paths=tuple(raw_sys_path),
        isolated_mode=flags["isolated"],
        ignore_environment=flags["ignore_environment"],
        safe_path=flags["safe_path"],
        no_site=flags["no_site"],
        no_user_site=flags["no_user_site"],
        dont_write_bytecode=flags["dont_write_bytecode"],
        environment=environment,
        dependencies=tuple(dependencies),
        fresh_process=isolation["fresh_process"],
        parent_sys_modules_inherited=isolation["parent_sys_modules_inherited"],
        external_cas_imports=tuple(isolation["external_cas_imports"]),
        os_sandboxed=isolation["os_sandboxed"],
        host_os_dependencies_content_addressed=isolation[
            "host_os_dependencies_content_addressed"
        ],
    )


def _run_isolated_worker(
    *, compiler_source: bytes, compiler_identity: ArtifactIdentity, source: str, source_sha256: str
) -> tuple[Mapping[str, Any], ExecutionDependencyProfile]:
    worker_path = Path(__file__).with_name("_compiler_worker.py").resolve()
    if not worker_path.is_file():
        raise CompatibilityError(
            "E-COMPAT-WORKER-MISSING", f"isolated worker is absent at {worker_path}"
        )
    request = {
        "protocol": WORKER_PROTOCOL,
        "compiler_source_b64": base64.b64encode(compiler_source).decode("ascii"),
        "compiler_raw_sha256": compiler_identity.raw_sha256,
        "source": source,
        "source_sha256": source_sha256,
    }
    command = [
        str(Path(sys.executable).resolve()),
        "-I",
        "-S",
        "-B",
        "-u",
        str(worker_path),
    ]
    worker_environment = _worker_environment()
    worker_launch_lock_path = _worker_launch_lock_path()
    try:
        with _serialized_worker_launch(worker_launch_lock_path):
            with tempfile.TemporaryDirectory(
                prefix="cas-core-v8-worker-"
            ) as temporary_cwd:
                completed = subprocess.run(
                    command,
                    input=canonical_json_bytes(request),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=temporary_cwd,
                    env=worker_environment,
                    timeout=WORKER_TIMEOUT_SECONDS,
                    check=False,
                )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CompatibilityError(
            "E-COMPAT-WORKER-START", f"cannot execute isolated compiler worker: {exc}"
        ) from exc
    transport_receipt = {
        "returncode": completed.returncode,
        "stdout_bytes": len(completed.stdout),
        "stdout_sha256": sha256_hex(completed.stdout),
        "stderr_bytes": len(completed.stderr),
        "stderr_sha256": sha256_hex(completed.stderr),
    }
    transport_text = json.dumps(
        transport_receipt, sort_keys=True, separators=(",", ":")
    )
    if completed.stderr:
        raise CompatibilityError(
            "E-COMPAT-WORKER-STDERR",
            f"isolated compiler worker emitted stderr; transport={transport_text}",
        )
    try:
        response = json.loads(
            completed.stdout.decode("utf-8"),
            object_pairs_hook=_no_duplicate_object,
            parse_float=Decimal,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, CompatibilityError) as exc:
        code = (
            "E-COMPAT-WORKER-EXIT"
            if completed.returncode != 0
            else "E-COMPAT-WORKER-PROTOCOL"
        )
        raise CompatibilityError(
            code,
            "worker did not return one canonical JSON object; "
            f"transport={transport_text}",
        ) from exc
    if not isinstance(response, Mapping) or response.get("protocol") != WORKER_PROTOCOL:
        code = (
            "E-COMPAT-WORKER-EXIT"
            if completed.returncode != 0
            else "E-COMPAT-WORKER-PROTOCOL"
        )
        raise CompatibilityError(
            code, f"worker response protocol is invalid; transport={transport_text}"
        )
    if response.get("ok") is not True:
        _require_exact_keys(
            response,
            {"protocol", "ok", "error_code", "message"},
            label="worker error response",
        )
        error_code = _clean_text(response["error_code"], field_name="worker error_code")
        message = _clean_text(response["message"], field_name="worker error message")
        raise CompatibilityError(error_code, f"{message}; transport={transport_text}")
    if completed.returncode != 0:
        raise CompatibilityError(
            "E-COMPAT-WORKER-EXIT",
            "worker returned success with a nonzero exit; "
            f"transport={transport_text}",
        )
    _require_exact_keys(
        response,
        {"protocol", "ok", "artifact", "runtime", "dependencies", "isolation"},
        label="worker success response",
    )
    artifact = response["artifact"]
    if not isinstance(artifact, Mapping):
        raise CompatibilityError(
            "E-COMPAT-ARTIFACT-SHAPE", "legacy compiler artifact must be a mapping"
        )
    profile = _execution_profile_from_worker(
        response,
        worker_environment=worker_environment,
        worker_launch_lock_path=worker_launch_lock_path,
    )
    return artifact, profile


def _frozen_compiler_policy() -> CompilerIdentityPolicy:
    policy = CompilerIdentityPolicy.cas_v77()
    if not (
        type(policy) is CompilerIdentityPolicy
        and policy.source_id == CAS_V77_COMPILER_SOURCE_ID
        and type(policy.accepted_versions) is tuple
        and policy.accepted_versions == ("CAS v7.7", "CAS v7.7 compatibility")
        and type(policy.accepted_syntax_profiles) is tuple
        and policy.accepted_syntax_profiles == (CAS_V77_SYNTAX_PROFILE,)
        and type(policy.raw_sha256_variants) is tuple
        and policy.raw_sha256_variants
        == (
            CAS_V77_COMPILER_RAW_CRLF_SHA256,
            CAS_V77_COMPILER_CANONICAL_LF_SHA256,
        )
        and policy.canonical_lf_sha256 == CAS_V77_COMPILER_CANONICAL_LF_SHA256
    ):
        raise CompatibilityError(
            "E-COMPAT-POLICY", "frozen compiler policy constants are incoherent"
        )
    return policy


def _compile_bound_source(
    envelope: LegacySourceEnvelope,
    compiler_source: bytes,
    compiler_identity: ArtifactIdentity,
) -> CompatibilityCompilation:
    """Run two fresh workers over exact retained source and compiler bytes."""

    if type(envelope) is not LegacySourceEnvelope:
        raise CompatibilityError(
            "E-COMPAT-ENVELOPE", "an exact LegacySourceEnvelope is required"
        )
    if type(compiler_source) is not bytes or type(compiler_identity) is not ArtifactIdentity:
        raise CompatibilityError(
            "E-COMPAT-COMPILER-IDENTITY", "exact compiler bytes and identity are required"
        )
    policy = _frozen_compiler_policy()
    actual_source_hash = sha256_hex(envelope.source.encode("utf-8"))
    if actual_source_hash != envelope.source_sha256:
        raise CompatibilityError(
            "E-COMPAT-SOURCE-HASH",
            "source bytes do not match the declared source_sha256",
        )
    if envelope.declared_version not in policy.accepted_versions:
        raise CompatibilityError(
            "E-COMPAT-VERSION", f"unsupported version {envelope.declared_version!r}"
        )
    if envelope.syntax_profile not in policy.accepted_syntax_profiles:
        raise CompatibilityError(
            "E-COMPAT-PROFILE", f"unsupported syntax profile {envelope.syntax_profile!r}"
        )

    identity = ArtifactIdentity.from_bytes(compiler_source)
    if not artifact_identities_match(identity, compiler_identity):
        raise CompatibilityError(
            "E-COMPAT-COMPILER-IDENTITY",
            "compiler bytes do not match the retained compiler identity",
        )
    if compiler_identity.raw_sha256 not in policy.raw_sha256_variants:
        raise CompatibilityError(
            "E-COMPAT-COMPILER-RAW-HASH",
            f"unrecognized compiler raw SHA-256 {compiler_identity.raw_sha256}",
        )
    if compiler_identity.canonical_lf_sha256 != policy.canonical_lf_sha256:
        raise CompatibilityError(
            "E-COMPAT-COMPILER-CONTENT-HASH",
            "compiler LF-normalized content does not match the frozen identity",
        )

    serialized, execution_profile = _run_isolated_worker(
        compiler_source=compiler_source,
        compiler_identity=compiler_identity,
        source=envelope.source,
        source_sha256=envelope.source_sha256,
    )
    replay_serialized, replay_execution_profile = _run_isolated_worker(
        compiler_source=compiler_source,
        compiler_identity=compiler_identity,
        source=envelope.source,
        source_sha256=envelope.source_sha256,
    )
    replay_frozen_artifact = _freeze_legacy_value(replay_serialized)
    if canonical_json_sha256(_freeze_legacy_value(serialized)) != canonical_json_sha256(
        replay_frozen_artifact
    ):
        raise CompatibilityError(
            "E-COMPAT-NONDETERMINISTIC-RESULT",
            "independent isolated workers produced different legacy artifacts",
        )
    if execution_profile.profile_sha256 != replay_execution_profile.profile_sha256:
        raise CompatibilityError(
            "E-COMPAT-NONDETERMINISTIC-PROFILE",
            "independent isolated workers produced different dependency profiles; "
            f"diagnostic={_profile_mismatch_diagnostic(execution_profile, replay_execution_profile)}",
        )
    if serialized.get("engine") != "python":
        raise CompatibilityError(
            "E-COMPAT-ENGINE",
            "legacy compiler did not remain in the Python-only engine profile",
        )
    for node in _walk_ast(serialized.get("ast")):
        if node.get("node") in ("UseStmt", "UseStatement", "ModuleImport"):
            raise CompatibilityError(
                "E-COMPAT-UNBOUND-IMPORT",
                "legacy artifact contains an unbound import",
            )

    frozen_artifact = _freeze_legacy_value(serialized)
    artifact_sha256 = canonical_json_sha256(frozen_artifact)
    diagnostics: list[LegacyDiagnosticCode] = [
        LegacyDiagnosticCode.LEGACY_COMPATIBILITY_PROFILE
    ]
    for node in _walk_ast(frozen_artifact.get("ast")):
        if node.get("node") == "FractalLiteral":
            diagnostics.append(LegacyDiagnosticCode.UNTYPED_FRACTAL_REQUIRES_BRIDGE)
        if node.get("node") == "RpmCall":
            diagnostics.append(LegacyDiagnosticCode.OVERLOADED_RPM_REQUIRES_TYPE_CHOICE)
    diagnostics = list(dict.fromkeys(diagnostics))
    result = CompatibilityCompilation(
        source_envelope=envelope,
        compiler_source=compiler_source,
        source_sha256=envelope.source_sha256,
        compiler_identity=compiler_identity,
        compiler_source_id=policy.source_id,
        legacy_artifact=frozen_artifact,
        legacy_artifact_sha256=artifact_sha256,
        diagnostics=tuple(diagnostics),
        engine_profile=PYTHON_ONLY_ENGINE_PROFILE,
        execution_profile=execution_profile,
        execution_profile_sha256=execution_profile.profile_sha256,
        boundary=ResearchBoundary.ring4_open(),
    )
    return result


def replay_compatibility_compilation(
    compilation: CompatibilityCompilation,
) -> CompatibilityCompilation:
    """Freshly replay and exactly compare a bound compatibility compilation."""

    if type(compilation) is not CompatibilityCompilation:
        raise CompatibilityError(
            "E-COMPAT-REPLAY", "an exact CompatibilityCompilation is required"
        )
    if not ExecutionDependencyProfile.verify_current_files(
        compilation.execution_profile
    ):
        raise CompatibilityError(
            "E-COMPAT-DEPENDENCY-RACE",
            "execution dependency bytes changed since compilation",
        )
    replay = _compile_bound_source(
        compilation.source_envelope,
        compilation.compiler_source,
        compilation.compiler_identity,
    )
    original_view = CompatibilityCompilation.to_dict(compilation)
    replay_view = CompatibilityCompilation.to_dict(replay)
    if canonical_json_bytes(original_view) != canonical_json_bytes(replay_view):
        raise CompatibilityError(
            "E-COMPAT-REPLAY-MISMATCH",
            "fresh deterministic replay differs from the supplied compilation",
        )
    return replay


def compile_legacy_expression(
    envelope: LegacySourceEnvelope,
    *,
    compiler_path: str | Path,
) -> CompatibilityCompilation:
    """Compile under the single frozen policy and retain exact replay inputs."""

    if type(envelope) is not LegacySourceEnvelope:
        raise CompatibilityError(
            "E-COMPAT-ENVELOPE", "an exact LegacySourceEnvelope is required"
        )
    path = Path(compiler_path)
    if not path.is_file():
        raise CompatibilityError(
            "E-COMPAT-COMPILER-MISSING", f"compiler is not present at {path}"
        )
    try:
        compiler_source = path.read_bytes()
    except OSError as exc:
        raise CompatibilityError(
            "E-COMPAT-COMPILER-MISSING", f"cannot read compiler from {path}: {exc}"
        ) from exc
    identity = ArtifactIdentity.from_bytes(compiler_source)
    return _compile_bound_source(envelope, compiler_source, identity)


def bridge_legacy_fractal(
    sequence: Sequence[int],
    *,
    arrow_catalog: Mapping[int, FiniteArrow],
) -> SemigroupoidPath:
    """Translate digits only through an explicit, typed, caller-owned catalog."""

    # Keep the v8 category dependency out of the legacy compilation path.
    from tks_v8_core.category import FiniteArrow, SemigroupoidPath

    if isinstance(sequence, (str, bytes, bytearray)) or not isinstance(
        sequence, Sequence
    ):
        raise CompatibilityError(
            "E-COMPAT-FRACTAL-SEQUENCE", "sequence must be ordered and replayable"
        )
    if not isinstance(arrow_catalog, Mapping):
        raise CompatibilityError(
            "E-COMPAT-FRACTAL-CATALOG", "an explicit arrow catalog is required"
        )
    arrows: list[FiniteArrow] = []
    for digit in sequence:
        if isinstance(digit, bool) or not isinstance(digit, int) or not 0 <= digit <= 9:
            raise CompatibilityError(
                "E-COMPAT-FRACTAL-DIGIT", f"invalid legacy digit {digit!r}"
            )
        try:
            arrow = arrow_catalog[digit]
        except KeyError as exc:
            raise CompatibilityError(
                "E-COMPAT-FRACTAL-UNMAPPED", f"digit {digit} has no typed mapping"
            ) from exc
        if not isinstance(arrow, FiniteArrow):
            raise CompatibilityError(
                "E-COMPAT-FRACTAL-CATALOG", f"digit {digit} is not mapped to FiniteArrow"
            )
        arrows.append(arrow)
    try:
        return SemigroupoidPath(tuple(arrows))
    except (TypeError, ValueError) as exc:
        raise CompatibilityError(
            "E-COMPAT-FRACTAL-TYPE", f"legacy sequence is not composable: {exc}"
        ) from exc
