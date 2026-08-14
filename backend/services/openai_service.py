# backend/services/openai_service.py

import os
import json
import logging
from openai import OpenAI
from fastapi import HTTPException, status
from backend.services.ai_provider import AIProviderManager

import re

logger = logging.getLogger("openai_service")
logger.setLevel(logging.INFO)

def classify_document_type(industry: str, text: str) -> str:
    """
    Identifies the specific document type for the selected industry.
    Queries active configured types from the fields database, asks the AI to classify,
    and falls back to rule-based keyword mapping if AI calls fail.
    """
    from backend.services.database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT document_type FROM fields WHERE industry = ? AND active = 1", (industry,))
        configured_types = [row["document_type"] for row in cursor.fetchall()]
        
    if not configured_types:
        if industry == "insurance":
            return "vehicle_insurance_claim"
        elif industry == "finance":
            return "expense_receipt"
        else:
            return "patient_registration"
            
    types_list = ", ".join(configured_types)
    system_prompt = (
        "You are a precise document classifier.\n"
        f"Analyze the document text and identify which document type it is for the '{industry}' industry.\n"
        f"Choose from the following configured document types: {types_list}.\n"
        "You MUST return that exact matching string (e.g. 'vehicle_insurance_claim').\n"
        "If it is a completely new or different document type, return a short snake_case name for it (e.g. 'medical_bill').\n"
        "Return ONLY the string of the document type (no markdown, no quotes, no extra text)."
    )
    
    user_prompt = f"Document text:\n{text[:2000]}"
    
    try:
        schema = {
            "name": "document_classifier",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "document_type": {
                        "type": "string",
                        "description": "The classified document type label in snake_case"
                    }
                },
                "required": ["document_type"],
                "additionalProperties": False
            }
        }
        
        result = AIProviderManager.extract(
            industry=industry,
            text=text[:2000],
            response_schema=schema,
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        doc_type = result.get("document_type", "").strip().lower()
        if doc_type:
            return doc_type
    except Exception as e:
        logger.warning(f"[AI] Document classification call failed: {str(e)}. Falling back to keyword search.")
        
    # Keyword-based fallback classifier
    text_lower = text.lower()
    if industry == "insurance":
        if any(kw in text_lower for kw in ["health", "medical", "patient", "treatment"]):
            return "health_insurance_claim"
        return "vehicle_insurance_claim"
    elif industry == "finance":
        if any(kw in text_lower for kw in ["hotel", "stay", "guest", "check-in"]):
            return "hotel_expense"
        return "expense_receipt"
    elif industry == "healthcare":
        if any(kw in text_lower for kw in ["bill", "invoice", "total amount", "charge"]):
            return "medical_bill"
        return "patient_registration"
        
    return configured_types[0]

def build_json_schema_dynamic(document_type: str, fields: list) -> dict:
    """Builds a dynamic JSON schema based on database field configurations."""
    properties = {}
    required_keys = []
    
    for field in fields:
        field_name = field["name"]
        field_type = field["field_type"]
        description = f"Extracted value for {field['label']}"
        
        if field_type in ("number", "currency"):
            val_type = ["number", "null"]
        else:
            val_type = ["string", "null"]
            
        properties[field_name] = {
            "type": "object",
            "properties": {
                "value": {
                    "type": val_type,
                    "description": description
                },
                "applicable": {
                    "type": "boolean",
                    "description": f"True if the field '{field_name}' is applicable to this specific document layout, False otherwise."
                }
            },
            "required": ["value", "applicable"],
            "additionalProperties": False
        }
        required_keys.append(field_name)
        
    return {
        "name": "document_scanner",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "document_type": {
                    "type": "string",
                    "description": f"Specific type of the document (should be '{document_type}')"
                },
                "extracted_fields": {
                    "type": "object",
                    "properties": properties,
                    "required": required_keys,
                    "additionalProperties": False
                }
            },
            "required": ["document_type", "extracted_fields"],
            "additionalProperties": False
        }
    }

