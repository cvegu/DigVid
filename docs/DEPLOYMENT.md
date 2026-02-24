# Deploying Sonivo to Production

## Why Not Netlify or Vercel?

**Netlify** and **Vercel** are built for **static sites** and **short-lived serverless functions**. This app does not fit that model:

| Requirement | Netlify / Vercel | This app |
|-------------|------------------|----------|
| **Runtime** | Serverless (invoke per request, then exit) | Long-running **Python server** (FastAPI + Uvicorn) |
| **System binaries** | Limited; no FFmpeg in standard runtimes | **FFmpeg** is required (video encoding) |
| **Execution time** | ~10–60 seconds max per request | Video generation can take **several minutes** |
| **Filesystem** | Ephemeral (writes are not persistent) | Needs **persistent** `uploads/` and `outputs/` |
| **Process model** | Stateless, scale-to-zero | Stateful (in-memory job progress, file paths) |

So **Netlify and Vercel are not suitable** for this stack. You need a platform that runs a **persistent container or VM** and allows **FFmpeg** (and optionally persistent disk).

---

## Recommended “Easy” Options

These are still simple to use but support long-running processes and FFmpeg.

### 1. **Railway** (easiest)

- Connect your GitHub repo, add a **Dockerfile** (or use Nixpacks with FFmpeg).
- Railway runs your app as a **web service** (always-on process).
- Add **FFmpeg** via a Dockerfile or buildpack.
- Free tier has limits; paid tier is straightforward.
- **Persistent volume**: You can attach a volume for `uploads/` and `outputs/` so files survive deploys.

**Good for**: Quick deploy, minimal config, support for FFmpeg and disk.

### 2. **Render**

- **Web Service** (not Static Site): connect repo, choose “Web Service”, set build command and start command.
- Use a **Dockerfile** that installs FFmpeg and runs Uvicorn (recommended).
- Free tier: service sleeps after inactivity; first request may be slow (cold start).
- **Disk**: Ephemeral by default; for production you’d use a **Render Disk** (paid) for `uploads/` and `outputs/`, or an external store (e.g. S3).

**Good for**: Simple UI, Docker-based, predictable pricing.

### 3. **Fly.io**

- Deploy a **Docker image** that includes Python + FFmpeg.
- Global regions, good for low latency.
- **Volumes** for persistent storage (e.g. for uploads/outputs).
- Slightly more “CLI-first” than Railway/Render but still manageable.

**Good for**: Global deployment and full control over the container.

### 4. **Small VPS** (DigitalOcean, Linode, etc.)

- A **Droplet** or small VM: install Python, FFmpeg, run Uvicorn behind **Nginx** (reverse proxy + static files).
- Use **systemd** or **supervisor** to keep the app running.
- Full control; you manage OS, firewall, and backups.

**Good for**: Maximum control and no platform limits; a bit more ops work.

---

## What You Need for Production

Regardless of where you deploy:

1. **FFmpeg in the environment**  
   The server must have `ffmpeg` on `PATH` (Dockerfile or base image that installs FFmpeg).

2. **Production ASGI server**  
   Use Uvicorn with workers or Gunicorn + Uvicorn worker (see below).

3. **CORS**  
   Restrict `allow_origins` to your frontend domain(s) instead of `["*"]`.

4. **Secrets**  
   Don’t hardcode secrets; use env vars (e.g. `os.environ.get("ALLOWED_ORIGINS")`).

5. **Persistent storage (recommended)**  
   On Railway/Render/Fly, use a **volume** or external object storage (S3, R2) for `uploads/` and `outputs/` so files and videos survive restarts and redeploys.

6. **Cleanup (optional but good)**  
   Cron or a background task to delete old files in `uploads/` and `outputs/` to avoid filling disk.

---

## Example Dockerfile

Use this (or adapt) for **Railway**, **Render**, or **Fly.io** so the environment includes FFmpeg and runs the app:

```dockerfile
# Use a Python image that we can add FFmpeg to
FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Create dirs the app expects
RUN mkdir -p uploads outputs

# Production: bind to 0.0.0.0 and use PORT if the platform provides it
ENV HOST=0.0.0.0
ENV PORT=8000
EXPOSE 8000

CMD uvicorn app.main:app --host ${HOST} --port ${PORT}
```

- **Render**: Set start command to the same `uvicorn` line (or leave as `CMD`).
- **Railway**: Often auto-detects; set **Start Command** to the `uvicorn` command and ensure **Root Directory** is the app root.
- **Fly.io**: Use this Dockerfile and in `fly.toml` set the internal port (e.g. 8000).

---

## Summary

| Goal | Suggestion |
|------|------------|
| Easiest deploy with minimal config | **Railway** (repo connect + Dockerfile + volume for files) |
| Simple UI, Docker, free tier with sleep | **Render** (Web Service + Dockerfile; add Disk for persistence) |
| Global, more control | **Fly.io** (Docker + volume) |
| Full control, no platform limits | **VPS** (Nginx + Uvicorn + systemd) |

**Netlify and Vercel** do not support this stack because they are for static/serverless workloads; this app needs a long-running server and FFmpeg. Use one of the options above instead.
