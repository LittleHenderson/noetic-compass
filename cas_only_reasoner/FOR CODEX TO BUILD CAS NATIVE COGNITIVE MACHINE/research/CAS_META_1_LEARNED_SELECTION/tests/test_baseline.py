from cas_meta1.baseline import verify_baseline, BASELINE_SHA

def test_accepted_source_bytes_preserved():
    receipt = verify_baseline()
    assert receipt["baseline_sha"] == BASELINE_SHA
    assert receipt["files_verified"] == 316
