DRAFT — not legal advice; requires founder + qualified-counsel review before any external use.

# CAS Harness — Subprocessors (DRAFT)

**Status**: Internal draft for founder + qualified-counsel review. NOT published. NOT legal advice.
**Scope**: CAS Harness invite-only comped NDA beta.
**Draft date**: 2026-06-04
**Source of truth**: `noetic-compass-scaffold/noetic-compass/infra/render.yaml`, repo-root `render.yaml`, `api/llm_connectors/`, and the production-readiness TODO (`docs/working/cas_harness_production_todo.md`).

> This draft lists the third-party services that process data on Noetic Compass's behalf (or that a participant directs data to) during the CAS Harness beta. It is derived from the deployment configuration in the repository. Before any external use, counsel should confirm each entry, add the processing locations / DPA links, and confirm the AWS region.

---

## 1. Infrastructure subprocessors (Noetic Compass-operated)

| Subprocessor | Role in CAS Harness | Data processed | Notes |
|---|---|---|---|
| **Render** | Application hosting — runs the `noetic-compass-api` backend service (Docker / FastAPI) and the static frontend/dashboard hosting referenced in the blueprint | Model inputs/outputs in transit, Evidence Packet processing, account/auth/operational data, CRM/lead data in transit | Primary hosting platform. Single paid-disk instance; durability is single-instance restart-survival only (see `data_retention_and_worm_disclosure_DRAFT.md`). Hosts the database (Postgres) connection via `NC_DATABASE_URL`. |
| **Amazon Web Services — S3 (`us-west-2`)** | Evidence Packet external anchoring / storage | Evidence Packet anchor objects (packet hash commitments + manifests) | S3 Object Lock **GOVERNANCE** mode, ~30-day rolling retention, tamper-evident on re-verify, operator-overridable — **not** immutable, **not** permanent, **not** COMPLIANCE-mode. Anchor bucket observed in production evidence as `cas-harness-runpod-92754088`. Confirm region (`us-west-2`) and final bucket before external use. |
| **Vercel** | Frontend hosting (deployments served from `*.vercel.app`; permitted in the backend CORS allowlist/regex) | Frontend assets; relays participant requests to the backend | Listed because the deployed CORS configuration explicitly permits `*.vercel.app` origins. Confirm whether a Vercel-hosted frontend is in use for the beta. |
| **Airtable** *(only if configured)* | CRM — external sync of sales/lead records | Lead contact + pipeline data | Active **only** when the deployment sets `NC_CRM_PROVIDER=airtable` plus `NC_AIRTABLE_TOKEN` / `NC_AIRTABLE_BASE_ID` / `NC_AIRTABLE_TABLE_NAME`. Otherwise lead data stays in the local lead store and Airtable is **not** a subprocessor. Per the TODO, external CRM sync is not yet operational by default. |

## 2. Participant-directed LLM providers (Bring-Your-Own-Key)

When a participant runs an audit that calls a hosted LLM provider, the participant selects the provider and supplies their own API key (BYOK). That provider then processes the participant's request **under the provider's own terms and privacy policy**, not Noetic Compass's. The participant's API key is **ephemeral and never stored at rest** by CAS Harness (see `privacy_policy_DRAFT.md` §4).

The provider connectors implemented in the codebase (`api/llm_connectors/`), each gated on a participant-supplied key (`sync: false` in the deployment blueprint — not stored in committed configuration), are:

| Provider | Connector |
|---|---|
| OpenAI | `openai_connector.py` |
| Anthropic | `anthropic_connector.py` |
| Google | `google_connector.py` |
| Meta | `meta_connector.py` |
| xAI | `xai_connector.py` |
| DeepSeek | `deepseek_connector.py` |
| Qwen | `qwen_connector.py` |

A "mock" connector also exists for non-live/demo runs and calls no external provider. Only the provider(s) a participant actually selects on the BYOK path will process that participant's data; a participant who does not use a hosted provider does not engage any of these subprocessors.

## 3. What is NOT a subprocessor here

- The **open-weight models** a participant audits (for example Pythia, GPT-NeoX, OLMo, Qwen weights, or a participant-supplied checkpoint) are processed by the harness/worker compute, not sent to a third-party model-as-a-service, on the local/open-weight audit path.
- **BYOK API keys** are not stored at rest and are not shared with any subprocessor other than the provider the key belongs to, for the request that uses it.

## 4. Maintenance

This list must be kept current. Add a subprocessor here **before** it begins processing beta participant data, and confirm processing locations and data-processing agreements with counsel before any external publication.

---

**END — subprocessors_DRAFT.md — DRAFT for founder + qualified-counsel review. Not legal advice.**
