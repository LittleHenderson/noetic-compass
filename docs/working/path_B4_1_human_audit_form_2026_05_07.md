# Path B-4.1 — Human PoC + Relevance Audit

**Goal:** verify the experimental B-4 chat REPL is good enough to call v0 production-ready, OR identify specific failure modes to fix first.

**Sample size:** 21 curated demo prompts (run via `/menu`) + 10 free-form prompts you write yourself = 31 total.

**Promotion gate (decided 2026-05-07):**
- Average **relevance** ≥ 3.5 / 5
- Average **register fit** ≥ 4 / 5
- **Leakage** = 0 (any CAS / noetic / domain / drive / register / `^N` / F1-F7 in the reply text)

If gate clears → record stakeholder PoC. If not → tune inference defaults or add a Tier 4 instruction-following SDG slice + fine-tune.

---

## How to launch the REPL (step-by-step)

### One-time terminal setup

1. Open **Git Bash** (or PowerShell) on Windows.
2. Navigate to the project root:
   ```
   cd /c/Users/wakil/OneDrive/Desktop/tksCAS
   ```
   (in PowerShell: `cd C:\Users\wakil\OneDrive\Desktop\tksCAS`)

### Launch the chat REPL

3. Run the REPL:
   ```
   python noetic-compass-scaffold/noetic-compass/cas-native/inference/chat.py
   ```
   You should see a banner that mentions **"B-3 native generator AVAILABLE (/native to toggle)"**. If you see "B-3 native generator NOT FOUND" or no native reference, the artifacts didn't load — stop and surface to me.

### Enter native mode

4. At the prompt, type:
   ```
   /native
   ```
   Press Enter. You'll see `Native generation: ON`. The model is now wired to generate replies via the trained checkpoint after K=9 predicts the CAS state.

### Run through the 21 curated prompts

5. Type:
   ```
   /menu
   ```
   You'll see a numbered list of 21 demo prompts, each tagged with bucket and feature.
6. Pick a number (1-21), press Enter. You'll see:
   - **INPUT**: the demo prompt text
   - **CAS PREDICTION**: K=9's Stage-1 output (e.g., `^5^C_{F1}`)
   - **NATIVE ENGLISH**: the model's Stage-2 generated reply
   - **NOTE**: bucket / feature / ground_truth metadata
7. Score it in the table below (curated section). Then `/menu` again, pick the next number. Repeat for all 21.

### Run 10 free-form prompts

8. After the curated 21, just **type your own prompt** at the chat prompt — anything conversational. Examples:
   - "I'm anxious about a deadline tomorrow."
   - "I keep replaying this argument in my head."
   - "Help me think through whether to take this job offer."
   - "I'm trying to figure out if I should reach out to my friend or just let it go."
9. The model treats these as user input (not a `/command`), runs Stage 1 + Stage 2, shows you the same INPUT / CAS PREDICTION / NATIVE ENGLISH layout. Score in the free-form table below.

### When done

