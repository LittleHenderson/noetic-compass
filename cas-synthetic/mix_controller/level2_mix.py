"""Level 2 mix controller — authoritative 30/25/15/20/10 ratios.

Given a target count N, produces a sequence of GeneratedExample instances
with exactly the bucket distribution specified in the Level 2 directive:

  v7.4 baseline:      30% (e.g. 3000 of 10000)
  v7.5 register:      25% (e.g. 2500 of 10000)
  v7.7 Rule 4:        15% (e.g. 1500 of 10000) — 20% of these are violations
  v7.7 Ω_*:           20% (e.g. 2000 of 10000)
  v7.6 production:    10% (e.g. 1000 of 10000)

Rounding: floor for all buckets, with any remainder allocated to the
baseline bucket. This keeps total exactly = N.

Output order: interleaved, drawn with the RNG seed set, so downstream
shuffles are reproducible.

Supports checkpoint/resume: `generate_to_jsonl` can accept `resume_from`
to skip already-written examples and continue to target N.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from ..generator.base import GeneratedExample
from ..generator.v74_baseline import V74BaselineGenerator
from ..generator.v75_register import V75RegisterGenerator
from ..generator.v77_rule_four import V77RuleFourGenerator
from ..generator.v77_omega import V77OmegaGenerator
from ..generator.v76_production import V76ProductionGenerator


@dataclass
class Level2MixConfig:
    # Bucket fractions — authoritative, locked.
    v74_fraction: float = 0.30
    v75_fraction: float = 0.25
    v77_rule_four_fraction: float = 0.15
    v77_omega_fraction: float = 0.20
    v76_production_fraction: float = 0.10

    seed: int = 42
    llm_provider: Any = None
    shuffle: bool = True

    def fractions(self) -> dict[str, float]:
        return {
            "v74_baseline": self.v74_fraction,
            "v75_register": self.v75_fraction,
            "v77_rule_four": self.v77_rule_four_fraction,
            "v77_omega": self.v77_omega_fraction,
            "v76_production": self.v76_production_fraction,
        }

    def validate(self) -> None:
        total = sum(self.fractions().values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Mix fractions must sum to 1.0; got {total}")


class Level2MixController:
    def __init__(self, config: Level2MixConfig | None = None) -> None:
        self.config = config or Level2MixConfig()
        self.config.validate()

        seed = self.config.seed
        prov = self.config.llm_provider
        self.generators = {
            "v74_baseline": V74BaselineGenerator(seed=seed, llm_provider=prov),
            "v75_register": V75RegisterGenerator(seed=seed + 1, llm_provider=prov),
            "v77_rule_four": V77RuleFourGenerator(seed=seed + 2, llm_provider=prov),
            "v77_omega": V77OmegaGenerator(seed=seed + 3, llm_provider=prov),
            "v76_production": V76ProductionGenerator(seed=seed + 4, llm_provider=prov),
        }

    def bucket_sizes(self, n: int) -> dict[str, int]:
        """Integer bucket sizes summing to exactly n. Remainder goes to v74_baseline."""
        fractions = self.config.fractions()
        sizes = {k: int(round(v * n)) for k, v in fractions.items()}
        drift = n - sum(sizes.values())
        sizes["v74_baseline"] += drift  # correct rounding drift
        return sizes

    def iter_examples(self, n: int) -> Iterator[GeneratedExample]:
        """Stream n examples in interleaved bucket order."""
        sizes = self.bucket_sizes(n)
        import random as _random

        rng = _random.Random(self.config.seed + 7)

        # Build a shuffled list of bucket tags summing to n.
        tags: list[str] = []
        for bucket, count in sizes.items():
            tags.extend([bucket] * count)
        if self.config.shuffle:
            rng.shuffle(tags)

        # Each generator has its own RNG seeded separately; iterating in tag
        # order exhausts each generator one example at a time.
        iterators = {
            bucket: self.generators[bucket].iter_examples(sizes[bucket])
            for bucket in sizes
        }
        for tag in tags:
            yield next(iterators[tag])

    def generate_to_jsonl(
        self,
        output_path: str | Path,
        n: int,
        resume_from: int = 0,
        progress_every: int = 1000,
    ) -> dict[str, Any]:
        """Generate n examples and write to JSONL. Supports checkpoint/resume.

        When resume_from > 0, the first resume_from examples are drawn from
        the generators (to advance RNG state) but NOT written, and appending
        resumes at index resume_from. The output file is opened in append
        mode iff resume_from > 0.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if resume_from > 0 else "w"

        bucket_counts: dict[str, int] = {k: 0 for k in self.generators}
        written = 0
        skipped = 0

        with open(path, mode, encoding="utf-8") as f:
            for i, ex in enumerate(self.iter_examples(n)):
                if i < resume_from:
                    skipped += 1
                    continue
                f.write(json.dumps(ex.to_dict(), ensure_ascii=False) + "\n")
                bucket_counts[ex.bucket] = bucket_counts.get(ex.bucket, 0) + 1
                written += 1
                if progress_every and written % progress_every == 0:
                    print(f"  wrote {written}/{n - resume_from} (total target {n})")

        return {
            "target_n": n,
            "resume_from": resume_from,
            "written": written,
            "skipped": skipped,
            "bucket_counts": bucket_counts,
            "output_path": str(path),
        }
