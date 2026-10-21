# Architecture

One orchestrator (`toolkit/orchestrator/orchestrator.py`) runs the whole business as a pipeline of departments. Every department runs the same cycle: **do** the work, **verify** it against written rules, and **save** it. Only verified output is promoted for the departments after it. Output that fails verification is kept in `work/<department>/` for a person to review and is never used downstream.

## Pipeline

```
 inputs (laptop, not in git)          departments, in order                       human gates
 ───────────────────────────          ─────────────────────                       ───────────
 research engine on laptop ──► engine ──► intake ─► diff.md ───────────────────► person edits data/properties.csv
 data/inputs/research/        ─────────────┘
 data/properties.csv ───────────────────► register ─┬─► matching ─► web ─► compliance ─┐
 data/inputs/listings.csv ──────────────► listings ─┤                     ▲            │
 data/inputs/reels.csv ─────────────────► references┤                     │            ├─► launch ──► person fills launch settings
                                                    └─► content ──────────┘            │              (form links, agent number,
                                                         post kits (drafts) ──────────►┘               store links, research confirmed)
 data/leads/export.csv ─────────────────► leads (counts only)                               person posts, emails, sells
```

## Departments

| Department | Does | Verifies | Saves to |
|---|---|---|---|
| engine | Runs the laptop research engine and carousel generator (only with `--run-engine`), then collects the newest `*_projects.json` | JSON is a non-empty list; every project has a name | `outputs/engine/` |
| intake | Maps engine projects to candidate rows; lists research documents | Every candidate has a project name | `outputs/intake/` (`candidates.csv`, `diff.md`) |
| register | Summarises `data/properties.csv` | Rules in `scripts/validate_register.py` | `outputs/register/` |
| listings | Screens internet listings | Showcased listings have a valid MahaRERA ID, an https source, a retrieval date, a RERA ID that agrees with the register, and media only with rights | `outputs/listings/` |
| references | Builds a style brief from reference reels | At least one valid Instagram reel URL. Nothing is downloaded | `outputs/references/` |
| matching | Shortlists per segment | Every matched project has a real MahaRERA ID and a verified price | `outputs/matching/` |
| content | Reel scripts, carousels and captions for verified projects and screened listings | Each kit has its MahaRERA ID, the disclaimer and a QR placeholder; no banned claims | `outputs/content/` |
| web | Builds the site: home, three segment funnels, checklist, privacy | Disclaimer on every page; no placeholders; no broken links | `site/` |
| compliance | Scans the site, products and post kits | No banned claims (returns, "best", "sold out", fake urgency) | `outputs/compliance/` |
| leads | Counts leads from a local sheet export | Every row has recorded consent | `outputs/leads/` |
| launch | Final gate | Every launch setting is present and the research is confirmed | `outputs/launch/` |

Statuses: `ok`, `pending` (nothing to do yet), `blocked` (needs a person), `waiting` (a dependency is not ok), `failed` (verification failed or crashed). Only `failed` fails the run.

## Saving and versioning

- A department's output version is a hash of its files. Saving writes a `.manifest.json` with the version and a hash per file.
- If the version is unchanged, nothing is rewritten, so re-runs are safe and produce no churn.
- A save removes only files that department saved before, never anything else in its folder.
- `data/jobs/state.json` holds the last run. `outputs/report/status.md` is the readable report.

## What stays out of git

The repo is public. Research documents, engine output, listings, reel lists, lead exports, `outputs/`, `work/` and `toolkit/config.local.json` are ignored. Only code, templates, the register, products and the generated site are committed.

## Human gates

1. Review `outputs/intake/diff.md` and edit `data/properties.csv` by hand. Nothing is merged automatically.
2. Check every post kit against MahaRERA, add the MahaRERA QR code, then post.
3. Fill in the launch settings and set `research_confirmed` once the register matches the research document.
4. Send emails and hand shortlists to the licensed agent.

## Extending

Add a department: write `toolkit/departments/<name>.py` with `NAME`, `do`, `verify` and `summary`, register it in `toolkit/departments/__init__.py`, and add it to `toolkit/orchestrator/pipeline.json` after its dependencies. Add a test in `tests/test_pipeline.py`.

Planned, not built: a drafting department that writes full ebook chapters with the Claude API from the research document. It will be an explicit command, never automatic in CI, because it costs money.
