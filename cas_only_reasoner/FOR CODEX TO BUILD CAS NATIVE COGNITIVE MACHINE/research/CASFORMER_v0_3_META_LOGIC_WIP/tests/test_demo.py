from cas_meta.demo import run_demo


def test_actual_fresh_process_resume_and_semantic_equivalence(tmp_path):
    result = run_demo(tmp_path / "demo")
    assert result["fresh_process_restart"]
    assert result["native_trace_count"] == 5
    assert result["accepted_effects"] == 4
    assert result["meta_event_count"] == 20
    assert result["budget_reserved_policy_units"] == 360
    assert result["semantic_projection_equal"]
    assert result["fixed_weights"]
