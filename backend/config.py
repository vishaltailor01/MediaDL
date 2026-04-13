import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to the ffmpeg binary directory.
# Override by setting the FFMPEG_PATH environment variable before starting the server.
FFMPEG_PATH = os.environ.get(
    "FFMPEG_PATH",
    r"C:\Users\tailo\ffmpeg-8.1-full_build\bin",
)

# Path to the Netscape-format cookies.txt file.
# Override by setting the COOKIES_FILE environment variable.
COOKIES_FILE = os.environ.get(
    "COOKIES_FILE",
    os.path.join(BASE_DIR, "cookies.txt"),
)

# yt-dlp player clients tried in order when a download attempt fails.
# Each represents a different YouTube API path with different bot-detection profiles.
#   android_vr   — Android VR client; works without cookies or PO tokens for public videos
#   android      — native Android API; good fallback
#   ios          — native iOS API; needs GVS PO token for some formats but often works
#   mweb         — mobile web; lighter fingerprint
#   web_creator  — YouTube Studio client; less monitored traffic
# On bot-detection the next client is tried automatically.
# Any other error (private, geo-blocked, etc.) stops the retry immediately.
PLAYER_CLIENTS = ["android_vr", "android", "ios", "mweb", "web_creator"]

# Browsers whose cookies are tried (in order) as a last-resort automatic fallback
# when all player clients fail with bot-detection and no cookies.txt is present.
# Firefox is listed first because it stores cookies without Windows DPAPI encryption,
# making it reliably readable by yt-dlp. Chrome/Edge use DPAPI which can fail when
# the browser process is running or under certain Windows user contexts.
BROWSER_COOKIE_SOURCES = ["firefox", "edge", "chrome", "brave", "chromium", "opera"]

# Valid quality values for each output format.
MP3_QUALITIES = ("128", "192", "320")
MP4_QUALITIES = ("360", "480", "720", "1080", "2160")
