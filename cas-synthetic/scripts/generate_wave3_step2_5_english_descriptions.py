"""Wave 2.5 step — pre-generate English descriptions from seed CAS expressions.

This step bridges phase-1 cas_to_english (which generates English from CAS)
and phase-2 english_to_cas (which translates English back to CAS without
seeing the source CAS, fixing the verbatim-copy parrot defect from phase 1).

The pipeline is:

  1. Stratified-sample N seed CAS expressions from
     ``cas-synthetic/data/path_d/seeds.jsonl``.

  2. For each seed, build the v2 ``cas_to_english`` prompt (which has the
     coefficient + Ω + fractal-k preservation rules patched in).

  3. Call the model and validate every output against the v2 content-
     preservation validators (recipe + fractal). Reject failures inline.

  4. Write accepted records to
     ``cas-synthetic/data/path_d/wave3_step2_5_english_descriptions_<ts>.jsonl``
     with fields:
       seed_id
       source_cas
       grammar_category
       english_description
       prompt_template_version
       validators_run
       validators_passed
       validators_failed_reasons
       model_used
       raw_response
       input_tokens
       output_tokens
       estimated_cost_usd
       generated_at

The Wave 3 v2 ``english_to_cas`` slot then reads this file and uses the
``english_description`` field as the input to translate back to CAS.

Seed-pool decision (documented per task spec deliverable 3):
- Seed pool for Wave 2.5 is DISJOINT from the seed pool used for Wave 3 v2
  ``cas_to_english``. Reason: a fully shared pool would let the model see
  both directions during training (CAS→English and English→CAS) on the
  same surface form, which is closer to memorization than translation. A
  disjoint pool exercises the round-trip on distinct seed surface forms.
- The default split is 60% Wave 2.5 / 40% phase-2 cas_to_english (configurable
  via ``--wave2_5-fraction``). Selection is deterministic given ``--seed``.
- Note: this is a heuristic, not a validated decision. The first paid
  smoke run should compare exact-match round-trip rate on shared vs
  disjoint pools and confirm the disjoint pool is at least as good.

Hard constraints:
- Compiler-validated seeds only (the input file is already compiler-clean).
- API key from ANTHROPIC_API_KEY or NC_ANTHROPIC_API_KEY env var (or .env).
- Default ``--dry-run`` is on; paid execution requires BOTH ``--paid`` AND
  ``--yes-i-am-sure``. Without ``--yes-i-am-sure``, ``--paid`` prints the
  planned spend and exits without calling the API (this is the preflight).
- Default ``--cost-cap-usd`` 10.0 unless overridden. The cap is enforced
  per-call with a $0.05 reserve so a single in-flight call cannot push
  total spend over the cap.

Usage (dry run, no API):
  python cas-synthetic/scripts/generate_wave3_step2_5_english_descriptions.py \
      --seeds cas-synthetic/data/path_d/seeds.jsonl \
      --out-dir cas-synthetic/data/path_d \
      --target 50 \
      --dry-run

Usage (paid preflight, prints planned spend then exits, no API call):
  python cas-synthetic/scripts/generate_wave3_step2_5_english_descriptions.py \
      --seeds cas-synthetic/data/path_d/seeds.jsonl \
      --out-dir cas-synthetic/data/path_d \
      --target 200 \
      --cost-cap-usd 1.0 \
      --paid

Usage (paid execute — actually calls the API):
  python cas-synthetic/scripts/generate_wave3_step2_5_english_descriptions.py \
      --seeds cas-synthetic/data/path_d/seeds.jsonl \
      --out-dir cas-synthetic/data/path_d \
      --target 200 \
      --cost-cap-usd 1.0 \
      --paid \
      --yes-i-am-sure
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Optional


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_v2_module():
    name = "cas_synthetic_path_d_wave3_v2"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name,
        _REPO_ROOT / "cas-synthetic" / "scripts" / "generate_path_d_wave3_v2.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_phase1_module():
    """Load the phase-1 generator module to reuse AnthropicClient + CostTracker.

    We do not modify phase-1; we only import its classes. Loading this way
    (vs ``import``) keeps the import side-effect-free relative to the
    package layout: phase-1 is a script, not a package member.
    """
    name = "cas_synthetic_path_d_wave3_smoke_for_paid"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name,
        _REPO_ROOT / "cas-synthetic" / "scripts" / "generate_path_d_wave3_smoke.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def stratified_sample(
    items: list[dict[str, Any]],
    *,
    key: str,
    target_n: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Stratified sample by ``key``.

    Mirrors phase-1's stratified sampler shape so coverage across grammar
    categories is balanced.
    """
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for it in items:
        by_bucket[it.get(key, "_unknown")].append(it)
    buckets = sorted(by_bucket.keys())
    if not buckets:
        return []
    base_per_bucket = max(1, target_n // len(buckets))
    selected: list[dict[str, Any]] = []
    used_ids: set[int] = set()
    for b in buckets:
        pool = by_bucket[b]
        rng.shuffle(pool)
        take = min(base_per_bucket, len(pool))
        for it in pool[:take]:
            selected.append(it)
            used_ids.add(id(it))
    if len(selected) < target_n:
        rest = [it for it in items if id(it) not in used_ids]
        rng.shuffle(rest)
        for it in rest:
            if len(selected) >= target_n:
                break
            selected.append(it)
    rng.shuffle(selected)
    return selected[:target_n]


def split_seed_pool(
    seeds: list[dict[str, Any]],
    *,
    wave2_5_fraction: float,
    rng: random.Random,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition seeds into Wave 2.5 pool and Wave 3 cas_to_english pool.

    Disjoint by default. ``wave2_5_fraction`` ∈ (0,1) controls the split.
    Order-stable when ``rng`` has a fixed seed.
    """
    if not (0.0 < wave2_5_fraction < 1.0):
        raise ValueError(
            f"wave2_5_fraction must be in (0, 1), got {wave2_5_fraction}"
        )
    indexed = list(enumerate(seeds))
    rng.shuffle(indexed)
    split = int(len(indexed) * wave2_5_fraction)
    wave2_5_indices = sorted(i for i, _ in indexed[:split])
    cas_to_english_indices = sorted(i for i, _ in indexed[split:])
    return (
        [seeds[i] for i in wave2_5_indices],
        [seeds[i] for i in cas_to_english_indices],
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument(
        "--seeds",
        type=Path,
        default=_REPO_ROOT / "cas-synthetic" / "data" / "path_d" / "seeds.jsonl",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=_REPO_ROOT / "cas-synthetic" / "data" / "path_d",
    )
    p.add_argument("--target", type=int, default=50)
    p.add_argument(
        "--max-records",
        type=int,
        default=500,
        help="hard upper bound on records to generate in --paid mode "
        "(an extra safety belt on top of --target).",
    )
    p.add_argument(
        "--cost-cap",
        "--cost-cap-usd",
        dest="cost_cap_usd",
        type=float,
        default=5.0,
        help="hard cost cap in USD for --paid mode. --cost-cap-usd is "
        "retained as a back-compat alias.",
    )
    p.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        help="Anthropic model id for the Wave 2.5 translation slot. "
        "Defaults to claude-haiku-4-5-20251001 (the cheaper translation "
        "slot, matching phase-1 convention).",
    )
    p.add_argument("--seed", type=int, default=4242)
    p.add_argument(
        "--wave2_5-fraction",
        type=float,
        default=0.60,
        help="fraction of seed pool reserved for Wave 2.5 (the rest goes "
        "to Wave 3 v2 cas_to_english).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="default: don't call the API; emit synthetic English text "
        "fixtures for shape testing only.",
    )
    p.add_argument(
        "--paid",
        action="store_true",
        help="opt-in flag for paid execution. Disables --dry-run. The user "
        "must pass this explicitly; default is dry-run.",
    )
    p.add_argument(
        "--yes-i-am-sure",
        action="store_true",
        help="confirmation flag required to actually issue paid API calls. "
        "Without this flag, --paid prints the planned cost and exits "
        "without calling the API.",
    )
    return p.parse_args(argv)


def _build_paid_model_callable(
    *,
    client: Any,
    cost_tracker: Any,
    model: str,
    pricing: dict[str, tuple[float, float]],
    run_id: str,
    out_dir: Path,
):
    """Wrap an AnthropicClient call into the (system, user) -> (text, in, out)
    contract that ``v2.wave2_5_iterate`` expects.

    Side effects: updates ``cost_tracker`` and writes a per-call ledger
    line so the run is fully traceable. Raises ``RuntimeError`` when the
    cost cap would be exceeded — ``wave2_5_iterate`` records this as an
    errored record and continues to the next seed (the cap stays hard).
    """
    in_price, out_price = pricing[model]
    ledger_path = out_dir / f"wave3_step2_5_ledger_{run_id}.jsonl"

    def _ledger_append(entry: dict[str, Any]) -> None:
        with ledger_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def callable_(system: str, user: str) -> tuple[str, int, int]:
        # Reserve a per-call buffer so we cannot overshoot the cap mid-call.
        # 0.05 USD is comfortably above a single Haiku call (~$0.005) and
        # leaves slack even if Sonnet pricing applies. Without this, the
        # cap is checked against the *prior* total only, so one in-flight
        # call could push slightly over before the next pre-check fires.
        if cost_tracker.would_exceed(projected_call_cost=0.05):
            raise RuntimeError(
                f"cost cap exceeded (with $0.05 per-call reserve): "
                f"${cost_tracker.total_cost_usd:.4f} / "
                f"${cost_tracker.cost_cap_usd:.4f}"
            )
        result = client.call(
            model=model,
            system_prompt=system,
            user_message=user,
        )
        cost = cost_tracker.add(
            slot="wave2_5_cas_to_english",
            model=model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
        _ledger_append({
            "run_id": run_id,
            "model": model,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost_usd": round(cost, 6),
            "cumulative_cost_usd": round(cost_tracker.total_cost_usd, 6),
            "error_reason": result.error_reason,
        })
        if result.text is None:
            # The v2 iterate loop treats empty text as an error and writes
            # to reject_writer, so returning empty is safe.
            return "", result.input_tokens, result.output_tokens
        return result.text, result.input_tokens, result.output_tokens

    return callable_, ledger_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    v2 = _load_v2_module()
    rng = random.Random(args.seed)
    seeds = v2.load_jsonl(args.seeds)
    wave2_5_seeds, _cas_to_english_seeds = split_seed_pool(
        seeds, wave2_5_fraction=args.wave2_5_fraction, rng=rng
    )
    # In paid mode, --max-records is a hard upper bound on top of --target.
    target_n = min(args.target, args.max_records) if args.paid else args.target
    selected = stratified_sample(
        wave2_5_seeds,
        key="grammar_category",
        target_n=target_n,
        rng=random.Random(args.seed + 1),
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    ts = v2._timestamp_slug()
    run_id = uuid.uuid4().hex
    accept_path = (
        args.out_dir / f"wave3_step2_5_english_descriptions_{ts}.jsonl"
    )
    reject_path = (
        args.out_dir / f"wave3_step2_5_rejected_{ts}.jsonl"
    )
    manifest_path = (
        args.out_dir / f"wave3_step2_5_manifest_{ts}.json"
    )

    paid = bool(args.paid)
    confirmed = bool(args.yes_i_am_sure)

    # Confirmation prompt for paid mode. Without --yes-i-am-sure we print
    # the planned cost and exit cleanly; nothing has been spent.
    if paid and not confirmed:
        sys.stdout.write(
            f"About to run paid Wave 2.5 against {len(selected)} seeds with "
            f"cost cap ${args.cost_cap_usd:.2f} on model {args.model}. "
            f"Confirm with --yes-i-am-sure to proceed.\n"
        )
        return 0

    if paid and confirmed:
        phase1 = _load_phase1_module()
        api_key = phase1.load_api_key()
        if not api_key:
            sys.stderr.write(
                "[error] no Anthropic API key found. Set ANTHROPIC_API_KEY "
                "or NC_ANTHROPIC_API_KEY (env var or .env). Aborting "
                "without spending.\n"
            )
            return 2
        if args.model not in phase1.PRICING:
            sys.stderr.write(
                f"[error] model {args.model!r} has no pricing entry in "
                f"phase-1 PRICING table {sorted(phase1.PRICING.keys())}. "
                f"Add pricing or pick a known model. Aborting.\n"
            )
            return 2
        client = phase1.AnthropicClient(api_key)
        cost_tracker = phase1.CostTracker(cost_cap_usd=args.cost_cap_usd)
        model_callable, ledger_path = _build_paid_model_callable(
            client=client,
            cost_tracker=cost_tracker,
            model=args.model,
            pricing=phase1.PRICING,
            run_id=run_id,
            out_dir=args.out_dir,
        )
        in_price, out_price = phase1.PRICING[args.model]
        # Convert per-million pricing to per-token for v2.wave2_5_iterate's
        # ``estimated_cost_usd`` field on each accepted record.
        cost_per_in = in_price / 1_000_000.0
        cost_per_out = out_price / 1_000_000.0
        model_name_for_record = args.model
    else:
        # Dry run.
        def model_callable(system: str, user: str) -> tuple[str, int, int]:
            text = (
                "[DRY-RUN PLACEHOLDER] An English description that does "
                "not actually preserve coefficients or fractal k-indices."
            )
            return text, 1, 1

        cost_tracker = None
        ledger_path = None
        cost_per_in = 0.0
        cost_per_out = 0.0
        model_name_for_record = "dry-run"

    accept_fp = accept_path.open("w", encoding="utf-8")
    reject_fp = reject_path.open("w", encoding="utf-8")

    # Each accepted record gets traceability fields appended on top of the
    # base Wave2_5Record. Per feedback_traceability_is_the_whole_purpose.md.
    def accept_writer(rec: "v2.Wave2_5Record") -> None:
        record = rec.to_record()
        record["wave2_5_run_id"] = run_id
        accept_fp.write(json.dumps(record, ensure_ascii=False) + "\n")
        accept_fp.flush()

    def reject_writer(rec: dict[str, Any]) -> None:
        rec = dict(rec)
        rec["wave2_5_run_id"] = run_id
        reject_fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
        reject_fp.flush()

    counts = v2.wave2_5_iterate(
        selected,
        model_callable=model_callable,
        model_name=model_name_for_record,
        cost_per_in_token=cost_per_in,
        cost_per_out_token=cost_per_out,
        accept_writer=accept_writer,
        reject_writer=reject_writer,
    )
    accept_fp.close()
    reject_fp.close()

    manifest = {
        "started_at": v2._now_utc_iso(),
        "wave2_5_run_id": run_id,
        "args": {
            "seeds": str(args.seeds),
            "out_dir": str(args.out_dir),
            "target": args.target,
            "max_records": args.max_records,
            "wave2_5_fraction": args.wave2_5_fraction,
            "seed": args.seed,
            "dry_run": not paid,
            "paid": paid,
            "model": args.model if paid else None,
            "cost_cap_usd": args.cost_cap_usd if paid else None,
        },
        "counts": counts,
        "outputs": {
            "accepted": str(accept_path),
            "rejected": str(reject_path),
            "ledger": str(ledger_path) if ledger_path is not None else None,
        },
        "prompt_template_version": v2.WAVE_2_5_TEMPLATE_VERSION,
    }
    if paid and cost_tracker is not None:
        manifest["spend"] = {
            "total_cost_usd": round(cost_tracker.total_cost_usd, 6),
            "total_input_tokens": cost_tracker.total_input_tokens,
            "total_output_tokens": cost_tracker.total_output_tokens,
            "cost_cap_usd": cost_tracker.cost_cap_usd,
        }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    sys.stdout.write(
        json.dumps({"manifest": str(manifest_path), **counts}, indent=2) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
