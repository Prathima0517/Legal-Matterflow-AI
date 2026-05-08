import boto3
from config import S3_BUCKET_NAME

def get_s3_client():
    return boto3.client("s3")

def get_s3_bucket_name():
    return S3_BUCKET_NAME


