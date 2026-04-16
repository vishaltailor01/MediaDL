import os
import sys
import uuid
import tempfile
import traceback
import shutil
import requests
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional

# Add parent directory to python path for local execution module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.ffmpeg_wrapper import FfmpegEngine
from storage.s3 import S3StorageLayer
from storage.db import DynamoJobStore

app = FastAPI(title="MediaDL Core API")

# Use local memory fallback if DynamoDB is unavailable or mocked
jobs_fallback = {}
db = DynamoJobStore()

class JobRequest(BaseModel):
    type: str # 'convert', 'trim', 'extract_audio'
    input: str
    outputFormat: str
    trimStart: Optional[str] = None # For trim, e.g., '00:00:10'
    trimDuration: Optional[str] = None # E.g., '00:00:05'
    webhookUrl: Optional[str] = None # Webhook callback

def trigger_webhook(url: str, payload: dict):
    if url:
        try:
            requests.post(url, json=payload, timeout=5)
            print(f"Webhook delivered to {url}")
        except Exception as e:
            print(f"Webhook failed to deliver: {e}")

def update_status(job_id: str, status: str, result: str = None, error: str = None, webhook: str = None):
    # Fallback memory
    if job_id in jobs_fallback:
        jobs_fallback[job_id]["status"] = status
        if result: jobs_fallback[job_id]["result"] = result
        if error: jobs_fallback[job_id]["error"] = error
    
    # DynamoDB (Silently fails if no AWS configured natively)
    db.update_job_status(job_id, status, result, error)
    
    if status in ["completed", "failed"] and webhook:
        trigger_webhook(webhook, {
            "jobId": job_id,
            "status": status,
            "result": result,
            "error": error
        })

def process_job(job_id: str, request: JobRequest):
    update_status(job_id, "processing")
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ffmpeg = FfmpegEngine()
            s3 = S3StorageLayer()
            
            input_uri = request.input
            output_ext = request.outputFormat
            
            # Download Input
            if input_uri.startswith("s3://"):
                _, key = s3.parse_s3_uri(input_uri)
                local_input_filename = os.path.basename(key) or "input.tmp"
                local_input_path = os.path.join(tmpdir, local_input_filename)
                
                print(f"[Job {job_id}] Downloading {input_uri} to {local_input_path}")
                s3.download_file(input_uri, local_input_path)
                
                base_uri, _ = os.path.splitext(input_uri)
                output_uri = f"{base_uri}.{output_ext}"
            else:
                local_input_path = input_uri
                if not os.path.exists(local_input_path):
                    raise FileNotFoundError(f"Local file not found: {local_input_path}")
                base_path, _ = os.path.splitext(local_input_path)
                output_uri = f"{base_path}.{output_ext}"
            
            # Process
            local_output_filename = f"output.{output_ext}"
            local_output_path = os.path.join(tmpdir, local_output_filename)
            
            if request.type == "convert":
                ffmpeg.convert(local_input_path, local_output_path, output_ext)
            elif request.type == "trim":
                ffmpeg.trim(local_input_path, local_output_path, request.trimStart, request.trimDuration)
            elif request.type == "extract_audio":
                ffmpeg.convert(local_input_path, local_output_path, "mp3") # Same wrapper method
            else:
                raise ValueError(f"Unknown job type: {request.type}")

            # Deliver Output
            if input_uri.startswith("s3://"):
                s3.upload_file(local_output_path, output_uri)
            else:
                shutil.copy(local_output_path, output_uri)
                
        update_status(job_id, "completed", result=output_uri, webhook=request.webhookUrl)
        
    except Exception as e:
        print(f"[Job {job_id}] Failed: {e}")
        traceback.print_exc()
        update_status(job_id, "failed", error=str(e), webhook=request.webhookUrl)

@app.post("/jobs")
def create_job(request: JobRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    payload = request.model_dump()
    
    # Store Local & DynamoDB
    jobs_fallback[job_id] = {
        "status": "queued",
        "request": payload,
        "result": None,
        "error": None
    }
    db.create_job(job_id, payload)
    
    # ── Phase 2: Decoupled Queueing ──
    # If SQS is configured, enqueue and rely on `workers/main.py`
    # Otherwise, fallback gracefully to `BackgroundTasks`
    import storage.queue
    sqs_queue = storage.queue.SqsJobQueue()
    if sqs_queue.sqs:
        sqs_queue.enqueue_job(job_id, payload)
    else:
        background_tasks.add_task(process_job, job_id, request)
        
    return {"jobId": job_id, "status": "queued"}

@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    # Check Dynamo First
    record = db.get_job(job_id)
    if record:
        return record
    
    # Check Local Fallback
    if job_id not in jobs_fallback:
        raise HTTPException(status_code=404, detail="Job not found in database or memory.")
    return jobs_fallback[job_id]

@app.get("/")
def read_root():
    return {"message": "Welcome to MediaDL Core API. Post jobs to /jobs or check /docs for Swagger UI!"}
