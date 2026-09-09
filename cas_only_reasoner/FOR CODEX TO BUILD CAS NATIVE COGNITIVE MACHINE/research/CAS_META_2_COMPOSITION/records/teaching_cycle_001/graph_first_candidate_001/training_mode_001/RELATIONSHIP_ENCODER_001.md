# Graph-first ^6 — relationship encoder 001 (PREPARED, NOT LAUNCHED)

Owner-directed (option 2), 2026-09-09. Training pilot stays PENDING. This
document is the prepared candidate and the bounded diagnostic request;
nothing here has been registered, reserved, or launched.

## Basis

Attempt 006 (`ATTEMPT_LN3_006_RESULT.md`) measured that the lookup repair
works (token identity and corrective signals survive) AND that the problem
representation was a bag of words: same-token relationship rewiring moved
the module output by only ~5e-5, one row exactly 0.0. Which part belongs to
which idea never reached the module. This candidate finishes giving the
specialist the information the lesson requires.

## The encoding rule (actual, fixed, no learned parameters)

For the problem side only. The option path, the repaired token lookup, the
^6 module, the learning scope (`operation:^6`), and the teaching allowance
are UNCHANGED.

1. Tokenize the public problem with the campaign's lossless tokenizer; take
   the problem token ids (kind 0).
2. Segment LINE-WISE on the structural markers: a `node` or `rel` token
   opens a segment; the newline token closes it. Everything outside
   structural lines (framing text, the request, `Choose one option.`) is
   `rest`.
3. **Bind each complete line into ONE joint vector** with a fixed
   elementwise (Hadamard) product over that line's token rows:
   `bound(line) = e(t1) ⊙ e(t2) ⊙ … ⊙ e(tk)` — so a relation line binds
   `rel ⊙ source ⊙ kind ⊙ target ⊙ common=…` and a node line binds
   `node ⊙ label ⊙ kind=… ⊙ fields…`. This is a joint, role-sensitive
   combination — NOT independent role sums (summing all sources and all
   targets separately loses which source connects to which target).
4. `problem vector = Σ bound(line) over structural lines + mean(rest)`.

The encoder's job ends at preserving the supplied facts — it does not
determine parts, compute shared intersections, or solve routes.

## Why this passes the owner's contrast

For GRAPH A (`Bicycle contains wheel; Cart contains handle`) vs GRAPH B
(`Bicycle contains handle; Cart contains wheel`): the bound relation
vectors differ per pairing, so the sums differ. For a connection-list
REORDER of the same graph: the same set of bound lines is summed — equal in
exact arithmetic (float summation order only). Verified purely at the
vector level with the real tokenizer (`test_structural_problem_encoder_
preserves_pairings_not_order`): rewire → different vector; reorder →
identical vector.

## The bounded diagnostic checks (reused diagnostic, zero updates)

| Controlled change | Requirement |
|---|---|
| Rewire a valid graph, same words/question/choices | changed relationships produce distinguishable module inputs beyond the reorder baseline |
| Reorder the connection list, graph unchanged | representation equivalent within declared tolerance (reorder output difference ≪ rewire difference; exact at the vector level) |
| Change the private corrective target, public exercise fixed | encoded input unchanged (checked purely on permitted records — `check_target_independence`) |
| Alternative training targets on the same public example | existing gradient measurement shows distinct corrective signals reaching the permitted parameters |

No correct untrained answer is demanded; a changed argmax is not required on
every contrast — scores and internal representations responding meaningfully
is sufficient evidence that the lesson's essential distinction reaches the
student.

## Interface note (explicit)

The module interface is UNCHANGED: one d_model vector in, one out. No
trainable components were added. If preserving structure had required
changing the module interface or adding learned parameters, that would have
been documented separately — it did not.

## Next

If the diagnostic demonstrates relationship preservation, the next
experiment is the planned bounded teaching pilot (separately initialized
candidate copies, existing allowance, fresh evaluation) — not another
general review.
