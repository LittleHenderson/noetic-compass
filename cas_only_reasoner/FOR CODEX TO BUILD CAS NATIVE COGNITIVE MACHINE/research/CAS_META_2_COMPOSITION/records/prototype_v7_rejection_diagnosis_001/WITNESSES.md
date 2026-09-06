# Representative saved-token witnesses

These examples are selected from the completed
[diagnosis.json](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_rejection_diagnosis_001/run_001/diagnosis.json>),
SHA256 `6221afb137ed5a35654d5c9bdde71569c271825c9530b31a5ca7a8061a1d41d4`.
All token indices are zero-based. No token was substituted and no native
execution was repeated. They are observed structural boundaries, not proven
neural causes.

## 1. Trained CAS case 28: a locally allowed, noncompletable PROC

Depth 4, deeper_calls; saved action SHA256
`80bad153d80704639b6bf88055bd745e7c1633d870b7a9c8afd988b9f9ef91e8`.

Exact saved prefix through token 42:

```text
[BOS] BIND1 PROC main ALLOW A B C ENDALLOW
RUN A arg v0 RUN A arg v1 CALL p5 arg v2 RETURN v2 ENDPROC
PROC p5 ALLOW A B C ENDALLOW RUN B arg v0 RUN C v0 v1 RETURN v0 ENDPROC
PROC
```

Before that final `PROC`, the actual state is
`role=procedure_or_eos`, declared procedures `[main,p5]`,
last declaration `p5`, and pending forward calls `[]`.
Actual v3 allows `PROC`; the existing v4 check rejects it as
`PROC_WITH_NO_PENDING_FORWARD_CALL`. Closed procedures cannot acquire a
future call to the newly declared procedure.

The stream continues to 90 saved tokens. After `ENDPROC` at index 89 the
first empty mask is in `procedure_or_eos`, with
`UNREACHABLE_PROCEDURE`. Declared procedures are `[main,p5,p6,p9]`;
pending forward calls are empty. Both terminal allowed sets are empty,
including the raw set without the 256-token budget.
A second detected PROC witness occurs at index 60. It is not a second task.

## 2. Untrained CAS case 2: CALL allowed, but no target can follow

Exact complete saved prefix, 40 tokens:

```text
[BOS] BIND2 PROC main ALLOW C B A R ENDALLOW
RUN C arg v0 RETURN arg ENDPROC
PROC p8 ALLOW C B A R ENDALLOW RUN C arg v0 RETURN arg ENDPROC
PROC p9 ALLOW C B A ENDALLOW CALL
```

The `CALL` at index 39 is allowed by v3 but produces the first empty mask:
`role=call_target`, current procedure `p9`,
scope `[C,B,A]`, available variables `[arg]`,
declared procedures `[main,p8,p9]`, pending forward calls `[]`.

The receipt records a reason for excluding every target:

- `main` and `p8`: `CHILD_SCOPE_EXCEEDS_PARENT`.
- `p9`: `WOULD_FORM_CALL_CYCLE`.
- Every remaining codec procedure name:
  `UNDECLARED_NAME_PASSED_CANONICAL_ORDER`.

This is `CALL_WITH_NO_LEGAL_TARGET`, with terminal reason
`NO_LEGAL_CALL_TARGET`. It is **not** this row's first detected structural
impossibility: earlier `PROC` witnesses occur at indices 17 and 32.
The stream contains no disallowed emitted token.

## 3. Trained CAS case 26: no early witness from the two existing checks

Depth 3, same_depth; saved action SHA256
`f827502a6eafc883829a5082498dff17ac34a76f7cb532e0e7aceea64440f554`.

Exact saved stream, 102 tokens:

```text
[BOS] BIND0 PROC main ALLOW A B C ENDALLOW
RUN A arg v0 CALL p12 v0 v1 CALL p9 v0 v2 CALL p9 v0 v3 CALL p12 v0 v4 RETURN v4 ENDPROC
PROC p12 ALLOW A B C ENDALLOW RUN B arg v0 RUN B arg v1 RUN C v0 v2 RETURN v1 ENDPROC
PROC p15 ALLOW A B C ENDALLOW RUN B arg v0 RUN B arg v1 RUN C v0 v2 RETURN v1 ENDPROC
PROC p9 ALLOW A B C ENDALLOW RUN B arg v0 RUN B arg v1 RUN C v0 v2 RUN C v0 v3 RETURN v3 ENDPROC
```

Neither of the two early checks fires. This does not establish that every
prefix could still have been completed. The reference-free checks are
deliberately incomplete.

After the final `ENDPROC` at index 101, the first empty mask is
`role=procedure_or_eos`, declared procedures `[main,p12,p15,p9]`,
last declaration `p9`, pending forward calls `[]`,
instruction count 15, and no current procedure or available variables.
Actual and raw allowed sets are both `[]`.
The completion checker reports `UNREACHABLE_PROCEDURE`.

The literal saved calls in this stream target `p12` or `p9`; none targets
`p15`. This is visible in the stream, without consulting the task answer.
Under the frozen grammar's name order (main first, then lexical name order),
no later declaration name remains after `p9`; invalid completion excludes
EOS. The receipt does not supply a callee-exclusion map for this state,
because it is not a `call_target` state.

The other trained CAS rows without an early witness are 45, 52, 60, and 70.
All five end in the same recorded terminal role and completion error.
This example does not locate the first neural mistake.

## 4. Trained generic case 34: complete action rejected at native admission

Depth 4, deeper_calls; saved action SHA256
`2b5d23502ff55c925eacaddd88c404f219424d632fcdbf4b1dd7d4c8b511a776`.

There is no generator-rejection wrapper and no saved emitted token stream.
The evaluator records:

```json
{"code":"PREDICTED_PROGRAM_INVALID","message":"NATIVE_TOPOLOGY_MISMATCH","type":"CurriculumError"}
```

The underlying saved case receipt has SHA256
`a74df202a94c20498d1b8bd82f902b83cfce29c6ccd1dc2dbd5be5d99de345ac`
at packet member
`cloud_job/campaign/native/evaluation/case_0034/generic_trained/case_receipt.json`.
The analyzer verifies its exact completed action against the sealed prediction
and prior checked audit row. It preserves this as a complete-action native
admission rejection, not a token-mask failure. It does not replay or infer
unrecorded tokens.

