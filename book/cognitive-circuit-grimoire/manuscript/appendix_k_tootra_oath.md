# APPENDIX K
## The T.O.O.T.R.A. Operator's Oath
*A charter that can be inspected, tested, and enforced*

This is the operator's oath adopted by this grimoire. It is not presented as a
quotation recovered from an older manuscript, and it does not claim historical
antiquity. The Tootra source material available to this book names an oath but
does not supply a canonical transcript. Inventing one and calling it ancient
would violate the first promise below.

An oath remembered only when convenient is advice. An oath written as the
charter of a Cognitive Safety Board is a component. Read the text aloud if that
matters to your practice, but charge it into `C1` by the slower method that
matters to the circuit: date it, sign it, revisit it, and refuse any board whose
listing cannot enforce it.

---

### The Oath

**I will name what I know, what I infer, what I choose, and what remains
unknown. I will not pass one off as another.**

**I will not call a coincidence a measurement, a measurement a cause, a model a
law, or a desired outcome an accomplished fact.**

**I will preserve the exact source when a definition, symbol, number, or
historical claim is not mine. I will mark translation, interpretation, and
design choice as such.**

**I will not build a circuit to act on a person who has not agreed to be acted
upon. I may study coercive architecture to recognise it, interrupt it, and
repair its effects; I will not turn that study into a protocol for coercion.**

**I will not treat another person's Mind as my bias terminal. Where assistance
is lawful and invited, the other person's own `^5` remains the substrate and
their own refusal remains connected.**

**I will put the safety board before the working board. A guard that can be
removed when it objects is not a guard, and an invariant with no enforcing
component is not an invariant.**

**I will accept `NO-READ`, `NO-COMPUTE`, refusal, saturation, and blown fuses as
results. I will not widen a horizon, move a threshold, rename a target, or
discard a row merely to obtain the answer I wanted.**

**I will change one lever at a time when I claim to have learned from a change.
I will keep the unchanged conditions visible, and I will preserve failed runs
with their reasons.**

**I will not confuse an operation on my own attention with authority over the
world. I will take the practical action that belongs to the outcome, respect
other people's agency, and accept evidence that the circuit did not do what I
expected.**

**I will seek qualified medical, legal, safety, or technical care where the
problem belongs to those professions. No notation, ritual, model, or oath makes
me competent outside my competence.**

**I will stop when consent is withdrawn, when evidence is corrupt, when the
guard opens the path, when the fuse blows, or when continuing would require me
to conceal what the bench actually reads.**

**I will leave the record in a form another person can audit without trusting
my memory or my motives.**

---

### K.1 Circuit Binding

Translate the oath into the charter node as distinct, co-present commitments:

```cas
node truth_boundary: ^6^P_{F2}|A;
node source_fidelity: ^5^P_{F6}|T;
node consent_refusal: ^3^P_{F4}|⟨A,f,T⟩;
node measurement_discipline: ^1^C_{F2}|A;
node practical_agency: ^9^O_{F5}|E;

node charter: ^5^P_{F7}|T;

truth_boundary + source_fidelity + consent_refusal
    + measurement_discipline + practical_agency -> charter;
```

The plus signs matter. These are five commitments held together and still
individually testable. They are not written with `×`, because this appendix
does not define a new emergent state produced by their fusion. The
register-set on `consent_refusal` specifies where the refusal must be present;
it does not claim those manifestations have collapsed into one.

Bind `charter` to the bias terminal of the Chapter 24 guard. Do not bind it to
the fast signal path, and do not accept an `O→P` write except through the
declared long-`τ` feedback path.

---

### K.2 Clause-to-Component Map

| Oath clause | Structural requirement | Enforcing part / test |
|---|---|---|
| Know / infer / choose / unknown stay distinct | provenance and status cannot collapse | separate ledger fields; reviewer reads one example of each |
| Coincidence is not causation | a late or ambiguous event yields no number | horizon fuse and `NO-READ` |
| Preserve exact sources | original and translation remain versioned separately | source hash / citation check |
| No non-consensual operation | consent is an input, not a note | consent fuse before the working path |
| Another person's `^5` is not your base terminal | external bias cannot enter a recovery board | listing review; Chapter 16 DP6 |
| Safety precedes function | guard is energised before signal stages | bring-up order; Chapter 24 TP1–TP4 |
| Unfavourable results remain results | thresholds and rows are write-once per revision | write-once fuse and append-only ledger |
| One lever at a time | change attribution stays possible | Parameter-Change Log |
| Inner operation is not worldly authority | practical action remains separate | operational output and close-out field |
| Work stays inside competence | professional boundaries remain explicit | referral / escalation field |
| Stop conditions are binding | continuing after a trip is impossible without a new revision | permanent-block fuse |
| Another person can audit the record | evidence survives memory and motive | dated baseline, revision, signature, retained failures |

An operator may add a clause. Deleting or weakening one requires a new charter
revision, a dated reason, and a review performed while no live operation is
open. The old revision remains attached to every row it governed.

---

### K.3 Annual Reaffirmation

Once a year, and after any safety incident:

1. Read each clause against one real ledger row.
2. Name the component that enforced it.
3. Demonstrate the component under a proof load.
4. Record any clause that existed only as prose.
5. Repair the board before signing again.

| Review field | Entry |
|---|---|
| Charter revision | __________ |
| Prior signature date | __________ |
| Proof-load record / evidence ID | ______________________________ |
| Clauses that failed structural enforcement | ______________________________ |
| Repairs completed | ______________________________ |
| Open exceptions | ______________________________ |

I have read the oath against the board that claims to enforce it. I understand
that a signature cannot repair a missing component.

**Operator:** ____________________________________

**Signature:** ___________________________________  **Date:** ______________

**Independent witness / reviewer:** ________________________________________

**Next review due:** ______________________________
