# backend/validators/deterministic.py

import datetime
import re
import json
import logging
from typing import Dict, Any, Tuple
from backend.services.database import get_db

logger = logging.getLogger("validators")

def validate_date(date_str: str) -> bool:
    """Attempts to parse a date string using common formats."""
    if not isinstance(date_str, str):
        return False
        
    cleaned = date_str.strip()
    formats = [
        "%Y-%m-%d",       # 2026-08-10
        "%d %b %Y",       # 10 Aug 2026
        "%d %B %Y",       # 10 August 2026
        "%m/%d/%Y",       # 08/10/2026
        "%d/%m/%Y",       # 10/08/2026
        "%Y/%m/%d",       # 2026/08/10
        "%b %d, %Y",      # Aug 10, 2026
        "%B %d, %Y"       # August 10, 2026
    ]
    
    for fmt in formats:
        try:
            datetime.datetime.strptime(cleaned, fmt)
            return True
        except ValueError:
            continue
            
    return False

def validate_number(num_val: Any) -> bool:
    """Checks if the value is a valid numeric/currency value."""
    if isinstance(num_val, (int, float)):
        return True
    if isinstance(num_val, str):
        cleaned = num_val.replace("$", "").replace(",", "").replace("%", "").strip()
        try:
            float(cleaned)
            return True
        except ValueError:
            return False
    return False

def validate_extracted_data(industry: str, extracted_data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Runs dynamic deterministic validation on extracted JSON data.
    Loads fields dynamically from database. Supports nested value structure.
    """
    doc_type = extracted_data.get("document_type")
    
    # Check if doc_type is configured
    configured_types = []
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT document_type FROM fields WHERE industry = ?", (industry,))
            configured_types = [row["document_type"] for row in cursor.fetchall()]
    except Exception:
        pass
        
    # Infer document type for legacy calls that lack document_type label or have mismatch
    if not doc_type or doc_type not in configured_types:
        try:
            doc_types = configured_types[:]
                
            best_doc_type = None
            max_overlap = -1
            
            extracted_keys = set()
            nested_fields = extracted_data.get("extracted_fields")
            if nested_fields and isinstance(nested_fields, dict):
                extracted_keys = set(nested_fields.keys())
            elif isinstance(extracted_data, dict):
                extracted_keys = set(extracted_data.keys())
                
            for dt in doc_types:
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM fields WHERE industry = ? AND document_type = ?", (industry, dt))
                    dt_fields = {row["name"] for row in cursor.fetchall()}
                overlap = len(extracted_keys.intersection(dt_fields))
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_doc_type = dt
                    
            if best_doc_type:
                doc_type = best_doc_type
        except Exception:
            pass
            
    # 1. Fetch active fields for this specific document type & industry
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, label, industry, document_type, field_type, required, active, display_order, validation_rules "
            "FROM fields WHERE industry = ? AND document_type = ? AND active = 1 "
            "ORDER BY display_order ASC",
            (industry, doc_type)
        )
        fields_config = [dict(row) for row in cursor.fetchall()]
        
    # If no fields match, default to general industry fields
    if not fields_config:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, label, industry, document_type, field_type, required, active, display_order, validation_rules "
                "FROM fields WHERE industry = ? AND active = 1 "
                "ORDER BY display_order ASC",
                (industry,)
            )
            fields_config = [dict(row) for row in cursor.fetchall()]
            
    validation_results = {}
    all_valid = True
    
    nested_fields = extracted_data.get("extracted_fields") if isinstance(extracted_data, dict) else None
    
    for field in fields_config:
        field_name = field["name"]
        field_label = field["label"]
        field_type = field["field_type"]
        is_required = bool(field["required"])
        
        applicable = True
        has_field = False
        val = None
        
        if nested_fields is not None:
            if field_name in nested_fields:
                has_field = True
                field_entry = nested_fields[field_name] or {}
                if isinstance(field_entry, dict):
                    val = field_entry.get("value")
                    applicable = field_entry.get("applicable", True)
                else:
                    val = field_entry
        else:
            if isinstance(extracted_data, dict) and field_name in extracted_data:
                has_field = True
                val = extracted_data[field_name]
                
        # 1. If not applicable, it is valid! (Skip validation checks)
        if not applicable:
            validation_results[field_name] = {
                "valid": True,
                "message": f"{field_label} is not applicable to this document layout."
            }
            continue
            
        # 2. If applicable and the field is missing from the output completely
        if not has_field:
            validation_results[field_name] = {
                "valid": False,
                "message": f"{field_label} is missing."
            }
            all_valid = False
            continue
            
        # 3. Check if required and empty/null
        if is_required and (val is None or (isinstance(val, str) and not val.strip())):
            validation_results[field_name] = {
                "valid": False,
                "message": f"{field_label} is empty."
            }
            all_valid = False
            continue
            
        # If it's not required and empty, it's valid
        if not is_required and (val is None or (isinstance(val, str) and not val.strip())):
            validation_results[field_name] = {
                "valid": True,
                "message": f"{field_label} is empty (optional)."
            }
            continue
            
        # 4. Type validations
        if field_type == "date":
            if validate_date(str(val)):
                validation_results[field_name] = {
                    "valid": True,
                    "message": f"{field_label} is valid ({val})."
                }
            else:
                validation_results[field_name] = {
                    "valid": False,
                    "message": f"{field_label} has an invalid date format: '{val}'."
                }
                all_valid = False
                
        elif field_type in ("number", "currency"):
            if validate_number(val):
                validation_results[field_name] = {
                    "valid": True,
                    "message": f"{field_label} is valid ({val})."
                }
            else:
                validation_results[field_name] = {
                    "valid": False,
                    "message": f"{field_label} must be a valid number: '{val}'."
                }
                all_valid = False
                
        elif field_type == "email":
            email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
            if re.match(email_pattern, str(val).strip()):
                 validation_results[field_name] = {
                    "valid": True,
                    "message": f"{field_label} is valid ({val})."
                }
            else:
                validation_results[field_name] = {
                    "valid": False,
                    "message": f"{field_label} has an invalid email format: '{val}'."
                }
                all_valid = False
                
        elif field_type == "select":
            try:
                rules = json.loads(field["validation_rules"] or "{}")
                options = rules.get("options", [])
                if options and str(val).strip() not in options:
                    validation_results[field_name] = {
                        "valid": False,
                        "message": f"{field_label} must be one of: {', '.join(options)}."
                    }
                    all_valid = False
                else:
                    validation_results[field_name] = {
                        "valid": True,
                        "message": f"{field_label} is valid."
                    }
            except Exception:
                validation_results[field_name] = {
                    "valid": True,
                    "message": f"{field_label} found."
                }
        else:
            validation_results[field_name] = {
                "valid": True,
                "message": f"{field_label} found."
            }
            
    overall_status = "ready_for_review" if all_valid else "needs_review"
    return validation_results, overall_status
