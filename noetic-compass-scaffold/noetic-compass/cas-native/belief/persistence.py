"""SQLite persistence for the CAS-as-Belief-Substrate.

Schema (one belief row per claim_key, append-only observations and contradictions):

    beliefs (
        claim_key       TEXT PRIMARY KEY,
        claim_text      TEXT NOT NULL,
        cas_expression  TEXT NOT NULL,
        vibration       REAL NOT NULL,
        rhythm_count    INTEGER NOT NULL,
        rpm_satisfied   INTEGER NOT NULL,        -- 0/1 boolean
        rpm_status      TEXT NOT NULL,           -- JSON
        inversion_clean INTEGER NOT NULL,
        inversion_axes  TEXT NOT NULL,           -- JSON
        inversion_scanner_version TEXT NOT NULL,
        first_seen      TEXT NOT NULL,           -- ISO 8601
        last_reinforced TEXT NOT NULL,
        sources         TEXT NOT NULL,           -- JSON list[str]
        locked          INTEGER NOT NULL
    )

    observations (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_key         TEXT NOT NULL,
        timestamp         TEXT NOT NULL,
        evidence_strength REAL NOT NULL,
        source            TEXT NOT NULL,
        FOREIGN KEY (claim_key) REFERENCES beliefs(claim_key)
    )

    contradictions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_key   TEXT NOT NULL,
        timestamp   TEXT NOT NULL,
        reason      TEXT NOT NULL,
        FOREIGN KEY (claim_key) REFERENCES beliefs(claim_key)
    )

Default DB path is ``~/.cas-native/beliefs.db``. The directory is created on
demand. Tests pass an explicit path to keep state isolated.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .belief import Belief
from .inversion_gate import INVERSION_SCANNER_VERSION
from .vibration import Observation


DEFAULT_DB_PATH = Path.home() / ".cas-native" / "beliefs.db"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


_BELIEFS_DDL = """
CREATE TABLE IF NOT EXISTS beliefs (
    claim_key       TEXT PRIMARY KEY,
    claim_text      TEXT NOT NULL,
    cas_expression  TEXT NOT NULL,
    vibration       REAL NOT NULL,
    rhythm_count    INTEGER NOT NULL,
    rpm_satisfied   INTEGER NOT NULL,
    rpm_status      TEXT NOT NULL,
    inversion_clean INTEGER NOT NULL,
    inversion_axes  TEXT NOT NULL,
    inversion_scanner_version TEXT NOT NULL DEFAULT '',
    first_seen      TEXT NOT NULL,
    last_reinforced TEXT NOT NULL,
    sources         TEXT NOT NULL,
    locked          INTEGER NOT NULL
)
"""

_OBSERVATIONS_DDL = """
CREATE TABLE IF NOT EXISTS observations (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_key         TEXT NOT NULL,
    timestamp         TEXT NOT NULL,
    evidence_strength REAL NOT NULL,
    source            TEXT NOT NULL,
    FOREIGN KEY (claim_key) REFERENCES beliefs(claim_key)
)
"""

_CONTRADICTIONS_DDL = """
CREATE TABLE IF NOT EXISTS contradictions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_key   TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    reason      TEXT NOT NULL,
    FOREIGN KEY (claim_key) REFERENCES beliefs(claim_key)
)
"""

_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_obs_claim ON observations(claim_key)",
    "CREATE INDEX IF NOT EXISTS idx_contra_claim ON contradictions(claim_key)",
    "CREATE INDEX IF NOT EXISTS idx_beliefs_locked ON beliefs(locked)",
)


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


def open_db(path: Path | str | None = None) -> sqlite3.Connection:
    """Open or create the beliefs DB and return a connection.

    Parent directory is created on demand. PRAGMAs: foreign_keys=ON. Row
    factory: ``sqlite3.Row``.
    """
    resolved = Path(path) if path is not None else DEFAULT_DB_PATH
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_BELIEFS_DDL)
    conn.execute(_OBSERVATIONS_DDL)
    conn.execute(_CONTRADICTIONS_DDL)
    belief_columns = {
        str(row[1]) for row in conn.execute("PRAGMA table_info(beliefs)").fetchall()
    }
    if "inversion_scanner_version" not in belief_columns:
        conn.execute(
            "ALTER TABLE beliefs ADD COLUMN "
            "inversion_scanner_version TEXT NOT NULL DEFAULT ''"
        )
    for stmt in _INDEXES:
        conn.execute(stmt)
    conn.commit()


# ---------------------------------------------------------------------------
# Belief CRUD
# ---------------------------------------------------------------------------


def upsert_belief(
    conn: sqlite3.Connection,
    belief: Belief,
    *,
    inversion_scanner_version: str = INVERSION_SCANNER_VERSION,
) -> None:
    """Insert or replace a belief row."""
    conn.execute(
        """
        INSERT OR REPLACE INTO beliefs (
            claim_key, claim_text, cas_expression, vibration, rhythm_count,
            rpm_satisfied, rpm_status, inversion_clean, inversion_axes,
            inversion_scanner_version,
            first_seen, last_reinforced, sources, locked
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            belief.claim_key,
            belief.claim_text,
            belief.cas_expression,
            float(belief.vibration),
            int(belief.rhythm_count),
            1 if belief.rpm_chain_satisfied else 0,
            json.dumps(belief.rpm_chain_status, default=str),
            1 if belief.inversion_scan_clean else 0,
            json.dumps(belief.inversion_scan_axes, default=str),
            inversion_scanner_version,
            belief.first_seen.isoformat(),
            belief.last_reinforced.isoformat(),
            json.dumps(list(belief.sources)),
            1 if belief.locked else 0,
        ),
    )
    conn.commit()


