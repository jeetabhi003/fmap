"""References: analyses reference Instagram reels to learn why they work. Never downloads or reposts them.

Input: data/inputs/reels.csv (kept out of git). Template: data/inputs/reels.template.csv.
Each row needs a reel URL. The caption can be pasted in, or fetched from the
public reel page on the laptop with `run --fetch-reels` (cached in
data/inputs/reels_cache.json). Instagram is blocked from the cloud session.

Outputs:
  analysis.json  one record per reel: caption features, pattern, reasons it works (private, local only)
  playbook.md    patterns and rules to reuse in our own words, per customer segment
  style.json     the pattern, caption shape and format the storyboard department uses
"""

import html
import json
import re
import urllib.request
from collections import Counter
from statistics import median

from core import Pending, read_csv_rows

NAME = "references"

COLUMNS = ["url", "account", "caption", "format", "length_sec", "notes"]
REEL_URL = re.compile(r"^https://(www\.)?instagram\.com/(reel|reels|p)/[A-Za-z0-9_-]+/?(\?.*)?$")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅❌]")
PRICE = re.compile(r"(₹|rs\.?\s?\d|\d+(\.\d+)?\s?(cr|crore|lakh|lac|l)\b)", re.I)
NUMBER = re.compile(r"\d")
LIST_LINE = re.compile(r"^\s*(\d+[.)]|[-•✅❌👉➡️]|[\U0001F300-\U0001FAFF])")
CTAS = {
    "comment": re.compile(r"\bcomment\b", re.I),
    "dm": re.compile(r"\b(dm|direct message|message us)\b", re.I),
    "save": re.compile(r"\bsave\b", re.I),
    "share": re.compile(r"\bshare\b", re.I),
    "follow": re.compile(r"\bfollow\b", re.I),
    "link_in_bio": re.compile(r"link in (the )?bio", re.I),
    "call_whatsapp": re.compile(r"\b(call|whatsapp)\b", re.I),
}

# Which of our segments each pattern suits, and the storyboard template that rebuilds it in our words.
PATTERN_USE = {
    "price_reveal": (["investor", "end_user"], "price_check"),
    "list": (["investor", "end_user", "legacy"], "three_checks"),
    "question_hook": (["end_user", "legacy"], "three_checks"),
    "myth_vs_fact": (["investor", "legacy"], "myth_vs_fact"),
    "pov": (["end_user"], "three_checks"),
    "statement": (["investor", "end_user", "legacy"], "price_check"),
}


def parse_og_description(page):
    """Instagram's public page meta: '1,234 likes, 56 comments - account on <date>: "caption"'."""
    m = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"', page)
    if not m:
        return {}
    text = html.unescape(m.group(1))
    out = {}
    likes = re.search(r"([\d,.]+[KkMm]?) likes", text)
    comments = re.search(r"([\d,.]+[KkMm]?) comments", text)
    account = re.search(r" - ([\w.]+) on ", text)
    caption = re.search(r':\s*"(.*)"\s*\.?\s*$', text, re.S)
    if likes:
        out["likes"] = to_int(likes.group(1))
    if comments:
        out["comments"] = to_int(comments.group(1))
    if account:
        out["account"] = "@" + account.group(1)
    if caption:
        out["caption"] = caption.group(1)
    return out


def to_int(text):
    text = text.replace(",", "")
    scale = {"k": 1_000, "m": 1_000_000}.get(text[-1].lower(), 1)
    return int(float(text.rstrip("KkMm")) * scale)


def fetch(url, timeout=15):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return parse_og_description(response.read().decode("utf-8", "replace"))


