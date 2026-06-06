"""Filter — keep only user-facing PRs, drop internal noise (refactors, CI, deps).
Cheap heuristics first; Claude (Haiku) only for the ambiguous ones."""
from __future__ import annotations

import json
from typing import List, Optional, Tuple

import llm

from config import FILTER_MODEL
from models import FilterOutput, PRInfo

_INTERNAL_PREFIXES = ("chore", "ci", "build", "test", "refactor", "style", "perf-internal")
_INTERNAL_PATHS = (".github/", "tests/", "test/", ".circleci/", "scripts/ci")

_FILTER_GUIDE = """You classify pull requests as user-facing or internal for a product changelog.

USER-FACING = something a customer would notice: new features, user-visible bug fixes,
performance/UX improvements, API or behavior changes.
INTERNAL = refactors, CI/build/test-only changes, dependency bumps with no user impact,
internal tooling, code cleanup.

For each PR, return user_facing (bool) and a one-line reason. Be strict: when a change
has no observable effect for a user, mark it internal."""


def _heuristic(pr: PRInfo) -> Optional[bool]:
    """True/False if obvious, None if ambiguous (-> ask the model)."""
    if pr.user_impact.strip().lower() == "internal":   # author classified it themselves
        return False
    prefix = pr.title.split(":")[0].strip().lower() if ":" in pr.title else ""
    if prefix in _INTERNAL_PREFIXES:
        return False
    if pr.files_changed and all(
        any(f.startswith(p) for p in _INTERNAL_PATHS) for f in pr.files_changed
    ):
        return False
    return None


def _classify_with_llm(prs: List[PRInfo]) -> dict[int, bool]:
    payload = json.dumps([
        {"pr_number": p.number, "title": p.title, "labels": p.labels,
         "files_changed": p.files_changed[:15], "body": p.body[:400]}
        for p in prs
    ], indent=2)
    out = llm.structured(_FILTER_GUIDE, payload, FilterOutput,
                         anthropic_model=FILTER_MODEL, max_tokens=4000)
    return {d.pr_number: d.user_facing for d in out.decisions} if out else {}


def filter_user_facing(prs: List[PRInfo]) -> Tuple[List[PRInfo], List[PRInfo]]:
    """Returns (kept, dropped)."""
    decided: dict[int, bool] = {}
    ambiguous: List[PRInfo] = []
    for pr in prs:
        h = _heuristic(pr)
        if h is None:
            ambiguous.append(pr)
        else:
            decided[pr.number] = h
    if ambiguous:
        decided.update(_classify_with_llm(ambiguous))

    kept = [p for p in prs if decided.get(p.number, True)]   # default keep if unknown
    dropped = [p for p in prs if not decided.get(p.number, True)]
    return kept, dropped
