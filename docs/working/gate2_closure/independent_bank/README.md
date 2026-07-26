# Track A — AI-Mediated Independent Bank

## Purpose

Break the shared-authorship deadlock that killed six instruments (v1–v5b) by
generating an evaluation bank using a frontier AI model prompted with ONLY
colloquial English descriptions — zero TKS/CAS terminology.

## Files

| File | Purpose |
|---|---|
| `cell_descriptions_colloquial.json` | 40 cell descriptions in plain English with positive/negative examples |
| `elicit_prompt_template.txt` | Prompt template with placeholders for cell descriptions |
| `build_prompt.py` | Assembles the full prompt from cell descriptions + template |
| `blindness_probe.py` | Verifies the AI authoring model hasn't been exposed to TKS/CAS |
| `acceptance_gate.py` | Validates generated bank BEFORE any model run (5 gates) |

## Workflow

### Step 1: Build the prompt
```bash
cd docs/working/gate2_closure/independent_bank
python build_prompt.py --items-per-cell 12 --output elicit_prompt.txt
```

Verify the prompt passes the TKS terminology check (printed by build_prompt.py).

### Step 2: Probe the AI model for blindness
```bash
python blindness_probe.py --model gpt-4o --threshold 0.3
```

If the model FAILS (mean score ≥ 0.3), it likely knows TKS — try a different
model or an older model with a training cutoff before TKS publication.

### Step 3: Generate the bank
Send `elicit_prompt.txt` to the AI model at temperature 0.7–1.0.
Request exactly the JSON array output format.
Save the response as `generated_bank_raw.json`.

### Step 4: Convert to JSONL and validate
```bash
python -c "
import json
data = json.load(open('generated_bank_raw.json'))
with open('generated_bank.jsonl', 'w') as f:
    for item in data:
        f.write(json.dumps(item) + '\n')
print(f'{len(data)} items written')
"
```

### Step 5: Run acceptance gates
```bash
python acceptance_gate.py \
  --bank generated_bank.jsonl \
  --tks-defs ../../tks_owner_locked_definitions_20260603.json \
  --cas-defs ../item4_arms/arm_D_compact_cas.json
```

All five gates (G1–G5) must PASS. If any gate fails, the bank is REJECTED.
Do not repair — a repaired bank has been laundered against the gates.

### Step 6: Use the bank in Gate 2 Item 4
If the bank passes all gates, it becomes Arm E (or a replacement holdout) in
the `GATE2_ITEM4_PREREGISTRATION.md` experiment.

## Rules

- **R1**: Authors (AI or human) must never see TKS or CAS definitions.
- **R2**: The bank is REJECTED if any acceptance gate fails.
- **R3**: No post-hoc repair of a failed bank.
- **R4**: Vocabulary overlap with both definition sets measured and reported BEFORE any model run.

## Status

`SPECIFIED / SCRIPTS WRITTEN / NOT YET EXECUTED / NO MODEL PROBED`
