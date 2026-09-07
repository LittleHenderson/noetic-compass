"""Pure structure and identity checks for the publication-packet verifier.

No git, network, tensor, or provider work occurs. Git operations are injected
as fakes, so these tests run identically everywhere and cannot be fooled by the
local repository state.
"""
from hashlib import sha256
import json
from pathlib import Path

import pytest

import tools.verify_condition_skill_v9_publication_packet as verify


GOOD_COMMIT = "a" * 40
GOOD_BASE = "c" * 40
GOOD_BLOB = "b" * 40
GOOD_PATH = ("cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"
             "research/CAS_META_2_COMPOSITION/cas_meta2/condition_skill_v9/data.py")
SECOND_PATH = ("cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"
               "research/CAS_META_2_COMPOSITION/cas_meta2/condition_skill_v9/bundle.py")


def entry(path, raw):
    return {"path": path, "bytes": len(raw),
            "sha256": sha256(raw).hexdigest(), "git_blob": GOOD_BLOB}


def packet(bound, commit=GOOD_COMMIT):
    files = [entry(path, data) for path, data in bound]
    files.sort(key=lambda item: item["path"])
    return {"schema": verify.SCHEMA, "source_commit": commit, "files": files}


def raw(packet):
    return (json.dumps(packet, indent=2, sort_keys=True) + "\n").encode("utf-8")


class FakeGit:
    def __init__(self, blobs, changed=None, ancestor=True):
        self.blobs = dict(blobs)          # path -> bytes at the source commit
        self.changed = list(changed) if changed is not None else sorted(blobs)
        self.ancestor = ancestor

    def bytes_fn(self, root, commit, path):
        assert commit == GOOD_COMMIT
        return self.blobs[path]

    def blob_fn(self, root, commit, path):
        assert commit == GOOD_COMMIT
        return GOOD_BLOB.encode("ascii")

    def changed_fn(self, root, commit, base=None):
        assert commit == GOOD_COMMIT
        return list(self.changed)

    def ancestor_fn(self, root, commit, head):
        assert commit == GOOD_COMMIT or commit == GOOD_BASE
        return self.ancestor


@pytest.fixture
def bound():
    return [(GOOD_PATH, b"first-file-bytes"), (SECOND_PATH, b"second-file-bytes")]


@pytest.fixture
def fake(bound):
    return FakeGit(dict(bound))


def verify_with(bound, fake):
    return verify.verify_packet(Path("unused"), raw(packet(bound)), "HEAD",
                                git_bytes_fn=fake.bytes_fn, git_blob_fn=fake.blob_fn,
                                git_changed_fn=fake.changed_fn, git_ancestor_fn=fake.ancestor_fn)


def test_strict_load_rejects_duplicate_keys():
    with pytest.raises(ValueError, match="PACKET_DUPLICATE_JSON_KEY"):
        verify.strict_load(b'{"schema":"x","schema":"y"}')


def test_strict_load_rejects_nonfinite_json():
    with pytest.raises(ValueError, match="PACKET_NONFINITE_JSON"):
        verify.strict_load(b'{"schema":NaN}')


@pytest.mark.parametrize("mutate,reason", [
    (lambda p: p.pop("schema"), "PACKET_SCHEMA"),
    (lambda p: p.update(schema="cas-meta2-other/1"), "PACKET_SCHEMA"),
    (lambda p: p.update(source_commit="abc"), "PACKET_SOURCE_COMMIT"),
    (lambda p: p.update(base_commit="zz"), "PACKET_BASE_COMMIT"),
    (lambda p: p.update(files=[]), "PACKET_FILES"),
    (lambda p: p["files"][0].update(path="C:\\absolute\\path"), "PACKET_ENTRY_PATH"),
    (lambda p: p["files"][0].update(path="../escape.py"), "PACKET_ENTRY_PATH"),
    (lambda p: p["files"][0].update(path="elsewhere/file.py"), "PACKET_ENTRY_PATH"),
    (lambda p: p["files"][0].update(path="docs/somewhere.md"), "PACKET_ENTRY_PATH"),
    (lambda p: p["files"][0].update(bytes=-1), "PACKET_ENTRY_BYTES"),
    (lambda p: p["files"][0].update(sha256="zz"), "PACKET_ENTRY_SHA256"),
    (lambda p: p["files"][0].update(git_blob="zz"), "PACKET_ENTRY_BLOB"),
    (lambda p: p["files"][0].update(extra=1), "PACKET_ENTRY_FIELDS"),
    (lambda p: p["files"].append(p["files"][0]), "PACKET_DUPLICATE_PATH"),
])
def test_validate_structure_rejects_mutations(bound, mutate, reason):
    candidate = packet(bound)
    mutate(candidate)
    with pytest.raises(ValueError, match=reason):
        verify.validate_structure(candidate)


