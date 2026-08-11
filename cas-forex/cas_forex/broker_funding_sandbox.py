"""Persistent sandbox for the CAS broker-funding middleware contract.

This service moves no external money. It models a broker-bound account in a
SQLite database so provider idempotency, pending finality, balance evidence,
and crash/restart recovery can be exercised through the real HTTP adapter.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Mapping

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from cas_forex.time_utils import utc_now


REPORT_KIND = "cas_forex_broker_funding_sandbox"
FINAL_STATUSES = frozenset({"paid", "failed", "canceled"})
PENDING_STATUSES = frozenset({"submitted", "pending", "processing", "in_transit"})

CLAIM_BOUNDARY = (
    "This is a local broker-funding contract sandbox. It changes only a SQLite "
    "test balance and never contacts Hugo's Way, a blockchain, a bank, a card "
    "rail, or any external payment provider."
)


class SandboxError(ValueError):
    pass


class SandboxIdempotencyConflict(SandboxError):
    pass


class SandboxMovementNotFound(SandboxError):
    pass


class SandboxMovementRequest(BaseModel):
    account_id: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)
    amount_usd: float = Field(..., gt=0)
    source_id: str | None = None
    destination_id: str | None = None
    idempotency_key: str = Field(..., min_length=1)


class SandboxTransitionRequest(BaseModel):
    status: str = Field(default="paid")
    detail: str = ""


@dataclass(frozen=True)
class BrokerFundingSandboxStore:
    path: Path
    bound_account_id: str
    initial_balance_usd: float = 10_000.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path))
        if not str(self.bound_account_id or "").strip():
            raise SandboxError("bound_account_id is required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def submit(self, request: Mapping[str, Any]) -> dict[str, Any]:
        normalized = _normalize_request(request)
        if normalized["account_id"] != self.bound_account_id:
            raise SandboxError("request account_id does not match the bound sandbox account")
        fingerprint = _request_fingerprint(normalized)
        now = utc_now().isoformat()
        reference = "sbox-" + hashlib.sha256(
            normalized["idempotency_key"].encode("utf-8")
        ).hexdigest()[:24]
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_account(connection)
            existing = connection.execute(
                "SELECT * FROM movements WHERE idempotency_key = ?",
                (normalized["idempotency_key"],),
            ).fetchone()
            if existing is not None:
                if str(existing["request_fingerprint"]) != fingerprint:
                    raise SandboxIdempotencyConflict(
                        "idempotency key was already used for a different movement request"
                    )
                return _movement_payload(existing)
            account = connection.execute(
                "SELECT balance_cents FROM accounts WHERE account_id = ?",
                (self.bound_account_id,),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO movements (
                    reference, idempotency_key, request_fingerprint, account_id,
                    kind, amount_cents, source_id, destination_id, status,
                    before_balance_cents, after_balance_cents,
                    balance_snapshot_reference, detail, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'submitted', ?, NULL, NULL, ?, ?, ?)
                """,
                (
                    reference,
                    normalized["idempotency_key"],
                    fingerprint,
                    self.bound_account_id,
                    normalized["kind"],
                    normalized["amount_cents"],
                    normalized["source_id"],
                    normalized["destination_id"],
                    int(account["balance_cents"]),
                    "Sandbox accepted the movement; settlement is still pending.",
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM movements WHERE reference = ?",
                (reference,),
            ).fetchone()
            return _movement_payload(row)

    def by_reference(self, reference: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM movements WHERE reference = ?",
                (str(reference or "").strip(),),
            ).fetchone()
        if row is None:
            raise SandboxMovementNotFound("movement reference was not found")
        return _movement_payload(row)

    def by_idempotency_key(self, idempotency_key: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM movements WHERE idempotency_key = ?",
                (str(idempotency_key or "").strip(),),
            ).fetchone()
        if row is None:
            raise SandboxMovementNotFound("movement idempotency key was not found")
        return _movement_payload(row)

    def transition(
        self,
        reference: str,
        *,
        status: str,
        detail: str = "",
    ) -> dict[str, Any]:
        target = str(status or "").strip().lower()
        if target not in FINAL_STATUSES | PENDING_STATUSES:
            raise SandboxError("unsupported sandbox movement status")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_account(connection)
            row = connection.execute(
                "SELECT * FROM movements WHERE reference = ?",
                (str(reference or "").strip(),),
            ).fetchone()
            if row is None:
                raise SandboxMovementNotFound("movement reference was not found")
            if str(row["status"]) in FINAL_STATUSES:
                return _movement_payload(row)
            before = int(
                connection.execute(
                    "SELECT balance_cents FROM accounts WHERE account_id = ?",
                    (self.bound_account_id,),
                ).fetchone()["balance_cents"]
            )
            amount = int(row["amount_cents"])
            final_status = target
            after: int | None = None
            snapshot_reference: str | None = None
            movement_detail = str(detail or "").strip()
            if target == "paid":
                if str(row["kind"]) == "deposit":
                    after = before + amount
                elif amount <= before:
                    after = before - amount
                else:
                    final_status = "failed"
                    movement_detail = "Sandbox account has insufficient balance."
                if after is not None:
                    connection.execute(
                        "UPDATE accounts SET balance_cents = ?, updated_at = ? WHERE account_id = ?",
                        (after, utc_now().isoformat(), self.bound_account_id),
                    )
                    snapshot_reference = "sbox-balance-" + hashlib.sha256(
                        f"{row['reference']}|{before}|{after}".encode("utf-8")
                    ).hexdigest()[:20]
            if not movement_detail:
                movement_detail = (
                    "Sandbox movement settled with a durable balance snapshot."
                    if final_status == "paid"
                    else f"Sandbox movement status={final_status}."
                )
            connection.execute(
                """
                UPDATE movements
                SET status = ?, before_balance_cents = ?, after_balance_cents = ?,
                    balance_snapshot_reference = ?, detail = ?, updated_at = ?
                WHERE reference = ?
                """,
                (
                    final_status,
                    before,
                    after,
                    snapshot_reference,
                    movement_detail,
                    utc_now().isoformat(),
                    row["reference"],
                ),
            )
            updated = connection.execute(
                "SELECT * FROM movements WHERE reference = ?",
                (row["reference"],),
            ).fetchone()
            return _movement_payload(updated)

    def account(self) -> dict[str, Any]:
        with self._connect() as connection:
            self._ensure_account(connection)
            row = connection.execute(
                "SELECT * FROM accounts WHERE account_id = ?",
                (self.bound_account_id,),
            ).fetchone()
        return {
            "account_id": row["account_id"],
            "balance_usd": _from_cents(int(row["balance_cents"])),
            "updated_at": row["updated_at"],
            "sandbox_only": True,
        }

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    balance_cents INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS movements (
                    reference TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    request_fingerprint TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    source_id TEXT,
                    destination_id TEXT,
                    status TEXT NOT NULL,
                    before_balance_cents INTEGER,
                    after_balance_cents INTEGER,
                    balance_snapshot_reference TEXT,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
                );
                """
            )
            self._ensure_account(connection)

    def _ensure_account(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT OR IGNORE INTO accounts (account_id, balance_cents, updated_at)
            VALUES (?, ?, ?)
            """,
            (
                self.bound_account_id,
                _to_cents(self.initial_balance_usd),
                utc_now().isoformat(),
            ),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection


