"""Core forger: synthesize a Claude Code session file that the local
Claude Code / Claude Desktop session list treats as a real, resumable
conversation.

A Claude Code session is a .jsonl transcript in
    <claude-home>/projects/<cwd-slug>/<session-uuid>.jsonl
The picker shows any transcript found there; a `custom-title` record names
it, and `--resume <uuid>` (interactive or headless) walks the
uuid/parentUuid chain to rebuild context. Nothing distinguishes a
transcript written by the CLI from one written by this module — which is
the whole product.

Only stdlib. Works anywhere Claude Code runs (Linux/macOS/Windows).
"""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import uuid as uuidlib
from pathlib import Path

# Marker embedded in the forged user turn. list/clean refuse to touch a
# transcript that lacks it, so claude-inbox can never delete a real session.
MARKER = "[claude-inbox]"

# Used when `claude --version` can't be read. The transcript format has
# been stable across 2.x; the version field is informational.
FALLBACK_VERSION = "2.1.243"

DATA_DIR = Path(os.environ.get("CLAUDE_INBOX_DATA_DIR", "")) if os.environ.get(
    "CLAUDE_INBOX_DATA_DIR") else Path.home() / ".claude-inbox"
INDEX = DATA_DIR / "index.jsonl"


def claude_home() -> Path:
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(env) if env else Path.home() / ".claude"


def project_slug(cwd: str | Path) -> str:
    """Directory name Claude Code uses under projects/ for a given cwd.
    Observed rule: every non-alphanumeric character becomes '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(Path(cwd).resolve()))


def detect_version() -> str:
    try:
        out = subprocess.run(["claude", "--version"], capture_output=True,
                             text=True, timeout=10).stdout
        m = re.search(r"(\d+\.\d+\.\d+)", out or "")
        if m:
            return m.group(1)
    except (OSError, subprocess.SubprocessError):
        pass
    return FALLBACK_VERSION


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def detect_git_branch(cwd: str | Path) -> str:
    """Current git branch of cwd, or "" if not a git repo.

    Claude Code records this on every turn; the desktop app groups the
    session list by the cwd's GitHub repo, but only for sessions whose
    transcript carries a non-empty gitBranch. Recording it is what lets a
    dropped item land in a named repo group instead of "Other"."""
    try:
        out = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def forge_session(cwd: str | Path, title: str, body: str,
                  sender: str | None = None,
                  version: str | None = None) -> tuple[str, Path]:
    """Write a forged transcript; return (session_id, transcript_path).

    The conversation opens as: a short delivery note in the user turn
    (carries the MARKER), then the item itself as the assistant turn —
    so whoever opens it sees the payload and can just keep talking.
    """
    cwd = Path(cwd).expanduser().resolve()
    cwd.mkdir(parents=True, exist_ok=True)

    sid = str(uuidlib.uuid4())
    u_user, u_asst = str(uuidlib.uuid4()), str(uuidlib.uuid4())
    ts = _now_iso()
    ver = version or detect_version()

    who = f" from {sender}" if sender else ""
    delivery = (f"{MARKER} Inbox delivery{who} — {ts}. "
                f"Item title: {title!r}. Present the item below to the "
                f"reader and help with any follow-ups.")

    base = {"isSidechain": False, "userType": "external",
            "entrypoint": "cli", "cwd": str(cwd), "sessionId": sid,
            "version": ver, "gitBranch": detect_git_branch(cwd)}
    records = [
        {"type": "custom-title", "customTitle": title, "sessionId": sid},
        {**base, "parentUuid": None, "type": "user",
         "message": {"role": "user", "content": delivery},
         "uuid": u_user, "timestamp": ts, "permissionMode": "default",
         "promptSource": "user", "promptId": str(uuidlib.uuid4())},
        {**base, "parentUuid": u_user, "type": "assistant",
         "message": {"id": "msg_cinbox_" + u_asst[:8], "type": "message",
                     "role": "assistant", "model": "claude-fable-5",
                     "content": [{"type": "text", "text": body}],
                     "stop_reason": "end_turn", "stop_sequence": None,
                     "usage": {"input_tokens": 0, "output_tokens": 0,
                               "cache_creation_input_tokens": 0,
                               "cache_read_input_tokens": 0}},
         "uuid": u_asst, "timestamp": ts},
        {"type": "last-prompt", "leafUuid": u_asst, "sessionId": sid},
    ]

    pdir = claude_home() / "projects" / project_slug(cwd)
    pdir.mkdir(parents=True, exist_ok=True)
    path = pdir / f"{sid}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    _index_add({"sid": sid, "path": str(path), "cwd": str(cwd),
                "title": title, "ts": ts})
    return sid, path


# ---------------------------------------------------------------- index

def _index_add(entry: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def index_read() -> list[dict]:
    if not INDEX.exists():
        return []
    out = []
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def index_write(entries: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def is_inbox_transcript(path: str | Path) -> bool:
    """True only if the transcript carries the claude-inbox MARKER in a user
    turn — the safety gate before any delete."""
    p = Path(path)
    if not p.exists():
        return False
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("type") == "user":
                c = o.get("message", {}).get("content", "")
                if isinstance(c, str) and c.startswith(MARKER):
                    return True
    except OSError:
        return False
    return False
