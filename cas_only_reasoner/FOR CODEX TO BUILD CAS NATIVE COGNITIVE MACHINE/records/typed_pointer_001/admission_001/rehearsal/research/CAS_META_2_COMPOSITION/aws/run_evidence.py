"""RUN_EVIDENCE_PRESERVATION_001: the shared evidence contract and its checks.

One module for the whole evidence boundary, so the four candidate jobs cannot each
invent their own: the pre-run contract, the dedicated evidence directory, the
atomic writer, the journal, the byte-integrity verifier, the experimental
completeness verifier, the receiver-issued collection receipt, and the
deletion decision that defaults to DENY.

Why it exists. Attempt 004 delivered four verified checkpoints and lost its own
readout: ``measurements.json`` was uploaded but never declared as an artefact, so
verified collection kept the declared files only, and routine cleanup then deleted
the bucket. Two earlier attempts lost a completed result to an exception handler
that overwrote it before destructive cleanup. The lesson is stated in the
directive and encoded here:

    Stop compute on schedule; preserve evidence independently. A valid hash
    proves the identity of supplied bytes, not that every required measurement
    was supplied.

The three sets the directive distinguishes are kept apart in the data this module
produces, because conflating them is what allowed the loss:

* REQUIRED - logical records and files the registered measurement needs. Pinned in
  the contract BEFORE the worker starts, and held by the collector independently of
  anything the worker uploads.
* PRODUCED - files actually present in the evidence directory. Reported as reality,
  including missing and partial outputs; cannot shrink REQUIRED.
* COLLECTED - bytes actually obtained and verified by the receiver.

A worker-supplied ``verified: true`` is not a collection receipt. Only
``collection_receipt`` below issues one, and it is bound to the job, the contract
digest and the inventory digest, so it cannot be reused for another job or an
altered inventory.

No model, no torch, no AWS SDK, no network in this module.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from pathlib import Path

# --------------------------------------------------------------------------
# schemas and the status vocabulary
# --------------------------------------------------------------------------

CONTRACT_SCHEMA = "cas.run-evidence-contract/1"
INVENTORY_SCHEMA = "cas.run-evidence-inventory/1"
RECEIPT_SCHEMA = "cas.run-evidence-collection-receipt/1"
DECISION_SCHEMA = "cas.run-evidence-deletion-decision/1"

#: Execution, byte collection, measurement completeness, backup verification and
#: compute cleanup are separate states with separate words. A scientific negative
#: can be a fully delivered experiment; a good aggregate with lost rows is not.
EXECUTION_STATES = ("FINISHED", "FAILED", "UNKNOWN")
COLLECTION_STATES = ("COMPLETE_VERIFIED", "INCOMPLETE", "NOT_ATTEMPTED")
COMPLETENESS_STATES = ("COMPLETE", "INCOMPLETE", "NOT_EVALUATED")
BACKUP_STATES = ("VERIFIED", "NOT_VERIFIED", "NOT_ATTEMPTED")
COMPUTE_STATES = ("COMPLETE", "INCOMPLETE", "NOT_ATTEMPTED")
ARCHIVE_STATES = ("RETAINED_UNDER_POLICY", "RETAINED_PENDING_COLLECTION",
                  "DELETION_DENIED", "ABSENT")

#: The one deletion decision this module will ever issue without an approved
#: policy. It is spelled out rather than implied so a caller cannot mistake a
#: missing decision for permission.
DENY = "DENY"
ALLOW = "ALLOW"

SAFE_NAME = re.compile(r"[A-Za-z0-9._-]+\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")

#: Reasons that never authorise deletion on their own. Named because each one has
#: been offered as if it were enough.
NON_REASONS = (
    "the worker reported FINISHED",
    "exit code zero",
    "the expected number of checkpoints exists",
    "a retention timer expired",
    "every file the worker declared was downloaded",
    "the bucket name is not in the resource plan anymore",
)


def require(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def digest_file(path):
    accumulator = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            accumulator.update(block)
    return accumulator.hexdigest()


# --------------------------------------------------------------------------
# 1. the contract, frozen before execution
# --------------------------------------------------------------------------

def requirement(key, purpose, *, kind="file", condition=None, layer=None,
                records=None, records_key="item_id", phases=None, faces=None,
                per_face=None, required=True):
    """One REQUIRED entry.

    ``kind`` is ``file`` for bytes that must arrive intact, or ``records`` for a
    JSON-lines file whose record identities are checked: ``records`` lists the exact
    keys expected (or ``None`` when the file is only required to exist and be
    readable). ``phases`` declares the before/after coverage a records file must
    carry, and ``faces``/``per_face`` declare the six-face and 16-per-face shape the
    directive requires for the primary layers.
    """
    require(type(key) is str and key, "EVIDENCE_CONTRACT_KEY")
    require(".." not in Path(key).parts and not key.startswith("/"),
            "EVIDENCE_CONTRACT_KEY_SCOPE")
    require(kind in ("file", "records", "json"), "EVIDENCE_CONTRACT_KIND:" + str(kind))
    entry = {"key": key, "purpose": purpose, "kind": kind, "required": bool(required)}
    for name, value in (("condition", condition), ("layer", layer),
                        ("records_key", records_key if kind == "records" else None),
                        ("phases", sorted(phases) if phases else None),
                        ("faces", sorted(faces) if faces else None),
                        ("per_face", per_face)):
        if value is not None:
            entry[name] = value
    if kind == "records":
        entry["records"] = sorted(records) if records is not None else None
    return entry


def contract(profile, requirements, *, job=None, notes=None):
    """The pre-run evidence contract for one experiment profile."""
    require(type(profile) is str and profile, "EVIDENCE_CONTRACT_PROFILE")
    entries = list(requirements)
    require(entries, "EVIDENCE_CONTRACT_EMPTY")
    keys = [entry["key"] for entry in entries]
    require(len(set(keys)) == len(keys), "EVIDENCE_CONTRACT_DUPLICATE_KEY")
    document = {"schema": CONTRACT_SCHEMA, "profile": profile,
                "required": sorted(entries, key=lambda entry: entry["key"]),
                "required_count": len(entries),
                "cannot_shrink_after_a_failure": True,
                "worker_may_not_amend_required": True,
                "scope": ("the registered measurement's records and files; a valid "
                          "hash proves the identity of supplied bytes, not that "
                          "every required measurement was supplied")}
    if job is not None:
        document["job"] = job
    if notes:
        document["notes"] = list(notes)
    return document


def contract_digest(document):
    return digest(canonical(document))


def contract_keys(document):
    return [entry["key"] for entry in document["required"]]


def required_records(document):
    """The declared record identities per records-file key."""
    declared = {}
    for entry in document["required"]:
        if entry["kind"] == "records":
            declared[entry["key"]] = {"records": entry.get("records"),
                                      "records_key": entry.get("records_key"),
                                      "phases": entry.get("phases"),
                                      "faces": entry.get("faces"),
                                      "per_face": entry.get("per_face"),
                                      "condition": entry.get("condition"),
                                      "layer": entry.get("layer")}
    return declared


# ---- the registered profiles ------------------------------------------------

def face_condition_requirements(conditions, panel_facts, *, layers=None):
    """REQUIRED evidence for the four-condition face experiment, as frozen.

    ``panel_facts`` carries the frozen panel's exact item identities per layer and
    per face, computed locally before any launch, so the collector checks the real
    question-ID sets rather than a count.
    """
    layers = layers or {"role_application": 96, "role_recognition": 96,
                        "targeted_check": 24}
    entries = [
        requirement("results/result.json", "transport marker and delivery envelope",
                    kind="json"),
        requirement("results/result.json.sha256", "sidecar binding the envelope bytes"),
        requirement("results/artifacts/manifest.json",
                    "the worker's produced-file manifest, reported as reality"),
        requirement("results/artifacts/measurements.json",
                    "the registered measurement: per-face, per-question, baselines "
                    "and milestone report"),
        requirement("results/evidence/panel.json",
                    "the public evaluation panel as delivered",
                    kind="json"),
        requirement("results/evidence/frozen_inputs.json",
                    "encoder identity, tokenizer identity and the frozen "
                    "configuration the observations depend on", kind="json"),
        requirement("results/evidence/containment.json",
                    "the parameters that could change and the proof of which did",
                    kind="json"),
        requirement("results/evidence/panel_analysis.json",
                    "per-face and per-layer summaries, declared baselines, paired "
                    "analysis and the milestone report", kind="json"),
    ]
    for condition in conditions:
        entries.extend([
            requirement("results/artifacts/checkpoint_%s.pt" % condition,
                        "final checkpoint for the condition", condition=condition),
            requirement("results/evidence/rows_%s.jsonl" % condition,
                        "per-question rows: offered choices and slot order, selected "
                        "answer, three scores, loss, phase and assistance state",
                        kind="records", condition=condition,
                        records=panel_facts["item_ids"],
                        phases=("before", "after"), faces=panel_facts["faces"],
                        per_face=panel_facts.get("per_face")),
            requirement("results/evidence/updates_%s.jsonl" % condition,
                        "optimizer-update records: actual committed exposure",
                        kind="records", condition=condition),
        ])
    entries.append(
        requirement("results/artifacts/checkpoint_initial.pt",
                    "the actual original initial state used for the before "
                    "comparison; a seed is not a substitute for stored state"))
    entries.append(
        requirement("results/evidence/encoder_identity.json",
                    "the frozen encoder/projection identity"))
    entries.append(
        requirement("results/evidence/worker.log",
                    "worker log covering the run"))
    return entries


def readout_requirements(conditions, panel_facts):
    """REQUIRED evidence for the zero-update readout profile."""
    entries = [
        requirement("results/result.json", "transport marker and readout envelope",
                    kind="json"),
        requirement("results/result.json.sha256", "sidecar binding the envelope bytes"),
        requirement("results/artifacts/manifest.json",
                    "the worker's produced-file manifest"),
        requirement("results/artifacts/measurements.json",
                    "the recovered measurement summary"),
        requirement("results/artifacts/readout.json",
                    "the full per-question readout, the recovery's payload"),
        requirement("results/evidence/panel.json", "the public panel as delivered",
                    kind="json"),
        requirement("results/evidence/panel_analysis.json",
                    "per-face summaries, baselines, paired analysis and milestone "
                    "report", kind="json"),
    ]
    for condition in conditions:
        entries.append(
            requirement("results/evidence/rows_%s.jsonl" % condition,
                        "recovered per-question rows, before and after phases",
                        kind="records", condition=condition,
                        records=panel_facts["item_ids"],
                        phases=("before", "after"), faces=panel_facts["faces"],
                        per_face=panel_facts.get("per_face")))
    return entries


# --------------------------------------------------------------------------
# 2. the dedicated evidence directory, and writing into it
# --------------------------------------------------------------------------

def evidence_directory(path):
    """A directory that is not a link, not inside one, and has no parent step."""
    path = Path(path).absolute()
    require(".." not in path.parts, "EVIDENCE_PATH_PARENT_COMPONENT")
    for ancestor in (path, *path.parents):
        require(not ancestor.is_symlink()
                and not getattr(ancestor, "is_junction", lambda: False)(),
                "EVIDENCE_LINKED_PATH")
    return path


def prepare_directory(path):
    path = evidence_directory(path)
    require(not path.exists() and path.parent.is_dir(),
            "FRESH_EVIDENCE_DIRECTORY_REQUIRED")
    path.mkdir()
    return path


_TEMP_COUNTER = {"value": 0}


def write_atomic(path, raw, *, unique=False):
    """Publish bytes without ever overwriting an immutable evidence object.

    Write a temporary file in the destination filesystem, flush and fsync it,
    verify the bytes read back, then publish under the final name with a
    create-only link. A crash leaves the temporary file, never a partial final
    object. This protects against partial-file publication; it is not protection
    against loss of the whole disk, which is what the retained archive is for.
    """
    require(type(raw) is bytes and len(raw) <= 256 * 1024**2, "EVIDENCE_BYTES_BOUND")
    final = Path(path)
    # Only the non-unique case refuses an existing object: with unique=True the
    # caller is explicitly asking for a new name beside it.
    require(unique or not final.exists(),
            "EVIDENCE_OBJECT_ALREADY_EXISTS:" + str(final))
    if unique:
        _TEMP_COUNTER["value"] += 1
        final = final.with_name("%s.%d.%d" % (final.name, os.getpid(),
                                              _TEMP_COUNTER["value"]))
    temporary = final.with_name("." + final.name + ".partial")
    require(not temporary.exists(), "EVIDENCE_TEMP_EXISTS:" + str(temporary))
    final.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        require(temporary.read_bytes() == raw,
                "EVIDENCE_READBACK_MISMATCH:" + str(final))
        require(not final.exists(), "EVIDENCE_OBJECT_ALREADY_EXISTS:" + str(final))
        try:
            os.link(temporary, final)          # create-only, atomic
        except (OSError, NotImplementedError):
            with final.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        _fsync_directory(final.parent)
    finally:
        try:
            temporary.unlink()
        except OSError:
            pass
    require(final.stat().st_nlink >= 1 and final.read_bytes() == raw,
            "EVIDENCE_PUBLISH_MISMATCH:" + str(final))
    return {"path": str(final), "sha256": digest(raw), "bytes": len(raw)}


def _fsync_directory(directory):
    """Best effort: POSIX needs the directory entry flushed, Windows does not."""
    try:
        handle = os.open(str(directory), os.O_RDONLY)
    except (OSError, AttributeError):
        return
    try:
        os.fsync(handle)
    except OSError:
        pass
    finally:
        os.close(handle)


def write_document(path, document, *, unique=False):
    return write_atomic(path, canonical(document), unique=unique)


# --------------------------------------------------------------------------
# 3. the produced inventory: reality, including what is missing
# --------------------------------------------------------------------------

def inventory(directory, document=None, *, extra_purposes=None):
    """Every regular file under the evidence directory, regardless of extension.

    Extension selection is not the definition of scientific importance, so nothing
    is filtered by suffix. Files the contract does not name are reported as
    unlisted and are retained and surfaced rather than discarded.
    """
    directory = Path(directory)
    purposes = {entry["key"]: entry["purpose"]
                for entry in (document or {}).get("required", [])}
    if extra_purposes:
        purposes.update(extra_purposes)
    base = directory.relative_to(directory)                # "." for reporting
    files, unlisted = [], []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(directory).as_posix()
        entry = {"relative_path": relative, "bytes": path.stat().st_size,
                 "sha256": digest_file(path),
                 "purpose": purposes.get(relative, "unlisted")}
        files.append(entry)
        if relative not in purposes:
            unlisted.append(relative)
    present = {entry["relative_path"] for entry in files}
    required = contract_keys(document) if document else []
    missing = [key for key in required if key not in present]
    return {"schema": INVENTORY_SCHEMA, "directory": str(directory),
            "file_count": len(files), "files": files,
            "unlisted": sorted(unlisted),
            "unlisted_retained": True,
            "required_count": len(required), "missing_required": missing,
            "complete": not missing,
            "note": ("the produced-file manifest reports reality, including missing "
                     "and partial outputs, and cannot shrink REQUIRED")}


def produced_manifest(directory, document, *, job=None, condition=None, phase=None,
                      chunk=None, errors=None):
    """The worker's produced-file manifest, with the contract still in force."""
    report = inventory(directory, document)
    report.update({"job": job, "condition": condition, "phase": phase,
                   "chunk": chunk, "errors": list(errors or ()),
                   "required_keys_still_required": contract_keys(document),
                   "cannot_shrink_required": True})
    return report


