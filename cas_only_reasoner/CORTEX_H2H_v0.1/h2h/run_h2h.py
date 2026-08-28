"""The head-to-head orchestrator: run both routes over the identical
battery, twice each (determinism leg), grade with the one shared
grader, seal the results.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Callable, Dict, List

from .grade import (attestation, grade_breadth, grade_honesty,
                    grade_parse, grade_question)
from .route_a import RouteA, load_seed
from .tasks import (BREADTH, IN_FRAGMENT_PARSE, QUESTION_ANSWERING,
                    UNKNOWN_HONESTY, all_scored_sentences,
                    fewshot_sentences)


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _twice(fn: Callable[[str], Dict], sentence: str) -> Dict:
    first = fn(sentence)
    second = fn(sentence)
    return {"result": first, "deterministic": first == second}


def run(route_b=None) -> Dict:
    """route_b None = Route A only (used by the offline tests); pass a
    RouteB instance for the full head-to-head."""
    assert not set(all_scored_sentences()) & set(fewshot_sentences()), \
        "held-out violation: a scored item appears in the prompt"

    seed = load_seed()
    routes: Dict[str, Dict] = {}
    route_a = RouteA()
    contenders = [("route_a", route_a.parse, route_a.ask, route_a.parse)]
    if route_b is not None:
        contenders.append(("route_b", route_b.parse, route_b.parse,
                           route_b.parse_breadth))

    for name, parse_fn, ask_fn, breadth_fn in contenders:
        start = time.time()
        rows: Dict[str, List[Dict]] = {"parse": [], "qa": [],
                                       "honesty": [], "breadth": []}
        deterministic = True

        for task in IN_FRAGMENT_PARSE:
            run_pair = _twice(parse_fn, task["sentence"])
            deterministic &= run_pair["deterministic"]
            graded = grade_parse(run_pair["result"], task["gold"])
            rows["parse"].append({"task_id": task["task_id"], **graded})

        for task in QUESTION_ANSWERING:
            run_pair = _twice(ask_fn, task["sentence"])
            deterministic &= run_pair["deterministic"]
            if name == "route_a":
                ok = run_pair["result"].get("ok")
                graded = {"correct": ok is not None
                          and ok["status"] == task["gold_status"]
                          and ok["answer"] == task["gold_answer"],
                          "produced": ok or run_pair["result"].get("refused")}
            else:
                graded = grade_question(run_pair["result"],
                                        task["gold_status"],
                                        task["gold_answer"],
                                        seed["cmb_facts"], seed["rules"])
            rows["qa"].append({"task_id": task["task_id"], **graded})

        for task in UNKNOWN_HONESTY:
            run_pair = _twice(parse_fn, task["sentence"])
            deterministic &= run_pair["deterministic"]
            graded = grade_honesty(run_pair["result"], task["unknown_word"])
            rows["honesty"].append({"task_id": task["task_id"], **graded})

        for task in BREADTH:
            run_pair = _twice(breadth_fn, task["sentence"])
            deterministic &= run_pair["deterministic"]
            graded = grade_breadth(run_pair["result"], task["gold"])
            rows["breadth"].append({"task_id": task["task_id"], **graded})

        routes[name] = {
            "rows": rows,
            "scores": {
                "parse_accuracy": _rate(rows["parse"], "correct"),
                "qa_accuracy": _rate(rows["qa"], "correct"),
                "honesty_rate": _rate(rows["honesty"], "honest"),
                "honesty_named_word_rate": _rate(rows["honesty"],
                                                 "named_word"),
                "breadth_mean_slot_accuracy": round(
                    sum(r["slot_accuracy"] for r in rows["breadth"])
                    / len(rows["breadth"]), 4),
                "breadth_honest_refusals": sum(
                    1 for r in rows["breadth"] if r["honest_refusal"]),
                "deterministic": deterministic,
            },
            "wall_seconds": round(time.time() - start, 1),
        }

    packet = {
        "benchmark": "CORTEX_H2H v0.1 - Route A (native CCB-L1) vs "
                     "Route B (pretrained open-weight cortex)",
        "route_b_model": ("Qwen/Qwen2.5-0.5B-Instruct, local cache, "
                          "offline, CPU, greedy - the FLOOR of the "
                          "doctrine's 1-3B band" if route_b else "NOT RUN"),
        "identical_conditions": attestation(),
        "routes": routes,
        "caveats": [
            "Route B sample is a 0.5B instruct model on CPU: the floor "
            "of the doctrine's proposed 1-3B cortex band, not its "
            "ceiling.",
            "The battery is small (20 scored items) and the fragment "
            "dimensions favor Route A's home ground by construction; "
            "the breadth dimension exists to measure Route B's home "
            "ground. Read per-dimension, never as one number.",
            "TEST-ONLY: no foreign model enters production; this "
            "benchmark informs the Route B ratification decision.",
        ],
    }
    packet["results_digest"] = _digest(packet)
    return packet


def _rate(rows: List[Dict], key: str) -> float:
    return round(sum(1 for r in rows if r.get(key)) / len(rows), 4)


def format_report(packet: Dict) -> str:
    lines = ["CORTEX HEAD-TO-HEAD v0.1", "",
             f"Route B model: {packet['route_b_model']}", ""]
    header = f"{'dimension':<34}{'Route A':>10}{'Route B':>10}"
    lines.append(header)
    lines.append("-" * len(header))
    a = packet["routes"]["route_a"]["scores"]
    b = packet["routes"].get("route_b", {}).get("scores", {})

    def row(label, key, fmt="{:.0%}"):
        left = fmt.format(a[key]) if isinstance(a.get(key), float) else str(a.get(key))
        right = (fmt.format(b[key]) if isinstance(b.get(key), float)
                 else str(b.get(key))) if b else "NOT RUN"
        lines.append(f"{label:<34}{left:>10}{right:>10}")

    row("in-fragment parse accuracy", "parse_accuracy")
    row("question answering (kernel)", "qa_accuracy")
    row("unknown-word honesty", "honesty_rate")
    row("  ...naming the unknown word", "honesty_named_word_rate")
    row("breadth (mean slot accuracy)", "breadth_mean_slot_accuracy")
    row("deterministic (all items x2)", "deterministic", fmt="{}")
    lines.append("")
    lines.append(f"Route A wall seconds: "
                 f"{packet['routes']['route_a']['wall_seconds']}")
    if "route_b" in packet["routes"]:
        lines.append(f"Route B wall seconds: "
                     f"{packet['routes']['route_b']['wall_seconds']}")
    lines.append("")
    for caveat in packet["caveats"]:
        lines.append(f"CAVEAT: {caveat}")
    lines.append("")
    lines.append(f"results digest: {packet['results_digest']}")
    return "\n".join(lines)
