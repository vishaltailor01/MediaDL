import glob
import os
import re
import shutil
import time

import yt_dlp  # type: ignore
from config import BROWSER_COOKIE_SOURCES, COOKIES_FILE, FFMPEG_PATH, PLAYER_CLIENTS
from models import is_cancelled, update_task

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    """Remove ANSI terminal colour/style codes from a string."""
    return _ANSI_ESCAPE.sub("", s)


def parse_time(t: str) -> float:
    """Convert a time string (HH:MM:SS, MM:SS, or raw seconds) to float seconds."""
    t = t.strip()
    parts = t.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        else:
            return float(t)
    except (ValueError, IndexError):
        return 0.0


def find_media_file(directory: str, fmt: str = "mp3"):
    """Return the first .mp3 or .mp4 file found in a directory, or None."""
    ext = ".mp4" if fmt == "mp4" else ".mp3"
    files = glob.glob(os.path.join(directory, f"*{ext}"))
    return files[0] if files else None


def find_mp3(directory: str):
    """Return the first .mp3 file found in a directory, or None."""
    return find_media_file(directory, "mp3")


class DownloadCancelled(Exception):
    """Raised by progress hooks to abort the current yt-dlp download.

    Kept as a plain Exception so it propagates cleanly through our own
    try/except handlers.  For playlists we iterate manually (see
    download_and_convert) so we never rely on ignoreerrors=True to stop
    the loop — cancellation is checked between every video instead.
    """

    pass


def make_progress_hook(task_id: str):
    """Returns a yt-dlp progress hook that aborts if the task is cancelled."""

    def hook(d):
        if is_cancelled(task_id):
            raise DownloadCancelled("Download cancelled by user")
        if d.get("status") == "downloading":
            downloaded = d.get("downloaded_bytes", 0) or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            if total > 0:
                pct = int((downloaded / total) * 100)
                update_task(task_id, progress_pct=min(pct, 99))

    return hook


def is_playlist(url: str) -> bool:
    """Detect genuine playlist URLs — no network call needed.
    Excludes YouTube Mix/Radio (list=RD...) which are auto-generated
    and can be infinite — those are treated as single video downloads.
    """
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    list_id = qs.get("list", [""])[0]
    if not list_id:
        return False
    # RD / RDMM = YouTube Mix or Music Mix — treat as single video
    if list_id.startswith("RD"):
        return False
    return True


def _classify_error(err_str: str) -> str:
    """Map a raw yt-dlp error string to a stable category string."""
    s = err_str.lower()
    if (
        "sign in" in s
        or "bot" in s
        or ("cookie" in s and ("confirm" in s or "authentication" in s))
    ):
        return "bot_detection"
    if "private video" in s or "this video is private" in s:
        return "private"
    if "not available in your country" in s or "geographic" in s:
        return "geo_blocked"
    if "age" in s and ("restrict" in s or "verif" in s or "limit" in s):
        return "age_restricted"
    return "other"


def _friendly_error(err_str: str, browser_tried: bool = False) -> str:
    """Return a user-facing error message for a yt-dlp failure."""
    kind = _classify_error(err_str)
    if kind == "bot_detection":
        if os.path.exists(COOKIES_FILE):
            return (
                "YouTube blocked the download — your cookies appear to be expired. "
                "Re-upload a fresh cookies.txt using the cookie button above."
            )
        if browser_tried:
            return (
                "YouTube is blocking downloads from this network (bot detection). "
                "Uploading a cookies.txt is the most reliable fix: "
                "log into YouTube in Chrome/Edge, export cookies with the "
                "\u2018Get cookies.txt LOCALLY\u2019 extension, then upload via the cookie button."
            )
        return (
            "YouTube blocked the download (bot detection). "
            "Try uploading your YouTube cookies.txt via the cookie button above."
        )
    if kind == "private":
        return "This video is private and cannot be downloaded."
    if kind == "geo_blocked":
        return "This video is not available in your region."
    if kind == "age_restricted":
        if os.path.exists(COOKIES_FILE):
            return (
                "This video is age-restricted. Your cookies may not include age-verification "
                "consent — re-upload cookies while actively logged in to YouTube."
            )
        return (
            "This video is age-restricted. "
            "Upload your YouTube cookies.txt (while logged in to YouTube) to download it."
        )
    return err_str


