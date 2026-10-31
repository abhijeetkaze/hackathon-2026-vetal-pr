"""vetal — a ghost that won't let you push until you explain your own diff."""
import argparse
import base64
import json
import os
import stat
import subprocess
import sys
import time

from . import git, oracle

SILENT = ("You knew the answer and kept silent, Vikram. Your push shatters "
          "into a thousand pieces.")
HOOK = """#!/bin/sh
# installed by vetal — remove with: vetal uninstall
exec "{python}" -m vetal hook "$@"
"""

# ---------- terminal voice -------------------------------------------------

_tty = sys.stderr.isatty() and not os.environ.get("NO_COLOR")
DIM, RED, GREEN, GOLD, RESET = (("\033[2m", "\033[31m", "\033[32m", "\033[33m", "\033[0m")
                                if _tty else ("",) * 5)


def say(text="", color="", slow=False):
    if slow and _tty and not os.environ.get("VETAL_FAST"):
        sys.stderr.write(color)
        for ch in text:
            sys.stderr.write(ch)
            sys.stderr.flush()
            time.sleep(0.012)
        sys.stderr.write(RESET + "\n")
    else:
        sys.stderr.write(f"{color}{text}{RESET}\n")
    sys.stderr.flush()


def ask_vikram(prompt):
    if "VETAL_ANSWER" in os.environ:  # tests / scripted demos
        return os.environ["VETAL_ANSWER"]
    try:
        with open("/dev/tty") as tty:
            sys.stderr.write(prompt)
            sys.stderr.flush()
            return tty.readline().strip()
    except OSError:
        return None  # no terminal (GUI client, CI)


# ---------- the encounter --------------------------------------------------

def encounter(diff_text):
    """Tell a tale, ask a riddle, judge. Returns True if Vetal lets go."""
    diff_text = git.trim(diff_text)
    say("\n🌳  Something heavy drops onto your shoulders from the tamarind tree...", DIM)
    say(f"    (Vetal is reading your diff with {oracle.model()})\n", DIM)
    r = oracle.summon(diff_text)
    say(r["tale"], GOLD, slow=True)
    say()
    say(r["riddle"], GOLD + "\033[1m" if _tty else "", slow=True)
    say("If you know the answer and keep silent, your head will burst into a thousand pieces.\n",
        DIM)
    answer = ask_vikram("Your answer, Vikram › ")
    if answer is None:
        say("Vetal cannot hear you without a terminal. He lets you pass — tonight.", DIM)
        return True
    if not answer:
        say(SILENT, RED)
        return False
    v = oracle.judge(diff_text, r["riddle"], r["answer_key"], answer)
    say()
    if v["verdict"] == "release":
        say(v["reply"], GREEN, slow=True)
        say("Vetal lets go and flies back to his tree. Your push continues.\n", DIM)
        return True
    say(v["reply"], RED, slow=True)
    say("Vetal clings on. Push refused. (Try again — he tells a new tale each time.)\n", DIM)
    return False


def _guarded(fn):
    try:
        return fn()
    except oracle.Asleep as e:
        say(f"Vetal is asleep: {e}", DIM)
        if os.environ.get("VETAL_STRICT"):
            say("VETAL_STRICT is set — no ghost, no push.", RED)
            return 1
        say("Letting the push through.", DIM)
        return 0
    except KeyboardInterrupt:
        say("\nYou flee the cremation ground. Push refused.", RED)
        return 1


# ---------- commands -------------------------------------------------------

def cmd_hook(_args):
    ranges = list(git.push_ranges(sys.stdin.read()))
    if not ranges:
        return 0
    path = git.pardon_file()
    pardoned = set(open(path).read().split()) if os.path.exists(path) else set()
    pending = [(b, h) for b, h in ranges if f"{b}..{h}" not in pardoned]
    if not pending:
        say("Vetal remembers you from last time. Go.", DIM)
        return 0
    text = "".join(git.diff(b, h) for b, h in pending)
    if not text.strip():
        return 0

    def run():
        if not encounter(text):
            return 1
        with open(path, "a") as f:
            f.write("".join(f"{b}..{h}\n" for b, h in pending))
        return 0
    return _guarded(run)


def cmd_ask(args):
    head = args.head
    base = args.base or git.default_base(head)
    text = git.diff(base, head)
    if not text.strip():
        say("Nothing changed. Vetal yawns.", DIM)
        return 0
    return _guarded(lambda: 0 if encounter(text) else 1)


