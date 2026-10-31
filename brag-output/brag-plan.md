# /brag plan — Vetal

**What it is:** a git pre-push hook + GitHub Action where a ghost from the Vikram–Vetal tales reads your diff with local Gemma, tells a tale, and won't let you push/merge until you answer a riddle about your own change.
**For:** developers (and teams shipping lots of AI-written code).
**Sets it apart:** folklore as a code-comprehension check; runs on a local open-weight model, so code never leaves the machine.
**Best claim:** "If you know the answer and keep silent, your head will burst into a thousand pieces."
**Visual hook:** `$ git push` → something drops onto your shoulders (screen thump, branch sways).
**Real UI shown:** the actual terminal strings from `vetal/cli.py` and the PR comment format from `cmd_ci_ask`. The tale/riddle/answer text is illustrative (same example as the README) since no model ran in the build environment.
**Tone:** cinematic folk-horror, but punchy (default pacing). Night palette, tamarind gold.
**Share caption:** see share-copy.txt.

## Identity
- Background `#0a0c0b` night, moon glow `#1c2621`, fog
- Gold `#e0b04a` (Vetal's voice), red `#e05a4a` (refused), green `#6cc477` (released), dim `#8a948e`
- Lora (title, folklore), Inter (UI captions), DejaVu Sans Mono (terminal)
- Original tamarind-branch silhouette, top-left, sways all video

## Music
104 BPM (beat = 0.577s), D minor: drone + music-box arpeggio (Dm–B♭–Gm–A), kick/bass enter with the terminal scene, soft hats/claps, whooshes into each cut, typing ticks on 16ths, bell on each "release". 39 beats = 22.5s. Every cut and key reveal is on a beat.

## Storyboard (beats → seconds)
| # | Beats | Time | Scene | Readable text |
|---|---|---|---|---|
| 1 Hook | 0–4 | 0.00–2.31 | Terminal types `$ git push`; on beat 1 a THUMP (shake, branch whips) | "Something drops onto your shoulders…" (1.6s) |
| 2 Reveal | 4–9 | 2.31–5.19 | Big gold **Vetal**; kicker "from the tales of Vikram & Vetal" | "Won't let you push until you explain your diff." (2.6s) |
| 3 Highlight: git push | 9–21 | 5.19–12.12 | Chip "On every git push". Tale types fast (texture), riddle lands beat 11, answer types beats 14–16, green verdict beat 17 | riddle (5.8s), verdict (2.3s) |
| 4 Highlight: PR | 21–29 | 12.12–16.73 | Chip "And on every pull request". Bot comment card with riddle; status "Vetal awaits your /answer" (pending) → `/answer …` reply beat 25 → status ✓ "Vetal let go" beat 26 | riddle (4.3s), status (1.7s) |
| 5 Highlight: open weights | 29–34 | 16.73–19.62 | Big line + chips `Ollama · Gemma · offline · no API key` | "Local Gemma. Your diff never leaves your machine." (2.7s) |
| 6 Outro | 34–39 | 19.62–22.50 | Logo + tagline + install command | "Explain your diff. Or he won't let go." (2.7s) |

Transitions: dip through the night background (out 0.2s, in 0.25s) — no muddy crossfades.
