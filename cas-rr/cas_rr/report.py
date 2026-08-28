"""Human-readable reporting for CAS-RR episodes.

The machine's full output is the ProvenancePacket (a nested dict). These
helpers turn the packet into bench-readable reports: terminal status,
output, the RPM recursion story, memory lacunae, comparison results, the
commitment gates, and the winning proof path.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


def summarize(packet: Dict) -> str:
    lines: List[str] = []
    lines.append(f"problem:     {packet['problem_id']}")
    lines.append(f"status:      {packet['terminal_status']}  (ticks={packet['ticks']})")
    out = packet.get("output")
    lines.append(f"output:      {out['conclusion'] if out else 'none'}")

    events = packet["rpm"]["subgoal_events"]
    if events:
        lines.append("rpm story:")
        for ev in events:
            if ev["event"] == "SUBGOAL_CREATED":
                lines.append(
                    f"  descend  {ev['subgoal_type']:<10} from {ev['parent']} "
                    f"(blocked on {ev['blocked_prerequisite']}, action={ev['action']})")
            else:
                lines.append(f"  resolve  {'':<10} {ev['subgoal']} via {ev['action']}")

    scans = packet["rpm"]["scan_history"]
    if scans:
        lines.append("rpm scans:")
        for s in scans:
            flag = lambda ok: "Y" if ok else "n"
            lines.append(
                f"  {s['goal_id']:<24} D={flag(s['D_ok'])} W={flag(s['W_ok'])} "
                f"P={flag(s['P_ok'])} unmet={s['first_unmet']} cached={s['cached']}")

    lacunae = list(dict.fromkeys(
        (l["query"], l["kind"])
        for m in packet["memory"] for l in m["lacunae"]))
    if lacunae:
        lines.append("lacunae:")
        for query, kind in lacunae:
            lines.append(f"  {kind:<18} {query}")

    for tour in packet["comparisons"]:
        if tour["winner"]:
            lines.append(f"tournament: winner {tour['winner']}; "
                         f"eliminated: {tour['eliminated'] or 'none'}")

    dec = packet.get("commitment")
    if dec:
        lines.append("gates:")
        for g in dec["gates"]:
            mark = "PASS" if g["passed"] else "FAIL"
            lines.append(f"  {mark:<4} {g['gate']:<28} {g['detail']}")

    if out and out.get("conclusion"):
        for rec in packet["inferences"].values():
            if rec["conclusion"] == out["conclusion"] and rec["success"]:
                rules = rec["rules_used"] or ["(facts only)"]
                lines.append(
                    f"proof:      {out['conclusion']} <- rules {rules} "
                    f"via premises {rec['premises_used']}")
                break

    return "\n".join(lines)


def battery_table(results: Dict[str, Dict]) -> str:
    """One-line-per-task table of terminal statuses."""
    lines = [f"{'task':<24} {'status':<20} output"]
    for name, packet in results.items():
        out = packet.get("output")
        conclusion = out["conclusion"] if out else "-"
        lines.append(f"{name:<24} {packet['terminal_status']:<20} {conclusion}")
    return "\n".join(lines)


def trace_compact(packet: Dict) -> str:
    """The append-only trace, one line per event."""
    lines = []
    for ev in packet["trace"]:
        payload = ""
        if ev["kind"] == "SCAN":
            p = ev["payload"]
            payload = (f"D={p.get('D_ok')} W={p.get('W_ok')} P={p.get('P_ok')} "
                       f"unmet={p.get('first_unmet')}")
        elif ev["kind"] == "INFERRED":
            p = ev["payload"]
            payload = (f"{p.get('candidate')} success={p.get('success')} "
                       f"rules={p.get('rules_used')} status={p.get('contradiction')}")
        elif ev["kind"] == "TOURNAMENT":
            p = ev["payload"]
            payload = f"winner={p.get('winner')} eliminated={p.get('eliminated')}"
        elif ev["kind"] in ("SUBGOAL_CREATED", "SUBGOAL_RESOLVED",
                            "OUTPUT", "DECISION"):
            payload = str(ev["payload"])
        lines.append(f"t{ev['tick']:>3} {ev['phase']:<14} {ev['kind']:<16} {payload}")
    return "\n".join(lines)


def determinism_check(task_factory, constitution) -> Tuple[bool, str]:
    """Run the same episode twice; traces must match exactly."""
    from cas_rr.runtime import CASRuntime

    packet_a = CASRuntime(constitution, task_factory()).run()
    packet_b = CASRuntime(constitution, task_factory()).run()
    key = lambda p: [(e["tick"], e["phase"], e["kind"]) for e in p["trace"]]
    same_trace = key(packet_a) == key(packet_b)
    same_status = packet_a["terminal_status"] == packet_b["terminal_status"]
    same_output = packet_a["output"] == packet_b["output"]
    ok = same_trace and same_status and same_output
    detail = ("traces, status, output identical" if ok
              else f"trace={same_trace} status={same_status} output={same_output}")
    return ok, detail