# --------------------------------------------------------------------------
# 4. the journal: observations persisted as they are produced
# --------------------------------------------------------------------------

class Journal:
    """Append observations to closed, immutable JSON-lines chunks.

    The rows go to disk as they are produced rather than living only inside a
    Python object until the end of the run. ``record_prediction`` writes the
    prediction *before* any training correction is applied, and the correction's
    own identity is recorded separately by ``record_update``: a crash between the
    two leaves an explicitly incomplete event, and nothing here infers that an
    update happened because a prediction row exists.
    """

    def __init__(self, directory, *, prefix, contract_document=None, now=None):
        self.directory = evidence_directory(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.prefix = prefix
        self.document = contract_document
        self.sequence = 0
        self.open_rows = []
        self.chunks = []
        self.updates_path = self.directory / ("updates_%s.jsonl" % prefix)
        self.updates_seen = []
        self.log_path = self.directory / "worker.log"
        self._now = now

    # -- durable log ---------------------------------------------------------
    def log(self, message):
        line = canonical({"at": self._timestamp(), "message": message})
        with self.log_path.open("ab") as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
        return {"path": str(self.log_path), "bytes": self.log_path.stat().st_size}

    def _timestamp(self):
        if self._now is not None:
            return float(self._now())
        import time
        return round(time.time(), 3)

    # -- rows ----------------------------------------------------------------
    def record_prediction(self, row):
        """Append one observation. No update is implied by its presence."""
        require(type(row) is dict and row.get("item_id"), "JOURNAL_ROW_ITEM_ID")
        entry = dict(row)
        entry.setdefault("update_committed", None)
        entry.setdefault("update_index", None)
        self.open_rows.append(entry)
        return entry

    def record_update(self, update):
        """Record a committed update and the exposure it actually consumed."""
        require(type(update) is dict and "update_index" in update,
                "JOURNAL_UPDATE_INDEX")
        self.updates_seen.append(dict(update))
        with self.updates_path.open("ab") as stream:
            stream.write(canonical(update))
            stream.flush()
            os.fsync(stream.fileno())
        for row in self.open_rows:
            if row.get("batch_index") is not None \
                    and row["batch_index"] == update.get("batch_index"):
                row["update_committed"] = True
                row["update_index"] = update["update_index"]
        return update

    def pending_updates(self):
        """Rows whose update is not confirmed: explicitly incomplete events."""
        return [row["item_id"] for row in self.open_rows
                if row.get("update_batch_expected") and row.get("update_committed") is not True]

    def close_chunk(self, boundary, *, condition=None, phase=None):
        """Close an immutable chunk at a declared boundary."""
        rows = self.open_rows
        self.sequence += 1
        name = "%s_%04d_%s.jsonl" % (self.prefix, self.sequence, _slug(boundary))
        path = self.directory / (("rows_%s.jsonl" % self.prefix)
                                 if boundary == "condition_complete"
                                 else name)
        payload = b"".join(canonical(row) for row in rows)
        receipt = write_atomic(path, payload, unique=(boundary != "condition_complete"
                                                     and path.exists()))
        receipt.update({"boundary": boundary, "condition": condition,
                        "phase": phase, "records": len(rows),
                        "chunk": self.sequence})
        self.chunks.append(receipt)
        self.open_rows = []
        return receipt


def _slug(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value))[:64] or "chunk"


