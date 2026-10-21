"""Register: checks data/properties.csv, the curated list of projects every other department uses."""

import json
import sys
from collections import Counter

from core import read_csv_rows

NAME = "register"


def _validator(ctx):
    sys.path.insert(0, str(ctx.path("scripts")))
    import validate_register

    return validate_register


def do(ctx):
    fields, rows = read_csv_rows(ctx.path("data", "properties.csv"))
    data = {
        "columns": fields,
        "projects": len(rows),
        "verified_prices": sum(r.get("price_verified") == "yes" for r in rows),
        "by_shortlist": dict(sorted(Counter(r.get("shortlist", "") for r in rows).items())),
        "source_confirmed": bool(ctx.config.get("research_confirmed")),
        "data_as_of": ctx.config.get("data_as_of", ""),
    }
    return {"summary.json": json.dumps(data, indent=2) + "\n"}


def verify(ctx, files):
    validator = _validator(ctx)
    data = json.loads(files["summary.json"])
    missing = [c for c in validator.REQUIRED if c not in data["columns"]]
    if missing:
        return [f"missing columns: {missing}"]
    _, rows = read_csv_rows(ctx.path("data", "properties.csv"))
    return validator.check(rows)


def summary(files):
    data = json.loads(files["summary.json"])
    note = "" if data["source_confirmed"] else "; source not yet confirmed as the research document"
    return f"{data['projects']} projects, {data['verified_prices']} with a verified price{note}"
