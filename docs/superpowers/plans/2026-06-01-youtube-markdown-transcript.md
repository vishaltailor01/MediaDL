# YouTube Markdown Transcript Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `Markdown Transcript` output option that converts a YouTube video's available captions/transcript into a downloadable `.md` file using Microsoft MarkItDown.

**Architecture:** Implement this in the existing `backend/` app because it already owns URL validation, blocklisting, task state, async background work, and downloadable result files. Add a focused transcript function in `backend/tasks.py`, route `format == "md"` from `backend/main.py`, and update the static UI to expose the new format.

**Tech Stack:** FastAPI, existing in-memory task store, Microsoft `markitdown[youtube-transcription]`, pytest, static HTML/CSS/JavaScript.

---

## File Structure

- Modify `backend/requirements.txt`: add the MarkItDown YouTube transcript extra.
- Modify `backend/tasks.py`: add Markdown filename helpers and `transcribe_youtube_to_markdown`.
- Modify `backend/main.py`: allow `md` format, dispatch the transcript task, and serve `.md` files as `text/markdown`.
- Modify `backend/static/index.html`: add the transcript format button, quality visibility behavior, button text, result metadata, and history rendering support.
- Modify `backend/test_main.py`: add focused API tests that do not call the network.

## Implementation Tasks

### Task 1: Add MarkItDown Dependency

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add the dependency**

Append this line to `backend/requirements.txt`:

```txt
markitdown[youtube-transcription]==0.1.6
```

- [ ] **Step 2: Install backend dependencies**

Run:

```powershell
pip install -r backend/requirements.txt
```

Expected: `markitdown`, `youtube-transcript-api`, and current backend dependencies install successfully.

- [ ] **Step 3: Verify import works**

Run:

```powershell
@'
from markitdown import MarkItDown
print(MarkItDown)
'@ | python -
```

Expected: command prints a `MarkItDown` class reference and exits with code `0`.

- [ ] **Step 4: Commit**

Run:

```powershell
git add backend/requirements.txt
git commit -m "chore: add markitdown youtube transcript dependency"
```

### Task 2: Add Backend Transcript Task

**Files:**
- Modify: `backend/tasks.py`
- Test: `backend/test_main.py`

- [ ] **Step 1: Write failing unit tests for transcript task**

Add these tests to `backend/test_main.py`:

```python
def test_transcribe_youtube_to_markdown_writes_result_file(monkeypatch, tmp_path):
    import tasks as yt_tasks
    from models import create_task, get_task

    class FakeResult:
        text_content = "# Sample Transcript\n\nHello from captions."

    class FakeMarkItDown:
        def convert(self, source, **kwargs):
            assert source == "https://www.youtube.com/watch?v=abc123"
            assert kwargs == {"youtube_transcript_languages": ["en"]}
            return FakeResult()

    monkeypatch.setattr(yt_tasks, "MarkItDown", lambda: FakeMarkItDown())

    task_id = create_task()
    yt_tasks.transcribe_youtube_to_markdown(
        task_id,
        "https://www.youtube.com/watch?v=abc123",
        str(tmp_path),
    )

    task = get_task(task_id)
    assert task["status"] == "completed"
    assert task["format"] == "md"
    assert task["progress_pct"] == 100
    assert task["result_file"].endswith("transcript.md")

    with open(task["result_file"], "r", encoding="utf-8") as f:
        assert f.read() == "# Sample Transcript\n\nHello from captions."


def test_transcribe_youtube_to_markdown_reports_missing_transcript(monkeypatch, tmp_path):
    import tasks as yt_tasks
    from models import create_task, get_task

    class FakeMarkItDown:
        def convert(self, source, **kwargs):
            raise RuntimeError("No transcript is available for this video")

    monkeypatch.setattr(yt_tasks, "MarkItDown", lambda: FakeMarkItDown())

    task_id = create_task()
    yt_tasks.transcribe_youtube_to_markdown(
        task_id,
        "https://www.youtube.com/watch?v=abc123",
        str(tmp_path),
    )

    task = get_task(task_id)
    assert task["status"] == "error"
    assert "No transcript is available" in task["error"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
pytest backend/test_main.py::test_transcribe_youtube_to_markdown_writes_result_file backend/test_main.py::test_transcribe_youtube_to_markdown_reports_missing_transcript -v
```

