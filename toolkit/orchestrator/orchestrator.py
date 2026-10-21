"""One orchestrator for the whole project.

It is the only entry point. It runs every department in pipeline.json in order.
Each department does its work, verifies it, and saves it; only verified output
is promoted for the departments after it.

Statuses:
  ok       done, verified, saved
  pending  nothing to do yet; not an error
  blocked  needs an input only a person can provide
  waiting  a department it depends on is not ok, so it was skipped
  failed   verification failed or the department crashed; draft kept in work/

Exit code is 1 only when a department failed.

Usage:
  python3 toolkit/orchestrator/orchestrator.py run [--only NAME ...] [--run-engine] [--fetch-reels] [--render]
  python3 toolkit/orchestrator/orchestrator.py status
  python3 toolkit/orchestrator/orchestrator.py list
  python3 toolkit/orchestrator/orchestrator.py match --segment investor [--budget-cr 30]
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import Context, Result, read_csv_rows, run_department  # noqa: E402
from departments import DEPARTMENTS  # noqa: E402
from departments.matching import SEGMENT_LABELS, match  # noqa: E402

PIPELINE = Path(__file__).with_name("pipeline.json")


def load_pipeline():
    steps = json.loads(PIPELINE.read_text(encoding="utf-8"))["departments"]
    seen = set()
    for step in steps:
        if step["name"] not in DEPARTMENTS:
            raise SystemExit(f"pipeline.json names unknown department: {step['name']}")
        later = [d for d in step["depends_on"] + step["uses"] if d not in seen]
        if later:
            raise SystemExit(f"{step['name']} needs {later}, which must come earlier in pipeline.json")
        seen.add(step["name"])
    return steps


def select(steps, only):
    """The named departments plus everything they depend on, in pipeline order."""
    if not only:
        return steps
    unknown = [n for n in only if n not in DEPARTMENTS]
    if unknown:
        raise SystemExit(f"unknown department(s): {unknown}")
    by_name = {s["name"]: s for s in steps}
    needed, stack = set(), list(only)
    while stack:
        name = stack.pop()
        if name not in needed:
            needed.add(name)
            stack.extend(by_name[name]["depends_on"])
    return [s for s in steps if s["name"] in needed]


def run(ctx, only=None):
    for step in select(load_pipeline(), only):
        name = step["name"]
        ctx.outputs[name] = ctx.path(step["output"])
        open_deps = [d for d in step["depends_on"] if ctx.results[d].status != "ok"]
        if open_deps:
            result = Result("waiting", "waiting on " + ", ".join(open_deps))
        else:
            result = run_department(DEPARTMENTS[name], ctx, ctx.outputs[name], ctx.path("work", name))
        ctx.results[name] = result
        print(f"{name:<11} {result.status:<8} {result.message}", flush=True)

    jobs = {n: {"status": r.status, "message": r.message, "files": r.files} for n, r in ctx.results.items()}
    state = {"last_run": datetime.now(timezone.utc).isoformat(timespec="seconds"), "departments": jobs}
    state_path = ctx.path("data", "jobs", "state.json")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    write_report(ctx, jobs)
    return 1 if any(r.status == "failed" for r in ctx.results.values()) else 0


def write_report(ctx, jobs):
    lines = ["# Pipeline status", "", "| Department | Status | Detail |", "|---|---|---|"]
    lines += [f"| {n} | {j['status']} | {j['message']} |" for n, j in jobs.items()]
    for title, status in (("Needs a person", "blocked"), ("Failed", "failed")):
        items = [f"- {n}: {j['message']}" for n, j in jobs.items() if j["status"] == status]
        lines += ["", f"## {title}", ""] + (items or ["Nothing."])
    report = ctx.path("outputs", "report", "status.md")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def status(ctx):
    path = ctx.path("data", "jobs", "state.json")
    if not path.exists():
        print("No run yet. Run: python3 toolkit/orchestrator/orchestrator.py run")
        return 0
    state = json.loads(path.read_text(encoding="utf-8"))
    print(f"Last run: {state['last_run']}")
    for name, job in state["departments"].items():
        print(f"{name:<11} {job['status']:<8} {job['message']}")
    return 0


def list_departments():
    for step in load_pipeline():
        print(f"{step['name']:<11} depends on: {', '.join(step['depends_on']) or 'none':<22} "
              f"uses: {', '.join(step['uses']) or 'none':<22} saves to: {step['output']}")
    return 0


def match_command(ctx, segment, budget_cr):
    _, rows = read_csv_rows(ctx.path("data", "properties.csv"))
    result = match(rows, segment, budget_cr)
    budget = f" within ₹{budget_cr} Cr" if budget_cr is not None else ""
    print(f"Segment: {SEGMENT_LABELS[segment]}{budget}. Facts as of {ctx.config.get('data_as_of', '')}.")
    if not ctx.config.get("research_confirmed"):
        print("Note: the register is not yet confirmed as the research document.")
    for title, key in (("Matched (verified price)", "matched"), ("Price not verified: check first", "to_check"),
                       ("Over budget", "over_budget")):
        print(f"\n{title}:")
        for e in result[key] or [{"project": "none"}]:
            if e["project"] == "none":
                print("  none")
                continue
            print(f"  {e['project']} | MahaRERA {e['rera_id']} | {e['status']} | ₹{e['price_cr_range']} Cr")
            print(f"    still to check: {e['caveats']}")
    print("\nResearch, not advice. Verify on MahaRERA before you pay.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Run the project pipeline.")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="run the departments in order")
    run_p.add_argument("--only", nargs="+", metavar="NAME", help="run these departments and what they depend on")
    run_p.add_argument("--run-engine", action="store_true", help="also run the laptop research engine (takes hours)")
    run_p.add_argument("--fetch-reels", action="store_true", help="fetch reel captions from Instagram (laptop only)")
    run_p.add_argument("--render", action="store_true", help="render reels with Remotion and ffmpeg (laptop)")
    sub.add_parser("status", help="show the last run")
    sub.add_parser("list", help="list departments and dependencies")
    match_p = sub.add_parser("match", help="shortlist projects for a buyer")
    match_p.add_argument("--segment", required=True, choices=sorted(SEGMENT_LABELS))
    match_p.add_argument("--budget-cr", type=float)
    args = parser.parse_args()

    ctx = Context(options={key: getattr(args, key, False) for key in ("run_engine", "fetch_reels", "render")})
    if args.command == "run":
        return run(ctx, args.only)
    if args.command == "status":
        return status(ctx)
    if args.command == "list":
        return list_departments()
    return match_command(ctx, args.segment, args.budget_cr)


if __name__ == "__main__":
    sys.exit(main())
