"""Single-request S3 transport with a shared, irreversible local budget.

Every SDK call is preceded by an atomic, fsynced reservation under a finite
cross-process lock. Failed or ambiguous requests consume their reservations;
once-only transfers remain spent across controller modes and process restarts.
There are no paginators, transfer managers, or SDK retries. Multipart output
uses one scoped UploadId, at most 269 parts, and a single completion attempt.
The controller's 18.1 GB response allowance excludes the worker's separately
reserved 4.2 GB input download within the existing AWS region. Controller
Tier1 allowance1600 plus at most370 guest PUTs fits the priced2000 requests.
Each controller request reserves at least64 KiB for response/error overhead.
Lists additionally reserve 16 KiB per requested entry, including XML escaping.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import threading
import time
import uuid

def _op11_deadline():
    value=os.environ.get('OP11_CONTROL_DEADLINE_UNIX')
    if value and time.time()>=float(value):raise ResourceLimitError('OP11 absolute control deadline')


MiB = 1024 * 1024
OVERHEAD_BYTES = 64 * 1024
LIST_ENTRY_BYTES = 16 * 1024
LIMITS = {
    "tier1_attempts": 1600,
    "tier2_attempts": 1000,
    "response_bytes": 18100000000,
    "worker_input_bytes_reserved_separately": 4200000000,
    "response_overhead_per_request": OVERHEAD_BYTES,
    "list_entry_response_bytes": LIST_ENTRY_BYTES,
    "maximum_list_keys": 200,
    "maximum_put_bytes": 4200000000,
    "maximum_get_bytes": 18000000000,
}
SCHEMA = "helm.controller-s3-budget/1"
LEDGER_NAME = "op11-s3-ledger.json"
MAX_LEDGER_BYTES = 8 * MiB
LOCK_WAIT_SECONDS = 10.0
CONTROL_BODY_BYTES = OVERHEAD_BYTES // 2
TIERS = {
    "get_bucket_location": "tier2",
    "get_bucket_request_payment": "tier2",
    "get_bucket_accelerate_configuration": "tier2",
    "get_bucket_versioning": "tier2",
    "get_bucket_lifecycle_configuration": "tier2",
    "get_public_access_block": "tier2",
    "get_bucket_policy_status": "tier2",
    "get_bucket_policy": "tier2",
    "head_object": "tier2",
    "get_object": "tier2",
    "list_object_versions": "tier1",
    "list_objects_v2": "tier1",
    # Deletion is conservatively charged against the Tier 1 request cap.
    "delete_object": "tier1",
    "put_object": "tier1",
    "create_multipart_upload": "tier1",
    "complete_multipart_upload": "tier1",
    "abort_multipart_upload": "tier1",
    "list_multipart_uploads": "tier1",
    "list_parts": "tier1",
}


class ResourceLimitError(RuntimeError):
    """A local budget or bounded response contract prohibits dispatch/use."""


class AttemptAlreadyReserved(ResourceLimitError):
    """A persistent once-only request token has already been consumed."""


class _DeadlineFile:
    """Stream the SDK input body in bounded reads against the original clock."""
    def __init__(self, stream):self._stream=stream
    def read(self, size=-1):
        _op11_deadline()
        if not isinstance(size,int) or not 0 <= size <= 8*MiB:
            raise ResourceLimitError('Unbounded SDK input body read refused')
        return self._stream.read(size)
    def readinto(self, buffer):
        _op11_deadline()
        if len(buffer)>8*MiB:raise ResourceLimitError('Oversized SDK input buffer refused')
        return self._stream.readinto(buffer)
    def seek(self,*args):
        _op11_deadline();return self._stream.seek(*args)
    def __getattr__(self,name):return getattr(self._stream,name)


class _BoundedRaw:
    """Cap raw reads before botocore buffers control and error responses."""

    def __init__(self, raw, limit, declared_length):
        self._raw = raw
        self._limit = limit
        self._declared_length = declared_length
        self._received = 0

    def read(self, amt=None, decode_content=None, cache_content=False):
        _op11_deadline()
        if decode_content:
            raise ResourceLimitError("Decoded S3 transport bodies are prohibited")
        if amt == 0:
            return b""
        remaining = self._limit - self._received
        if remaining == 0:
            if self._declared_length == self._received:
                self.close()
                return b""
            self.close()
            raise ResourceLimitError("S3 raw response byte cap reached before verified EOF")
        amount = remaining if amt is None or amt < 0 else min(amt, remaining)
        chunk = self._raw.read(amount, decode_content=False, cache_content=False)
        self._received += len(chunk)
        if self._received > self._limit:
            self.close()
            raise ResourceLimitError("S3 raw response exceeded its byte cap")
        return chunk

    def stream(self, amt=16 * 1024, decode_content=None):
        while True:
            chunk = self.read(amt, decode_content=decode_content)
            if not chunk:
                return
            yield chunk

    def close(self):
        return self._raw.close()

    def __getattr__(self, name):
        return getattr(self._raw, name)


def _utc():
    return datetime.now(timezone.utc).isoformat()


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(MiB), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _integer(value, name, minimum=0, maximum=None):
    if type(value) is not int or value < minimum:
        raise ValueError(name + " must be a bounded integer")
    if maximum is not None and value > maximum:
        raise ResourceLimitError(name + " exceeds its limit")
    return value


def _version(value):
    # S3's literal 'null' is the version identifier for an unversioned object.
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 1024:
        raise ValueError("A nonempty actual VersionId is required")
    return value


def _fsync_directory(directory):
    if os.name != "nt":
        descriptor = os.open(str(directory), os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _atomic_json(path, value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_LEDGER_BYTES:
        raise ResourceLimitError("Persistent S3 ledger size limit")
    temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        # Flush the installed file too; Windows does not expose POSIX directory
        # fsync. Any failed persistence step prevents the subsequent SDK call.
        with path.open("r+b") as stream:
            os.fsync(stream.fileno())
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def _locked(path):
    with path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
            os.fsync(stream.fileno())
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        acquired = False
        while not acquired:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except OSError as error:
                if time.monotonic() >= deadline:
                    raise ResourceLimitError("S3 budget lock wait exceeded") from error
                time.sleep(0.05)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class BudgetedS3:
    """All instances for this work root share one persisted S3 budget."""

    sha_file = staticmethod(sha_file)

    def __init__(self, client, work_root, *, owner, bucket, prefix, region="us-west-2"):
        if not re.fullmatch(r"[0-9]{12}", owner):
            raise ValueError("Expected a twelve-digit AWS account")
        if not isinstance(bucket, str) or not bucket:
            raise ValueError("A fixed S3 bucket is required")
        if (not isinstance(prefix, str) or not prefix.endswith("/")
                or prefix.startswith("/") or len(prefix.encode("utf-8")) > 900
                or any(part in ("", ".", "..") for part in prefix[:-1].split("/"))):
            raise ValueError("A nonempty, fixed job prefix ending in '/' is required")
        self._client = client
        self.work_root = Path(work_root).resolve()
        self.work_root.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.work_root / LEDGER_NAME
        self.lock_path = self.work_root / (LEDGER_NAME + ".lock")
        self.identity = {
            "account": owner, "region": region, "bucket": bucket,
            "prefix": prefix, "job": prefix.rstrip("/").rsplit("/", 1)[-1],
        }
        self.exceptions = client.exceptions
        self._validate_client()
        if getattr(client, "_helm_budgeted_s3_owner", None) is not None:
            raise ValueError("Construct exactly one BudgetedS3 wrapper per SDK client")
        self._original_http_send = client._endpoint.http_session.send
        if not callable(self._original_http_send):
            raise ValueError("S3 SDK raw-response transport interface is unavailable")
        # max_attempts=0 alone does not disable S3's region redirect handlers.
        # Gate the actual before-send event, which also covers their internal
        # HeadBucket calls and subsequent sends, before any network dispatch.
        self._send_budget = threading.local()
        client.meta.events.register_first(
            "before-send.s3", self._before_send,
            unique_id="helm-bounded-s3-single-send-" + str(id(self)),
        )
        client._endpoint.http_session.send = self._send_http
        client._helm_budgeted_s3_owner = self
        with _locked(self.lock_path):
            state = self._read_state()
            if not self.ledger_path.exists():
                _atomic_json(self.ledger_path, state)

    def _before_send(self, **kwargs):
        if (not getattr(self._send_budget, "active", False)
                or getattr(self._send_budget, "remaining", 0) != 1):
            raise ResourceLimitError("Unreserved S3 HTTP request or internal retry blocked")
        self._send_budget.remaining = 0
        self._send_budget.http_allowed = True

    def _send_http(self, request, **kwargs):
        if (not getattr(self._send_budget, "active", False)
                or not getattr(self._send_budget, "http_allowed", False)):
            raise ResourceLimitError("Unreserved S3 HTTP transport call blocked")
        self._send_budget.http_allowed = False
        # Suppress the HTTP session's eager control/error-body buffering so the
        # raw cap is attached before the operation-model parser consumes it.
        original_stream_output = request.stream_output
        request.stream_output = True
        try:
            response = self._original_http_send(request, **kwargs)
        finally:
            request.stream_output = original_stream_output
        try:
            limit = self._send_budget.raw_body_limit
            if response.status_code >= 300:
                limit = min(limit, CONTROL_BODY_BYTES)
            # HEAD Content-Length describes the object, not a response body.
            if request.method == "HEAD":
                declared = 0
                limit = 0
            else:
                header = response.headers.get("content-length")
                declared = int(header) if header is not None else None
                if declared is not None and (declared < 0 or declared > limit):
                    raise ResourceLimitError("S3 raw Content-Length exceeds its reservation")
            response.raw = _BoundedRaw(response.raw, limit, declared)
            return response
        except BaseException:
            response.raw.close()
            raise

    def _validate_client(self):
        config = self._client.meta.config
        retries = config.retries or {}
        total = retries.get("total_max_attempts")
        if not (total == 1 or (total is None and retries.get("max_attempts") == 0)):
            raise ValueError("S3 SDK retries must be disabled before use")
        if self._client.meta.region_name != self.identity["region"]:
            raise ValueError("S3 client region does not match the fixed identity")
        if (config.s3 or {}).get("use_accelerate_endpoint"):
            raise ValueError("S3 acceleration is prohibited")
        for name in ("connect_timeout", "read_timeout"):
            value = getattr(config, name, None)
            if not isinstance(value, (int, float)) or not 0 < value <= 30:
                raise ValueError("S3 client needs finite connect/read timeouts at most 30 seconds")

    def _initial(self):
        return {
            "schema": SCHEMA, "identity": dict(self.identity), "limits": dict(LIMITS),
            "attempted": {"tier1": 0, "tier2": 0}, "response_bytes_reserved": 0,
            "once": {}, "attempts": [],
        }

    def _read_state(self):
        if not self.ledger_path.exists():
            return self._initial()
        if self.ledger_path.stat().st_size > MAX_LEDGER_BYTES:
            raise ResourceLimitError("Persistent S3 ledger size limit")
        state = json.loads(self.ledger_path.read_bytes())
        if (state.get("schema") != SCHEMA or state.get("identity") != self.identity
                or state.get("limits") != LIMITS):
            raise ResourceLimitError("S3 ledger identity or policy changed")
        counts = {"tier1": 0, "tier2": 0}
        response_bytes = 0
        once = {}
        attempts = state.get("attempts")
        if not isinstance(attempts, list) or len(attempts) > 2799:
            raise ResourceLimitError("Malformed S3 ledger attempts")
        for index, attempt in enumerate(attempts):
            operation = attempt.get("operation")
            if attempt.get("id") != index or operation not in TIERS:
                raise ResourceLimitError("Malformed S3 ledger attempt")
            tier = TIERS[operation]
            if attempt.get("tier") != tier:
                raise ResourceLimitError("Malformed S3 ledger request tier")
            counts[tier] += 1
            response_bytes += _integer(attempt.get("response_bytes_reserved"),
                                       "reserved response bytes", OVERHEAD_BYTES)
            token = attempt.get("once")
            if token is not None:
                if not isinstance(token, str) or not token or token in once:
                    raise ResourceLimitError("Malformed S3 ledger once token")
                once[token] = index
        if (state.get("attempted") != counts
                or state.get("response_bytes_reserved") != response_bytes
                or state.get("once") != once):
            raise ResourceLimitError("S3 ledger accounting mismatch")
        if (counts["tier1"] > LIMITS["tier1_attempts"]
                or counts["tier2"] > LIMITS["tier2_attempts"]
                or response_bytes > LIMITS["response_bytes"]):
            raise ResourceLimitError("Existing S3 ledger exceeds its policy")
        return state

    def snapshot(self):
        with _locked(self.lock_path):
            return self._read_state()

    def _reserve(self, operation, kwargs, response_bytes, once):
        _integer(response_bytes, "response bytes", OVERHEAD_BYTES, LIMITS["response_bytes"])
        if once is not None and (not isinstance(once, str)
                                 or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", once)):
            raise ValueError("A short stable once token is required")
        tier = TIERS[operation]
        with _locked(self.lock_path):
            state = self._read_state()
            if once is not None and once in state["once"]:
                raise AttemptAlreadyReserved("S3 attempt already reserved: " + once)
            if state["attempted"][tier] >= LIMITS[tier + "_attempts"]:
                raise ResourceLimitError("S3 " + tier + " request cap reached")
            if state["response_bytes_reserved"] + response_bytes > LIMITS["response_bytes"]:
                raise ResourceLimitError("S3 cumulative response byte cap reached")
            index = len(state["attempts"])
            attempt = {
                "id": index, "utc": _utc(), "operation": operation, "tier": tier,
                "key": kwargs.get("Key"), "prefix": kwargs.get("Prefix"),
                "version_id": kwargs.get("VersionId"), "range": kwargs.get("Range"),
                "response_bytes_reserved": response_bytes, "once": once,
            }
            state["attempts"].append(attempt)
            state["attempted"][tier] += 1
            state["response_bytes_reserved"] += response_bytes
            if once is not None:
                state["once"][once] = index
            _atomic_json(self.ledger_path, state)

    def _key(self, key):
        if (not isinstance(key, str) or not key.startswith(self.identity["prefix"])
                or key == self.identity["prefix"] or len(key.encode("utf-8")) > 1024):
            raise ValueError("S3 key must remain strictly within the fixed job prefix")
        return key

    def _scope(self, operation, kwargs):
        if operation not in TIERS:
            raise ValueError("S3 operation is not in the bounded allowlist")
        kwargs = dict(kwargs)
        for name, fixed in (("Bucket", self.identity["bucket"]),
                            ("ExpectedBucketOwner", self.identity["account"])):
            if name in kwargs and kwargs[name] != fixed:
                raise ValueError("S3 " + name + " does not match the fixed job")
            kwargs[name] = fixed
        if "RequestPayer" in kwargs:
            raise ValueError("Requester Pays requests are prohibited")
        if operation in ("head_object", "get_object", "put_object", "delete_object", "create_multipart_upload", "complete_multipart_upload", "abort_multipart_upload", "list_parts"):
            self._key(kwargs.get("Key"))
        if operation in ("create_multipart_upload", "complete_multipart_upload", "abort_multipart_upload", "list_parts"):
            if kwargs.get("Key") != self.identity["prefix"] + "pointer-saturation-deliverable.zip":
                raise ValueError("Multipart is restricted to the one output key")
        if operation in ("complete_multipart_upload", "abort_multipart_upload", "list_parts"):
            upload_id = kwargs.get("UploadId")
            if not isinstance(upload_id, str) or not 1 <= len(upload_id) <= 2048:
                raise ValueError("Explicit scoped multipart UploadId required")
        if operation == "create_multipart_upload" and set(kwargs) != {"Bucket", "Key", "ExpectedBucketOwner", "ContentType"}:
            raise ValueError("No multipart configuration changes permitted")
        if operation == "complete_multipart_upload":
            parts = kwargs.get("MultipartUpload", {}).get("Parts")
            if not isinstance(parts, list) or not 1 <= len(parts) <= 269:
                raise ValueError("Bounded multipart completion required")
            for number, part in enumerate(parts, 1):
                if set(part) != {"PartNumber", "ETag"} or part["PartNumber"] != number or not re.fullmatch(r'"[0-9a-f]{32}"', part["ETag"]):
                    raise ValueError("Exact sequential ordinary part ETags required")
        if operation == "list_parts":
            if kwargs.get("PartNumberMarker", 0) != 0:
                raise ValueError("No multipart pagination admitted")
            kwargs["MaxParts"] = _integer(kwargs.get("MaxParts", 300), "MaxParts", 1, 300)
        if operation == "list_multipart_uploads":
            if kwargs.get("Prefix", self.identity["prefix"]) != self.identity["prefix"]:
                raise ValueError("Exact multipart list prefix required")
            kwargs["Prefix"] = self.identity["prefix"]
            kwargs["MaxUploads"] = _integer(kwargs.get("MaxUploads", 10), "MaxUploads", 1, 10)
            if "KeyMarker" in kwargs or "UploadIdMarker" in kwargs:
                raise ValueError("No multipart upload pagination admitted")
        if "VersionId" in kwargs:
            _version(kwargs["VersionId"])
        if operation == "delete_object" and "VersionId" not in kwargs:
            raise ValueError("Deletion requires an explicit actual VersionId")
        if operation in ("list_object_versions", "list_objects_v2"):
            prefix = kwargs.get("Prefix", self.identity["prefix"])
            if not isinstance(prefix, str) or not prefix.startswith(self.identity["prefix"]):
                raise ValueError("List prefix must remain within the fixed job prefix")
            kwargs["Prefix"] = prefix
            kwargs["MaxKeys"] = _integer(kwargs.get("MaxKeys", 200), "MaxKeys", 1, 200)
            for name in ("KeyMarker", "StartAfter"):
                if name in kwargs:
                    self._key(kwargs[name])
        return kwargs

    def _dispatch(self, operation, kwargs, *, response_bytes, once=None):
        if getattr(self._send_budget, "active", False):
            raise ResourceLimitError("Nested S3 budget dispatch is prohibited")
        kwargs = self._scope(operation, kwargs)
        self._validate_client()
        self._reserve(operation, kwargs, response_bytes, once)
        # No reservation is ever released, including exceptions raised here.
        self._send_budget.active = True
        self._send_budget.remaining = 1
        self._send_budget.http_allowed = False
        self._send_budget.raw_body_limit = (response_bytes - OVERHEAD_BYTES
                                            if response_bytes > OVERHEAD_BYTES
                                            else CONTROL_BODY_BYTES)
        try:
            return getattr(self._client, operation)(**kwargs)
        finally:
            self._send_budget.remaining = 0
            self._send_budget.http_allowed = False
            self._send_budget.active = False

    def call(self, operation, *, tier=None, response_bytes=OVERHEAD_BYTES, once=None, **kwargs):
        if operation in ("get_object", "put_object"):
            raise ValueError("Use bounded get_bytes/get_file/put_file for object bodies")
        scoped = self._scope(operation, kwargs)
        if tier is not None and tier != TIERS[operation]:
            raise ValueError("Request tier cannot override the operation's actual tier")
        minimum = OVERHEAD_BYTES
        if operation in ("list_object_versions", "list_objects_v2"):
            minimum += scoped["MaxKeys"] * LIST_ENTRY_BYTES
        if operation == "list_parts":
            minimum += scoped["MaxParts"] * LIST_ENTRY_BYTES
        if operation == "list_multipart_uploads":
            minimum += scoped["MaxUploads"] * LIST_ENTRY_BYTES
        _integer(response_bytes, "response bytes", OVERHEAD_BYTES)
        return self._dispatch(operation, scoped,
                              response_bytes=max(minimum, response_bytes), once=once)

    def control(self, operation, **kwargs):
        return self.call(operation, **kwargs)

    def get_bucket_location(self, **kwargs):
        return self.call("get_bucket_location", **kwargs)

    def get_bucket_request_payment(self, **kwargs):
        return self.call("get_bucket_request_payment", **kwargs)

    def get_bucket_accelerate_configuration(self, **kwargs):
        return self.call("get_bucket_accelerate_configuration", **kwargs)

    def list_object_versions(self, **kwargs):
        return self.call("list_object_versions", **kwargs)

    def list_objects_v2(self, **kwargs):
        return self.call("list_objects_v2", **kwargs)

    def head_object(self, **kwargs):
        return self.call("head_object", **kwargs)

    def delete_object(self, **kwargs):
        return self.call("delete_object", **kwargs)

    def head(self, key, *, version_id=None):
        kwargs = {"Key": key}
        if version_id is not None:
            kwargs["VersionId"] = _version(version_id)
        return self.call("head_object", **kwargs)

    def put_file(self, key, path, *, max_bytes=64 * MiB, once="input_put"):
        if once != "input_put":
            raise ValueError("Input PUT must use the persistent input_put singleton")
        self._key(key)
        _integer(max_bytes, "put maximum bytes", 1, LIMITS["maximum_put_bytes"])
        source = Path(path)
        if source.is_symlink():
            raise ValueError("Upload source must be a regular nonsymlink file")
        descriptor, temporary_name = tempfile.mkstemp(prefix=".s3-put-", dir=self.work_root)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w+b") as snapshot:
                digest = hashlib.sha256()
                length = 0
                with source.open("rb") as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                        raise ValueError("Upload source must be a regular file")
                    while True:
                        _op11_deadline()
                        chunk = stream.read(min(MiB, max_bytes - length + 1))
                        if not chunk:
                            break
                        length += len(chunk)
                        if length > max_bytes:
                            raise ResourceLimitError("Upload exceeds its single-part byte cap")
                        snapshot.write(chunk)
                        digest.update(chunk)
                snapshot.flush()
                os.fsync(snapshot.fileno())
                snapshot.seek(0)
                checksum = digest.hexdigest()
                response = self._dispatch("put_object", {
                    "Key": key, "Body": _DeadlineFile(snapshot), "ContentLength": length,
                    "Metadata": {"sha256": checksum, "length": str(length)},
                }, response_bytes=OVERHEAD_BYTES, once=once)
            return {"sha256": checksum, "bytes": length,
                    "version_id": response.get("VersionId") or "null", "response": response}
        finally:
            if temporary.exists():
                temporary.unlink()

    def _get_response(self, key, *, limit, version_id, once):
        self._key(key)
        _integer(limit, "get maximum bytes", 1, LIMITS["maximum_get_bytes"])
        kwargs = {"Key": key, "Range": "bytes=0-" + str(limit - 1)}
        if version_id is not None:
            kwargs["VersionId"] = _version(version_id)
        return self._dispatch("get_object", kwargs,
                              response_bytes=OVERHEAD_BYTES + limit, once=once)

    @staticmethod
    def _response_length(response, *, limit, version_id, expected_bytes=None):
        length = _integer(response.get("ContentLength"), "S3 response ContentLength", 0, limit)
        if version_id is not None and (response.get("VersionId") or "null") != version_id:
            raise ValueError("S3 GET returned a different object version")
        content_range = response.get("ContentRange")
        if content_range is not None:
            match = re.fullmatch(r"bytes 0-([0-9]+)/([0-9]+)", content_range)
            if not match or int(match[1]) + 1 != length or int(match[2]) != length:
                raise ResourceLimitError("S3 range response is not the complete bounded object")
        if expected_bytes is not None and length != expected_bytes:
            raise ValueError("S3 GET length differs from the pinned object length")
        return length

    @staticmethod
    def _copy_body(body, stream, length):
        digest = hashlib.sha256()
        copied = 0
        while copied < length:
            _op11_deadline()
            chunk = body.read(min(MiB, length - copied))
            if not chunk:
                raise ValueError("S3 response body ended before its declared length")
            copied += len(chunk)
            if copied > length:
                raise ResourceLimitError("S3 body exceeded its declared byte bound")
            stream.write(chunk)
            digest.update(chunk)
        return copied, digest.hexdigest()

    def get_bytes(self, key, *, limit=OVERHEAD_BYTES, version_id=None, once=None):
        # Small control/progress/terminal objects only; never a large ZIP in RAM.
        _integer(limit, "small GET byte limit", 1, OVERHEAD_BYTES)
        response = self._get_response(key, limit=limit, version_id=version_id, once=once)
        body = response["Body"]
        try:
            length = self._response_length(response, limit=limit, version_id=version_id)
            import io
            result = io.BytesIO()
            self._copy_body(body, result, length)
            return result.getvalue()
        finally:
            body.close()

    def get_file(self, key, path, *, max_bytes, expected_bytes, expected_sha256,
                 version_id, once="final_get"):
        if once != "final_get":
            raise ValueError("Final GET must use the persistent final_get singleton")
        _integer(max_bytes, "file GET maximum bytes", 1, LIMITS["maximum_get_bytes"])
        _integer(expected_bytes, "pinned GET bytes", 1, max_bytes)
        _version(version_id)
        if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise ValueError("A lowercase SHA256 from the pinned object metadata is required")
        destination = Path(path).resolve()
        if not destination.is_relative_to(self.work_root):
            raise ValueError("Downloaded artifact must remain within the work root")
        if destination == self.ledger_path or destination == self.lock_path:
            raise ValueError("Downloaded artifact cannot replace its transport ledger")
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".s3-get-", dir=destination.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                response = self._get_response(key, limit=expected_bytes,
                                              version_id=version_id, once=once)
                body = response["Body"]
                try:
                    length = self._response_length(response, limit=expected_bytes,
                                                   version_id=version_id,
                                                   expected_bytes=expected_bytes)
                    copied, checksum = self._copy_body(body, stream, length)
                finally:
                    body.close()
                if copied != expected_bytes or checksum != expected_sha256:
                    raise ValueError("Downloaded artifact does not match pinned length/SHA256")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
            with destination.open("r+b") as stream:
                os.fsync(stream.fileno())
            _fsync_directory(destination.parent)
            return {"path": str(destination), "bytes": copied,
                    "sha256": checksum, "version_id": version_id}
        finally:
            if temporary.exists():
                temporary.unlink()


BoundedS3 = BudgetedS3

