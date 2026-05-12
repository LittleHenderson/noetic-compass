# Agent Exchange Protocol

Shared handoff between Claude (in this Claude Code session) and Codex (audit/advisor in user's other agent context). Replaces user copy-paste between agents.

## Files

| File | Owner | Purpose |
|---|---|---|
| `inbox_claude.md` | Claude writes | Proposals, results, in-progress state, "open request" for Codex |
| `codex_audit.md` | Codex writes | Audit findings, patches, blocking objections, sign-offs |
| `decisions.md` | Both write (append-only) | Confirmed user-ratified decisions ONLY. Append, never edit existing entries. |

## Rules

1. **Claude writes proposal/result** in `inbox_claude.md`.
2. **User tells Codex:** "audit docs/working/agent_exchange/inbox_claude.md."
3. **Codex reads, writes** audit findings into `codex_audit.md`.
4. **User tells Claude:** "read codex's audit" (or Claude grep/reads `codex_audit.md` directly when relevant).
5. **No pod launch** unless `decisions.md` contains an `AUTHORIZED: yes` line **AND** the user also says "launch" / "go" in chat. Both required.
6. **Decisions only count if they appear in `decisions.md`** — anything in inbox or audit is proposal/discussion, not commitment.

## Naming conventions inside files

Each entry starts with an ISO-8601 timestamp + author tag:

```
## 2026-05-12T20:50Z — claude: <topic>

<body>

---
```

Entries are append-only. Don't edit a prior entry; write a new one referencing it.

## When to use this vs chat

- **Chat:** ad-hoc Q&A, simple yes/no, copy/paste-free directives.
- **Exchange:** anything requiring an audit, a launch decision, or a multi-turn back-and-forth. Saves the user from copy-paste relay duty.

## Decision lifecycle

A decision is "ratified" only when:
1. Codex sign-off in `codex_audit.md`
2. User confirms in chat
3. The decision appears in `decisions.md` with an `AUTHORIZED: yes` line

Without all three, it's a proposal, not a commitment.
