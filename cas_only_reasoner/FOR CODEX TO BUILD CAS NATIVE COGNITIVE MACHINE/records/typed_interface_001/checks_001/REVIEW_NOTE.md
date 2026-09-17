# Passed run superseded by a reviewed bound repair

This run completed normally: 237 checks passed and complete public-input/slot
sizing passed. Its receipt and all listed artifacts remain unmodified.
Receipt SHA-256: 7e039e128c70df4db27bdf8c987930a9604d163fe79c3a90d5e8ada69ddfafad.

Subsequent source review found that encode_text expanded a complete unknown
lexical unit into byte-token IDs before checking the output cap. The training
fixtures did not trigger this issue. The next version bounds raw text, iterates
lexical matches, and checks available capacity before expanding unknown units.
It also bounds decoded text before accumulating repeated fitted units or bytes.

The original runtime and test file are preserved here as tokenization_snapshot.py
and tokenization_test_snapshot.py, matching the original input pins. This record
does not certify the later fix. A new complete aggregate is required for it.
An attempted stop found no matching process because this run had already ended;
no test process was stopped. No tensor or provider execution occurred.
