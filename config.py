"""Central config — model choices and tunables, all in one place."""
import os

# Models (per ARCHITECTURE.md cost strategy):
GEN_MODEL = os.getenv("GEN_MODEL", "claude-sonnet-4-6")       # release-notes generation
FILTER_MODEL = os.getenv("FILTER_MODEL", "claude-haiku-4-5")  # cheap user-facing/internal classify
# POLISH_MODEL = "claude-opus-4-8"  # optional escalation for final polish (not wired in v1)

MAX_PRS = int(os.getenv("MAX_PRS", "100"))    # cap PRs included per release
MAX_SCAN = int(os.getenv("MAX_SCAN", "400"))  # cap closed-PR scan to bound API calls
BODY_TRUNCATE = 1200                           # chars of PR body sent to the model
ISSUE_TRUNCATE = 600                           # chars of linked-issue body sent to the model
