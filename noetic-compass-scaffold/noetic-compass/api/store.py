"""Assessment store — PostgreSQL with in-memory fallback.

When NC_DATABASE_URL is configured, assessments are persisted to PostgreSQL
via SQLAlchemy async + asyncpg.  When it is not set (tests, local dev without
a database), a simple in-memory dict is used instead.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# In-memory fallback store
# ---------------------------------------------------------------------------

_MAX_PER_KEY = 1000

_memory_store: dict[str, list[dict[str, Any]]] = defaultdict(list)


def _inmemory_save(api_key: str, text: str, response: dict[str, Any]) -> str:
    """Save an assessment to the in-memory store.  Returns the new ID."""
    record_id = str(uuid.uuid4())
    bucket = _memory_store[api_key]
    bucket.append(
        {
            "id": record_id,
            "api_key": api_key,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "text": text,
            "response": response,
        }
    )
    # Enforce per-key cap
    if len(bucket) > _MAX_PER_KEY:
        _memory_store[api_key] = bucket[-_MAX_PER_KEY:]
    return record_id


def _inmemory_get(api_key: str, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    """Retrieve assessments for *api_key* (newest first)."""
    bucket = _memory_store.get(api_key, [])
    # Newest first
    ordered = list(reversed(bucket))
    return ordered[offset : offset + limit]


def _inmemory_clear() -> None:
    """Clear the entire in-memory store (for testing)."""
    _memory_store.clear()


# ---------------------------------------------------------------------------
# Database-backed store (used when DATABASE_URL is available)
# ---------------------------------------------------------------------------

async def _db_save(api_key: str, text: str, response: dict[str, Any]) -> str:
    """Persist an assessment to PostgreSQL.  Returns the new UUID."""
    from api.db import async_session_factory

    from api.models_db import Assessment

    record_id = uuid.uuid4()
    async with async_session_factory() as session:
        assessment = Assessment(
            id=record_id,
            api_key=api_key,
            text=text,
            response=response,
        )
        session.add(assessment)
        await session.commit()
    return str(record_id)


async def _db_get(api_key: str, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    """Retrieve assessments from PostgreSQL (newest first)."""
    from sqlalchemy import select

    from api.db import async_session_factory
    from api.models_db import Assessment

    async with async_session_factory() as session:
        stmt = (
            select(Assessment)
            .where(Assessment.api_key == api_key)
            .order_by(Assessment.timestamp.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "api_key": r.api_key,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "text": r.text,
                "response": r.response,
            }
            for r in rows
        ]


# ---------------------------------------------------------------------------
# Public interface — automatically picks DB vs in-memory
# ---------------------------------------------------------------------------

def _use_db() -> bool:
    """Return True when a database URL is configured."""
    from api.config import settings

    return bool(settings.database_url)


async def save_assessment(api_key: str, text: str, response: dict[str, Any]) -> str:
    """Save an assessment.  Returns the record ID."""
    if _use_db():
        return await _db_save(api_key, text, response)
    return _inmemory_save(api_key, text, response)


async def get_assessments(api_key: str, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    """Retrieve assessments for an API key (newest first)."""
    if _use_db():
        return await _db_get(api_key, limit, offset)
    return _inmemory_get(api_key, limit, offset)


def clear_memory_store() -> None:
    """Clear the in-memory store.  Only affects the fallback store."""
    _inmemory_clear()
