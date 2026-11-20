# CLIPX AI — V0.01

A mobile-friendly gaming-video clip generator prototype.

## What works in this version
- Android-friendly web interface
- Upload an authorized gameplay video
- Scan audio loudness across the video to find candidate high-energy moments
- Export up to 10 vertical 9:16 MP4 clips, 30–60 seconds each
- Download generated clips

## Important limitations
This is a real processing prototype, not the fully AI-powered product yet.
- It uses audio intensity as a rough highlight signal, not semantic understanding of gameplay.
- It does **not** yet generate subtitles, understand game events, or publish to YouTube.
- A URL field is intentionally not implemented as a downloader. A public YouTube URL does not grant download/republication rights, and the YouTube Data API does not provide arbitrary video downloads. Upload your own file or use a direct media source you are authorized to process.
- Free hosting may sleep, limit upload size, or lack enough memory/CPU for long gameplay files. Large jobs may fail on free tiers.

## Run locally
Requires Python 3.11+ and FFmpeg/FFprobe installed.

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000`.

## Deploy
1. Create a GitHub repository and upload this project.
2. Create a Docker web service on a hosting provider that supports Docker.
3. Connect the repository and deploy.
4. Check `/api/health`.
5. Test with a short gameplay recording first.

The included `render.yaml` is a deployment starting point, not a guarantee of free hosting availability. Check current provider limits.

## Roadmap
- V0.02: speech transcription and word-level subtitle timing (Whisper)
- V0.03: scene-change + audio + visual-event ranking
- V0.04: facecam/gameplay-aware vertical reframing and subtitle styling
- V0.05: authenticated YouTube upload of user-owned clips
- V1.0: job queue, progress tracking, storage cleanup, retries and scheduling

## Copyright and safety
Only process footage you own or have permission to edit and publish. Review each clip before publishing. Automated selection can produce irrelevant or misleading cuts.
