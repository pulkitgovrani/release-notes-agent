"""Release Intelligence agent — CLI entry point.

  python main.py --repo owner/name --since v1.0 --version v1.1
  python main.py --repo facebook/react --last 10        # most recent 10 merged PRs
  python main.py --demo                                  # offline demo (canned PRs)
  python main.py --demo --local                          # ...run on a local Ollama model (free)

Wires: collect merged PRs (chosen window) -> filter user-facing -> generate
grounded notes -> publish a changelog page + RSS feed.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

from dotenv import load_dotenv

import agent
import announce
import collector
import demo_data
import llm
import filter as pr_filter
import publish
from config import MAX_PRS


def _resolve_window(gh_repo, args, now) -> tuple:
    """Pick which merged PRs to include. Returns (since_or_None, limit, label)."""
    if args.last:
        return None, args.last, f"last {args.last} merged PRs"
    if args.since_hours:
        return now - timedelta(hours=args.since_hours), MAX_PRS, f"last {args.since_hours}h"
    if args.since_days:
        return now - timedelta(days=args.since_days), MAX_PRS, f"last {args.since_days}d"
    if args.since:
        return collector.get_since_date(gh_repo, args.since), MAX_PRS, f"since {args.since}"
    return collector.get_since_date(gh_repo, None), MAX_PRS, "since last release"


def main() -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(description="Generate grounded release notes from merged PRs.")
    ap.add_argument("--repo", default=os.getenv("GITHUB_REPO"), help="owner/name")
    ap.add_argument("--version", default="Unreleased", help="label for this release, e.g. v1.1")
    ap.add_argument("--output", default="./output", help="output directory")
    ap.add_argument("--demo", action="store_true", help="use canned sample PRs (no GitHub needed)")
    ap.add_argument("--announce", action=argparse.BooleanOptionalAction, default=True,
                    help="also draft X/Slack/LinkedIn announcements (--no-announce to skip)")
    # --- LLM provider ---
    ap.add_argument("--provider", choices=["anthropic", "ollama"], default=None,
                    help="LLM provider (default: env LLM_PROVIDER or anthropic)")
    ap.add_argument("--local", action="store_true", help="shortcut for --provider ollama (free, offline)")
    ap.add_argument("--ollama-model", dest="ollama_model", default=None,
                    help="local model name, e.g. gemma3n:e4b (see: ollama list)")
    # --- window: pick one (default = since last release) ---
    ap.add_argument("--since", default=None, help="tag to diff from")
    ap.add_argument("--last", type=int, default=None, help="most recent N merged PRs")
    ap.add_argument("--since-hours", type=int, default=None, dest="since_hours",
                    help="PRs merged in the last H hours")
    ap.add_argument("--since-days", type=int, default=None, dest="since_days",
                    help="PRs merged in the last D days")
    args = ap.parse_args()

    # Resolve provider (CLI > env > default) and validate prerequisites.
    provider = "ollama" if args.local else (args.provider or os.getenv("LLM_PROVIDER", "anthropic"))
    os.environ["LLM_PROVIDER"] = provider
    if args.ollama_model:
        os.environ["OLLAMA_MODEL"] = args.ollama_model
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY, or use --local for a free local Ollama model.", file=sys.stderr)
        return 2
    print(f"→ LLM provider: {llm.provider_label()}")

    now = datetime.now(timezone.utc)

    # 1. Collect
    if args.demo:
        repo = "acme/widget"
        version = args.version if args.version != "Unreleased" else "v2.0"
        print("→ Demo mode: using canned sample PRs")
        prs = demo_data.sample_prs()
    else:
        token = os.getenv("GITHUB_TOKEN")
        if not args.repo:
            print("Set GITHUB_REPO/--repo, or use --demo.", file=sys.stderr)
            return 2
        if not token:
            print("  (no GITHUB_TOKEN — using unauthenticated GitHub; low rate limits)")
        repo, version = args.repo, args.version
        gh_repo = collector.get_repo(token, repo)
        since, limit, label = _resolve_window(gh_repo, args, now)
        print(f"→ Collecting merged PRs in {repo} ({label}) …")
        prs = collector.collect_prs(gh_repo, since, limit)
    print(f"  found {len(prs)} merged PR(s)")
    if not prs:
        print("Nothing to release. Exiting.")
        return 0

    # 2. Filter
    print("→ Filtering user-facing vs internal …")
    kept, dropped = pr_filter.filter_user_facing(prs)
    print(f"  kept {len(kept)} user-facing, dropped {len(dropped)} internal "
          f"({', '.join('#%d' % p.number for p in dropped) or '—'})")
    if not kept:
        print("No user-facing changes. Exiting.")
        return 0

    # 3. Generate (grounded)
    print("→ Generating release notes with the agent …")
    notes = agent.generate_notes(kept, version)
    print(f"  wrote {len(notes.items)} grounded item(s)")

    # 3b. Announce — same grounded notes -> ready-to-post channel drafts
    drafts = None
    if args.announce:
        print("→ Drafting announcements (X / Slack / LinkedIn) …")
        page_url = f"https://github.com/{repo}/releases"
        drafts = announce.generate_announcements(notes, version, repo, page_url)
        if drafts:
            print(f"  drafted a {len(drafts.tweet_thread)}-tweet thread + Slack + LinkedIn")

    # 4. Publish
    paths = publish.write_outputs(
        notes, version, kept, repo, args.output,
        pub_date=format_datetime(now), date_label=now.strftime("%B %d, %Y"),
        drafts=drafts,
    )
    print("\n✅ Done. Outputs:")
    for kind, path in paths.items():
        print(f"   {kind:9} {path}")
    print(f"\nPreview the page:  open {paths['html']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
