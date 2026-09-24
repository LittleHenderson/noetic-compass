#!/usr/bin/env python3
"""Checkpoint roster checker for ONE training receipt (readout plan item 2; prereg A5).

WHAT IT ANSWERS, IN PLAIN WORDS
  Prereg A5 names six trained checkpoints for every repaired seed. This program says whether all
  six came back in one receipt, whether each file is byte-for-byte the file the receiver listed,
  and whether each one sits at the right number of training updates:

      pass_01.pt                              147 updates   collected/results/artifacts/
      evidence/main_checkpoint_0294.pt        294 updates   collected/results/evidence/
      evidence/main_checkpoint_0588.pt        588 updates   collected/results/evidence/
      evidence/main_checkpoint_0882.pt        882 updates   collected/results/evidence/
      evidence/main_checkpoint_1176.pt       1176 updates   collected/results/evidence/
      final.pt                               1470 updates   collected/results/artifacts/

  For each of the six it checks:
    - the .pt file and its JSON sidecar are on disk and listed in collected_inventory.json;
    - their sha256 and byte size equal the inventory's;
    - the sidecar's own pin (sha256, bytes, file name) names the same .pt file;
    - the sidecar's update counters (completed_main_updates for evidence files, cursor,
      model_revision and counters.optimizer_updates) all equal the expected count;
    - the sidecar's learnable_names list equals the arm's frozen list exactly
      (53 names for a repaired receipt, 48 for an unchanged receipt);
    - all six sidecars carry the same run_identity_digest (one run, not a mix).
  It also reads the update totals from the worker report and requires
  1,488 = 1,470 main + 16 interference + 2 replay.

  A REDUCED (smoke) run writes no evidence/main_checkpoint files when it has one pass. For such a
  receipt the program checks the checkpoints the reduced run did write, requires the others to be
  absent, and says ROSTER_REDUCED_RUN_CONSISTENT. That is NOT an A5 roster.

WHAT IT DOES NOT ANSWER
  Presence and integrity only. It says nothing about what any checkpoint learned. It is not the
  A5 wiring probe, not the A5.5 matched-start check, and not a score of any kind.

READ-ONLY AND CUSTODY
  It reads collected_inventory.json, the six .pt files and their sidecars, the worker report and
  the receipt-root reduced_schedule.json. It writes nothing, loads no model, imports no torch and
  makes no network call. It never opens a scoring or prediction file. From worker_report.json it
  reads only update-count fields; no score field is read out or printed (prereg A5.1).

USAGE (on this laptop run from C:\\ with absolute paths)
  python -B check_roster.py --arm repaired  "<receipt folder>"
  python -B check_roster.py --arm unchanged "<receipt folder>" --json

VERDICTS AND EXIT CODES
  ROSTER_COMPLETE                exit 0  registered schedule; every check above passes.
  ROSTER_PROBLEM                 exit 1  anything else; every problem is named "<path>=<CODE>".
  ROSTER_REDUCED_RUN_CONSISTENT  exit 3  a reduced run, internally consistent; not an A5 roster.
  TOOL_STOP / usage error        exit 2  the receipt folder does not exist, or bad arguments.

Label: CLAUDE_BUILT_CLAUDE_CHECKED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath

SCHEMA = "helm.readout.checkpoint-roster/0.1"
LABEL = "CLAUDE_BUILT_CLAUDE_CHECKED"
BOUNDARY = ("Roster presence and integrity only. It says nothing about what any checkpoint learned. "
            "It is not the A5 wiring probe, the A5.5 matched-start check, or a score.")

# The registered schedule (Helm 2.0 receipt_20260917 at c8d5c430 and the repaired study use the same one):
# 10 passes x 147 updates, then 16 interference updates, then 2 replay updates.
UPDATES_PER_PASS = 147
REGISTERED_PASSES = 10
MAIN_UPDATES = 1470
INTERFERENCE_UPDATES = 16
REPLAY_UPDATES = 2
GLOBAL_UPDATES = 1488
assert MAIN_UPDATES == UPDATES_PER_PASS * REGISTERED_PASSES
assert GLOBAL_UPDATES == MAIN_UPDATES + INTERFERENCE_UPDATES + REPLAY_UPDATES

INVENTORY = "collected_inventory.json"
REDUCED_RECORD = "reduced_schedule.json"
WORKER_REPORT = "results/artifacts/worker_report.json"      # relative to collected/
PARTIAL_SIDECAR_SCHEMA = "cncm.typed-course-partial-checkpoint/0.1"

# (label, kind, checkpoint path, sidecar path, registered update count); paths are relative to collected/.
# kind "artifact": the sidecar IS the checkpoint pin; kind "evidence": the pin sits under sidecar["checkpoint"].
ROSTER = (
    ("pass_01", "artifact", "results/artifacts/pass_01.pt", "results/artifacts/pass_01_checkpoint.json", 147),
    ("main_checkpoint_0294", "evidence", "results/evidence/main_checkpoint_0294.pt",
     "results/evidence/main_checkpoint_0294.json", 294),
    ("main_checkpoint_0588", "evidence", "results/evidence/main_checkpoint_0588.pt",
     "results/evidence/main_checkpoint_0588.json", 588),
    ("main_checkpoint_0882", "evidence", "results/evidence/main_checkpoint_0882.pt",
     "results/evidence/main_checkpoint_0882.json", 882),
    ("main_checkpoint_1176", "evidence", "results/evidence/main_checkpoint_1176.pt",
     "results/evidence/main_checkpoint_1176.json", 1176),
    ("final", "artifact", "results/artifacts/final.pt", "results/artifacts/final_checkpoint.json", 1470),
)

# Frozen learnable-name lists, exactly as the sidecars record them (sorted by name).
# UNCHANGED_48: Helm 2.0 receipt_20260917 final_checkpoint.json at commit c8d5c430 (48 names).
# REPAIRED_53: switch-ON smoke receipt_analogy_on_smoke_20260917 final_checkpoint.json
#              (inventory sha256 5a54bc42...), committed in 1ddf6a1e: the 48 above plus 5 analogy_head names.
UNCHANGED_48 = (
    "attention_key.weight", "declaration_projection.weight", "declaration_table", "directed_pair_embedding",
    "edge_head.0.weight", "edge_head.2.bias", "edge_head.2.weight", "edge_head.3.bias", "edge_head.3.weight",
    "left.weight", "match_key.weight", "merge.weight",
    "mode_option_head.0.weight", "mode_option_head.2.bias", "mode_option_head.2.weight",
    "mode_option_head.3.bias", "mode_option_head.3.weight",
    "node_encode.weight", "node_head.0.weight", "node_head.2.bias", "node_head.2.weight", "node_head.3.bias",
    "node_head.3.weight", "pointer_key.weight", "query_norm.bias", "query_norm.weight",
    "query_projection.weight",
    "reach_option_head.0.weight", "reach_option_head.2.bias", "reach_option_head.2.weight",
    "reach_option_head.3.bias", "reach_option_head.3.weight",
    "right.weight", "role_embedding", "role_head.0.weight", "role_head.2.bias", "role_head.2.weight",
    "role_head.3.bias", "role_head.3.weight", "round_mix", "round_rate", "state_encode.weight",
    "world_head.0.weight", "world_head.2.bias", "world_head.2.weight", "world_head.3.bias",
    "world_head.3.weight", "world_projection.weight",
)
ANALOGY_HEAD_5 = ("analogy_head.0.weight", "analogy_head.2.bias", "analogy_head.2.weight",
                  "analogy_head.3.bias", "analogy_head.3.weight")
REPAIRED_53 = ANALOGY_HEAD_5 + UNCHANGED_48
assert len(UNCHANGED_48) == 48 and len(REPAIRED_53) == 53
assert list(REPAIRED_53) == sorted(REPAIRED_53) and list(UNCHANGED_48) == sorted(UNCHANGED_48)
EXPECTED_LEARNABLE = {"repaired": REPAIRED_53, "unchanged": UNCHANGED_48}


def names_digest(names):
    """sha256 of the names joined by newlines; printed so a manifest can cite which list was used."""
    return hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path):
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def _get(mapping, dotted):
    value = mapping
    for key in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


class _Check:
    """Collects named problems for one receipt."""

    def __init__(self, receipt):
        self.root = Path(receipt)
        self.collected = self.root / "collected"
        self.problems = []
        self.entries = {}
        self.duplicates = set()

    def flag(self, name, code, detail=None):
        self.problems.append({"name": name, "code": code, "detail": detail})

    def load_inventory(self):
        path = self.root / INVENTORY
        if not path.is_file():
            self.flag(INVENTORY, "MISSING")
            return None
        try:
            inventory = _load_json(path)
        except (OSError, ValueError) as error:
            self.flag(INVENTORY, "UNREADABLE", str(error))
            return None
        if not isinstance(inventory, dict) or not isinstance(inventory.get("files"), list):
            self.flag(INVENTORY, "UNREADABLE", "no files list")
            return None
        for entry in inventory["files"]:
            relative = entry.get("relative_path") if isinstance(entry, dict) else None
            if relative in self.entries:
                self.duplicates.add(relative)
            self.entries[relative] = entry
        if inventory.get("failures"):
            self.flag(INVENTORY, "INVENTORY_REPORTS_FAILURES", len(inventory["failures"]))
        return inventory

    def verify_file(self, relative):
        """On disk, listed once in the inventory, same bytes and sha256. Returns the sha256 or None."""
        path = self.collected / relative
        entry = self.entries.get(relative)
        good = True
        if relative in self.duplicates:
            self.flag(relative, "INVENTORY_DUPLICATE_ENTRY")
            good = False
        if entry is None:
            self.flag(relative, "NOT_IN_INVENTORY")
            good = False
        if not path.is_file():
            self.flag(relative, "MISSING")
            return None
        actual = _sha256_file(path)
        if entry is not None:
            if entry.get("bytes") != path.stat().st_size:
                self.flag(relative, "BYTES_MISMATCH", "disk %d, inventory %r" % (path.stat().st_size,
                                                                                entry.get("bytes")))
                good = False
            if entry.get("sha256") != actual:
                self.flag(relative, "SHA256_MISMATCH", "disk %s, inventory %r" % (actual, entry.get("sha256")))
                good = False
        return actual if good else None

    def verified_json(self, relative):
        if self.verify_file(relative) is None:
            return None
        try:
            return _load_json(self.collected / relative)
        except (OSError, ValueError) as error:
            self.flag(relative, "UNREADABLE", str(error))
            return None


def _reduced_schedule(check):
    """None for a registered run. The receipt-root record is absent on older (Helm 2.0) receipts."""
    path = check.root / REDUCED_RECORD
    if not path.is_file():
        return None
    try:
        record = _load_json(path)
    except (OSError, ValueError) as error:
        check.flag(REDUCED_RECORD, "UNREADABLE", str(error))
        return None
    return record.get("reduced_schedule") if isinstance(record, dict) else None


def _worker_counts(report):
    """Update-count fields only. No score field is read."""
    work = report.get("global_actual_work") if isinstance(report.get("global_actual_work"), dict) else {}
    phases = {"main_training": 0, "interference_training": 0, "replay": 0, "other": 0}
    for row in work.get("phases") or []:
        name = row.get("phase") if isinstance(row, dict) else None
        updates = _get(row, "delta.optimizer_updates") if isinstance(row, dict) else None
        if not isinstance(updates, int):
            continue
        if name in ("main_training", "interference_training"):
            phases[name] += updates
        elif isinstance(name, str) and name.startswith("replay_"):
            phases["replay"] += updates
        else:
            phases["other"] += updates
    cursor_ends = [row.get("cursor_end") for row in report.get("pass_summaries") or [] if isinstance(row, dict)]
    return {
        "schedule_plan_mode": report.get("schedule_plan_mode"),
        "completed_main_updates": report.get("completed_main_updates"),
        "main_updates": report.get("main_updates"),
        "global_updates": report.get("global_updates"),
        "global_actual_work.expected_updates": work.get("expected_updates"),
        "global_actual_work.totals.optimizer_updates": _get(work, "totals.optimizer_updates"),
        "global_actual_work.totals.backward_calls": _get(work, "totals.backward_calls"),
        "phases.main_training": phases["main_training"],
        "phases.interference_training": phases["interference_training"],
        "phases.replay": phases["replay"],
        "phases.other": phases["other"],
        "pass_cursor_ends": cursor_ends,
    }


def _expected_totals(mode, plan):
    if mode == "REGISTERED":
        main, interference, replay = MAIN_UPDATES, INTERFERENCE_UPDATES, REPLAY_UPDATES
    else:
        main = plan.get("updates")
        interference = INTERFERENCE_UPDATES if plan.get("interference") else 0
        replay = REPLAY_UPDATES if plan.get("replays") else 0
    total = main + interference + replay if isinstance(main, int) else None
    return {
        "schedule_plan_mode": mode,
        "completed_main_updates": main,
        "main_updates": main,
        "global_updates": total,
        "global_actual_work.expected_updates": total,
        "global_actual_work.totals.optimizer_updates": total,
        "global_actual_work.totals.backward_calls": total,
        "phases.main_training": main,
        "phases.interference_training": interference,
        "phases.replay": replay,
        "phases.other": 0,
    }


def _check_row(check, arm_names, label, kind, pt, side, expected_updates):
    row = {"label": label, "checkpoint": pt, "sidecar": side, "expected_updates": expected_updates,
           "sha256": None, "bytes": None, "updates": None, "learnable_names": None, "run_identity_digest": None}
    before = len(check.problems)
    sha = check.verify_file(pt)
    if sha is not None:
        row["sha256"] = sha
        row["bytes"] = (check.collected / pt).stat().st_size
    sidecar = check.verified_json(side)
    if isinstance(sidecar, dict):
        if kind == "evidence":
            if sidecar.get("schema") != PARTIAL_SIDECAR_SCHEMA or not isinstance(sidecar.get("checkpoint"), dict):
                check.flag(side, "SIDECAR_SHAPE", "expected a %s wrapper" % PARTIAL_SIDECAR_SCHEMA)
            pin = sidecar.get("checkpoint") if isinstance(sidecar.get("checkpoint"), dict) else {}
        else:
            pin = sidecar
        metadata = pin.get("metadata") if isinstance(pin.get("metadata"), dict) else {}
        entry = check.entries.get(pt) or {}
        if pin.get("sha256") != entry.get("sha256") or pin.get("bytes") != entry.get("bytes"):
            check.flag(side, "SIDECAR_PIN_DIFFERS_FROM_INVENTORY",
                       "pin %r/%r, inventory %r/%r" % (pin.get("sha256"), pin.get("bytes"),
                                                       entry.get("sha256"), entry.get("bytes")))
        if PurePosixPath(str(pin.get("path", "")).replace("\\", "/")).name != PurePosixPath(pt).name:
            check.flag(side, "SIDECAR_NAMES_ANOTHER_FILE", pin.get("path"))
        counts = {"cursor": metadata.get("cursor"), "model_revision": metadata.get("model_revision"),
                  "counters.optimizer_updates": _get(metadata, "counters.optimizer_updates")}
        if kind == "evidence":
            counts = {"completed_main_updates": sidecar.get("completed_main_updates"), **counts}
        row["updates"] = counts
        wrong = {key: value for key, value in counts.items() if value != expected_updates}
        if wrong:
            check.flag(side, "UPDATE_COUNT_MISMATCH", "expected %r, got %s" % (expected_updates,
                                                                             json.dumps(wrong, sort_keys=True)))
        names = metadata.get("learnable_names")
        row["learnable_names"] = len(names) if isinstance(names, list) else None
        if names != list(arm_names):
            check.flag(side, "LEARNABLE_NAMES_MISMATCH",
                       "got %s names, expected the %d-name list" % (row["learnable_names"], len(arm_names)))
        row["run_identity_digest"] = pin.get("run_identity_digest")
    row["status"] = "OK" if len(check.problems) == before else "PROBLEM"
    return row


def _absent_row(check, label, pt, side, expected_updates):
    """A reduced run does not write this checkpoint: require it absent from disk and inventory."""
    row = {"label": label, "checkpoint": pt, "sidecar": side, "expected_updates": None,
           "registered_updates": expected_updates, "sha256": None, "bytes": None, "updates": None,
           "learnable_names": None, "run_identity_digest": None}
    found = [name for name in (pt, side) if (check.collected / name).exists() or name in check.entries]
    for name in found:
        check.flag(name, "UNEXPECTED_IN_REDUCED_RUN")
    row["status"] = "PROBLEM" if found else "ABSENT_EXPECTED_REDUCED_RUN"
    return row


def check_receipt(receipt, arm):
    """Return the roster report (a dict) for one receipt folder. Pure reads."""
    if arm not in EXPECTED_LEARNABLE:
        raise ValueError("arm must be one of %s" % sorted(EXPECTED_LEARNABLE))
    arm_names = EXPECTED_LEARNABLE[arm]
    check = _Check(receipt)
    report = {"schema": SCHEMA, "label": LABEL, "boundary": BOUNDARY, "receipt": str(check.root.resolve()),
              "arm": arm, "expected_learnable_names": len(arm_names),
              "expected_learnable_names_sha256": names_digest(arm_names),
              "schedule_mode": None, "job": None, "rows": [], "update_totals": None}
    inventory = check.load_inventory()
    if inventory is not None:
        report["job"] = inventory.get("job")
    reduced = _reduced_schedule(check)
    mode = "REGISTERED" if reduced is None else "REDUCED"
    report["schedule_mode"] = mode
    plan = reduced.get("plan") if isinstance(reduced, dict) and isinstance(reduced.get("plan"), dict) else {}
    worker = check.verified_json(WORKER_REPORT) if inventory is not None else None
    counts = _worker_counts(worker) if isinstance(worker, dict) else None

    # Expected update count for each roster row, and which rows this run must have written.
    expected = {label: (updates, True) for label, _k, _p, _s, updates in ROSTER}
    if mode == "REDUCED":
        ends = counts["pass_cursor_ends"] if counts else []
        passes, updates = plan.get("passes"), plan.get("updates")
        if not (isinstance(passes, int) and passes >= 1 and len(ends) == passes and ends[-1] == updates):
            check.flag(WORKER_REPORT, "REDUCED_PLAN_AND_PASS_SUMMARIES_DISAGREE",
                       "plan passes=%r updates=%r, pass cursor ends %r" % (passes, updates, ends))
        written = set(ends[:-1])
        for label, kind, _p, _s, registered in ROSTER:
            if label == "pass_01":
                expected[label] = (ends[0] if ends else None, True)
            elif label == "final":
                expected[label] = (updates, True)
            else:
                expected[label] = (registered, registered in written)

    if inventory is not None:
        for label, kind, pt, side, registered in ROSTER:
            updates, must_exist = expected[label]
            if must_exist:
                report["rows"].append(_check_row(check, arm_names, label, kind, pt, side, updates))
            else:
                report["rows"].append(_absent_row(check, label, pt, side, registered))

        digests = {row["run_identity_digest"] for row in report["rows"] if row["run_identity_digest"]}
        if len(digests) > 1:
            reference = next((row["run_identity_digest"] for row in report["rows"]
                              if row["label"] == "final" and row["run_identity_digest"]), None)
            for row in report["rows"]:
                if row["run_identity_digest"] and row["run_identity_digest"] != reference:
                    check.flag(row["sidecar"], "RUN_IDENTITY_DIFFERS_FROM_FINAL", row["run_identity_digest"])
                    row["status"] = "PROBLEM"

    if counts is not None:
        want = _expected_totals(mode, plan)
        totals = {"expected": want, "got": {key: counts[key] for key in want}}
        for key, value in want.items():
            if counts[key] != value:
                check.flag(WORKER_REPORT, "UPDATE_TOTAL_MISMATCH", "%s: expected %r, got %r" % (key, value,
                                                                                               counts[key]))
        report["update_totals"] = totals

    report["problems"] = ["%s=%s" % (p["name"], p["code"]) for p in check.problems]
    report["problem_details"] = check.problems
    if check.problems:
        report["verdict"] = "ROSTER_PROBLEM"
    elif mode == "REDUCED":
        report["verdict"] = "ROSTER_REDUCED_RUN_CONSISTENT"
    else:
        report["verdict"] = "ROSTER_COMPLETE"
    return report


EXIT_CODES = {"ROSTER_COMPLETE": 0, "ROSTER_PROBLEM": 1, "ROSTER_REDUCED_RUN_CONSISTENT": 3}


def render(report):
    lines = ["CHECKPOINT ROSTER (%s, %s)" % (report["schema"], report["label"]),
             "receipt  %s" % report["receipt"],
             "job      %s" % report["job"],
             "arm      %s (expected %d learnable names, list sha256 %s)" % (
                 report["arm"], report["expected_learnable_names"], report["expected_learnable_names_sha256"]),
             "schedule %s" % report["schedule_mode"]]
    for row in report["rows"]:
        if row["status"] == "ABSENT_EXPECTED_REDUCED_RUN":
            lines.append("  %-22s %-42s ABSENT (expected: a reduced run does not write it)" % (
                row["label"], row["checkpoint"]))
            continue
        counts = row["updates"] or {}
        seen = sorted({value for value in counts.values()}, key=repr)
        lines.append("  %-22s %-42s %s sha256=%s updates=%s/%s learnable=%s/%d" % (
            row["label"], row["checkpoint"], "PRESENT" if row["sha256"] else "NOT_VERIFIED",
            row["sha256"], ",".join(repr(v) for v in seen) or None, row["expected_updates"],
            row["learnable_names"], report["expected_learnable_names"]) + "  " + row["status"])
    totals = report["update_totals"]
    if totals:
        got, want = totals["got"], totals["expected"]
        lines.append("  update total (worker report): main %r + interference %r + replay %r = global %r;"
                     " expected %r + %r + %r = %r" % (
                         got["phases.main_training"], got["phases.interference_training"], got["phases.replay"],
                         got["global_updates"], want["phases.main_training"], want["phases.interference_training"],
                         want["phases.replay"], want["global_updates"]))
    for problem in report["problem_details"]:
        lines.append("  PROBLEM %s=%s%s" % (problem["name"], problem["code"],
                                             "" if problem["detail"] is None else "  (%s)" % problem["detail"]))
    if report["verdict"] == "ROSTER_REDUCED_RUN_CONSISTENT":
        lines.append("  NOTE a reduced (smoke) run: consistent with itself, but NOT an A5 roster.")
    lines.append("ROSTER_VERDICT: %s" % report["verdict"])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only checkpoint roster check for one receipt (prereg A5).")
    parser.add_argument("receipt", help="receipt folder (holds collected_inventory.json and collected/)")
    parser.add_argument("--arm", required=True, choices=sorted(EXPECTED_LEARNABLE),
                        help="repaired = 53 learnable names; unchanged = 48")
    parser.add_argument("--json", action="store_true", help="print the report as JSON instead of text")
    args = parser.parse_args(argv)
    if not Path(args.receipt).is_dir():
        print("TOOL_STOP: receipt folder not found: %s" % args.receipt)
        return 2
    report = check_receipt(args.receipt, args.arm)
    print(json.dumps(report, indent=1, sort_keys=True) if args.json else render(report))
    return EXIT_CODES[report["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
