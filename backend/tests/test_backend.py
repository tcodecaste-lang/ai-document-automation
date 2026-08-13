# backend/tests/test_backend.py

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Set mock API key before importing
os.environ["OPENAI_API_KEY"] = "mock-openai-key"

from backend.main import app
from backend.services.pdf_extractor import extract_text_from_pdf
from backend.validators.deterministic import validate_date, validate_number, validate_extracted_data

client = TestClient(app)

# Helper to get path of demo files
DEMO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo-pdfs"))

# ==========================================
# 1. FILE & TEXT EXTRACTION TESTS
# ==========================================

def test_extract_text_valid_pdf():
    # Test text extraction from valid generated insurance demo
    pdf_path = os.path.join(DEMO_DIR, "insurance_demo.pdf")
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
    
    text = extract_text_from_pdf(file_bytes)
    assert "Insurance Claim Form" in text
    assert "John Smith" in text
    assert "POL12345" in text

def test_extract_text_invalid_bytes():
    # Empty bytes should fail parsing
    with pytest.raises(Exception) as excinfo:
        extract_text_from_pdf(b"")
    assert "empty" in str(excinfo.value).lower() or "fail" in str(excinfo.value).lower()

# ==========================================
# 2. DETERMINISTIC VALIDATOR TESTS
# ==========================================

def test_date_validator():
    # Test happy formats
    assert validate_date("2026-08-10") is True
    assert validate_date("10 Aug 2026") is True
    assert validate_date("10 August 2026") is True
    assert validate_date("08/10/2026") is True
    
    # Test unhappy formats
    assert validate_date("invalid-date") is False
    assert validate_date("2026/13/45") is False
    assert validate_date("") is False

def test_number_validator():
    # Test happy formats
    assert validate_number(250) is True
    assert validate_number(250.00) is True
    assert validate_number("250.00") is True
    assert validate_number("$250") is True
    assert validate_number("1,250.50") is True
    
    # Test unhappy formats
    assert validate_number("two hundred") is False
    assert validate_number(None) is False

def test_extracted_data_validation_insurance_success():
    extracted = {
        "customer_name": "John Smith",
        "policy_number": "POL12345",
        "policy_type": "Health Insurance",
        "policy_start_date": "2026-01-01",
        "policy_end_date": "2026-12-31",
        "coverage_amount": "$5000",
        "accident_date": "2026-08-10",
        "claim_type": "Car Accident"
    }
    results, status = validate_extracted_data("insurance", extracted)
    assert status == "ready_for_review"
    assert results["customer_name"]["valid"] is True
    assert results["accident_date"]["valid"] is True

def test_extracted_data_validation_insurance_missing_date():
    extracted = {
        "customer_name": "John Smith",
        "policy_number": "POL12345",
        "policy_type": "Health Insurance",
        "policy_start_date": "2026-01-01",
        "policy_end_date": "2026-12-31",
        "coverage_amount": "$5000",
        "claim_type": "Car Accident"
        # missing accident_date
    }
    results, status = validate_extracted_data("insurance", extracted)
    assert status == "needs_review"
    assert results["accident_date"]["valid"] is False
    assert "missing" in results["accident_date"]["message"].lower()

def test_extracted_data_validation_finance_invalid_amount():
    extracted = {
        "employee_name": "Sarah Jones",
        "merchant_name": "Boston Transit Co",
        "amount": "not-a-number",
        "date": "2026-08-08",
        "category": "Travel"
    }
    results, status = validate_extracted_data("finance", extracted)
    assert status == "needs_review"
    assert results["amount"]["valid"] is False
    assert "number" in results["amount"]["message"].lower()

# ==========================================
# 3. ENDPOINT TESTS (WITH OPENAI MOCKED)
# ==========================================

