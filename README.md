# AI Document Automation MVP

A reusable AI-driven document information extraction and validation system. This application demonstrates a single, configuration-driven extraction workflow applied across three different industries: **Insurance**, **Finance**, and **Healthcare**.

## 1. Project Architecture

The system consists of a Next.js/React frontend communicating with a FastAPI/Python backend:

```
+-------------------------------------------------------------+
|                          FRONTEND                           |
|                       (Next.js/React)                       |
|  - Industry Selector    - File Upload & Demo Select         |
|  - PDF Preview Panel    - Extraction/Validation Display     |
|  - Session History (In-Memory)                              |
+------------------------------+------------------------------+
                               |
                        POST /api/process-document (FormData)
                               |
                               v
+-------------------------------------------------------------+
|                          BACKEND                            |
|                          (FastAPI)                          |
|  - PDF & File size validation                               |
|  - PyMuPDF text extractor                                   |
|  - Config-driven prompt builder                             |
|  - OpenAI Structured Outputs (JSON Schema)                  |
|  - Deterministic Python Validators                          |
+-------------------------------------------------------------+
```

1. **Frontend**: Allows industry selection, uploading custom files, previewing PDFs in-app, displaying structured extractions alongside deterministic validation cards, and maintaining a session history list.
2. **Backend**: Handles PDF validation (size <= 10MB, format verification), text extraction via PyMuPDF, OpenAI Structured Outputs integration (using dynamic JSON Schemas), and deterministic python-based data validation.

---

## 2. Supported Industries & Fields Config

All industry-specific behaviors are completely configuration-driven:

| Industry | Document Type | Fields to Extract | Validation Constraints |
| :--- | :--- | :--- | :--- |
| **Insurance** | `insurance_claim` | `customer_name`, `policy_number`, `accident_date`, `claim_type` | Date parsing checks on `accident_date` |
| **Finance** | `expense_claim` | `employee_name`, `amount`, `date`, `category` | Date parsing on `date`, numeric check on `amount` |
| **Healthcare** | `patient_registration` | `patient_name`, `date_of_birth`, `appointment_type`, `appointment_date` | Date parsing on `date_of_birth` and `appointment_date` |

---

## 3. Local Development Setup

### Prerequisite Dependencies
- **Python 3.10+**
- **Node.js 18+**

### A. Backend Setup
1. Open a terminal in the `backend/` directory:
   ```bash
   pip3 install -r requirements.txt
   ```
2. Setup environment variable file:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and configure your `OPENAI_API_KEY`:
   ```env
   OPENAI_API_KEY=sk-proj-...
   ```
3. Generate the demonstration and negative test PDFs:
   ```bash
   python3 scripts/generate_demos.py
   ```
4. Start the FastAPI local server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   The backend will be running at `http://localhost:8000`.

### B. Frontend Setup
1. Open a new terminal in the `frontend/` directory:
   ```bash
   npm install
   ```
2. Start the Next.js development server:
   ```bash
   npm run dev
   ```
   The frontend will be running at `http://localhost:3000`. Open your browser to `http://localhost:3000`.

---

## 4. Environment Variables

### Backend (`backend/.env`)
- `OPENAI_API_KEY`: Your OpenAI Secret API Key (Server-side only).

### Frontend (`frontend/.env.local`)
- `NEXT_PUBLIC_API_URL`: The HTTP URL of the running FastAPI server (defaults to `http://localhost:8000` if omitted).

---

## 5. API Endpoint Documentation

### `POST /api/process-document`
Processes an uploaded PDF according to the specified industry config.

- **Content-Type**: `multipart/form-data`
- **Request Form Data**:
  - `industry` (string): `"insurance"`, `"finance"`, or `"healthcare"`
  - `file` (binary): PDF file upload, max size 10MB

- **Response Success Sample (200 OK)**:
  ```json
  {
    "success": true,
    "industry": "insurance",
    "document_type": "insurance_claim",
    "file_name": "insurance_demo.pdf",
    "extracted_data": {
      "customer_name": "John Smith",
      "policy_number": "POL12345",
      "accident_date": "2026-08-10",
      "claim_type": "Car Accident"
    },
    "validation": {
      "customer_name": { "valid": true, "message": "Customer name found." },
      "policy_number": { "valid": true, "message": "Policy number found." },
      "accident_date": { "valid": true, "message": "Accident date is valid (2026-08-10)." },
      "claim_type": { "valid": true, "message": "Claim type found." }
    },
    "overall_status": "ready_for_review"
  }
  ```

- **Response Error Sample (400 / 500)**:
  ```json
  {
    "success": false,
    "error": "Only PDF files are supported."
  }
  ```

---

## 6. Testing

### Run Backend Unit Tests
Execute the test suite using `pytest`. Run from the project root:
```bash
PYTHONPATH=. pytest backend/tests/test_backend.py
```
This runs 12 automated unit tests covering file size limits, parsing checks, date/number validator heuristics, and endpoint route parameters (using mocked OpenAI clients).

### Run Frontend Static Checks
Run the compile build script to verify no TS or configuration errors in the Next.js bundle:
```bash
cd frontend
npm run build
```

---

## 7. Deployment Guidelines

1. **Frontend (Vercel)**:
   - Push the code to a Git repository.
   - Connect the repository to Vercel.
   - Configure Root Directory to `frontend`.
   - Set environment variable: `NEXT_PUBLIC_API_URL` to point to your deployed backend.

2. **Backend**:
   - Host FastAPI on services like Render, Railway, or AWS App Runner.
   - Configure the root directory to `backend`.
   - Set the environment variable: `OPENAI_API_KEY` in the hosting dashboard (kept strictly on the server-side, never exposed).
