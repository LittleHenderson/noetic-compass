"""Mode 7 → Evidence Packet persistence integration test.

Confirms that:

1. ``_persist_evidence_trace`` writes a packet-loadable JSON to
   ``.tmp/traces/{trace_id}.json``.
2. The persisted file lives at a path included in
   ``api.routes.evidence._candidate_trace_paths``.
3. ``GET /api/evidence/{trace_id}`` returns 200 (not 404) for the
   persisted trace_id, with the shape consistent with what the dashboard
   drawer renders.

This is the test that makes the "Open Evidence" wiring honest end-to-end:
without it, the dashboard knows a real trace_id but the backend has
nothing to serve.
"""

from __future__ import annotations

from pathlib import Path


def test_mode7_persist_evidence_trace_writes_packet_loadable_json(
    client, auth_headers, tmp_path, monkeypatch
):
    """End-to-end: build a Mode 7 trace report, persist it, fetch the
    evidence packet by trace_id. Must not 404.

    Uses ``monkeypatch`` to redirect ``_scaffold_root_for_traces`` to a
    temp directory so the test does not leave artifacts behind, and to
    also redirect ``_scaffold_root`` in ``api.routes.evidence`` so the
    evidence-side path resolution finds the file we just wrote.
    """
    from api.routes import evidence as evidence_route
    from api.routes import mode7 as mode7_route

    # Redirect Mode 7's write target AND the evidence route's candidate
    # path resolver to the same temp root so the round-trip works in
    # isolation.
    monkeypatch.setattr(mode7_route, "_scaffold_root_for_traces", lambda: tmp_path)
    monkeypatch.setattr(evidence_route, "_scaffold_root", lambda: tmp_path)

    # Build a real Mode 7 trace report.
    report, _warnings = mode7_route._build_trace_report(
        "What's the difference between principled and felt aversion?",
        None,
    )
    assert report.get("traceability_v0", {}).get("trace_id"), (
        "v0 traceability is expected to mint a trace_id"
    )

    # Persist it. Must return the trace_id, must drop a JSON file at the
    # expected path.
    trace_id = mode7_route._persist_evidence_trace(report, "What's the difference?")
    assert trace_id, "persistence helper must return the trace_id on success"

    expected_path = tmp_path / ".tmp" / "traces" / f"{trace_id}.json"
    assert expected_path.is_file(), (
        f"expected packet JSON at {expected_path}, none found"
    )

    # The path the evidence route will look at must include this location.
    candidates = evidence_route._candidate_trace_paths(trace_id)
    assert any(Path(c).resolve() == expected_path.resolve() for c in candidates), (
        "evidence route's candidate paths must include the Mode 7 write target"
    )

    # Hit the evidence route. Must be 200, not 404, with the shape the
    # drawer expects.
    resp = client.get(f"/api/evidence/{trace_id}", headers=auth_headers)
    assert resp.status_code == 200, (
        f"expected 200 from /api/evidence/{trace_id}; got "
        f"{resp.status_code} {resp.text!r}"
    )
    body = resp.json()

    assert body["trace_id"] == trace_id
    assert body["schema_version"] == "evidence_packet.v1"
    # Drawer renders these — must be present and non-empty per SPEC §4.
    assert body["input"]["text"]
    assert body["cas_expression"]["text"]
    assert body["output"]["text"]
    # copy_slot_trace may be empty if no identifiers were copied, but the
    # field must exist as a list.
    assert isinstance(body["copy_slot_trace"], list)
    assert isinstance(body["claim_levels"], list)
    assert isinstance(body["caveats"], list)


def test_mode7_persist_evidence_trace_returns_none_on_missing_trace_id(monkeypatch, tmp_path):
    """If a report somehow lacks ``traceability_v0.trace_id``, persistence
    is a no-op that returns None rather than raising — Mode 7's SSE stream
    must never fail because of evidence-side persistence."""
    from api.routes import mode7 as mode7_route

    monkeypatch.setattr(mode7_route, "_scaffold_root_for_traces", lambda: tmp_path)

    bad_report = {"traceability_v0": {"trace_id": None}}
    assert mode7_route._persist_evidence_trace(bad_report, "ignored") is None

    no_v0 = {}
    assert mode7_route._persist_evidence_trace(no_v0, "ignored") is None
