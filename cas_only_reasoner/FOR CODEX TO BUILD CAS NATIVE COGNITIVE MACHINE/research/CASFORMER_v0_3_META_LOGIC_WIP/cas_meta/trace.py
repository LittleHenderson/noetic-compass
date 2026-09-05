"""Schema and hash-chain validation for the bounded-call research trace.

These checks establish record shape and internal consistency, not provenance
from a trusted signer or proof that the recorded execution really occurred.
The executor separately compares native receipts and validates stored traces.
"""

from hashlib import sha256
import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError, validators


META_EVENT_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "meta_event.schema.json"
_SCHEMA = json.loads(META_EVENT_SCHEMA_PATH.read_text(encoding="utf-8"))
Draft202012Validator.check_schema(_SCHEMA)
# JSON Schema integers are mathematical integers, so 1.0 normally qualifies.
# Wire records from this executor use actual ints, never bools or floats.
_TYPES = Draft202012Validator.TYPE_CHECKER.redefine(
    "integer", lambda checker, value: type(value) is int
)
_VALIDATOR = validators.extend(Draft202012Validator, type_checker=_TYPES)(_SCHEMA)


class MetaTraceError(ValueError):
    def __init__(self, code: str, event_index: int | None = None):
        self.code = code
        self.event_index = event_index
        super().__init__(code)


def _digest(value) -> str:
    wire = json.dumps(
        value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")
    )
    return sha256(wire.encode("ascii")).hexdigest()


def validate_meta_events(events) -> None:
    """Reject malformed records, broken identities, hash chains, and charges.

    An empty list is a valid empty chain. It is not evidence of a completed
    program. Completion and call-stack checks belong to the executor.
    """
    if type(events) not in (list, tuple) or len(events) > 65536:
        raise MetaTraceError("META_TRACE_SCHEMA_INVALID")
    previous = None
    chain_id = None
    program_digest = None
    for index, event in enumerate(events):
        try:
            _VALIDATOR.validate(event)
        except (ValidationError, TypeError, RecursionError) as error:
            raise MetaTraceError("META_TRACE_SCHEMA_INVALID", index) from error
        if index == 0:
            chain_id, program_digest = event["chain_id"], event["program_digest"]
        wire = {key: value for key, value in event.items() if key != "digest"}
        if (
            event["seq"] != index or event["previous"] != previous
            or event["chain_id"] != chain_id or event["program_digest"] != program_digest
            or _digest(wire) != event["digest"]
            or any(
                event.get(key) is not None and not event[key].startswith(chain_id + ":call:")
                for key in ("call_id", "child_id", "parent_id")
            )
        ):
            raise MetaTraceError("META_TRACE_CHAIN_INVALID", index)
        if event["kind"] == "CHARGE" and event["units"] != sum(event["components"].values()):
            raise MetaTraceError("META_TRACE_CHARGE_MISMATCH", index)
        previous = event["digest"]
