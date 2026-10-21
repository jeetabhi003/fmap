"""Video: renders the storyboard plans into MP4 reels. Runs on the laptop with `run --render`.

Per plan:
  1. Voice each scene with edge-tts (video.voice_engine = "edge-tts"), or a silent
     track ("none") when no voice is wanted or reachable.
  2. Stretch any scene whose voice runs longer than planned, so speech never gets cut.
  3. Join the scene audio with ffmpeg and normalise loudness for Instagram (-14 LUFS).
  4. Render the Remotion "Reel" composition in video/ with the timed plan and the voice track.
  5. Optionally ask a running MoneyPrinterTurbo (video.moneyprinterturbo_url) for a
     stock-footage version from the same script.

Verification probes every MP4 with ffprobe: 1080x1920, H.264, has audio, and a
duration within half a second of the timed plan.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from core import Blocked, Pending

NAME = "video"

PAD_SEC = 0.5  # breathing room after each voiced line


def _run(cmd, cwd=None):
    subprocess.run(cmd, cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height",
         "-of", "json", str(path)], check=True, capture_output=True, text=True).stdout
    data = json.loads(out)
    video = next((s for s in data["streams"] if s["codec_type"] == "video"), {})
    return {
        "duration": float(data["format"]["duration"]),
        "width": video.get("width"), "height": video.get("height"), "codec": video.get("codec_name"),
        "has_audio": any(s["codec_type"] == "audio" for s in data["streams"]),
    }


def _voice_scene(text, voice, target, engine, proxy):
    if engine == "edge-tts":
        cmd = [sys.executable, "-m", "edge_tts", "--voice", voice, "--text", text, "--write-media", str(target)]
        if proxy:
            cmd[3:3] = ["--proxy", proxy]
        _run(cmd)
        return probe(target)["duration"]
    return 0.0


def build_audio(plan, work, engine, proxy):
    """Voice every scene, then return (timed plan, path to the joined voice track)."""
    timed = json.loads(json.dumps(plan))
    parts = []
    for scene in timed["scenes"]:
        raw = work / f"{scene['id']}.mp3"
        spoken = _voice_scene(scene["voice"], plan["voice"], raw, engine, proxy)
        scene["duration_sec"] = round(max(scene["duration_sec"], spoken + PAD_SEC), 2)
        part = work / f"{scene['id']}.wav"
        if spoken:
            _run(["ffmpeg", "-y", "-i", str(raw), "-af", "apad", "-t", str(scene["duration_sec"]),
                  "-ar", "48000", "-ac", "2", str(part)])
        else:
            _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                  "-t", str(scene["duration_sec"]), str(part)])
        parts.append(part)
    timed["duration_sec"] = round(sum(s["duration_sec"] for s in timed["scenes"]), 2)
    listing = work / "parts.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    joined = work / "voice.wav"
    loudness = "loudnorm=I=-14:TP=-1.5:LRA=11" if engine != "none" else "anull"
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listing.name, "-af", loudness,
          "-ar", "48000", "-ac", "2", joined.name], cwd=work)
    return timed, joined


def render(ctx, timed, voice_track, work):
    video_dir = ctx.path("video")
    public = video_dir / "public" / f"{timed['id']}.wav"
    shutil.copy(voice_track, public)
    props = work / "props.json"
    props.write_text(json.dumps({**timed, "audio": public.name}, ensure_ascii=False), encoding="utf-8")
    out = work / f"{timed['id']}.mp4"
    cmd = ["npx", "remotion", "render", "src/index.ts", "Reel", str(out), f"--props={props}", "--log=error"]
    browser = ctx.config.get("video", {}).get("browser_executable")
    if browser:
        cmd.append(f"--browser-executable={browser}")
    try:
        _run(cmd, cwd=video_dir)
    finally:
        public.unlink(missing_ok=True)
    return out


def moneyprinterturbo(base_url, body, api_key="", timeout_sec=1800, poll_sec=10):
    """Submit to MoneyPrinterTurbo's REST API, wait for the task, and return the first video's bytes."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    def call(path, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(base_url.rstrip("/") + path, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()

    task_id = json.loads(call("/api/v1/videos", body))["data"]["task_id"]
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        task = json.loads(call(f"/api/v1/tasks/{task_id}"))["data"]
        if task.get("state") == 1 and task.get("videos"):
            url = task["videos"][0]
            return call(url if url.startswith("/") else "/" + url.split("/", 3)[-1])
        if task.get("state") == -1:
            raise RuntimeError(f"MoneyPrinterTurbo task {task_id} failed")
        time.sleep(poll_sec)
    raise TimeoutError(f"MoneyPrinterTurbo task {task_id} not done after {timeout_sec}s")


