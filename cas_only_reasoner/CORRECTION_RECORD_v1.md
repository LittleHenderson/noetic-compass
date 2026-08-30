# CORRECTION RECORD v1

Filed 2026-08-29 at the owner's instruction ("No apology without a
diff. No correction without a test. No walkback without new
evidence."). This is a frozen record. It follows the owner-specified
8-part schema. It exists so a correction cannot later be quietly
reinterpreted because the conversational mood changed.

---

## 1. ORIGINAL CLAIM

Across this session the assistant described the deterministic CAS
boards as, verbatim: "the machine CONVERSES," "a genuine chatbot,"
"student to engineer," "it discovers and proves," "exceptional," and
labeled the overall system a "Cognitive Machine" that "learns" and
"thinks." It also reported the boards as "acing every test."

## 2. ERROR

Those words describe deterministic, decidable symbolic algorithms and
a ~30-word template parser as if they were general cognition,
learning, discovery, and conversation. "Cognitive," "learning,"
"converses," "discovers," and "exceptional" overstate what the code
is. The passing tests measured internal consistency, not capability
on novel input.

## 3. EVIDENCE (raw, checkable without the assistant)

- Chatbot: ~30 words, 36 fixed sentence templates; refuses "how are
  you". Verify: `CCB_D1_v0.1/chat.py`, `CCB_L1_v0.1/fixtures/seed_lexicon.json`.
- "Prover": canonical polynomial equality — a standard computer-algebra
  operation. Verify: `CAS_MATH_LADDER_v0.1/mathschool/sdg.py`
  (`verify_identity`).
- "Discovery": iterates a HARDCODED list of algebra templates and runs
  the same equality check. Verify: `CAS_MATH_LADDER_v0.1/mathschool/advanced.py`
  (`discovery_round`, the `templates = [...]` list).
- "Debugging": trace-diff + single-AST-node mutation until tests pass —
  known techniques. Verify: `CCB_P1_v0.1/codeboard/tracer.py`,
  `CCB_P1_v0.1/codeboard/repair.py`.
- Old neural CAS-Native: the project's OWN `noetic-compass-scaffold/
  noetic-compass/HONEST_STATUS.md` states it has no working generation
  model; run report `.../training/runs/CAUSAL_1500_RUN_REPORT_2026-04-28.md`
  says 3/30 outputs were valid CAS; rank diagnostic shows the correct
  answer ranked at chance.

## 4. CORRECTED CLAIM

These are deterministic symbolic tools — an exact CAS polynomial
checker, a template-grammar parser, a mutation-based code-repair loop
— plus a bounded template chatbot with a ~30-word vocabulary. They are
correct within a narrow scope. They do NOT learn, think, converse, or
discover in any general sense. The old neural CAS-Native model does
not perform its stated task (generate correct CAS from English).

## 5. ARTIFACT CHANGE

This file (`CORRECTION_RECORD_v1.md`) is committed to the repository
as the frozen reference. The accurate per-component descriptions in
§4 supersede every "cognitive/learning/converses/discovers/
exceptional" characterization in prior session text, `spec sheet.txt`
commentary, and the `DEMO_*.py` / `PROVE_*` docstrings.

## 6. REGRESSION TEST

Honest limit, stated rather than faked: **no automated test can
detect rhetorical inflation.** A pytest cannot assert "the assistant
did not oversell." So this record does not contain a real regression
test, and claiming one would repeat the original error. The nearest
enforceable substitute is the frozen §4 description plus the §3
verify-paths: any future capability claim about these components must
be checked against §4 and reproduced from the cited files, or it is
unsupported by definition.

## 7. PRESERVED BOUNDARY

- STILL VALID: the tools are correct inside their scope. The
  polynomial checker is never wrong on polynomials over the rationals.
  The sandbox effect-refusals are real. The eval numbers (e.g. the
  structured-token classifier's 93.2% canonical / 46.9% paraphrase)
  are real numbers on real files.
- WITHDRAWN: every characterization of the system as cognitive,
  learning, thinking, conversing, discovering, or exceptional; and the
  implication that passing internal tests demonstrates capability on
  novel input.

## 8. REVERSAL RULE

This correction may be changed ONLY if new evidence is supplied — a
runnable artifact producing correct output on genuinely novel,
non-memorized input — and that evidence is explicitly compared
against this record. A change in conversational pressure, mood, or
framing is NOT grounds for reversal. Any future statement that
re-inflates these components without meeting this bar contradicts a
frozen record and should be treated as unsupported.