def create_broker_funding_sandbox_app(
    *,
    db_path: Path | str,
    bound_account_id: str,
    api_key: str,
    admin_key: str,
    initial_balance_usd: float = 10_000.0,
) -> FastAPI:
    if not str(api_key or "").strip() or not str(admin_key or "").strip():
        raise SandboxError("sandbox API and admin keys are required")
    store = BrokerFundingSandboxStore(
        Path(db_path),
        bound_account_id=str(bound_account_id),
        initial_balance_usd=initial_balance_usd,
    )
    app = FastAPI(title="CAS Broker Funding Sandbox", version="1.0")
    app.state.sandbox_store = store

    def require_api(authorization: str) -> None:
        _require_bearer(authorization, api_key)

    def require_admin(authorization: str) -> None:
        _require_bearer(authorization, admin_key)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "report_kind": REPORT_KIND,
            "status": "SANDBOX_READY",
            "sandbox_only": True,
            "account": store.account(),
            "claim_boundary": CLAIM_BOUNDARY,
        }

    @app.post("/v1/deposits")
    def deposit(
        body: SandboxMovementRequest,
        authorization: str = Header(default=""),
        idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        require_api(authorization)
        if body.kind.strip().lower() != "deposit":
            raise HTTPException(status_code=422, detail="deposit endpoint requires kind=deposit")
        return _submit(store, body, idempotency_key)

    @app.post("/v1/withdrawals")
    def withdrawal(
        body: SandboxMovementRequest,
        authorization: str = Header(default=""),
        idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        require_api(authorization)
        if body.kind.strip().lower() not in {"withdrawal", "payout"}:
            raise HTTPException(
                status_code=422,
                detail="withdrawal endpoint requires kind=withdrawal or payout",
            )
        return _submit(store, body, idempotency_key)

    @app.get("/v1/movements/by-idempotency/{idempotency_key}")
    def movement_by_idempotency(
        idempotency_key: str,
        authorization: str = Header(default=""),
    ) -> dict[str, Any]:
        require_api(authorization)
        try:
            return store.by_idempotency_key(idempotency_key)
        except SandboxMovementNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/v1/movements/{reference}")
    def movement(
        reference: str,
        authorization: str = Header(default=""),
    ) -> dict[str, Any]:
        require_api(authorization)
        try:
            return store.by_reference(reference)
        except SandboxMovementNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/v1/sandbox/movements/{reference}/transition")
    def transition(
        reference: str,
        body: SandboxTransitionRequest,
        authorization: str = Header(default=""),
    ) -> dict[str, Any]:
        require_admin(authorization)
        try:
            return store.transition(reference, status=body.status, detail=body.detail)
        except SandboxMovementNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except SandboxError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


def _submit(
    store: BrokerFundingSandboxStore,
    body: SandboxMovementRequest,
    header_key: str,
) -> dict[str, Any]:
    if not header_key or header_key != body.idempotency_key:
        raise HTTPException(
            status_code=422,
            detail="Idempotency-Key header must match body idempotency_key",
        )
    try:
        return store.submit(body.model_dump())
    except SandboxIdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SandboxError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _require_bearer(authorization: str, expected_key: str) -> None:
    prefix = "Bearer "
    supplied = authorization[len(prefix) :] if authorization.startswith(prefix) else ""
    if not supplied or not secrets.compare_digest(supplied, expected_key):
        raise HTTPException(status_code=401, detail="invalid sandbox bearer token")


def _normalize_request(request: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(request.get("kind") or "").strip().lower()
    if kind not in {"deposit", "withdrawal", "payout"}:
        raise SandboxError("unsupported movement kind")
    account_id = str(request.get("account_id") or "").strip()
    key = str(request.get("idempotency_key") or "").strip()
    if not account_id or not key:
        raise SandboxError("account_id and idempotency_key are required")
    amount_cents = _to_cents(request.get("amount_usd"))
    if amount_cents <= 0:
        raise SandboxError("movement amount must be positive")
    return {
        "account_id": account_id,
        "kind": kind,
        "amount_cents": amount_cents,
        "source_id": _optional_text(request.get("source_id")),
        "destination_id": _optional_text(request.get("destination_id")),
        "idempotency_key": key,
    }


def _request_fingerprint(request: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(request), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _movement_payload(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "report_kind": REPORT_KIND,
        "reference": row["reference"],
        "idempotency_key": row["idempotency_key"],
        "account_id": row["account_id"],
        "kind": row["kind"],
        "amount_usd": _from_cents(int(row["amount_cents"])),
        "source_id": row["source_id"],
        "destination_id": row["destination_id"],
        "status": row["status"],
        "before_balance_usd": (
            _from_cents(int(row["before_balance_cents"]))
            if row["before_balance_cents"] is not None
            else None
        ),
        "after_balance_usd": (
            _from_cents(int(row["after_balance_cents"]))
            if row["after_balance_cents"] is not None
            else None
        ),
        "balance_snapshot_reference": row["balance_snapshot_reference"],
        "detail": row["detail"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "sandbox_only": True,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _to_cents(value: Any) -> int:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(amount * 100)


def _from_cents(value: int) -> float:
    return float(Decimal(value) / Decimal(100))


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
