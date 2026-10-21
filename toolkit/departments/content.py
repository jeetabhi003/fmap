"""Content: post kits (reel script, carousel, caption) built only from verified facts.

Sources:
  - data/properties.csv: shortlisted projects with a verified price
  - listings department (optional): internet listings cleared to showcase
  - references department (optional): the most used reel format and length

Every kit is a draft. A person checks it against MahaRERA, adds the MahaRERA QR
code, and posts it. Nothing here is posted automatically.
"""

import json

from core import has_rera_id, read_csv_rows, slugify
from departments.compliance import scan_text

NAME = "content"

DISCLAIMER = "Research, not advice. Verify on MahaRERA before you pay."
DEFAULT_FORMAT = "talking head with text overlays"
DEFAULT_LENGTH = 30


def _style(ctx):
    refs = ctx.upstream("references")
    if not refs:
        return DEFAULT_FORMAT, DEFAULT_LENGTH
    style = json.loads((refs / "style.json").read_text(encoding="utf-8"))
    return style["top_format"] or DEFAULT_FORMAT, style["median_length_sec"] or DEFAULT_LENGTH


def _agent_line(ctx):
    number = ctx.config.get("launch", {}).get("agent_rera_number", "")
    return f"Agent MahaRERA registration: {number}" if number else "Agent MahaRERA registration: ADD BEFORE POSTING"


def project_kit(row, as_of, fmt, length, agent_line):
    low, high = row["price_cr_range"].split("-")
    return f"""# {row['project']}: post kit

Draft for review. Check every fact on MahaRERA and add the MahaRERA QR code before posting.
Facts as of {as_of}. Source: data/properties.csv.

## Facts used
- Project: {row['project']}, {row['locality']}
- MahaRERA ID: {row['rera_id']}
- Developer: {row['developer']}
- Status: {row['status']}
- Price range: ₹{row['price_cr_range']} Cr (verified)
- Still open: {row['open_items']}

## Reel script ({fmt}, about {length} seconds)
1. Hook: "₹{low} to {high} Cr in {row['locality']}. Here is what we could verify about {row['project']}."
2. "MahaRERA ID {row['rera_id']}. Status: {row['status']}."
3. "Developer: {row['developer']}."
4. "Still to check: {row['open_items']}."
5. "Get our free buyer's checklist. Link in bio."

## Carousel (5 slides)
1. {row['project']}: what is verified
2. MahaRERA ID {row['rera_id']}, {row['status']}
3. Price range ₹{row['price_cr_range']} Cr, as of {as_of}
4. Still to check: {row['open_items']}
5. Free buyer's checklist: link in bio

## Caption
{row['project']}, {row['locality']}. MahaRERA ID {row['rera_id']}. Price range ₹{row['price_cr_range']} Cr as of {as_of}. {DISCLAIMER}
{agent_line}
[MahaRERA QR code]
"""


def listing_kit(item, fmt, length, agent_line):
    media = item["media_url"] or f"none ({item['media_note']})"
    return f"""# {item['project']} listing {item['listing_id']}: post kit

Draft for review. Check every fact on MahaRERA and add the MahaRERA QR code before posting.
Facts as of {item['retrieved_on']}. Source: {item['source_name']} ({item['source_url']}).

## Facts used
- Project: {item['project']}, {item['locality']}
- MahaRERA ID: {item['rera_id']}
- Configuration: {item['configuration']}, {item['carpet_sqft']} sq ft carpet
- Listed price: {item['price_text']} (as listed by {item['source_name']}, not verified by us)
- Media: {media}

## Reel script ({fmt}, about {length} seconds)
1. Hook: "A {item['configuration']} in {item['locality']} listed at {item['price_text']}. Here is how to check it."
2. "MahaRERA ID {item['rera_id']}. Look it up before you visit."
3. "Ask for the carpet area in writing. This listing says {item['carpet_sqft']} sq ft."
4. "Get our free buyer's checklist. Link in bio."

## Caption
{item['configuration']} at {item['project']}, {item['locality']}. Listed at {item['price_text']} by {item['source_name']} on {item['retrieved_on']}. MahaRERA ID {item['rera_id']}. {DISCLAIMER}
{agent_line}
[MahaRERA QR code]
"""


def do(ctx):
    as_of = ctx.config.get("data_as_of", "")
    fmt, length = _style(ctx)
    agent_line = _agent_line(ctx)
    _, rows = read_csv_rows(ctx.path("data", "properties.csv"))
    files = {}
    warning = "" if ctx.config.get("research_confirmed") else (
        "WARNING: the register is not yet confirmed as the research document. Do not post until it is.\n\n")
    for row in rows:
        if row["shortlist"] != "None" and row["price_verified"] == "yes" and has_rera_id(row["rera_id"]):
            files[f"posts/{slugify(row['project'])}.md"] = warning + project_kit(row, as_of, fmt, length, agent_line)
    listings = ctx.upstream("listings")
    if listings:
        for item in json.loads((listings / "showcase.json").read_text(encoding="utf-8")):
            name = slugify(f"{item['project']}-{item['listing_id']}")
            files[f"posts/listing-{name}.md"] = listing_kit(item, fmt, length, agent_line)
    index = ["# Post kits", "", f"Format: {fmt}, about {length} seconds.", ""]
    index += [f"- {name}" for name in sorted(files)] or ["No posts: nothing verified to post yet."]
    files["index.md"] = "\n".join(index) + "\n"
    return files


def verify(ctx, files):
    problems = []
    for name, text in files.items():
        if not name.startswith("posts/"):
            continue
        for required in ("MahaRERA ID", DISCLAIMER, "[MahaRERA QR code]"):
            if required not in text:
                problems.append(f"{name}: missing '{required}'")
        problems += [f"{name}:{line} {reason} ('{hit}')" for line, reason, hit in scan_text(text)]
    return problems


def summary(files):
    posts = [n for n in files if n.startswith("posts/")]
    listings = sum(n.startswith("posts/listing-") for n in posts)
    return f"{len(posts)} post kit(s) ({listings} from listings), all drafts for review"
