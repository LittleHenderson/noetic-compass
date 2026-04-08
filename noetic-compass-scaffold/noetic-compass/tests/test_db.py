"""Tests for database store and in-memory fallback."""

from __future__ import annotations

import pytest

from api.store import (
    clear_memory_store,
    get_assessments,
    save_assessment,
)


@pytest.fixture(autouse=True)
def _clean_store():
    """Ensure clean in-memory store for every test."""
    clear_memory_store()
    yield
    clear_memory_store()


@pytest.mark.asyncio
async def test_inmemory_fallback():
    """When DATABASE_URL is None, the in-memory store works transparently."""
    from api.config import settings

    assert not settings.database_url, "Tests should run without DATABASE_URL"

    record_id = await save_assessment(
        api_key="test-key",
        text="hello world",
        response={"nccs": {"composite": 75.0}},
    )
    assert isinstance(record_id, str)
    assert len(record_id) == 36  # UUID format


@pytest.mark.asyncio
async def test_save_and_retrieve():
    """Basic round-trip: save an assessment and get it back."""
    await save_assessment(
        api_key="roundtrip-key",
        text="test prompt",
        response={"nccs": {"composite": 82.5, "certification": "Gold"}},
    )

    records = await get_assessments(api_key="roundtrip-key")
    assert len(records) == 1
    assert records[0]["text"] == "test prompt"
    assert records[0]["response"]["nccs"]["composite"] == 82.5


@pytest.mark.asyncio
async def test_multiple_keys_isolated():
    """Assessments for different API keys are isolated."""
    await save_assessment("key-a", "prompt a", {"score": 1})
    await save_assessment("key-b", "prompt b", {"score": 2})

    a_records = await get_assessments("key-a")
    b_records = await get_assessments("key-b")

    assert len(a_records) == 1
    assert len(b_records) == 1
    assert a_records[0]["text"] == "prompt a"
    assert b_records[0]["text"] == "prompt b"


@pytest.mark.asyncio
async def test_newest_first_ordering():
    """get_assessments returns newest records first."""
    await save_assessment("order-key", "first", {"n": 1})
    await save_assessment("order-key", "second", {"n": 2})
    await save_assessment("order-key", "third", {"n": 3})

    records = await get_assessments("order-key")
    assert len(records) == 3
    assert records[0]["text"] == "third"
    assert records[2]["text"] == "first"


@pytest.mark.asyncio
async def test_limit_and_offset():
    """Pagination via limit and offset works correctly."""
    for i in range(5):
        await save_assessment("page-key", f"text-{i}", {"i": i})

    page1 = await get_assessments("page-key", limit=2, offset=0)
    assert len(page1) == 2

    page2 = await get_assessments("page-key", limit=2, offset=2)
    assert len(page2) == 2

    page3 = await get_assessments("page-key", limit=2, offset=4)
    assert len(page3) == 1


def test_health_db_no_database(client):
    """GET /health/db returns 503 when no database is configured."""
    resp = client.get("/health/db")
    assert resp.status_code == 503
    assert resp.json()["database"] == "disconnected"
