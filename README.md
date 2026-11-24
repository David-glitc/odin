# Odin

See what your agent is doing toward your goal. Not tool-call counts. The work.

Odin is a [Claude Code](https://claude.com/claude-code) skill. It reads a session transcript and builds a page that leads with the **goal** and a plain-text **summary** with footnotes, then lets you open any task in a drawer: the plan steps and how far they got, every finding, each decision with your answer, what changed, and what waits on you.

**Live demo:** https://odin.kierkegaard.space

## Install

```bash
git clone https://github.com/David-glitc/odin ~/.claude/skills/odin
```

Then ask Claude Code: "show me what you are doing" or "build an Odin work view of this session". Python 3.8+, no packages.

## Use it by hand

```bash
# the latest session of a project, as a page you can open
python3 scripts/build_work_view.py ~/.claude/projects/<project-dir> --all --standalone -o work.html

# with a summary the agent wrote (STE style, [n] links to task n)
python3 scripts/build_work_view.py <session-id> --all --summary summary.json --standalone -o work.html

# check what Odin read
python3 scripts/work_state.py <session-id> --coverage
```

Try it on the made-up session in `examples/`:

```bash
python3 scripts/build_work_view.py examples/demo-session.jsonl --all --standalone -o demo.html
```

## What you get

- **Overview**: goal, summary, footnotes, clickable counts, what needs you.
- **Tasks**: blocks or list, filters, search. Click for the drawer.
- **Decisions**, **Changes**, **Needs you** tabs.
- Copy report, copy task, copy link (`#t5`), replay, theme, keys (`1`-`5`, `j`/`k`, `/`, `r`, `Esc`, `?`).

## What Odin can and cannot see

It reads your requests, plan steps (`update_plan` and `TodoWrite`), recaps (`wrap_up`), questions and answers, file edits (also files written by shell commands), commits, deploys and artifact links. Work never written to a plan, recap, file or link does not show. Plan steps are rebuilt from plan calls, so an unticked step can look pending when it is done.

## Privacy

Everything runs locally. Output is redacted by pattern (tokens, bearer values, `KEY=`/`SECRET=` values, long hex, seed phrases). Patterns miss things, so read a page before you share it.

## Writing style

Summaries follow ASD-STE100 Simplified Technical English rules: short active sentences, one word one meaning, numbers with units. The approved dictionary is not bundled, so the lint is partial. See `references/asd-ste100.md`.

## Test

```bash
python3 -m unittest discover -s tests
```

MIT licence.
