#!/usr/bin/env python3
"""
Aggregate benchmark results and generate benchmark_report.md.

Usage:
    python benchmarks/aggregate_results.py
"""
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks"
RESULTS_DIR = BENCHMARKS_DIR / "results"
SYSTEM_INFO_PATH = BENCHMARKS_DIR / "system_info.json"
REPORT_PATH = PROJECT_ROOT / "benchmark_report.md"


def percentile(data: list[float], p: float) -> float:
    """Compute the p-th percentile of a list (0-100)."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)


def load_results() -> dict[int, list[dict]]:
    """Load all result JSONs grouped by segment duration."""
    groups: dict[int, list[dict]] = {}
    for fp in sorted(RESULTS_DIR.glob("*.json")):
        with open(fp) as f:
            data = json.load(f)
        dur = int(data["segment_duration_seconds"])
        groups.setdefault(dur, []).append(data)
    return groups


def aggregate(groups: dict[int, list[dict]]) -> list[dict]:
    """Compute p50/p95 stats for each duration group."""
    rows = []
    for dur in sorted(groups.keys()):
        runs = groups[dur]
        times = [r["total_job_time_seconds"] for r in runs]
        peak_mems = [r["peak_memory_mb"] for r in runs]
        avg_cpus = [r["avg_cpu_percent"] for r in runs]
        output_sizes = [r["output_video_size_mb"] for r in runs]

        eff_cores = []
        for r in runs:
            wall = r["total_job_time_seconds"]
            cpu_total = r["cpu_user_time_seconds"] + r["cpu_system_time_seconds"]
            if wall > 0:
                eff_cores.append(cpu_total / wall)

        rtfs = []
        for r in runs:
            seg = r["segment_duration_seconds"]
            if seg > 0:
                rtfs.append(r["total_job_time_seconds"] / seg)

        rows.append({
            "duration": dur,
            "n_runs": len(runs),
            "p50_time": round(percentile(times, 50), 2),
            "p95_time": round(percentile(times, 95), 2),
            "p50_rtf": round(percentile(rtfs, 50), 3),
            "p95_rtf": round(percentile(rtfs, 95), 3),
            "p50_eff_cores": round(percentile(eff_cores, 50), 2),
            "p95_peak_mem": round(percentile(peak_mems, 95), 1),
            "p50_peak_mem": round(percentile(peak_mems, 50), 1),
            "p50_output_mb": round(percentile(output_sizes, 50), 2),
            "p50_avg_cpu": round(percentile(avg_cpus, 50), 1),
        })

    return rows


def linear_fit(rows: list[dict]) -> dict:
    """Best-effort linear fit: seconds per minute of audio, peak RAM per minute."""
    if len(rows) < 2:
        return {}

    # x = segment minutes, y = job time seconds
    xs = [r["duration"] / 60.0 for r in rows]
    ys_p50 = [r["p50_time"] for r in rows]
    ys_p95 = [r["p95_time"] for r in rows]
    mems = [r["p95_peak_mem"] for r in rows]

    def slope(xs, ys):
        n = len(xs)
        sx = sum(xs)
        sy = sum(ys)
        sxy = sum(x * y for x, y in zip(xs, ys))
        sxx = sum(x * x for x in xs)
        denom = n * sxx - sx * sx
        if abs(denom) < 1e-10:
            return 0.0
        return (n * sxy - sx * sy) / denom

    return {
        "seconds_per_minute_audio_p50": round(slope(xs, ys_p50), 2),
        "seconds_per_minute_audio_p95": round(slope(xs, ys_p95), 2),
        "peak_ram_mb_per_minute_audio_p95": round(slope(xs, mems), 2),
    }


def generate_report(rows: list[dict], fit: dict, sys_info: dict):
    """Generate the benchmark_report.md file."""
    lines = []
    lines.append("# Video Generation Benchmark Report\n")

    # System Info
    lines.append("## System Info\n")
    lines.append(f"| Property | Value |")
    lines.append(f"|----------|-------|")
    for key, val in sys_info.items():
        lines.append(f"| {key} | {val} |")
    lines.append("")

    # Repo Pipeline
    lines.append("## Repo Pipeline\n")
    lines.append("```")
    lines.append("FastAPI endpoint (/api/generate)")
    lines.append("  → app/routes/video.py::generate_single_video()")
    lines.append("  → threading.Thread → app/services/video_generator.py::generate_video()")
    lines.append("    → PIL: create_vinyl_image() + _prerender_rotation_cycle() (~54 frames)")
    lines.append("    → FFmpeg subprocess (stdin pipe, raw RGB → H.264 libx264)")
    lines.append("    → outputs/*.mp4")
    lines.append("```")
    lines.append("")
    lines.append("**Key files:**")
    lines.append("- `app/services/video_generator.py` — frame generation + FFmpeg encoding")
    lines.append("- `app/services/image_processor.py` — vinyl disc image creation")
    lines.append("- `app/routes/video.py` — API endpoints, async job management")
    lines.append("- `app/services/benchmarking.py` — instrumentation module\n")

    # Results Summary
    lines.append("## Results Summary (Aggregated)\n")
    lines.append("| Segment (s) | Runs | p50 Time (s) | p95 Time (s) | RTF p50 | Eff. CPU Cores p50 | p95 Peak RAM (MB) | p50 Output (MB) |")
    lines.append("|-------------|------|-------------|-------------|---------|--------------------|--------------------|-----------------|")
    for r in rows:
        lines.append(
            f"| {r['duration']} | {r['n_runs']} | {r['p50_time']} | {r['p95_time']} "
            f"| {r['p50_rtf']} | {r['p50_eff_cores']} | {r['p95_peak_mem']} | {r['p50_output_mb']} |"
        )
    lines.append("")

    # Resource Profile
    lines.append("## Resource Profile\n")

    if rows:
        # Determine CPU vs IO bound
        avg_cpu = sum(r["p50_avg_cpu"] for r in rows) / len(rows)
        lines.append(f"- **CPU utilization** (avg across durations): ~{avg_cpu:.0f}%")

        if avg_cpu > 150:
            lines.append("- **Classification**: CPU-bound (heavy multi-core utilization during Pillow frame rendering + FFmpeg encoding)")
        elif avg_cpu > 80:
            lines.append("- **Classification**: CPU-bound (moderate, single-core heavy with FFmpeg encoding)")
        else:
            lines.append("- **Classification**: Mixed CPU/IO (frame piping and disk writes significant)")

        # RAM scaling
        if len(rows) >= 2:
            ram_first = rows[0]["p95_peak_mem"]
            ram_last = rows[-1]["p95_peak_mem"]
            dur_first = rows[0]["duration"]
            dur_last = rows[-1]["duration"]
            ram_growth = (ram_last - ram_first) / max(1, dur_last - dur_first)
            if ram_growth < 0.1:
                lines.append(f"- **RAM scaling**: Nearly constant (~{ram_first:.0f}–{ram_last:.0f} MB). Memory usage does not scale with duration.")
            else:
                lines.append(f"- **RAM scaling**: Grows ~{ram_growth:.1f} MB per second of audio ({ram_first:.0f}–{ram_last:.0f} MB range)")

        lines.append("- **Parallel contention**: Each job runs its own FFmpeg subprocess. Concurrent jobs compete for CPU cores and memory bandwidth. RAM is the likely bottleneck for parallel execution.")
    lines.append("")

    # Capacity Estimation
    lines.append("## Capacity Estimation\n")
    lines.append("Rule: `min(vCPU / eff_cpu_cores_p50, RAM_GB / p95_peak_ram_GB) × 0.8`\n")

    if rows:
        # Use the "typical" (30s) or median duration for estimates
        ref_row = None
        for r in rows:
            if r["duration"] == 30:
                ref_row = r
                break
        if not ref_row:
            ref_row = rows[len(rows) // 2]

        eff_cores = ref_row["p50_eff_cores"] or 1
        peak_ram_gb = ref_row["p95_peak_mem"] / 1024.0

        configs = [
            (4, 8), (8, 16), (16, 32),
        ]
        lines.append(f"Reference: {ref_row['duration']}s segment, eff. cores = {eff_cores}, p95 peak RAM = {ref_row['p95_peak_mem']} MB\n")
        lines.append("| Server Config | CPU-limited | RAM-limited | Max Concurrent (×0.8) |")
        lines.append("|---------------|------------|------------|----------------------|")
        for vcpu, ram in configs:
            cpu_cap = vcpu / eff_cores if eff_cores > 0 else 999
            ram_cap = ram / peak_ram_gb if peak_ram_gb > 0 else 999
            raw = min(cpu_cap, ram_cap)
            safe = max(1, int(raw * 0.8))
            lines.append(
                f"| {vcpu} vCPU / {ram}GB | {cpu_cap:.1f} | {ram_cap:.1f} | **{safe}** |"
            )
    lines.append("")

    # Cost Modeling Inputs
    lines.append("## Cost Modeling Inputs (MEASURED ONLY)\n")
    if fit:
        lines.append(f"- **Seconds compute per 1 min audio (p50):** {fit['seconds_per_minute_audio_p50']}s")
        lines.append(f"- **Seconds compute per 1 min audio (p95):** {fit['seconds_per_minute_audio_p95']}s")
        lines.append(f"- **Peak RAM per minute audio growth (p95):** {fit['peak_ram_mb_per_minute_audio_p95']} MB/min")

    if rows:
        lines.append("")
        lines.append("| Segment (s) | p95 Peak RAM (MB) | Disk Read (MB) | Disk Write (MB) | Output MB/min audio |")
        lines.append("|-------------|-------------------|----------------|-----------------|---------------------|")
        for r in rows:
            runs = load_results().get(r["duration"], [])
            avg_read = sum(run.get("disk_read_mb", 0) for run in runs) / max(1, len(runs))
            avg_write = sum(run.get("disk_write_mb", 0) for run in runs) / max(1, len(runs))
            output_per_min = (r["p50_output_mb"] / (r["duration"] / 60.0)) if r["duration"] > 0 else 0
            lines.append(
                f"| {r['duration']} | {r['p95_peak_mem']} "
                f"| {avg_read:.1f} | {avg_write:.1f} | {output_per_min:.1f} |"
            )

    lines.append("")
    lines.append("- **GPU:** not used (CPU-only libx264 encoding)\n")

    # Raw Files
    lines.append("## Raw Files\n")
    for fp in sorted(RESULTS_DIR.glob("*.json")):
        lines.append(f"- `benchmarks/results/{fp.name}`")
    lines.append("")

    # Write
    report_text = "\n".join(lines)
    with open(REPORT_PATH, "w") as f:
        f.write(report_text)
    print(f"  ✓ Report written to {REPORT_PATH}")


def main():
    print("=" * 60)
    print("Sonivo Benchmark Aggregation")
    print("=" * 60)

    # Load system info
    if not SYSTEM_INFO_PATH.exists():
        print("ERROR: system_info.json not found. Run run_benchmarks.py first.")
        sys.exit(1)
    with open(SYSTEM_INFO_PATH) as f:
        sys_info = json.load(f)

    # Load results
    groups = load_results()
    if not groups:
        print("ERROR: No result files found in benchmarks/results/")
        sys.exit(1)

    print(f"\n  Found results for durations: {sorted(groups.keys())}s")
    for dur, runs in sorted(groups.items()):
        print(f"    {dur}s: {len(runs)} runs")

    # Aggregate
    print("\n  Computing aggregates...")
    rows = aggregate(groups)
    fit = linear_fit(rows)

    # Generate report
    print("\n  Generating report...")
    generate_report(rows, fit, sys_info)

    # Print summary table
    print("\n  ── Summary ──")
    print(f"  {'Dur':>5s} | {'p50 Time':>9s} | {'p95 Time':>9s} | {'RTF p50':>8s} | {'Peak RAM':>9s}")
    print(f"  {'─'*5} | {'─'*9} | {'─'*9} | {'─'*8} | {'─'*9}")
    for r in rows:
        print(f"  {r['duration']:>5d} | {r['p50_time']:>8.1f}s | {r['p95_time']:>8.1f}s | {r['p50_rtf']:>8.3f} | {r['p95_peak_mem']:>7.0f}MB")

    if fit:
        print(f"\n  Linear fit:")
        print(f"    Seconds per minute audio (p50): {fit['seconds_per_minute_audio_p50']}s")
        print(f"    Seconds per minute audio (p95): {fit['seconds_per_minute_audio_p95']}s")

    print(f"\n{'=' * 60}")


if __name__ == "__main__":
    main()
