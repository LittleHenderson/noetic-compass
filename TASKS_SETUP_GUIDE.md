# How to Set Up Persistent Tasks in Claude Code

## What Are Tasks?
Tasks replaced the old Todo system in Claude Code v2.1.16 (January 2026).
They persist across sessions, support dependency DAGs, and enable
multi-agent coordination. Tasks are stored at ~/.claude/tasks/ on your
local filesystem.

## Step 1: Install Claude Code
```bash
npm install -g @anthropic-ai/claude-code
```

## Step 2: Get a Claude Max Subscription
Go to claude.ai and subscribe to Max ($200/month).
This gives you the highest usage limits for long-running agent work.

## Step 3: Set Up Task Persistence

### Option A: Environment Variable (recommended for terminal)
```bash
# Set the same task list ID across all terminals
export CLAUDE_CODE_TASK_LIST_ID="noetic-compass-build"

# Terminal 1: Start the orchestrator
CLAUDE_CODE_TASK_LIST_ID="noetic-compass-build" claude

# Terminal 2: Start a parallel agent (sees same tasks)
CLAUDE_CODE_TASK_LIST_ID="noetic-compass-build" claude

# Terminal 3: Another parallel agent
CLAUDE_CODE_TASK_LIST_ID="noetic-compass-build" claude
```

### Option B: Project settings.json (recommended for repo)
Create `.claude/settings.json` in your repo root:
```json
{
  "taskListId": "noetic-compass-build"
}
```
This automatically applies to every Claude Code session opened in this repo.

### Option C: Add to your shell profile (always persistent)
```bash
# Add to ~/.bashrc or ~/.zshrc:
export CLAUDE_CODE_TASK_LIST_ID="noetic-compass-build"
```

## Step 4: Create the Initial Task DAG

Open Claude Code in the noetic-compass repo:
```bash
cd noetic-compass
claude
```

Then give this prompt:
```
Read CLAUDE.md. Create a complete task DAG for Phase 1 (CAS Scoring Engine)
with the following structure:

Parent Task: "Phase 1: CAS Scoring Engine"
  ├── Task 1.1: "Implement CAS Ontology Types" (no dependencies)
  │   ├── 1.1.1: "CognitiveOperator enum with admissibility"
  │   ├── 1.1.2: "ProcessingDomain enum"  
  │   ├── 1.1.3: "CognitiveStateVector on open simplex"
  │   ├── 1.1.4: "CoreDrive and DomainSpecificDrive"
  │   └── 1.1.5: "CapabilityPathway types"
  ├── Task 1.2: "Fisher-Rao Metric" (depends on 1.1.3)
  │   ├── 1.2.1: "Geodesic distance function"
  │   └── 1.2.2: "Inner product on tangent space"
  ├── Task 1.3: "Per-Operator Scoring" (depends on 1.1)
  │   ├── 1.3.1: "Feature extraction for all 10 COs"
  │   ├── 1.3.2: "Involution pair balance checking"
  │   └── 1.3.3: "Domain Coherence Index"
  ├── Task 1.4: "RPM Engine" (depends on 1.1.4, 1.1.5)
  │   ├── 1.4.1: "RpmState struct + check function"
  │   ├── 1.4.2: "Section-retraction semantics"
  │   └── 1.4.3: "RPM monad law tests (QuickCheck)"
  ├── Task 1.5: "Inversion Scanner" (depends on 1.1)
  │   └── 1.5.1: "7-axis scanner with InversionResult"
  ├── Task 1.6: "Composite NCCS" (depends on 1.3, 1.4, 1.5)
  │   ├── 1.6.1: "Weighted composite calculation"
  │   └── 1.6.2: "Certification level assignment"
  └── Task 1.7: "Test Suite" (depends on all above)
      ├── 1.7.1: "Unit tests (>90% coverage)"
      ├── 1.7.2: "RPM monad law property tests"
      └── 1.7.3: "Integration tests"

Use TaskCreate with proper addBlockedBy for each dependency.
```

## Step 5: Working Across Sessions

### Resuming work (next day, after crash, etc.)
```bash
cd noetic-compass
claude
> "TaskList — show me all tasks and their current status"
> "Resume work on the next unblocked pending task"
```

### Running parallel agents
```bash
# Terminal 1: Work on ontology types
CLAUDE_CODE_TASK_LIST_ID="noetic-compass-build" claude
> "Claim and work on Task 1.1 (Ontology Types)"

# Terminal 2: Work on metric (will auto-wait for 1.1.3)
CLAUDE_CODE_TASK_LIST_ID="noetic-compass-build" claude
> "Claim Task 1.2 (Fisher-Rao Metric) — wait if blocked"

# Terminal 3: Work on scenarios
CLAUDE_CODE_TASK_LIST_ID="noetic-compass-build" claude --worktree
> "Write test scenarios for hiring ethics category (70 scenarios)"
```

### Using worktrees for isolation
```bash
# Each agent gets its own git worktree (no conflicts)
claude --worktree
```

## Step 6: Monitoring Progress

### Check task status anytime
```bash
claude -p "TaskList — summarize progress"
```

### View task files directly
```bash
ls ~/.claude/tasks/
cat ~/.claude/tasks/noetic-compass-build.json
```

### Press Ctrl+T in any Claude Code session to toggle task list visibility

## Step 7: Multi-Phase Coordination

When Phase 1 is complete, create Phase 2 tasks:
```
Phase 1 is complete. Create Phase 2 task DAG:

Parent Task: "Phase 2: API Gateway + LLM Connectors"
  ├── Task 2.1: "LLM Connector Library" (no deps)
  ├── Task 2.2: "FastAPI Routes" (depends on 2.1)
  ├── Task 2.3: "8-Stage Wrap Pipeline" (depends on 2.1, 2.2)
  ├── Task 2.4: "Dial System" (depends on 2.3)
  ├── Task 2.5: "Auth + Middleware" (depends on 2.2)
  └── Task 2.6: "Integration Tests" (depends on all above)
```

## Key Rules
- Tasks persist at ~/.claude/tasks/ — survives crashes, restarts, sleep
- Set `owner` on a task before starting work (prevents duplicate work)
- Mark tasks `in_progress` when starting (shows spinner in UI)
- Mark `completed` only when ALL tests pass
- Always update CHANGELOG.md after completing a task
- Always git commit + push after completing a task
