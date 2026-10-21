"""Storyboard: turns verified projects and the reel playbook into scene-by-scene reel plans.

For the configured segment (video.segment), each matched project gets a plan built
from the template the references department picked for that segment. Every word
is ours: the reference reels give the shape (hook type, pacing, caption length,
call to action), never the text.

Outputs per plan:
  plans/<id>.json                 the scene plan the video department renders (Remotion)
  moneyprinterturbo/<id>.json     request body for MoneyPrinterTurbo's /api/v1/videos (stock b-roll version)
  openmontage/<id>.md             brief to paste into OpenMontage in Claude Code (optional third version)
"""

import json
import re

from core import has_rera_id, place, slugify
from departments.compliance import scan_text

NAME = "storyboard"

DISCLAIMER = "Research, not advice. Verify on MahaRERA before you pay."
VISUALS = {"data_card", "stock", "own"}
HASHTAGS = ["#Worli", "#MumbaiRealEstate", "#MahaRERA", "#MumbaiProperty", "#PropertyResearch",
            "#HomeBuyingIndia", "#WorliMumbai", "#RealEstateIndia"]
CTA_LINES = {
    "comment": ("Comment CHECKLIST for our free buyer's checklist.", "Comment CHECKLIST"),
    "dm": ("Message us CHECKLIST for the free buyer's checklist.", "Message us CHECKLIST"),
    "save": ("Save this for your site visit. Free checklist: link in bio.", "Save this · link in bio"),
    "share": ("Share this with someone buying in Mumbai. Free checklist: link in bio.", "Free checklist · link in bio"),
    "follow": ("Follow for verified project facts. Free checklist: link in bio.", "Follow · link in bio"),
    "link_in_bio": ("Free buyer's checklist: link in bio.", "Free checklist · link in bio"),
    "call_whatsapp": ("Free buyer's checklist: link in bio.", "Free checklist · link in bio"),
}


def spoken_id(rera_text):
    """'P51900080218 / P51900080252' -> 'P 5 1 9 0 0 0 8 0 2 1 8', so the voice reads it digit by digit."""
    first = re.search(r"P[0-9A-Z]{10,15}", rera_text)
    return " ".join(first.group(0)) if first else rera_text


def _scenes(template, p, cta_short):
    p = {**p, "locality": place(p["locality"])}
    low, high = p["price_cr_range"].split("-")
    rera = p["rera_id"]
    said = spoken_id(rera)
    if template == "three_checks":
        return [
            ("hook", f"3 checks before a deposit in {p['locality']}", p["project"], 3,
             f"Three checks before you pay a deposit at {p['project']}."),
            ("check", "1. MahaRERA ID", rera, 4, f"One. Look up the MahaRERA ID: {said}."),
            ("check", "2. Status", p["status"], 4, f"Two. Confirm the status: {p['status']}."),
            ("check", "3. Still open", p["caveats"], 5, f"Three. Ask about what is still open: {p['caveats']}."),
            ("cta", "Free buyer's checklist", cta_short, 4, "Get our free buyer's checklist. Link in bio."),
        ]
    if template == "myth_vs_fact":
        return [
            ("hook", "Myth: the brochure price is the price", p["project"], 3,
             "Myth: the brochure price is the price you will pay."),
            ("fact", "Fact: compare registered sales", f"Listed range ₹{low} to {high} Cr", 5,
             f"Fact: compare it with registered sales. The listed range here is {low} to {high} crore."),
            ("fact", "MahaRERA ID", rera, 4, f"Check the MahaRERA ID: {said}."),
            ("check", "Still to check", p["caveats"], 5, f"Still to check: {p['caveats']}."),
            ("cta", "Free buyer's checklist", cta_short, 4, "Get our free buyer's checklist. Link in bio."),
        ]
    return [  # price_check
        ("hook", f"₹{low} to {high} Cr in {p['locality']}", "What can you actually verify?", 3,
         f"{low} to {high} crore in {p['locality']}. Here is what we could verify."),
        ("fact", "MahaRERA ID", rera, 4, f"The MahaRERA ID is {said}. Look it up before any site visit."),
        ("fact", "Status", f"{p['status']} · {p['developer']}", 4, f"Status: {p['status']}. Developer: {p['developer']}."),
        ("check", "Still to check", p["caveats"], 5, f"Still to check: {p['caveats']}."),
        ("cta", "Free buyer's checklist", cta_short, 4, "Get our free buyer's checklist. Link in bio."),
    ]