def stale_inversion_claim_keys(
    conn: sqlite3.Connection,
    *,
    scanner_version: str = INVERSION_SCANNER_VERSION,
) -> list[str]:
    """Return rows whose persisted derived scan used another algorithm."""

    rows = conn.execute(
        "SELECT claim_key FROM beliefs "
        "WHERE inversion_scanner_version <> ? ORDER BY claim_key",
        (scanner_version,),
    ).fetchall()
    return [str(row["claim_key"]) for row in rows]


def update_inversion_state_without_commit(
    conn: sqlite3.Connection,
    *,
    claim_key: str,
    clean: bool,
    axes: dict[str, Any],
    locked: bool,
    scanner_version: str = INVERSION_SCANNER_VERSION,
) -> None:
    """Update derived inversion fields inside the caller's transaction."""

    cursor = conn.execute(
        """
        UPDATE beliefs
        SET inversion_clean = ?, inversion_axes = ?,
            inversion_scanner_version = ?, locked = ?
        WHERE claim_key = ?
        """,
        (
            1 if clean else 0,
            json.dumps(axes, default=str),
            scanner_version,
            1 if locked else 0,
            claim_key,
        ),
    )
    if cursor.rowcount != 1:
        raise RuntimeError(f"belief disappeared during inversion migration: {claim_key}")


def inversion_scanner_version_for_claim(
    conn: sqlite3.Connection, claim_key: str
) -> str | None:
    row = conn.execute(
        "SELECT inversion_scanner_version FROM beliefs WHERE claim_key = ?",
        (claim_key,),
    ).fetchone()
    return None if row is None else str(row["inversion_scanner_version"])


def fetch_belief(
    conn: sqlite3.Connection, claim_key: str
) -> Belief | None:
    """Return the belief row for ``claim_key`` or ``None``."""
    row = conn.execute(
        "SELECT * FROM beliefs WHERE claim_key = ?", (claim_key,)
    ).fetchone()
    if row is None:
        return None
    return _row_to_belief(row)


def list_beliefs(
    conn: sqlite3.Connection, *, locked_only: bool = False
) -> list[Belief]:
    """Return all beliefs (optionally only locked) ordered by vibration desc."""
    if locked_only:
        rows = conn.execute(
            "SELECT * FROM beliefs WHERE locked = 1 ORDER BY vibration DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM beliefs ORDER BY vibration DESC"
        ).fetchall()
    return [_row_to_belief(r) for r in rows]


