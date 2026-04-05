from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
import logging
from pathlib import Path
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PaperChat", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("data/uploaded_papers")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024 
ALLOWED_EXTENSIONS = {".pdf"}

class UploadResponse(BaseModel):
    message: str
    filename: str
    file_path: str
    file_size: int

def sanitize_filename(filename: str) -> str:
    """Remove path traversal attempts and dangerous characters."""
    name = os.path.basename(filename)
    name = "".join(c for c in name if c.isalnum() or c in "._- ")
    return name.strip()

def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename to prevent conflicts."""
    sanitized = sanitize_filename(original_filename)
    name, ext = os.path.splitext(sanitized)
    unique_id = uuid.uuid4().hex[:8]
    return f"{name}_{unique_id}{ext}"

@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Only PDF files are allowed."
            )
        
        contents = await file.read()
        file_size = len(contents)
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        if not contents.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="File is not a valid PDF")
        
        unique_filename = generate_unique_filename(file.filename)
        file_location = UPLOAD_DIR / unique_filename
        
        with open(file_location, "wb") as buffer:
            buffer.write(contents)
        
        logger.info(f"File uploaded successfully: {unique_filename} ({file_size} bytes)")
        
        return UploadResponse(
            message="File uploaded successfully",
            filename=unique_filename,
            file_path=str(file_location),
            file_size=file_size
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "PaperChat"}