"""Agent — turn filtered PRs into grounded release notes (two registers).
Grounding: every note must cite a real PR number; we enforce it in code too."""
from __future__ import annotations

import json
from typing import List

import llm

from config import GEN_MODEL
from models import PRInfo, ReleaseNotes

# Edit this to match your product's voice. It's cached, so changing it is cheap to iterate on.
STYLE_GUIDE = """You write release notes for a software product, from its merged pull requests.

Rules:
1. GROUNDING — every item must reference exactly one PR from the provided list, by its
   pr_number. Never invent a change that isn't backed by a PR.
2. AUTHOR INTENT — if a PR includes `user_impact` (the author's own one-line statement of
   what changes for users), treat it as the authoritative source for the user-facing note.
   Prefer it over guessing from the title or diff.
3. CODE CHANGE — `diff` is the PR's actual code change (a unified diff of the changed files).
   Use it as the ground truth for *what* really changed, especially when the title/body are
   vague or empty. It sharpens the note — it never licenses inventing a change not in the list.
4. user_facing_text: ONE sentence, benefit-first, under ~25 words. Plain language, no jargon
   or internal names. Cut filler ("expanding your options", "ensuring a reliable experience",
   "making things easier") — state the concrete change and who it helps.
5. technical_text: the terse developer-changelog line (a few words is fine).
6. category is one of: feature, improvement, fix, breaking.
7. One item per PR (merge only true duplicates).
8. summary: ONE sentence (≤ 30 words) framing the release for users. No marketing fluff,
   no emoji in the text fields."""


def _pr_for_prompt(pr: PRInfo) -> dict:
    return {
        "pr_number": pr.number,
        "title": pr.title,
        "user_impact": pr.user_impact,
        "body": pr.body,
        "labels": pr.labels,
        "files_changed": pr.files_changed[:20],
        "diff": pr.diff,
        "linked_issues": [{"title": i.title, "body": i.body} for i in pr.linked_issues],
    }


def generate_notes(prs: List[PRInfo], version: str) -> ReleaseNotes:
    valid = {pr.number for pr in prs}
    payload = json.dumps(
        {"version": version, "pull_requests": [_pr_for_prompt(p) for p in prs]}, indent=2
    )
    notes = llm.structured(STYLE_GUIDE, payload, ReleaseNotes,
                           anthropic_model=GEN_MODEL, max_tokens=8000)
    if notes is None:
        return ReleaseNotes(summary="", items=[])

    # Grounding enforcement: drop anything not tied to a real PR in this release.
    notes.items = [it for it in notes.items if it.pr_number in valid]
    return notes
