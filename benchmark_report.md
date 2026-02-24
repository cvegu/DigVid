# Video Generation Benchmark Report

## System Info

| Property | Value |
|----------|-------|
| os | Darwin 25.2.0 |
| kernel | Darwin Kernel Version 25.2.0: Tue Nov 18 21:09:55 PST 2025; root:xnu-12377.61.12~1/RELEASE_ARM64_T8103 |
| machine | arm64 |
| python_version | 3.11.9 |
| cpu_physical_cores | 8 |
| cpu_logical_cores | 8 |
| ram_total_gb | 8.0 |
| cpu_model | Apple M1 |
| ffmpeg_version | ffmpeg version 7.1.1 Copyright (c) 2000-2025 the FFmpeg developers |
| gpu_name | not available (no NVIDIA GPU detected) |
| disk_total_gb | 460.4 |
| disk_free_gb | 38.6 |

## Repo Pipeline

```
FastAPI endpoint (/api/generate)
  → app/routes/video.py::generate_single_video()
  → threading.Thread → app/services/video_generator.py::generate_video()
    → PIL: create_vinyl_image() + _prerender_rotation_cycle() (~54 frames)
    → FFmpeg subprocess (stdin pipe, raw RGB → H.264 libx264)
    → outputs/*.mp4
```

**Key files:**
- `app/services/video_generator.py` — frame generation + FFmpeg encoding
- `app/services/image_processor.py` — vinyl disc image creation
- `app/routes/video.py` — API endpoints, async job management
- `app/services/benchmarking.py` — instrumentation module

## Results Summary (Aggregated)

| Segment (s) | Runs | p50 Time (s) | p95 Time (s) | RTF p50 | Eff. CPU Cores p50 | p95 Peak RAM (MB) | p50 Output (MB) |
|-------------|------|-------------|-------------|---------|--------------------|--------------------|-----------------|
| 15 | 5 | 12.96 | 16.37 | 0.864 | 2.0 | 703.3 | 14.77 |
| 30 | 5 | 22.17 | 22.72 | 0.739 | 3.82 | 1007.9 | 29.6 |
| 60 | 5 | 44.69 | 50.64 | 0.745 | 3.57 | 1108.4 | 59.27 |
| 120 | 5 | 90.72 | 100.0 | 0.756 | 3.76 | 999.0 | 118.51 |
| 300 | 4 | 204.94 | 218.67 | 0.683 | 3.88 | 1067.7 | 296.24 |

## Resource Profile

- **CPU utilization** (avg across durations): ~42%
- **Classification**: Mixed CPU/IO (frame piping and disk writes significant)
- **RAM scaling**: Grows ~1.3 MB per second of audio (703–1068 MB range)
- **Parallel contention**: Each job runs its own FFmpeg subprocess. Concurrent jobs compete for CPU cores and memory bandwidth. RAM is the likely bottleneck for parallel execution.

## Capacity Estimation

Rule: `min(vCPU / eff_cpu_cores_p50, RAM_GB / p95_peak_ram_GB) × 0.8`

Reference: 30s segment, eff. cores = 3.82, p95 peak RAM = 1007.9 MB

| Server Config | CPU-limited | RAM-limited | Max Concurrent (×0.8) |
|---------------|------------|------------|----------------------|
| 4 vCPU / 8GB | 1.0 | 8.1 | **1** |
| 8 vCPU / 16GB | 2.1 | 16.3 | **1** |
| 16 vCPU / 32GB | 4.2 | 32.5 | **3** |

## Cost Modeling Inputs (MEASURED ONLY)

- **Seconds compute per 1 min audio (p50):** 40.54s
- **Seconds compute per 1 min audio (p95):** 42.98s
- **Peak RAM per minute audio growth (p95):** 38.24 MB/min

| Segment (s) | p95 Peak RAM (MB) | Disk Read (MB) | Disk Write (MB) | Output MB/min audio |
|-------------|-------------------|----------------|-----------------|---------------------|
| 15 | 703.3 | 0.0 | 0.0 | 59.1 |
| 30 | 1007.9 | 0.0 | 0.0 | 59.2 |
| 60 | 1108.4 | 0.0 | 0.0 | 59.3 |
| 120 | 999.0 | 0.0 | 0.0 | 59.3 |
| 300 | 1067.7 | 0.0 | 0.0 | 59.2 |

- **GPU:** not used (CPU-only libx264 encoding)

## Raw Files

- `benchmarks/results/20260218_223748_15s_run_1.json`
- `benchmarks/results/20260218_223801_15s_run_2.json`
- `benchmarks/results/20260218_223815_15s_run_3.json`
- `benchmarks/results/20260218_223827_15s_run_4.json`
- `benchmarks/results/20260218_223845_15s_run_5.json`
- `benchmarks/results/20260218_223929_30s_run_1.json`
- `benchmarks/results/20260218_223952_30s_run_2.json`
- `benchmarks/results/20260218_224014_30s_run_3.json`
- `benchmarks/results/20260218_224037_30s_run_4.json`
- `benchmarks/results/20260218_224100_30s_run_5.json`
- `benchmarks/results/20260218_224224_60s_run_1.json`
- `benchmarks/results/20260218_224310_60s_run_2.json`
- `benchmarks/results/20260218_224351_60s_run_3.json`
- `benchmarks/results/20260218_224444_60s_run_4.json`
- `benchmarks/results/20260218_224532_60s_run_5.json`
- `benchmarks/results/20260218_224846_120s_run_1.json`
- `benchmarks/results/20260218_225005_120s_run_2.json`
- `benchmarks/results/20260218_225136_120s_run_3.json`
- `benchmarks/results/20260218_225319_120s_run_4.json`
- `benchmarks/results/20260218_225455_120s_run_5.json`
- `benchmarks/results/20260218_231306_300s_run_2.json`
- `benchmarks/results/20260218_231647_300s_run_3.json`
- `benchmarks/results/20260218_232020_300s_run_4.json`
- `benchmarks/results/20260218_232338_300s_run_5.json`
