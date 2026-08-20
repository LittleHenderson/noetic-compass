"""Exact runtime and Rust scanner binding for WELD v3."""

from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any, Mapping, Sequence

from .core import (
    WeldProtocolError,
    canonical_json_bytes,
    require_exact_keys,
    require_mapping,
    require_nonempty_string,
    require_sha256,
    sha256_bytes,
    sha256_file,
)


RUNTIME_BINDING_SCHEMA = "weld-v3-runtime-binding/1"
RUST_VERSION_SCHEMA = "weld-v3-rust-version/1"
RUST_PROTOCOL_ID = "WELD-V3-SEALED-FIXED-PIPELINE-2"
ISOLATION_CONTRACT = {
    "truth_availability_during_actor": "COMMITMENT_ONLY",
    "actor_input_channel": "STDIN_ONLY",
    "actor_output_channel": "STDOUT_ONLY",
    "host_truth_custody": "EXTERNAL_NO_PLAINTEXT_ON_ACTOR_HOST",
}


def _run_version_probe(command: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    """Run an exact local version probe with no shell or inherited stdin."""
    try:
        return subprocess.run(
            list(command),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise WeldProtocolError(f"version probe failed for {command[0]}: {exc}") from exc


def _encode_version_evidence(completed: subprocess.CompletedProcess[bytes]) -> bytes:
    if completed.returncode != 0:
        raise WeldProtocolError(f"version probe returned {completed.returncode}")
    return (
        b"stdout\x00"
        + completed.stdout
        + b"\x00stderr\x00"
        + completed.stderr
        + b"\x00returncode\x000"
    )


def version_evidence_bytes(command: Sequence[str]) -> bytes:
    """Run an exact local version probe and encode both output channels."""
    return _encode_version_evidence(_run_version_probe(command))


def _bound_file(record: Any, where: str) -> tuple[Mapping[str, Any], Path]:
    item = require_mapping(record, where)
    require_exact_keys(item, {"absolute_path", "sha256", "size_bytes"}, where)
    raw_path = require_nonempty_string(item["absolute_path"], f"{where}.absolute_path")
    path = Path(raw_path)
    if not path.is_absolute():
        raise WeldProtocolError(f"{where}.absolute_path must be absolute")
    path = path.resolve()
    if not path.is_file():
        raise WeldProtocolError(f"bound file does not exist: {path}")
    expected_hash = require_sha256(item["sha256"], f"{where}.sha256")
    if not isinstance(item["size_bytes"], int) or isinstance(item["size_bytes"], bool):
        raise WeldProtocolError(f"{where}.size_bytes must be an integer")
    if item["size_bytes"] <= 0:
        raise WeldProtocolError(f"{where}.size_bytes must be positive")
    if path.stat().st_size != item["size_bytes"]:
        raise WeldProtocolError(f"bound file byte count changed: {path}")
    if sha256_file(path) != expected_hash:
        raise WeldProtocolError(f"bound file SHA-256 changed: {path}")
    return item, path


def _versioned_file(record: Any, where: str) -> tuple[Mapping[str, Any], Path]:
    item = require_mapping(record, where)
    require_exact_keys(
        item,
        {"absolute_path", "sha256", "size_bytes", "version_argv", "version_evidence_sha256"},
        where,
    )
    base = {
        "absolute_path": item["absolute_path"],
        "sha256": item["sha256"],
        "size_bytes": item["size_bytes"],
    }
    _, path = _bound_file(base, where)
    argv = item["version_argv"]
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(arg, str) and arg for arg in argv)
    ):
        raise WeldProtocolError(f"{where}.version_argv must be a non-empty string array")
    require_sha256(item["version_evidence_sha256"], f"{where}.version_evidence_sha256")
    return item, path