def _fit(weights, total):
    """Scale scene lengths to the target total, in tenths of a second, summing exactly."""
    scale = total / sum(weights)
    tenths = [max(15, round(w * scale * 10)) for w in weights]
    tenths[-1] += round(total * 10) - sum(tenths)
    return [t / 10 for t in tenths]


def caption(p, style, cta_long, agent_line, as_of):
    tags = HASHTAGS[: max(3, min(len(HASHTAGS), style["caption"]["median_hashtags"] or 5))]
    return "\n".join([
        f"{p['project']}, {place(p['locality'])}: what is verified, and what is not.",
        f"MahaRERA ID {p['rera_id']} · {p['status']} · listed ₹{p['price_cr_range']} Cr (as of {as_of}).",
        f"Still to check: {p['caveats']}",
        cta_long,
        DISCLAIMER,
        agent_line,
        " ".join(tags),
    ])


def build_plan(p, segment, choice, style, cfg):
    video = cfg.get("video", {})
    as_of = cfg.get("data_as_of", "")
    cta_long, cta_short = CTA_LINES.get(style["caption"]["top_cta"], CTA_LINES["link_in_bio"])
    raw = _scenes(choice["template"], p, cta_short)
    target = style["median_length_sec"] or video.get("default_length_sec", 20)
    target = min(45, max(15, target))
    durations = _fit([s[3] for s in raw], target)
    agent = cfg.get("launch", {}).get("agent_rera_number") or "ADD BEFORE POSTING"
    plan_id = slugify(f"{segment}-{choice['template']}-{p['project']}")
    return {
        "id": plan_id,
        "segment": segment,
        "pattern": choice["pattern"],
        "template": choice["template"],
        "project": p["project"],
        "rera_id": p["rera_id"],
        "as_of": as_of,
        "width": 1080, "height": 1920, "fps": 30,
        "duration_sec": round(sum(durations), 1),
        "voice": video.get("voice", "en-IN-NeerjaNeural"),
        "brand": video.get("brand", {}),
        "disclaimer": DISCLAIMER,
        "scenes": [
            {"id": f"s{i + 1}", "kind": kind, "title": title, "body": body, "voice": voice,
             "duration_sec": d, "visual": {"kind": "data_card"}}
            for i, ((kind, title, body, _, voice), d) in enumerate(zip(raw, durations))
        ],
        "caption": caption(p, style, cta_long, f"Agent MahaRERA registration: {agent}", as_of),
        "sources": [f"data/properties.csv (as of {as_of})", f"MahaRERA {p['rera_id']}"],
        "posting_checklist": ["Check every fact on MahaRERA today", "Add the MahaRERA QR code",
                              "Add the agent's MahaRERA registration", "Watch the full render before posting"],
    }


def mpt_request(plan, cfg):
    """Body for MoneyPrinterTurbo POST /api/v1/videos (stock footage + subtitles from our script)."""
    video = cfg.get("video", {})
    return {
        "video_subject": f"{plan['project']} property facts, Mumbai",
        "video_script": " ".join(s["voice"] for s in plan["scenes"]),
        "video_terms": video.get("stock_terms", ["mumbai skyline", "worli sea link", "apartment interior", "city traffic night"]),
        "video_aspect": "9:16",
        "video_source": "pexels",
        "voice_name": video.get("mpt_voice", "en-IN-NeerjaNeural-Female"),
        "subtitle_enabled": True,
        "video_count": 1,
    }