def delete_belief(conn: sqlite3.Connection, claim_key: str) -> None:
    """Remove a belief and all its observations/contradictions."""
    conn.execute("DELETE FROM observations WHERE claim_key = ?", (claim_key,))
    conn.execute(
        "DELETE FROM contradictions WHERE claim_key = ?", (claim_key,)
    )
    conn.execute("DELETE FROM beliefs WHERE claim_key = ?", (claim_key,))
    conn.commit()


def _row_to_belief(row: sqlite3.Row) -> Belief:
    return Belief(
        claim_key=row["claim_key"],
        claim_text=row["claim_text"],
        cas_expression=row["cas_expression"],
        vibration=float(row["vibration"]),
        rhythm_count=int(row["rhythm_count"]),
        rpm_chain_satisfied=bool(row["rpm_satisfied"]),
        rpm_chain_status=json.loads(row["rpm_status"]),
        inversion_scan_clean=bool(row["inversion_clean"]),
        inversion_scan_axes=json.loads(row["inversion_axes"]),
        first_seen=datetime.fromisoformat(row["first_seen"]),
        last_reinforced=datetime.fromisoformat(row["last_reinforced"]),
        sources=list(json.loads(row["sources"])),
        locked=bool(row["locked"]),
    )


# ---------------------------------------------------------------------------
# Observation CRUD
# ---------------------------------------------------------------------------


def insert_observation(
    conn: sqlite3.Connection,
    claim_key: str,
    timestamp: datetime,
    evidence_strength: float,
    source: str,
) -> int:
    """Insert a new observation; return its row id."""
    cur = conn.execute(
        """
        INSERT INTO observations (claim_key, timestamp, evidence_strength, source)
        VALUES (?, ?, ?, ?)
        """,
        (claim_key, timestamp.isoformat(), float(evidence_strength), source),
    )
    conn.commit()
    return int(cur.lastrowid)


def fetch_observations(
    conn: sqlite3.Connection, claim_key: str
) -> list[Observation]:
    """Return all observations for a claim, oldest first."""
    rows = conn.execute(
        """
        SELECT timestamp, evidence_strength FROM observations
        WHERE claim_key = ? ORDER BY timestamp ASC
        """,
        (claim_key,),
    ).fetchall()
    return [
        Observation(
            timestamp=datetime.fromisoformat(r["timestamp"]),
            evidence_strength=float(r["evidence_strength"]),
        )
        for r in rows
    ]


def count_observations(conn: sqlite3.Connection, claim_key: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM observations WHERE claim_key = ?",
        (claim_key,),
    ).fetchone()
    return int(row["c"]) if row is not None else 0


# ---------------------------------------------------------------------------
# Contradiction CRUD
# ---------------------------------------------------------------------------


def insert_contradiction(
    conn: sqlite3.Connection,
    claim_key: str,
    timestamp: datetime,
    reason: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO contradictions (claim_key, timestamp, reason)
        VALUES (?, ?, ?)
        """,
        (claim_key, timestamp.isoformat(), reason),
    )
    conn.commit()
    return int(cur.lastrowid)


def fetch_contradictions(
    conn: sqlite3.Connection, claim_key: str
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT timestamp, reason FROM contradictions
        WHERE claim_key = ? ORDER BY timestamp ASC
        """,
        (claim_key,),
    ).fetchall()
    return [
        {
            "timestamp": datetime.fromisoformat(r["timestamp"]),
            "reason": r["reason"],
        }
        for r in rows
    ]


def count_contradictions(conn: sqlite3.Connection, claim_key: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM contradictions WHERE claim_key = ?",
        (claim_key,),
    ).fetchone()
    return int(row["c"]) if row is not None else 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def all_claim_keys(conn: sqlite3.Connection) -> Iterable[str]:
    """Yield every claim_key in the beliefs table."""
    rows = conn.execute("SELECT claim_key FROM beliefs").fetchall()
    return [r["claim_key"] for r in rows]
