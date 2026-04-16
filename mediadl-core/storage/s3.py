import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

class S3StorageLayer:
    def __init__(self, region_name="us-east-1"):
        # Relies on standard AWS configure environment variables or IAM roles
        self.s3_client = boto3.client('s3', region_name=region_name)

    def parse_s3_uri(self, s3_uri: str):
        """Parse s3://bucket-name/path/to/file into bucket and key."""
        if not s3_uri.startswith("s3://"):
            raise ValueError(f"Invalid S3 URI: {s3_uri}")
        
        parts = s3_uri[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        return bucket, key

    def download_file(self, s3_uri: str, local_path: str) -> str:
        """Download a file from S3 to local storage."""
        bucket, key = self.parse_s3_uri(s3_uri)
        try:
            self.s3_client.download_file(bucket, key, local_path)
            return local_path
        except ClientError as e:
            raise RuntimeError(f"Failed to download from S3: {e}")

    def upload_file(self, local_path: str, s3_uri: str) -> str:
        """Upload a local file to S3."""
        bucket, key = self.parse_s3_uri(s3_uri)
        try:
            self.s3_client.upload_file(local_path, bucket, key)
            return s3_uri
        except ClientError as e:
            raise RuntimeError(f"Failed to upload to S3: {e}")

    def is_s3_uri(self, uri: str) -> bool:
        return uri.startswith("s3://")
