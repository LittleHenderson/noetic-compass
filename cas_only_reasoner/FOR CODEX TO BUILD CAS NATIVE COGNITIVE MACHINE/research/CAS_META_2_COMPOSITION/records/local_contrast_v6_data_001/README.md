# Focused data-adapter tests

77 tests passed in 11.98 seconds, covering the curriculum and data adapter.
The process installed `NoNeuralOrProviderImports` before loading pytest, disabled
plugin autoload and cache, and tested `tests/test_contrast_v6_data.py` plus
`tests/test_contrast_v6_curriculum.py`. XML is preserved in `tests.xml`.

This initial focused invocation used pytest's default temporary-directory
setting. The subsequent full validator uses explicit retained homebase scratch
and provides the complete command, environment, source snapshots, and raw output.
No neural or provider execution occurred; no learning is claimed.
