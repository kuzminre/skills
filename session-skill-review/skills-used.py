#!/usr/bin/env python3
"""Which skills did a pi session actually invoke?

  skills-used.py --list [N]        newest sessions, numbered, for picking one
  skills-used.py <session.jsonl>   skills reached inside that session
  skills-used.py --actions <session.jsonl> [--from LINE]
                                   every tool call, in order, with line numbers

A skill is "used" when the agent opened a file under a skills directory: a
`read` tool call whose path contains /skills/<name>/ and ends in .md, or when
the skill was loaded by direct `<skill name="...">` injection into the user
context (the platform's own "use this skill" mechanism) -- the body may then
run its bundled scripts without ever `read`-ing SKILL.md. Bash
commands that merely mention a skills path are ignored, and so is the skill
index in the system prompt -- that index is in every session and proves nothing.
"""
import collections
import datetime
import glob
import json
import os
import re
import sys

ROOT = os.path.expanduser("~/.pi/agent/sessions")
SKILL_RE = re.compile(r"/skills/([^/\s\"']+)/")
# Direct skill loading, distinct from the index: <skill name="X" location="...">
# injected into a user message. The name may carry the platform "skill:" prefix.
INJECT_RE = re.compile(r"<skill\s+name=[\"']([^\"']+)[\"']")


def rows(path):
    for n, line in enumerate(open(path, errors="replace"), 1):
        try:
            yield n, json.loads(line)
        except json.JSONDecodeError:
            continue


def sessions():
    return sorted(glob.glob(f"{ROOT}/**/*.jsonl", recursive=True),
                  key=os.path.getmtime, reverse=True)


def text(msg):
    content = msg.get("content")
    if isinstance(content, str):
        return content
    return " ".join(p.get("text", "") for p in content or []
                    if isinstance(p, dict) and p.get("type") == "text")


def first_user(path):
    for _, e in rows(path):
        m = e.get("message") or {}
        if m.get("role") == "user":
            return " ".join(text(m).split())[:90]
    return ""


def fires(path):
    counter = collections.Counter()
    evidence = collections.defaultdict(list)
    for n, e in rows(path):
        m = e.get("message") or {}
        if m.get("role") == "user":
            inj = INJECT_RE.search(text(m))
            if inj:
                name = inj.group(1)
                if name.startswith("skill:"):
                    name = name[len("skill:"):]
                counter[name] += 1
                evidence[name].append(f"line {n}: <skill> injection")
        for part in m.get("content") or []:
            if not (isinstance(part, dict) and part.get("type") == "toolCall"):
                continue
            if part.get("name") != "read":
                continue
            target = (part.get("arguments") or {}).get("path") or ""
            match = SKILL_RE.search(target)
            if not match or not target.endswith(".md"):
                continue
            counter[match.group(1)] += 1
            evidence[match.group(1)].append(f"line {n}: {target}")
    return counter, evidence


def actions(path, start=0):
    counter = collections.Counter()
    for n, e in rows(path):
        m = e.get("message") or {}
        for part in m.get("content") or []:
            if not (isinstance(part, dict) and part.get("type") == "toolCall"):
                continue
            if n < start:
                continue
            args = part.get("arguments") or {}
            detail = args.get("command") or args.get("path") or json.dumps(args)
            counter[part.get("name")] += 1
            print(f"line {n}  {part.get('name'):9} {' '.join(str(detail).split())[:110]}")
    print("# " + "  ".join(f"{v}x {k}" for k, v in counter.most_common()))


def main(argv):
    if argv and argv[0] == "--actions":
        path = argv[1] if len(argv) > 1 else sys.exit("--actions needs a session log")
        start = int(argv[argv.index("--from") + 1]) if "--from" in argv else 0
        if not os.path.isfile(path):
            sys.exit(f"no such session log: {path}")
        actions(path, start)
        return 0

    if not argv or argv[0] == "--list":
        limit = int(argv[1]) if len(argv) > 1 else 8
        for i, p in enumerate(sessions()[:limit], 1):
            stamp = datetime.datetime.fromtimestamp(os.path.getmtime(p))
            print(f"{i}. {stamp:%Y-%m-%d %H:%M}  {p}  ::  {first_user(p)}")
        return 0

    path = argv[0]
    if not os.path.isfile(path):
        sys.exit(f"no such session log: {path}")

    counter, evidence = fires(path)
    if not counter:
        print("no skills invoked in this session")
        return 0
    for name, count in counter.most_common():
        print(f"{count}x {name}")
        for hit in evidence[name]:
            print(f"    {hit}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
