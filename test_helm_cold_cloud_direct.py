"""test_helm_cold_cloud_direct.py -- HELM's direct cloud client (A-TEACH2-14), FIX FIRST.

Written BEFORE the code. Owner's words (2026-10-22): "build a direct cloud client for HELM (standard library only, signs
its own requests, keeps one connection open) so cloud calls stop starting a new program each time." In plain words:
  - the request signing matches AWS's own published Signature Version 4 examples for S3 (an unfakeable check);
  - one connection is opened and kept; a dropped connection is reopened once;
  - uploads are encrypted at rest and carry their body's sha256; never an ACL; there is no delete;
  - 404 means "not there"; any other failure means "cannot be reached";
  - `get_many` follows the list pages and fetches only matching objects;
  - keys come from the environment or ~/.aws/credentials and are never shown.
No network: every test uses a stand-in connection.
Run:  python -m pytest test_helm_cold_cloud_direct.py -q
"""
from __future__ import annotations

import http.client
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import helm_cold_cloud as hcc  # noqa: E402

# AWS documentation, "Signature Calculations for the Authorization Header: Transferring Payload in a Single Chunk
# (AWS Signature Version 4)" -- the example keys, date and bucket (published examples, not real keys)
AK = "AKIAIOSFODNN7EXAMPLE"
SK = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
WHEN = "20130524T000000Z"
HOST = "examplebucket.s3.amazonaws.com"
EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def _sig(auth):
    return auth.split("Signature=")[1]


# ----------------------------------------------------------------------------------------------- signing
def test_signing_matches_the_aws_get_object_example():
    headers = {"host": HOST, "range": "bytes=0-9", "x-amz-content-sha256": EMPTY, "x-amz-date": WHEN}
    auth = hcc.sigv4_authorization("GET", "/test.txt", {}, headers, EMPTY, WHEN, "us-east-1", AK, SK)
    assert "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date" in auth
    assert _sig(auth) == "f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"


def test_signing_matches_the_aws_put_object_example():
    body = b"Welcome to Amazon S3."
    sha = hcc.sha256_hex(body)
    assert sha == "44ce7dd67c959e0d3524ffac1771dfbba87d2b6b4b4e99e42034a8b803f8b072"
    headers = {"date": "Fri, 24 May 2013 00:00:00 GMT", "host": HOST, "x-amz-content-sha256": sha,
               "x-amz-date": WHEN, "x-amz-storage-class": "REDUCED_REDUNDANCY"}
    auth = hcc.sigv4_authorization("PUT", "/test$file.text", {}, headers, sha, WHEN, "us-east-1", AK, SK)
    assert _sig(auth) == "98ad721746da40c64f1a55b78f14c238d841ea1380cd77a1b5971af0ece108bd"


def test_signing_matches_the_aws_list_objects_example():
    headers = {"host": HOST, "x-amz-content-sha256": EMPTY, "x-amz-date": WHEN}
    auth = hcc.sigv4_authorization("GET", "/", {"max-keys": "2", "prefix": "J"}, headers, EMPTY, WHEN, "us-east-1",
                                   AK, SK)
    assert _sig(auth) == "34b48302e7b5fa45bde8084f4b7868a86f0a534bc59db6670ed5711ef69dc6f7"


# ----------------------------------------------------------------------------------------------- the stand-in connection
class Resp:
    def __init__(self, status, data=b""):
        self.status = status
        self._data = data

    def read(self):
        return self._data


class Conn:
    """Records requests; answers with `handler(method, url, body, headers) -> (status, data)`."""
    made = []

    def __init__(self, host, timeout=None, handler=None, drop_first=False):
        self.host = host
        self.handler = handler
        self.drop_first = drop_first
        self.requests = []
        self._next = None
        Conn.made.append(self)

    def request(self, method, url, body=None, headers=None):
        if self.drop_first:
            self.drop_first = False
            raise http.client.RemoteDisconnected("closed")
        self.requests.append((method, url, body, dict(headers or {})))
        self._next = self.handler(method, url, body, headers or {})

    def getresponse(self):
        status, data = self._next
        return Resp(status, data)

    def close(self):
        pass


def _client(handler, drop_first=False, **kw):
    Conn.made = []
    first = {"drop": drop_first}

    def factory(host, timeout=None):
        c = Conn(host, timeout, handler, drop_first=first["drop"])
        first["drop"] = False
        return c
    return hcc.S3DirectCloud(bucket="helm-cold-memory-807562639912-usw2", region="us-west-2",
                             credentials=("AKIDTESTONLY", "secret-test-only", None), conn_factory=factory, **kw)


def test_one_connection_is_kept_for_every_call():
    store = {}

    def handler(method, url, body, headers):
        if method == "PUT":
            store[url] = body
            return 200, b""
        if method == "GET":
            return (200, store[url]) if url in store else (404, b"")
        return 200, b""
    c = _client(handler)
    c.put("teach/s/a.jsonl", b"one")
    c.put("teach/s/b.jsonl", b"two")
    assert c.get("teach/s/a.jsonl") == b"one" and c.available()
    assert len(Conn.made) == 1 and len(Conn.made[0].requests) == 4
    assert Conn.made[0].host == "helm-cold-memory-807562639912-usw2.s3.us-west-2.amazonaws.com"


