"""Use only the manifest-materialized native dependency tree for these tests."""
import sys
from pathlib import Path
from uuid import uuid4

runtime = Path(__file__).resolve().parent / "_runtime"
if not (runtime / "cncm/compound_engine.py").is_file():
    raise RuntimeError("Run python research/cas_closed_loop_1/bootstrap_runtime.py first")
sys.dont_write_bytecode = True
sys.path.insert(0, str(runtime))
sys.path.insert(0, str(runtime.parent.parents[1]))


def pytest_configure(config):
    if config.option.basetemp is None:
        # Fresh task-owned path; pytest never scans or cleans the owner's temp tree.
        (runtime.parent / ".test_tmp").mkdir(exist_ok=True)
        config.option.basetemp = str(runtime.parent / ".test_tmp" / uuid4().hex)