def validate_binding(binding: Any, *, allow_mock: bool) -> Mapping[str, Any]:
    item = require_mapping(binding, "runtime binding")
    require_exact_keys(
        item,
        {
            "schema_version",
            "profile",
            "binding_status",
            "runtime",
            "adapter",
            "rust_version_claim",
            "source_bindings",
            "isolation_contract",
        },
        "runtime binding",
    )
    if item["schema_version"] != RUNTIME_BINDING_SCHEMA:
        raise WeldProtocolError("unsupported runtime binding schema")
    if item["binding_status"] != "BOUND":
        raise WeldProtocolError("runtime binding is not BOUND")
    profile = item["profile"]
    if profile not in {"PRODUCTION_RUST", "MOCK_TEST_ONLY"}:
        raise WeldProtocolError("unknown runtime binding profile")
    if profile == "MOCK_TEST_ONLY" and not allow_mock:
        raise WeldProtocolError("mock binding requires explicit test-only authorization")
    if item["isolation_contract"] != ISOLATION_CONTRACT:
        raise WeldProtocolError("runtime isolation contract changed")

    runtime = require_mapping(item["runtime"], "runtime binding.runtime")
    _versioned_file(runtime, "runtime binding.runtime")
    adapter = require_mapping(item["adapter"], "runtime binding.adapter")
    require_exact_keys(
        adapter,
        {
            "absolute_path",
            "sha256",
            "size_bytes",
            "version_argv",
            "version_evidence_sha256",
            "language",
            "crate_name",
            "crate_version",
        },
        "runtime binding.adapter",
    )
    _versioned_file(
        {key: adapter[key] for key in (
            "absolute_path",
            "sha256",
            "size_bytes",
            "version_argv",
            "version_evidence_sha256",
        )},
        "runtime binding.adapter",
    )
    require_nonempty_string(adapter["language"], "runtime binding.adapter.language")
    require_nonempty_string(adapter["crate_name"], "runtime binding.adapter.crate_name")
    require_nonempty_string(adapter["crate_version"], "runtime binding.adapter.crate_version")

    sources = item["source_bindings"]
    if not isinstance(sources, list):
        raise WeldProtocolError("source_bindings must be an array")
    labels: set[str] = set()
    source_paths: dict[str, Path] = {}
    for index, raw in enumerate(sources):
        source = require_mapping(raw, f"source_bindings[{index}]")
        require_exact_keys(
            source, {"label", "absolute_path", "sha256", "size_bytes"}, f"source_bindings[{index}]"
        )
        label = require_nonempty_string(source["label"], f"source_bindings[{index}].label")
        if label in labels:
            raise WeldProtocolError(f"duplicate source binding label {label}")
        labels.add(label)
        _, source_path = _bound_file(
            {key: source[key] for key in ("absolute_path", "sha256", "size_bytes")},
            f"source_bindings[{index}]",
        )
        source_paths[label] = source_path

    runtime_path = Path(runtime["absolute_path"]).resolve()
    adapter_path = Path(adapter["absolute_path"]).resolve()
    if profile == "PRODUCTION_RUST":
        if runtime_path != adapter_path:
            raise WeldProtocolError("PRODUCTION_RUST runtime and adapter must be the same executable")
        if adapter["language"] != "rust" or adapter["crate_name"] != "cas-engine":
            raise WeldProtocolError("production adapter must be the Rust cas-engine executable")
        required_labels = {"Cargo.toml", "Cargo.lock", "scanner_source"}
        if labels != required_labels:
            raise WeldProtocolError(
                f"production source bindings must be exactly {sorted(required_labels)}"
            )
        if runtime["version_argv"] != adapter["version_argv"]:
            raise WeldProtocolError("production runtime and adapter version probes must be identical")
        if runtime["version_evidence_sha256"] != adapter["version_evidence_sha256"]:
            raise WeldProtocolError("production runtime and adapter version evidence must be identical")
        if runtime["sha256"] != adapter["sha256"] or runtime["size_bytes"] != adapter["size_bytes"]:
            raise WeldProtocolError("production runtime and adapter identities must be identical")
        _validate_native_executable(adapter_path)
        _validate_rust_source_identity(item, source_paths)
    else:
        if adapter["language"] != "python-mock" or sources:
            raise WeldProtocolError("mock profile must use python-mock and no source bindings")
        if item["rust_version_claim"] is not None:
            raise WeldProtocolError("mock profile must not carry a Rust version claim")
    return item


