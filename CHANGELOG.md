# Changelog

## 0.2.0 (2026-11-24)
- Restyled work view: night and parchment palettes, serif display, icons, run strip, step-fill blocks, decision timeline, edit bars.
- Two-way mode (`--live`): Inbox tab (note, new direction, pause, resume), answer buttons on Needs you, Live now card, task comments. See `references/live.md`.

## 0.1.0 (2026-11-24)
First release.
- Reads Claude Code transcripts and shows the work: goal, plan steps, findings, decisions with your answers, files changed, commits, deploys, what waits on you.
- Work view with five tabs, a side drawer, footnoted summary, filters, search, copy and link actions, replay and keyboard keys.
- `--summary` for an agent-written summary; an automatic factual summary without it.
- Secrets are redacted by pattern before any output.
- Harness view (tool calls, parallelism, tokens) kept as an opt-in extra.
- Summary text follows ASD-STE100 style rules. The approved dictionary is not bundled.
