from pydantic import BaseModel
from typing import Optional
from fastapi import Form

class ContentInput:
    def __init__(self, content: str = Form(None)):
        self.content = content

class ContentResponse(BaseModel):
    request_id: str
    uploaded_file_s3_key: str
    extracted_file_s3_key: str
    input_type: str
    
class TemplateExtractorInput(BaseModel):
    extracted_file_s3_key: str

class TemplateExtractorOutput(BaseModel):
    extracted_file_s3_key: str
    template_type: str
    confidence: Optional[float] = None
    action: Optional[str] = None
    processing_time_ms: Optional[int] = None
    reason: Optional[str] = None
    
class TemplateFieldExtractorInput(BaseModel):
    extracted_file_s3_key: str
    template_type: str
    
