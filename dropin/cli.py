"""dropin CLI — drop / list / clean.

drop   Deliver an inbox item: forge a named, resumable conversation into
       the local Claude Code / Claude Desktop session list.
list   Show items dropin has delivered on this machine.
clean  Remove delivered items (only transcripts dropin itself wrote).
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path

from . import forge


def _default_cwd() -> str:
    return os.environ.get("DROPIN_CWD", str(Path.home() / "inbox"))


def cmd_drop(args: argparse.Namespace) -> int:
    if args.text is not None:
        body = args.text
    elif args.body == "-":
        body = sys.stdin.read()
    elif args.body:
        body = Path(args.body).expanduser().read_text(encoding="utf-8")
    else:
        print("error: provide --body FILE (or '-' for stdin) or --text STR",
              file=sys.stderr)
        return 2
    if not body.strip():
        print("error: empty body", file=sys.stderr)
        return 2

    sid, path = forge.forge_session(args.cwd, args.title, body,
                                    sender=args.sender)
    print(f"dropped: {args.title}")
    print(f"  session   {sid}")
    print(f"  transcript {path}")
    print(f"  appears in the session list for cwd {Path(args.cwd).expanduser().resolve()}")
    print(f"  resume:   cd {args.cwd} && claude --resume {sid}")
    return 0


def _age(ts: str) -> str:
    try:
        then = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=datetime.timezone.utc)
    except ValueError:
        return "?"
    d = datetime.datetime.now(datetime.timezone.utc) - then
    if d.days:
        return f"{d.days}d"
    h = d.seconds // 3600
    return f"{h}h" if h else f"{d.seconds // 60}m"


def cmd_list(_args: argparse.Namespace) -> int:
    entries = forge.index_read()
    if not entries:
        print("no items dropped on this machine")
        return 0
    for e in entries:
        gone = "" if Path(e["path"]).exists() else "  (deleted)"
        print(f"{e['sid'][:8]}  {_age(e['ts']):>4}  {e['title']}{gone}")
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    entries = forge.index_read()
    if not entries:
        print("nothing to clean")
        return 0
    cutoff = None
    if args.older_than:
        try:
            days = float(args.older_than.rstrip("d"))
        except ValueError:
            print(f"error: bad --older-than {args.older_than!r} (use e.g. 7d)",
                  file=sys.stderr)
            return 2
        cutoff = datetime.datetime.now(datetime.timezone.utc) - \
            datetime.timedelta(days=days)
    if not (args.all or cutoff or args.id):
        print("error: pass --all, --older-than Nd, or --id SID",
              file=sys.stderr)
        return 2

    keep, removed = [], 0
    for e in entries:
        target = args.all or \
            (args.id and e["sid"].startswith(args.id)) or \
            (cutoff and datetime.datetime.strptime(
                e["ts"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                    tzinfo=datetime.timezone.utc) < cutoff)
        if not target:
            keep.append(e)
            continue
        p = Path(e["path"])
        if p.exists():
            if forge.is_dropin_transcript(p):
                p.unlink()
                removed += 1
                print(f"removed {e['sid'][:8]}  {e['title']}")
            else:
                # never delete a transcript we can't prove we wrote
                print(f"SKIPPED {e['sid'][:8]} — no dropin marker, left in place")
                keep.append(e)
        else:
            removed += 1  # already gone; drop from index
    forge.index_write(keep)
    print(f"{removed} removed, {len(keep)} kept")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dropin", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("drop", help="deliver an inbox item")
    d.add_argument("--title", required=True,
                   help="name shown in the session list — this IS the inbox line")
    d.add_argument("--body", help="markdown file with the item ('-' = stdin)")
    d.add_argument("--text", help="item body inline (alternative to --body)")
    d.add_argument("--sender", help="attribution shown in the delivery note")
    d.add_argument("--cwd", default=_default_cwd(),
                   help="project dir the conversation belongs to "
                        "(default: ~/inbox, or $DROPIN_CWD)")
    d.set_defaults(fn=cmd_drop)

    l = sub.add_parser("list", help="list delivered items")
    l.set_defaults(fn=cmd_list)

    c = sub.add_parser("clean", help="remove delivered items")
    c.add_argument("--all", action="store_true")
    c.add_argument("--older-than", metavar="Nd")
    c.add_argument("--id", metavar="SID", help="session id (prefix ok)")
    c.set_defaults(fn=cmd_clean)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
