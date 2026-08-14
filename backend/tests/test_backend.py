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

def get_auth_headers(email="test@user.com", name="Test User", role="user"):
    # Clear user first if existing
    from backend.services.database import get_db
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE email = ?", (email,))
        conn.commit()
    # Register
    client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "Password123",
        "confirm_password": "Password123"
    })
    # Login
    login_response = client.post("/api/auth/login", json={
        "email": email,
        "password": "Password123"
    })
    token = login_response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


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
    
    headers = get_auth_headers()
    pdf_path = os.path.join(DEMO_DIR, "insurance_demo.pdf")
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/process-document",
            data={"industry": "insurance"},
            files={"file": ("insurance_demo.pdf", f, "application/pdf")},
            headers=headers
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
    
    headers = get_auth_headers()
    pdf_path = os.path.join(DEMO_DIR, "insurance_negative_demo.pdf")
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/process-document",
            data={"industry": "insurance"},
            files={"file": ("insurance_negative_demo.pdf", f, "application/pdf")},
            headers=headers
        )
        
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["overall_status"] == "needs_review"
    assert json_data["validation"]["accident_date"]["valid"] is False

def test_api_invalid_file_format():
    headers = get_auth_headers()
    response = client.post(
        "/api/process-document",
        data={"industry": "insurance"},
        files={"file": ("test.txt", b"plain text content", "text/plain")},
        headers=headers
    )
    assert response.status_code == 400
    json_data = response.json()
    assert json_data["success"] is False
    assert "only pdf" in json_data["error"].lower()

def test_api_file_too_large():
    # Mock file object that exceeds 10MB limit
    headers = get_auth_headers()
    large_payload = b"0" * (10 * 1024 * 1024 + 10)
    response = client.post(
        "/api/process-document",
        data={"industry": "insurance"},
        files={"file": ("large.pdf", large_payload, "application/pdf")},
        headers=headers
    )
    assert response.status_code == 400
    json_data = response.json()
    assert json_data["success"] is False
    assert "10 mb or smaller" in json_data["error"].lower()

