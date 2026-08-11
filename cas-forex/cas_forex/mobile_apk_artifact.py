"""Android debug APK artifact metadata for the app/API surface."""

from __future__ import annotations

import hashlib
import os
import secrets
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPORT_KIND = "cas_forex_android_debug_apk_artifact"
RELEASE_APK_REPORT_KIND = "cas_forex_android_release_apk_artifact"
RELEASE_SIGNING_REPORT_KIND = "cas_forex_android_release_signing_status"
DEFAULT_APK_PATH = Path("ui") / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
DEFAULT_RELEASE_APK_PATH = Path("ui") / "android" / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"
DEFAULT_DOWNLOAD_PATH = "/api/forex/mobile/apk/debug/download"
DEFAULT_RELEASE_DOWNLOAD_PATH = "/api/forex/mobile/apk/release/download"
DOWNLOAD_FILENAME = "cas-forex-debug.apk"
RELEASE_DOWNLOAD_FILENAME = "cas-forex-release.apk"
APK_MEDIA_TYPE = "application/vnd.android.package-archive"
RELEASE_BUILD_COMMAND = "npm --prefix ui run mobile:apk:release"
RELEASE_SIGNING_SETUP_COMMAND = "npm --prefix ui run mobile:apk:setup-release-signing"
RELEASE_SIGNING_SETUP_JSON_COMMAND = "npm --prefix ui run mobile:apk:setup-release-signing -- --json"
DEFAULT_RELEASE_KEYSTORE_FILENAME = "cas-forex-release.jks"
DEFAULT_RELEASE_KEY_ALIAS = "cas-forex"
DEFAULT_RELEASE_KEY_DNAME = "CN=CAS Forex, OU=Owner, O=CAS Forex, L=Local, S=Local, C=US"
DEFAULT_RELEASE_KEY_VALIDITY_DAYS = 10000
CLAIM_BOUNDARY = (
    "APK artifact metadata/download proves the current debug APK file is present "
    "and checksum-addressable. It does not prove the APK was installed, opened, "
    "paired on a real phone, or authorized for any trading or money-moving action."
)
RELEASE_SIGNING_CLAIM_BOUNDARY = (
    "Android release signing status reports whether local signing inputs and the "
    "signed release APK artifact are present. It does not expose keystore secrets, "
    "prove the APK was installed or opened on a phone, or authorize any trading or "
    "money-moving action."
)
_RELEASE_FIELDS = (
    ("storeFile", "CAS_FOREX_ANDROID_STOREFILE"),
    ("storePassword", "CAS_FOREX_ANDROID_STOREPASSWORD"),
    ("keyAlias", "CAS_FOREX_ANDROID_KEYALIAS"),
    ("keyPassword", "CAS_FOREX_ANDROID_KEYPASSWORD"),
)


