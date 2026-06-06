"""Announce — turn the finished release notes into ready-to-post announcement drafts
for the channels a team actually ships updates on (X/Twitter thread, Slack, LinkedIn).

One grounded source of truth (the release notes) -> every channel. This is the first
concrete step toward the "release communication hub" north star in ARCHITECTURE.md:
merge -> every customer touchpoint, written once. It reuses the already-grounded items,
so the drafts inherit the no-invented-features guarantee — never re-derived from raw PRs.
"""
from __future__ import annotations

import json
from typing import Optional

import llm

from config import GEN_MODEL
from models import AnnouncementDrafts, ReleaseNotes

ANNOUNCE_GUIDE = """You are a developer-marketing writer. Turn a software release's notes
into ready-to-post announcement drafts. You're given the release summary and a list of
user-facing items — each is already grounded in a real shipped change.

Write three channel drafts, each in its native voice:

1. tweet_thread — an X/Twitter thread, as a list of tweets in posting order.
   - Tweet 1 hooks with the single most exciting change + the version. No "🧵 Thread" cliche.
   - Each later tweet covers one notable item, benefit-first and concrete, ≤ 270 chars.
   - Lead any breaking change clearly ("⚠️ Heads up:"). Final tweet points to the full notes
     (use page_url if given). 3–6 tweets total; ≤ 2 tasteful hashtags across the WHOLE thread.
2. slack_post — one message to paste into a team's #announcements channel.
   - Slack mrkdwn (*bold*, "•" bullets), short and friendly, not salesy.
   - Open with the version + a one-line why-it-matters, then the highlights.
3. linkedin_post — a short professional post (≤ 120 words). Lead with user value, not internal
   jargon. One light emoji is fine; ≤ 3 hashtags at the very end.

Rules: only mention changes present in the provided items — never invent or embellish a
feature. Benefit-first, cut filler. Enthusiastic but credible developer-tools tone."""


def generate_announcements(notes: ReleaseNotes, version: str, repo: str,
                           page_url: str = "") -> Optional[AnnouncementDrafts]:
    """Draft channel announcements from the grounded notes. None if there's nothing to announce."""
    if not notes.items:
        return None
    payload = json.dumps({
        "repo": repo,
        "version": version,
        "page_url": page_url,
        "summary": notes.summary,
        "items": [
            {"category": it.category, "text": it.user_facing_text}
            for it in notes.items
        ],
    }, indent=2)
    return llm.structured(ANNOUNCE_GUIDE, payload, AnnouncementDrafts,
                          anthropic_model=GEN_MODEL, max_tokens=2000)
