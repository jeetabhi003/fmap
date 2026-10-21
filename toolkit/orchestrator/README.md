# Orchestrator

One agent runs the whole project. `orchestrator.py` is the only entry point. It runs each job in `pipeline.json` in order, skips jobs whose dependencies are not ok, saves the result, and writes `docs/strategy/status.md`.

## Commands

```bash
python3 toolkit/orchestrator/orchestrator.py list     # jobs and their dependencies
python3 toolkit/orchestrator/orchestrator.py run      # run the pipeline
python3 toolkit/orchestrator/orchestrator.py status   # last saved run
```

## Job statuses

| Status | Meaning | Fails the run? |
|---|---|---|
| ok | Done and healthy | no |
| pending | Not started yet | no |
| blocked | Needs an input only a person can give | no |
| waiting | A dependency is not ok, so the job was skipped | no |
| failed | Something in the repo is wrong | yes |

## Current jobs

| Job | Checks |
|---|---|
| research_input | A research document exists in `data/inputs/research/`. Blocked until one is added. |
| validate_register | `data/properties.csv` follows the rules in `scripts/validate_register.py`. |
| site_placeholders | `site/index.html` has no `FORM_ID` or missing agent registration number. |
| ebook_outlines | Each outline in `products/ebooks/` has 5 or more sections. |
| lead_summary | Counts leads from `data/leads/export.csv` if you put a local export there. Prints counts only. |
| shortlist_ready | At least one shortlisted project has a verified price. |
| ebook_drafts | Full drafts exist in `products/ebooks/drafts/`. Waits on the research input and the outlines. |

## Adding a job

1. Write `job_<name>(cfg)` in `orchestrator.py`. It returns `(status, message)`.
2. Register it in `JOBS`.
3. Add it to `pipeline.json` after its dependencies.

## What the orchestrator does not do yet

- It does not draft ebooks or write content. `ebook_drafts` only checks that drafts exist. Drafting will be a job added once the research document is in place.
- It does not send email, take payments, or post anywhere.
- It does not commit its own output. CI runs it and fails on `failed` jobs only. Run it locally to refresh `docs/strategy/status.md`.

## Private data

Lead exports and job state stay out of git (see `.gitignore`). The orchestrator prints counts only.
