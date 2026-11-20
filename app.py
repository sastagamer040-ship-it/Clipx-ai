import os, uuid, shutil, subprocess, json
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).parent
DATA = BASE / "data"
UPLOADS = DATA / "uploads"
OUTPUTS = DATA / "outputs"
for p in (UPLOADS, OUTPUTS): p.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="CLIPX AI")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUTS), name="outputs")

@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/api/health")
def health():
    return {"ok": True, "ffmpeg": shutil.which("ffmpeg") is not None}

@app.post("/api/process")
async def process_video(file: UploadFile = File(...), clips: int = Form(3), duration: int = Form(45)):
    if not file.filename or not file.filename.lower().endswith((".mp4", ".mov", ".mkv", ".webm", ".m4v")):
        raise HTTPException(400, "Upload an MP4, MOV, MKV, WEBM or M4V video.")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise HTTPException(500, "FFmpeg is not installed on the server.")
    job = uuid.uuid4().hex[:10]
    src = UPLOADS / f"{job}_{Path(file.filename).name}"
    with src.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    try:
        result = create_clips(src, job, max(1, min(clips, 10)), max(30, min(duration, 60)))
    except Exception as e:
        raise HTTPException(500, f"Processing failed: {e}")
    return {"job_id": job, "clips": result, "note": "Review clips before publishing. Only use footage you own or have permission to edit."}

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-1800:])
    return p.stdout

def probe(path):
    raw = run(["ffprobe","-v","error","-show_entries","format=duration","-of","json",str(path)])
    return float(json.loads(raw)["format"]["duration"])

def create_clips(src, job, count, length):
    total = probe(src)
    if total < 8: raise ValueError("Video is too short.")
    # Coarse candidate scan: sample windows across the source. Rank by audio loudness
    # (a useful gaming-action proxy), then spread selected moments apart.
    step = max(5, min(15, total / 24))
    candidates = []
    t = 0.0
    while t < total:
        window = min(8.0, total - t)
        if window >= 3:
            cmd = ["ffmpeg","-ss",str(t),"-i",str(src),"-t",str(window),"-vn","-af","volumedetect","-f","null","-"]
            p = subprocess.run(cmd, capture_output=True, text=True)
            import re
            m = re.search(r"mean_volume:\s*(-?[\d.]+)\s*dB", p.stderr or "")
            peak = re.search(r"max_volume:\s*(-?[\d.]+)\s*dB", p.stderr or "")
            mean = float(m.group(1)) if m else -60
            maxv = float(peak.group(1)) if peak else -60
            candidates.append((0.65*maxv + 0.35*mean, t + window/2))
        t += step
    candidates.sort(reverse=True)
    chosen = []
    for score, center in candidates:
        start = max(0, min(total-length, center-length/2))
        if all(abs(start-x) > length*0.65 for x in chosen):
            chosen.append(start)
        if len(chosen) >= count: break
    if not chosen: chosen = [max(0, (total-length)/2)]
    results = []
    for i, start in enumerate(sorted(chosen), 1):
        out = OUTPUTS / f"{job}_short_{i}.mp4"
        # Center crop to vertical. Scale to fill 1080x1920; subtitles can be added
        # when Whisper is installed/configured in a later extension.
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        run(["ffmpeg","-y","-ss",str(start),"-i",str(src),"-t",str(min(length,total-start)),
             "-vf",vf,"-r","30","-c:v","libx264","-preset","veryfast","-crf","23",
             "-c:a","aac","-b:a","128k","-movflags","+faststart",str(out)])
        results.append({"name":out.name,"url":f"/outputs/{out.name}","start_seconds":round(start,1),
                        "duration_seconds":round(min(length,total-start),1)})
    return results

@app.get("/api/download/{filename}")
def download(filename: str):
    path = OUTPUTS / Path(filename).name
    if not path.exists(): raise HTTPException(404, "Clip not found")
    return FileResponse(path, media_type="video/mp4", filename=path.name)
