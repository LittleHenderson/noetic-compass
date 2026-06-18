# W0 Pre-Speech (comply/refuse) — Lane A RESULT

Date: 2026-06-18
Status: **Lane A FAILS. internal_w0 comply/refuse detection stays OPEN / NOT LICENSED. Lane B not attempted (gated on Lane A).**

## What was run

Direct Lane A readout: can W0 (embedding/early hidden state at the final prompt
token, pre-token-1) predict COMPLIED vs REFUSED, beating word- AND char-level text
controls? Grouped 5-fold CV (folds by exact prompt carrier), balanced accuracy,
StandardScaler+LogisticRegression — layer scan over all 29 layers, on the two real
archived Qwen2.5-1.5B comply/refuse W0 datasets.

## Result (both datasets fail)

| Dataset | rows / groups | labels | best hidden BA (layer) | word-text BA | char-text BA | hidden−word | hidden−char |
|---|---|---|---|---|---|---|---|
| matched_chain_break seed00_47_v2 | 1312 / 40 | REFUSED 1006 / COMPLIED 306 | 0.569 (L25) | 0.516 | 0.513 | +0.053 | +0.056 |
| expanded_bank_v2_s16 | 1920 / 120 | REFUSED 1545 / COMPLIED 375 | 0.587 (L28) | 0.586 | 0.558 | +0.0006 | +0.029 |

Gate requires hidden BA ≥ 0.75 AND hidden − text ≥ 0.15 (word AND char). Both
datasets miss on every count. On the expanded bank the hidden readout *ties* the
word-text control (+0.0006) — exactly the "no signal beyond surface" pattern.

## Interpretation

W0 does **not** linearly expose comply/refuse on Qwen2.5-1.5B for these banks: the
readout is near chance (~0.57–0.59) and does not beat text. The earlier "0.745"
figure came from a different, more elaborate chain-break-RISK framing (per-prompt
break-rate → HIGH/LOW risk class), which itself failed its text-margin gate; the
direct per-row comply/refuse readout is weaker still.

Effective N is small (40 and 120 prompt groups; rows are seed/variant copies), so
even the marginal hidden−text gaps are within noise.

## Consequence

- `internal_w0_prompt_injection_detection` (comply/refuse stance): OPEN / NOT LICENSED — empirically fails.
- Lane B (causal intervention) NOT run: it is gated on a Lane A pass and on a
  validated direction; the direction here barely separates (BA ~0.57), so steering
  it would test noise.
- All six active-goal claims remain OPEN / NOT LICENSED.

## Apparatus is reusable

The apparatus (`w0_capture.py`, `refusal_recipe_probe.py`, `causal_intervention.py`,
runners, prereg) stands. If a future bank with many INDEPENDENT prompts and a real
behavioral signal is built and W0 clears the gate on a fresh GPU capture, Lane B can
run unchanged. Nothing here licenses a claim.
