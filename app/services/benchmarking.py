"""
Benchmark instrumentation module for DigVid video generation.

Monitors CPU, memory, I/O, and optionally GPU usage during video generation.
Produces per-job JSON metrics files.
"""
import json
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import psutil


BENCHMARKS_DIR = Path(__file__).resolve().parent.parent.parent / "benchmarks"
RESULTS_DIR = BENCHMARKS_DIR / "results"


class BenchmarkSession:
    """
    Context manager that monitors resource usage for a video generation job.

    Usage:
        with BenchmarkSession(segment_duration=30.0, audio_duration=180.0) as session:
            session.set_ffmpeg_pid(proc.pid)
            # ... generation work ...
        metrics = session.metrics
    """

    def __init__(
        self,
        segment_duration: float,
        audio_duration: float = 0.0,
        label: str = "",
        save_results: bool = True,
    ):
        self.segment_duration = segment_duration
        self.audio_duration = audio_duration or segment_duration
        self.label = label
        self.save_results = save_results

        self._ffmpeg_pid: Optional[int] = None
        self._ffmpeg_cmdline: str = ""
        self._exit_code: Optional[int] = None

        # Monitoring state
        self._samples_cpu: list[float] = []
        self._samples_mem: list[float] = []  # RSS in MB
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None

        # Timing
        self._start_time = 0.0
        self._end_time = 0.0

        # Process-level counters
        self._cpu_user = 0.0
        self._cpu_system = 0.0
        self._io_read_start = 0
        self._io_write_start = 0
        self._io_read_end = 0
        self._io_write_end = 0

        # GPU
        self._gpu_samples_util: list[float] = []
        self._gpu_samples_vram: list[float] = []
        self._has_nvidia = shutil.which("nvidia-smi") is not None

        # Output
        self.output_path: Optional[str] = None
        self.metrics: dict = {}

    def set_ffmpeg_pid(self, pid: int, cmdline: str = ""):
        """Set the FFmpeg process PID for targeted monitoring."""
        self._ffmpeg_pid = pid
        self._ffmpeg_cmdline = cmdline

    def set_exit_code(self, code: int):
        self._exit_code = code

    def set_output_path(self, path: str):
        self.output_path = path

    def __enter__(self):
        # Capture baseline I/O for current process
        proc = psutil.Process(os.getpid())
        try:
            io = proc.io_counters()
            self._io_read_start = io.read_bytes
            self._io_write_start = io.write_bytes
        except (psutil.AccessDenied, AttributeError):
            pass

        self._start_time = time.monotonic()
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._end_time = time.monotonic()
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

        # Capture final I/O
        proc = psutil.Process(os.getpid())
        try:
            io = proc.io_counters()
            self._io_read_end = io.read_bytes
            self._io_write_end = io.write_bytes
        except (psutil.AccessDenied, AttributeError):
            pass

        # Capture CPU times
        try:
            cpu_times = proc.cpu_times()
            self._cpu_user = cpu_times.user
            self._cpu_system = cpu_times.system
        except psutil.AccessDenied:
            pass

        self._build_metrics()

        if self.save_results:
            self._save()

        return False  # don't suppress exceptions

    def _monitor_loop(self):
        """Sample resource usage every 250ms."""
        proc = psutil.Process(os.getpid())

        while not self._stop_event.is_set():
            try:
                # CPU percent for process tree
                cpu = proc.cpu_percent(interval=0)
                children = proc.children(recursive=True)
                for child in children:
                    try:
                        cpu += child.cpu_percent(interval=0)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                self._samples_cpu.append(cpu)

                # Memory (RSS) for process tree
                mem = proc.memory_info().rss
                for child in children:
                    try:
                        mem += child.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                self._samples_mem.append(mem / (1024 * 1024))  # MB

                # GPU if available
                if self._has_nvidia:
                    self._sample_gpu()

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            self._stop_event.wait(0.25)

    def _sample_gpu(self):
        """Poll nvidia-smi for GPU stats."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                if len(parts) >= 2:
                    self._gpu_samples_util.append(float(parts[0].strip()))
                    self._gpu_samples_vram.append(float(parts[1].strip()))
        except Exception:
            pass

    def _build_metrics(self):
        """Build the final metrics dict from collected samples."""
        wall_time = self._end_time - self._start_time

        # Output file size
        output_size_mb = 0.0
        if self.output_path and os.path.exists(self.output_path):
            output_size_mb = os.path.getsize(self.output_path) / (1024 * 1024)

        self.metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "label": self.label,
            "audio_duration_seconds": self.audio_duration,
            "segment_duration_seconds": self.segment_duration,
            "total_job_time_seconds": round(wall_time, 3),
            "cpu_user_time_seconds": round(self._cpu_user, 3),
            "cpu_system_time_seconds": round(self._cpu_system, 3),
            "avg_cpu_percent": round(
                sum(self._samples_cpu) / len(self._samples_cpu), 1
            )
            if self._samples_cpu
            else 0,
            "peak_memory_mb": round(max(self._samples_mem), 1)
            if self._samples_mem
            else 0,
            "avg_memory_mb": round(
                sum(self._samples_mem) / len(self._samples_mem), 1
            )
            if self._samples_mem
            else 0,
            "disk_read_mb": round(
                (self._io_read_end - self._io_read_start) / (1024 * 1024), 2
            ),
            "disk_write_mb": round(
                (self._io_write_end - self._io_write_start) / (1024 * 1024), 2
            ),
            "output_video_size_mb": round(output_size_mb, 2),
            "ffmpeg_cmdline": self._ffmpeg_cmdline,
            "exit_code": self._exit_code if self._exit_code is not None else -1,
            "samples_collected": len(self._samples_cpu),
        }

        # GPU section
        if self._has_nvidia and self._gpu_samples_vram:
            self.metrics["gpu"] = {
                "peak_vram_mb": round(max(self._gpu_samples_vram), 1),
                "avg_gpu_utilization_percent": round(
                    sum(self._gpu_samples_util) / len(self._gpu_samples_util),
                    1,
                ),
            }
        else:
            self.metrics["gpu"] = "not available"

    def _save(self):
        """Save metrics JSON to benchmarks/results/."""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dur = int(self.segment_duration)
        label = self.label or "run"
        filename = f"{ts}_{dur}s_{label}.json"
        filepath = RESULTS_DIR / filename

        with open(filepath, "w") as f:
            json.dump(self.metrics, f, indent=2)
