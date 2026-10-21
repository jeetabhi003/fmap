"""Shared pieces for every department: context, results, and the do -> verify -> save cycle.

A department is a module with:
  NAME           its name in pipeline.json
  do(ctx)        returns {relative_file_name: text or bytes}; may raise Blocked or Pending
  verify(ctx, files)  returns a list of problems (empty means it passed)
  summary(files) returns a one-line description of what was produced

Only verified output is promoted to the department's output folder. Output that
fails verification is kept in work/<department>/ for a person to review.
"""

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ".manifest.json"


class Blocked(Exception):
    """Needs an input only a person can provide."""


class Pending(Exception):
    """Nothing to do yet. Not an error."""


@dataclass
class Result:
    status: str
    message: str
    files: list = field(default_factory=list)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def merge(base, override):
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(root):
    """toolkit/config.json, overlaid with toolkit/config.local.json (laptop-only, not in git)."""
    cfg = load_json(root / "toolkit" / "config.json")
    local = root / "toolkit" / "config.local.json"
    if local.exists():
        cfg = merge(cfg, load_json(local))
    return cfg


class Context:
    def __init__(self, root=ROOT, config=None, options=None):
        self.root = Path(root)
        self.config = config if config is not None else load_config(self.root)
        self.options = options or {}
        self.results = {}
        self.outputs = {}

    def path(self, *parts):
        return self.root.joinpath(*parts)

    def upstream(self, name):
        """Promoted output folder of a department that finished ok in this run, else None."""
        result = self.results.get(name)
        if result is not None and result.status == "ok":
            return self.outputs[name]
        return None


def as_bytes(content):
    return content if isinstance(content, bytes) else content.encode("utf-8")


def version_of(files):
    h = hashlib.sha256()
    for name in sorted(files):
        h.update(name.encode("utf-8") + b"\0" + as_bytes(files[name]) + b"\0")
    return h.hexdigest()[:12]


def write_files(folder, files):
    for name, content in files.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")


def promote(folder, files, department):
    """Save verified files. Returns False when the output is unchanged since the last save."""
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / MANIFEST
    version = version_of(files)
    old = load_json(manifest_path) if manifest_path.exists() else {}
    if old.get("version") == version:
        return False
    # Remove only files this department saved last time, never anything else in the folder.
    for name in old.get("files", {}):
        if name not in files:
            (folder / name).unlink(missing_ok=True)
    write_files(folder, files)
    manifest = {
        "department": department,
        "version": version,
        "files": {n: hashlib.sha256(as_bytes(c)).hexdigest()[:12] for n, c in sorted(files.items())},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return True


def run_department(dept, ctx, output_dir, work_dir):
    try:
        files = dept.do(ctx)
    except Blocked as e:
        return Result("blocked", str(e))
    except Pending as e:
        return Result("pending", str(e))
    except Exception as e:  # a crash in one department must not stop the others
        return Result("failed", f"error in do: {type(e).__name__}: {e}")

    problems = dept.verify(ctx, files)
    if problems:
        if work_dir.exists():
            shutil.rmtree(work_dir)
        write_files(work_dir, files)
        shown = "; ".join(problems[:3]) + (f" (+{len(problems) - 3} more)" if len(problems) > 3 else "")
        return Result("failed", f"{len(problems)} check(s) failed: {shown}. Draft kept in {work_dir.relative_to(ctx.root)}/")

    changed = promote(output_dir, files, dept.NAME)
    message = dept.summary(files) + ("" if changed else " (unchanged)")
    return Result("ok", message, sorted(files))


def read_csv_rows(path):
    import csv

    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def to_csv(fieldnames, rows):
    import csv
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    return buf.getvalue()


def has_rera_id(text):
    """True when the text contains a MahaRERA project number, not a placeholder like 'see ledger'."""
    import re

    return bool(re.search(r"P[0-9A-Z]{10,15}", text or ""))


def place(locality, market="Worli"):
    """'Naka' -> 'Worli Naka'; leaves names that already include the market alone."""
    locality = (locality or "").strip()
    if not locality:
        return market
    return locality if market.lower() in locality.lower() or "(" in locality else f"{market} {locality}"


def slugify(text):
    import re

    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
