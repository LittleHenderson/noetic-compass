import sys, os
sys.path.insert(0, r"C:\Users\wakil\OneDrive\Desktop\tksCAS")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(r"C:\Users\wakil\OneDrive\Desktop\tksCAS")
import helm_agentic_executor as H
ex = H.AgenticExecutionEngine(workspace_root=r"C:\Users\wakil\OneDrive\Desktop\tksCAS")
planner = ex.planner
GOALS = [
 ("A. canonical control", "Write the code for auth.py, verify the tests pass, then commit it to git."),
 ("B. UNUSUAL: verify FIRST", "Before writing any code, run the verification on auth.py to see which tests already fail."),
 ("C. UNUSUAL: git FIRST", "First check git to see what changed and recover the last known good state, then write the code."),
 ("D. git only", "Show me the git log and diff for the last three commits."),
]
for label, goal in GOALS:
    dag = planner.decompose_goal(goal)
    print("="*88); print(label); print("  GOAL:", goal)
    steps = list(dag.steps.values())
    for s in steps:
        print("    %-28s tool=%-16s deps=%s" % (s.step_id, s.tool_name, s.dependencies or "[]"))
    print("  TOOL ORDER:", " -> ".join(s.tool_name for s in steps))