def openmontage_brief(plan):
    scenes = "\n".join(f"{i + 1}. ({s['duration_sec']}s) On screen: \"{s['title']}\" / \"{s['body']}\". "
                       f"Voice: \"{s['voice']}\"" for i, s in enumerate(plan["scenes"]))
    return f"""# OpenMontage brief: {plan['id']}

Open the OpenMontage folder in Claude Code and paste the prompt below.

---
Make a {plan['duration_sec']}-second vertical (9:16) reel for Instagram about a Mumbai property project.
Use exactly this script and on-screen text. Do not add claims, prices, or facts that are not here.
Use free stock or abstract motion graphics only; never show footage presented as the actual project.
Indian English narration, calm and factual. Burn in captions. End on the call to action.

Scenes:
{scenes}

Final frame text: "{plan['disclaimer']}"
---

Sources: {'; '.join(plan['sources'])}
"""


def do(ctx):
    cfg = ctx.config
    segment = cfg.get("video", {}).get("segment", "investor")
    shortlists = json.loads((ctx.upstream("matching") / "shortlists.json").read_text(encoding="utf-8"))
    refs = ctx.upstream("references")
    if refs:
        style = json.loads((refs / "style.json").read_text(encoding="utf-8"))
    else:  # no reference reels yet: a neutral default shape
        style = {"median_length_sec": 0, "caption": {"median_hashtags": 5, "top_cta": "link_in_bio"},
                 "by_segment": {segment: {"pattern": "price_reveal", "template": "price_check"}}}
    choice = style["by_segment"][segment]
    projects = [p for p in shortlists[segment]["matched"] if has_rera_id(p["rera_id"])]
    projects = projects[: cfg.get("video", {}).get("max_reels", 3)]
    files = {}
    for p in projects:
        plan = build_plan(p, segment, choice, style, cfg)
        files[f"plans/{plan['id']}.json"] = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
        files[f"moneyprinterturbo/{plan['id']}.json"] = json.dumps(mpt_request(plan, cfg), indent=2, ensure_ascii=False) + "\n"
        files[f"openmontage/{plan['id']}.md"] = openmontage_brief(plan)
    files["index.md"] = (f"# Storyboards: {segment}\n\nTemplate {choice['template']} (pattern {choice['pattern']}"
                         f"{'' if refs else ', default: no reference reels yet'}).\n\n"
                         + ("\n".join(f"- {n}" for n in sorted(files) if n.startswith("plans/")) or "No verified projects to plan.")
                         + "\n")
    return files


def verify(ctx, files):
    problems = []
    for name, text in files.items():
        if not name.startswith("plans/"):
            continue
        plan = json.loads(text)
        total = round(sum(s["duration_sec"] for s in plan["scenes"]), 1)
        if abs(total - plan["duration_sec"]) > 0.05:
            problems.append(f"{name}: scenes add to {total}s, plan says {plan['duration_sec']}s")
        if not has_rera_id(plan["rera_id"]) or plan["rera_id"] not in plan["caption"]:
            problems.append(f"{name}: caption lacks the MahaRERA ID")
        if DISCLAIMER not in plan["caption"]:
            problems.append(f"{name}: caption lacks the disclaimer")
        for s in plan["scenes"]:
            if not (s["title"] and s["body"] and s["voice"]):
                problems.append(f"{name}: scene {s['id']} has empty text")
            if s["visual"]["kind"] not in VISUALS:
                problems.append(f"{name}: scene {s['id']} uses visual '{s['visual']['kind']}' without rights")
        words = " ".join([plan["caption"]] + [f"{s['title']} {s['body']} {s['voice']}" for s in plan["scenes"]])
        problems += [f"{name}: {reason} ('{hit}')" for _, reason, hit in scan_text(words)]
    return problems


def summary(files):
    plans = [n for n in files if n.startswith("plans/")]
    return f"{len(plans)} reel plan(s) with MoneyPrinterTurbo and OpenMontage briefs"
