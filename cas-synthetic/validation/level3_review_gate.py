"""Manual-review quality gate for Level 3 conversational SDG records."""

from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Level3ReviewThresholds:
    """Thresholds for conversational corpus review."""

    min_prompt_unique_ratio: float = 0.25
    min_response_unique_ratio: float = 0.90
    min_bucket_prompt_unique_ratio: float = 0.20
    max_short_prompt_fraction: float = 0.02
    max_short_response_fraction: float = 0.02
    min_prompt_words: int = 6
    min_response_words: int = 12
    require_cas_expression_in_response: bool = True


@dataclass
class Level3ReviewResult:
    """Aggregate review result for a Level 3 conversational corpus."""

    total: int
    metrics: dict[str, Any]
    bucket_metrics: dict[str, dict[str, Any]]
    sample_records: list[dict[str, Any]] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def review_jsonl(
    path: str | Path,
    *,
    thresholds: Level3ReviewThresholds | None = None,
    sample_per_bucket: int = 2,
    seed: int = 42,
) -> Level3ReviewResult:
    """Load a Level 3 JSONL file and run the review gate."""

    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return review_records(
        records,
        thresholds=thresholds,
        sample_per_bucket=sample_per_bucket,
        seed=seed,
    )


def review_records(
    records: Iterable[dict[str, Any]],
    *,
    thresholds: Level3ReviewThresholds | None = None,
    sample_per_bucket: int = 2,
    seed: int = 42,
) -> Level3ReviewResult:
    """Review in-memory Level 3 conversational records."""

    rows = list(records)
    thresholds = thresholds or Level3ReviewThresholds()
    failures: list[str] = []
    warnings: list[str] = []

    total = len(rows)
    if total == 0:
        return Level3ReviewResult(
            total=0,
            metrics={},
            bucket_metrics={},
            failures=["dataset is empty"],
        )

    prompts = [_text(row.get("user_prompt")) for row in rows]
    responses = [_text(row.get("assistant_response")) for row in rows]
    expressions = [_text(row.get("cas_expression")) for row in rows]
    buckets = [_text(row.get("bucket")) or "unknown" for row in rows]

    prompt_unique = len(set(prompts))
    response_unique = len(set(responses))
    prompt_unique_ratio = prompt_unique / total
    response_unique_ratio = response_unique / total
    short_prompt_count = sum(
        1 for prompt in prompts if _word_count(prompt) < thresholds.min_prompt_words
    )
    short_response_count = sum(
        1
        for response in responses
        if _word_count(response) < thresholds.min_response_words
    )
    missing_expression_in_response = sum(
        1
        for expression, response in zip(expressions, responses)
        if expression and expression not in response
    )

    metrics = {
        "total": total,
        "bucket_counts": dict(Counter(buckets)),
        "unique_user_prompts": prompt_unique,
        "prompt_unique_ratio": round(prompt_unique_ratio, 6),
        "unique_assistant_responses": response_unique,
        "response_unique_ratio": round(response_unique_ratio, 6),
        "short_prompt_count": short_prompt_count,
        "short_prompt_fraction": round(short_prompt_count / total, 6),
        "short_response_count": short_response_count,
        "short_response_fraction": round(short_response_count / total, 6),
        "missing_expression_in_response": missing_expression_in_response,
    }

    if prompt_unique_ratio < thresholds.min_prompt_unique_ratio:
        failures.append(
            "prompt uniqueness ratio "
            f"{prompt_unique_ratio:.3f} is below {thresholds.min_prompt_unique_ratio:.3f}"
        )
    if response_unique_ratio < thresholds.min_response_unique_ratio:
        failures.append(
            "assistant response uniqueness ratio "
            f"{response_unique_ratio:.3f} is below {thresholds.min_response_unique_ratio:.3f}"
        )
    if (short_prompt_count / total) > thresholds.max_short_prompt_fraction:
        failures.append(
            "short prompt fraction "
            f"{short_prompt_count / total:.3f} exceeds "
            f"{thresholds.max_short_prompt_fraction:.3f}"
        )
    if (short_response_count / total) > thresholds.max_short_response_fraction:
        failures.append(
            "short response fraction "
            f"{short_response_count / total:.3f} exceeds "
            f"{thresholds.max_short_response_fraction:.3f}"
        )
    if thresholds.require_cas_expression_in_response and missing_expression_in_response:
        failures.append(
            "assistant responses missing exact cas_expression: "
            f"{missing_expression_in_response}"
        )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_text(row.get("bucket")) or "unknown"].append(row)

    bucket_metrics: dict[str, dict[str, Any]] = {}
    for bucket, bucket_rows in sorted(grouped.items()):
        bucket_prompts = [_text(row.get("user_prompt")) for row in bucket_rows]
        bucket_expressions = [_text(row.get("cas_expression")) for row in bucket_rows]
        bucket_prompt_unique = len(set(bucket_prompts))
        bucket_prompt_ratio = bucket_prompt_unique / len(bucket_rows)
        bucket_metrics[bucket] = {
            "total": len(bucket_rows),
            "unique_cas_expressions": len(set(bucket_expressions)),
            "unique_user_prompts": bucket_prompt_unique,
            "prompt_unique_ratio": round(bucket_prompt_ratio, 6),
        }
        if bucket_prompt_ratio < thresholds.min_bucket_prompt_unique_ratio:
            failures.append(
                f"bucket {bucket!r} prompt uniqueness ratio "
                f"{bucket_prompt_ratio:.3f} is below "
                f"{thresholds.min_bucket_prompt_unique_ratio:.3f}"
            )

    if prompt_unique_ratio < 0.35:
        warnings.append(
            "prompt diversity passes the hard gate but remains low enough "
            "to merit manual sample review before training"
        )

    samples = _sample_by_bucket(grouped, sample_per_bucket=sample_per_bucket, seed=seed)
    return Level3ReviewResult(
        total=total,
        metrics=metrics,
        bucket_metrics=bucket_metrics,
        sample_records=samples,
        failures=failures,
        warnings=warnings,
    )


