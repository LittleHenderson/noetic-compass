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
    resp = client.get(f"/evidence/{trace_id}", headers=auth_headers)
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


def test_mode7_persist_evidence_trace_rejects_path_traversal_trace_id(monkeypatch, tmp_path):
    """A trace_id that is not strict UUID4 — including path-traversal
    payloads — must be rejected before any disk write happens.

    Codex audit confirmed ``trace_id="../escape_probe"`` would have written
    outside ``.tmp/traces/``. The UUID4 regex + resolved-path containment
    check both protect against this; this test locks in the rejection.
    """
    from api.routes import mode7 as mode7_route

    monkeypatch.setattr(mode7_route, "_scaffold_root_for_traces", lambda: tmp_path)
    traces_dir = tmp_path / ".tmp" / "traces"

    malicious_ids = [
        "../escape_probe",
        "..\\windows_escape",
        "/etc/passwd",
        "trace_id_with_spaces and slashes/",
        "not-a-uuid",
        "0123456789",
        "",
    ]
    for bad_id in malicious_ids:
        bad_report = {"traceability_v0": {"trace_id": bad_id}}
        result = mode7_route._persist_evidence_trace(bad_report, "ignored")
        assert result is None, f"expected None for trace_id={bad_id!r}"

    # Confirm nothing escaped: tmp_path should contain at most the empty
    # .tmp/traces/ directory; no files anywhere under tmp_path other than
    # the directory itself.
    files_written = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert files_written == [], (
        f"no files should have been written; found {files_written}"
    )
    # The traces directory may or may not have been created depending on
    # ordering — what matters is no file landed inside it (or outside it).
    if traces_dir.exists():
        assert list(traces_dir.iterdir()) == []


def test_mode7_persist_evidence_trace_merges_warnings_into_caveats(monkeypatch, tmp_path):
    """SSE-stream warnings (fallback / synthesis notices) must be preserved
    inside the persisted packet's ``caveats`` list — stakeholders inspecting
    the packet after the stream is over should still see why the model
    chose what it chose.
    """
    import json
    from api.routes import mode7 as mode7_route

    monkeypatch.setattr(mode7_route, "_scaffold_root_for_traces", lambda: tmp_path)

    report, _warnings = mode7_route._build_trace_report("warning test prompt", None)
    trace_id = report["traceability_v0"]["trace_id"]
    warnings = [
        "CAS Native predictor expression did not compile; used deterministic fallback expression.",
        "Synthesis fell back to CO-0^C_{F1}.",
    ]

    result = mode7_route._persist_evidence_trace(report, "warning test prompt", warnings=warnings)
    assert result == trace_id

    written = tmp_path / ".tmp" / "traces" / f"{trace_id}.json"
    assert written.is_file()
    body = json.loads(written.read_text(encoding="utf-8"))
    caveats = body.get("caveats", [])
    # Both warnings must appear, and they must precede any default caveat.
    assert warnings[0] in caveats
    assert warnings[1] in caveats
    # Verify the ordering: warnings come first.
    first_warning_index = caveats.index(warnings[0])
    second_warning_index = caveats.index(warnings[1])
    assert first_warning_index < second_warning_index
    # There must still be at least one default caveat after warnings
    # (sparse-hashes notice OR an upstream confidence caveat).
    assert len(caveats) > len(warnings)


def test_mode7_stream_emits_empty_final_trace_id_when_persistence_fails():
    """When persistence fails (or is skipped), ``_stream_report`` must emit
    an empty ``final_trace_id`` over SSE so the dashboard keeps its
    'Open Example Evidence' fallback instead of claiming a trace_id that
    would 404.
    """
    import asyncio
    import json
    from api.routes import mode7 as mode7_route

    # Minimal report shaped enough to drive _stream_report.
    report = {
        "input_prompt": "smoke",
        "input_cas_expression": "^0^C_{F1}",
        "generated_english": "stub",
        "traceability_v0": {
            "trace_id": "00000000-0000-4000-8000-000000000000",
            "thought_tree": {"nodes": [{"id": "n0", "label": "root"}], "edges": []},
        },
    }

    async def consume() -> list[str]:
        events: list[str] = []
        async for event in mode7_route._stream_report(
            turn_id="t0",
            prompt="smoke",
            report=report,
            warnings=[],
            delay_ms=0,
            persisted_trace_id=None,
        ):
            events.append(event)
        return events

    events = asyncio.run(consume())
    # Find the turn.end event. SSE events are formatted as
    # "event: turn.end\ndata: { ... }\n\n".
    turn_end_event = next(
        (e for e in events if "turn.end" in e or "final_trace_id" in e),
        None,
    )
    assert turn_end_event is not None, "no turn.end event was emitted"
    # Parse data: <json> line.
    data_line = next(
        (line for line in turn_end_event.splitlines() if line.startswith("data:")),
        None,
    )
    assert data_line is not None
    payload = json.loads(data_line[len("data:") :].strip())
    assert payload.get("final_trace_id", "<missing>") == "", (
        f"final_trace_id must be empty when persistence failed; got "
        f"{payload.get('final_trace_id')!r}"
    )
