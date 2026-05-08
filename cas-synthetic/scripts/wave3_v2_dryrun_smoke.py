"""Wave 3 v2 dry-run smoke (no API spend).

Constructs 50 hand-built example outputs covering each failure mode the
audit caught, runs them through the v2 validators, and writes a markdown
report to ``docs/working/wave3_dry_run_smoke_2026_05_08.md``.

The point: prove the v2 validators reject the failure modes the audit
caught (recipe coefficient drops, fractal k-misread, english_to_cas
verbatim copy, invalid_to_corrected unrelated correction) on hand-built
examples. This is NOT evidence that the new prompts produce faithful
output — only that the validators correctly classify accept/reject.

Usage:
  python cas-synthetic/scripts/wave3_v2_dryrun_smoke.py
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_v2():
    name = "cas_synthetic_path_d_wave3_v2_smoke_loader"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, _REPO_ROOT / "cas-synthetic" / "scripts" / "generate_path_d_wave3_v2.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@dataclass
class SmokeCase:
    """A single hand-built case that exercises one validator."""

    case_id: int
    failure_mode: str  # "recipe_coeff_drop" / "fractal_count_misread" / etc.
    expected_pass: bool
    description: str
    inputs: dict
    validator: str  # which validator name to invoke


def build_cases() -> list[SmokeCase]:
    """50 hand-built cases across all four failure modes plus controls."""
    cases: list[SmokeCase] = []
    case_id = 0

    # --- recipe coefficient + Ω preservation (failure mode 1) -------------
    # 12 cases: 6 pass, 6 fail (drop coefficient or drop Ω or drop both).
    # 2026-05-08: rewritten for stem-only Ω rule. Echoing the Ω_ prefix in
    # English is now CAS notation leakage (rejected); only the stem
    # (e.g. ``decision_47``) appears.
    recipe_pass = [
        ("recipe single coeff + Ω stem present",
         "Θ(Ω_decision_47) = 0.7*^9^C|A → Ω_decision_47",
         "When 0.7 of an analytical thought-emergence combines, the production yields the outcome called decision_47."),
        ("recipe two coeffs + Ω stem",
         "Θ(Ω_reasoning_02) = 1.5*^6^E + 1.5*^6^P|T → Ω_reasoning_02",
         "1.5 of unpacking in evaluative judgment mixed with 1.5 of unpacking principled foundations produces the outcome called reasoning_02."),
        ("recipe with 0.15 leakage coeff (stems only)",
         "Θ(Ω_target_01) = 1*^5^P → Ω_target_01 + 0.15*Λ·Ω_side",
         "1 of shaped principled experience produces the outcome target_01 with a 0.15 leakage to outcome side."),
        ("recipe with named omega only (stem)",
         "Θ(Ω_focus_03) = 1*^1^P → Ω_focus_03",
         "1 of paying attention to a foundational principle produces the outcome called focus_03."),
        ("recipe with three coefficients + stem",
         "Θ(Ω_pipeline_88) = 0.5*^2^C + 0.3*^3^E + 0.2*^7^O → Ω_pipeline_88",
         "0.5 of cognitive attraction, 0.3 of evaluative aversion, and 0.2 of operational rhythm produce the outcome called pipeline_88."),
        ("recipe with decimal-style stem name",
         "Θ(Ω_v3_step_12) = 1.0*^4^P|A → Ω_v3_step_12",
         "1.0 of analytical resonance with a foundational principle produces the outcome called v3_step_12."),
    ]
    for label, src, eng in recipe_pass:
        case_id += 1
        cases.append(SmokeCase(
            case_id=case_id,
            failure_mode="recipe_coeff_drop",
            expected_pass=True,
            description=label,
            inputs={"source_cas": src, "english_output": eng},
            validator="recipe_preservation",
        ))
    recipe_fail = [
        ("recipe coeff dropped",
         "Θ(Ω_decision_47) = 0.7*^9^C|A → Ω_decision_47",
         "An analytical thought-emergence produces the named target Ω_decision_47."),
        ("recipe Ω paraphrased away",
         "Θ(Ω_reasoning_02) = 1.5*^6^E → Ω_reasoning_02",
         "1.5 of unpacking in evaluative judgment yields a reasoning outcome."),
        ("recipe both coefficients dropped",
         "Θ(Ω_X) = 1.5*^6^E + 1.5*^6^P → Ω_X",
         "Unpacking in evaluative judgment mixes with unpacking in principled foundations to produce Ω_X."),
        ("recipe with 'partial' replacing 0.5",
         "Θ(Ω_focus_03) = 0.5*^1^P → Ω_focus_03",
         "Partial paying attention to a foundational principle produces Ω_focus_03."),
        ("recipe with 'mostly' replacing 0.7",
         "Θ(Ω_decision_47) = 0.7*^9^C|A → Ω_decision_47",
         "Mostly an analytical thought-emergence produces Ω_decision_47."),
        ("recipe Ω truncated",
         "Θ(Ω_pipeline_88) = 1*^7^O → Ω_pipeline_88",
         "1 of operational rhythm produces a pipeline outcome."),
    ]
    for label, src, eng in recipe_fail:
        case_id += 1
        cases.append(SmokeCase(
            case_id=case_id,
            failure_mode="recipe_coeff_drop",
            expected_pass=False,
            description=label,
            inputs={"source_cas": src, "english_output": eng},
            validator="recipe_preservation",
        ))

    # --- fractal k-indices (failure mode 2) -------------------------------
    # 12 cases: 6 pass, 6 fail.
    fractal_pass = [
        ("fractal Φ⟨9:4:7⟩ rendered as operators",
         "Φ⟨9:4:7⟩",
         "An idea popped into mind, then struck a chord, then turned into muscle memory."),
        ("fractal Φ⟨0:1⟩ rendered as Idea→Mind",
         "Φ⟨0:1⟩",
         "A thought first sits all in your head, then you start paying attention to it."),
        ("fractal Φ⟨3:5⟩ rendered with operator names",
         "Φ⟨3:5⟩",
         "Aversion (^3 Negative) gives way to the sum of one's experiences (^5 Female)."),
        ("fractal Φ⟨2:6⟩ with colloquialisms",
         "Φ⟨2:6⟩",
         "Drawn to an idea, then unpacking it to see what's underneath."),
        ("fractal Φ⟨8:9⟩ trigger and effect",
         "Φ⟨8:9⟩",
         "That reminds me of something, and the thought just popped into mind."),
        ("ASCII fractal Phi<7:4>",
         "Phi<7:4>",
         "Practice makes perfect, and over time the activity hits hard like a chord struck."),
    ]
    for label, src, eng in fractal_pass:
        case_id += 1
        cases.append(SmokeCase(
            case_id=case_id,
            failure_mode="fractal_count_misread",
            expected_pass=True,
            description=label,
            inputs={"source_cas": src, "english_output": eng},
            validator="fractal_k_indices",
        ))
    fractal_fail = [
        ("fractal misread as count of stages",
         "Φ⟨2:9:6:7:8:9:2:5⟩",
         "A sequence of 8 stages moving through operations 2, 9, 6, 7, 8, 9, 2, 5."),
        ("fractal misread as 9 domains",
         "Φ⟨9:9⟩",
         "The expression covers 9 domains of structured thought."),
        ("fractal Φ⟨3:5⟩ rendered as bare numbers",
         "Φ⟨3:5⟩",
         "The path moves from 3 to 5 across abstract levels."),
        ("fractal Φ⟨0:0:0⟩ count-only",
         "Φ⟨0:0:0⟩",
         "A sequence of 3 zero-valued operations."),
        ("ASCII fractal misread as operations count",
         "Phi<6:2:8>",
         "There are 6 operations, then 2 operations, then 8 operations."),
        ("fractal sequence reduced to abstract count",
         "Φ⟨1:2:3⟩",
         "The expression encodes 3 steps of cognitive activity."),
    ]
    for label, src, eng in fractal_fail:
        case_id += 1
        cases.append(SmokeCase(
            case_id=case_id,
            failure_mode="fractal_count_misread",
            expected_pass=False,
            description=label,
            inputs={"source_cas": src, "english_output": eng},
            validator="fractal_k_indices",
        ))

    # --- english_to_cas verbatim-copy (failure mode 3) -------------------
    # 13 cases: 7 pass (independent generation), 6 fail (verbatim copy).
    e2c_pass = [
        ("independent generation, simple",
         "Translate to CAS: a thought drawn toward foundations.",
         "^0 ∘ ^2^P"),
        ("independent generation, recipe",
         "Translate to CAS: 0.7 of cognitive emergence and 1.5 of principled attention produce the named target Ω_reasoning_02.",
         "Θ(Ω_reasoning_02) = 0.7*^9^C|A + 1.5*^1^P|A → Ω_reasoning_02"),
        ("independent generation, fractal",
         "Translate to CAS: a thought popped into mind, struck a chord, then became muscle memory.",
         "Φ⟨9:4:7⟩"),
        ("independent generation, binary composition",
         "Translate to CAS: principled aversion combines with evaluative resonance.",
         "^3^P|A + ^4^E|f"),
        ("independent generation, meta-logic",
         "Translate to CAS: a Noetic cluster covering all 10 operators.",
         "NoeticCluster{^0..^9}"),
        ("independent generation, let-binding",
         "Translate to CAS: bind a source to ^5^P, a target to ^8^C, then connect them.",
         "let s = ^5^P; let t = ^8^C; s → t"),
        ("independent generation, cross-register Ω",
         "Translate to CAS: principled aversion across analytical, affective, and transcendent registers.",
         "(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω"),
    ]
    for label, prompt, gen in e2c_pass:
        case_id += 1
        cases.append(SmokeCase(
            case_id=case_id,
            failure_mode="english_to_cas_verbatim",
            expected_pass=True,
            description=label,
            inputs={"prompt_text": prompt, "generated_cas": gen},
            validator="anti_copy",
        ))
    e2c_fail = [
        ("verbatim copy of phase-1 reference target pattern",
         "reference target (for guidance only — do not paste verbatim, render afresh): ^0^P|A + ^0^P|T",
         "^0^P|A + ^0^P|T"),
        ("verbatim copy of recipe in prompt",
         "Express as CAS: Θ(Ω_x) = 1*^5^P → Ω_x",
         "Θ(Ω_x) = 1*^5^P → Ω_x"),
        ("verbatim copy of fractal in prompt",
         "Express as CAS: Φ⟨9:4:7⟩",
         "Φ⟨9:4:7⟩"),
        ("verbatim copy of meta-logic constructor",
         "The expression NoeticCluster{^0..^9} covers all operators.",
         "NoeticCluster{^0..^9}"),
        ("verbatim copy of let-binding",
         "Render: let s = ^5^P; let t = ^8^C; s → t",
         "let s = ^5^P; let t = ^8^C; s → t"),
        ("verbatim copy of cross-register expression",
         "Express: (^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω",
         "(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω"),
    ]
    for label, prompt, gen in e2c_fail:
        case_id += 1
        cases.append(SmokeCase(
            case_id=case_id,
            failure_mode="english_to_cas_verbatim",
            expected_pass=False,
            description=label,
            inputs={"prompt_text": prompt, "generated_cas": gen},
            validator="anti_copy",
        ))

    # --- invalid_to_corrected jaccard (failure mode 4) --------------------
    # 13 cases: 7 pass (minimal edit), 6 fail (whole rewrite).
    i2c_pass = [
        ("operator index 13->1 (single char fix)",
         "^13^E|f + ^1^E|E", "^1^E|f + ^1^E|E"),
        ("missing closing bracket added",
         "Phi<6 2", "Phi<6:2>"),
        ("missing domain letter inserted",
         "^5^ + ^8^C", "^5^P + ^8^C"),
        ("F8 -> F7 (single token fix)",
         "let s = ^9^P_{F8}", "let s = ^9^P_{F7}"),
        ("comma -> colon in fractal",
         "Phi<6,2,7>", "Phi<6:2:7>"),
        ("missing register letter added",
         "^3^E| + ^1^E|E", "^3^E|f + ^1^E|E"),
        ("plus -> times in recipe",
         "Theta(Omega_x) = 0.7+^5^P -> Omega_x",
         "Theta(Omega_x) = 0.7*^5^P -> Omega_x"),
    ]
    for label, inv, cor in i2c_pass:
        case_id += 1
        cases.append(SmokeCase(
            case_id=case_id,
            failure_mode="invalid_to_corrected_unrelated",
            expected_pass=True,
            description=label,
            inputs={"invalid_expression": inv, "corrected_expression": cor},
            validator="jaccard",
        ))
    i2c_fail = [
        ("whole-expression rewrite, recipe to state literal",
         "Θ(Ω_x) = 0.7+^5^P → Ω_x",
         "^3^P|A"),
        ("whole-expression rewrite, fractal to recipe",
         "Phi<6 2",
         "Θ(Ω_y) = 1*^4^E → Ω_y"),
        ("whole-expression rewrite, RPM chain to bare state",
         "let s = ^9^P_{F8}; let t = ^9^C_{F7}; s -> t",
         "^4^P"),
        ("whole-expression rewrite, meta-logic to recipe",
         "PartitionOf(StateSet{^0,^1,^2}, NoeticCluster{^3,^4})",
         "Θ(Ω_z) = 1*^7^O → Ω_z"),
        ("whole-expression rewrite, cross-register to fractal",
         "(^3^P|A × ^3^P|f) = ^3^P|Ω",
         "Φ⟨9:4:7⟩"),
        ("whole-expression rewrite, binary composition to let-binding",
         "^4^E × ^2^",
         "let foo = ^1^P; let bar = ^2^C; foo -> bar"),
    ]
    for label, inv, cor in i2c_fail:
        case_id += 1
        cases.append(SmokeCase(
            case_id=case_id,
            failure_mode="invalid_to_corrected_unrelated",
            expected_pass=False,
            description=label,
            inputs={"invalid_expression": inv, "corrected_expression": cor},
            validator="jaccard",
        ))

    return cases


def run_smoke():
    v2 = _load_v2()
    cases = build_cases()
    assert len(cases) == 50, f"expected 50 cases, got {len(cases)}"
    results: list[dict] = []
    for c in cases:
        if c.validator == "recipe_preservation":
            r = v2.validate_cas_to_english_recipe_preservation(**c.inputs)
        elif c.validator == "fractal_k_indices":
            r = v2.validate_cas_to_english_fractal_k_indices(**c.inputs)
        elif c.validator == "anti_copy":
            r = v2.validate_anti_copy_english_to_cas(**c.inputs)
        elif c.validator == "jaccard":
            r = v2.validate_invalid_to_corrected_jaccard(**c.inputs)
        else:
            raise ValueError(f"unknown validator: {c.validator}")
        outcome_correct = (r.passed == c.expected_pass)
        results.append({
            "case_id": c.case_id,
            "failure_mode": c.failure_mode,
            "validator": c.validator,
            "description": c.description,
            "expected_pass": c.expected_pass,
            "actual_pass": r.passed,
            "outcome_correct": outcome_correct,
            "reason": r.reason,
            "inputs": c.inputs,
        })
    return results


def write_markdown_report(results: list[dict], out_path: Path) -> None:
    """Write the smoke report markdown."""
    by_mode: dict[str, list[dict]] = {}
    for r in results:
        by_mode.setdefault(r["failure_mode"], []).append(r)

    correct_total = sum(1 for r in results if r["outcome_correct"])
    incorrect_total = len(results) - correct_total

    lines: list[str] = []
    lines.append("# Wave 3 v2 dry-run smoke (2026-05-08)")
    lines.append("")
    lines.append(
        "Hand-built 50-case smoke covering the four content-preservation "
        "failure modes the audit caught. **No API calls.** Every example "
        "output is hand-constructed; each is run through the corresponding "
        "v2 validator; the report records expected vs actual pass/fail."
    )
    lines.append("")
    lines.append(
        "Purpose: prove the validators reject the audit's known-bad cases "
        "and accept the audit's known-good shapes. This is NOT evidence "
        "that the new prompts produce faithful output at scale."
    )
    lines.append("")
    lines.append("## Aggregate")
    lines.append("")
    lines.append(f"- Total cases: {len(results)}")
    lines.append(f"- Validator outcome correct (matches expected): {correct_total}")
    lines.append(f"- Validator outcome wrong: {incorrect_total}")
    lines.append("")
    if incorrect_total > 0:
        lines.append(
            "**WARNING: validator behavior diverged from expectation in "
            f"{incorrect_total} case(s).** Investigate before paid generation."
        )
        lines.append("")

    lines.append("## Per-failure-mode breakdown")
    lines.append("")
    for mode in sorted(by_mode.keys()):
        mode_cases = by_mode[mode]
        n_pass_expected = sum(1 for r in mode_cases if r["expected_pass"])
        n_fail_expected = len(mode_cases) - n_pass_expected
        n_correct = sum(1 for r in mode_cases if r["outcome_correct"])
        lines.append(f"### `{mode}`")
        lines.append("")
        lines.append(
            f"- {len(mode_cases)} cases ({n_pass_expected} expected-pass, "
            f"{n_fail_expected} expected-fail)"
        )
        lines.append(
            f"- Validator outcome correct: {n_correct}/{len(mode_cases)}"
        )
        lines.append("")

    lines.append("## Per-case detail")
    lines.append("")
    for r in results:
        marker = "OK" if r["outcome_correct"] else "MISMATCH"
        lines.append(
            f"### Case {r['case_id']:02d} — [{marker}] `{r['failure_mode']}` "
            f"(`{r['validator']}`)"
        )
        lines.append("")
        lines.append(f"- Description: {r['description']}")
        lines.append(f"- Expected pass: `{r['expected_pass']}` — Actual pass: `{r['actual_pass']}`")
        if r["reason"]:
            reason = str(r["reason"]).replace("\n", " ")
            lines.append(f"- Validator reason: {reason}")
        for k, v in r["inputs"].items():
            v_str = str(v).replace("\n", " ")
            lines.append(f"- `{k}`: `{v_str}`")
        lines.append("")

    lines.append("## What this smoke does NOT prove")
    lines.append("")
    lines.append(
        "- That the new prompts produce faithful output. Every example "
        "output here is hand-constructed; the smoke only exercises the "
        "validators."
    )
    lines.append(
        "- That the new pipeline produces clean records at scale. Wave 3 "
        "phase 2 paid generation must be re-run by the user before any "
        "such claim. The validators are necessary but not sufficient."
    )
    lines.append(
        "- That the Wave 2.5 design produces useful English. The dry-run "
        "Wave 2.5 generates synthetic placeholder text; only paid model "
        "calls produce real English candidates for the english_to_cas slot."
    )
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    results = run_smoke()
    out_path = (
        _REPO_ROOT / "docs" / "working" / "wave3_dry_run_smoke_2026_05_08.md"
    )
    write_markdown_report(results, out_path)
    correct = sum(1 for r in results if r["outcome_correct"])
    print(f"wrote {out_path}")
    print(f"validator outcome correct: {correct}/{len(results)}")
    return 0 if correct == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
