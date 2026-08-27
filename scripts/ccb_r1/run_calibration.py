#!/usr/bin/env python3
"""Run a calibration gate against a cloud model and record the result.

    python scripts/ccb_r1/run_calibration.py --kind honesty --provider deepseek

Baseline only. There is no board or wrapper in this script, because
`calibration.calibrate` has no parameter through which one could be passed —
P5's blindness is a property of that signature, and this runner does not work
around it.

What it adds over calling `calibrate` directly:

* **Keys are read the way the product reads them.** `NC_<PROVIDER>_API_KEY`
  first, then the bare name, matching `api/config.py`'s AliasChoices, and a
  `.env` alongside it is loaded if present. Nothing is printed, logged, or
  written to the result file.
* **Concurrency without touching the gate.** Generation is deterministic, so
  the runner builds each attempt's set itself, fetches every prompt through a
  thread pool, then hands `calibrate` a scorer backed by that cache. The gate
  runs its own sequential loop over an identical set and every lookup is a hit.
  A fingerprint check asserts the sets really are identical rather than
  assuming it.
* **The result is evidence, not scrollback.** JSON carrying the procedure
  fingerprint, every attempt's set fingerprint, rate, interval and verdict, the
  unparseable count, and the pinned provider/model/temperature the
  specification requires. A run whose provider config differs from the
  registered one is a different experiment.

**Transport policy.** Cloud only. Local CPU inference is refused here, not just
discouraged in prose: sustained CPU inference was a suspected crash trigger,
and a run that takes the machine down loses the run and the machine.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from calibration import (  # noqa: E402
    GenerationProcedure,
    calibrate,
    default_procedure,
    hard_procedure,
    honesty_procedure,
)
from runners import (  # noqa: E402
    AnthropicCompletion,
    OpenAICompatCompletion,
    ScoreLog,
    score_deduction,
    score_honesty,
)


@dataclass(frozen=True)
class Provider:
    key_env: tuple[str, ...]
    base_url: str
    default_model: str
    anthropic: bool = False


#: Cloud endpoints only. `OllamaCompletion` and `HFCausalCompletion` exist in
#: `runners.py` for a future GPU host and are deliberately unreachable from
#: here — see the transport policy above.
PROVIDERS: dict[str, Provider] = {
    "deepseek": Provider(("NC_DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY"),
                         "https://api.deepseek.com/v1", "deepseek-chat"),
    "openai": Provider(("NC_OPENAI_API_KEY", "OPENAI_API_KEY"),
                       "https://api.openai.com/v1", "gpt-4o-mini"),
    "xai": Provider(("NC_XAI_API_KEY", "XAI_API_KEY"),
                    "https://api.x.ai/v1", "grok-2-latest"),
    "qwen": Provider(("NC_QWEN_API_KEY", "QWEN_API_KEY"),
                     "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
    "anthropic": Provider(("NC_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
                          "https://api.anthropic.com", "claude-sonnet-4-5", anthropic=True),
}

LADDERS = {"default": default_procedure, "hard": hard_procedure}


def load_dotenv(path: Path) -> int:
    """Minimal .env loader — the keys live in a file, not the shell.

    Existing environment wins, so an explicit export is never overridden by a
    stale file. Values are not echoed anywhere.
    """
    if not path.is_file():
        return 0
    loaded = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name, value = name.strip(), value.strip().strip("'\"")
        if name and name not in os.environ:
            os.environ[name] = value
            loaded += 1
    return loaded


def resolve_key(provider: Provider) -> str:
    for name in provider.key_env:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise SystemExit(
        f"none of {', '.join(provider.key_env)} is set. "
        "Point --env-file at the .env that holds it, or export it."
    )


def build_completion(provider: Provider, model: str, timeout: float):
    key = resolve_key(provider)
    env_name = next(n for n in provider.key_env if os.environ.get(n, "").strip())
    del key  # resolved only to fail fast; the transports read it themselves
    if provider.anthropic:
        return AnthropicCompletion(model=model, base_url=provider.base_url,
                                   api_key_env=env_name, max_tokens=16, timeout=timeout)
    return OpenAICompatCompletion(model=model, base_url=provider.base_url,
                                  api_key_env=env_name, max_tokens=16, timeout=timeout)


def fetch_all(completion, prompts: list[str], workers: int, retries: int) -> dict[str, str]:
    """Every prompt once, concurrently, with bounded retry.

    A failed prompt resolves to empty text rather than aborting the run: the
    scorers already treat unreadable output as wrong, and `unparseable` in the
    result file is what tells you a low score was transport trouble rather than
    model behaviour.
    """
    def one(prompt: str) -> tuple[str, str]:
        for attempt in range(retries + 1):
            try:
                return prompt, completion(prompt)
            except Exception:  # noqa: BLE001 - any transport failure is retryable
                if attempt == retries:
                    return prompt, ""
                time.sleep(2 ** attempt)
        return prompt, ""  # pragma: no cover - loop always returns

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(one, prompts))


def run(procedure: GenerationProcedure, completion, *, workers: int, retries: int,
        verbose: bool):
    """Prefetch each attempt's replies, then let the gate score them.

    The cache is keyed on prompt text. Because generation is deterministic the
    gate rebuilds an identical set, so every lookup hits — asserted below
    rather than assumed.
    """
    cache: dict[str, str] = {}
    log = ScoreLog()
    fingerprints: list[str] = []

    for attempt in range(len(procedure.schedule)):
        task_set = procedure.build(attempt)
        fingerprints.append(task_set.fingerprint())
        prompts = [item.prompt() for item in task_set.items]
        if verbose:
            print(f"fetching attempt {attempt + 1} "
                  f"[{task_set.difficulty.label()}] — {len(prompts)} prompt(s)",
                  file=sys.stderr)
        cache.update(fetch_all(completion, prompts, workers, retries))

    misses: list[str] = []

    def scorer(item) -> bool:
        prompt = item.prompt()
        if prompt not in cache:
            misses.append(item.item_id)
            return False
        reply = cache[prompt]
        if procedure.kind == "honesty":
            return score_honesty(item, reply, log)
        return score_deduction(item, reply, log)

    result = calibrate(procedure, scorer)
    if misses:
        raise SystemExit(
            f"{len(misses)} item(s) missed the prefetch cache — the gate scored a "
            "different set than was fetched; this run is void"
        )
    for attempt, expected in zip(result.attempts, fingerprints):
        if attempt.task_fingerprint != expected:
            raise SystemExit(f"attempt {attempt.index + 1} fingerprint drifted; run is void")
    return result, log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kind", choices=("deduction", "honesty"), default="honesty")
    parser.add_argument("--provider", choices=sorted(PROVIDERS), default="deepseek")
    parser.add_argument("--model", default=None, help="defaults to the provider's")
    parser.add_argument("--ladder", choices=sorted(LADDERS), default="default",
                        help="deduction only; honesty has one schedule")
    parser.add_argument("--n", type=int, default=120)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--env-file", type=Path,
                        default=Path("noetic-compass-scaffold/noetic-compass/.env"))
    parser.add_argument("--out", type=Path, default=None, help="write the result as JSON")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    load_dotenv(args.env_file)
    provider = PROVIDERS[args.provider]
    model = args.model or provider.default_model

    if args.kind == "honesty":
        procedure = honesty_procedure(n=args.n)
    else:
        procedure = LADDERS[args.ladder](n=args.n)

    completion = build_completion(provider, model, args.timeout)
    result, log = run(procedure, completion, workers=args.workers,
                      retries=args.retries, verbose=not args.quiet)

    print(result.summary())
    print(log.summary())
    if log.unparseable:
        print(f"WARNING: {log.unparseable_rate:.1%} of replies were unreadable — "
              "read that before reading the score", file=sys.stderr)

    if args.out:
        payload = {
            "kind": procedure.kind,
            "procedure": procedure.name,
            "procedure_fingerprint": procedure.fingerprint(),
            # The pinning the specification requires: "DeepSeek" is not a
            # specification; provider, model and temperature are.
            "provider": args.provider,
            "model": model,
            "temperature": 0.0,
            "n": args.n,
            "band": list(procedure.band),
            "chance": procedure.chance,
            "status": result.status,
            "accepted": result.ok,
            "accepted_fingerprint": result.accepted.fingerprint() if result.ok else None,
            "scored": log.scored,
            "unparseable": log.unparseable,
            "abstained": log.abstained,
            "attempts": [
                {
                    "index": a.index + 1,
                    "difficulty": a.difficulty.label(),
                    "seed": a.seed,
                    "task_fingerprint": a.task_fingerprint,
                    "correct": a.correct,
                    "n": a.n,
                    "rate": a.rate,
                    "ci_low": a.interval.low,
                    "ci_high": a.interval.high,
                    "verdict": a.verdict,
                }
                for a in result.attempts
            ],
        }
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.out}")

    return 0 if result.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
