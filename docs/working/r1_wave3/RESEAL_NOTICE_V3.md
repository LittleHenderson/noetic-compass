# Reseal notice v3 — to the X2 custodian (written 2026-10-19 by the wave-3 builder)

The package you checked against (`26b0ef7e…`) is VOID_SUPERSEDED_BY_A1. Use the v3 package from now on:

- `Documents\Codex\2026-10-19\r1_wave3\HELM_R1_W3_20261019_SOURCE_R1W3_v3.zip`
  sha256 `152bca2a3c869212642f96514e7d485413727bf92cf67e9aff1774cefa532362`, PACKAGE_FREEZE
  `bd06f324a9643a8aacefab3d8ef52de4cf673a68820544897def95854b73d310`. Check the zip's sha256 before you extract it.

What changed (amendment R1W3-A1, nothing else): the receiver's checker `r1w3/check_x2_format.py` and the host's first
stage now apply the English-16 / Faces-16 text rule to each item's STATEMENT only. Exactly one of the generator's 15
enumerated follow-up questions (`gen_live.FOLLOWUPS`, list sha256
`14f5cb49c7fb60a0d40686d0d6b18e8d34aa81de0a61fed345d0f1749d751ef5`) is stripped from the end of the last turn; every
stripped tail is recorded in the receipt (`followup_tails_stripped`). The generators' item code, the seed rule, the bands
and every other check are unchanged, so the files you already built need NOT be regenerated.

What to do:
1. Extract the v3 zip to a fresh folder. Do not edit anything in it.
2. Re-run the receiver's check on the files you already built (originals, unconverted):
   `python -B -m r1w3.check_x2_format <your X2 folder> --w1-dir <wave-1 v3 package> --extra-text-file <X1 ENGLISH16_X1.json>`
   from the extracted v3 package. It must print `all_pass: true`.
3. If it does: write `X2_SEAL_RECORD.json` with this v3 receipt as `receiver_check` (plus the A1 adjudication you already
   wrote), then `X2_PINS.json`, and hand over the pins and their sha256 as the contract says. If it does not: stop and
   report; do not convert or regenerate anything.
4. Your seed derivation stands only if it was computed from the owner's line that the X2 seed source names. The owner
   must re-sign on `152bca2a`; if the coordinator rules that X2's seed source moves to the new line, X2 is rebuilt from
   that line — that decision is the coordinator's and the owner's, not yours.

The builder has not seen and will not see any X2 content.
