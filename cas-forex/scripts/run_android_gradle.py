"""Run the CAS Forex Android Gradle wrapper cross-platform."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    task_args = args or ["assembleDebug"]
    root = Path(__file__).resolve().parent.parent
    android_dir = root / "ui" / "android"
    wrapper = android_dir / ("gradlew.bat" if os.name == "nt" else "gradlew")
    if not wrapper.exists():
        print(f"Gradle wrapper not found at {wrapper}", file=sys.stderr)
        return 1
    completed = subprocess.run([str(wrapper), *task_args], cwd=android_dir)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