Expected: both tests fail because `backend/tasks.py` does not define `MarkItDown` or `transcribe_youtube_to_markdown`.

- [ ] **Step 3: Add lazy MarkItDown import and transcript function**

In `backend/tasks.py`, add this near the imports:

```python
try:
    from markitdown import MarkItDown
except ImportError:
    MarkItDown = None
```

Add this helper near `find_media_file`:

```python
def find_markdown_file(directory: str):
    """Return the first .md file found in a directory, or None."""
    files = glob.glob(os.path.join(directory, "*.md"))
    return files[0] if files else None
```

Add this function before `download_and_convert`:

```python
def transcribe_youtube_to_markdown(
    task_id: str,
    url: str,
    output_dir: str,
    languages: list[str] | None = None,
):
    task_dir = os.path.join(output_dir, task_id)
    os.makedirs(task_dir, exist_ok=True)
    output_path = os.path.join(task_dir, "transcript.md")
    transcript_languages = languages or ["en"]

    try:
        if MarkItDown is None:
            raise RuntimeError(
                "Markdown transcript support is not installed. "
                "Install markitdown[youtube-transcription]."
            )

        if is_cancelled(task_id):
            update_task(task_id, status="cancelled")
            return

        update_task(
            task_id,
            format="md",
            progress_pct=10,
            current_track="Fetching transcript",
        )

        result = MarkItDown().convert(
            url,
            youtube_transcript_languages=transcript_languages,
        )
        markdown = (getattr(result, "text_content", "") or "").strip()
        if not markdown:
            raise RuntimeError("No transcript text was returned for this video.")

        with open(output_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(markdown)
            f.write("\n")

        update_task(
            task_id,
            status="completed",
            format="md",
            result_file=output_path,
            progress_pct=100,
            current_track=None,
        )
    except Exception as exc:
        update_task(
            task_id,
            status="error",
            format="md",
            error=str(exc),
            current_track=None,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
pytest backend/test_main.py::test_transcribe_youtube_to_markdown_writes_result_file backend/test_main.py::test_transcribe_youtube_to_markdown_reports_missing_transcript -v
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add backend/tasks.py backend/test_main.py
git commit -m "feat: add youtube markdown transcript task"
```

### Task 3: Route `md` Format Through the API

**Files:**
- Modify: `backend/main.py`
- Test: `backend/test_main.py`

- [ ] **Step 1: Write failing API routing tests**

Add these tests to `backend/test_main.py`:

