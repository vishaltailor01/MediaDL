import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ─── Logging Setup ───────────────────────────────────────────────────────────
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("backend")


def log_request(request):
    logger.info(
        f"{getattr(request, 'method', 'UNKNOWN')} {getattr(request.url, 'path', 'UNKNOWN')} from {getattr(getattr(request, 'client', None), 'host', 'unknown')}"
    )


def log_error(request, exc):
    logger.error(
        f"Error on {getattr(request, 'method', 'UNKNOWN')} {getattr(request.url, 'path', 'UNKNOWN')} from {getattr(getattr(request, 'client', None), 'host', 'unknown')}: {exc}"
    )


import os
from datetime import datetime

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Header,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from supabase import Client, create_client
except ImportError:
    create_client = None
    Client = None
import hmac
import ipaddress
import json
import re
import threading
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from urllib.parse import urlparse, urlunparse

import tasks as yt_tasks
from config import MP3_QUALITIES, MP4_QUALITIES
from course_generator.schemas import CourseExportResponse, CoursePlanRequest
from course_generator.service import create_course_export, create_course_plan
from fastapi.responses import FileResponse, JSONResponse
from fastapi import Response
from fastapi.staticfiles import StaticFiles
from models import cancel_task, cleanup_old_tasks, create_task, get_task, update_task

# ─── URL Blocklist ─────────────────────────────────────────────────────────────
_bl_lock = threading.Lock()
_BLOCKLIST_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "blocklist.json"
)


def _bl_load() -> dict:
    if os.path.exists(_BLOCKLIST_FILE):
        try:
            with open(_BLOCKLIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _bl_save(data: dict):
    with open(_BLOCKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _bl_normalize(url: str) -> str:
    try:
        p = urlparse(url.strip())
        return urlunparse(
            (p.scheme.lower(), p.netloc.lower(), p.path, p.params, p.query, "")
        )
    except Exception:
        return url.strip()


def _bl_is_blocked(url: str) -> tuple[bool, str]:
    normalized = _bl_normalize(url)
    with _bl_lock:  # hold lock for the entire read+iterate
        data = _bl_load()
        for blocked, entry in data.items():
            if normalized == blocked:
                return True, entry.get("reason", "")
            # Prefix-match only at a path boundary (trailing '/') to avoid
            # blocking ?v=ABCxxx when only ?v=ABC is listed.
            if blocked.endswith("/") and normalized.startswith(blocked):
                return True, entry.get("reason", "")
    return False, ""


def _require_admin(key: str | None):
    expected = os.environ.get("MEDIADL_ADMIN_KEY", "")
    if not expected or not hmac.compare_digest(key or "", expected):
        raise HTTPException(status_code=403, detail="Forbidden")


# ─── Rate limiter ──────────────────────────────────────────────────────────────
class _RateLimit:
    """Sliding-window in-process rate limiter, keyed by IP."""

    def __init__(self, max_calls: int, window: int):
        self._max = max_calls
        self._window = window
        self._lock = threading.Lock()
        self._calls: dict = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            calls = self._calls[key]
            calls[:] = [t for t in calls if t > cutoff]
            if len(calls) >= self._max:
                return False
            calls.append(now)
            return True


_dl_limiter = _RateLimit(max_calls=10, window=60)  # 10 downloads / IP / minute
_admin_limiter = _RateLimit(max_calls=30, window=60)  # 30 admin calls / IP / minute


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─── Input validators ──────────────────────────────────────────────────────────
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_ALLOWED_SCHEMES = frozenset({"http", "https"})
_BLOCKED_HOST_RE = re.compile(
    r"^(localhost|.*\.local|.*\.internal|.*\.localdomain|metadata\.google\.internal)$",
    re.IGNORECASE,
)


def _validate_task_id(task_id: str) -> None:
    """Reject non-UUID task_id values before hitting the task store."""
    if not _UUID_RE.match(task_id):
        raise HTTPException(status_code=404, detail="Task not found")


def _validate_url(url: str) -> None:
    """Reject non-http/https schemes and private/loopback hosts (SSRF protection)."""
    if not isinstance(url, str) or not url.strip():
        raise HTTPException(status_code=400, detail="Missing URL")
    if len(url) > 2048:
        raise HTTPException(status_code=400, detail="URL too long")
    try:
        p = urlparse(url.strip())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL")
    if p.scheme not in _ALLOWED_SCHEMES:
        raise HTTPException(status_code=400, detail="URL scheme not allowed")
    hostname = (p.hostname or "").lower()
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL")
    if _BLOCKED_HOST_RE.match(hostname):
        raise HTTPException(status_code=400, detail="URL not allowed")
    try:
        addr = ipaddress.ip_address(hostname)
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_unspecified
        ):
            raise HTTPException(status_code=400, detail="URL not allowed")
    except ValueError:
        pass  # Not a bare IP address — hostname is fine


# ─── Path constants ────────────────────────────────────────────────────────────
def _is_youtube_url(url: str) -> bool:
    try:
        hostname = (urlparse(url.strip()).hostname or "").lower()
    except Exception:
        return False
    return (
        hostname == "youtu.be"
        or hostname == "youtube.com"
        or hostname.endswith(".youtube.com")
    )


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
COURSE_EXPORT_DIR = os.path.join(BASE_DIR, "course_exports")


# ─── Lifespan (replaces deprecated @app.on_event) ─────────────────────────────
def _start_cleanup_thread():
    import shutil as _shutil

    def _loop():
        while True:
            cleanup_old_tasks(max_age_seconds=86400)
            now = time.time()
            try:
                for entry in os.scandir(DOWNLOAD_DIR):
                    try:
                        if now - entry.stat().st_mtime > 86400:
                            if entry.is_file():
                                os.remove(entry.path)
                            elif entry.is_dir():
                                _shutil.rmtree(entry.path, ignore_errors=True)
                    except OSError:
                        pass
            except OSError:
                pass
            time.sleep(600)

    threading.Thread(target=_loop, daemon=True, name="cleanup").start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(COURSE_EXPORT_DIR, exist_ok=True)
    _start_cleanup_thread()
    yield


# ─── Supabase Config ──────────────────────────────────────────────────────────
SUPABASE_URL = (
    "https://fxucfxbgsoijhrkpdjfu.supabase.co"  # project ref from your dashboard
)
SUPABASE_KEY = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY", "YOUR_SUPABASE_SERVICE_ROLE_KEY"
)  # set your service role key in env
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if create_client else None

