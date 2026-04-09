"""Tests for assessment evaluation trace."""

from api.pipeline.trace import AssessmentTrace, build_trace_from_stages, TraceStep


class TestAssessmentTrace:
    def test_add_step(self):
        trace = AssessmentTrace()
        trace.add_step("input_analyzer", "parse", "text", "247 tokens", "Parsed")
        assert len(trace.steps) == 1
        assert trace.steps[0].stage == "input_analyzer"

    def test_complete(self):
        trace = AssessmentTrace()
        trace.complete()
        assert trace.completed_at != ""

    def test_to_dict(self):
        trace = AssessmentTrace()
        trace.add_step("test", "rule", "in", "out", "done")
        d = trace.to_dict()
        assert d["step_count"] == 1
        assert len(d["steps"]) == 1
        assert d["steps"][0]["stage"] == "test"

    def test_to_text(self):
        trace = AssessmentTrace()
        trace.add_step("input_analyzer", "parse(text)", "raw text", "247 tokens", "Validated")
        trace.complete()
        text = trace.to_text()
        assert "Step 1" in text
        assert "input_analyzer" in text
        assert "parse(text)" in text


class TestBuildTrace:
    def test_build_from_stages(self):
        stages = [
            {"stage": "input_analyzer", "success": True, "data": {"token_count": 247}},
            {"stage": "operator_scoring", "success": True, "data": {"scores": [0.5] * 10}},
            {"stage": "domain_coherence", "success": True, "data": {"dci": 0.85, "domain_averages": [0.25] * 4}},
            {"stage": "output_gate", "success": True, "data": {"composite": 68.5, "certification": "Silver"}},
        ]
        trace = build_trace_from_stages(stages)
        assert len(trace.steps) == 4
        assert "247" in trace.steps[0].output_summary
        assert "0.500" in trace.steps[1].output_summary
        assert "Silver" in trace.steps[3].output_summary

    def test_build_with_failure(self):
        stages = [
            {"stage": "base_llm_call", "success": False, "data": {}, "error": "Provider timeout"},
        ]
        trace = build_trace_from_stages(stages)
        assert "FAILED" in trace.steps[0].output_summary
        assert "timeout" in trace.steps[0].reduction