def test_validate_structure_rejects_unsorted_paths(bound):
    candidate = packet(bound)
    candidate["files"] = list(reversed(candidate["files"]))
    with pytest.raises(ValueError, match="PACKET_PATHS_NOT_SORTED"):
        verify.validate_structure(candidate)


def test_monorepo_changelog_is_explicitly_allowed(bound):
    allowed = packet(bound)
    allowed["files"].append(entry("CHANGELOG.md", b"campaign-log-bytes"))
    allowed["files"].sort(key=lambda item: item["path"])
    assert verify.validate_structure(allowed)["source_commit"] == GOOD_COMMIT


def test_verify_exact_packet_passes(bound, fake):
    report = verify_with(bound, fake)
    assert report["status"] == "PACKET_EXACT"
    assert report["source_commit"] == GOOD_COMMIT
    assert report["packet_sha256"] == sha256(raw(packet(bound))).hexdigest()
    assert sorted(report["files"]) == sorted([GOOD_PATH, SECOND_PATH])


def test_verify_rejects_tampered_size_or_hash(bound, fake):
    def verify_raw(payload):
        verify.verify_packet(Path("unused"), payload, "HEAD",
                             git_bytes_fn=fake.bytes_fn, git_blob_fn=fake.blob_fn,
                             git_changed_fn=fake.changed_fn, git_ancestor_fn=fake.ancestor_fn)

    tampered = packet(bound)
    tampered["files"][0]["bytes"] += 1
    with pytest.raises(ValueError, match="PACKET_BYTES_MISMATCH"):
        verify_raw(raw(tampered))
    tampered = packet(bound)
    tampered["files"][0]["sha256"] = "c" * 64
    with pytest.raises(ValueError, match="PACKET_SHA256_MISMATCH"):
        verify_raw(raw(tampered))
    tampered = packet(bound)
    tampered["files"][0]["git_blob"] = "d" * 40
    with pytest.raises(ValueError, match="PACKET_BLOB_MISMATCH"):
        verify_raw(raw(tampered))


def test_verify_rejects_coverage_mismatch(bound):
    fake = FakeGit(dict(bound), changed=[GOOD_PATH])
    with pytest.raises(ValueError, match="PACKET_COVERAGE_MISMATCH"):
        verify_with(bound, fake)


def test_verify_rejects_non_ancestor_source(bound):
    fake = FakeGit(dict(bound), ancestor=False)
    with pytest.raises(ValueError, match="SOURCE_COMMIT_NOT_ANCESTOR_OF_HEAD"):
        verify_with(bound, fake)


def test_build_packet_emits_lf_only_sorted_exact(bound, fake):
    built, packet_raw = verify.build_packet(Path("unused"), GOOD_COMMIT,
                                            git_bytes_fn=fake.bytes_fn,
                                            git_blob_fn=fake.blob_fn,
                                            git_changed_fn=fake.changed_fn)
    assert b"\r" not in packet_raw
    assert built == packet(bound)
    parsed = verify.strict_load(packet_raw)
    assert [item["path"] for item in parsed["files"]] == sorted([GOOD_PATH, SECOND_PATH])
    for item in parsed["files"]:
        assert item["sha256"] == sha256(dict(bound)[item["path"]]).hexdigest()


