from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

from . import __version__, probes, render
from .diagnose import trace_command

COMMANDS = {"trace", "file", "env", "snapshot"}


def _emit(record, text, as_json):
    print(json.dumps(record, indent=2, default=str) if as_json else text)


def _log_history(cmd, record):
    state = os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
    d = os.path.join(state, "resolve-trace")
    try:
        os.makedirs(d, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        with open(os.path.join(d, "history.log"), "a") as fh:
            fh.write(f"{ts}\t{cmd}\t{record['type']['kind']}\t"
                     f"{record['paths'].get('primary') or '-'}\n")
    except OSError:
        pass


def cmd_trace(args):
    r = trace_command(args.command)
    if not args.no_log:
        _log_history(args.command, r)
    _emit(r, render.render_trace(r), args.json)
    return 0 if r["type"]["kind"] != "not found" else 1


def cmd_file(args):
    f = probes.file_info(os.path.expanduser(args.path))
    _emit(f, render.render_file(f), args.json)
    return 0 if f.get("exists") else 1


def cmd_env(args):
    e = probes.suspicious_env()
    _emit(e, render.render_env(e), args.json)
    return 0


def cmd_snapshot(args):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ctx = probes.exec_context()
    env = probes.suspicious_env()

    if args.json:
        out = json.dumps(
            {"timestamp": ts, "context": ctx, "env": env,
             "path": os.environ.get("PATH", "")},
            indent=2, default=str,
        )
    else:
        lines = [
            "resolve-trace snapshot",
            f"timestamp: {ts}",
            f"user:      {ctx['user']} (uid={ctx['uid']} euid={ctx['euid']})",
            f"shell:     {ctx['shell']}",
            f"init:      {ctx['init']}",
            f"tty:       {ctx.get('tty')}",
            f"sudo:      {ctx['sudo']} (from {ctx.get('sudo_from')})",
            f"container: {ctx.get('container')}",
            f"ssh:       {ctx['ssh']}",
            "",
            "PATH:",
        ]
        lines += [f"  {d}" for d in os.environ.get("PATH", "").split(os.pathsep)]
        lines += ["", render.render_env(env)]
        out = "\n".join(lines)

    if args.output:
        with open(args.output, "w") as fh:
            fh.write(out + "\n")
        print(f"snapshot written to {args.output}")
    else:
        print(out)
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="rt",
        description="Explain what actually runs, where it comes from, and why.",
    )
    p.add_argument("--version", action="version", version=f"resolve-trace {__version__}")
    sub = p.add_subparsers(dest="cmd")

    def add_json(sp):
        sp.add_argument("--json", action="store_true", help="machine-readable output")

    t = sub.add_parser("trace", help="full breakdown of a command")
    t.add_argument("command")
    t.add_argument("--no-log", action="store_true", help="do not append to history log")
    add_json(t)
    t.set_defaults(func=cmd_trace)

    f = sub.add_parser("file", help="what a file is, where it came from, who owns it")
    f.add_argument("path")
    add_json(f)
    f.set_defaults(func=cmd_file)

    e = sub.add_parser("env", help="show suspicious environment variables")
    add_json(e)
    e.set_defaults(func=cmd_env)

    s = sub.add_parser("snapshot", help="save current system state to a report")
    s.add_argument("-o", "--output", help="write report to file instead of stdout")
    add_json(s)
    s.set_defaults(func=cmd_snapshot)

    return p


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    parser = build_parser()

    if argv and argv[0] not in COMMANDS and not argv[0].startswith("-"):
        argv = ["trace"] + argv
    if not argv:
        parser.print_help()
        return 0

    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
