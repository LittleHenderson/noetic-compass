"""Build the dependency-free CAS offline package.

Creates dist/cas-offline/ and dist/cas-offline.zip with:
  - cas.py
  - cas_svg.py
  - vendored api/notation/compiler.py and its CAS-Ohm helper
  - small launch helpers
"""

from __future__ import annotations

import shutil
import os
import stat
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "offline-cas"
NOETIC_ROOT = ROOT / "noetic-compass-scaffold" / "noetic-compass"
COMPILER = NOETIC_ROOT / "api" / "notation" / "compiler.py"
CAS_OHM = COMPILER.with_name("cas_ohm.py")
DIST = ROOT / "dist"
PACKAGE = DIST / "cas-offline"
STAGING = DIST / "_cas-offline-build"


def _safe_remove(path: Path) -> None:
    resolved = path.resolve()
    dist = DIST.resolve()
    if dist not in resolved.parents and resolved != dist:
        raise RuntimeError(f"refusing to remove path outside dist/: {resolved}")
    if resolved.exists():
        last_error: Exception | None = None
        for _ in range(6):
            try:
                shutil.rmtree(resolved)
                return
            except PermissionError as exc:
                last_error = exc
                _make_tree_writable(resolved)
                time.sleep(0.25)
        if last_error:
            raise last_error


def _make_tree_writable(path: Path) -> None:
    """Windows/OneDrive can leave generated files read-only after test runs."""
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            os.chmod(Path(root) / name, stat.S_IREAD | stat.S_IWRITE)
        for name in dirs:
            os.chmod(Path(root) / name, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    os.chmod(path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)


def _populate(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE / "cas.py", target / "cas.py")
    shutil.copy2(SOURCE / "cas_svg.py", target / "cas_svg.py")
    shutil.copy2(SOURCE / "cas_terminal.py", target / "cas_terminal.py")
    shutil.copy2(SOURCE / "README.md", target / "README.md")

    notation_dir = target / "api" / "notation"
    notation_dir.mkdir(parents=True)
    (target / "api" / "__init__.py").write_text("", encoding="utf-8")
    (notation_dir / "__init__.py").write_text(
        "from .compiler import CAS_GRAMMAR_BNF, compile_expression, compile_file\n"
        "__all__ = ['CAS_GRAMMAR_BNF', 'compile_expression', 'compile_file']\n",
        encoding="utf-8",
        newline="\n",
    )
    shutil.copy2(COMPILER, notation_dir / "compiler.py")
    shutil.copy2(CAS_OHM, notation_dir / "cas_ohm.py")

    (target / "cas.bat").write_bytes(b'@echo off\r\npython "%~dp0cas.py" %*\r\n')


def build() -> None:
    if not COMPILER.exists():
        raise FileNotFoundError(f"compiler not found: {COMPILER}")
    if not CAS_OHM.exists():
        raise FileNotFoundError(f"CAS-Ohm helper not found: {CAS_OHM}")

    DIST.mkdir(exist_ok=True)
    _safe_remove(STAGING)
    _populate(STAGING)

    archive = DIST / "cas-offline.zip"
    if archive.exists():
        archive.unlink()
    shutil.make_archive(str(archive.with_suffix("")), "zip", STAGING)

    try:
        _safe_remove(PACKAGE)
        shutil.copytree(STAGING, PACKAGE)
    except PermissionError as exc:
        PACKAGE.mkdir(parents=True, exist_ok=True)
        shutil.copytree(STAGING, PACKAGE, dirs_exist_ok=True)
        print(f"warning: refreshed {PACKAGE} by overlay because Windows held the directory root: {exc}")
    print(f"built: {PACKAGE}")
    print(f"zip:   {archive}")


if __name__ == "__main__":
    build()
