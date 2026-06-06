"""Publish — render the notes to a polished changelog page (HTML), Markdown, and
an RSS feed. Each line links back to its PR (grounding made visible)."""
from __future__ import annotations

import html
import os
import re
from difflib import SequenceMatcher
from typing import Dict, List

from models import AnnouncementDrafts, PRInfo, ReleaseNotes

_BACKPORT_RE = re.compile(r"^\s*back[\s-]?ports?\s+", re.I)
_MERGE_THRESHOLD = 0.9  # char-similarity above which two lines are treated as the same change


def _norm(text: str) -> str:
    """Normalize a user-facing line so backports / dupes collapse together (drop a leading
    'Backports', lowercase, strip trailing period and runs of whitespace)."""
    t = _BACKPORT_RE.sub("", text or "").strip().lower().rstrip(".")
    return re.sub(r"\s+", " ", t)


def _merge_items(items: list) -> list:
    """Collapse near-duplicate lines (same fix backported to several release branches, or
    true dupes) into one row linking ALL its PRs. Uses fuzzy similarity so 'Rejects X' and
    'Backports reject X' merge, while genuinely distinct lines stay separate. Grounding is
    preserved — every PR still appears (as a pill here, individually in the technical log)."""
    groups: List[dict] = []
    for it in items:
        k = _norm(it.user_facing_text)
        match = next((g for g in groups
                      if k == g["key"] or SequenceMatcher(None, k, g["key"]).ratio() >= _MERGE_THRESHOLD),
                     None)
        if match is None:
            groups.append({"key": k, "text": it.user_facing_text, "prs": [it.pr_number]})
        else:
            if len(it.user_facing_text) < len(match["text"]):  # prefer the cleaner / non-"Backports" phrasing
                match["text"] = it.user_facing_text
            match["prs"].append(it.pr_number)
    return groups

CATEGORY_META = {
    "breaking": ("⚠️", "Breaking changes"),
    "feature": ("✨", "New features"),
    "improvement": ("⚡", "Improvements"),
    "fix": ("🐛", "Bug fixes"),
}
_ORDER = ["breaking", "feature", "improvement", "fix"]

_CSS = """
:root{--accent:#6d5efc;--bg:#fafafb;--ink:#1c1c22;--muted:#6b6b77;--line:#ececf1;--breaking:#d99700}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.bar{height:4px;background:linear-gradient(90deg,var(--accent),#a78bfa)}
.wrap{max-width:720px;margin:0 auto;padding:56px 20px 96px}
.eyebrow{color:var(--muted);text-transform:uppercase;letter-spacing:.09em;font-size:.72rem;font-weight:700}
h1{font-size:2.3rem;letter-spacing:-.02em;margin:.18em 0 .12em}
.date{color:var(--muted);font-size:.9rem}
.summary{font-size:1.12rem;color:#34343d;margin:1.3em 0 2.4em}
.section{margin:2.2em 0}
.section h2{font-size:1.05rem;display:flex;align-items:center;gap:.45em;margin:0 0 .5em}
.items{background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}
.item{display:flex;gap:1em;align-items:baseline;justify-content:space-between;
 padding:.7em 1.05em;border-top:1px solid var(--line)}
.item:first-child{border-top:none}
.txt{flex:1}
.pill{flex:none;font-size:.72rem;color:var(--muted);text-decoration:none;
 border:1px solid var(--line);border-radius:999px;padding:.08em .6em;white-space:nowrap}
.pill:hover{border-color:var(--accent);color:var(--accent)}
.section.breaking .items{background:#fff9e9;border-color:#f0e2ab;border-left:4px solid var(--breaking)}
a{color:var(--accent)}
footer{margin-top:3.2em;padding-top:1.3em;border-top:1px solid var(--line);
 color:var(--muted);font-size:.85rem}
.section.announce h2{margin-bottom:.15em}
.announce-sub{color:var(--muted);font-size:.88rem;margin:0 0 1.1em}
.draft-block{background:#fff;border:1px solid var(--line);border-radius:12px;
 margin:0 0 .9em;overflow:hidden}
.draft-head{display:flex;justify-content:space-between;align-items:center;
 padding:.5em .9em;border-bottom:1px solid var(--line);background:#fbfbfe}
.chan{font-weight:700;font-size:.85rem}
.copy{font:inherit;font-size:.74rem;cursor:pointer;border:1px solid var(--line);
 background:#fff;color:var(--muted);border-radius:999px;padding:.18em .85em}
.copy:hover{border-color:var(--accent);color:var(--accent)}
.draft{margin:0;padding:.85em 1.05em;white-space:pre-wrap;
 font:inherit;font-size:.94rem;color:#2a2a32}
.thread{padding:.3em 0}
.tweet{display:flex;gap:.7em;padding:.6em 1.05em;border-top:1px solid var(--line)}
.tweet:first-child{border-top:none}
.tnum{flex:none;color:var(--muted);font-size:.74rem;font-variant-numeric:tabular-nums;padding-top:.15em}
.ttxt{flex:1;white-space:pre-wrap}
.stats{display:flex;flex-wrap:wrap;gap:.5em;margin:1.1em 0 0}
.chip{display:inline-flex;align-items:center;gap:.35em;font-size:.8rem;font-weight:600;
 color:#34343d;background:#fff;border:1px solid var(--line);border-radius:999px;padding:.28em .75em}
.prov{display:inline-flex;align-items:center;gap:.45em;font-weight:600;color:#34343d;margin-top:.6em}
.prov .dot{width:.55em;height:.55em;border-radius:50%;background:#76b900;
 box-shadow:0 0 0 3px rgba(118,185,0,.18)}
.pills{display:flex;flex-wrap:wrap;gap:.3em;justify-content:flex-end}
"""

