import os
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure backend is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_download_endpoint_missing_url():
    response = client.post("/download", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing URL"


def test_status_not_found():
    response = client.get("/status/nonexistent-task-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_download_file_not_found():
    response = client.get("/download/nonexistent-task-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


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
        assert f.read() == "# Sample Transcript\n\nHello from captions.\n"


def test_transcribe_youtube_to_markdown_reports_missing_transcript(
    monkeypatch, tmp_path
):
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


def test_download_markdown_format_rejects_non_youtube_url():
    response = client.post(
        "/download",
        json={
            "url": "https://example.com/video",
            "format": "md",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Markdown transcripts are only supported for YouTube URLs"


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
    assert response.text.replace("\r\n", "\n") == "# Transcript\n"


def test_static_page_defines_truncate_helper():
    static_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(static_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert "function truncate(" in html


def test_agree_endpoint_succeeds_without_supabase(monkeypatch):
    import main

    monkeypatch.setattr(main, "supabase", None)

    response = client.post(
        "/api/agree",
        json={"agreement_version": "copyright-v1", "user_id": None},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "logged": False}


def test_favicon_returns_no_content():
    response = client.get("/favicon.ico")

    assert response.status_code == 204


def test_course_plan_endpoint_returns_course_package():
    response = client.post(
        "/course/plan",
        json={
            "markdown": "# Demo\n\n## Intro\n\nContent",
            "target": "both",
            "audience_level": "beginner",
            "transformation_mode": "original",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["course"]["title"] == "Demo"
    assert data["course"]["modules"][0]["lessons"][0]["title"] == "Intro"


def test_course_export_endpoint_creates_downloadable_zip():
    response = client.post(
        "/course/export",
        json={"markdown": "# Demo\n\n## Intro\n\nContent"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["package_id"]
    assert data["download_url"].startswith("/course/download/")

    download = client.get(data["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/zip")


def test_course_generator_page_served():
    response = client.get("/course-generator")

    assert response.status_code == 200
    assert "Markdown Course Generator" in response.text
    assert "Preview Course Plan" in response.text
    assert "Export Course Package" in response.text


def test_homepage_links_to_course_generator():
    static_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(static_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert 'href="/course-generator"' in html