```python
def test_download_accepts_markdown_format(monkeypatch):
    import main

    captured = {}

    def fake_create_task():
        return "123e4567-e89b-12d3-a456-426614174000"

    def fake_update_task(task_id, **kwargs):
        captured.setdefault("updates", []).append((task_id, kwargs))

    def fake_add_task(self, func, *args, **kwargs):
        captured["task_func"] = func.__name__
        captured["task_args"] = args
        captured["task_kwargs"] = kwargs

    monkeypatch.setattr(main, "create_task", fake_create_task)
    monkeypatch.setattr(main, "update_task", fake_update_task)
    monkeypatch.setattr(main.BackgroundTasks, "add_task", fake_add_task)

    response = client.post(
        "/download",
        json={
            "url": "https://www.youtube.com/watch?v=abc123",
            "format": "md",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"task_id": "123e4567-e89b-12d3-a456-426614174000"}
    assert captured["task_func"] == "transcribe_youtube_to_markdown"
    assert captured["task_args"] == (
        "123e4567-e89b-12d3-a456-426614174000",
        "https://www.youtube.com/watch?v=abc123",
        main.DOWNLOAD_DIR,
    )
    assert captured["updates"][-1] == (
        "123e4567-e89b-12d3-a456-426614174000",
        {"format": "md"},
    )


def test_download_markdown_file_uses_text_markdown_media_type(tmp_path, monkeypatch):
    import main

    transcript = tmp_path / "transcript.md"
    transcript.write_text("# Transcript\n", encoding="utf-8")

    monkeypatch.setattr(main, "DOWNLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(
        main,
        "get_task",
        lambda task_id: {"result_file": str(transcript), "status": "completed"},
    )

    response = client.get("/download/123e4567-e89b-12d3-a456-426614174000")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.text == "# Transcript\n"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
pytest backend/test_main.py::test_download_accepts_markdown_format backend/test_main.py::test_download_markdown_file_uses_text_markdown_media_type -v
```

Expected: first test fails because `md` falls back to `mp3`; second test fails because `.md` is served as `application/octet-stream`.

- [ ] **Step 3: Update `/download` format handling**

In `backend/main.py`, replace:

```python
if fmt not in ("mp3", "mp4"):
    fmt = "mp3"
default_quality = "192" if fmt == "mp3" else "720"
quality = str(data.get("quality", default_quality))
valid_qualities = MP3_QUALITIES if fmt == "mp3" else MP4_QUALITIES
if quality not in valid_qualities:
    quality = default_quality
```

with:

```python
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
```

- [ ] **Step 4: Dispatch transcript task for `md`**

In `backend/main.py`, replace the current `background_tasks.add_task(...)` block in `start_download` with:

```python
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
```

- [ ] **Step 5: Serve Markdown with the correct media type**

In `backend/main.py`, replace:

```python
media_types = {".mp3": "audio/mpeg", ".mp4": "video/mp4", ".zip": "application/zip"}
```

with:

```python
media_types = {
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".zip": "application/zip",
    ".md": "text/markdown",
}
```

- [ ] **Step 6: Run API tests**

Run:

```powershell
pytest backend/test_main.py::test_download_accepts_markdown_format backend/test_main.py::test_download_markdown_file_uses_text_markdown_media_type -v
```

Expected: both tests pass.

- [ ] **Step 7: Commit**

Run:

```powershell
git add backend/main.py backend/test_main.py
git commit -m "feat: route markdown transcript downloads"
```

### Task 4: Update the Static Frontend

**Files:**
- Modify: `backend/static/index.html`

- [ ] **Step 1: Add a Markdown Transcript format button**

In the `.format-row` block, after the MP4 button, add:

```html
<button class="format-btn" id="fmt-md" type="button" data-fmt="md" aria-label="Markdown transcript format">
  <span class="fmt-icon">TXT</span>
  Markdown Transcript
</button>
```

- [ ] **Step 2: Hide quality and trim controls for Markdown**

In the JavaScript section, after the existing element constants, add:

```javascript
const optionsRow = qualitySelect.closest('.options-row');
```

In `function setFormat(fmt)`, replace:

```javascript
convertBtn.textContent = fmt === 'mp4' ? 'Download MP4 Video' : 'Convert to MP3';
updateQualityOptions(fmt);
```

with:

```javascript
convertBtn.textContent =
  fmt === 'mp4'
    ? 'Download MP4 Video'
    : fmt === 'md'
      ? 'Create Markdown Transcript'
      : 'Convert to MP3';

if (optionsRow) optionsRow.style.display = fmt === 'md' ? 'none' : '';
if (trimToggle) trimToggle.style.display = fmt === 'md' ? 'none' : '';
if (trimSection) {
  trimSection.style.display = fmt === 'md' ? 'none' : '';
  if (fmt === 'md') {
    trimSection.classList.remove('open');
    trimToggle.classList.remove('open');
    trimToggle.setAttribute('aria-expanded', 'false');
    trimSection.setAttribute('aria-hidden', 'true');
  }
}

if (fmt !== 'md') updateQualityOptions(fmt);
```

