---
name: inbox
description: List or clean the inbox items claude-inbox has delivered to this machine's session list. Use when asked "what's in my inbox", "list dropped conversations", "clean up my inbox", "remove old inbox items".
---

- List: `uv run --directory "${CLAUDE_PLUGIN_ROOT}" claude-inbox list` — shows id, age, title for every item delivered on this machine (index: `~/.claude-inbox/index.jsonl`).
- Clean: `claude-inbox clean --older-than 7d` (or `--all`, or `--id <sid-prefix>`). Clean only ever deletes transcripts that carry claude-inbox's own `[claude-inbox]` marker — it refuses anything else, so real sessions are never touched.
- To read an item without opening the UI: `cd <cwd> && claude -p "summarize this conversation" --resume <session-id>`.
