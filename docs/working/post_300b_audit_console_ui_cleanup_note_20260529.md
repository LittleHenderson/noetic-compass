# Post-300B Audit Console UI Cleanup Note

Date: 2026-05-29

After the 300B model run/eval work lands, schedule a dedicated Audit Console cleanup pass.

Current issue:
- The Audit Console is becoming word-heavy again.
- The added WORM/Evidence Packet explanations are useful, but the screen is drifting back toward clutter.
- A new user can be overwhelmed by explanatory copy before they understand the action path.

Cleanup rule:
- Keep only decisive action text visible by default: connect, run, verify, accept/suppress/flag, evidence packet status.
- Move explanatory text into hover popovers, compact FAQ drawers, or a single persistent help surface.
- The main page should answer: What is connected? What can I run? What verdict came back? What proof is blocking or passing?
- FAQ/help should answer: What does this term mean? Why does this proof matter? What should I tell a reviewer?

Target after 300B:
- Audit Console first screen should read like an operator cockpit, not a white paper.
- Evidence Packet / WORM / baseline / ablation / control explanations stay available, but not always visible.
- Re-check mobile and desktop for dense text blocks, repeated warnings, and redundant panel labels.

