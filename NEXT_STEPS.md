# Roadmap

## ✅ v1 (shipped)
- **Collect** merged PRs with windows: since release / `--last N` / `--since-hours` / `--since-days`
- **User-impact capture**: PR template + parse `## User impact`; author intent feeds the notes;
  `internal` PRs auto-dropped; nudge + auto-suggest Actions
- **Filter** user-facing vs internal (heuristics + LLM)
- **Grounded, concise notes**: every line cites a PR; one-sentence user-facing copy
- Two registers: user-facing "What's new" + technical changelog
- **Publish**: changelog page + RSS + **GitHub Pages hosting**
- **Providers**: Anthropic API *or* local Ollama (free, offline)

## 🔜 v2 (next)
1. **Accumulating changelog history** — persist past releases so the page + RSS show a real
   timeline, not just the latest run.
2. **Multi-channel announcement drafts** — turn one grounded release into a tweet thread, a
   Slack post, and a LinkedIn post (one source → every channel).
3. **Email / delivery** — integrate the customer's email tool (Mailchimp / Customer.io /
   Resend); later, optionally become the sender (deliverability, consent/GDPR, unsubscribe).
4. **Impact-aware notes** — only tell each user about features relevant to them (usage data),
   plus audience segmentation (free vs enterprise).
5. **Analytics loop** — open rates / which features land → feedback to product.
6. **In-app changelog widget** — a small JS embed so users see updates inside the product.
7. **GitHub Marketplace App** — one-click install + a nicer bot identity.
8. **Version-bump suggestion** — infer semver (major/minor/patch) from breaking/feature/fix.
9. **Brand voice** — few-shot the company's past notes to match tone.
10. **No-PR fallback** — generate from commits for repos that push straight to main.
11. **Multi-language** release notes.

## Business
Buyer: PM / founder / dev-rel / product-marketing. Pricing: per-active-repo or per-seat SaaS.
Bottom-up: a dev installs the Action free → product upgrades for delivery/segmentation. The
accumulated "why" (impact capture) becomes institutional memory — the moat.
