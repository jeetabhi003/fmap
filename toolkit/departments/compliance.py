"""Compliance: scans everything we publish for claims we must not make.

Scans site/*.html, products/**/*.md and the content department's posts.
Any hit fails the department, which stops the launch department.
"""

import json
import re

NAME = "compliance"

BANNED = [
    (re.compile(r"\bguarantee[ds]?\s+(returns?|appreciation|rental|yields?|profits?)\b", re.I), "promises a return"),
    (re.compile(r"\bassured\s+(returns?|rental|yields?)\b", re.I), "promises a return"),
    (re.compile(r"\bbest\s+(investment|project|deal|property|buy)\b", re.I), "calls something the best"),
    (re.compile(r"\bsold\s+out\b", re.I), "says sold out"),
    (re.compile(r"\brisk[- ]free\b", re.I), "says risk-free"),
    (re.compile(r"\bdouble\s+your\s+money\b", re.I), "promises a return"),
    (re.compile(r"\bonly\s+\d+\s+(units?|flats?|homes?|apartments?)\s+left\b", re.I), "fake urgency"),
    (re.compile(r"\blimited[- ]period\s+offer\b", re.I), "fake urgency"),
    (re.compile(r"\bhurry\b", re.I), "fake urgency"),
]


def scan_text(text):
    """Return [(line_number, reason, matched_text)] for every banned phrase."""
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        for pattern, reason in BANNED:
            for m in pattern.finditer(line):
                hits.append((number, reason, m.group(0)))
    return hits


def _targets(ctx):
    paths = sorted(ctx.path("site").glob("*.html")) + sorted(ctx.path("products").rglob("*.md"))
    content = ctx.upstream("content")
    if content:
        paths += sorted(content.rglob("*.md"))
    return paths


def do(ctx):
    findings = []
    paths = _targets(ctx)
    for path in paths:
        for line, reason, text in scan_text(path.read_text(encoding="utf-8")):
            findings.append({"file": str(path.relative_to(ctx.root)), "line": line, "reason": reason, "text": text})
    return {"report.json": json.dumps({"scanned": len(paths), "findings": findings}, indent=2) + "\n"}


def verify(ctx, files):
    data = json.loads(files["report.json"])
    return [f"{f['file']}:{f['line']} {f['reason']} ('{f['text']}')" for f in data["findings"]]


def summary(files):
    return f"{json.loads(files['report.json'])['scanned']} file(s) scanned, no banned claims"
