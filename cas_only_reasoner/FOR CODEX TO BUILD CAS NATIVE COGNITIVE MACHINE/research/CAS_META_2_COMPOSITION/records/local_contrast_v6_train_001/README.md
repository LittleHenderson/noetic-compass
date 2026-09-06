# Candidate CUDA-loop control checks

The first focused run passed 45 pure tests in 0.42 seconds. It installed
`NoNeuralOrProviderImports` before pytest, disabled plugin autoload and cache,
and used retained homebase scratch `_tmp/contrast-train-v6-001`.
It ran `tests/test_contrast_v6_train.py` and saved XML to `tests.xml` here.
The later pinned-exclusion CLI check is included in the full regression run.

The tests check configuration bounds, explicit job admission, validation
denominators, measurement scheduling, four-arm prediction coverage, immutable
receipt writes, and source coverage. No model or provider was loaded.

The new CUDA loop is candidate code, not measured learning. Its separate GPU
end-to-end test has not been executed. A bounded parent still needs to bind
source/configuration, reserve spend, run GPU gates, generate registered data,
export the training bundle, invoke the trainer, confirm successful child exit,
recount validation/selection, add the rule arm, run the unchanged native verifier,
collect a complete packet, and confirm cleanup.
