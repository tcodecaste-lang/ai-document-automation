# backend/validators/deterministic.py

import datetime
from typing import Dict, Any, Tuple
from backend.config.industries import INDUSTRIES

def validate_date(date_str: str) -> bool:
    """
    Attempts to parse a date string using common formats.
    Returns True if valid, False otherwise.
    """
    if not isinstance(date_str, str):
        return False
        
    cleaned = date_str.strip()
    # Try various common formats
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
    """
    Checks if the value is a valid numeric value.
    Returns True if float or int, or string representing float/int.
    """
    if isinstance(num_val, (int, float)):
        return True
    if isinstance(num_val, str):
        # Remove common currency/comma characters for ease of validation
        cleaned = num_val.replace("$", "").replace(",", "").strip()
        try:
            float(cleaned)
            return True
        except ValueError:
            return False
    return False

def validate_extracted_data(industry: str, extracted_data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """
    Runs deterministic validations on extracted JSON data.
    Supports both nested structure (value + applicable) and raw flat dictionary.
    Returns (validation_results, overall_status)
    """
    config = INDUSTRIES[industry]
    fields_config = config["fields"]
    
    validation_results = {}
    all_valid = True
    
    # Check if we have the nested structure or the flat structure
    nested_fields = extracted_data.get("extracted_fields") if isinstance(extracted_data, dict) else None
    
    for field_name, field_info in fields_config.items():
        field_type = field_info["type"]
        is_required = field_info.get("required", False)
        
        # Determine value and applicability
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
                "message": f"{field_name.replace('_', ' ').title()} is not applicable to this document layout."
            }
            continue
            
        # 2. If applicable and the field is missing from the output completely
        if not has_field:
            validation_results[field_name] = {
                "valid": False,
                "message": f"{field_name.replace('_', ' ').title()} is missing."
            }
            all_valid = False
            continue
            
        # 3. Check if required and empty/null
        if is_required and (val is None or (isinstance(val, str) and not val.strip())):
            validation_results[field_name] = {
                "valid": False,
                "message": f"{field_name.replace('_', ' ').title()} is empty."
            }
            all_valid = False
            continue
            
        # If it's not required and empty, it's valid
        if not is_required and (val is None or (isinstance(val, str) and not val.strip())):
            validation_results[field_name] = {
                "valid": True,
                "message": f"{field_name.replace('_', ' ').title()} is empty (optional)."
            }
            continue
            
        # 4. Type validations
        if field_type == "date":
            # Date validation
            if validate_date(str(val)):
                validation_results[field_name] = {
                    "valid": True,
                    "message": f"{field_name.replace('_', ' ').title()} is valid ({val})."
                }
            else:
                validation_results[field_name] = {
                    "valid": False,
                    "message": f"{field_name.replace('_', ' ').title()} has an invalid date format: '{val}'."
                }
                all_valid = False
                
        elif field_type == "number":
            # Number validation
            if validate_number(val):
                validation_results[field_name] = {
                    "valid": True,
                    "message": f"{field_name.replace('_', ' ').title()} is valid ({val})."
                }
            else:
                validation_results[field_name] = {
                    "valid": False,
                    "message": f"{field_name.replace('_', ' ').title()} must be a valid number: '{val}'."
                }
                all_valid = False
                
        else:
            # Standard string validation
            validation_results[field_name] = {
                "valid": True,
                "message": f"{field_name.replace('_', ' ').title()} found."
            }
            
    overall_status = "ready_for_review" if all_valid else "needs_review"
    return validation_results, overall_status
