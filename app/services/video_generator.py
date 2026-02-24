"""
Video generation service: creates Instagram-style vinyl music videos (1080x1350px).
Uses Pillow for frame rendering and FFmpeg for video encoding.

Optimized: pre-renders one rotation cycle of vinyl frames, reuses them.
"""
import math
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from app.services.image_processor import (
    extract_dominant_colors,
    create_vinyl_image,
)


# Video dimensions (Instagram square)
WIDTH = 1080
HEIGHT = 1080
FPS = 30
VINYL_RPM = 33.333  # Standard LP speed

# Vinyl sizing - full width, centered
VINYL_SIZE = WIDTH
VINYL_X = 0
VINYL_Y = 0


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get the best available font."""
    font_candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    if bold:
        bold_candidates = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSDisplay.ttf",
        ]
        for font_path in bold_candidates:
            try:
                return ImageFont.truetype(font_path, size, index=1)
            except (OSError, IndexError):
                pass

    for font_path in font_candidates:
        try:
            return ImageFont.truetype(font_path, size)
        except (OSError, IndexError):
            pass

    return ImageFont.load_default()


def _prerender_rotation_cycle(vinyl_base: Image.Image) -> list:
    """
    Pre-render all unique rotation frames for one full rotation.
    At 33⅓ RPM / 30fps, one rotation = 54 frames.
    Returns a list of RGB byte buffers ready to composite.
    """
    degrees_per_second = VINYL_RPM * 6  # RPM * 360/60
    degrees_per_frame = degrees_per_second / FPS

    # Number of frames for one full 360° rotation
    frames_per_rotation = int(math.ceil(360.0 / degrees_per_frame))

    rotated_frames = []
    for i in range(frames_per_rotation):
        angle = -(i * degrees_per_frame) % 360
        rotated = vinyl_base.rotate(angle, resample=Image.BICUBIC, expand=False)
        rotated_frames.append(rotated)

    return rotated_frames


def generate_video(
    audio_path: str,
    cover_path: Optional[str],
    artist: str,
    title: str,
    start_sec: float,
    end_sec: float,
    output_path: str,
    progress_callback=None,
    benchmark_session=None,
) -> str:
    """
    Generate a vinyl-style Instagram video.
    Optimized: pre-renders one rotation cycle, black background, minimal per-frame work.
    """
    duration = end_sec - start_sec
    total_frames = int(duration * FPS)

    # Create vinyl disc image (1080x1080 RGBA)
    vinyl_base = create_vinyl_image(cover_path, VINYL_SIZE)

    # Pre-render all unique rotation positions (~54 frames)
    if progress_callback:
        progress_callback(2)

    rotation_cycle = _prerender_rotation_cycle(vinyl_base)
    cycle_length = len(rotation_cycle)

    if progress_callback:
        progress_callback(5)

    # Pre-render the base frame: solid black (reused every frame)
    base_rgb = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))

    # Set up FFmpeg process
    tmp_dir = tempfile.mkdtemp(prefix="sonivo_")

    try:
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{WIDTH}x{HEIGHT}",
            "-r", str(FPS),
            "-i", "pipe:0",
            "-ss", str(start_sec),
            "-t", str(duration),
            "-i", str(audio_path),
            # High quality for Instagram
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-profile:v", "high",
            "-level:v", "4.0",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "256k",
            "-ar", "48000",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path)
        ]

        ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Feed benchmark session the FFmpeg PID
        if benchmark_session is not None:
            benchmark_session.set_ffmpeg_pid(
                ffmpeg_proc.pid,
                cmdline=" ".join(ffmpeg_cmd),
            )

        # Generate and pipe frames
        # The per-frame work is now: copy base → paste pre-rendered vinyl → tobytes
        for frame_idx in range(total_frames):
            # Pick the pre-rendered rotation frame
            vinyl_rotated = rotation_cycle[frame_idx % cycle_length]

            # Copy base frame and composite vinyl
            frame = base_rgb.copy()
            frame.paste(
                vinyl_rotated.convert("RGB"),
                (VINYL_X, VINYL_Y),
                vinyl_rotated.split()[3],  # alpha channel as mask
            )

            # Write raw bytes to FFmpeg
            ffmpeg_proc.stdin.write(frame.tobytes())

            # Progress callback every 10 frames
            if progress_callback and frame_idx % 10 == 0:
                # 5-90% for frame generation, 90-100% for FFmpeg finalization
                percent = 5 + int((frame_idx / total_frames) * 85)
                progress_callback(percent)

        # Close stdin and wait for FFmpeg to finish encoding
        ffmpeg_proc.stdin.close()
        if progress_callback:
            progress_callback(92)

        ffmpeg_proc.wait(timeout=900)

        if ffmpeg_proc.returncode != 0:
            stderr = ffmpeg_proc.stderr.read().decode()
            if benchmark_session is not None:
                benchmark_session.set_exit_code(ffmpeg_proc.returncode)
            raise RuntimeError(f"FFmpeg error: {stderr[-500:]}")

        if benchmark_session is not None:
            benchmark_session.set_exit_code(0)
            benchmark_session.set_output_path(str(output_path))

        if progress_callback:
            progress_callback(100)

        return str(output_path)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def generate_video_batch(
    tasks: list,
    output_dir: str,
) -> list:
    """Generate multiple videos."""
    results = []
    for i, task in enumerate(tasks):
        output_path = os.path.join(output_dir, task["filename"])
        try:
            generate_video(
                audio_path=task["audio_path"],
                cover_path=task.get("cover_path"),
                artist=task.get("artist", "Unknown"),
                title=task.get("title", "Unknown"),
                start_sec=task.get("start_sec", 0),
                end_sec=task.get("end_sec", 30),
                output_path=output_path,
            )
            results.append({"filename": task["filename"], "status": "success", "path": output_path})
        except Exception as e:
            results.append({"filename": task["filename"], "status": "error", "error": str(e)})

    return results
