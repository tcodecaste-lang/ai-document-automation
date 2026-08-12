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
