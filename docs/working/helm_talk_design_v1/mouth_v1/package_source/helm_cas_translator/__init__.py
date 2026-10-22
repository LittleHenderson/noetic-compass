"""helm_cas_translator -- the CAS-token translator (CTT-1, "ears first"). A SEPARATE component.

It proposes CAS records from English. It decides nothing. It imports only the Python standard library and torch,
and nothing from HELM (no brain, cube store, receipts, memory, loop, reader or voice). Static gate: H-SEP
(tests_ctt/test_separation.py). Runtime gate: H-WRITE (the audit hook in serve.py).
Claim status: ENGINEERED-NOT-VALIDATED.
"""
CTT_VERSION = "ctt-1 (2026-10-19)"
