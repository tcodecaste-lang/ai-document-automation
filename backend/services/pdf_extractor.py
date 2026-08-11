# backend/services/pdf_extractor.py

import fitz  # PyMuPDF
from fastapi import HTTPException, status

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts text content from PDF bytes using PyMuPDF (fitz).
    Raises HTTPException if extraction fails or if the text is empty/uncaught.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse PDF document. Ensure it is a valid PDF. Error: {str(e)}"
        )
    
    if len(doc) == 0:
        doc.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The PDF file has 0 pages (empty PDF)."
        )
        
    text = ""
    for page in doc:
        page_text = page.get_text()
        if page_text:
            text += page_text + "\n"
            
    doc.close()
    
    cleaned_text = text.strip()
    if not cleaned_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No readable text could be extracted from the PDF. Scanned images/OCR are not supported."
        )
        
    return cleaned_text
