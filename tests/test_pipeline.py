"""Tests for the orchestrator and every department. Run: python3 -m unittest discover -s tests"""

import csv
import http.server
import io
import json
import shutil
import threading
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "toolkit"))
sys.path.insert(0, str(REPO / "toolkit" / "orchestrator"))

import orchestrator  # noqa: E402
from core import Context, Result, promote, run_department  # noqa: E402
from departments import compliance, intake, listings, matching, references, storyboard, video  # noqa: E402

LISTING_FIELDS = listings.COLUMNS
REEL_FIELDS = references.COLUMNS


def listing(**overrides):
    row = {
        "listing_id": "L1", "project": "Runwal Raaya", "locality": "Worli", "rera_id": "P51900080218",
        "configuration": "3 BHK", "carpet_sqft": "1400", "price_text": "Rs 9.5 Cr", "source_name": "Example portal",
        "source_url": "https://example.com/l/1", "retrieved_on": "2026-10-20", "media_url": "https://example.com/p.jpg",
        "media_rights": "none", "notes": "",
    }
    row.update(overrides)
    return row


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class Sandbox(unittest.TestCase):
    """A copy of the committed repo files in a temp folder, so runs never touch the real repo."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for folder in ("toolkit", "scripts", "products"):
            shutil.copytree(REPO / folder, self.tmp / folder, ignore=shutil.ignore_patterns("__pycache__", "config.local.json"))
        (self.tmp / "data").mkdir()
        shutil.copy(REPO / "data" / "properties.csv", self.tmp / "data" / "properties.csv")
        (self.tmp / "site").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_pipeline(self, only=None):
        ctx = Context(root=self.tmp)
        with redirect_stdout(io.StringIO()):
            code = orchestrator.run(ctx, only)
        return ctx, code

    def add_engine_output(self):
        projects = [
            {"project_name": "Lodha Adrina", "developer": "Lodha", "rank": 1,
             "score": {"normalized_score": 78, "grade": "B+"},
             "research": {"project_identity": {"rera_number": "P51900014000", "status": "Ready"}}},
            {"project_name": "Godrej Trilogy", "developer": "Godrej", "rank": 2,
             "score": {"normalized_score": 70, "grade": "B"},
             "research": {"project_identity": {"rera_number": "P51900099999"}}},
            {"project_name": "New Tower", "developer": "Someone", "rank": 3,
             "research": {"identity": {"rera_number": "P51900011111"}, "location_data": {"zone": "Naka"}}},
        ]
        target = self.tmp / "data" / "inputs" / "engine" / "Worli_20261020_projects.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(projects), encoding="utf-8")


class CoreTests(unittest.TestCase):
    def test_promote_is_idempotent_and_removes_only_its_own_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "keep.txt").write_text("not ours")
            self.assertTrue(promote(folder, {"a.txt": "1", "b.txt": "2"}, "x"))
            self.assertFalse(promote(folder, {"a.txt": "1", "b.txt": "2"}, "x"))
            self.assertTrue(promote(folder, {"a.txt": "1"}, "x"))
            self.assertFalse((folder / "b.txt").exists())
            self.assertTrue((folder / "keep.txt").exists())

    def test_failed_verification_keeps_draft_and_leaves_output_untouched(self):
        class Bad:
            NAME = "bad"

            @staticmethod
            def do(ctx):
                return {"out.txt": "draft"}

            @staticmethod
            def verify(ctx, files):
                return ["wrong"]

            @staticmethod
            def summary(files):
                return ""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = Context(root=root, config={})
            result = run_department(Bad, ctx, root / "out", root / "work" / "bad")
            self.assertEqual(result.status, "failed")
            self.assertEqual((root / "work" / "bad" / "out.txt").read_text(), "draft")
            self.assertFalse((root / "out").exists())


class DepartmentTests(unittest.TestCase):
    def test_engine_projects_map_both_identity_shapes(self):
        rows = intake.map_engine_projects([
            {"project_name": "A", "research": {"project_identity": {"rera_number": "P1"}}},
            {"project_name": "B", "research": {"identity": {"rera_number": "P2"}, "location_data": {"zone": "Naka"}}},
            {"project_name": "C"},
        ])
        self.assertEqual([r["rera_id"] for r in rows], ["P1", "P2", ""])
        self.assertEqual(rows[1]["zone"], "Naka")

    def test_listings_screening(self):
        register = [{"project": "Runwal Raaya", "rera_id": "P51900080218 / P51900080252"},
                    {"project": "Godrej Trilogy", "rera_id": "see ledger"}]
        showcase, excluded = listings.screen([
            listing(),
            listing(listing_id="L2", media_rights="own"),
            listing(listing_id="L3", rera_id="P51900099999"),
            listing(listing_id="L4", retrieved_on="20 Oct"),
            listing(listing_id="L5", project="Godrej Trilogy", rera_id="P51900012345"),
        ], register)
        by_id = {s["listing_id"]: s for s in showcase}
        self.assertEqual(sorted(by_id), ["L1", "L2", "L5"])
        self.assertEqual(by_id["L1"]["media_url"], "")
        self.assertEqual(by_id["L2"]["media_url"], "https://example.com/p.jpg")
        reasons = {e["listing_id"]: e["reasons"] for e in excluded}
        self.assertIn("differs from register", reasons["L3"][0])
        self.assertIn("YYYY-MM-DD", reasons["L4"][0])

    def test_reference_urls(self):
        kept, rejected = references.screen([
            {"url": "https://www.instagram.com/reel/AbC_123/"},
            {"url": "https://instagram.com/p/xyz"},
            {"url": "https://example.com/video"},
        ])
        self.assertEqual(len(kept), 2)
        self.assertEqual(rejected, ["https://example.com/video"])

    def test_matching_filters_by_budget_and_verification(self):
        rows = [
            {"project": "A", "locality": "", "rera_id": "P51900000001", "developer": "", "status": "Under construction",
             "price_cr_range": "10-20", "price_verified": "yes", "shortlist": "Investor", "open_items": ""},
            {"project": "B", "locality": "", "rera_id": "P51900000002", "developer": "", "status": "Ready",
             "price_cr_range": "30-40", "price_verified": "yes", "shortlist": "Investor", "open_items": ""},
            {"project": "C", "locality": "", "rera_id": "P51900000003", "developer": "", "status": "Ready",
             "price_cr_range": "unknown", "price_verified": "no", "shortlist": "Investor", "open_items": "price"},
            {"project": "D", "locality": "", "rera_id": "see ledger", "developer": "", "status": "Ready",
             "price_cr_range": "5-6", "price_verified": "yes", "shortlist": "Investor", "open_items": ""},
        ]
        result = matching.match(rows, "investor", budget_cr=25)
        self.assertEqual([e["project"] for e in result["matched"]], ["A"])
        self.assertEqual([e["project"] for e in result["over_budget"]], ["B"])
        self.assertEqual([e["project"] for e in result["to_check"]], ["C", "D"])
        with self.assertRaises(ValueError):
            matching.match(rows, "tourist")

    def test_compliance_patterns(self):
        self.assertTrue(compliance.scan_text("Assured returns of 12%"))
        self.assertTrue(compliance.scan_text("Only 2 flats left!"))
        self.assertTrue(compliance.scan_text("The best investment in Worli"))
        self.assertFalse(compliance.scan_text("It is best to check MahaRERA first."))
        self.assertFalse(compliance.scan_text("We do not predict returns."))


REEL_CAPTIONS = [
    {"url": "https://www.instagram.com/reel/AAA/", "account": "@one", "format": "talking head", "length_sec": "24",
     "caption": "₹3.2 Cr for a 2 BHK in Worli?\n1. Check the RERA page\n2. Ask for carpet area\n3. Compare registered sales\n"
                "Comment CHECK for the list #Worli #Mumbai #RealEstate"},
    {"url": "https://www.instagram.com/reel/BBB/", "account": "@two", "format": "talking head", "length_sec": "30",
     "caption": "Is the brochure price the real price?\nSave this before your next site visit. #Mumbai"},
]


class AnalysisTests(unittest.TestCase):
    def test_caption_features_and_pattern(self):
        f = references.analyse_caption(REEL_CAPTIONS[0]["caption"])
        self.assertEqual(f["pattern"], "price_reveal")
        self.assertTrue(f["hook_has_price"])
        self.assertEqual(f["list_lines"], 3)
        self.assertEqual(f["hashtags"], 3)
        self.assertIn("comment", f["ctas"])
        q = references.analyse_caption(REEL_CAPTIONS[1]["caption"])
        self.assertEqual(q["pattern"], "question_hook")
        self.assertIn("save", q["ctas"])
        self.assertIn("opens on a price", " ".join(references.reasons(f)))

    def test_parse_instagram_meta(self):
        page = ('<meta property="og:description" content="1,234 likes, 56 comments - some.account on October 1, 2026: '
                '&quot;Line one\nLine two #tag&quot;. ">')
        meta = references.parse_og_description(page)
        self.assertEqual(meta["likes"], 1234)
        self.assertEqual(meta["comments"], 56)
        self.assertEqual(meta["account"], "@some.account")
        self.assertTrue(meta["caption"].startswith("Line one"))

    def test_spoken_id_and_place(self):
        self.assertEqual(storyboard.spoken_id("P51900080218 / P51900080252"), "P 5 1 9 0 0 0 8 0 2 1 8")
        from core import place
        self.assertEqual(place("Naka"), "Worli Naka")
        self.assertEqual(place("Worli Naka"), "Worli Naka")


class FakeMoneyPrinterTurbo(http.server.BaseHTTPRequestHandler):
    """Mimics MoneyPrinterTurbo: POST /api/v1/videos, GET /api/v1/tasks/{id}, static /tasks/... files."""
    polls = 0

    def log_message(self, *args):
        pass

    def _json(self, body):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        assert self.headers.get("x-api-key") == "secret"
        assert body["video_aspect"] == "9:16" and body["video_script"]
        self._json({"status": 200, "data": {"task_id": "t1"}})

    def do_GET(self):
        if self.path == "/api/v1/tasks/t1":
            FakeMoneyPrinterTurbo.polls += 1
            done = FakeMoneyPrinterTurbo.polls > 1
            self._json({"status": 200, "data": {"state": 1 if done else 4, "progress": 100 if done else 50,
                                                 "videos": ["http://127.0.0.1/tasks/t1/final-1.mp4"] if done else []}})
        elif self.path == "/tasks/t1/final-1.mp4":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"MP4BYTES")
        else:
            self.send_response(404)
            self.end_headers()


class VideoTests(unittest.TestCase):
    def test_moneyprinterturbo_adapter(self):
        server = http.server.HTTPServer(("127.0.0.1", 0), FakeMoneyPrinterTurbo)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{server.server_port}"
            body = {"video_aspect": "9:16", "video_script": "hello"}
            self.assertEqual(video.moneyprinterturbo(url, body, "secret", timeout_sec=10, poll_sec=0), b"MP4BYTES")
        finally:
            server.shutdown()


class PipelineTests(Sandbox):
    def test_committed_repo_runs_clean(self):
        ctx, code = self.run_pipeline()
        self.assertEqual(code, 0)
        statuses = {n: r.status for n, r in ctx.results.items()}
        self.assertEqual(statuses["register"], "ok")
        self.assertEqual(statuses["web"], "ok")
        self.assertEqual(statuses["compliance"], "ok")
        self.assertEqual(statuses["launch"], "blocked")
        self.assertTrue((self.tmp / "site" / "index.html").exists())

    def test_full_run_with_all_inputs(self):
        self.add_engine_output()
        write_csv(self.tmp / "data" / "inputs" / "listings.csv", LISTING_FIELDS,
                  [listing(), listing(listing_id="L2", rera_id="bad")])
        write_csv(self.tmp / "data" / "inputs" / "reels.csv", REEL_FIELDS, [
            {"url": "https://www.instagram.com/reel/AAA/", "format": "walkthrough", "length_sec": "40",
             "caption": "₹9 Cr in Worli: what is verified?"},
            {"url": "https://www.instagram.com/reel/BBB/", "format": "walkthrough", "length_sec": "30"},
        ])
        ctx, code = self.run_pipeline()
        self.assertEqual(code, 0)
        statuses = {n: r.status for n, r in ctx.results.items()}
        for name in ("intake", "listings", "references", "content", "compliance"):
            self.assertEqual(statuses[name], "ok", ctx.results[name].message)
        diff = (self.tmp / "outputs" / "intake" / "diff.md").read_text()
        self.assertIn("New Tower", diff)
        self.assertIn("Lodha Adrina: engine P51900014000 vs register P51900014937", diff)
        self.assertNotIn("Godrej Trilogy: engine", diff)  # register says 'see ledger', so no clash claimed
        post = (self.tmp / "outputs" / "content" / "posts" / "listing-runwal-raaya-l1.md").read_text()
        self.assertIn("walkthrough", post)
        self.assertIn("none (use our own footage", post)

    def test_banned_claim_in_listing_fails_content_and_blocks_launch(self):
        write_csv(self.tmp / "data" / "inputs" / "listings.csv", LISTING_FIELDS,
                  [listing(price_text="Rs 9.5 Cr, assured returns")])
        ctx, code = self.run_pipeline()
        self.assertEqual(code, 1)
        self.assertEqual(ctx.results["content"].status, "failed")
        self.assertEqual(ctx.results["launch"].status, "waiting")
        self.assertTrue((self.tmp / "work" / "content" / "index.md").exists())
        self.assertFalse((self.tmp / "outputs" / "content").exists())

    def test_engine_runs_commands_then_feeds_intake(self):
        engine_root = self.tmp / "laptop-engine"
        script = engine_root / "backend" / "main.py"
        script.parent.mkdir(parents=True)
        script.write_text(
            "import json, pathlib\n"
            "out = pathlib.Path('output/reports'); out.mkdir(parents=True, exist_ok=True)\n"
            "(out / 'Worli_1_projects.json').write_text(json.dumps([{'project_name': 'Engine Tower'}]))\n"
        )
        config = json.loads((self.tmp / "toolkit" / "config.json").read_text())
        config["engine"].update(root=str(engine_root), research_cmd=[sys.executable, "backend/main.py"], carousel_cmd=[])
        ctx = Context(root=self.tmp, config=config, options={"run_engine": True})
        with redirect_stdout(io.StringIO()):
            orchestrator.run(ctx, ["intake", "engine"])
        self.assertEqual(ctx.results["engine"].status, "ok", ctx.results["engine"].message)
        self.assertIn("Engine Tower", (self.tmp / "outputs" / "intake" / "candidates.csv").read_text())

    def test_reels_analysed_without_copying_captions(self):
        write_csv(self.tmp / "data" / "inputs" / "reels.csv", REEL_FIELDS, REEL_CAPTIONS + [{"url": "https://example.com/x"}])
        ctx, _ = self.run_pipeline(only=["references", "storyboard"])
        self.assertEqual(ctx.results["references"].status, "ok", ctx.results["references"].message)
        playbook = (self.tmp / "outputs" / "references" / "playbook.md").read_text()
        self.assertNotIn("Check the RERA page", playbook)
        self.assertIn("price_reveal", playbook)
        style = json.loads((self.tmp / "outputs" / "references" / "style.json").read_text())
        self.assertEqual(style["by_segment"]["investor"]["template"], "price_check")
        self.assertEqual(style["caption"]["top_cta"], "comment")
        plan_path = next((self.tmp / "outputs" / "storyboard" / "plans").glob("*.json"))
        plan = json.loads(plan_path.read_text())
        self.assertEqual(plan["duration_sec"], 27.0)  # median of 24 and 30 seconds
        self.assertAlmostEqual(sum(s["duration_sec"] for s in plan["scenes"]), 27.0)
        self.assertIn("Comment CHECKLIST", plan["caption"])

    def test_banned_claim_blocks_storyboard(self):
        path = self.tmp / "data" / "properties.csv"
        path.write_text(path.read_text().replace("Developer not listed; locality address conflict",
                                                 "Assured returns of 12 percent"))
        ctx, code = self.run_pipeline(only=["storyboard"])
        self.assertEqual(code, 1)
        self.assertEqual(ctx.results["storyboard"].status, "failed")

    def test_video_waits_for_render_flag(self):
        ctx, _ = self.run_pipeline(only=["video"])
        self.assertEqual(ctx.results["video"].status, "pending")

    @unittest.skipUnless(shutil.which("ffmpeg") and (REPO / "video" / "node_modules").exists(),
                         "needs ffmpeg and `cd video && npm ci`")
    def test_render_one_reel(self):
        shutil.copytree(REPO / "video", self.tmp / "video", symlinks=True,
                        ignore=shutil.ignore_patterns("out"))
        config = json.loads((self.tmp / "toolkit" / "config.json").read_text())
        config["video"].update(voice_engine="none", max_reels=1, default_length_sec=15)
        headless = Path("/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell")
        if headless.exists():
            config["video"]["browser_executable"] = str(headless)
        ctx = Context(root=self.tmp, config=config, options={"render": True})
        with redirect_stdout(io.StringIO()):
            orchestrator.run(ctx, ["video"])
        self.assertEqual(ctx.results["video"].status, "ok", ctx.results["video"].message)
        info = video.probe(next((self.tmp / "outputs" / "video").glob("*.mp4")))
        self.assertEqual((info["width"], info["height"]), (1080, 1920))
        self.assertTrue(info["has_audio"])

    def test_only_runs_dependencies(self):
        ctx, _ = self.run_pipeline(only=["web"])
        self.assertEqual(list(ctx.results), ["register", "matching", "web"])

    def test_waiting_result_type(self):
        self.assertEqual(Result("waiting", "x").status, "waiting")


if __name__ == "__main__":
    unittest.main()
