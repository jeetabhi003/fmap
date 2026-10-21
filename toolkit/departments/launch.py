"""Launch: the final gate. Lists every setting a person must provide before going live."""

import json

from core import Blocked

NAME = "launch"


def missing_settings(cfg):
    launch = cfg.get("launch", {})
    missing = [key for key in ("form_url", "shortlist_form_url", "agent_rera_number", "contact_email")
               if not launch.get(key)]
    missing += [f"ebook_store_urls.{seg}" for seg, url in launch.get("ebook_store_urls", {}).items() if not url]
    if not cfg.get("research_confirmed"):
        missing.append("research_confirmed (confirm data/properties.csv against the research document)")
    return missing


def do(ctx):
    missing = missing_settings(ctx.config)
    if missing:
        raise Blocked("set in toolkit/config.json or config.local.json: " + ", ".join(missing))
    return {"ready.json": json.dumps({"ready": True}, indent=2) + "\n"}


def verify(ctx, files):
    return []


def summary(files):
    return "all launch settings present"
