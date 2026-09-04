"""Access the trace transport schema from source trees and installed wheels."""

from __future__ import annotations

from importlib.resources import files
import json
from typing import Any


def load_trace_schema() -> dict[str, Any]:
    """Load a fresh copy of the packaged CASformer trace JSON Schema."""

    resource = files("casformer").joinpath("casformer_trace.schema.json")
    return json.loads(resource.read_text(encoding="utf-8"))

