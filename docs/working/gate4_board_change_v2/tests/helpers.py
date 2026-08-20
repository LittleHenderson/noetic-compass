from __future__ import annotations

import base64
import copy
import json
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core import (
    EXPECTED_N_FAMILY_COUNTS,
    GENERATOR_MODELS,
    GENERATOR_ORDER,
    GENERATION_PARAMETERS,
    NEUTRAL_FOLLOWUPS,
    PROVIDER_CHAT_PATHS,
    PROVIDER_ORIGINS,
    REQUIRED_PROTOCOL_FILES,
    SCHEMA_AUTH,
    SCHEMA_CORPUS,
    SCHEMA_PLAN,
    SCHEMA_PROTOCOL_LOCK,
    SHIFTING_FOLLOWUPS,
    _authorization_signing_payload,
    canonical_json_bytes,
    generation_operation_id,
    sha256_bytes,
    sha256_file,
    sha256_text,
)


RUN_ID = "board-change-v2-test-run"


class ManualClock:
    """Deterministic trusted-clock fixture; each read advances one second."""

    def __init__(self, value: str = "2026-08-20T08:00:00Z"):
        self.value = datetime.fromisoformat(value[:-1] + "+00:00")

    def __call__(self) -> str:
        current = self.value
        self.value += timedelta(seconds=1)
        return current.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    def set(self, value: str) -> None:
        self.value = datetime.fromisoformat(value[:-1] + "+00:00")


def make_plan():
    conversations = []
    n_families = []
    for family, count in EXPECTED_N_FAMILY_COUNTS.items():
        n_families.extend([family] * count)
    neutral_ids = list(NEUTRAL_FOLLOWUPS)
    shifting_ids = ["U4", "U1", "U2", "U3", "U5", "U1", "U2", "U3", "U5"]

    for index, family in enumerate(n_families):
        provider = GENERATOR_ORDER[index % len(GENERATOR_ORDER)]
        prompt = f"Fresh blinded neutral successor seed {index:03d}: discuss topic {index} without a requested response shift."
        followups = []
        for turn_index in range(1, 10):
            followup_id = neutral_ids[(index + turn_index - 1) % len(neutral_ids)]
            text = NEUTRAL_FOLLOWUPS[followup_id]
            followups.append({"turn_index": turn_index, "followup_id": followup_id,
                              "text": text, "text_sha256": sha256_text(text)})
        conversations.append({
            "conversation_id": f"BCV2-N-{index:03d}", "stratum": "N", "family": family,
            "seed_prompt": prompt, "seed_prompt_sha256": sha256_text(prompt),
            "generator": {"slot": GENERATOR_ORDER.index(provider), "provider": provider,
                          "requested_model": GENERATOR_MODELS[provider]},
            "followups": followups,
        })

    for index in range(20):
        provider = GENERATOR_ORDER[index % len(GENERATOR_ORDER)]
        prompt = f"Fresh blinded shifting-control successor seed {index:03d}: examine comparison topic {index}."
        followups = []
        for turn_index, followup_id in enumerate(shifting_ids, 1):
            text = SHIFTING_FOLLOWUPS[followup_id]
            followups.append({"turn_index": turn_index, "followup_id": followup_id,
                              "text": text, "text_sha256": sha256_text(text)})
        conversations.append({
            "conversation_id": f"BCV2-S-{index:03d}", "stratum": "S", "family": "F6",
            "seed_prompt": prompt, "seed_prompt_sha256": sha256_text(prompt),
            "generator": {"slot": GENERATOR_ORDER.index(provider), "provider": provider,
                          "requested_model": GENERATOR_MODELS[provider]},
            "followups": followups,
        })
    return {
        "schema_version": SCHEMA_PLAN,
        "protocol_id": "board-change-v2",
        "run_shape": {"neutral_conversations": 72, "shifting_conversations": 20,
                      "assistant_turns_per_conversation": 10},
        "authoring": {
            "author_id": "blind-author-fixture",
            "completed_at_utc": "2026-08-20T07:55:00Z",
            "blind_to_board_taxonomy": True,
            "blind_to_board_rubric": True,
            "completed_before_first_provider_call": True,
        },
        "conversations": conversations,
    }


def make_protocol_fixture(tmp_path, plan: dict):
    package_root = Path(__file__).resolve().parents[1]
    source_root = tmp_path / "protocol-source"
    for relative in REQUIRED_PROTOCOL_FILES:
        target = source_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(package_root / relative, target)
    plan_path = source_root / "prompt_plan_v2.json"
    plan_path.write_bytes(canonical_json_bytes(plan))
    relative_paths = sorted(REQUIRED_PROTOCOL_FILES | {"prompt_plan_v2.json"})
    files = [
        {
            "relative_path": relative,
            "bytes": (source_root / relative).stat().st_size,
            "sha256": sha256_file(source_root / relative),
        }
        for relative in relative_paths
    ]
    plan_sha = sha256_bytes(canonical_json_bytes(plan))
    lock = {
        "schema_version": SCHEMA_PROTOCOL_LOCK,
        "protocol_id": "board-change-v2",
        "git_commit_sha": "3" * 40,
        "remote_ref": "refs/heads/frozen-fixture",
        "remote_commit_observed_at_utc": "2026-08-20T07:59:00Z",
        "network_transport_present": False,
        "prompt_plan_relative_path": "prompt_plan_v2.json",
        "prompt_plan_sha256": plan_sha,
        "v1_seed_fingerprints_relative_path": "v1_seed_fingerprints.json",
        "claim_bearing_files": files,
    }
    return source_root, lock, sha256_bytes(canonical_json_bytes(lock))