def do(ctx):
    if not ctx.options.get("render"):
        raise Pending("rendering runs on the laptop: run with --render")
    for tool in ("ffmpeg", "ffprobe", "npx"):
        if not shutil.which(tool):
            raise Blocked(f"{tool} not installed")
    if not ctx.path("video", "node_modules").exists():
        raise Blocked("Remotion not installed: run `cd video && npm ci`")
    cfg = ctx.config.get("video", {})
    engine = cfg.get("voice_engine", "edge-tts")
    plans_dir = ctx.upstream("storyboard") / "plans"
    plans = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(plans_dir.glob("*.json"))]
    if not plans:
        raise Pending("no reel plans to render")

    files, report = {}, ["# Renders", ""]
    for plan in plans:
        work = ctx.path("work", "video-build", plan["id"])
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        timed, voice_track = build_audio(plan, work, engine, cfg.get("tts_proxy", ""))
        out = render(ctx, timed, voice_track, work)
        files[f"{plan['id']}.mp4"] = out.read_bytes()
        files[f"{plan['id']}.timed.json"] = json.dumps(timed, indent=2, ensure_ascii=False) + "\n"
        files[f"{plan['id']}.caption.txt"] = plan["caption"] + "\n"
        line = f"- {plan['id']}: Remotion {timed['duration_sec']}s, voice {engine}"
        mpt_url = cfg.get("moneyprinterturbo_url")
        if mpt_url:
            body = json.loads((ctx.upstream("storyboard") / "moneyprinterturbo" / f"{plan['id']}.json").read_text())
            try:
                files[f"{plan['id']}.stock.mp4"] = moneyprinterturbo(mpt_url, body, cfg.get("moneyprinterturbo_api_key", ""))
                line += "; MoneyPrinterTurbo stock version saved"
            except Exception as e:  # the Remotion render stands on its own
                line += f"; MoneyPrinterTurbo failed: {type(e).__name__}: {e}"
        report.append(line)
    report += ["", "Before posting: watch each render, check facts on MahaRERA, add the QR code and agent number."]
    files["report.md"] = "\n".join(report) + "\n"
    return files


def verify(ctx, files):
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, content in files.items():
            if not name.endswith(".mp4"):
                continue
            path = Path(tmp) / name
            path.write_bytes(content)
            info = probe(path)
            if (info["width"], info["height"]) != (1080, 1920):
                problems.append(f"{name}: {info['width']}x{info['height']}, expected 1080x1920")
            if info["codec"] != "h264":
                problems.append(f"{name}: codec {info['codec']}, expected h264")
            if not info["has_audio"]:
                problems.append(f"{name}: no audio track")
            if name.endswith(".stock.mp4"):
                continue
            timed = json.loads(files[name.replace(".mp4", ".timed.json")])
            if abs(info["duration"] - timed["duration_sec"]) > 0.5:
                problems.append(f"{name}: {info['duration']:.1f}s, plan says {timed['duration_sec']}s")
    return problems


def summary(files):
    reels = [n for n in files if n.endswith(".mp4") and not n.endswith(".stock.mp4")]
    stock = sum(n.endswith(".stock.mp4") for n in files)
    return f"{len(reels)} reel(s) rendered and checked" + (f", {stock} stock version(s)" if stock else "")
