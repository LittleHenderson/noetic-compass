# v1 PREFIX128 5ep — 24-record human grading pack (20260510T191358Z)

## How to grade

For each record below, fill in the 5-axis grading row at the bottom:

- **correct_task** — did the gen produce the right silhouette for
  this task family? (cas_to_english silhouette for valid CAS,
  invalid_to_explanation silhouette for invalid CAS)
- **cas_meaning** — does the gen's content reflect the actual CAS
  source semantics (correct noetic, domain, drive, register)?
- **natural_language** — does it read like English a human would
  write, or like translation-ese?
- **completion** — does the sentence complete cleanly, or trail
  off / get clipped mid-clause?
- **useful_ending** — does the gen land a conclusion / "bring it
  home," or just stop?

Scale: ``green`` (faithful, lands), ``high_yellow`` (one slip),
``yellow`` (understandable but body content drifts),
``flop`` (target is clearly better),
``wrong`` (wrong task or major content error),
``incoherent`` (broken language).

After grading all 24 records, run::

    python cas-synthetic/scripts/v1_eval_pack_aggregator.py \
        --grades cas-synthetic/data/path_d/v1_eval_pack_24records_GRADED_<timestamp>.md

to aggregate against the v1 audit baseline (5/8 combined on
the prior 8-record pack).

## Structural summary (auto-filled, not the audit)

- records:                      24
- truncated (no EOS reached):   1/24
- quality_passed (no flags):    20/24
- task routed cas_to_english:   21/24
- task routed invalid_to_expl:  3/24
- hard CAS notation in gens:    0 (must be 0)
- jargon in gens:               0 (must be 0)
- Ω-name recovery pre-repair:   5/7 (71.4%)
- Ω-name recovery post-repair:  6/7 (85.7%)
- coefficient recovery pre:     3/8 (37.5%)
- coefficient recovery post:    4/8 (50.0%)

Aggregate counts are a starting point, not the audit. Per-record
human grades below are the truth source.

---

## Record 1/24 — [cas_to_english / state_literal]

**source CAS:** `^0^C_{F5}|E`

**target reply:**
> A thought in cognitive thinking, driven by a need for agency and self-determination, expressed in an embodied way.

**raw model gen:**
> A thought in cognitive thinking, driven by a need for agency and self-determination, expressed in an embodied way.

**repaired model gen:**
> A thought in cognitive thinking, driven by a need for agency and self-determination, expressed in an embodied way.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        47/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 2/24 — [cas_to_english / state_literal]

**source CAS:** `^0^E_{F2}|A`

**target reply:**
> A thought in evaluative judgment, driven by a need for wisdom, expressed through analytical reasoning.

**raw model gen:**
> A thought in evaluative judgment, driven by a need for wisdom, expressed through analytical reasoning.

**repaired model gen:**
> A thought in evaluative judgment, driven by a need for wisdom, expressed through analytical reasoning.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        34/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 3/24 — [cas_to_english / state_literal]

**source CAS:** `^8^P|E`

**target reply:**
> When one thing reminds you of another, triggering a memory or connection in a principled foundation, expressed through an embodied, sensorimotor way.

**raw model gen:**
> Amemory memory triggered by memory or association triggered a principled foundation expressed through an embodied way, and a transcendent strategic way of understanding.

**repaired model gen:**
> A memory triggered by memory or association triggered a principled foundation expressed through an embodied way, and a transcendent strategic way of understanding.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        49/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 4/24 — [cas_to_english / binary_composition]

**source CAS:** `^4^P + ^1^P`

**target reply:**
> A resonant impression in the foundational arena combined with paying attention in the foundational arena.

**raw model gen:**
> Something that struck a chord in the principled arena combined with paying attention in the principled arena.

**repaired model gen:**
> Something that struck a chord in the principled arena combined with paying attention in the principled arena.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        38/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 5/24 — [cas_to_english / binary_composition]

**source CAS:** `^8^E -> ^5^E`

**target reply:**
> A memory or association triggered in the evaluative arena becomes who one is shaped by experience in the evaluative arena.

