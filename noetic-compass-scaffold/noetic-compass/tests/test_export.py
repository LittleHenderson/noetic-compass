"""Tests for GET /assessments/export endpoint."""

from __future__ import annotations

import csv
import io

from api.store import clear_assessments


def test_export_json_empty(client, auth_headers):
    """Empty store returns empty JSON list."""
    clear_assessments()
    resp = client.get("/assessments/export?format=json", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_export_json_after_wrap(client, auth_headers, valid_wrap_payload):
    """After a /wrap call, export returns one record with correct fields."""
    clear_assessments()
    client.post("/wrap", json=valid_wrap_payload, headers=auth_headers)

    resp = client.get("/assessments/export?format=json", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1

    record = data[0]
    assert "timestamp" in record
    assert "composite" in record
    assert "certification" in record
    assert record["text"] == valid_wrap_payload["text"][:200]


def test_export_csv_after_wrap(client, auth_headers, valid_wrap_payload):
    """After a /wrap call, CSV export returns header + 1 data row."""
    clear_assessments()
    client.post("/wrap", json=valid_wrap_payload, headers=auth_headers)

    resp = client.get("/assessments/export?format=csv", headers=auth_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers.get("content-disposition", "")

    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 2  # header + 1 data row


def test_export_csv_columns(client, auth_headers, valid_wrap_payload):
    """CSV header contains all expected columns."""
    clear_assessments()
    client.post("/wrap", json=valid_wrap_payload, headers=auth_headers)

    resp = client.get("/assessments/export?format=csv", headers=auth_headers)
    reader = csv.reader(io.StringIO(resp.text))
    header = next(reader)

    expected = [
        "timestamp",
        "text",
        "composite",
        "certification",
        "operator_profile",
        "domain_coherence",
        "drive_rpm_integrity",
        "pathway_quality",
        "inversion_resistance",
        "social_engineering",
        "co_0", "co_1", "co_2", "co_3", "co_4",
        "co_5", "co_6", "co_7", "co_8", "co_9",
        "domain_P", "domain_C", "domain_E", "domain_O",
        "provider",
        "elapsed_ms",
    ]
    assert header == expected


def test_export_requires_auth(client):
    """Export endpoint requires JWT authentication."""
    resp = client.get("/assessments/export?format=json")
    assert resp.status_code == 401
