"""Check data/properties.csv before anything is published.

Rules:
- Every row has the required columns and a non-empty project name.
- A price can only be marked verified when a range is given.
- Every project with a shortlist label must have a RERA ID or 'see ledger'.
- Rows marked 'no' for price_verified must say why in open_items.

Exit code 1 on any failure so GitHub Actions goes red.
"""

import csv
import sys
from pathlib import Path

REQUIRED = [
    "id", "project", "locality", "rera_id", "developer", "status",
    "price_cr_range", "price_verified", "shortlist", "open_items",
]
PATH = Path(__file__).resolve().parent.parent / "data" / "properties.csv"


def check(rows):
    errors = []
    for line, row in enumerate(rows, start=2):
        name = row.get("project", "").strip()
        if not name:
            errors.append(f"line {line}: empty project name")
            continue
        if row["price_verified"] == "yes" and row["price_cr_range"] == "unknown":
            errors.append(f"line {line} ({name}): price marked verified but no range")
        if row["shortlist"] not in {"End user", "Investor", "Legacy", "None"}:
            errors.append(f"line {line} ({name}): unknown shortlist '{row['shortlist']}'")
        if row["shortlist"] != "None" and not row["rera_id"].strip():
            errors.append(f"line {line} ({name}): shortlisted without a RERA ID")
        if row["price_verified"] == "no" and not row["open_items"].strip():
            errors.append(f"line {line} ({name}): unverified price with no open item")
    return errors


def main():
    with PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            print(f"FAIL missing columns: {missing}")
            return 1
        rows = list(reader)
    errors = check(rows)
    if errors:
        print("FAIL")
        print("\n".join(errors))
        return 1
    print(f"PASS {len(rows)} projects checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