def debug_apk_artifact_metadata(
    *,
    workspace_root: str | Path = ".",
    apk_path: str | Path = DEFAULT_APK_PATH,
    download_path: str = DEFAULT_DOWNLOAD_PATH,
) -> dict[str, Any]:
    """Return token-free, checksum-first metadata for the local debug APK."""
    root = Path(workspace_root).resolve()
    resolved_apk = _resolve_under_root(root, apk_path)
    payload: dict[str, Any] = {
        "report_kind": REPORT_KIND,
        "artifact_id": "android_debug_apk",
        "path": str(resolved_apk),
        "filename": DOWNLOAD_FILENAME,
        "content_type": APK_MEDIA_TYPE,
        "exists": False,
        "transfer_ready": False,
        "size_bytes": None,
        "sha256": None,
        "modified_at": None,
        "download_url_path": download_path,
        "build_command": "npm --prefix ui run mobile:apk:debug",
        "install_command": "npm --prefix ui run mobile:apk:install",
        "install_pair_command": "npm --prefix ui run mobile:apk:install-pair",
        "wait_install_pair_command": "npm --prefix ui run mobile:apk:wait-install-pair",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    if not resolved_apk.exists() or not resolved_apk.is_file():
        payload["summary"] = "Android debug APK is missing; build it before transfer."
        return payload

    stat = resolved_apk.stat()
    payload.update(
        {
            "exists": True,
            "transfer_ready": True,
            "size_bytes": stat.st_size,
            "sha256": _sha256_file(resolved_apk),
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "summary": "Android debug APK is present and ready for authenticated transfer.",
        }
    )
    return payload


def android_release_signing_status(
    *,
    workspace_root: str | Path = ".",
    release_apk_path: str | Path = DEFAULT_RELEASE_APK_PATH,
) -> dict[str, Any]:
    """Return token-free status for Android signed-release APK readiness."""
    root = Path(workspace_root).resolve()
    android_root = root / "ui" / "android"
    properties_path = android_root / "keystore.properties"
    properties = _read_properties(properties_path)

    inputs: dict[str, bool] = {}
    sources: dict[str, str] = {}
    values: dict[str, str | None] = {}
    for prop_name, env_name in _RELEASE_FIELDS:
        prop_value = _non_empty(properties.get(prop_name))
        env_value = _non_empty(os.environ.get(env_name))
        value = prop_value or env_value
        values[prop_name] = value
        inputs[prop_name] = bool(value)
        if prop_value:
            sources[prop_name] = "keystore.properties"
        elif env_value:
            sources[prop_name] = "environment"
        else:
            sources[prop_name] = "missing"

    store_file = values["storeFile"]
    store_file_path = _resolve_release_store_file(android_root, store_file)
    store_file_exists = bool(store_file_path and store_file_path.exists() and store_file_path.is_file())
    all_fields_present = all(inputs.values())
    ready = all_fields_present and store_file_exists
    release_apk = _artifact_fields(root, release_apk_path)

    missing = [name for name, present in inputs.items() if not present]
    if ready:
        status = "ready"
        summary = "Android release signing inputs are present and the keystore file exists."
    elif missing:
        status = "missing_config"
        summary = "Android release signing is missing: " + ", ".join(missing) + "."
    else:
        status = "missing_store_file"
        summary = "Android release signing fields are present, but the configured keystore file was not found."

    return {
        "report_kind": RELEASE_SIGNING_REPORT_KIND,
        "status": status,
        "ready": ready,
        "summary": summary,
        "inputs_present": inputs,
        "input_sources": sources,
        "keystore_properties_exists": properties_path.exists(),
        "keystore_properties_path": "ui/android/keystore.properties",
        "store_file_configured": bool(store_file),
        "store_file_is_absolute": bool(store_file_path and Path(store_file).is_absolute()) if store_file else False,
        "store_file_exists": store_file_exists,
        "release_apk_exists": bool(release_apk["exists"]),
        "release_apk_size_bytes": release_apk["size_bytes"],
        "release_apk_sha256": release_apk["sha256"],
        "release_apk_modified_at": release_apk["modified_at"],
        "release_apk_path": release_apk["path"],
        "build_command": RELEASE_BUILD_COMMAND,
        "setup_command": RELEASE_SIGNING_SETUP_COMMAND,
        "setup_json_command": RELEASE_SIGNING_SETUP_JSON_COMMAND,
        "claim_boundary": RELEASE_SIGNING_CLAIM_BOUNDARY,
    }


def release_apk_artifact_metadata(
    *,
    workspace_root: str | Path = ".",
    apk_path: str | Path = DEFAULT_RELEASE_APK_PATH,
    download_path: str = DEFAULT_RELEASE_DOWNLOAD_PATH,
) -> dict[str, Any]:
    """Return token-free, checksum-first metadata for the signed release APK."""
    root = Path(workspace_root).resolve()
    resolved_apk = _resolve_under_root(root, apk_path)
    signing = android_release_signing_status(workspace_root=root, release_apk_path=apk_path)
    artifact = _artifact_fields(root, apk_path)
    exists = bool(artifact["exists"])
    signing_ready = bool(signing.get("ready"))
    payload: dict[str, Any] = {
        "report_kind": RELEASE_APK_REPORT_KIND,
        "artifact_id": "android_release_apk",
        "path": str(resolved_apk),
        "filename": RELEASE_DOWNLOAD_FILENAME,
        "content_type": APK_MEDIA_TYPE,
        "exists": exists,
        "transfer_ready": exists and signing_ready,
        "size_bytes": artifact["size_bytes"],
        "sha256": artifact["sha256"],
        "modified_at": artifact["modified_at"],
        "download_url_path": download_path,
        "build_command": RELEASE_BUILD_COMMAND,
        "setup_command": RELEASE_SIGNING_SETUP_COMMAND,
        "setup_json_command": RELEASE_SIGNING_SETUP_JSON_COMMAND,
        "signing_ready": signing_ready,
        "signing_status": signing.get("status"),
        "summary": (
            "Android signed release APK is present and ready for authenticated transfer."
            if exists and signing_ready
            else "Android signed release APK is missing or release signing is not ready."
        ),
        "claim_boundary": RELEASE_SIGNING_CLAIM_BOUNDARY,
    }
    return payload


def setup_android_release_signing(
    *,
    workspace_root: str | Path = ".",
    store_file: str = DEFAULT_RELEASE_KEYSTORE_FILENAME,
    key_alias: str = DEFAULT_RELEASE_KEY_ALIAS,
    dname: str = DEFAULT_RELEASE_KEY_DNAME,
    validity_days: int = DEFAULT_RELEASE_KEY_VALIDITY_DAYS,
    force: bool = False,
    keytool_path: str | None = None,
    run_command: Callable[..., subprocess.CompletedProcess[Any]] | None = None,
) -> dict[str, Any]:
    """Generate a local Android release keystore without returning secrets."""
    root = Path(workspace_root).resolve()
    android_root = root / "ui" / "android"
    android_root.mkdir(parents=True, exist_ok=True)
    properties_path = android_root / "keystore.properties"
    keystore_path = _resolve_release_store_file(android_root, store_file)
    if keystore_path is None:
        raise ValueError("store_file must be non-empty")

    existing_targets = [
        str(path.relative_to(root) if _is_relative_to(path, root) else path)
        for path in (properties_path, keystore_path)
        if path.exists()
    ]
    if existing_targets and not force:
        return {
            "report_kind": "cas_forex_android_release_signing_setup",
            "status": "already_exists",
            "created": False,
            "summary": (
                "Android release signing files already exist; rerun with --force only "
                "if you intentionally want to replace the local signing key."
            ),
            "existing_targets": existing_targets,
            "keystore_properties_path": "ui/android/keystore.properties",
            "store_file_path": str(keystore_path.relative_to(root) if _is_relative_to(keystore_path, root) else keystore_path),
            "setup_command": RELEASE_SIGNING_SETUP_COMMAND,
            "build_command": RELEASE_BUILD_COMMAND,
            "claim_boundary": RELEASE_SIGNING_CLAIM_BOUNDARY,
        }

    keytool = keytool_path or shutil.which("keytool")
    if not keytool:
        return {
            "report_kind": "cas_forex_android_release_signing_setup",
            "status": "keytool_missing",
            "created": False,
            "summary": "Java keytool was not found on PATH; install a JDK or run from a shell where keytool is available.",
            "keystore_properties_path": "ui/android/keystore.properties",
            "store_file_path": str(keystore_path.relative_to(root) if _is_relative_to(keystore_path, root) else keystore_path),
            "setup_command": RELEASE_SIGNING_SETUP_COMMAND,
            "build_command": RELEASE_BUILD_COMMAND,
            "claim_boundary": RELEASE_SIGNING_CLAIM_BOUNDARY,
        }

    store_password = _release_password()
    key_password = store_password
    command = [
        keytool,
        "-genkeypair",
        "-v",
        "-keystore",
        str(keystore_path),
        "-storetype",
        "PKCS12",
        "-alias",
        key_alias,
        "-keyalg",
        "RSA",
        "-keysize",
        "2048",
        "-validity",
        str(max(1, int(validity_days))),
        "-dname",
        dname,
        "-storepass",
        store_password,
        "-keypass",
        key_password,
    ]
    runner = run_command or subprocess.run
    completed = runner(
        command,
        cwd=android_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if int(completed.returncode) != 0:
        return {
            "report_kind": "cas_forex_android_release_signing_setup",
            "status": "keytool_failed",
            "created": False,
            "summary": "Java keytool failed while generating the Android release keystore.",
            "returncode": int(completed.returncode),
            "stdout_present": bool(getattr(completed, "stdout", "")),
            "stderr_present": bool(getattr(completed, "stderr", "")),
            "keystore_properties_path": "ui/android/keystore.properties",
            "store_file_path": str(keystore_path.relative_to(root) if _is_relative_to(keystore_path, root) else keystore_path),
            "setup_command": RELEASE_SIGNING_SETUP_COMMAND,
            "build_command": RELEASE_BUILD_COMMAND,
            "claim_boundary": RELEASE_SIGNING_CLAIM_BOUNDARY,
        }

    properties_path.write_text(
        "\n".join(
            [
                "# Local CAS Forex Android release signing. Do not commit this file.",
                f"storeFile={store_file}",
                f"storePassword={store_password}",
                f"keyAlias={key_alias}",
                f"keyPassword={key_password}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    status = android_release_signing_status(workspace_root=root)
    return {
        "report_kind": "cas_forex_android_release_signing_setup",
        "status": "created" if status.get("ready") else "created_but_not_ready",
        "created": True,
        "summary": (
            "Android release signing keystore and local keystore.properties were created. "
            "Back up ui/android/keystore.properties and the .jks file outside the repo."
        ),
        "keystore_properties_path": "ui/android/keystore.properties",
        "store_file_path": str(keystore_path.relative_to(root) if _is_relative_to(keystore_path, root) else keystore_path),
        "key_alias": key_alias,
        "store_file_exists": bool(status.get("store_file_exists")),
        "inputs_present": status.get("inputs_present"),
        "setup_command": RELEASE_SIGNING_SETUP_COMMAND,
        "build_command": RELEASE_BUILD_COMMAND,
        "claim_boundary": RELEASE_SIGNING_CLAIM_BOUNDARY,
    }


def _resolve_under_root(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _resolve_release_store_file(android_root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    candidate = Path(value)
    return candidate if candidate.is_absolute() else android_root / candidate


def _artifact_fields(root: Path, path: str | Path) -> dict[str, Any]:
    resolved = _resolve_under_root(root, path)
    payload: dict[str, Any] = {
        "path": str(resolved),
        "exists": False,
        "size_bytes": None,
        "sha256": None,
        "modified_at": None,
    }
    if not resolved.exists() or not resolved.is_file():
        return payload
    stat = resolved.stat()
    payload.update(
        {
            "exists": True,
            "size_bytes": stat.st_size,
            "sha256": _sha256_file(resolved),
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        }
    )
    return payload


def _read_properties(path: Path) -> dict[str, str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    out: dict[str, str] = {}
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "!")):
            continue
        separator = "=" if "=" in line else ":" if ":" in line else None
        if not separator:
            continue
        key, value = line.split(separator, 1)
        out[key.strip()] = value.strip()
    return out


def _non_empty(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _release_password() -> str:
    return secrets.token_urlsafe(32)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
    except ValueError:
        return False
    return True
