# backend/services/openai_service.py

import os
import json
from openai import OpenAI
from fastapi import HTTPException, status
from backend.config.industries import INDUSTRIES

import re

def get_openai_client() -> OpenAI:
    # Use GEMINI_API_KEY if defined, or check if OPENAI_API_KEY starts with Gemini's prefix
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    # Auto-detect Gemini key type from value
    is_gemini = False
    api_key = None
    
    if gemini_key:
        api_key = gemini_key
        is_gemini = True
    elif openai_key:
        api_key = openai_key
        if openai_key.strip().startswith("AIzaSy"):
            is_gemini = True
            
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key is missing. Please set either OPENAI_API_KEY or GEMINI_API_KEY in backend/.env."
        )
        
    if is_gemini:
        # Route to Google's official OpenAI compatibility endpoint for Gemini
        return OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        
    return OpenAI(api_key=api_key)

def build_json_schema(industry: str, fields_config: dict) -> dict:
    """
    Builds a JSON schema compatible with OpenAI's structured outputs.
    All fields in config are marked required in the schema, but allow nulls 
    if they cannot be found in the document text.
    """
    properties = {}
    required_keys = []
    
    for field_name, field_info in fields_config.items():
        field_type = field_info["type"]
        description = field_info.get("description", f"Extracted {field_name.replace('_', ' ')}")
        
        # Map config types to JSON schema types (allowing null)
        if field_type == "number":
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
                    "description": "Specific type of the document identified (e.g. Life Insurance Policy, Health Insurance Claim, Receipt, Patient Registration Form)"
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

def mock_extraction_fallback(industry: str, text: str) -> dict:
    """
    Locally parses document text using regular expressions.
    Acts as a free fallback if OpenAI API calls fail.
    Supports same-line values and consecutive-line values from layout shifts.
    """
    # Clean and list non-empty lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Custom regex aliases for each field to ensure match resilience
    field_lookups = {
        "customer_name": ["customer name", "customer", "claimant", "applicant name", "applicant", "insured name", "insured", "policyholder name", "policyholder"],
        "policy_number": ["policy number", "policy code", "policy no", "policy #"],
        "policy_type": ["policy type", "type of policy", "coverage type", "plan type"],
        "policy_start_date": ["policy start date", "start date", "effective date", "commencement date"],
        "policy_end_date": ["policy end date", "end date", "expiration date", "expiry date"],
        "coverage_amount": ["coverage amount", "coverage", "sum insured", "insured amount", "limit", "limit of liability"],
        "accident_date": ["accident date", "incident date", "date of accident", "date of occurrence"],
        "claim_type": ["claim type", "incident type", "type of claim"],
        
        "employee_name": ["employee name", "staff name", "submitted by", "employee"],
        "merchant_name": ["merchant name", "merchant", "vendor name", "vendor", "store name", "store"],
        "amount": ["amount", "total", "cost", "price", "sum", "expense amount", "total amount"],
        "date": ["date", "receipt date", "expense date", "transaction date", "date of expense", "purchased date"],
        "category": ["category", "expense type", "category type", "expense category", "class"],
        
        "patient_name": ["patient name", "member name", "patient"],
        "date_of_birth": ["date of birth", "dob", "birthdate", "birth date", "d.o.b.", "patient dob"],
        "hospital_name": ["hospital name", "hospital", "healthcare provider name", "provider name", "clinic name", "clinic"],
        "appointment_type": ["appointment type", "consultation type", "visit type", "reason for visit"],
        "appointment_date": ["appointment date", "visit date", "scheduled date", "date of appointment", "date of visit"]
    }
    
    # Identify document type
    text_lower = text.lower()
    doc_type_detected = "Unknown"
    is_claim = False
    
    if industry == "insurance":
        is_claim = any(kw in text_lower for kw in ["claim", "accident", "incident", "damage", "collision", "theft", "loss"])
        has_accident_policy_type = any(kw in text_lower for kw in ["travel insurance", "personal accident insurance", "motor/auto insurance", "health insurance", "travel", "personal accident", "motor", "auto", "health"])
        is_accident_related = is_claim or has_accident_policy_type
        doc_type_detected = "Insurance Claim Form" if is_claim else "Insurance Policy Schedule"
    elif industry == "finance":
        doc_type_detected = "Expense Receipt" if "receipt" in text_lower or "invoice" in text_lower else "Expense Claim"
    elif industry == "healthcare":
        doc_type_detected = "Patient Registration Form"
        
    extracted_fields = {}
    fields = INDUSTRIES[industry]["fields"]
    
    for field_name, field_info in fields.items():
        applicable = True
        
        # For insurance, accident_date is always applicable (representing accident/incident date)
            
        if not applicable:
            extracted_fields[field_name] = {
                "value": None,
                "applicable": False
            }
            continue
            
        val = None
        aliases = field_lookups.get(field_name, [field_name.replace('_', ' ')])
        
        for i, line in enumerate(lines):
            matched_alias = None
            for alias in aliases:
                pattern = rf"\b{re.escape(alias)}\s*:?$"
                if re.search(pattern, line, re.IGNORECASE):
                    matched_alias = alias
                    break
                    
            if matched_alias:
                # Value is on the next line
                if i + 1 < len(lines):
                    val = lines[i + 1]
                break
                
            # Otherwise check if it is on the same line after a colon
            for alias in aliases:
                pattern = rf"\b{re.escape(alias)}\s*:\s*(.+)$"
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    val = match.group(1).strip()
                    break
            if val:
                break
                
        # Handle decimal formats for amount field
        if val is not None:
            if field_info["type"] == "number":
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
        "document_type": doc_type_detected,
        "extracted_fields": extracted_fields
    }

