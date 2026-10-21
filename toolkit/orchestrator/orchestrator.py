"""One orchestrator for the whole project.

It is the only entry point. It runs every job in pipeline.json in order,
skips jobs whose dependencies are not ok, saves the result of each run,
and writes docs/strategy/status.md.

Job statuses:
  ok       done and healthy
  pending  not started yet; nothing is wrong
  blocked  needs an input only a person can provide
  waiting  a dependency is not ok, so the job was skipped
  failed   the repo has a problem to fix

Exit code is 1 only when a job failed. Blocked and pending do not fail the run.

Usage:
  python3 toolkit/orchestrator/orchestrator.py run
  python3 toolkit/orchestrator/orchestrator.py status
  python3 toolkit/orchestrator/orchestrator.py list
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = Path(__file__).with_name("pipeline.json")
STATE = ROOT / "data" / "jobs" / "state.json"
REPORT = ROOT / "docs" / "strategy" / "status.md"

sys.path.insert(0, str(ROOT / "scripts"))
import validate_register  # noqa: E402

SITE_PLACEHOLDERS = {
    "FORM_ID": "Google Form link",
    "to be added": "agent registration number",
}


def job_research_input(cfg):
    folder = ROOT / "data" / "inputs" / "research"
    files = [p for p in folder.glob("*") if p.is_file() and p.name != "README.md"]
    if not files:
        return "blocked", "no research document in data/inputs/research/"
    return "ok", f"{len(files)} file(s): " + ", ".join(p.name for p in files)


def job_validate_register(cfg):
    with validate_register.PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    errors = validate_register.check(rows)
    if errors:
        return "failed", f"{len(errors)} register error(s): " + "; ".join(errors[:3])
    verified = sum(r["price_verified"] == "yes" for r in rows)
    return "ok", (
        f"{len(rows)} projects, {verified} with a verified price "
        "(source is the Worli knowledge base, not yet confirmed as the research document)"
    )


def job_site_placeholders(cfg):
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    missing = [label for token, label in SITE_PLACEHOLDERS.items() if token in html]
    if missing:
        return "blocked", "not set in site/index.html: " + ", ".join(missing)
    return "ok", "no placeholders left"


def job_ebook_outlines(cfg):
    files = sorted((ROOT / "products" / "ebooks").glob("*.md"))
    if not files:
        return "failed", "no ebook outlines in products/ebooks/"
    thin = [
        f.name
        for f in files
        if len(re.findall(r"^\d+\. ", f.read_text(encoding="utf-8"), re.M)) < 5
    ]
    if thin:
        return "failed", "fewer than 5 outline sections: " + ", ".join(thin)
    return "ok", f"{len(files)} outlines, each with 5+ sections"


def job_lead_summary(cfg):
    path = ROOT / "data" / "leads" / "export.csv"
    if not path.exists():
        return "pending", "no local export; leads stay in Google Sheets"
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # Counts only. Names and emails are never printed or written to the report.
    by_segment = Counter(r.get("segment", "unknown") for r in rows)
    summary = ", ".join(f"{k}={v}" for k, v in sorted(by_segment.items()))
    return "ok", f"{len(rows)} leads ({summary})"


def job_shortlist_ready(cfg):
    path = ROOT / "data" / "properties.csv"
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ready = [r for r in rows if r["shortlist"] != "None" and r["price_verified"] == "yes"]
    if not ready:
        return "pending", "no shortlisted project has a verified price yet"
    return "ok", f"{len(ready)} shortlisted project(s) with a verified price"


def job_ebook_drafts(cfg):
    folder = ROOT / "products" / "ebooks" / "drafts"
    drafts = sorted(folder.glob("*.md")) if folder.exists() else []
    if not drafts:
        return "pending", "no full drafts yet (products/ebooks/drafts/)"
    return "ok", f"{len(drafts)} full draft(s)"


JOBS = {
    "research_input": job_research_input,
    "validate_register": job_validate_register,
    "site_placeholders": job_site_placeholders,
    "ebook_outlines": job_ebook_outlines,
    "lead_summary": job_lead_summary,
    "shortlist_ready": job_shortlist_ready,
    "ebook_drafts": job_ebook_drafts,
}


def load_pipeline():
    cfg = json.loads(PIPELINE.read_text(encoding="utf-8"))
    seen = set()
    for job in cfg["jobs"]:
        if job["name"] not in JOBS:
            raise SystemExit(f"pipeline.json names unknown job: {job['name']}")
        missing = [d for d in job["depends_on"] if d not in seen]
        if missing:
            raise SystemExit(f"{job['name']} depends on {missing}, which must come earlier")
        seen.add(job["name"])
    return cfg


def run():
    cfg = load_pipeline()
    results = {}
    for job in cfg["jobs"]:
        name = job["name"]
        open_deps = [d for d in job["depends_on"] if results[d]["status"] != "ok"]
        if open_deps:
            results[name] = {"status": "waiting", "message": "waiting on " + ", ".join(open_deps)}
        else:
            status, message = JOBS[name](cfg)
            results[name] = {"status": status, "message": message}

    saved = {"last_run": datetime.now(timezone.utc).isoformat(timespec="seconds"), "jobs": results}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    write_report(saved)
    print_table(results)
    return 1 if any(r["status"] == "failed" for r in results.values()) else 0


def print_table(results):
    width = max(len(n) for n in results)
    for name, r in results.items():
        print(f"{name:<{width}}  {r['status']:<8}  {r['message']}")


def write_report(saved):
    lines = [
        "# Project status",
        "",
        f"Last run: {saved['last_run']} (generated by `toolkit/orchestrator/orchestrator.py`)",
        "",
        "| Job | Status | Detail |",
        "|---|---|---|",
    ]
    for name, r in saved["jobs"].items():
        lines.append(f"| {name} | {r['status']} | {r['message']} |")
    blocked = [n for n, r in saved["jobs"].items() if r["status"] == "blocked"]
    lines += ["", "## Needs a person", ""]
    lines += [f"- {n}: {saved['jobs'][n]['message']}" for n in blocked] or ["Nothing blocked."]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def status():
    if not STATE.exists():
        print("No run yet. Run: python3 toolkit/orchestrator/orchestrator.py run")
        return 0
    saved = json.loads(STATE.read_text(encoding="utf-8"))
    print(f"Last run: {saved['last_run']}")
    print_table(saved["jobs"])
    return 0


def list_jobs():
    for job in load_pipeline()["jobs"]:
        deps = ", ".join(job["depends_on"]) or "none"
        print(f"{job['name']:<20} depends on: {deps}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Run the project pipeline.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="run every job in order")
    sub.add_parser("status", help="show the last run")
    sub.add_parser("list", help="list jobs and dependencies")
    args = parser.parse_args()
    handlers = {"run": run, "status": status, "list": list_jobs}
    return handlers[args.command]()


if __name__ == "__main__":
    sys.exit(main())