@patch("backend.api.endpoints.extract_document_info")
def test_api_insurance_demo_success(mock_extract):
    # Mocking OpenAI response with new schema layout
    mock_extract.return_value = {
        "document_type": "Insurance Claim Form",
        "extracted_fields": {
            "customer_name": {"value": "John Smith", "applicable": True},
            "policy_number": {"value": "POL12345", "applicable": True},
            "policy_type": {"value": "Health Insurance", "applicable": True},
            "policy_start_date": {"value": "2026-01-01", "applicable": True},
            "policy_end_date": {"value": "2026-12-31", "applicable": True},
            "coverage_amount": {"value": "$5000", "applicable": True},
            "accident_date": {"value": "2026-08-10", "applicable": True},
            "claim_type": {"value": "Car Accident", "applicable": True}
        }
    }
    
    pdf_path = os.path.join(DEMO_DIR, "insurance_demo.pdf")
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/process-document",
            data={"industry": "insurance"},
            files={"file": ("insurance_demo.pdf", f, "application/pdf")}
        )
        
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["industry"] == "insurance"
    assert json_data["extracted_data"]["customer_name"] == "John Smith"
    assert json_data["validation"]["accident_date"]["valid"] is True
    assert json_data["overall_status"] == "ready_for_review"

@patch("backend.api.endpoints.extract_document_info")
def test_api_insurance_negative_demo_needs_review(mock_extract):
    # Mocking OpenAI response for missing date
    mock_extract.return_value = {
        "document_type": "Insurance Claim Form",
        "extracted_fields": {
            "customer_name": {"value": "John Smith", "applicable": True},
            "policy_number": {"value": "POL12345", "applicable": True},
            "policy_type": {"value": "Health Insurance", "applicable": True},
            "policy_start_date": {"value": "2026-01-01", "applicable": True},
            "policy_end_date": {"value": "2026-12-31", "applicable": True},
            "coverage_amount": {"value": "$5000", "applicable": True},
            "accident_date": {"value": None, "applicable": True},
            "claim_type": {"value": "Car Accident", "applicable": True}
        }
    }
    
    pdf_path = os.path.join(DEMO_DIR, "insurance_negative_demo.pdf")
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/process-document",
            data={"industry": "insurance"},
            files={"file": ("insurance_negative_demo.pdf", f, "application/pdf")}
        )
        
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["overall_status"] == "needs_review"
    assert json_data["validation"]["accident_date"]["valid"] is False

def test_api_invalid_file_format():
    response = client.post(
        "/api/process-document",
        data={"industry": "insurance"},
        files={"file": ("test.txt", b"plain text content", "text/plain")}
    )
    assert response.status_code == 400
    json_data = response.json()
    assert json_data["success"] is False
    assert "only pdf" in json_data["error"].lower()

def test_api_file_too_large():
    # Mock file object that exceeds 10MB limit
    large_payload = b"0" * (10 * 1024 * 1024 + 10)
    response = client.post(
        "/api/process-document",
        data={"industry": "insurance"},
        files={"file": ("large.pdf", large_payload, "application/pdf")}
    )
    assert response.status_code == 400
    json_data = response.json()
    assert json_data["success"] is False
    assert "10 mb or smaller" in json_data["error"].lower()

def test_api_unsupported_industry():
    response = client.post(
        "/api/process-document",
        data={"industry": "unknown_industry"},
        files={"file": ("insurance_demo.pdf", b"%PDF-1.4 mock content", "application/pdf")}
    )
    assert response.status_code == 400
    json_data = response.json()
    assert json_data["success"] is False
    assert "unsupported industry" in json_data["error"].lower()

# ==========================================
# 4. REGEX FALLBACK PARSER TESTS
# ==========================================
from backend.services.openai_service import mock_extraction_fallback

