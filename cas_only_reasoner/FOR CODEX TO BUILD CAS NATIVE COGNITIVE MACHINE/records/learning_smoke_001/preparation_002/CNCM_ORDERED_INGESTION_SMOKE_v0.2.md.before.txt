# Ordered ingestion teaching and reload smoke v0.2

This extension connects the accepted source-bound lessons to one actual CUDA
teaching cycle, then checks reconstruction from saved model, optimizer and
encoder state. It is an exposed-material mechanical test, not an experiment
establishing better learning. Current execution status belongs in
records/learning_smoke_001/STATUS.md; this document specifies the implementation.

The accepted v0.1 adapter and cycle remain unchanged. The new
cncm/rpa_learning_smoke.py orchestrates the existing training connection and
retains three checkpoints: the run's origin, an initial complete snapshot, and a
final complete snapshot. The complete snapshots include ordered parameter names,
AdamW state, tokenizer, frozen projection, source/request identities and encoder
profile. Decoding requires a caller-held size/hash and uses weights_only=True.

Reload reconstructs the tokenizer and projection from saved values, loads the
model and optimizer, and compares exact typed tensor contents. Both phases also
compare cached and uncached public predictions, actual public vectors, and the
original versus reconstructed state. Predictions are sealed before the private
scoring join. Source admission already constructs teacher sidecars; those targets
are not arguments to prediction. Reload is within the same worker process. This
does not establish a fresh-process restart or resumed optimizer-step equivalence.

The frozen smoke uses the existing exposed view_context cube fixture: three
training requests, one per operation, and six prediction requests, including
three cached and three uncached public inputs. It fits the tokenizer only on the
three training inputs. The candidate starts from a fresh initializer. It uses no
retained trained checkpoint and reads no new final evaluation family.

cncm/rpa_learning_worker.py binds the source inventory, fixture, two fixed import
wheels, exact requests and runtime. It checks the actual installed and loaded
casformer/cas_cjt source files against wheel contents before and after numeric
work. It retains model files, all four prediction seals, reload checks, runtime
details and actual work counts. Failure and partial artifacts are retained.

research/CAS_META_2_COMPOSITION/aws/ingestion_smoke_launch.py reuses the existing
candidate lifecycle and evidence transport with a separate experiment binding.
The package contains committed bytes, explicit cncm and research imports, and
fixed wheels. A caller-held authority binds source/archive/manifest, config,
existing owner instruction, spending bounds and the evidence contract. The actual
inner subprocess timeout is 1200 seconds; the inherited training loop permits at
most 64 updates in 600 seconds. The hardware/bootstrap limits remain one
g7.2xlarge in us-west-2, 3600/7200 seconds and one $7 reservation, with no automatic
job retry. The canonical ledger path is explicitly required for execution.

A successful run establishes this bounded teaching/reload connection only.
Learning speed, delayed retention and unseen transfer still require a separately
frozen, matched multi-seed comparison against ordinary graph teaching. The older
three-seed recurrence result remains NOT_MET, 0/3 positive.
