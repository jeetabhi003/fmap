"""Matching: buyer criteria in, shortlist out. Uses verified fields only and shows every caveat.

It never ranks projects as good or bad investments. It filters by segment and
budget, and separates projects whose price or MahaRERA ID is still unverified.
"""

import json

from core import has_rera_id, read_csv_rows

NAME = "matching"

SEGMENT_LABELS = {"end_user": "End user", "investor": "Investor", "legacy": "Legacy"}


def parse_range(text):
    """'6.42-18' -> (6.42, 18.0). Anything else -> None."""
    try:
        low, high = text.split("-")
        return float(low), float(high)
    except (ValueError, AttributeError):
        return None


def match(rows, segment, budget_cr=None):
    if segment not in SEGMENT_LABELS:
        raise ValueError(f"segment must be one of {sorted(SEGMENT_LABELS)}")
    label = SEGMENT_LABELS[segment]
    result = {"segment": segment, "budget_cr": budget_cr, "matched": [], "to_check": [], "over_budget": []}
    for r in rows:
        if r["shortlist"] != label:
            continue
        entry = {
            "project": r["project"], "locality": r["locality"], "rera_id": r["rera_id"],
            "developer": r["developer"], "status": r["status"], "price_cr_range": r["price_cr_range"],
            "caveats": r["open_items"],
        }
        price = parse_range(r["price_cr_range"])
        if r["price_verified"] != "yes" or price is None or not has_rera_id(r["rera_id"]):
            result["to_check"].append(entry)
        elif budget_cr is not None and price[0] > budget_cr:
            result["over_budget"].append(entry)
        else:
            result["matched"].append(entry)
    ready_first = segment == "end_user"
    result["matched"].sort(key=lambda e: (ready_first and e["status"] != "Ready", parse_range(e["price_cr_range"])[0]))
    return result


def do(ctx):
    _, rows = read_csv_rows(ctx.path("data", "properties.csv"))
    shortlists = {seg: match(rows, seg) for seg in SEGMENT_LABELS}
    return {"shortlists.json": json.dumps(shortlists, indent=2, ensure_ascii=False) + "\n"}


def verify(ctx, files):
    problems = []
    for seg, data in json.loads(files["shortlists.json"]).items():
        for entry in data["matched"]:
            if not has_rera_id(entry["rera_id"]):
                problems.append(f"{seg}: {entry['project']} matched without a RERA ID")
    return problems


def summary(files):
    data = json.loads(files["shortlists.json"])
    return ", ".join(f"{seg} {len(d['matched'])} matched / {len(d['to_check'])} to check" for seg, d in data.items())
