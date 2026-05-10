"""One-off: k=7/k=8 follow-up infill (30 each).

Reuses generate_v1d_long_fractal_infill internals but skips k=6
(which already cleared the >=25 threshold). Different seed than
the first round so we don't regenerate identical sources.
"""
from __future__ import annotations

import importlib.util
import random
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "cas-synthetic" / "scripts"
SCAFFOLD_ROOT = REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass"

pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(SCAFFOLD_ROOT / "cas-native")]
sys.modules.setdefault("cas_native", pkg)
sys.path.insert(0, str(SCAFFOLD_ROOT))


def _load(name: str, fname: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / fname)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def main() -> int:
    infill = _load("infill_mod", "generate_v1d_long_fractal_infill.py")
    phase1 = _load("p1_mod", "generate_path_d_wave3_smoke.py")
    regen = _load("rg_mod", "build_v1d_targeted_regen.py")

    rng = random.Random(20260511)
    plan: list[tuple[int, str]] = []
    for k in (7, 8):
        n_repeat = 18
        n_unique = 12
        for _ in range(n_unique):
            seq = infill.generate_diverse_k_sequence(
                k, allow_repeats=False, rng=rng,
            )
            notation = "Φ" if rng.random() < 0.5 else "Phi"
            plan.append((k, infill.build_source_cas(seq, notation)))
        for _ in range(n_repeat):
            seq = infill.generate_diverse_k_sequence(
                k, allow_repeats=True, rng=rng,
            )
            notation = "Φ" if rng.random() < 0.5 else "Phi"
            plan.append((k, infill.build_source_cas(seq, notation)))
    rng.shuffle(plan)
    print(f"Plan: {len(plan)} candidates")
    print(
        f"  k=7: {sum(1 for k,_ in plan if k==7)}, "
        f"k=8: {sum(1 for k,_ in plan if k==8)}"
    )

    api_key = phase1.load_api_key()
    if not api_key:
        print("[error] no API key")
        return 2
    client = phase1.AnthropicClient(api_key)
    cost_tracker = phase1.CostTracker(cost_cap_usd=2.0)
    validator = regen.make_validator("fractal")

    results: list[dict] = []
    for i, (k, src) in enumerate(plan, 1):
        if cost_tracker.would_exceed(projected_call_cost=0.05):
            print(f"[cap] stopping at {i-1}/{len(plan)}")
            break
        r = infill.generate_one_row(
            source_cas=src, k=k, client=client,
            cost_tracker=cost_tracker, validator=validator,
            model="claude-haiku-4-5-20251001",
            max_retries=3, dry_run=False,
        )
        results.append(r)
        if i % 15 == 0 or i == len(plan):
            n_acc = sum(1 for x in results if x["accepted"])
            print(
                f"  [{i}/{len(plan)}] accepted={n_acc}, "
                f"spend=${cost_tracker.total_cost_usd:.3f}"
            )

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    paths = infill.write_outputs(
        results=results, timestamp=ts, dry_run=False,
        summary_extra={
            "spend_usd": round(cost_tracker.total_cost_usd, 4),
            "model": "claude-haiku-4-5-20251001",
            "max_retries": 3,
            "round": "k7_k8_followup",
        },
    )
    print(f"\nTotal spend: ${cost_tracker.total_cost_usd:.3f}")
    for k, v in paths.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
