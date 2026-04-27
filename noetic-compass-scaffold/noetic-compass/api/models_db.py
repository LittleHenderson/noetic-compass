"""SQLAlchemy ORM models for persistent storage."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class Idea(Base):
    """A user-captured idea translated to CAS notation (Idea Atlas, Sprint 1).

    user_id is a string identifier (matches the JWT `sub` claim) since the
    auth layer is JWT-only — there is no separate users table to FK against.
    """

    __tablename__ = "ideas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    cas_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    ast_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("idx_ideas_user_id_created", "user_id", created_at.desc()),
    )

    def __repr__(self) -> str:
        return f"<Idea id={self.id} user_id={self.user_id!r}>"


class Assessment(Base):
    """A single assessment record produced by the /wrap pipeline."""

    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    api_key: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )

    __table_args__ = (
        Index("idx_assessments_api_key_ts", "api_key", timestamp.desc()),
    )

    def __repr__(self) -> str:
        return f"<Assessment id={self.id} api_key={self.api_key!r}>"
