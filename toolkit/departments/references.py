"""References: Instagram reels we study for format and pacing. We never download or repost them.

Input: data/inputs/reels.csv (kept out of git). Template: data/inputs/reels.template.csv.
Output: a style brief the content department uses to pick a format. Hooks are
summarised as patterns; our posts are written in our own words.
"""

import json
import re
from collections import Counter
from statistics import median

from core import Pending, read_csv_rows

NAME = "references"

COLUMNS = ["url", "account", "topic", "format", "hook_pattern", "length_sec", "why_it_works"]
REEL_URL = re.compile(r"^https://(www\.)?instagram\.com/(reel|reels|p)/[A-Za-z0-9_-]+/?(\?.*)?$")


def screen(rows):
    kept, rejected = [], []
    for row in rows:
        if REEL_URL.match(row.get("url", "").strip()):
            kept.append({k: row.get(k, "").strip() for k in COLUMNS})
        else:
            rejected.append(row.get("url", ""))
    return kept, rejected


def brief(kept):
    formats = Counter(r["format"] or "unspecified" for r in kept)
    lengths = [int(r["length_sec"]) for r in kept if r["length_sec"].isdigit()]
    lines = [
        "# Reel style brief",
        "",
        f"Based on {len(kept)} reference reel(s). Study only: do not download, repost, or copy their audio, footage, or captions.",
        "",
        "## Formats, most used first",
    ]
    lines += [f"- {fmt}: {n}" for fmt, n in formats.most_common()]
    lines += ["", f"Typical length: {int(median(lengths))} seconds" if lengths else "Typical length: unknown", "",
              "## Hook patterns to adapt in our own words"]
    lines += sorted({f"- {r['hook_pattern']}" for r in kept if r["hook_pattern"]}) or ["- none recorded"]
    lines += ["", "## Why they work (notes)"]
    lines += [f"- {r['why_it_works']}" for r in kept if r["why_it_works"]] or ["- none recorded"]
    return "\n".join(lines) + "\n"


def do(ctx):
    path = ctx.path("data", "inputs", "reels.csv")
    if not path.exists():
        raise Pending("no reference reels yet: copy data/inputs/reels.template.csv to data/inputs/reels.csv")
    _, rows = read_csv_rows(path)
    kept, rejected = screen(rows)
    top = Counter(r["format"] for r in kept if r["format"]).most_common(1)
    lengths = [int(r["length_sec"]) for r in kept if r["length_sec"].isdigit()]
    style = {
        "top_format": top[0][0] if top else "",
        "median_length_sec": int(median(lengths)) if lengths else 0,
        "count": len(kept),
        "rejected_urls": len(rejected),
    }
    return {"brief.md": brief(kept), "style.json": json.dumps(style, indent=2) + "\n"}


def verify(ctx, files):
    style = json.loads(files["style.json"])
    return [] if style["count"] else ["no valid Instagram reel URLs in data/inputs/reels.csv"]


def summary(files):
    style = json.loads(files["style.json"])
    return f"{style['count']} reference reel(s), {style['rejected_urls']} rejected URL(s)"
