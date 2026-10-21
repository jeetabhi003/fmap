"""Web: builds the static site (GitHub Pages) for the three funnels.

Each segment page carries all three layers: the free checklist (Layer 1), the
ebook (Layer 2) and the shortlist request handed to a licensed agent (Layer 3).
Project tables appear only when publish_project_tables is true in the config.
Links that are not set yet render as disabled "coming soon" buttons.
"""

import html
import json
import re

from core import load_json

NAME = "web"
DISCLAIMER = "Research, not advice. Verify each project on MahaRERA before you pay."

CSS = """:root {
  --bg: #fafaf7; --fg: #1d1d1b; --muted: #5d5d58; --accent: #1f5f4a;
  --card: #ffffff; --line: #e2e2dc; --on-accent: #ffffff;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #161614; --fg: #ecece6; --muted: #a4a49c; --accent: #7fc4a8;
    --card: #1f1f1c; --line: #33332f; --on-accent: #10201a;
  }
}
:root[data-theme="dark"] {
  --bg: #161614; --fg: #ecece6; --muted: #a4a49c; --accent: #7fc4a8;
  --card: #1f1f1c; --line: #33332f; --on-accent: #10201a;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; }
header, main, footer { max-width: 780px; margin: 0 auto; padding: 0 16px; }
header { padding-top: 20px; display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: baseline; }
header .brand { font-weight: 700; color: var(--fg); text-decoration: none; margin-right: auto; }
header a { color: var(--muted); }
main { padding-bottom: 48px; }
h1 { font-size: 1.8rem; line-height: 1.25; margin: 28px 0 12px; }
h2 { font-size: 1.25rem; margin: 32px 0 8px; }
h3 { font-size: 1.05rem; margin: 20px 0 6px; }
p, li { color: var(--muted); }
a { color: var(--accent); }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 18px 20px; margin: 16px 0; }
.cards { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
.layer { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--accent); margin: 0; }
.btn { display: inline-block; background: var(--accent); color: var(--on-accent); text-decoration: none; padding: 10px 16px; border-radius: 8px; font-weight: 600; }
.btn-off { background: var(--line); color: var(--muted); cursor: not-allowed; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 0.92rem; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
footer { border-top: 1px solid var(--line); padding-top: 16px; padding-bottom: 32px; font-size: 0.85rem; color: var(--muted); }
"""


def esc(text):
    return html.escape(str(text), quote=True)


def button(url, label):
    if url:
        return f'<a class="btn" href="{esc(url)}">{esc(label)}</a>'
    return f'<span class="btn btn-off" aria-disabled="true">{esc(label)} (coming soon)</span>'


def render_markdown(text):
    """Small Markdown subset: headings, bullet and numbered lists, paragraphs, **bold**."""
    out, para, list_tag = [], [], None

    def inline(s):
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc(s))

    def flush():
        nonlocal list_tag
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()
        if list_tag:
            out.append(f"</{list_tag}>")
            list_tag = None

    for raw in text.splitlines():
        line = raw.strip()
        heading = re.match(r"^(#{1,3}) (.+)$", line)
        bullet = re.match(r"^- (.+)$", line)
        numbered = re.match(r"^\d+\. (.+)$", line)
        if not line:
            flush()
        elif heading:
            flush()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
        elif bullet or numbered:
            tag = "ul" if bullet else "ol"
            if para:
                out.append(f"<p>{inline(' '.join(para))}</p>")
                para.clear()
            if list_tag != tag:
                if list_tag:
                    out.append(f"</{list_tag}>")
                out.append(f"<{tag}>")
                list_tag = tag
            out.append(f"<li>{inline((bullet or numbered).group(1))}</li>")
        else:
            if list_tag:
                out.append(f"</{list_tag}>")
                list_tag = None
            para.append(line)
    flush()
    return "\n".join(out)


def chapters(outline_text):
    return re.findall(r"^\d+\. \*\*(.+?)\*\*", outline_text, re.M)


def page(cfg, segments, title, description, body):
    launch = cfg.get("launch", {})
    agent = launch.get("agent_rera_number") or "registration number to be added before launch"
    contact = launch.get("contact_email")
    nav = " ".join(f'<a href="{s["slug"]}.html">{esc(s["nav"])}</a>' for s in segments)
    contact_line = f' Contact: <a href="mailto:{esc(contact)}">{esc(contact)}</a>.' if contact else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header><a class="brand" href="index.html">{esc(cfg.get("brand", ""))}</a> {nav}</header>
<main>
{body}
</main>
<footer>
<p>{DISCLAIMER} Project data as of {esc(cfg.get("data_as_of", ""))}.</p>
<p>Property sales are handled by a MahaRERA-registered agent: {esc(agent)}.{contact_line} <a href="privacy.html">Privacy</a></p>
</footer>
</body>
</html>
"""


def project_section(cfg, shortlist):
    if not cfg.get("publish_project_tables"):
        return ("<h2>Projects</h2>\n<p>We share a shortlist on request. Every project on it comes with its "
                "MahaRERA ID and the date its facts were checked.</p>")
    rows = "".join(
        f"<tr><td>{esc(e['project'])}</td><td>{esc(e['rera_id'])}</td><td>{esc(e['status'])}</td>"
        f"<td>₹{esc(e['price_cr_range'])} Cr</td><td>{esc(e['caveats'])}</td></tr>"
        for e in shortlist["matched"]
    )
    pending = ", ".join(esc(e["project"]) for e in shortlist["to_check"])
    table = (f'<div class="table-wrap"><table><thead><tr><th>Project</th><th>MahaRERA ID</th><th>Status</th>'
             f"<th>Price range</th><th>Still to check</th></tr></thead><tbody>{rows}</tbody></table></div>"
             if rows else "<p>No project in this segment has a verified price yet.</p>")
    extra = f"<p>Price on request: {pending}.</p>" if pending else ""
    return f"<h2>Projects with a verified price</h2>\n{table}\n{extra}"


def segment_page(ctx, cfg, segments, seg, shortlist):
    launch = cfg.get("launch", {})
    outline_path = ctx.path(seg["ebook_file"])
    titles = chapters(outline_path.read_text(encoding="utf-8")) if outline_path.exists() else []
    chapter_list = "".join(f"<li>{esc(t)}</li>" for t in titles)
    worries = "".join(f"<li>{esc(w)}</li>" for w in seg["worries"])
    body = f"""<h1>{esc(seg['headline'])}</h1>
