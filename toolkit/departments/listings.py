"""Listings: properties found on the internet, filtered down to what we may showcase.

Input: data/inputs/listings.csv (kept out of git). Template: data/inputs/listings.template.csv.

A listing is showcased only when it has a RERA ID, a source URL and a retrieval
date, and its RERA ID agrees with the register when the project is in it.
Media is kept only when we own it or have a licence or written permission.
Everything else is shown as text facts with the source credited.
"""

import json
import re
from datetime import date

from core import Pending, read_csv_rows

NAME = "listings"

COLUMNS = [
    "listing_id", "project", "locality", "rera_id", "configuration", "carpet_sqft",
    "price_text", "source_name", "source_url", "retrieved_on", "media_url", "media_rights", "notes",
]
MEDIA_ALLOWED = {"own", "licensed", "written_permission"}
RERA_PATTERN = re.compile(r"^P[0-9A-Z]{10,15}$")
RERA_IN_TEXT = re.compile(r"P[0-9A-Z]{10,15}")


def _valid_date(text):
    try:
        date.fromisoformat(text)
        return True
    except ValueError:
        return False


def screen(rows, register_rows):
    """Split listings into (showcase, excluded). Each excluded item carries its reasons."""
    register = {r["project"].casefold(): r for r in register_rows}
    showcase, excluded = [], []
    for row in rows:
        reasons = []
        rera = row.get("rera_id", "").strip()
        if not RERA_PATTERN.match(rera):
            reasons.append("no valid MahaRERA ID")
        if not row.get("source_url", "").startswith("https://"):
            reasons.append("no https source URL")
        if not _valid_date(row.get("retrieved_on", "")):
            reasons.append("retrieved_on is not YYYY-MM-DD")
        match = next((r for name, r in register.items()
                      if row.get("project", "").casefold() and row["project"].casefold() in name), None)
        register_ids = RERA_IN_TEXT.findall(match["rera_id"]) if match else []
        if register_ids and rera and rera not in register_ids:
            reasons.append(f"RERA ID differs from register ({match['rera_id']})")
        if reasons:
            excluded.append({"listing_id": row.get("listing_id", ""), "project": row.get("project", ""), "reasons": reasons})
            continue
        item = {k: row.get(k, "") for k in COLUMNS if k not in ("media_url", "media_rights")}
        rights = row.get("media_rights", "").strip().lower()
        item["media_rights"] = rights
        item["media_url"] = row.get("media_url", "") if rights in MEDIA_ALLOWED else ""
        item["media_note"] = "" if item["media_url"] else "use our own footage or a text card; no rights to source media"
        showcase.append(item)
    return showcase, excluded


def do(ctx):
    path = ctx.path("data", "inputs", "listings.csv")
    if not path.exists():
        raise Pending("no listings yet: copy data/inputs/listings.template.csv to data/inputs/listings.csv")
    fields, rows = read_csv_rows(path)
    missing = [c for c in COLUMNS if c not in fields]
    if missing:
        return {"error.txt": f"missing columns: {missing}\n"}
    _, register_rows = read_csv_rows(ctx.path("data", "properties.csv"))
    showcase, excluded = screen(rows, register_rows)
    lines = ["# Listings not showcased", ""]
    lines += [f"- {e['listing_id']} {e['project']}: {'; '.join(e['reasons'])}" for e in excluded] or ["None."]
    return {
        "showcase.json": json.dumps(showcase, indent=2, ensure_ascii=False) + "\n",
        "excluded.md": "\n".join(lines) + "\n",
    }


def verify(ctx, files):
    if "error.txt" in files:
        return [files["error.txt"].strip()]
    problems = []
    for item in json.loads(files["showcase.json"]):
        if not RERA_PATTERN.match(item["rera_id"]):
            problems.append(f"{item['listing_id']}: showcased without a valid RERA ID")
        if item["media_url"] and item["media_rights"] not in MEDIA_ALLOWED:
            problems.append(f"{item['listing_id']}: media kept without rights")
    return problems


def summary(files):
    shown = len(json.loads(files["showcase.json"]))
    hidden = files["excluded.md"].count("\n- ")
    return f"{shown} listing(s) cleared to showcase, {hidden} held back"
