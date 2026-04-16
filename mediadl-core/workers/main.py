import sys
import os
import time
import json
from pydantic import BaseModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from the API core loop for actual processing mechanics mapped
# Normally, you'd decouple entirely or place `process_job` in a shared `engine` util
from api.main import process_job, JobRequest
from storage.queue import SqsJobQueue

def run_worker_loop():
    print("Starting MediaDL Core Worker... Poll queue for Jobs")
    sqs = SqsJobQueue()
    
    if not sqs.sqs:
        print("FATAL: AWS SQS Configuration not provided via process environment variables.")
        print("Cannot start distributed worker without queue. Run API in background task mode instead for local tests.")
        sys.exit(1)
        
    while True:
        try:
            messages = sqs.poll_jobs(wait_time_seconds=20)
            if not messages:
                continue
                
            for msg in messages:
                body = json.loads(msg['Body'])
                job_id = body.get('jobId')
                payload = body.get('request', {})
                receipt = msg['ReceiptHandle']
                
                print(f"[Worker] Picked up job {job_id}")
                
                # Transform untyped dict to BaseModel mapping used in current API
                req_obj = JobRequest(**payload)
                
                # Executes process deterministically
                process_job(job_id, req_obj)
                
                print(f"[Worker] Finished job {job_id}. Deleting from SQS.")
                sqs.delete_message(receipt)
                
        except Exception as e:
            print(f"[Worker Error] {e}")
            time.sleep(5) # Prevent aggressive looping on persistent network drops

if __name__ == "__main__":
    run_worker_loop()