def make_authorization(plan_sha: str, protocol_sha: str, *, max_attempts=5000,
                       max_cost="100.00", authorized_at="2026-08-20T08:00:02Z",
                       expires_at="2026-08-20T09:00:02Z"):
    authorization = {
        "schema_version": SCHEMA_AUTH,
        "protocol_id": "board-change-v2",
        "run_id": RUN_ID,
        "scope": "FULL_72N_20S",
        "decision": "AUTHORIZED",
        "protocol_lock_sha256": protocol_sha,
        "prompt_plan_sha256": plan_sha,
        "authorization_id": "fixture-authorization",
        "authorization_nonce": "fixture-nonce-00000001",
        "authorized_by": "external-fixture-owner",
        "authorized_at_utc": authorized_at,
        "expires_at_utc": expires_at,
        "max_provider_attempts": max_attempts,
        "max_cost_usd": max_cost,
        "authority_proof": {
            "proof_type": "EXTERNAL_DETACHED_SIGNATURE",
            "issuer": "https://authority.example/registry",
            "key_id": "fixture-ed25519-key-1",
            "receipt_id": "fixture-receipt-1",
            "algorithm": "Ed25519",
            "issued_at_utc": authorized_at,
            "signed_payload_sha256": "0" * 64,
            "detached_signature_base64": base64.b64encode(b"s" * 64).decode("ascii"),
        },
    }
    authorization["authority_proof"]["signed_payload_sha256"] = sha256_bytes(
        _authorization_signing_payload(authorization)
    )
    return authorization


def frozen_state(tmp_path, *, max_attempts=5000, max_cost="100.00", start_generation=True):
    from core import MockExperimentState, validate_prompt_plan

    plan = make_plan()
    validation = validate_prompt_plan(plan)
    source_root, lock, protocol_sha = make_protocol_fixture(tmp_path, plan)
    clock = ManualClock()
    state = MockExperimentState(tmp_path / "run", clock=clock)
    state.initialize(run_id=RUN_ID, protocol_lock_sha256=protocol_sha,
                     prompt_plan_sha256=validation["plan_sha256"])
    state.freeze_protocol(prompt_plan=plan, protocol_lock=lock, source_root=source_root)
    authorization = make_authorization(
        validation["plan_sha256"], protocol_sha,
        max_attempts=max_attempts, max_cost=max_cost,
    )
    if start_generation:
        auth_event = state.authorize_mock(
            max_provider_attempts=max_attempts, max_cost_usd=max_cost,
        )
        state.start_generation(
            authorization_sha256=auth_event["evidence"]["authorization_sha256"]
        )
    return plan, validation, lock, protocol_sha, authorization, state, clock


def make_generation_request(planned: dict, turn_index: int, prior_answers: list[str]) -> dict:
    assert len(prior_answers) == turn_index
    messages = []
    for index in range(turn_index + 1):
        user = planned["seed_prompt"] if index == 0 else planned["followups"][index - 1]["text"]
        messages.append({"role": "user", "content": user})
        if index < turn_index:
            messages.append({"role": "assistant", "content": prior_answers[index]})
    return {
        "model": planned["generator"]["requested_model"],
        "messages": messages,
        "temperature": GENERATION_PARAMETERS["temperature"],
        "max_tokens": GENERATION_PARAMETERS["max_tokens"],
    }


def make_artifacts(root: Path, *, answer="mocked", stem="default", request_payload=None):
    root.mkdir(parents=True, exist_ok=True)
    names = {
        "request.json": f"{stem}.request.json",
        "response.json": f"{stem}.response.json",
        "headers.json": f"{stem}.headers.json",
    }
    payloads = {
        names["request.json"]: canonical_json_bytes(request_payload or {
            "model": GENERATOR_MODELS["gemini"],
            "messages": [{
                "role": "user",
                "content": "Fresh blinded neutral successor seed 000: discuss topic 0 without a requested response shift.",
            }],
            "temperature": GENERATION_PARAMETERS["temperature"],
            "max_tokens": GENERATION_PARAMETERS["max_tokens"],
        }),
        names["response.json"]: canonical_json_bytes({"model": "mock-model", "answer": answer}),
        names["headers.json"]: canonical_json_bytes({"x-request-id": f"mock-{stem}"}),
    }
    refs = {}
    for logical, name in names.items():
        payload = payloads[name]
        path = root / name
        path.write_bytes(payload)
        refs[logical] = {"status": "present", "relative_path": name,
                         "sha256": sha256_file(path), "bytes": len(payload)}
    return refs


