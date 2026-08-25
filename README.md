# claude-inbox

**An inbox for Claude Code and Claude Desktop.** claude-inbox delivers a *conversation* instead of a notification: it writes a named, ready-to-resume session straight into the local Claude Code session store, so the item shows up in the session picker (CLI `--resume`, desktop app, IDE extensions) like any other conversation. The reader opens it, sees the payload as Claude's opening message, and just keeps talking — full context, zero setup, and near-zero tokens to deliver (no model call happens until the reader replies).

```
$ claude-inbox drop --title "inbox: 3 PRs need review" --body brief.md --sender ci-watcher
dropped: inbox: 3 PRs need review
  session   1c2a…  →  appears in the session list, resumable like any conversation
```

## Why

Every background agent eventually needs to hand something to a human: a morning brief, a failing-deploy report, a research summary, a "here's what I did overnight" handoff. SMS truncates, email gets buried, and a webpage is one more tab. But the human already has an inbox they open every day — the Claude session list. claude-inbox puts items there, and unlike every other channel, the delivery *is* the follow-up interface: "which PR is riskiest?" is just the next message in the conversation.

## How it works

A Claude Code session is a `.jsonl` transcript in `~/.claude/projects/<cwd-slug>/<uuid>.jsonl`. The picker lists whatever transcripts exist there; a `custom-title` record names them; `--resume` rebuilds context by walking the transcript's `uuid → parentUuid` chain. Nothing distinguishes a transcript written by the CLI from one written by a script. claude-inbox forges a minimal 4-record transcript — title record, a marked delivery turn, the item as the assistant's message, a `last-prompt` pointer — and the entire surface area of Claude Code treats it as a real conversation.

Delivery is **local machine, local account** by design: claude-inbox writes files under `~/.claude`, it does not (and cannot) push into anyone's account remotely. To deliver to another machine you run claude-inbox *on* that machine — over SSH, from a daemon, or from that machine's own agent.

## Install

As a Claude Code plugin (skills `/claude-inbox:drop`, `/claude-inbox:inbox`):

```
/plugin install claude-inbox@softwaresoftware
```

Or standalone (stdlib-only, Python ≥ 3.10, Linux/macOS/Windows):

```
uv tool install claude-inbox    # or: pip install .
```

## CLI

```
claude-inbox drop --title "<inbox line>" --body item.md [--text "..."] [--sender who] [--cwd DIR]
claude-inbox list
claude-inbox clean --older-than 7d | --all | --id <sid>
```

- `--title` is the inbox line — it's all the picker shows, so make it carry the payload.
- `--cwd` (default `~/inbox`, or `$CLAUDE_INBOX_CWD`) is the project directory the conversation belongs to; using one dedicated dir keeps drops grouped in the picker.
- `clean` only deletes transcripts carrying claude-inbox's own `[claude-inbox]` marker in the delivery turn. It refuses anything else, so it can never destroy a real session. An inbox that only fills is noise — put `claude-inbox clean --older-than 7d` in a cron.

## Recipes

```bash
# Morning brief from a cron/daemon
some-brief-generator | claude-inbox drop --title "brief $(date +%m-%d)" --body - --sender sentinel

# Hand an overnight agent's report to the human
claude-inbox drop --title "inbox: overnight refactor — 2 decisions need you" \
                  --body report.md --sender taskpilot --cwd ~/projects/myrepo

# Deliver to another machine on your tailnet
ssh laptop "$(command -v claude-inbox || echo uv tool run claude-inbox) drop --title 'inbox: deploy failed' --text '...'"
```

## Notes & limits

- The transcript `version` field mirrors your installed `claude --version` (informational; format stable across 2.x).
- The forged assistant turn reports zero token usage — cost telemetry stays honest.
- Sessions delivered while a machine is offline appear as soon as the files exist; there's no sync step, the store *is* the inbox.
- Companion: for items that need live work done first, spawn a real agent (e.g. [taskpilot](https://github.com/softwaresoftware-dev/taskpilot)) with `--name` — finished taskpilot sessions land in the same picker; claude-inbox covers the "just deliver content" half for free.

MIT · a [softwaresoftware.dev](https://softwaresoftware.dev) project
