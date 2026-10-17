# The 13 points the frozen policy leaves open — decided, with reasons

The owner's instruction: *"this is what I have you for"* — decide these in the files, and **justify
every decision with the intention of making HELM better and CAS unique.**

The frozen policy `647ffc44…` is not edited. These are readings taken where the policy is silent, and
every one of them is written into the package as a comment so it cannot drift. Any of them can be
overruled by a dated owner amendment before the first scored row. Nothing is scored yet.

---

## 1. The fault vocabulary is not listed
**Decided:** the policy's own sentence IS the list. `CLASSIFIED` = {missing, corrupt-digest-mismatch,
stale}. `UNCLASSIFIED` = {authorization, malformed-metadata, conflicting-manifests, timeout, and
anything else}. Unknown never becomes classified.

**Why:** the policy names eight kinds in one sentence. Adding more would be inventing; removing any
would weaken it. Defaulting to unclassified is the safe direction because unclassified is what
triggers the search and the search always ends in a verifier.

## 2. A "classified" claim with missing or contradictory evidence
**Decided:** it stops being classified. With no evidence of *what* broke, it goes to `UNCLASSIFIED`.

**Why:** the whole point of "classified" is that we know what the fault is. A label without the
evidence to support it is a guess wearing a label. This is the same rule as "a name is not a reading".

## 3. A cost declared as zero, negative, or contradictory
**Decided:** treated as **undeclared**, and undeclared is the **asymmetric** class.

**Why:** the 20× threshold is a comparison. Where the numbers cannot be compared, the rule has nothing
to say — and a rule with nothing to say must not become a licence to guess. A blank or nonsense cost
entry should buy you caution, never freedom. Undeclared → asymmetric → search at distance 1 only, then
refuse.

## 4. The nearby-reading operations and the distance measure
**Decided:** six named operations — digit substitution, adjacent transposition, single deletion,
single insertion, case change on an identifier, and an identity no-op — with **distance = number of
atomic edits applied**.

**Why:** a result nobody can replay is not a result. Six named operations with a counted distance is
the smallest set that can be logged, reproduced and argued about. The identity no-op is included so a
"no change needed" outcome is representable rather than invisible.

## 5. How seeds are derived
**Decided:** per-candidate seed = first 8 bytes of
`sha256(item_id, item_version, operator_name, distance, run_seed)`.

**Why:** deterministic, replayable, and it carries no hidden state. Given the same item and run seed,
anyone reproduces the same candidates in the same order — which is what makes the receipt worth
keeping.

## 6. How many candidates per widening step
**Decided:** the step size **equals the distance**. At distance 1 try **1** candidate, at 2 try **2**,
at 4 try **4**, at 8 try **8** — which is **15 in total**, exactly the policy's own "worst case 15
candidates".

**Why:** it makes the policy's 15 fall out arithmetically instead of being an arbitrary cap. The
number in the frozen file and the number in the search cannot drift apart.

## 7. Widen after one refusal, or after the whole step is refused?
**Decided:** after **every candidate at the current distance has been refused**.

**Why:** it is the only reading consistent with 1 + 2 + 4 + 8 = 15. Widening after a single refusal
would spend the 15 in five refusals and never use the wider distances.

## 8. Which anchor when both a fingerprint and a last-verified state exist
**Decided:** prefer the **recorded fingerprint**. Use the last-verified state only when no fingerprint
exists, and **record in the receipt which one was used**.

**Why:** the fingerprint is a fact about the original. The last-verified state is weaker precisely
because it may be the thing being reconstructed — trusting it is circular. When forced to use it, the
receipt must say so, so nobody later mistakes a weaker check for a stronger one.

## 9. The receipt chain
**Decided:** each receipt carries the sha256 of the previous receipt; the first carries 64 zeros.

**Why:** it is checkable in one pass and it makes a deleted or reordered receipt impossible to hide.
The project already uses a zero-digest convention elsewhere, so this adds no new idea.

## 10. "Exact at this distance" is not one of the matrix axes
**Decided:** it is a **derived column**, not a new axis.

**Why:** whether a candidate happened to hit the target exactly is a *property of a row*, not an
independent dimension of the test. Adding it as an axis would change the frozen row count from 768 and
silently invalidate the frozen matrix.

## 11. A classified fault with no eligible spare — does it enter the search?
**Decided:** **no.** Classified with no spare → `UNKNOWN`.

**Why:** the search exists for faults we cannot name. When the fault is named and there is nothing to
check against, there is nothing to search toward — and searching anyway is exactly the plausible-but-
unverified answer the policy forbids.

## 12. C4's "floor" is written as a criterion, not a numbered floor
**Decided:** treat it as the policy says — **report it as its own separate line**, never folded into
another score.

**Why:** the policy is explicit that rates are reported separately "and never combined into one score
that can hide a failed safety gate". Following its own instruction is safer than renumbering it.

## 13. No denominators or pass rates are fixed
**Decided:** the matrix's own counts are the denominators — **768 rows** in total, with each area's
count printed. The four floors are **absolute** (zero wrong exact answers, zero plausible-unverified
answers, nothing labelled as an original, every proposal logged). Rates are **reported**, floors are
**gated**.

**Why:** the floors are the promise. A rate can be improved by getting better at easy rows; a floor
cannot. Gating on the floors and reporting the rates keeps the promise where it belongs.

---

## What this means in plain terms

The test package can now be run. **Nothing has been scored.** The first run is on this laptop, costs
nothing, and produces numbers — it cannot produce a claim, because the pass is a mechanism check, not
evidence about the world.

If any of the thirteen above is wrong, the cost of changing it is one line and a dated note, because
nothing has been scored and no result depends on it yet.
