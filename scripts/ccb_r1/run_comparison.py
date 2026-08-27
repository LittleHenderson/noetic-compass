#!/usr/bin/env python3
"""Run Stage 5 end to end: the same model wrapped, bare, and compute-matched.

    python scripts/ccb_r1/run_comparison.py --provider deepseek --dry-run
    python scripts/ccb_r1/run_comparison.py --provider deepseek --out result.json

This is the piece that was missing. `run_calibration.py` measures a baseline
against the gate; every other module builds a part of the comparison. Nothing
joined them, so no result existed — not because anything was blocked, but
because the runner had not been written.

What it does, in the order `stage5.py` requires:

  1. build the three task sets and record their fingerprints
  2. pre-register thresholds and fingerprints, and record that fingerprint too
  3. run every arm on the identical items, in the identical order
  4. `verify()` — a set that is not the pre-registered one voids the run
  5. `run_stage5()` — judge M1, M2 and M3, reporting all three either way

Arms:

  wrapped     the model inside the Wrap Pipeline
  bare        the same model, no pipeline
  bare-CoT    the same model asked to reason step by step — the compute-matched
              control, because the wrapped arm spends an extra call per
              open-world item and a wrapped win could otherwise be architecture
              or simply more inference

Concurrency is per item, not per call: the wrapped pipeline decides its second
call based on the first, so a call-level prefetch cannot work here the way it
does for calibration. Each item runs its whole arm inside a worker.

**Cost is real.** `--dry-run` reports the call count and spends nothing. Read
it before spending anything.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flips import DEFAULT_BANDS, Outcome  # noqa: E402
from rpm import Terminal  # noqa: E402
from run_calibration import LADDERS, PROVIDERS, build_completion, load_dotenv  # noqa: E402
from runners import ScoreLog, score_deduction, score_honesty  # noqa: E402
from stage5 import PreRegistration, run_stage5, verify  # noqa: E402
from stats import MIN_PAIRED_N  # noqa: E402
from tasksets import (  # noqa: E402
    generate_firewall_pairs,
    generate_honesty_set,
)
from wrap import (  # noqa: E402
    DEFAULT_DIALS,
    bare_cot_deduction,
    bare_deduction,
    bare_firewall_pair,
    bare_honesty,
    wrap_deduction,
    wrap_firewall_pair,
    wrap_honesty,
)


@dataclass
class Counter:
    """Calls actually spent, per arm. The compute confound, measured."""

    calls: int = 0

    def wrap(self, completion):
        def counted(prompt: str) -> str:
            self.calls += 1
            return completion(prompt)
        return counted


@dataclass
class ArmScores:
    name: str
    scores: list[int] = field(default_factory=list)
    failures: int = 0
    log: ScoreLog = field(default_factory=ScoreLog)

    @property
    def rate(self) -> float:
        return sum(self.scores) / len(self.scores) if self.scores else 0.0


def _parallel(items, work, workers: int, retries: int):
    """Run `work(item)` per item, in order, with bounded retry.

    A permanently failing item resolves to None rather than aborting the run:
    the arms must stay aligned item for item or the paired statistics are
    meaningless, so a hole is recorded and counted, never dropped.
    """
    def one(item):
        for attempt in range(retries + 1):
            try:
                return work(item)
            except Exception:  # noqa: BLE001 - any transport failure is retryable
                if attempt == retries:
                    return None
                time.sleep(2 ** attempt)
        return None  # pragma: no cover

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, items))


def score_arm(name: str, items, answers, scorer) -> ArmScores:
    """Turn per-item answers into aligned 0/1 scores.

    A failed item scores 0 rather than being dropped. Dropping would silently
    shorten one arm, and `stats.paired_difference` would then raise on the
    length mismatch — correct, but it would void a run over something the
    result file should simply report.
    """
    arm = ArmScores(name)
    for item, answer in zip(items, answers):
        if answer is None:
            arm.failures += 1
            arm.scores.append(0)
            arm.log.scored += 1
            arm.log.unparseable += 1
            continue
        arm.scores.append(1 if scorer(item, answer, arm.log) else 0)
    return arm


def run_deduction(items, workers, retries, counter_wrapped, counter_bare, counter_cot):
    wrapped = _parallel(items, lambda i: wrap_deduction(counter_wrapped, i, DEFAULT_DIALS).answer,
                        workers, retries)
    bare = _parallel(items, lambda i: bare_deduction(counter_bare, i)[0], workers, retries)
    cot = _parallel(items, lambda i: bare_cot_deduction(counter_cot, i)[0], workers, retries)
    return (
        score_arm("wrapped", items, wrapped, score_deduction),
        score_arm("bare", items, bare, score_deduction),
        score_arm("bare-cot", items, cot, score_deduction),
    )


def run_honesty(items, workers, retries, counter_wrapped, counter_bare):
    wrapped = _parallel(items, lambda i: wrap_honesty(counter_wrapped, i, DEFAULT_DIALS).answer,
                        workers, retries)
    bare = _parallel(items, lambda i: bare_honesty(counter_bare, i)[0], workers, retries)
    return (
        score_arm("wrapped", items, wrapped, score_honesty),
        score_arm("bare", items, bare, score_honesty),
    )


def _pair_or_blank(result):
    if result is None:
        blank = Outcome(Terminal.NEEDS_INFORMATION)
        return blank, blank
    return result


def run_firewall(pairs, workers, retries, counter_wrapped, counter_bare):
    wrapped = _parallel(
        pairs, lambda p: wrap_firewall_pair(counter_wrapped, p, DEFAULT_DIALS)[:2],
        workers, retries,
    )
    bare = _parallel(pairs, lambda p: bare_firewall_pair(counter_bare, p), workers, retries)
    return (
        {p.pair_id: _pair_or_blank(r) for p, r in zip(pairs, wrapped)},
        {p.pair_id: _pair_or_blank(r) for p, r in zip(pairs, bare)},
    )


#: Calls each arm spends per item, for the dry-run estimate. The wrapped
#: honesty arm is 1 or 2 depending on whether the RPM gate releases, so the
#: estimate is an upper bound and says so.
CALLS_PER_ITEM = {
    "deduction wrapped": 1, "deduction bare": 1, "deduction bare-cot": 1,
    "honesty wrapped": 2, "honesty bare": 1,
    "firewall wrapped": 2, "firewall bare": 2,
}


def estimate(n: int) -> tuple[dict[str, int], int]:
    per_arm = {name: n * calls for name, calls in CALLS_PER_ITEM.items()}
    return per_arm, sum(per_arm.values())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--provider", choices=sorted(PROVIDERS), default="deepseek")
    parser.add_argument("--model", default=None)
    parser.add_argument("--n", type=int, default=MIN_PAIRED_N)
    parser.add_argument("--ladder", choices=sorted(LADDERS), default="hard",
                        help="'hard' by default: a strong model abandoned the "
                             "default ladder as TOO_EASY at every rung")
    parser.add_argument("--deduction-attempt", type=int, default=0,
                        help="which rung of the ladder to use (0-based)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--env-file", type=Path,
                        default=Path("noetic-compass-scaffold/noetic-compass/.env"))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true",
                        help="report the call count and spend nothing")
    args = parser.parse_args(argv)

    per_arm, total = estimate(args.n)
    if args.dry_run:
        print(f"n = {args.n} per criterion")
        for name, calls in per_arm.items():
            print(f"  {name:22} {calls:6,} call(s)")
        print(f"  {'TOTAL (upper bound)':22} {total:6,} call(s)")
        print("\nUpper bound: the wrapped honesty arm spends 1 call, not 2, "
              "whenever the RPM gate withholds.")
        return 0

    if args.n < MIN_PAIRED_N:
        raise SystemExit(
            f"n = {args.n} is below the registered floor of {MIN_PAIRED_N}; "
            "the criteria would be void, so this run is refused"
        )

    load_dotenv(args.env_file)
    provider = PROVIDERS[args.provider]
    model = args.model or provider.default_model
    completion = build_completion(provider, model, args.timeout)

    # 1. Build the sets.
    deduction_set = LADDERS[args.ladder](n=args.n).build(args.deduction_attempt)
    honesty_set = generate_honesty_set(args.n, 20260830)
    firewall_set = generate_firewall_pairs(args.n, 20260831)

    # 2. Pre-register before a single item is scored.
    prereg = PreRegistration(
        name=f"stage5-{args.provider}-{model}",
        deduction_fingerprint=deduction_set.fingerprint(),
        honesty_fingerprint=honesty_set.fingerprint(),
        firewall_fingerprint=firewall_set.fingerprint(),
    )
    print(f"pre-registration {prereg.fingerprint()[:16]}… "
          f"({args.provider}/{model}, n={args.n}, {total:,} calls upper bound)",
          file=sys.stderr)

    counters = {name: Counter() for name in
                ("d_wrapped", "d_bare", "d_cot", "h_wrapped", "h_bare",
                 "f_wrapped", "f_bare")}
    counted = {k: v.wrap(completion) for k, v in counters.items()}

    # 3. Run every arm on the identical items, in the identical order.
    d_wrapped, d_bare, d_cot = run_deduction(
        deduction_set.items, args.workers, args.retries,
        counted["d_wrapped"], counted["d_bare"], counted["d_cot"],
    )
    h_wrapped, h_bare = run_honesty(
        honesty_set.items, args.workers, args.retries,
        counted["h_wrapped"], counted["h_bare"],
    )
    f_wrapped, f_bare = run_firewall(
        firewall_set.items, args.workers, args.retries,
        counted["f_wrapped"], counted["f_bare"],
    )

    # 4. The sets must still be the pre-registered ones.
    verify(prereg, deduction_set, honesty_set, firewall_set)

    # 5. Judge. Every criterion is reported, pass or fail.
    report = run_stage5(
        prereg,
        honesty_board=h_wrapped.scores, honesty_baseline=h_bare.scores,
        deduction_board=d_wrapped.scores, deduction_baseline=d_bare.scores,
        firewall_results=f_wrapped,
    )

    print(report.summary())
    print()
    print(f"  deduction  wrapped {d_wrapped.rate:.1%}  bare {d_bare.rate:.1%}  "
          f"bare-CoT {d_cot.rate:.1%}   <- read CoT before crediting the pipeline")
    print(f"  honesty    wrapped {h_wrapped.rate:.1%}  bare {h_bare.rate:.1%}")
    print(f"  calls      {sum(c.calls for c in counters.values()):,} "
          f"(wrapped {counters['d_wrapped'].calls + counters['h_wrapped'].calls + counters['f_wrapped'].calls:,}, "
          f"bare {counters['d_bare'].calls + counters['h_bare'].calls + counters['f_bare'].calls:,})")

    arms = {"deduction": (d_wrapped, d_bare, d_cot), "honesty": (h_wrapped, h_bare)}
    for label, group in arms.items():
        for arm in group:
            if arm.log.unparseable:
                print(f"WARNING: {label}/{arm.name} — "
                      f"{arm.log.unparseable_rate:.1%} unreadable "
                      f"({arm.failures} transport failure(s)); read that before the score",
                      file=sys.stderr)

    if args.out:
        payload = {
            "provider": args.provider, "model": model, "temperature": 0.0,
            "n": args.n, "ladder": args.ladder,
            "deduction_difficulty": deduction_set.difficulty.label(),
            "prereg_fingerprint": prereg.fingerprint(),
            "deduction_fingerprint": deduction_set.fingerprint(),
            "honesty_fingerprint": honesty_set.fingerprint(),
            "firewall_fingerprint": firewall_set.fingerprint(),
            "passed": report.passed,
            "m1": {
                "cleared": report.honesty.cleared,
                "threshold": report.honesty.threshold,
                "point": report.honesty.interval.point,
                "ci_low": report.honesty.interval.low,
                "ci_high": report.honesty.interval.high,
                "wrapped_rate": h_wrapped.rate, "bare_rate": h_bare.rate,
            },
            "m2": {
                "passed": report.firewall.passed,
                "flips": report.firewall.flips,
                "pairs": report.firewall.pairs,
                "max_movement": report.firewall.max_movement,
                "ceiling": report.firewall.ceiling,
                "over_ceiling": len(report.firewall.over_ceiling),
            },
            "m3": {
                "cleared": report.deduction.cleared,
                "threshold": report.deduction.threshold,
                "point": report.deduction.interval.point,
                "ci_low": report.deduction.interval.low,
                "ci_high": report.deduction.interval.high,
                "wrapped_rate": d_wrapped.rate, "bare_rate": d_bare.rate,
                "bare_cot_rate": d_cot.rate,
            },
            "unparseable": {
                f"{label}/{arm.name}": arm.log.unparseable
                for label, group in arms.items() for arm in group
            },
            "transport_failures": {
                f"{label}/{arm.name}": arm.failures
                for label, group in arms.items() for arm in group
            },
            "calls": {name: c.calls for name, c in counters.items()},
        }
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")

    return 0 if report.passed else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
