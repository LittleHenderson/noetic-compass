"""helm_cold_cloud.py -- the cloud tier of HELM's cold memory (A-TEACH2-5 L3-L6): where the oldest verbatim originals
go when the device's own cold folder is full, and where HELM fetches them back when it is online.

WHAT THIS IS, IN PLAIN WORDS
----------------------------
Three tiers: WORKING (lines and capsules, in RAM) -> LOCAL COLD (verbatim originals in the device's folder) -> CLOUD
COLD (a private S3 bucket). This module is only the last step: put bytes, get bytes, say whether the cloud can be
reached. It never deletes anything (only the owner deletes). The caller checks every fingerprint.

  FakeCloud  an in-memory stand-in for tests and exams (no network); `online` and `corrupt` are set by the test.
  S3Cloud    the real bucket through the AWS command line tool (standard library only: one subprocess per call).
  S3DirectCloud  the real bucket spoken to directly (A-TEACH2-14): one kept HTTPS connection, requests signed with
             AWS Signature Version 4 by the standard library; keys from the environment or ~/.aws/credentials,
             never printed. No new program per call.
             Uploads are encrypted at rest by AWS (SSE-S3) and never carry an ACL; the bucket blocks public access.

Design: docs/working/helm_cube_oscillation_v1/AMENDMENT_A_TEACH2_5.md; spec 7.125.
CLAIM STATUS: ENGINEERED-NOT-VALIDATED.
"""
from __future__ import annotations

import configparser
import hashlib
import hmac
import http.client
import os
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, List, Optional, Tuple

DEFAULT_BUCKET = "helm-cold-memory-807562639912-usw2"
DEFAULT_REGION = "us-west-2"
CLI_TIMEOUT_S = 60
#: A-TEACH2-13: a "reachable" yes is remembered this long (seconds); a no is never remembered; any failed call forgets
REACHABLE_MEMORY_S = 60
_now = time.monotonic


def remembered_reachable(cloud: Any) -> bool:
    until = getattr(cloud, "_reachable_until", None)
    return until is not None and _now() < until


def remember_reachable(cloud: Any) -> None:
    try:
        cloud._reachable_until = _now() + REACHABLE_MEMORY_S
    except AttributeError:
        pass


def forget_reachable(cloud: Any) -> None:
    try:
        cloud._reachable_until = None
    except AttributeError:
        pass


def is_reachable(cloud: Any) -> bool:
    """Yes if a yes was remembered less than REACHABLE_MEMORY_S ago; otherwise ask the cloud (one call) and remember
    only a yes."""
    if cloud is None:
        return False
    if remembered_reachable(cloud):
        return True
    try:
        ok = bool(cloud.available())
    except Exception:
        ok = False
    (remember_reachable if ok else forget_reachable)(cloud)
    return ok


class CloudUnavailable(RuntimeError):
    """The cloud cannot be reached right now (no Wi-Fi, no credentials, or the call failed)."""


class FakeCloud:
    """A stand-in for the bucket. `corrupt=True` stores damaged bytes, so the read-back check fails."""

    def __init__(self, online: bool = True, corrupt: bool = False) -> None:
        self.online = online
        self.corrupt = corrupt
        self.objects: Dict[str, bytes] = {}
        self.deletes = 0

    def available(self) -> bool:
        return self.online

    def put(self, key: str, data: bytes) -> None:
        if not self.online:
            raise CloudUnavailable("offline")
        self.objects[key] = (data[:-1] + b"#") if (self.corrupt and data) else bytes(data)

    def get(self, key: str) -> Optional[bytes]:
        if not self.online:
            raise CloudUnavailable("offline")
        return self.objects.get(key)

    def get_many(self, prefix: str, suffix: str) -> Dict[str, bytes]:
        """Every object under `prefix` whose name ends with `suffix`, in one call (A-TEACH2-12)."""
        if not self.online:
            raise CloudUnavailable("offline")
        return {k: v for k, v in self.objects.items() if k.startswith(prefix) and k.endswith(suffix)}