def test_a_dropped_connection_is_reopened_once():
    c = _client(lambda m, u, b, h: (200, b"x"), drop_first=True)
    assert c.get("teach/s/a.jsonl") == b"x"
    assert len(Conn.made) == 2


def test_uploads_are_encrypted_signed_and_never_carry_an_acl():
    c = _client(lambda m, u, b, h: (200, b""))
    c.put("teach/s/a b.jsonl", b"hello")
    method, url, body, headers = Conn.made[0].requests[0]
    low = {k.lower(): v for k, v in headers.items()}
    assert method == "PUT" and url == "/teach/s/a%20b.jsonl" and body == b"hello"
    assert low["x-amz-server-side-encryption"] == "AES256"
    assert low["x-amz-content-sha256"] == hcc.sha256_hex(b"hello")
    assert low["authorization"].startswith("AWS4-HMAC-SHA256 Credential=AKIDTESTONLY/")
    assert "/us-west-2/s3/aws4_request" in low["authorization"]
    assert not any("acl" in k for k in low)
    assert not hasattr(hcc.S3DirectCloud, "delete")


def test_missing_is_none_and_other_failures_are_unreachable():
    assert _client(lambda m, u, b, h: (404, b"")).get("k") is None
    with pytest.raises(hcc.CloudUnavailable):
        _client(lambda m, u, b, h: (403, b"denied")).get("k")
    with pytest.raises(hcc.CloudUnavailable):
        _client(lambda m, u, b, h: (500, b"")).put("k", b"x")

    def boom(m, u, b, h):
        raise OSError("no network")
    with pytest.raises(hcc.CloudUnavailable):
        _client(boom).get("k")
    assert _client(lambda m, u, b, h: (403, b"")).available() is False
    assert _client(boom).available() is False


def test_get_many_follows_the_pages_and_fetches_only_matches():
    pages = {
        None: b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><IsTruncated>true</IsTruncated>'
              b'<Contents><Key>teach/s/fold-1-0001.fold.json</Key></Contents>'
              b'<Contents><Key>teach/s/cap-1.lean.json</Key></Contents>'
              b'<NextContinuationToken>tok/1=</NextContinuationToken></ListBucketResult>',
        "tok/1=": b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><IsTruncated>false</IsTruncated>'
                  b'<Contents><Key>teach/s/sub/fold-2-0001.fold.json</Key></Contents></ListBucketResult>',
    }
    objects = {"/teach/s/fold-1-0001.fold.json": b"A", "/teach/s/sub/fold-2-0001.fold.json": b"B"}

    def handler(method, url, body, headers):
        if url.startswith("/?"):
            from urllib.parse import parse_qs, urlsplit
            q = parse_qs(urlsplit(url).query)
            assert q["list-type"] == ["2"] and q["prefix"] == ["teach/s/"]
            return 200, pages[q.get("continuation-token", [None])[0]]
        return (200, objects[url]) if url in objects else (404, b"")
    c = _client(handler)
    got = c.get_many("teach/s/", ".fold.json")
    assert got == {"teach/s/fold-1-0001.fold.json": b"A", "teach/s/sub/fold-2-0001.fold.json": b"B"}
    assert len(Conn.made) == 1                                   # all over the one connection


# ----------------------------------------------------------------------------------------------- keys
def test_keys_come_from_the_environment_first(tmp_path):
    cred = tmp_path / "credentials"
    cred.write_text("[default]\naws_access_key_id = FILEKEY\naws_secret_access_key = FILESECRET\n", encoding="utf-8")
    env = {"AWS_ACCESS_KEY_ID": "ENVKEY", "AWS_SECRET_ACCESS_KEY": "ENVSECRET", "AWS_SESSION_TOKEN": "ENVTOKEN"}
    assert hcc.load_credentials(env=env, path=str(cred)) == ("ENVKEY", "ENVSECRET", "ENVTOKEN")
    assert hcc.load_credentials(env={}, path=str(cred)) == ("FILEKEY", "FILESECRET", None)
    assert hcc.load_credentials(env={}, path=str(tmp_path / "missing")) is None


def test_a_session_token_is_sent_and_signed():
    Conn.made = []
    c = hcc.S3DirectCloud(bucket="b", region="us-west-2", credentials=("AK", "SK", "TOKEN"),
                          conn_factory=lambda host, timeout=None: Conn(host, timeout, lambda m, u, b, h: (200, b"")))
    c.get("k")
    low = {k.lower(): v for k, v in Conn.made[0].requests[0][3].items()}
    assert low["x-amz-security-token"] == "TOKEN" and "x-amz-security-token" in low["authorization"]


def test_no_keys_means_unreachable_and_keys_are_never_shown():
    c = hcc.S3DirectCloud(bucket="b", region="us-west-2", credentials=None, env={}, credentials_path="/nowhere",
                          conn_factory=lambda host, timeout=None: Conn(host, timeout, lambda m, u, b, h: (200, b"")))
    assert c.available() is False
    with pytest.raises(hcc.CloudUnavailable):
        c.get("k")
    shown = repr(_client(lambda m, u, b, h: (200, b""))) + str(_client(lambda m, u, b, h: (200, b"")))
    assert "secret-test-only" not in shown and "AKIDTESTONLY" not in shown
