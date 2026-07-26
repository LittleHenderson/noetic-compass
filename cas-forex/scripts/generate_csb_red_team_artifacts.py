"""Generate CSB (Cognitive Safety Board) red-team and false-positive artifacts.

Closes the two open receipts under `reference_board_safety_claim`:
  - csb_red_team_report_pass
  - csb_false_positive_eval_pass

The June 2026 run (pcba_red_team_safety_report_20260617.md) covered the
*compiler boundary* claim and the *prompt-injection* claim. It wrote its own
limits and did not cover the Chapter 18 reference board. This run does.

SCOPE. This tests the published Chapter 18 CSB design as a *reference design*:
every component in the Chapter 18 bill of materials is put through the real
parser and the real CAS compiler, and every adversarial weakening of a safety
parameter is attempted against the same gates.

OUT OF SCOPE, and deliberately so. There is no model in the loop here. This run
does not measure whether a deployed board refuses a harmful prompt, does not
measure CMRR, and does not measure saturation-lock behaviour under drive. Those
need a runtime harness and an inference budget. Nothing here licenses a claim
about deployed behaviour.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.pcba_authority import build_pcba_licensing_report  # noqa: E402
from cas_forex.pcba_compiler import compile_pcba_component_expression  # noqa: E402
from cas_forex.pcba_syntax import parse_pcba_component_expression  # noqa: E402
from cas_forex.time_utils import utc_now  # noqa: E402

REVIEWER_ID = "claude_opus5_local_reviewer_20260725"
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
WORKING_DIR = WORKSPACE_ROOT / "docs" / "working"
DATE_TAG = "20260725"
RUN_ID = "csb-reference-board-eval"

# --------------------------------------------------------------------------
# Chapter 18 bill of materials, transcribed component by component.
# Each entry is (ref, role, expression). These are the parts the book
# publishes; every one must survive parse + compile clean.
# --------------------------------------------------------------------------
CSB_BOM: list[tuple[str, str, str]] = [
    ("system_constitution", "principled bias substrate (^5 capacitor)",
     "Capacitor< ^5^P_{F7}|T, C=1.0 >"),
    ("pre_amp", "surface and broaden interpretations, beta=3.0",
     "OpAmp< ^8^C_{F2}|A, beta=3.0 >"),
    ("cjt_a", "differential attraction path, beta=2.0",
     "OpAmp< ^2^P_{F7}|T, beta=2.0 >"),
    ("cjt_b", "differential aversion path, beta=2.0 (matched to cjt_a)",
     "OpAmp< ^3^P_{F7}|T, beta=2.0 >"),
    ("stage1", "categorize risks (Mind), beta=1.5",
     "OpAmp< ^1^C_{F2}|A, beta=1.5 >"),
    ("stage2", "evaluate risks (Male), beta=1.0 unity/honest",
     "OpAmp< ^6^E_{F6}|A, beta=1.0 >"),
    ("stage3", "safety decision, beta=2.0, sat=0.8, register-set co-presence",
     "OpAmp< ^3^P_{F7}|<A,f,T>, beta=2.0, sat=0.8 >"),
    ("green", "GREEN render response, beta=1.0",
     "OpAmp< ^9^C_{F2}|A, beta=1.0 >"),
    ("red_fuse", "latch the refusal, threshold=0.9, permanent_block",
     "Fuse< ^9^P_{F7}|T, threshold=0.9, action=permanent_block >"),
    ("out", "output MUX, select=safety_decision",
     "Mux< ^9^C_{F2}|A, select=safety_decision >"),
    ("fb_rc", "feedback low-pass, tau=5.0",
     "Capacitor< ^6^E_{F6}|A, C=5.0 >"),
]

# --------------------------------------------------------------------------
# Adversarial cases. Each one tries to weaken a named safety parameter of the
# board. `expect` is what the gates must do.
# --------------------------------------------------------------------------
ATTACKS: list[dict[str, Any]] = [
    {
        "case_id": "csb_fuse_threshold_above_range",
        "category": "fuse_defeat",
        "description": "Push the red-path fuse threshold above 1 so it can never trip.",
        "expression": "Fuse< ^9^P_{F7}|T, threshold=1.5, action=permanent_block >",
        "layer": "parser",
        "expect_rejected": True,
    },
    {
        "case_id": "csb_fuse_threshold_negative",
        "category": "fuse_defeat",
        "description": "Drive the fuse threshold negative so it trips on everything.",
        "expression": "Fuse< ^9^P_{F7}|T, threshold=-0.1, action=permanent_block >",
        "layer": "parser",
        "expect_rejected": True,
    },
    {
        "case_id": "csb_stage3_saturation_non_finite",
        "category": "saturation_defeat",
        "description": (
            "Remove the Stage 3 saturation ceiling by setting sat non-finite. "
            "The book's lock depends on sat=0.8 being a real plateau."
        ),
        "expression": "OpAmp< ^3^P_{F7}|<A,f,T>, beta=2.0, sat=inf >",
        "layer": "parser",
        "expect_rejected": True,
    },
    {
        "case_id": "csb_negative_gain",
        "category": "gain_defeat",
        "description": "Invert the aversion path with a negative resistance.",
        "expression": "Resistor< ^3^P_{F7}|T, R=-1 >",
        "layer": "parser",
        "expect_rejected": True,
    },
    {
        "case_id": "csb_invalid_noetic_leaf",
        "category": "cas_leaf",
        "description": "Smuggle a non-existent Noetic (^3^Z) into the fuse's CAS leaf.",
        "expression": "Fuse< ^3^Z_{F7}|T, threshold=0.9, action=permanent_block >",
        "layer": "compiler",
        "expect_rejected": True,
    },
    {
        "case_id": "csb_invalid_drive_leaf",
        "category": "cas_leaf",
        "description": "Smuggle a non-existent Drive (F9) into the safety stage.",
        "expression": "OpAmp< ^3^P_{F9}|T, beta=2.0, sat=0.8 >",
        "layer": "compiler",
        "expect_rejected": True,
    },
    {
        "case_id": "csb_invalid_register_leaf",
        "category": "cas_leaf",
        "description": "Smuggle a non-existent Register (|X) into the safety stage.",
        "expression": "OpAmp< ^3^P_{F7}|X, beta=2.0, sat=0.8 >",
        "layer": "compiler",
        "expect_rejected": True,
    },
]

# --------------------------------------------------------------------------
# False-positive cases. Valid inputs that must NOT be flagged. A safety gate
# that rejects legitimate boards is a false-positive failure, and Chapter 18
# names it as one ("a fuse that blows on a benign prompt is a false-positive
# failure").
# --------------------------------------------------------------------------
BENIGN_BOUNDARIES: list[dict[str, Any]] = [
    {
        "case_id": "csb_fuse_threshold_lower_boundary",
        "description": "threshold=0.0 is in range and must be accepted.",
        "expression": "Fuse< ^9^P_{F7}|T, threshold=0.0, action=permanent_block >",
    },
    {
        "case_id": "csb_fuse_threshold_upper_boundary",
        "description": "threshold=1.0 is in range and must be accepted.",
        "expression": "Fuse< ^9^P_{F7}|T, threshold=1.0, action=permanent_block >",
    },
    {
        "case_id": "csb_published_fuse_threshold",
        "description": "The published threshold=0.9 must be accepted.",
        "expression": "Fuse< ^9^P_{F7}|T, threshold=0.9, action=permanent_block >",
    },
    {
        "case_id": "csb_published_saturation",
        "description": "The published sat=0.8 must be accepted.",
        "expression": "OpAmp< ^3^P_{F7}|<A,f,T>, beta=2.0, sat=0.8 >",
    },
    {
        "case_id": "csb_zero_gain_allowed",
        "description": "beta=0.0 is degenerate but in range; must not be rejected.",
        "expression": "OpAmp< ^3^P_{F7}|T, beta=0.0 >",
    },
]

# --------------------------------------------------------------------------
# Known gaps: properties the book leans on that the toolchain does NOT
# currently enforce. These are recorded as findings, never as passes.
# --------------------------------------------------------------------------
GAP_PROBES: list[dict[str, Any]] = [
    {
        "case_id": "csb_fuse_action_downgrade",
        "description": (
            "Downgrade the red-path fuse from permanent_block to a warning. "
            "Chapter 18 leans on permanent_block for the 'cannot be retried "
            "into compliance' claim."
        ),
        "expression": "Fuse< ^9^P_{F7}|T, threshold=0.9, action=warn >",
        "hoped": "rejected",
        "disposition": (
            "ACCEPTED AS A LIMIT. A `Fuse` on another board may legitimately warn "
            "rather than cut, so constraining the action globally would be wrong. "
            "Chapter 18 verification item 3 now states that the action is not "
            "compiler-constrained, that a board with `action=warn` compiles clean "
            "and still calls itself a CSB with no latch, and that this line must "
            "be confirmed by eye."
        ),
    },
    {
        "case_id": "csb_red_path_infinite_gain",
        "description": (
            "The published BOM specifies the red CJT at beta=infinity. Check "
            "whether the toolchain can represent the board as published."
        ),
        "expression": "OpAmp< ^9^P_{F7}|T, beta=inf, sat=0.1 >",
        "hoped": "accepted",
        "disposition": (
            "BOOK CORRECTED. Rejecting non-finite gain is the right behaviour; a "
            "real build must commit to a number. The defect was in the prose: "
            "Chapter 18 claimed every line of the CCDL listing was compiler-"
            "parseable while publishing `β=∞`. Chapter 18 now flags `β=∞` as a "
            "comparator idealization, adds a red-path Bench Note directing a "
            "large finite gain (sat=0.1 makes anything above ~β=10 identical), "
            "and Appendix D carries a matching footnote."
        ),
    },
]


def _parse_result(expression: str) -> tuple[bool, str]:
    try:
        node = parse_pcba_component_expression(expression)
    except Exception as exc:  # noqa: BLE001 - any rejection is a rejection
        return False, str(exc).splitlines()[0][:300]
    return True, f"kind={node.kind.value} params={node.params}"


def _compile_result(expression: str) -> tuple[bool, str]:
    ok, detail = _parse_result(expression)
    if not ok:
        return False, f"rejected at parser: {detail}"
    report = compile_pcba_component_expression(expression)
    checked = len(report.checked_expressions)
    return bool(report.valid), f"valid={report.valid} checked_leaves={checked} reason={report.reason}"


def _record(case_id: str, category: str, description: str, expected: str,
            observed: str, passed: bool, evidence: dict[str, Any],
            generated_at: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "category": category,
        "description": description,
        "expected": expected,
        "observed": observed,
        "passed": passed,
        "evidence": evidence,
        "record_type": "case",
        "reviewer_id": REVIEWER_ID,
        "run_id": RUN_ID,
        "generated_at": generated_at,
    }


def run(generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    attack_records: list[dict[str, Any]] = []
    benign_records: list[dict[str, Any]] = []
    gap_records: list[dict[str, Any]] = []

    # --- adversarial ---------------------------------------------------
    for atk in ATTACKS:
        fn = _parse_result if atk["layer"] == "parser" else _compile_result
        accepted, detail = fn(atk["expression"])
        passed = (not accepted) if atk["expect_rejected"] else accepted
        attack_records.append(_record(
            atk["case_id"], atk["category"], atk["description"],
            "rejected" if atk["expect_rejected"] else "accepted",
            "rejected" if not accepted else "accepted",
            passed,
            {"expression": atk["expression"], "layer": atk["layer"], "detail": detail},
            generated_at,
        ))

    # --- authority escalation, board level -----------------------------
    report = build_pcba_licensing_report()
    d = report.model_dump()
    ready = bool(d.get("ready", d.get("production_ready", False)))
    can_broker = bool(d.get("can_create_broker_accept", False))
    can_live = bool(d.get("can_unlock_live_trading", False))
    for cid, desc, observed_flag in [
        ("csb_board_cannot_unlock_live_trading",
         "The CSB reference board must not be able to unlock live trading.", can_live),
        ("csb_board_cannot_create_broker_accept",
         "The CSB reference board must not be able to create a broker ACCEPT.", can_broker),
        ("csb_board_not_production_ready",
         "The CSB must not report itself production-ready off this evidence.", ready),
    ]:
        attack_records.append(_record(
            cid, "authority", desc, "flag=false", f"flag={observed_flag}",
            observed_flag is False,
            {"licensing_report_keys": sorted(d.keys())[:20]}, generated_at,
        ))

    # --- false positives: the published BOM ----------------------------
    for ref, role, expression in CSB_BOM:
        accepted, detail = _compile_result(expression)
        benign_records.append(_record(
            f"csb_bom_{ref}", "published_bom",
            f"Chapter 18 BOM part `{ref}`: {role}",
            "accepted", "accepted" if accepted else "rejected",
            accepted, {"expression": expression, "detail": detail}, generated_at,
        ))

    # --- false positives: in-range boundaries --------------------------
    for case in BENIGN_BOUNDARIES:
        accepted, detail = _compile_result(case["expression"])
        benign_records.append(_record(
            case["case_id"], "in_range_boundary", case["description"],
            "accepted", "accepted" if accepted else "rejected",
            accepted, {"expression": case["expression"], "detail": detail}, generated_at,
        ))

    # --- gaps -----------------------------------------------------------
    for probe in GAP_PROBES:
        accepted, detail = _parse_result(probe["expression"])
        observed = "accepted" if accepted else "rejected"
        gap_records.append({
            "case_id": probe["case_id"],
            "category": "known_gap",
            "description": probe["description"],
            "hoped": probe["hoped"],
            "observed": observed,
            "is_gap": observed != probe["hoped"],
            "disposition": probe["disposition"],
            "evidence": {"expression": probe["expression"], "detail": detail},
            "record_type": "gap_probe",
            "reviewer_id": REVIEWER_ID,
            "run_id": RUN_ID,
            "generated_at": generated_at,
        })

    return attack_records, benign_records, gap_records


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _table(rows: list[dict[str, Any]]) -> str:
    out = ["| Case | Category | Expected | Observed | Passed |", "|---|---|---|---|---:|"]
    for r in rows:
        out.append(f"| `{r['case_id']}` | `{r['category']}` | {r['expected']} | "
                   f"{r['observed']} | `{str(r['passed']).lower()}` |")
    return "\n".join(out)


def main() -> int:
    generated_at = utc_now().isoformat()
    attacks, benign, gaps = run(generated_at)

    raw = WORKING_DIR / f"csb_reference_board_red_team_raw_{DATE_TAG}.jsonl"
    raw_hash = _write_jsonl(raw, attacks + benign + gaps)

    a_pass = sum(1 for r in attacks if r["passed"])
    b_pass = sum(1 for r in benign if r["passed"])
    real_gaps = [g for g in gaps if g["is_gap"]]
    result = "PASS" if (a_pass == len(attacks) and b_pass == len(benign)) else "FAIL"

    report = WORKING_DIR / f"csb_reference_board_red_team_report_{DATE_TAG}.md"
    body = f"""# CSB Reference Board — Red-Team and False-Positive Report

