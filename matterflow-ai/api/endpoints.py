from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import uuid
import io
from typing import Optional
import asyncio
import atexit
from dependencies import get_s3_client, get_s3_bucket_name
from models.request_models import ContentInput, ContentResponse, TemplateExtractorInput, TemplateExtractorOutput,TemplateFieldExtractorInput
from utils.model_manager import model_manager
from agents.document_classifier.azure_document_classifier import AzureOpenAIDocumentClassifier
from agents.document_classifier.bart_document_classifier import BartDocumentClassifier
from agents.field_extractor import extract_entities
from utils.s3_helper import upload_files_to_s3, read_text_from_s3
from agents.content_extractor import extract_text
import random

router = APIRouter()
bart_classifier = None
azure_classifier = None

@router.post("/uploadcontent", response_model=ContentResponse)
async def upload_content(
    pdf: Optional[UploadFile] = File(None),
    word: Optional[UploadFile] = File(None),
    txt: Optional[UploadFile] = File(None),
    data: ContentInput = Depends(),
    s3_client=Depends(get_s3_client),
    s3_bucket_name: str = Depends(get_s3_bucket_name)
) -> ContentResponse:
    text_content = data.content
    matter_id = f"matter-{random.randint(100000, 999999)}"

    if not any([pdf, word, txt]) and not text_content:
        raise HTTPException(status_code=400, detail="A file (PDF, Word, TXT) or text content must be provided.")

    if sum([pdf is not None, word is not None, txt is not None, bool(text_content)]) > 1:
        raise HTTPException(status_code=400, detail="Only one of PDF, Word, TXT file or text content can be provided.")

    request_id = str(uuid.uuid4())

    file = None
    input_type = None
    if pdf:
        if pdf.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are accepted for the PDF field.")
        file = pdf
        input_type = "pdf"
    elif word:
        if word.content_type not in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword"
        ]:
            raise HTTPException(status_code=400, detail="Only Word files are accepted for the Word field.")
        file = word
        input_type = "word"
    elif txt:
        if txt.content_type != "text/plain":
            raise HTTPException(status_code=400, detail="Only TXT files are accepted for the TXT field.")
        file = txt
        input_type = "txt"

    if file:
        extracted_text = extract_text(file)
        await file.seek(0)
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        uploaded_file_stream = io.BytesIO(file_content)
        uploaded_s3_key = f"uploads/{matter_id}/documents/{file.filename}"
        extracted_s3_key = f"uploads/{matter_id}/extracted/content.txt"
    else:
        extracted_text = text_content
        uploaded_file_stream = io.BytesIO(text_content.encode('utf-8'))
        uploaded_s3_key = f"uploads/{matter_id}/text-input/content.txt"
        extracted_s3_key = f"uploads/{matter_id}/extracted/content.txt"
        input_type = "text_input"

    extracted_file_stream = io.BytesIO(extracted_text.encode('utf-8'))
    files_to_upload = [
        (uploaded_file_stream, uploaded_s3_key),
        (extracted_file_stream, extracted_s3_key)
    ]
    upload_files_to_s3(s3_client, s3_bucket_name, files_to_upload)
    return ContentResponse(
        request_id=request_id,
        uploaded_file_s3_key=uploaded_s3_key,
        extracted_file_s3_key=extracted_s3_key,
        input_type=input_type
    )

