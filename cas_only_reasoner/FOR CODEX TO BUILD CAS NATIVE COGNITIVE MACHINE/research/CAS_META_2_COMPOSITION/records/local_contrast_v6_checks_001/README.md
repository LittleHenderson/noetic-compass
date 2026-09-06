# Parent-gate and evaluation-adapter pure tests

First run: 29 tests passed in 11.33 seconds (`tests.xml`).
Expanded focused run: 76 tests passed in 11.26 seconds (`tests_v2.xml`), covering
`tests/test_contrast_v6_checks.py` and `tests/test_contrast_v6_train.py`.

Both runs installed `NoNeuralOrProviderImports` before pytest, disabled plugin
autoload/cache, and used retained homebase scratch directories
`_tmp/contrast-checks-v6-001` and `_tmp/contrast-checks-v6-002` respectively.

The fixtures are deliberately synthetic: their checkpoint files say NOT A MODEL,
their process command says synthetic, and their CUDA environment is fabricated
test data. Passing these fixtures proves only checker behavior, not that any
model or provider ran. Mutation tests cover process failure, unconfirmed exit,
changed stdout/checkpoints, altered selection and saved actions, private-label
claims, source differences, invalid seal timing/hashes, and case/arm mismatches.

The pure rule-control test checks that all five arms are sealed before the
evaluator opens private targets, and that the four-arm neural file is unchanged.
Group tests retain depth and wording-condition denominators. Local native
execution is refused before reaching model imports.

The AWS-only test now includes a real training child, exit receipt, gate,
checkpoint reloads, and nine diagnostic native cases. It has not yet run.
