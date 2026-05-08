from fastapi import UploadFile, HTTPException
import io
import docx
import pdfplumber
from PIL import Image
import pytesseract

ALLOWED_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/jpeg",
    "image/png"
]

    
def extract_text(file: UploadFile) -> str:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    content = file.file.read() if hasattr(file.file, 'read') else file.read()
    text = ""
    if file.content_type == "application/pdf":
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        if not text.strip():
            raise HTTPException(status_code=422, detail="No text found in PDF.")
    elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(io.BytesIO(content))
        text = "\n".join([para.text for para in doc.paragraphs])
        if not text.strip():
            raise HTTPException(status_code=422, detail="No text found in Word document.")
    elif file.content_type == "text/plain":
        text = content.decode("utf-8")
        if not text.strip():
            raise HTTPException(status_code=422, detail="No text found in text file.")
    elif file.content_type in ["image/jpeg", "image/png"]:
        image = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(image)
        if not text.strip():
            raise HTTPException(status_code=422, detail="No text found in image.")
    return text
