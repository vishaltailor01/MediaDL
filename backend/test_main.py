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
    assert response.json()["detail"] == "File not found"
