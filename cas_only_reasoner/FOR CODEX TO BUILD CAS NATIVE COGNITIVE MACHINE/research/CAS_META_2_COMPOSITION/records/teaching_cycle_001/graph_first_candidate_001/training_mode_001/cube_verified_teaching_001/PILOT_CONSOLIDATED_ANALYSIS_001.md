# PILOT_CONSOLIDATED_ANALYSIS_001 — the answer-selection readout

Read-only analysis of the checked-component pilot, 2026-09-10. One pass, five
items, as directed. Machine-readable companion: `PILOT_AUDIT_001.json`, produced
by `tools/graph6_pilot_audit.py` (no torch, no model, no provider, no
reservation, no training). Attempt 007 is preserved exactly as delivered: nothing
below rewrites it, and no missing telemetry is backfilled.

---

## 1. The probe's answer distribution, verified — and one row of the reconstruction corrected

From the pinned scene and the declared exclusion rule, computed with the
**reference checker** (`cube_node.answer_cases` → `reference.direct_parts`,
`reference.shared_parts`) rather than by reading:

| operation | questions | expected answers, by category |
| --- | --- | --- |
| `LIST_PARTS` | 5 | **3 empty lists**, 2 non-empty |
| `FIND_SHARED_PART` | 14 | **9 `none`**, 5 shared part |
| `REACHED_VIA` | 25 | **21 `absent`**, 3 `direct`, 1 `via:Wheel` |

- 44 probe questions, from a 51-question catalog, with the 7 distinct taught
  questions excluded — the declared rule reproduces exactly.
- **Absence answers: 33 of 44 = 75.0 %** (not 38 of 44).
- Only 2 of the 44 questions do not offer an absence option at all.
- Taught questions, for contrast: 2 of 8 exposures are absence-category (25 %);
  the probe is 75 %.

**The corrected row.** `FIND_SHARED_PART` is 9 `none`, not 14. The rule is:

```
reference.shared_parts: direct_parts(a) ∩ direct_parts(b),
                        plus a itself if a is a direct constituent of b,
                        plus b itself if b is a direct constituent of a
```

The second and third clauses are why `Bicycle/Frame` answers `Frame`,
`Bicycle/Wheel` answers `Wheel`, `Cart/Platform` answers `Platform` and
`Rim/Wheel` answers `Rim`. Reading only the intersection clause yields
`none` for all fourteen, which is how the 14/0 row and the 86.36 % figure arise.
The substantive claim survives and is arithmetic: **the panel is 75 % absence, and
it is an absence panel.** Only its degree changes.

**Constant-answer baselines for this exact panel**, computed with the
learner-visible option order:

| rule | score |
| --- | --- |
| always absence, else first offered (77.3 %) | **34 / 44** |
| always absence, else last offered | 34 / 44 |
| always a non-absence answer | 7 / 44 |
| always slot 0 / slot 1 / slot 2 | 17 / 14 / 13 |
| uniform random among three choices | 14.67 / 44 |
| correct-answer slot histogram | 17 / 14 / 13 (near-uniform) |

So a rule that never looks at the graph scores **34 of 44**, and the learners
scored **9 of 44** (checked) and **7 of 44** (control). No aggregate on this panel
can be read as evidence of reasoning, in either direction.

## 2. Label alignment is not leakage — and a real target dependence was found

**Kept as it is.** `all_slots_carry_the_teacher_answer` asserts
`encoded_options[encoded_correct_index] == the teacher answer`. That is label
alignment: if it failed, the loss could reward the wrong option. It is not
evidence of leakage, and it stays.

**The old dependency is still active in the delivered compilation**, and this is
its concrete path:

```
private teacher target
    expected_choice_id  and  witness.kind
        -> record["cube_verified_teaching"] inside `core`      (verified_training.py)
        -> record_id = digest(canonical(core))
        -> adapter.public_records: seed = digests(record_id + ':' + arm)[:8]
        -> random.Random(seed).shuffle(ordered)
        -> the ORDER of the three option tags the learner sees
```

Measured, holding the graph, the question and the candidate answers fixed and
swapping only the private target for a different offered choice:

