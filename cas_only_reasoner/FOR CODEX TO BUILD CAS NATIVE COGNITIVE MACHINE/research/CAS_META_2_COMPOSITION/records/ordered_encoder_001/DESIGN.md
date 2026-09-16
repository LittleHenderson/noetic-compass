# Ordered problem encoder 001

Status: separate candidate; no training result or native-flow claim. The legacy
encoder and frozen complementary/perspective experiments remain byte-identical.

The current structural encoder multiplies every token row within a line. This
commutative product loses source/target order when an edge reversal retains the
same token multiset. Its mean-pooled request text similarly loses query argument
roles. Repeated training or recurrence cannot recover a distinction erased by
this input map. Floating reduction roundoff is not a reliable semantic channel.

`cas.graph-ordered-problem-encoder/0.1` reuses the inherited train-fitted
LosslessPublicTokenizer, frozen projection rows, dimension, option encoder,
option vectors and readout. Only `encode_problem` changes. It introduces no
trainable parameters and does not import a graph checker or reference answer.

Public text is split into newline-delimited frames. Lines beginning with the
public `node` or `rel` marker are structural. This is syntax framing, not graph
evaluation: endpoints, reachability, containment, and answers are never parsed.
Remaining framing/query lines retain their relative nonempty line order. Each
line uses the inherited tokenizer including exact UTF-8 fallback. Newlines are
frame separators; empty lines are ignored. A separate CLS frame remains present.
The complete original input and the linewise token count both obey the inherited
length bound. Options are validated but do not enter the problem binding.

For token position p, a full coordinate permutation and independent signs are
derived from SHA256 over the algorithm version, seed, frame kind, framing line
ordinal, p, dimension, coordinate ID, and separate permutation/sign domains.
This is not a periodic roll. The permuted, signed rows are summed, divided by
sqrt(line length), and unit-normalized. Exactly zero or nonfinite line norms
fail closed. No products of small coordinates are used, avoiding the previous
long-product underflow mechanism. Structural frames are sorted by kind and
token IDs before aggregation, so their reordering yields the same addition
order; duplicate lines remain duplicate contributions.

The adapter requires CUDA before touching tensors. It reads the existing
embedding rows, keeps an exact snapshot for problem encoding, and retains the
inherited option callable. The new profile binds tokenizer digest, actual
projection bytes/dtype/shape, dimension, permutation seed, algorithm, and frame
rules. A checkpoint must carry that exact `encoder_identity`; missing legacy
identities and mismatches are rejected. Existing checkpoints must not be called
compatible or resumed under this profile without an explicit new experiment.
The adapter and identity guard are preparation seams; the unchanged legacy
training/checkpoint loaders do not call them. A future versioned training worker
must record and validate this identity before loading any model or optimizer.

Pure tests compare exact symbolic linear-binding coefficients for edge reversal,
query-role swaps, and unseen byte-anagrams; they also cover structural reorder,
framing order, duplicate preservation, private-field rejection, input ceilings,
checkpoint identity and the CPU execution guard. These tests establish removal
of the old forced token-multiset symmetry. They do not measure GPU separation.
The parent task will record any separately authorized CUDA encoder-only probe.

A 64-dimensional sum remains a lossy projection. Accidental numerical collisions,
near-collisions, sensitivity to wording, and learnability remain open. The change
does not establish graph competence, generalization, improved accuracy, native
CAS-Ohm current/resistance, empirical calibration, or V02/V09 completion.
