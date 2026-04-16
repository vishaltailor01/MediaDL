import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional

class DynamoJobStore:
    """
    Manages job states, configurations, and webhook definitions using Amazon DynamoDB.
    """
    def __init__(self, table_name="MediaDLJobs", region_name="us-east-1"):
        self.table_name = table_name
        self.dynamo = boto3.resource('dynamodb', region_name=region_name)
        self.table = self.dynamo.Table(self.table_name)
        
    def create_job(self, job_id: str, payload: dict) -> None:
        try:
            self.table.put_item(
                Item={
                    'jobId': job_id,
                    'status': 'queued',
                    'request': payload,
                    'error': None,
                    'result': None
                }
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Graceful degradation for local testing without AWS configured
                pass
            else:
                raise RuntimeError(f"DynamoDB Error: {e}")

    def update_job_status(self, job_id: str, status: str, result: Optional[str] = None, error: Optional[str] = None) -> None:
        update_expr = "set #st = :s"
        expr_attr_names = {'#st': 'status'}
        expr_attr_vals = {':s': status}
        
        if result:
            update_expr += ", #res = :r"
            expr_attr_names['#res'] = 'result'
            expr_attr_vals[':r'] = result
            
        if error:
            update_expr += ", #err = :e"
            expr_attr_names['#err'] = 'error'
            expr_attr_vals[':e'] = error
            
        try:
            self.table.update_item(
                Key={'jobId': job_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_vals
            )
        except ClientError:
            pass

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.table.get_item(Key={'jobId': job_id})
            return response.get('Item')
        except ClientError:
            return None
