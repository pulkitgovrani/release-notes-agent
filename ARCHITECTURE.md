# Release Intelligence Agent — MVP Architecture (solo-scoped)

> **Pitch:** When you ship, the bot reads the merged PRs, understands *why* each change was made, and writes a polished **"What's new"** for your users — plus a technical changelog — in seconds. Every line is grounded in a real PR, so it never invents a feature. Engineering → customer communication, automatically.

Two chained ideas (from the senior): **(A)** capture the *why* behind each PR (intent), **(B)** on release, turn that into user-facing release notes. A feeds B — the "why" is what makes the notes meaningful instead of a dump of commit messages.

This is the locked direction: less-crowded market, clean SaaS shape, cheap to run, and — critically — **buildable and shippable by one person.**

---

## Design principles (what makes it real, not a toy)

These four are the difference between a demo and a product:

1. **Grounding — every note cites a PR #.** The agent may only write a note it can tie to a specific merged PR. No invented features, no hallucinated changelog. This is the trust core (the equivalent of a "verify loop").
2. **Signal filter — user-facing vs internal.** Not every PR matters to customers (refactors, CI tweaks, dep bumps, internal plumbing). The agent classifies and **hides internal noise** from the user-facing notes, keeping them clean.
3. **Impact-aware input — capture the *why*.** MVP infers intent from the PR body + linked issue + diff. The standout upgrade (fast Phase-1 add): a PR bot/template field that asks the dev *"what's the user impact?"* at PR time — fixes the empty-description problem and is the real differentiator.
4. **Solo-safe distribution — RSS + page, not email-as-sender.** Sidestep email ops (deliverability, lists, GDPR) entirely for v1: publish a **changelog page + an RSS feed** that users subscribe to. That answers "how do users get notified" without the ops tax. Become the email sender later.

---

## 🎯 Solo scope: BUILD NOW vs NOT YET

The whole product is big. As a solo dev, ship the narrow wedge first. Discipline = this table.

| ✅ BUILD NOW (solo v1) | 🚫 NOT YET (Phase 2+, skip for now) |
|---|---|
| Collect merged PRs since last release | **Being the email sender to end users** (deliverability, lists, GDPR) → RSS + page covers "notify" for now |
| **Filter user-facing vs internal** (hide refactors/CI/deps) | PR-time "user impact" capture bot (fast Phase-1 add; MVP infers instead) |
| Generate user-facing + technical notes, **each grounded in a PR #** | Audience segmentation / usage-based personalization |
| Pull the "why" from PR body + linked issue (+ diff fallback) | Multi-language notes |
| Publish: changelog page + **RSS feed** + GitHub Release body | Open-rate analytics + feedback loop |
| Manual approve/edit before publish | Slack / social auto-post |

---

## What's IN the hackathon MVP
- A trigger: git tag / merge-to-main / manual `release since vX`.
- Collect merged PRs + commits since the last release (title, body, linked issue, diff summary).
- **Filter** each PR: user-facing or internal.
- Release agent (Claude) groups + classifies (feature / fix / breaking), translates dev-speak → user benefit, and **grounds every line in a PR #**.
- Output **two registers**: a technical changelog *and* a user-facing "What's new".
- Publish to a **changelog page + RSS feed**, and set it as the GitHub Release body.

## What's explicitly OUT (say this — shows focus)
- Sending email to end users (we generate + publish + RSS; sending is later).
- Segmentation, analytics, multi-channel. Post-hackathon.

---

## Architecture

```
  Release trigger  (git tag · merge to main · manual "release since vX")
          │
          ▼
  ┌──────────────────┐
  │  Collector        │  find last release → merged PRs + commits since
  └────────┬─────────┘   (title, body, linked issue, diff summary = the "why")
           ▼
  ┌──────────────────┐
  │  Filter           │  user-facing vs internal → drop refactors/CI/dep-bumps
  └────────┬─────────┘
           ▼
  ┌──────────────────┐   tools: list_merged_prs, read_pr, read_issue, read_diff
  │  Release Agent   │   · groups + classifies (feature/fix/breaking)
  │  (Claude)        │   · dev-speak → user benefit
  │                  │   · GROUNDS every line in a PR #  (no invented features)
  └────────┬─────────┘
           ▼  two registers
  ┌──────────────────┐
  │  Draft Notes      │  technical changelog + user-facing "What's new"
  │                  │  (each line → its PR #)
  └────────┬─────────┘
           ▼
   Human approve / edit   ← the trust step (PM tweaks before it's public)
           ▼
  ┌──────────────────┐
  │  Publish          │  changelog page + RSS feed + GitHub Release body
  │                  │   [email sender = NOT YET]
  └──────────────────┘
```

