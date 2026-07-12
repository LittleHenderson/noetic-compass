"""End-to-end CAS Harness live-worker audit test.

This drives the FULL hosted open-weight audit for ``EleutherAI/pythia-160m``
through the public API surface (create -> run) and then reads the persisted
side effects directly from the shared stores: the Evidence Packet store and the
append-only harvest corpus. It is the integration counterpart to the unit-level
``test_cas_harness_live_worker_runner.py`` — instead of mocking the runner, it
exercises the real ``run_audit_session`` route handler, the runner, the packet
writer, the harvest capture, and the evidence-gated verdict, as one chain.

It asserts six honesty-load-bearing properties:

  (a) an Evidence Packet was written and is loadable for the run's trace_id;
  (b) a harvest record exists and JOINS the packet on trace_id;
  (c) the audit scope is honestly labelled ``open_weight_live_trace``;
  (d) the proof-chip HONESTY INVARIANT holds (each chip's present/absent state
      matches the underlying packet evidence — NOT hardcoded chip values);
  (e) real-vs-demo provenance is consistent (manifest ``is_real_model`` truthy
      <=> harvest ``model_io_is_demo_fallback`` false);
  (f) the live open-weight path lands at FLAG_FOR_HUMAN_REVIEW, never a
      fabricated ACCEPT, because causal/control proofs are not yet run.

Worker source priority (most-real first; never hard-fails):
  1. A live worker reachable at ``ATLAS_LIVE_WORKER_URL`` (or 127.0.0.1:18080).
     Used as-is — may be real Pythia (is_real_model true) or demo.
  2. A worker started locally in demo mode (``LIVE_TRACE_DEMO_MODE=1``). The
     demo honesty path is asserted (is_real_model false => demo fallback true).
  3. An in-process stub of the worker dump (no network). Still drives the real
     runner + harvest + verdict chain; asserts the demo-fallback honesty path.

If the live-run implementation modules are not present on this branch (e.g. a
worktree that predates the live-worker wiring), the whole module SKIPS with a
clear message rather than failing red.

The packet store and harvest corpus are pinned to per-test tmp dirs via env
overrides for hermeticity, and any worker process this test starts is torn down.
"""

from __future__ import annotations

import contextlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterator
from urllib.error import URLError
from urllib.request import urlopen

import pytest


# --- Guard: skip cleanly if the live-run implementation is not on this branch.
# The E2E test must PASS where the live worker wiring exists and cleanly SKIP
# where it does not. Importing the runner + harvest + verdict modules up front
# turns "branch lacks the feature" into a single, well-labelled skip instead of
# a collection error.
pytest.importorskip(
    "api.services.cas_harness_live_worker_runner",
    reason="live-worker runner not present on this branch - E2E skipped",
)
pytest.importorskip(
    "api.services.cas_harness_harvest",
    reason="harvest capture not present on this branch - E2E skipped",
)

from api.services.cas_harness_harvest import (  # noqa: E402
    iter_harvest_records,
)
from api.services.cas_harness_live_worker_runner import (  # noqa: E402
    HOSTED_OPEN_WEIGHT_MODEL_IDS,
)
from api.services.cas_harness_audit_sessions import (  # noqa: E402
    reset_audit_sessions_for_tests,
)
from api.services.cas_harness_merged_evidence_packets import (  # noqa: E402
    reset_merged_fleet_evidence_packets_for_tests,
)

# The route under test must also know how to drive the hosted open-weight path.
# If the M1 scaffold route is in place but has no live-worker branch, skip.
import api.routes.cas_harness_audit as _audit_routes  # noqa: E402

if not hasattr(_audit_routes, "run_live_worker_audit"):
    pytest.skip(
        "audit route has no live-worker wiring on this branch — E2E skipped",
        allow_module_level=True,
    )

HOSTED_MODEL_ID = "EleutherAI/pythia-160m"
DEFAULT_WORKER_URL = "http://127.0.0.1:18080"
_DUMP_PATH = "/sessions/dump"


# --------------------------------------------------------------------------- #
# Worker source resolution
# --------------------------------------------------------------------------- #


