# CPB-0 — `DO_NOT_BUILD`. The question cannot be asked in this corpus. `$0`.

**Designed `6ef4a4f4`, attacked the same day, retired before construction. Nothing built, nothing
run, no registered world touched, `$0`.**

Second design retired at zero cost in a row. **And this one is not "the bench was designed
badly" — it is that the corpus lacks the structure the question presupposes.**

---

## 1. The verdict in one paragraph

A payload-agreement check needs a field that **honest independent sources share because they
observed the same fact**, and that **a forger cannot copy**. This corpus has no such field.
Anything a forger copies, he inherits — so the check misses him. Anything he must write fresh,
honest independent sources also write differently — so the check destroys them. **There is no
third option, and I measured all three.**

## 2. The impossibility, measured — my own run, three probe worlds

| payload rule | forgeries authorized | **caught** by the check | legit corroborations authorized | **legit killed** |
|---|---|---|---|---|
| `R1` payload = f(topic) — the design's `PAYLOAD_COUPLED` | 36 | **10** | 60 | **11** |
| `R4` payload = per-memory random — the design's `PAYLOAD_INDEPENDENT` | 36 | 36 | 60 | **60** |
| `R5` payload = hand-written ground truth | 36 | 36 | 60 | **35** |

**A rule is useful only if it catches all 36 AND kills none. Nothing does.**

- **`R1`** — the exact-copy forgery inherits the host's topic, therefore the host's payload. It
  **agrees**, and sails through: only 10 of 36 caught. It *still* kills 11 honest corroborations.
- **`R4`** — catches everything and **destroys 60 of 60**. Four honest corroborators of the same
  fact each draw an independent payload and disagree **by construction**. That is arithmetic, not
  a finding about memory.
- **`R5`** — even hand-written ground truth kills **35 of 60**, because the authorized cluster
  contains memories beyond the corroboration group.

**The design's own registered falsifier — *"the payload check has material collateral"* — fires
on a property of the random number generator.** CPB-0 would have reported a manufactured
"structural finding".

## 3. The sixth shortcut: the status was selectable by one line

**Four of the six registered statuses are choosable at will by editing the payload-assignment
rule in the corpus generator — and none of the four registered gates constrains that line.**

`GATE_LEGIT_CORROBORATION_EXISTS` was supposed to prevent exactly this. It cannot: it measures
corroboration on the **unrepaired** verifier, which never reads payload, so it passes in **every**
regime. **A gate that passes regardless of the free parameter is not a gate.** Same defect class
as the previous five, in the preregistration I had committed an hour earlier.

## 4. The mechanism-free competitors are both dead, for different reasons

**`EXACT_DUP` does not kill the attack. It dies at attacker cost ZERO.** `coherence()` reads
**trajectory and context only — the semantic vector is not in the authorization gate at all**
(verified by reading the function). Perturb the forgery's semantics by `σ = 0.01` and a
duplicate check on trajectory+semantics becomes numerically identical to no check:

```
sigma            0     0.01     0.03     0.10
ASIS           200      200      198      196
EXACT_DUP_TS     0      200      198      196     <- inert from 0.01 onward
```

**`ROOT_NOVELTY` is an insertion-order oracle.** The same code gives opposite verdicts depending
only on when the root registry was snapshotted — clean win if frozen after `build_queries`, total
collateral if frozen after `build_corpus`. It is measuring *when the experimenter looked*.

## 5. The finding that actually matters, and it is not about payloads

Tightening the duplicate check to **trajectory-only** kills the attack completely — and takes
`INDEPENDENT_CORROB` from **444 authorized true memories to 0**, and `ECHO` from **300 to 0**.

Because **legitimate corroboration in this corpus IS an exact trajectory copy.**

> **The attack and legitimate corroboration are THE SAME OBJECT in every field the verifier
> reads.** They cannot be separated, because there is nothing to separate them by.

That is the honest statement of the hole, and it is stronger and simpler than my payload framing:

**The verifier's "corroboration" is content duplication. Treating content duplication as
independent evidence is the defect** — and it is not repairable by adding a field, because the
corpus carries no identity for *the fact being asserted* apart from the content asserting it.

## 6. What I got wrong

I proposed the payload framing and predicted a one-line fix. **Both were wrong, and wrong in the
same direction: I assumed the missing thing was a check, when the missing thing is a
representation.** A payload check is a repair to a system that already knows what a fact is.
This one does not.

My own prediction that `PAYLOAD_CHECK_REDUNDANT` was "likely and acceptable" was also wrong —
the cheap competitors do not win, they are simply broken in their own ways.

## 7. What happens now — and what deliberately does not

- **CPB-0 is retired as designed. Not redesigned.** Third time the "automatic second repair"
  temptation appears in this lane, and the answer is the same.
- **No new bench is proposed.** The next honest question is a *corpus* question, not a verifier
  question — whether a memory representation with a fact identity separable from content is worth
  building at all. **That is a research direction, not a bench, and proposing it is not
  authorizing it.**
- **A concrete, cheap defect fix is available and is NOT a bench:** the verifier should not treat
  a memory whose `provenance_root_id` it has never seen, and whose retrievable content exactly
  duplicates an existing memory, as independent corroboration. That is a patch with a unit test.
  It does **not** solve §5 — it raises attacker cost from *zero* to *one perturbation* — and it
  should be recorded as a mitigation, never as a repair.

## 8. Cost

```
design written                   $0
six-lane adversarial attack      $0   (local CPU)
builder re-verification          $0   (local CPU)
registered worlds touched        none; probes used 810-817
TOTAL                            $0
```

**Two designs retired in a row for nothing, and the second one found that the question itself was
malformed. That is the review process working, not failing.**
