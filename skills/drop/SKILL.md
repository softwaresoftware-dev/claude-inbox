---
name: drop
description: Deliver an inbox item to this machine's Claude Code / Claude Desktop session list — a named, ready-to-resume conversation carrying a brief, report, or handoff. Use when asked to "drop this in my inbox", "put this in my session list", "send this to my desktop inbox", "deliver this as a conversation", or when a daemon/agent should hand work to a human without SMS/email.
---

`uv run --directory "${CLAUDE_PLUGIN_ROOT}" claude-inbox drop --title "<title>" --body <file>` (or `--text "<body>"`, or pipe markdown to `--body -`). Optional: `--sender "<who/what sent it>"`, `--cwd <dir>` (default `~/inbox` — the project the conversation appears under).

- The **title is the inbox line** — the only thing visible in the session picker. Make it carry the payload: `inbox: 3 PRs need review`, `brief 08-24`, not `notification`.
- The body is the assistant's opening message: write it in markdown, self-contained, ending ready for follow-up questions. The reader resumes the conversation and just keeps talking — so include the context a fresh Claude would need to answer follow-ups.
- Delivery is local-machine, local-account only (it writes `~/.claude/projects/...`). To deliver to another machine, run claude-inbox there (over SSH or its own agent).
- Don't let items pile up: suggest `claude-inbox clean --older-than 7d` if `claude-inbox list` shows stale items.
