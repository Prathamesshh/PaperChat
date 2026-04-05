from pypdf import PdfReader
from pathlib import Path
from typing import Optional, Dict, List
from pydantic import BaseModel
import logging
import re

logger = logging.getLogger(__name__)

class PageContent(BaseModel):
    page_number: int
    text: str
    word_count: int

class PDFMetadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None

class PDFContent(BaseModel):
    text: str
    pages: List[PageContent]
    metadata: PDFMetadata
    page_count: int
    total_word_count: int
    abstract: Optional[str] = None
    references: Optional[str] = None

class PDFParserError(Exception):
    """Custom exception for PDF parsing errors."""
    pass

def clean_text(text: str) -> str:
    """Clean and normalize extracted text."""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()
    return text

def extract_section(text: str, section_name: str) -> Optional[str]:
    """Extract a specific section from the PDF text."""
    patterns = {
        'abstract': r'(?i)(abstract|summary)\s*[:.\-]?\s*(.*?)(?=\n\s*(?:introduction|keywords|1\.?\s+introduction|\Z))',
        'references': r'(?i)(?:references|bibliography|works cited)\s*[:.\-]?\s*(.*?)(?=\Z)',
    }
    
    if section_name.lower() not in patterns:
        return None
    
    match = re.search(patterns[section_name.lower()], text, re.DOTALL | re.MULTILINE)
    if match:
        section_text = match.group(2) if len(match.groups()) > 1 else match.group(1)
        return clean_text(section_text)[:2000]  # Limit to first 2000 chars
    return None

def extract_metadata(reader: PdfReader) -> PDFMetadata:
    """Extract PDF metadata."""
    try:
        meta = reader.metadata if reader.metadata else {}
        return PDFMetadata(
            title=meta.get('/Title', None),
            author=meta.get('/Author', None),
            subject=meta.get('/Subject', None),
            creator=meta.get('/Creator', None),
            producer=meta.get('/Producer', None),
            creation_date=str(meta.get('/CreationDate', None)) if meta.get('/CreationDate') else None
        )
    except Exception as e:
        logger.warning(f"Error extracting metadata: {e}")
        return PDFMetadata()

def extract_text(pdf_path: str) -> PDFContent:
    """
    Extract comprehensive content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        PDFContent object with text, metadata, and analysis
        
    Raises:
        PDFParserError: If PDF cannot be parsed
    """
    try:
        pdf_file = Path(pdf_path)
        
        if not pdf_file.exists():
            raise PDFParserError(f"PDF file not found: {pdf_path}")
        
        if not pdf_file.is_file():
            raise PDFParserError(f"Path is not a file: {pdf_path}")
        
        if pdf_file.stat().st_size == 0:
            raise PDFParserError(f"PDF file is empty: {pdf_path}")
        
        logger.info(f"Parsing PDF: {pdf_path}")
        
        reader = PdfReader(str(pdf_file))
        
        if len(reader.pages) == 0:
            raise PDFParserError(f"PDF has no pages: {pdf_path}")
        
        metadata = extract_metadata(reader)
        
        pages_content = []
        full_text = ""
        
        for page_num, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text()
                cleaned_text = clean_text(page_text)
                word_count = len(cleaned_text.split())
                
                pages_content.append(PageContent(
                    page_number=page_num,
                    text=cleaned_text,
                    word_count=word_count
                ))
                
                full_text += cleaned_text + "\n\n"
                
            except Exception as e:
                logger.warning(f"Error extracting page {page_num}: {e}")
                pages_content.append(PageContent(
                    page_number=page_num,
                    text="[Error extracting page content]",
                    word_count=0
                ))
        
        full_text = clean_text(full_text)
        total_words = len(full_text.split())
        
        abstract = extract_section(full_text, 'abstract')
        references = extract_section(full_text, 'references')
        
        logger.info(f"Successfully parsed {len(pages_content)} pages, {total_words} words")
        
        return PDFContent(
            text=full_text,
            pages=pages_content,
            metadata=metadata,
            page_count=len(pages_content),
            total_word_count=total_words,
            abstract=abstract,
            references=references
        )
        
    except PDFParserError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing PDF {pdf_path}: {e}")
        raise PDFParserError(f"Failed to parse PDF: {str(e)}")

def extract_text_simple(pdf_path: str) -> str:
    """
    Simple text extraction (backward compatible).
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as string
    """
    result = extract_text(pdf_path)
    return result.text