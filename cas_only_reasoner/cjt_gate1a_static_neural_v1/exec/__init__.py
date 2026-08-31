"""Gate 1B execution code (FROZEN at Gate 1A.1, BEFORE any owner signature).

Law (owner audit 2026-08-31, section 2): the complete training/evaluation
implementation is committed and digest-pinned in GATE1B_CODE_MANIFEST.json so the
owner's signature can bind the ACTUAL program, not a folder describing one.

Nothing in this package loads a model, touches a GPU, or reads protected data at
Gate 1A. Neural entry points fail closed with GPU_REQUIRED (exec/gpu_guard.py).
"""
