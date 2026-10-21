---
name: fmap-pipeline
description: Run, check, or extend the Find Me A Property pipeline (orchestrator, departments, register, listings, reels, post kits, site, leads, launch). Use when asked to run the pipeline, add listings or reference reels, shortlist projects for a buyer, build the site, or add a department.
---

# Find Me A Property pipeline

Read `docs/architecture.md` first.

## Run
- Full run: `python3 toolkit/orchestrator/orchestrator.py run`, then read `outputs/report/status.md`.
- Shortlist for a buyer: `python3 toolkit/orchestrator/orchestrator.py match --segment <end_user|investor|legacy> --budget-cr <N>`.
- Tests: `python3 -m unittest discover -s tests`. Run them after every change.
- Only use `--run-engine` when the user asks: the research engine takes hours.

## Rules
- Never edit `site/` by hand; change `toolkit/departments/web.py` or `toolkit/segments.json` and re-run.
- Never merge `outputs/intake/candidates.csv` into `data/properties.csv` without the user approving each change.
- Never commit anything under `data/inputs/`, `outputs/`, `work/`, `data/leads/export.csv` or `toolkit/config.local.json`. The repo is public.
- Never post, email, or contact anyone. Post kits are drafts for a person.
- Never download or repost reference reels, or use listing media without rights.
- No promised returns, "best", "sold out" or fake urgency. The compliance department enforces this; do not weaken its patterns to make a run pass.

## Add a department
Write `toolkit/departments/<name>.py` with `NAME`, `do(ctx)`, `verify(ctx, files)`, `summary(files)`; register it in `toolkit/departments/__init__.py`; add it to `toolkit/orchestrator/pipeline.json` after its dependencies; add a test.