def read_records(path):
    """Parse a JSON-lines evidence file into rows."""
    rows = []
    for number, line in enumerate(Path(path).read_bytes().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except ValueError as error:
            raise ValueError("EVIDENCE_RECORD_UNPARSABLE:%s:%d:%s"
                             % (path, number, error)) from None
    return rows


# --------------------------------------------------------------------------
# 5. verification has two separate jobs
# --------------------------------------------------------------------------

def verify_byte_integrity(collected_files, document, *, versions=None):
    """Byte integrity: every required object's real bytes, recomputed.

    Each entry keeps relative key, size, SHA-256 of the complete original bytes,
    purpose and the object version where the transport supplies one. An S3 ETag or
    a multipart composite checksum is never treated as equivalent to this full-file
    SHA-256: this function only ever compares a recomputed SHA-256.
    """
    versions = versions or {}
    by_key = {entry["relative_path"] if "relative_path" in entry else entry["key"]:
              entry for entry in collected_files}
    verified, missing, mismatched, unavailable = [], [], [], []
    for entry in document["required"]:
        key = entry["key"]
        found = by_key.get(key)
        if found is None:
            missing.append(key)
            continue
        raw = found.get("bytes_raw")
        recorded = found.get("sha256")
        size = found.get("bytes")
        if raw is None:
            unavailable.append({"key": key, "reason": "BYTES_NOT_SUPPLIED_TO_VERIFIER"})
            continue
        actual_size, actual_sha = len(raw), digest(raw)
        record = {"key": key, "purpose": entry["purpose"], "bytes": actual_size,
                  "sha256": actual_sha, "condition": entry.get("condition"),
                  "layer": entry.get("layer"),
                  "object_version": versions.get(key)}
        if recorded is not None and recorded != actual_sha:
            mismatched.append(dict(record, recorded_sha256=recorded,
                                   reason="SHA256_MISMATCH"))
        elif size is not None and size != actual_size:
            mismatched.append(dict(record, recorded_bytes=size,
                                   reason="SIZE_MISMATCH"))
        elif found.get("etag") and not found.get("sha256"):
            mismatched.append(dict(record, reason="ETAG_IS_NOT_A_FULL_FILE_SHA256"))
        else:
            verified.append(record)
    state = "COMPLETE_VERIFIED" if not (missing or mismatched or unavailable) \
        else "INCOMPLETE"
    return {"state": state, "verified": verified, "missing": sorted(missing),
            "mismatched": mismatched, "unavailable": unavailable,
            "verified_count": len(verified),
            "required_count": len(document["required"]),
            "method": ("size and SHA-256 recomputed from the received bytes; an ETag "
                       "or multipart composite checksum is never accepted as "
                       "equivalent"),
            "note": ("a valid hash proves the identity of supplied bytes, not that "
                     "every required measurement was supplied")}


def _phase_of(row):
    return row.get("phase") or row.get("assistance") or None


def verify_completeness(collected_records, document, *, summaries=None,
                        missing_measurement=()):
    """Experimental completeness: parse the records and check the science.

    Checks exact question-ID sets per records file, no omitted conditions, no
    duplicate rows substituting for missing rows, declared before/after phase
    coverage, all six faces where required, per-face item counts, and score-field
    presence. A missing score is recorded as unavailable with a reason and refuses
    a completed measurement; it is never invented as zero. A measurement *object*
    that never arrived also refuses completeness: an aggregate with a lost payload
    is not a complete measurement.
    """
    declared = required_records(document)
    conditions_seen, failures, per_file = set(), [], {}
    for key in sorted(missing_measurement):
        failures.append({"key": key, "code": "MEASUREMENT_OBJECT_MISSING",
                         "note": ("the measurement object did not arrive, so the "
                                  "registered measurement is not complete even "
                                  "though its rows may be")})
    for key, spec in sorted(declared.items()):
        rows = collected_records.get(key)
        if rows is None:
            failures.append({"key": key, "code": "RECORDS_NOT_COLLECTED"})
            continue
        expected = spec["records"] or []
        item_field = spec.get("records_key") or "item_id"
        phases_declared = list(spec.get("phases") or [])
        # Per-question rules apply only to files the contract declares as
        # per-question rows. An update log or a plain record file is checked for
        # arrival and parseability, not for scores it was never meant to carry.
        per_question = spec.get("records") is not None
        if not per_question:
            conditions_seen.add(spec["condition"]) if spec.get("condition") else None
            per_file[key] = {"rows": len(rows), "kind": "records",
                             "expected_per_phase": None}
            continue
        # A question measured before and after is the same question twice, not a
        # duplicate: identity is (item, phase).
        identities = [(str(row.get(item_field)), _phase_of(row)) for row in rows]
        duplicate_pairs = sorted({pair for pair in identities
                                  if identities.count(pair) > 1})
        duplicates = ["%s@%s" % pair for pair in duplicate_pairs]
        by_phase = {}
        for row in rows:
            by_phase.setdefault(_phase_of(row), set()).add(str(row.get(item_field)))
        phases = sorted(phase for phase in by_phase if phase)
        if phases_declared:
            missing = [value for phase in phases_declared
                       for value in expected if value not in by_phase.get(phase, set())]
            missing_phases = [phase for phase in phases_declared
                              if phase not in by_phase]
        else:
            seen = {value for values in by_phase.values() for value in values}
            missing = [value for value in expected if value not in seen]
            missing_phases = []
        seen_any = {value for values in by_phase.values() for value in values}
        extra = sorted(seen_any - set(expected)) if expected else []
        faces_present = sorted({str(row.get("face")) for row in rows
                                if row.get("face") is not None})
        missing_faces = [str(face) for face in (spec.get("faces") or [])
                         if str(face) not in faces_present]
        per_face = spec.get("per_face")
        face_shape = {}
        if per_face:
            for row in rows:
                if row.get("face") is None:
                    continue
                bucket_key = "%s|%s" % (_phase_of(row), int(row["face"]))
                face_shape[bucket_key] = face_shape.get(bucket_key, 0) + 1
            for phase in (phases_declared or [None]):
                for face, wanted in sorted(per_face.items()):
                    actual = face_shape.get("%s|%s" % (phase, int(face)), 0)
                    if actual != wanted:
                        failures.append({"key": key, "code": "PER_FACE_ITEM_COUNT",
                                         "phase": phase, "face": str(face),
                                         "expected": wanted, "actual": actual})
        no_scores = [row.get(item_field) for row in rows
                     if not _score_fields_ok(row)]
        if no_scores:
            failures.append({"key": key, "code": "SCORE_FIELDS_MISSING",
                             "items": sorted(str(value) for value in no_scores)[:20],
                             "count": len(no_scores),
                             "note": ("a missing score must be recorded as "
                                      "unavailable with a reason, never as zero")})
        if spec.get("condition"):
            conditions_seen.add(spec["condition"])
        if duplicates:
            failures.append({"key": key, "code": "DUPLICATE_ROWS_SUBSTITUTING",
                             "items": duplicates[:20], "count": len(duplicates)})
        if missing:
            failures.append({"key": key, "code": "EXACT_ITEM_IDS_MISSING",
                             "items": missing[:20], "count": len(missing)})
        if extra:
            failures.append({"key": key, "code": "UNDECLARED_ITEM_IDS",
                             "items": extra[:20], "count": len(extra)})
        if missing_phases:
            failures.append({"key": key, "code": "PHASE_COVERAGE_MISSING",
                             "phases": missing_phases})
        if missing_faces:
            failures.append({"key": key, "code": "FACE_COVERAGE_MISSING",
                             "faces": missing_faces})
        per_file[key] = {"rows": len(rows), "expected_per_phase": len(expected),
                         "duplicates": len(duplicates), "missing": len(missing),
                         "phases": phases, "faces": faces_present,
                         "face_shape": face_shape}
    declared_conditions = {entry.get("condition") for entry in document["required"]
                           if entry.get("condition")}
    omitted = sorted(name for name in declared_conditions
                     if name not in conditions_seen)
    if omitted:
        failures.append({"code": "CONDITIONS_OMITTED", "conditions": omitted})
    summary_checks = _recompute_summaries(collected_records, document,
                                          summaries or {})
    failures.extend(summary_checks["failures"])
    return {"state": "COMPLETE" if not failures else "INCOMPLETE",
            "failures": failures, "per_file": per_file,
            "conditions": sorted(conditions_seen),
            "conditions_omitted": omitted,
            "summary_recomputation": summary_checks,
            "note": ("a summary and manifest can agree while both omit a required "
                     "file; the independent pre-run contract is what detects it")}


def _score_fields_ok(row):
    """Scores and loss present, or explicitly unavailable with a reason."""
    for key in ("scores_unavailable", "unavailable"):
        marker = row.get(key)
        if isinstance(marker, dict) and marker.get("reason"):
            return True
    if "scores" in row or "loss" in row:
        scores = row.get("scores")
        if isinstance(scores, (list, tuple)) and len(scores) >= 2:
            return True
        return False
    return False


def _recompute_summaries(collected_records, document, summaries):
    """Derive counts from raw rows and compare them with the stored summaries.

    Deterministic derivation from retained raw rows, so a stored summary is
    checkable rather than trusted.
    """
    derived, failures = {}, []
    for key, rows in sorted(collected_records.items()):
        spec = required_records(document).get(key)
        if not spec or (not spec.get("layer") and not spec.get("condition")):
            continue
        # A stored summary describes the final state, so the derived counts come
        # from the latest declared phase rather than from both phases at once.
        phases = list(spec.get("phases") or [])
        wanted_phase = phases[-1] if phases else None
        chosen = [row for row in rows
                  if wanted_phase is None or _phase_of(row) == wanted_phase]
        per_layer = {}
        for row in chosen:
            layer = row.get("layer") or spec.get("layer") or "unknown"
            bucket = per_layer.setdefault(layer, {"rows": 0, "correct": 0})
            bucket["rows"] += 1
            bucket["correct"] += 1 if row.get("is_correct") else 0
        derived[key] = {"phase": wanted_phase, "layers": per_layer}
    for layer, stored in sorted(summaries.items()):
        if not isinstance(stored, dict):
            continue
        stored_correct = stored.get("correct")
        stored_questions = stored.get("questions") or stored.get("total")
        if stored_correct is None or stored_questions is None:
            continue
        matching = [(key, value["layers"][layer]) for key, value in derived.items()
                    if layer in value["layers"]]
        if not matching:
            continue
        if len(matching) != 1:
            # A stored figure that pools conditions cannot be checked against
            # per-condition rows without guessing which pooling was meant.
            failures.append({"code": "SUMMARY_NOT_COMPARABLE", "layer": layer,
                             "records_files": [entry[0] for entry in matching],
                             "note": ("the stored summary is not declared per "
                                      "condition, so it is reported rather than "
                                      "compared")})
            continue
        total_correct = matching[0][1]["correct"]
        total_rows = matching[0][1]["rows"]
        if total_correct != stored_correct or total_rows != stored_questions:
            failures.append({"code": "SUMMARY_MISMATCH", "layer": layer,
                             "derived": {"correct": total_correct,
                                         "questions": total_rows},
                             "stored": {"correct": stored_correct,
                                        "questions": stored_questions},
                             "from": matching[0][0]})
    return {"derived": derived, "compared": sorted(summaries), "failures": failures,
            "method": "recomputed from the collected raw rows"}


# --------------------------------------------------------------------------
# 6. the receiver's collection receipt
# --------------------------------------------------------------------------

def collection_receipt(*, job, profile, document, collected_inventory,
                       byte_verdict, completeness_verdict, destination,
                       versions=None, failures=None, backup=None, compute=None):
    """Issue the receipt only the receiver can issue.

    It binds the job, the experiment profile, the contract digest, the actual
    inventory digest, the immutable object versions, the exact local destination,
    the coverage checks and the failures. A receipt that does not bind all of these
    cannot be reused for another job or an altered inventory, which is the point.
    """
    require(type(job) is str and job, "EVIDENCE_RECEIPT_JOB")
    require(byte_verdict and completeness_verdict, "EVIDENCE_RECEIPT_VERDICTS")
    inventory_digest = digest(canonical([
        {"relative_path": entry["relative_path"], "bytes": entry["bytes"],
         "sha256": entry["sha256"]} for entry in
        sorted(collected_inventory, key=lambda item: item["relative_path"])]))
    receipt = {
        "schema": RECEIPT_SCHEMA, "job": job, "profile": profile,
        "contract_sha256": contract_digest(document),
        "required_count": document["required_count"],
        "inventory_sha256": inventory_digest,
        "inventory_count": len(collected_inventory),
        "object_versions": dict(sorted((versions or {}).items())),
        "destination": str(destination),
        "byte_integrity": {key: byte_verdict[key] for key in
                           ("state", "verified_count", "required_count", "missing",
                            "mismatched", "unavailable")},
        "measurement_completeness": {
            "state": completeness_verdict["state"],
            "failures": completeness_verdict["failures"],
            "conditions": completeness_verdict["conditions"],
            "conditions_omitted": completeness_verdict["conditions_omitted"]},
        "backup": backup or {"state": "NOT_ATTEMPTED"},
        "compute_cleanup": compute or {"state": "NOT_ATTEMPTED"},
        "failures": list(failures or ()),
        "issued_by": "receiver",
        "worker_supplied_verified_field_is_not_a_receipt": True,
        "reusable_for_another_job": False,
    }
    receipt["collection"] = (
        "COMPLETE_VERIFIED"
        if byte_verdict["state"] == "COMPLETE_VERIFIED"
        and completeness_verdict["state"] == "COMPLETE" else "INCOMPLETE")
    receipt["receipt_sha256"] = digest(canonical(receipt))
    return receipt


def receipt_is_valid_for(receipt, *, job, document, collected_inventory):
    """A receipt must not be reusable for another job or an altered inventory."""
    if type(receipt) is not dict or receipt.get("schema") != RECEIPT_SCHEMA:
        return False, "RECEIPT_SCHEMA"
    if receipt.get("job") != job:
        return False, "RECEIPT_JOB_MISMATCH"
    if not document or receipt.get("contract_sha256") != contract_digest(document):
        return False, "RECEIPT_CONTRACT_MISMATCH"
    expected = digest(canonical([
        {"relative_path": entry["relative_path"], "bytes": entry["bytes"],
         "sha256": entry["sha256"]} for entry in
        sorted(collected_inventory, key=lambda item: item["relative_path"])]))
    if receipt.get("inventory_sha256") != expected:
        return False, "RECEIPT_INVENTORY_MISMATCH"
    body = {key: value for key, value in receipt.items()
            if key != "receipt_sha256"}
    if receipt.get("receipt_sha256") != digest(canonical(body)):
        return False, "RECEIPT_DIGEST_MISMATCH"
    return True, None


# --------------------------------------------------------------------------
# 7. cleanup and retention are separate decisions
# --------------------------------------------------------------------------

def deletion_decision(*, receipt, contract_document, inventory_digest_check=True,
                      retention=None, backup=None, policy=None, denied_before=False):
    """Deletion defaults to DENY, and an error never opens the path.

    Deletion is allowed only when every one of these holds: an approved retention
    policy names the archive and its minimum protection period; that period has
    actually elapsed; the receiver's receipt says the collection is complete and
    verified; measurement completeness is COMPLETE or explicitly not required by
    the profile; and an independently readable retained backup has been verified by
    reading it back. None of the NON_REASONS authorises deletion, and a prior denial
    is sticky.
    """
    reasons = []
    if denied_before:
        reasons.append("A_PREVIOUS_DENIAL_IS_STICKY")
    if type(receipt) is not dict or receipt.get("schema") != RECEIPT_SCHEMA:
        reasons.append("NO_RECEIVER_RECEIPT")
    else:
        # The bound fields are checked here; the inventory digest is checked by
        # receipt_is_valid_for against the collection actually on disk, because this
        # decision does not receive the inventory.
        if not contract_document:
            reasons.append("NO_CONTRACT_TO_CHECK_THE_RECEIPT_AGAINST")
        elif receipt.get("contract_sha256") != contract_digest(contract_document):
            reasons.append("RECEIPT_CONTRACT_MISMATCH")
        body = {key: value for key, value in receipt.items()
                if key != "receipt_sha256"}
        if receipt.get("receipt_sha256") != digest(canonical(body)):
            reasons.append("RECEIPT_DIGEST_MISMATCH")
        if receipt.get("collection") != "COMPLETE_VERIFIED":
            reasons.append("COLLECTION_NOT_COMPLETE_VERIFIED")
        completeness = (receipt.get("measurement_completeness") or {}).get("state")
        if completeness not in ("COMPLETE", "NOT_EVALUATED"):
            reasons.append("MEASUREMENT_COMPLETENESS:" + str(completeness))
    if not retention:
        reasons.append("NO_APPROVED_RETENTION_POLICY")
    else:
        require(type(retention) is dict, "EVIDENCE_RETENTION_DOCUMENT")
        if not retention.get("approved_by_owner"):
            reasons.append("RETENTION_POLICY_NOT_APPROVED")
        if retention.get("minimum_protection_days") in (None, 0):
            reasons.append("RETENTION_MINIMUM_MISSING")
        if retention.get("elapsed_days") is None:
            reasons.append("RETENTION_ELAPSED_UNKNOWN")
        elif retention.get("minimum_protection_days") is not None \
                and retention["elapsed_days"] < retention["minimum_protection_days"]:
            reasons.append("RETENTION_PERIOD_NOT_ELAPSED")
    if not backup or backup.get("state") != "VERIFIED":
        reasons.append("INDEPENDENT_BACKUP_NOT_VERIFIED")
    if not policy or not policy.get("approved_cleanup_policy"):
        reasons.append("NO_APPROVED_DELETION_POLICY")
    if not inventory_digest_check:
        reasons.append("INVENTORY_DIGEST_NOT_CHECKED")
    decision = ALLOW if not reasons else DENY
    return {"schema": DECISION_SCHEMA, "decision": decision,
            "archive_state": ("DELETION_APPROVED" if decision == ALLOW
                              else "DELETION_DENIED"),
            "reasons": reasons,
            "denial_is_sticky": True,
            "logging_an_error_never_opens_this_path": True,
            "never_sufficient_on_its_own": list(NON_REASONS),
            "when_allowed": ("an approved policy, an elapsed minimum protection "
                             "period, a complete verified collection, a verified "
                             "independent backup, and the separate authorised "
                             "cleanup policy")}


def archive_status(*, collection_state, retention=None, backup=None):
    """The archive's own state, which is not the compute's state."""
    retention = retention if isinstance(retention, dict) else None
    backup = backup if isinstance(backup, dict) else None
    if retention and retention.get("approved_by_owner"):
        return "RETAINED_UNDER_POLICY"
    if collection_state in ("COMPLETE_VERIFIED", "INCOMPLETE"):
        return "RETAINED_PENDING_COLLECTION"
    return "DELETION_DENIED"


def stage_states(*, execution, byte_verdict, completeness_verdict, backup=None,
                 compute=None, retention=None, measurement_keys=(),
                 document=None):
    """The separate states, never collapsed into one word.

    ``checkpoint_collection`` and ``measurement_collection`` are reported apart on
    purpose: the failure this directive answers had every checkpoint arrive and the
    measurement missing, and a single "everything was received" word is exactly what
    hid it. A run may legitimately report execution FINISHED and compute cleanup
    COMPLETE while measurement collection is INCOMPLETE and completed_deliverable is
    false; the unacceptable state is an incomplete measurement whose only surviving
    copy was deleted.
    """
    byte_verdict = byte_verdict if isinstance(byte_verdict, dict) else {}
    completeness_verdict = (completeness_verdict
                            if isinstance(completeness_verdict, dict) else {})
    compute = compute if isinstance(compute, dict) else {"state": "NOT_ATTEMPTED"}
    backup = backup if isinstance(backup, dict) else None
    retention = retention if isinstance(retention, dict) else None
    byte_state = byte_verdict.get("state", "NOT_ATTEMPTED")
    missing = set(byte_verdict.get("missing") or ())
    required = set(contract_keys(document)) if document else set()
    checkpoint_keys = {key for key in required if key.endswith(".pt")}
    measurement = set(measurement_keys) & (required or set(measurement_keys))
    checkpoint_missing = sorted(missing & checkpoint_keys)
    measurement_missing = sorted(missing & measurement)
    if byte_state == "NOT_ATTEMPTED":
        checkpoint_state = measurement_state = "NOT_ATTEMPTED"
    else:
        checkpoint_state = ("INCOMPLETE" if checkpoint_missing
                            else "COMPLETE_VERIFIED")
        measurement_state = ("INCOMPLETE" if measurement_missing
                             else "COMPLETE_VERIFIED")
    archive = archive_status(collection_state=byte_state, retention=retention,
                             backup=backup)
    return {"execution": execution,
            "compute_cleanup": (compute or {}).get("state", "NOT_ATTEMPTED"),
            "checkpoint_collection": checkpoint_state,
            "checkpoint_collection_state": byte_state,
            "measurement_collection": measurement_state,
            "measurement_completeness": (completeness_verdict or {}).get(
                "state", "NOT_EVALUATED"),
            "backup_verification": (backup or {}).get("state", "NOT_ATTEMPTED"),
            "evidence_retention": ("ACTIVE" if archive in
                                   ("RETAINED_UNDER_POLICY",
                                    "RETAINED_PENDING_COLLECTION",
                                    "DELETION_DENIED") else "NONE"),
            "evidence_archive": archive,
            "missing_checkpoint_objects": checkpoint_missing,
            "missing_measurement_objects": measurement_missing,
            "missing_required_objects": sorted(missing),
            # so no reader has to remember which of the words decides deletion
            "only_surviving_copy": ("RETAINED" if archive != "ABSENT"
                                    else "ABSENT")}


def panel_facts(items, *, primary_layers=("role_application", "role_recognition")):
    """The frozen panel's exact identities, for the pre-run contract.

    Computed from the panel itself, before any launch, so the collector checks real
    question identities, phases, faces and per-face item counts rather than a count
    the worker happens to report.
    """
    item_ids = sorted(str(item["item_id"]) for item in items)
    faces = sorted({int(item["face"]) for item in items if item.get("face") is not None})
    per_face = {}
    for item in items:
        if item.get("face") is None:
            continue
        key = str(int(item["face"]))
        per_face[key] = per_face.get(key, 0) + 1
    by_layer = {}
    for item in items:
        by_layer[item["layer"]] = by_layer.get(item["layer"], 0) + 1
    return {"item_ids": item_ids, "faces": faces, "per_face": per_face,
            "by_layer": by_layer,
            "primary_layers": list(primary_layers),
            "item_count": len(item_ids),
            "note": ("exact item identities, not counts alone; duplicates cannot "
                     "substitute for missing questions")}


def completed_deliverable(*, execution, byte_verdict, completeness_verdict,
                          receipt, compute, document):
    """Computed from the registered requirements and the receiver's checks.

    It cannot be set by the worker and is not inferred from exit code zero. Failing
    to produce a declared measurement is an explicit incomplete deliverable, not
    zero performance; a scientific negative with complete evidence is deliverable.
    """
    return bool(
        execution == "FINISHED"
        and byte_verdict and byte_verdict.get("state") == "COMPLETE_VERIFIED"
        and completeness_verdict and completeness_verdict.get("state") == "COMPLETE"
        and receipt and receipt.get("collection") == "COMPLETE_VERIFIED"
        and (compute or {}).get("state") == "COMPLETE"
        and document and document.get("required_count"))


# --------------------------------------------------------------------------
# 8. the shared outer-worker transport
# --------------------------------------------------------------------------

ENTRYPOINT_GUARD = "if __name__ == '__main__':"


def entrypoint_index(lines):
    """Index of the module's ``if __name__ == '__main__':`` line, or None.

    Either quoting is accepted, because the rendered workers are written by hand
    and a future one may use double quotes.
    """
    for index in range(len(lines) - 1, -1, -1):
        text = lines[index]
        if text.startswith("if __name__ ==") and "__main__" in text:
            return index
    return None


def insert_before_entrypoint(source, block):
    """Place rendered definitions BEFORE the module calls ``main()``.

    Python binds a name when it executes the ``def``, not when it parses the
    file. The transport was appended to the END of the worker, which put
    ``def beacon`` after ``if __name__ == '__main__': main()``: the interpreter
    reached the guard first, entered ``main()``, and died on
    ``NameError: name 'beacon' is not defined`` before the worker wrote a single
    byte. The instance bootstrap was correct the whole time, and a launched GPU
    instance plus a $7.00 reservation were spent proving it - job
    cas-meta2-graph6read-20260912044325-14fcd081, instance i-0916a3eedfccea11f,
    the NameError visible in that instance's serial console.

    So the block goes in FRONT of the guard, and
    :func:`require_definitions_precede_entrypoint` refuses any source where a
    definition still trails it.
    """
    require(type(source) is str and type(block) is str,
            "TRANSPORT_INSERT_TEXT_REQUIRED")
    lines = source.splitlines()
    guard = entrypoint_index(lines)
    body = block.strip("\n").splitlines()
    if guard is None:
        return "\n".join(lines + ["", ""] + body) + "\n"
    head = lines[:guard]
    while head and not head[-1].strip():
        head.pop()
    return "\n".join(head + ["", ""] + body + ["", ""] + lines[guard:]) + "\n"


def require_definitions_precede_entrypoint(source):
    """Refuse a worker whose module body binds a name after it calls ``main()``.

    The invariant is deliberately blunt: every top-level ``def``, ``class``,
    assignment and import must appear before the entrypoint guard. That is
    exactly the law the appended transport broke, it is checkable without
    running anything, and a compile check cannot see it - the broken worker
    compiled cleanly and still failed on the instance.

    Returns the names bound before the guard, so a caller can record them.
    """
    require(type(source) is str and source, "ENTRYPOINT_ORDER_SOURCE_REQUIRED")
    tree = ast.parse(source)
    guard = entrypoint_index(source.splitlines())
    bound, trailing = [], []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = [node.name]
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.asname or alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
        else:
            names = []
        if not names:
            continue
        if guard is not None and node.lineno > guard + 1:
            trailing.extend(names)
        else:
            bound.extend(names)
    require(not trailing,
            "DEFINITION_AFTER_ENTRYPOINT:" + ",".join(sorted(set(trailing))))
    return bound


def unified_transport(source, *, evidence_subdir="results", marker="result.json",
                      sidecar="result.json.sha256", publisher_seconds=60.0,
                      artifact_prefix="results/artifacts/",
                      manifest_key="results/artifacts/manifest.json"):
    """Rewrite a rendered worker so it uses the shared transport, and say so.

    Declared, not silent: the caller is told exactly which functions were replaced
    and the package manifest records it, so a reader of the package can see that the
    transport is the shared one rather than a copy that has drifted.

    The launchers each grew their own ``upload_results``, and that duplication is
    how attempt 004 lost its readout: the copies staged an explicit list of names
    instead of the evidence directory, so a payload the worker wrote but did not
    list was never uploaded under a declared artefact. One implementation removes
    the class of defect rather than the instance.
    """
    require(type(source) is str and source, "TRANSPORT_SOURCE_REQUIRED")
    if "def upload_results(s3, bucket, root, published=None):" in source:
        # already unified: applying it twice is a no-op, so a caller cannot
        # accidentally drop the transport by unifying an already-unified source
        require_definitions_precede_entrypoint(source)
        return {"source": source, "replaced": [], "already_unified": True,
                "transport": "aws.run_evidence.render_transport",
                "evidence_subdir": evidence_subdir,
                "publisher_wired": "publisher(" in source,
                "note": "the source already carries the shared transport"}
    lines = source.splitlines()
    kept, replaced, skipping = [], [], False
    for line in lines:
        if line.startswith("def upload_results("):
            skipping = True
            replaced.append("upload_results")
            continue
        if skipping:
            # the replaced function ends at the next top-level statement
            if line and not line[0].isspace() and not line.startswith(")"):
                skipping = False
            else:
                continue
        kept.append(line)
    require(replaced, "TRANSPORT_UPLOADER_NOT_FOUND")
    text = "\n".join(kept)
    # the shared uploader takes the run root, because it walks the evidence
    # directory; the copies took the results directory
    for call in (", results_dir)", ", results)"):
        text = text.replace(call, call[:-1] + ".parent)")
    # Hand the publisher's own record of what it already uploaded to the final
    # upload. Without it the final pass starts from an EMPTY map, re-puts every
    # file the publisher had already sent, and every one of those create-only
    # puts conflicts. Job cas-meta2-graph6read-20260912062331-b34e3d92 died that
    # way AFTER its readout was complete and uploaded: the conflict handler tried
    # to read the object back to compare digests, the job role grants GetObject on
    # input/* only, and the AccessDenied killed the worker before it could write
    # results/result.json. The science was done; the delivery marker was lost.
    text = text.replace("upload_results(s3, bucket, results_dir.parent)",
                        "upload_results(s3, bucket, results_dir.parent, _published)")
    text = text.replace("upload_results(s3, bucket, results.parent)",
                        "upload_results(s3, bucket, results.parent, _published)")

    # Environment phases are marked as they complete, and the publisher is started
    # BEFORE the install rather than after the run. The 2026-09-11 readout burned its
    # full two-hour ceiling in the environment phase and left an empty archive: with
    # the client created only at the end, nothing the worker wrote was ever uploaded,
    # so the hang could not be located. Beacons and an early publisher make that
    # failure visible while it is happening.
    marked, started = [], False
    # Inserted BEFORE each step, so a phase that hangs is named rather than only the
    # phases that finished. Anchoring on the opening line of each call keeps this
    # robust across the workers' differing argument layouts.
    ordered_marks = (
        ("        python = str(venv_py)", "venv_ready", "after"),
        ("        run_checked([python, '-m', 'pip', 'install',", "pip_step", "before"),
        ("        inner = subprocess.run([python, '-B', str(runner), str(root)],",
         "inner_runner_starting", "before"),
    )
    pip_names = ("pip_torch_starting", "pip_wheels_starting",
                 "pip_requirements_starting")
    pip_seen = 0
    for anchor, name, where in ordered_marks:
        while anchor in text:
            if name == "pip_step":
                if pip_seen >= len(pip_names):
                    break
                mark = "        beacon(root, %r)" % pip_names[pip_seen]
                pip_seen += 1
            else:
                mark = "        beacon(root, %r)" % name
            if where == "after":
                text = text.replace(anchor, anchor + "\n" + mark, 1)
            else:
                text = text.replace(anchor, mark + "\n" + anchor, 1)
            marked.append(mark.strip().split("'")[1])
            if name != "pip_step":
                break
    starter = (
        "    failure = None\n"
        "    import threading\n"
        "    import boto3\n"
        "    s3 = boto3.client('s3', region_name=region)\n"
        "    _published = {}\n"
        "    _publish_errors = []\n"
        "    _stop_publishing = threading.Event()\n"
        "    beacon(root, 'worker_started')\n"
        "    _publisher = threading.Thread(\n"
        "        target=publisher,\n"
        "        args=(s3, bucket, root, _published, _stop_publishing,\n"
        "              _publish_errors, PUBLISH_SECONDS), daemon=True)\n"
        "    _publisher.start()\n"
        "    beacon(root, 'publisher_started')\n")
    if "    failure = None\n" in text:
        text = text.replace("    failure = None\n", starter, 1)
        started = True
    if started:
        # the publisher is stopped before the final upload, so the inventory it was
        # writing is quiet while the marker goes up
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if "upload_results(s3, bucket," in line and "def upload_results" not in line:
                indent = line[:len(line) - len(line.lstrip())]
                lines[index:index] = [
                    indent + "_stop_publishing.set()",
                    indent + "_publisher.join(timeout=30)",
                    indent + "beacon(root, 'publishing_stopped')"]
                break
        text = "\n".join(lines)
    text = insert_before_entrypoint(text, "\n".join(render_transport(
        evidence_subdir=evidence_subdir, marker=marker, sidecar=sidecar,
        publisher_seconds=publisher_seconds, artifact_prefix=artifact_prefix,
        manifest_key=manifest_key)))
    require_definitions_precede_entrypoint(text)
    return {"source": text, "replaced": replaced,
            "transport": "aws.run_evidence.render_transport",
            "evidence_subdir": evidence_subdir,
            "publisher_wired": started,
            "phase_beacons": marked,
            "note": ("the stager now uploads every regular file under the evidence "
                     "directory, with create-only keys and the marker last, and the "
                     "publisher runs from before the environment install so a hang "
                     "leaves a visible timeline")}


def unified_worker_source(source, **kwargs):
    """The rewritten source alone, for callers that only want the text."""
    return unified_transport(source, **kwargs)["source"]


def render_transport(*, evidence_subdir="results", marker="result.json",
                     sidecar="result.json.sha256", publisher_seconds=60.0,
                     artifact_prefix="results/artifacts/",
                     manifest_key="results/artifacts/manifest.json"):
    """The one transport every candidate worker uses, as source lines.

    It lives in the OUTER worker, which already has boto3, so no AWS SDK import
    ever enters the training environment. It stages the whole evidence directory -
    every regular file, no extension filter - states the worker's produced manifest,
    publishes completed files incrementally while the body runs, and uploads the
    transport marker last, after the inventory is durable. The marker means only
    that the producer finished publishing its current inventory: it grants neither
    collection completeness nor evidence deletion.
    """
    lines = [
        "PUBLISH_SECONDS = %.1f" % publisher_seconds,
        "",
        "",
        "def beacon(root, name, **fields):",
        "    \"\"\"A durable mark that an environment phase completed.",
        "    ",
        "    Written into the evidence directory the moment it happens, so a run that",
        "    later hangs or is killed still shows how far it got. The two-hour run on",
        "    2026-09-11 left an empty archive for exactly this reason: when the worker",
        "    dies before its first upload, nothing on the instance is visible afterwards.",
        "    \"\"\"",
        "    import json as _json",
        "    import time as _time",
        "    directory = root / %r / 'evidence'" % evidence_subdir,
        "    try:",
        "        directory.mkdir(parents=True, exist_ok=True)",
        "        document = dict(fields, phase=name, at=round(_time.time(), 3))",
        "        path = directory / ('phase_%s.json' % name)",
        "        if not path.exists():",
        "            path.write_text(_json.dumps(document, sort_keys=True) + '\\n')",
        "        return str(path)",
        "    except BaseException:                     # noqa: BLE001 - never fatal",
        "        return None",
        "",
        "",
        "def evidence_files(root):",
        "    \"\"\"Every regular file under the evidence directory, no suffix filter.\"\"\"",
        "    base = root / %r" % evidence_subdir,
        "    found = []",
        "    for path in sorted(base.rglob('*')):",
        "        if path.is_file() and not path.is_symlink():",
        "            found.append(path)",
        "    return found",
        "",
        "",
        "def sha256_file(path):",
        "    digest = hashlib.sha256()",
        "    with open(path, 'rb') as stream:",
        "        for block in iter(lambda: stream.read(1 << 20), b''):",
        "            digest.update(block)",
        "    return digest.hexdigest()",
        "",
        "",
        "def publish_once(s3, bucket, root, published, marker_name=%r," % marker,
        "                 sidecar_name=%r):" % sidecar,
        "    \"\"\"Upload new completed files. Create-only where the SDK supports it.\"\"\"",
        "    uploaded, skipped, unverified = [], [], []",
        "    for path in evidence_files(root):",
        "        key = path.relative_to(root).as_posix()",
        "        if key.endswith('.partial') or key.endswith('.tmp'):",
        "            skipped.append(key)",
        "            continue",
        "        if key.endswith(marker_name) or key.endswith(sidecar_name):",
        "            skipped.append(key)          # the transport marker goes last",
        "            continue",
        "        digest_value = sha256_file(path)",
        "        if published.get(key) == digest_value:",
        "            continue",
        "        body = path.read_bytes()",
        "        try:",
        "            s3.put_object(Bucket=bucket, Key=key, Body=body,",
        "                          IfNoneMatch='*')",
        "        except Exception as error:                      # noqa: BLE001",
        "            code = getattr(error, 'response', {}).get('Error', {}).get('Code')",
        "            if code in ('PreconditionFailed', 'ConditionalRequestConflict'):",
        "                try:",
        "                    existing = s3.get_object(Bucket=bucket, Key=key)",
        "                    current = existing['Body'].read()",
        "                except Exception as read_error:          # noqa: BLE001",
        "                    # The key is already there - create-only said so - but",
        "                    # we cannot read it back to compare. Losing the whole",
        "                    # delivery over a file that IS uploaded is the worse",
        "                    # failure, so record it and carry on.",
        "                    unverified.append({'key': key,",
        "                                       'reason': type(read_error).__name__})",
        "                    published[key] = digest_value",
        "                    continue",
        "                if hashlib.sha256(current).hexdigest() != digest_value:",
        "                    raise SystemExit('EVIDENCE_DIGEST_CONFLICT:' + key)",
        "                published[key] = digest_value",
        "                continue",
        "            raise",
        "        published[key] = digest_value",
        "        uploaded.append({'key': key, 'sha256': digest_value,",
        "                         'bytes': len(body)})",
        "    return {'uploaded': uploaded, 'skipped': skipped,",
        "            'unverified_existing': unverified,",
        "            'artifacts': [entry['key'] for entry in uploaded],",
        "            'published_sequence': len(published),",
        "            'transport_tail': [key for key in skipped",
        "                               if key.endswith(marker_name)",
        "                               or key.endswith(sidecar_name)],",
        "            'unuploaded_tail': [key for key in",
        "                                (path.relative_to(root).as_posix()",
        "                                 for path in evidence_files(root))",
        "                                if key not in published",
        "                                and not key.endswith(marker_name)",
        "                                and not key.endswith(sidecar_name)]}",
        "",
        "",
        "def upload_results(s3, bucket, root, published=None):",
        "    \"\"\"The inventory, then the sidecar, then the transport marker LAST.\"\"\"",
        "    published = {} if published is None else published",
        "    results = root / %r" % evidence_subdir,
        "    upload = publish_once(s3, bucket, root, published, %r, %r)" % (
            marker, sidecar),
        "    manifest = results / 'artifacts' / 'manifest.json'",
        "    if manifest.is_file():",
        "        s3.put_object(Bucket=bucket, Key=%r," % manifest_key,
        "                      Body=manifest.read_bytes())",
        "    sidecar_path = results / %r" % sidecar,
        "    if sidecar_path.is_file():",
        "        s3.put_object(Bucket=bucket,",
        "                      Key=%r + %r," % (evidence_subdir + "/", sidecar),
        "                      Body=sidecar_path.read_bytes())",
        "    marker_path = results / %r" % marker,
        "    if marker_path.is_file():",
        "        s3.put_object(Bucket=bucket,",
        "                      Key=%r + %r," % (evidence_subdir + "/", marker),
        "                      Body=marker_path.read_bytes())",
        "        upload['marker'] = True",
        "    upload['manifest'] = manifest.is_file()",
        "    upload['sidecar'] = sidecar_path.is_file()",
        # The replaced per-worker uploaders returned a 'result' flag and their
        # callers still print it. Dropping the key turned every readout run into
        # an uncaught KeyError on the last line of main(), after the evidence was
        # already up: a delivered run that reported itself as a crash. A
        # replacement keeps the keys its callers read.
        "    upload['result'] = bool(upload.get('marker'))",
        "    upload['marker_meaning'] = ('the producer finished publishing its "
        "current inventory; it grants neither collection completeness nor "
        "evidence deletion')",
        "    return upload",
        "",
        "",
        "def publisher(s3, bucket, root, published, stop, errors, seconds):",
        "    \"\"\"Publish completed files while the body runs; bounded unsaved work.\"\"\"",
        "    import time",
        "    while not stop.is_set():",
        "        try:",
        "            publish_once(s3, bucket, root, published, %r, %r)" % (
            marker, sidecar),
        "        except BaseException as error:                # noqa: BLE001",
        "            errors.append(type(error).__name__ + ':' + str(error)[:500])",
        "        stop.wait(seconds)",
        "",
    ]
    return lines