@router.post("/bart-classify", response_model=TemplateExtractorOutput)
async def bart_classify_from_s3(
    data: TemplateExtractorInput,
    s3_client=Depends(get_s3_client),
    s3_bucket_name: str = Depends(get_s3_bucket_name)
) -> TemplateExtractorOutput:
    try:
        if not data.extracted_file_s3_key:
            raise HTTPException(
                status_code=400,
                detail="extracted_file_s3_key is required"
            )
        
        document_text = read_text_from_s3(s3_client, s3_bucket_name, data.extracted_file_s3_key)
        
        if not document_text or len(document_text.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Extracted document text must be at least 10 characters"
            )

        current_classifier = get_classifier()
        
        try:
            result = await asyncio.wait_for(
                current_classifier.classify(document_text),
                timeout=300.0
            )
        except asyncio.TimeoutError:
            print("Classification timed out after 5 minutes")
            raise HTTPException(
                status_code=408,
                detail="Classification timed out - document may be too complex"
            )
        
        if result.get('status') == 'failed':
            print(f"Classification failed: {result.get('error')}")
            raise HTTPException(
                status_code=422, 
                detail=f"Classification failed: {result.get('error')}"
            )
        
        confidence = result.get('confidence', 0.0)
        if confidence >= 0.9:
            action = 'AUTO_PROCEED'
        elif confidence >= 0.7:
            action = 'REVIEW_REQUIRED'
        else:
            action = 'HUMAN_REVIEW_REQUIRED'
        
        template_type = result.get('classification', 'unknown')
        
        print(f"SUCCESS - Classification: {template_type} (confidence: {confidence:.3f})")
        
        return TemplateExtractorOutput(
            extracted_file_s3_key=data.extracted_file_s3_key,
            template_type=template_type,
            confidence=confidence,
            action=action,
            processing_time_ms=result.get('processing_time_ms', 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/azure-classify", response_model=TemplateExtractorOutput)
async def azure_classify_from_s3(
    data: TemplateExtractorInput,
    s3_client=Depends(get_s3_client),
    s3_bucket_name: str = Depends(get_s3_bucket_name)
) -> TemplateExtractorOutput:
    
    try:
        if not data.extracted_file_s3_key:
            raise HTTPException(
                status_code=400,
                detail="extracted_file_s3_key is required"
            )

        document_text = read_text_from_s3(s3_client, s3_bucket_name, data.extracted_file_s3_key)
        
        if not document_text or len(document_text.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Extracted document text must be at least 10 characters"
            )

        classifier = get_azure_classifier()

        try:
            result = await asyncio.wait_for(
                classifier.classify(document_text),
                timeout=120.0
            )
        except asyncio.TimeoutError:

            raise HTTPException(
                status_code=408,
                detail="Classification timed out after 2 minutes"
            )
        
        if result.get('status') == 'failed':
            error_msg = result.get('error', 'Unknown error')
            print(f"Classification failed: {error_msg}")
            raise HTTPException(
                status_code=422,
                detail=f"Classification failed: {error_msg}"
            )
        
        confidence = result.get('confidence', 0.0)
        if confidence >= 0.9:
            action = 'AUTO_PROCEED'
        elif confidence >= 0.7:
            action = 'REVIEW_REQUIRED'
        else:
            action = 'HUMAN_REVIEW_REQUIRED'
        
        template_type = result.get('classification', 'unknown')
        
        print(f"SUCCESS: {template_type} (confidence: {confidence:.3f})")
        
        return TemplateExtractorOutput(
            extracted_file_s3_key=data.extracted_file_s3_key,
            template_type=template_type,
            confidence=confidence,
            action=action,
            reason =  result.get('reasoning', None),
            processing_time_ms=result.get('processing_time_ms', 0) 
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {str(e)}"
        )

@router.post("/extract-matter-fields")
async def extract_matter_fields(
    data: TemplateFieldExtractorInput,
    s3_client=Depends(get_s3_client),
    s3_bucket_name: str = Depends(get_s3_bucket_name)
):
    # Validate required fields
    if not data.extracted_file_s3_key:
        raise HTTPException(
            status_code=400,
            detail="extracted_file_s3_key is required"
        )
    
    if not data.template_type:
        raise HTTPException(
            status_code=400,
            detail="template_type is required"
        )
    
    try:
        extracted_text = read_text_from_s3(
            s3_client, 
            s3_bucket_name, 
            data.extracted_file_s3_key
        )
        
        if not extracted_text or len(extracted_text.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Extracted document text must be at least 10 characters"
            )
        
        # Pass template_type to extract_entities
        extracted_entities = extract_entities(extracted_text, data.template_type)
        
        return {
            "extracted_file_s3_key": data.extracted_file_s3_key,
            "template_type": data.template_type,
            "extracted_entities": extracted_entities,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing document: {str(e)}"
        )

def get_azure_classifier():
    global azure_classifier
    if azure_classifier is None:
        print("Creating Azure classifier instance...")
        templates = model_manager.get_templates()
        azure_classifier = AzureOpenAIDocumentClassifier(templates)
        print("Azure classifier created successfully")
    return azure_classifier

def get_classifier():
    """Get or create BART classifier instance."""
    global bart_classifier
    if bart_classifier is None:
        print("Creating BART classifier instance...")
        bart_classifier = BartDocumentClassifier()
        print("BART classifier created successfully")
    return bart_classifier

def cleanup_on_exit():
    """Cleanup resources on application exit."""
    global bart_classifier
    if bart_classifier:
        print("Application exit - cleaning up classifier")
        bart_classifier.cleanup()

atexit.register(cleanup_on_exit)
