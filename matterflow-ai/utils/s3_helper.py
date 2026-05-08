import io
from typing import List, Tuple
from fastapi import HTTPException

def upload_files_to_s3(
    s3_client, 
    s3_bucket_name: str, 
    files_to_upload: List[Tuple[io.BytesIO, str]]
) -> None:
    try:
        for file_stream, s3_key in files_to_upload:
            file_stream.seek(0, 2)
            file_size = file_stream.tell()
            file_stream.seek(0)
            
            print(f"Uploading {s3_key}: {file_size} bytes")
            
            if file_size == 0:
                raise HTTPException(status_code=400, detail=f"Cannot upload empty file: {s3_key}")
            
            s3_client.upload_fileobj(file_stream, s3_bucket_name, s3_key)
            print(f"Successfully uploaded {s3_key}")
            
    except Exception as e:
        print(f"S3 upload error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to upload files to S3: {str(e)}"
        )

def read_text_from_s3(s3_client, s3_bucket_name: str, s3_key: str) -> str:
    try:
        response = s3_client.get_object(Bucket=s3_bucket_name, Key=s3_key)
        content = response['Body'].read().decode('utf-8')
        return content
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read content from S3: {str(e)}"
        )

