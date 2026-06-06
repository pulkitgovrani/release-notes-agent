"""Collector — find merged PRs since the last release and gather their context
(body, linked issues, diff summary). This is the deterministic 'read from GitHub'
half; no LLM here."""
from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional

from github import Github
from github.Repository import Repository

from config import BODY_TRUNCATE, ISSUE_TRUNCATE, MAX_PRS, MAX_SCAN
from models import LinkedIssue, PRInfo

# "Closes #12", "fixes #7", "resolved #99"
_LINK_RE = re.compile(r"(?i)\b(?:close[sd]?|fixe?[sd]?|resolve[sd]?)\s+#(\d+)")

# author-written "## User impact" section (the differentiator — captures the *why*)
_IMPACT_RE = re.compile(r"#{1,6}\s*user impact\s*\n(.+?)(?=\n#{1,6}\s|\Z)",
                        re.IGNORECASE | re.DOTALL)


def _extract_user_impact(body: Optional[str]) -> str:
    if not body:
        return ""
    m = _IMPACT_RE.search(body)
    if not m:
        return ""
    text = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.DOTALL).strip()
    if not text or text.lower() in {"n/a", "tbd", "none"}:
        return ""
    return text[:400]


def get_repo(token: Optional[str], repo_name: str) -> Repository:
    # token optional: public repos work unauthenticated (low rate limits)
    return (Github(token) if token else Github()).get_repo(repo_name)


def collect_one(repo: Repository, pr_number: int) -> PRInfo:
    """Build PRInfo for a single PR (used by the impact-suggestion bot)."""
    return _build_pr_info(repo, repo.get_pull(pr_number))


def get_since_date(repo: Repository, since_tag: Optional[str]) -> Optional[datetime]:
    """Datetime to collect PRs after. Explicit tag > latest release > None (first release)."""
    if since_tag:
        for tag in repo.get_tags():
            if tag.name == since_tag:
                return tag.commit.commit.author.date
        raise ValueError(f"Tag '{since_tag}' not found in {repo.full_name}")
    try:
        return repo.get_latest_release().created_at
    except Exception:
        return None  # no releases yet — treat everything (up to caps) as the first release


def _truncate(text: Optional[str], n: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[:n] + " …"


def _linked_issues(repo: Repository, body: Optional[str]) -> List[LinkedIssue]:
    out: List[LinkedIssue] = []
    seen = set()
    for num in (int(m) for m in _LINK_RE.findall(body or "")):
        if num in seen or len(out) >= 3:
            continue
        seen.add(num)
        try:
            issue = repo.get_issue(num)
            out.append(LinkedIssue(number=num, title=issue.title,
                                   body=_truncate(issue.body, ISSUE_TRUNCATE)))
        except Exception:
            continue  # referenced number wasn't a real/accessible issue
    return out


def _build_pr_info(repo: Repository, pr) -> PRInfo:
    try:
        files = [f.filename for f in pr.get_files()][:50]
    except Exception:
        files = []
    return PRInfo(
        number=pr.number,
        title=pr.title or "",
        body=_truncate(pr.body, BODY_TRUNCATE),
        user_impact=_extract_user_impact(pr.body),
        author=pr.user.login if pr.user else "unknown",
        merged_at=pr.merged_at.isoformat() if pr.merged_at else "",
        url=pr.html_url,
        labels=[l.name for l in pr.labels],
        files_changed=files,
        additions=pr.additions or 0,
        deletions=pr.deletions or 0,
        linked_issues=_linked_issues(repo, pr.body),
    )


def collect_prs(repo: Repository, since: Optional[datetime], limit: int = MAX_PRS) -> List[PRInfo]:
    """Merged PRs after `since` (or the most recent ones if since is None), capped at `limit`.
    Scans recently-updated closed PRs up to MAX_SCAN.

    NOTE (MVP limitation): scans by 'updated' order, not 'merged', so a very old
    PR merged into a fast-moving repo could be missed past MAX_SCAN. Fine for a
    demo; production would diff tag..HEAD via the compare API.
    """
    prs: List[PRInfo] = []
    scanned = 0
    for pr in repo.get_pulls(state="closed", sort="updated", direction="desc"):
        scanned += 1
        if scanned > MAX_SCAN or len(prs) >= limit:
            break
        if not pr.merged or pr.merged_at is None:
            continue
        if since is not None and pr.merged_at <= since:
            continue
        prs.append(_build_pr_info(repo, pr))
    return prs
