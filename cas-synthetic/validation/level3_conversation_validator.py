"""Validator for Level 3 conversational SDG JSONL records."""

from __future__ import annotations

import importlib
import json
import math
import re
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "id",
    "source_level2_id",
    "bucket",
    "cas_expression",
    "user_prompt",
    "natural_language_mapping",
    "assistant_response",
    "follow_up_question",
    "soft_operator_targets",
    "soft_domain_targets",
    "tags",
    "provenance",
)

STRING_FIELDS = (
    "id",
    "source_level2_id",
    "bucket",
    "cas_expression",
    "user_prompt",
    "natural_language_mapping",
    "assistant_response",
    "follow_up_question",
)

DOMAIN_TARGET_KEYS = {"P", "C", "E", "O"}
OPERATOR_TARGET_COUNT = 10
DOMAIN_TARGET_COUNT = 4
DEFAULT_DISTRIBUTION_TOLERANCE = 1e-3

_BANNED_RESPONSE_PATTERNS = (
    ("diagnose", re.compile(r"\bdiagnos(?:e|es|ed|ing)\b", re.IGNORECASE)),
    ("will happen", re.compile(r"\bwill\s+happen\b", re.IGNORECASE)),
    ("guarantee", re.compile(r"\bguarantee(?:d|s|ing)?\b", re.IGNORECASE)),
)

_QUOTE_PAIRS = {
    "'": "'",
    '"': '"',
    "`": "`",
    "\u2018": "\u2019",
    "\u201c": "\u201d",
}


class CompilerUnavailableError(RuntimeError):
    """Raised when the CAS notation compiler cannot be imported."""


@dataclass(frozen=True)
class Level3RecordReport:
    """Validation result for a single Level 3 conversational record."""

    errors: list[str] = field(default_factory=list)
    compiler_checked: bool = False

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class Level3Issue:
    """A failed JSONL record with source location and collected errors."""

    index: int
    line_number: int
    record_id: str | None
    errors: list[str]


