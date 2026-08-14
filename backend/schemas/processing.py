# backend/schemas/processing.py

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class FieldValidation(BaseModel):
    valid: bool = Field(..., description="Whether the field passed all deterministic checks")
    message: str = Field(..., description="Details regarding field validation result")

class DocumentProcessResponse(BaseModel):
    success: bool = Field(..., description="Overall request status flag")
    industry: str = Field(..., description="The chosen industry schema used for extraction")
    document_type: str = Field(..., description="The matching document type tag")
    file_name: str = Field(..., description="The name of the processed file")
    extracted_data: Dict[str, Any] = Field(..., description="Structured JSON key-value extraction results from OpenAI")
    extracted_fields: Optional[Dict[str, Any]] = Field(None, description="Detailed field extraction metadata containing value and applicability rules")
    validation: Dict[str, FieldValidation] = Field(..., description="Field-by-field validation results")
    overall_status: str = Field(..., description="Aggregated validation status: ready_for_review or needs_review")
    ai_provider: Optional[str] = Field(None, description="The name of the AI engine used to process the document")
    id: Optional[str] = Field(None, description="The stored database document identifier")

class ErrorResponse(BaseModel):
    success: bool = Field(False)
    error: str = Field(..., description="A user-friendly, human-readable error description")

class GeneratePdfRequest(BaseModel):
    file_name: str = Field(..., description="The name of the original file")
    industry: str = Field(..., description="Target industry")
    document_type: str = Field(..., description="Document type")
    extracted_data: Dict[str, Any] = Field(..., description="Merged final key-value pairs")
    validation: Dict[str, FieldValidation] = Field(..., description="Validation results")
    overall_status: str = Field(..., description="Overall status")
    original_data: Dict[str, Any] = Field(..., description="Original extracted key-value pairs")

class CombinedReportRequest(BaseModel):
    items: List[GeneratePdfRequest] = Field(..., description="List of all successfully processed documents in the session")

# Authentication schemas
class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: str = Field(...)
    password: str = Field(..., min_length=6)
    confirm_password: str = Field(...)

class UserLoginRequest(BaseModel):
    email: str = Field(...)
    password: str = Field(...)

class AuthResponse(BaseModel):
    success: bool
    token: str
    name: str
    email: str
    role: str

# Dynamic Fields schemas
class FieldCreateRequest(BaseModel):
    name: str = Field(...)
    label: str = Field(...)
    industry: str = Field(...)
    document_type: str = Field(...)
    field_type: str = Field(...)
    required: bool = Field(False)
    active: bool = Field(True)
    display_order: int = Field(0)
    validation_rules: Optional[str] = Field("{}")

class FieldUpdateRequest(BaseModel):
    label: str = Field(...)
    field_type: str = Field(...)
    required: bool = Field(False)
    active: bool = Field(True)
    display_order: int = Field(0)
    validation_rules: Optional[str] = Field("{}")
    industry: Optional[str] = Field(None)
    document_type: Optional[str] = Field(None)

# Document Manual Update schema
class DocumentUpdateRequest(BaseModel):
    id: str = Field(..., description="The unique document identifier")
    extracted_data: Dict[str, Any] = Field(..., description="Manually edited key-value fields")

# Email Send schema
class SendEmailRequest(BaseModel):
    recipient_email: str = Field(...)
    items: List[GeneratePdfRequest] = Field(...)