**raw model gen:**
> A memory triggered in evaluative judging judging arena combined with who one is shaped by evaluative judgment that just clicked into evaluative judgment.

**repaired model gen:**
> A memory triggered in evaluative judging arena combined with who one is shaped by evaluative judgment that just clicked into evaluative judgment.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        48/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 6/24 — [cas_to_english / binary_composition]

**source CAS:** `^8^E + ^7^E`

**target reply:**
> A triggered memory in the evaluative arena combined with a practiced rhythm in the evaluative arena.

**raw model gen:**
> A memory triggered in evaluative judgment combined with practiced rhythm in evaluative judgment combined with practiced rhythm in evaluative judgment.

**repaired model gen:**
> A memory triggered in evaluative judgment combined with practiced rhythm in evaluative judgment combined with practiced rhythm in evaluative judgment.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `False`
- quality_failures:  `['repeated_phrase_count=1']`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        41/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 7/24 — [cas_to_english / cross_register_omega]

**source CAS:** `(^4^C|A × ^4^C|E × ^4^C|f) = ^4^C|Ω_clarity`

**target reply:**
> When something resonates in your mental thinking expressed through analytical reasoning, embodied bodily awareness, and felt emotion, those three modes fuse into the outcome called clarity.

**raw model gen:**
> When something resonates in your cognitive thinking expressed through analytical reasoning, embodied sensorimotor experience, and felt emotion — all three modes fusing together—the outcome called clarity.

**repaired model gen:**
> When something resonates in your cognitive thinking expressed through analytical reasoning, embodied sensorimotor experience, and felt emotion — all three modes fusing together—the outcome called clarity.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 1/1, post 1/1
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        62/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 8/24 — [cas_to_english / cross_register_omega]

**source CAS:** `(^5|T × ^5|f) = ^5|Ω_refusal`

**target reply:**
> When who you are—shaped by your sum of experiences—is expressed both in a felt, emotional way and in a transcendent, strategic way, those two modes fuse together into the outcome called refusal.

**raw model gen:**
> When who you are—shaped by your sum of experiences—is expressed through felt emotion and transcendent strategic conviction, those two modes fuse into the outcome called alignment.

**repaired model gen:**
> When who you are—shaped by your sum of experiences—is expressed through felt emotion and transcendent strategic conviction, those two modes fuse into the outcome called refusal.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/1, post 1/1
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=1 coef=0 var=0
- gen tokens:        59/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 9/24 — [cas_to_english / cross_register_omega]

**source CAS:** `(^1^E|E × ^1^E|f) = ^1^E|Ω_judgment`

**target reply:**
> When you pay attention to something in an evaluative way and combine that focused awareness with an affective, felt response and a bodily, sensorimotor dimension—all three modes of judging working together—they fuse into the outcome called judgment.

**raw model gen:**
> When you pay attention to an evaluative judgment expressed through embodied sensorimotor awareness and also through a felt, emotional way, those two modes fuse together into the outcome called judgment.

**repaired model gen:**
> When you pay attention to an evaluative judgment expressed through embodied sensorimotor awareness and also through a felt, emotional way, those two modes fuse together into the outcome called judgment.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 1/1, post 1/1
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        68/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 10/24 — [cas_to_english / recipe]

**source CAS:** `Θ(Ω_rehearsal_40) = 1*^3^E + 1.5*^1^P|f → Ω_rehearsal_40`

**target reply:**
> To produce the outcome called rehearsal_40, combine 1 unit of something that rubs the wrong way in an evaluative way, and add 1.5 units of paying attention to a foundational principle in an affective way — together these inputs yield the outcome called rehearsal_40.

**raw model gen:**
> To produce the outcome called rehearsal_40, combine 1 measure of paying attention to a foundational principle expressed through an affective way, and add 1.5 measures of paying attention to a foundational principle expressed through an affective way — together these inputs yield the named outcome production_40.

