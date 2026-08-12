# backend/api/endpoints.py

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from fastapi.responses import StreamingResponse
import io
from backend.schemas.processing import DocumentProcessResponse, ErrorResponse, GeneratePdfRequest, CombinedReportRequest
from backend.config.industries import INDUSTRIES
from backend.services.pdf_extractor import extract_text_from_pdf
from backend.services.openai_service import extract_document_info
from backend.services.pdf_generator import generate_validated_summary_pdf, generate_combined_summary_report_pdf
from backend.validators.deterministic import validate_extracted_data

router = APIRouter()

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

@router.post(
    "/process-document",
    response_model=DocumentProcessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file, industry, or extraction failure"},
        500: {"model": ErrorResponse, "description": "Internal server/dependency error"}
    }
)
async def process_document(
    industry: str = Form(..., description="Target industry schema ('insurance', 'finance', 'healthcare')"),
    file: UploadFile = File(..., description="PDF document to process")
):
    # 1. Validate Industry Choice
    industry_lower = industry.lower().strip()
    if industry_lower not in INDUSTRIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported industry '{industry}'. Choose from: {', '.join(INDUSTRIES.keys())}."
        )
        
    # 2. Validate File Content Type (PDF only)
    # Some browsers/clients might not report the application/pdf mime type properly, 
    # but we check both filename extension and content type for safety.
    filename = file.filename or "uploaded_file.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )
        
    # 3. Read bytes & check size limit (10MB)
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file contents: {str(e)}"
        )
        
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF file must be 10 MB or smaller."
        )
        
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PDF file is empty."
        )
        
    # 4. Extract Plain Text
    extracted_text = extract_text_from_pdf(file_bytes)
    
    # 5. Extract Structured JSON via OpenAI/Gemini
    extracted_data = extract_document_info(industry_lower, extracted_text)
    
    # 6. Apply Deterministic Validation Rules
    validation_results, overall_status = validate_extracted_data(industry_lower, extracted_data)
    
    # Determine document type dynamically from AI output
    detected_doc_type = extracted_data.get("document_type") if isinstance(extracted_data, dict) else None
    if not detected_doc_type:
        detected_doc_type = INDUSTRIES[industry_lower]["document_type"]
        
    # Flatten the extracted values for the frontend raw table display (backwards compatible)
    nested_fields = extracted_data.get("extracted_fields") if isinstance(extracted_data, dict) else None
    flat_data = {}
    if nested_fields:
        for k, v in nested_fields.items():
            if isinstance(v, dict):
                flat_data[k] = v.get("value")
            else:
                flat_data[k] = v
    else:
        flat_data = extracted_data
        
    # 7. Construct Final Response
    return DocumentProcessResponse(
        success=True,
        industry=industry_lower,
        document_type=detected_doc_type,
        file_name=filename,
        extracted_data=flat_data,
        extracted_fields=nested_fields,
        validation=validation_results,
        overall_status=overall_status
    )

@router.post(
    "/generate-pdf",
    responses={
        400: {"model": ErrorResponse, "description": "Failed to generate PDF"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def generate_pdf(request_data: GeneratePdfRequest):
    try:
        validation_dict = {
            k: {"valid": v.valid, "message": v.message}
            for k, v in request_data.validation.items()
        }
        
        pdf_bytes = generate_validated_summary_pdf(
            original_filename=request_data.file_name,
            industry=request_data.industry,
            document_type=request_data.document_type,
            extracted_data=request_data.extracted_data,
            validation=validation_dict,
            overall_status=request_data.overall_status,
            original_data=request_data.original_data
        )
        
        stream = io.BytesIO(pdf_bytes)
        
        base_name = request_data.file_name
        if base_name.lower().endswith(".pdf"):
            base_name = base_name[:-4]
        download_name = f"{base_name}-updated.pdf"
        
        return StreamingResponse(
            stream,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={download_name}"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate updated PDF summary copy: {str(e)}"
        )

@router.post(
    "/generate-combined-report",
    responses={
        400: {"model": ErrorResponse, "description": "Failed to generate combined report"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def generate_combined_report(request_data: CombinedReportRequest):
    try:
        if not request_data.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No items provided to generate combined report."
            )
            
        pdf_bytes = generate_combined_summary_report_pdf(request_data.items)
        stream = io.BytesIO(pdf_bytes)
        
        return StreamingResponse(
            stream,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=processed_documents_report.pdf"
            }
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate combined processed documents report: {str(e)}"
        )
