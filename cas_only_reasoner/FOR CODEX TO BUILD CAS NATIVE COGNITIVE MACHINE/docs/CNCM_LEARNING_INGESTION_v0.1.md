# Source-bound learner ingestion v0.1

The versioned ingestion path translates the existing cube's declared containment
graph into the node/rel input consumed by the real graph learner. It keeps
supervision separate from public prediction input and binds the learner's
ID-based cache to exact public content. Final evidence and current status are in
records/learning_ingestion_001/STATUS.md.

This implements a connection needed for a learning experiment. Pure conformance
checks and recording stubs do not establish a numerical encoder run, model
update, retention, transfer, or improved learning.

## Public preparation and source-checked supervision

cncm/rpa_learning_adapter.py has two phases. prepare_public_lesson renders the
source-bound document before any tokenizer fitting. Its envelope carries public
text and ordered choices alongside a separate teacher sidecar and provenance.
Only the closed learner_input packet may enter prediction:

- record_id
- public, containing the problem and three unmarked observations
- encoded_options, retaining their exact visible order

bind_prepared_lesson independently reconstructs the prepared envelope from its
source before binding a supplied tokenizer, complete ordered-encoder profile and
run-initial model context. training_record and check_source_target repeat source
admission before supervision is used. Calling the frozen public_records codec
again is prohibited here because it would reshuffle choices under the new ID.

The rendering preserves declared nodes, directed containment edges, questions
and ordered choices. It supports the existing three scored operations. Labels
are bounded ASCII word phrases, including the actual source's Kit A and Kit B;
syntax delimiters, control characters, ambiguous reserved labels, lossy rendering
and duplicate choices are refused. This is a versioned containment-task profile,
not a general serialization of every cube face or graph type.

The actual pure LosslessPublicTokenizer must round-trip text exactly, fit the
1024-token inherited ceiling, and pass ordered_encoder.compile_frames. The new
input ID binds the public bytes, options, complete ordered profile and model
origin. A changed question or encoder context cannot keep an old ID. Different
source or assistance metadata with identical visible content can share a public
ID; source admission still distinguishes their private provenance.

Projection and checkpoint digests supplied to the pure adapter remain claims
about identity. Its capability flags stay false. No placeholder hash counts as
an observed checkpoint or numerical encoder. The worker records its separately
computed initial checkpoint and actual ordered profile.

## Connection to the existing learner

cncm/rpa_learning_cycle.py uses the existing GraphLearner and
trainer.run_training. It injects the newly admitted records instead of silently
selecting trainer.launch's old dataset. The training registry carries the private
encoded target index; every registry row must match the source-checked target
immediately before and after updates, including exact integer type.

PublicPredictor checks the actual cached public bytes and index mapping before
and after each prediction. It passes only the closed public packet and rejects
input mutation or a returned value outside the three options. The existing
GraphLearner.scores method is not used because its indexed path reads a private
target and computes a loss. Scores are explicitly unavailable in this first
connection surface.

seal_predictions writes and reads back the complete prediction file before
score_sealed_predictions invokes a private-target loader. The scorer checks the
caller-held byte count and SHA-256, closed canonical structure, exact record IDs,
unique choices and prediction indices before opening targets. Source-checked
targets must bind the same public packet. This is local integrity and sequencing,
not authenticated custody or an adversarial process sandbox.

## Opt-in worker path

run_worker_smoke is an implemented, locally unexecuted CUDA entrypoint. The
caller must supply an authorized worker runtime and source-bound document.
The inherited execution guard requires Linux and the explicit teaching enable
flag; those are configuration checks, not proof of AWS identity or spending
authority. No provider call, launch, reservation or automatic retry is made by
this module.

The smoke path is bounded to eight distinct training inputs and sixteen
prediction inputs. It fits the tokenizer on supplied training inputs only,
constructs the ordered encoder explicitly, seeds module initialization, and
retains an initial checkpoint containing model, frozen projection, tokenizer
and profile. Its public cache context names this run-initial origin and remains
fixed as the candidate's weights change.

The path then checks numerical cached/on-demand agreement, runs the inherited
bounded training loop, requires an observed permitted parameter change, checks
the frozen encoder again, seals public-only predictions and performs private
scoring. A final checkpoint includes model, optimizer and encoder material.
Forward calls and elapsed time are recorded. Checkpoint reload remains an open
gate; the receipt explicitly reports it unverified. These worker operations have
received source review, not local neural execution or CUDA acceptance.

Use only already-exposed engineering material for this mechanical smoke. An
actual smoke pass would establish the connection, not a treatment benefit.
The inherited learning-rate/update limits and external worker lifecycle still
need an exact packaged-source, provider and budget binding before a real run.

## Learning comparison and existing panel

The separate research/CAS_META_2_COMPOSITION/records/learning_panel_001 audit
reconciles existing corpus preparation and retained exposure history. It does
not create a new final panel or change old execution requests. In particular,
the prepared complementary corpus and its historical initializer cannot be
silently combined with a new ordered encoder.

The next experiment needs a fresh matched initializer, the same training-only
tokenizer and ordered encoder in every arm, a preregistered teaching difference,
equal information and measured work, and a final panel excluded from that run's
training and development decisions. Prior authoring/reference checking differs
from learner exposure. Historical custody gaps remain explicit; no worldwide
or unretained-history guarantee is made.

The learning protocol is docs/CNCM_NEXT_LEARNING_EXPERIMENT_GATE.md. The complete
CNCM charter and earlier negative three-seed recurrence result remain open and
unchanged, respectively.
