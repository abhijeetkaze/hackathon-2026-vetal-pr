"""Vetal's voice: talks to a local open-weight model (Gemma via Ollama)."""
import json
import os
import urllib.error
import urllib.request

from . import prompts

DEFAULT_MODEL = "gemma3:4b"


class Asleep(Exception):
    """The model could not be reached or did not answer sensibly."""


RIDDLE_SCHEMA = {
    "type": "object",
    "properties": {
        "tale": {"type": "string"},
        "riddle": {"type": "string"},
        "answer_key": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["tale", "riddle", "answer_key"],
}

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["release", "cling"]},
        "reply": {"type": "string"},
    },
    "required": ["verdict", "reply"],
}


def model():
    return os.environ.get("VETAL_MODEL", DEFAULT_MODEL)


def _host():
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    if not host.startswith("http"):
        host = "http://" + host
    return host.rstrip("/")


def _chat(system, user, schema, temperature):
    if os.environ.get("VETAL_BACKEND") == "fake":
        return _fake(schema, user)
    body = json.dumps({
        "model": model(),
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "stream": False,
        "format": schema,
        "options": {"temperature": temperature},
    }).encode()
    req = urllib.request.Request(_host() + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(2):
        try:
            with opener.open(req, timeout=600) as resp:
                data = json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise Asleep(f"model '{model()}' not found — run: ollama pull {model()}")
            raise Asleep(f"Ollama returned HTTP {e.code}")
        except (urllib.error.URLError, OSError) as e:
            raise Asleep(f"no Ollama at {_host()} ({e})")
        try:
            out = json.loads(data["message"]["content"])
            if all(k in out for k in schema["required"]):
                return out
        except (KeyError, ValueError, TypeError):
            pass
    raise Asleep("Vetal mumbled something unintelligible (bad JSON twice)")


def summon(diff):
    """Return {'tale', 'riddle', 'answer_key'} for a diff."""
    out = _chat(prompts.ASK_SYSTEM, prompts.ask_user(diff), RIDDLE_SCHEMA, 0.8)
    key = out.get("answer_key") or []
    out["answer_key"] = [str(k) for k in key][:4] if isinstance(key, list) else [str(key)]
    return out


def judge(diff, riddle, answer_key, answer):
    """Return {'verdict': 'release'|'cling', 'reply'}."""
    out = _chat(prompts.JUDGE_SYSTEM, prompts.judge_user(diff, riddle, answer_key, answer),
                VERDICT_SCHEMA, 0.2)
    if out.get("verdict") not in ("release", "cling"):
        out["verdict"] = "cling"
    return out


def _fake(schema, user):
    """Deterministic stand-in so the plumbing can be tested without a model."""
    if schema is RIDDLE_SCHEMA:
        files = [l[6:] for l in user.splitlines() if l.startswith("+++ b/")]
        target = files[0] if files else "this change"
        return {
            "tale": "In the old city a gatekeeper changed the lock on the eastern gate "
                    "and told no one. At midnight the lamplighter came and could not get in.",
            "riddle": f"Tell me, Vikram: what did you change in {target}, and why?",
            "answer_key": [f"the change touches {target}"],
        }
    answer = user.rsplit("VIKRAM'S ANSWER:", 1)[-1]
    ok = len(answer.split()) >= 6
    return {"verdict": "release" if ok else "cling",
            "reply": "You speak true. I let go — this time." if ok
            else "Too few words to fool a ghost. I cling on."}