def _validate_native_executable(path: Path) -> None:
    with path.open("rb") as stream:
        prefix = stream.read(4)
    mach_o = {
        b"\xfe\xed\xfa\xce",
        b"\xfe\xed\xfa\xcf",
        b"\xce\xfa\xed\xfe",
        b"\xcf\xfa\xed\xfe",
    }
    if not (prefix.startswith(b"MZ") or prefix == b"\x7fELF" or prefix in mach_o):
        raise WeldProtocolError("PRODUCTION_RUST adapter must be a native executable image")


def _load_toml(path: Path, where: str) -> Mapping[str, Any]:
    try:
        with path.open("rb") as stream:
            parsed = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise WeldProtocolError(f"cannot parse {where}: {exc}") from exc
    return require_mapping(parsed, where)


def _validate_rust_source_identity(
    binding: Mapping[str, Any], source_paths: Mapping[str, Path]
) -> None:
    cargo_toml_path = source_paths["Cargo.toml"]
    cargo_lock_path = source_paths["Cargo.lock"]
    scanner_path = source_paths["scanner_source"]
    crate_root = cargo_toml_path.parent.resolve()
    if cargo_toml_path.name != "Cargo.toml" or cargo_lock_path != crate_root / "Cargo.lock":
        raise WeldProtocolError("Cargo.toml and Cargo.lock must identify one exact crate root")
    try:
        scanner_path.relative_to(crate_root / "src")
    except ValueError as exc:
        raise WeldProtocolError("scanner_source must resolve inside the bound crate src directory") from exc
    if scanner_path.suffix != ".rs":
        raise WeldProtocolError("scanner_source must be a Rust .rs source file")

    cargo_toml = _load_toml(cargo_toml_path, "Cargo.toml")
    package = require_mapping(cargo_toml.get("package"), "Cargo.toml.package")
    crate_name = binding["adapter"]["crate_name"]
    crate_version = binding["adapter"]["crate_version"]
    if package.get("name") != crate_name or package.get("version") != crate_version:
        raise WeldProtocolError("Cargo.toml package identity differs from the adapter binding")

    cargo_lock = _load_toml(cargo_lock_path, "Cargo.lock")
    packages = cargo_lock.get("package")
    if not isinstance(packages, list):
        raise WeldProtocolError("Cargo.lock has no package inventory")
    exact = [
        record
        for record in packages
        if isinstance(record, dict)
        and record.get("name") == crate_name
        and record.get("version") == crate_version
    ]
    if len(exact) != 1:
        raise WeldProtocolError("Cargo.lock must contain the exact bound crate identity once")

    claim = require_mapping(binding["rust_version_claim"], "runtime binding.rust_version_claim")
    claim_keys = {
        "schema_version",
        "language",
        "binary_kind",
        "crate_name",
        "crate_version",
        "protocol_id",
        "rustc_version",
        "target_triple",
        "cargo_toml_sha256",
        "cargo_lock_sha256",
        "scanner_source_sha256",
    }
    require_exact_keys(claim, claim_keys, "runtime binding.rust_version_claim")
    expected_literals = {
        "schema_version": RUST_VERSION_SCHEMA,
        "language": "rust",
        "binary_kind": "RUST_NATIVE_EXECUTABLE",
        "crate_name": crate_name,
        "crate_version": crate_version,
        "protocol_id": RUST_PROTOCOL_ID,
    }
    for field, expected in expected_literals.items():
        if claim[field] != expected:
            raise WeldProtocolError(f"Rust version claim {field} differs from the binding")
    require_nonempty_string(claim["rustc_version"], "Rust version claim.rustc_version")
    require_nonempty_string(claim["target_triple"], "Rust version claim.target_triple")
    hashes = {
        "cargo_toml_sha256": sha256_file(cargo_toml_path),
        "cargo_lock_sha256": sha256_file(cargo_lock_path),
        "scanner_source_sha256": sha256_file(scanner_path),
    }
    for field, expected in hashes.items():
        require_sha256(claim[field], f"Rust version claim.{field}")
        if claim[field] != expected:
            raise WeldProtocolError(f"Rust version claim {field} differs from bound source")


