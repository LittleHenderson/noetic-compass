# RESULT — CAS involution relational-structure test on 20B (2026-08-18)

**Verdict: DISCONFIRMED.** CAS's involution pairs are NOT geometrically opposite in the
model — they are the MOST SIMILAR, and CAS's specific pairing is the LEAST antipodal of
the 15 possible pairings. This is the sharpest relational CAS claim, and it fails cleanly.

## Test
On the real Condition-3 GPT-NeoX-20B activations (`condition3_gptneox20b_activations_20260531.npz`,
1440×44×6144, 144 scenarios/operator, balanced), for the 6 operators in CAS's involution
pairs {^2↔^3, ^5↔^6, ^8↔^9}: is CAS's specific pairing more **antipodal** (opposite about
the global centroid) than the other 14 ways to pair those 6 operators? Exact 15-matching
permutation test, per layer. Also: pairwise separability (held-out diff-of-means). Pure
numpy on captured activations; no model/GPU. `cas_involution_test.py`.

## Result (robust across all 43 real layers)
- **CAS involution matching ranks 14/14 (LAST) in antipodality on every real layer** (layer 0 = embeddings, degenerate). It is the *least* oppositional pairing.
- **Involution-pair centroid cosine is POSITIVE (+0.32 to +0.61), not negative** — `^2`/`^3` etc. are represented as SIMILAR, not opposite. (E.g. best-signal layers 12-14: +0.32..+0.34.)
- **Involution pairs are LESS separable than random pairs** (e.g. layer 13: involution-pair sep 0.743 vs all-involved-pair sep 0.845). Harder to tell apart, not opposite.

## Read
- The model groups `^2`(attraction)/`^3`(aversion) etc. by shared **topic/valence** (both are "valenced" scenarios → similar), NOT by CAS's claimed **opposition**. The involution's *directional* opposition is not the model's dominant geometry.
- This is consistent with the flat-detection collapse (§Condition-3: CAS 6.5% ≈ chance on leakage-controlled fixtures) and the MTC GREY: the model represents these scenarios by surface/topic, not CAS's relational structure.
- **Honest scope:** "antipodality about the global mean" is one operationalization; the *relative* result (CAS pairing is worst of 15) is a fair comparison and is decisive for the opposites claim. A finer subspace could still carry weak directional signal (involution pairs ARE ~0.6-0.74 separable), but the sharpest relational prediction fails.

## Remaining relational checks (not yet run)
Domain precedence `P≻C≻E≻O` geometry; RPM prerequisite-chain geometry. The involution
failure lowers the prior on these, but they are different relations worth a cheap check.

## Where this leaves CAS-specificity
Three independent lines now agree: flat-detection collapses to chance under leakage control;
MTC Condition-3 = GREY; involution relational structure = disconfirmed. CAS-specificity
remains NOT LICENSED, and the evidence is trending toward "CAS structure is not distinctly
present in the model beyond generic topical structure." Honest, and worth stating plainly.
