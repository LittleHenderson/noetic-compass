# CNCM provenance-bound semantic correction memory v0.4

Status: VERSIONED CONTRACT. Current acceptance and limitations are recorded in
records/semantic_memory_001/STATUS.md. This version extends the real nested0.3
coordinator with sourced input memory; old source profiles stay unchanged.

The controlling charter is cas_reasoner.txt, SHA256
a72312231bfb346dc4895b1a0963e0c255d26b707c8a4fbc94d90ac52979dfea.
Its memory distinctions and integrated steps5,17,18,19 require provenance-bound
recall, correction, and an effect on a later task. This implementation advances
that path for exact rational equation inputs. It does not implement CMB-R1,
learned retrieval, general semantic concepts, or the complete integrated episode.

## Sources, custody and truth

A source statement names an exact scope, key, source identity, canonical rational
value, status, source reference, action, and previous source-head digest. ASSERT
creates or corrects a source claim; RETRACT leaves a tombstone. History is append
only. Source heads are separate for each (scope,key,source_id). A correction must
name that exact head; an old head, unrelated head or replay cannot overwrite it.
The coordinator is the only writer. Statements in a problem remain proposals
until the protected source checker admits them through STORE_SOURCE.

The trusted host supplies an initial set of exact statement digests. A new
correction may arrive after the first task: at the next terminal/quiescent
episode boundary the host may explicitly append newly authorized digests.
Existing authorization cannot be removed, and active episodes cannot change
it. Journals bind each episode's ingress identity; recovery requires the initial
set and ordered extension schedule again from an external trusted source.
It never derives authorization from statements or journal metadata.
A source name, digest in a journal, or self-written status grants no
authority. This is an explicit host/genesis/custody boundary, not cryptographic
identity authentication or proof a human actually approved a statement.

Current source statuses are USER_ATTESTED and TEST_FIXTURE. Source binding may
be verified while the fact remains unverified. Neither status meets a request
for INDEPENDENTLY_VERIFIED knowledge. A checked arithmetic answer is conditional
on recalled premises and cannot promote their factual status. Acceptance uses
identified engineering fixtures and does not invent a real user correction.

## Recall and later-task behavior

Semantic equation scalar fields a,b,constant accept a literal or a typed memory
reference. A reference names scope,key and an evidence requirement; it contains
no cached numeric value. The coordinator walks the query dependency closure,
recalls relevant references, and checks source history before any equation call.
It never resolves a reference from a previous answer or an unrelated scope.

All active source heads for one reference must agree. Different values refuse
with a conflict. Retraction never falls back to the source's previous claim.
Another live agreeing source can still support a query, with the retraction
retained in provenance. Missing, fully retracted, conflicting, and insufficiently
verified information remain distinct typed failures. Recall binds the exact
source digests, statuses, value, reference and checker receipt.

The original problem preserves every equation. The resolved nested problem
contains exactly reachable equations, in original order, with recalled scalars
substituted. Missing producers and cycles are left for native nested diagnosis.
An independent checker recomputes reachability, history, every reference and
every substitution. A placeholder packet exists only for pre-call planning;
it cannot authorize arithmetic. CHECK_MEMORY_RESOLUTION must pass before any
nested transition. Input/task identity and the resolution receipt join the
runtime state and the root proof's provenance.

## Shared runtime and verifier obligations

SemanticState0.4 extends the existing state with append-only statements and
receipts, current bindings, update cursor, failure and resolution identity.
SemanticCoordinator extends the actual TransactionCoordinator/NestedCoordinator;
it is not a detached promotion store. Memory mutation is permitted only before
the first equation call, preserving every suspended parent and numeric input.
Old nested frames, protected candidate executor, arithmetic checks, commitment,
procedure registry, reuse and first-install rollback remain active unchanged.

STORE_SOURCE reserves12 instructions/1 checker call, RECALL_MEMORY12/1,
CHECK_MEMORY_RESOLUTION16/1. The same budget funds later acquisition/application.
These are conservative policy units, not measured CPU, energy, time or money.
Malformed/authority/scope/stale proposals fail before expensive work. Failed
semantic checks keep their allocations and records. No refund is implemented.

The new common verifier receipt distinguishes its domain, exact claim, source
profile, evidence support, status and reason. It binds provenance and arithmetic
obligations without equating valid source custody to verified world truth. The
older arithmetic receipt protocols remain transitive evidence; this is not yet
a universal replacement for all charter verifiers.

## Persistence, refusal and acceptance

New episodes inherit admitted history and procedural artifacts only from the
host's preceding terminal, quiescent state. Bindings are always rebuilt for the
new task. Recovery replays every exact proposal occurrence through the same
source profile and external ingress set, comparing complete traces/states.
It never imports a saved state or upgrades a rehashed false journal to authority.
Unresolved native frames still prohibit a fresh budget episode.

Required evidence includes a baseline task using recalled fee5, an anchored
correction to fee8, and a new task omitting that value whose result changes from
10 to9. A separate process must recover and execute the new task with acquisition
disabled, preserving unrelated scopes and historical records. Engineering
variants must change coefficients and structure, not simply replay an answer.
Every transition cut, source substitution, stale/replayed correction, forged
binding/status, conflict/retraction, evidence threshold, bypass attempt, failed
check cost, budget exhaustion and rehashed false history needs direct coverage.

The full V01-V18,31-system,integrated20-step vision remains open. Memory of
unverified attestations is not the charter's independently verified CMB recall.
No improved reasoning, general learning, neural program synthesis, descendant
evolution, English-language understanding or CAS-specific advantage follows
from this bounded implementation alone.