def test_api_unsupported_industry():
    headers = get_auth_headers()
    response = client.post(
        "/api/process-document",
        data={"industry": "unknown_industry"},
        files={"file": ("insurance_demo.pdf", b"%PDF-1.4 mock content", "application/pdf")},
        headers=headers
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
    
    headers = get_auth_headers()
    response = client.post("/api/generate-combined-report", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert "processed_documents_report.pdf" in response.headers["content-disposition"]
    assert len(response.content) > 0

def test_provider_manager_gemini_success():
    from backend.services.ai_provider import AIProviderManager
    from unittest.mock import MagicMock, patch
    
    AIProviderManager.mark_gemini_available()
    AIProviderManager.mark_groq_available()
    
    mock_gemini = MagicMock(return_value={"status": "success", "provider": "gemini"})
    mock_groq = MagicMock()
    mock_mistral = MagicMock()
    
    with patch.object(AIProviderManager._gemini_provider, "extract", mock_gemini), \
         patch.object(AIProviderManager._groq_provider, "extract", mock_groq), \
         patch.object(AIProviderManager._mistral_provider, "extract", mock_mistral):
         
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
        mock_mistral.assert_not_called()
        assert AIProviderManager.is_gemini_available() is True

def test_provider_manager_gemini_fails_429_fallback_groq():
    from backend.services.ai_provider import AIProviderManager, RecoverableProviderError
    from unittest.mock import MagicMock, patch
    
    AIProviderManager.mark_gemini_available()
    AIProviderManager.mark_groq_available()
    
    mock_gemini = MagicMock(side_effect=RecoverableProviderError("Quota exceeded", cooldown_seconds=10))
    mock_groq = MagicMock(return_value={"status": "success", "provider": "groq"})
    mock_mistral = MagicMock()
    
    with patch.object(AIProviderManager._gemini_provider, "extract", mock_gemini), \
         patch.object(AIProviderManager._groq_provider, "extract", mock_groq), \
         patch.object(AIProviderManager._mistral_provider, "extract", mock_mistral):
         
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
        mock_mistral.assert_not_called()
        assert AIProviderManager.is_gemini_available() is False

def test_provider_manager_gemini_cooldown_directly_to_groq():
    from backend.services.ai_provider import AIProviderManager
    from unittest.mock import MagicMock, patch
    
    AIProviderManager.mark_gemini_unavailable(cooldown_seconds=100)
    AIProviderManager.mark_groq_available()
    
    mock_gemini = MagicMock()
    mock_groq = MagicMock(return_value={"status": "success", "provider": "groq"})
    mock_mistral = MagicMock()
    
    with patch.object(AIProviderManager._gemini_provider, "extract", mock_gemini), \
         patch.object(AIProviderManager._groq_provider, "extract", mock_groq), \
         patch.object(AIProviderManager._mistral_provider, "extract", mock_mistral):
         
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
        mock_mistral.assert_not_called()

def test_provider_manager_cooldown_expires_retry_gemini_success():
    from backend.services.ai_provider import AIProviderManager
    from unittest.mock import MagicMock, patch
    
    AIProviderManager.mark_gemini_unavailable(cooldown_seconds=-5)
    AIProviderManager.mark_groq_available()
    
    mock_gemini = MagicMock(return_value={"status": "success", "provider": "gemini"})
    mock_groq = MagicMock()
    mock_mistral = MagicMock()
    
    with patch.object(AIProviderManager._gemini_provider, "extract", mock_gemini), \
         patch.object(AIProviderManager._groq_provider, "extract", mock_groq), \
         patch.object(AIProviderManager._mistral_provider, "extract", mock_mistral):
         
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
        mock_mistral.assert_not_called()
        assert AIProviderManager.is_gemini_available() is True

def test_provider_manager_gemini_and_groq_fail_fallback_mistral():
    from backend.services.ai_provider import AIProviderManager, RecoverableProviderError
    from unittest.mock import MagicMock, patch
    
    AIProviderManager.mark_gemini_available()
    AIProviderManager.mark_groq_available()
    
    mock_gemini = MagicMock(side_effect=RecoverableProviderError("Gemini Quota exceeded", cooldown_seconds=10))
    mock_groq = MagicMock(side_effect=RecoverableProviderError("Groq Quota exceeded", cooldown_seconds=15))
    mock_mistral = MagicMock(return_value={"status": "success", "provider": "mistral"})
    
    with patch.object(AIProviderManager._gemini_provider, "extract", mock_gemini), \
         patch.object(AIProviderManager._groq_provider, "extract", mock_groq), \
         patch.object(AIProviderManager._mistral_provider, "extract", mock_mistral):
         
        result = AIProviderManager.extract(
            industry="insurance",
            text="hello",
            response_schema={},
            system_prompt="",
            user_prompt=""
        )
        assert result == {"status": "success", "provider": "mistral"}
        mock_gemini.assert_called_once()
        mock_groq.assert_called_once()
        mock_mistral.assert_called_once()
        assert AIProviderManager.is_gemini_available() is False
        assert AIProviderManager.is_groq_available() is False

def test_provider_manager_all_three_fail_raises_503():
    from backend.services.ai_provider import AIProviderManager, RecoverableProviderError
    from unittest.mock import MagicMock, patch
    from fastapi import HTTPException
    
    AIProviderManager.mark_gemini_available()
    AIProviderManager.mark_groq_available()
    
    mock_gemini = MagicMock(side_effect=RecoverableProviderError("Gemini Quota exceeded", cooldown_seconds=10))
    mock_groq = MagicMock(side_effect=RecoverableProviderError("Groq Quota exceeded", cooldown_seconds=10))
    mock_mistral = MagicMock(side_effect=Exception("Mistral down"))
    
    with patch.object(AIProviderManager._gemini_provider, "extract", mock_gemini), \
         patch.object(AIProviderManager._groq_provider, "extract", mock_groq), \
         patch.object(AIProviderManager._mistral_provider, "extract", mock_mistral):
         
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
    AIProviderManager.mark_groq_available()
    
    mock_gemini = MagicMock(side_effect=HTTPException(status_code=401, detail="Invalid API key"))
    mock_groq = MagicMock()
    mock_mistral = MagicMock()
    
    with patch.object(AIProviderManager._gemini_provider, "extract", mock_gemini), \
         patch.object(AIProviderManager._groq_provider, "extract", mock_groq), \
         patch.object(AIProviderManager._mistral_provider, "extract", mock_mistral):
         
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
        mock_mistral.assert_not_called()


# =====================================================================
# 5. AUTHENTICATION & SECURITY ENHANCEMENTS TESTS
# =====================================================================

def test_user_registration_success():
    email = "new_user@test.com"
    # Clean first
    from backend.services.database import get_db
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE email = ?", (email,))
        conn.commit()
        
    response = client.post("/api/auth/register", json={
        "name": "New User",
        "email": email,
        "password": "SecurePassword123",
        "confirm_password": "SecurePassword123"
    })
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_user_registration_duplicate_email():
    email = "new_user@test.com"
    response = client.post("/api/auth/register", json={
        "name": "New User",
        "email": email,
        "password": "SecurePassword123",
        "confirm_password": "SecurePassword123"
    })
    assert response.status_code == 400
    assert "exists" in response.json()["error"].lower()

def test_user_registration_password_mismatch():
    response = client.post("/api/auth/register", json={
        "name": "Mismatch User",
        "email": "mismatch@test.com",
        "password": "SecurePassword123",
        "confirm_password": "DifferentPassword123"
    })
    assert response.status_code == 400
    assert "match" in response.json()["error"].lower()

def test_user_login_success():
    email = "new_user@test.com"
    response = client.post("/api/auth/login", json={
        "email": email,
        "password": "SecurePassword123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "token" in data
    assert data["email"] == email

def test_user_login_wrong_password():
    response = client.post("/api/auth/login", json={
        "email": "new_user@test.com",
        "password": "IncorrectPassword"
    })
    assert response.status_code == 401

def test_unauthenticated_protected_api():
    response = client.get("/api/documents")
    assert response.status_code == 401

def test_authenticated_protected_api():
    headers = get_auth_headers(email="auth_user@test.com")
    response = client.get("/api/documents", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_user_isolation_security():
    headers_a = get_auth_headers(email="user_a@test.com")
    headers_b = get_auth_headers(email="user_b@test.com")
    
    # Process doc for user A
    pdf_path = os.path.join(DEMO_DIR, "insurance_demo.pdf")
    with open(pdf_path, "rb") as f:
        response_a = client.post(
            "/api/process-document",
            data={"industry": "insurance"},
            files={"file": ("insurance_demo.pdf", f, "application/pdf")},
            headers=headers_a
        )
    doc_id = response_a.json()["id"]
    
    # User B tries to update User A's document
    response_b = client.post(
        "/api/documents/update",
        json={
            "id": doc_id,
            "extracted_data": {"customer_name": "Hack Attack"}
        },
        headers=headers_b
    )
    assert response_b.status_code == 403
    assert "isolated" in response_b.json()["error"].lower()

# =====================================================================
# 6. DYNAMIC FIELD CONFIGURATION TESTS
# =====================================================================

def test_list_fields():
    headers = get_auth_headers()
    response = client.get("/api/fields", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) > 0
    assert "field_type" in response.json()[0]

def test_create_and_toggle_field_admin_only():
    headers_user = get_auth_headers(email="user@test.com", role="user")
    headers_admin = get_auth_headers(email="admin@test.com", role="admin")
    
    # Make sure database roles are updated
    from backend.services.database import get_db
    with get_db() as conn:
        conn.execute("UPDATE users SET role = 'admin' WHERE email = 'admin@test.com'")
        conn.execute("DELETE FROM fields WHERE name = 'new_dynamic_field'")
        conn.execute("DELETE FROM fields WHERE name = 'new_dynamic_field_admin'")
        conn.commit()
        
    payload = {
        "name": "new_dynamic_field",
        "label": "New Dynamic Field",
        "industry": "insurance",
        "document_type": "vehicle_insurance_claim",
        "field_type": "text",
        "required": True,
        "active": True,
        "display_order": 100,
        "validation_rules": "{}"
    }
    
    # Regular user succeeds
    res_user = client.post("/api/fields", json=payload, headers=headers_user)
    assert res_user.status_code == 201
    
    # Admin succeeds
    payload_admin = dict(payload)
    payload_admin["name"] = "new_dynamic_field_admin"
    res_admin = client.post("/api/fields", json=payload_admin, headers=headers_admin)
    assert res_admin.status_code == 201
    
    # Check created field exists
    fields_list = client.get("/api/fields", headers=headers_user).json()
    field_item = next((f for f in fields_list if f["name"] == "new_dynamic_field"), None)
    assert field_item is not None
    field_id = field_item["id"]
    
    # Admin updates field
    update_payload = {
        "label": "Updated Dynamic Label",
        "field_type": "text",
        "required": False,
        "active": True,
        "display_order": 110,
        "validation_rules": "{}"
    }
    res_update = client.put(f"/api/fields/{field_id}", json=update_payload, headers=headers_admin)
    assert res_update.status_code == 200
    
    # Admin toggles active status
    res_toggle = client.delete(f"/api/fields/{field_id}", headers=headers_admin)
    assert res_toggle.status_code == 200
    assert "disabled" in res_toggle.json()["message"]

# =====================================================================
# 7. MANUAL UPDATE CORRECTIONS & EMAIL DISPATCH TESTS
# =====================================================================

@patch("backend.api.endpoints.extract_document_info")
def test_manual_correction_and_revalidation(mock_extract):
    mock_extract.return_value = {
        "document_type": "insurance_policy_or_claim",
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
    
    headers = get_auth_headers()
    
    # Process document
    pdf_path = os.path.join(DEMO_DIR, "insurance_demo.pdf")
    with open(pdf_path, "rb") as f:
        proc_res = client.post(
            "/api/process-document",
            data={"industry": "insurance"},
            files={"file": ("insurance_demo.pdf", f, "application/pdf")},
            headers=headers
        )
    doc_id = proc_res.json()["id"]
    
    # Perform manual correction
    corr_res = client.post(
        "/api/documents/update",
        json={
            "id": doc_id,
            "extracted_data": {
                "customer_name": "Manual Corrected Name",
                "policy_number": "POL-CORRECTED",
                "policy_type": "Motor/Auto Insurance",
                "policy_start_date": "2026-05-15",
                "policy_end_date": "2027-05-15",
                "coverage_amount": "$10000",
                "accident_date": "2026-08-11",
                "claim_type": "Windshield Damage"
            }
        },
        headers=headers
    )
    assert corr_res.status_code == 200
    json_data = corr_res.json()
    assert json_data["extracted_data"]["customer_name"] == "Manual Corrected Name"
    assert json_data["validation"]["policy_number"]["valid"] is True
    assert json_data["overall_status"] == "ready_for_review"

def test_api_send_email_validation():
    headers = get_auth_headers()
    
    # Invalid email format
    response = client.post(
        "/api/send-email",
        json={
            "recipient_email": "invalid_email_format",
            "items": []
        },
        headers=headers
    )
    assert response.status_code == 400
    assert "email" in response.json()["error"].lower()