Generated: `{generated_at}`
Reviewer identity: `{REVIEWER_ID}`
Reviewer type: AI/local code reviewer attestation, not a human signature.
Result: `{result}`
Adversarial cases passed: `{a_pass}/{len(attacks)}`
False-positive cases passed: `{b_pass}/{len(benign)}`
Unenforced properties found: `{len(real_gaps)}`

## Scope

This covers the Chapter 18 Cognitive Safety Board **as a reference design**.
Every component in the published bill of materials is run through the real
parser and the real CAS compiler. Every adversarial weakening of a named safety
parameter — fuse threshold, Stage 3 saturation, path gain, CAS leaf validity —
is attempted against those same gates. Board-level authority escalation is
checked against the licensing report.

**Out of scope, deliberately.** There is no model in the loop. This run does not
measure whether a deployed board refuses a harmful prompt, does not measure
CMRR, and does not measure saturation-lock behaviour under drive. Those require
a runtime harness. Nothing in this artifact licenses a claim about deployed
behaviour, and the book does not make one.

This run does **not** supersede `pcba_red_team_safety_report_20260617.md`, which
covered the compiler-boundary claim, or
`pcba_prompt_injection_red_team_report_20260617.md`, which covered prompt
injection. Those remain the evidence for their own claims.

## Pass/Fail Thresholds

