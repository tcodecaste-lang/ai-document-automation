# backend/api/endpoints.py

import io
import json
import uuid
import re
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status, Depends
from fastapi.responses import StreamingResponse

from backend.schemas.processing import (
    DocumentProcessResponse,
    ErrorResponse,
    GeneratePdfRequest,
    CombinedReportRequest,
    UserRegisterRequest,
    UserLoginRequest,
    AuthResponse,
    FieldCreateRequest,
    FieldUpdateRequest,
    DocumentUpdateRequest,
    SendEmailRequest
)
from backend.services.pdf_extractor import extract_text_from_pdf
from backend.services.openai_service import extract_document_info, classify_document_type
from backend.services.pdf_generator import generate_validated_summary_pdf, generate_combined_summary_report_pdf
from backend.validators.deterministic import validate_extracted_data

from backend.services.database import get_db
from backend.services.auth import (
    hash_password,
    verify_password,
    generate_token,
    get_current_user,
    require_admin
)
from backend.services.email import send_combined_report_email

router = APIRouter()

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# =====================================================================
# AUTHENTICATION ENDPOINTS
# =====================================================================

@router.post(
    "/auth/register",
    responses={
        400: {"model": ErrorResponse, "description": "Validation or email duplicate error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def register(req: UserRegisterRequest):
    # 1. Validate fields
    email_clean = req.email.strip().lower()
    name_clean = req.name.strip()
    
    if not name_clean or not email_clean or not req.password:
        raise HTTPException(status_code=400, detail="All registration fields are required.")
        
    # Email regex verification
    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_pattern, email_clean):
        raise HTTPException(status_code=400, detail="Invalid email address format.")
        
    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
        
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
        
    # 2. Check if user already exists
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail="An account with this email address already exists."
            )
            
        # 3. Insert user (default role is 'user')
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (name_clean, email_clean, hash_password(req.password), "user")
        )
        conn.commit()
        
    return {"success": True, "message": "Registration successful. You can now login."}

@router.post(
    "/auth/login",
    response_model=AuthResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid email or password"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def login(req: UserLoginRequest):
    email_clean = req.email.strip().lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, password_hash, role FROM users WHERE email = ?", (email_clean,))
        row = cursor.fetchone()
        
    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )
        
    token = generate_token({
        "user_id": row["id"],
        "email": row["email"],
        "role": row["role"]
    })
    
    return AuthResponse(
        success=True,
        token=token,
        name=row["name"],
        email=row["email"],
        role=row["role"]
    )

@router.get("/auth/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user

# =====================================================================
# DYNAMIC FIELDS MANAGEMENT ENDPOINTS (ADMIN ONLY)
# =====================================================================

@router.get("/fields")
async def list_fields(current_user: Dict[str, Any] = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fields WHERE user_id IS NULL OR user_id = ? ORDER BY display_order ASC, name ASC", (current_user["id"],))
        rows = cursor.fetchall()
    return [dict(r) for r in rows]

@router.post("/fields", status_code=status.HTTP_201_CREATED)
async def create_field(req: FieldCreateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    name_clean = req.name.strip().lower().replace(" ", "_")
    
    # Validation rules parsing check
    try:
        if req.validation_rules:
            json.loads(req.validation_rules)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON object in validation_rules field.")
        
    with get_db() as conn:
        cursor = conn.cursor()
        # Verify uniqueness per industry and user (so user 1 and user 2 can create fields with same name without colliding!)
        cursor.execute("SELECT id FROM fields WHERE name = ? AND industry = ? AND (user_id IS NULL OR user_id = ?)", (name_clean, req.industry, current_user["id"]))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"A field with name '{name_clean}' already exists in industry '{req.industry}'.")
            
        cursor.execute(
            "INSERT INTO fields (name, label, industry, document_type, field_type, required, active, display_order, validation_rules, user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name_clean, req.label, req.industry, req.document_type, req.field_type, int(req.required), int(req.active), req.display_order, req.validation_rules, current_user["id"])
        )
        conn.commit()
        
    return {"success": True, "message": "Dynamic field created successfully."}

@router.put("/fields/{field_id}")
async def update_field(field_id: int, req: FieldUpdateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        if req.validation_rules:
            json.loads(req.validation_rules)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON object in validation_rules field.")
        
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id FROM fields WHERE id = ?", (field_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dynamic field not found.")
        if row["user_id"] != current_user["id"] and current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="You do not have permission to modify this field.")
            
        cursor.execute(
            "UPDATE fields SET label = ?, field_type = ?, required = ?, active = ?, display_order = ?, validation_rules = ?, industry = COALESCE(?, industry), document_type = COALESCE(?, document_type), updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?",
            (req.label, req.field_type, int(req.required), int(req.active), req.display_order, req.validation_rules, req.industry, req.document_type, field_id)
        )
        conn.commit()
        
    return {"success": True, "message": "Dynamic field updated successfully."}

@router.delete("/fields/{field_id}")
async def toggle_field_active(field_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Deletes/toggles dynamic field active status."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT active, user_id FROM fields WHERE id = ?", (field_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dynamic field not found.")
        if row["user_id"] != current_user["id"] and current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="You do not have permission to delete this field.")
            
        new_status = 0 if row["active"] else 1
        cursor.execute("UPDATE fields SET active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, field_id))
        conn.commit()
        
    status_label = "disabled" if new_status == 0 else "enabled"
    return {"success": True, "message": f"Dynamic field status toggled to {status_label}."}

# =====================================================================
# DOCUMENT PROCESSING ENDPOINTS
# =====================================================================

@router.get("/documents")
async def list_documents(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve all processed documents belonging to the authenticated user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE user_id = ? ORDER BY created_at DESC", (current_user["id"],))
        rows = cursor.fetchall()
        
    res = []
    for r in rows:
        d = dict(r)
        d["extracted_data"] = json.loads(d["extracted_data"])
        d["extracted_fields"] = json.loads(d["extracted_fields"]) if d["extracted_fields"] else {}
        d["validation"] = json.loads(d["validation"])
        d["original_data"] = json.loads(d["original_data"])
        res.append(d)
    return res

@router.post(
    "/process-document",
    response_model=DocumentProcessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file, industry, or extraction failure"},
        401: {"model": ErrorResponse, "description": "Authentication failure"},
        500: {"model": ErrorResponse, "description": "Internal server/dependency error"}
    }
)
async def process_document(
    industry: str = Form(..., description="Target industry schema ('insurance', 'finance', 'healthcare')"),
    file: UploadFile = File(..., description="PDF document to process"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    industry_lower = industry.lower().strip()
    if industry_lower not in ("insurance", "finance", "healthcare"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported industry '{industry}'. Choose from: insurance, finance, healthcare."
        )
    
    # Verification checks
    filename = file.filename or "uploaded_file.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file contents: {str(e)}")
        
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="PDF file must be 10 MB or smaller.")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="The uploaded PDF file is empty.")
        
    # Extract plain text
    extracted_text = extract_text_from_pdf(file_bytes)
    
    # Dynamic classification and dynamic field extraction
    extracted_data = extract_document_info(industry_lower, extracted_text)
    
    # Dynamic deterministic validation checks
    validation_results, overall_status = validate_extracted_data(industry_lower, extracted_data)
    
    detected_doc_type = extracted_data.get("document_type", "Unknown")
    
    # Normalizing extracted fields values (flat dictionary)
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
        
    # 7. Generate UUID and persist document
    doc_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO documents (id, user_id, file_name, industry, document_type, overall_status, extracted_data, extracted_fields, validation, original_data, ai_provider) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                doc_id,
                current_user["id"],
                filename,
                industry_lower,
                detected_doc_type,
                overall_status,
                json.dumps(flat_data),
                json.dumps(nested_fields),
                json.dumps(validation_results),
                json.dumps(flat_data),  # Store flat_data as original_data too
                extracted_data.get("ai_provider", "Gemini")
            )
        )
        conn.commit()
        
    return DocumentProcessResponse(
        success=True,
        id=doc_id,
        industry=industry_lower,
        document_type=detected_doc_type,
        file_name=filename,
        extracted_data=flat_data,
        extracted_fields=nested_fields,
        validation=validation_results,
        overall_status=overall_status,
        ai_provider=extracted_data.get("ai_provider")
    )