class S3Cloud:
    """The private bucket, through `aws s3api`. `runner` is subprocess.run (a test passes a fake one)."""

    def __init__(self, bucket: str = DEFAULT_BUCKET, prefix: str = "", region: str = DEFAULT_REGION,
                 aws: str = "aws", runner: Optional[Callable[..., Any]] = None) -> None:
        self.bucket, self.prefix, self.region, self.aws = bucket, prefix, region, aws
        self.runner = runner or subprocess.run

    def _run(self, args: List[str]) -> Any:
        try:
            res = self.runner([self.aws, "s3api"] + args + ["--region", self.region], capture_output=True,
                              timeout=CLI_TIMEOUT_S)
        except (OSError, subprocess.SubprocessError) as exc:
            raise CloudUnavailable(str(exc)) from exc
        if res.returncode != 0:
            raise CloudUnavailable((res.stderr or b"").decode("utf-8", "replace")[:200])
        return res

    def available(self) -> bool:
        try:
            self._run(["head-bucket", "--bucket", self.bucket])
            return True
        except CloudUnavailable:
            return False

    def put(self, key: str, data: bytes) -> None:
        fd, path = tempfile.mkstemp(prefix="helm_cold_")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            self._run(["put-object", "--bucket", self.bucket, "--key", key, "--body", path,
                       "--server-side-encryption", "AES256"])
        finally:
            os.remove(path)

    def get_many(self, prefix: str, suffix: str) -> Dict[str, bytes]:
        """Every object under `prefix` whose name ends with `suffix`, in ONE `aws s3 cp --recursive` call into a
        temporary folder that is removed afterwards (A-TEACH2-12)."""
        tmp = tempfile.mkdtemp(prefix="helm_cold_many_")
        try:
            try:
                res = self.runner([self.aws, "s3", "cp", f"s3://{self.bucket}/{prefix}", tmp, "--recursive",
                                   "--exclude", "*", "--include", f"*{suffix}", "--region", self.region],
                                  capture_output=True, timeout=CLI_TIMEOUT_S * 5)
            except (OSError, subprocess.SubprocessError) as exc:
                raise CloudUnavailable(str(exc)) from exc
            if res.returncode != 0:
                raise CloudUnavailable((res.stderr or b"").decode("utf-8", "replace")[:200])
            out: Dict[str, bytes] = {}
            for root, _dirs, files in os.walk(tmp):
                for name in files:
                    full = os.path.join(root, name)
                    rel = os.path.relpath(full, tmp).replace(os.sep, "/")
                    with open(full, "rb") as fh:
                        out[prefix + rel] = fh.read()
            return out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def get(self, key: str) -> Optional[bytes]:
        fd, path = tempfile.mkstemp(prefix="helm_cold_")
        os.close(fd)
        try:
            self._run(["get-object", "--bucket", self.bucket, "--key", key, path])
            with open(path, "rb") as fh:
                return fh.read()
        finally:
            os.remove(path)


# ===================================================================== the direct client (A-TEACH2-14)
# Standard library only: one kept HTTPS connection (http.client), AWS Signature Version 4 (hashlib + hmac), the object
# list read with xml.etree. Keys come from the environment or ~/.aws/credentials and are never printed or logged.
def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _enc(text: str, safe: str = "-_.~") -> str:
    return urllib.parse.quote(text, safe=safe)