def _parse_rust_version_stdout(stdout: bytes) -> Mapping[str, Any]:
    try:
        decoded = stdout.decode("utf-8")
        value = json.loads(decoded)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise WeldProtocolError("PRODUCTION_RUST version probe did not emit one JSON object") from exc
    return require_mapping(value, "PRODUCTION_RUST version probe output")


def adapter_command(binding: Mapping[str, Any], *, version_probe: bool = False) -> list[str]:
    profile = binding["profile"]
    runtime_path = str(Path(binding["runtime"]["absolute_path"]).resolve())
    adapter_path = str(Path(binding["adapter"]["absolute_path"]).resolve())
    if profile == "PRODUCTION_RUST":
        command = [adapter_path]
    else:
        command = [runtime_path, adapter_path]
    if version_probe:
        command.extend(binding["adapter"]["version_argv"])
    return command


def attest_binding(binding: Any, *, allow_mock: bool) -> Mapping[str, Any]:
    item = validate_binding(binding, allow_mock=allow_mock)
    runtime = item["runtime"]
    runtime_command = [str(Path(runtime["absolute_path"]).resolve()), *runtime["version_argv"]]
    runtime_completed = _run_version_probe(runtime_command)
    runtime_evidence = _encode_version_evidence(runtime_completed)
    if sha256_bytes(runtime_evidence) != runtime["version_evidence_sha256"]:
        raise WeldProtocolError("runtime version evidence changed")
    adapter_completed = _run_version_probe(adapter_command(item, version_probe=True))
    adapter_evidence = _encode_version_evidence(adapter_completed)
    if sha256_bytes(adapter_evidence) != item["adapter"]["version_evidence_sha256"]:
        raise WeldProtocolError("adapter version evidence changed")
    if item["profile"] == "PRODUCTION_RUST":
        if adapter_completed.stderr:
            raise WeldProtocolError("PRODUCTION_RUST version probe must not write stderr")
        observed_claim = _parse_rust_version_stdout(adapter_completed.stdout)
        if observed_claim != item["rust_version_claim"]:
            raise WeldProtocolError("PRODUCTION_RUST version probe claim differs from binding")

    source_attestations = []
    for source in item["source_bindings"]:
        path = Path(source["absolute_path"]).resolve()
        source_attestations.append(
            {
                "label": source["label"],
                "absolute_path": str(path),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    attestation = {
        "profile": item["profile"],
        "runtime": {
            "absolute_path": str(Path(runtime["absolute_path"]).resolve()),
            "sha256": sha256_file(Path(runtime["absolute_path"])),
            "size_bytes": Path(runtime["absolute_path"]).stat().st_size,
            "version_evidence_sha256": sha256_bytes(runtime_evidence),
        },
        "adapter": {
            "absolute_path": str(Path(item["adapter"]["absolute_path"]).resolve()),
            "sha256": sha256_file(Path(item["adapter"]["absolute_path"])),
            "size_bytes": Path(item["adapter"]["absolute_path"]).stat().st_size,
            "version_evidence_sha256": sha256_bytes(adapter_evidence),
            "language": item["adapter"]["language"],
            "crate_name": item["adapter"]["crate_name"],
            "crate_version": item["adapter"]["crate_version"],
        },
        "source_bindings": source_attestations,
        "binding_sha256": sha256_bytes(canonical_json_bytes(item)),
    }
    return attestation
