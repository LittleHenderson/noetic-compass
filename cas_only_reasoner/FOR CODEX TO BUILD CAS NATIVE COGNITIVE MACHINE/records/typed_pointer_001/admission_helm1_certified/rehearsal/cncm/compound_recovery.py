"""Host journal persistence and compound recovery through compound transitions.

No saved state is imported into the registry. A caller supplies the trusted
initial problem, exact external source allowlist and complete journal digest; replay reconstructs every
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
from .compound_model import CompoundIntentType, CompoundProblem, CompoundState
from .semantic_model import SemanticIntentType, canonical_trusted_ingress, ingress_digest
from .compound_profile import (MAX_EPISODES, MAX_JOURNAL_BYTES, MAX_JOURNAL_EVENTS,
                             CompoundProfile, load_compound_profile)

JOURNAL_SCHEMA = "cncm.compound-journal/0.5"


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
    require(type(raw) is bytes and len(raw) <= MAX_JOURNAL_BYTES, "compound journal byte bound exceeded")
    try:
        return json.loads(raw, object_pairs_hook=unique_object,
            parse_int=_parse_json_integer,
            parse_constant=lambda _: (_ for _ in ()).throw(ContractError("nonfinite journal number")))
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ContractError("invalid compound journal JSON") from error


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
        require(count <= 1_000_000 and depth <= 64, "compound journal structure bound exceeded")
        if type(item) is dict:
            require(len(item) <= 4096 and all(type(key) is str for key in item), "invalid journal object")
            for key in item:
                require(len(key) <= MAX_JOURNAL_BYTES, "journal key bound exceeded")
                text_bytes += _utf8_size(key)
            require(text_bytes <= MAX_JOURNAL_BYTES, "compound journal aggregate text bound exceeded")
            pending.extend((child, depth+1) for child in item.values())
        elif type(item) is list:
            require(len(item) <= 4096, "invalid journal array")
            pending.extend((child, depth+1) for child in item)
        elif type(item) is str:
            require(len(item) <= MAX_JOURNAL_BYTES, "journal string bound exceeded")
            text_bytes += _utf8_size(item)
            require(text_bytes <= MAX_JOURNAL_BYTES, "compound journal aggregate text bound exceeded")
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
    require(type(wire) is dict and set(wire) == required, "compound journal intent fields invalid")
    require(type(wire["intent_type"]) is str and type(wire["created_at_tick"]) is int,
            "compound journal intent types invalid")
    try:
        kind = IntentType(wire["intent_type"])
    except ValueError:
        try:
            kind = SemanticIntentType(wire["intent_type"])
        except ValueError:
            try:
                kind = CompoundIntentType(wire["intent_type"])
            except ValueError as error:
                raise ContractError("unknown recovered intent type") from error
    require(type(wire["provenance"]) is list and len(wire["provenance"]) <= 64,
            "compound intent provenance bound exceeded")
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
    require(type(batch) is list and len(batch) <= 8, "compound proposal occurrence bound exceeded")
    result = []
    for row in batch:
        require(type(row) is dict and set(row) == {"intent", "malformed"}
                and type(row["malformed"]) is bool, "compound proposal occurrence invalid")
        intent = _decode_intent(row["intent"])
        # The kernel regenerates its own malformed surrogate using this
        # occurrence's index and pre-state; no supplied rejection is imported.
        # Replay then compares the regenerated full event AND normalized batch.
        result.append(replace(intent, intent_id="replay-malformed") if row["malformed"] else intent)
    return tuple(result)


def recover_compound_journal(journal, *, trusted_genesis, trusted_ingress,
                             expected_journal_digest, profile=None, trusted_ingress_extensions=()):
    """Rebuild a live CompoundMachine, including partially completed acquisition.

    expected_journal_digest must come from the caller's trusted retained receipt,
    not from the untrusted journal being checked. It detects truncation as well
    as altered content. The source profile must match the current pinned code. trusted_ingress must
    come from caller custody; statements and journal metadata do not grant trust.
    trusted_ingress is the initial set. trusted_ingress_extensions contains
    external additions for episodes 1 onward; omitted trailing entries are
    empty. Even a correct final set cannot replace this original chronology.
    """
    from .compound_engine import CompoundMachine
    require(type(trusted_genesis) is CompoundProblem, "trusted typed genesis required")
    ingress = canonical_trusted_ingress(trusted_ingress)
    require(type(trusted_ingress_extensions) is tuple and len(trusted_ingress_extensions) < MAX_EPISODES,
            "external ingress extension schedule must be a bounded tuple")
    extensions = tuple(canonical_trusted_ingress(row) for row in trusted_ingress_extensions)
    final_ingress = ingress
    for addition in extensions:
        require(not set(addition) & set(final_ingress), "ingress extension repeats existing authority")
        final_ingress = canonical_trusted_ingress(final_ingress + addition)
    trusted_ingress_digest = ingress_digest(final_ingress)
    require(type(expected_journal_digest) is str and len(expected_journal_digest) == 64
            and all(char in "0123456789abcdef" for char in expected_journal_digest),
            "expected complete journal digest required")
    if type(journal) is bytes:
        journal = decode_journal(journal)
    _check_json_tree(journal)
    require(type(journal) is dict and set(journal) == {"schema_version", "source_profile", "ingress_digest", "episodes", "journal_digest"},
            "compound journal fields invalid")
    require(len(canonical_json(journal).encode()) <= MAX_JOURNAL_BYTES, "compound journal byte bound exceeded")
    require(journal["schema_version"] == JOURNAL_SCHEMA, "unsupported compound journal schema")
    require(journal["ingress_digest"] == trusted_ingress_digest,
            "journal ingress differs from caller trusted ingress")
    body = {key: value for key, value in journal.items() if key != "journal_digest"}
    require(digest(body) == journal["journal_digest"] == expected_journal_digest,
            "complete compound journal digest mismatch")
    profile = load_compound_profile() if profile is None else profile
    require(type(profile) is CompoundProfile and canonical_json(journal["source_profile"]) == canonical_json(profile.to_dict()),
            "recovery source profile mismatch")
    episodes = journal["episodes"]
    require(type(episodes) is list and 1 <= len(episodes) <= MAX_EPISODES, "compound episode count invalid")
    require(len(extensions) <= len(episodes) - 1, "ingress extension schedule exceeds episode count")
    machine = CompoundMachine(profile=profile, trusted_ingress=ingress)
    event_count = 0
    for index, episode in enumerate(episodes):
        require(type(episode) is dict and set(episode) == {"problem", "initial_state_hash", "prior_episode_state_hash",
                    "source_profile_digest", "ingress_digest", "trace", "proposal_batches", "final_state"}, "compound episode fields invalid")
        problem = CompoundProblem.from_dict(episode["problem"])
        if index == 0:
            require(canonical_json(problem.to_dict()) == canonical_json(trusted_genesis.to_dict()),
                    "compound genesis differs from trusted problem")
        require(episode["source_profile_digest"] == profile.profile_digest, "episode profile mismatch")
        addition = extensions[index - 1] if 0 < index <= len(extensions) else ()
        machine.start(problem, additional_trusted_ingress=addition)
        coordinator = machine.coordinator
        initial = coordinator.store.snapshot()
        require(initial.state_hash == episode["initial_state_hash"]
                and initial.prior_episode_state_hash == episode["prior_episode_state_hash"]
                and initial.ingress_digest == episode["ingress_digest"],
                "compound episode genesis/handoff mismatch")
        require(type(episode["trace"]) is list, "compound trace must be a list")
        require(type(episode["proposal_batches"]) is list
                and len(episode["proposal_batches"]) == len(episode["trace"]),
                "compound proposal batches must align with trace")
        event_count += len(episode["trace"])
        require(event_count <= MAX_JOURNAL_EVENTS, "compound journal event bound exceeded")
        for event_index, wire in enumerate(episode["trace"]):
            require(type(wire) is dict, "compound trace event malformed")
            require(type(wire.get("proposed_intents")) is list and len(wire["proposed_intents"]) <= 8,
                    "compound trace intent count invalid")
            require(type(wire.get("enabled_components")) is list and type(wire.get("scheduled_components")) is list
                    and len(wire["enabled_components"]) <= 32 and len(wire["scheduled_components"]) <= 32,
                    "compound trace component bounds invalid")
            intents = _decode_proposal_batch(episode["proposal_batches"][event_index])
            outcome = coordinator.execute(enabled_components=wire["enabled_components"],
                scheduled_components=wire["scheduled_components"], intents=intents)
            require(canonical_json(outcome.trace_event.to_dict()) == canonical_json(wire),
                    "compound transition does not reproduce saved event")
            require(canonical_json(coordinator.proposal_batches[-1])
                    == canonical_json(episode["proposal_batches"][event_index]),
                    "compound proposal normalization does not reconstruct")
        # Structural validation is additional evidence only: this parsed object
        # never enters a StateStore and never installs its supplied procedure.
        CompoundState.from_dict(episode["final_state"])
        require(canonical_json(coordinator.store.snapshot().to_dict()) == canonical_json(episode["final_state"]),
                "compound final state does not reconstruct")
    require(canonical_json(machine.journal()) == canonical_json(journal), "compound complete journal does not reconstruct")
    return machine


def save_compound_journal(machine, path):
    """Atomically persist outside the kernel; return the external integrity anchor."""
    journal = machine.journal()
    raw = (canonical_json(journal)+"\n").encode()
    require(len(raw) <= MAX_JOURNAL_BYTES, "compound journal byte bound exceeded")
    destination = Path(path).resolve()
    require(destination.parent.is_dir(), "compound journal destination parent missing")
    descriptor, temporary = tempfile.mkstemp(prefix=".compound-journal-", dir=destination.parent)
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
            "ingress_digest": journal["ingress_digest"],
            "boundary": "Integrity anchor only; external initial ingress and extension schedule remain caller custody."}


def verify_compound_journal(journal, *, trusted_genesis, trusted_ingress,
                            expected_journal_digest, profile=None, trusted_ingress_extensions=()):
    """Return an exact replay receipt; failed replay raises ContractError."""
    machine = recover_compound_journal(journal, trusted_genesis=trusted_genesis,
        expected_journal_digest=expected_journal_digest, profile=profile, trusted_ingress=trusted_ingress,
        trusted_ingress_extensions=trusted_ingress_extensions)
    return {"schema_version": "cncm.compound-replay-receipt/0.5",
        "journal_digest": machine.journal()["journal_digest"],
        "source_profile_digest": machine.profile.profile_digest,
        "ingress_digest": machine.state.ingress_digest,
        "final_state_hash": machine.state.state_hash, "episodes": len(machine.journal()["episodes"]),
        "boundary": "Compound replay under caller-trusted genesis and source profile and external trusted ingress; not principal authentication or world-fact verification."}