@router.post(
    "/documents/update",
    response_model=DocumentProcessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation or format errors"},
        403: {"model": ErrorResponse, "description": "Not authorized to access document"},
        404: {"model": ErrorResponse, "description": "Document not found"}
    }
)
async def update_document(req: DocumentUpdateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Saves manually corrected document values, re-validates dynamically, and updates SQLite records."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (req.id,))
        row = cursor.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Document record not found.")
        
    # Security check: User account data isolation
    if row["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Unauthorized access. User data is isolated.")
        
    # Recheck dynamic validation with newly submitted user corrections
    original_extracted_fields = json.loads(row["extracted_fields"]) if row["extracted_fields"] else {}
    
    # Rebuild nested layout format
    updated_extracted_fields = {}
    for field_name, value in req.extracted_data.items():
        orig_entry = original_extracted_fields.get(field_name, {})
        applicable = orig_entry.get("applicable", True) if isinstance(orig_entry, dict) else True
        updated_extracted_fields[field_name] = {
            "value": value,
            "applicable": applicable
        }
        
    payload_to_validate = {
        "document_type": row["document_type"],
        "extracted_fields": updated_extracted_fields
    }
    
    validation_results, overall_status = validate_extracted_data(row["industry"], payload_to_validate)
    
    # Save updates back to DB
    with get_db() as conn:
        conn.execute(
            "UPDATE documents SET extracted_data = ?, extracted_fields = ?, validation = ?, overall_status = ? "
            "WHERE id = ?",
            (
                json.dumps(req.extracted_data),
                json.dumps(updated_extracted_fields),
                json.dumps(validation_results),
                overall_status,
                req.id
            )
        )
        conn.commit()
        
    return DocumentProcessResponse(
        success=True,
        id=req.id,
        industry=row["industry"],
        document_type=row["document_type"],
        file_name=row["file_name"],
        extracted_data=req.extracted_data,
        extracted_fields=updated_extracted_fields,
        validation=validation_results,
        overall_status=overall_status,
        ai_provider=row["ai_provider"]
    )

# =====================================================================
# PDF REPORT & EMAIL DOWNLOAD ENDPOINTS
# =====================================================================

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
async def generate_combined_report(request_data: CombinedReportRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
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

@router.post(
    "/send-email",
    responses={
        400: {"model": ErrorResponse, "description": "Failed to email report"},
        401: {"model": ErrorResponse, "description": "Authentication failure"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def send_report_email(req: SendEmailRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    email_clean = req.recipient_email.strip().lower()
    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_pattern, email_clean):
        raise HTTPException(status_code=400, detail="Invalid recipient email address format.")
        
    if not req.items:
        raise HTTPException(status_code=400, detail="No processed documents provided to generate email report.")
        
    try:
        # Generate the exact same combined report PDF bytes
        pdf_bytes = generate_combined_summary_report_pdf(req.items)
        
        # Dispatch via SMTP backend service
        send_combined_report_email(email_clean, pdf_bytes)
        return {"success": True, "message": "Processed report PDF has been emailed successfully."}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deliver report email: {str(e)}"
        )
