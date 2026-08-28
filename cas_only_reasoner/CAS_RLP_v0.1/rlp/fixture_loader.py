"""Load RLP parent packages from the fixtures directory."""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_package(name: str) -> dict:
    path = os.path.join(ROOT, "fixtures", name, "parent.json")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
