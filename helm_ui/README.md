# HELM UI v0

A calm local web page for talking with HELM in everyday English. Every reply can be opened to the record it rests on.

## Run it

```
python helm_ui/server.py
```

Then open http://127.0.0.1:8765. The server binds to 127.0.0.1 only. It needs FastAPI and uvicorn (already installed on the laptop); nothing else.

- Tests: `python -m pytest helm_ui/tests -q` (10 tests, about 2 s, peak about 76 MiB on the laptop).
- Demo page with no server: `helm_ui/demo/index.html`. Rebuild it from a real session with `python helm_ui/make_demo.py`.
- Screenshots: `helm_ui/docs/helm_ui_dark.png`, `helm_ui/docs/helm_ui_light.png`.
- Page options: `?theme=dark|light`, `?records=1` (open every record), `?view=plan&plan=...` (open the planner on a request).

## What is on the page

| Area | What it shows | Source |
|---|---|---|
| Conversation | HELM's reply in plain words. Under it: a plain status ("Stock noted") and a "Show the record" link. | `helm_chat.HELMConversationalSession.handle_turn`, imported and called as-is |
| The record | Status in plain words plus the exact word (for example `INVENTORY_RECORDED`), what was saved, the turn gate, the safety check (RPM gate verdict), the information valve numbers, the receipt hash, the time, the session log file. "Under the hood" adds the station path, the checked form (the CAS expression the reader made) and the raw loop records. | the loop's own trace records for that turn |
| Plan a task | The prerequisite planner's order as a graph, each step's gate verdict from a dry run, or a typed refusal such as `PLAN_CYCLE`. Nothing is run. | `docs/working/noetic_council/prereq_planner` (`build_plan`, then `execute_plan` with no runner) |
| What HELM knows | Stock on hand, recipes with learned amounts, what you told it about yourself, the brain's own limit sentence. | the live session's loop, brain and memory |
| Self-check | The Unity Eye's plain report, with findings marked. Choose a clean test copy or a copy with one planted fault, then Run. | the U3-T1 scanner (`Documents/Codex/2026-10-19/u3_t1`), run read-only in its own process |
| Attention | A radial display of where idle attention went across the 7 desires (F1-F7), and a 7 x 7 grid of which brain job worked for which desire. | the RB-I3 run record `rb_i3/READING.json` (family A, seed 11) |
| Search dials | The five dials and the Eye's four presets. | the session's `UnityEyeSupervisor.dial` (`helm_creativity_dial.CreativityDial` setters) |
| Status strip | The claim status of each panel, with the project's markers and exact words, and "Synthetic worlds only". | the run records' own reading files |

## Wired vs not wired (honest list)

- Wired: the chat turn, the record, What HELM knows, the planner dry run, the dials (read and set).
- Wired, but not to this chat: the Self-check runs on a built test copy of HELM's state (dev seed), not on the live session. The Attention card reads a finished run record, not the live session. Both say so on screen.
- Not wired: the Eye reading or whispering to the live chat session; a live idle drive loop; the live attention point (it is never written into a record, so only the share of steps is shown).
- Not built: Phase A of the Radial Architecture Display (the 40-petal, 4-ring display in `docs/design/cas_v7_5_multimodal_display_specification.md`). HELM produces no 40 x 4 activation data to fill it, so drawing it would mean inventing numbers. The Attention card uses only the Drive ring idea.
- Switched off: tool actions (write files, run commands, git, cloud jobs). In this window a tool request is planned but not run, and its record says `UI_TOOLS_OFF`. Set `HELM_UI_ALLOW_TOOLS=1` to turn them on.

## Rules the page keeps

- Only `POST /turn` can change HELM's state, and it goes through HELM's own turn function. A test checks that the other endpoints change nothing (turns, cube store writes, stock, recipes, facts, trace).
- `POST /dials` changes only the tool planner's dials. Recipe answers do not read them.
- The Unity Eye reports; it never writes. Each scan shows `Eye writes 0` and `whisper writes 0` from the run itself.
- Status words are copied from the run records. The page never upgrades them.
- A part that cannot load shows "not wired" instead of numbers.
- The session log goes to `helm_ui/sessions/` (git-ignored).

## Endpoints

| Method | Path | Does |
|---|---|---|
| POST | `/turn` `{"text": ...}` | one turn; returns the reply, the record, and the new state |
| GET | `/state` | what HELM knows, dials, pairing table, last self-check, wiring, claims |
| GET | `/history` | this session's turns with their records |
| GET | `/eye/scan?world=clean\|fault` | one read-only self-scan on a test copy |
| GET, POST | `/dials` | read the dials; set a preset `{"preset": "BALANCED"}` or values `{"K": 12}` (422 if out of range) |
| POST | `/plan` `{"text": ...}` | plan only, plus the gate's dry run; never runs a tool |

## Things HELM itself does that the page shows as they are

- Telling HELM anything about bees gets a reply about "beekeeping in the south of France", even when France was never said. That sentence is hard-coded in `helm_chat.py`. The page shows it unchanged.
- The terminal command `dials` fails inside `helm_chat.py` (`UnityEyeSupervisor` has no `dial_params`). The page reports the error; the Search dials card reads the dial directly.
- Making a `HELMConversationalSession` creates an empty `sessions/` folder at the repo root before the page can point the log elsewhere.
- The planner reads only ordering words. "First knead the dough, then let it rise" gives steps named `knead` and `let`. Its own limit: "MECHANISM ONLY. ORDERING IS DERIVED FROM STATED PREREQUISITES. NO UNDERSTANDING OF THE REQUEST IS CLAIMED."