def _http_get_json(url: str, timeout: float = 2.0) -> dict[str, Any] | None:
    try:
        with urlopen(url, timeout=timeout) as resp:  # noqa: S310 (local health URL)
            if resp.status >= 400:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, OSError, ValueError, TimeoutError):
        return None


def _worker_is_live(base_url: str) -> bool:
    """A worker is 'live' if its health endpoint answers. Real OR demo both ok."""
    base = base_url.rstrip("/")
    for path in ("/health/realmode", "/health"):
        if _http_get_json(f"{base}{path}") is not None:
            return True
    return False


def _free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _worker_app_dir() -> Path | None:
    """Locate the live-trace-worker package dir (holds app/main.py)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "live-trace-worker"
        if (candidate / "app" / "main.py").exists():
            return candidate
    return None


def _wait_for_worker(base_url: str, *, timeout_s: float = 40.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _worker_is_live(base_url):
            return True
        time.sleep(0.5)
    return False


@contextlib.contextmanager
def _local_demo_worker() -> Iterator[str | None]:
    """Start the live-trace worker locally in demo mode; yield its base URL.

    Yields ``None`` if the worker package or uvicorn is not importable, so the
    caller can fall back to the in-process stub instead of hard-failing.
    """
    app_dir = _worker_app_dir()
    if app_dir is None:
        yield None
        return

    port = _free_port()
    env = dict(os.environ)
    env["LIVE_TRACE_DEMO_MODE"] = "1"  # never download weights in a unit test
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(app_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        if not _wait_for_worker(base_url):
            yield None
            return
        yield base_url
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=10)
        if proc.poll() is None:
            proc.kill()
            with contextlib.suppress(Exception):
                proc.wait(timeout=5)


def _stub_worker_dump(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the runner's worker call so the full chain runs with no network.

    The stubbed manifest deliberately omits ``is_real_model``, exercising the
    conservative honesty path: absent/false provenance => demo fallback true.
    """

    async def fake_dump(worker_base: str, payload: dict[str, Any]) -> dict[str, Any]:
        assert payload["model_id"] == HOSTED_MODEL_ID
        return {
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": HOSTED_MODEL_ID,
                        "runtime": "demo_stub",
                        # no is_real_model -> harvest must flag demo fallback
                    },
                },
                {
                    "type": "token",
                    "token_index": 0,
                    "token": " Hello",
                    "confidence": 0.7,
                    "top_activated_neurons": [{"layer": 1, "index": 2, "activation": 0.3}],
                    "mode7_attribution": [],
                },
                {
                    "type": "token",
                    "token_index": 1,
                    "token": " world",
                    "confidence": 0.8,
                    "top_activated_neurons": [],
                    "mode7_attribution": [],
                },
                {
                    "type": "neuron_covers",
                    "per_class_neuron_covers": {"F1": [{"label": "L1N2"}]},
                },
                {"type": "complete", "total_tokens": 2},
            ]
        }

    monkeypatch.setattr(
        "api.services.cas_harness_live_worker_runner._post_worker_dump",
        fake_dump,
    )


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _isolated_stores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Pin the Evidence Packet store and harvest corpus to empty per-test dirs.

    Without this the route would read a developer machine's default temp store
    and the global harvest corpus, so prior runs could leak packets/records and
    flip proof chips or break the single-record harvest assumption.
    """
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_PACKET_STORE_DIR", str(tmp_path / "packets"))
    monkeypatch.setenv("CAS_HARNESS_HARVEST_STORE_DIR", str(tmp_path / "harvest"))
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_MODE", raising=False)
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", raising=False)
    monkeypatch.delenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", raising=False)
    reset_audit_sessions_for_tests()
    reset_merged_fleet_evidence_packets_for_tests()
    yield
    reset_audit_sessions_for_tests()
    reset_merged_fleet_evidence_packets_for_tests()


# --------------------------------------------------------------------------- #
# Honesty-invariant assertions (shared by every worker-source variant)
# --------------------------------------------------------------------------- #


def _assert_live_audit_honesty(*, body: dict[str, Any], trace_id: str) -> None:
    """Assert every non-negotiable honesty property of a completed live audit.

    ``body`` is the JSON of the /run response. ``trace_id`` is its packet id.
    Reads the packet + harvest back from the stores and cross-checks them.
    """
    from api.routes.evidence import _verify_packet_hashes, build_packet_for_trace

    # (a) Evidence Packet was written and is loadable for this trace_id.
    packet = build_packet_for_trace(trace_id)
    assert packet.trace_id == trace_id
    verify = _verify_packet_hashes(packet)
    assert verify.overall == "all_match"

    packet_dict = packet.model_dump() if hasattr(packet, "model_dump") else dict(packet.__dict__)

    # (c) Audit scope is the honest open-weight live-trace label.
    audit_scope = body.get("audit_scope") or {}
    assert audit_scope.get("kind") == "open_weight_live_trace"
    assert audit_scope.get("internal_activation_access") is True
    assert audit_scope.get("verdict_disposition") == "held_for_human_review"

    # (f) Live open-weight path lands at human review, never fabricated ACCEPT.
    assert body["status"] == "COMPLETE"
    assert body["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert body["verdict"] != "ACCEPT"

    # (b) A harvest record exists and JOINS the packet on trace_id.
    harvest_records = [r for r in iter_harvest_records() if r.get("trace_id") == trace_id]
    assert len(harvest_records) == 1, "exactly one harvest record must join this trace"
    harvest = harvest_records[0]
    assert harvest["evidence_packet_trace_id"] == trace_id
    assert harvest["join"] == {"key": "trace_id", "pairs_with": "native_nl.v1"}

    # Derive ground-truth evidence presence FROM the packet (not chip values).
    packet_output = packet_dict.get("output") if isinstance(packet_dict.get("output"), dict) else {}
    output_text = (packet_output or {}).get("text") or ""
    has_output = bool(output_text)

    live_audit = packet_dict.get("live_audit") if isinstance(packet_dict.get("live_audit"), dict) else {}
    event_counts = (live_audit or {}).get("event_counts") or {}
    has_readout_events = bool(event_counts.get("token") or event_counts.get("neuron_covers"))

    ablation = packet_dict.get("ablation") if isinstance(packet_dict.get("ablation"), dict) else {}
    ablation_status = (ablation or {}).get("status")

    # (d) HONESTY INVARIANT on proof chips: each chip's status reflects the real
    # underlying evidence, asserted as a biconditional — NOT a hardcoded literal.
    # This is forward-compatible: if another workstream legitimately runs the
    # ablation and flips causal_proof to present, the invariant still holds
    # because it is tied to packet.ablation.status, not to "unavailable".
    chips = {c["id"]: c["status"] for c in body["provenance_chips"]}
    PRESENT = {"verified", "present"}

    # causal_proof present  <=>  packet ablation evidence present
    causal_present = chips.get("causal_proof") in PRESENT
    assert causal_present == (ablation_status in {"present", "verified"}), (
        "causal_proof chip must mirror packet.ablation.status"
    )

    # output_proof present  <=>  output text exists
    assert (chips.get("output_proof") in PRESENT) == has_output, (
        "output_proof chip must mirror presence of output text"
    )

    # cas_readout present  <=>  token/readout events exist
    assert (chips.get("cas_readout") in PRESENT) == has_readout_events, (
        "cas_readout chip must mirror presence of token/readout events"
    )

    # (e) Real-vs-demo consistency: manifest is_real_model truthy
    #     <=>  harvest model_io_is_demo_fallback is False.
    model_block = packet_dict.get("model") if isinstance(packet_dict.get("model"), dict) else {}
    manifest = (model_block or {}).get("manifest")
    manifest_is_real = bool(manifest.get("is_real_model")) if isinstance(manifest, dict) else False
    demo_fallback = harvest["model_io_is_demo_fallback"]
    assert demo_fallback == (not manifest_is_real), (
        "harvest demo-fallback flag must be the negation of manifest is_real_model"
    )
    # The harvest's own model.is_real_model echo must agree with the manifest.
    assert bool((harvest.get("model") or {}).get("is_real_model")) == manifest_is_real


def _create_and_run(client: Any, auth_headers: dict[str, str]) -> dict[str, Any]:
    """Drive create -> run through the API surface; return the /run response JSON."""
    created = client.post(
        "/api/cas-harness/audit/session",
        json={
            "model_id": HOSTED_MODEL_ID,
            "audit_mode": "BALANCED",
            "prompt": "Audit this live prompt end to end.",
            "selected_modules": ["active_trace", "confidence_margin"],
        },
        headers=auth_headers,
    )
    assert created.status_code == 200, created.text
    audit_id = created.json()["audit_id"]

    ran = client.post(
        f"/api/cas-harness/audit/session/{audit_id}/run",
        headers=auth_headers,
    )
    assert ran.status_code == 200, ran.text
    return ran.json()


# --------------------------------------------------------------------------- #
# The end-to-end test
# --------------------------------------------------------------------------- #


def test_live_worker_audit_e2e_create_run_packet_harvest(
    client: Any,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full create->run->packet->harvest chain for hosted Pythia-160m.

    Picks the most-real available worker source, drives the audit through the
    API, and asserts the honesty invariant. Never fabricates ACCEPT; never
    hard-fails when no worker is reachable.
    """
    assert HOSTED_MODEL_ID in HOSTED_OPEN_WEIGHT_MODEL_IDS, (
        "test target must be a hosted open-weight model id"
    )

    configured = (
        os.environ.get("ATLAS_LIVE_WORKER_URL")
        or os.environ.get("NC_ATLAS_LIVE_WORKER_URL")
        or ""
    ).strip()

    # ---- Source 1: a live worker already reachable (real OR demo). ---------- #
    live_url = ""
    if configured and _worker_is_live(configured):
        live_url = configured
    elif _worker_is_live(DEFAULT_WORKER_URL):
        live_url = DEFAULT_WORKER_URL

    if live_url:
        monkeypatch.setattr("api.config.settings.atlas_live_worker_url", live_url, raising=False)
        body = _create_and_run(client, auth_headers)
        trace_id = body["evidence_packet_trace_id"]
        assert trace_id, "live run must persist an evidence_packet_trace_id"
        _assert_live_audit_honesty(body=body, trace_id=trace_id)
        return

    # ---- Source 2: start the worker locally in demo mode. ------------------- #
    with _local_demo_worker() as demo_url:
        if demo_url:
            monkeypatch.setattr(
                "api.config.settings.atlas_live_worker_url", demo_url, raising=False
            )
            body = _create_and_run(client, auth_headers)
            trace_id = body["evidence_packet_trace_id"]
            assert trace_id, "demo run must persist an evidence_packet_trace_id"
            _assert_live_audit_honesty(body=body, trace_id=trace_id)
            # Demo mode reports is_real_model False -> the honesty path must
            # have flagged the harvest as demo fallback.
            harvest = next(r for r in iter_harvest_records() if r["trace_id"] == trace_id)
            assert harvest["model_io_is_demo_fallback"] is True
            return

    # ---- Source 3: in-process stub (no network, full real chain). ----------- #
    # Configure a non-empty worker URL so the runner's guard passes, then stub
    # the network call. This still drives the real runner, packet writer,
    # harvest capture, and verdict gate.
    monkeypatch.setattr(
        "api.config.settings.atlas_live_worker_url", "http://worker.e2e.test", raising=False
    )
    monkeypatch.setattr(
        "api.config.settings.atlas_live_worker_token", "e2e-worker-token", raising=False
    )
    _stub_worker_dump(monkeypatch)
    body = _create_and_run(client, auth_headers)
    trace_id = body["evidence_packet_trace_id"]
    assert trace_id, "stubbed run must persist an evidence_packet_trace_id"
    _assert_live_audit_honesty(body=body, trace_id=trace_id)
    # The stub omits is_real_model, so the conservative honesty path applies.
    harvest = next(r for r in iter_harvest_records() if r["trace_id"] == trace_id)
    assert harvest["model_io_is_demo_fallback"] is True