| what was compared | result over the 8 taught records |
| --- | --- |
| learner-visible problem text | identical 8 / 8 |
| record id | **changed 8 / 8** |
| learner-visible option order | **changed 4 / 8** |
| learner-visible observations | **changed 4 / 8** |

The same test on the probe records — the `record_from_question` path — changed
nothing: id, prompt and option order identical in every case. So the dependence
is specific to the taught-record builder.

**What it means, and what it does not.** It is not an answer leak: all three
options remain present and unmarked, and the learner cannot compute the digest.
It is a hygiene failure against the adapter's own documented invariant ("the
private target is NEVER used to order, position, mark, or specially encode a
choice") and against the owner's stated intent that the cube compiler not inherit
that behaviour. The private target currently determines *which slot* holds the
answer for each question.

**Fixed for new compilations only**, as directed: `verified_training.public_projection`
strips `expected_choice_id` and `witness_kind` from the id basis, and the private
fields are still carried in the record, outside it. Re-measured after the fix:
id, visible option order and problem text identical **8 / 8** when the target is
swapped, with the private fields intact. The delivered Attempt 007 records keep
the ids they were measured with; `check_report.json` was regenerated (its
predecessor preserved as `check_report_rev5.json`) and still reads
`TEACHING_DATA_READY_NEURAL_UNTESTED`. A test now pins the invariant.

## 3. Three different observations, kept apart

| observation | what it is | source identity | updates | checkpoints |
| --- | --- | --- | --- | --- |
| **Attempt 007** | the paid measurement, AWS `i-0a86c9e3a0826ab60`, g7.2xlarge A10G | package `candidate_package_006`, archive `e33a6497…`, source `b2ff5a4b` | **128** (64 + 64) | `checkpoint_checked_component_teaching.pt` `e4b41c74e423636faeff006c78622bafeba5447ca859872cc44d17c5f28025b0`; `checkpoint_final_answer_only.pt` `67f18a4cb93c1db15a7d702a3b32e4757eb9f94b8f2ed14ac0a1ce17a1c59142` |
| **SMOKE_RUN_001** | local instrumentation check, RTX 4070, torch 2.11.0+cu128 | package `candidate_package_006` | **6** (3 + 3) | throwaway `smoke_checkpoint_*.pt`, written that run |
| **SMOKE_RUN_002** | local instrumentation check after the reporting fixes | package `candidate_package_007` | **6** (3 + 3) | throwaway `smoke_checkpoint_*.pt`, written that run |
| **the zero-update reread** | reads the retained Attempt 007 weights, **not taken** | — | **0** | would read the two hashes above |

Both smoke runs trained from fresh initial weights: they are newly trained
mini-runs, **not** rereads of the retained weights, and they cannot recover
Attempt 007's missing per-question probe rows or its missing scores. They
establish that the corrected instrumentation records those fields. The smoke tool
now records its own package archive hash, packaged source sha, worker hash, member
count, checkpoint hashes and update counts, so a future smoke report identifies
itself instead of needing reconstruction.

## 4. What the retained per-question telemetry shows

Attempt 007 did deliver **per-step expected and selected answers for all 128
updates**, with operation, phase, block and per-step parameter digests. From them:

**Checked-component teaching — 30 of 64 steps correct**, first half 14, second
half 16 (no improvement trend). Its 64 steps are 8 records × 8 blocks.

| taught question | expected | correct | what it selected |
| --- | --- | --- | --- |
| `FIND_SHARED_PART` | `Wheel` | 7/8 | `Wheel` ×7, `none` ×1 |
| `LIST_PARTS` | `["Frame","Wheel"]` | 7/8 | the right list ×7 |
| `REACHED_VIA` | `absent` | **0/8** | `via:Wheel` ×6, `direct` ×2 |
| `REACHED_VIA` | `absent` | **1/8** | `via:Wheel` ×5, `direct` ×2, `absent` ×1 |
| `REACHED_VIA` | `direct` | 2/8 | `via:Wheel` ×5, `direct` ×2, `absent` ×1 |
| `REACHED_VIA` | `direct` | 3/8 | `absent` ×5, `direct` ×3 |
| `REACHED_VIA` | `via:Wheel` | 4/8 | `via:Wheel` ×4, `absent` ×2, `direct` ×2 |
| `REACHED_VIA` | `via:Wheel` | 6/8 | `via:Wheel` ×6, `absent` ×1, `direct` ×1 |