**repaired model gen:**
> To produce the outcome called rehearsal_40, combine 1 measure of paying attention to a foundational principle expressed through an affective way, and add 1.5 measures of paying attention to a foundational principle expressed through an affective way — together these inputs yield the named outcome production_40.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 1/1, post 1/1
- coef recovery:     pre 2/2, post 2/2
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        106/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 11/24 — [cas_to_english / recipe]

**source CAS:** `Θ(Ω_rehearsal_11) = 1.5*^7^O|T + 2*^6^C_{F3} → Ω_rehearsal_11 + 0.1*Λ·Ω_production_side`

**target reply:**
> To build the outcome called rehearsal_11, take 1.5 of what happens when you practice something until it becomes muscle memory in an operational way, expressed through a transcendent perspective. Add 2 of the analytical unpacking of a thought shaped by the need for vitality and energy. Together these inputs produce the outcome called rehearsal_11, which also contributes 0.1 of itself toward the outcome called production_side.

**raw model gen:**
> To produce the outcome called rehearsal_11, combine 1.5 measures of practiced rhythm applied to agency and self-determination in cognitive thinking, plus 1.5 measures of practiced rhythm in operational behavior tied to agency and self-determination. This recipe produces engagement_11.

**repaired model gen:**
> To produce the outcome called rehearsal_11, combine 1.5 measures of practiced rhythm applied to agency and self-determination in cognitive thinking, plus 1.5 measures of practiced rhythm in operational behavior tied to agency and self-determination. This recipe produces engagement_11.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 1/2, post 1/2
- coef recovery:     pre 1/3, post 1/3
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        110/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 12/24 — [cas_to_english / recipe]

**source CAS:** `Θ(Ω_judgment_78) = 2*^7^O + 0.7*^8^P|f + 0.7*^0^P_{F6} → Ω_judgment_78`

**target reply:**
> To produce the outcome called judgment_78, combine these inputs: muscle memory and practiced habit weighted at 2 from operational behavior, a 0.7 contribution from a foundational thought that triggered a memory expressed through an affective way, and a 0.7 contribution from a foundational idea about structure and order.

**raw model gen:**
> To produce the outcome called judgment_78, combine these three inputs: a full contribution of practice makes perfect applied to operational behavior expressed in an affective way, and add 1 of something that triggered a memory in operational behavior expressed in an affective way. Together these create the outcome called production_78.

**repaired model gen:**
> To produce the outcome called judgment_78, combine these three inputs: a full contribution of practice makes perfect applied to operational behavior expressed in an affective way, and add 2 of something that triggered a memory in operational behavior expressed in an affective way. Together these create the outcome called production_78.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 1/1, post 1/1
- coef recovery:     pre 0/3, post 1/3
- repair subs:       Ω=0 coef=1 var=0
- gen tokens:        117/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 13/24 — [cas_to_english / fractal_sequence]

**source CAS:** `Phi<6:9:7:0:9:5:2:0>`

**target reply:**
> An idea on the mind led to something drawn to it, then breaking it down, which became practice makes perfect, and finally something that popped into mind, in turn triggered by another thought, and shaped by experience, which then just clicked.

**raw model gen:**
> An idea on the mind led to paying attention, which then popped into mind again, then popped into mind again, and finally popped into mind again, then popped into mind again, popped into mind again, and finally popped into mind again.

**repaired model gen:**
> An idea on the mind led to paying attention, which then popped into mind again, then popped into mind again, and finally popped into mind again, then popped into mind again, popped into mind again, and finally popped into mind again.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `False`
- quality_failures:  `['repeated_phrase_count=3']`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        89/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 14/24 — [cas_to_english / fractal_sequence]

**source CAS:** `Φ<3:7>`

**target reply:**
> An aversion that became muscle memory.

**raw model gen:**
> Something that rubs the wrong way led to a thought that then became muscle memory.

**repaired model gen:**
> Something that rubs the wrong way led to a thought that then became muscle memory.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        32/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 15/24 — [cas_to_english / fractal_sequence]

**source CAS:** `Φ<1:0:3:3:1:1:7:5>`

