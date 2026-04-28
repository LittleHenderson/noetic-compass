"""Level 3 conversational wrapper for Level 2 CAS records.

This generator reads existing Level 2 JSONL records and emits deterministic
multi-turn conversational variants. It never calls an external API and always
copies the source ``cas_expression`` exactly.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

import yaml


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "templates"
    / "level3_conversational_templates.yaml"
)

_NOETIC_RE = re.compile(r"\^([0-9])(?![0-9])")
_STATE_DOMAIN_RE = re.compile(r"\^[0-9](?![0-9])\^([PCEO])")
_COORD_DOMAIN_RE = re.compile(
    r"(?:Coordinate\{\s*\^[0-9]\s*,\s*|<\s*\^[0-9]\s*,\s*)([PCEO])\b"
)
_REGISTER_RE = re.compile(r"\|([TAfE])(?![A-Za-z])")
_REGISTER_SET_RE = re.compile(r"\|(?:<|\u27e8)([^>\u27e9]+)(?:>|\u27e9)")
_OMEGA_RE = re.compile(r"(?:Omega|[\u03a9])_[A-Za-z0-9_]+")

_DOMAIN_NAMES = {
    "P": "principled",
    "C": "cognitive",
    "E": "evaluative",
    "O": "operational",
}
_NOETIC_NAMES = {
    0: "open possibility",
    1: "direct attention",
    2: "affinity",
    3: "aversion",
    4: "impression",
    5: "integration",
    6: "analysis",
    7: "entrainment",
    8: "association",
    9: "consequence",
}


@dataclass
class ConversationalExample:
    """One Level 3 conversational training record."""

    id: str
    source_level2_id: str
    bucket: str
    cas_expression: str
    user_prompt: str
    natural_language_mapping: str
    assistant_response: str
    follow_up_question: str
    soft_operator_targets: list[float]
    soft_domain_targets: list[float]
    tags: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return the JSONL-ready target shape."""
        return {
            "id": self.id,
            "source_level2_id": self.source_level2_id,
            "bucket": self.bucket,
            "cas_expression": self.cas_expression,
            "user_prompt": self.user_prompt,
            "natural_language_mapping": self.natural_language_mapping,
            "assistant_response": self.assistant_response,
            "follow_up_question": self.follow_up_question,
            "soft_operator_targets": list(self.soft_operator_targets),
            "soft_domain_targets": list(self.soft_domain_targets),
            "tags": list(self.tags),
            "provenance": dict(self.provenance),
        }


def extract_noetic_counts(cas_expression: str) -> list[int]:
    """Count noetic atoms ``^0`` through ``^9`` in a CAS expression."""
    counts = [0] * 10
    for match in _NOETIC_RE.finditer(cas_expression):
        counts[int(match.group(1))] += 1
    return counts


def extract_domain_counts(cas_expression: str) -> list[int]:
    """Count explicit P/C/E/O domain-axis mentions in a CAS expression."""
    counts = [0] * 4
    domain_index = {"P": 0, "C": 1, "E": 2, "O": 3}
    for match in _STATE_DOMAIN_RE.finditer(cas_expression):
        counts[domain_index[match.group(1)]] += 1
    for match in _COORD_DOMAIN_RE.finditer(cas_expression):
        counts[domain_index[match.group(1)]] += 1
    return counts


def infer_soft_operator_targets(
    cas_expression: str,
    source_scores: dict[str, Any] | None = None,
    smoothing: float = 0.01,
) -> list[float]:
    """Infer a normalized soft target over the 10 noetic operators."""
    del source_scores  # Level 3 targets are inferred from the CAS expression.
    counts = extract_noetic_counts(cas_expression)
    if any(counts):
        return _normalize_soft(counts, smoothing=smoothing)
    return _normalize_soft([0.0] * 10, smoothing=smoothing)


def infer_soft_domain_targets(
    cas_expression: str,
    source_scores: dict[str, Any] | None = None,
    smoothing: float = 0.01,
) -> list[float]:
    """Infer a normalized soft target over domains ordered P/C/E/O."""
    del source_scores  # Domains fall back to uniform when absent from notation.
    counts = extract_domain_counts(cas_expression)
    if any(counts):
        return _normalize_soft(counts, smoothing=smoothing)
    return _normalize_soft([0.0] * 4, smoothing=smoothing)


