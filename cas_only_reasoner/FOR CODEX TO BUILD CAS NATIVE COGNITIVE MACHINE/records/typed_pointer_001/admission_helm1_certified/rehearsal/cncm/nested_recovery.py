"""Host journal persistence and semantic recovery through nested transitions.

No saved state is imported into the registry. A caller supplies the trusted
initial problem and expected complete journal digest; replay reconstructs every
coordinator transition. A hash alone does not authenticate a principal.
"""
from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
import tempfile

from .canonical import canonical_json, digest
from .model import ContractError, Intent, IntentType, Provenance
from .nested_model import NestedIntentType, NestedProblem, NestedState
from .nested_profile import (MAX_EPISODES, MAX_JOURNAL_BYTES, MAX_JOURNAL_EVENTS,
                             NestedProfile, load_nested_profile)

JOURNAL_SCHEMA = "cncm.nested-journal/0.3"


def require(condition, reason):
    if not condition:
        raise ContractError(reason)


def unique_object(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate journal object key")
        result[key] = value
    return result


def decode_journal(raw):
    require(type(raw) is bytes and len(raw) <= MAX_JOURNAL_BYTES, "nested journal byte bound exceeded")
    try:
        return json.loads(raw, object_pairs_hook=unique_object,
            parse_int=_parse_json_integer,
            parse_constant=lambda _: (_ for _ in ()).throw(ContractError("nonfinite journal number")))
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ContractError("invalid nested journal JSON") from error


def _parse_json_integer(raw):
    # A signed 512-bit receipt value needs at most 155 decimal digits. Bound
    # the input before int(), then enforce the exact binary bound. Typed state
    # counters remain subject to their own narrower model/kernel checks.
    digits = raw[1:] if raw.startswith("-") else raw
    require(len(digits) <= 155, "journal integer text bound exceeded")
    value = int(raw)
    require(value.bit_length() <= 512, "journal integer bound exceeded")
    return value


def _check_json_tree(value):
    """Reject coercible Python objects and bound traversal before serialization."""
    pending, count, text_bytes = [(value, 0)], 0, 0
    while pending:
        item, depth = pending.pop()
        count += 1
        require(count <= 1_000_000 and depth <= 64, "nested journal structure bound exceeded")
        if type(item) is dict:
            require(len(item) <= 4096 and all(type(key) is str for key in item), "invalid journal object")
            for key in item:
                require(len(key) <= MAX_JOURNAL_BYTES, "journal key bound exceeded")
                text_bytes += _utf8_size(key)
            require(text_bytes <= MAX_JOURNAL_BYTES, "nested journal aggregate text bound exceeded")
            pending.extend((child, depth+1) for child in item.values())
        elif type(item) is list:
            require(len(item) <= 4096, "invalid journal array")
            pending.extend((child, depth+1) for child in item)
        elif type(item) is str:
            require(len(item) <= MAX_JOURNAL_BYTES, "journal string bound exceeded")
            text_bytes += _utf8_size(item)
            require(text_bytes <= MAX_JOURNAL_BYTES, "nested journal aggregate text bound exceeded")
        elif type(item) is int:
            require(item.bit_length() <= 512, "journal integer bound exceeded")
        else:
            require(item is None or type(item) is bool, "invalid journal primitive")


def _utf8_size(text):
    try:
        return len(text.encode("utf-8"))
    except UnicodeError as error:
        raise ContractError("invalid journal Unicode") from error


def _decode_intent(wire):
    required = {"intent_id", "intent_type", "issuer_subsystem", "required_capability", "target_scope",
                "branch_id", "goal_id", "precondition", "proposed_mutation", "created_at_tick", "provenance"}
    require(type(wire) is dict and set(wire) == required, "nested journal intent fields invalid")
    require(type(wire["intent_type"]) is str and type(wire["created_at_tick"]) is int,
            "nested journal intent types invalid")
    try:
        kind = IntentType(wire["intent_type"])
    except ValueError:
        try:
            kind = NestedIntentType(wire["intent_type"])
        except ValueError as error:
            raise ContractError("unknown recovered intent type") from error
    require(type(wire["provenance"]) is list and len(wire["provenance"]) <= 64,
            "nested intent provenance bound exceeded")
    body = {key: value for key, value in wire.items() if key != "intent_id"}
    body["intent_type"] = kind
    try:
        body["provenance"] = tuple(Provenance.from_dict(row) for row in wire["provenance"])
        intent = Intent.create(**body)
        # Preserve a format-valid but forged ID and noncanonical provenance
        # order so the coordinator reproduces their original rejection.
        intent = replace(intent, intent_id=wire["intent_id"], provenance=body["provenance"])
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as error:
        raise ContractError("invalid recovered intent") from error
    require(canonical_json(intent.to_dict()) == canonical_json(wire), "recovered intent does not reconstruct")
    return intent


def _decode_proposal_batch(batch):
    require(type(batch) is list and len(batch) <= 8, "nested proposal occurrence bound exceeded")
    result = []
    for row in batch:
        require(type(row) is dict and set(row) == {"intent", "malformed"}
                and type(row["malformed"]) is bool, "nested proposal occurrence invalid")
        intent = _decode_intent(row["intent"])
        # The kernel regenerates its own malformed surrogate using this
        # occurrence's index and pre-state; no supplied rejection is imported.
        # Replay then compares the regenerated full event AND normalized batch.
        result.append(replace(intent, intent_id="replay-malformed") if row["malformed"] else intent)
    return tuple(result)


def recover_nested_journal(journal, *, trusted_genesis, expected_journal_digest, profile=None):
    """Rebuild a live NestedMachine, including partially completed acquisition.

    expected_journal_digest must come from the caller's trusted retained receipt,
    not from the untrusted journal being checked. It detects truncation as well
    as altered content. The source profile must match the current pinned code.
    """
    from .nested_engine import NestedMachine
    require(type(trusted_genesis) is NestedProblem, "trusted typed genesis required")
    require(type(expected_journal_digest) is str and len(expected_journal_digest) == 64
            and all(char in "0123456789abcdef" for char in expected_journal_digest),
            "expected complete journal digest required")
    if type(journal) is bytes:
        journal = decode_journal(journal)
    _check_json_tree(journal)
    require(type(journal) is dict and set(journal) == {"schema_version", "source_profile", "episodes", "journal_digest"},
            "nested journal fields invalid")
    require(len(canonical_json(journal).encode()) <= MAX_JOURNAL_BYTES, "nested journal byte bound exceeded")
    require(journal["schema_version"] == JOURNAL_SCHEMA, "unsupported nested journal schema")
    body = {key: value for key, value in journal.items() if key != "journal_digest"}
    require(digest(body) == journal["journal_digest"] == expected_journal_digest,
            "complete nested journal digest mismatch")
    profile = load_nested_profile() if profile is None else profile
    require(type(profile) is NestedProfile and canonical_json(journal["source_profile"]) == canonical_json(profile.to_dict()),
            "recovery source profile mismatch")
    episodes = journal["episodes"]
    require(type(episodes) is list and 1 <= len(episodes) <= MAX_EPISODES, "nested episode count invalid")
    machine = NestedMachine(profile=profile)
    event_count = 0
    for index, episode in enumerate(episodes):
        require(type(episode) is dict and set(episode) == {"problem", "initial_state_hash", "prior_episode_state_hash",
                    "source_profile_digest", "trace", "proposal_batches", "final_state"}, "nested episode fields invalid")
        problem = NestedProblem.from_dict(episode["problem"])
        if index == 0:
            require(canonical_json(problem.to_dict()) == canonical_json(trusted_genesis.to_dict()),
                    "nested genesis differs from trusted problem")
        require(episode["source_profile_digest"] == profile.profile_digest, "episode profile mismatch")
        machine.start(problem)
        coordinator = machine.coordinator
        initial = coordinator.store.snapshot()
        require(initial.state_hash == episode["initial_state_hash"]
                and initial.prior_episode_state_hash == episode["prior_episode_state_hash"],
                "nested episode genesis/handoff mismatch")
        require(type(episode["trace"]) is list, "nested trace must be a list")
        require(type(episode["proposal_batches"]) is list
                and len(episode["proposal_batches"]) == len(episode["trace"]),
                "nested proposal batches must align with trace")
        event_count += len(episode["trace"])
        require(event_count <= MAX_JOURNAL_EVENTS, "nested journal event bound exceeded")
        for event_index, wire in enumerate(episode["trace"]):
            require(type(wire) is dict, "nested trace event malformed")
            require(type(wire.get("proposed_intents")) is list and len(wire["proposed_intents"]) <= 8,
                    "nested trace intent count invalid")
            require(type(wire.get("enabled_components")) is list and type(wire.get("scheduled_components")) is list
                    and len(wire["enabled_components"]) <= 32 and len(wire["scheduled_components"]) <= 32,
                    "nested trace component bounds invalid")
            intents = _decode_proposal_batch(episode["proposal_batches"][event_index])
            outcome = coordinator.execute(enabled_components=wire["enabled_components"],
                scheduled_components=wire["scheduled_components"], intents=intents)
            require(canonical_json(outcome.trace_event.to_dict()) == canonical_json(wire),
                    "nested transition does not reproduce saved event")
            require(canonical_json(coordinator.proposal_batches[-1])
                    == canonical_json(episode["proposal_batches"][event_index]),
                    "nested proposal normalization does not reconstruct")
        # Structural validation is additional evidence only: this parsed object
        # never enters a StateStore and never installs its supplied procedure.
        NestedState.from_dict(episode["final_state"])
        require(canonical_json(coordinator.store.snapshot().to_dict()) == canonical_json(episode["final_state"]),
                "nested final state does not reconstruct")
    require(canonical_json(machine.journal()) == canonical_json(journal), "nested complete journal does not reconstruct")
    return machine


def save_nested_journal(machine, path):
    """Atomically persist outside the kernel; return the external integrity anchor."""
    journal = machine.journal()
    raw = (canonical_json(journal)+"\n").encode()
    require(len(raw) <= MAX_JOURNAL_BYTES, "nested journal byte bound exceeded")
    destination = Path(path).resolve()
    require(destination.parent.is_dir(), "nested journal destination parent missing")
    descriptor, temporary = tempfile.mkstemp(prefix=".nested-journal-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return {"path": str(destination), "journal_digest": journal["journal_digest"],
            "bytes": len(raw), "source_profile_digest": machine.profile.profile_digest,
            "boundary": "Integrity anchor from trusted caller; not cryptographic principal authentication."}


def verify_nested_journal(journal, *, trusted_genesis, expected_journal_digest, profile=None):
    """Return an exact replay receipt; failed replay raises ContractError."""
    machine = recover_nested_journal(journal, trusted_genesis=trusted_genesis,
        expected_journal_digest=expected_journal_digest, profile=profile)
    return {"schema_version": "cncm.nested-replay-receipt/0.3",
        "journal_digest": machine.journal()["journal_digest"],
        "source_profile_digest": machine.profile.profile_digest,
        "final_state_hash": machine.state.state_hash, "episodes": len(machine.journal()["episodes"]),
        "boundary": "Semantic replay under caller-trusted genesis and source profile; not principal authentication."}
