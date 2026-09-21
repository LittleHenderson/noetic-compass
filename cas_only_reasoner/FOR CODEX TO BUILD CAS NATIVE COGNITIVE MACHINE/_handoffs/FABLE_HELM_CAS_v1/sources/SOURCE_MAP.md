# Source map and evidence boundaries

S1: `HELM_CAS_EXPRESSION_SPACE_REVIEW.md` (original attachment has `(1)` suffix). Use the addendum as a revision to the earlier negative verdict. Source for actual-versus-proposed distinctions, SDG direction, Helm/CAS-Native separation, representation interfaces, namespaces, reported component gaps, and the combined plan.

S2: `HELM_2_0_HANDOFF.md`. Source for the reported local branch, implemented F1/F2/F4 changes, unfinished optimizer/ladder wiring, recovery risks, stand-in versus real learner tests, and evaluator-integrity gap.

S3: `HELM_ARCHITECTURE_FINDING_AND_PLAN.md`. Source for the code excerpt and frozen-message finding, parameter counts, and proposed architecture/compute plan. Claims that the single defect explains every failure or guarantees later gains are not adopted.

S4: `TYPED_POINTER_WORKER_RESULT.json`, exact bytes from `RESULT~1(6).JSO`. The file reports source `9b84b35c82bda422f744e76a170892313bc8b61b`, eight main updates in a reduced schedule, and skipped checks. Its artifact names/hashes do not supply their contents. Do not assign its scores to Helm 2.0 without resolving the model/source identities.

S5: `CLAUDE_OWNER_UPDATE_EXCERPT.md`. Labeled excerpt and summary from the current user message, including reported local-only commits. Not a complete verbatim transcript or independently verified Git state.

Exact copy hashes are in `SOURCE_MANIFEST.json`. Each source may be stale relative to Fable's local checkout. Neither a reference to another document nor a hash of an absent artifact establishes that absent document's contents.

## External primary-source precedents

E1: Pang Wei Koh et al., *Concept Bottleneck Models*, Proceedings of ICML 2020, PMLR 119. https://proceedings.mlr.press/v119/koh20a.html
Use: explicit intermediate concepts and interventions on downstream predictions. Not CAS or Helm evidence.

E2: Matt J. Kusner, Brooks Paige, Jose Miguel Hernandez-Lobato, *Grammar Variational Autoencoder*, Proceedings of ICML 2017, PMLR 70. https://proceedings.mlr.press/v70/kusner17a.html
Use: grammar-tree encoding/decoding through latent representations. Syntax validity is not a semantic correctness guarantee.

E3: Gonzalo Mena, David Belanger, Scott Linderman, Jasper Snoek, *Learning Latent Permutations with Gumbel-Sinkhorn Networks*, 2018. https://arxiv.org/abs/1802.08665
Use: differentiable continuous approximation to matching. Soft normalization does not ensure a legal discrete result under row-wise argmax.

These public primary-source pages were checked during preparation on 2026-09-21. This package does not include copies of their full text. All thresholds, work-item IDs, new schemas, proposed APIs, and integration choices in the directive are handoff design decisions, not claims from these publications.

## Authority hierarchy for implementation

Use actual current owner instructions and applicable repository rules for resource and write permissions. Use a versioned, independently reviewed semantic contract for each reference operation. Use source-pinned code and independent tests to verify the implementation. Treat these attached reviews as inspection reports and proposals, not a replacement for those authorities.

When a conflict is found, record both sources and the resolution. Do not silently change an ontology to match a test, or rewrite a test to match an implementation.