<p>{esc(seg['intro'])}</p>
<h2>What buyers like you ask</h2>
<ul>{worries}</ul>
<div class="card">
<p class="layer">Free</p>
<h3>The buyer's checklist</h3>
<p>The checks to run before you pay a deposit. Free by email.</p>
<p>{button(launch.get('form_url'), 'Get the free checklist')}</p>
</div>
{project_section(cfg, shortlist)}
<div class="card">
<p class="layer">Guide</p>
<h3>{esc(seg['ebook_title'])}</h3>
<ol>{chapter_list}</ol>
<p>{button(launch.get('ebook_store_urls', {}).get(seg['key']), 'Buy the guide')}</p>
</div>
<div class="card">
<p class="layer">Shortlist</p>
<h3>Get a shortlist for your budget</h3>
<p>Tell us your budget, timeline and purpose. A MahaRERA-registered agent follows up with projects that fit, each with what is verified and what is still open.</p>
<p>{button(launch.get('shortlist_form_url'), 'Request a shortlist')}</p>
</div>"""
    return page(cfg, segments, f"{seg['title']} | {cfg.get('brand', '')}", seg["intro"], body)


def index_page(cfg, segments):
    cards = "".join(
        f'<div class="card"><h3><a href="{s["slug"]}.html">{esc(s["title"])}</a></h3><p>{esc(s["blurb"])}</p></div>'
        for s in segments
    )
    body = f"""<h1>Buying property in {esc(cfg.get('market', ''))}? Check before you pay.</h1>
<p>A free checklist, guides for each kind of buyer, and a shortlist service. Every project fact comes with its MahaRERA ID and the date it was checked.</p>
<h2>Which buyer are you?</h2>
<div class="cards">{cards}</div>
<h2>How it works</h2>
<ol>
<li><strong>Free checklist.</strong> The checks to run before any deposit.</li>
<li><strong>Guide.</strong> A deeper guide for your kind of purchase.</li>
<li><strong>Shortlist.</strong> Projects that fit your budget, handed to a MahaRERA-registered agent.</li>
</ol>
<h2>What we do not do</h2>
<p>We do not predict returns, rank any project as a sure thing, or take deposits. Unknown facts stay marked unknown.</p>"""
    return page(cfg, segments, cfg.get("brand", ""), "Verified project facts and checklists for property buyers.", body)


def privacy_page(cfg, segments):
    contact = cfg.get("launch", {}).get("contact_email") or "the contact email shown once we launch"
    body = f"""<h1>Privacy</h1>
<p>We collect only what we need to send what you asked for: your name, email, and the kind of buyer you are. We ask for a phone number, budget and timeline only if you request a shortlist.</p>
<h2>How we use it</h2>
<ul>
<li>To send the checklist and a short series of emails. Every email has an unsubscribe link.</li>
<li>To pass a shortlist request to a MahaRERA-registered agent, only with your consent.</li>
</ul>
<h2>Your rights</h2>
<p>You can ask us to show, correct or delete your data at any time. Write to {esc(contact)}. We act on deletion requests within 7 days.</p>
<p>We follow India's Digital Personal Data Protection Act, 2023. We do not sell your data.</p>"""
    return page(cfg, segments, f"Privacy | {cfg.get('brand', '')}", "How we use your data.", body)


def do(ctx):
    cfg = ctx.config
    segments = load_json(ctx.path("toolkit", "segments.json"))
    shortlists = json.loads((ctx.upstream("matching") / "shortlists.json").read_text(encoding="utf-8"))
    checklist = ctx.path("products", "lead-magnet", "checklist.md").read_text(encoding="utf-8")
    files = {
        "style.css": CSS,
        "index.html": index_page(cfg, segments),
        "privacy.html": privacy_page(cfg, segments),
        "checklist.html": page(cfg, segments, f"Buyer's checklist | {cfg.get('brand', '')}",
                               "The checks to run before you pay a deposit.", render_markdown(checklist)),
    }
    for seg in segments:
        files[f"{seg['slug']}.html"] = segment_page(ctx, cfg, segments, seg, shortlists[seg["key"]])
    return files


def verify(ctx, files):
    problems = []
    for name, text in files.items():
        if not name.endswith(".html"):
            continue
        if DISCLAIMER not in text:
            problems.append(f"{name}: missing disclaimer")
        if "FORM_ID" in text:
            problems.append(f"{name}: placeholder FORM_ID left in page")
        for link in re.findall(r'href="([^"#:]+\.(?:html|css))"', text):
            if link not in files:
                problems.append(f"{name}: broken link to {link}")
    return problems


def summary(files):
    pages = sum(n.endswith(".html") for n in files)
    return f"{pages} page(s) built into site/"
