"""Engine: runs the laptop research engine and carousel generator, then collects the newest projects.json.

The engine lives outside this repo (set engine.root in toolkit/config.local.json).
It takes hours, so it only runs with `run --run-engine`. Without the flag this
department picks up the newest output the engine already wrote.
"""

import json
import subprocess
from pathlib import Path

from core import Blocked, Pending

NAME = "engine"


def do(ctx):
    cfg = ctx.config.get("engine", {})
    if not cfg.get("root"):
        raise Blocked("engine.root not set (toolkit/config.local.json); the engine runs on the laptop")
    root = Path(cfg["root"]).expanduser()
    if not root.exists():
        raise Blocked(f"engine folder not found: {root}")

    if ctx.options.get("run_engine"):
        for key in ("research_cmd", "carousel_cmd"):
            if cfg.get(key):
                subprocess.run(cfg[key], cwd=root, check=True)

    found = sorted(root.glob(cfg.get("projects_glob", "output/reports/*_projects.json")),
                   key=lambda p: p.stat().st_mtime)
    if not found:
        raise Pending("no projects.json from the engine yet (run with --run-engine)")
    latest = found[-1]
    return {"projects.json": latest.read_text(encoding="utf-8"), "source.txt": latest.name + "\n"}


def verify(ctx, files):
    try:
        projects = json.loads(files["projects.json"])
    except json.JSONDecodeError as e:
        return [f"projects.json is not valid JSON: {e}"]
    if not isinstance(projects, list) or not projects:
        return ["projects.json has no projects"]
    missing = [i for i, p in enumerate(projects) if not isinstance(p, dict) or not p.get("project_name")]
    return [f"{len(missing)} project(s) without project_name"] if missing else []


def summary(files):
    return f"{len(json.loads(files['projects.json']))} projects from {files['source.txt'].strip()}"
