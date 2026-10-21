"""Leads: counts from a local export of the Google Sheet. Never names, emails or phone numbers.

Download the sheet as CSV to data/leads/export.csv (kept out of git) and run the pipeline.
"""

import json
from collections import Counter

from core import Pending, read_csv_rows

NAME = "leads"


def do(ctx):
    path = ctx.path("data", "leads", "export.csv")
    if not path.exists():
        raise Pending("no local export (data/leads/export.csv); leads stay in Google Sheets")
    _, rows = read_csv_rows(path)
    consented = [r for r in rows if r.get("consent_given", "").strip().lower() in ("yes", "true", "1")]
    data = {
        "total": len(rows),
        "without_consent": len(rows) - len(consented),
        "by_segment": dict(sorted(Counter(r.get("segment", "unknown") for r in consented).items())),
        "by_layer": dict(sorted(Counter(r.get("layer", "unknown") for r in consented).items())),
        "by_status": dict(sorted(Counter(r.get("status", "unknown") for r in consented).items())),
    }
    return {"summary.json": json.dumps(data, indent=2) + "\n"}


def verify(ctx, files):
    data = json.loads(files["summary.json"])
    if data["without_consent"]:
        return [f"{data['without_consent']} lead row(s) without recorded consent: fix the sheet before emailing anyone"]
    return []


def summary(files):
    data = json.loads(files["summary.json"])
    return f"{data['total']} lead(s): " + ", ".join(f"{k}={v}" for k, v in data["by_segment"].items())
