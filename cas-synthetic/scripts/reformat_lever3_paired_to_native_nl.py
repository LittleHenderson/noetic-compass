"""Reformat Lever 3 paired Q/A rows into native-NL one-turn dialogue rows.

This is a bridge tool, not a substitute for Tier 3 dialogue generation.

The existing Lever 3 paired corpora contain useful prompt -> response pairs,
but most ``assistant_response`` values explain the CAS notation directly. That
is not the same thing as a fluent conversational reply grounded in CAS. For
that reason this script defaults to strict conversational filtering: rows that
leak CAS jargon or notation are rejected.

If you intentionally want the explanatory rows for an auxiliary "explain CAS"
task, pass ``--include-explanatory``. Those rows are marked with:

    training_lane = "cas_explanation_auxiliary"
    use_for_conversational_lm = false

so they do not silently contaminate the conversational reply corpus.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import uuid
from collections import Counter
from pathlib import Path
from typing import Iterable


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SEED_SCRIPT = _REPO_ROOT / "cas-synthetic" / "scripts" / "generate_native_nl_sdg_v1.py"


def _load_seed_module():
    mod_name = "_native_nl_sdg_v1_seed_for_lever3_reformat"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, _SEED_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load seed SDG module from {_SEED_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


seed = _load_seed_module()

SCHEMA_VERSION = seed.SCHEMA_VERSION
GENERATION_VERSION = "native_nl_lever3_reformat_v1"

DEFAULT_INPUTS = (
    _REPO_ROOT / "cas-synthetic" / "data" / "level2_scaffold" / "lever3_paired_dt_K4.jsonl",
    _REPO_ROOT / "cas-synthetic" / "data" / "level2_scaffold" / "lever3_paired_freeform_5k_2026_05_04.jsonl",
)
DEFAULT_OUT = (
    _REPO_ROOT
    / "cas-synthetic"
    / "data"
    / "native_nl"
    / "v1_dialogue_lever3_reformatted_20260506.jsonl"
)
DEFAULT_MANIFEST = (
    _REPO_ROOT
    / "cas-synthetic"
    / "data"
    / "native_nl"
    / "v1_dialogue_lever3_reformatted_20260506_manifest.json"
)

_STATE_RE = re.compile(r"\^([0-9])\^([PCEO])(?:_\{?(F[1-7])\}?)?(?:\|([TAfE]))?")
_EXPLANATORY_REPLY_PATTERNS = (
    re.compile(r"\bnotation\b", re.IGNORECASE),
    re.compile(r"\bexact (?:CAS )?expression\b", re.IGNORECASE),
    re.compile(r"\bprecise notation\b", re.IGNORECASE),
    re.compile(r"\bformal slots?\b", re.IGNORECASE),
    re.compile(r"\bslot evidence\b", re.IGNORECASE),
    re.compile(r"\btyped finite\b", re.IGNORECASE),
    re.compile(r"\bprompt supplied\b", re.IGNORECASE),
    re.compile(r"\bUse [A-Z][A-Za-z0-9_]*\(", re.IGNORECASE),
    re.compile(r"\bmaps? to\b", re.IGNORECASE),
)
_PROMPT_REQUESTS_CAS_PATTERNS = (
    re.compile(r"\bCAS\b", re.IGNORECASE),
    re.compile(r"\bwhat expression\b", re.IGNORECASE),
    re.compile(r"\bexact expression\b", re.IGNORECASE),
    re.compile(r"\bformal (?:CAS )?expression\b", re.IGNORECASE),
    re.compile(r"\bprecise CAS read\b", re.IGNORECASE),
    re.compile(r"\bwhat(?:'s| is) it map", re.IGNORECASE),
    re.compile(r"\bgive me the expression\b", re.IGNORECASE),
    re.compile(r"\bsupply the formal\b", re.IGNORECASE),
)


def iter_jsonl(path: Path) -> Iterable[tuple[int, dict]]:
    with path.open("r", encoding="utf-8") as fp:
        for line_no, raw in enumerate(fp, start=1):
            raw = raw.strip()
            if not raw:
                continue
            yield line_no, json.loads(raw)


def parse_primary_axes(cas_expression: str) -> dict[str, str]:
    """Best-effort first-state parser for manifest distributions."""
    match = _STATE_RE.search(cas_expression or "")
    if not match:
        return {
            "noetic": "?",
            "domain": "?",
            "drive": "?",
            "register": "?",
            "axis_parse_quality": "missing",
        }
    noetic, domain, drive, register = match.groups()
    return {
        "noetic": f"^{noetic}",
        "domain": domain or "?",
        "drive": drive or "?",
        "register": register or "?",
        "axis_parse_quality": "first_state",
    }


def profile_name(code: str | None) -> str:
    if not code:
        return "unknown"
    try:
        return seed.profile_for(code).name
    except Exception:  # noqa: BLE001
        return str(code)


def tone_name(code: str | None) -> str:
    if not code:
        return "unknown"
    try:
        return seed.tone_for(code).name
    except Exception:  # noqa: BLE001
        return str(code)


def validate_conversational_pair(prompt: str, reply: str) -> tuple[bool, list[str]]:
    """Stricter gate for using Lever 3 rows as fluent dialogue data."""
    ok, reasons = seed.validate_reply(reply)
    out = list(reasons)
    for pattern in _EXPLANATORY_REPLY_PATTERNS:
        if pattern.search(reply):
            out.append(f"explanatory_reply:{pattern.pattern}")
            break
    for pattern in _PROMPT_REQUESTS_CAS_PATTERNS:
        if pattern.search(prompt):
            out.append(f"prompt_requests_cas:{pattern.pattern}")
            break
    return len(out) == 0, out


def _record_id(
    *,
    cas_expression: str,
    prompt: str,
    source_id: str,
    source_path: Path,
    line_no: int,
) -> str:
    return seed.deterministic_id(
        "lever3_reformat",
        cas_expression,
        prompt,
        source_id,
        source_path.name,
        str(line_no),
    )


def convert_record(
    rec: dict,
    *,
    source_path: Path,
    line_no: int,
    trace_id: str,
    include_explanatory: bool,
) -> tuple[dict | None, str]:
    prompt = str(rec.get("user_prompt") or "").strip()
    reply = seed.clean_reply(str(rec.get("assistant_response") or ""))
    cas_expression = str(rec.get("cas_expression") or "").strip()
    if not prompt:
        return None, "missing_prompt"
    if not reply:
        return None, "missing_reply"
    if not cas_expression:
        return None, "missing_cas_expression"

    ok, reasons = validate_conversational_pair(prompt, reply)
    if not ok and not include_explanatory:
        return None, f"strict_reject:{reasons[0] if reasons else 'unknown'}"

    source_id = str(rec.get("id") or rec.get("source_id") or f"{source_path.name}:{line_no}")
    profile_code = str(rec.get("demographic_profile") or "")
    tone_code = str(rec.get("tonal_register") or "")
    axes = parse_primary_axes(cas_expression)
    now = seed.utc_now_iso()
    training_lane = "conversational_lm" if ok else "cas_explanation_auxiliary"

    out = {
        "id": _record_id(
            cas_expression=cas_expression,
            prompt=prompt,
            source_id=source_id,
            source_path=source_path,
            line_no=line_no,
        ),
        "created_at": now,
        "schema_version": SCHEMA_VERSION,
        "trace_id": trace_id,
        "tier": "tier3_reformatted",
        "parent_ids": [source_id],
        "source": "lever3_paired_reformat",
        "source_template_id": rec.get("provenance", {}).get("template_id"),
        "source_path": str(source_path),
        "source_line": line_no,
        "source_bucket": rec.get("bucket"),
        "generator_model": str(rec.get("generation_metadata", {}).get("model") or "unknown"),
        "generation_timestamp": now,
        "conversation_id": f"lever3_{source_id}",
        "turn_index": 0,
        "turn_count": 1,
        "cas_expression": cas_expression,
        "expression_family": str(rec.get("bucket") or "unknown"),
        "noetic": axes["noetic"],
        "domain": axes["domain"],
        "drive": axes["drive"],
        "register": axes["register"],
        "axis_parse_quality": axes["axis_parse_quality"],
        "prompt": prompt,
        "prompt_text": prompt,
        "reply": reply,
        "reply_text": reply,
        "demographic_profile": profile_name(profile_code),
        "demographic_profile_code": profile_code or "unknown",
        "tone": tone_name(tone_code),
        "tone_code": tone_code or "unknown",
        "validator_pass": ok,
        "validator_reasons": list(reasons),
        "round_trip_validator": "deferred",
        "generation_version": GENERATION_VERSION,
        "training_lane": training_lane,
        "use_for_conversational_lm": ok,
        "original_record": rec,
    }
    return out, "accepted"


def compute_distributions(records: list[dict]) -> dict[str, dict[str, int]]:
    keys = (
        "tier",
        "training_lane",
        "use_for_conversational_lm",
        "source_bucket",
        "noetic",
        "domain",
        "drive",
        "register",
        "axis_parse_quality",
        "demographic_profile",
        "tone",
    )
    out: dict[str, Counter[str]] = {key: Counter() for key in keys}
    for rec in records:
        for key in keys:
            out[key][str(rec.get(key, "?"))] += 1
    return {key: dict(counter) for key, counter in out.items()}


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        for rec in records:
            fp.write(json.dumps(rec, ensure_ascii=False) + "\n")


def write_manifest(
    path: Path,
    *,
    records: list[dict],
    failure_counts: Counter[str],
    inputs: list[Path],
    out_path: Path,
    trace_id: str,
    include_explanatory: bool,
    limit: int | None,
) -> dict:
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generation_version": GENERATION_VERSION,
        "trace_id": trace_id,
        "input_paths": [str(p) for p in inputs],
        "out_path": str(out_path),
        "include_explanatory": include_explanatory,
        "limit": limit,
        "total_records": len(records),
        "conversational_lm_records": sum(
            1 for rec in records if rec.get("use_for_conversational_lm")
        ),
        "cas_explanation_auxiliary_records": sum(
            1 for rec in records if rec.get("training_lane") == "cas_explanation_auxiliary"
        ),
        "validator_pass_count": sum(1 for rec in records if rec.get("validator_pass")),
        "failure_counts": dict(failure_counts),
        "distributions": compute_distributions(records),
        "notes": [
            "Lever3 assistant_response often explains CAS notation directly.",
            "Rows with use_for_conversational_lm=false must not be mixed into the fluent dialogue LM loss.",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def run(
    *,
    inputs: list[Path],
    out_path: Path,
    manifest_path: Path,
    include_explanatory: bool,
    limit: int | None,
) -> int:
    trace_id = str(uuid.uuid4())
    records: list[dict] = []
    failure_counts: Counter[str] = Counter()

    for source_path in inputs:
        for line_no, rec in iter_jsonl(source_path):
            converted, status = convert_record(
                rec,
                source_path=source_path,
                line_no=line_no,
                trace_id=trace_id,
                include_explanatory=include_explanatory,
            )
            if converted is None:
                failure_counts[status] += 1
                continue
            records.append(converted)
            if limit is not None and len(records) >= limit:
                break
        if limit is not None and len(records) >= limit:
            break

    write_jsonl(out_path, records)
    manifest = write_manifest(
        manifest_path,
        records=records,
        failure_counts=failure_counts,
        inputs=inputs,
        out_path=out_path,
        trace_id=trace_id,
        include_explanatory=include_explanatory,
        limit=limit,
    )
    print(
        f"[done] total={manifest['total_records']} "
        f"conversational={manifest['conversational_lm_records']} "
        f"explanatory={manifest['cas_explanation_auxiliary_records']} "
        f"failures={sum(failure_counts.values())}",
        flush=True,
    )
    if failure_counts:
        for key, count in failure_counts.most_common(10):
            print(f"   {count:>6d} {key}", flush=True)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        action="append",
        type=Path,
        dest="inputs",
        help="Input Lever 3 JSONL path. May be repeated.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--include-explanatory",
        action="store_true",
        help="Include CAS-explanation rows as auxiliary, not conversational LM, data.",
    )
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    inputs = args.inputs or list(DEFAULT_INPUTS)
    return run(
        inputs=inputs,
        out_path=args.out,
        manifest_path=args.manifest,
        include_explanatory=args.include_explanatory,
        limit=args.limit,
    )


if __name__ == "__main__":
    raise SystemExit(main())