def test_mock_extraction_insurance():
    pdf_path = os.path.join(DEMO_DIR, "insurance_demo.pdf")
    with open(pdf_path, "rb") as f:
        text = extract_text_from_pdf(f.read())
    extracted = mock_extraction_fallback("insurance", text)
    fields = extracted["extracted_fields"]
    assert fields["customer_name"]["value"] == "John Smith"
    assert fields["policy_number"]["value"] == "POL12345"
    assert fields["accident_date"]["value"] == "2026-08-10"
    assert fields["claim_type"]["value"] == "Car Accident"

def test_mock_extraction_insurance_negative():
    pdf_path = os.path.join(DEMO_DIR, "insurance_negative_demo.pdf")
    with open(pdf_path, "rb") as f:
        text = extract_text_from_pdf(f.read())
    extracted = mock_extraction_fallback("insurance", text)
    fields = extracted["extracted_fields"]
    assert fields["customer_name"]["value"] == "John Smith"
    assert fields["policy_number"]["value"] == "POL12345"
    assert fields["accident_date"]["value"] is None
    assert fields["claim_type"]["value"] == "Car Accident"

def test_mock_extraction_finance():
    pdf_path = os.path.join(DEMO_DIR, "finance_demo.pdf")
    with open(pdf_path, "rb") as f:
        text = extract_text_from_pdf(f.read())
    extracted = mock_extraction_fallback("finance", text)
    fields = extracted["extracted_fields"]
    assert fields["employee_name"]["value"] == "Sarah Jones"
    assert fields["merchant_name"]["value"] == "Boston Transit Co"
    assert fields["amount"]["value"] == 250.00
    assert fields["date"]["value"] == "2026-08-08"
    # category is Travel, which is a select option
    assert fields["category"]["value"] == "Travel"

def test_mock_extraction_healthcare():
    pdf_path = os.path.join(DEMO_DIR, "healthcare_demo.pdf")
    with open(pdf_path, "rb") as f:
        text = extract_text_from_pdf(f.read())
    extracted = mock_extraction_fallback("healthcare", text)
    fields = extracted["extracted_fields"]
    assert fields["patient_name"]["value"] == "David Brown"
    assert fields["date_of_birth"]["value"] == "1980-03-12"
    assert fields["hospital_name"]["value"] == "General Health Clinic"
    assert fields["appointment_type"]["value"] == "General Consultation"
    assert fields["appointment_date"]["value"] == "2026-08-15"