- [ ] **Step 3: Send empty trim values for Markdown**

In `startDownload`, replace the request body fields:

```javascript
trim_start: trimStartInput.value.trim(),
trim_end:   trimEndInput.value.trim()
```

with:

```javascript
trim_start: currentFormat === 'md' ? '' : trimStartInput.value.trim(),
trim_end:   currentFormat === 'md' ? '' : trimEndInput.value.trim()
```

- [ ] **Step 4: Add Markdown result metadata**

In `FORMAT_META`, add:

```javascript
md: {
  icon: 'TXT',
  label: 'Download Markdown',
  cls: 'md'
},
```

Update `getFormatKey(downloadUrl, fmt)` to:

```javascript
function getFormatKey(downloadUrl, fmt) {
  if (downloadUrl && /playlist_/.test(downloadUrl)) return 'zip';
  if (fmt === 'mp4') return 'mp4';
  if (fmt === 'md') return 'md';
  return 'mp3';
}
```

- [ ] **Step 5: Add history icon fallback for Markdown**

In `HIST_SVG`, add:

```javascript
md: `<span style="font-size:11px;font-weight:800;color:white;">TXT</span>`,
```

Also add CSS classes near the existing history format styles:

```css
.h-icon-md { background: linear-gradient(135deg, #0f766e, #14b8a6); }
.h-fmt-md { background: rgba(20,184,166,0.16); color: #0f766e; }
```

- [ ] **Step 6: Quick static validation**

Run:

```powershell
Select-String -Path backend/static/index.html -Pattern "Markdown Transcript|Create Markdown Transcript|Download Markdown|h-icon-md|h-fmt-md"
```

Expected: all five patterns are present.

- [ ] **Step 7: Commit**

Run:

```powershell
git add backend/static/index.html
git commit -m "feat: add markdown transcript option to frontend"
```

### Task 5: Run Full Backend Verification

**Files:**
- Verify: `backend/test_main.py`

- [ ] **Step 1: Run all backend tests**

Run:

```powershell
pytest backend/test_main.py -v
```

Expected: all tests pass.

- [ ] **Step 2: Start the backend locally**

Run:

```powershell
uvicorn backend.main:app --reload --port 8000
```

Expected: FastAPI starts on `http://127.0.0.1:8000`.

- [ ] **Step 3: Smoke test the health endpoint**

In another terminal, run:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected:

```powershell
status
------
ok
```

- [ ] **Step 4: Smoke test transcript task creation**

Run:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/download -ContentType "application/json" -Body '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","format":"md"}'
```

Expected: response contains a `task_id`. If YouTube captions are unavailable or blocked, `/status/{task_id}` may eventually report `error`; task creation should still work.

- [ ] **Step 5: Commit verification-only fixes if needed**

If verification required code changes, run:

```powershell
git add backend
git commit -m "test: verify markdown transcript workflow"
```

If no changes were needed, do not create an empty commit.

## Acceptance Criteria

- `/download` accepts `"format": "md"` without falling back to MP3.
- `format == "md"` jobs call `transcribe_youtube_to_markdown`, not `download_and_convert`.
- Successful transcript jobs write `transcript.md` and expose it through the existing `/download/{task_id}` endpoint.
- `.md` files are served as `text/markdown`.
- The frontend exposes `Markdown Transcript` as a third format and shows a Markdown-specific download label.
- Backend tests cover the transcript task, API routing, and Markdown media type.

## Known Limitation

This v1 uses YouTube captions/transcripts available to MarkItDown. Videos without accessible captions may fail with a user-visible task error. A later v2 can add an audio speech-to-text fallback using a separate transcription engine.
