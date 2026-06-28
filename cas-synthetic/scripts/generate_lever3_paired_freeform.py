"""Lever 3 paired-data generator: training-surface CAS prompts -> free-form English via Claude.

Reads the recoverable Level-3 training set, removes records overlapping the v77-relabeled
eval set on the joint key (id, source_level2_id, cas_expression), draws a stratified sample
of ~5,000 records across the six buckets, and rewrites each record's user_prompt into a
natural colloquial English sentence using Claude Sonnet 4.6.

USAGE
    python -m cas_synthetic.scripts.generate_lever3_paired_freeform \
        --target 5000 \
        --out cas-synthetic/data/level2_scaffold/lever3_paired_freeform_5k_2026_05_04.jsonl \
        --calibration-out cas-synthetic/data/level2_scaffold/lever3_paired_freeform_calibration_50.jsonl

    # Dry run (no API calls):
    python cas-synthetic/scripts/generate_lever3_paired_freeform.py --dry-run \
        --out /tmp/out.jsonl --calibration-out /tmp/cal.jsonl

ENVIRONMENT
    ANTHROPIC_API_KEY  must be set unless --dry-run is passed.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Iterator

# pip install anthropic
try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover
    Anthropic = None  # validated lazily in main()


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "cas-synthetic" / "data" / "level2_scaffold"
TRAIN_FILE = DATA_DIR / "level3_recoverable_full.jsonl"
EVAL_FILE = DATA_DIR / "level3_recoverable_eval_1000_v77_relabeled.jsonl"

MODEL_ID = "claude-sonnet-4-6"
DEFAULT_TEMPERATURE = 0.7
RETRY_TEMPERATURE = 0.5
MAX_TOKENS = 256
CALIBRATION_COUNT = 50

BUCKETS = [
    "v74_baseline",
    "v75_register",
    "v76_production",
    "v77_omega",
    "v77_rule_four",
    "meta_logic",
]


REWRITE_PROMPT = """You are translating CAS-notation prompts into natural colloquial English.

Original prompt (training-surface format):
{ORIGINAL_PROMPT}

Underlying CAS expression:
{CAS_EXPRESSION}

Bucket: {BUCKET}

Generate ONE free-form colloquial English sentence (or short paragraph) that
EXPRESSES THE SAME UNDERLYING COGNITIVE STRUCTURE as the CAS expression. Use
natural language a human might actually say. Do NOT include the words "CAS",
"Noetic", "domain", "drive", "register", or any operator notation. Do not
mention the structure exists. Just say what the structure WOULD MEAN if a
human were experiencing or describing it.

Apply the colloquialism map authoritative in CAS:
- ^2 Positive (attraction): "drawn to", "speaks to me", "love"
- ^3 Negative (visceral aversion, NOT analytical critique): "can't stand", "rubs me wrong"
- ^4 Vibration (resonance): "struck a chord", "hit me hard"
- ^5 Female (accumulated experience): "shaped by years", "made me who I am"
- ^6 Male (decomposition, NOT aversion): "breaking it down", "unpacking"
- ^7 Rhythm (pattern repetition): "practice", "every day", "muscle memory"
- ^8 Above/Cause (associative trigger, NOT deduction): "reminds me", "made me think of"
- ^9 Below/Effect (the surfaced thought): "popped into my head", "came to me"
- ^0 Idea: just "an idea" or content-neutral
- ^1 Mind: "paying attention", "making up my mind"

Register markers:
- |T transcendent: high-abstraction, vision, calling
- |A analytical: explicit reasoning
- |f affective: feeling-toned
- |E embodied: bodily, sensorimotor

Domain:
- P principled: ethical/normative
- C cognitive: thinking
- E evaluative: feeling about
- O operational: doing/practicing

Output ONLY the natural English sentence. No quotes, no preamble, no commentary."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# Forbidden vocabulary (case-insensitive whole words). The model must speak
# colloquial English, never CAS jargon.
FORBIDDEN_WORDS = [
    "cas",
    "noetic",
    "noetics",
    "domain",
    "domains",
    "drive",
    "drives",
    "register",
    "registers",
]

# Forbidden tokens (substring search, case-sensitive); these would leak the
# notation surface back into the rewrite.
FORBIDDEN_SUBSTRINGS = [
    "^",
    "F1", "F2", "F3", "F4", "F5", "F6", "F7",
    "|T", "|A", "|f", "|E",
    "CO-",
]