**target reply:**
> An idea on the mind led to paying attention, then became an aversion, then another aversion, then struck a chord, then struck a chord again, then led to paying attention once more, then was shaped by something, which in turn turned into muscle memory, and finally just clicked.

**raw model gen:**
> Paying attention led to paying attention, which then became drawn to it, then pushed away by the other thing, and finally struck a chord, which became shaped by experience, then paying attention again, and finally just clicked into place again.

**repaired model gen:**
> Paying attention led to paying attention, which then became drawn to it, then pushed away by the other thing, and finally struck a chord, which became shaped by experience, then paying attention again, and finally just clicked into place again.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        88/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 16/24 — [cas_to_english / meta_logic_relation]

**source CAS:** `PartitionOf(Noetics, NoeticCluster{^5}, NoeticCluster{^1, ^2, ^3, ^4, ^6, ^7, ^8}, NoeticCluster{^0, ^9})`

**target reply:**
> The ten ways of thinking partition into three groups: the first group contains who one is (shaped by experience), the second group contains paying attention, drawn to it, an aversion, something that struck a chord, unpacking an idea, practice makes perfect, that reminds me, and it just clicked, and the third group contains a thought and popped into mind.

**raw model gen:**
> The ten ways of thinking partition into two groups: the first group contains paying attention, drawn to it, an aversion, struck a chord, who one is, breaking it down, practice makes perfect, and one thing leads to another; the second group contains paying attention, an aversion, struck a chord, who one is, breaking it down, practice makes perfect, perfect, and it just clicked.

**repaired model gen:**
> The ten ways of thinking partition into two groups: the first group contains paying attention, drawn to it, an aversion, struck a chord, who one is, breaking it down, practice makes perfect, and one thing leads to another; the second group contains paying attention, an aversion, struck a chord, who one is, breaking it down, practice makes perfect, perfect, and it just clicked.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `False`
- quality_failures:  `['adjacent_duplicate_count=1']`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        146/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 17/24 — [cas_to_english / meta_logic_relation]

**source CAS:** `Product(NoeticCluster{^5, ^9}, NoeticCluster{^0, ^1, ^9})`

**target reply:**
> The product of two clusters: the first uniting who one is and it just clicked; the second uniting a thought, paying attention, and it just clicked. This pairing describes a meta-logical relation between these two groups of cognitive states.

**raw model gen:**
> The product of two clusters: the first contains a thought and who one is; the second contains paying attention, an aversion, who one is, and it just clicked. Together, they form a single cluster of three: paying attention, an aversion, something that popped into mind.

**repaired model gen:**
> The product of two clusters: the first contains a thought and who one is; the second contains paying attention, an aversion, who one is, and it just clicked. Together, they form a single cluster of three: paying attention, an aversion, something that popped into mind.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        104/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 18/24 — [cas_to_english / meta_logic_relation]

**source CAS:** `CoverOf(Noetics, NoeticCluster{^1, ^2, ^3, ^4, ^5, ^6, ^7}, NoeticCluster{^0, ^8, ^9})`

**target reply:**
> The full set of ten ways of thinking—something on your mind, paying attention, drawn to something, an aversion, struck a chord, who one is, breaking it down, practice makes perfect, triggered a memory, and popped into mind—is covered by two clusters: the first cluster contains paying attention, drawn to something, an aversion, struck a chord, who one is, breaking it down, and practice makes perfect; the second cluster contains something on your mind, triggered a memory, and popped into mind.

**raw model gen:**
> The ten ways of thinking partition into two groups: the first group contains a thought, paying attention, drawn to it, an aversion, struck a chord, who one is, breaking it down, practice makes perfect, and that reminds me; the second group contains a thought, paying attention, drawn to it, an aversion, and popped into mind. Together, these three clusters account for all ten ways 