class Level3ConversationalGenerator:
    """Deterministic wrapper from Level 2 examples to Level 3 conversations."""

    BUCKET = "level3_conversational"
    GENERATOR_VERSION = "level3_conversational_v1"

    def __init__(
        self,
        seed: int = 42,
        template_path: str | Path | None = None,
        variants_per_source: int = 3,
    ) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.variants_per_source = _validate_variants_per_source(variants_per_source)
        path = Path(template_path) if template_path is not None else _TEMPLATE_PATH
        with open(path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        self.templates = loaded
        self.styles = list(loaded.get("styles", []))
        if not self.styles:
            raise RuntimeError(f"No Level 3 conversational styles found in {path}")

    def iter_jsonl(
        self,
        input_path: str | Path,
        *,
        max_source_records: int | None = None,
        variants_per_source: int | None = None,
        include_invalid_sources: bool = False,
    ) -> Iterator[ConversationalExample]:
        """Stream conversational variants from a Level 2 JSONL file."""
        path = Path(input_path)
        max_records = _validate_max_source_records(max_source_records)
        record_count = 0
        with open(path, encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                if max_records is not None and record_count >= max_records:
                    break
                source = json.loads(line)
                if not include_invalid_sources and _source_is_invalid(source):
                    record_count += 1
                    continue
                yield from self.iter_source_record(
                    source,
                    source_index=record_count,
                    source_line=line_number,
                    source_path=path,
                    variants_per_source=variants_per_source,
                )
                record_count += 1

    def iter_source_record(
        self,
        source: dict[str, Any],
        *,
        source_index: int,
        source_line: int | None = None,
        source_path: str | Path | None = None,
        variants_per_source: int | None = None,
    ) -> Iterator[ConversationalExample]:
        """Yield 2-5 conversational variants for a single Level 2 record."""
        variant_count = (
            self.variants_per_source
            if variants_per_source is None
            else _validate_variants_per_source(variants_per_source)
        )
        expression = source.get("cas_expression")
        if not isinstance(expression, str) or not expression:
            raise ValueError(f"source_index={source_index} has no cas_expression")

        style_order = list(self.styles)
        self.rng.shuffle(style_order)
        for variant_index in range(variant_count):
            style = style_order[variant_index % len(style_order)]
            yield self._build_variant(
                source,
                source_index=source_index,
                source_line=source_line,
                source_path=source_path,
                variant_index=variant_index,
                variants_per_source=variant_count,
                style=style,
            )

    def generate_to_jsonl(
        self,
        input_path: str | Path,
        output_path: str | Path,
        *,
        max_source_records: int | None = None,
        variants_per_source: int | None = None,
        progress_every: int = 1000,
        include_invalid_sources: bool = False,
    ) -> dict[str, Any]:
        """Generate a Level 3 JSONL file from a Level 2 JSONL source."""
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        written = 0
        source_indices: set[int] = set()
        source_records_read = 0
        source_records_skipped = 0
        bucket_counts: dict[str, int] = {}
        max_records = _validate_max_source_records(max_source_records)
        with open(input_path, encoding="utf-8") as source_file, open(
            out_path, "w", encoding="utf-8"
        ) as f:
            for line_number, line in enumerate(source_file, start=1):
                line = line.strip()
                if not line:
                    continue
                if max_records is not None and source_records_read >= max_records:
                    break
                source = json.loads(line)
                source_index = source_records_read
                source_records_read += 1
                if not include_invalid_sources and _source_is_invalid(source):
                    source_records_skipped += 1
                    continue
                for ex in self.iter_source_record(
                    source,
                    source_index=source_index,
                    source_line=line_number,
                    source_path=input_path,
                    variants_per_source=variants_per_source,
                ):
                    f.write(json.dumps(ex.to_dict(), ensure_ascii=False) + "\n")
                    written += 1
                    source_indices.add(int(ex.provenance["source_index"]))
                    bucket_counts[ex.bucket] = bucket_counts.get(ex.bucket, 0) + 1
                    if progress_every and written % progress_every == 0:
                        print(f"  wrote {written} Level 3 records")

        return {
            "input_path": str(input_path),
            "output_path": str(out_path),
            "source_records": len(source_indices),
            "source_records_read": source_records_read,
            "source_records_skipped": source_records_skipped,
            "written": written,
            "variants_per_source": (
                self.variants_per_source
                if variants_per_source is None
                else _validate_variants_per_source(variants_per_source)
            ),
            "bucket_counts": bucket_counts,
        }

    def _build_variant(
        self,
        source: dict[str, Any],
        *,
        source_index: int,
        source_line: int | None,
        source_path: str | Path | None,
        variant_index: int,
        variants_per_source: int,
        style: dict[str, Any],
    ) -> ConversationalExample:
        expression = source["cas_expression"]
        source_id = _source_level2_id(source, source_index)
        source_bucket = _source_bucket(source)
        source_prompt = _clean_text(source.get("prompt", ""))
        source_response = _clean_text(source.get("response", ""))

        operator_targets = infer_soft_operator_targets(expression)
        domain_targets = infer_soft_domain_targets(expression)
        feature_summary = _feature_summary(expression)
        focus_summary = _focus_summary(expression)
        style_id = str(style.get("id", f"style_{variant_index}"))

        values = {
            "cas_expression": expression,
            "source_prompt": source_prompt or "No source prompt was supplied.",
            "source_response": source_response or "No source response was supplied.",
            "source_bucket": source_bucket,
            "focus_summary": focus_summary,
            "feature_summary": feature_summary,
            "operator_summary": _target_summary(operator_targets, "noetic"),
            "domain_summary": _target_summary(domain_targets, "domain"),
        }

        record_id = _record_id(
            source_id=source_id,
            expression=expression,
            variant_index=variant_index,
            seed=self.seed,
            style_id=style_id,
        )
        source_meta = source.get("_meta") if isinstance(source.get("_meta"), dict) else {}
        provenance = {
            "level3_spec_version": "0.1.0",
            "generation_method": "deterministic_template",
            "generator": type(self).__name__,
            "generator_version": self.GENERATOR_VERSION,
            "level2_dataset": Path(source_path).name if source_path is not None else "inline",
            "seed": self.seed,
            "source_path": str(source_path) if source_path is not None else None,
            "source_line": source_line,
            "source_index": source_index,
            "source_bucket": source_bucket,
            "source_level2_id": source_id,
            "source_hash": _short_hash(
                json.dumps(source, sort_keys=True, ensure_ascii=False)
            ),
            "level2_row_index": source_index,
            "level2_hash": _short_hash(
                json.dumps(source, sort_keys=True, ensure_ascii=False)
            ),
            "conversation_id": record_id,
            "turn_index": 0,
            "variant_index": variant_index,
            "variants_per_source": variants_per_source,
            "template_id": style_id,
            "source_is_valid": source_meta.get("is_valid"),
            "source_violation_type": source_meta.get("violation_type"),
        }

        return ConversationalExample(
            id=record_id,
            source_level2_id=source_id,
            bucket=source_bucket,
            cas_expression=expression,
            user_prompt=_render(style, "user_prompt_templates", values, self.rng),
            natural_language_mapping=_render(
                style, "natural_language_mapping_templates", values, self.rng
            ),
            assistant_response=_render(
                style, "assistant_response_templates", values, self.rng
            ),
            follow_up_question=_render(
                style, "follow_up_question_templates", values, self.rng
            ),
            soft_operator_targets=operator_targets,
            soft_domain_targets=domain_targets,
            tags=_tags_for(source_bucket, expression, source_meta, style_id),
            provenance=provenance,
        )


def _normalize_soft(values: Sequence[float | int], *, smoothing: float) -> list[float]:
    if smoothing < 0:
        raise ValueError("smoothing must be non-negative")
    raw = [max(float(v), 0.0) + smoothing for v in values]
    total = sum(raw)
    if total <= 0:
        raw = [1.0 for _ in values]
        total = sum(raw)
    normalized = [round(v / total, 6) for v in raw]
    if normalized:
        normalized[-1] = round(normalized[-1] + (1.0 - sum(normalized)), 6)
    return normalized


def _validate_variants_per_source(value: int) -> int:
    if not isinstance(value, int):
        raise TypeError("variants_per_source must be an integer")
    if value < 2 or value > 5:
        raise ValueError("variants_per_source must be between 2 and 5")
    return value


def _validate_max_source_records(value: int | None) -> int | None:
    if value is None:
        return None
    if value < 0:
        raise ValueError("max_source_records must be non-negative")
    return value


def _source_level2_id(source: dict[str, Any], source_index: int) -> str:
    raw_id = source.get("id")
    if raw_id is not None and str(raw_id).strip():
        return str(raw_id)
    return f"level2-{source_index:06d}"


def _source_bucket(source: dict[str, Any]) -> str:
    meta = source.get("_meta")
    if isinstance(meta, dict) and meta.get("bucket"):
        return str(meta["bucket"])
    if source.get("bucket"):
        return str(source["bucket"])
    return "unknown"


def _source_is_invalid(source: dict[str, Any]) -> bool:
    meta = source.get("_meta")
    return isinstance(meta, dict) and meta.get("is_valid") is False


def _record_id(
    *,
    source_id: str,
    expression: str,
    variant_index: int,
    seed: int,
    style_id: str,
) -> str:
    digest = _short_hash(f"{seed}|{source_id}|{variant_index}|{style_id}|{expression}")
    return f"l3conv-{digest}"


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def _render(
    style: dict[str, Any],
    key: str,
    values: dict[str, str],
    rng: random.Random,
) -> str:
    templates = style.get(key)
    if not isinstance(templates, list) or not templates:
        raise RuntimeError(f"template style {style.get('id')!r} has no {key}")
    template = rng.choice(templates)
    return str(template).format_map(_SafeFormat(values))


class _SafeFormat(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _feature_summary(expression: str) -> str:
    parts: list[str] = []
    registers = _registers(expression)
    omegas = sorted(set(_OMEGA_RE.findall(expression)))
    if registers:
        parts.append(f"registers {', '.join(registers)}")
    if omegas:
        parts.append(f"named emergent {', '.join(omegas)}")
    if "->" in expression:
        parts.append("directional relation")
    if "Theta(" in expression or "\u0398(" in expression:
        parts.append("production rule")
    if any(token in expression for token in ("Cluster{", "Product(", "Pullback(", "CoverOf(", "PartitionOf(")):
        parts.append("typed finite meta-logic construct")
    if not parts:
        parts.append("state-level CAS structure")
    return "; ".join(parts)


def _focus_summary(expression: str) -> str:
    noetic_counts = extract_noetic_counts(expression)
    domain_counts = extract_domain_counts(expression)
    noetic_part = _axis_focus(noetic_counts, _NOETIC_NAMES, "Noetic")
    domain_part = _axis_focus(domain_counts, _DOMAIN_NAMES, "domain")
    return f"{noetic_part}; {domain_part}; {_feature_summary(expression)}"


def _axis_focus(
    counts: Sequence[int],
    names: dict[int | str, str],
    label: str,
) -> str:
    if not any(counts):
        return f"no explicit {label.lower()} emphasis"
    top_value = max(counts)
    top_indices = [i for i, count in enumerate(counts) if count == top_value]
    if label == "domain":
        ordered = ["P", "C", "E", "O"]
        described = [
            f"{ordered[i]} ({names[ordered[i]]})"
            for i in top_indices
        ]
    else:
        described = [
            f"^{i} ({names.get(i, 'unspecified')})"
            for i in top_indices
        ]
    if len(described) == 1:
        return f"primary {label.lower()} emphasis on {described[0]}"
    return f"shared {label.lower()} emphasis on {', '.join(described)}"


def _target_summary(targets: Sequence[float], axis: str) -> str:
    if not targets:
        return f"no {axis} target"
    top_index = max(range(len(targets)), key=lambda i: targets[i])
    top_value = targets[top_index]
    if axis == "domain":
        labels = ["P", "C", "E", "O"]
        top_label = labels[top_index]
    else:
        top_label = f"^{top_index}"
    return f"{top_label} at {top_value:.3f}"


def _registers(expression: str) -> list[str]:
    found: list[str] = []
    for match in _REGISTER_RE.finditer(expression):
        found.append(match.group(1))
    for match in _REGISTER_SET_RE.finditer(expression):
        for item in match.group(1).split(","):
            register = item.strip()
            if register in {"T", "A", "f", "E"}:
                found.append(register)
    return sorted(set(found), key=lambda r: ["T", "A", "f", "E"].index(r))


def _tags_for(
    source_bucket: str,
    expression: str,
    source_meta: dict[str, Any],
    style_id: str,
) -> list[str]:
    tags = ["level3", "conversational", source_bucket, style_id]
    if _registers(expression):
        tags.append("has_register")
    if _OMEGA_RE.search(expression):
        tags.append("has_omega")
    if "Theta(" in expression or "\u0398(" in expression:
        tags.append("has_production")
    if any(token in expression for token in ("Cluster{", "Product(", "Pullback(", "CoverOf(", "PartitionOf(")):
        tags.append("meta_logic")
    if source_meta.get("is_valid") is False:
        tags.append("source_invalid")
    violation_type = source_meta.get("violation_type")
    if violation_type:
        tags.append(str(violation_type))
    return list(dict.fromkeys(tags))
