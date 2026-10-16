# R1-RT design, appendix K: the runtime abstains on a hosted answer, and the repair cannot be reached

**Date:** 2026-10-16
**Status:** R1-RT's **third requirement cannot be met by a client operation**. This is a measurement,
and it is the third time the design has been corrected by one. The first two were repairable. This one
is a governance boundary, and crossing it is not an engineering decision.

## 1. What was measured

One hosted tick, the brain answering across the boundary, with the verifier's receipt printed in full:

```
the brain answered       : FIRST_UNSUPPORTED_LEG_1
the runtime decoded      : FIRST_UNSUPPORTED_LEG_1

the verifier's receipt:
  disposition        ABSTAIN
  semantic_outcome   UNKNOWN
  reason_codes       ('EXPERIMENTAL_OPERATION_NOT_AUTHORITY_ADMITTED',)
  repair_required    False

was a repair frame opened : False
was a repair subgoal set  : False
repair outcome            : None
operating region          : ACTIVE
audit_only                : True
```

The answer arrives, and the runtime's own decoder reads it correctly. **And then the runtime declines
to publish it.**

## 2. Why, exactly

`verifier.py:304-340` is a chain of tests, and the order is what decides everything:

| test | result |
|---|---|
| region is CUTOFF | ABSTAIN, `ZERO_FLOW` |
| region is BREAKDOWN | QUARANTINE, `BREAKDOWN_REGION` |
| **the operation is not `CANONICAL_ADMITTED`** | **ABSTAIN, `EXPERIMENTAL_OPERATION_NOT_AUTHORITY_ADMITTED`** |
| no semantic evidence | ABSTAIN, `SEMANTIC_EVIDENCE_MISSING` |
| content matches the expected one | ACCEPT, `EXACT_SEMANTIC_MATCH` |
| content matches the opposite one | REPAIR, `EXACT_OPPOSITE_MATCH` |
| anything else | REPAIR, `SEMANTIC_OFF_AXIS` |

The client's operation is `EXPERIMENTAL_OPEN_SEMANTICS`, so the third test fires **before the semantic
comparison is reached at all**. Both REPAIR outcomes live *below* that test.

So a client operation:

- can never reach **ACCEPT**, and
- can never reach **REPAIR**, and therefore
- **can never drive a nested repair.**

`audit_only: True` in the receipt is the runtime saying the same thing in one word: this is being
looked at, not published.

## 3. The runtime is doing the right thing

This is worth stating plainly, because it would be easy to write this appendix as though the runtime
had failed. It has not.

HELM's runtime is refusing to give **authority** to an operation that is not authority-admitted.
That is the governance design working. A runtime that let an experimental operation's output be
published as a verified effect would be a worse runtime, not a better one. The design asked for
something the runtime's own rules forbid, and the runtime said no.

The honest conclusion is therefore not "the runtime is broken". It is: **the design's assumption that
the brain could occupy the operation slot and be believed was wrong.**

## 4. What reaching the repair would require

Two ways exist. Neither is an engineering choice.

**Make the operation canonical-admitted.** The `state.py` entry this work added declares the client
`EXPERIMENTAL_OPEN_SEMANTICS`. Changing that entry to `CANONICAL_ADMITTED` would put the brain's
operation in the same authority class as the frozen `^6`. It would also mean declaring that this
brain's output carries the authority of a canonical operation — which is a **claim about authority**,
not a configuration detail. It is the owner's to make or refuse, and it would need its own seal.
(`register_operation` separately refuses a *registration* admitted as canonical, so this is not a
one-line change even for someone willing to make the claim.)

**Find another route into the repair machinery.** The runtime's repair frames are reachable from other
paths — `repair.py` guards one at line 69, and the network and teaching coordinators carry repair
receipts. Whether any of them can be reached by a hosted answer, and what that would mean for the
claim, has not been investigated and is not claimed here.

