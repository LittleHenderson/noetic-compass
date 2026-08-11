# Attempt 2 operator notes

These notes are stored adjacent to, not inside, the frozen Attempt 2
directory. They preserve operator context without adding to or changing the
independently verified evidence directory.

## Rejected preflight-only mapping pair

Two files are deliberately retained inside the frozen attempt directory with
`REJECTED` in their names:

- `jacobian_lens_canary_v1_launch_config_REJECTED_BASE_PROTOCOL_CANONICAL.json`
  - SHA-256
    `89f6d3436733ebd6cb2057929a884f84a1d5df7f45a61597195dd06ba2dde603`
- `jacobian_lens_canary_v1_launch_target_paths_REJECTED_BASE_PROTOCOL_CANONICAL.json`
  - SHA-256
    `e64b908f8be1fdd2692bbe3d40b4191fe6ab1771c26dd3ad9066926f2bb6b704`

They were generated and rejected during local preflight because they mapped
`base_protocol_path` to the canonicalized V0 representation rather than the
required raw V0 file. They were never uploaded, anchored, or executed. The
accepted Attempt 2 mapping points to the raw V0 file. Preserve the rejected
pair as failed-preflight provenance; never substitute either file into an
official reconstruction.

## Malformed wrapper-exit transcript

`runlog/wrapper.exit_code.txt` contains the literal text `0n` because the
remote PowerShell-to-shell quoting wrote the character `n` instead of a
newline. Preserve that file unchanged. The provider/SSH execution record
separately observed wrapper process exit code `0`.

Exit code `0` means only that the official wrapper completed its fail-closed
publication duties and successfully wrote the negative receipt. It does not
mean that CUDA initialized, a model ran, a technical canary passed, or a
scientific claim was licensed. The controlling facts are the create-once
producer receipt, marker, POST capture, and independent receiver receipt:
`FAILED_CLOSED_EVIDENCE_CHAIN_VERIFIED_NO_SCIENTIFIC_CONCLUSION`.