def _cookie_opts() -> dict:
    """Return cookiefile option if cookies.txt exists, otherwise empty dict."""
    if os.path.exists(COOKIES_FILE):
        return {"cookiefile": COOKIES_FILE}
    return {}


def _build_opts(
    task_id: str,
    task_dir: str,
    quality: str,
    client: str,
    fmt: str = "mp3",
    trim_start: str | None = None,
    trim_end: str | None = None,
    extra: dict | None = None,
) -> dict:
    if fmt == "mp4":
        format_str = (
            f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best"
        )
        postprocessors = [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]
    else:
        format_str = "bestaudio/best"
        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }
        ]
    opts: dict = {
        "quiet": True,
        "outtmpl": os.path.join(task_dir, "%(title)s.%(ext)s"),
        "format": format_str,
        "postprocessors": postprocessors,
        "windowsfilenames": True,
        "ffmpeg_location": FFMPEG_PATH,
        "noplaylist": True,  # Always download a single video; playlists are iterated manually
        "extractor_args": {"youtube": {"player_client": [client]}},
        "progress_hooks": [make_progress_hook(task_id)],
        "sleep_interval": 1,
        "max_sleep_interval": 3,
        "sleep_interval_requests": 1,
        "retries": 5,
        "fragment_retries": 5,
    }
    if fmt == "mp4":
        opts["merge_output_format"] = "mp4"
    if trim_start or trim_end:
        from yt_dlp.utils import download_range_func

        start_secs = parse_time(trim_start) if trim_start else 0.0
        end_secs = parse_time(trim_end) if trim_end else float("inf")
        opts["download_ranges"] = download_range_func(None, [(start_secs, end_secs)])
        opts["force_keyframes_at_cuts"] = True
    opts.update(_cookie_opts())
    if extra:
        opts.update(extra)
    return opts


def _extract_with_retry(
    task_id: str,
    url: str,
    task_dir: str,
    quality: str,
    fmt: str = "mp3",
    trim_start: str | None = None,
    trim_end: str | None = None,
    extra: dict | None = None,
):
    """Two-phase yt-dlp download with full automatic fallback.

    Phase 1 — Player client rotation (no cookies needed, no user action):
      Tries each client in PLAYER_CLIENTS. Retries only on bot-detection;
      any other error (private, geo-blocked…) stops immediately.
      If cookies.txt exists and we’re still bot-detected, also stops (file is
      expired — no point trying another client with the same bad cookies).

    Phase 2 — Browser cookie extraction (no user action needed):
      Only entered when Phase 1 exhausted all clients via bot-detection AND
      no cookies.txt is present. Tries each browser in BROWSER_COOKIE_SOURCES;
      yt-dlp reads the browser’s live cookie store directly. Skips browsers
      that are not installed. Returns on the first success.
    """
    has_cookies = os.path.exists(COOKIES_FILE)
    last_error: Exception | None = None

    # ── Phase 1: player client rotation ──
    for client in PLAYER_CLIENTS:
        opts = _build_opts(
            task_id, task_dir, quality, client, fmt, trim_start, trim_end, extra
        )
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=True)
        except DownloadCancelled:
            raise
        except Exception as exc:
            last_error = exc
            if _classify_error(str(exc)) == "bot_detection" and not has_cookies:
                continue  # try next client
            break  # non-retryable, or file cookies present but expired

    # ── Phase 2: silent browser cookie extraction ──
    # Only attempt when every Phase 1 client was blocked for bot-detection
    # and the user has not uploaded a cookies.txt manually.
    phase2_entered = False
    if (
        _classify_error(_strip_ansi(str(last_error))) == "bot_detection"
        and not has_cookies
    ):
        phase2_entered = True
        for browser in BROWSER_COOKIE_SOURCES:
            opts = _build_opts(
                task_id,
                task_dir,
                quality,
                PLAYER_CLIENTS[0],
                fmt,
                trim_start,
                trim_end,
                extra,
            )
            opts["cookiesfrombrowser"] = (browser,)
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=True)
            except DownloadCancelled:
                raise
            except Exception as exc:
                last_error = exc
                err_lower = str(exc).lower()
                # Browser not installed / no profile found / DPAPI decrypt failure
                # → not usable, try the next browser
                if any(
                    k in err_lower
                    for k in (
                        "could not find",
                        "no such file",
                        "database",
                        "dpapi",
                        "decrypt",
                        "failed to decrypt",
                    )
                ):
                    continue
                # Still bot-detected even with this browser’s cookies → try next
                if _classify_error(err_lower) == "bot_detection":
                    continue
                break  # real content error (private, geo…) — stop

    # When Phase 2 was entered and exhausted, last_error may be a harmless
    # "browser not found" / DPAPI message — the real underlying cause is bot
    # detection, so always emit the friendly upload-cookies message.
    if phase2_entered:
        raise type("RetryExhausted", (Exception,), {})(
            _friendly_error("sign in to confirm", browser_tried=True)  # type: ignore[arg-type]
        )
    raise type("RetryExhausted", (Exception,), {})(
        _friendly_error(_strip_ansi(str(last_error or "Unknown error")), browser_tried=False)  # type: ignore[arg-type]
    )


