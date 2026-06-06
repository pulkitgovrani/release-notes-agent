# Integrate into a repo

Three capabilities, all via GitHub Actions (infra ≈ $0, runs in the repo's own CI):
1. Generate a changelog from merged PRs on each release.
2. Publish it to **GitHub Pages** (a real URL).
3. Capture the **user impact** on each PR (nudge + auto-suggest).

## Quickest: use the published action (no copy) ⭐

If this agent is published as a GitHub Action, a repo doesn't need to vendor any
code — just one workflow file:

1. Add the secret `ANTHROPIC_API_KEY` (Settings → Secrets and variables → Actions).
2. Settings → Pages → Source = **GitHub Actions**.
3. Drop [`examples/release-notes-action.yml`](examples/release-notes-action.yml) into
   `.github/workflows/`. It pins `uses: pulkitgovrani/release-notes-agent@v1`.

That's it — no `release-notes-agent/` folder in the consumer repo. On each published
Release the changelog regenerates and deploys to `https://<owner>.github.io/<repo>/`.
The "vendor the folder" steps below are the manual alternative.

## Prerequisites
- An **Anthropic API key** — CI runners can't reach a local Ollama, so use the API there.
- Repo admin access (to add a secret + enable Pages).

## Steps (~10 min)

1. **Vendor the agent.** Copy the `release-notes-agent/` folder into the repo (or add it as a
   git submodule). The workflows reference `release-notes-agent/`.

2. **Add the secret.** Repo → Settings → Secrets and variables → Actions → new secret
   `ANTHROPIC_API_KEY`. (`GITHUB_TOKEN` is provided automatically.)

3. **Add workflows.** Copy from `release-notes-agent/examples/` into `.github/workflows/`:
   | Workflow | Does |
   |---|---|
   | `release-notes-pages.yml` | generate + publish to Pages on each release |
   | `release-notes-scheduled.yml` *(optional)* | weekly / every-N-hours |
   | `pr-impact-nudge.yml` *(optional)* | ask for user impact on new PRs |
   | `pr-impact-suggest.yml` *(optional)* | auto-suggest the impact from the diff |

4. **Enable Pages.** Repo → Settings → Pages → Source = **GitHub Actions**.

5. **Add the PR template.** Copy `examples/PULL_REQUEST_TEMPLATE.md` →
   `.github/PULL_REQUEST_TEMPLATE.md`.

Done. On each published Release the changelog regenerates and deploys to
`https://<owner>.github.io/<repo>/`. On each PR, contributors get nudged/suggested for the
user impact, which flows into the next changelog.

## Run it manually instead (no Actions)

```bash
cd release-notes-agent
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...  GITHUB_TOKEN=...   # GITHUB_TOKEN = a read-only PAT
python main.py --repo OWNER/NAME --last 10 --version v1.2
# or fully free + offline:
python main.py --repo OWNER/NAME --last 10 --local --ollama-model gemma4:e4b
```

## Cost
Fires only at release/PR time. With prompt caching, ~cents per run on the Anthropic API; $0 on
local Ollama. GitHub Pages hosting is free.
