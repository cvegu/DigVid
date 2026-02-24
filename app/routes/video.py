"""
API routes for video generation.
Uses background threads for video generation so progress polling works.
"""
import os
import uuid
import json
import zipfile
import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.services.audio_processor import extract_metadata, generate_waveform_peaks, extract_audio_segment
from app.services.video_generator import generate_video, generate_video_batch

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

# In-memory progress tracking: job_id -> {progress: int, status: str, result: dict|None}
_jobs = {}

# Supported audio formats
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma", ".aif", ".aiff"}


@router.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    """Upload an audio file and extract metadata."""
    ext = Path(file.filename).suffix.lower()
    if ext not in AUDIO_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format: {ext}. Supported: {', '.join(AUDIO_EXTENSIONS)}")

    file_id = str(uuid.uuid4())[:8]
    safe_name = f"{file_id}{ext}"
    filepath = UPLOAD_DIR / safe_name

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        metadata = extract_metadata(str(filepath))

        cover_url = None
        if metadata.get("cover_path"):
            cover_file = Path(metadata["cover_path"])
            new_cover = UPLOAD_DIR / f"{file_id}_cover{cover_file.suffix}"
            if cover_file != new_cover:
                cover_file.rename(new_cover)
            cover_url = f"/uploads/{new_cover.name}"
            metadata["cover_path"] = str(new_cover)

        return {
            "file_id": file_id,
            "filename": file.filename,
            "filepath": str(filepath),
            "artist": metadata["artist"],
            "title": metadata["title"],
            "album": metadata["album"],
            "duration": metadata["duration"],
            "bpm": metadata.get("bpm"),
            "cover_url": cover_url,
            "cover_path": metadata.get("cover_path"),
        }

    except Exception as e:
        filepath.unlink(missing_ok=True)
        raise HTTPException(500, f"Error processing file: {str(e)}")


@router.get("/waveform/{file_id}")
async def get_waveform(file_id: str):
    """Get waveform peak data for visualization."""
    filepath = _find_upload(file_id)
    if not filepath:
        raise HTTPException(404, "File not found")

    peaks = generate_waveform_peaks(str(filepath))
    return {"peaks": peaks}


@router.get("/preview-audio/{file_id}")
async def preview_audio(file_id: str):
    """Serve the uploaded audio file for preview playback."""
    filepath = _find_upload(file_id)
    if not filepath:
        raise HTTPException(404, "File not found")

    return FileResponse(
        str(filepath),
        media_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes"},
    )


@router.post("/generate")
async def generate_single_video(
    file_id: str = Form(...),
    artist: str = Form("Unknown Artist"),
    title: str = Form("Unknown Title"),
    start_sec: float = Form(0),
    end_sec: float = Form(30),
    cover_path: Optional[str] = Form(None),
    cover_file: Optional[UploadFile] = File(None),
):
    """Start video generation in a background thread. Returns job_id for progress polling."""
    # Find audio file
    audio_path = _find_upload(file_id)
    if not audio_path:
        raise HTTPException(404, "Audio file not found")

    # Handle custom cover upload
    actual_cover_path = cover_path
    if cover_file and cover_file.filename:
        cover_ext = Path(cover_file.filename).suffix.lower()
        cover_save_path = UPLOAD_DIR / f"{file_id}_custom_cover{cover_ext}"
        with open(cover_save_path, "wb") as f:
            content = await cover_file.read()
            f.write(content)
        actual_cover_path = str(cover_save_path)

    # Generate output filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title).strip()
    safe_artist = "".join(c if c.isalnum() or c in " -_" else "" for c in artist).strip()
    output_filename = f"{safe_artist} - {safe_title}.mp4"
    output_path = OUTPUT_DIR / output_filename

    # Create job for tracking
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {"progress": 0, "status": "processing", "result": None}

    def on_progress(pct):
        _jobs[job_id]["progress"] = pct

    def run_generation():
        try:
            generate_video(
                audio_path=str(audio_path),
                cover_path=actual_cover_path,
                artist=artist,
                title=title,
                start_sec=start_sec,
                end_sec=end_sec,
                output_path=str(output_path),
                progress_callback=on_progress,
            )
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["progress"] = 100
            _jobs[job_id]["result"] = {
                "filename": output_filename,
                "download_url": f"/outputs/{output_filename}",
            }
        except Exception as e:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["result"] = {"error": str(e)}

    # Start generation in background thread
    thread = threading.Thread(target=run_generation, daemon=True)
    thread.start()

    return {"job_id": job_id, "status": "started"}


@router.get("/progress/{job_id}")
async def get_progress(job_id: str):
    """Get generation progress for a job."""
    job = _jobs.get(job_id)
    if not job:
        return {"progress": -1, "status": "not_found"}

    response = {
        "progress": job["progress"],
        "status": job["status"],
    }

    # Include result if done or errored
    if job["status"] in ("done", "error") and job["result"]:
        response["result"] = job["result"]
        # Clean up job after client gets the result (give some grace period)

    return response


@router.post("/batch/generate")
async def generate_batch(data: str = Form(...)):
    """Generate multiple videos."""
    try:
        tracks = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON data")

    if len(tracks) > 10:
        raise HTTPException(400, "Maximum 10 tracks allowed")

    tasks = []
    for track in tracks:
        file_id = track.get("file_id")
        audio_path = _find_upload(file_id)
        if not audio_path:
            continue

        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in track.get("title", "Unknown")).strip()
        safe_artist = "".join(c if c.isalnum() or c in " -_" else "" for c in track.get("artist", "Unknown")).strip()
        filename = f"{safe_artist} - {safe_title}.mp4"

        tasks.append({
            "audio_path": str(audio_path),
            "cover_path": track.get("cover_path"),
            "artist": track.get("artist", "Unknown"),
            "title": track.get("title", "Unknown"),
            "start_sec": track.get("start_sec", 0),
            "end_sec": track.get("end_sec", 30),
            "filename": filename,
        })

    results = generate_video_batch(tasks, str(OUTPUT_DIR))

    successful = [r for r in results if r["status"] == "success"]
    zip_filename = None

    if len(successful) > 1:
        zip_filename = "Sonivo_batch.zip"
        zip_path = OUTPUT_DIR / zip_filename
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for r in successful:
                zf.write(r["path"], os.path.basename(r["path"]))
            tracklist = "\n".join(
                f"{i+1}. {os.path.splitext(os.path.basename(r['path']))[0]}"
                for i, r in enumerate(successful)
            )
            zf.writestr("tracklist.txt", tracklist)

    return {
        "results": [
            {"filename": r["filename"], "status": r["status"],
             "download_url": f"/outputs/{r['filename']}" if r["status"] == "success" else None,
             "error": r.get("error")}
            for r in results
        ],
        "zip_url": f"/outputs/{zip_filename}" if zip_filename else None,
    }


@router.get("/download/{filename}")
async def download_file(filename: str):
    """Download a generated video."""
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(filepath), filename=filename)


def _find_upload(file_id: str) -> Optional[Path]:
    """Find an uploaded file by its ID prefix."""
    for f in UPLOAD_DIR.iterdir():
        if f.name.startswith(file_id) and not f.name.endswith(("_cover.jpg", "_cover.png", "_custom_cover.jpg", "_custom_cover.png")):
            if f.suffix.lower() in AUDIO_EXTENSIONS:
                return f
    return None
