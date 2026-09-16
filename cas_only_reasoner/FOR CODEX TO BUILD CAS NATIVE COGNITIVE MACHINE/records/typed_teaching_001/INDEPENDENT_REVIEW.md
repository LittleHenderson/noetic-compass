# Independent typed-teaching interface review

Date: 2026-09-16. Status: **bounded source/syntax review and independent combined
receipt verification passed**. This is not full-course execution admission.

The reviewed current files are relative to the CNCM repository root:

| File | SHA-256 |
| --- | --- |
| `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/source.py` | `13c265e576dd027362611ca0956ac9f1e6285945cb7e626cef9270c2d08a9337` |
| `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/answers.py` | `4d4cf21b65914c5b6878b58a52ab3cfe2f8864b319a3bb5ad1b95c6780686e5c` |
| `research/CAS_META_2_COMPOSITION/docs/TYPED_TEACHING_SEMANTIC_REVIEW_v0.1.md` | `405edc898301ae8e305b3d10e41ce2829c1b2dabd5cca75c0d8836674024cd1e` |

The design review contains the inherited source identities, exact source
locations, concrete semantic counterexamples and the full-course coverage
requirements. Its existing-course counts are evidence about the prior pure
preparation, not proof that this new interface has rebuilt that course.

## Checks performed

The reviewer read the source and answer contracts and ran a small independent
in-memory probe with `python -I -B`. A module-import guard denied numerical,
model, provider and network modules. Among project modules it allowed only
`cas_meta2`, the `typed_teaching` package, `source` and `answers`; no graph teaching,
task, evaluation or final-target module was imported.

The probe established these bounded facts:

- The literal-only constructor produced 64 training source families, from the
  mechanical, grammatical, procedural and container domains. It did not call the
  legacy all-split constructor or generate teacher targets.
- Freezing their bank and selecting a focus retained all 64 worlds. The analogy
  answer space exactly matched the public bank, with no target-based filtering.
  Null and same-focus analogy candidates passed syntax.
- All six role IDs were present. The payload `roles=[5,6], status=AMBIGUOUS`
  survived canonical encoding and decoding. This proves that ambiguity is
  representable, not that this particular role judgment is semantically correct.
- The four-node edge-account space contained all 16 possible ordered node pairs,
  including self-pairs. A false self-edge was accepted syntactically.
- Four-node correspondence yielded 24 complete bijections plus `NO_MATCH`.
  All 25 candidates passed syntax checks, without filtering on graph edges.
- All public worlds declared complete supplied containment snapshots and null
  process order. Source/answer inspection keeps lexical edge serialization
  separate from temporal order and uses world-scoped references.
- The final answer source explicitly handles invalid UTF-8 excerpts and rejects
  self-reach queries (`TYPED_EXCERPT_ENCODING` and
  `TYPED_REACH_DISTINCT_NODES`). This statement is from source inspection; the
  independent small probe did not claim separate behavioral tests of these two
  controls.

The first successful probe used source hash
`d11b406faab7433739b1dc181e9c557772959ebff2e16538a42a5efee533d1f8` and the answer
hash in the table. Both were unchanged from its start to end. No forbidden module
was loaded. The reviewer wrote only review documents, not runtime files, tests,
checkpoints or provider records.

The source owner then made one narrow change: public JSON rejects tuples, while
the authored family constructor may still accept tuple-valued source literals.
The reviewer inspected this change and ran a second bounded probe against the
final source and answer hashes in the table. It reconfirmed 64 training families,
a full 64-world bank, and admission of all 24 four-node bijections plus
`NO_MATCH`. Converting a public `branch_order.source_order` list into a tuple was
refused with `TYPED_SOURCE_JSON_TYPE`. Both final source hashes remained unchanged
during this probe, and no forbidden module was loaded.

## Transient first attempt

The first independent probe reached its final source-stability assertion while
the source owners were still editing. That assertion stopped the attempt because
the source bytes changed. It was **not an observed answer-contract behavior
failure**. A subsequent probe used the earlier stable `d11b406f...` source,
verified unchanged bytes before/after, and completed successfully; the final
tuple/list change was then checked separately as described above. The interruption is retained in the
review record rather than erased or described as an initial green run.

## Limits and remaining gates

No critical target-filtering or graph-versus-process-order defect was found in
this bounded syntax/source interface. Incorrect but well-formed answers are
deliberately admitted. A semantic checker, full-course compiler, new loss/scoring
path and learner execution are not established by these checks.

The target remains all **1,152 event occurrences in 160 groups**, covering all six
faces, without dropping ambiguous cases. This interface review did not rebuild
or execute that course. It did not count all semantic ambiguities or certify any
private target.

Arbitrary received sources remain caller-supplied declarations. Their hashes
and closed syntax do not authenticate source custody, prove canonical training
membership or establish world truth. The controlled training constructor and a
future independently pinned execution harness must establish the experiment's
source boundary. No final targets, model/tensor execution, provider calls,
learning gain, matched-study result or final experimental protocol is claimed.

## Combined receipt

The independently verified final receipt is
`records/typed_teaching_001/checks_002/receipt.json`, SHA-256
`a3f213d340c8ec37368688fbf2b805fa4ed5d58fc5af6ffffa25fedebe4eb869`, status
`PURE_SOURCE_AND_SYNTAX_PASS`.

All six listed artifact sizes and hashes match the retained bytes. All 11 input
pins match the current files; `inputs_before.json` and `inputs_after.json` are
byte-identical, SHA-256
`dbc7c940a06f2ef7b3a46fb00cd023a69e9f1945eea9b6d23806190ba9da97aa`.
Direct JUnit case recount gives **72 tests: 37 source tests and 35 answer tests,
zero failures, errors or skips**. The JUnit file SHA-256 is
`695f1049fc4167a6cab4d19041a38ec22f636d31d1aa556af14e140b33b38044`.

The retained bank contains 64 worlds: 16 from each of the four training domains,
12 worlds with three nodes and 52 with four nodes. No world declares temporal
process order. The first source envelope contains the same worlds and bank, and
the retained query examples cover eight answer kinds. They are public grammar
examples, not semantic targets. The receipt reports no forbidden imports,
blocked artifact reads or blocked execution attempts, and zero neural calls,
optimizer updates and provider calls. This reviewer did not rerun the test suite,
models or provider operations during receipt verification.

The earlier combined attempt in `checks_001` is separately preserved. Its JUnit
reporting was interrupted by an overbroad guard rejecting the local
`socket.gethostname` lookup. It is not a completed passing aggregate receipt.
The preserved `runner_snapshot.py` exactly matches that attempt's runner input
pin. Comparing the failed and successful input inventories shows that **only
`records/typed_teaching_001/check.py` changed**; all runtime source and test bytes
are identical across the two attempts. Source comparison confirms that the runner
repair exempts only the hostname lookup from the socket guard and adds reporting
failure retention. Other network and subprocess guards remain present.

The combined receipt explicitly leaves `full_course_rebuilt`,
`semantic_teacher_checker_implemented`, `neural_decoder_implemented` and
`study_admitted` false. These open gates remain necessary before any full-course
or learning claim.
