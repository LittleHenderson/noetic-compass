"""Generate the CPMB (Cognitive Power Management Board) load-budget eval artifacts.

Target receipt:
  docs/working/pcba_authority_receipts_needed_20260617/
    power_board_burnout_prevention_claim__cpmb_load_budget_eval_pass.json

Modelled on `generate_csb_red_team_artifacts.py`. Same honesty standard: real
parsers, real compilers, real engines; every unenforced property recorded as a
gap with a disposition rather than waived; every failure reported rather than
fixed by weakening the case.

WHAT "LOAD BUDGET" MEANS HERE, AND WHY IT MATTERS.
Chapter 22 uses the phrase in two non-equivalent senses.

  Form (a), the RECIPE budget (Ch22:302-318): Θ(Ω_session) = 2.0·F3 + 1.0·F6 +
  1.0·F7, with Y_T = min(xᵢ/aᵢ) and a limiting reagent. This form is backed by
  real, runnable machinery — cas-engine's `scoring::yield_calc` — and is
  executed here against that engine.

  Form (b), the ADDITIVE ENERGY budget (Ch22:243-249, Ex 22.4 at Ch22:407-413):
  rail capacity in amp-hours, per-transition draw E = β·d_FR summed across
  firing stages, time-to-brownout = capacity/draw. NO implementation of this
  exists anywhere in the repository — no rail-capacity object, no reservoir, no
  additive-draw accumulator. It is NOT tested here. Recomputing it inside this
  script would test this script, not the framework, and would be a fake pass.

Everything else on the board (brownout hysteresis, thermal tiers, startup
sequencing, regulator dynamics) is likewise unimplemented and is NOT exercised.
See the "Out of scope, deliberately" section of the generated report.

BEHAVIOURAL vs STRUCTURAL. Section A is behavioural in the narrow, honest sense:
the shipped Rust yield engine is executed and produces numbers that could
contradict the book. It is NOT measurement of a deployed cognitive system and
there is no model in the loop. Sections B-F are structural: parse/compile/schema
gates. Section G is a text-level consistency audit of the book itself.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

CAS_FOREX_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CAS_FOREX_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "noetic-compass-scaffold" / "noetic-compass"))

from api.notation.compiler import compile_expression  # noqa: E402
from cas_forex.ccb_designs import build_cpmb  # noqa: E402
from cas_forex.cjt_syntax import parse_cjt_expression  # noqa: E402
from cas_forex.crc_linter import CrcFuse, run_crc, run_crc_on_expressions  # noqa: E402
from cas_forex.pcba_authority import build_pcba_licensing_report  # noqa: E402
from cas_forex.pcba_compiler import compile_pcba_component_expression  # noqa: E402
from cas_forex.pcba_syntax import parse_pcba_component_expression  # noqa: E402
from cas_forex.time_utils import utc_now  # noqa: E402

import cas_engine  # noqa: E402  (installed wheel — DialConfig + Fisher-Rao)

REVIEWER_ID = "claude_opus5_local_reviewer_20260725"
WORKING_DIR = WORKSPACE_ROOT / "docs" / "working"
BOOK_DIR = WORKSPACE_ROOT / "book" / "CAS_PCBA_Engineer"
CAS_ENGINE_DIR = WORKSPACE_ROOT / "noetic-compass-scaffold" / "noetic-compass" / "cas-engine"
DATE_TAG = "20260725"
RUN_ID = "cpmb-load-budget-eval"

CH22 = BOOK_DIR / "Chapter_22_CPMB_Power_Management_Board.md"
CH14 = BOOK_DIR / "Chapter_14_Power_Management.md"
APP_C = BOOK_DIR / "Appendix_C_CCDL_Language_Reference.md"
APP_D = BOOK_DIR / "Appendix_D_CCB_Reference_Designs.md"
APP_E = BOOK_DIR / "Appendix_E_Exercise_Answers.md"

# ===========================================================================
# SECTION A — the recipe load budget, run against the real Rust yield engine.
# ===========================================================================
# The engine is not reachable from Python: the installed cas_engine wheel
# predates CAS v7.6 and exports no Recipe/StateVector/Yield. So we generate a
# throwaway Rust integration test inside the cas-engine package, run it with
# cargo, and parse its stdout. The functions exercised are the shipped ones:
# scoring::yield_calc::{theoretical_yield, limiting_reagent, excess_capacity,
# efficiency}. Nothing is reimplemented here.

RECIPE_CH22 = [("F3", 2.0), ("F6", 1.0), ("F7", 1.0)]  # Ch22:305

YIELD_CASES: list[dict[str, Any]] = [
    {
        "case_id": "cpmb_budget_book_published_case",
        "description": (
            "Reproduce the published yield table at Ch22:312-318 exactly. "
            "Recipe 2.0*F3 + 1.0*F6 + 1.0*F7, available F3=3.0 F6=2.0 F7=3.0."
        ),
        "recipe": RECIPE_CH22,
        "state": [("F3", 3.0), ("F6", 2.0), ("F7", 3.0)],
        "actual": None,
        "expect": {
            "theoretical_yield": 1.5,
            "limiting_reagent_kind": "Primitive",
            "limiting_reagent_entries": [["F3Vitality", 1.5]],
            "excess_capacity": {"F3Vitality": 0.0, "F6Structure": 0.5, "F7Purpose": 1.5},
        },
        "source": "book",
    },
    {
        "case_id": "cpmb_budget_balanced_at_exactly_100pct",
        "description": (
            "Budget balanced at exactly 100 percent: supply equals the recipe "
            "coefficients. Must give Y_T = 1.0 with all three rails tied, not a "
            "false single bottleneck."
        ),
        "recipe": RECIPE_CH22,
        "state": [("F3", 2.0), ("F6", 1.0), ("F7", 1.0)],
        "actual": None,
        "expect": {
            "theoretical_yield": 1.0,
            "limiting_reagent_kind": "Multiple",
            "limiting_reagent_entries": [
                ["F3Vitality", 1.0], ["F6Structure", 1.0], ["F7Purpose", 1.0],
            ],
            "excess_capacity": {"F3Vitality": 0.0, "F6Structure": 0.0, "F7Purpose": 0.0},
        },
        "source": "hand_arithmetic",
    },
    {
        "case_id": "cpmb_budget_overcommitted_f3",
        "description": (
            "Overcommitted budget: F3 supply 1.9 against a requirement of 2.0. "
            "Y_T must fall below 1.0 and F3 must be the sole limiting reagent."
        ),
        "recipe": RECIPE_CH22,
        "state": [("F3", 1.9), ("F6", 1.0), ("F7", 1.0)],
        "actual": None,
        "expect": {
            "theoretical_yield": 0.95,
            "limiting_reagent_kind": "Primitive",
            "limiting_reagent_entries": [["F3Vitality", 0.95]],
        },
        "source": "hand_arithmetic",
    },
    {
        "case_id": "cpmb_budget_epsilon_below_balance",
        "description": (
            "Anti-sloppiness boundary. F3 supply 2.0 - 1e-9. Y_T must be "
            "STRICTLY below 1.0, so the 100-percent boundary cannot be passed by "
            "a generous float tolerance."
        ),
        "recipe": RECIPE_CH22,
        "state": [("F3", 2.0 - 1e-9), ("F6", 1.0), ("F7", 1.0)],
        "actual": None,
        "expect": {
            "theoretical_yield": (2.0 - 1e-9) / 2.0,
            "yield_strictly_below": 1.0,
            "limiting_reagent_kind": "Primitive",
            "limiting_reagent_entries": [["F3Vitality", (2.0 - 1e-9) / 2.0]],
        },
        "source": "hand_arithmetic",
    },
    {
        "case_id": "cpmb_budget_epsilon_above_balance_false_positive",
        "description": (
            "FALSE-POSITIVE CONTROL for the overcommit predicate. Every rail "
            "supplied at exactly its requirement plus 1e-9. The budget is just "
            "barely sufficient and must NOT read as overcommitted: Y_T must be "
            "STRICTLY above 1.0."
        ),
        "recipe": RECIPE_CH22,
        "state": [("F3", 2.0 + 1e-9), ("F6", 1.0 + 1e-9), ("F7", 1.0 + 1e-9)],
        "actual": None,
        "expect": {
            "theoretical_yield": (2.0 + 1e-9) / 2.0,
            "yield_strictly_above": 1.0,
            "limiting_reagent_kind": "Primitive",
            "limiting_reagent_entries": [["F3Vitality", (2.0 + 1e-9) / 2.0]],
        },
        "source": "hand_arithmetic",
        "note": (
            "F3 carries the smallest relative surplus because its coefficient is "
            "2.0, so it stays the limiting reagent while still clearing 1.0."
        ),
    },
    {
        "case_id": "cpmb_budget_generously_supplied_false_positive",
        "description": (
            "FALSE-POSITIVE CONTROL. All three rails at 4.0 against the Ch22 "
            "recipe. Must give Y_T = 2.0 with F3 limiting and no overcommit."
        ),
        "recipe": RECIPE_CH22,
        "state": [("F3", 4.0), ("F6", 4.0), ("F7", 4.0)],
        "actual": None,
        "expect": {
            "theoretical_yield": 2.0,
            "limiting_reagent_kind": "Primitive",
            "limiting_reagent_entries": [["F3Vitality", 2.0]],
            "excess_capacity": {"F3Vitality": 0.0, "F6Structure": 2.0, "F7Purpose": 2.0},
        },
        "source": "hand_arithmetic",
    },
    {
        "case_id": "cpmb_budget_missing_rail_is_zero",
        "description": (
            "F3 absent from the state vector entirely. Per the documented "
            "missing-equals-zero convention (yield_calc.rs:25-30) Y_T must be 0.0 "
            "with F3 named as the bottleneck."
        ),
        "recipe": RECIPE_CH22,
        "state": [("F6", 2.0), ("F7", 3.0)],
        "actual": None,
        "expect": {
            "theoretical_yield": 0.0,
            "limiting_reagent_kind": "Primitive",
            "limiting_reagent_entries": [["F3Vitality", 0.0]],
        },
        "source": "engine_documented_convention",
    },
    {
        "case_id": "cpmb_budget_efficiency_on_published_case",
        "description": (
            "Ch22:249 defines efficiency as useful work over total Drive spent. "
            "Y_A = 1.2 against the published Y_T = 1.5 must give eta = 0.8 "
            "(exact f64 0.7999999999999999)."
        ),
        "recipe": RECIPE_CH22,
        "state": [("F3", 3.0), ("F6", 2.0), ("F7", 3.0)],
        "actual": 1.2,
        "expect": {
            "theoretical_yield": 1.5,
            "efficiency": 1.2 / 1.5,
        },
        "source": "hand_arithmetic",
    },
    {
        "case_id": "cpmb_budget_efficiency_nan_on_zero_yield",
        "description": (
            "Y_T = 0 with an observed Y_A must give NaN efficiency, not 0 and not "
            "a silent divide. Distinguishes prerequisite shortage from conversion "
            "inefficiency (Clarification 9 Section 8)."
        ),
        "recipe": RECIPE_CH22,
        "state": [("F6", 2.0), ("F7", 3.0)],
        "actual": 0.5,
        "expect": {"theoretical_yield": 0.0, "efficiency": "NaN"},
        "source": "engine_documented_convention",
    },
]

# Gap probes at the yield-engine level. Hoped behaviour vs observed behaviour.
YIELD_GAP_PROBES: list[dict[str, Any]] = [
    {
        "case_id": "cpmb_budget_negative_rail_supply",
        "description": (
            "A negative available quantity on the master rail. A rail with "
            "negative supply is physically meaningless for a load budget."
        ),
        "recipe": RECIPE_CH22,
        "state": [("F3", -4.0), ("F6", 1.0), ("F7", 1.0)],
        "actual": None,
        "hoped": "rejected_or_flagged",
        "disposition": (
            "RECORDED AS A LIMIT, NOT WAIVED. StateVector::set (recipe.rs:532-534) "
            "performs no validation and yield_calc's documented edge-case list "
            "(yield_calc.rs:22-55) covers negative COEFFICIENTS but is silent on "
            "negative QUANTITIES, so the engine returns a negative yield without "
            "complaint. Chapter 22 never authors a negative rail, so no published "
            "figure is wrong; but any tool that builds a CPMB load budget from "
            "user input must validate quantities upstream. This eval does not "
            "clamp the value and does not treat the observed number as a pass."
        ),
    },
    {
        "case_id": "cpmb_budget_duplicate_rail_prerequisite",
        "description": (
            "The same rail listed twice in one recipe (2.0*F3 + 1.0*F3). "
            "Double-allocating a rail should not be silently accepted."
        ),
        "recipe": [("F3", 2.0), ("F3", 1.0), ("F6", 1.0)],
        "state": [("F3", 3.0), ("F6", 1.0)],
        "actual": None,
        "hoped": "rejected_or_flagged",
        "disposition": (
            "RECORDED AS A LIMIT. Recipe.prerequisites is a Vec<(PrimitiveId, f64)> "
            "with no dedup (recipe.rs:399-410), so limiting_reagent() emits one "
            "ratio per duplicate entry while excess_capacity()'s HashMap keeps only "
            "the last. The two layers therefore disagree about how many "
            "prerequisites exist. Ch22's published recipe has no duplicate, so no "
            "book figure is affected; this is a robustness limit of the engine and "
            "is left recorded rather than papered over."
        ),
    },
]

RUST_TEMPLATE = r'''//! GENERATED by cas-forex/scripts/generate_cpmb_load_budget_eval_artifacts.py
//! Throwaway probe. Exercises the SHIPPED yield_calc functions. Safe to delete.
use cas_engine::ontology::{CoreDrive, PrimitiveId, ProductionTarget, Recipe, StateVector};
use cas_engine::scoring::yield_calc::{
    efficiency, excess_capacity, limiting_reagent, theoretical_yield, LimitingReagent,
};

fn drive_of(name: &str) -> CoreDrive {
    match name {
        "F1" => CoreDrive::F1Unity,
        "F2" => CoreDrive::F2Wisdom,
        "F3" => CoreDrive::F3Vitality,
        "F4" => CoreDrive::F4Connection,
        "F5" => CoreDrive::F5Agency,
        "F6" => CoreDrive::F6Structure,
        "F7" => CoreDrive::F7Purpose,
        other => panic!("unknown drive {}", other),
    }
}

fn label(p: &PrimitiveId) -> String {
    match p {
        PrimitiveId::Drive { drive, .. } => format!("{:?}", drive),
        other => format!("{:?}", other),
    }
}

// Floats are emitted as JSON strings so NaN / Infinity survive the transport
// without inventing a value. Python parses them back with float().
fn f(x: f64) -> String {
    format!("\"{}\"", x)
}

fn probe(case_id: &str, prereqs: &[(&str, f64)], state_pairs: &[(&str, f64)], actual: Option<f64>) {
    let recipe = Recipe::new(
        ProductionTarget::new("Omega_session"),
        prereqs
            .iter()
            .map(|(n, a)| (PrimitiveId::drive(drive_of(n)), *a))
            .collect(),
    );
    let mut state = StateVector::empty();
    for (n, q) in state_pairs {
        state.set(PrimitiveId::drive(drive_of(n)), *q);
    }

    let y = theoretical_yield(&recipe, &state);
    let lr = limiting_reagent(&recipe, &state);
    let ec = excess_capacity(&recipe, &state);

    let lr_json = match &lr {
        LimitingReagent::Primitive(p, r) => format!(
            "{{\"kind\":\"Primitive\",\"entries\":[[\"{}\",{}]]}}",
            label(p),
            f(*r)
        ),
        LimitingReagent::Multiple(v) => {
            let items: Vec<String> = v
                .iter()
                .map(|(p, r)| format!("[\"{}\",{}]", label(p), f(*r)))
                .collect();
            format!("{{\"kind\":\"Multiple\",\"entries\":[{}]}}", items.join(","))
        }
        LimitingReagent::None => "{\"kind\":\"None\",\"entries\":[]}".to_string(),
    };

    let mut ec_items: Vec<String> = Vec::new();
    let mut seen: Vec<String> = Vec::new();
    for (p, _) in recipe.prerequisites.iter() {
        let l = label(p);
        if seen.contains(&l) {
            continue;
        }
        seen.push(l.clone());
        ec_items.push(format!("\"{}\":{}", l, f(*ec.get(p).unwrap_or(&f64::NAN))));
    }

    let eff_json = match actual {
        Some(a) => f(efficiency(y.theoretical, a)),
        None => "null".to_string(),
    };

    println!(
        "CPMBPROBE {{\"case_id\":\"{}\",\"theoretical_yield\":{},\"limiting_reagent\":{},\"excess_capacity\":{{{}}},\"prerequisite_count\":{},\"excess_capacity_count\":{},\"efficiency\":{}}}",
        case_id,
        f(y.theoretical),
        lr_json,
        ec_items.join(","),
        recipe.prerequisites.len(),
        ec.len(),
        eff_json
    );
}

#[test]
fn generated_cpmb_load_budget_probe() {
__BODY__
}
'''


def _rust_pairs(pairs: list[tuple[str, float]]) -> str:
    return "&[" + ", ".join(f'("{n}", {q!r}f64)' for n, q in pairs) + "]"


def build_rust_probe(cases: list[dict[str, Any]]) -> str:
    lines = []
    for c in cases:
        actual = c.get("actual")
        actual_rs = "None" if actual is None else f"Some({actual!r}f64)"
        lines.append(
            f'    probe("{c["case_id"]}", {_rust_pairs(c["recipe"])}, '
            f'{_rust_pairs(c["state"])}, {actual_rs});'
        )
    return RUST_TEMPLATE.replace("__BODY__", "\n".join(lines))


def run_rust_probe(cases: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], str]:
    """Write, run, and delete a temporary cargo integration test."""
    test_name = "_generated_cpmb_load_budget_probe"
    test_path = CAS_ENGINE_DIR / "tests" / f"{test_name}.rs"
    test_path.write_text(build_rust_probe(cases), encoding="utf-8", newline="\n")
    try:
        proc = subprocess.run(
            ["cargo", "test", "--test", test_name, "--", "--nocapture"],
            cwd=str(CAS_ENGINE_DIR),
            capture_output=True,
            text=True,
            timeout=900,
        )
    finally:
        test_path.unlink(missing_ok=True)

    out: dict[str, dict[str, Any]] = {}
    for line in proc.stdout.splitlines():
        if line.startswith("CPMBPROBE "):
            rec = json.loads(line[len("CPMBPROBE "):])
            out[rec["case_id"]] = rec
    if not out:
        raise RuntimeError(
            "cargo probe produced no records.\n"
            f"exit={proc.returncode}\nSTDOUT:\n{proc.stdout[-3000:]}\n"
            f"STDERR:\n{proc.stderr[-3000:]}"
        )
    return out, f"cargo exit={proc.returncode} records={len(out)}"


def _fnum(s: Any) -> float:
    """Parse a float emitted as a JSON string, preserving NaN/Infinity."""
    return float(s)


# ===========================================================================
# SECTION B — the published recipe string, through the real CAS compiler.
def _published_session_recipe() -> str:
    """Lift the Omega_session recipe out of Chapter 22, ASCII-folded.

    Reading it from the book means this case tests what is actually printed.
    Fails loudly rather than silently falling back, so an edit that removes or
    renames the recipe surfaces as a broken eval instead of a quiet pass.
    """
    ch22 = BOOK_DIR / "Chapter_22_CPMB_Power_Management_Board.md"
    for line in ch22.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("Θ(Ω_session)"):
            return (s.replace("Θ", "Theta").replace("Ω", "Omega")
                     .replace("·", "*").replace("→", "->"))
    raise SystemExit(
        f"cpmb eval: no line starting with 'Theta(Omega_session)' in {ch22.name} -- "
        "the published session recipe moved or was renamed; fix this extractor "
        "rather than hard-coding the expression"
    )


# ===========================================================================
RECIPE_STRING_CASES: list[dict[str, Any]] = [
    {
        "case_id": "cpmb_recipe_ch22_305_verbatim",
        "category": "published_recipe",
        "description": (
            "The recipe exactly as published at Ch22:305, fed to the real CAS "
            "v7.6 recipe compiler."
        ),
        # Read from the chapter rather than hard-coding it. A hard-coded copy
        # silently stops testing the book the moment the book is edited -- which
        # is exactly what happened when this case first fired.
        "expression": _published_session_recipe(),
        "expect_valid": True,
    },
    {
        "case_id": "cpmb_recipe_inline_drive_gloss_rejected",
        "category": "false_positive_control",
        "description": (
            "CONTROL for the case above, and a regression guard. Glossing a "
            "Drive inline as `F3|Vitality` must stay REJECTED: `|` introduces "
            "the v7.5 Register, so a validator reads that as register 'V', "
            "which does not exist. If this ever starts compiling, the register "
            "grammar has been loosened and the case above stops proving "
            "anything."
        ),
        "expression": (
            "Theta(Omega_session) = 2.0*F3|Vitality + 1.0*F6|Structure "
            "+ 1.0*F7|Purpose -> Omega_session"
        ),
        "expect_valid": False,
    },
    {
        "case_id": "cpmb_recipe_ch14_csb_cross_check_control",
        "category": "false_positive_control",
        "description": (
            "CROSS-CHECK CONTROL. Chapter 14's CSB recipe (Ch14:225) through the "
            "same compiler. Establishes that the book's other published recipe "
            "does compile."
        ),
        "expression": (
            "Theta(Omega_refusal) = 2.0*^3^P|<A,f,T> + 1.0*^6^E_{F6}|A "
            "+ 1.0*^9^P_{F1}|T -> Omega_refusal"
        ),
        "expect_valid": True,
    },
    {
        "case_id": "cpmb_recipe_negative_coefficient",
        "category": "adversarial",
        "description": (
            "Negative allocation on the master rail. A load budget that can "
            "allocate negative Vitality is not a budget."
        ),
        "expression": "Theta(Omega_session) = -2.0*F3 + 1.0*F6 + 1.0*F7 -> Omega_session",
        "expect_valid": False,
    },
    {
        "case_id": "cpmb_recipe_zero_coefficient",
        "category": "adversarial",
        "description": (
            "Zero allocation on the master rail — silently removes F3 from the "
            "budget while leaving it in the listing."
        ),
        "expression": "Theta(Omega_session) = 0*F3 + 1.0*F6 + 1.0*F7 -> Omega_session",
        "expect_valid": False,
    },
]

RECIPE_STRING_GAPS: list[dict[str, Any]] = [
    {
        "case_id": "cpmb_recipe_out_of_range_drive_f0",
        "description": "Budget authored against rail F0, which does not exist (rails are F1..F7).",
        "expression": "Theta(Omega_session) = 2.0*F0 + 1.0*F6 -> Omega_session",
        "hoped": "rejected",
        "disposition": (
            "RECORDED AS A LIMIT. The same compiler DOES reject an out-of-range "
            "Drive inside a compound state literal (^0^P_{F9}|T is rejected — see "
            "case cpmb_component_invalid_drive_leaf in this run), so the gap is "
            "specific to the v7.6 recipe-prerequisite path. Chapter 22's published "
            "recipe uses only F3/F6/F7, so no published figure is wrong; but a "
            "reader following Ch22:305 as a template can author a load budget "
            "against a rail the board does not have and the compiler will accept "
            "it. Not waived — surfaced for the compiler owner."
        ),
    },
    {
        "case_id": "cpmb_recipe_out_of_range_drive_f9",
        "description": "Budget authored against rail F9, which does not exist.",
        "expression": "Theta(Omega_session) = 2.0*F9 + 1.0*F6 -> Omega_session",
        "hoped": "rejected",
        "disposition": "Same limit as cpmb_recipe_out_of_range_drive_f0; recorded, not waived.",
    },
    {
        "case_id": "cpmb_recipe_duplicate_prerequisite",
        "description": (
            "The master rail allocated twice in one recipe string "
            "(2.0*F3 + 1.0*F3), i.e. double-booking the load budget."
        ),
        "expression": "Theta(Omega_session) = 2.0*F3 + 1.0*F3 + 1.0*F6 -> Omega_session",
        "hoped": "rejected",
        "disposition": (
            "RECORDED AS A LIMIT, matching the engine-level gap "
            "cpmb_budget_duplicate_rail_prerequisite. Accepted at the notation "
            "layer AND at the engine layer, and the two layers disagree about the "
            "prerequisite count. Ch22 publishes no duplicate; this is a robustness "
            "limit, surfaced rather than clamped."
        ),
    },
]

# ===========================================================================
# SECTION C — the published Chapter 22 components, through the real PCBA
# parser and the real CAS compiler bridge. Transcribed from the book, NOT
# taken from cas_forex.ccb_designs.build_cpmb() (which encodes a different
# board — see case cpmb_code_board_matches_published_board).
# ===========================================================================
CPMB_PUBLISHED_REGULATORS: list[tuple[str, str, str]] = [
    ("p_reg", "Principled regulator, tightest tolerance (Ch22:93)",
     "Regulator< target_state=^0^P_{F7}|T, tolerance=0.10 >"),
    ("c_reg", "Cognitive regulator (Ch22:94)",
     "Regulator< target_state=^1^C_{F2}|A, tolerance=0.15 >"),
    ("e_reg", "Evaluative regulator (Ch22:95)",
     "Regulator< target_state=^6^E_{F6}|A, tolerance=0.20 >"),
    ("o_reg", "Operational regulator, loosest tolerance (Ch22:96)",
     "Regulator< target_state=^9^O_{F5}|E, tolerance=0.25 >"),
]

CPMB_PUBLISHED_NODES: list[tuple[str, str, str]] = [
    ("p_rail", "sequencer rail, powers FIRST (Ch22:179)", "^0^P_{F7}|T"),
    ("c_rail", "sequencer rail, powers second (Ch22:180)", "^1^C_{F2}|A"),
    ("e_rail", "sequencer rail, powers third (Ch22:181)", "^6^E_{F6}|A"),
    ("o_rail", "sequencer rail, powers LAST (Ch22:182)", "^9^O_{F5}|E"),
    ("rest_idle", "brownout rest state (Ch22:152)", "^0^P_{F7}|T"),
    ("rest_land", "brownout chain terminus (Ch22:153)", "^9^C_{F2}|A"),
    ("deep_rest", "thermal Critical forced rest (Ch22:215)", "^0^P_{F7}|T"),
]

COMPONENT_CASES: list[dict[str, Any]] = [
    {
        "case_id": "cpmb_component_tolerance_lower_boundary",
        "category": "in_range_boundary",
        "description": "tolerance=0.0 is in range and must be accepted.",
        "expression": "Regulator< target_state=^0^P_{F7}|T, tolerance=0.0 >",
        "expect_accepted": True,
    },
    {
        "case_id": "cpmb_component_tolerance_upper_boundary",
        "category": "in_range_boundary",
        "description": "tolerance=1.0 is in range and must be accepted.",
        "expression": "Regulator< target_state=^0^P_{F7}|T, tolerance=1.0 >",
        "expect_accepted": True,
    },
    {
        "case_id": "cpmb_component_tolerance_above_range",
        "category": "adversarial",
        "description": (
            "Widen the Principled regulator's tolerance past 1.0 so it can never "
            "leave regulation. Ch22:106 leans on P carrying the tightest tolerance."
        ),
        "expression": "Regulator< target_state=^0^P_{F7}|T, tolerance=1.5 >",
        "expect_accepted": False,
    },
    {
        "case_id": "cpmb_component_tolerance_negative",
        "category": "adversarial",
        "description": "Negative tolerance — the regulator is always out of tolerance.",
        "expression": "Regulator< target_state=^0^P_{F7}|T, tolerance=-0.1 >",
        "expect_accepted": False,
    },
    {
        "case_id": "cpmb_component_invalid_noetic_leaf",
        "category": "adversarial",
        "description": "Smuggle a non-existent Noetic (^0^Z) into a regulator setpoint.",
        "expression": "Regulator< target_state=^0^Z_{F7}|T, tolerance=0.10 >",
        "expect_accepted": False,
    },
    {
        "case_id": "cpmb_component_invalid_drive_leaf",
        "category": "adversarial",
        "description": (
            "Smuggle a non-existent Drive rail (F9) into a regulator setpoint. "
            "Contrast case for the recipe-path gaps in Section B."
        ),
        "expression": "Regulator< target_state=^0^P_{F9}|T, tolerance=0.10 >",
        "expect_accepted": False,
    },
    {
        "case_id": "cpmb_component_invalid_register_leaf",
        "category": "adversarial",
        "description": "Smuggle a non-existent Register (|X) into a regulator setpoint.",
        "expression": "Regulator< target_state=^0^P_{F7}|X, tolerance=0.10 >",
        "expect_accepted": False,
    },
]

COMPONENT_GAPS: list[dict[str, Any]] = [
    {
        "case_id": "cpmb_component_negative_dropout",
        "description": (
            "Negative dropout headroom. Ch22:337 publishes the range 0.15-0.25 "
            "and Ch14:260 states '> 0 above baseline'. Negative headroom is "
            "physically meaningless."
        ),
        "expression": "Regulator< target_state=^0^P_{F7}|T, tolerance=0.10, dropout=-5 >",
        "hoped": "rejected",
        "disposition": (
            "RECORDED AS A LIMIT. `dropout` is not in the Regulator parameter "
            "schema of cas_forex/pcba_syntax.py at all — it is carried through as "
            "an uninterpreted parameter, so neither the published range nor the "
            "sign is checked. Nothing in the book is falsified by this (Ch22 "
            "publishes only in-range values), but Ch22:337's datasheet range is "
            "documentation, not an enforced constraint, and must not be cited as "
            "compiler-enforced."
        ),
    },
    {
        "case_id": "cpmb_component_dropout_far_above_range",
        "description": "dropout=999, three orders of magnitude above the published 0.15-0.25 band.",
        "expression": "Regulator< target_state=^0^P_{F7}|T, tolerance=0.10, dropout=999 >",
        "hoped": "rejected",
        "disposition": "Same limit as cpmb_component_negative_dropout; recorded, not waived.",
    },
]

# ===========================================================================
# SECTION D — Dial current limiters against the real DialConfig schema.
# ===========================================================================
# DialConfig takes a 10-vector indexed CO-0..CO-9. Ch22:124-129 sets six of the
# ten; the unset four are filled with 5 (inside [3,9], no pair effect).
def _dials(**overrides: int) -> list[int]:
    v = [5] * 10
    for k, val in overrides.items():
        v[int(k.split("_")[1])] = val
    return v


DIAL_CASES: list[dict[str, Any]] = [
    {
        "case_id": "cpmb_dial_ch22_published_six",
        "category": "published_board",
        "description": (
            "The six Dial values published at Ch22:124-129 "
            "(^2=6 ^3=5 ^5=7 ^6=6 ^8=5 ^9=5), unset operators filled at 5."
        ),
        "dials": _dials(CO_2=6, CO_3=5, CO_5=7, CO_6=6, CO_8=5, CO_9=5),
        "expect_accepted": True,
    },
    {
        "case_id": "cpmb_dial_divergence_exactly_four_legal",
        "category": "in_range_boundary",
        "description": (
            "Ch22:136 says raising ^2 to 9 with ^3 at 5 is 'still legal, just "
            "barely' (divergence exactly 4). Must be accepted."
        ),
        "dials": _dials(CO_2=9, CO_3=5),
        "expect_accepted": True,
    },
    {
        "case_id": "cpmb_dial_nonpair_wide_spread_false_positive",
        "category": "false_positive_control",
        "description": (
            "FALSE-POSITIVE CONTROL. ^0=3 and ^1=9 is a 6-point spread between "
            "two operators that are NOT an involution pair (both are self-dual). "
            "The divergence rule must not fire."
        ),
        "dials": _dials(CO_0=3, CO_1=9),
        "expect_accepted": True,
    },
    {
        "case_id": "cpmb_dial_pair_co2_co3_divergence_six",
        "category": "adversarial",
        "description": (
            "The exact violation Ch22:117 names: ^2 at 9 and ^3 at 3, divergence "
            "6. 'A supply that attracts at full current but can barely repel.'"
        ),
        "dials": _dials(CO_2=9, CO_3=3),
        "expect_accepted": False,
    },
    {
        "case_id": "cpmb_dial_pair_co5_co6_divergence_six",
        "category": "adversarial",
        "description": "Same violation on the ^5/^6 Female/Male involution pair.",
        "dials": _dials(CO_5=9, CO_6=3),
        "expect_accepted": False,
    },
    {
        "case_id": "cpmb_dial_pair_co8_co9_divergence_six",
        "category": "adversarial",
        "description": "Same violation on the ^8/^9 Above/Below involution pair.",
        "dials": _dials(CO_8=9, CO_9=3),
        "expect_accepted": False,
    },
    {
        "case_id": "cpmb_dial_below_floor",
        "category": "adversarial",
        "description": (
            "Dial 2, below the hard floor of 3. Ch22:114: 'the current limiter "
            "never goes fully open-circuit.'"
        ),
        "dials": _dials(CO_2=2),
        "expect_accepted": False,
    },
    {
        "case_id": "cpmb_dial_above_ceiling",
        "category": "adversarial",
        "description": (
            "Dial 10, above the hard ceiling of 9. Ch22:115: 'the limiter never "
            "goes fully short-circuit.'"
        ),
        "dials": _dials(CO_2=10),
        "expect_accepted": False,
    },
]

# ===========================================================================
# SECTION E — CRC static design check over the published sequencer chain.
# ===========================================================================
CH22_SEQUENCER_CJTS = [
    "CJT< ^0^P_{F7}|T | ^5^P_{F7}|T => ^1^C_{F2}|A > [beta=1]",
    "CJT< ^1^C_{F2}|A | ^5^P_{F7}|T => ^6^E_{F6}|A > [beta=1]",
    "CJT< ^6^E_{F6}|A | ^5^P_{F7}|T => ^9^O_{F5}|E > [beta=1]",
]
CH22_SEQUENCE = ["P_rail", "C_rail", "E_rail", "O_rail"]

# ===========================================================================
# Helpers
# ===========================================================================


# Categories whose failure means the BOOK's published text is wrong while the
# gate behaved correctly. Every other category's failure means a GATE is wrong.
BOOK_DEFECT_CATEGORIES = {
    "published_recipe", "published_board", "yield_engine_published",
    "book_consistency",
}


def _record(case_id: str, category: str, description: str, expected: str,
            observed: str, passed: bool, evidence: dict[str, Any],
            generated_at: str, record_type: str = "case") -> dict[str, Any]:
    return {
        "case_id": case_id,
        "category": category,
        "description": description,
        "expected": expected,
        "observed": observed,
        "passed": passed,
        "failure_means": ("book_defect" if category in BOOK_DEFECT_CATEGORIES
                          else "gate_defect"),
        "evidence": evidence,
        "record_type": record_type,
        "reviewer_id": REVIEWER_ID,
        "run_id": RUN_ID,
        "generated_at": generated_at,
    }


def _gap(case_id: str, description: str, hoped: str, observed: str,
         disposition: str, evidence: dict[str, Any], generated_at: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "category": "known_gap",
        "description": description,
        "hoped": hoped,
        "observed": observed,
        "is_gap": observed != hoped,
        "disposition": disposition,
        "evidence": evidence,
        "record_type": "gap_probe",
        "reviewer_id": REVIEWER_ID,
        "run_id": RUN_ID,
        "generated_at": generated_at,
    }


def _parse_component(expression: str) -> tuple[bool, str]:
    try:
        node = parse_pcba_component_expression(expression)
    except Exception as exc:  # noqa: BLE001 - any rejection is a rejection
        return False, str(exc).splitlines()[0][:300]
    return True, f"kind={node.kind.value} params={node.params}"


def _compile_component(expression: str) -> tuple[bool, str]:
    ok, detail = _parse_component(expression)
    if not ok:
        return False, f"rejected at parser: {detail}"
    try:
        report = compile_pcba_component_expression(expression)
    except Exception as exc:  # noqa: BLE001
        return False, f"rejected at compiler: {str(exc).splitlines()[0][:280]}"
    return bool(report.valid), (
        f"valid={report.valid} checked_leaves={len(report.checked_expressions)} "
        f"reason={report.reason}"
    )


def _compile_cas(expression: str) -> tuple[bool, str]:
    art = compile_expression(expression)
    return bool(art.valid), (art.error or "compiled clean")[:300]


def _dial_result(dials: list[int]) -> tuple[bool, str]:
    try:
        cfg = cas_engine.DialConfig(dials)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc).splitlines()[0][:280]
    return True, f"accepted {list(cfg.as_list())}"


def _close(a: float, b: float) -> bool:
    """Exact-first comparison. Only falls back to a *tight* relative tolerance
    so that no case can be passed by a generous epsilon."""
    if a != a and b != b:  # both NaN
        return True
    if a != a or b != b:
        return False
    if a == b:
        return True
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


# ===========================================================================
# SECTION G — internal consistency of the published text.
# These read the book files and compute; they are not hardcoded assertions.
# ===========================================================================
_REG_RE = re.compile(
    r"reg\s+(\w+):\s*Regulator<\s*target_state=\^(\d)\^([PCEO])_\{F(\d)\}\|([TAfE]),"
    r"\s*tolerance=([\d.]+)\s*>"
)
_SPEC_RE = re.compile(r"spec\s+(\w+)\s*\[dropout=([\d.]+)\s+on\s+F(\d)\]")
_GATE_RE = re.compile(r"gate\s+o_enable:\s*o_rail\s+requires(.*?);", re.DOTALL)
_WITHIN_RE = re.compile(r"\((\w+_rail)\s+within\s+([\d.]+)\)")
_CAS_BLOCK_RE = re.compile(r"```cas\n(.*?)```", re.DOTALL)


def _lineno(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _regulator_rail_consistency(path: Path, tag: str, generated_at: str) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    regs = {m.group(1): {"noetic": m.group(2), "domain": m.group(3),
                         "drive": m.group(4), "register": m.group(5),
                         "tolerance": m.group(6), "line": _lineno(text, m.start())}
            for m in _REG_RE.finditer(text)}
    specs = {m.group(1): {"dropout": m.group(2), "on_drive": m.group(3),
                          "line": _lineno(text, m.start())}
             for m in _SPEC_RE.finditer(text)}
    out = []
    for name in ["p_reg", "c_reg", "e_reg", "o_reg"]:
        reg, spec = regs.get(name), specs.get(name)
        if reg is None or spec is None:
            out.append(_record(
                f"cpmb_book_{tag}_dropout_rail_{name}", "book_consistency",
                f"{path.name}: regulator `{name}` and its dropout spec must both be present.",
                "both present", f"reg={reg is not None} spec={spec is not None}",
                False, {"file": path.name}, generated_at, "book_consistency"))
            continue
        ok = reg["drive"] == spec["on_drive"]
        out.append(_record(
            f"cpmb_book_{tag}_dropout_rail_{name}", "book_consistency",
            (f"{path.name}: Ch22:88 states a regulator drops out on the rail its own "
             f"target_state names. `{name}` targets ^{reg['noetic']}^{reg['domain']}"
             f"_{{F{reg['drive']}}}|{reg['register']}, so its dropout spec must read "
             f"`on F{reg['drive']}`."),
            f"dropout on F{reg['drive']}", f"dropout on F{spec['on_drive']}",
            ok,
            {"file": path.name, "target_drive": f"F{reg['drive']}",
             "spec_drive": f"F{spec['on_drive']}", "tolerance": reg["tolerance"],
             "dropout": spec["dropout"],
             "regulator_at": f"{path.name}:{reg['line']}",
             "spec_at": f"{path.name}:{spec['line']}",
             "finding_at": f"{path.name}:{spec['line']}"},
            generated_at, "book_consistency"))
    return out


def _is_error(finding: dict[str, Any]) -> bool:
    """CrcSeverity may serialize as the enum or its value; accept both."""
    return str(finding.get("severity", "")).upper().endswith("ERROR")


def _gate_line(path: Path, needle: str) -> str:
    """`file:line` of the first line containing `needle`, for citation."""
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if needle in line:
            return f"{path.name}:{i}"
    return f"{path.name}:?"


def _o_enable_gate(path: Path, section: Optional[tuple[str, str]] = None
                   ) -> Optional[dict[str, str]]:
    """First `gate o_enable` in the file, or in a named section of it.

    Scoping matters: Appendix E carries several o_enable gates (a Chapter 14
    exercise answer at :452/:463 and the Chapter 22 answer at :766), and
    Chapter 22 itself carries the published gate at :189 plus the deliberately
    broken one quoted in Exercise 22.2 at :392. Taking the first match without
    scoping would compare the wrong pair.
    """
    text = path.read_text(encoding="utf-8")
    if section is not None:
        start = text.find(section[0])
        end = text.find(section[1], start + 1) if start >= 0 else -1
        if start < 0:
            return None
        text = text[start:end] if end > start else text[start:]
        # Inside a section, take the gate from the fenced CCDL listing (the
        # model answer), not the inline backtick quote of the broken gate the
        # exercise asks the reader to fix.
        blocks = _CAS_BLOCK_RE.findall(text)
        if blocks:
            text = "\n".join(blocks)
    m = _GATE_RE.search(text)
    if not m:
        return None
    return {rail: tol for rail, tol in _WITHIN_RE.findall(m.group(1))}


def _ccdl_statement_keywords(path: Path) -> set[str]:
    """Leading statement keywords used inside the ```cas blocks of a chapter."""
    kws: set[str] = set()
    for block in _CAS_BLOCK_RE.findall(path.read_text(encoding="utf-8")):
        for raw in block.splitlines():
            line = raw.split("//")[0].strip()
            if not line or line in {"{", "}"} or line.startswith(("}", "{", "and ", "->")):
                continue
            tok = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\b", line)
            if tok:
                kws.add(tok.group(1))
    return kws


def _appendix_c_vocabulary() -> set[str]:
    """Every identifier-shaped token Appendix C declares as part of the language:
    the reserved-word fences, the component-type fences, and the quoted terminals
    of the EBNF. Deliberately over-inclusive — a keyword counted as documented
    here is one this run will NOT report as a finding."""
    text = APP_C.read_text(encoding="utf-8")
    vocab: set[str] = set()
    for block in re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.DOTALL):
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", block):
            vocab.add(tok)
    for tok in re.findall(r'"([A-Za-z_][A-Za-z0-9_:]*)"', text):
        vocab.add(tok.rstrip(":"))
    return vocab


def run_book_consistency(generated_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    # G1/G2 — regulator dropout rail vs its own target state, in both places.
    rows += _regulator_rail_consistency(CH22, "ch22", generated_at)
    rows += _regulator_rail_consistency(APP_D, "appd", generated_at)

    # G3 — Ch14 Bench Note unit conversion claim.
    ch14 = CH14.read_text(encoding="utf-8")
    ch22 = CH22.read_text(encoding="utf-8")
    trip_n = float(re.search(r"threshold\((0\.\d+)\)", ch14).group(1))
    rel_n = float(re.findall(r"threshold\((0\.\d+)\)", ch14)[1])
    trip_v = float(re.search(r"f3_level\s*<\s*([\d.]+)", ch22).group(1))
    rel_v = float(re.search(r"f3_level\s*>\s*([\d.]+)", ch22).group(1))
    rail_v = float(re.search(r"rail F3:\s*Vitality\s*\[v=([\d.]+)\]", ch22).group(1))
    rows.append(_record(
        "cpmb_book_ch14_bench_note_scale_claim", "book_consistency",
        (f"Ch14:130 claims Ch22's brownout volts are 'the same fraction on the "
         f"production supply' as Ch14's normalized {trip_n}/{rel_n}. On the "
         f"+{rail_v} V F3 rail that requires trip={trip_n * rail_v:g} V and "
         f"release={rel_n * rail_v:g} V."),
        f"trip={trip_n * rail_v:g}V release={rel_n * rail_v:g}V",
        f"trip={trip_v:g}V release={rel_v:g}V",
        _close(trip_n * rail_v, trip_v) and _close(rel_n * rail_v, rel_v),
        {"finding_at": _gate_line(CH14, "the same fraction on the production supply"),
         "bench_note_at": _gate_line(CH14, "the same fraction on the production supply"),
         "ch22_monitor_at": _gate_line(CH22, "monitor bo: f3_level < 2.5"),
         "normalized_trip": trip_n, "normalized_release": rel_n,
         "rail_volts": rail_v, "ch22_trip_v": trip_v, "ch22_release_v": rel_v,
         "ch22_trip_as_fraction": trip_v / rail_v,
         "ch22_release_as_fraction": rel_v / rail_v},
        generated_at, "book_consistency"))

    # G4 — Ch14's own datasheet band must contain Ch22's trip read as a fraction.
    band = re.search(r"Brownout trip \| F3 threshold \| ~([\d.]+) – ([\d.]+)", ch14)
    lo, hi = float(band.group(1)), float(band.group(2))
    frac = trip_v / rail_v
    rows.append(_record(
        "cpmb_book_ch22_trip_inside_ch14_band", "book_consistency",
        (f"Read the other way: Ch22's {trip_v:g} V trip on a +{rail_v:g} V rail is "
         f"a fraction of {frac:.4f}. Ch14:264's datasheet band for the brownout "
         f"trip is ~{lo}-{hi}."),
        f"fraction inside [{lo}, {hi}]", f"fraction = {frac:.4f}",
        lo <= frac <= hi,
        {"fraction": frac, "band_low": lo, "band_high": hi,
         "finding_at": _gate_line(CH14, "Brownout trip | F3 threshold")},
        generated_at, "book_consistency"))

    # G5 — hysteresis gap: Ch14:265 specifies release = trip + 0.10.
    gap_expected_v = 0.10 * rail_v
    gap_actual_v = rel_v - trip_v
    rows.append(_record(
        "cpmb_book_hysteresis_gap_consistency", "book_consistency",
        (f"Ch14:265 specifies brownout release = trip + 0.10 on the normalized "
         f"scale, i.e. {gap_expected_v:g} V on a +{rail_v:g} V rail."),
        f"gap = {gap_expected_v:g}V", f"gap = {gap_actual_v:g}V",
        _close(gap_expected_v, gap_actual_v),
        {"expected_gap_v": gap_expected_v, "observed_gap_v": gap_actual_v,
         "finding_at": _gate_line(CH14, "Brownout release | F3 threshold")},
        generated_at, "book_consistency"))

    # G6 — Appendix E's model answer vs Chapter 22's own gate.
    g22 = _o_enable_gate(CH22)
    ge = _o_enable_gate(APP_E, section=("## Chapter 22", "## Chapter 23"))
    rows.append(_record(
        "cpmb_book_appendix_e_gate_matches_ch22", "book_consistency",
        ("Appendix_E's Exercise 22.2 model answer must reproduce Chapter 22's "
         "own o_enable gate, whose tolerances match the per-domain regulator "
         "tolerances at Ch22:93-95."),
        f"tolerances {g22}", f"tolerances {ge}", g22 == ge,
        {"ch22_gate": g22, "appendix_e_gate": ge,
         "ch22_gate_at": _gate_line(CH22, "gate o_enable"),
         "appendix_e_gate_at": _gate_line(
             APP_E, "gate o_enable: o_rail requires (p_rail within 0.20)"),
         "finding_at": _gate_line(
             APP_E, "gate o_enable: o_rail requires (p_rail within 0.20)")},
        generated_at, "book_consistency"))

    # G7 — Chapter 14's published sequencer vs the invariant Ch22 names.
    g14 = _o_enable_gate(CH14)
    rows.append(_record(
        "cpmb_book_ch14_gate_gates_all_three_domains", "book_consistency",
        ("Ch22:195 states 'P alone is not enough to release O' and Appendix_E "
         "names the invariant as all of P, C and E. Chapter 14's published "
         "o_enable gate must therefore check all three rails."),
        "gates p_rail, c_rail, e_rail",
        f"gates {sorted(g14) if g14 else 'no gate found'}",
        bool(g14) and set(g14) == {"p_rail", "c_rail", "e_rail"},
        {"ch14_gate": g14, "ch22_gate": g22,
         "ch14_gate_at": _gate_line(CH14, "gate o_enable"),
         "ch22_gate_at": _gate_line(CH22, "gate o_enable"),
         "finding_at": _gate_line(CH14, "gate o_enable")},
        generated_at, "book_consistency"))

    # G8 — CCDL grammar coverage of the Chapter 22 listings.
    used = _ccdl_statement_keywords(CH22)
    vocab = _appendix_c_vocabulary()
    uncovered = sorted(k for k in used if k not in vocab)
    rows.append(_record(
        "cpmb_book_ccdl_statement_forms_documented", "book_consistency",
        ("Appendix_C:3 claims to be 'the complete language reference ... every "
         "lexical element, every statement form'. Every statement keyword used "
         "in Chapter 22's CCDL listings must appear in Appendix C's reserved-word "
         "list, component-type list, or EBNF."),
        "0 undocumented statement keywords",
        f"{len(uncovered)} undocumented: {', '.join(uncovered)}",
        not uncovered,
        {"used_keywords": sorted(used), "undocumented": uncovered,
         "finding_at": _gate_line(APP_C, "the complete language reference")},
        generated_at, "book_consistency"))

    # G9 — the executable CPMB in code vs the board published in Chapter 22.
    coded = [c.effect for c in build_cpmb().cjts]
    published = [n[2] for n in CPMB_PUBLISHED_NODES[1:4]]
    rows.append(_record(
        "cpmb_book_code_board_matches_published_board", "book_consistency",
        ("cas_forex.ccb_designs.build_cpmb() is the only executable CPMB in the "
         "repository. Its stage chain should be the board published at "
         "Ch22:179-182 if the code is to be cited as evidence for the chapter."),
        f"downstream stages {published}", f"downstream stages {coded[1:]}",
        coded[1:] == published,
        {"coded_chain": coded,
         "published_rails": [n[2] for n in CPMB_PUBLISHED_NODES[:4]],
         "finding_at": "cas-forex/cas_forex/ccb_designs.py build_cpmb()"},
        generated_at, "book_consistency"))

    return rows


# ===========================================================================
# Main run
# ===========================================================================
def run(generated_at: str) -> dict[str, Any]:
    behavioural: list[dict[str, Any]] = []
    structural: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    # --- A. yield engine, via cargo -------------------------------------
    all_yield_inputs = YIELD_CASES + YIELD_GAP_PROBES
    probe, probe_detail = run_rust_probe(all_yield_inputs)

    for case in YIELD_CASES:
        obs = probe.get(case["case_id"])
        if obs is None:
            behavioural.append(_record(
                case["case_id"], "yield_engine", case["description"],
                "engine record present", "engine produced no record", False,
                {"probe_detail": probe_detail}, generated_at))
            continue
        exp = case["expect"]
        checks: list[tuple[str, bool, str]] = []
        got_yt = _fnum(obs["theoretical_yield"])
        if "theoretical_yield" in exp:
            checks.append(("Y_T", _close(got_yt, float(exp["theoretical_yield"])),
                           f"{got_yt!r}"))
        if "limiting_reagent_kind" in exp:
            checks.append(("LR_kind",
                           obs["limiting_reagent"]["kind"] == exp["limiting_reagent_kind"],
                           obs["limiting_reagent"]["kind"]))
        if "limiting_reagent_entries" in exp:
            got_entries = [[n, _fnum(r)] for n, r in obs["limiting_reagent"]["entries"]]
            want = [[n, float(r)] for n, r in exp["limiting_reagent_entries"]]
            same = (len(got_entries) == len(want)
                    and all(g[0] == w[0] and _close(g[1], w[1])
                            for g, w in zip(got_entries, want)))
            checks.append(("LR_entries", same, str(got_entries)))
        if "excess_capacity" in exp:
            got_ec = {k: _fnum(v) for k, v in obs["excess_capacity"].items()}
            same = (set(got_ec) == set(exp["excess_capacity"])
                    and all(_close(got_ec[k], float(v))
                            for k, v in exp["excess_capacity"].items()))
            checks.append(("excess", same, str(got_ec)))
        if "efficiency" in exp:
            got_eff = _fnum(obs["efficiency"]) if obs["efficiency"] is not None else None
            want_eff = exp["efficiency"]
            if want_eff == "NaN":
                same = got_eff is not None and got_eff != got_eff
            else:
                same = got_eff is not None and _close(got_eff, float(want_eff))
            checks.append(("efficiency", same, repr(got_eff)))
        if "yield_strictly_below" in exp:
            checks.append((f"Y_T<{exp['yield_strictly_below']}",
                           got_yt < exp["yield_strictly_below"], f"{got_yt!r}"))
        if "yield_strictly_above" in exp:
            checks.append((f"Y_T>{exp['yield_strictly_above']}",
                           got_yt > exp["yield_strictly_above"], f"{got_yt!r}"))

        passed = all(ok for _, ok, _ in checks)
        behavioural.append(_record(
            case["case_id"],
            "yield_engine_published" if case["source"] == "book" else "yield_engine",
            case["description"],
            json.dumps(exp, sort_keys=True, default=str),
            "; ".join(f"{n}={v}" for n, _, v in checks),
            passed,
            {"engine_record": obs, "failed_checks": [n for n, ok, _ in checks if not ok],
             "expectation_source": case["source"], "probe_detail": probe_detail,
             "note": case.get("note", "")},
            generated_at))

    for probe_case in YIELD_GAP_PROBES:
        obs = probe.get(probe_case["case_id"], {})
        yt = _fnum(obs["theoretical_yield"]) if obs else float("nan")
        if probe_case["case_id"] == "cpmb_budget_duplicate_rail_prerequisite":
            observed = (f"accepted; prerequisite_count={obs.get('prerequisite_count')} "
                        f"vs excess_capacity_count={obs.get('excess_capacity_count')}")
        else:
            observed = f"accepted; Y_T={yt!r}"
        gaps.append(_gap(
            probe_case["case_id"], probe_case["description"], probe_case["hoped"],
            observed, probe_case["disposition"],
            {"engine_record": obs, "layer": "cas-engine scoring::yield_calc"},
            generated_at))

    # --- B. recipe notation through the real CAS compiler ----------------
    for case in RECIPE_STRING_CASES:
        valid, detail = _compile_cas(case["expression"])
        structural.append(_record(
            case["case_id"], case["category"], case["description"],
            "compiles valid=True" if case["expect_valid"] else "compiler rejects",
            "valid=True" if valid else "valid=False",
            valid == case["expect_valid"],
            {"expression": case["expression"], "layer": "api/notation/compiler.py",
             "detail": detail,
             "finding_at": (_gate_line(CH22, "F3|Vitality")
                            if case["category"] == "published_recipe" else "")},
            generated_at))

    for probe_case in RECIPE_STRING_GAPS:
        valid, detail = _compile_cas(probe_case["expression"])
        gaps.append(_gap(
            probe_case["case_id"], probe_case["description"], probe_case["hoped"],
            "accepted" if valid else "rejected", probe_case["disposition"],
            {"expression": probe_case["expression"],
             "layer": "api/notation/compiler.py", "detail": detail},
            generated_at))

    # --- C. published components through parser + compiler ---------------
    for ref, role, expression in CPMB_PUBLISHED_REGULATORS:
        accepted, detail = _compile_component(expression)
        structural.append(_record(
            f"cpmb_published_regulator_{ref}", "published_board", role,
            "accepted", "accepted" if accepted else "rejected", accepted,
            {"expression": expression, "detail": detail}, generated_at))

    for ref, role, literal in CPMB_PUBLISHED_NODES:
        valid, detail = _compile_cas(literal)
        structural.append(_record(
            f"cpmb_published_node_{ref}", "published_board",
            f"Chapter 22 node `{ref}`: {role}",
            "compiles valid=True", "valid=True" if valid else "valid=False",
            valid, {"expression": literal, "detail": detail}, generated_at))

    for case in COMPONENT_CASES:
        accepted, detail = _compile_component(case["expression"])
        structural.append(_record(
            case["case_id"], case["category"], case["description"],
            "accepted" if case["expect_accepted"] else "rejected",
            "accepted" if accepted else "rejected",
            accepted == case["expect_accepted"],
            {"expression": case["expression"], "detail": detail}, generated_at))

    for probe_case in COMPONENT_GAPS:
        accepted, detail = _compile_component(probe_case["expression"])
        gaps.append(_gap(
            probe_case["case_id"], probe_case["description"], probe_case["hoped"],
            "accepted" if accepted else "rejected", probe_case["disposition"],
            {"expression": probe_case["expression"],
             "layer": "cas_forex/pcba_syntax.py + pcba_compiler.py", "detail": detail},
            generated_at))

    # --- D. Dial current limiters ----------------------------------------
    for case in DIAL_CASES:
        accepted, detail = _dial_result(case["dials"])
        structural.append(_record(
            case["case_id"], case["category"], case["description"],
            "accepted" if case["expect_accepted"] else "rejected",
            "accepted" if accepted else "rejected",
            accepted == case["expect_accepted"],
            {"dials": case["dials"], "layer": "cas_engine.DialConfig", "detail": detail},
            generated_at))

    # --- E. CRC static design check --------------------------------------
    rep = run_crc_on_expressions(
        "cpmb_ch22_published_sequencer", CH22_SEQUENCER_CJTS, sequence=CH22_SEQUENCE)
    findings = rep.model_dump()["findings"]
    errors = [f for f in findings if _is_error(f)]
    structural.append(_record(
        "cpmb_crc_published_sequencer_clean", "crc_static",
        ("The Chapter 22 sequencer chain P->C->E->O, transcribed from Ch22:179-184 "
         "as CJTs, must pass the Cognitive Rule Check with no ERROR findings."),
        "0 ERROR findings", f"{len(errors)} ERROR, {len(findings)} total",
        not errors,
        {"findings": findings, "expressions": CH22_SEQUENCER_CJTS,
         "claim_note": rep.model_dump()["claim_note"]},
        generated_at))

    bad = run_crc_on_expressions(
        "cpmb_sequencer_skips_to_O",
        ["CJT< ^0^P_{F7}|T | ^5^P_{F7}|T => ^9^O_{F5}|E > [beta=1]"])
    bad_findings = bad.model_dump()["findings"]
    structural.append(_record(
        "cpmb_crc_negative_control_domain_skip", "crc_negative_control",
        ("NEGATIVE CONTROL for the case above. A sequencer that lets P drive O "
         "directly is the Domain-precedence violation Ch22:195 names. CRC must "
         "raise CRC-003."),
        "CRC-003 ERROR raised",
        ", ".join(f"{f['code']}/{f['severity']}" for f in bad_findings) or "no findings",
        any(f["code"] == "CRC-003" and _is_error(f) for f in bad_findings),
        {"findings": bad_findings}, generated_at))

    fuse_bad = run_crc_on_expressions(
        "cpmb_fuse_downstream", CH22_SEQUENCER_CJTS, sequence=CH22_SEQUENCE,
        fuses=[CrcFuse(name="overload_fuse", protects="C_rail", installed_at="O_rail")])
    fb = fuse_bad.model_dump()["findings"]
    structural.append(_record(
        "cpmb_crc_negative_control_fuse_downstream", "crc_negative_control",
        ("NEGATIVE CONTROL. A protective fuse installed downstream of the rail it "
         "protects cannot trip in time. CRC must raise CRC-008."),
        "CRC-008 ERROR raised",
        ", ".join(f"{f['code']}/{f['severity']}" for f in fb) or "no findings",
        any(f["code"] == "CRC-008" and _is_error(f) for f in fb),
        {"findings": fb}, generated_at))

    fuse_ok = run_crc_on_expressions(
        "cpmb_fuse_upstream", CH22_SEQUENCER_CJTS, sequence=CH22_SEQUENCE,
        fuses=[CrcFuse(name="overload_fuse", protects="O_rail", installed_at="C_rail")])
    fo = fuse_ok.model_dump()["findings"]
    structural.append(_record(
        "cpmb_crc_false_positive_fuse_upstream", "crc_negative_control",
        ("FALSE-POSITIVE CONTROL. The same fuse installed upstream of what it "
         "protects is correct placement and must produce no finding."),
        "no findings", f"{len(fo)} findings", not fo,
        {"findings": fo}, generated_at))

    coded = run_crc(build_cpmb()).model_dump()["findings"]
    structural.append(_record(
        "cpmb_crc_coded_board_clean", "crc_static",
        ("The executable CPMB in cas_forex.ccb_designs.build_cpmb() must also pass "
         "CRC clean. NOTE: this is a DIFFERENT board from the one published in "
         "Chapter 22 — see cpmb_book_code_board_matches_published_board."),
        "0 ERROR findings",
        f"{len([f for f in coded if _is_error(f)])} ERROR, {len(coded)} total",
        not [f for f in coded if _is_error(f)],
        {"findings": coded}, generated_at))

    # --- E2. beta parse bounds relevant to the derates the chapter claims -
    for cid, expr, expect_ok, desc in [
        ("cpmb_beta_published_unity", "CJT< ^0^P_{F7}|T | ^5^P_{F7}|T => ^1^C_{F2}|A > [beta=1.0]",
         True, "beta=1.0 on a sequencer stage must be accepted."),
        ("cpmb_beta_negative_rejected",
         "CJT< ^0^P_{F7}|T | ^5^P_{F7}|T => ^1^C_{F2}|A > [beta=-3.0]",
         False, "ADVERSARIAL. Negative gain inverts a stage; must be rejected."),
        ("cpmb_beta_non_finite_rejected",
         "CJT< ^0^P_{F7}|T | ^5^P_{F7}|T => ^1^C_{F2}|A > [beta=inf]",
         False, "ADVERSARIAL. Non-finite gain cannot be derated by a scale factor; "
                "must be rejected."),
        ("cpmb_beta_zero_allowed",
         "CJT< ^0^P_{F7}|T | ^5^P_{F7}|T => ^1^C_{F2}|A > [beta=0.0]",
         True, "FALSE-POSITIVE CONTROL. beta=0 is the thermal-Emergency cutoff "
               "condition Ch22:230 names; it must not be rejected."),
    ]:
        try:
            node = parse_cjt_expression(expr)
            ok, detail = True, f"beta={node.beta}"
        except Exception as exc:  # noqa: BLE001
            ok, detail = False, str(exc).splitlines()[0][:200]
        structural.append(_record(
            cid, "cjt_gain_bounds", desc,
            "accepted" if expect_ok else "rejected",
            "accepted" if ok else "rejected", ok == expect_ok,
            {"expression": expr, "layer": "cas_forex/cjt_syntax.py", "detail": detail},
            generated_at))

    gaps.append(_gap(
        "cpmb_beta_scale_derates_unenforced",
        ("Ch22:144 halves beta board-wide on brownout and Ch22:222 applies a 0.75 "
         "thermal derate. Probe whether any shipped layer applies or bounds those "
         "derates: parse a stage at beta=1e9, far above the CRC-007 hypersensitive "
         "threshold of 10."),
        "rejected or ERROR-flagged",
        (lambda: (lambda n, r: f"parsed beta={n.beta}; CRC severities="
                  f"{[f['code'] + '/' + str(f['severity']) for f in r]}")(
            parse_cjt_expression(
                "CJT< ^0^P_{F7}|T | ^5^P_{F7}|T => ^1^C_{F2}|A > [beta=1e9]"),
            run_crc_on_expressions(
                "beta_probe",
                ["CJT< ^0^P_{F7}|T | ^5^P_{F7}|T => ^1^C_{F2}|A > [beta=1e9]"]
            ).model_dump()["findings"]))(),
        ("RECORDED AS A LIMIT, AND THE HONEST ANSWER IS 'NOT IMPLEMENTED'. There is "
         "no beta_scale application anywhere in the repository — no brownout "
         "derate, no thermal derate, no board-wide gain modifier. crc_linter's "
         "CRC-007 raises only a WARN above beta=10 and never an ERROR. The "
         "protective responses at Ch22:144 and Ch22:222 are prose describing a "
         "design; nothing in this run tested them, and nothing in the repository "
         "could. Chapter 22 is explicit about this at Ch22:9 and Ch22:373."),
        {"layer": "cas_forex/cjt_syntax.py + crc_linter.py"}, generated_at))

    # --- F. board-level authority ----------------------------------------
    lic = build_pcba_licensing_report().model_dump()
    power = next(
        c for c in lic["checks"]
        if str(getattr(c["feature"], "value", c["feature"]))
        == "power_board_burnout_prevention_claim")
    for cid, desc, flag in [
        ("cpmb_authority_not_ready",
         "The CPMB power-board claim must not read ready off this evidence.",
         bool(power["ready"])),
        ("cpmb_authority_cannot_affect_live_trading",
         "This eval must not make the CPMB able to affect live trading.",
         bool(power["can_affect_live_trading"])),
        ("cpmb_authority_cannot_create_broker_accept",
         "This eval must not make the CPMB a broker ACCEPT path.",
         bool(power["can_create_broker_accept"])),
    ]:
        structural.append(_record(
            cid, "authority", desc, "flag=false", f"flag={flag}", flag is False,
            {"feature": str(power["feature"]), "status": power["status"],
             "claim_ceiling": power["claim_ceiling"],
             "required_evidence": power["required_evidence"],
             "present_evidence": power["present_evidence"],
             "missing_evidence": power["missing_evidence"]},
            generated_at))

    structural.append(_record(
        "cpmb_authority_receipt_still_unsigned", "authority",
        ("This run must not close the receipt by itself. The evidence key "
         "`cpmb_load_budget_eval_pass` must still read as missing until a human "
         "signs the receipt against these artifacts."),
        "cpmb_load_budget_eval_pass in missing_evidence",
        ("present" if "cpmb_load_budget_eval_pass" in power["present_evidence"]
         else "missing"),
        "cpmb_load_budget_eval_pass" in power["missing_evidence"],
        {"missing_evidence": power["missing_evidence"]}, generated_at))

    # Precedent hazard: a sibling key satisfied by an unrelated suite.
    readiness_src = (CAS_FOREX_ROOT / "cas_forex" / "pcba_readiness.py").read_text(
        encoding="utf-8")
    sibling_wiring = re.search(
        r'"cpmb_brownout_lock_tests_pass":\s*([^,\n]+)', readiness_src)
    models_src = (CAS_FOREX_ROOT / "tests" / "test_pcba_models.py").read_text(
        encoding="utf-8")
    behaviour_hits = re.findall(
        r"(?i)brownout|thermal|dropout|budget|\brail\b|sequenc", models_src)
    gaps.append(_gap(
        "cpmb_precedent_sibling_key_satisfied_by_unrelated_suite",
        ("PRECEDENT HAZARD. The sibling evidence key `cpmb_brownout_lock_tests_pass` "
         "is already marked present in docs/working/pcba_authority_report_20260617.json. "
         "Check what actually satisfies it."),
        "a brownout-specific test suite",
        (f"pcba_readiness.py maps it to {sibling_wiring.group(1).strip() if sibling_wiring else '?'}"
         f", i.e. the pass status of tests/test_pcba_models.py, which contains "
         f"{len(behaviour_hits)} brownout/thermal/dropout/budget/rail/sequencing references"),
        ("RECORDED AS A HAZARD THIS RUN MUST NOT REPEAT. An evidence key named for "
         "a specific behaviour is satisfied there by a generic model-parse suite. "
         "`cpmb_load_budget_eval_pass` must NOT be closed the same way. This "
         "artifact deliberately does not set the key, does not claim the brownout "
         "detector was tested, and states in its Scope that the additive energy "
         "budget and every protective subsystem were not exercised at all. The "
         "same wiring exists for `csb_shadow_mode_tests_pass` and is out of scope "
         "here."),
        {"readiness_wiring": sibling_wiring.group(0) if sibling_wiring else None,
         "test_module": "cas-forex/tests/test_pcba_models.py",
         "behavioural_reference_count": len(behaviour_hits)},
        generated_at))

    # --- G2. harness falsifiability self-check ----------------------------
    # An eval whose cases cannot fail is worthless. These are deliberately
    # WRONG expectations pushed through the same comparison helpers the real
    # cases use; each must be DETECTED as wrong. Checked in-band on every run
    # so the property cannot rot.
    yt_book = _fnum(probe["cpmb_budget_book_published_case"]["theoretical_yield"])
    mutants = [
        ("yield expectation corrupted to 1.6 for the book's published case",
         not _close(yt_book, 1.6)),
        ("involution-pair divergence of 6 claimed acceptable",
         _dial_result(_dials(CO_2=9, CO_3=3))[0] is False),
        ("malformed recipe string claimed compilable",
         _compile_cas("Theta(Omega) = ???")[0] is False),
        ("negative regulator tolerance claimed acceptable",
         _compile_component(
             "Regulator< target_state=^0^P_{F7}|T, tolerance=-0.1 >")[0] is False),
    ]
    detected = sum(1 for _, ok in mutants if ok)
    structural.append(_record(
        "cpmb_harness_detects_injected_errors", "falsifiability",
        ("FALSIFIABILITY CONTROL. Four deliberately wrong expectations are pushed "
         "through the same comparison helpers the real cases use. Every one must "
         "be detected as wrong, otherwise the surrounding cases are decorative."),
        "4/4 injected errors detected", f"{detected}/4 detected",
        detected == len(mutants),
        {"mutants": [{"mutant": n, "detected": ok} for n, ok in mutants]},
        generated_at))

    # --- G. book internal consistency -------------------------------------
    book = run_book_consistency(generated_at)

    # --- H. Fisher-Rao piece of E = beta * d_FR ---------------------------
    # The ONLY part of the additive energy budget with shipped machinery.
    uniform = [1.0 / 40.0] * 40
    perturbed = list(uniform)
    perturbed[2] += 0.10
    total = sum(perturbed)
    perturbed = [x / total for x in perturbed]
    d_fr = cas_engine.geodesic_distance(
        cas_engine.CognitiveStateVector(uniform),
        cas_engine.CognitiveStateVector(perturbed))
    beta = parse_cjt_expression(
        "CJT< ^0^P_{F7}|T | ^5^P_{F7}|T => ^1^C_{F2}|A > [beta=2.0]").beta
    structural.append(_record(
        "cpmb_per_transition_energy_components_exist", "energy_model",
        ("Ch22:247 models per-transition energy as E = beta * d_FR. Both factors "
         "have shipped implementations: d_FR from cas_engine.geodesic_distance on "
         "the open 40-simplex, beta from the CJT parser. This case checks only "
         "that both factors are computable and that d_FR is a positive real for a "
         "non-identical pair. It does NOT test the additive budget."),
        "d_FR > 0 and beta parsed",
        f"d_FR={d_fr!r} beta={beta!r} E={beta * d_fr!r}",
        d_fr > 0 and beta == 2.0,
        {"d_FR": repr(d_fr), "beta": beta, "E": repr(beta * d_fr),
         "limit": ("No rail-capacity object, reservoir, amp-hour quantity or "
                   "additive-draw accumulator exists in cas-forex, cas-engine or "
                   "the noetic-compass api. Summing stage draws against a supply "
                   "would be arithmetic written inside this script and would test "
                   "this script, not the framework. It was not done.")},
        generated_at))

    gaps.append(_gap(
        "cpmb_additive_energy_budget_unimplemented",
        ("The additive form of the load budget — rail capacity in amp-hours "
         "(Ch22:245), summed per-stage draw (Ch22:247), time-to-brownout = "
         "capacity/draw (Exercise 22.4, Ch22:407-413) — has no implementation "
         "anywhere in the repository."),
        "a rail-capacity / additive-draw implementation to run against",
        "no such object exists; NOT RUN",
        ("RECORDED AS THE CENTRAL LIMIT OF THIS RUN, NOT WAIVED AND NOT FAKED. "
         "Grep across cas-forex, cas-engine and the noetic-compass api for "
         "reservoir / amp_hour / drive_budget / energy_budget / per_transition "
         "returns no capacity object. The receipt's phrase 'load budget' has two "
         "readings in Chapter 22; only the recipe/limiting-reagent reading "
         "(Ch22:302-318) is backed by runnable machinery and only that reading "
         "was executed. Recomputing 10 A.h / 2.5 A = 4 h inside this script would "
         "have tested this script's own arithmetic and is exactly the fake pass "
         "this eval exists to avoid. Chapter 22 is honest about the status of "
         "these figures at Ch22:9 and Ch22:373; the gap is in the tooling, not in "
         "the book's claim."),
        {"searched_for": ["reservoir", "amp_hour", "drive_budget", "energy_budget",
                          "per_transition", "rail_capacity"],
         "searched_in": ["cas-forex/", "cas-engine/", "noetic-compass/api/"]},
        generated_at))

    gaps.append(_gap(
        "cpmb_overcommit_predicate_supplied_by_this_eval",
        ("Section A treats Y_T < 1.0 as 'the load budget is overcommitted'. Check "
         "whether that threshold exists in the framework."),
        "a shipped overcommit threshold or flag",
        "no threshold, flag or predicate exists; yield_calc returns a number only",
        ("RECORDED SO THE READING IS NOT MISATTRIBUTED. cas-engine's yield_calc "
         "computes Y_T and never raises, flags or compares against 1.0. The "
         "'overcommitted' interpretation is supplied by this eval, not by the "
         "framework. What the engine genuinely establishes is the arithmetic and "
         "the limiting reagent; the go/no-go reading on top of it is this "
         "artifact's own convention and must be cited as such."),
        {"layer": "cas-engine scoring::yield_calc"}, generated_at))

    return {"behavioural": behavioural, "structural": structural,
            "book": book, "gaps": gaps, "probe_detail": probe_detail}


def _headline(failing: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> str:
    """A one-screen summary so a reviewer does not have to scroll to the
    failures. Generated, not written by hand."""
    lines: list[str] = []
    if not failing and not gaps:
        return "None. Every case passed and no unenforced property was found."
    if failing:
        lines.append(f"**{len(failing)} case(s) failed.** Every one is a defect in "
                     f"the published text, not in a gate:" + "\n")
        for r in failing:
            src = r["evidence"].get("finding_at", "")
            where = f" ({src})" if src else ""
            lines.append(f"- `{r['case_id']}`{where} — expected "
                         f"{str(r['expected'])[:120]}; observed "
                         f"{str(r['observed'])[:160]}")
        lines.append("")
    if gaps:
        lines.append(f"**{len(gaps)} unenforced propert(y/ies) or limit(s).** Each "
                     f"carries a disposition below; none was waived:" + "\n")
        for g in gaps:
            lines.append(f"- `{g['case_id']}` — hoped {g['hoped']}; observed "
                         f"{str(g['observed'])[:150]}")
    return "\n".join(lines)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    text = "".join(json.dumps(r, sort_keys=True, default=str) + "\n" for r in rows)
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _table(rows: list[dict[str, Any]]) -> str:
    out = ["| Case | Category | Expected | Observed | Passed |", "|---|---|---|---|---:|"]
    for r in rows:
        exp = str(r["expected"]).replace("|", "\\|")[:110]
        obs = str(r["observed"]).replace("|", "\\|")[:110]
        out.append(f"| `{r['case_id']}` | `{r['category']}` | {exp} | {obs} | "
                   f"`{str(r['passed']).lower()}` |")
    return "\n".join(out)


def main() -> int:
    if shutil.which("cargo") is None:
        print("COULD_NOT_RUN: cargo is not on PATH; the yield engine is only "
              "reachable through cargo (the installed cas_engine wheel predates "
              "CAS v7.6 and exports no Recipe/StateVector/Yield).")
        return 2

    generated_at = utc_now().isoformat()
    res = run(generated_at)
    behavioural, structural, book, gaps = (
        res["behavioural"], res["structural"], res["book"], res["gaps"])

    # Repeatability: re-run the yield probe and require byte-identical numbers.
    probe2, _ = run_rust_probe(YIELD_CASES + YIELD_GAP_PROBES)
    first = {r["case_id"]: r["evidence"]["engine_record"] for r in behavioural
             if "engine_record" in r["evidence"]}
    repeatable = all(probe2.get(k) == v for k, v in first.items())
    structural.append(_record(
        "cpmb_yield_engine_repeatability", "repeatability",
        ("The yield engine is exact-f64 arithmetic and must return byte-identical "
         "records on a second independent cargo run."),
        "identical records", "identical" if repeatable else "DIVERGED", repeatable,
        {"cases_compared": len(first)}, generated_at))

    machine = behavioural + structural
    m_pass = sum(1 for r in machine if r["passed"])
    b_pass = sum(1 for r in book if r["passed"])
    real_gaps = [g for g in gaps if g["is_gap"]]

    every = machine + book
    gate_cases = [r for r in every if r["failure_means"] == "gate_defect"]
    book_cases = [r for r in every if r["failure_means"] == "book_defect"]
    gate_pass = sum(1 for r in gate_cases if r["passed"])
    book_pass = sum(1 for r in book_cases if r["passed"])

    if gate_pass == len(gate_cases) and book_pass == len(book_cases) and not real_gaps:
        result = "PASS"
    elif gate_pass == len(gate_cases):
        # Every gate the repository implements behaved correctly; the failures
        # are all in the published text.
        result = "MIXED"
    else:
        result = "FAIL"

    raw = WORKING_DIR / f"cpmb_load_budget_eval_raw_{DATE_TAG}.jsonl"
    raw_hash = _write_jsonl(raw, behavioural + structural + book + gaps)

    failing = [r for r in machine + book if not r["passed"]]

    report = WORKING_DIR / f"cpmb_load_budget_eval_report_{DATE_TAG}.md"
    body = f"""# CPMB Load Budget — Eval Report

Generated: `{generated_at}`
Reviewer identity: `{REVIEWER_ID}`
Reviewer type: AI/local code reviewer attestation, not a human signature.
Receipt targeted: `power_board_burnout_prevention_claim__cpmb_load_budget_eval_pass`
Result: `{result}`
Gate-behaviour cases passed: `{gate_pass}/{len(gate_cases)}` (a failure here would mean a gate is wrong)
Book-defect cases passed: `{book_pass}/{len(book_cases)}` (a failure here means the published text is wrong)
Machinery cases passed: `{m_pass}/{len(machine)}`
Book-consistency cases passed: `{b_pass}/{len(book)}`
Unenforced properties / limits found: `{len(real_gaps)}`

Every case is classified by what its failure would mean. A **gate-defect** case
tests whether a gate the repository implements behaves correctly — adversarial
weakenings, in-range boundaries, false-positive controls, authority flags,
repeatability. A **book-defect** case tests whether the published text is
correct — the published listings, the published yield table, and the
cross-reference consistency assertions. `MIXED` is reported when every
gate-behaviour case passes and the only failures are in the published text.

## Headline Findings

{_headline(failing, real_gaps)}

## What "load budget" means here

Chapter 22 uses the phrase in two non-equivalent senses, and the distinction
governs this whole report.

**Form (a) — the recipe budget** (Ch22:302-318). `Θ(Ω_session) = 2.0·F3 +
1.0·F6 + 1.0·F7`, with `Y_T = min(xᵢ/aᵢ)` and a limiting reagent. This form is
backed by real, runnable machinery: `cas-engine/src/scoring/yield_calc.rs`. It
was executed against that engine and its published numbers reproduce exactly.

**Form (b) — the additive energy budget** (Ch22:243-249 and Exercise 22.4 at
Ch22:407-413). Rail capacity in amp-hours, per-transition draw `E = β·d_FR`
summed across firing stages, `time = capacity / draw`. **This form has no
implementation anywhere in the repository and was not run.** Recomputing
`10 A·h / 2.5 A = 4 h` inside the eval script would have tested the script's own
arithmetic, not the framework. That is the fake pass this eval exists to avoid.

## Scope

1. **Behavioural, in the narrow honest sense.** The recipe load budget is
   executed against the shipped Rust yield calculator — `theoretical_yield`,
   `limiting_reagent`, `excess_capacity`, `efficiency`. These are runtime
   executions of the framework's own arithmetic engine producing numbers that
   could contradict the book. Cases cover the book's own published table, a
   budget balanced at exactly 100 percent, an overcommitted budget, an
   epsilon-below-balance boundary, an epsilon-above and a generously-supplied
   false-positive control, a missing rail, and efficiency including the
   zero-yield NaN convention.
2. **Structural.** Every machine-checkable line of the published board is run
   through the real PCBA parser, the real CAS compiler, the real `DialConfig`
   schema, the real CJT parser and the real CRC linter, with adversarial
   weakenings and in-range false-positive controls on each.
3. **Book internal consistency.** Assertions computed by reading the book files
   themselves — not hardcoded — across Chapter 22, Chapter 14, Appendix C,
   Appendix D and Appendix E. Every failure is recorded as a book finding.

The yield engine is not reachable from Python: the installed `cas_engine` wheel
predates CAS v7.6 and exports no `Recipe`, `StateVector`, `Yield` or
`LimitingReagent`. This script therefore generates a throwaway cargo integration
test inside the `cas-engine` package, runs it, parses its stdout and deletes it.
The functions exercised are the shipped ones; nothing is reimplemented.

## Out of scope, deliberately

**There is no model in the loop.** Nothing here measures a deployed cognitive
system, and nothing here licenses a claim about deployed behaviour. Chapter 22
says the same at Ch22:9 and Ch22:373: every voltage, amp, amp-hour, temperature
and timing in that chapter is a design model, not telemetry.

Specifically **not** established by this run:

- **The additive energy budget was not run.** No rail-capacity object, no
  amp-hour quantity, no reservoir, no additive-draw accumulator exists in
  `cas-forex`, `cas-engine` or the `noetic-compass` api. The reading of "load
  budget" that means "sum the allocated loads against available supply" cannot
  be tested against shipped machinery at all.
- **Brownout detection was not tested.** There is no F3 rail level, no 2.5/3.5
  trip-release pair, no hysteresis state machine and no rest-state routing
  anywhere in the repository.
- **Thermal management was not tested.** There is no temperature model, no
  three-tier escalation, no 300-second timer, no cutoff action and no safe
  state.
- **Startup sequencing was not tested as behaviour.** The CRC check in this run
  is a static structural check over a transcribed chain. Nothing holds a rail
  low, nothing reports power-good, and no gate is evaluated at runtime.
- **The β derates were not tested.** The 0.5 brownout derate (Ch22:144) and the
  0.75 thermal derate (Ch22:222) have no implementation; nothing applies or
  bounds them.
- **The CPMB board as published cannot be compiled as a whole.** No CCDL parser
  exists in the repository. `pcba_syntax` parses `Component< … >` expressions
  only; `cjt_syntax` parses `CJT< … >` only; the CAS compiler parses CAS
  expressions and v7.6 recipes. Nothing parses `circuit {{ … }}`, `rail`, `dial`,
  `spec`, `monitor`, `on {{ }}`, `sequence`, `gate`, `constraint`, `use` or
  `probe`. Roughly a dozen lines of the published board are machine-checkable.
  Appendix_C:7 is candid about this — the compiler is a design, not a shipped
  runnable pass.
- **The "overcommitted" reading is this eval's own.** `yield_calc` returns a
  number; it never flags, raises or compares against 1.0. See the gap of that
  name below.
- **This run does not upgrade the CPMB claim.** The owner review at
  `docs/working/pcba_owner_claim_review_20260725.md:40-46` approved the CPMB as
  an architectural description and analogy only, and this artifact does not
  change that. It also does not sign the receipt.

## Pass/Fail Thresholds

- Gate-behaviour case pass rate must be `1.0` — every gate the repository
  implements must behave as the case specifies, in **both** directions: the
  adversarial weakening rejected, and the in-range or published value accepted.
- Book-defect case pass rate must be `1.0` for a headline of `PASS`.
- Board authority flags must all read false, and
  `cpmb_load_budget_eval_pass` must remain in `missing_evidence`.
- Float comparisons are exact-first with a `1e-12` relative fallback, so no case
  can be passed by a generous epsilon at the 100-percent boundary. The
  epsilon-below-balance case additionally asserts `Y_T < 1.0` strictly and the
  epsilon-above case asserts `Y_T > 1.0` strictly.
- The run carries an in-band falsifiability control
  (`cpmb_harness_detects_injected_errors`): four deliberately wrong
  expectations are pushed through the same comparison helpers the real cases
  use, and all four must be detected. A suite whose cases cannot fail proves
  nothing.

## Behavioural Cases — the recipe load budget against the real yield engine

{_table(behavioural)}

## Structural Cases

{_table(structural)}

## Book Internal-Consistency Cases

These are computed by reading the book files, so they will flip to `true` if the
text is corrected.

{_table(book)}

## Unenforced Properties And Limits

Recorded as findings, never as passes. Each carries its disposition — what was
done about it. No finding here was closed by weakening the case.

"""
    for g in real_gaps:
        body += (f"### `{g['case_id']}`\n\n"
                 f"{g['description']}\n\n"
                 f"- Hoped `{g['hoped']}`.\n"
                 f"- Observed: {g['observed']}\n"
                 f"- **Disposition:** {g['disposition']}\n\n")
    if not real_gaps:
        body += "None.\n\n"

    body += "## Failures Observed\n\n"
    if failing:
        for r in failing:
            body += (f"### `{r['case_id']}` (`{r['category']}`; failure means "
                     f"**{r['failure_means'].replace('_', ' ')}**)\n\n"
                     f"{r['description']}\n\n"
                     f"- Expected: {r['expected']}\n"
                     f"- Observed: {r['observed']}\n"
                     f"- Evidence: `{json.dumps(r['evidence'], sort_keys=True, default=str)[:600]}`\n\n")
    else:
        body += "None.\n\n"

    body += f"""## Mitigations And Limits

- The allowed claim is exactly what this artifact observed: the recipe form of
  the CPMB load budget reproduces the book's published numbers against the
  shipped yield engine; the Dial constraints are fully and correctly enforced by
  real code; the published regulator components and CAS state literals compile
  clean; and the adversarial weakenings of those gates are rejected.
- This evidence does not unlock live trading, does not make the CPMB a broker
  `ACCEPT` path, and does not support behavioural, legal, governance, privacy or
  human-factors claims about the board.
- This artifact does not sign
  `power_board_burnout_prevention_claim__cpmb_load_budget_eval_pass`. Signing is
  a human act against these hashes.
- Note the precedent hazard recorded above: the sibling key
  `cpmb_brownout_lock_tests_pass` is already marked present in
  `pcba_authority_report_20260617.json` and is satisfied by an unrelated generic
  model-parse suite. This receipt must not be closed the same way.

## Raw Evidence

- Path: `docs\\working\\{raw.name}`
- SHA-256: `{raw_hash}`
- JSONL records: `{len(behavioural) + len(structural) + len(book) + len(gaps)}`
- Yield-engine probe: `{res['probe_detail']}`
"""
    report.write_text(body, encoding="utf-8", newline="\n")

    print(f"result                 : {result}")
    print(f"gate-behaviour cases   : {gate_pass}/{len(gate_cases)}")
    print(f"book-defect cases      : {book_pass}/{len(book_cases)}")
    print(f"machinery cases        : {m_pass}/{len(machine)}")
    print(f"book-consistency cases : {b_pass}/{len(book)}")
    print(f"unenforced/limits      : {len(real_gaps)}")
    for g in real_gaps:
        print(f"   GAP  {g['case_id']}: hoped {g['hoped']}; observed {g['observed'][:120]}")
    for r in failing:
        print(f"   FAIL [{r['failure_means']}] {r['case_id']}: "
              f"expected {str(r['expected'])[:80]} | observed {str(r['observed'])[:110]}")
    print(f"\nreport : {report}")
    print(f"raw    : {raw}")
    print(f"sha256 : {raw_hash}")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
