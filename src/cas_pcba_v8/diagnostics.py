"""Stable PCBA8 diagnostic catalog and report types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Iterable
import unicodedata

from .boundary import (
    ResearchBoundary,
    fixed_research_boundary,
    require_research_boundary,
)
from .arithmetic import DECIMAL_CONTEXT_SHA256
from .integrity import (
    DRC_PROFILE,
    engine_sha256,
    package_source_sha256,
    require_safe_reference,
    require_sha256,
    sha256_payload,
)
from .model import Board, board_sha256, canonical_board_payload


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class DiagnosticCode(str, Enum):
    INVALID_BOARD_METADATA = "PCBA8-MDL-001"
    DUPLICATE_REFERENCE = "PCBA8-MDL-002"
    UNKNOWN_COMPONENT_KIND = "PCBA8-SEM-001"
    UNRESOLVED_SEMANTICS = "PCBA8-SEM-002"
    UNKNOWN_PARAMETER = "PCBA8-PAR-001"
    MISSING_PARAMETER = "PCBA8-PAR-002"
    INVALID_PARAMETER = "PCBA8-PAR-003"
    UNKNOWN_STATE_BINDING = "PCBA8-STATE-001"
    MISSING_STATE_BINDING = "PCBA8-STATE-002"
    INVALID_STATE_BINDING = "PCBA8-STATE-003"
    BIAS_INCOHERENT = "PCBA8-BIAS-001"
    UNKNOWN_ENDPOINT_OWNER = "PCBA8-NET-001"
    UNKNOWN_PORT = "PCBA8-NET-002"
    INVALID_DRIVER_COUNT = "PCBA8-NET-003"
    MISSING_NET_LOAD = "PCBA8-NET-004"
    SIGNAL_KIND_MISMATCH = "PCBA8-NET-005"
    UNIT_MISMATCH = "PCBA8-NET-006"
    PORT_MULTIPLY_CONNECTED = "PCBA8-NET-007"
    REQUIRED_PORT_UNCONNECTED = "PCBA8-NET-008"
    INVALID_SIGNAL_UNIT_PAIR = "PCBA8-NET-009"
    UNKNOWN_TEST_POINT_NET = "PCBA8-TP-001"
    MISSING_SAFETY_TEST_POINT = "PCBA8-TP-002"
    UNKNOWN_CALIBRATION = "PCBA8-CAL-001"
    INVALID_CALIBRATION = "PCBA8-CAL-002"
    CALIBRATION_UNIT_MISMATCH = "PCBA8-CAL-003"
    MISSING_TEST_POINT_CALIBRATION = "PCBA8-CAL-004"
    SAFETY_TEST_POINT_NOT_MARKED = "PCBA8-TP-003"
    UNDECLARED_FEEDBACK = "PCBA8-FBK-001"
    FEEDBACK_WITHOUT_DELAY = "PCBA8-FBK-002"
    UNSAFE_FEEDBACK_GAIN = "PCBA8-FBK-003"
    INVALID_FEEDBACK_DECLARATION = "PCBA8-FBK-004"
    UNREACHABLE_SAFETY_THRESHOLD = "PCBA8-SAF-001"
    UNSAFE_FUSE_ACTION = "PCBA8-SAF-002"
    UNRESOLVED_SAFETY_ANALYSIS = "PCBA8-SAF-003"
    INVALID_FINITE_TRANSITION = "PCBA8-TKS-001"


_SEVERITY_ORDER = {
    Severity.ERROR: 0,
    Severity.WARNING: 1,
    Severity.INFO: 2,
}

@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: DiagnosticCode
    severity: Severity
    subject: str
    message: str

    def __post_init__(self) -> None:
        if type(self) is not Diagnostic:
            raise TypeError("Diagnostic subclasses are not accepted")
        self.revalidate()

    def revalidate(self) -> None:
        if type(self) is not Diagnostic:
            raise TypeError("diagnostics must use the exact type")
        if type(self.code) is not DiagnosticCode or type(self.severity) is not Severity:
            raise TypeError("diagnostic code and severity must use exact enum types")
        if (
            type(self.subject) is not str
            or not self.subject
            or len(self.subject) > 512
            or not self.subject.isascii()
            or unicodedata.normalize("NFKC", self.subject) != self.subject
            or any(
                unicodedata.category(character).startswith("C")
                for character in self.subject
            )
        ):
            raise ValueError("Diagnostic.subject must be printable canonical ASCII")
        if type(self.message) is not str or not self.message:
            raise TypeError("Diagnostic.message must be a nonempty exact string")
        if any(ord(character) < 32 or ord(character) == 127 for character in self.message):
            raise ValueError("Diagnostic.message cannot contain control characters")

    @property
    def sort_key(self) -> tuple[int, str, str, str]:
        self.revalidate()
        return (_SEVERITY_ORDER[self.severity], self.code.value, self.subject, self.message)

    def to_dict(self) -> dict[str, str]:
        self.revalidate()
        return {
            "code": self.code.value,
            "severity": self.severity.value,
            "subject": self.subject,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class DrcReport:
    board: Board
    board_ref: str
    board_sha256: str
    source_sha256: str
    catalog_sha256: str
    engine_sha256: str
    decimal_context_sha256: str
    drc_sha256: str
    diagnostics: tuple[Diagnostic, ...]
    report_sha256: str
    boundary: ResearchBoundary = field(default_factory=fixed_research_boundary)

    def __post_init__(self) -> None:
        if type(self) is not DrcReport:
            raise TypeError("DrcReport subclasses are not accepted")
        require_research_boundary(self.boundary)
        if type(self.board) is not Board:
            raise TypeError("DrcReport must embed the exact validated Board")
        self.board.revalidate()
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        require_safe_reference(self.board_ref, "DrcReport.board_ref")
        if self.board_ref != self.board.ref or self.board_sha256 != board_sha256(self.board):
            raise ValueError("DrcReport board linkage is stale or tampered")
        if any(type(item) is not Diagnostic for item in self.diagnostics):
            raise TypeError("DrcReport diagnostics must use exact Diagnostic values")
        for item in self.diagnostics:
            item.revalidate()
        keys = tuple(item.sort_key for item in self.diagnostics)
        if keys != tuple(sorted(keys)):
            raise ValueError("DrcReport diagnostics must use deterministic sort order")
        for field_name in (
            "board_sha256",
            "source_sha256",
            "catalog_sha256",
            "engine_sha256",
            "decimal_context_sha256",
            "drc_sha256",
            "report_sha256",
        ):
            require_sha256(getattr(self, field_name), f"DrcReport.{field_name}")
        if not self.verify_identity():
            raise ValueError("DrcReport diagnostic identity is stale or tampered")

    @classmethod
    def create(
        cls,
        *,
        board: Board,
        diagnostics: Iterable[Diagnostic],
        boundary: ResearchBoundary | None = None,
    ) -> "DrcReport":
        from .contracts import component_catalog_sha256

        if cls is not DrcReport:
            raise TypeError("DrcReport subclasses are not accepted")
        if type(board) is not Board:
            raise TypeError("DrcReport.create requires an exact Board")
        board.revalidate()
        board_ref = board.ref
        board_digest = board_sha256(board)
        fixed_boundary = fixed_research_boundary() if boundary is None else boundary
        require_research_boundary(fixed_boundary)
        raw_items = tuple(diagnostics)
        if any(type(item) is not Diagnostic for item in raw_items):
            raise TypeError("DrcReport diagnostics must use exact Diagnostic values")
        for item in raw_items:
            item.revalidate()
        items = tuple(sorted(raw_items, key=lambda item: item.sort_key))
        source_sha = package_source_sha256()
        catalog_sha = component_catalog_sha256()
        engine_sha = engine_sha256(catalog_sha256=catalog_sha)
        drc_sha = sha256_payload(
            {
                "profile": DRC_PROFILE,
                "source_sha256": source_sha,
                "engine_sha256": engine_sha,
                "catalog_sha256": catalog_sha,
                "decimal_context_sha256": DECIMAL_CONTEXT_SHA256,
            }
        )
        digest = _report_sha256(
            board,
            board_ref,
            board_digest,
            source_sha,
            catalog_sha,
            engine_sha,
            DECIMAL_CONTEXT_SHA256,
            drc_sha,
            items,
            fixed_boundary,
        )
        return cls(
            board,
            board_ref,
            board_digest,
            source_sha,
            catalog_sha,
            engine_sha,
            DECIMAL_CONTEXT_SHA256,
            drc_sha,
            items,
            digest,
            fixed_boundary,
        )

    def verify_identity(self) -> bool:
        if type(self) is not DrcReport:
            return False
        require_research_boundary(self.boundary)
        try:
            if type(self.board) is not Board:
                return False
            self.board.revalidate()
            require_safe_reference(self.board_ref, "DrcReport.board_ref")
            for field_name in (
                "board_sha256",
                "source_sha256",
                "catalog_sha256",
                "engine_sha256",
                "decimal_context_sha256",
                "drc_sha256",
                "report_sha256",
            ):
                require_sha256(getattr(self, field_name), f"DrcReport.{field_name}")
            if type(self.diagnostics) is not tuple or any(
                type(item) is not Diagnostic for item in self.diagnostics
            ):
                return False
            for item in self.diagnostics:
                item.revalidate()
            keys = tuple(item.sort_key for item in self.diagnostics)
            if keys != tuple(sorted(keys)):
                return False
        except (TypeError, ValueError):
            return False
        if self.board_ref != self.board.ref or self.board_sha256 != board_sha256(self.board):
            return False
        from .drc import _collect_diagnostics

        expected_diagnostics = _collect_diagnostics(self.board)
        if tuple(item.to_dict() for item in self.diagnostics) != tuple(
            item.to_dict() for item in expected_diagnostics
        ):
            return False
        from .contracts import component_catalog_sha256

        current_source = package_source_sha256()
        current_catalog = component_catalog_sha256()
        current_engine = engine_sha256(catalog_sha256=current_catalog)
        current_drc = sha256_payload(
            {
                "profile": DRC_PROFILE,
                "source_sha256": current_source,
                "engine_sha256": current_engine,
                "catalog_sha256": current_catalog,
                "decimal_context_sha256": DECIMAL_CONTEXT_SHA256,
            }
        )
        if (
            self.source_sha256 != current_source
            or self.catalog_sha256 != current_catalog
            or self.engine_sha256 != current_engine
            or self.decimal_context_sha256 != DECIMAL_CONTEXT_SHA256
            or self.drc_sha256 != current_drc
        ):
            return False
        expected = _report_sha256(
            self.board,
            self.board_ref,
            self.board_sha256,
            self.source_sha256,
            self.catalog_sha256,
            self.engine_sha256,
            self.decimal_context_sha256,
            self.drc_sha256,
            self.diagnostics,
            self.boundary,
        )
        return self.report_sha256 == expected

    @property
    def is_clean(self) -> bool:
        self._require_valid()
        return not any(item.severity is Severity.ERROR for item in self.diagnostics)

    @property
    def error_count(self) -> int:
        self._require_valid()
        return sum(item.severity is Severity.ERROR for item in self.diagnostics)

    @property
    def codes(self) -> tuple[DiagnosticCode, ...]:
        self._require_valid()
        return tuple(item.code for item in self.diagnostics)

    def _require_valid(self) -> None:
        if type(self) is not DrcReport:
            raise TypeError("DrcReport operations require the exact type")
        require_research_boundary(self.boundary)
        if not self.verify_identity():
            raise ValueError("DrcReport identity is stale or tampered")

    def to_dict(self) -> dict[str, object]:
        self._require_valid()
        error_count = sum(
            item.severity is Severity.ERROR for item in self.diagnostics
        )
        return {
            "board_ref": self.board_ref,
            "board_sha256": self.board_sha256,
            "board": canonical_board_payload(self.board),
            "source_sha256": self.source_sha256,
            "catalog_sha256": self.catalog_sha256,
            "engine_sha256": self.engine_sha256,
            "decimal_context_sha256": self.decimal_context_sha256,
            "drc_sha256": self.drc_sha256,
            "is_clean": error_count == 0,
            "error_count": error_count,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "report_sha256": self.report_sha256,
            "boundary": self.boundary.to_dict(),
        }


def _report_sha256(
    board: Board,
    board_ref: str,
    board_sha256: str,
    source_sha256: str,
    catalog_sha256: str,
    engine_sha256_value: str,
    decimal_context_sha256: str,
    drc_sha256: str,
    diagnostics: tuple[Diagnostic, ...],
    boundary: ResearchBoundary,
) -> str:
    payload = {
        "identity_schema": "cas-pcba-v8.drc-report-identity.v3",
        "board_ref": board_ref,
        "board_sha256": board_sha256,
        "board": canonical_board_payload(board),
        "source_sha256": source_sha256,
        "catalog_sha256": catalog_sha256,
        "engine_sha256": engine_sha256_value,
        "decimal_context_sha256": decimal_context_sha256,
        "drc_sha256": drc_sha256,
        "diagnostics": [item.to_dict() for item in diagnostics],
        "boundary": boundary.to_dict(),
    }
    data = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest().upper()
