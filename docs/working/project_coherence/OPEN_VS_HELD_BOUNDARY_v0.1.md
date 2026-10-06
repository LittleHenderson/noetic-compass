# Project Coherence open-vs-held boundary v0.1

Document status: `DRAFT / FLAG_FOR_HUMAN_REVIEW / NOT LEGAL ADVICE`

Date: 2026-08-04

This document is a disclosure-control worksheet, not a disclosure decision. It does not determine patentability, ownership, inventorship, trade-secret status, export status, publication rights, or legal privilege. Those decisions require the owner and qualified counsel where applicable.

## 1. Decision states

Every Project Coherence artifact receives exactly one disclosure state:

- `OPEN` - the owner has approved this exact version for public release, or it is already publicly available from an authorized source and Project Coherence is merely citing it accurately.
- `HELD` - the exact artifact is restricted to authorized participants and approved storage. It must not be placed in a public issue, public repository, public model prompt, conference submission, demo, or customer packet.
- `FLAG_FOR_HUMAN_REVIEW` - no valid disclosure decision has been recorded, the scope is mixed, or ownership/licensing/patent/confidentiality questions remain. This fails closed as `HELD` for transmission purposes.

`OPEN` describes disclosure permission only. It does not mean correct, peer-reviewed, validated, licensed as a product claim, safe, or ready for release.

## 2. Default boundary

Until a signed decision says otherwise, the following are `HELD` or `FLAG_FOR_HUMAN_REVIEW`:

- the Project Coherence charter and successor architecture;
- proposed TKS v8, Noetic Topos 2.0, PCBA 8, CAS-Ohm 1.0, and Harness 2 mechanisms;
- unpublished proofs, counterexamples, proof-assistant work, and novelty analyses;
- CAS-specific reductions of third-party or internal-model mathematics;
- unreleased compiler changes, private fixtures, hidden evaluation taxonomies, probe details, and scoring thresholds;
- private Evidence Packets, WORM receipts, operational logs, provider configuration, security controls, red-team methods, and incident data;
- customer, participant, annotator, employee, provider, or model data that is private, licensed, personal, confidential, or contract-restricted;
- patent-sensitive claims, implementation details, diagrams, or experimental results;
- model weights, datasets, publications, or source code for which redistribution rights have not been checked; and
- any product statement whose current claim status is `OPEN` or `NOT LICENSED`.

## 3. Material that may become open

The following are candidates for `OPEN` only after exact-version and rights review:

- citations and accurate summaries of already public primary sources;
- standard mathematical definitions and proofs, with correct attribution and within applicable licenses;
- negative or null research results whose data and method are cleared for release;
- corrigenda and theorem-status tables that do not reveal held implementation details;
- public-safe schemas, validators, and synthetic examples; and
- an owner-approved public edition of the charter or plain-English companion.

The public OpenAI-hosted PDF *Ten Advances in Mathematics and Theoretical Computer Science* may be cited as an OpenAI public technical manuscript. Its public availability does not authorize reuse of unrelated held Project Coherence material, and it must not be described as peer-reviewed unless that status later changes and is verified.

## 4. Current Phase 0 classifications

| Item | Current disclosure state | Reason / closure action |
|---|---|---|
| Exact public `ten-proofs-oai.pdf` URL and bibliographic facts | `OPEN` | Already available from an OpenAI-hosted public URL; describe publication status conservatively. |
| Ten manuscript results as established facts | `FLAG_FOR_HUMAN_REVIEW` | Proof, novelty, authorship attribution, and publication review remain open. |
| Project Coherence Phase 0 package | `FLAG_FOR_HUMAN_REVIEW` | Internal governance draft; owner has not approved a public edition. |
| TKS/CAS source identities and local filesystem paths | `FLAG_FOR_HUMAN_REVIEW` | Useful for reproducibility but may reveal private corpus organization; sanitize paths in any public edition. |
| Exact canonical Noetic names and definitions | `FLAG_FOR_HUMAN_REVIEW` | The normative source says the names apply in public contexts, but this worksheet does not independently establish release rights for every source artifact. |
| Standard projector-kernel proof | `FLAG_FOR_HUMAN_REVIEW` | Mathematically standard; clear attribution, exact wording, and packaging before release. |
| Projector-capacity CAS specialization | `HELD` | Current transfer has a proof gap and may be patent-sensitive; no public claim. |
| Marked/modal Noetic Topos successor design | `HELD` | Unreleased design and open proof obligations. |
| CAS-Ohm formulas, calibration data, and instrumentation mappings | `HELD` | Experimental and potentially patent-sensitive; measurement honesty and rights review required. |
| Current CAS Harness methods, taxonomies, controls, evidence, and provider details | `HELD` | Preserve existing confidential-methodology and security boundaries. |
| Customer-facing readiness or efficacy claims | `HELD` unless the canonical record says `LICENSED` | A theorem or successful research run cannot license a product claim. |

## 5. Release packet required for `OPEN`

An `OPEN` transition must identify:

1. exact artifact path, version, and SHA-256;
2. owner or delegated decision authority;
3. decision date and intended audience;
4. authorship and contribution record;
5. source and data licenses;
6. patent/disclosure review state;
7. privacy, security, customer, provider, and contractual review state;
8. theorem, evidence, and product-claim status;
9. redactions or public-safe transformations and their hashes; and
10. a public wording record that states what the artifact does not prove.

If a public-safe derivative is created, both the held source and open derivative receive separate hashes. Redaction does not mutate the source artifact.

## 6. Operational rules

- Do not paste held source text, confidential methodology, private evidence, or secrets into external models or public collaboration tools.
- Do not treat a Git commit, branch push, preprint upload, demo deployment, or customer email as a harmless intermediate step; each can be a disclosure.
- Before pushing this Phase 0 package, verify repository visibility and intended audience. A private repository push is not a public release, but access still must be authorized.
- Before public release, replace user-specific absolute paths with stable public identifiers or redacted source IDs.
- Cite public sources by direct URL or DOI and describe manuscript/preprint/peer-review status exactly.
- Keep negative findings and failed proofs in the held audit record; do not erase them to make a public narrative cleaner.
- Never include credentials, tokens, private keys, provider receipts containing secrets, personal data, or customer-confidential content in a release packet.

## 7. Human decisions still required

- Approve or revise the three-state disclosure vocabulary and decision authority.
- Decide whether any Phase 0 artifact may have a public-safe edition.
- Resolve whether the proposed successor designs should remain trade secret, enter a filing, or be published.
- Review source and output licenses for the TKS corpus, the OpenAI manuscript, diagrams, datasets, and generated proof artifacts.
- Resolve inventorship and authorship for human, model-assisted, and model-generated contributions.
- Decide when the compiler drift, source-version conflicts, and PCBA build label are safe to describe outside the authorized project group.

Until those decisions are recorded, this package remains `FLAG_FOR_HUMAN_REVIEW` and fails closed as held for transmission.
