"""Check one-to-one coverage between manuscript figure markers and TikZ assets."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


BOOK = Path(__file__).resolve().parent.parent
MS = BOOK / "manuscript"
FIGDIR = BOOK / "build" / "figures"
MARKER_RE = re.compile(r"\[\[FIGURE\s+([0-9]+)-([A-Z]):")
ASSET_RE = re.compile(r"^fig_([0-9]+)_([A-Z])\.tex$")


def key(chapter: str, letter: str) -> str:
    return f"{int(chapter):02d}-{letter}"


def main() -> int:
    markers: list[str] = []
    for path in sorted(MS.glob("ch[0-2][0-9]_*.md")):
        markers.extend(key(*match) for match in MARKER_RE.findall(
            path.read_text(encoding="utf-8")
        ))

    assets: list[str] = []
    for path in sorted(FIGDIR.glob("fig_*.tex")):
        match = ASSET_RE.match(path.name)
        if match:
            assets.append(key(*match.groups()))

    marker_counts = Counter(markers)
    duplicates = sorted(k for k, count in marker_counts.items() if count > 1)
    missing = sorted(set(markers) - set(assets))
    orphan = sorted(set(assets) - set(markers))

    print(f"figure markers    : {len(markers)} ({len(set(markers))} unique)")
    print(f"figure assets     : {len(assets)} ({len(set(assets))} unique)")
    print(f"missing assets    : {len(missing)}")
    print(f"orphan assets     : {len(orphan)}")
    print(f"duplicate markers : {len(duplicates)}")

    for label, values in (
        ("MISSING", missing),
        ("ORPHAN", orphan),
        ("DUPLICATE", duplicates),
    ):
        if values:
            print(f"{label}: {', '.join(values)}")

    return 1 if missing or orphan or duplicates else 0


if __name__ == "__main__":
    raise SystemExit(main())
