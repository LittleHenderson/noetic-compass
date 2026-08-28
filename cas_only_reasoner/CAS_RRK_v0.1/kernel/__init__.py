"""CAS Reasoning Runtime Kernel v0.1 - the Python reference kernel.

Single-threaded, deterministic, typed, snapshot-based, intent-driven.
No subsystem mutates authoritative state: every component emits typed
intents and the transaction coordinator is the sole writer.
"""

CAS_RRK_VERSION = "0.1.0"