Summed over the 16 presentations whose answer is `absent`: it answered `absent`
**once**, `direct` 4 times, `via:` 11 times.

**Final-answer-only — 63 of 64 steps correct**, first half 31, second half 32. Its
three practised questions are all positive-answer (`Wheel`, `["Frame","Wheel"]`,
`via:Wheel`) and it learned them: 21/21, 21/22, 21/21. It never practises an
absence-answer question at all.

**Paired comparison where it legitimately exists:** only the 3 records both
conditions practised. Both were correct on all 3 at last exposure — 0 discordant
pairs, so no difference is measurable there either. The 5 component questions
have no control-condition telemetry because the control never practises them.

**Integrity:** the per-step parameter digests form a proper chain — 64 links,
64 distinct post-update identities, each step's `checkpoint_after` equal to the
next step's `checkpoint_before`, in both conditions.

**Explicitly missing from this delivery, not backfilled:** the per-question probe
rows (the report kept only the after-training per-operation breakdown), the
per-question selections behind the probe's 9/44 and 7/44, the before-training
per-operation breakdown, and every score and loss (no scorer was injected; the
learner exposed no scores method, so 64 of 64 read "unavailable").

## 5. The measurement that needs execution — packaged, not run

`BOUNDED_DIAGNOSTIC_001.md` specifies one bounded readout against the two retained
checkpoints with **zero optimizer steps**: the 44 probe questions per question,
the taught questions on the same instrument, the already-prepared contrast set
(original, renamed, reordered, rewired, with option-length readings), and an
absence-inventory control. Its purpose is the probe's per-question selections —
the paired comparison this delivery lost — and a direct test of the hypothesis
below. It is not authorised, reserves nothing, and launches nothing.

## Statistical framing, corrected

- The paired comparison the directive asks for is **McNemar over discordant
  pairs**, and it cannot be computed from this delivery: the per-question probe
  rows are not in it. The Fisher figures I reported earlier used marginal totals
  only, which do not contain the pairing; they should be read as a weak check, not
  as the comparison.
- The 1/3 baseline assumes a uniform three-choice chooser; it does not require the
  correct slot to be uniformly placed. A learner with a fixed slot or a fixed
  answer-meaning preference needs a baseline computed from this exact panel — that
  is the table in section 1, and it is the comparison that matters here.
- The binomial figures against 1/3 compare the observed count with a specified
  independent-trial model. They do not identify a mechanism, and these 44
  questions are one graph's questions, not 44 samples of graph families.

## The one conclusion

**Measured.** The probe is a 75 %-absence panel on which a rule that never looks
at the graph scores 34 of 44. Both learners scored far below that — 9 and 7 of 44
— and below uniform chance. On the taught questions, where the learner's own
selections *are* retained, the checked-component learner answered a positive
reach label (`via:` or `direct`) in **15 of 16** presentations whose answer was
`absent`, and answered `absent` once; the control, which saw only positive-answer
teaching, learned its three questions to 63 of 64 and then scored exactly the
constant "never answer absence" baseline on the probe. The pilot's negative result
stands unchanged, and no advantage for the component allocation is established.

**Hypothesis, not measured.** Both learners carry a **positive-answer
preference**: they select a familiar positive relation even where the supplied
graph requires absence. The probe's composition converts that preference into a
below-baseline score, and the 2-question gap between the conditions (9 against 7)
is consistent with slight attenuation of that preference rather than with better
reasoning. What would settle it is the probe's per-question selections, which the
delivery did not retain.

**Smallest change the evidence justifies.** Two, and both are the owner's to
choose: take the packaged zero-update diagnostic, which reads the retained
checkpoints and returns the per-question selections with no training; or, if the
teaching question is retried at all, stop presenting the positive-answer questions
in isolation and present absence and presence together — because 64 updates on two
absence examples produced one correct absence answer in sixteen. Nothing else is
justified by what is on disk, and no retraining, allowance increase, probe
replacement or curriculum redesign is implied by it.
