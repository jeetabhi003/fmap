# fmap: Find Me A Property pipeline

One orchestrator runs the business as a pipeline: research → verified register → listings and reel references → post kits → website funnels → compliance → launch. Every department does its work, verifies it, and saves it. Design: [`docs/architecture.md`](docs/architecture.md).

## Set up on the laptop

1. Clone the repo and check out this branch.
2. Create `toolkit/config.local.json` (not committed) pointing at the research engine:
   ```json
   {
     "engine": { "root": "/Users/abhijeet/Desktop/market intelligence/research and content engine" }
   }
   ```
   Add launch settings here too when you have them (see `toolkit/config.json` for the keys).
3. Put the private inputs in place. All of them stay out of git:
   - Research document → `data/inputs/research/`
   - Internet listings → `data/inputs/listings.csv` (start from `data/inputs/listings.template.csv`)
   - Reference reels → `data/inputs/reels.csv` (start from `data/inputs/reels.template.csv`)
   - Lead sheet export → `data/leads/export.csv`
4. Run it:
   ```bash
   python3 toolkit/orchestrator/orchestrator.py run                # uses the engine's latest output
   python3 toolkit/orchestrator/orchestrator.py run --run-engine   # re-runs the engine first (hours)
   ```
5. Read `outputs/report/status.md`. It lists what is done, what needs a person, and what failed.

## Reels on the laptop

```bash
pip install edge-tts==7.3.1                 # free AI voice
cd video && npm ci && cd ..                 # Remotion templates
# reference reels: put links (and captions if you have them) in data/inputs/reels.csv
python3 toolkit/orchestrator/orchestrator.py run --only references --fetch-reels   # analyse why they work
python3 toolkit/orchestrator/orchestrator.py run --only video --render             # plan and render MP4s
```

Renders land in `outputs/video/` with a caption file each. Optional: run MoneyPrinterTurbo locally and set `video.moneyprinterturbo_url` (and `moneyprinterturbo_api_key`) in `toolkit/config.local.json` for a stock-footage version. For OpenMontage, paste `outputs/storyboard/openmontage/<id>.md` into Claude Code inside an OpenMontage clone. Preview templates with `cd video && npm run studio`.

The whole project in one file: [`docs/project.spec.json`](docs/project.spec.json).

## What is where

| Path | What it is |
|---|---|
| `toolkit/orchestrator/` | The orchestrator and `pipeline.json` (department order) |
| `toolkit/departments/` | One file per department |
| `toolkit/config.json` | Settings; overlaid by `config.local.json` on the laptop |
| `toolkit/segments.json` | The three customer segments and their funnel copy |
| `data/properties.csv` | The curated project register (edited by a person) |
| `products/` | Ebook outlines, free checklist, email sequences, shortlist service |
| `video/` | Remotion project that renders reel plans |
| `docs/project.spec.json` | The whole project, decisions and build order in one JSON spec |
| `site/` | The generated website (do not edit by hand; edit `toolkit/departments/web.py`) |
| `docs/strategy/` | Funnel, segments, compliance rules |
| `tests/` | Tests for every department |

## Rules the pipeline enforces

- No project is shown, matched or posted without a real MahaRERA ID.
- Prices are shown only when verified, always with their date.
- Internet listings are credited to their source; their photos and videos are used only with rights.
- Reference reels are studied, never downloaded or reposted.
- No promised returns, "best", "sold out" or fake urgency anywhere.
- Lead data never enters the repo; the pipeline reports counts only.
- Property sales go through a MahaRERA-registered agent.

Research, not advice. Verify each project on MahaRERA before you pay.
