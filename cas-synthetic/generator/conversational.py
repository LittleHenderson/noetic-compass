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
# The ten canonical Noetic NAMES (docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md, Clarification 1). These are the only
# names allowed in a name slot such as "^6 (Male)". The plain-word glosses in _NOETIC_NAMES below are DESCRIPTIONS
# for story sentences only; before 2026-09-21 they were also written into the name slot ("^6 (analysis)").
_NOETIC_CANONICAL_NAMES = {
    0: "Idea",
    1: "Mind",
    2: "Positive",
    3: "Negative",
    4: "Vibration",
    5: "Female",
    6: "Male",
    7: "Rhythm",
    8: "Above/Cause",
    9: "Below/Effect",
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
_DOMAIN_STORY_NAMES = {
    "P": "values or first-principles judgment",
    "C": "thinking through the idea",
    "E": "felt evaluation",
    "O": "practical action",
}
_REGISTER_STORY_NAMES = {
    "T": "meaning-level",
    "A": "analytical",
    "f": "felt",
    "E": "embodied",
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
        style_ids: Sequence[str] | None = None,
    ) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.variants_per_source = _validate_variants_per_source(variants_per_source)
        path = Path(template_path) if template_path is not None else _TEMPLATE_PATH
        with open(path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        self.templates = loaded
        self.styles = list(loaded.get("styles", []))
        if style_ids is not None:
            wanted = {str(style_id) for style_id in style_ids}
            self.styles = [style for style in self.styles if str(style.get("id")) in wanted]
            found = {str(style.get("id")) for style in self.styles}
            missing = sorted(wanted - found)
            if missing:
                raise RuntimeError(f"Unknown Level 3 conversational style id(s): {', '.join(missing)}")
        if not self.styles:
            raise RuntimeError(f"No Level 3 conversational styles found in {path}")

    def iter_jsonl(
        self,
        input_path: str | Path,
        *,
        max_source_records: int | None = None,
        start_source_record: int = 0,
        variants_per_source: int | None = None,
        include_invalid_sources: bool = False,
    ) -> Iterator[ConversationalExample]:
        """Stream conversational variants from a Level 2 JSONL file."""
        path = Path(input_path)
        max_records = _validate_max_source_records(max_source_records)
        start_record = _validate_start_source_record(start_source_record)
        source_records_seen = 0
        selected_records = 0
        with open(path, encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                source_index = source_records_seen
                source_records_seen += 1
                if source_index < start_record:
                    continue
                if max_records is not None and selected_records >= max_records:
                    break
                selected_records += 1
                source = json.loads(line)
                if not include_invalid_sources and _source_is_invalid(source):
                    continue
                yield from self.iter_source_record(
                    source,
                    source_index=source_index,
                    source_line=line_number,
                    source_path=path,
                    variants_per_source=variants_per_source,
                )

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
        start_source_record: int = 0,
        max_output_records: int | None = None,
        variants_per_source: int | None = None,
        progress_every: int = 1000,
        include_invalid_sources: bool = False,
    ) -> dict[str, Any]:
        """Generate a Level 3 JSONL file from a Level 2 JSONL source."""
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        written = 0
        source_indices: set[int] = set()
        source_records_seen = 0
        selected_source_records = 0
        source_records_skipped = 0
        bucket_counts: dict[str, int] = {}
        max_records = _validate_max_source_records(max_source_records)
        start_record = _validate_start_source_record(start_source_record)
        max_outputs = _validate_max_output_records(max_output_records)
        with open(input_path, encoding="utf-8") as source_file, open(
            out_path, "w", encoding="utf-8"
        ) as f:
            for line_number, line in enumerate(source_file, start=1):
                line = line.strip()
                if not line:
                    continue
                source_index = source_records_seen
                source_records_seen += 1
                if source_index < start_record:
                    continue
                if max_records is not None and selected_source_records >= max_records:
                    break
                if max_outputs is not None and written >= max_outputs:
                    break
                source = json.loads(line)
                selected_source_records += 1
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
                    if max_outputs is not None and written >= max_outputs:
                        break
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
            "source_records_seen": source_records_seen,
            "start_source_record": start_record,
            "selected_source_records": selected_source_records,
            "source_records_skipped": source_records_skipped,
            "max_output_records": max_outputs,
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
        noetic = _top_noetic(expression)
        domain = _top_domain(expression)
        noetic_name = _NOETIC_NAMES.get(noetic, "the main CAS dynamic")
        domain_phrase = _DOMAIN_STORY_NAMES.get(domain or "", "the situation")
        registers = _registers(expression)
        register_phrase = _register_story(registers)
        omega = _omega_label(expression) or "the named outcome"
        case_context = _case_context(source_bucket, expression, rng=self.rng)

        values = {
            "cas_expression": expression,
            "source_prompt": source_prompt or "No source prompt was supplied.",
            "source_response": source_response or "No source response was supplied.",
            "source_bucket": source_bucket,
            "case_context": case_context,
            "noetic_name": noetic_name,
            "domain_phrase": domain_phrase,
            "register_phrase": register_phrase,
            "omega": omega,
            "plain_situation": _plain_situation(
                source_bucket,
                expression,
                source_prompt=source_prompt,
                rng=self.rng,
            ),
            "cas_reading": _cas_reading(expression),
            "formal_axis_reading": _formal_axis_reading(expression),
            "conversation_need": _conversation_need(source_bucket, expression, self.rng),
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
    if value < 1 or value > 5:
        raise ValueError("variants_per_source must be between 1 and 5")
    return value


def _validate_max_source_records(value: int | None) -> int | None:
    if value is None:
        return None
    if value < 0:
        raise ValueError("max_source_records must be non-negative")
    return value


def _validate_start_source_record(value: int) -> int:
    if not isinstance(value, int):
        raise TypeError("start_source_record must be an integer")
    if value < 0:
        raise ValueError("start_source_record must be non-negative")
    return value


def _validate_max_output_records(value: int | None) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise TypeError("max_output_records must be an integer")
    if value < 0:
        raise ValueError("max_output_records must be non-negative")
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


def _plain_situation(
    source_bucket: str,
    expression: str,
    *,
    source_prompt: str,
    rng: random.Random,
) -> str:
    noetic = _top_noetic(expression)
    domain = _top_domain(expression)
    noetic_name = _NOETIC_NAMES.get(noetic, "the main dynamic")
    domain_phrase = _DOMAIN_STORY_NAMES.get(domain or "", "the situation")
    registers = _registers(expression)
    register_phrase = _register_story(registers)
    omega = _omega_label(expression)

    bucket_templates = {
        "v74_baseline": [
            "I'm trying to understand a moment where {noetic_name} shows up through {domain_phrase}.",
            "Something in this situation feels like {noetic_name}, but I need a plain-language CAS read.",
            "Can CAS help me name a pattern of {noetic_name} without making it sound fixed or final?",
        ],
        "v75_register": [
            "The same pattern seems to come through a {register_phrase} register, and I want to explain that clearly.",
            "I can name the content, but the way it is showing up feels {register_phrase}.",
            "How would CAS describe a {register_phrase} version of {noetic_name} in {domain_phrase}?",
        ],
        "v76_production": [
            "It feels like several ingredients are combining into {omega}, and I want the recipe explained simply.",
            "I can see pieces of the outcome, but I need help describing how they produce {omega}.",
            "Can CAS explain what is being produced here without treating it as a certainty?",
        ],
        "v77_omega": [
            "Different registers seem to converge into {omega}, and I want to understand the fusion.",
            "Part of this is {register_phrase}, but the combined result feels like {omega}.",
            "How would CAS explain a named emergent like {omega} in ordinary language?",
        ],
        "v77_rule_four": [
            "I'm comparing registers and need to know when integration requires a named result.",
            "This looks like multiple registers around the same state; how should CAS keep it disciplined?",
            "Can you explain why this register pattern needs a careful CAS reading?",
        ],
        "meta_logic": [
            "I want to group CAS pieces together without saying they are identical.",
            "Can CAS talk about containment, overlap, or membership in a way a non-math reader can follow?",
            "Help me explain this set-level CAS claim without turning it into a math lecture.",
        ],
    }
    templates = bucket_templates.get(source_bucket, bucket_templates["v74_baseline"])
    fallback = source_prompt or "this situation"
    values = {
        "noetic_name": noetic_name,
        "domain_phrase": domain_phrase,
        "register_phrase": register_phrase,
        "omega": omega or "the named outcome",
        "source_prompt": fallback,
    }
    return rng.choice(templates).format_map(_SafeFormat(values))


def _case_context(
    source_bucket: str,
    expression: str,
    *,
    rng: random.Random,
) -> str:
    """Build an expression-specific conversational scenario phrase."""
    noetic = _top_noetic(expression)
    domain = _top_domain(expression)
    noetic_name = _NOETIC_NAMES.get(noetic, "the main CAS dynamic")
    domain_phrase = _DOMAIN_STORY_NAMES.get(domain or "", "the situation")
    registers = _registers(expression)
    register_phrase = _register_story(registers)
    omega = _omega_label(expression) or "the named outcome"
    state_hint = _state_hint(expression)

    bucket_templates = {
        "v74_baseline": [
            "{state_hint}: a {domain_phrase} moment where {noetic_name} is the main signal",
            "a first-pass CAS read of {noetic_name} moving through {domain_phrase}",
            "a baseline state pattern centered on {state_hint}",
        ],
        "v75_register": [
            "{state_hint} carried through a {register_phrase} register",
            "a {domain_phrase} case where {noetic_name} arrives in a {register_phrase} mode",
            "a register-aware reading of {state_hint}",
        ],
        "v76_production": [
            "a production recipe where {state_hint} contributes to {omega}",
            "an outcome-building case around {omega}, with {noetic_name} visible in the ingredients",
            "a provisional recipe for {omega} in {domain_phrase}",
        ],
        "v77_omega": [
            "a cross-register integration where {register_phrase} evidence converges into {omega}",
            "a named-emergent case where {noetic_name} is organized as {omega}",
            "{state_hint} integrated into {omega} through {register_phrase} registers",
        ],
        "v77_rule_four": [
            "a Rule 4 check where {state_hint} appears across {register_phrase} registers and resolves to {omega}",
            "a cross-register discipline case for {noetic_name} in {domain_phrase}",
            "a same-state integration pattern where {register_phrase} registers must not be flattened",
            "{state_hint} becoming a named emergent instead of loose register co-presence",
        ],
        "meta_logic": [
            "a typed set-level relation involving {state_hint}",
            "a grouping or containment claim about CAS objects rather than a single state",
            "a meta-logic statement where the relation matters more than a single atom",
        ],
    }
    templates = bucket_templates.get(source_bucket, bucket_templates["v74_baseline"])
    values = {
        "state_hint": state_hint,
        "noetic_name": noetic_name,
        "domain_phrase": domain_phrase,
        "register_phrase": register_phrase,
        "omega": omega,
    }
    return rng.choice(templates).format_map(_SafeFormat(values))


_STATE_TOKEN_RE = re.compile(
    r"\^([0-9])(?:\^([PCEO]))?(?:_\{F([1-7])(?:\|([TAfE]))?\})?(?:\|([TAfE]))?"
)


def _formal_axis_reading(expression: str) -> str:
    """Verbalize exact CAS slots without copying the CAS expression.

    This is for recoverable Level 3 prompts: the user-facing prompt states the
    formal slots in natural language so expression generation is learnable
    instead of hidden behind an arbitrary scenario.
    """

    pieces: list[str] = []
    families = _formal_family_names(expression)
    if families:
        pieces.append(f"families: {', '.join(families)}")

    production_reading = _production_recipe_reading(expression)
    if production_reading:
        pieces.append(production_reading)

    state_parts: list[str] = []
    seen_states: set[str] = set()
    for match in _STATE_TOKEN_RE.finditer(expression):
        noetic_raw, domain, drive, drive_register, outer_register = match.groups()
        if not noetic_raw:
            continue
        desc: list[str] = [f"Noetic ^{noetic_raw}"]
        if domain:
            desc.append(f"domain {domain} ({_DOMAIN_NAMES[domain]})")
        if drive:
            desc.append(f"drive F{drive}")
        register = outer_register or drive_register
        if register:
            desc.append(f"register |{register} ({_REGISTER_STORY_NAMES[register]})")
        rendered = "; ".join(desc)
        if rendered not in seen_states:
            seen_states.add(rendered)
            state_parts.append(rendered)
    if state_parts:
        pieces.append("states: " + " / ".join(state_parts[:6]))

    omega_terms = sorted(set(_OMEGA_RE.findall(expression)))
    if omega_terms:
        pieces.append("named emergent target: " + ", ".join(omega_terms))

    foundation_terms = sorted(set(re.findall(r"Foundation_\d+", expression)))
    if foundation_terms:
        pieces.append("foundations: " + ", ".join(foundation_terms))

    carriers = [
        carrier
        for carrier in (
            "Noetics",
            "Domains",
            "Drives",
            "Registers",
            "States",
            "Foundations",
            "SubFoundations",
        )
        if carrier in expression
    ]
    if carriers:
        pieces.append("carriers: " + ", ".join(carriers))

    operators = _formal_operator_names(expression)
    if operators:
        pieces.append("operators: " + ", ".join(operators))

    return "; ".join(pieces) if pieces else "a compact CAS expression with no separately verbalized slots"


def _formal_family_names(expression: str) -> list[str]:
    families: list[str] = []
    if "Theta(" in expression or "\u0398(" in expression:
        families.append("production recipe")
    if "Product(" in expression:
        families.append("Cartesian product")
    if "Cluster{" in expression:
        families.append("typed cluster")
    if "CoverOf(" in expression:
        families.append("cover")
    if "PartitionOf(" in expression:
        families.append("partition")
    if "Pullback(" in expression:
        families.append("pullback")
    if _OMEGA_RE.search(expression):
        families.append("named emergent")
    if not families and _STATE_TOKEN_RE.search(expression):
        families.append("state expression")
    return families


_PRODUCTION_TARGET_RE = re.compile(r"(?:Theta|\u0398)\(([^)]+)\)")
_RECIPE_TERM_RE = re.compile(
    r"([0-9]+(?:\.[0-9]+)?)\s*(?:\*|\u00b7)\s*"
    r"(\^[0-9](?:\^[PCEO])?(?:_\{F[1-7](?:\|[TAfE])?\})?(?:\|[TAfE])?)"
)
_LEAKAGE_TERM_RE = re.compile(
    r"([0-9]+(?:\.[0-9]+)?)\s*(?:\*|\u00b7)\s*(?:Lambda|\u039b)\s*(?:\*|\u00b7)\s*"
    r"((?:Omega|\u03a9)_[A-Za-z0-9_]+)"
)


def _production_recipe_reading(expression: str) -> str:
    target_match = _PRODUCTION_TARGET_RE.search(expression)
    if not target_match:
        return ""

    parts = [f"production target {target_match.group(1)}"]
    recipe_terms: list[str] = []
    for coeff, state_token in _RECIPE_TERM_RE.findall(expression):
        state_desc = _describe_state_token(state_token)
        if state_desc:
            recipe_terms.append(f"{coeff} times {state_desc}")
    if recipe_terms:
        parts.append("recipe coefficients: " + " / ".join(recipe_terms[:8]))

    leakage_terms = [
        f"{coeff} leakage to {omega}"
        for coeff, omega in _LEAKAGE_TERM_RE.findall(expression)
    ]
    if leakage_terms:
        parts.append("leakage: " + " / ".join(leakage_terms[:4]))
    return "; ".join(parts)


def _describe_state_token(state_token: str) -> str:
    match = _STATE_TOKEN_RE.fullmatch(state_token)
    if not match:
        return state_token
    noetic_raw, domain, drive, drive_register, outer_register = match.groups()
    desc: list[str] = [f"Noetic ^{noetic_raw}"]
    if domain:
        desc.append(f"domain {domain} ({_DOMAIN_NAMES[domain]})")
    if drive:
        desc.append(f"drive F{drive}")
    register = outer_register or drive_register
    if register:
        desc.append(f"register |{register} ({_REGISTER_STORY_NAMES[register]})")
    return "; ".join(desc)


def _formal_operator_names(expression: str) -> list[str]:
    operator_map = [
        ("->", "directed arrow"),
        ("\u2192", "directed arrow"),
        ("\u00d7", "cross-register integration"),
        ("=", "emergent assignment"),
        ("\u2208", "membership"),
        ("\u2209", "not-membership"),
        ("\u2282", "strict subset"),
        ("\u2286", "subset-or-equal"),
        ("\u2283", "strict superset"),
        ("\u2287", "superset-or-equal"),
        ("\u222a", "union"),
        ("\u2229", "intersection"),
        ("\u2216", "difference"),
    ]
    out: list[str] = []
    is_production = bool(_PRODUCTION_TARGET_RE.search(expression))
    if "*" in expression:
        out.append("coefficient multiplication" if is_production else "composition star")
    if " + " in expression:
        out.append("ingredient sum" if is_production else "plus co-presence")
    for token, name in operator_map:
        if token in expression and name not in out:
            out.append(name)
    return out


def _cas_reading(expression: str) -> str:
    noetic = _top_noetic(expression)
    domain = _top_domain(expression)
    pieces: list[str] = []
    if noetic is not None:
        pieces.append(f"^{noetic} {_NOETIC_CANONICAL_NAMES.get(noetic, '')} as the main noetic signal".replace("  ", " "))
    if domain is not None:
        pieces.append(f"{_DOMAIN_STORY_NAMES.get(domain, domain)} as the main domain")
    registers = _registers(expression)
    if registers:
        pieces.append(f"{_register_story(registers)} register evidence")
    omega = _omega_label(expression)
    if omega:
        pieces.append(f"the named emergent {omega}")
    if any(token in expression for token in ("Cluster{", "Set{", "Product(", "Pullback(", "CoverOf(", "PartitionOf(")):
        pieces.append("a set-level relationship rather than a single state")
    if not pieces:
        return "a compact CAS structural reading"
    return "; ".join(pieces)


def _conversation_need(source_bucket: str, expression: str, rng: random.Random) -> str:
    options = {
        "v74_baseline": [
            "name the pattern without over-reading it",
            "turn the notation into a plain first pass",
            "separate the signal from any conclusion",
        ],
        "v75_register": [
            "explain the register without changing the state",
            "show how the same content can arrive in a different mode",
            "make the register distinction easy to hear",
        ],
        "v76_production": [
            "describe the ingredients and the resulting outcome",
            "keep the recipe provisional instead of predictive",
            "explain what is being produced without claiming certainty",
        ],
        "v77_omega": [
            "explain the fused outcome without flattening the registers",
            "show why the named emergent matters",
            "keep the integration explicit",
        ],
        "v77_rule_four": [
            "show why cross-register integration needs discipline",
            "distinguish co-presence from a named emergent result",
            "explain the rule without sounding punitive",
        ],
        "meta_logic": [
            "make the set-level claim readable",
            "show grouping or containment without collapsing the parts",
            "translate the formal relation into a practical explanation",
        ],
    }
    del expression
    return rng.choice(options.get(source_bucket, options["v74_baseline"]))


def _focus_summary(expression: str) -> str:
    noetic_counts = extract_noetic_counts(expression)
    domain_counts = extract_domain_counts(expression)
    noetic_part = _axis_focus(noetic_counts, _NOETIC_CANONICAL_NAMES, "Noetic")
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


def _top_noetic(expression: str) -> int | None:
    counts = extract_noetic_counts(expression)
    if not any(counts):
        return None
    return max(range(len(counts)), key=lambda i: counts[i])


def _top_domain(expression: str) -> str | None:
    counts = extract_domain_counts(expression)
    if not any(counts):
        return None
    labels = ["P", "C", "E", "O"]
    return labels[max(range(len(counts)), key=lambda i: counts[i])]


def _register_story(registers: Sequence[str]) -> str:
    if not registers:
        return "unspecified"
    described = [_REGISTER_STORY_NAMES.get(register, register) for register in registers]
    if len(described) == 1:
        return described[0]
    if len(described) == 2:
        return f"{described[0]} and {described[1]}"
    return ", ".join(described[:-1]) + f", and {described[-1]}"


def _omega_label(expression: str) -> str | None:
    match = _OMEGA_RE.search(expression)
    if not match:
        return None
    return match.group(0)


def _state_hint(expression: str) -> str:
    """Return a compact first state-like token for conversational context."""
    match = re.search(r"\^[0-9](?:\^[PCEO])?(?:_\{F[1-7]\})?(?:\|[TAfE])?", expression)
    if match:
        return match.group(0)
    cluster_match = re.search(r"[A-Za-z]+Cluster\{[^}]+\}", expression)
    if cluster_match:
        return cluster_match.group(0)
    carrier_match = re.search(r"\b(Noetics|States|Domains|Drives|Registers|Foundations)\b", expression)
    if carrier_match:
        return carrier_match.group(0)
    return "the CAS expression"


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
