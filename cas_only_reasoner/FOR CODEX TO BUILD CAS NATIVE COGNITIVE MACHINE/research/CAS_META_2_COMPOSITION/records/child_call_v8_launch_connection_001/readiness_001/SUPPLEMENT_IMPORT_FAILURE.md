# Preserved local import failure

The first supplemental price lookup exited 1 before any AWS call in that script.

Original supplemental script SHA-256: `2e26fa8904efdf00834d06921b505a3fa54d8fce776f4d887383f87d0fb4ba8a`.

Command: `python -B records/child_call_v8_launch_connection_001/readiness_001/supplement.py`

The terminal reported at supplement.py line 9: `import probe`, then
`ModuleNotFoundError: No module named 'probe'`.

The follow-up changes only helper loading to use its explicit sibling path.
The 27 completed primary query records remain unchanged.
