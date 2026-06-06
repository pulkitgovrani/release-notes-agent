"""Impact-suggestion bot (NEXT_STEPS step 3) — given a PR, suggest a one-line user
impact + category from its diff, so the author just confirms or edits.

  python suggest_impact.py --repo owner/name --pr 123            # print suggestion
  python suggest_impact.py --repo owner/name --pr 123 --comment  # post it on the PR
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv

import collector
import llm
from config import GEN_MODEL
from models import ImpactSuggestion

GUIDE = """You read a pull request and suggest its release-note classification.
Return:
- internal: true if the change has no user-visible effect (refactor, CI, deps, tests).
- category: feature | improvement | fix | breaking.
- user_impact: ONE plain-language sentence on what changes for users (empty if internal)."""


def suggest(repo_name, pr_number, token):
    repo = collector.get_repo(token, repo_name)
    pr = collector.collect_one(repo, pr_number)
    payload = json.dumps(
        {"title": pr.title, "body": pr.body, "files_changed": pr.files_changed[:20]}, indent=2
    )
    s = llm.structured(GUIDE, payload, ImpactSuggestion, anthropic_model=GEN_MODEL, max_tokens=1000)
    return pr, s


def main() -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(description="Suggest a user-impact line for a PR.")
    ap.add_argument("--repo", default=os.getenv("GITHUB_REPO"), help="owner/name")
    ap.add_argument("--pr", type=int, required=True, help="PR number")
    ap.add_argument("--comment", action="store_true", help="post the suggestion as a PR comment")
    ap.add_argument("--provider", choices=["anthropic", "ollama"], default=None)
    ap.add_argument("--local", action="store_true", help="use local Ollama")
    ap.add_argument("--ollama-model", dest="ollama_model", default=None)
    args = ap.parse_args()

    provider = "ollama" if args.local else (args.provider or os.getenv("LLM_PROVIDER", "anthropic"))
    os.environ["LLM_PROVIDER"] = provider
    if args.ollama_model:
        os.environ["OLLAMA_MODEL"] = args.ollama_model
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY, or use --local.", file=sys.stderr)
        return 2

    token = os.getenv("GITHUB_TOKEN")
    if not args.repo:
        print("Set --repo / GITHUB_REPO.", file=sys.stderr)
        return 2

    pr, s = suggest(args.repo, args.pr, token)
    if s is None:
        print("No suggestion produced.")
        return 1

    md = (
        f"🤖 **Suggested release note** for #{pr.number}\n\n"
        f"- **Category:** {s.category}{' — internal, likely skip' if s.internal else ''}\n"
        f"- **User impact:** {s.user_impact or '_none_'}\n\n"
        f"_Edit the `## User impact` section in the PR body to adjust._"
    )
    print(md)

    if args.comment:
        if not token:
            print("--comment needs GITHUB_TOKEN.", file=sys.stderr)
            return 2
        repo = collector.get_repo(token, args.repo)
        repo.get_pull(pr.number).create_issue_comment(md)
        print("\n✅ Posted comment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