_COPY_JS = (
    "<script>document.querySelectorAll('.copy').forEach(function(b){"
    "b.addEventListener('click',function(){"
    "var el=document.getElementById(b.dataset.cid);"
    "navigator.clipboard.writeText(el.textContent).then(function(){"
    "var t=b.textContent;b.textContent='Copied \\u2713';"
    "setTimeout(function(){b.textContent=t;},1500);});});});</script>"
)


def _index(prs: List[PRInfo]) -> Dict[int, str]:
    return {p.number: p.url for p in prs}


def _grouped(notes: ReleaseNotes) -> Dict[str, list]:
    out: Dict[str, list] = {c: [] for c in _ORDER}
    for it in notes.items:
        out.get(it.category, out["improvement"]).append(it)
    return out


def _sections_html(notes: ReleaseNotes, prs: List[PRInfo]) -> str:
    urls = _index(prs)
    grouped = _grouped(notes)
    out = []
    for cat in _ORDER:
        items = grouped[cat]
        if not items:
            continue
        emoji, title = CATEGORY_META[cat]
        rows = []
        for g in _merge_items(items):
            pills = "".join(
                f'<a class="pill" href="{html.escape(urls.get(n, "#"))}">#{n}</a>'
                for n in g["prs"]
            )
            rows.append(
                f'<div class="item"><span class="txt">{html.escape(g["text"])}</span>'
                f'<span class="pills">{pills}</span></div>'
            )
        out.append(
            f'<section class="section {cat}"><h2>{emoji} {title}</h2>'
            f'<div class="items">{"".join(rows)}</div></section>'
        )
    return "".join(out)


def _draft_block(chan: str, body_html: str, copy_text: str, cid: str) -> str:
    """One channel card: a header with a copy button, the rendered draft, and a hidden
    node holding the raw text (textContent decodes the entities back) for clipboard copy."""
    return (
        '<div class="draft-block">'
        f'<div class="draft-head"><span class="chan">{html.escape(chan)}</span>'
        f'<button class="copy" data-cid="{cid}">Copy</button></div>'
        f"{body_html}"
        f'<div id="{cid}" hidden>{html.escape(copy_text)}</div></div>'
    )


def _announce_html(drafts: AnnouncementDrafts) -> str:
    n = len(drafts.tweet_thread)
    tweets = "".join(
        f'<div class="tweet"><span class="tnum">{i}/{n}</span>'
        f'<span class="ttxt">{html.escape(t)}</span></div>'
        for i, t in enumerate(drafts.tweet_thread, 1)
    )
    blocks = [
        _draft_block("𝕏 / Twitter thread", f'<div class="thread">{tweets}</div>',
                     "\n\n".join(drafts.tweet_thread), "copy_x"),
        _draft_block("Slack", f'<div class="draft">{html.escape(drafts.slack_post)}</div>',
                     drafts.slack_post, "copy_slack"),
        _draft_block("LinkedIn", f'<div class="draft">{html.escape(drafts.linkedin_post)}</div>',
                     drafts.linkedin_post, "copy_li"),
    ]
    return (
        '<section class="section announce"><h2>📣 Announce this release</h2>'
        '<p class="announce-sub">Ready to paste — drafted from the same grounded notes, '
        "so nothing here is invented.</p>" + "".join(blocks) + "</section>"
    )


def _stats_chips(notes: ReleaseNotes) -> str:
    """Release-at-a-glance: one chip per non-empty category, counting distinct changes
    (after merge), so backport-padded counts don't overstate the release."""
    grouped = _grouped(notes)
    chips = []
    for cat in _ORDER:
        items = grouped[cat]
        if not items:
            continue
        n = len(_merge_items(items))
        emoji, title = CATEGORY_META[cat]
        chips.append(f'<span class="chip">{emoji} {n} {html.escape(title.lower())}</span>')
    return f'<div class="stats">{"".join(chips)}</div>' if chips else ""