def write_review_markdown(result: Level3ReviewResult, path: str | Path) -> None:
    """Write a compact manual-review report with sampled records."""

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Level 3 Conversational Review",
        "",
        f"Status: {'PASS' if result.ok else 'FAIL'}",
        f"Total records: {result.total}",
        "",
        "## Metrics",
        "",
    ]
    for key, value in result.metrics.items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Bucket Metrics", ""])
    for bucket, metrics in result.bucket_metrics.items():
        lines.append(
            "- "
            f"{bucket}: total={metrics['total']}, "
            f"unique_cas={metrics['unique_cas_expressions']}, "
            f"unique_prompts={metrics['unique_user_prompts']}, "
            f"prompt_ratio={metrics['prompt_unique_ratio']}"
        )

    if result.failures:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result.failures)
    if result.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result.warnings)

    lines.extend(["", "## Samples", ""])
    for row in result.sample_records:
        lines.extend(
            [
                f"### {row.get('bucket', 'unknown')} / {row.get('id', 'unknown')}",
                "",
                f"CAS: `{row.get('cas_expression', '')}`",
                "",
                f"Prompt: {row.get('user_prompt', '')}",
                "",
                f"Response: {row.get('assistant_response', '')}",
                "",
                f"Follow-up: {row.get('follow_up_question', '')}",
                "",
            ]
        )

    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def result_to_jsonable(result: Level3ReviewResult) -> dict[str, Any]:
    """Return a JSON-serializable result object for automation."""

    return {
        "ok": result.ok,
        "total": result.total,
        "metrics": result.metrics,
        "bucket_metrics": result.bucket_metrics,
        "failures": result.failures,
        "warnings": result.warnings,
        "sample_count": len(result.sample_records),
    }


def _sample_by_bucket(
    grouped: dict[str, list[dict[str, Any]]],
    *,
    sample_per_bucket: int,
    seed: int,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    samples: list[dict[str, Any]] = []
    for bucket in sorted(grouped):
        rows = list(grouped[bucket])
        rng.shuffle(rows)
        samples.extend(rows[: max(sample_per_bucket, 0)])
    return samples


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w^]+\b", text))
