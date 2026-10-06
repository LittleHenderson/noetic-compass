"""A dedicated persistent memory location: an S3 prefix, reached with the standard library only.

The lasting-memory directive's survival level (b) — the accepted state survives
termination and replacement of the machine — needs storage that is not the
machine. The owner's decision (directive amendment item 1) is to reuse the
existing authorized AWS arrangement. This module is the smallest client that
can put a sealed history document into an S3 prefix and get it back: Signature
Version 4 over `urllib`, no SDK, no dependency.

It lives in `scripts/cas_memory`, outside the reasoning package on purpose:
the sever test guarantees that nothing in `scripts/cas_rpu` can reach the
network, and a storage client can. The organism never imports this module; a
`Stream` receives a store by injection (`mirror=`), so the reasoning package's
law is intact and the storage is replaceable.

What it does not do, by design: create buckets, change policies, list anything
outside the one prefix it is given, or delete. A memory store that can delete
is a memory store that can lose accepted knowledge by a bug; the retention
rule is "archive, never delete by code".

Credentials come from the environment (`AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, optional `AWS_SESSION_TOKEN`); the region and bucket
are explicit arguments, never guessed. Every request failure is raised with
the HTTP status and the service's error code so a permission problem is
reported, not papered over.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from xml.etree import ElementTree

SERVICE = "s3"
_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


class StoreError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret: str, date: str, region: str) -> bytes:
    k = _sign(("AWS4" + secret).encode("utf-8"), date)
    k = _sign(k, region)
    k = _sign(k, SERVICE)
    return _sign(k, "aws4_request")


def _quote(s: str) -> str:
    return urllib.parse.quote(s, safe="-_.~")


@dataclass(frozen=True)
class Credentials:
    access_key: str
    secret_key: str
    session_token: str | None = None

    @classmethod
    def from_env(cls) -> "Credentials":
        access = os.environ.get("AWS_ACCESS_KEY_ID")
        secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
        if not access or not secret:
            raise StoreError("E-S3-001", "no AWS credentials in the environment")
        return cls(access, secret, os.environ.get("AWS_SESSION_TOKEN") or None)


def authorization(method: str, canonical_uri: str, canonical_query: str, headers: dict, payload_hash: str,
                  amz_date: str, region: str, credentials: Credentials) -> str:
    """The Signature Version 4 Authorization header, as a pure function of its inputs.

    Pure so it can be checked against AWS's published test vector without a
    network (see the tests); `_request` only assembles the inputs.
    """
    date = amz_date[:8]
    signed_headers = ";".join(sorted(headers))
    canonical_headers = "".join(f"{k}:{headers[k].strip()}\n" for k in sorted(headers))
    canonical_request = "\n".join([method, canonical_uri, canonical_query, canonical_headers, signed_headers, payload_hash])
    scope = f"{date}/{region}/{SERVICE}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])
    signature = hmac.new(_signing_key(credentials.secret_key, date, region), string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    return (
        f"AWS4-HMAC-SHA256 Credential={credentials.access_key}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )


class S3Prefix:
    """One bucket, one prefix, one region. Put, get, head, list. Never delete."""

    def __init__(self, bucket: str, prefix: str, region: str, credentials: Credentials | None = None, *, timeout: float = 30.0) -> None:
        if not bucket or "/" in bucket:
            raise StoreError("E-S3-002", f"bucket name {bucket!r} invalid")
        self.bucket = bucket
        self.prefix = prefix.strip("/") + "/" if prefix.strip("/") else ""
        self.region = region
        self.credentials = credentials or Credentials.from_env()
        self.timeout = timeout
        self.host = f"{bucket}.s3.{region}.amazonaws.com"

    # ---- signing ------------------------------------------------------------

    def _request(self, method: str, key: str = "", query: dict | None = None, body: bytes = b"", extra_headers: dict | None = None):
        now = _dt.datetime.now(_dt.timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        canonical_uri = "/" + _quote(key) if key else "/"
        query = dict(sorted((query or {}).items()))
        canonical_query = "&".join(f"{_quote(k)}={_quote(str(v))}" for k, v in query.items())
        payload_hash = hashlib.sha256(body).hexdigest() if body else _EMPTY_SHA256
        headers = {
            "host": self.host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        if self.credentials.session_token:
            headers["x-amz-security-token"] = self.credentials.session_token
        for k, v in (extra_headers or {}).items():
            headers[k.lower()] = v
        headers["authorization"] = authorization(
            method, canonical_uri, canonical_query, headers, payload_hash, amz_date, self.region, self.credentials
        )
        url = f"https://{self.host}{canonical_uri}" + (f"?{canonical_query}" if canonical_query else "")
        req = urllib.request.Request(url, data=body if body else None, method=method)
        for k, v in headers.items():
            if k != "host":
                req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            code = "unknown"
            try:
                root = ElementTree.fromstring(detail)
                code = (root.findtext("Code") or code)
            except ElementTree.ParseError:
                pass
            raise StoreError(f"E-S3-HTTP-{exc.code}", f"{method} {key or '/'}: {code}") from None
        except urllib.error.URLError as exc:
            raise StoreError("E-S3-NET", f"{method} {key or '/'}: {exc.reason}") from None

    # ---- the four operations -------------------------------------------------------

    def _full(self, name: str) -> str:
        if not name or name.startswith("/") or ".." in name.split("/"):
            raise StoreError("E-S3-002", f"object name {name!r} invalid")
        return self.prefix + name

    def put(self, name: str, data: bytes) -> str:
        """Write bytes; returns the sha256 the service echoed back as ETag-independent check."""
        digest = hashlib.sha256(data).hexdigest()
        status, headers, _ = self._request("PUT", self._full(name), body=data, extra_headers={"content-type": "application/json"})
        if status not in (200, 201):
            raise StoreError("E-S3-003", f"put {name}: HTTP {status}")
        # Read back and verify: the store is a memory, not a cache.
        back = self.get(name)
        if hashlib.sha256(back).hexdigest() != digest:
            raise StoreError("E-S3-004", f"put {name}: read-back digest differs")
        return digest

    def get(self, name: str) -> bytes:
        status, _, body = self._request("GET", self._full(name))
        if status != 200:
            raise StoreError("E-S3-003", f"get {name}: HTTP {status}")
        return body

    def exists(self, name: str) -> bool:
        try:
            self._request("HEAD", self._full(name))
            return True
        except StoreError as exc:
            if exc.code in ("E-S3-HTTP-404", "E-S3-HTTP-403"):
                return False
            raise

    def list(self) -> list[str]:
        """Object names under the prefix, without the prefix. Never beyond it."""
        names: list[str] = []
        token: str | None = None
        while True:
            query = {"list-type": "2", "prefix": self.prefix}
            if token:
                query["continuation-token"] = token
            status, _, body = self._request("GET", "", query=query)
            if status != 200:
                raise StoreError("E-S3-003", f"list: HTTP {status}")
            root = ElementTree.fromstring(body)
            ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
            for contents in root.findall(f"{ns}Contents"):
                key = contents.findtext(f"{ns}Key") or ""
                if key.startswith(self.prefix):
                    names.append(key[len(self.prefix):])
            if (root.findtext(f"{ns}IsTruncated") or "false").lower() == "true":
                token = root.findtext(f"{ns}NextContinuationToken")
            else:
                break
        return sorted(names)

    def describe(self) -> str:
        return f"s3://{self.bucket}/{self.prefix} ({self.region})"


class DirectoryStore:
    """The same four operations over a local directory.

    Stands in for the remote in tests that must run without credentials, and
    is what "a second location" means on a machine with no network. It is not
    level (b) storage and never claims to be.
    """

    def __init__(self, root) -> None:
        from pathlib import Path
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, name: str, data: bytes) -> str:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def get(self, name: str) -> bytes:
        path = self.root / name
        if not path.exists():
            raise StoreError("E-S3-HTTP-404", f"get {name}: not found")
        return path.read_bytes()

    def exists(self, name: str) -> bool:
        return (self.root / name).exists()

    def list(self) -> list[str]:
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file() and not p.name.endswith(".tmp"))

    def describe(self) -> str:
        return f"dir://{self.root}"
