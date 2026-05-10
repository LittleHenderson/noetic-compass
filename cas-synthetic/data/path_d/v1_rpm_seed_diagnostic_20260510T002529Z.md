# rpm_chain decoder-seeding diagnostic — 20260510T002529Z

Diagnostic question (per user 2026-05-09): if we force the valid RPM answer to start as a valid RPM explanation, can the model continue correctly?

Setup: same v1 PREFIX128 5ep checkpoint, same 3 rpm_chain val records the 24-record audit graded `wrong`. Greedy decoding both runs. Control = no seed. Treatment = `seed_rpm_silhouette=True` (decoder primed with `"Let <first_var_name> name "`).

Grades remain the human's call. Per-record human grading is
the truth source.

---

## Record 1/3 — `v1mix_cas_to_english_000068`

**source CAS:** `let stageA0_3_0234 = ^0^P; let stageD3_3_0234 = ^9^P_{F3}; let stageW3_3_0234 = ^9^C_{F3}; let stageP3_3_0234 = ^9^E_{F3}; stageW3_3_0234 -> stageP3_3_0234`

**target reply:**
> Let stageA0_3_0234 name a foundational thought, stageD3_3_0234 name something that popped into mind in the evaluative arena driven by a need for vitality, and stageW3_3_0234 name cognitive thinking driven by a need for vitality. Let stageP3_3_0234 name evaluative judgment driven by a need for vitality. stageW3_3_0234 then leads to stageP3_3_0234.

**control gen (no seed):**
> The expression sets up a starting point and then tries to hand off to a destination that was never defined anywhere. The destination name simply doesn't exist in the system, so the connection cannot be completed. A careful reader would notice that only one side of the intended link was actually created.
  *(n_steps=111, truncated=False)*

**seed text used (treatment):** `Let stageA0_3_0234 name `

**treatment gen (with seed):**
> Let stageA0_3_0234 name a foundational thought in the realm of a thought in the realm of wisdom and insight, and let stageD3_3_0234 name something that struck a chord in the evaluative realm of wisdom and insight. The then then leads to stageW3_3_0234 name something that rubs the wrong way in the evaluative arena.
  *(seed_tokens=15, new_n_steps=126, truncated=False)*

**human grading (fill in):**

| | grade | one-line note |
|---|---|---|
| control gen | _____ | |
| treatment gen | _____ | |
| **diagnostic verdict** | _____ | improved / unchanged / worse / mixed |

---

## Record 2/3 — `v1mix_cas_to_english_004854`

**source CAS:** `let stageA0_2_0277 = ^0^P; let stageD2_2_0277 = ^5^P_{F2}; let stageW2_2_0277 = ^5^C_{F2}; let stageP2_2_0277 = ^5^E_{F2}; stageW2_2_0277 -> stageP2_2_0277`

**target reply:**
> Let stageA0_2_0277 name a foundational thought, stageD2_2_0277 name who one is shaped by wisdom and insight, stageW2_2_0277 name cognitive thinking shaped by wisdom and insight, and stageP2_2_0277 name evaluative judgment shaped by wisdom and insight. stageW2_2_0277 then leads to stageP2_2_0277.

**control gen (no seed):**
> The expression sets up a starting point and then tries to hand off to a destination that was never defined anywhere. The destination name simply doesn't exist in the system, so the connection cannot be completed. A careful reader would notice that only one side of the intended link was actually created.
  *(n_steps=111, truncated=False)*

**seed text used (treatment):** `Let stageA0_2_0277 name `

**treatment gen (with seed):**
> Let stageA0_2_0277 name a foundational thought and let stageD2_2_0277 name something that speaks to you in the realm of wisdom and insight, and stageW2_2_0277 name a cognitive impression in the realm of wisdom and insight. The destination may the connection then leads to stageP2_2_0277.
  *(seed_tokens=15, new_n_steps=110, truncated=False)*

**human grading (fill in):**

| | grade | one-line note |
|---|---|---|
| control gen | _____ | |
| treatment gen | _____ | |
| **diagnostic verdict** | _____ | improved / unchanged / worse / mixed |

---

## Record 3/3 — `v1mix_cas_to_english_004826`

**source CAS:** `let stageA0_2_0287 = ^0^P; let stageD2_2_0287 = ^2^P_{F2}; let stageW2_2_0287 = ^2^C_{F2}; let stageP2_2_0287 = ^2^E_{F2}; stageA0_2_0287 -> stageD2_2_0287`

**target reply:**
> Let stageA0_2_0287 name a foundational thought, stageD2_2_0287 name something drawn toward wisdom and insight in the evaluative arena, stageW2_2_0287 name cognitive attention toward wisdom and insight, and stageP2_2_0287 name evaluative judgment toward wisdom and insight. stageA0_2_0287 leads to stageD2_2_0287.

**control gen (no seed):**
> The expression sets up a starting point and then tries to hand off to a destination that was never defined anywhere. The destination name simply doesn't exist in the system, so the connection cannot be completed. A careful reader would notice that only one side of the intended link was actually created.
  *(n_steps=111, truncated=False)*

**seed text used (treatment):** `Let stageA0_2_0287 name `

**treatment gen (with seed):**
> Let stageA0_2_0287 name a foundational thought and let stageD2_2_0287 name something that speaks to you in the realm of wisdom and insight, and let stageW2_2_0287 name something that popped into mind in the operational realm. The then then leads to stageP2_2_0287.
  *(seed_tokens=15, new_n_steps=107, truncated=False)*

**human grading (fill in):**

| | grade | one-line note |
|---|---|---|
| control gen | _____ | |
| treatment gen | _____ | |
| **diagnostic verdict** | _____ | improved / unchanged / worse / mixed |

---

## Diagnostic interpretation guide

- **All three improved (treatment >= control by ≥1 grade band):**
  Model has rpm_chain content but the silhouette opening collapses
  into invalid-explanation language. Task-control is the issue.
  → schedule Option C (retrain with [VALID]/[INVALID] task tokens).

- **Treatment unchanged or worse:**
  Model doesn't actually know how to fill valid RPM chains
  reliably. Decoder-seeding only forces the opening; if the
  continuation is still wrong, the issue is training data /
  task tokens, not silhouette routing.
  → Option A is insufficient; need more rpm_chain training
  data, [VALID]/[INVALID] tokens, or both.

- **Mixed (some improved, some not):**
  Partial signal. Probe with 10-20 more rpm_chain records before
  committing to direction.