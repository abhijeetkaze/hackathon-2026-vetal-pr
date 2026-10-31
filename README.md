# 🌳 Vetal — a ghost that won't let you push until you explain your own diff

In the old Indian tales of **Vikram and Vetal**, King Vikram must carry a ghost down from a
tamarind tree in the cremation ground. On the way, Vetal tells him a story that ends in a riddle.
*"If you know the answer and keep silent,"* says the ghost, *"your head will burst into a
thousand pieces."*

**Vetal** brings that ghost into git. When you `git push` (or open a pull request), Vetal reads
your diff with a **local open-weight model (Gemma, via Ollama)**, tells you a short folk tale that
secretly mirrors your change, and asks one riddle about it. For example: *what happens to
`parse_date` when the string is empty?*

- Answer well → Vetal lets go and your push goes through.
- Answer badly → Vetal clings on. Push refused. He tells a new tale next time.
- Stay silent → your push shatters into a thousand pieces.

It's a five-second check that you understand the code you're about to ship, which matters more
now that so much of it is written by AI.

```
$ git push
🌳  Something heavy drops onto your shoulders from the tamarind tree...

In the kingdom of Avanti, the old gatekeeper was told he need no longer ask travellers
their names. "Let them through," said the minister, "the gate is slow enough." That
night, a stranger with no name walked in...

Tell me, Vikram: in validate_user(), you removed the email check — what now happens
when a signup arrives with an empty email?
Your answer, Vikram › it hits the DB constraint and returns a 500 instead of a 400
```

## Why it runs on open weights

Vetal reads every diff you push. Sending all of that to a hosted API would be the actual horror
story. With Gemma running in Ollama on your laptop, **your code never leaves your machine**. In
CI, the model runs on the GitHub runner itself, so no API key, no vendor, and no cost per riddle.

## Quick start (local pre-push hook)

```bash
# 1. a local model
ollama pull gemma3:4b          # or gemma3:1b on a small laptop

# 2. vetal (stdlib-only Python, no dependencies)
pipx install git+https://github.com/abhijeetkaze/hackathon-2026-vetal-pr

# 3. in any repo
vetal install                  # adds .git/hooks/pre-push
vetal ask                      # face Vetal now, without pushing
```

| Setting | Default | |
|---|---|---|
| `VETAL_MODEL` | `gemma3:4b` | any Ollama model works |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | |
| `VETAL_STRICT` | unset | if set, block the push when the model is unreachable |
| `VETAL_FAST` | unset | skip the typewriter effect |

Other behaviour:
- **Model unreachable:** Vetal is asleep and lets you through, unless `VETAL_STRICT=1`.
- **No terminal** (a GUI git client): Vetal can't hear your answer and lets you through.
- **Already answered:** Vetal remembers ranges you've answered for, so re-pushing the same
  commits doesn't ask again.
- **Emergency:** `git push --no-verify` skips him. He will remember.

## On pull requests (GitHub Action)

Copy [`.github/workflows/vetal.yml`](.github/workflows/vetal.yml) into your repo and make `vetal`
a **required status check**. Then:

1. A PR is opened or updated → Vetal posts a tale and a riddle. The `vetal` check goes **pending**.
2. The PR author replies with `/answer <your answer>` → Vetal judges it and replies.
   The check turns **green** or **red**.
3. New commits mean a new riddle.

The workflow runs `gemma3:1b` on the runner with Ollama, with the weights cached between runs.
It **never checks out or runs PR code**: Vetal is installed from the default branch and the
diff is fetched as text. Only the PR author's `/answer` counts.

## How it works

```
git push ──► pre-push hook ──► git diff (lockfiles/minified dropped, each file trimmed fairly)
                                   │
                    Gemma (Ollama, JSON schema) ──► { tale, riddle, answer_key }
                                   │
                         your answer from /dev/tty
                                   │
                    Gemma as judge ──► { verdict: release | cling, reply }
                                   │
                        exit 0 (push) / exit 1 (refused)
```

- Two small prompts in [`vetal/prompts.py`](vetal/prompts.py). The riddle step also writes a
  hidden *answer key*, facts from the diff, so a small model can judge fairly.
- Ollama's structured outputs (`format: <json schema>`) keep a 1B model's output parseable.
- The diff and your answer are treated as data. The judge is told to ignore anything in them
  that asks it to release you.

## Honest limits

- A 1B model sometimes asks shallow riddles. 4B is noticeably better. Pick what your hardware
  can run.
- It's a speed bump, not a security control. `--no-verify` exists, and a determined person can
  sweet-talk a small model.

## Development

```bash
VETAL_BACKEND=fake python -m unittest   # stand-in model, no Ollama needed
```

Built for the [DEV Hacktoberfest 2026 Open-Source AI Challenge — Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26).
Apache 2.0 licensed.
