"""Intake: turns research inputs into candidate register rows for a person to review.

Sources, in order:
  1. projects.json from the engine department (this run), or the newest
     *_projects.json copied into data/inputs/engine/
  2. research documents in data/inputs/research/ (listed for review; not parsed)

Candidates are never merged into data/properties.csv automatically. A person
reviews outputs/intake/diff.md and edits the register.
"""

import json
import re

from core import Blocked, read_csv_rows, to_csv

NAME = "intake"

FIELDS = [
    "project", "developer", "rera_id", "status", "possession",
    "asking_psf", "registered_psf", "zone", "engine_score", "engine_grade", "qc_verdict",
]


def _identity(project):
    research = project.get("research") or {}
    return research.get("project_identity") or research.get("identity") or {}


def map_engine_projects(projects):
    """Map engine projects.json entries to flat candidate rows. Missing fields stay empty."""
    rows = []
    for p in projects:
        ident = _identity(p)
        research = p.get("research") or {}
        score = p.get("score") or {}
        rows.append({
            "project": p.get("project_name", ""),
            "developer": p.get("developer", "") or "",
            "rera_id": ident.get("rera_number", "") or "",
            "status": ident.get("status", "") or "",
            "possession": ident.get("possession_date", "") or "",
            "asking_psf": ident.get("asking_price_psf", "") or "",
            "registered_psf": ident.get("registered_price_psf", "") or "",
            "zone": (research.get("location_data") or {}).get("zone", "") or ident.get("zone", "") or "",
            "engine_score": score.get("normalized_score", ""),
            "engine_grade": score.get("grade", ""),
            "qc_verdict": p.get("qc_verdict", "") or (p.get("qc") or {}).get("overall_verdict", ""),
        })
    return rows


def _engine_projects(ctx):
    upstream = ctx.upstream("engine")
    if upstream:
        return json.loads((upstream / "projects.json").read_text(encoding="utf-8")), "engine department"
    drops = sorted(ctx.path("data", "inputs", "engine").glob("*_projects.json"), key=lambda p: p.stat().st_mtime)
    if drops:
        return json.loads(drops[-1].read_text(encoding="utf-8")), drops[-1].name
    return None, None


def _diff(candidates, register_rows):
    by_name = {r["project"].casefold(): r for r in register_rows}
    lines = ["# Intake diff", "", "Review before editing data/properties.csv. Nothing here is merged automatically.", ""]
    new, mismatched = [], []
    for c in candidates:
        reg = None
        for name, row in by_name.items():
            if c["project"].casefold() in name or name in c["project"].casefold():
                reg = row
                break
        if reg is None:
            new.append(c)
        elif c["rera_id"] and re.search(r"P[0-9A-Z]{10,15}", reg["rera_id"]) and c["rera_id"] not in reg["rera_id"]:
            mismatched.append((c, reg))
    lines.append(f"## New projects not in the register ({len(new)})")
    lines += [f"- {c['project']} ({c['developer'] or 'developer unknown'}), RERA {c['rera_id'] or 'unknown'}" for c in new] or ["None."]
    lines += ["", f"## RERA ID differs from the register ({len(mismatched)})"]
    lines += [f"- {c['project']}: engine {c['rera_id']} vs register {r['rera_id']}" for c, r in mismatched] or ["None."]
    return "\n".join(lines) + "\n"


def do(ctx):
    research_dir = ctx.path("data", "inputs", "research")
    documents = sorted(p.name for p in research_dir.glob("*") if p.is_file() and p.name != "README.md")
    projects, source = _engine_projects(ctx)
    if projects is None and not documents:
        raise Blocked("no research input: add the research document to data/inputs/research/ "
                      "or engine output to data/inputs/engine/")

    files = {
        "documents.md": "# Research documents\n\n" + ("\n".join(f"- {d}" for d in documents) or "None yet.") + "\n",
    }
    if projects is not None:
        candidates = map_engine_projects(projects)
        _, register_rows = read_csv_rows(ctx.path("data", "properties.csv"))
        files["candidates.csv"] = to_csv(FIELDS, candidates)
        files["diff.md"] = _diff(candidates, register_rows)
        files["source.txt"] = f"{source}\n"
    return files


def verify(ctx, files):
    if "candidates.csv" not in files:
        return []
    import csv
    import io

    rows = list(csv.DictReader(io.StringIO(files["candidates.csv"])))
    problems = []
    if not rows:
        problems.append("engine output produced no candidate rows")
    blank = sum(1 for r in rows if not r["project"].strip())
    if blank:
        problems.append(f"{blank} candidate row(s) without a project name")
    return problems


def summary(files):
    docs = files["documents.md"].count("\n- ")
    if "candidates.csv" in files:
        count = files["candidates.csv"].count("\n") - 1
        return f"{count} candidate project(s) for review, {docs} research document(s)"
    return f"{docs} research document(s); no engine output yet"