def _provenance() -> str:
    """Human label of the model that wrote these notes — transparency for AI-drafted copy."""
    import llm
    label = llm.provider_label()
    if label.startswith("nvidia:"):
        return "NVIDIA " + label.split(":", 1)[1]
    if label.startswith("ollama:"):
        return "a local model (" + label.split(":", 1)[1] + ")"
    if label == "anthropic":
        return "Anthropic Claude"
    return label


def render_html(notes: ReleaseNotes, version: str, prs: List[PRInfo],
                repo: str, date_label: str, drafts: AnnouncementDrafts | None = None) -> str:
    sections = _sections_html(notes, prs)
    announce = _announce_html(drafts) if drafts else ""
    script = _COPY_JS if drafts else ""
    v, r = html.escape(version), html.escape(repo)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{r} — What's new in {v}</title>"
        '<link rel="alternate" type="application/rss+xml" title="Changelog" href="feed.xml">'
        f"<style>{_CSS}</style></head><body><div class=\"bar\"></div><div class=\"wrap\">"
        f'<div class="eyebrow">{r} · Changelog</div>'
        f"<h1>What's new in {v}</h1>"
        f'<div class="date">{html.escape(date_label)}</div>'
        f"{_stats_chips(notes)}"
        f'<p class="summary">{html.escape(notes.summary)}</p>'
        f"{sections}"
        f"{announce}"
        '<footer>📡 <a href="feed.xml">Subscribe via RSS</a> · '
        "powered by Release Intelligence"
        f'<br><span class="prov"><span class="dot"></span>'
        f"AI-drafted with {html.escape(_provenance())}, grounded in real merged PRs</span></footer>"
        f"</div>{script}</body></html>"
    )


def render_markdown(notes: ReleaseNotes, version: str, prs: List[PRInfo]) -> str:
    urls = _index(prs)
    grouped = _grouped(notes)
    lines = [f"# What's new in {version}", "", notes.summary, ""]
    for cat in _ORDER:
        items = grouped[cat]
        if not items:
            continue
        emoji, title = CATEGORY_META[cat]
        lines.append(f"## {emoji} {title}")
        for g in _merge_items(items):
            links = ", ".join(f"[#{n}]({urls.get(n, '')})" for n in g["prs"])
            lines.append(f"- {g['text']} ({links})")
        lines.append("")
    lines += ["---", "<details><summary>Technical changelog</summary>", ""]
    for it in notes.items:  # full, un-merged — every PR listed for a complete audit trail
        lines.append(f"- #{it.pr_number} ({it.category}): {it.technical_text}")
    lines += ["", "</details>"]
    return "\n".join(lines)


def render_announcements_markdown(drafts: AnnouncementDrafts, version: str) -> str:
    n = len(drafts.tweet_thread)
    lines = [f"# Announcement drafts — {version}", "",
             "_Drafted from the same grounded release notes. Copy, tweak, post._", "",
             "## 𝕏 / Twitter thread", ""]
    for i, t in enumerate(drafts.tweet_thread, 1):
        lines += [f"**{i}/{n}** {t}", ""]
    lines += ["## Slack", "", "```", drafts.slack_post, "```", "",
              "## LinkedIn", "", "```", drafts.linkedin_post, "```", ""]
    return "\n".join(lines)


def render_rss(notes: ReleaseNotes, version: str, prs: List[PRInfo],
               repo: str, pub_date: str) -> str:
    fragment = f"<p>{html.escape(notes.summary)}</p>" + _sections_html(notes, prs)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel>'
        f"<title>{html.escape(repo)} Changelog</title>"
        f"<link>https://github.com/{html.escape(repo)}/releases</link>"
        f"<description>Product updates for {html.escape(repo)}</description>"
        f"<item><title>{html.escape(f'{repo} {version}')}</title>"
        f"<pubDate>{pub_date}</pubDate>"
        f"<description><![CDATA[{fragment}]]></description></item>"
        "</channel></rss>"
    )


def write_outputs(notes: ReleaseNotes, version: str, prs: List[PRInfo], repo: str,
                  out_dir: str, pub_date: str, date_label: str,
                  drafts: AnnouncementDrafts | None = None) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    files = {
        "markdown": (os.path.join(out_dir, "CHANGELOG.md"),
                     render_markdown(notes, version, prs)),
        "html": (os.path.join(out_dir, "index.html"),
                 render_html(notes, version, prs, repo, date_label, drafts)),
        "rss": (os.path.join(out_dir, "feed.xml"),
                render_rss(notes, version, prs, repo, pub_date)),
    }
    if drafts:
        files["announce"] = (os.path.join(out_dir, "ANNOUNCEMENTS.md"),
                             render_announcements_markdown(drafts, version))
    for path, content in files.values():
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    return {k: v[0] for k, v in files.items()}
