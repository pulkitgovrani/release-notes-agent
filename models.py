"""Typed data shapes. The two passed to Claude as output_format are
FilterOutput and ReleaseNotes — keep them schema-simple (no min/max constraints)."""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel


# ---- collected from GitHub (internal, not LLM output) ----
class LinkedIssue(BaseModel):
    number: int
    title: str
    body: str


class PRInfo(BaseModel):
    number: int
    title: str
    body: str
    user_impact: str = ""           # author-stated impact (## User impact), if present
    author: str
    merged_at: str
    url: str
    labels: List[str]
    files_changed: List[str]
    diff: str = ""                  # combined unified diff of the changed files (the actual code change)
    additions: int
    deletions: int
    linked_issues: List[LinkedIssue]


# ---- LLM structured outputs ----
class FilterDecision(BaseModel):
    pr_number: int
    user_facing: bool
    reason: str


class FilterOutput(BaseModel):
    decisions: List[FilterDecision]


class ImpactSuggestion(BaseModel):
    internal: bool
    category: Literal["feature", "improvement", "fix", "breaking"]
    user_impact: str


class ReleaseNoteItem(BaseModel):
    pr_number: int                                              # grounding: ties the note to a real PR
    category: Literal["feature", "improvement", "fix", "breaking"]
    user_facing_text: str                                       # customer-friendly
    technical_text: str                                         # dev changelog


class ReleaseNotes(BaseModel):
    summary: str
    items: List[ReleaseNoteItem]


# ---- announcement drafts (one grounded release -> every channel) ----
class AnnouncementDrafts(BaseModel):
    tweet_thread: List[str]   # each string is one tweet, in posting order
    slack_post: str           # ready to paste into #announcements (Slack mrkdwn)
    linkedin_post: str        # short professional post
