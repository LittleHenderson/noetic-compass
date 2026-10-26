# Worktree deletion log, 2026-10-20 (owner order: delete the clean, fully-on-GitHub worktrees)

Re-checked each worktree right before removal: 0 uncommitted files AND every commit on GitHub (`git branch -r --contains HEAD` non-empty). Skipped everything else. Kept the main checkout and the coordinator's live worktree `C:/tmp/helm-ctt2r-c49-read`.

**Deleted: 158. Skipped (dirty, local-only commits or unreadable): 148. Failed to remove: 2. Disk free before 8.1 GB, after 60.3 GB, freed 52.2 GB.**

## Deleted

| folder | branch | head | git note |
|---|---|---|---|
| C:/tmp/agent-b-live-session-evidence | codex/live-session-evidence | 16aaae26 | error: failed to delete '.git/worktrees/agent-b-live-session-evidence': Permission denied |
| C:/tmp/agent-c-verification-mode | codex/agent-c-verification-mode | 41e27181 | error: failed to delete '.git/worktrees/agent-c-verification-mode': Permission denied |
| C:/tmp/agent-e-live-verified-walkthrough | codex/agent-e-live-verified-walkthrough | 302a85d5 | error: failed to delete '.git/worktrees/agent-e-live-verified-walkthrough': Permission denied |
| C:/tmp/atlas-agent-d-scenarios | agent-d/alpha-scenarios-picker | 00a8276c | error: failed to delete '.git/worktrees/atlas-agent-d-scenarios': Permission denied |
| C:/tmp/atlas-evidence-api-base | fix/evidence-drawer-api-base | 78491454 | error: failed to delete '.git/worktrees/atlas-evidence-api-base': Permission denied |
| C:/tmp/atlas-evidence-only | cleanup/atlas-evidence-only | 7baca891 | error: failed to delete '.git/worktrees/atlas-evidence-only': Permission denied |
| C:/tmp/atlas-layer-detach | cockpit/layer-card-open-overlay | 20bff53a | error: failed to delete '.git/worktrees/atlas-layer-detach': Permission denied |
| C:/tmp/atlas-live-cockpit-integration | codex/atlas-live-cockpit-integration | 5033d8e2 | error: failed to delete '.git/worktrees/atlas-live-cockpit-integration': Permission denied |
| C:/tmp/atlas-live-knob-proof | codex/atlas-live-knob-proof | 936d3bf7 | error: failed to delete '.git/worktrees/atlas-live-knob-proof': Permission denied |
| C:/tmp/atlas-live-proof-panel-agent-a-20260525 | codex/live-proof-panel-agent-a | b2ecd0f3 | error: failed to delete '.git/worktrees/atlas-live-proof-panel-agent-a-20260525': Permission denied |
| C:/tmp/atlas-live-real-controls | atlas-live/real-controls | 2f2926f3 | error: failed to delete '.git/worktrees/atlas-live-real-controls': Permission denied |
| C:/tmp/atlas-live-realmode-proof | codex/atlas-live-realmode-proof | 1019cce5 | error: failed to delete '.git/worktrees/atlas-live-realmode-proof': Permission denied |
| C:/tmp/atlas-live-wire-up | codex/atlas-live-m3-m4 | 74d7b5a4 | error: failed to delete '.git/worktrees/atlas-live-wire-up': Permission denied |
| C:/tmp/atlas-preview-narrow-20260522 | codex/atlas-preview-narrow-20260522 | e9847f44 | error: failed to delete '.git/worktrees/atlas-preview-narrow-20260522': Permission denied |
| C:/tmp/atlas-scenario-proof | codex/atlas-scenario-proof | e9ad5724 | error: failed to delete '.git/worktrees/atlas-scenario-proof': Permission denied |
| C:/tmp/audit-pr47 | HEAD | 07f88d6f | error: failed to delete '.git/worktrees/audit-pr47': Permission denied |
| C:/tmp/audit-pr47-v2 | HEAD | 721416a9 | error: failed to delete '.git/worktrees/audit-pr47-v2': Permission denied |
| C:/tmp/audit-pr48 | HEAD | c564cba1 | error: failed to delete '.git/worktrees/audit-pr48': Permission denied |
| C:/tmp/audit-pr48-v2 | HEAD | 95e2b7c6 | error: failed to delete '.git/worktrees/audit-pr48-v2': Permission denied |
| C:/tmp/audit-pr49 | HEAD | 038ffe04 | error: failed to delete '.git/worktrees/audit-pr49': Permission denied |
| C:/tmp/audit-pr49-v2 | HEAD | 83ac67b1 | error: failed to delete '.git/worktrees/audit-pr49-v2': Permission denied |
| C:/tmp/audit-pr50 | HEAD | c6ac5ea2 | error: failed to delete '.git/worktrees/audit-pr50': Permission denied |
| C:/tmp/audit-pr50-v2 | HEAD | a40c8b40 | error: failed to delete '.git/worktrees/audit-pr50-v2': Permission denied |
| C:/tmp/audit-pr52-words | HEAD | b8d61e25 | error: failed to delete '.git/worktrees/audit-pr52-words': Permission denied |
| C:/tmp/audit-pr53-blindspots | HEAD | 80457d8f | error: failed to delete '.git/worktrees/audit-pr53-blindspots': Permission denied |
| C:/tmp/cas-1120-deployed | HEAD | 1120f552 | error: failed to delete '.git/worktrees/cas-1120-deployed': Permission denied |
| C:/tmp/cas-ab-audit-610c | HEAD | 610c6469 | error: failed to delete '.git/worktrees/cas-ab-audit-610c': Permission denied |
| C:/tmp/cas-acceptance-authority-publisher | codex/acceptance-authority-publisher | 9badf50e | error: failed to delete '.git/worktrees/cas-acceptance-authority-publisher': Permission denied |
| C:/tmp/cas-account-capability-handshake | codex/account-capability-handshake-20260714 | 570c92c9 | error: failed to delete '.git/worktrees/cas-account-capability-handshake': Permission denied |
| C:/tmp/cas-account-hardening | build/cas-account-hardening-20260712 | 010ea8f1 | error: failed to delete '.git/worktrees/cas-account-hardening': Permission denied |
| C:/tmp/cas-account-rollout-bridge | build/account-rollout-bridge-20260715 | 2fbce2da | error: failed to delete '.git/worktrees/cas-account-rollout-bridge': Permission denied |
| C:/tmp/cas-account-ui | build/cas-account-ui-20260712 | 0f17cb56 | error: failed to delete '.git/worktrees/cas-account-ui': Permission denied |
| C:/tmp/cas-af7-deployed | HEAD | af7c2f76 | error: failed to delete '.git/worktrees/cas-af7-deployed': Permission denied |
| C:/tmp/cas-alert-builder-production-binding | codex/alert-builder-production-binding-20260714 | d2fa71df | error: failed to delete '.git/worktrees/cas-alert-builder-production-binding': Permission denied |
| C:/tmp/cas-atlas-ci-flake-20260713 | fix/atlas-fleet-gate-determinism-20260713 | 6f362f05 | error: failed to delete '.git/worktrees/cas-atlas-ci-flake-20260713': Permission denied |
| C:/tmp/cas-attestation-failclosed | fix/attestation-store-failclosed-20260715 | 3ae950c2 | error: failed to delete '.git/worktrees/cas-attestation-failclosed': Permission denied |
| C:/tmp/cas-audit-console-visual | codex/audit-console-visual-command-center | 746dc6a2 | error: failed to delete '.git/worktrees/cas-audit-console-visual': Permission denied |
| C:/tmp/cas-billing-meter-dispatch | agent/billing-meter-dispatch | 963403ef | error: failed to delete '.git/worktrees/cas-billing-meter-dispatch': Permission denied |
| C:/tmp/cas-billing-reconciliation-v2 | codex/billing-reconciliation-v2-20260714 | 26e9e6c1 | error: failed to delete '.git/worktrees/cas-billing-reconciliation-v2': Permission denied |
| C:/tmp/cas-ci-worker-release-20260713 | fix/runpod-smoke-user-agent-20260713 | ffba0f9f | error: failed to delete '.git/worktrees/cas-ci-worker-release-20260713': Permission denied |
| C:/tmp/cas-claim-honesty-binding | fix/claim-honesty-binding-20260715 | 89b26f4e | error: failed to delete '.git/worktrees/cas-claim-honesty-binding': Permission denied |
| C:/tmp/cas-customer-hardening-post200 | integration/customer-production-hardening-post200-20260715 | cb66de70 | error: failed to delete '.git/worktrees/cas-customer-hardening-post200': Permission denied |
| C:/tmp/cas-customer-identity-lock | ops/customer-identity-lock-20260715 | d93cfa7e | error: failed to delete '.git/worktrees/cas-customer-identity-lock': Permission denied |
| C:/tmp/cas-customer-production-hardening-876e | agent/customer-production-machine-hardening-20260715 | 1bc4f4b4 | error: failed to delete '.git/worktrees/cas-customer-production-hardening-876e': Permission denied |
| C:/tmp/cas-customer-production-integration | integration/customer-production-hardening-20260715 | a9119e73 | error: failed to delete '.git/worktrees/cas-customer-production-integration': Permission denied |
| C:/tmp/cas-dashboard-account-migration-20260715 | build/dashboard-account-migration-20260715 | 2fbce2da | error: failed to delete '.git/worktrees/cas-dashboard-account-migration-20260715': Permission denied |
| C:/tmp/cas-dashboard-contextual-faq | codex/dashboard-contextual-faq | efec978f | error: failed to delete '.git/worktrees/cas-dashboard-contextual-faq': Permission denied |
| C:/tmp/cas-dashboard-declutter | codex/dashboard-declutter-copy | a1b1f220 | error: failed to delete '.git/worktrees/cas-dashboard-declutter': Permission denied |
| C:/tmp/cas-docs-master | docs/cas-harness-status-master-20260712 | 323fc177 | error: failed to delete '.git/worktrees/cas-docs-master': Permission denied |
| C:/tmp/cas-docs-status | docs/cas-harness-status-20260712 | e2719d59 | error: failed to delete '.git/worktrees/cas-docs-status': Permission denied |
| C:/tmp/cas-evidence-object-store-p0 | build/cas-evidence-object-store-20260713 | 9da07fbf | error: failed to delete '.git/worktrees/cas-evidence-object-store-p0': Permission denied |
| C:/tmp/cas-final-audit-f17 | HEAD | d8ac2f41 | error: failed to delete '.git/worktrees/cas-final-audit-f17': Permission denied |
| C:/tmp/cas-final-c73 | HEAD | c73afa8f | error: failed to delete '.git/worktrees/cas-final-c73': Permission denied |
| C:/tmp/cas-final-evidence-b911 | HEAD | b9110494 | error: failed to delete '.git/worktrees/cas-final-evidence-b911': Permission denied |
| C:/tmp/cas-final-master-1f5645e0 | HEAD | 1f5645e0 | error: failed to delete '.git/worktrees/cas-final-master-1f5645e0': Permission denied |
| C:/tmp/cas-final-master-c570 | HEAD | c570e375 | error: failed to delete '.git/worktrees/cas-final-master-c570': Permission denied |
| C:/tmp/cas-final-verification-20260715 | HEAD | d8e7edd0 | error: failed to delete '.git/worktrees/cas-final-verification-20260715': Permission denied |
| C:/tmp/cas-fleet-service-auth | build/cas-fleet-service-auth-20260713 | 1eaafd5a | error: failed to delete '.git/worktrees/cas-fleet-service-auth': Permission denied |
| C:/tmp/cas-harness-agent-c-m4 | codex/cas-harness-m4-license-api-flow | c0ebc84c | error: failed to delete '.git/worktrees/cas-harness-agent-c-m4': Permission denied |
| C:/tmp/cas-harness-agent-f-target-verify | agent-f-target-verify | ec2dc980 | error: failed to delete '.git/worktrees/cas-harness-agent-f-target-verify': Permission denied |
| C:/tmp/cas-harness-audit-flow | codex/audit-console-decision-flow | aa8fb5a5 | error: failed to delete '.git/worktrees/cas-harness-audit-flow': Permission denied |
| C:/tmp/cas-harness-beta-coord | codex/cas-harness-beta-coord | ec2dc980 | error: failed to delete '.git/worktrees/cas-harness-beta-coord': Permission denied |
| C:/tmp/cas-harness-evidence-packet-faq | codex/cas-harness-evidence-packet-faq | 0b263f91 | error: failed to delete '.git/worktrees/cas-harness-evidence-packet-faq': Permission denied |
| C:/tmp/cas-harness-m3-verifier-adapter | codex/cas-harness-m3-verifier-adapter | 6fcdab12 | error: failed to delete '.git/worktrees/cas-harness-m3-verifier-adapter': Permission denied |
| C:/tmp/cas-harness-master | fix/cas-harness-findings-20260630 | 3b126f24 | error: failed to delete '.git/worktrees/cas-harness-master': Permission denied |
| C:/tmp/cas-harness-model-target | codex/cas-harness-model-target | e10de60a | error: failed to delete '.git/worktrees/cas-harness-model-target': Permission denied |
| C:/tmp/cas-harness-rollout-docs | codex/cas-harness-rollout-docs | 013bb1f8 | error: failed to delete '.git/worktrees/cas-harness-rollout-docs': Permission denied |
| C:/tmp/cas-harness-smoke-fix | fix/evidence-smoke-honesty | d44f3d56 | error: failed to delete '.git/worktrees/cas-harness-smoke-fix': Permission denied |
| C:/tmp/cas-harness-verdict-explainer-ui | codex/cas-harness-verdict-explainer-ui | a529ae8d | error: failed to delete '.git/worktrees/cas-harness-verdict-explainer-ui': Permission denied |
| C:/tmp/cas-harness-worker-token | launch/worker-token-send | 95737b86 | error: failed to delete '.git/worktrees/cas-harness-worker-token': Permission denied |
| C:/tmp/cas-helm-dictionary | claude/cas-helm-dictionary-20261019 | 13b45feb |  |
| C:/tmp/cas-hosted-customer-journey-probe | codex/hosted-customer-journey-probe-20260714 | a2b1b526 | error: failed to delete '.git/worktrees/cas-hosted-customer-journey-probe': Permission denied |
| C:/tmp/cas-identity-claim-assurance | fix/identity-claim-assurance-20260715 | 03a6a5ff | error: failed to delete '.git/worktrees/cas-identity-claim-assurance': Permission denied |
| C:/tmp/cas-master-876e8a6d | HEAD | 876e8a6d | error: failed to delete '.git/worktrees/cas-master-876e8a6d': Permission denied |
| C:/tmp/cas-master-bc9 | fix/root-ci-volatile-repository-field-20260715 | 602d5958 | error: failed to delete '.git/worktrees/cas-master-bc9': Permission denied |
| C:/tmp/cas-mode7-trace-fix | fix/mode7-final-trace-20260712 | 9ea1d13a | error: failed to delete '.git/worktrees/cas-mode7-trace-fix': Permission denied |
| C:/tmp/cas-postdeploy-52f80ec0-src | HEAD | 52f80ec0 | error: failed to delete '.git/worktrees/cas-postdeploy-52f80ec0-src': Permission denied |
| C:/tmp/cas-postdeploy-f475bff6 | HEAD | f475bff6 | error: failed to delete '.git/worktrees/cas-postdeploy-f475bff6': Permission denied |
| C:/tmp/cas-provider-reconcile-p0 | build/cas-provider-reconcile-20260713 | 4c475f0e | error: failed to delete '.git/worktrees/cas-provider-reconcile-p0': Permission denied |
| C:/tmp/cas-quota-post-fix-20260713 | codex/fix-account-canary-post-proof | c962af3f | error: failed to delete '.git/worktrees/cas-quota-post-fix-20260713': Permission denied |
| C:/tmp/cas-quota-proof-boundary-20260713 | agent/quota-proof-boundary-20260713 | 1aa56858 | error: failed to delete '.git/worktrees/cas-quota-proof-boundary-20260713': Permission denied |
| C:/tmp/cas-render-ipallowlist-fix | fix/render-postgres-ipallowlist-null-20260715 | a081e329 | error: failed to delete '.git/worktrees/cas-render-ipallowlist-fix': Permission denied |
| C:/tmp/cas-render-live-drift-20260713 | agent/render-live-service-drift-20260713 | 179cb1ca | error: failed to delete '.git/worktrees/cas-render-live-drift-20260713': Permission denied |
| C:/tmp/cas-root-ci-freshness | fix/root-ci-proof-freshness-20260715 | fbe89b88 | error: failed to delete '.git/worktrees/cas-root-ci-freshness': Permission denied |
| C:/tmp/cas-runpod-master | grok/model-provenance-packet | fc0e6360 | error: failed to delete '.git/worktrees/cas-runpod-master': Permission denied |
| C:/tmp/cas-runtime-freshness | fix/runtime-proof-freshness-20260715 | 8aa81f8b | error: failed to delete '.git/worktrees/cas-runtime-freshness': Permission denied |
| C:/tmp/cas-source-bound-identities | fix/source-bound-acceptance-pseudonyms-20260715 | dbdefb50 | error: failed to delete '.git/worktrees/cas-source-bound-identities': Permission denied |
| C:/tmp/cas-tenant-scoped-bootstrap-20260715 | fix/tenant-scoped-bootstrap-20260715 | 716c7e8e | error: failed to delete '.git/worktrees/cas-tenant-scoped-bootstrap-20260715': Permission denied |
| C:/tmp/cas-ui-launch | build/cas-ui-launch-20260712 | 9d4f6aa5 | error: failed to delete '.git/worktrees/cas-ui-launch': Permission denied |
| C:/tmp/harness-master-verify | harness/console-real-stage9-accept | d0e3f60c | error: failed to delete '.git/worktrees/harness-master-verify': Permission denied |
| C:/tmp/helm-continuity-packet | claude/helm-continuity-packet-20261020 | 328930e9 |  |
| C:/tmp/helm-design-packets | claude/design-packets-ear-shape-eye-cells-20261020 | fb8f0831 |  |
| C:/tmp/helm-hub | claude/helm-hub-w6-result-20261020 | 86d0e88d |  |
| C:/tmp/helm-lmt4-rerun | claude/helm-lmt4-rerun-sealed-reader-20261020 | 644b1f65 |  |
| C:/tmp/helm-lmt4c | claude/helm-lmt4c-cont3-fix-20261020 | 699e30e6 |  |
| C:/tmp/helm-w7v4 | claude/helm-r1w7-v4-reader-repair-20261020 | 69bd1106 |  |
| C:/tmp/paid-security-master-audit | HEAD | 79c0cdb9 | error: failed to delete '.git/worktrees/paid-security-master-audit': Permission denied |
| C:/tmp/pr38-audit | codex/pr-38-audit | 7c3fc4f7 | error: failed to delete '.git/worktrees/pr38-audit': Permission denied |
| C:/tmp/pythia-audit | HEAD | e1c3098a | error: failed to delete '.git/worktrees/pythia-audit': Permission denied |
| C:/tmp/pythia-reaudit | HEAD | 81318479 | error: failed to delete '.git/worktrees/pythia-reaudit': Permission denied |
| C:/tmp/r1w6-v3-reseal | claude/helm-r1w6-v3-reseal-20261020 | be7cb9af |  |
| C:/tmp/xreal-stock-frame-fix | claude/xreal-stock-frame-fix-20261019 | 60524b6f |  |
| C:/Users/wakil/.codex/worktrees/0c81/tksCAS | HEAD | eb3c9b1e |  |
| C:/Users/wakil/.codex/worktrees/b442/tksCAS | HEAD | 61c8bad7 | error: failed to delete '.git/worktrees/tksCAS': Permission denied |
| C:/Users/wakil/.codex/worktrees/ca0f/tksCAS | codex/project-coherence-cas-core | fbac9909 | error: failed to delete '.git/worktrees/tksCAS8': Permission denied |
| C:/Users/wakil/_nc_login_fix | fix/validation-redaction | 920c2a95 |  |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/evidence_coverage_dispersion_stage1 | codex/evidence-coverage-dispersion-stage1 | e541355f | error: failed to delete '.git/worktrees/evidence_coverage_dispersion_stage1': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_gate5_clean_a | HEAD | e0405bf5 | error: failed to delete '.git/worktrees/project_coherence_gate5_clean_a': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_gate5_receipt_b | HEAD | c1f06f44 | error: failed to delete '.git/worktrees/project_coherence_gate5_receipt_b': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_gate5_receipt_replay | HEAD | 1c837422 | error: failed to delete '.git/worktrees/project_coherence_gate5_receipt_replay': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_gate5_successor | codex/project-coherence-gate5-successor | 1c837422 | error: failed to delete '.git/worktrees/project_coherence_gate5_successor': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_publication/category | codex/project-coherence-publication-category | 643169e9 | error: failed to delete '.git/worktrees/category': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_publication/engineering | codex/project-coherence-publication-engineering | c8635270 | error: failed to delete '.git/worktrees/engineering': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_publication/formal | codex/project-coherence-publication-formal | 3c8491db | error: failed to delete '.git/worktrees/formal': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_publication/integration | codex/project-coherence-publication-integration | fde98f55 | error: failed to delete '.git/worktrees/integration1': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_publication/review_category | codex/project-coherence-review-category | c2e96622 | error: failed to delete '.git/worktrees/review_category': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_publication/review_formal | codex/project-coherence-review-formal | b613c249 | error: failed to delete '.git/worktrees/review_formal': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_publication/review_lead_corrections | codex/project-coherence-review-lead-corrections | 64d02d20 | error: failed to delete '.git/worktrees/review_lead_corrections': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_publication/verify_c1_0f5e46c1 | HEAD | 0f5e46c1 | error: failed to delete '.git/worktrees/verify_c1_0f5e46c1': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_publication/verify_c2_fde98f55 | HEAD | fde98f55 | error: failed to delete '.git/worktrees/verify_c2_fde98f55': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_publication/wave2_acbe | codex/project-coherence-wave2-acbe | f1decd9c | error: failed to delete '.git/worktrees/wave2_acbe': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_publication/wave2_harness | codex/project-coherence-wave2-harness | 6b3e72dc | error: failed to delete '.git/worktrees/wave2_harness': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_publication/wave2_memristive | codex/project-coherence-wave2-memristive | 4666004e | error: failed to delete '.git/worktrees/wave2_memristive': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/runpod_canary_workflow_default_20260820 | codex/runpod-canary-stop-supervisor-default-v2-20260820 | f4e5ff16 | error: failed to delete '.git/worktrees/runpod_canary_workflow_default_20260820': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/runpod_workflow_sync_20260820 | codex/runpod-canary-supervisor-v3 | d110dc64 | error: failed to delete '.git/worktrees/runpod_workflow_sync_20260820': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-27/heyu/work/ccb-r1-m1-fix | codex/ccb-r1-m1-w-step-parser | bf369d61 | error: failed to delete '.git/worktrees/ccb-r1-m1-fix': Permission denied |
| C:/Users/wakil/Documents/Codex/2026-08-27/heyu/work/ccb-r1-stage5-integration | codex/ccb-r1-stage5-diagnostics-integration | d8ec05a5 | error: failed to delete '.git/worktrees/ccb-r1-stage5-integration': Permission denied |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/audit-identity | launch/paid-audit-identity | f82920b6 | error: failed to delete 'C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/audit-identity': Permission denied
err |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/helm-ui-v0 | claude/helm-ui-v0-20261019 | ec208d5d |  |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/launch-scoped-beta | launch/scoped-beta | fdb4c401 | error: failed to delete 'C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/launch-scoped-beta': Permission denied |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/paid-security-spine | launch/paid-security-spine | a50c9681 | error: failed to delete 'C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/paid-security-spine': Permission denie |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/tenant-iso | launch/paid-tenant-isolation | cd4d9801 | error: failed to delete 'C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/tenant-iso': Permission denied
error:  |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.tmp/audit_ccb_r1/pr219_worktree | HEAD | d8ec05a5 | error: failed to delete 'C:/Users/wakil/OneDrive/Desktop/tksCAS/.tmp/audit_ccb_r1/pr219_worktree': Permission denied
err |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.tmp/cas-billing-entitlement-p0 | build/cas-billing-entitlement-20260713 | a8ad0ac2 | error: failed to delete 'C:/Users/wakil/OneDrive/Desktop/tksCAS/.tmp/cas-billing-entitlement-p0': Permission denied
erro |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.tmp/cas-p0-integration-20260713 | build/cas-p0-integration-20260713 | 5be479ff | error: failed to delete 'C:/Users/wakil/OneDrive/Desktop/tksCAS/.tmp/cas-p0-integration-20260713': Permission denied
err |
| D:/tksCAS-worktrees/cas-lean-check | claude/cas-lean-check-20261001 | f58d1c82 |  |
| D:/tksCAS-worktrees/docs-catchup-20261018 | claude/docs-catchup-20261018 | 4c30f028 |  |
| D:/tksCAS-worktrees/docs-dwp-20261018 | claude/docs-dwp-20261018 | d5e4b5c0 |  |
| D:/tksCAS-worktrees/docs-policy-v02-20261016b | claude/policy-v02-docs-20261016 | 9f022a47 |  |
| D:/tksCAS-worktrees/docs-r1x0-m1v5-20261016 | claude/r1x0-m1v5-docs-20261016 | ac554043 |  |
| D:/tksCAS-worktrees/docs-rb1g2-20261014 | claude/rb1g2-docs-20261014 | 153f0630 |  |
| D:/tksCAS-worktrees/docs-rb2b-20261014 | claude/rb2b-docs-20261014 | b1d91220 |  |
| D:/tksCAS-worktrees/docs-rb2c-20261014 | claude/rb2c-docs-20261014 | 6469b887 |  |
| D:/tksCAS-worktrees/docs-rb3-20261015 | claude/rb3-docs-20261015 | d67becdf |  |
| D:/tksCAS-worktrees/docs-rbw-20261015 | claude/rbw-docs-20261015 | f5e9a9a2 |  |
| D:/tksCAS-worktrees/docs-u3-t1-20261019 | claude/u3-t1-result-20261019 | 70fc191e |  |
| D:/tksCAS-worktrees/docs-w3-erratum-20261019 | claude/docs-w3-erratum-20261019 | 7debee3e |  |
| D:/tksCAS-worktrees/english-in-20261018 | claude/english-in-20261018 | 9916ad2b |  |
| D:/tksCAS-worktrees/lexicon-20261018 | claude/lexicon-20261018 | 927a3360 |  |
| D:/tksCAS-worktrees/r1-wave2-20261018 | claude/r1-wave2-20261018 | bcc46a29 |  |
| D:/tksCAS-worktrees/r1-wave3-20261019 | claude/r1-wave3-v3-20261019 | 307f8829 |  |
| D:/tksCAS-worktrees/r1-wave3b-20261019 | claude/r1-wave3b-20261019 | ea2d9485 |  |
| D:/tksCAS-worktrees/rb-g8-docs-20261019 | docs/rb-g8-curiosity-growth-20261019 | d04edc21 |  |
| D:/tksCAS-worktrees/rbi1c-c36-20261019 | claude/rbi1c-c36-result-20261019 | 992ce5d0 |  |
| D:/tksCAS-worktrees/rbw1-dishname-fix-20261020 | claude/rbw1t-v3-reseal-20261020 | 0d2ef1c3 |  |
| D:/tksCAS-worktrees/rbw1t-20261019 | claude/rbw1t-v2-reseal-20261019 | 7b2368b8 |  |
| D:/tksCAS-worktrees/rbw1t-c46-20261020 | claude/rbw1t-c46-result-20261020 | f80594d9 |  |
| D:/tksCAS-worktrees/rbw1t-v3-c47-20261020 | claude/rbw1t-v3-c47-result-20261020 | 25894a3c |  |

