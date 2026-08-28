"""Strategy memory: learned problem-solving procedures (ring R1).

A strategy is an ordered repair schedule for a fault class - the
procedure the machine follows when a fault of that class is diagnosed.
Entries are versioned content: provisional, then promoted under the
acceptance law; corrections version verified entries; the parent state
is always restorable.
"""

from __future__ import annotations

import copy
from typing import Dict, List, Optional


class StrategyError(Exception):
    pass


class StrategyMemory:
    def __init__(self) -> None:
        self.entries: Dict[str, Dict] = {}

    def add_provisional(self, fault_class: str, guard_order: List[str],
                        provenance: str = "prior_proof") -> Dict:
        if fault_class in self.entries:
            raise StrategyError(
                f"strategy for fault class '{fault_class}' already exists")
        entry = {
            "fault_class": fault_class,
            "guard_order": list(guard_order),
            "status": "provisional",
            "provenance": provenance,
            "revision": 1,
            "history": [],
        }
        self.entries[fault_class] = entry
        return entry

    def promote(self, fault_class: str) -> Dict:
        entry = self.entries.get(fault_class)
        if entry is None:
            raise StrategyError(f"no strategy for fault class '{fault_class}'")
        entry["history"].append({"revision": entry["revision"],
                                 "status": entry["status"],
                                 "guard_order": list(entry["guard_order"])})
        entry["status"] = "verified"
        entry["revision"] += 1
        return entry

    def lookup(self, fault_class: str) -> Optional[Dict]:
        return self.entries.get(fault_class)

    def snapshot(self) -> Dict:
        return copy.deepcopy(self.entries)

    def to_json(self) -> Dict:
        return copy.deepcopy(self.entries)
