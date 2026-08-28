"""Task Difficulty Grade: nine axes, DI index, D0-D10 banding, floors."""

from __future__ import annotations

from typing import Dict, List

AXES = (
    "depth", "branching", "memory", "recursion", "novelty",
    "uncertainty", "learning", "environment", "adversarial",
)

AXIS_LABELS = {
    "depth": "Reasoning depth",
    "branching": "Branching",
    "memory": "Memory burden",
    "recursion": "Recursion",
    "novelty": "Novelty",
    "uncertainty": "Uncertainty",
    "learning": "Learning requirement",
    "environment": "Environment/tool burden",
    "adversarial": "Adversarial pressure",
}

BANDS = [
    (0, 2, "D0", "Direct"),
    (3, 5, "D1", "Simple"),
    (6, 8, "D2", "Basic"),
    (9, 11, "D3", "Compositional"),
    (12, 14, "D4", "Deliberative"),
    (15, 17, "D5", "Stateful"),
    (18, 20, "D6", "Recursive"),
    (21, 23, "D7", "Robust"),
    (24, 26, "D8", "Adaptive"),
    (27, 30, "D9", "Evolutionary"),
    (31, 36, "D10", "Frontier"),
]

HARD_FLOORS = [
    ("branching", 2, "D4", "multiple genuine candidate branches"),
    ("memory", 2, "D5", "durable memory required"),
    ("recursion", 2, "D6", "nested subgoal and parent resumption"),
    ("environment", 2, "D7", "tool use under uncertainty"),
    ("learning", 2, "D8", "learning plus held-out transfer"),
]

FLOOR_FOR_NOVEL_RESEARCH = "D10"


def difficulty_index(axes: Dict[str, int]) -> int:
    if any(axis not in axes for axis in AXES):
        raise ValueError("difficulty axes must cover all nine dimensions")
    for axis, value in axes.items():
        if not 0 <= value <= 4:
            raise ValueError(f"axis '{axis}' out of range: {value}")
    return sum(axes.values())


def band_for(index: int) -> str:
    for low, high, grade, label in BANDS:
        if low <= index <= high:
            return grade
    raise ValueError(f"difficulty index {index} out of 0..36")


def hard_floor(axes: Dict[str, int], novel_research: bool = False,
                self_modification: bool = False) -> str:
    """The minimum grade forced by task properties, regardless of DI.

    Changing its own strategy or architecture is a TASK property (a
    D9 floor), not an axis value; novel research is a D10 floor.
    """
    floor_index = 0
    for axis, threshold, grade, _ in HARD_FLOORS:
        if axes.get(axis, 0) >= threshold:
            floor_index = max(floor_index, int(grade[1:]))
    if self_modification:
        floor_index = max(floor_index, 9)
    if novel_research:
        floor_index = 10
    return f"D{floor_index}"


def grade_task(axes: Dict[str, int], novel_research: bool = False,
               self_modification: bool = False) -> Dict:
    index = difficulty_index(axes)
    raw_grade = band_for(index)
    floor = hard_floor(axes, novel_research, self_modification)
    final = floor if int(floor[1:]) > int(raw_grade[1:]) else raw_grade
    return {
        "di": index,
        "raw_grade": raw_grade,
        "hard_floor": floor,
        "grade": final,
        "axes": dict(axes),
        "novel_research": novel_research,
        "self_modification": self_modification,
    }