**repaired model gen:**
> The ten ways of thinking are covered by two groups: the first group contains a thought, paying attention, drawn to it, an aversion, struck a chord, who one is, breaking it down, practice makes perfect, and that reminds me; the second group contains a thought, paying attention, drawn to it, an aversion, and popped into mind. Together, these three clusters account for all ten ways 

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `True`
- quality_passed:    `False`
- quality_failures:  `['truncated_at_max_tokens']`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        150/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 19/24 — [cas_to_english / rpm_chain]

**source CAS:** `let stageA0_3_0234 = ^0^P; let stageD3_3_0234 = ^9^P_{F3}; let stageW3_3_0234 = ^9^C_{F3}; let stageP3_3_0234 = ^9^E_{F3}; stageW3_3_0234 -> stageP3_3_0234`

**target reply:**
> Let stageA0_3_0234 name a foundational thought, stageD3_3_0234 name something that popped into mind in the evaluative arena driven by a need for vitality, and stageW3_3_0234 name cognitive thinking driven by a need for vitality. Let stageP3_3_0234 name evaluative judgment driven by a need for vitality. stageW3_3_0234 then leads to stageP3_3_0234.

**raw model gen:**
> Let stageA0_3_0234 name a foundational thought, stageD3_3 name something that speaks to you in the evaluative arena, and let stageW3_3 name a cognitive impression in the wisdom arena, and let stageP3_4_0234 name an evaluative judgment in the wisdom arena. stageD3_3_023 leads to stageW3_3.

**repaired model gen:**
> Let stageA0_3_0234 name a foundational thought, stageD3_3_0234 name something that speaks to you in the evaluative arena, and let stageW3_3_0234 name a cognitive impression in the wisdom arena, and let stageP3_3_0234 name an evaluative judgment in the wisdom arena. stageW3_3_0234 leads to stageP3_3_0234.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=3
- gen tokens:        117/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 20/24 — [cas_to_english / rpm_chain]

**source CAS:** `let stageA0_2_0277 = ^0^P; let stageD2_2_0277 = ^5^P_{F2}; let stageW2_2_0277 = ^5^C_{F2}; let stageP2_2_0277 = ^5^E_{F2}; stageW2_2_0277 -> stageP2_2_0277`

**target reply:**
> Let stageA0_2_0277 name a foundational thought, stageD2_2_0277 name who one is shaped by wisdom and insight, stageW2_2_0277 name cognitive thinking shaped by wisdom and insight, and stageP2_2_0277 name evaluative judgment shaped by wisdom and insight. stageW2_2_0277 then leads to stageP2_2_0277.

**raw model gen:**
> Let stageA0_2_0277 name a foundational thought, stageD2_27 name something on your mind in the wisdom realm, stageW2_2_027 name a positive draw in the wisdom realm. stageA0_27 leads to stageD2_2_027.

**repaired model gen:**
> Let stageA0_2_0277 name a foundational thought, stageD2_2_0277 name something on your mind in the wisdom realm, stageW2_2_0277 name a positive draw in the wisdom realm. stageW2_2_0277 leads to stageP2_2_0277.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=3
- gen tokens:        84/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 21/24 — [cas_to_english / rpm_chain]

**source CAS:** `let stageA0_2_0287 = ^0^P; let stageD2_2_0287 = ^2^P_{F2}; let stageW2_2_0287 = ^2^C_{F2}; let stageP2_2_0287 = ^2^E_{F2}; stageA0_2_0287 -> stageD2_2_0287`

**target reply:**
> Let stageA0_2_0287 name a foundational thought, stageD2_2_0287 name something drawn toward wisdom and insight in the evaluative arena, stageW2_2_0287 name cognitive attention toward wisdom and insight, and stageP2_2_0287 name evaluative judgment toward wisdom and insight. stageA0_2_0287 leads to stageD2_2_0287.

**raw model gen:**
> Let stageA0_2_0287 name a foundational thought, stageD2_2_027 name something on your mind in the wisdom realm, stageW2_2_0278 name a positive draw in the cognitive arena with wisdom and insight, and stageP2_2_028 name a positive draw toward wisdom and insight as the driving need. stageD2_2_02878 leads to stageW2_2_028.