def sigv4_authorization(method: str, path: str, query: Dict[str, str], headers: Dict[str, str], payload_sha256: str,
                        amz_date: str, region: str, access_key: str, secret_key: str, service: str = "s3") -> str:
    """The Authorization header of AWS Signature Version 4 for one request (every given header is signed)."""
    canon_uri = _enc(path, safe="/-_.~")
    canon_query = "&".join(f"{_enc(k)}={_enc(v)}" for k, v in sorted(query.items()))
    h = {k.lower().strip(): " ".join(str(v).strip().split()) for k, v in headers.items()}
    signed = ";".join(sorted(h))
    canon_headers = "".join(f"{k}:{h[k]}\n" for k in sorted(h))
    canonical = "\n".join([method, canon_uri, canon_query, canon_headers, signed, payload_sha256])
    scope = f"{amz_date[:8]}/{region}/{service}/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, sha256_hex(canonical.encode("utf-8"))])
    key = ("AWS4" + secret_key).encode("utf-8")
    for part in (amz_date[:8], region, service, "aws4_request"):
        key = hmac.new(key, part.encode("utf-8"), hashlib.sha256).digest()
    signature = hmac.new(key, to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, SignedHeaders={signed}, Signature={signature}"


def load_credentials(env: Optional[Dict[str, str]] = None,
                     path: Optional[str] = None) -> Optional[Tuple[str, str, Optional[str]]]:
    """(access key, secret key, session token or None): the environment first, else [default] of ~/.aws/credentials."""
    env = os.environ if env is None else env
    if env.get("AWS_ACCESS_KEY_ID") and env.get("AWS_SECRET_ACCESS_KEY"):
        return env["AWS_ACCESS_KEY_ID"], env["AWS_SECRET_ACCESS_KEY"], env.get("AWS_SESSION_TOKEN") or None
    path = path or os.path.join(os.path.expanduser("~"), ".aws", "credentials")
    parser = configparser.ConfigParser()
    try:
        if not parser.read(path, encoding="utf-8") or not parser.has_section("default"):
            return None
    except configparser.Error:
        return None
    sec = parser["default"]
    if not sec.get("aws_access_key_id") or not sec.get("aws_secret_access_key"):
        return None
    return sec["aws_access_key_id"].strip(), sec["aws_secret_access_key"].strip(), (sec.get("aws_session_token") or None)


class S3DirectCloud:
    """The private bucket, spoken to directly over one kept HTTPS connection (A-TEACH2-14). Same operations as S3Cloud;
    no delete. A missing object is None; any other failure raises CloudUnavailable."""

    def __init__(self, bucket: str = DEFAULT_BUCKET, region: str = DEFAULT_REGION,
                 credentials: Optional[Tuple[str, str, Optional[str]]] = None, env: Optional[Dict[str, str]] = None,
                 credentials_path: Optional[str] = None, conn_factory: Optional[Callable[..., Any]] = None,
                 timeout: float = 30) -> None:
        self.bucket, self.region, self.timeout = bucket, region, timeout
        self.host = f"{bucket}.s3.{region}.amazonaws.com"
        self._creds = credentials if credentials is not None else load_credentials(env, credentials_path)
        self._factory = conn_factory or (lambda host, timeout=None: http.client.HTTPSConnection(host, timeout=timeout))
        self._conn: Any = None

    def __repr__(self) -> str:
        return f"S3DirectCloud(bucket={self.bucket!r}, region={self.region!r}, keys={'set' if self._creds else 'none'})"

    __str__ = __repr__

    def _request(self, method: str, key: str, query: Optional[Dict[str, str]] = None, body: bytes = b"",
                 extra: Optional[Dict[str, str]] = None) -> Tuple[int, bytes]:
        if not self._creds:
            raise CloudUnavailable("no AWS keys found")
        access, secret, token = self._creds
        query = query or {}
        path = "/" + key
        url = _enc(path, safe="/-_.~")
        if query:
            url += "?" + "&".join(f"{_enc(k)}={_enc(v)}" for k, v in sorted(query.items()))
        for attempt in (0, 1):
            amz_date = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            payload = sha256_hex(body)
            headers = {"host": self.host, "x-amz-date": amz_date, "x-amz-content-sha256": payload}
            headers.update(extra or {})
            if token:
                headers["x-amz-security-token"] = token
            headers["Authorization"] = sigv4_authorization(method, path, query, headers, payload, amz_date, self.region,
                                                           access, secret)
            try:
                if self._conn is None:
                    self._conn = self._factory(self.host, timeout=self.timeout)
                self._conn.request(method, url, body=body if method == "PUT" else None, headers=headers)
                resp = self._conn.getresponse()
                return resp.status, resp.read()
            except (http.client.HTTPException, OSError) as exc:
                try:
                    if self._conn is not None:
                        self._conn.close()
                except Exception:
                    pass
                self._conn = None                       # K2: reopen once, then give up
                if attempt == 1:
                    raise CloudUnavailable(type(exc).__name__) from exc
        raise CloudUnavailable("unreachable")

    def available(self) -> bool:
        try:
            return self._request("HEAD", "")[0] == 200
        except CloudUnavailable:
            return False

    def put(self, key: str, data: bytes) -> None:
        status, _ = self._request("PUT", key, body=bytes(data), extra={"x-amz-server-side-encryption": "AES256"})
        if status != 200:
            raise CloudUnavailable(f"put status {status}")

    def get(self, key: str) -> Optional[bytes]:
        status, data = self._request("GET", key)
        if status == 200:
            return data
        if status == 404:
            return None
        raise CloudUnavailable(f"get status {status}")

    def get_many(self, prefix: str, suffix: str) -> Dict[str, bytes]:
        keys: List[str] = []
        token: Optional[str] = None
        while True:
            q = {"list-type": "2", "prefix": prefix}
            if token:
                q["continuation-token"] = token
            status, data = self._request("GET", "", query=q)
            if status != 200:
                raise CloudUnavailable(f"list status {status}")
            root = ET.fromstring(data)
            ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
            keys += [el.text or "" for el in root.iter(f"{ns}Key")]
            truncated = (root.findtext(f"{ns}IsTruncated") or "false").strip().lower() == "true"
            token = root.findtext(f"{ns}NextContinuationToken")
            if not truncated or not token:
                break
        out: Dict[str, bytes] = {}
        for k in keys:
            if k.endswith(suffix):
                got = self.get(k)
                if got is not None:
                    out[k] = got
        return out
