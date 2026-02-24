"""
Audio processing service: metadata extraction, waveform generation, segment extraction.
"""
import os
import json
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.id3 import ID3
from mutagen import File as MutagenFile


def extract_metadata(filepath: str) -> dict:
    """
    Extract metadata (artist, title, album, cover art, duration, bpm) from an audio file.
    Returns a dict with all available metadata.
    """
    filepath = Path(filepath)
    audio = MutagenFile(str(filepath))

    if audio is None:
        raise ValueError(f"Could not read audio file: {filepath}")

    metadata = {
        "artist": "Unknown Artist",
        "title": filepath.stem,
        "album": "Unknown Album",
        "duration": 0,
        "bpm": None,
        "cover_path": None,
    }

    # Duration
    if audio.info:
        metadata["duration"] = round(audio.info.length, 2)

    # Extract tags based on file type
    if isinstance(audio, MP3) or hasattr(audio, 'tags') and audio.tags:
        tags = audio.tags
        if tags:
            _extract_id3_tags(tags, metadata, filepath)
    elif isinstance(audio, MP4):
        _extract_mp4_tags(audio, metadata, filepath)
    elif isinstance(audio, FLAC):
        _extract_vorbis_tags(audio, metadata, filepath)
    elif isinstance(audio, OggVorbis):
        _extract_vorbis_tags(audio, metadata, filepath)

    return metadata


def _extract_id3_tags(tags, metadata: dict, filepath: Path):
    """Extract metadata from ID3 tags (MP3)."""
    # Artist
    if "TPE1" in tags:
        metadata["artist"] = str(tags["TPE1"])
    elif "TPE2" in tags:
        metadata["artist"] = str(tags["TPE2"])

    # Title
    if "TIT2" in tags:
        metadata["title"] = str(tags["TIT2"])

    # Album
    if "TALB" in tags:
        metadata["album"] = str(tags["TALB"])

    # BPM
    if "TBPM" in tags:
        try:
            metadata["bpm"] = int(str(tags["TBPM"]))
        except (ValueError, TypeError):
            pass

    # Cover art
    for key in tags.keys():
        if key.startswith("APIC"):
            apic = tags[key]
            ext = "jpg" if "jpeg" in apic.mime else "png"
            cover_filename = f"{filepath.stem}_cover.{ext}"
            cover_dir = filepath.parent
            cover_path = cover_dir / cover_filename
            with open(cover_path, "wb") as f:
                f.write(apic.data)
            metadata["cover_path"] = str(cover_path)
            break


def _extract_mp4_tags(audio: MP4, metadata: dict, filepath: Path):
    """Extract metadata from MP4/M4A tags."""
    tags = audio.tags
    if not tags:
        return

    if "\xa9ART" in tags:
        metadata["artist"] = tags["\xa9ART"][0]
    if "\xa9nam" in tags:
        metadata["title"] = tags["\xa9nam"][0]
    if "\xa9alb" in tags:
        metadata["album"] = tags["\xa9alb"][0]
    if "tmpo" in tags:
        metadata["bpm"] = int(tags["tmpo"][0])

    # Cover art
    if "covr" in tags and tags["covr"]:
        cover_data = bytes(tags["covr"][0])
        cover_filename = f"{filepath.stem}_cover.jpg"
        cover_path = filepath.parent / cover_filename
        with open(cover_path, "wb") as f:
            f.write(cover_data)
        metadata["cover_path"] = str(cover_path)


def _extract_vorbis_tags(audio, metadata: dict, filepath: Path):
    """Extract metadata from Vorbis comments (FLAC, OGG)."""
    if "artist" in audio:
        metadata["artist"] = audio["artist"][0]
    if "title" in audio:
        metadata["title"] = audio["title"][0]
    if "album" in audio:
        metadata["album"] = audio["album"][0]
    if "bpm" in audio:
        try:
            metadata["bpm"] = int(audio["bpm"][0])
        except (ValueError, TypeError):
            pass

    # Cover art for FLAC
    if isinstance(audio, FLAC) and audio.pictures:
        pic = audio.pictures[0]
        ext = "jpg" if "jpeg" in pic.mime else "png"
        cover_filename = f"{filepath.stem}_cover.{ext}"
        cover_path = filepath.parent / cover_filename
        with open(cover_path, "wb") as f:
            f.write(pic.data)
        metadata["cover_path"] = str(cover_path)


def generate_waveform_peaks(filepath: str, num_points: int = 800) -> list:
    """
    Generate waveform peak data using FFmpeg.
    Returns a list of normalized peak values (0.0 to 1.0) for rendering in canvas.
    """
    try:
        # Use FFmpeg to get raw PCM data
        cmd = [
            "ffmpeg", "-i", str(filepath),
            "-ac", "1",           # Mono
            "-ar", "8000",        # Low sample rate for speed
            "-f", "f32le",        # 32-bit float little-endian
            "-vn",                # No video
            "pipe:1"
        ]
        result = subprocess.run(
            cmd, capture_output=True, timeout=30
        )

        if result.returncode != 0:
            return [0.5] * num_points

        import numpy as np
        samples = np.frombuffer(result.stdout, dtype=np.float32)

        if len(samples) == 0:
            return [0.5] * num_points

        # Chunk samples into num_points groups
        chunk_size = max(1, len(samples) // num_points)
        peaks = []
        for i in range(num_points):
            start = i * chunk_size
            end = min(start + chunk_size, len(samples))
            if start >= len(samples):
                peaks.append(0.0)
            else:
                chunk = samples[start:end]
                peak = float(np.max(np.abs(chunk)))
                peaks.append(min(peak, 1.0))

        # Normalize to 0-1 range
        max_peak = max(peaks) if peaks else 1.0
        if max_peak > 0:
            peaks = [p / max_peak for p in peaks]

        return peaks

    except Exception as e:
        print(f"Error generating waveform: {e}")
        return [0.5] * num_points


def extract_audio_segment(filepath: str, start_sec: float, end_sec: float, output_path: str) -> str:
    """
    Extract a segment of audio using FFmpeg.
    Returns the output file path.
    """
    duration = end_sec - start_sec
    cmd = [
        "ffmpeg", "-y",
        "-i", str(filepath),
        "-ss", str(start_sec),
        "-t", str(duration),
        "-acodec", "copy",
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=30)
    return output_path