def cmd_install(args):
    hooks = git.git("rev-parse", "--git-path", "hooks").strip()
    os.makedirs(hooks, exist_ok=True)
    path = os.path.join(hooks, "pre-push")
    if os.path.exists(path) and "vetal" not in open(path).read() and not args.force:
        say(f"A pre-push hook already exists at {path}. Use --force to replace it.", RED)
        return 1
    with open(path, "w") as f:
        f.write(HOOK.format(python=sys.executable))
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    say(f"🌳 Vetal now waits in {path}", GREEN)
    say(f"   Model: {oracle.model()}  (change with VETAL_MODEL)", DIM)
    return 0


def cmd_uninstall(_args):
    path = os.path.join(git.git("rev-parse", "--git-path", "hooks").strip(), "pre-push")
    if os.path.exists(path) and "vetal" in open(path).read():
        os.remove(path)
        say("Vetal has gone back to his tree.", DIM)
    return 0


# ---------- CI (GitHub Action) ---------------------------------------------

MARK = "<!-- vetal:"


def cmd_ci_ask(args):
    text = git.trim(open(args.diff_file).read())
    r = oracle.summon(text)
    state = base64.b64encode(json.dumps(
        {"head": args.head, "riddle": r["riddle"], "key": r["answer_key"]}).encode()).decode()
    tale = "\n".join("> " + l for l in r["tale"].splitlines())
    print(f"""### 🌳 Vetal has climbed onto this pull request

{tale}

**{r['riddle']}**

The PR author must answer in a comment that starts with `/answer`. Until Vetal is satisfied,
the `vetal` check stays pending. *If you know the answer and keep silent, your head will burst
into a thousand pieces.*

<sub>Riddled by `{oracle.model()}`, running on this CI runner. Your code never left GitHub.</sub>
{MARK}{state} -->""")
    return 0


def cmd_ci_judge(args):
    comments = json.load(open(args.comments_file))
    state = None
    for c in reversed(comments):
        body = c.get("body") or ""
        if MARK in body and (c.get("user") or {}).get("type") == "Bot":
            state = json.loads(base64.b64decode(body.split(MARK, 1)[1].split("-->")[0].strip()))
            break
    if state is None:
        print("Vetal has asked no riddle here yet.")
        return 2
    if state["head"] != args.head:
        print("You pushed new commits, Vikram. Vetal has a fresh riddle for you — answer that one.")
        return 3
    answer = open(args.answer_file).read().strip()
    if answer.lower().startswith("/answer"):
        answer = answer[len("/answer"):].strip()
    if not answer:
        print(f"**{SILENT}**")
        return 1
    v = oracle.judge(git.trim(open(args.diff_file).read()), state["riddle"], state["key"], answer)
    if v["verdict"] == "release":
        print(f"🕊️ {v['reply']}\n\n*Vetal lets go and flies back to his tree. The `vetal` check passes.*")
        return 0
    print(f"🪢 {v['reply']}\n\n*Vetal clings on. Try another `/answer`.*")
    return 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="vetal", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("install", help="install the pre-push hook in this repo").add_argument(
        "--force", action="store_true")
    sub.add_parser("uninstall", help="remove the pre-push hook")
    sub.add_parser("hook", help="(called by git) pre-push entry point").add_argument(
        "remote", nargs="*", help=argparse.SUPPRESS)
    a = sub.add_parser("ask", help="face Vetal now, without pushing")
    a.add_argument("--base", help="compare against this ref (default: merge-base with upstream)")
    a.add_argument("--head", default="HEAD")
    ca = sub.add_parser("ci-ask", help="(CI) print a riddle comment for a PR diff")
    ca.add_argument("--diff-file", required=True)
    ca.add_argument("--head", required=True)
    cj = sub.add_parser("ci-judge", help="(CI) judge an /answer comment")
    for f in ("--diff-file", "--comments-file", "--answer-file", "--head"):
        cj.add_argument(f, required=True)
    args = p.parse_args(argv)
    try:
        return {"install": cmd_install, "uninstall": cmd_uninstall, "hook": cmd_hook,
                "ask": cmd_ask, "ci-ask": cmd_ci_ask, "ci-judge": cmd_ci_judge}[args.cmd](args)
    except subprocess.CalledProcessError as e:
        say(f"git failed: {e.stderr.strip()}", RED)
        return 1
