# Task state management for YouTube-to-MP3 app
import threading
import time
import uuid
from typing import Any, Dict

# In-memory task state (can be replaced with sqlite for persistence)
tasks: Dict[str, Dict[str, Any]] = {}
tasks_lock = threading.Lock()


# Helper to create a new task
def create_task() -> str:
    task_id = str(uuid.uuid4())
    with tasks_lock:
        tasks[task_id] = {
            "status": "processing",
            "format": "mp3",
            "progress_count": 0,
            "total_count": 0,
            "progress_pct": 0,
            "current_track": None,
            "error": None,
            "result_file": None,
            "created_at": time.time(),
            "cancelled": False,
        }
    return task_id


def update_task(task_id: str, **kwargs):
    with tasks_lock:
        if task_id in tasks:
            tasks[task_id].update(kwargs)


def get_task(task_id: str) -> Dict[str, Any]:
    with tasks_lock:
        return tasks.get(task_id)


def cancel_task(task_id: str):
    with tasks_lock:
        if task_id in tasks:
            tasks[task_id]["cancelled"] = True


def is_cancelled(task_id: str) -> bool:
    with tasks_lock:
        t = tasks.get(task_id)
        return bool(t and t.get("cancelled", False))


def cleanup_old_tasks(max_age_seconds: int = 3600):
    now = time.time()
    with tasks_lock:
        to_delete = [
            tid for tid, t in tasks.items() if now - t["created_at"] > max_age_seconds
        ]
        for tid in to_delete:
            del tasks[tid]
