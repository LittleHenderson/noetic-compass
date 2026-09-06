# V7 smoke trainer private-file boundary

The corrected training-child admission passes with zero private-file access
attempts. It reads the real saved public-only 352/24/9 fixture and reaches an
inert training sentinel. No neural framework or provider is imported, no
training runs, and no task is generated.

Exact command, from `research/CAS_META_2_COMPOSITION`:

```text
C:/Python314/python.exe -I -S -B tests/test_contrast_v7_smoke_private.py --records records/contrast_v7_smoke_private_review_001/checks_001
```

Result: 2 tests passed, 7.569 seconds. Each test runs in a separate fresh child.
The child checks five independent traps: `builtins.open`, `io.open`, Python's
`open` audit event, `hashlib.file_digest`, and the smoke helper's `file_hash`.
Each trap is tested before admission; those self-checks are excluded from the
admission counters. Real public bundle reads are required during admission.

The saved fixture manifest is externally pinned to
`19162857679b3eb2e698c58ee8e0ac5dc3c7ffe7265e11e8ae1c726834067f29`.
The real loader checks the source identities, original256 append and counts.
The test repeats the public load at the inert `t.run` entrypoint and checks the
one-epoch, batch16 configuration: 22 optimizer steps per family if actually run.

The `former` test reconstructs the old routing from `check_assembly` to the full
private-reading fixture checker. The hash trap catches its `test_private.json`
access before any private byte is read or training sentinel is called. This is
a reconstructed regression, not byte-for-byte execution of an archived file.

AWS/path guards and the prior parent-exit record are simulated. The actual
receipt/hash checks, public fixture reads and public loader are exercised.
These records prove a read boundary, not GPU execution, completed training,
successful parent execution, or learning.

Retained records:

- `checks_001/fixed/test_receipt.json`, SHA256
  `107e74fbe977d4f1965369bb28a8ba5176ca044d5e931916e2e571c1cf1afd84`.
- `checks_001/former/test_receipt.json`, SHA256
  `065bfe24592314a5301729ad551910d03d463bbd15089895c8118a783b324c51`.
- Both fresh-child commands and raw stdout/stderr are beside those directories.

Test source SHA256:
`54a2b99aaaaa8e3dd6c9a962d5d98939d1177fd1f055685e4399660be5afb3f6`.
No other agent's code was edited and nothing was staged or committed here.