def analyse_caption(caption):
    lines = [line for line in caption.splitlines() if line.strip()]
    hook = lines[0].strip() if lines else ""
    body = " ".join(lines)
    hashtags = re.findall(r"#\w+", body)
    words = re.sub(r"#\w+", "", body).split()
    list_lines = sum(1 for line in lines[1:] if LIST_LINE.match(line))
    ctas = sorted(name for name, pattern in CTAS.items() if pattern.search(body))
    if re.match(r"^\s*pov\b", hook, re.I):
        pattern = "pov"
    elif re.search(r"\bmyths?\b|\bfact\b", body, re.I):
        pattern = "myth_vs_fact"
    elif PRICE.search(hook):
        pattern = "price_reveal"
    elif list_lines >= 3:
        pattern = "list"
    elif hook.endswith("?"):
        pattern = "question_hook"
    else:
        pattern = "statement"
    return {
        "hook_words": len(hook.split()),
        "hook_has_number": bool(NUMBER.search(hook)),
        "hook_has_price": bool(PRICE.search(hook)),
        "hook_is_question": hook.endswith("?"),
        "lines": len(lines),
        "words": len(words),
        "list_lines": list_lines,
        "hashtags": len(hashtags),
        "emojis": len(EMOJI.findall(body)),
        "mentions": len(re.findall(r"@\w+", body)),
        "ctas": ctas,
        "pattern": pattern,
    }


def reasons(features, likes=None, median_likes=None):
    out = []
    if features["hook_has_price"]:
        out.append("opens on a price, which stops the scroll for buyers")
    elif features["hook_has_number"]:
        out.append("opens on a number, which promises something concrete")
    if features["hook_is_question"]:
        out.append("opens on a question the viewer wants answered")
    if features["hook_words"] and features["hook_words"] <= 10:
        out.append("short hook that reads in one glance")
    if features["list_lines"] >= 3:
        out.append("list structure that is easy to skim and save")
    if features["ctas"]:
        out.append("clear call to action: " + ", ".join(features["ctas"]))
    if features["words"] <= 60:
        out.append("short caption; the video carries the message")
    if likes is not None and median_likes and likes >= 2 * median_likes:
        out.append("engagement at least twice the median of this set")
    return out or ["no clear signal from the caption alone; add notes on the visuals"]


def screen(rows):
    kept, rejected = [], []
    for row in rows:
        if REEL_URL.match(row.get("url", "").strip()):
            kept.append({k: (row.get(k) or "").strip() for k in COLUMNS})
        else:
            rejected.append(row.get("url", ""))
    return kept, rejected