### Components
1. **`collector.py`** — GitHub API (PyGithub): find the last release tag, list merged PRs + commits since, gather each PR's body + linked issue + a diff summary.
2. **`filter.py`** — classify each PR user-facing vs internal. Cheap heuristics first (labels, paths like `.github/`, `chore:`/`refactor:` prefixes), then Claude for the ambiguous ones (route to Haiku `claude-haiku-4-5` to save cost).
3. **`agent.py`** — Claude Sonnet 4.6 (`claude-sonnet-4-6`); escalate final polish to Opus 4.8 (`claude-opus-4-8`). Tools: `read_pr`, `read_issue`, `read_diff`. Produces the two registers from one style-guide system prompt, **emitting `{note, pr_number}` pairs so every line stays grounded**. **Prompt-cache the style guide** (fires every release — caching pays off fast).
4. **`publish.py`** — render markdown → a changelog page (static HTML / GitHub Pages for MVP) + an **RSS feed** (`feed.xml`) so users can subscribe; also set the GitHub Release body via the API.
5. **(impact capture — Phase-1 add)** — a PR bot/template that asks "what's the user impact?" at PR time. MVP skips this and infers; this is the first post-hackathon upgrade and the differentiator.

### Stack
- Python 3.11, `anthropic` (caching ON), `PyGithub`
- Output: markdown → changelog page (GitHub Pages) + RSS `feed.xml`; GitHub Release body
- Runs as a **GitHub Action** on release → **~$0 infra**
- Email later: Resend/SendGrid (not in v1)

---

## Build order (≈8 hrs, demo-first)
1. **(45m) Collect** — given a repo, find the last release tag and print merged PRs + commits since. Prove data access first.
2. **(75m) Generate (grounded)** — Claude turns those PRs into a user-facing "What's new", each line tagged with its PR #. **Minimum demo — reach by lunch.**
3. **(45m) Filter** — drop internal/non-user-facing PRs so the notes stay clean.
4. **(45m) Two registers** — add the technical changelog + group/classify (feature/fix/breaking).
5. **(60m) Publish** — changelog page + RSS feed + set the GitHub Release body.
6. **(45m) "Why" enrichment** — pull linked issues (+ diff fallback) so notes explain *why*, not just *what*.
7. **(remaining) Polish the page + demo script + record the clip.**

> Rule: keep one working end-to-end path at all times; layer on top.

---

## Demo script (the part that wins)
1. A repo with a few merged PRs since `v1.0` — one feature, one fix, one breaking change, **and one internal refactor** (to show the filter working).
2. On stage: run `release-notes since v1.0`.
3. Narrate: "reading the merged PRs… the refactor got filtered out as internal… it pulled the linked issue to understand *why*… each line links back to its PR so nothing is invented…"
4. Show the output: a polished **"What's new in v1.1"** page (with a subscribe-by-RSS link), each note linking to its PR, plus a technical changelog. Line: *"Raw PRs in, something you'd email a customer out — grounded in real PRs, no PM wrote a word."*

Keep a pre-recorded backup video.

---

## Cost & distribution (solo-friendly)
- **Cost:** fires only at **release time** (not per PR) → minimal LLM spend; the filter routes cheap classification to Haiku; ~$0 infra (Action + GitHub Pages). Cheapest of all the ideas.
- **Distribution (earns back the "less viral" concern):** the **changelog page** carries a "powered by [you]" footer → SEO + a viral-ish loop; the **RSS feed** gives users a notify channel with zero email ops; an in-app **widget** shows your brand to end users; ship as a **GitHub Marketplace** Action/App for self-serve installs.

---

## Productionization path (north star, not solo-v1)
- **Phase 1:** GitHub App + approval flow + hosted changelog page + RSS + the PR-time **user-impact capture** bot (the differentiator).
- **Phase 2:** add sending (or become the sender), audience segmentation, **impact-aware notes** (only tell users about features they use), analytics.
- **Phase 3:** the "release communication hub" — merge → every customer touchpoint from one source; the accumulated "why" becomes institutional memory (the moat).

Buyer: PM / founder / dev-rel / product-marketing. Pricing: per-active-repo or per-seat SaaS. Bottom-up entry: a dev installs the Action free → product upgrades for sending/segmentation.