def validate(text: str) -> tuple[bool, str]:
    """Return (ok, reason). reason is empty when ok=True."""
    if not isinstance(text, str):
        return False, "not_a_string"
    s = text.strip()
    if len(s) < 10:
        return False, f"too_short({len(s)})"
    if len(s) > 500:
        return False, f"too_long({len(s)})"

    # Must end with letter, period, or question mark.
    last = s[-1]
    if not (last.isalpha() or last in ".?"):
        return False, f"bad_terminal({last!r})"

    for sub in FORBIDDEN_SUBSTRINGS:
        if sub in s:
            return False, f"forbidden_substring({sub!r})"

    lowered = s.lower()
    # Whole-word forbidden vocabulary check.
    for word in FORBIDDEN_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return False, f"forbidden_word({word!r})"

    return True, ""


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as fp:
        for line_idx, raw in enumerate(fp, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as exc:
                print(
                    f"[warn] {path.name}:{line_idx} JSON decode failed: {exc}",
                    file=sys.stderr,
                )


def joint_key(rec: dict) -> tuple:
    return (
        rec.get("id"),
        rec.get("source_level2_id"),
        rec.get("cas_expression"),
    )


def filter_eval_overlap(train: list[dict], eval_set: list[dict]) -> list[dict]:
    eval_keys = {joint_key(r) for r in eval_set}
    return [r for r in train if joint_key(r) not in eval_keys]


def stratified_sample(
    train: list[dict],
    total: int,
    buckets: Iterable[str],
    rng: random.Random,
) -> list[dict]:
    """Stratified sample across buckets. If a bucket has fewer than its quota,
    spill the deficit evenly to the others (largest-remainder)."""
    bucket_to_records: dict[str, list[dict]] = defaultdict(list)
    for r in train:
        b = r.get("bucket")
        if b in set(buckets):
            bucket_to_records[b].append(r)

    base_quota = total // max(1, len(list(buckets)))
    quotas: dict[str, int] = {b: base_quota for b in buckets}

    # First pass: take what each bucket can fill.
    chosen: list[dict] = []
    leftover_capacity: dict[str, int] = {}
    for b in buckets:
        recs = bucket_to_records.get(b, [])
        rng.shuffle(recs)
        take = min(quotas[b], len(recs))
        chosen.extend(recs[:take])
        leftover_capacity[b] = len(recs) - take

    # Second pass: redistribute deficit across buckets that still have records.
    deficit = total - len(chosen)
    if deficit > 0:
        donors = [b for b in buckets if leftover_capacity[b] > 0]
        # Round-robin draw from donors until deficit is filled or capacity exhausted.
        round_robin_idx = 0
        # Rebuild a per-bucket pool of remaining records (keeping order from earlier shuffle).
        remaining_pool: dict[str, list[dict]] = {}
        for b in donors:
            already = quotas[b]
            remaining_pool[b] = bucket_to_records[b][already:]
        while deficit > 0 and donors:
            b = donors[round_robin_idx % len(donors)]
            pool = remaining_pool[b]
            if pool:
                chosen.append(pool.pop(0))
                deficit -= 1
            else:
                donors.remove(b)
                continue
            round_robin_idx += 1

    rng.shuffle(chosen)
    return chosen


# ---------------------------------------------------------------------------
# Anthropic call
# ---------------------------------------------------------------------------


def build_prompt(record: dict) -> str:
    return REWRITE_PROMPT.format(
        ORIGINAL_PROMPT=record.get("user_prompt", ""),
        CAS_EXPRESSION=record.get("cas_expression", ""),
        BUCKET=record.get("bucket", ""),
    )


def generate_one(
    client,
    record: dict,
    *,
    temperature: float = DEFAULT_TEMPERATURE,
    max_retries_on_api_error: int = 3,
) -> str | None:
    """One-shot rewrite. Returns the model's text on success, None on transport failure.

    Retries transient API errors (rate limit, 5xx, network) up to max_retries_on_api_error
    with exponential backoff. Validation failures are NOT retried here; the caller orchestrates
    a temperature-adjusted retry per the spec.
    """
    prompt = build_prompt(record)

    backoff = 2.0
    for attempt in range(max_retries_on_api_error):
        try:
            resp = client.messages.create(
                model=MODEL_ID,
                max_tokens=MAX_TOKENS,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # noqa: BLE001 - transport-level, retry policy below
            msg = str(exc)
            transient = any(
                tok in msg.lower()
                for tok in ("rate limit", "429", "overloaded", "timeout", "503", "502", "500")
            )
            if attempt + 1 < max_retries_on_api_error and transient:
                sleep_for = backoff * (2 ** attempt)
                print(
                    f"[warn] transient API error (attempt {attempt + 1}): {exc}; "
                    f"sleeping {sleep_for:.1f}s",
                    file=sys.stderr,
                )
                time.sleep(sleep_for)
                continue
            print(f"[error] API call failed permanently: {exc}", file=sys.stderr)
            return None

        # Extract text from response.
        try:
            parts = resp.content or []
            text_parts: list[str] = []
            for p in parts:
                t = getattr(p, "text", None)
                if t:
                    text_parts.append(t)
            text = "".join(text_parts).strip()
            return text
        except Exception as exc:  # noqa: BLE001
            print(f"[error] failed to read response content: {exc}", file=sys.stderr)
            return None
    return None


# ---------------------------------------------------------------------------
# Output assembly
# ---------------------------------------------------------------------------


def assemble_output_record(source: dict, generated_text: str) -> dict:
    """Build the output JSON line: copy all source fields verbatim, then set the
    rewritten user_prompt and add bookkeeping fields (id, original_prompt,
    generation_metadata)."""
    out = dict(source)  # shallow copy preserves verbatim fields
    source_id = source.get("id", "")
    out["id"] = f"lever3_{source_id}_v1"
    out["source_id"] = source_id
    out["original_prompt"] = source.get("user_prompt", "")
    out["user_prompt"] = generated_text
    # bucket and cas_expression remain copied from source. Make explicit guarantees:
    out["bucket"] = source.get("bucket", "")
    out["cas_expression"] = source.get("cas_expression", "")
    out["generation_metadata"] = {
        "model": MODEL_ID,
        "temperature": DEFAULT_TEMPERATURE,
        "version": 1,
    }
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def write_jsonl_append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def already_done_source_ids(partial_path: Path) -> set[str]:
    if not partial_path.exists():
        return set()
    done: set[str] = set()
    for rec in load_jsonl(partial_path):
        sid = rec.get("source_id")
        if sid:
            done.add(sid)
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=5000,
                        help="Total examples to generate after stratified sampling.")
    parser.add_argument("--out", required=True, type=Path,
                        help="Final JSONL of validated examples.")
    parser.add_argument("--calibration-out", required=True, type=Path,
                        help="Calibration JSONL of the FIRST 50 validated examples.")
    parser.add_argument("--checkpoint-every", type=int, default=500,
                        help="Write progress checkpoints every N successes.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=None,
                        help="Cap the number of source records processed (for testing).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run pipeline without API calls (validates data flow only).")
    parser.add_argument("--train-file", type=Path, default=TRAIN_FILE)
    parser.add_argument("--eval-file", type=Path, default=EVAL_FILE)
    args = parser.parse_args()

    rng = random.Random(args.seed)

    # API key check.
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not args.dry_run:
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Export it or pass --dry-run."
            )
        if Anthropic is None:
            raise RuntimeError(
                "anthropic SDK not installed. Run: pip install anthropic"
            )

    # Load.
    print(f"[info] loading training records from {args.train_file}")
    train = list(load_jsonl(args.train_file))
    print(f"[info] loaded {len(train)} training records")

    print(f"[info] loading eval records from {args.eval_file}")
    eval_set = list(load_jsonl(args.eval_file))
    print(f"[info] loaded {len(eval_set)} eval records")

    # Filter eval overlap on joint key.
    filtered = filter_eval_overlap(train, eval_set)
    print(
        f"[info] removed {len(train) - len(filtered)} eval-overlapping records; "
        f"{len(filtered)} remain"
    )

    # Stratified sample.
    sampled = stratified_sample(filtered, args.target, BUCKETS, rng)
    print(
        f"[info] stratified sample: {len(sampled)} records across "
        f"{len(BUCKETS)} buckets"
    )
    bucket_dist = Counter(r.get("bucket") for r in sampled)
    for b in BUCKETS:
        print(f"        {b}: {bucket_dist.get(b, 0)}")

    if args.limit is not None:
        sampled = sampled[: args.limit]
        print(f"[info] --limit applied: processing {len(sampled)} records")

    # Resume support: read partial checkpoint to skip already-completed source_ids.
    partial_path = args.out.with_suffix("")  # strip .jsonl
    partial_path = partial_path.with_name(partial_path.name + ".partial.jsonl")
    done_ids = already_done_source_ids(partial_path)
    if done_ids:
        print(f"[info] resume: {len(done_ids)} source_ids already completed in {partial_path.name}")

    # Counters.
    successes = 0
    validation_failures = 0
    drops = 0
    api_failures = 0
    bucket_success: Counter = Counter()
    calibration_written = sum(1 for _ in load_jsonl(args.calibration_out)) if args.calibration_out.exists() else 0

    # Anthropic client.
    client = None
    if not args.dry_run:
        client = Anthropic(api_key=api_key)

    # Ensure parent dirs exist for outputs.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.calibration_out.parent.mkdir(parents=True, exist_ok=True)

    t_start = time.time()

    for idx, record in enumerate(sampled, start=1):
        source_id = record.get("id", "")
        if source_id in done_ids:
            continue

        if args.dry_run:
            # Synthesize a placeholder rewrite that passes validation.
            generated = (
                f"This is a dry-run placeholder for bucket {record.get('bucket','?')} "
                f"that simulates a colloquial sentence."
            )
        else:
            # First attempt at default temperature.
            generated = generate_one(client, record, temperature=DEFAULT_TEMPERATURE)
            if generated is None:
                api_failures += 1
                drops += 1
                print(
                    f"[drop] {idx}/{len(sampled)} source_id={source_id} api_failure",
                    file=sys.stderr,
                )
                continue

            ok, reason = validate(generated)
            if not ok:
                # Retry once at lower temperature.
                retry_text = generate_one(client, record, temperature=RETRY_TEMPERATURE)
                if retry_text is None:
                    api_failures += 1
                    drops += 1
                    print(
                        f"[drop] {idx}/{len(sampled)} source_id={source_id} api_failure_on_retry",
                        file=sys.stderr,
                    )
                    continue
                ok2, reason2 = validate(retry_text)
                if not ok2:
                    validation_failures += 1
                    drops += 1
                    print(
                        f"[drop] {idx}/{len(sampled)} source_id={source_id} "
                        f"validation_failed: first={reason!r} retry={reason2!r}",
                        file=sys.stderr,
                    )
                    continue
                generated = retry_text

        # Final-validation guard for dry-run too (synthetic text is fine).
        ok, reason = validate(generated)
        if not ok:
            validation_failures += 1
            drops += 1
            print(
                f"[drop] {idx}/{len(sampled)} source_id={source_id} "
                f"validation_failed_final: {reason!r}",
                file=sys.stderr,
            )
            continue

        out_rec = assemble_output_record(record, generated.strip())

        # Write to partial checkpoint and to calibration set if applicable.
        write_jsonl_append(partial_path, out_rec)
        successes += 1
        bucket_success[record.get("bucket")] += 1

        if calibration_written < CALIBRATION_COUNT:
            write_jsonl_append(args.calibration_out, out_rec)
            calibration_written += 1
            if calibration_written == CALIBRATION_COUNT:
                print(
                    f"[info] calibration set complete ({CALIBRATION_COUNT} examples) "
                    f"-> {args.calibration_out}"
                )

        # Progress / checkpoint logs.
        if idx % 100 == 0 or idx == len(sampled):
            elapsed = time.time() - t_start
            rate = idx / max(elapsed, 1e-6)
            eta_s = (len(sampled) - idx) / max(rate, 1e-6)
            print(
                f"[progress] {idx}/{len(sampled)}  ok={successes}  drops={drops}  "
                f"val_fail={validation_failures}  api_fail={api_failures}  "
                f"rate={rate:.2f}/s  eta={eta_s/60:.1f}m"
            )
        if successes and successes % args.checkpoint_every == 0:
            print(f"[checkpoint] {successes} validated examples in {partial_path.name}")

    # Promote partial -> final by copying validated lines (partial IS the validated stream
    # since drops are not written to it).
    print(f"[info] writing final output {args.out}")
    if args.out.exists():
        args.out.unlink()
    if partial_path.exists():
        with partial_path.open("r", encoding="utf-8") as src, args.out.open("w", encoding="utf-8") as dst:
            for line in src:
                dst.write(line)

    # Summary.
    total_attempted = max(1, successes + drops)
    pass_rate = successes / total_attempted
    print("=" * 72)
    print("SUMMARY")
    print(f"  attempted: {total_attempted}")
    print(f"  validated: {successes}")
    print(f"  drops: {drops}  (validation_failures={validation_failures}, api_failures={api_failures})")
    print(f"  pass_rate: {pass_rate:.4f}")
    print("  bucket distribution (validated):")
    for b in BUCKETS:
        print(f"    {b}: {bucket_success.get(b, 0)}")
    print(f"  output: {args.out}")
    print(f"  calibration: {args.calibration_out}")
    print(f"  partial: {partial_path}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
