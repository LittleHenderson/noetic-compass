"""Allocate a new task-owned pytest temp directory; execute only on admitted AWS."""
from pathlib import Path
from uuid import uuid4


def pytest_configure(config):
    if config.option.basetemp is None:
        root = Path(__file__).resolve().parent / ".test_tmp"
        root.mkdir(exist_ok=True)
        config.option.basetemp = str(root / uuid4().hex)
