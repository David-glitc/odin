---
name: odin
description: Work observability. Shows the user what the agent is doing toward their goal (goal, plan steps and progress, what is now true, decisions that need the user, what changed), as visuals in the chat. Use when the user asks to see what the agent is doing or has done, wants progress or status on the work, asks for a visual report, replay or "observability", or when planning engineering work with subagents that needs intermittent visual reports and short summaries.
---

# odin

Odin shows the WORK, not the harness. Do not report tool-call counts, token use, cache hits, cost or latency. The user wants to see: the goal, the plan, how far it got, what is now true, what needs them, and what changed.

## What to show (in this order)
1. **Goal**: the user's request in one plain line.
2. **Steps and progress**: the plan steps with done, in progress and pending, plus a progress bar. For a replay, tick the steps off in order.
3. **Where it stands**: what is now true (the findings or the result), in ASD-STE100 style: short, active, one idea per sentence, numbers with units. Read `references/asd-ste100.md`.
4. **Needs you**: the open decision, with buttons that call `sendPrompt`.
5. **What changed**: files, commits, deployments, links.
For a swarm, add one lane per subagent with the same four elements and say why a swarm was or was not used.

## Where the data comes from
- Live work: you already know it. Keep the plan list (`update_plan`) honest and call `wrap_up` with a recap of what is now true. Odin reads exactly those.
- Past or other runs: `python3 ~/.claude/skills/odin/scripts/work_state.py <session.jsonl|id|project-dir> --last 4 --widget` returns, per user direction, the goal, plan steps, how they progressed, the last recap, the open question and the files and commits. It reconstructs from plan and recap calls, so a run that never kept a plan shows little. Rewrite goals and recaps into plain STE before showing them, and say when you changed them.
- Session files: `~/.claude/projects/<project-dir>/<session-id>.jsonl`, subagents under `<session-id>/subagents/`.

## The work view
Every task also shows short reasoning notes: the sentences the agent wrote between tool calls (and its thinking, where the transcript keeps it). A diamond marks decision-like ones. Overview collects them under "Why it went this way". Notes are free: they come from the transcript.

`build_work_view.py` fills `assets/work_view.html` from a transcript. It leads with the **goal** and a plain-text **summary**. Footnote numbers in the summary open the task they came from. Five tabs:
- **Overview**: goal, summary with footnotes, clickable chips (tasks, steps done, findings, decisions, files changed, shipped, waiting on you), what needs the user, and every task as a block.
- **Tasks**: block or list view, filters, search. Click a task to open the **drawer**: the user's words, steps with progress, every finding, each decision with the user's answer, what changed, and a Needs you box.
- **Decisions**: every question, its options and the answer.
- **Changes**: files with edit counts, commits, deploys, published links.
- **Needs you**: what waits on the user. Only the newest task can wait.
Actions: Copy report, Copy task text, Copy link to a task (`#t5`), Replay (steps tick off in order), theme toggle. Keys: 1-5 tabs, j/k next and previous task, / search, r replay, Esc close, ? help.

## Write the summary yourself when you can
`python3 ~/.claude/skills/odin/scripts/build_work_view.py <session|id|project-dir> [--all | --last N] [--name NAME] [--goal TEXT] [--summary summary.json] [-o out.html] [--standalone]`
Without `--summary`, Odin writes a short factual summary from the data. A better one comes from you: `{"goal": "one plain line", "paragraphs": ["Short active sentence.[3] Next sentence.[5]"]}`. `[n]` is a task number and becomes a footnote link. Write in ASD-STE100 style (`references/asd-ste100.md`): one idea per sentence, active voice, numbers with units. Say what the work did and why, not how many tools ran.
Output is an artifact-ready fragment. `--standalone` writes a full page for hosting. `work_state.py --coverage` prints the totals, so you can check that nothing was dropped.

## Choose the look
Do not ship the same look every time. Pick it from the work and say why in one sentence. `--style style.json` (or `auto`, the default, which varies by project name; `default` is the gold Odin look):
`{"palette": "gold|ember|ocean|forest|violet|ink", "font": "serif|sans|mono", "motif": "ring|grid|dots|none", "density": "airy|compact", "order": ["hero","needs","strip","chips","why","live"], "why": "One sentence."}`
Guide: incident or failure work, `ember`, compact, `needs` first. Research or reading, `ocean` or `forest`, airy. Long runs with many tasks, compact, `strip` early. Design or writing, `violet`, airy. Strict or formal work, `ink`. Omit a block from `order` to hide it; `hero` always shows. Only these values work, and every palette meets WCAG AA contrast in both themes. With `--live` the agent can change the look without a republish by writing the same object to `live/style`.

## Two-way: live view and quick actions
With `--live` the artifact shows live progress and gives the user prefilled action buttons (no free text). Read `references/live.md` first. In short: publish with the `db`, `user` and `comments` capabilities listed there. At the start of every turn and at each milestone, read `inbox` rows with `status == queued` through `ArtifactData` (one query, no polling), act on them, set them to `seen` then `done` with a short `reply`, and keep `live/now` current. The page updates by itself, so you do not republish for progress. Rows cannot interrupt a running step, and the inline widget's `sendPrompt` stays the way to get an instant reply.

## How to display (use the host's own visuals)
1. **Inline in chat**: load `mcp__visualize__read_me` (modules `interactive`), then `mcp__visualize__show_widget`. Build a work view: task tabs, goal, animated step checklist with progress bar and Replay button, "Where it stands", a "Needs you" box and change chips. Use the host CSS variables. Explanations go in normal text, not in the widget.
2. **Work view page**: `build_work_view.py` output through the Artifact tool. Use it for long sessions (about 20 tasks or more) and when the user wants a link. Republish it at each milestone; a viewer cannot read the transcript by itself.
3. **Local file**: `--standalone` output or `build_viewer.py`. Last resort.

Post a new view at each milestone (a step finishes, a decision is needed, a failure changes the plan). Do not wait for the end.

## Harness view (only if the user asks for it)
`build_viewer.py`, `widget_data.py` and `adset_report.py` show tool calls, parallelism, tokens and cache. That is harness observability. Use it only on request, for example to debug why a run was slow.

## Limits
Plan state is rebuilt from `update_plan` calls, so unticked steps can be shown as pending even when done. Rule-based goals are the user's raw words and can be messy.
