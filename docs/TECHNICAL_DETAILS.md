# Technical Details — DigVid / Sonivo

This document explains how this repository works from a technical perspective. It assumes no prior knowledge of the project.

---

## What This Repo Does

**Sonivo** (also referred to as DigVid in the workspace) is a **web application that generates short music videos for Instagram** from audio files. You upload a song (e.g. MP3), optionally edit metadata and choose a segment, and the app produces a vertical video (1080×1080 px) with a **spinning vinyl record** (album art on the disc) on a black background, synced to the selected audio. It supports **single-track** and **batch** (up to 10 tracks) modes.

---

## Tech Stack (High Level)

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+, [FastAPI](https://fastapi.tiangolo.com/) |
| **Server** | [Uvicorn](https://www.uvicorn.org/) (ASGI) |
| **Templates** | [Jinja2](https://jinja.palletsprojects.com/) (single page: `index.html`) |
| **Frontend** | Vanilla JavaScript, no framework; CSS for layout and theme |
| **Audio metadata** | [Mutagen](https://mutagen.readthedocs.io/) (MP3, FLAC, M4A, OGG, etc.) |
| **Image processing** | [Pillow (PIL)](https://pillow.readthedocs.io/) |
| **Video/audio processing** | [FFmpeg](https://ffmpeg.org/) (CLI, must be installed on the system) |
| **Numerics** | [NumPy](https://numpy.org/) (waveform peaks, image arrays) |

The app does **not** use a database: uploads and outputs are stored as files on disk; job progress is kept in memory.

---

## Repository Layout

```
DigVid/
├── app/
│   ├── main.py                 # FastAPI app, static/template mounts, CORS
│   ├── routes/
│   │   └── video.py            # All API endpoints (upload, waveform, generate, progress, batch, download)
│   ├── services/
│   │   ├── audio_processor.py  # Metadata extraction, waveform peaks, audio segment extraction
│   │   ├── image_processor.py # Dominant colors, vinyl disc image, background frame (gradient)
│   │   ├── video_generator.py # Main video generation (Pillow + FFmpeg)
│   │   └── benchmarking.py    # Optional benchmarking of video generation
│   └── templates/
│       └── index.html         # Single-page UI (Single / Batch tabs)
├── static/
│   ├── css/style.css          # Styles (dark theme, layout)
│   ├── js/app.js              # Frontend logic (upload, waveform, preview, generate, progress)
│   └── fonts/                 # Font assets (e.g. Inter)
├── uploads/                   # Uploaded audio + extracted/custom covers (gitignored)
├── outputs/                   # Generated MP4s and batch ZIP (gitignored)
├── docs/                      # Documentation (README, TECHNICAL_DETAILS, DEPLOYMENT, benchmark_report)
├── benchmarks/                # Scripts and results for performance runs
├── requirements.txt           # Python dependencies
├── start.sh                   # Start script (venv, ffmpeg check, uvicorn)
└── README.md                  # User-facing readme (project root)
```

---

## How a Request Flows (Single Video)

1. **Upload**  
   User drops/selects an audio file → `POST /api/upload` → file is saved under `uploads/` with a short UUID prefix. Backend uses **Mutagen** to read tags (artist, title, album, cover art, duration, BPM) and, if present, extracts cover to `uploads/{id}_cover.*`. Response includes `file_id`, metadata, and `cover_url` for the UI.

2. **Waveform**  
   Frontend requests `GET /api/waveform/{file_id}`. **audio_processor** runs FFmpeg to decode audio to mono 8 kHz float PCM, then uses NumPy to compute peak values over ~800 bins and returns a normalized list. The UI draws this in a canvas and lets the user set start/end (segment).

3. **Preview (optional)**  
   `GET /api/preview-audio/{file_id}` serves the uploaded file so the user can play it (and the segment) in the browser.

4. **Generate**  
   User clicks “Generate Video” → `POST /api/generate` with `file_id`, artist, title, start/end seconds, optional custom cover. Backend:
   - Resolves the audio file and any cover path.
   - Creates a **job** in an in-memory dict (`_jobs[job_id]`) and starts a **background thread** that calls `video_generator.generate_video(...)` with a progress callback.
   - Returns `job_id` immediately.

5. **Progress**  
   Frontend polls `GET /api/progress/{job_id}` until `status` is `done` or `error`. Progress is updated by the generator (e.g. 0–100%) and stored in `_jobs[job_id]`. When done, the response includes `result.download_url` (e.g. `/outputs/Artist - Title.mp4`).

6. **Download**  
   User opens the download URL or uses `GET /api/download/{filename}`; files are served from the `outputs/` directory mounted by FastAPI.

---

## Backend in More Detail

### Entry point (`app/main.py`)

- Builds paths for `uploads/`, `outputs/`, `static/`, `templates/`.
- Creates the FastAPI app, adds CORS middleware (all origins for dev), mounts:
  - `/static` → `static/`
  - `/uploads` → `uploads/`
  - `/outputs` → `outputs/`
- Uses Jinja2 to render `index.html` at `/`.
- Includes the API router under `/api` (from `app.routes.video`).

### API routes (`app/routes/video.py`)

- **Upload**: Validates extension (e.g. `.mp3`, `.wav`, `.flac`, `.m4a`, …), saves file, calls `extract_metadata()`, renames cover to `{file_id}_cover.*`, returns metadata + `cover_url`.
- **Waveform**: Finds file by `file_id` prefix in `uploads/`, calls `generate_waveform_peaks()`, returns `{ peaks: [...] }`.
- **Preview**: Serves the audio file with `FileResponse` and `Accept-Ranges` for seeking.
- **Generate**: Validates audio, optionally saves custom cover, creates job, starts thread running `generate_video(..., progress_callback=...)`, returns `job_id`.
- **Progress**: Reads `_jobs[job_id]`, returns `progress`, `status`, and optional `result` (download URL or error).
- **Batch generate**: `POST /api/batch/generate` with JSON body (list of tracks). Runs `generate_video_batch()` sequentially, then optionally builds a ZIP of all outputs + `tracklist.txt` and returns per-file results + `zip_url`.
- **Download**: Sends the file from `outputs/` with the requested filename.

File lookup by `file_id` is done by scanning `uploads/` for a file whose name starts with the ID and has an audio extension (excluding cover/custom-cover files).

### Audio service (`app/services/audio_processor.py`)

- **extract_metadata(filepath)**: Uses Mutagen’s `File()` and type-specific handling (ID3 for MP3, MP4 tags for M4A, Vorbis for FLAC/OGG) to get artist, title, album, duration, BPM; extracts embedded cover to a file and sets `cover_path`.
- **generate_waveform_peaks(filepath, num_points=800)**: FFmpeg outputs raw float PCM; NumPy chunks it into `num_points` bins, takes max absolute value per bin, normalizes to [0, 1].
- **extract_audio_segment(filepath, start_sec, end_sec, output_path)**: FFmpeg `-ss` / `-t` with `-acodec copy` to produce a clip without re-encoding.

### Image service (`app/services/image_processor.py`)

- **extract_dominant_colors(image_path, n=5)**: Resize to 150×150, quantize to `n` colors (PIL median cut), return RGB tuples sorted by luminance (for potential background use; current video uses a fixed black background).
- **create_vinyl_image(cover_path, size)**: Builds a 1080×1080 RGBA “vinyl”: circular mask over resized cover, overlay of circular “groove” lines, center hole, subtle shine. Used as the spinning disc.
- **create_background_frame(...)**: Builds a single gradient frame (e.g. for animated backgrounds); not used in the current minimal black-background pipeline but available for future use.

### Video service (`app/services/video_generator.py`)

- **Output**: 1080×1080, 30 fps, black background, spinning vinyl only (no text overlay in the current code you have).
- **Optimization**: One full rotation at 33⅓ RPM is 54 frames at 30 fps. The code **pre-renders** those 54 rotated vinyl images once, then for each frame of the video only:
  - Copies a black base image,
  - Pastes the pre-rendered frame `rotation_cycle[frame_idx % 54]` with alpha,
  - Writes raw RGB bytes to FFmpeg’s stdin.
- **Encoding**: FFmpeg is launched with `-f rawvideo -pix_fmt rgb24 -s 1080x1080 -r 30 -i pipe:0`, and the same audio file with `-ss`/`-t` for the segment. Video is encoded with libx264 (e.g. preset medium, CRF 20), audio as AAC; output is MP4 with `-movflags +faststart`.
- **Progress**: Callback is invoked every 10 frames (and at start/end) to update the in-memory job progress (e.g. 5–90% for frames, 92–100% for FFmpeg).
- **Batch**: `generate_video_batch()` runs `generate_video()` in a loop; no parallelization (one video at a time).

---

## Frontend (High Level)

- **Single HTML page** (`app/templates/index.html`): Two tabs, “Single” and “Batch”. Single: drop zone → editor (metadata, cover, waveform, start/end, play, generate, progress, result + download). Batch: multi-file drop, list of tracks with per-track metadata and segment, “Generate Videos”, progress, list of results + ZIP download.
- **JS** (`static/js/app.js`): State object for `mode`, `single` (fileId, segment, peaks, audio context for preview), and `batch` (tracks, playing index). Functions for upload, fetching waveform, drawing waveform and selection handles, audio preview (Web Audio API or `<audio>`), form submit to `/api/generate`, polling `/api/progress`, and batch submit to `/api/batch/generate`. No build step; plain ES6 in the browser.
- **CSS** (`static/css/style.css`): Dark theme, layout for cards, waveform, buttons, progress bar, etc.

---

## External Dependencies

- **FFmpeg**: Must be on the system `PATH`. Used for:
  - Waveform: decode audio to raw PCM.
  - Segment extraction (if used).
  - Video encoding: raw frames from stdin + audio file → MP4 (H.264 + AAC).

- **Python**: 3.11+ recommended. All app dependencies are in `requirements.txt` (FastAPI, uvicorn, python-multipart, jinja2, mutagen, Pillow, numpy, aiofiles).

---

## Running the App

1. Install Python 3.11+, FFmpeg, and create a virtualenv.
2. `pip install -r requirements.txt`
3. `./start.sh` (or `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`).
4. Open `http://localhost:8000`.

Uploads go to `uploads/`, outputs to `outputs/`. Job state is in-memory only; restarting the server clears progress.

---

## Optional: Benchmarks

The `benchmarks/` folder contains scripts and result files for timing video generation (e.g. different segment lengths, multiple runs). The video generator can accept an optional `benchmark_session` and report FFmpeg PID, exit code, and output path for profiling. This is separate from the normal UI flow. See [benchmark_report.md](benchmark_report.md) for results.

---

## Summary Table

| Topic | Detail |
|-------|--------|
| **Purpose** | Generate Instagram-style vertical music videos (spinning vinyl + audio) from uploaded tracks |
| **Backend** | FastAPI (Python), Uvicorn, no DB |
| **Video pipeline** | Pillow (vinyl frames) → raw RGB → FFmpeg (H.264 + AAC) |
| **Audio metadata** | Mutagen; waveform via FFmpeg + NumPy |
| **Frontend** | One Jinja2 page, vanilla JS, CSS |
| **Concurrency** | Single-video generation in a background thread; batch is sequential |
| **Storage** | Files in `uploads/` and `outputs/`; job progress in memory |

If you want more detail on a specific file or function, say which one and we can go line by line.
