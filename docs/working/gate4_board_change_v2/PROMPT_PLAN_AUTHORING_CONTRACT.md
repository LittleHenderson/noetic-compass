# Prompt-plan authoring contract

The claim-bearing `prompt_plan_v2.json` must be written by an author who has not read the
board taxonomy, board names, board rubric, or v1 model outputs. The current implementation
agent is not eligible because it audited those materials.

The author receives only the six family descriptions below and the JSON schema. No API or
model call may occur until the completed plan passes `core.validate_prompt_plan`, is
committed with the protocol, and is named by the remotely observed protocol lock.

## Exact allocation

| Stratum | Family | Count |
|---|---|---:|
| N | F1 factual → personal | 11 |
| N | F2 request → boundary | 11 |
| N | F3 open → action | 11 |
| N | F4 explain → edge of knowledge | 11 |
| N | F5 steady negative | 10 |
| N | F6 mixed | 18 |
| S | F6 mixed positive-control stratum | 20 |

All 92 seed prompts must be fresh. They must be unique both byte-for-byte and after NFKC,
whitespace, and case normalization. They must match neither the exact nor normalized SHA-256
bank for all 80 historical v1 prompt sources. The model
rotation is frozen so every provider receives exactly 18 N and 5 S conversations.

Each N conversation has nine explicitly frozen follow-ups chosen from C1–C5. Each S
conversation has nine explicitly frozen follow-ups from U1–U5 and must include U4 at least
once. Repetition inside a follow-up sequence is allowed; seed-prompt reuse is not.

The final file must validate against `schemas/prompt_plan_v2.schema.json` and the stronger
semantic checks in `core.validate_prompt_plan`. A self-attestation is required in the file,
but the author-selection record remains separate evidence; a boolean alone is not proof of
blindness.
