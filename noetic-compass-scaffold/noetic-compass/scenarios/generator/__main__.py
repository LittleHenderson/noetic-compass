"""CLI for scenario generation and augmentation.

Usage:
    python -m scenarios.generator --augment --count 500
    python -m scenarios.generator --augment                  # all (base * 8)
    python -m scenarios.generator --stats                    # show library stats
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .augmentation import load_base_scenarios, augment_scenarios, save_augmented


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CAS Scenario Generator — inversion augmentation and stats"
    )
    parser.add_argument(
        "--augment", action="store_true",
        help="Generate augmented scenarios via 7-axis inversion",
    )
    parser.add_argument(
        "--count", type=int, default=None,
        help="Maximum number of augmented scenarios to generate",
    )
    parser.add_argument(
        "--output", type=str, default="scenarios/augmented_library.json",
        help="Output path for augmented library (default: scenarios/augmented_library.json)",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show statistics about the scenario library",
    )
    args = parser.parse_args()

    if not args.augment and not args.stats:
        parser.print_help()
        sys.exit(0)

    base = load_base_scenarios()
    print(f"Loaded {len(base)} base scenarios")

    if args.stats:
        print(f"\nBase Library Statistics:")
        print(f"  Total scenarios: {len(base)}")
        categories = {}
        for s in base:
            categories[s.category] = categories.get(s.category, 0) + 1
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count}")
        domains = {}
        for s in base:
            domains[s.target_domain] = domains.get(s.target_domain, 0) + 1
        print(f"\nDomain distribution:")
        for d, count in sorted(domains.items()):
            print(f"  {d}: {count}")
        projected = len(base) * 8  # base + 7 inversions
        print(f"\nProjected augmented size: {projected} ({len(base)} x 8)")

    if args.augment:
        print(f"\nAugmenting {len(base)} base scenarios across 7 inversion axes...")
        results = augment_scenarios(base, max_total=args.count)

        originals = sum(1 for r in results if r.get("is_original"))
        inverted = sum(1 for r in results if not r.get("is_original"))

        axis_counts = {}
        for r in results:
            if r.get("inversion_axis"):
                axis_counts[r["inversion_axis"]] = axis_counts.get(r["inversion_axis"], 0) + 1

        print(f"Generated {len(results)} scenarios:")
        print(f"  Originals: {originals}")
        print(f"  Inverted: {inverted}")
        for axis, count in sorted(axis_counts.items()):
            print(f"    {axis}-axis: {count}")

        save_augmented(results, args.output)
        print(f"\nSaved to: {args.output}")


if __name__ == "__main__":
    main()