**repaired model gen:**
> Let stageA0_2_0287 name a foundational thought, stageD2_2_0287 name something on your mind in the wisdom realm, stageW2_2_0287 name a positive draw in the cognitive arena with wisdom and insight, and stageP2_2_0287 name a positive draw toward wisdom and insight as the driving need. stageA0_2_0287 leads to stageD2_2_0287.

**structural metrics (auto-filled):**

- routing:           `cas_to_english` (compiled=True)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=3
- gen tokens:        138/150

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 22/24 — [invalid_to_explanation / rpm]

**source CAS:** `let stageA_3_8562 = ^3^E_{F3}; let stageB_3_8562 = ^3^P_{F3}; stageA_3_8562 -> stageB_3_8562`

**target reply:**
> The expression tries to move from one abstract category to a different, incompatible one. These two categories have a strict rule: the first cannot transition into the second. No matter how the connection is set up, that particular pairing is forbidden, so the whole expression breaks down at the point where the transition is attempted.

**raw model gen:**
> The expression tries to connect two ideas where the second cannot logically follow from the first. The starting point belongs to one abstract category, and the destination belongs to a different abstract category that the rules of this system do not allow that particular category to lead into. A careful reader would notice that the two categories are simply not allowed in this direction of this system recognizes as forbidden and this starting category.

**repaired model gen:**
> The expression tries to connect two ideas where the second cannot logically follow from the first. The starting point belongs to one abstract category, and the destination belongs to a different abstract category that the rules of this system do not allow that particular category to lead into. A careful reader would notice that the two categories are simply not allowed in this direction of this system recognizes as forbidden and this starting category.

**structural metrics (auto-filled):**

- routing:           `invalid_to_explanation` (compiled=False)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        158/250

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 23/24 — [invalid_to_explanation / rpm]

**source CAS:** `stageD1_1_5813 -> stageW1_1_5813`

**target reply:**
> The expression tries to draw a connection from one named stage to another, but the starting stage has never been defined anywhere in the system. Because it doesn't exist, the connection can't be built — you can't link from something the system has no record of.

**raw model gen:**
> The expression tries to draw a connection from one named stage to another, but the starting stage has never been defined anywhere in the system. Because it doesn't exist, the connection can't be made — you can't link from something that hasn't been established.

**repaired model gen:**
> The expression tries to draw a connection from one named stage to another, but the starting stage has never been defined anywhere in the system. Because it doesn't exist, the connection can't be made — you can't link from something that hasn't been established.

**structural metrics (auto-filled):**

- routing:           `invalid_to_explanation` (compiled=False)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        101/250

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---

## Record 24/24 — [invalid_to_explanation / rpm]

**source CAS:** `let stageA0_3_4762 = ^0^P; stageA0_3_4762 -> stageW_3_4762`

**target reply:**
> The expression sets up a starting point and then tries to hand off to a destination that was never defined anywhere. Because that destination has no definition, the system has no idea what it refers to and cannot complete the connection.

**raw model gen:**
> The expression sets up a starting point and then tries to hand off to a destination that was never defined anywhere. The destination name simply doesn't exist in the system, so the connection cannot be completed. A careful reader would notice that only one side of the intended link was ever given a definition.

**repaired model gen:**
> The expression sets up a starting point and then tries to hand off to a destination that was never defined anywhere. The destination name simply doesn't exist in the system, so the connection cannot be completed. A careful reader would notice that only one side of the intended link was ever given a definition.

**structural metrics (auto-filled):**

- routing:           `invalid_to_explanation` (compiled=False)
- truncated:         `False`
- quality_passed:    `True`
- quality_failures:  `none`
- Ω recovery:        pre 0/0, post 0/0
- coef recovery:     pre 0/0, post 0/0
- repair subs:       Ω=0 coef=0 var=0
- gen tokens:        115/250

**human grading (fill in):**

| axis | grade | one-line note |
|---|---|---|
| correct_task | _____ | |
| cas_meaning | _____ | |
| natural_language | _____ | |
| completion | _____ | |
| useful_ending | _____ | |

---
