"""Local at-rest secret envelopes for CAS Forex runtime files.

Windows uses DPAPI scoped to the current user. Non-Windows falls back to a
local key-file stream envelope so runtime JSON never stores raw secrets.
"""

from __future__ import annotations

import base64
import ctypes
import hmac
import json
import os
import secrets
import stat
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_KEY_PATH = REPO_ROOT / "runtime" / "cas-forex-secret.key"
SECRET_ENVELOPE_VERSION = "cas_forex_secret_envelope.v1"
DPAPI_SCHEME = "windows_dpapi_current_user_v1"
LOCAL_SCHEME = "local_hmac_stream_v1"


class SecretEnvelopeError(ValueError):
    """Raised when a local secret envelope cannot be opened."""


def protect_secret(value: str) -> dict[str, Any]:
    plaintext = str(value or "")
    if plaintext == "":
        return {"encrypted": False, "scheme": "empty", "value": ""}
    data = plaintext.encode("utf-8")
    if os.name == "nt":
        ciphertext = _dpapi_protect(data)
        return {
            "encrypted": True,
            "version": SECRET_ENVELOPE_VERSION,
            "scheme": DPAPI_SCHEME,
            "ciphertext": _b64(ciphertext),
        }
    envelope = _local_protect(data)
    envelope.update({"encrypted": True, "version": SECRET_ENVELOPE_VERSION, "scheme": LOCAL_SCHEME})
    return envelope


def unprotect_secret(envelope: Any) -> str:
    if envelope is None:
        return ""
    if isinstance(envelope, str):
        # Legacy plaintext runtime files are accepted so they can be migrated on
        # the next save. Callers decide whether to rewrite the file.
        return envelope
    if not isinstance(envelope, Mapping):
        raise SecretEnvelopeError("secret envelope is not a mapping")
    if not bool(envelope.get("encrypted")):
        return str(envelope.get("value") or "")
    scheme = str(envelope.get("scheme") or "")
    if scheme == DPAPI_SCHEME:
        return _dpapi_unprotect(_unb64(str(envelope.get("ciphertext") or ""))).decode("utf-8")
    if scheme == LOCAL_SCHEME:
        return _local_unprotect(envelope).decode("utf-8")
    raise SecretEnvelopeError(f"unsupported secret envelope scheme: {scheme}")


def is_secret_envelope(value: Any) -> bool:
    return isinstance(value, Mapping) and bool(value.get("encrypted")) and "scheme" in value


def secret_storage_status() -> dict[str, Any]:
    if os.name == "nt":
        return {
            "scheme": DPAPI_SCHEME,
            "at_rest_encrypted": True,
            "scope": "current_windows_user",
        }
    return {
        "scheme": LOCAL_SCHEME,
        "at_rest_encrypted": True,
        "scope": "local_key_file",
        "key_path": str(DEFAULT_LOCAL_KEY_PATH),
    }


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))


def _local_key() -> bytes:
    env_key = os.environ.get("CAS_FOREX_SECRET_STORE_KEY", "").strip()
    if env_key:
        try:
            raw = _unb64(env_key)
        except Exception as exc:  # pragma: no cover - operator config issue
            raise SecretEnvelopeError("CAS_FOREX_SECRET_STORE_KEY is not valid base64") from exc
        if len(raw) < 32:
            raise SecretEnvelopeError("CAS_FOREX_SECRET_STORE_KEY must decode to at least 32 bytes")
        return raw[:32]
    DEFAULT_LOCAL_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DEFAULT_LOCAL_KEY_PATH.exists():
        raw_text = DEFAULT_LOCAL_KEY_PATH.read_text(encoding="utf-8").strip()
        try:
            raw = _unb64(raw_text)
        except Exception as exc:
            raise SecretEnvelopeError(f"secret key file is not valid base64: {DEFAULT_LOCAL_KEY_PATH}") from exc
        if len(raw) < 32:
            raise SecretEnvelopeError(f"secret key file is too short: {DEFAULT_LOCAL_KEY_PATH}")
        return raw[:32]
    raw = secrets.token_bytes(32)
    DEFAULT_LOCAL_KEY_PATH.write_text(_b64(raw), encoding="utf-8")
    try:
        DEFAULT_LOCAL_KEY_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return raw


def _local_protect(data: bytes) -> dict[str, Any]:
    key = _local_key()
    nonce = secrets.token_bytes(16)
    ciphertext = _xor_bytes(data, _keystream(key, nonce, len(data)))
    tag = hmac.new(key, b"CAS_FOREX_SECRET" + nonce + ciphertext, sha256).digest()
    return {
        "nonce": _b64(nonce),
        "ciphertext": _b64(ciphertext),
        "tag": _b64(tag),
    }


def _local_unprotect(envelope: Mapping[str, Any]) -> bytes:
    key = _local_key()
    nonce = _unb64(str(envelope.get("nonce") or ""))
    ciphertext = _unb64(str(envelope.get("ciphertext") or ""))
    tag = _unb64(str(envelope.get("tag") or ""))
    expected = hmac.new(key, b"CAS_FOREX_SECRET" + nonce + ciphertext, sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise SecretEnvelopeError("secret envelope authentication failed")
    return _xor_bytes(ciphertext, _keystream(key, nonce, len(ciphertext)))


def _keystream(key: bytes, nonce: bytes, size: int) -> bytes:
    chunks: list[bytes] = []
    counter = 0
    while sum(len(chunk) for chunk in chunks) < size:
        counter_blob = counter.to_bytes(8, "big")
        chunks.append(hmac.new(key, nonce + counter_blob, sha256).digest())
        counter += 1
    return b"".join(chunks)[:size]


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))


def _dpapi_protect(data: bytes) -> bytes:
    return _dpapi_call(data, protect=True)


def _dpapi_unprotect(data: bytes) -> bytes:
    return _dpapi_call(data, protect=False)


def _dpapi_call(data: bytes, *, protect: bool) -> bytes:
    if os.name != "nt":  # pragma: no cover - guarded by callers
        raise SecretEnvelopeError("DPAPI is available only on Windows")

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_buffer = ctypes.create_string_buffer(data)
    in_blob = DATA_BLOB(len(data), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_byte)))
    out_blob = DATA_BLOB()

    if protect:
        ok = crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            "CAS Forex local runtime secret",
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        )
    else:
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        )
    if not ok:
        raise OSError(ctypes.get_last_error())
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def envelope_to_json(envelope: Mapping[str, Any]) -> str:
    """Debug/test helper that keeps callers from relying on dict ordering."""

    return json.dumps(dict(envelope), sort_keys=True)
