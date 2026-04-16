import boto3
import json
import os
from botocore.exceptions import ClientError
from typing import Optional

class SqsJobQueue:
    """
    Manages job queueing using AWS SQS.
    Phase 2: Decouples API from heavy FFmpeg workers.
    """
    def __init__(self, queue_url=os.getenv("SQS_QUEUE_URL", ""), region_name=os.getenv("AWS_REGION", "us-east-1")):
        self.queue_url = queue_url
        if self.queue_url:
            self.sqs = boto3.client('sqs', region_name=region_name)
        else:
            self.sqs = None
            print("WARNING: SQS_QUEUE_URL sequence not provided. Queueing will fail if not using local fallback.")
            
    def enqueue_job(self, job_id: str, payload: dict) -> bool:
        if not self.sqs:
            return False
            
        message = {
            "jobId": job_id,
            "request": payload
        }
        try:
            self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message)
            )
            return True
        except ClientError as e:
            print(f"SQS Enqueue Error: {e}")
            return False

    def poll_jobs(self, max_messages=1, wait_time_seconds=10) -> list:
        if not self.sqs:
            return []
            
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time_seconds
            )
            return response.get('Messages', [])
        except ClientError as e:
            print(f"SQS Poll Error: {e}")
            return []
            
    def delete_message(self, receipt_handle: str):
        if not self.sqs: return
        try:
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
        except ClientError as e:
            print(f"SQS Delete Error: {e}")