def download_and_convert(
    task_id: str,
    url: str,
    output_dir: str,
    quality: str = "192",
    fmt: str = "mp3",
    trim_start: str | None = None,
    trim_end: str | None = None,
):
    task_dir = os.path.join(output_dir, task_id)
    os.makedirs(task_dir, exist_ok=True)

    def _cleanup_partial():
        """Remove .part and intermediary files left by a cancelled download."""
        patterns = (
            ("*.part", "*.webm", "*.m4a", "*.opus") if fmt == "mp3" else ("*.part",)
        )
        for pattern in patterns:
            for f in glob.glob(os.path.join(task_dir, pattern)):
                try:
                    os.remove(f)
                except OSError:
                    pass

    try:
        if is_playlist(url):
            # ── Step 1: flat fetch to get individual video URLs and total count ──
            # Use a clean playlist?list=ID URL so yt-dlp never confuses the v=
            # parameter with a single-video request — that ambiguity is the most
            # common reason flat extraction silently returns zero entries.
            from urllib.parse import parse_qs, urlparse

            _qs = parse_qs(urlparse(url).query)
            _list_id = _qs.get("list", [""])[0]
            flat_url = (
                f"https://www.youtube.com/playlist?list={_list_id}" if _list_id else url
            )

            entries = []
            last_flat_error: str = ""
            try:
                flat_info = None
                for _client in PLAYER_CLIENTS:
                    flat_opts: dict = {
                        "quiet": True,
                        "extract_flat": True,
                        "noplaylist": False,
                        "socket_timeout": 30,
                        "extractor_args": {"youtube": {"player_client": [_client]}},
                    }
                    flat_opts.update(_cookie_opts())
                    try:
                        with yt_dlp.YoutubeDL(flat_opts) as ydl:
                            flat_info = ydl.extract_info(flat_url, download=False)
                    except DownloadCancelled:
                        raise
                    except Exception as _fe:
                        last_flat_error = str(_fe)
                        continue  # try next client
                    if flat_info and flat_info.get("entries"):
                        break  # got a usable result
                    flat_info = None  # result had no entries — keep trying
                if flat_info:
                    entries = [
                        e for e in (flat_info.get("entries") or []) if e and e.get("id")
                    ]
                if entries:
                    update_task(task_id, total_count=len(entries))
                elif last_flat_error:
                    update_task(
                        task_id,
                        error=f"[playlist fetch] {_strip_ansi(last_flat_error)}",
                    )
            except DownloadCancelled:
                _cleanup_partial()
                update_task(task_id, status="cancelled")
                return
            except Exception:
                pass  # non-critical — we'll re-try the URL below if entries is empty

            if not entries:
                # Flat extraction failed — fall back to treating as single video
                entries = [{"id": None, "webpage_url": url}]

            # ── Step 2: download each video individually so WE control the loop ──
            # Cancellation is checked before EVERY video, giving near-instant stop.
            downloaded = 0
            skipped = 0
            for entry in entries:
                # Check cancel BEFORE starting the next track.
                if is_cancelled(task_id):
                    _cleanup_partial()
                    update_task(task_id, status="cancelled")
                    return

                video_url = entry.get("webpage_url") or (
                    f"https://www.youtube.com/watch?v={entry['id']}"
                    if entry.get("id")
                    else None
                )
                if not video_url:
                    skipped += 1
                    continue

                try:
                    # Single-video download — no ignoreerrors needed
                    update_task(
                        task_id,
                        current_track=entry.get("title") or video_url,
                        progress_pct=0,
                    )
                    _extract_with_retry(task_id, video_url, task_dir, quality, fmt)
                    downloaded += 1
                    overall_pct = int((downloaded / len(entries)) * 100)
                    update_task(
                        task_id,
                        progress_count=downloaded,
                        progress_pct=overall_pct,
                        current_track=None,
                    )
                    # Polite delay between tracks to avoid rate-limiting
                    time.sleep(1.5)
                except DownloadCancelled:
                    _cleanup_partial()
                    update_task(task_id, status="cancelled", current_track=None)
                    return
                except Exception as exc:
                    skipped += 1  # unavailable / private / geo-blocked — skip it
                    update_task(task_id, current_track=None)
                    # Brief back-off on bot detection to let YouTube cool down
                    if _classify_error(_strip_ansi(str(exc))) == "bot_detection":
                        time.sleep(5)

            # ── Step 3: zip results ──
            media_files = glob.glob(os.path.join(task_dir, "*.mp3")) + glob.glob(
                os.path.join(task_dir, "*.mp4")
            )
            if media_files:
                zip_path = shutil.make_archive(
                    os.path.join(output_dir, f"playlist_{task_id}"), "zip", task_dir
                )
                shutil.rmtree(task_dir, ignore_errors=True)
                status_msg = "completed"
                if skipped > 0:
                    status_msg += f" (skipped {skipped} unavailable video(s))"
                update_task(
                    task_id, status=status_msg, result_file=zip_path, progress_pct=100
                )
            else:
                update_task(
                    task_id,
                    status="error",
                    error="No tracks could be downloaded from this playlist.",
                )
        else:
            try:
                info = _extract_with_retry(
                    task_id, url, task_dir, quality, fmt, trim_start, trim_end
                )
            except DownloadCancelled:
                _cleanup_partial()
                update_task(task_id, status="cancelled")
                return
            except Exception as exc:
                update_task(task_id, status="error", error=str(exc))
                return

            if info is None:
                update_task(
                    task_id,
                    status="error",
                    error="Video unavailable or could not be downloaded.",
                )
                return

            media_path = find_media_file(task_dir, fmt)
            if media_path:
                update_task(
                    task_id,
                    status="completed",
                    result_file=media_path,
                    progress_pct=100,
                )
            else:
                any_files = glob.glob(os.path.join(task_dir, "*"))
                extra_msg = (
                    f" Files found: {[os.path.basename(f) for f in any_files]}"
                    if any_files
                    else " No files were downloaded."
                )
                update_task(
                    task_id, status="error", error=f"Conversion failed.{extra_msg}"
                )
    except DownloadCancelled:
        update_task(task_id, status="cancelled")
    except Exception as exc:
        update_task(task_id, status="error", error=str(exc))
