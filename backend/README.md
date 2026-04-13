
# Media Downloader Web App (Backend)

This is the backend for a production-ready Media Downloader web application. It supports downloading and converting videos or audio from YouTube, TikTok, Instagram, and Facebook into MP3 or MP4 formats. Built with FastAPI, yt-dlp, and FFmpeg.

## Features
- Download and convert videos/audio from YouTube, TikTok, Instagram, Facebook
- Select MP3 or MP4 format and quality (128/192/320 kbps, 360p–4K)
- Trim media before downloading
- Playlist detection and ZIP bundling
- Task status tracking and progress endpoint
- Automatic cleanup of old files
- No login, no ads, no tracking (privacy-first)
- Responsive, mobile-friendly frontend (served from `static/`)

## Architecture
- **Frontend:** Static HTML/CSS/JS (Tailwind CSS)
- **Backend:** FastAPI (Python), yt-dlp, FFmpeg
- **API:** REST endpoints for download/convert

## API Endpoints
- `POST /download` — Accepts URL, format, quality, trim; returns download link
- `POST /cancel/{task_id}` — Cancels a running job
- `GET /status/{task_id}` — Polls job status

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the server:
   ```bash
   uvicorn main:app --reload
   ```
3. Health check:
   Visit http://localhost:8000/health

## Deployment
- Dockerized backend for easy deployment
- Static frontend deployable to CDN (Vercel, Netlify, S3, etc.)
- CI/CD pipeline with GitHub Actions

## Security
- Input validation and shell command sanitization
- No persistent user data or PII stored
- Hardened server, minimal dependencies
- Rate limiting and monitoring for abuse

## Project Planning
Comprehensive planning documents are available in `docs/ways-of-work/plan/media-downloader/`:
- Product Requirements (prd.md)
- Strategic Plan
- Implementation Plan
- Security Review
- GitHub Issues Breakdown
- Deployment Strategy
- CI/CD Enhancement
- SEO Strategy
- Rollout Plan

## Output & Static Files
- Output files are stored in the `downloads/` directory
- Frontend is served from the `static/` directory
