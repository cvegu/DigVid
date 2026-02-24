#!/usr/bin/env python3
"""
Benchmark runner for Sonivo video generation pipeline.

Generates synthetic audio fixtures (sine waves via FFmpeg), then runs
the real generate_video() function with BenchmarkSession instrumentation.

Usage:
    python benchmarks/run_benchmarks.py
"""
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.benchmarking import BenchmarkSession
from app.services.video_generator import generate_video

BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks"
RESULTS_DIR = BENCHMARKS_DIR / "results"
FIXTURES_DIR = BENCHMARKS_DIR / "fixtures"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# Test durations in seconds
DURATIONS = [15, 30, 60, 120, 300]
WARMUP_RUNS = 1
MEASURED_RUNS = 5


def collect_system_info() -> dict:
    """Gather machine info and save to system_info.json."""
    info = {
        "os": f"{platform.system()} {platform.release()}",
        "kernel": platform.version(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
    }

    # CPU
    try:
        import psutil
        info["cpu_physical_cores"] = psutil.cpu_count(logical=False)
        info["cpu_logical_cores"] = psutil.cpu_count(logical=True)
        info["ram_total_gb"] = round(psutil.virtual_memory().total / (1024**3), 1)
    except ImportError:
        pass

    # CPU model (macOS)
    try:
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            info["cpu_model"] = result.stdout.strip()
    except Exception:
        pass

    # If sysctl failed (Apple Silicon), try hw.chip
    if "cpu_model" not in info:
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.model"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                info["cpu_model"] = result.stdout.strip()
        except Exception:
            pass

    # FFmpeg version
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            info["ffmpeg_version"] = result.stdout.split("\n")[0].strip()
    except Exception:
        info["ffmpeg_version"] = "not found"

    # GPU (nvidia-smi)
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            info["gpu_name"] = result.stdout.strip()
    except Exception:
        info["gpu_name"] = "not available (no NVIDIA GPU detected)"

    # Disk info (best-effort)
    try:
        import psutil
        disk = psutil.disk_usage("/")
        info["disk_total_gb"] = round(disk.total / (1024**3), 1)
        info["disk_free_gb"] = round(disk.free / (1024**3), 1)
    except Exception:
        pass

    return info


def generate_fixture(duration_sec: int) -> Path:
    """Generate a synthetic audio WAV file (sine wave) of given duration."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    filepath = FIXTURES_DIR / f"sine_{duration_sec}s.wav"

    if filepath.exists():
        print(f"  ✓ Fixture exists: {filepath.name}")
        return filepath

    print(f"  Generating {duration_sec}s sine wave fixture...")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration_sec}",
        "-ar", "48000",
        "-ac", "2",
        str(filepath),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    print(f"  ✓ Created: {filepath.name}")
    return filepath


def generate_cover_fixture() -> Path:
    """Generate a simple cover image fixture."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    cover_path = FIXTURES_DIR / "test_cover.png"

    if cover_path.exists():
        return cover_path

    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (800, 800), (30, 30, 40))
        draw = ImageDraw.Draw(img)
        # Draw some concentric circles for visual interest
        for i in range(20):
            r = 400 - i * 20
            color = (50 + i * 8, 30 + i * 5, 80 + i * 7)
            draw.ellipse(
                [400 - r, 400 - r, 400 + r, 400 + r],
                outline=color, width=2,
            )
        img.save(str(cover_path))
    except ImportError:
        # Fallback: generate via FFmpeg
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i",
            "color=c=0x1E1E28:s=800x800:d=1",
            "-frames:v", "1",
            str(cover_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)

    return cover_path


