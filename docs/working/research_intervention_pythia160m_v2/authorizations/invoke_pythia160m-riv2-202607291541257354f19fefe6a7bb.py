"""One-shot launcher for the owner-authorized Pythia-160M V2 run."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(
    r"C:\Users\wakil\.codex\worktrees\f939\tksCAS"
)
EXECUTOR_PATH = REPO_ROOT / (
    "noetic-compass-scaffold/noetic-compass/api/services/"
    "cas_harness_pythia160m_research_executor.py"
)
LOCK_PATH = REPO_ROOT / (
    "docs/working/research_intervention_pythia160m_v2/"
    "PYTHIA160M_RESEARCH_SUCCESSOR_LOCK_V2.json"
)
RECEIPT_PATH = REPO_ROOT / (
    "docs/working/research_intervention_pythia160m_v2/authorizations/"
    "pythia160m-riv2-202607291541257354f19fefe6a7bb.json"
)
OUTPUT_ROOT = REPO_ROOT / (
    "docs/working/research_intervention_pythia160m_v2/runs/"
    "pythia160m-riv2-202607291541257354f19fefe6a7bb"
)


spec = importlib.util.spec_from_file_location(
    "authorized_pythia160m_v2_executor", EXECUTOR_PATH
)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load exact Pythia V2 executor")
executor = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = executor
spec.loader.exec_module(executor)

raise SystemExit(
    executor.execute_authorized_run(
        repo_root=REPO_ROOT,
        lock_path=LOCK_PATH,
        receipt_path=RECEIPT_PATH,
        output_root=OUTPUT_ROOT,
    )
)
