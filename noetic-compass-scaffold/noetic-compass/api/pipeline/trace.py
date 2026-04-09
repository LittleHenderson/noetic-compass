"""Assessment Evaluation Trace — step-by-step derivation record.

Records a formal evaluation trace for every assessment, showing
exactly which rule fired at each pipeline stage and why.

Based on v6.1 Chapter 10 operational semantics (small-step/big-step).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TraceStep:
    """A single step in the evaluation trace."""

    stage: str
    rule_applied: str
    input_summary: str
    output_summary: str
    reduction: str  # Plain-English description
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AssessmentTrace:
    """Complete evaluation trace for an assessment."""

    steps: list[TraceStep] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = ""

    def add_step(
        self,
        stage: str,
        rule: str,
        input_summary: str,
        output_summary: str,
        reduction: str,
    ) -> None:
        self.steps.append(TraceStep(
            stage=stage,
            rule_applied=rule,
            input_summary=input_summary,
            output_summary=output_summary,
            reduction=reduction,
        ))

    def complete(self) -> None:
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "step_count": len(self.steps),
            "steps": [
                {
                    "stage": s.stage,
                    "rule": s.rule_applied,
                    "input": s.input_summary,
                    "output": s.output_summary,
                    "reduction": s.reduction,
                }
                for s in self.steps
            ],
        }

    def to_text(self) -> str:
        """Render trace as plain text for export."""
        lines = [
            "=== Assessment Evaluation Trace ===",
            f"Started: {self.started_at}",
            f"Completed: {self.completed_at}",
            f"Steps: {len(self.steps)}",
            "",
        ]
        for i, step in enumerate(self.steps, 1):
            lines.append(f"Step {i}: {step.stage}")
            lines.append(f"  Rule: {step.rule_applied}")
            lines.append(f"  Input: {step.input_summary}")
            lines.append(f"  Output: {step.output_summary}")
            lines.append(f"  Result: {step.reduction}")
            lines.append("")
        return "\n".join(lines)


def build_trace_from_stages(stages: list[dict]) -> AssessmentTrace:
    """Build a trace from pipeline stage results."""
    trace = AssessmentTrace()

    stage_rules = {
        "input_analyzer": ("parse(text) → TokenStream", "Tokenize and validate input text"),
        "rpm_gate": ("evalChain_m(σ)", "Evaluate RPM prerequisite chain"),
        "dial_adjustment": ("adjust(dials, input)", "Apply dial configuration to input"),
        "base_llm_call": ("generate(prompt, system)", "Call LLM for base response"),
        "operator_scoring": ("score(CO-k, response)", "Score response on 10 operators"),
        "domain_coherence": ("DCI = min(avg)/max(avg)", "Compute domain coherence index"),
        "inversion_scan": ("scan(response, 7-axes)", "Scan for inversions across 7 axes"),
        "output_gate": ("compute_nccs(subscores)", "Compute NCCS composite score"),
    }

    for stage_data in stages:
        name = stage_data.get("stage", "unknown")
        success = stage_data.get("success", False)
        data = stage_data.get("data", {})
        error = stage_data.get("error")

        rule, description = stage_rules.get(name, (name, name))

        if error:
            output_summary = f"FAILED: {error}"
            reduction = f"{name} failed — {error}"
        elif success:
            # Summarize key output data
            if name == "input_analyzer":
                tokens = data.get("token_count", "?")
                output_summary = f"{tokens} tokens processed"
                reduction = f"Input validated: {tokens} tokens"
            elif name == "operator_scoring":
                scores = data.get("scores", [])
                if scores:
                    avg = sum(scores) / len(scores)
                    output_summary = f"10 scores, avg={avg:.3f}"
                    reduction = f"Operator scoring complete: mean={avg:.3f}"
                else:
                    output_summary = "scores computed"
                    reduction = "Operator scoring complete"
            elif name == "domain_coherence":
                avgs = data.get("domain_averages", [])
                dci = data.get("dci", 0)
                output_summary = f"DCI={dci:.3f}"
                reduction = f"Domain coherence: DCI={dci:.3f}"
            elif name == "rpm_gate":
                completeness = data.get("rpm_completeness", 0)
                output_summary = f"RPM={completeness:.1%}"
                reduction = f"RPM completeness: {completeness:.1%}"
            elif name == "inversion_scan":
                stealth = data.get("stealth_resistance", 0)
                output_summary = f"stealth_resistance={stealth:.3f}"
                reduction = f"Inversion scan: stealth resistance {stealth:.3f}"
            elif name == "output_gate":
                composite = data.get("composite", 0)
                cert = data.get("certification", "?")
                output_summary = f"NCCS={composite:.1f}, cert={cert}"
                reduction = f"Final score: {composite:.1f} ({cert})"
            else:
                output_summary = "success"
                reduction = f"{name} completed successfully"
        else:
            output_summary = "no data"
            reduction = f"{name} produced no output"

        trace.add_step(
            stage=name,
            rule=rule,
            input_summary=f"stage {name}",
            output_summary=output_summary,
            reduction=reduction,
        )

    trace.complete()
    return trace
