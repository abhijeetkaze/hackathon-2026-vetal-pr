"""End-to-end tests with the fake backend: a real repo, a real remote, a real `git push`."""
import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOOD = "I made add raise ValueError when a is None instead of crashing later"


def sh(*cmd, cwd, env=None, check=True):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=check)


class PushTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.work = os.path.join(self.tmp, "work")
        sh("git", "init", "-q", "--bare", "remote.git", cwd=self.tmp)
        sh("git", "init", "-q", "-b", "main", "work", cwd=self.tmp)
        for k, v in (("user.email", "t@t"), ("user.name", "t")):
            sh("git", "config", k, v, cwd=self.work)
        sh("git", "remote", "add", "origin", "../remote.git", cwd=self.work)
        self.commit("def add(a, b):\n    return a + b\n")
        sh("git", "push", "-q", "origin", "main", cwd=self.work)
        self.env = dict(os.environ, PYTHONPATH=ROOT, VETAL_BACKEND="fake", VETAL_FAST="1")
        sh(sys.executable, "-m", "vetal", "install", cwd=self.work, env=self.env)
        self.commit("def add(a, b):\n    if a is None:\n        raise ValueError\n    return a + b\n")

    def commit(self, text):
        with open(os.path.join(self.work, "m.py"), "w") as f:
            f.write(text)
        sh("git", "commit", "-qam", "change", cwd=self.work, check=False)
        sh("git", "add", ".", cwd=self.work)
        sh("git", "commit", "-qm", "change", cwd=self.work, check=False)

    def push(self, answer, **extra):
        env = dict(self.env, VETAL_ANSWER=answer, **extra)
        return sh("git", "push", "-q", "origin", "main", cwd=self.work, env=env, check=False)

    def test_weak_answer_is_refused(self):
        self.assertNotEqual(self.push("dunno").returncode, 0)

    def test_silence_is_refused(self):
        r = self.push("")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("thousand pieces", r.stderr)

    def test_good_answer_pushes(self):
        self.assertEqual(self.push(GOOD).returncode, 0)

    def test_sleeping_model_lets_push_through_unless_strict(self):
        down = {"VETAL_BACKEND": "", "OLLAMA_HOST": "127.0.0.1:1"}
        self.assertNotEqual(self.push("", VETAL_STRICT="1", **down).returncode, 0)
        self.assertEqual(self.push("", **down).returncode, 0)


class CITest(unittest.TestCase):
    def test_ask_then_judge(self):
        env = dict(os.environ, PYTHONPATH=ROOT, VETAL_BACKEND="fake")
        d = tempfile.mkdtemp()
        p = lambda n: os.path.join(d, n)
        open(p("pr.diff"), "w").write("diff --git a/m.py b/m.py\n+++ b/m.py\n+raise ValueError\n")
        ask = sh(sys.executable, "-m", "vetal", "ci-ask", "--diff-file", p("pr.diff"),
                 "--head", "abc", cwd=d, env=env)
        state = ask.stdout.split("<!-- vetal:")[1].split("-->")[0]
        self.assertEqual(json.loads(base64.b64decode(state))["head"], "abc")
        json.dump([{"body": ask.stdout, "user": {"type": "Bot"}}], open(p("c.json"), "w"))

        def judge(answer, head="abc"):
            open(p("a.txt"), "w").write(answer)
            return sh(sys.executable, "-m", "vetal", "ci-judge", "--diff-file", p("pr.diff"),
                      "--comments-file", p("c.json"), "--answer-file", p("a.txt"),
                      "--head", head, cwd=d, env=env, check=False).returncode

        self.assertEqual(judge("/answer " + GOOD), 0)
        self.assertEqual(judge("/answer meh"), 1)
        self.assertEqual(judge("/answer"), 1)
        self.assertEqual(judge("/answer " + GOOD, head="newer"), 3)


if __name__ == "__main__":
    unittest.main()