def extract_document_info(industry: str, text: str) -> dict:
    """
    Calls OpenAI Chat Completions API with schema enforcement to extract structured data.
    Falls back to local regex extraction if credentials/quota issues occur.
    """
    if industry not in INDUSTRIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid industry: {industry}"
        )
        
    config = INDUSTRIES[industry]
    fields_config = config["fields"]
    
    # Build schema
    response_schema = build_json_schema(industry, fields_config)
    
    # Build system and user prompt
    fields_list = ", ".join(fields_config.keys())
    system_prompt = (
        "You are a precise document scanner and information extractor.\n"
        f"Analyze the document text for the '{industry}' industry.\n"
        "1. Identify the specific type of the document (e.g., 'Life Insurance Policy', 'Health Insurance Policy', 'Expense Receipt', 'Patient Registration Form').\n"
        f"2. For each expected field in the schema ({fields_list}), check if that field is applicable or relevant to this specific type of document layout.\n"
        "   - E.g., for the 'insurance' industry: 'accident_date' is always applicable (representing either the Accident Date or the Incident/Loss Date depending on the layout).\n"
        "3. Extract the value if present. If applicable but the information is missing from the document, set value=null and applicable=true.\n"
        "4. Do not invent, guess, or fabricate any details. Keep values null if not explicitly in the text."
    )
    
    user_prompt = f"Document text:\n{text}"
    
    try:
        # Load client inside try to capture missing key exceptions
        client = get_openai_client()
        
        # Determine model dynamically
        gemini_key = os.environ.get("GEMINI_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")
        is_gemini = bool(gemini_key) or (bool(openai_key) and openai_key.strip().startswith("AIzaSy"))
        model_name = "gemini-1.5-flash" if is_gemini else "gpt-4o-mini"
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": response_schema
            },
            temperature=0.0,
            timeout=30.0
        )
        
        raw_content = response.choices[0].message.content
        if not raw_content:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OpenAI returned an empty response."
            )
            
        extracted_data = json.loads(raw_content)
        return extracted_data
        
    except Exception as e:
        # Log/Print warning to server console, and run free local fallback extraction
        print(f"\n--- WARNING: OpenAI/Gemini API Call Failed ---")
        print(f"Error Details: {str(e)}")
        print(f"Action: Falling back to local deterministic regex extractor...")
        print(f"-----------------------------------------\n")
        return mock_extraction_fallback(industry, text)