def run_single_benchmark(
    audio_path: Path,
    cover_path: Path,
    duration: int,
    run_label: str,
) -> dict:
    """Run a single benchmark and return metrics."""
    output_filename = f"bench_{duration}s_{run_label}.mp4"
    output_path = OUTPUTS_DIR / output_filename

    # Clean any previous output
    if output_path.exists():
        output_path.unlink()

    session = BenchmarkSession(
        segment_duration=float(duration),
        audio_duration=float(duration),
        label=run_label,
        save_results=True,
    )

    with session:
        generate_video(
            audio_path=str(audio_path),
            cover_path=str(cover_path),
            artist="Benchmark",
            title=f"Test {duration}s",
            start_sec=0,
            end_sec=float(duration),
            output_path=str(output_path),
            benchmark_session=session,
        )

    # Clean up output file to save disk space
    if output_path.exists():
        output_path.unlink()

    return session.metrics


def main():
    print("=" * 60)
    print("Sonivo Benchmark Runner")
    print("=" * 60)

    # Ensure directories exist
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Collect system info
    print("\n[1/4] Collecting system information...")
    sys_info = collect_system_info()
    sys_info_path = BENCHMARKS_DIR / "system_info.json"
    with open(sys_info_path, "w") as f:
        json.dump(sys_info, f, indent=2)
    print(f"  ✓ Saved to {sys_info_path}")
    print(f"  CPU: {sys_info.get('cpu_model', 'unknown')}")
    print(f"  Cores: {sys_info.get('cpu_physical_cores', '?')} physical / {sys_info.get('cpu_logical_cores', '?')} logical")
    print(f"  RAM: {sys_info.get('ram_total_gb', '?')} GB")
    print(f"  FFmpeg: {sys_info.get('ffmpeg_version', '?')}")

    # Step 2: Generate fixtures
    print("\n[2/4] Preparing audio fixtures...")
    fixtures = {}
    for dur in DURATIONS:
        fixtures[dur] = generate_fixture(dur)
    cover = generate_cover_fixture()
    print(f"  ✓ Cover image ready: {cover.name}")

    # Step 3: Clean old results
    print("\n[3/4] Cleaning previous results...")
    old_count = 0
    for f in RESULTS_DIR.glob("*.json"):
        f.unlink()
        old_count += 1
    if old_count:
        print(f"  Removed {old_count} old result files")
    else:
        print("  No previous results found")

    # Step 4: Run benchmarks
    print("\n[4/4] Running benchmarks...")
    total_runs = len(DURATIONS) * (WARMUP_RUNS + MEASURED_RUNS)
    current_run = 0

    for dur in DURATIONS:
        audio_path = fixtures[dur]
        print(f"\n  ── Duration: {dur}s ──")

        # Warm-up
        for w in range(WARMUP_RUNS):
            current_run += 1
            print(f"    [{current_run}/{total_runs}] Warm-up {w+1}... ", end="", flush=True)
            try:
                m = run_single_benchmark(audio_path, cover, dur, f"warmup_{w+1}")
                print(f"✓ {m['total_job_time_seconds']:.1f}s")
            except Exception as e:
                print(f"✗ Error: {e}")
            # Delete warm-up result files (they were saved but we don't need them)
            for f in RESULTS_DIR.glob(f"*_{dur}s_warmup_*.json"):
                f.unlink()

        # Measured runs
        for r in range(MEASURED_RUNS):
            current_run += 1
            run_label = f"run_{r+1}"
            print(f"    [{current_run}/{total_runs}] Run {r+1}/{MEASURED_RUNS}... ", end="", flush=True)
            try:
                m = run_single_benchmark(audio_path, cover, dur, run_label)
                print(
                    f"✓ {m['total_job_time_seconds']:.1f}s | "
                    f"CPU {m['avg_cpu_percent']:.0f}% | "
                    f"Peak RAM {m['peak_memory_mb']:.0f}MB | "
                    f"Output {m['output_video_size_mb']:.1f}MB"
                )
            except Exception as e:
                print(f"✗ Error: {e}")
            # Small pause between runs
            time.sleep(1)

    # Summary
    result_files = list(RESULTS_DIR.glob("*.json"))
    print(f"\n{'=' * 60}")
    print(f"Benchmark complete! {len(result_files)} result files saved.")
    print(f"Results: {RESULTS_DIR}")
    print(f"System info: {sys_info_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