def _load_cache(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def analyse(kept, cache):
    records = []
    for row in kept:
        fetched = cache.get(row["url"], {})
        caption = row["caption"] or fetched.get("caption", "")
        record = {
            "url": row["url"],
            "account": row["account"] or fetched.get("account", ""),
            "format": row["format"],
            "length_sec": int(row["length_sec"]) if row["length_sec"].isdigit() else None,
            "likes": fetched.get("likes"),
            "comments": fetched.get("comments"),
            "caption_source": "pasted" if row["caption"] else ("fetched" if caption else "missing"),
            "caption": caption,
            "notes": row["notes"],
        }
        record["features"] = analyse_caption(caption) if caption else None
        records.append(record)
    likes = [r["likes"] for r in records if r["likes"] is not None]
    median_likes = median(likes) if likes else None
    for r in records:
        r["why_it_works"] = reasons(r["features"], r["likes"], median_likes) if r["features"] else [
            "caption missing: paste it into reels.csv or run --fetch-reels on the laptop"]
    return records


def style_from(records):
    analysed = [r for r in records if r["features"]]
    patterns = Counter(r["features"]["pattern"] for r in analysed)
    ctas = Counter(c for r in analysed for c in r["features"]["ctas"])
    formats = Counter(r["format"] for r in records if r["format"])
    lengths = [r["length_sec"] for r in records if r["length_sec"]]
    by_segment = {}
    for seg in ("investor", "end_user", "legacy"):
        fits = [p for p, _ in patterns.most_common() if seg in PATTERN_USE[p][0]]
        pattern = fits[0] if fits else "price_reveal"
        by_segment[seg] = {"pattern": pattern, "template": PATTERN_USE[pattern][1]}
    return {
        "count": len(records),
        "analysed": len(analysed),
        "patterns": dict(patterns.most_common()),
        "top_format": formats.most_common(1)[0][0] if formats else "",
        "median_length_sec": int(median(lengths)) if lengths else 0,
        "caption": {
            "median_words": int(median([r["features"]["words"] for r in analysed])) if analysed else 40,
            "median_hashtags": int(median([r["features"]["hashtags"] for r in analysed])) if analysed else 5,
            "uses_emoji": bool(analysed) and median([r["features"]["emojis"] for r in analysed]) >= 1,
            "top_cta": ctas.most_common(1)[0][0] if ctas else "link_in_bio",
        },
        "by_segment": by_segment,
    }


def playbook(records, style, rejected):
    lines = [
        "# Reel playbook",
        "",
        f"From {style['count']} reference reel(s), {style['analysed']} with a caption to analyse"
        + (f", {len(rejected)} rejected URL(s)." if rejected else "."),
        "Study only. Do not download, repost, or copy their captions, footage, or audio. Rebuild the pattern in our own words.",
        "",
        "## Patterns, most used first",
    ]
    lines += [f"- {p}: {n} (fits {', '.join(PATTERN_USE[p][0])})" for p, n in style["patterns"].items()] or ["- none yet"]
    cap = style["caption"]
    lines += [
        "",
        "## Caption shape to follow",
        f"- About {cap['median_words']} words, {cap['median_hashtags']} hashtags, emoji: {'yes, sparingly' if cap['uses_emoji'] else 'no'}",
        f"- Call to action most used: {cap['top_cta']}",
        f"- Typical length: {style['median_length_sec'] or 'unknown'} seconds; format: {style['top_format'] or 'unknown'}",
        "",
        "## Plan per segment",
    ]
    lines += [f"- {seg}: pattern {v['pattern']} → our template {v['template']}" for seg, v in style["by_segment"].items()]
    lines += ["", "## Why each reel works"]
    for r in records:
        name = r["account"] or r["url"]
        pattern = r["features"]["pattern"] if r["features"] else "unknown"
        lines.append(f"- {name} ({pattern}): " + "; ".join(r["why_it_works"]))
    return "\n".join(lines) + "\n"


def do(ctx):
    path = ctx.path("data", "inputs", "reels.csv")
    if not path.exists():
        raise Pending("no reference reels yet: copy data/inputs/reels.template.csv to data/inputs/reels.csv")
    _, rows = read_csv_rows(path)
    kept, rejected = screen(rows)
    cache_path = ctx.path("data", "inputs", "reels_cache.json")
    cache = _load_cache(cache_path)
    if ctx.options.get("fetch_reels"):
        for row in kept:
            if row["url"] not in cache and not row["caption"]:
                try:
                    cache[row["url"]] = fetch(row["url"])
                except Exception as e:  # blocked, private or removed reels stay unanalysed
                    cache[row["url"]] = {"error": f"{type(e).__name__}: {e}"}
        cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    records = analyse(kept, cache)
    style = style_from(records)
    return {
        "analysis.json": json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        "playbook.md": playbook(records, style, rejected),
        "style.json": json.dumps(style, indent=2) + "\n",
    }


def verify(ctx, files):
    style = json.loads(files["style.json"])
    if not style["count"]:
        return ["no valid Instagram reel URLs in data/inputs/reels.csv"]
    playbook_text = files["playbook.md"]
    leaked = [r["caption"] for r in json.loads(files["analysis.json"])
              if len(r["caption"]) > 30 and r["caption"][:30] in playbook_text]
    return ["playbook contains copied caption text"] if leaked else []


def summary(files):
    style = json.loads(files["style.json"])
    return (f"{style['count']} reel(s), {style['analysed']} with captions analysed; "
            f"investor pattern: {style['by_segment']['investor']['pattern']}")
