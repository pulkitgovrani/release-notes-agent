# Release Intelligence Agent

Reads merged PRs since your last release, understands the *why*, and writes a polished
**"What's new"** for users + a technical changelog — every line grounded in a real PR.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the design and the BUILD-NOW vs NOT-YET scope,
and [NEXT_STEPS.md](NEXT_STEPS.md) for the backlog (incl. the PR-time impact-capture bot).

## Run it locally

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in ANTHROPIC_API_KEY, GITHUB_TOKEN, GITHUB_REPO

python main.py --repo owner/name --since v1.0 --version v1.1
# outputs: ./output/CHANGELOG.md, ./output/index.html, ./output/feed.xml, ./output/ANNOUNCEMENTS.md
open ./output/index.html
```

**Offline demo (no GitHub needed — great for stage):**

```bash
python main.py --demo            # canned sample PRs; only ANTHROPIC_API_KEY required
open ./output/index.html
```

`--since` is optional (defaults to your latest GitHub release). `--version` is just the
label shown on the page.

## Run locally for free (no API key — Ollama)

No Anthropic credit? Run the model on your own machine via [Ollama](https://ollama.com):

```bash
ollama pull gemma3n:e4b        # or whatever you have — see: ollama list
pip install ollama
python main.py --demo --local --ollama-model gemma3n:e4b
```

`--local` switches the provider to Ollama (env equivalent: `LLM_PROVIDER=ollama`). It works
with any flag, e.g. `python main.py --repo owner/name --last 10 --local`. Output quality is
lower than Claude on small models, but it's free and offline. Default provider is Anthropic.

## Announce this release (X / Slack / LinkedIn)

The same grounded notes are turned into ready-to-post **announcement drafts** — an X/Twitter
thread, a Slack `#announcements` message, and a LinkedIn post. One source of truth → every
channel (the first step toward the "release communication hub"). Because the drafts are built
from the already-grounded items, they inherit the **no-invented-features** guarantee — they're
never re-derived from raw PRs.

- Lands as a **"📣 Announce this release"** section on the changelog page, each draft with a
  one-click **Copy** button, plus an `output/ANNOUNCEMENTS.md` file.
- On by default; add `--no-announce` to skip (saves one LLM call).

## Choosing which PRs to include (cadence)

Pick one window (default: since your last release):

| Flag | Includes |
|---|---|
| *(default)* | PRs merged since the latest GitHub release |
| `--since vX` | PRs merged since tag `vX` |
| `--last N` | the most recent N merged PRs (e.g. `--last 10`) |
| `--since-hours H` | PRs merged in the last H hours |
| `--since-days D` | PRs merged in the last D days |

**Cadence** (how *often* notes get generated) = how you schedule the run:
- Every N merged PRs → trigger on push to main with `--last N`.
- Every 5 hours → cron `0 */5 * * *` + `--since-hours 5`.
- Weekly → cron `0 9 * * 1` + `--since-days 7`.

See [`examples/release-notes-scheduled.yml`](examples/release-notes-scheduled.yml).

## How it works

```
collector.py  → merged PRs + commits + linked issues since the last release
filter.py     → user-facing vs internal (heuristics first, Haiku for the rest)
agent.py      → grounded notes (Sonnet): every item cites a PR #; dev-speak → user benefit
announce.py   → X thread + Slack + LinkedIn drafts from those same grounded notes
publish.py    → changelog page (HTML) + Markdown + RSS feed + ANNOUNCEMENTS.md
```

- **Grounding:** items are dropped if they don't tie to a real PR (`agent.py`).
- **Models:** Sonnet for generation, Haiku for the cheap filter — edit in `config.py`.
- **Caching:** the style guide / filter guide are prompt-cached.

## Deploy as a GitHub Action (~$0 infra)

**Easiest — the published action (no folder copy):** drop
[`examples/release-notes-action.yml`](examples/release-notes-action.yml) into a repo's
`.github/workflows/`, add the `ANTHROPIC_API_KEY` secret, and turn on Pages. It pins
`uses: pulkitgovrani/release-notes-agent@v1` and reads PRs via the API — no checkout, no
vendored code. See [INTEGRATION.md](INTEGRATION.md).

```yaml
- uses: pulkitgovrani/release-notes-agent@v1
  with:
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    version: ${{ github.event.release.tag_name || 'latest' }}
    output: _site
```

**Manual alternative (vendor the folder):** copy `release-notes-agent/` into the repo and
use [`examples/release-notes.yml`](examples/release-notes.yml). Runs on every published
release and regenerates the changelog.

## Not yet (see ARCHITECTURE.md)
Emailing end users (deliverability/GDPR ops) — RSS + page cover "notify" for now.
Segmentation, analytics, the PR-time "user impact" capture bot — Phase 1+.
