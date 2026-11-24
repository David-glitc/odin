# Changelog

## 0.3.0 (2026-11-24)
- The agent chooses the look: six contrast-checked palettes, three fonts, four hero motifs, two densities, block order and a one-line reason. `--style`, `auto` (varies by project) or `default`; with `--live`, `live/style` changes it without a republish.

## 0.2.0 (2026-11-24)
- Restyled work view: night and parchment palettes, serif display, icons, run strip, step-fill blocks, decision timeline, edit bars.
- Two-way mode (`--live`): prefilled quick actions on every task (Looks right, Redo this, Explain why, Stop here), answer buttons on Needs you, pause or resume the run, Live now card, task comments. No free-text box. See `references/live.md`.
- Reasoning notes on every task ("How it got there") and a "Why it went this way" card on Overview, taken from the sentences the agent wrote between tool calls. No extra model calls.

## 0.1.0 (2026-11-24)
First release.
- Reads Claude Code transcripts and shows the work: goal, plan steps, findings, decisions with your answers, files changed, commits, deploys, what waits on you.
- Work view with five tabs, a side drawer, footnoted summary, filters, search, copy and link actions, replay and keyboard keys.
- `--summary` for an agent-written summary; an automatic factual summary without it.
- Secrets are redacted by pattern before any output.
- Harness view (tool calls, parallelism, tokens) kept as an opt-in extra.
- Summary text follows ASD-STE100 style rules. The approved dictionary is not bundled.