def test_empty_file_bytes_are_bound_exactly(bound):
    fake = FakeGit(dict(bound))
    fake.blobs[SECOND_PATH] = b""
    built, packet_raw = verify.build_packet(Path("unused"), GOOD_COMMIT,
                                            git_bytes_fn=fake.bytes_fn,
                                            git_blob_fn=fake.blob_fn,
                                            git_changed_fn=fake.changed_fn)
    empty = [item for item in built["files"] if item["path"] == SECOND_PATH][0]
    assert empty["bytes"] == 0
    assert empty["sha256"] == ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    report = verify.verify_packet(Path("unused"), packet_raw, "HEAD",
                                  git_bytes_fn=fake.bytes_fn, git_blob_fn=fake.blob_fn,
                                  git_changed_fn=fake.changed_fn, git_ancestor_fn=fake.ancestor_fn)
    assert report["status"] == "PACKET_EXACT"


def test_build_and_verify_exclude_self_path(bound):
    self_path = ("cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"
                 "research/CAS_META_2_COMPOSITION/records/condition_skill_v9_001/publication_packet.json")
    fake = FakeGit(dict(bound), changed=[GOOD_PATH, SECOND_PATH, self_path])
    fake.blobs[self_path] = b"stale-self-bytes"
    built, packet_raw = verify.build_packet(Path("unused"), GOOD_COMMIT, None,
                                            self_path=self_path,
                                            git_bytes_fn=fake.bytes_fn,
                                            git_blob_fn=fake.blob_fn,
                                            git_changed_fn=fake.changed_fn)
    assert [item["path"] for item in built["files"]] == sorted([GOOD_PATH, SECOND_PATH])
    report = verify.verify_packet(Path("unused"), packet_raw, "HEAD", self_path=self_path,
                                  git_bytes_fn=fake.bytes_fn, git_blob_fn=fake.blob_fn,
                                  git_changed_fn=fake.changed_fn, git_ancestor_fn=fake.ancestor_fn)
    assert report["status"] == "PACKET_EXACT"


def test_build_and_verify_with_base_commit_range(bound):
    fake = FakeGit(dict(bound), changed=[GOOD_PATH, SECOND_PATH, "CHANGELOG.md"])
    fake.blobs["CHANGELOG.md"] = b"campaign-log-bytes"
    built, packet_raw = verify.build_packet(Path("unused"), GOOD_COMMIT, GOOD_BASE,
                                            git_bytes_fn=fake.bytes_fn,
                                            git_blob_fn=fake.blob_fn,
                                            git_changed_fn=fake.changed_fn)
    assert built["base_commit"] == GOOD_BASE
    assert [item["path"] for item in built["files"]] == sorted(["CHANGELOG.md", GOOD_PATH, SECOND_PATH])
    report = verify.verify_packet(Path("unused"), packet_raw, "HEAD",
                                  git_bytes_fn=fake.bytes_fn, git_blob_fn=fake.blob_fn,
                                  git_changed_fn=fake.changed_fn, git_ancestor_fn=fake.ancestor_fn)
    assert report["status"] == "PACKET_EXACT"
    assert report["source_commit"] == GOOD_COMMIT


def test_verify_rejects_range_packet_without_base_when_changed_fake_differs(bound):
    # A range packet lists the union; verifying it with a fake that only knows
    # the single-commit set must raise a coverage mismatch.
    fake = FakeGit(dict(bound), changed=[GOOD_PATH, SECOND_PATH, "CHANGELOG.md"])
    fake.blobs["CHANGELOG.md"] = b"campaign-log-bytes"
    built, packet_raw = verify.build_packet(Path("unused"), GOOD_COMMIT, GOOD_BASE,
                                            git_bytes_fn=fake.bytes_fn,
                                            git_blob_fn=fake.blob_fn,
                                            git_changed_fn=fake.changed_fn)
    single = FakeGit(dict(bound), changed=[GOOD_PATH, SECOND_PATH])
    with pytest.raises(ValueError, match="PACKET_COVERAGE_MISMATCH"):
        verify.verify_packet(Path("unused"), packet_raw, "HEAD",
                             git_bytes_fn=single.bytes_fn, git_blob_fn=single.blob_fn,
                             git_changed_fn=single.changed_fn, git_ancestor_fn=single.ancestor_fn)
