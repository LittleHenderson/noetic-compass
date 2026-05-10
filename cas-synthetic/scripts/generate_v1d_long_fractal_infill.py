"""C: long-fractal infill for v1d (k=6/7/8 net-new rows).

Per user directive 2026-05-10 (post B revalidation 4/227): k>=6
buckets still under 25 rows each (8 / 7 / 8). User's trigger for
C ("if k>=6 buckets still under ~25 clean rows each, run C for
long fractals only") is met.

Scope (user-specified):
  - 50-100 net-new k=6/7/8 rows
  - strict ordered-sequence gate (sequence_matches=True required)
  - skip recipe/meta infill — CoverOf and recipe-with-Lambda are
    "improved enough for this round"

Generation strategy:
  - Diverse k-sequences: random Noetic indices 0-9 with controlled
    repetition (some sequences have repeated k like Phi<5:5:3>; some
    don't; mix across the budget so the model sees both).
  - Notation mix: 50/50 Phi<...> ASCII / Phi<...> unicode (per
    existing corpus distribution).
  - Strict gate via build_v1d_targeted_regen.make_validator
    ('fractal'), so the same ordered-sequence check that audited
    the corpus is the gate for new rows.

Cost discipline (mirrors regen):
  - Default --dry-run; --paid + --yes-i-am-sure required.
  - --cost-cap-usd 5.0 default (sufficient for 100 rows at Haiku).
  - --target-per-k 30 default (90 rows total: 30 each k=6/7/8).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "cas-synthetic" / "scripts"
SCAFFOLD_ROOT = REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass"
DATA_DIR = REPO_ROOT / "cas-synthetic" / "data" / "path_d"

# Bootstrap cas_native package context (audit modules need it).
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(SCAFFOLD_ROOT / "cas-native")]
sys.modules.setdefault("cas_native", pkg)
sys.path.insert(0, str(SCAFFOLD_ROOT))


def _load(name: str, fname: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / fname)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {fname}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def _load_phase1():
    return _load("v1d_long_phase1", "generate_path_d_wave3_smoke.py")


def _load_regen():
    return _load("v1d_long_regen", "build_v1d_targeted_regen.py")


def _load_audit_fractal():
    return _load("v1d_long_audit_fractal", "audit_fractal_targets.py")


# ---------------------------------------------------------------------------
# K-sequence generation
# ---------------------------------------------------------------------------

def generate_diverse_k_sequence(
    k: int, *, allow_repeats: bool, rng: random.Random,
) -> tuple[int, ...]:
    """Generate one k-length Noetic sequence.

    When ``allow_repeats=False``, sample without replacement from
    0..9 (caps at k=10). When True, allow repeats but cap repeat
    runs at length 2 to keep sequences interesting (no all-same
    sequences like [5,5,5,5,5,5]).
    """
    if not allow_repeats:
        return tuple(rng.sample(range(10), k))
    seq: list[int] = []
    while len(seq) < k:
        candidate = rng.randint(0, 9)
        # Cap consecutive repeat runs at length 2.
        if (
            len(seq) >= 2
            and seq[-1] == seq[-2] == candidate
        ):
            continue
        seq.append(candidate)
    return tuple(seq)


def build_source_cas(
    k_values: tuple[int, ...], notation: str = "Φ",
) -> str:
    """Render a Phi<k1:k2:...:kn> source string."""
    body = ":".join(str(k) for k in k_values)
    return f"{notation}<{body}>"


def plan_infill(
    *,
    target_per_k: int,
    seed: int,
) -> list[tuple[int, str]]:
    """Build the infill work list. Returns ``[(k, source_cas), ...]``.

    Distribution per k (k=6/7/8):
      - 60% with allow_repeats=True (mirror existing corpus shape
        which has ~half repeating sequences)
      - 50/50 split between Φ unicode and Phi ASCII notation.
    """
    rng = random.Random(seed)
    plan: list[tuple[int, str]] = []
    for k in (6, 7, 8):
        n_repeat = int(round(target_per_k * 0.6))
        n_unique = target_per_k - n_repeat
        for _ in range(n_unique):
            seq = generate_diverse_k_sequence(
                k, allow_repeats=False, rng=rng,
            )
            notation = "Φ" if rng.random() < 0.5 else "Phi"
            plan.append((k, build_source_cas(seq, notation)))
        for _ in range(n_repeat):
            seq = generate_diverse_k_sequence(
                k, allow_repeats=True, rng=rng,
            )
            notation = "Φ" if rng.random() < 0.5 else "Phi"
            plan.append((k, build_source_cas(seq, notation)))
    rng.shuffle(plan)
    return plan


# ---------------------------------------------------------------------------
# Generation loop (one row at a time, retry on strict-gate fail)
# ---------------------------------------------------------------------------

def generate_one_row(
    *,
    source_cas: str,
    k: int,
    client,
    cost_tracker,
    validator,
    model: str,
    max_retries: int,
    dry_run: bool,
) -> dict:
    regen = _load_regen()
    fake_audit_row = {
        "id": f"v1d_infill_long_{k}_{abs(hash(source_cas)) % 10**8:08d}",
        "cas_expression": source_cas,
        "source_split": "infill",
        "expected_relation": None,  # not used by fractal prompt
    }
    system, user = regen.build_fractal_prompt(fake_audit_row | {
        "k_values": _parse_k(source_cas) or [],
    })
    attempts: list[dict] = []
    accepted_target: Optional[str] = None
    for attempt_idx in range(1, max_retries + 1):
        if dry_run:
            attempts.append({
                "attempt": attempt_idx,
                "dry_run": True,
                "user_preview": user[:160] + "...",
            })
            break
        result = client.call(
            model=model, system_prompt=system, user_message=user,
            max_output_tokens=400, temperature=0.4,
        )
        if result.text is None:
            attempts.append({
                "attempt": attempt_idx, "model": model,
                "error": result.error_reason,
            })
            continue
        cost = cost_tracker.add(
            slot="fractal_infill", model=model,
            input_tokens=int(result.input_tokens),
            output_tokens=int(result.output_tokens),
        )
        text = (result.text or "").strip()
        passed, log = validator(fake_audit_row, text)
        attempts.append({
            "attempt": attempt_idx, "model": model,
            "input_tokens": int(result.input_tokens),
            "output_tokens": int(result.output_tokens),
            "cost_usd": cost,
            "passed_strict": passed,
            "candidate_target": text,
        })
        if passed:
            accepted_target = text
            break
    return {
        "infill_id": fake_audit_row["id"],
        "k": k,
        "cas_expression": source_cas,
        "new_target": accepted_target,
        "accepted": accepted_target is not None,
        "n_attempts": len(attempts),
        "attempts": attempts,
    }


def _parse_k(source_cas: str) -> Optional[list[int]]:
    """Extract k-values from a Phi<...> string."""
    af = _load_audit_fractal()
    pkg_inf = sys.modules.get("cas_native.inference.fractal_repair")
    if pkg_inf is None:
        from cas_native.inference.fractal_repair import parse_fractal
    else:
        parse_fractal = pkg_inf.parse_fractal
    seq = parse_fractal(source_cas)
    return list(seq.k_values) if seq else None


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_outputs(
    *,
    results: list[dict],
    timestamp: str,
    dry_run: bool,
    summary_extra: dict,
) -> dict[str, Path]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "_dryrun" if dry_run else ""
    paths = {
        "clean": DATA_DIR / f"v1d_infill_long_fractal_clean_{timestamp}{suffix}.jsonl",
        "rejects": DATA_DIR / f"v1d_infill_long_fractal_rejects_{timestamp}{suffix}.jsonl",
        "summary": DATA_DIR / f"v1d_infill_long_fractal_summary_{timestamp}{suffix}.json",
    }
    accepted = [r for r in results if r["accepted"]]
    rejects = [r for r in results if not r["accepted"]]
    with paths["clean"].open("w", encoding="utf-8") as fh:
        for r in accepted:
            row = {
                "id": r["infill_id"],
                "v1mix_task_type": "cas_to_english",
                "v1mix_grammar_category_or_error_class": "fractal_sequence",
                "cas_expression": r["cas_expression"],
                "reply_text": r["new_target"],
                "regen_n_attempts": r["n_attempts"],
                "v1d_infill_k": r["k"],
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with paths["rejects"].open("w", encoding="utf-8") as fh:
        for r in rejects:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary = {
        "timestamp": timestamp,
        "dry_run": dry_run,
        "total_planned": len(results),
        "accepted": len(accepted),
        "rejected": len(rejects),
        "by_k": {
            str(k): {
                "planned": sum(1 for r in results if r["k"] == k),
                "accepted": sum(1 for r in accepted if r["k"] == k),
            }
            for k in (6, 7, 8)
        },
        **summary_extra,
    }
    paths["summary"].write_text(
        json.dumps(summary, indent=2), encoding="utf-8",
    )
    return paths


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="C: long-fractal infill for v1d.",
    )
    parser.add_argument("--paid", action="store_true")
    parser.add_argument("--yes-i-am-sure", action="store_true")
    parser.add_argument(
        "--target-per-k", type=int, default=30,
        help="Net-new accepted rows targeted per k bucket (k=6/7/8). "
        "Default 30 = 90 rows total target.",
    )
    parser.add_argument(
        "--max-retries", type=int, default=3,
        help="Retries per row before giving up.",
    )
    parser.add_argument(
        "--cost-cap-usd", type=float, default=5.0,
        help="Hard cap on spend (default $5).",
    )
    parser.add_argument(
        "--model", type=str, default="claude-haiku-4-5-20251001",
    )
    parser.add_argument("--seed", type=int, default=20260510)
    args = parser.parse_args()

    dry_run = not args.paid
    if args.paid and not args.yes_i_am_sure:
        print("[gate] --paid requires --yes-i-am-sure. Forcing dry-run.")
        dry_run = True

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"v1d long-fractal infill — timestamp {timestamp}")
    print(f"mode: {'DRY-RUN' if dry_run else 'PAID'}")
    print(
        f"target-per-k: {args.target_per_k} (planned k=6+k=7+k=8 "
        f"= {3*args.target_per_k} rows)"
    )
    print(f"model: {args.model}, max_retries: {args.max_retries}, "
          f"cost_cap_usd: {args.cost_cap_usd}")
    print()

    plan = plan_infill(target_per_k=args.target_per_k, seed=args.seed)
    print(f"Plan: {len(plan)} candidate rows")
    print(
        f"  k=6: {sum(1 for k,_ in plan if k==6)}, "
        f"k=7: {sum(1 for k,_ in plan if k==7)}, "
        f"k=8: {sum(1 for k,_ in plan if k==8)}"
    )
    print()

    # Estimated spend (Haiku ~$0.0019/row at our usage)
    est_per_row = 0.0019 * 2.0  # 2x retry overhead
    est_total = est_per_row * len(plan)
    print(f"Estimated spend: ${est_total:.2f} (cap ${args.cost_cap_usd:.2f})")
    print()

    # Show a sample prompt
    if dry_run and plan:
        print("--- sample prompt ---")
        regen = _load_regen()
        k, src = plan[0]
        s, u = regen.build_fractal_prompt({
            "cas_expression": src,
            "k_values": _parse_k(src),
        })
        print(f"  source: {src}")
        for ln in u[:300].splitlines():
            print(f"  {ln}")
        print()
        # Write planned-summary file
        results_dryrun = [
            {
                "infill_id": f"v1d_infill_dryrun_{i}",
                "k": k, "cas_expression": src,
                "new_target": None, "accepted": False,
                "n_attempts": 0, "attempts": [],
            }
            for i, (k, src) in enumerate(plan)
        ]
        paths = write_outputs(
            results=results_dryrun, timestamp=timestamp,
            dry_run=True,
            summary_extra={
                "estimated_spend_usd": round(est_total, 4),
                "model": args.model,
                "max_retries": args.max_retries,
            },
        )
        print("Dry-run artifacts:")
        for k, v in paths.items():
            print(f"  {k}: {v}")
        return 0

    # Paid path
    phase1 = _load_phase1()
    api_key = phase1.load_api_key()
    if not api_key:
        print("[error] no Anthropic API key.")
        return 2
    client = phase1.AnthropicClient(api_key)
    cost_tracker = phase1.CostTracker(cost_cap_usd=args.cost_cap_usd)
    regen = _load_regen()
    validator = regen.make_validator("fractal")

    results: list[dict] = []
    for i, (k, src) in enumerate(plan, 1):
        if cost_tracker.would_exceed(projected_call_cost=0.05):
            print(f"[cap] would exceed cap; stopping at row {i-1}/{len(plan)}.")
            break
        try:
            r = generate_one_row(
                source_cas=src, k=k, client=client,
                cost_tracker=cost_tracker, validator=validator,
                model=args.model, max_retries=args.max_retries,
                dry_run=False,
            )
        except Exception as exc:
            r = {
                "infill_id": f"err_{i}", "k": k, "cas_expression": src,
                "new_target": None, "accepted": False,
                "n_attempts": 0, "attempts": [],
                "error": f"{type(exc).__name__}: {exc}",
            }
        results.append(r)
        if i % 15 == 0 or i == len(plan):
            accepted = sum(1 for x in results if x["accepted"])
            print(
                f"  [{i}/{len(plan)}] accepted={accepted}, "
                f"spend=${cost_tracker.total_cost_usd:.3f}"
            )

    paths = write_outputs(
        results=results, timestamp=timestamp, dry_run=False,
        summary_extra={
            "spend_usd": round(cost_tracker.total_cost_usd, 4),
            "model": args.model,
            "max_retries": args.max_retries,
        },
    )
    print()
    print(f"Total spend: ${cost_tracker.total_cost_usd:.3f}")
    for k, v in paths.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