def test_api_generate_pdf_endpoint():
    payload = {
        "file_name": "insurance_demo.pdf",
        "industry": "insurance",
        "document_type": "insurance_policy_or_claim",
        "extracted_data": {
            "customer_name": "John Smith",
            "policy_number": "POL12345",
            "policy_type": "Health Insurance",
            "policy_start_date": "2026-01-01",
            "policy_end_date": "2026-12-31",
            "coverage_amount": "$5000",
            "accident_date": "2026-08-10",
            "claim_type": "Car Accident"
        },
        "validation": {
            "customer_name": {"valid": True, "message": "Valid"},
            "policy_number": {"valid": True, "message": "Valid"},
            "policy_type": {"valid": True, "message": "Valid"},
            "policy_start_date": {"valid": True, "message": "Valid"},
            "policy_end_date": {"valid": True, "message": "Valid"},
            "coverage_amount": {"valid": True, "message": "Valid"},
            "accident_date": {"valid": True, "message": "Valid"},
            "claim_type": {"valid": True, "message": "Valid"}
        },
        "overall_status": "ready_for_review",
        "original_data": {
            "customer_name": "John Smith",
            "policy_number": "POL12345",
            "policy_type": "Health Insurance",
            "policy_start_date": "2026-01-01",
            "policy_end_date": "2026-12-31",
            "coverage_amount": "$5000",
            "accident_date": None,
            "claim_type": "Car Accident"
        }
    }
    
    response = client.post("/api/generate-pdf", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert len(response.content) > 0

def test_api_generate_combined_report_endpoint():
    payload = {
        "items": [
            {
                "file_name": "insurance_demo.pdf",
                "industry": "insurance",
                "document_type": "insurance_policy_or_claim",
                "extracted_data": {
                    "customer_name": "John Smith",
                    "policy_number": "POL12345",
                    "policy_type": "Health Insurance",
                    "policy_start_date": "2026-01-01",
                    "policy_end_date": "2026-12-31",
                    "coverage_amount": "$5000",
                    "accident_date": "2026-08-10",
                    "claim_type": "Car Accident"
                },
                "validation": {
                    "customer_name": {"valid": True, "message": "Valid"},
                    "policy_number": {"valid": True, "message": "Valid"},
                    "policy_type": {"valid": True, "message": "Valid"},
                    "policy_start_date": {"valid": True, "message": "Valid"},
                    "policy_end_date": {"valid": True, "message": "Valid"},
                    "coverage_amount": {"valid": True, "message": "Valid"},
                    "accident_date": {"valid": True, "message": "Valid"},
                    "claim_type": {"valid": True, "message": "Valid"}
                },
                "overall_status": "ready_for_review",
                "original_data": {
                    "customer_name": "John Smith",
                    "policy_number": "POL12345",
                    "policy_type": "Health Insurance",
                    "policy_start_date": "2026-01-01",
                    "policy_end_date": "2026-12-31",
                    "coverage_amount": "$5000",
                    "accident_date": None,
                    "claim_type": "Car Accident"
                }
            },
            {
                "file_name": "finance_demo.pdf",
                "industry": "finance",
                "document_type": "expense_report",
                "extracted_data": {
                    "employee_name": "Sarah Jones",
                    "merchant_name": "Boston Transit Co",
                    "amount": 250.0,
                    "date": "2026-08-08",
                    "category": "Travel"
                },
                "validation": {
                    "employee_name": {"valid": True, "message": "Valid"},
                    "merchant_name": {"valid": True, "message": "Valid"},
                    "amount": {"valid": True, "message": "Valid"},
                    "date": {"valid": True, "message": "Valid"},
                    "category": {"valid": True, "message": "Valid"}
                },
                "overall_status": "ready_for_review",
                "original_data": {
                    "employee_name": "Sarah Jones",
                    "merchant_name": "Boston Transit Co",
                    "amount": 250.0,
                    "date": "2026-08-08",
                    "category": "Travel"
                }
            }
        ]
    }
    
    response = client.post("/api/generate-combined-report", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert "processed_documents_report.pdf" in response.headers["content-disposition"]
    assert len(response.content) > 0

def test_provider_manager_gemini_success():
    from backend.services.ai_provider import AIProviderManager
    from unittest.mock import MagicMock, patch
    
    AIProviderManager.mark_gemini_available()
    
    mock_gemini = MagicMock(return_value={"status": "success", "provider": "gemini"})
    mock_groq = MagicMock()
    
    with patch.object(AIProviderManager._gemini_provider, "extract", mock_gemini), \
         patch.object(AIProviderManager._groq_provider, "extract", mock_groq):
         
        result = AIProviderManager.extract(
            industry="insurance",
            text="hello",
            response_schema={},
            system_prompt="",
            user_prompt=""
        )
        assert result == {"status": "success", "provider": "gemini"}
        mock_gemini.assert_called_once()
        mock_groq.assert_not_called()
        assert AIProviderManager.is_gemini_available() is True

def test_provider_manager_gemini_fails_429_fallback_groq():
    from backend.services.ai_provider import AIProviderManager, RecoverableProviderError
    from unittest.mock import MagicMock, patch
    
    AIProviderManager.mark_gemini_available()
    
    mock_gemini = MagicMock(side_effect=RecoverableProviderError("Quota exceeded", cooldown_seconds=10))
    mock_groq = MagicMock(return_value={"status": "success", "provider": "groq"})
    
    with patch.object(AIProviderManager._gemini_provider, "extract", mock_gemini), \
         patch.object(AIProviderManager._groq_provider, "extract", mock_groq):
         
        result = AIProviderManager.extract(
            industry="insurance",
            text="hello",
            response_schema={},
            system_prompt="",
            user_prompt=""
        )
        assert result == {"status": "success", "provider": "groq"}
        mock_gemini.assert_called_once()
        mock_groq.assert_called_once()
        assert AIProviderManager.is_gemini_available() is False

def test_provider_manager_gemini_cooldown_directly_to_groq():
    from backend.services.ai_provider import AIProviderManager
    from unittest.mock import MagicMock, patch
    
    AIProviderManager.mark_gemini_unavailable(cooldown_seconds=100)
    
    mock_gemini = MagicMock()
    mock_groq = MagicMock(return_value={"status": "success", "provider": "groq"})
    
    with patch.object(AIProviderManager._gemini_provider, "extract", mock_gemini), \
         patch.object(AIProviderManager._groq_provider, "extract", mock_groq):
         
        result = AIProviderManager.extract(
            industry="insurance",
            text="hello",
            response_schema={},
            system_prompt="",
            user_prompt=""
        )
        assert result == {"status": "success", "provider": "groq"}
        mock_gemini.assert_not_called()
        mock_groq.assert_called_once()

def test_provider_manager_cooldown_expires_retry_gemini_success():
    from backend.services.ai_provider import AIProviderManager
    from unittest.mock import MagicMock, patch
    
    AIProviderManager.mark_gemini_unavailable(cooldown_seconds=-5)
    
    mock_gemini = MagicMock(return_value={"status": "success", "provider": "gemini"})
    mock_groq = MagicMock()
    
    with patch.object(AIProviderManager._gemini_provider, "extract", mock_gemini), \
         patch.object(AIProviderManager._groq_provider, "extract", mock_groq):
         
        result = AIProviderManager.extract(
            industry="insurance",
            text="hello",
            response_schema={},
            system_prompt="",
            user_prompt=""
        )
        assert result == {"status": "success", "provider": "gemini"}
        mock_gemini.assert_called_once()
        mock_groq.assert_not_called()
        assert AIProviderManager.is_gemini_available() is True

def test_provider_manager_both_fail_raises_503():
    from backend.services.ai_provider import AIProviderManager, RecoverableProviderError
    from unittest.mock import MagicMock, patch
    from fastapi import HTTPException
    
    AIProviderManager.mark_gemini_available()
    
    mock_gemini = MagicMock(side_effect=RecoverableProviderError("Quota exceeded", cooldown_seconds=10))
    mock_groq = MagicMock(side_effect=Exception("Groq down"))
    
    with patch.object(AIProviderManager._gemini_provider, "extract", mock_gemini), \
         patch.object(AIProviderManager._groq_provider, "extract", mock_groq):
         
        import pytest
        with pytest.raises(HTTPException) as excinfo:
            AIProviderManager.extract(
                industry="insurance",
                text="hello",
                response_schema={},
                system_prompt="",
                user_prompt=""
            )
        assert excinfo.value.status_code == 503
        assert "AI processing is temporarily unavailable" in excinfo.value.detail

def test_provider_manager_gemini_unauthorized_does_not_fallback():
    from backend.services.ai_provider import AIProviderManager
    from unittest.mock import MagicMock, patch
    from fastapi import HTTPException
    
    AIProviderManager.mark_gemini_available()
    
    mock_gemini = MagicMock(side_effect=HTTPException(status_code=401, detail="Invalid API key"))
    mock_groq = MagicMock()
    
    with patch.object(AIProviderManager._gemini_provider, "extract", mock_gemini), \
         patch.object(AIProviderManager._groq_provider, "extract", mock_groq):
         
        import pytest
        with pytest.raises(HTTPException) as excinfo:
            AIProviderManager.extract(
                industry="insurance",
                text="hello",
                response_schema={},
                system_prompt="",
                user_prompt=""
            )
        assert excinfo.value.status_code == 401
        mock_groq.assert_not_called()


