"""Small git helpers: which commits are being pushed, and what changed in them."""
import subprocess

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
NOISE = [":(exclude)*.lock", ":(exclude)package-lock.json", ":(exclude)pnpm-lock.yaml",
         ":(exclude)*.min.js", ":(exclude)*.svg", ":(exclude)dist/**"]


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def _exists(sha):
    return subprocess.run(["git", "cat-file", "-e", sha + "^{commit}"],
                          capture_output=True).returncode == 0


def _zero(sha):
    return set(sha) == {"0"}


def default_base(head):
    for ref in ("@{upstream}", "origin/HEAD", "origin/main", "origin/master", "main", "master"):
        try:
            base = git("merge-base", ref, head).strip()
            if base and base != git("rev-parse", head).strip():
                return base
        except subprocess.CalledProcessError:
            continue
    return EMPTY_TREE


def push_ranges(stdin_text):
    """Parse pre-push stdin into (base, head) pairs, skipping branch deletions."""
    for line in stdin_text.splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        _, local_sha, _, remote_sha = parts
        if _zero(local_sha):
            continue
        base = remote_sha if not _zero(remote_sha) and _exists(remote_sha) else default_base(local_sha)
        yield base, local_sha


def diff(base, head):
    return git("diff", "--no-color", "-M", base, head, "--", ".", *NOISE)


def trim(text, limit=8000):
    """Keep every file visible, giving each a fair share of the budget."""
    if len(text) <= limit:
        return text
    chunks = text.split("\ndiff --git")
    chunks = [chunks[0]] + ["diff --git" + c for c in chunks[1:]]
    share = max(limit // len(chunks), 400)
    out = []
    for c in chunks:
        out.append(c if len(c) <= share else c[:share] + "\n[... trimmed by Vetal ...]\n")
    return "\n".join(out)[: limit * 2]


def pardon_file():
    return git("rev-parse", "--git-path", "vetal-pardons").strip()