app = FastAPI(lifespan=lifespan)

from fastapi import HTTPException

# ─── Global Error Handlers ───────────────────────────────────────────────────
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    log_error(request, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    log_error(request, exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Allow CORS for local frontend dev (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    # IMPORTANT: Restrict CORS origins in production!
    # Only allow requests from your frontend domain(s).
    allow_origins=[
        "http://localhost:8000",  # dev server
        "http://127.0.0.1:8000",  # dev server
        "https://fxucfxbgsoijhrkpdjfu.supabase.co",  # example, replace with your frontend domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── User Agreement Logging Endpoint ──────────────────────────────────────────
class AgreementData(BaseModel):
    agreement_version: str
    user_id: str | None = None


@app.post("/api/agree")
async def log_user_agreement(data: AgreementData, request: Request):
    if not supabase:
        return {"status": "ok", "logged": False}
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    now = datetime.utcnow().isoformat()
    # Insert into Supabase
    res = (
        supabase.table("user_agreements")
        .insert(
            {
                "user_id": data.user_id,
                "agreement_version": data.agreement_version,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": now,
            }
        )
        .execute()
    )
    if hasattr(res, "status_code") and res.status_code >= 400:
        raise HTTPException(status_code=500, detail="Failed to log agreement")
    return {"status": "ok", "logged": True}


# Serve static frontend
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ─── Security response headers ─────────────────────────────────────────────────
@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.get("/")
def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/course-generator")
def course_generator_page():
    return FileResponse(os.path.join(STATIC_DIR, "course-generator.html"))


@app.get("/faq")
def faq_page():
    return FileResponse(os.path.join(STATIC_DIR, "faq.html"))




@app.get("/blog")
def blog_page():
    return FileResponse(os.path.join(STATIC_DIR, "blog.html"))


@app.get("/privacy-policy")
def privacy_page():
    return FileResponse(os.path.join(STATIC_DIR, "privacy-policy.html"))


@app.get("/terms-of-use")
def terms_page():
    return FileResponse(os.path.join(STATIC_DIR, "terms-of-use.html"))


@app.get("/copyright-claims")
def copyright_page():
    return FileResponse(os.path.join(STATIC_DIR, "copyright-claims.html"))


@app.get("/blog/youtube-mp3")
def blog_youtube_mp3():
    return FileResponse(os.path.join(STATIC_DIR, "blog-youtube-mp3.html"))


@app.get("/blog/playlist-zip")
def blog_playlist_zip():
    return FileResponse(os.path.join(STATIC_DIR, "blog-playlist-zip.html"))


@app.get("/blog/trim-download")
def blog_trim_download():
    return FileResponse(os.path.join(STATIC_DIR, "blog-trim-download.html"))


@app.get("/blog/social-media")
def blog_social_media():
    return FileResponse(os.path.join(STATIC_DIR, "blog-social-media.html"))


@app.get("/admin")
def admin_dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))


@app.get("/health")
def health_check():
    return JSONResponse(content={"status": "ok"})


@app.post("/course/plan")
def plan_course(request: CoursePlanRequest):
    return create_course_plan(request)


@app.post("/course/export")
def export_course(request: CoursePlanRequest):
    os.makedirs(COURSE_EXPORT_DIR, exist_ok=True)
    _, zip_path = create_course_export(request, COURSE_EXPORT_DIR)
    package_id = os.path.splitext(os.path.basename(zip_path))[0]
    return CourseExportResponse(
        package_id=package_id,
        download_url=f"/course/download/{package_id}",
    )


@app.get("/course/download/{package_id}")
def download_course_package(package_id: str):
    if not re.match(r"^[a-zA-Z0-9_.-]+$", package_id):
        raise HTTPException(status_code=404, detail="Package not found")
    zip_path = os.path.realpath(os.path.join(COURSE_EXPORT_DIR, f"{package_id}.zip"))
    real_export_dir = os.path.realpath(COURSE_EXPORT_DIR)
    if not zip_path.startswith(real_export_dir + os.sep):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Package not found")
    return FileResponse(
        zip_path,
        filename=f"{package_id}.zip",
        media_type="application/zip",
    )


# ─── Admin blocklist endpoints ─────────────────────────────────────────────────
@app.get("/admin/blocklist")
def admin_list(request: Request, x_admin_key: str | None = Header(default=None)):
    if not _admin_limiter.is_allowed(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests")
    _require_admin(x_admin_key)
    return JSONResponse(content=_bl_load())


@app.post("/admin/blocklist")
async def admin_add(request: Request, x_admin_key: str | None = Header(default=None)):
    if not _admin_limiter.is_allowed(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests")
    _require_admin(x_admin_key)
    data = await request.json()
    url = (data.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' field")
    reason = str(data.get("reason") or "").strip()
    normalized = _bl_normalize(url)
    with _bl_lock:
        existing = _bl_load()
        existing[normalized] = {"reason": reason, "original": url}
        _bl_save(existing)
    return JSONResponse(
        status_code=201, content={"blocked": normalized, "reason": reason}
    )


@app.delete("/admin/blocklist")
async def admin_remove(
    request: Request, x_admin_key: str | None = Header(default=None)
):
    if not _admin_limiter.is_allowed(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests")
    _require_admin(x_admin_key)
    data = await request.json()
    url = (data.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' field")
    normalized = _bl_normalize(url)
    with _bl_lock:
        existing = _bl_load()
        if normalized not in existing:
            raise HTTPException(status_code=404, detail="URL not found")
        del existing[normalized]
        _bl_save(existing)
    return JSONResponse(content={"removed": normalized})


@app.post("/download")
async def start_download(request: Request, background_tasks: BackgroundTasks):
    if not _dl_limiter.is_allowed(_client_ip(request)):
        raise HTTPException(
            status_code=429, detail="Too many requests. Please slow down."
        )
    data = await request.json()
    url = (data.get("url") or "").strip()
    _validate_url(url)  # SSRF protection: rejects private IPs, file://, etc.
    fmt = str(data.get("format", "mp3")).lower()
    if fmt not in ("mp3", "mp4", "md"):
        fmt = "mp3"
    default_quality = "720" if fmt == "mp4" else "192"
    quality = str(data.get("quality", default_quality))
    if fmt == "md":
        quality = default_quality
    else:
        valid_qualities = MP3_QUALITIES if fmt == "mp3" else MP4_QUALITIES
        if quality not in valid_qualities:
            quality = default_quality
    if fmt == "md" and not _is_youtube_url(url):
        raise HTTPException(
            status_code=400,
            detail="Markdown transcripts are only supported for YouTube URLs",
        )
    trim_start = str(data.get("trim_start") or "").strip() or None
    trim_end = str(data.get("trim_end") or "").strip() or None
    blocked, reason = _bl_is_blocked(url)
    if blocked:
        return JSONResponse(
            status_code=451,
            content={
                "error": "unavailable_for_legal_reasons",
                "detail": reason
                or "This URL has been blocked following a copyright claim.",
            },
        )
    task_id = create_task()
    update_task(task_id, format=fmt)
    output_dir = DOWNLOAD_DIR
    os.makedirs(output_dir, exist_ok=True)
    if fmt == "md":
        background_tasks.add_task(
            yt_tasks.transcribe_youtube_to_markdown,
            task_id,
            url,
            output_dir,
        )
    else:
        background_tasks.add_task(
            yt_tasks.download_and_convert,
            task_id,
            url,
            output_dir,
            quality,
            fmt,
            trim_start,
            trim_end,
        )
    return {"task_id": task_id}


@app.post("/cancel/{task_id}")
def cancel_download(task_id: str):
    _validate_task_id(task_id)
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    cancel_task(task_id)
    update_task(task_id, status="cancelled")
    return {"message": "Cancellation requested"}


@app.get("/status/{task_id}")
def get_status(task_id: str):
    _validate_task_id(task_id)
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    resp = {k: v for k, v in task.items() if k not in ("result_file", "cancelled")}
    if task["status"].startswith("completed") and task.get("result_file"):
        resp["download_url"] = f"/download/{task_id}"
    return resp


@app.get("/download/{task_id}")
def download_file(task_id: str):
    _validate_task_id(task_id)
    task = get_task(task_id)
    if not task or not task.get("result_file"):
        raise HTTPException(status_code=404, detail="File not found")
    # Resolve symlinks and verify the file is inside DOWNLOAD_DIR (path traversal protection)
    real_path = os.path.realpath(task["result_file"])
    real_dl_dir = os.path.realpath(DOWNLOAD_DIR)
    if not real_path.startswith(real_dl_dir + os.sep):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not os.path.exists(real_path):
        raise HTTPException(status_code=404, detail="File missing on disk")
    filename = os.path.basename(real_path)
    ext = os.path.splitext(filename)[1].lower()
    media_types = {
        ".mp3": "audio/mpeg",
        ".mp4": "video/mp4",
        ".zip": "application/zip",
        ".md": "text/markdown",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    return FileResponse(real_path, filename=filename, media_type=media_type)


# ─── Cookie management ────────────────────────────────────────────────────────
COOKIES_PATH = os.path.join(BASE_DIR, "cookies.txt")


@app.post("/settings/cookies")
async def upload_cookies(
    request: Request,
    file: UploadFile = File(...),
    x_admin_key: str | None = Header(default=None),
):
    """Accept a Netscape cookies.txt and persist it for yt-dlp authentication."""
    _require_admin(x_admin_key)  # admin-only: overwrites shared server cookies
    content = await file.read(512 * 1024)  # cap at 512 KB
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    text = content.decode("utf-8", errors="replace")
    lines = text.splitlines()
    # Require at least one .youtube.com cookie line (not just a comment)
    has_yt = any("youtube.com" in line for line in lines if not line.startswith("#"))
    if not has_yt:
        raise HTTPException(
            status_code=400,
            detail="File does not contain YouTube cookies. Make sure you exported "
            "cookies from youtube.com and the file uses the Netscape format.",
        )
    with open(COOKIES_PATH, "wb") as f:
        f.write(content)
    return {"status": "ok"}


@app.get("/settings/cookies")
def get_cookies_status():
    """Return cookie file presence and age so the UI can show live status."""
    if os.path.exists(COOKIES_PATH):
        age_days = (time.time() - os.path.getmtime(COOKIES_PATH)) / 86400
        return {"has_cookies": True, "age_days": round(age_days, 1)}
    return {"has_cookies": False, "age_days": None}


@app.delete("/settings/cookies")
def delete_cookies(x_admin_key: str | None = Header(default=None)):
    """Remove the stored cookies.txt."""
    _require_admin(x_admin_key)
    if os.path.exists(COOKIES_PATH):
        os.remove(COOKIES_PATH)
    return {"status": "ok"}