## Skipped (not touched)

| folder | branch | head | dirty files | on GitHub |
|---|---|---|---|---|
| C:/tmp/atlas-badge-truth | fix/atlas-live-badge-truth | 07cc93a9 | 0 | no |
| C:/tmp/atlas-live-all7 | codex/live-all7-scope | 7490a51f | 0 | no |
| C:/tmp/atlas-live-browser-proof | codex/agent-a-live-browser-proof | 4de94c98 | 2 | no |
| C:/tmp/atlas-live-failure-cleanup | codex/live-failure-cleanup | cd8ab9d8 | 0 | no |
| C:/tmp/atlas-live-final-proof | codex/atlas-live-final-proof | 69b70d32 | 0 | no |
| C:/tmp/atlas-live-hardening | codex/atlas-live-hardening | 599ad567 | 0 | no |
| C:/tmp/atlas-live-m2 | pr-43-live-m2 | 0ae81616 | 0 | no |
| C:/tmp/atlas-live-proof-panel | fix/atlas-live-proof-panel | 090696ac | 0 | no |
| C:/tmp/atlas-method-knob-audit | codex/live-method-knob-truth | 56f47f7c | 0 | no |
| C:/tmp/atlas-runpod-persistence-packaging | codex/runpod-persistence-packaging | adcce47d | 6 | yes |
| C:/tmp/audit-pr54-integration | HEAD | 98f4f6b3 | 0 | no |
| C:/tmp/audit-pr54-integration-v2 | HEAD | 41e2a7ba | 0 | no |
| C:/tmp/cas-accept-auth-plane-20260715 | build/acceptance-authorization-plane-20260715 | 48df0713 | 0 | no |
| C:/tmp/cas-acceptance-authority-f475bff6 | build/acceptance-authority-plane-20260714 | 75c2e73e | 0 | no |
| C:/tmp/cas-account-canary-quotas-20260713 | fix/account-canary-quotas-20260713 | 4c32883b | 0 | no |
| C:/tmp/cas-accounts-canary-20260713 | fix/ci-runner-cleanup-20260713 | d827bd1c | 0 | no |
| C:/tmp/cas-actions-node24-20260713 | agent/actions-node24-runtime | a2ecb011 | 0 | no |
| C:/tmp/cas-alert-delivery-adapter | build/alert-delivery-adapter-20260714 | da6da001 | 0 | no |
| C:/tmp/cas-alert-delivery-drill-b911 | build/alert-delivery-drill-20260715 | 472397ac | 0 | no |
| C:/tmp/cas-alert-hostile-review-7c30c7d-20260716-1229 | HEAD | 7c30c7d1 | 0 | no |
| C:/tmp/cas-alert-review-da6 | HEAD | da6da001 | 0 | no |
| C:/tmp/cas-alert-root-receipt-876e | fix/alert-drill-root-receipt-20260715 | 7c30c7d1 | 0 | no |
| C:/tmp/cas-alert-root-receipt-exact-7c30c7d1 | HEAD | 7c30c7d1 | 0 | no |
| C:/tmp/cas-alert-secondary-drill-1120 | codex/alert-secondary-drill-20260714 | 4aad7fbd | 0 | no |
| C:/tmp/cas-atlas-prerender-20260714 | build/atlas-static-claim-surfaces-20260714 | 09457347 | 0 | no |
| C:/tmp/cas-atlas-viewer-prerender-port-52f80ec | build/atlas-viewer-prerender-port-20260714 | 714e190f | 0 | no |
| C:/tmp/cas-attestation-binding-876e8a6d-a1 | codex/attestation-temporal-binding-hardening-20260715 | 9c03027d | 0 | no |
| C:/tmp/cas-audit-declutter | codex/audit-console-declutter-hover | b1cd04b8 | 0 | no |
| C:/tmp/cas-audit-legal-20260719 | codex/claims-remediation-20260719 | d6069513 | 0 | no |
| C:/tmp/cas-audit-master-20260719 | codex/audit-remediation-20260719 | 846ee041 | 0 | no |
| C:/tmp/cas-billing-audit-ca8 | HEAD | ca8c2efb | 0 | no |
| C:/tmp/cas-billing-hardening-b911 | fix/accounts-billing-invoice-receipt-20260715 | 54bb65aa | 0 | no |
| C:/tmp/cas-billing-lineage-876e8a6d | fix/billing-lineage-revalidation-20260715 | b87cb240 | 0 | no |
| C:/tmp/cas-billing-usage-reconciliation-af7 | codex/billing-usage-reconciliation-20260714 | 44529a4e | 4 | no |
| C:/tmp/cas-claim-evidence-20260714-redteam | codex/claim-honesty-machine-evidence-20260714 | 4d5bbfe2 | 0 | no |
| C:/tmp/cas-claim-legal-surfaces-20260714 | agent/claim-legal-surfaces-20260714 | c6bc9366 | 0 | no |
| C:/tmp/cas-crm-acceptance-binding-bc42 | agent/crm-acceptance-binding-20260715 | e9e77041 | 0 | no |
| C:/tmp/cas-crm-airtable-verifiable-1120 | codex/crm-airtable-verifiable-20260714 | 1cf77c70 | 0 | no |
| C:/tmp/cas-customer-accept-integration-20260714 | build/customer-production-accept-integration-20260714 | c1efc256 | 1 | no |
| C:/tmp/cas-customer-crm-blueprint-20260715 | build/customer-crm-blueprint-20260715 | ce24ecdf | 0 | no |
| C:/tmp/cas-customer-prod-machine-hardening | fix/customer-production-machine-hardening-20260714 | 3e60277c | 0 | no |
| C:/tmp/cas-customer-production-pseudonyms | fix/customer-production-pseudonyms-20260715 | dc93e427 | 2 | yes |
| C:/tmp/cas-customer-readiness-facts-20260714 | agent/customer-readiness-facts-20260714 | bca768ee | 0 | no |
| C:/tmp/cas-dependency-readiness-20260713 | fix/production-dependency-readiness-20260713 | 70297f6b | 0 | no |
| C:/tmp/cas-disabled-account-401 | codex/disabled-account-401-contract-20260714 | 6ff582b3 | 0 | no |
| C:/tmp/cas-final-9cffb816 | fix/evidence-clock-skew-20260715 | 7bed8d8d | 0 | no |
| C:/tmp/cas-final-accept-bundle-20260715 | build/final-accept-bundle-assembler-20260715 | e2dc1ee6 | 0 | no |
| C:/tmp/cas-final-corrective-20260714 | fix/production-host-corrective-20260714 | e60e1da3 | 1 | no |
| C:/tmp/cas-final-dc9 | HEAD | dc9d6c61 | 4 | yes |
| C:/tmp/cas-final-master-bc42 | build/public-customer-lane-20260715 | 6153a984 | 0 | no |
| C:/tmp/cas-harness-audit-connect-panel | codex/audit-console-connect-panel | ec2dc980 | 2 | yes |
| C:/tmp/cas-harness-enterprise-scale | codex/audit-console-evidence-faq | 4022969f | 0 | no |
| C:/tmp/cas-harness-live-run | codex/cas-harness-live-run | f32a6509 | 2 | yes |
| C:/tmp/cas-harness-m2-bridge-rebased | codex/cas-harness-m2-evidence-bridge-rebased | 5d6ca95d | 0 | no |
| C:/tmp/cas-harness-m2-evidence-bridge | codex/cas-harness-m2-evidence-bridge | 8e1a6983 | 0 | no |
| C:/tmp/cas-harness-m2-route-wire | codex/cas-harness-m2-route-wire | c32ae948 | 0 | no |
| C:/tmp/cas-harness-m3-verdict-runner | codex/cas-harness-m3-verdict-runner | 36b3737a | 5 | no |
| C:/tmp/cas-harness-moniker | codex/cas-harness-moniker | 6c07850c | 0 | no |
| C:/tmp/cas-harness-operational | build/cas-harness-operational-20260712 | c332de2a | 0 | no |
| C:/tmp/cas-harness-prod-goal-20260828 | codex/cas-harness-prod-goal-20260828 | cc392f5e | 53 | yes |
| C:/tmp/cas-harness-runner-packet | codex/evidence-root-robust | c59f504c | 0 | no |
| C:/tmp/cas-hosted-journey-deploy-binding-20260715 | build/hosted-journey-deploy-binding-20260715 | 564aafe5 | 0 | no |
| C:/tmp/cas-hosted-runtime-wrapper | fix/hosted-runtime-worm-wrapper-20260715 | cca436fe | 0 | no |
| C:/tmp/cas-human-attestation-plane | build/human-attestation-plane-20260715 | 96973d1f | 0 | no |
| C:/tmp/cas-incident-response-20260713 | docs/cas-incident-response-20260713 | 0f335a90 | 0 | no |
| C:/tmp/cas-journey-cleanup-atomic-b911 | fix/hosted-journey-cleanup-atomic-20260715 | 63642a52 | 0 | no |
| C:/tmp/cas-journey-clock-fix | fix/hosted-journey-clock-order-20260715 | e89442f0 | 0 | no |
| C:/tmp/cas-landing-support-contract-20260715 | build/landing-support-contract-20260715 | 32f331e6 | 0 | no |
| C:/tmp/cas-live-pythia-target | fix/live-pythia-target-20260715 | 91af3292 | 0 | no |
| C:/tmp/cas-live-run-realmode-p1 | agent/hosted-run-realmode-enforcement | 249c15fe | 0 | no |
| C:/tmp/cas-master-553 | integration/source-bound-acceptance-privacy-20260715 | cde46699 | 0 | no |
| C:/tmp/cas-master-merge-634b797 | codex/atlas-merge-634b797 | 086a8784 | 0 | no |
| C:/tmp/cas-ops-evidence-20260714 | build/ops-evidence-gates-20260714 | 6635be13 | 0 | no |
| C:/tmp/cas-pr196-review-96973d1 | HEAD | 96973d1f | 0 | no |
| C:/tmp/cas-pr198-review | HEAD | 91af3292 | 0 | no |
| C:/tmp/cas-prod-accept-20260714 | build/customer-production-next-20260714 | 3e4b884e | 0 | no |
| C:/tmp/cas-provider-contract-c570 | codex/provider-contract-env-slots | 5d52574d | 0 | no |
| C:/tmp/cas-realmode-integrity-independent | agent/realmode-integrity-independent-20260715 | c7a77dde | 0 | no |
| C:/tmp/cas-render-ipallowlist-readback | ops/render-ipallowlist-readback-20260715 | 220fe29a | 0 | no |
| C:/tmp/cas-render-live-retry-610c | codex/render-live-retry | 065a4adc | 0 | no |
| C:/tmp/cas-render-storage-headroom-20260715 | build/render-storage-headroom-20260715 | eaed5a15 | 0 | no |
| C:/tmp/cas-root-ci-facts-20260714 | build/root-ci-authoritative-facts-20260714 | bd84a0a2 | 0 | no |
| C:/tmp/cas-runtime-packet-fix-20260715 | fix/runtime-packet-binding-20260715 | ae8d00c3 | 0 | no |
| C:/tmp/cas-runtime-worm-evidence | build/runtime-worm-evidence-20260715 | c428dada | 0 | no |
| C:/tmp/cas-service-updated-ci-fix | agent/root-ci-service-updated-successor-20260715 | b9b40d3a | 2 | yes |
| C:/tmp/cas-share-lifecycle-20260714 | build/evidence-share-lifecycle-20260714 | 9aa50578 | 0 | no |
| C:/tmp/cas-share-projection-fix-20260715 | fix/shared-packet-projection-20260715 | 75d9b45b | 0 | no |
| C:/tmp/cas-shared-crm-support-store-20260715 | build/shared-crm-support-store-20260715 | e05264d1 | 0 | no |
| C:/tmp/cas-stripe-audit-360b | agent/billing-safety-tranche-1 | e9821f36 | 0 | no |
| C:/tmp/cas-support-privacy-guard-20260715 | fix/support-privacy-guard-20260715 | f036ad8e | 0 | no |
| C:/tmp/cas-tooltip-popovers | codex/audit-tooltip-popovers | 3092540a | 0 | no |
| C:/tmp/cas-worker-hardening | fix/cas-harness-worker-deploy-20260712 | 99668500 | 1 | yes |
| C:/tmp/cas-worm-retention-guard-20260714 | fix/worm-retention-acceptance-guard-20260714 | 5c3335be | 0 | no |
| C:/tmp/cas-worm-smoke-receipt | fix/structured-object-lock-smoke | a3f3aa28 | 0 | no |
| C:/tmp/cascompass-postdeploy-fix-20260714 | fix/cascompass-postdeploy-20260714 | 60acff94 | 0 | no |
| C:/tmp/codex-pr54-blindspots-20260524 | HEAD | 41e2a7ba | 2 | no |
| C:/tmp/evidence-merge | master | 4c9e0ac4 | 1 | yes |
| C:/tmp/fix-pr54-blindspot-ux | fix/pr54-blindspot-ux | 84c8a149 | 0 | no |
| C:/tmp/helm-k4-fix | claude/helm-wide-k4-relative-amount-20261020 | a732270b | 1 | yes |
| C:/tmp/tksCAS-cjt-ohm-cleanroom-reset-v1 | research/cjt-ohm-cleanroom-reset-v1 | 9d9fcfc9 | 9 | yes |
| C:/tmp/wave-5-integration | cockpit/wave-5-integration | d1b60e08 | 0 | no |
| C:/Users/wakil/.codex/worktrees/06fb/tksCAS | codex/tks-672-v3-corpus-lock | 130168b3 | 0 | no |
| C:/Users/wakil/.codex/worktrees/1266/tksCAS | HEAD | 4fc2bce2 | 0 | no |
| C:/Users/wakil/.codex/worktrees/8c0d/tksCAS | codex/tks-672-v8-full-cohort-lock | 9d68e028 | 0 | no |
| C:/Users/wakil/.codex/worktrees/955c/tksCAS | codex/gpt2-medium-phase1-runtime-v2 | 75d761e6 | 1 | no |
| C:/Users/wakil/.codex/worktrees/9a75/tksCAS | codex/tks-672-v8-scoring-readout-lock | 3be0c6a4 | 0 | no |
| C:/Users/wakil/.codex/worktrees/a06c/tksCAS | codex/readability-first-phase1-model-successor | e1c6609c | 0 | no |
| C:/Users/wakil/.codex/worktrees/f939/tksCAS | codex/tks-672-v8-condition-f-reconciliation | f4a5cc89 | 4 | no |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/cas_interpretability_successor_20260820 | codex/cas-interpretability-successor-v2 | 75bae3e2 | 5 | yes |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_model_smoke | codex/project-coherence-model-smoke | 96778baa | 6 | yes |
| C:/Users/wakil/Documents/Codex/2026-08-05/referenced-chatgpt-conversation-this-is-an/work/project_coherence_publication/review_engineering | codex/project-coherence-review-engineering | 15a3ff34 | 2 | yes |
| C:/Users/wakil/Documents/Codex/2026-08-27/heyu/work/ccb-r1-b4-fix | codex/ccb-r1-b4-answer-fix | 09cda29f | 0 | no |
| C:/Users/wakil/Documents/Codex/2026-08-27/heyu/work/ccb-r1-m2-diagnostics | codex/ccb-r1-m2-diagnostics | 567a7b57 | 0 | no |
| C:/Users/wakil/Documents/Codex/2026-08-27/heyu/work/ccb-r1-source-improvements | codex/ccb-r1-source-grounded-improvements | 7bf122a8 | 8 | no |
| C:/Users/wakil/Documents/Codex/2026-08-28/cas-production-closure | codex/cas-production-closure | cc392f5e | 5 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/agent-a0b66cbc93a6a2844 | worktree-agent-a0b66cbc93a6a2844 | a9f519be | 21 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/agent-a26292ec9850bf384 | worktree-agent-a26292ec9850bf384 | a9f519be | 3 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/agent-a379f95002b9162d7 | worktree-agent-a379f95002b9162d7 | a9f519be | 9 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/agent-a3e73120e5007ea28 | fix-auth-mint | 4c9e0ac4 | 7 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/agent-a53fd9575b2d88bbb | cockpit/interpretable-blindspots | 80457d8f | 1 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/agent-a6ec6e61e429eede6 | claude/lexicon-v3-nomap-20261019 | f872c879 | 3 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/agent-a78530c6ee1cd4c09 | worktree-agent-a78530c6ee1cd4c09 | a9f519be | 7 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/agent-a7f4caed3ad56fe55 | claude/noetic-drift-fix-20261019 | fd80b8fa | 1 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/agent-a90738f72f6022438 | feat/clickable-word-spans | b8d61e25 | 1 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/agent-aae77f3097dea1b9c | fix-tenant-scope | 4c9e0ac4 | 4 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/agent-ad4736a9a7b589626 | claude/helm-chat-defects-20261019 | e00d1618 | 1 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/integration | codex/cas-harness-public-beta-candidate | f8a72008 | 3 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/paid-security-sessions | launch/paid-security-sessions | 19a31a16 | 2 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/quotas-engine | launch/paid-quotas | 6dfccb9d | 4 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/stateless-audit | launch/stateless-audit-sessions | 4c9e0ac4 | 3 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.claude/worktrees/ui-audit-bench | launch/ui-audit-bench | 136e32ec | 1 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.tmp/cas-account-mode7-verify | HEAD | aeb86374 | 0 | no |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/.tmp/cas-evidence-object-store-verify | HEAD | 9da07fbf | 1 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/contrast-v6-audit-acbb266f | HEAD | acbb266f | 1 | no |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/contrast-v7-audit-80e44f20 | HEAD | 80e44f20 | 3 | no |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1 | codex/cas-meta-2-composition | 06d95cb0 | 461 | no |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta3-audit-63f5b421 | HEAD | 63f5b421 | 2 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta3_audit_8b5d8ac9 | HEAD | 8b5d8ac9 | 6 | yes |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/prototype-v7-audit-246f490d | HEAD | 246f490d | 0 | no |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/prototype-v7-audit-42f91647 | HEAD | 42f91647 | 2 | no |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/prototype-v7-audit-4bbb9162 | HEAD | 4bbb9162 | 3 | no |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/recovery-v6-audit-bd3341b0 | HEAD | bd3341b0 | 2 | no |
| C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/recovery-v6-audit-cbf13795 | HEAD | cbf13795 | 1 | no |
| D:/tksCAS-worktrees/docs-r1w1-wave1-20261016 | claude/noetic-language-v3 | 6cabe709 | 2 | yes |
| D:/tksCAS-worktrees/repair-performer-20261017 | verify-consolidated | 3332ae36 | 2 | yes |
| D:/tksCAS-worktrees/triad-20261018 | claude/triad-adapter-20261018 | 014e4976 | 2 | yes |
| D:/tksCAS-worktrees/voice-20261018 | claude/voice-20261018 | 169dd4e4 | 2 | yes |
| D:/tksCAS-worktrees/wire-recipe-brain-20261018 | claude/wire-recipe-brain-20261018 | 99ff8721 | 2 | yes |

## Failed to remove

| folder | branch | head | error |
|---|---|---|---|
| C:/tmp/self-reference-review | proposal/self-reference-lever | c09b5986 | error: failed to delete 'C:/tmp/self-reference-review': Directory not empty
error: failed to delete '.git/worktrees/self |
| C:/Users/wakil/.codex/worktrees/da21/tksCAS | codex/cas-closed-loop-1-recovery-20260925 | 318b22ad | error: failed to delete 'C:/Users/wakil/.codex/worktrees/da21/tksCAS': Directory not empty |

## Retry of the two failed removals

- C:\tmp\self-reference-review: left in place: not on GitHub
- C:\Users\wakil\.codex\worktrees\da21\tksCAS: left in place: not on GitHub

Free on C: after retry: 60.3 GB

Second retry (the two were half-removed remnants with no .git link; their pre-deletion heads re-checked on GitHub from the main repo):
- C:\tmp\self-reference-review: STILL PRESENT (locked)
- C:\Users\wakil\.codex\worktrees\da21\tksCAS: STILL PRESENT (locked)
Free on C: 60.3 GB
