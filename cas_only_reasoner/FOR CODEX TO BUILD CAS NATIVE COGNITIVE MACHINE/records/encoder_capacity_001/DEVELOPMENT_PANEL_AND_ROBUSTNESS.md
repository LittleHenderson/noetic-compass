# DEVELOPMENT_PANEL_AND_ROBUSTNESS — the held-out panel is unmeasurable from this receipt, and the constraint layer is structure-independent

**Round 38. One long-open question closed, one new robustness property established.**
**$0.00. Pure standard library plus the project's pure modules. No torch, no GPU, no model, no
training, no new run.**

Scripts: `records/encoder_capacity_001/probe_development_source.py` (`development_source_probe.txt`).
Tests: `tests/test_answer_constraints.py`, now **21 tests**, all passing.

---

## 1. The development panel cannot be scored from this receipt — definitively

The `development` panel is 59 questions with **zero overlap** with the exposed course, and the machine
scores **0 of 59 at every cursor** (0/59 at cursor 0 and 0/59 at cursor 160). Every round since 24 has
had to record it as unmeasured. **It is now closed as unmeasurable from this receipt, with the reason
stated exactly.**

```
frozen course registry size: 564
development record in the registry?  False
--- attempting a development packet ---
model_packet FAILED: ValueError: TYPED_COURSE_RECORD_UNKNOWN
```

`collected/results/artifacts/protocol_material.json` carries a `development` object, but it holds
**digests, not packets**:

```
'admission': list[59] of dict with
    'packet_sha256', 'source_digest', 'slot_plan_digest', 'frame_digest',
    'sequence_digest', 'topology', 'kind', 'record_id', 'slots', 'token_count'
```

**No `source` object, no `query`, no packets.** Without the packet there is no public snapshot, and
`checker.derive_target` needs one. The targets are therefore not derivable by any means available
here, and no amount of analysis in this record can produce them. **That panel stays unmeasured, and
now it is known why rather than merely noted.**

## 2. But the probe established what the panel *is*, and it explains the 0 of 59

```
'counts':  bank_worlds 64, families 6, packets 59, parts 6, reach 53, worlds_per_packet 65
'families': 6 families of 10 records, each with
    'split': 'development'
    'declarations_authority': 'NEW_CALLER_AUTHORED_DEVELOPMENT_FACTS_NOT_WORLD_TRUTH'
    'stats': nodes 10, relations 7, wholes 3, max_depth 3,
             has_nested_whole True, has_shared_part False, max_direct_parts 3
```

**The development panel is only two kinds — 6 `parts` and 53 `reach` — over worlds with TEN nodes,
depth 3 and nested wholes, declared by a caller rather than taken from world truth.** The exposed
course is four-node worlds.

**That is a distribution shift, and it lands on exactly the two kinds where the machine looks
strongest on the exposed course:**

| kind | exposed course, recorded | development panel |
|---|---|---|
| `reach` | **76.4798%** (642 questions) | **0 of 53** |
| `parts` | **29.2453%** unconstrained, **80.8176%** with the constraint layer | **0 of 6** |

**So the machine's apparent strength on `reach` and `parts` does not survive a change of world size.**
That is consistent with everything the record has measured about it: it answers from memorised layout,
not from structure, which is why `edge_account` reads its bits at **54.6353% balanced** and why six
runs converge on the same `W36`. **A readout that memorises layout scores zero on a layout it has
never seen.**

## 3. The constraint layer is structure-independent — five new tests

The layer is designed to read **declarations out of the test packet** rather than memorised layout, so
it *should* be immune to that shift. That is a claim about the code, so it is now tested rather than
asserted. Five tests, added this round, all passing on the first run:

| test | what it establishes |
|---|---|
| `test_declared_shape_does_not_assume_four_nodes` | a ten-node world reports `nodes 10` and the right cardinalities |
| `test_cardinality_and_self_links_hold_on_a_ten_node_world` | exactly 4 PRESENT out of 100 edge slots, and **no self-link** — the rules are not written for a 4×4 grid |
| `test_a_whole_absent_from_the_focus_nodes_does_not_crash` | a `whole` not among the focus's nodes yields cardinality 0 and leaves the selection intact |
| `test_the_joint_decoder_uses_POSITION_and_this_pins_that_assumption` | the positional node correspondence, pinned deliberately |
| `test_a_candidate_with_fewer_nodes_than_the_focus_is_skipped_not_crashed` | a short candidate is skipped, not crashed on |

**No rule in `cncm/answer_constraints.py` depends on the four-node layout it was mined from.** The
cardinalities come from `len(focus["contains"])` and `len(focus["declarations"]["participants"])`; the
self-link rule compares two coordinates; the joint decoder enumerates the bank. **The layer would
apply unchanged to the development panel's ten-node worlds** — which is the one thing about that panel
that can be established without its packets.

## 4. The one assumption the packet does not guarantee, now pinned

`_one_world_joint` maps a focus node to a candidate world's node **by position**, because the only
correspondence the packet offers is the alias namespace and aliases are positional (`N0`..`N9`). When
the focus and a candidate have different node counts, positions line up only as far as the shorter one
reaches, and a shorter candidate is skipped.

**That is an assumption, not a fact.** It holds on the development panel by uniformity — every world
there has ten nodes — and on the exposed course by uniformity at four. **It is pinned by a test that
asserts the positional behaviour explicitly, so that changing it becomes a visible act rather than a
silent one.** This is the only such assumption in the module, and it is named here rather than left
for someone to find.

## 5. What this round is worth

- **A question open since round 24 is closed with a reason**: the development panel cannot be scored
  from this receipt, because the receipt carries its digests and not its packets.
- **The panel's composition is now known**: 6 `parts` + 53 `reach`, ten-node worlds, caller-authored
  declarations — and the machine's 0 of 59 is a distribution shift on the two kinds it otherwise
  handles best.
- **A robustness property is established by test, not assertion**: the constraint layer does not
  depend on the layout it was derived from, so it is the one component here that would survive that
  shift.

## 6. Claim status

- **REAL:** §1. The registry has 564 records, the development record is absent, `model_packet` raises
  `TYPED_COURSE_RECORD_UNKNOWN`, and `protocol_material["development"]` contains digests only. Artifact:
  `development_source_probe.txt`.
- **REAL:** §2's composition and statistics, read from `protocol_material["development"]`.
- **REAL:** §3's five tests, passing. `tests/test_answer_constraints.py`, 21 tests.
- **NOT LICENSED:** that the constraint layer would score well on the development panel. Structure
  independence is necessary and is now tested; it is not sufficient, because that panel's scores would
  also depend on the per-slot readout underneath, and that readout is what fails there. **No claim is
  made about a development score.**
- **WITHDRAWN:** nothing this round.
- **OPEN, and unchanged:** the wiring decision from round 37 — whether the constraint layer is
  connected to a run's decision step, which changes the decision contract and its digest.
