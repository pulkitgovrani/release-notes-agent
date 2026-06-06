"""Canned sample PRs for a reliable, offline demo (--demo).

The set is chosen to tell a story on stage: 4 user-facing changes (feature, fix,
breaking, improvement) + 2 internal ones that the filter should drop. Still runs
the real filter + agent, so judges see real AI output — just without a live repo."""
from models import LinkedIssue, PRInfo

_REPO_URL = "https://github.com/acme/widget"


def _pr(number, title, body, labels, files, add, dele, issues=None, user_impact=""):
    return PRInfo(
        number=number, title=title, body=body, author="dev",
        merged_at="2026-06-05T10:00:00+00:00", url=f"{_REPO_URL}/pull/{number}",
        labels=labels, files_changed=files, additions=add, deletions=dele,
        user_impact=user_impact, linked_issues=issues or [],
    )


def sample_prs():
    return [
        _pr(
            142, "feat: dark mode toggle in settings",
            "Adds a dark mode toggle under Settings → Appearance. Preference persists "
            "across sessions. Closes #120",
            ["feature", "ui"], ["src/settings.tsx", "src/theme.ts"], 210, 14,
            [LinkedIssue(number=120, title="Please add a dark mode",
                         body="Lots of users on the forum keep asking for a dark theme, "
                              "especially for late-night work.")],
            user_impact="Users finally get the dark theme they've been asking for.",
        ),
        _pr(
            138, "fix: scheduled exports running one hour late",
            "Scheduled exports used the server's local time instead of the user's "
            "timezone, so they fired an hour off after DST. Now uses the account "
            "timezone. Fixes #131",
            ["bug"], ["src/jobs/export.ts"], 22, 9,
            [LinkedIssue(number=131, title="My 9am export arrives at 10am",
                         body="Every export is exactly one hour late since last week.")],
        ),
        _pr(
            145, "feat!: rename `name` to `full_name` in the Users API",
            "BREAKING: the `/v1/users` response field `name` is renamed to `full_name` "
            "for consistency with the rest of the API. The old field is removed.",
            ["api", "breaking"], ["src/api/users.ts", "docs/api.md"], 40, 31,
            user_impact="Anyone reading the `name` field from the Users API must switch to `full_name`.",
        ),
        _pr(
            140, "perf: stream CSV export instead of buffering",
            "Large CSV exports were built in memory and timed out past ~50k rows. "
            "We now stream rows, cutting export time roughly 3x and removing the cap.",
            ["performance"], ["src/export/csv.ts"], 88, 60,
        ),
        # --- these two should be filtered out as internal ---
        _pr(
            133, "chore: bump eslint and tidy CI workflow",
            "Routine lint/dep bump and a CI matrix cleanup. No user impact.",
            ["chore"], [".github/workflows/ci.yml", "package.json"], 12, 40,
        ),
        _pr(
            129, "refactor: extract shared validation helpers",
            "Pulls duplicated input validation into a shared module. Pure refactor.",
            ["refactor"], ["src/lib/validate.ts", "src/api/users.ts"], 70, 95,
        ),
    ]