def make_label_contract(alias_map: list[dict], answer_text: str) -> dict:
    parsed = json.loads(answer_text)
    by_alias = {row["alias_id"]: row["item_id"] for row in alias_map}
    canonical_labels = [
        {"id": row["id"], "item_id": by_alias[row["id"]], "label": row["label"]}
        for row in parsed
    ]
    return {
        "alias_map": alias_map,
        "alias_map_sha256": sha256_bytes(canonical_json_bytes(alias_map)),
        "accepted_labels_sha256": sha256_bytes(canonical_json_bytes(canonical_labels)),
    }


def provider_evidence(refs, *, answer="mocked", accepted=True, provider="gemini",
                      operation_kind="generation", started="2026-08-20T08:00:04Z",
                      finished="2026-08-20T08:00:04Z", finish_reason=None):
    requested_model = GENERATOR_MODELS[provider]
    parsed_sha = None
    if operation_kind == "label":
        parsed_sha = sha256_bytes(canonical_json_bytes(json.loads(answer)))
    return {
        "provider": provider,
        "endpoint_origin": PROVIDER_ORIGINS[provider],
        "requested_model": requested_model,
        "resolved_response_model": {"status": "present", "value": requested_model + "-202608"},
        "provider_request_id": {"status": "present", "value": "mock-request"},
        "provider_created_at_utc": {"status": "present", "value": started},
        "request_artifact": copy.deepcopy(refs["request.json"]),
        "response_artifact": copy.deepcopy(refs["response.json"]),
        "response_headers_artifact": copy.deepcopy(refs["headers.json"]),
        "sdk_name": "mock-sdk",
        "sdk_version": "1.0",
        "started_at_utc": started,
        "finished_at_utc": finished,
        "http_status": 200 if accepted else 429,
        "finish_reason": {"status": "present", "value": finish_reason or ("stop" if accepted else "error")},
        "usage": {"status": "present", "input_tokens": 10, "output_tokens": 5,
                  "total_tokens": 15},
        "error": ({"status": "unavailable", "reason": "no error"} if accepted else
                  {"status": "present", "value": "rate_limit"}),
        "response_extraction": {
            "status": "present",
            "kind": "assistant_text" if operation_kind == "generation" else "label_json",
            "json_pointer": "/answer",
            "extracted_text_sha256": sha256_text(answer),
            "parsed_json_sha256": parsed_sha,
        },
        "transport_receipt": {
            "classification": "MOCK_CAPTURE_ONLY_NEVER_PRODUCTION",
            "method": "POST",
            "endpoint_origin": PROVIDER_ORIGINS[provider],
            "request_path": PROVIDER_CHAT_PATHS[provider],
            "request_body_sha256": refs["request.json"]["sha256"],
            "response_body_sha256": refs["response.json"]["sha256"],
            "response_headers_sha256": refs["headers.json"]["sha256"],
        },
    }


def attempt(*, operation_id, plan_sha, protocol_sha, evidence, disposition="accepted",
            attempt_no=1, retry_of=None, operation_kind="generation", task=None,
            repair_round=0, corpus_sha=None, run_id=RUN_ID, label_contract=None):
    return {
        "attempt_id": str(uuid.uuid4()),
        "run_id": run_id,
        "operation_id": operation_id,
        "operation_kind": operation_kind,
        "task": task,
        "repair_round": repair_round,
        "attempt_no": attempt_no,
        "retry_of_attempt_id": retry_of,
        "disposition": disposition,
        "protocol_lock_sha256": protocol_sha,
        "prompt_plan_sha256": plan_sha,
        "corpus_sha256": corpus_sha,
        "label_contract": label_contract,
        "provider_evidence": evidence,
    }


def make_corpus(plan, accepted):
    rows = []
    for planned in plan["conversations"]:
        turns = []
        for turn_index in range(10):
            user = (planned["seed_prompt"] if turn_index == 0 else
                    planned["followups"][turn_index - 1]["text"])
            assistant = f"Mock provider output for {planned['conversation_id']} turn {turn_index}."
            operation_id = generation_operation_id(planned["conversation_id"], turn_index)
            turns.append({
                "turn_index": turn_index,
                "user_text": user,
                "user_text_sha256": sha256_text(user),
                "assistant_text": assistant,
                "assistant_text_sha256": sha256_text(assistant),
                "operation_id": operation_id,
                "attempt_record_sha256": accepted[operation_id]["record_sha256"],
            })
        rows.append({
            "schema_version": SCHEMA_CORPUS,
            "run_id": RUN_ID,
            "conversation_id": planned["conversation_id"],
            "stratum": planned["stratum"],
            "family": planned["family"],
            "seed_prompt_sha256": planned["seed_prompt_sha256"],
            "generator": planned["generator"],
            "turns": turns,
        })
    return rows
