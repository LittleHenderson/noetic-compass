# EYE-ACT-1 open questions (each has a default the build follows until the owner says otherwise)

1. **Where the scored run happens.** Default: the laptop, 0 USD (standard library, no model, a few minutes of light
   compute, run in parts of at most 300 s). Alternative: one small AWS CPU host, cap 1 USD, on the owner's typed line.
2. **Who picks the scored worlds.** Default: nobody. Seeds come from sha256 of the owner's typed line + the sealed zip's
   sha256 (commit-then-reveal), so the line must be typed after the seal. Suggested line form:
   `EYE ACT EXAM, sealed <zip8>, laptop, 0 USD`.
3. **What a keep word does.** Default: nothing automatic. The switch stays OFF by default in live HELM until the owner
   rules on the result.
4. **What the Eye watches next** (not in v1): the licensed brain, the triad faces, the cube store's own records,
   `helm_memory` user facts, memory capsules (spec 7.115). Each would be its own amendment or test.
