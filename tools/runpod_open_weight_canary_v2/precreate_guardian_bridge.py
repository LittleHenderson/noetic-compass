"""Production bridge guardian for the create-once launcher.

Implements the launcher's `PrecreateGuardian` protocol
(`create_provider_launch_receipt.py:200`) with real, durable semantics:

  * `consume_authorization_and_arm_precreate(intent)` — consume the one-time
    authorization (durably, exactly once), take a LIVE pre-arm inventory via
    the bounded RunPod adapter, and return the 22-key
    `cas_runpod_precreate_guardian_receipt.v1` the launcher validates.
  * `bind_exact_pod(context)` — dispatch the GitHub stop-supervisor workflow
    for the exact created Pod, so containment authority exists OUTSIDE this
    process, and durably record the binding.

Why this exists: the offline state machine (`precreate_guardian_offline.py`)
emits `cas_runpod_precreate_guardian_arm.v1` (23 keys), while the launcher's
`_validate_guardian_receipt` demands `cas_runpod_precreate_guardian_receipt.v1`
(22 keys, exact keyset). The two designs were never wired together; this bridge
implements the launcher's contract directly rather than weakening either
validator.

Authority boundary: this module can OBSERVE (inventory via the bounded
adapter), CONSUME an authorization marker on local disk, and DISPATCH the
GitHub stop workflow. It cannot create, delete, start, or stop a Pod itself —
the only provider transport reachable is `RunPodGuardianAdapter`, and the only
mutation that adapter offers (stop) is not invoked here.

One-time semantics: the consumption marker is created with `open(path, "xb")`.
A second consumption of the same key refuses — it never increments a
generation, because the launcher binds `guardian_consumption_generation: 1`
exactly, and "consumed twice" must be a refusal, not a higher number.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

from create_provider_launch_receipt import (
    ArmContext,
    ProtocolFailure,
    build_guardian_receipt,
    canonical_json_bytes,
    sha256_bytes,
)
from precreate_guardian_runpod_adapter import RunPodGuardianAdapter

GUARDIAN_ID = "cas-precreate-bridge:github-supervised:v1"
STOP_WORKFLOW = "runpod-canary-stop-supervisor.yml"
MAX_MARKER_BYTES = 1_000_000


class BridgeGuardian:
    """Durable, authorization-consuming guardian bound to GitHub containment."""

    def __init__(
        self,
        *,
        state_directory: Path,
        repository: str,
        adapter: Any | None = None,
        dispatcher: Callable[[list[str]], int] | None = None,
    ) -> None:
        if not isinstance(repository, str) or repository.count("/") != 1:
            raise ProtocolFailure("BRIDGE_REPOSITORY_INVALID")
        self._state = Path(state_directory)
        self._state.mkdir(parents=True, exist_ok=True)
        self._repository = repository
        self._adapter = adapter if adapter is not None else RunPodGuardianAdapter()
        self._dispatch = dispatcher if dispatcher is not None else _run_gh

    # -- PrecreateGuardian -------------------------------------------------

    def consume_authorization_and_arm_precreate(
        self, intent: Mapping[str, object]
    ) -> bytes:
        consumption_key = sha256_bytes(
            (
                str(intent["authorization_id"])
                + "\n"
                + str(intent["request_body_sha256"])
            ).encode("utf-8")
        )
        marker_path = self._state / f"consumed-{consumption_key}.json"
        marker = canonical_json_bytes(
            {
                "authorization_id": str(intent["authorization_id"]),
                "consumption_key": consumption_key,
                "consumed_at_utc": str(intent["prepared_at_utc"]),
                "guardian_id": GUARDIAN_ID,
                "intent_sha256": str(intent["intent_sha256"]),
                "pod_name": str(intent["pod_name"]),
                "schema_version": "cas_runpod_precreate_bridge_consumption.v1",
            }
        )
        try:
            # Durable one-time consumption. A crash AFTER this point leaves the
            # marker in place, and the authorization stays spent — that is the
            # safe direction: never a second create for the same authorization.
            with open(marker_path, "xb") as handle:
                handle.write(marker)
                handle.flush()
        except FileExistsError:
            raise ProtocolFailure(
                "BRIDGE_AUTHORIZATION_ALREADY_CONSUMED"
            ) from None

        # LIVE inventory through the bounded adapter, taken AFTER the marker so
        # the observation is inside the consumption, never before it.
        pods = self._adapter.list_pods()
        projection: list[dict[str, str]] = []
        for pod in pods:
            pod_id = pod.get("id")
            pod_name = pod.get("name")
            if not isinstance(pod_id, str) or not isinstance(pod_name, str):
                raise ProtocolFailure("BRIDGE_INVENTORY_ENTRY_INVALID")
            projection.append({"id": pod_id, "name": pod_name})
        return build_guardian_receipt(
            intent,
            guardian_id=GUARDIAN_ID,
            pre_arm_inventory=projection,
        )

    def bind_exact_pod(self, context: ArmContext) -> None:
        binding_path = self._state / f"binding-{context.pod_id}.json"
        binding = canonical_json_bytes(
            {
                "authorization_id": context.authorization_id,
                "guardian_id": GUARDIAN_ID,
                "hard_stop_deadline_utc": context.hard_stop_deadline_utc,
                "pod_id": context.pod_id,
                "pod_name": context.pod_name,
                "provider_receipt_sha256": context.provider_receipt_sha256,
                "provider_started_at_utc": context.provider_started_at_utc,
                "schema_version": "cas_runpod_precreate_bridge_binding.v1",
                "source_commit_sha256": context.source_commit_sha256,
                "stop_workflow": STOP_WORKFLOW,
                "stop_workflow_repository": self._repository,
            }
        )
        try:
            with open(binding_path, "xb") as handle:
                handle.write(binding)
                handle.flush()
        except FileExistsError:
            raise ProtocolFailure("BRIDGE_POD_ALREADY_BOUND") from None

        # Arm the EXTERNAL containment: dispatch the GitHub stop supervisor for
        # this exact Pod. If the dispatch fails, the bind fails — the launcher
        # then fail-stops the Pod itself, which is the correct outcome when no
        # independent stop authority could be armed.
        returncode = self._dispatch(
            [
                "gh",
                "workflow",
                "run",
                STOP_WORKFLOW,
                "--repo",
                self._repository,
                "--field",
                f"pod_id={context.pod_id}",
                "--field",
                f"pod_name={context.pod_name}",
                "--field",
                f"hard_stop_deadline_utc={context.hard_stop_deadline_utc}",
                "--field",
                f"provider_started_at_utc={context.provider_started_at_utc}",
                "--field",
                f"source_commit={context.source_commit_sha256}",
            ]
        )
        if returncode != 0:
            raise ProtocolFailure("BRIDGE_GITHUB_STOP_DISPATCH_FAILED")


def _run_gh(argv: list[str]) -> int:
    """Run gh without a shell; stdout/stderr are inherited, never parsed."""
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            argv, check=False, timeout=120
        )
    except Exception:
        return 1
    return int(completed.returncode)
