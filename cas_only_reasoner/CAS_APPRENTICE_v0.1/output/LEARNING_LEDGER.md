# THE CNCM LEARNING LEDGER

## 1. What the machine KNOWS right now

**Grammar constructions: 4 durable** (of 4 in the store)

| construction | state | taught by | evidence |
|---|---|---|---|
| active_past_transitive | ACTIVE/PROMOTED_DURABLY | hand_authored_seed_teacher | lesson:SEED_L001_active_past|teacher:hand_authored_seed_teac |
| negated_present_transitive | ACTIVE/PROMOTED_DURABLY | Qwen/Qwen2.5-3B-Instruct | lesson:LIVE_L002_negation_constrained|teacher:Qwen/Qwen2.5-3 |
| passive_past | ACTIVE/PROMOTED_DURABLY | hand_authored_seed_teacher | lesson:SEED_L002_passive_past|teacher:hand_authored_seed_tea |
| passive_present | ACTIVE/PROMOTED_DURABLY | hand_authored_seed_teacher | lesson:SEED_L003_passive_present|teacher:hand_authored_seed_ |

**Words: 10** (brown, cat, chases, dog, gray, is, it, not, quiet, the)
**Verb forms (morphology): 2** (chase, chased)

## 2. Learned from a LIVE MODEL TEACHER

- **negated_present_transitive** - provenance `lesson:LIVE_L002_negation_constrained|teacher:Qwen/Qwen2.5-3B-Instruct`

## 3. PROOF the learning is real (before vs after)

Teacher **Qwen/Qwen2.5-3B-Instruct**, probe `the cat does not chase the dog.`:
- BEFORE the lesson: **UNSUPPORTED_LANGUAGE** (route no_answer)
- AFTER the lesson: **UNDERSTOOD** (route native_gram), core = `{'args': ['chase', 'cat', 'dog'], 'pred': 'relation'}`

**Unseen-sentence check (run live at ledger generation, NATIVE only - no model anywhere):**

- `the dog does not chase the cat.` -> **UNDERSTOOD** (route native_gram), core = `{'pred': 'negation', 'args': [{'pred': 'relation', 'args': ['chase', 'dog', 'cat']}]}`
- `the dog was chased by the cat.` -> **UNDERSTOOD** (route native_gram), core = `{'pred': 'relation', 'args': ['chase', 'cat', 'dog']}`
- `the cat chases the dog.` -> **UNDERSTOOD** (route native), core = `{'pred': 'relation', 'args': ['chase', 'cat', 'dog']}`

## 4. The paper trail

- Seed teaching episodes on file: 3
- Live teacher episodes sealed: 2 (every attempt, pass or fail)
  - Qwen/Qwen2.5-1.5B-Instruct: REJECTED_SCHEMA, REJECTED_SCHEMA
  - Qwen/Qwen2.5-3B-Instruct: REJECTED_SCHEMA, REJECTED_SCHEMA
- Constrained-teaching artifacts: 1

Every durable rule carries provenance, its regression guard, and a rollback path; every lesson attempt - including every REJECTION - is a sealed episode. Nothing enters this ledger by assertion.
