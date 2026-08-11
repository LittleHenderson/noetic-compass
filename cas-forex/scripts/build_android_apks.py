"""Build the CAS Forex Android debug and release APKs serially.

This intentionally builds the web bundle once, syncs Capacitor once, then runs
both Gradle APK tasks in one process. Running the separate npm debug/release
scripts at the same time can race while Vite clears ui/dist.
"""

from __future__ import annotations

import subprocess
import sys
from shutil import which
from pathlib import Path


def resolve_executable(name: str) -> str | None:
    resolved = which(name)
    if resolved:
        return resolved
    if sys.platform == "win32" and not name.lower().endswith(".cmd"):
        return which(f"{name}.cmd")
    return None


def run_step(label: str, command: list[str], *, cwd: Path) -> int:
    print(f"\n== {label} ==")
    executable = resolve_executable(command[0])
    if not executable:
        print(f"{label} failed: executable not found: {command[0]}", file=sys.stderr)
        return 1
    resolved_command = [executable, *command[1:]]
    print(" ".join(command))
    completed = subprocess.run(resolved_command, cwd=cwd)
    if completed.returncode != 0:
        print(f"{label} failed with exit code {completed.returncode}", file=sys.stderr)
    return int(completed.returncode)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    ui_dir = root / "ui"

    steps = [
        ("Build web/PWA bundle", ["npm", "run", "build"], ui_dir),
        ("Sync Capacitor Android", ["npx", "cap", "sync", "android"], ui_dir),
        (
            "Build debug and release APKs",
            [sys.executable, str(root / "scripts" / "run_android_gradle.py"), "assembleDebug", "assembleRelease"],
            root,
        ),
    ]

    for label, command, cwd in steps:
        result = run_step(label, command, cwd=cwd)
        if result != 0:
            return result

    print("\nCAS Forex Android APK build-all complete.")
    print(f"Debug APK: {root / 'ui' / 'android' / 'app' / 'build' / 'outputs' / 'apk' / 'debug' / 'app-debug.apk'}")
    print(f"Release APK: {root / 'ui' / 'android' / 'app' / 'build' / 'outputs' / 'apk' / 'release' / 'app-release.apk'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