def mock_extraction_fallback_dynamic(industry: str, text: str, document_type: str, fields: list) -> dict:
    """Dynamic fallback parser that matches active DB fields using regex lookups."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    extracted_fields = {}
    
    for field in fields:
        field_name = field["name"]
        field_label = field["label"]
        field_type = field["field_type"]
        
        aliases = [
            field_name.lower(),
            field_name.replace('_', ' ').lower(),
            field_label.lower(),
            field_label.replace('/', ' ').replace('-', ' ').lower()
        ]
        
        val = None
        for i, line in enumerate(lines):
            matched_alias = None
            for alias in aliases:
                pattern = rf"\b{re.escape(alias)}\s*:?$"
                if re.search(pattern, line, re.IGNORECASE):
                    matched_alias = alias
                    break
                    
            if matched_alias:
                if i + 1 < len(lines):
                    val = lines[i + 1]
                break
                
            for alias in aliases:
                pattern = rf"\b{re.escape(alias)}\s*:\s*(.+)$"
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    val = match.group(1).strip()
                    break
            if val:
                break
                
        if val is not None:
            if field_type in ("number", "currency"):
                clean_num = val.replace("$", "").replace(",", "").strip()
                try:
                    val = float(clean_num)
                except ValueError:
                    pass
            if isinstance(val, str) and val.strip() in ["[missing]", "N/A", "empty", "null"]:
                val = None
                
        extracted_fields[field_name] = {
            "value": val,
            "applicable": True
        }
        
    return {
        "document_type": document_type,
        "extracted_fields": extracted_fields
    }

def mock_extraction_fallback(industry: str, text: str) -> dict:
    """Backward-compatible fallback extraction wrapper used by tests."""
    from backend.services.database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, label, industry, document_type, field_type, required, active, display_order, validation_rules "
            "FROM fields WHERE industry = ? AND active = 1 "
            "ORDER BY display_order ASC",
            (industry,)
        )
        fields = [dict(row) for row in cursor.fetchall()]
    doc_type = classify_document_type(industry, text)
    return mock_extraction_fallback_dynamic(industry, text, doc_type, fields)

def extract_document_info_dynamic(industry: str, text: str, document_type: str, fields: list) -> dict:
    """Invokes the AI provider manager with the dynamic field schema."""
    if not fields:
        return {
            "document_type": document_type,
            "extracted_fields": {}
        }
        
    response_schema = build_json_schema_dynamic(document_type, fields)
    
    fields_list = ", ".join(f["name"] for f in fields)
    system_prompt = (
        "You are a precise document scanner and information extractor.\n"
        f"Analyze the document text for the '{industry}' industry, classified as document type '{document_type}'.\n"
        f"1. For each expected field in the schema ({fields_list}), check if that field is applicable or relevant to this specific type of document layout.\n"
        "2. Extract the value if present. If applicable but the information is missing from the document, set value=null and applicable=true.\n"
        "3. Do not invent, guess, or fabricate any details. Keep values null if not explicitly in the text."
    )
    
    user_prompt = f"Document text:\n{text}"
    
    try:
        return AIProviderManager.extract(
            industry=industry,
            text=text,
            response_schema=response_schema,
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.warning(f"[AI] AI extraction call failed: {str(e)}. Falling back to regex engine.")
        data = mock_extraction_fallback_dynamic(industry, text, document_type, fields)
        if isinstance(data, dict):
            data["ai_provider"] = "Offline Engine (Regex)"
        return data

def extract_document_info(industry: str, text: str) -> dict:
    """
    Main entry point for document extraction.
    Dynamically classifies document type, loads applicable database fields,
    builds the extraction schema, and queries the AI fallback pipeline.
    """
    doc_type = classify_document_type(industry, text)
    
    from backend.services.database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, label, industry, document_type, field_type, required, active, display_order, validation_rules "
            "FROM fields WHERE industry = ? AND document_type = ? AND active = 1 "
            "ORDER BY display_order ASC",
            (industry, doc_type)
        )
        fields = [dict(row) for row in cursor.fetchall()]
        
    if not fields:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, label, industry, document_type, field_type, required, active, display_order, validation_rules "
                "FROM fields WHERE industry = ? AND active = 1 "
                "ORDER BY display_order ASC",
                (industry,)
            )
            fields = [dict(row) for row in cursor.fetchall()]
            
    data = extract_document_info_dynamic(industry, text, doc_type, fields)
    
    if isinstance(data, dict):
        data["document_type"] = doc_type
    return data