## 5. What this does and does not change

**It does not touch anything already proved.**

| part | still true? |
|---|---|
| the input rule replaced and proved on 323,851 cases | **yes** |
| the patch, measured on the real path | **yes** |
| the client operation, built and measured | **yes** |
| the process boundary, 0.061 ms per tick, never held torch | **yes** |
| the brain answering a real runtime tick, 3 of 3 | **yes** |
| surviving a restart through the store | **yes** |

**What it removes** is R1-RT's third requirement as the design wrote it: a real nested repair, inside
HELM, driven by the brain. **What it also removes**, and this is easy to miss, is the word "answers"
in R1-RT's target sentence. The runtime produces the brain's answers and then declines to publish
them. So the deliverable is not "the same answers inside HELM". It is **"the same answers computed
inside HELM's runtime, decoded by its own decoder, and withheld by its own verifier."** That is a
weaker and more awkward claim, and it is the true one.

## 6. What should happen next

This is a decision for the owner, and it is the first one since the gate that is genuinely a
judgement rather than a cost.

1. **Accept the weaker claim.** R1-RT reports that the brain computed its answers inside HELM's
   runtime and that HELM's verifier correctly declined to give them authority. Wave 1 stays the
   project's licensed result. Cost: nothing.
2. **Authorise the authority change.** Declare the client operation canonical-admitted, re-seal, and
   run. This makes the brain's output publishable and would let a nested repair be driven. It is a
   claim about authority and it should not be made casually.
3. **Investigate another route into the repair machinery first**, before deciding between the above,
   so the decision is made with the alternatives known.

The council's recommendation is **1 or 3, not 2** — and specifically **3 then 1**, because the
authority change is the kind of claim that should be reached only after the cheaper options are shown
to be closed.

## 7. The alternative route is closed, so the choice is now a real one

Section 4 named two ways to reach the repair machinery and left the second one — "find another route
into the repair machinery" — as something to investigate. **It has been investigated. It is closed,
and the reason is one line.**

Every route into a repair frame passes through `repair.open_repair`, and its first statement is:

```python
if receipt.disposition is not VerifierDisposition.REPAIR or not receipt.repair_required:
    raise RepairError("only an independent REPAIR receipt can open a repair frame")
```

So opening a repair frame **requires** a REPAIR receipt. A REPAIR receipt is produced only by the
verifier's semantic comparison, which section 2 showed is unreachable for a non-canonical operation.
The other thirteen call sites of `repair_frame_from_dict` across `runtime.py`,
`network_coordinator.py` and `persistence.py` either *read back* a frame that was already opened or
sit inside the same `open_repair` path; none of them opens a frame by another means.

**Therefore there is exactly one door, and it needs a REPAIR receipt.** The two ways named in section
4 were never two: the second one leads back through the first.

That collapses the decision to two real options, and it is worth being exact about what they are:

- **Accept the weaker claim.** R1-RT reports what it honestly earned: the answers computed inside
  HELM's runtime, decoded by its own decoder, and withheld by its own verifier. Wave 1 remains the
  project's licensed result. Nothing further is spent, and no new claim is made.
- **Make the operation authority-admitted.** This declares that the brain's output carries canonical
  authority. It would let a REPAIR appear and a nested repair be driven. It is a claim about authority
  rather than a configuration change, it needs its own seal, and it changes what the project asserts.

There is no third option, and the council recommends the first. The authority change purchases a
nested repair by asserting something about the brain that this work has not shown — the brain's
answers were correct on the cases tried, and correctness on cases tried is not authority.

## 8. Defects found while measuring

None in the tools. One in the reading, worth recording because it is the same failure the directive
names: the design's assumption was written down and built on for several rounds without anyone asking
what the runtime's **verifier** would do with the result. Appendix G measured that the runtime accepts
and calls a client operation. It did not ask whether the runtime would believe it. Those are different
questions, and only the first was asked.
