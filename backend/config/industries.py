# backend/config/industries.py

from typing import Dict, Any

INDUSTRIES: Dict[str, Dict[str, Any]] = {
    "insurance": {
        "document_type": "insurance_policy_or_claim",
        "fields": {
            "customer_name": {
                "type": "string",
                "required": True,
                "description": "Full name of the customer or policyholder"
            },
            "policy_number": {
                "type": "string",
                "required": True,
                "description": "Unique identification number of the insurance policy"
            },
            "policy_type": {
                "type": "select",
                "required": True,
                "options": ["Health Insurance", "Life Insurance", "Motor/Auto Insurance", "Home Insurance", "Travel Insurance", "Personal Accident Insurance"],
                "description": "Category of the insurance policy"
            },
            "policy_start_date": {
                "type": "date",
                "required": True,
                "description": "The active start date of the policy (format: YYYY-MM-DD)"
            },
            "policy_end_date": {
                "type": "date",
                "required": True,
                "description": "The active end date of the policy (format: YYYY-MM-DD)"
            },
            "coverage_amount": {
                "type": "string",
                "required": True,
                "description": "Coverage amount or sum insured benefits of the policy"
            },
            "accident_date": {
                "type": "date",
                "required": True,
                "description": "Date when the accident occurred (format: YYYY-MM-DD). Only applicable for claim documents."
            },
            "claim_type": {
                "type": "string",
                "required": True,
                "description": "Type of claim. Only applicable for claim documents."
            }
        }
    },
    "finance": {
        "document_type": "expense_claim",
        "fields": {
            "employee_name": {
                "type": "string",
                "required": True,
                "description": "Full name of the employee requesting reimbursement"
            },
            "merchant_name": {
                "type": "string",
                "required": True,
                "description": "Name of the merchant or vendor where the purchase was made"
            },
            "amount": {
                "type": "number",
                "required": True,
                "description": "Total expense amount as a decimal number (no currency symbols)"
            },
            "date": {
                "type": "date",
                "required": True,
                "description": "Date of the expense receipt (format: YYYY-MM-DD)"
            },
            "category": {
                "type": "select",
                "required": True,
                "options": ["Travel", "Meals", "Office Supplies", "Software", "Others"],
                "description": "Expense category classification"
            }
        }
    },
    "healthcare": {
        "document_type": "patient_registration",
        "fields": {
            "patient_name": {
                "type": "string",
                "required": True,
                "description": "Full name of the patient"
            },
            "date_of_birth": {
                "type": "date",
                "required": True,
                "description": "Date of birth of the patient (format: YYYY-MM-DD)"
            },
            "hospital_name": {
                "type": "string",
                "required": True,
                "description": "Name of the hospital or healthcare provider clinic"
            },
            "appointment_type": {
                "type": "string",
                "required": True,
                "description": "Type of clinic appointment (e.g., General Consultation, Specialist, Dental Checkup)"
            },
            "appointment_date": {
                "type": "date",
                "required": True,
                "description": "Date of the scheduled appointment (format: YYYY-MM-DD)"
            }
        }
    }
}