- Adversarial case pass rate must be `1.0`.
- False-positive case pass rate must be `1.0` — every part of the published
  board, and every in-range boundary value, must compile clean.
- Board authority flags must all read false.

## Adversarial Cases

{_table(attacks)}

## False-Positive Cases

{_table(benign)}

## Unenforced Properties

These are properties the book's prose leaned on that the toolchain does not
enforce. They are recorded as findings, not as passes. Each carries its
disposition — what was done about it.

"""
    if real_gaps:
        for g in real_gaps:
            body += (f"### `{g['case_id']}`\n\n"
                     f"{g['description']}\n\n"
                     f"- Hoped `{g['hoped']}`, observed `{g['observed']}`.\n"
                     f"- Evidence: `{g['evidence']['expression']}` → "
                     f"{g['evidence']['detail'][:200]}\n"
                     f"- **Disposition:** {g['disposition']}\n\n")
    else:
        body += "None.\n\n"

    body += f"""## Mitigations And Limits

- The allowed claim is limited to what this artifact observed: the published
  board compiles, and the named parameter gates reject the attempted weakenings.
- This evidence does not unlock live trading and does not make the CSB a broker
  `ACCEPT` path.
- This evidence does not support behavioural, legal, governance, privacy, or
  human-factors claims about the CSB.
- Both unenforced properties found by this run have been dispositioned above.
  Neither was closed by weakening the finding: one was corrected in the book,
  the other is documented in the book as a manual check the toolchain does not
  perform. Where a book claim outran the tooling, the claim was narrowed.

## Raw Evidence

- Path: `docs\\working\\{raw.name}`
- SHA-256: `{raw_hash}`
- JSONL records: `{len(attacks) + len(benign) + len(gaps)}`
"""
    report.write_text(body, encoding="utf-8", newline="\n")

    print(f"result            : {result}")
    print(f"adversarial       : {a_pass}/{len(attacks)}")
    print(f"false-positive    : {b_pass}/{len(benign)}")
    print(f"unenforced found  : {len(real_gaps)}")
    for g in real_gaps:
        print(f"   GAP {g['case_id']}: hoped {g['hoped']}, observed {g['observed']}")
    for r in attacks + benign:
        if not r["passed"]:
            print(f"   FAIL {r['case_id']}: expected {r['expected']}, observed {r['observed']}")
            print(f"        {r['evidence'].get('detail','')[:200]}")
    print(f"\nreport : {report}")
    print(f"raw    : {raw}  sha256 {raw_hash}")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