10. Type `/exit` or Ctrl+C to leave the REPL.
11. Save this filled-in form (it's your audit record).
12. Surface the totals to me; we'll decide on production-ready or follow-on tuning.

### Useful commands inside the REPL

- `/help` — list all commands
- `/native` — toggle native mode ON/OFF (compare native vs rule-based fallback if you want)
- `/raw` — toggle full prediction dump
- `/menu` or `/m` — show the 21 demo prompts
- `/sample` or `/s` — pick one demo at random
- `/trace` — show the most recent activation trace (Mode 7)

---

## Scoring rubric

| Field | Meaning |
|---|---|
| Prompt | Brief: copy the actual prompt text (or for /menu, just the demo number + bucket name is enough) |
| CAS prediction | The `^N^D_{Fn}\|R` string K=9 returned |
| Native reply | The first ~200 chars of the generated reply (paste enough to judge) |
| Leakage | Y / N — did the reply contain `CAS`, `noetic`, `domain`, `drive`, `register`, `^N`, or `F1`-`F7`? |
| Relevance 1-5 | 1 = ignored prompt entirely. 3 = related but drifts. 5 = directly engages the prompt's content |
| Register fit 1-5 | 1 = wrong voice for the conditioned register. 3 = some signs of register. 5 = clearly in-register (Affective = feeling-toned, Embodied = bodily, Analytical = step-by-step, Transcendent = abstract/integrative) |
| Notes | Repetition / mid-sentence cutoffs / stutters / stuck phrases |

---

## Section A — 21 Curated demo prompts (use `/menu`)

### Prompt 1
- **Prompt** (copy from /menu output):
- **Bucket / feature** (from NOTE):
- **CAS prediction**:
- **Native reply** (first ~200 chars):
- **Leakage** (Y/N):
- **Relevance** (1-5):
- **Register fit** (1-5):
- **Notes**:

### Prompt 2
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 3
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 4
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 5
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 6
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 7
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 8
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 9
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 10
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 11
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 12
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 13
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 14
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 15
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 16
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 17
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 18
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 19
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 20
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Prompt 21
- **Prompt**:
- **Bucket / feature**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

---

## Section B — 10 Free-form user prompts (your own questions)

These should be REAL conversational queries you'd actually ask. Mix of:
- Emotional / vulnerable ("I'm worried about X")
- Decision support ("Should I do X or Y?")
- Reflection ("Why do I keep doing X?")
- Practical ("Help me think through X")

Don't include CAS jargon — type like a normal user would.

### Free 1
- **Your prompt**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Free 2
- **Your prompt**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Free 3
- **Your prompt**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Free 4
- **Your prompt**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Free 5
- **Your prompt**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Free 6
- **Your prompt**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Free 7
- **Your prompt**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Free 8
- **Your prompt**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Free 9
- **Your prompt**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

### Free 10
- **Your prompt**:
- **CAS prediction**:
- **Native reply**:
- **Leakage**:
- **Relevance**:
- **Register fit**:
- **Notes**:

---

## Aggregate (fill in after scoring all 31)

### Curated 21
- Avg relevance: ___ / 5
- Avg register fit: ___ / 5
- Total leakage: ___ / 21
- Notable failure modes (count):
  - Prompt drift (model didn't address prompt): ___
  - Mid-sentence cutoffs (token cap): ___
  - Repetition / stutters: ___
  - Wrong register voice: ___

### Free-form 10
- Avg relevance: ___ / 5
- Avg register fit: ___ / 5
- Total leakage: ___ / 10
- Notable failure modes:
  - Prompt drift: ___
  - Mid-sentence cutoffs: ___
  - Repetition: ___
  - Wrong register: ___

### Combined verdict
- Combined avg relevance: ___ / 5  (gate: ≥ 3.5)
- Combined avg register fit: ___ / 5  (gate: ≥ 4)
- Total leakage: ___ / 31  (gate: 0)
- **GATE OUTCOME**: PASS / FAIL

If FAIL, which lever to pull first:
- [ ] Inference tuning (lower temp, tighter top_p, repetition penalty)
- [ ] Add Tier 4 instruction-following slice + fine-tune
- [ ] Larger architecture / more epochs
- [ ] Other:

---

## Quick sanity tips while scoring

- **A reply that's fluent but ignores the prompt** = relevance 2 (the smoke 3/3 example "ritual + continuity" was this — good English, didn't follow "produce the expression")
- **A reply that addresses the prompt but in the wrong register** = relevance 4-5, register fit 2-3
- **A reply with hangs / mid-word cutoff** = note in **Notes**, doesn't directly affect relevance score
- **Free-form prompts are the harder test** — that's where real users live; expect lower scores than curated prompts
- **Don't score harshly on minor stutters** ("continuity, continuity") — note them but if the rest is good, relevance/register stay high

When you're done, paste the aggregate section back to me and we'll decide the next move.