@dataclass
class Level3ValidationSummary:
    """Aggregate validation counts for a JSONL file or in-memory records."""

    total: int = 0
    valid: int = 0
    invalid: int = 0
    compiler_checked: int = 0
    compiler_skipped: int = 0
    bucket_counts: Counter[str] = field(default_factory=Counter)
    issues: list[Level3Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.invalid == 0


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _load_compile_expression() -> Callable[[str], Any]:
    """Import api.notation.compile_expression when the local API package exists."""

    first_error: ImportError | None = None
    try:
        module = importlib.import_module("api.notation")
    except ImportError as exc:
        first_error = exc
    else:
        compile_expression = getattr(module, "compile_expression", None)
        if callable(compile_expression):
            return compile_expression

    noetic_root = _repo_root() / "noetic-compass-scaffold" / "noetic-compass"
    if noetic_root.exists() and str(noetic_root) not in sys.path:
        sys.path.insert(0, str(noetic_root))

    try:
        module = importlib.import_module("api.notation")
    except ImportError as exc:
        detail = f"{exc}"
        if first_error is not None:
            detail = f"{first_error}; retry with local API path failed: {exc}"
        raise CompilerUnavailableError(
            f"Unable to import api.notation.compile_expression ({detail}). "
            "Use --skip-compiler to run schema/distribution checks only."
        ) from exc

    compile_expression = getattr(module, "compile_expression", None)
    if not callable(compile_expression):
        raise CompilerUnavailableError(
            "api.notation is importable but does not expose compile_expression. "
            "Use --skip-compiler to run schema/distribution checks only."
        )
    return compile_expression


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _blank_quoted_spans(text: str) -> str:
    """Replace quoted spans with spaces so quoted banned text is ignored."""

    chars = list(text)
    i = 0
    while i < len(chars):
        closing = _QUOTE_PAIRS.get(chars[i])
        if closing is None:
            i += 1
            continue
        j = i + 1
        while j < len(chars) and chars[j] != closing:
            j += 1
        if j >= len(chars):
            i += 1
            continue
        for k in range(i, j + 1):
            chars[k] = " "
        i = j + 1
    return "".join(chars)


def _response_safety_errors(response: Any) -> list[str]:
    if not isinstance(response, str):
        return []
    unquoted = _blank_quoted_spans(response)
    errors: list[str] = []
    for label, pattern in _BANNED_RESPONSE_PATTERNS:
        if pattern.search(unquoted):
            errors.append(
                "assistant_response contains banned overclaiming keyword "
                f"{label!r} outside quoted banned-text examples"
            )
    return errors


def _distribution_items(
    field_name: str,
    value: Any,
    expected_sequence_length: int,
    allowed_mapping_keys: set[str] | None = None,
) -> tuple[list[tuple[str, Any]], list[str]]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        items = [(str(key), item_value) for key, item_value in value.items()]
        if not items:
            errors.append(f"{field_name} must not be empty")
        if allowed_mapping_keys is not None:
            unknown = sorted(key for key, _ in items if key not in allowed_mapping_keys)
            if unknown:
                errors.append(
                    f"{field_name} contains unknown keys {unknown}; "
                    f"expected subset of {sorted(allowed_mapping_keys)}"
                )
        else:
            bad_keys = sorted(key for key, _ in items if not key)
            if bad_keys:
                errors.append(f"{field_name} contains empty target keys")
        return items, errors

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = [(str(index), item_value) for index, item_value in enumerate(value)]
        if len(items) != expected_sequence_length:
            errors.append(
                f"{field_name} list must have length {expected_sequence_length}; "
                f"got {len(items)}"
            )
        return items, errors

    errors.append(f"{field_name} must be a dict or list distribution")
    return [], errors


def _sequence_distribution_items(
    field_name: str,
    value: Any,
    expected_sequence_length: int,
) -> tuple[list[tuple[str, Any]], list[str]]:
    if not (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
    ):
        return [], [f"{field_name} must be a list distribution"]
    items = [(str(index), item_value) for index, item_value in enumerate(value)]
    if len(items) != expected_sequence_length:
        return items, [
            f"{field_name} list must have length {expected_sequence_length}; "
            f"got {len(items)}"
        ]
    return items, []


def _distribution_errors(
    field_name: str,
    value: Any,
    expected_sequence_length: int,
    tolerance: float,
    allowed_mapping_keys: set[str] | None = None,
) -> list[str]:
    items, errors = _distribution_items(
        field_name=field_name,
        value=value,
        expected_sequence_length=expected_sequence_length,
        allowed_mapping_keys=allowed_mapping_keys,
    )
    if errors:
        return errors

    total = 0.0
    for key, item_value in items:
        if not _is_finite_number(item_value):
            errors.append(f"{field_name}[{key!r}] must be a finite number")
            continue
        numeric_value = float(item_value)
        if numeric_value < 0.0:
            errors.append(f"{field_name}[{key!r}] must be non-negative")
        if numeric_value > 1.0:
            errors.append(f"{field_name}[{key!r}] must be <= 1.0")
        total += numeric_value

    if not errors and abs(total - 1.0) > tolerance:
        errors.append(
            f"{field_name} must sum to 1.0 within tolerance {tolerance}; "
            f"got {total:.6f}"
        )
    return errors


def _sequence_distribution_errors(
    field_name: str,
    value: Any,
    expected_sequence_length: int,
    tolerance: float,
) -> list[str]:
    items, errors = _sequence_distribution_items(
        field_name=field_name,
        value=value,
        expected_sequence_length=expected_sequence_length,
    )
    if errors:
        return errors

    total = 0.0
    for key, item_value in items:
        if not _is_finite_number(item_value):
            errors.append(f"{field_name}[{key!r}] must be a finite number")
            continue
        numeric_value = float(item_value)
        if numeric_value < 0.0:
            errors.append(f"{field_name}[{key!r}] must be non-negative")
        if numeric_value > 1.0:
            errors.append(f"{field_name}[{key!r}] must be <= 1.0")
        total += numeric_value

    if not errors and abs(total - 1.0) > tolerance:
        errors.append(
            f"{field_name} must sum to 1.0 within tolerance {tolerance}; "
            f"got {total:.6f}"
        )
    return errors


def _compiler_artifact_validity(artifact: Any) -> tuple[bool | None, str | None]:
    if isinstance(artifact, Mapping):
        valid = artifact.get("valid")
        error = artifact.get("error")
    else:
        valid = getattr(artifact, "valid", None)
        error = getattr(artifact, "error", None)
    if valid is None:
        return None, "compiler result did not expose a valid flag"
    return bool(valid), str(error) if error else None


@dataclass
class Level3ConversationValidator:
    """Validate Level 3 conversational SDG records."""

    skip_compiler: bool = False
    compile_expression: Callable[[str], Any] | None = None
    distribution_tolerance: float = DEFAULT_DISTRIBUTION_TOLERANCE

    def __post_init__(self) -> None:
        if self.skip_compiler:
            self.compile_expression = None
            return
        if self.compile_expression is None:
            self.compile_expression = _load_compile_expression()

    def validate_record(
        self,
        record: dict[str, Any],
    ) -> Level3RecordReport:
        errors: list[str] = []

        missing = [field for field in REQUIRED_FIELDS if field not in record]
        if missing:
            errors.append(f"missing required fields: {missing}")

        for field_name in STRING_FIELDS:
            value = record.get(field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{field_name} must be a non-empty string")

        tags = record.get("tags")
        if not isinstance(tags, list):
            errors.append("tags must be a list of strings")
        else:
            for index, tag in enumerate(tags):
                if not isinstance(tag, str) or not tag.strip():
                    errors.append(f"tags[{index}] must be a non-empty string")

        provenance = record.get("provenance")
        if not isinstance(provenance, dict):
            errors.append("provenance must be a dict")

        errors.extend(
            _sequence_distribution_errors(
                "soft_operator_targets",
                record.get("soft_operator_targets"),
                expected_sequence_length=OPERATOR_TARGET_COUNT,
                tolerance=self.distribution_tolerance,
            )
        )
        errors.extend(
            _distribution_errors(
                "soft_domain_targets",
                record.get("soft_domain_targets"),
                expected_sequence_length=DOMAIN_TARGET_COUNT,
                tolerance=self.distribution_tolerance,
                allowed_mapping_keys=DOMAIN_TARGET_KEYS,
            )
        )
        errors.extend(_response_safety_errors(record.get("assistant_response")))

        compiler_checked = False
        expression = record.get("cas_expression")
        if self.compile_expression is not None and isinstance(expression, str) and expression.strip():
            compiler_checked = True
            try:
                artifact = self.compile_expression(expression)
            except Exception as exc:  # pragma: no cover - defensive wrapper
                errors.append(
                    "cas_expression compiler raised "
                    f"{type(exc).__name__}: {exc}"
                )
            else:
                valid, error = _compiler_artifact_validity(artifact)
                if valid is None:
                    errors.append(f"cas_expression compiler returned invalid artifact: {error}")
                elif not valid:
                    errors.append(
                        "cas_expression failed compiler validation"
                        + (f": {error}" if error else "")
                    )

        return Level3RecordReport(errors=errors, compiler_checked=compiler_checked)

    def validate_records(
        self,
        records: Sequence[dict[str, Any]],
    ) -> Level3ValidationSummary:
        summary = Level3ValidationSummary()
        for index, record in enumerate(records):
            self._add_record_result(
                summary=summary,
                index=index,
                line_number=index + 1,
                record=record,
            )
        return summary

    def validate_jsonl(self, path: str | Path) -> Level3ValidationSummary:
        summary = Level3ValidationSummary()
        with open(path, encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                index = summary.total
                summary.total += 1
                try:
                    record = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    summary.invalid += 1
                    summary.issues.append(
                        Level3Issue(
                            index=index,
                            line_number=line_number,
                            record_id=None,
                            errors=[f"invalid JSON: {exc.msg}"],
                        )
                    )
                    continue
                if not isinstance(record, dict):
                    summary.invalid += 1
                    summary.issues.append(
                        Level3Issue(
                            index=index,
                            line_number=line_number,
                            record_id=None,
                            errors=["record must be a JSON object"],
                        )
                    )
                    continue
                self._add_parsed_record_result(
                    summary=summary,
                    index=index,
                    line_number=line_number,
                    record=record,
                    total_already_counted=True,
                )
        return summary

    def _add_record_result(
        self,
        summary: Level3ValidationSummary,
        index: int,
        line_number: int,
        record: dict[str, Any],
    ) -> None:
        summary.total += 1
        self._add_parsed_record_result(
            summary=summary,
            index=index,
            line_number=line_number,
            record=record,
            total_already_counted=True,
        )

    def _add_parsed_record_result(
        self,
        summary: Level3ValidationSummary,
        index: int,
        line_number: int,
        record: dict[str, Any],
        total_already_counted: bool,
    ) -> None:
        if not total_already_counted:
            summary.total += 1

        bucket = record.get("bucket", "unknown")
        summary.bucket_counts[str(bucket) if bucket is not None else "unknown"] += 1

        report = self.validate_record(record)
        if report.compiler_checked:
            summary.compiler_checked += 1
        elif self.skip_compiler:
            summary.compiler_skipped += 1

        if report.ok:
            summary.valid += 1
        else:
            summary.invalid += 1
            record_id = record.get("id")
            summary.issues.append(
                Level3Issue(
                    index=index,
                    line_number=line_number,
                    record_id=record_id if isinstance(record_id, str) else None,
                    errors=report.errors,
                )
            )
