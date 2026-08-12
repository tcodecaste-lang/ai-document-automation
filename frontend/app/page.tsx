/* eslint-disable @typescript-eslint/no-explicit-any */
// frontend/app/page.tsx
"use client";

import React, { useState, useEffect, useRef } from "react";

// ==========================================
// TYPES DEFINITIONS
// ==========================================
interface FieldValidation {
  valid: boolean;
  message: string;
}

interface ProcessResponse {
  success: boolean;
  industry: string;
  document_type: string;
  file_name: string;
  extracted_data: Record<string, any>;
  extracted_fields?: Record<string, any>; // Dynamic field metadata containing value + applicable flags
  validation: Record<string, FieldValidation>;
  overall_status: "ready_for_review" | "needs_review";
}

interface SessionResult {
  id: string;
  timestamp: string;
  industry: string;
  document_type: string;
  file_name: string;
  extracted_data: Record<string, any>;
  extracted_fields?: Record<string, any>;
  validation: Record<string, FieldValidation>;
  overall_status: "ready_for_review" | "needs_review";
  pdfUrl: string;
  file: File; // Actual file object for complete restore and re-process capability
  original_data?: Record<string, any>;
}


type Industry = "insurance" | "finance" | "healthcare";

const INDUSTRY_FIELDS: Record<Industry, string[]> = {
  insurance: ["customer_name", "policy_number", "policy_type", "policy_start_date", "policy_end_date", "coverage_amount", "accident_date", "claim_type"],
  finance: ["employee_name", "merchant_name", "amount", "date", "category"],
  healthcare: ["patient_name", "date_of_birth", "hospital_name", "appointment_type", "appointment_date"],
};


// ==========================================
// SVG INLINE ICONS
// ==========================================
const ShieldIcon = () => (
  <svg className="icon" viewBox="0 0 24 24" width="36" height="36" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);

const FinanceIcon = () => (
  <svg className="icon" viewBox="0 0 24 24" width="36" height="36" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="1" x2="12" y2="23"></line>
    <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
  </svg>
);

const HealthcareIcon = () => (
  <svg className="icon" viewBox="0 0 24 24" width="36" height="36" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
  </svg>
);

const UploadIcon = () => (
  <svg viewBox="0 0 24 24" width="48" height="48" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="17 8 12 3 7 8" />
    <line x1="12" y1="3" x2="12" y2="15" />
  </svg>
);

const ArrowLeftIcon = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <line x1="19" y1="12" x2="5" y2="12"></line>
    <polyline points="12 19 5 12 12 5"></polyline>
  </svg>
);

const TrashIcon = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"></polyline>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
    <line x1="10" y1="11" x2="10" y2="17"></line>
    <line x1="14" y1="11" x2="14" y2="17"></line>
  </svg>
);

const CheckIcon = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

const AlertIcon = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

const FilePdfIcon = () => (
  <svg viewBox="0 0 24 24" width="36" height="36" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
    <polyline points="14 2 14 8 20 8"></polyline>
    <line x1="16" y1="13" x2="8" y2="13"></line>
    <line x1="16" y1="17" x2="8" y2="17"></line>
    <polyline points="10 9 9 9 8 9"></polyline>
  </svg>
);

const Spinner = () => (
  <svg className="pulse-animation" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
    <circle cx="12" cy="12" r="10" strokeDasharray="32" strokeDashoffset="16" />
  </svg>
);

export default function Home() {
  // Dynamic host-based API URL resolution to prevent CORS and mixed-content issues
  const [apiUrl] = useState(() => {
    if (typeof window !== "undefined") {
      const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
      if (isLocalhost) {
        return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      } else {
        const envUrl = process.env.NEXT_PUBLIC_API_URL;
        const isEnvLocal = envUrl && (envUrl.includes("localhost") || envUrl.includes("127.0.0.1"));
        return isEnvLocal ? `${window.location.origin}/api/backend` : (envUrl || `${window.location.origin}/api/backend`);
      }
    }
    return "http://localhost:8000";
  });

  // App States
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [selectedIndustry, setSelectedIndustry] = useState<Industry | null>(null);
  
  // File States
  const [file, setFile] = useState<File | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [shakeError, setShakeError] = useState(false);

  // Processing & Extraction States
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<string>("");
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [manualInputs, setManualInputs] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<"process" | "existing">("process");
  const [originalData, setOriginalData] = useState<Record<string, any>>({});

  // In-Memory Session Results History
  const [history, setHistory] = useState<SessionResult[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Clean up object URL to prevent memory leaks
  useEffect(() => {
    return () => {
      if (fileUrl && fileUrl.startsWith("blob:")) {
        URL.revokeObjectURL(fileUrl);
      }
    };
  }, [fileUrl]);

  // Sync chosen industry CSS variables to document body for sleek theme transitions
  useEffect(() => {
    document.body.className = "";
    if (selectedIndustry) {
      document.body.classList.add(`theme-${selectedIndustry}`);
    }
  }, [selectedIndustry]);

  // Handle errors with animated shake effect
  const triggerError = (msg: string) => {
    setErrorMessage(msg);
    setShakeError(true);
    setTimeout(() => setShakeError(false), 500);
  };

  const handleSelectIndustry = (industry: Industry) => {
    setSelectedIndustry(industry);
    setErrorMessage(null);
  };

  const handleContinue = () => {
    if (!selectedIndustry) {
      triggerError("Please select an industry to continue.");
      return;
    }
    setStep(2);
    setErrorMessage(null);
  };

  const handleBack = () => {
    // Reset file and results states when changing industry context
    setFile(null);
    setFileUrl(null);
    setResult(null);
    setOriginalData({});
    setActiveTab("process");
    setErrorMessage(null);
    setStep(1);
  };

  // Helper function to read metadata and load files into preview URL
  const loadFileObject = (selectedFile: File) => {
    if (selectedFile.type !== "application/pdf" && !selectedFile.name.toLowerCase().endsWith(".pdf")) {
      triggerError("Only PDF files are supported.");
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      triggerError("PDF file must be 10 MB or smaller.");
      return;
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    setFile(selectedFile);
    setFileUrl(objectUrl);
    setResult(null); // Clear previous output
    setErrorMessage(null);
    setStep(3); // Shift user to preview/process split screen
  };

  // File dropzone events
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      loadFileObject(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      loadFileObject(e.target.files[0]);
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  // Load preset demonstration files from frontend public/demo-pdfs
  const handleLoadDemoPdf = async (isNegative: boolean = false) => {
    if (!selectedIndustry) return;
    
    let demoFileName = `${selectedIndustry}_demo.pdf`;
    if (selectedIndustry === "insurance" && isNegative) {
      demoFileName = "insurance_negative_demo.pdf";
    }

    setErrorMessage(null);
    setIsProcessing(true);
    setProcessingStatus("Fetching demo PDF file...");

    try {
      const demoUrl = `/demo-pdfs/${demoFileName}`;
      const response = await fetch(demoUrl);
      if (!response.ok) {
        throw new Error(`Demo file not found. Ensure it was successfully generated.`);
      }

      const blob = await response.blob();
      const demoFile = new File([blob], demoFileName, { type: "application/pdf" });
      
      loadFileObject(demoFile);
    } catch (err: any) {
      triggerError(err.message || "Failed to load the demo PDF.");
    } finally {
      setIsProcessing(false);
      setProcessingStatus("");
    }
  };

  // POST document processing request to FastAPI
  const handleProcessDocument = async () => {
    if (!file || !selectedIndustry) {
      triggerError("Missing document file or industry context.");
      return;
    }

    setIsProcessing(true);
    setResult(null);
    setErrorMessage(null);
    setManualInputs({});

    // Dynamic micro loading labels
    const steps = [
      "Extracting plain text from PDF pages...",
      "Submitting text & JSON schema to OpenAI...",
      "Running deterministic validations...",
      "Aggregating final results status..."
    ];
    let stepIndex = 0;
    setProcessingStatus(steps[0]);

    const statusInterval = setInterval(() => {
      if (stepIndex < steps.length - 1) {
        stepIndex++;
        setProcessingStatus(steps[stepIndex]);
      }
    }, 2000);

    const formData = new FormData();
    formData.append("industry", selectedIndustry);
    formData.append("file", file);

    try {
      const response = await fetch(`${apiUrl}/api/process-document`, {
        method: "POST",
        body: formData
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || `Server returned error status ${response.status}`);
      }

      clearInterval(statusInterval);
      setProcessingStatus("Complete!");
      
      const extractionResult: ProcessResponse = data;
      setResult(extractionResult);
      setOriginalData(extractionResult.extracted_data);
      
      const initialInputs: Record<string, string> = {};
      Object.entries(extractionResult.extracted_data).forEach(([k, v]) => {
        initialInputs[k] = v !== null ? String(v) : "";
      });
      setManualInputs(initialInputs);

      // Save valid output to temporary in-memory session history
      const newHistoryItem: SessionResult = {
        id: Math.random().toString(36).substring(2, 9),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        industry: extractionResult.industry,
        document_type: extractionResult.document_type,
        file_name: extractionResult.file_name,
        extracted_data: extractionResult.extracted_data,
        extracted_fields: extractionResult.extracted_fields,
        validation: extractionResult.validation,
        overall_status: extractionResult.overall_status,
        pdfUrl: fileUrl || "",
        file: file,
        original_data: extractionResult.extracted_data
      };

      setHistory(prev => [newHistoryItem, ...prev]);

    } catch (err: any) {
      clearInterval(statusInterval);
      triggerError(err.message || "An unexpected error occurred during processing.");
    } finally {
      setIsProcessing(false);
      setProcessingStatus("");
    }
  };

  // Inspect previous session items
  const handleSelectHistoryItem = (item: SessionResult) => {
    setSelectedIndustry(item.industry as Industry);
    
    if (item.file && item.file.size > 0) {
      // Create a fresh working Blob URL from the stored file object
      const newUrl = URL.createObjectURL(item.file);
      setFile(item.file);
      setFileUrl(newUrl);
    } else {
      // Fallback check to support hot-reloaded/legacy session items without crashing
      setFile(new File([], item.file_name, { type: "application/pdf" }));
      setFileUrl(item.pdfUrl);
    }
    
    setOriginalData(item.original_data || item.extracted_data);

    setResult({
      success: true,
      industry: item.industry,
      document_type: item.document_type,
      file_name: item.file_name,
      extracted_data: item.extracted_data,
      extracted_fields: item.extracted_fields,
      validation: item.validation,
      overall_status: item.overall_status
    });
    const initialInputs: Record<string, string> = {};
    Object.entries(item.extracted_data).forEach(([k, v]) => {
      initialInputs[k] = v !== null ? String(v) : "";
    });
    setManualInputs(initialInputs);
    setErrorMessage(null);
    setStep(3);
  };

  const triggerRevalidateWithInputs = (currentInputs: Record<string, string>) => {
    if (!result) return;
    
    const updatedData = { ...result.extracted_data };
    const updatedValidation = { ...result.validation };
    const updatedExtractedFields = { ...result.extracted_fields };
    
    // Copy user inputs to updated data
    Object.entries(currentInputs).forEach(([key, val]) => {
      updatedData[key] = val === "" ? null : val;
    });
    
    let allValid = true;
    
    // Re-run validation rules on all fields
    Object.keys(updatedValidation).forEach((fieldName) => {
      const val = updatedData[fieldName];
      
      const currentPolicyType = updatedData["policy_type"];
      const isAccidentPol = currentPolicyType === "Travel Insurance" || currentPolicyType === "Personal Accident Insurance" || currentPolicyType === "Motor/Auto Insurance" || currentPolicyType === "Health Insurance";
      
      let fieldLabel = fieldName.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
      if (fieldName === "accident_date" && !isAccidentPol) {
        fieldLabel = "Incident Date";
      }

      const isApplicable = result.extracted_fields?.[fieldName]?.applicable !== false;
      
      if (!isApplicable) {
        updatedValidation[fieldName] = {
          valid: true,
          message: `${fieldLabel} is not applicable to this document layout.`
        };
        return;
      }
      
      if (val === null || val === undefined || String(val).trim() === "") {
        updatedValidation[fieldName] = {
          valid: false,
          message: `${fieldLabel} is empty.`
        };
        allValid = false;
        return;
      }
      
      const fieldNameLower = fieldName.toLowerCase();
      
      // Date validations
      if (fieldNameLower.includes("date") || fieldNameLower === "date_of_birth") {
        const dateStr = String(val).trim();
        // Regex check for ISO YYYY-MM-DD
        const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
        if (!dateRegex.test(dateStr)) {
          updatedValidation[fieldName] = {
            valid: false,
            message: `${fieldLabel} has an invalid date format: '${val}' (expected YYYY-MM-DD).`
          };
          allValid = false;
        } else {
          // Check if valid calendar date
          const d = new Date(dateStr);
          if (isNaN(d.getTime())) {
            updatedValidation[fieldName] = {
              valid: false,
              message: `${fieldLabel} has an invalid calendar date: '${val}'.`
            };
            allValid = false;
          } else {
            updatedValidation[fieldName] = {
              valid: true,
              message: `${fieldLabel} is valid (${val}).`
            };
          }
        }
      } 
      // Numeric amount validation
      else if (fieldNameLower === "amount") {
        const clean = String(val).replace("$", "").replace(",", "").trim();
        const num = parseFloat(clean);
        if (isNaN(num)) {
          updatedValidation[fieldName] = {
            valid: false,
            message: `${fieldLabel} must be a valid number: '${val}'.`
          };
          allValid = false;
        } else {
          updatedValidation[fieldName] = {
            valid: true,
            message: `${fieldLabel} is valid (${num}).`
          };
        }
      } 
      // Default string validation
      else {
        updatedValidation[fieldName] = {
          valid: true,
          message: `${fieldLabel} found.`
        };
      }
    });
    
    const nextStatus = allValid ? "ready_for_review" : "needs_review";
    
    // Update active result state
    setResult({
      ...result,
      extracted_data: updatedData,
      extracted_fields: updatedExtractedFields,
      validation: updatedValidation,
      overall_status: nextStatus
    });
    
    // Also sync back to history item so user navigation is saved!
    setHistory(prev => prev.map(item => {
      if (item.file_name === result.file_name && item.industry === result.industry) {
        return {
          ...item,
          extracted_data: updatedData,
          extracted_fields: updatedExtractedFields,
          validation: updatedValidation,
          overall_status: nextStatus
        };
      }
      return item;
    }));
  };

  const [editingFields, setEditingFields] = useState<Record<string, boolean>>({});
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownloadUpdatedPdf = async () => {
    if (!result || !selectedIndustry || result.overall_status !== "ready_for_review") return;
    
    setIsDownloading(true);
    try {
      const response = await fetch(`${apiUrl}/api/generate-pdf`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          file_name: result.file_name,
          industry: result.industry,
          document_type: result.document_type,
          extracted_data: result.extracted_data,
          validation: result.validation,
          overall_status: result.overall_status,
          original_data: originalData
        })
      });
      
      if (!response.ok) {
        throw new Error("Failed to generate updated PDF summary copy.");
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      
      let baseName = result.file_name;
      if (baseName.toLowerCase().endsWith(".pdf")) {
        baseName = baseName.slice(0, -4);
      }
      a.download = `${baseName}-updated.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      triggerError(err.message || "Failed to download PDF summary.");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleUpdateAndRevalidate = () => {
    triggerRevalidateWithInputs(manualInputs);
  };

  const handleClearHistory = () => {
    setHistory([]);
  };

  return (
    <div style={{ position: "relative", zIndex: 1, minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <div className="bg-grid-overlay" />
      <div className="bg-radial-glow" />

      {/* Main Header navigation */}
      <header style={{ borderBottom: "1px solid var(--panel-border)", padding: "16px 32px", display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(255, 255, 255, 0.8)", backdropFilter: "blur(12px)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "var(--accent-gradient)", display: "flex", alignItems: "center", justifyItems: "center", justifyContent: "center", fontWeight: 800, color: "#fff" }}>AI</div>
          <span style={{ fontSize: "18px", fontWeight: 700, letterSpacing: "-0.5px" }}>Document Automation <span style={{ fontSize: "11px", opacity: 0.8, background: "rgba(15,23,42,0.05)", color: "var(--text-secondary)", padding: "2px 6px", borderRadius: "4px", marginLeft: "6px" }}>MVP</span></span>
        </div>
        {step > 1 && (
          <button className="btn-secondary" style={{ padding: "8px 16px", fontSize: "13px" }} onClick={handleBack}>
            <ArrowLeftIcon /> Change Industry
          </button>
        )}
      </header>

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: "40px 32px", maxWidth: "1400px", width: "100%", margin: "0 auto", display: "flex", flexDirection: "column", gap: "32px" }}>
        
        {/* Error message strip */}
        {errorMessage && (
          <div className={`glass-panel ${shakeError ? "shake-animation" : ""}`} style={{ borderColor: "rgba(239, 68, 68, 0.2)", padding: "16px 20px", display: "flex", alignItems: "center", gap: "12px", background: "var(--invalid-glow)" }}>
            <span style={{ color: "var(--invalid-color)", display: "inline-flex" }}><AlertIcon /></span>
            <span style={{ fontSize: "14px", color: "var(--invalid-color)" }}>{errorMessage}</span>
          </div>
        )}

        {/* SCREEN 1: INDUSTRY SELECTION */}
        {step === 1 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "32px", maxWidth: "800px", margin: "40px auto", width: "100%" }}>
            <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: "12px" }}>
              <h1 style={{ fontSize: "36px", fontWeight: 800, letterSpacing: "-1px" }}>AI-Driven Document Extraction</h1>
              <p style={{ color: "var(--text-secondary)", fontSize: "16px", maxWidth: "600px", margin: "0 auto" }}>
                Select an industry configuration to apply custom LLM structured extraction prompt rules and deterministic validators.
              </p>
            </div>

            <div className="glass-panel" style={{ padding: "32px", display: "flex", flexDirection: "column", gap: "24px" }}>
              <h2 style={{ fontSize: "18px", fontWeight: 600 }}>Select Target Industry</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
                
                {/* Insurance Card */}
                <div 
                  className={`industry-card ${selectedIndustry === "insurance" ? "selected" : ""}`}
                  onClick={() => handleSelectIndustry("insurance")}
                >
                  <div style={{ color: "var(--accent-color)" }}><ShieldIcon /></div>
                  <h3 style={{ fontWeight: 600, fontSize: "16px", marginTop: "8px" }}>Insurance Claims</h3>
                  <p style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Processes claims documents, extracting claimant name, policy code, accident date, and claim category.</p>
                </div>

                {/* Finance Card */}
                <div 
                  className={`industry-card ${selectedIndustry === "finance" ? "selected" : ""}`}
                  onClick={() => handleSelectIndustry("finance")}
                >
                  <div style={{ color: "var(--accent-color)" }}><FinanceIcon /></div>
                  <h3 style={{ fontWeight: 600, fontSize: "16px", marginTop: "8px" }}>Finance & Expenses</h3>
                  <p style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Extracts employee names, numeric expense amounts, purchase dates, and expense classification tags.</p>
                </div>

                {/* Healthcare Card */}
                <div 
                  className={`industry-card ${selectedIndustry === "healthcare" ? "selected" : ""}`}
                  onClick={() => handleSelectIndustry("healthcare")}
                >
                  <div style={{ color: "var(--accent-color)" }}><HealthcareIcon /></div>
                  <h3 style={{ fontWeight: 600, fontSize: "16px", marginTop: "8px" }}>Healthcare Registrations</h3>
                  <p style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Parses patient registrations, mapping name, birthdate, consult type, and appointment details.</p>
                </div>

              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: "20px" }}>
                <button 
                  className="btn-primary" 
                  onClick={handleContinue}
                  disabled={!selectedIndustry}
                >
                  Continue
                </button>
              </div>
            </div>
          </div>
        )}

        {/* SCREEN 2: CHOOSE / UPLOAD PDF FILE */}
        {step === 2 && selectedIndustry && (
          <div style={{ maxWidth: "600px", margin: "40px auto", width: "100%", display: "flex", flexDirection: "column", gap: "24px" }}>
            <div className="glass-panel" style={{ padding: "32px", display: "flex", flexDirection: "column", gap: "24px" }}>
              {/* Workflow Mode Tabs Switcher */}
              <div className="tab-container" style={{ display: "flex", gap: "8px", background: "rgba(15, 23, 42, 0.04)", padding: "4px", borderRadius: "10px", marginBottom: "8px" }}>
                <button 
                  className={`tab-btn ${activeTab === "process" ? "active" : ""}`}
                  style={{ 
                    flex: 1, 
                    padding: "10px", 
                    borderRadius: "8px", 
                    fontSize: "13.5px", 
                    fontWeight: 600, 
                    border: "none", 
                    cursor: "pointer", 
                    background: activeTab === "process" ? "#ffffff" : "transparent",
                    color: activeTab === "process" ? "var(--text-primary)" : "var(--text-secondary)",
                    boxShadow: activeTab === "process" ? "0 2px 8px rgba(15, 23, 42, 0.08)" : "none",
                    transition: "all 0.2s ease" 
                  }}
                  onClick={() => setActiveTab("process")}
                >
                  Process New Document
                </button>
                <button 
                  className={`tab-btn ${activeTab === "existing" ? "active" : ""}`}
                  style={{ 
                    flex: 1, 
                    padding: "10px", 
                    borderRadius: "8px", 
                    fontSize: "13.5px", 
                    fontWeight: 600, 
                    border: "none", 
                    cursor: "pointer", 
                    background: activeTab === "existing" ? "#ffffff" : "transparent",
                    color: activeTab === "existing" ? "var(--text-primary)" : "var(--text-secondary)",
                    boxShadow: activeTab === "existing" ? "0 2px 8px rgba(15, 23, 42, 0.08)" : "none",
                    transition: "all 0.2s ease" 
                  }}
                  onClick={() => setActiveTab("existing")}
                >
                  Existing Data Validation
                </button>
              </div>

              <div>
                <span style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "1px", color: "var(--accent-color)" }}>
                  {selectedIndustry} Config Activated
                </span>
                <h2 style={{ fontSize: "22px", fontWeight: 800, marginTop: "4px" }}>
                  {activeTab === "existing" ? "Validate Existing Data" : "Upload Document for Analysis"}
                </h2>
                <p style={{ fontSize: "13.5px", color: "var(--text-secondary)", marginTop: "6px" }}>
                  {activeTab === "existing" 
                    ? "Upload an existing document containing previously collected information to identify missing or incorrect data." 
                    : "Provide a text-based PDF (max 10MB) to run structural extraction."}
                </p>
              </div>

              {/* Drag and Drop Zone */}
              <div 
                className={`dropzone ${isDragging ? "active" : ""}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={triggerFileSelect}
              >
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  style={{ display: "none" }} 
                  accept=".pdf"
                  onChange={handleFileChange} 
                />
                <div style={{ color: isDragging ? "var(--accent-color)" : "var(--text-secondary)", transition: "var(--transition-smooth)" }}>
                  <UploadIcon />
                </div>
                <div>
                  <p style={{ fontWeight: 600, fontSize: "15px" }}>Drag & Drop PDF here</p>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>or click to browse local files</p>
                </div>
              </div>

              {/* Demo PDF section */}
              <div style={{ display: "flex", flexDirection: "column", gap: "12px", borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: "20px" }}>
                <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-secondary)" }}>OR use pre-generated test documents:</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
                  {activeTab === "existing" ? (
                    <button 
                      className="btn-secondary" 
                      style={{ flex: 1, minWidth: "160px", justifyContent: "center" }} 
                      onClick={() => handleLoadDemoPdf(selectedIndustry === "insurance")}
                    >
                      Use Demo Existing Document
                    </button>
                  ) : (
                    <>
                      <button className="btn-secondary" style={{ flex: 1, minWidth: "160px", justifyContent: "center" }} onClick={() => handleLoadDemoPdf(false)}>
                        Use Valid Demo PDF
                      </button>
                      {selectedIndustry === "insurance" && (
                        <button className="btn-secondary" style={{ flex: 1, minWidth: "160px", justifyContent: "center", borderColor: "rgba(239, 68, 68, 0.2)" }} onClick={() => handleLoadDemoPdf(true)}>
                          Use Negative Demo PDF
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>

            </div>
          </div>
        )}

        {/* SCREEN 3: PDF SPLIT PREVIEW & RESULTS COMPONENT */}
        {step === 3 && selectedIndustry && file && (
          !result ? (
            /* BEFORE PROCESSING: 50/50 Split (PDF Preview left, Placeholders & Control right) */
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "32px", alignItems: "start" }}>
              
              {/* Left side PDF Embed Preview */}
              <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <div style={{ color: "var(--accent-color)" }}><FilePdfIcon /></div>
                    <div>
                      <h3 style={{ fontSize: "14px", fontWeight: 600, maxWidth: "250px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {file.name}
                      </h3>
                      <p style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                        {(file.size / 1024).toFixed(1)} KB • PDF Document
                      </p>
                    </div>
                  </div>
                  <button className="btn-secondary" style={{ padding: "8px 12px", fontSize: "12px" }} onClick={() => { setFile(null); setFileUrl(null); setResult(null); setStep(2); }}>
                    Replace File
                  </button>
                </div>

                <div className="preview-container">
                  {fileUrl ? (
                    <object 
                      key={fileUrl}
                      data={fileUrl} 
                      type="application/pdf"
                      style={{ width: "100%", height: "100%", border: "none" }}
                    >
                      <div className="preview-placeholder">
                        <span style={{ fontSize: "13px" }}>PDF preview not supported by browser. <a href={fileUrl} target="_blank" rel="noreferrer" style={{ textDecoration: "underline", color: "var(--accent-color)" }}>Open PDF in new tab</a></span>
                      </div>
                    </object>
                  ) : (
                    <div className="preview-placeholder">
                      <Spinner />
                      <span>Preparing preview canvas...</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Right side Extraction Results Panel */}
              <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                
                {/* Operations Control box */}
                <div className="glass-panel" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <h3 style={{ fontSize: "16px", fontWeight: 600 }}>Processing Controls</h3>
                    <span style={{ fontSize: "11px", padding: "4px 8px", borderRadius: "4px", background: "var(--accent-glow)", color: "var(--accent-color)", fontWeight: 700, textTransform: "uppercase" }}>
                      {selectedIndustry}
                    </span>
                  </div>

                  {!isProcessing && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                      <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                        Document is loaded and ready. Click &quot;Process Document&quot; to parse plain text, extract information using OpenAI structure filters, and apply validation schemas.
                      </p>
                      <button className="btn-primary" style={{ width: "100%", justifyContent: "center" }} onClick={handleProcessDocument}>
                        Process Document
                      </button>
                    </div>
                  )}

                  {isProcessing && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "12px", padding: "10px 0" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <span style={{ color: "var(--accent-color)" }}><Spinner /></span>
                        <span style={{ fontWeight: 600, fontSize: "14px" }}>AI Engine Active</span>
                      </div>
                      <p style={{ fontSize: "13px", color: "var(--text-secondary)", animation: "pulse 1.5s infinite" }}>
                        {processingStatus}
                      </p>
                    </div>
                  )}
                </div>

                {/* Data Extraction Display Box (Placeholders) */}
                <div className="glass-panel" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
                  <h3 style={{ fontSize: "16px", fontWeight: 600, borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "12px" }}>
                    Extracted Information
                  </h3>

                  <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                    <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: "12px", padding: "16px", border: "1px solid rgba(255,255,255,0.04)" }}>
                      {INDUSTRY_FIELDS[selectedIndustry].map((field) => (
                        <div key={field} className="data-row">
                          <span className="data-label">{field.replace(/_/g, " ")}</span>
                          <span className="data-value" style={{ color: "var(--text-muted)", fontStyle: "italic", fontSize: "13.5px" }}>
                            [Awaiting Extraction]
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            activeTab === "existing" ? (
              /* EXISTING DATA VALIDATION WORKFLOW SCREEN */
              <div style={{ maxWidth: "1200px", width: "100%", margin: "0 auto", display: "flex", flexDirection: "column", gap: "24px" }}>
                
                {/* Header card indicating status */}
                <div className="glass-panel" style={{ padding: "20px", display: "flex", justifyContent: "space-between", alignItems: "center", borderLeft: `4px solid ${result.overall_status === "ready_for_review" ? "var(--valid-color)" : "var(--invalid-color)"}` }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <h3 style={{ fontSize: "17px", fontWeight: 700, color: "var(--text-primary)" }}>✓ Document Loaded & Validated</h3>
                      {result.overall_status === "ready_for_review" ? (
                        <div className="status-badge ready" style={{ display: "flex", alignItems: "center", gap: "4px", background: "rgba(22, 163, 74, 0.1)", color: "#16a34a", padding: "4px 8px", borderRadius: "4px", fontSize: "12px", fontWeight: 700 }}>
                          <CheckIcon /> Complete
                        </div>
                      ) : (
                        <div className="status-badge review" style={{ display: "flex", alignItems: "center", gap: "4px", background: "rgba(239, 68, 68, 0.1)", color: "#ef4444", padding: "4px 8px", borderRadius: "4px", fontSize: "12px", fontWeight: 700 }}>
                          <AlertIcon /> Needs Review
                        </div>
                      )}
                    </div>
                    <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "6px" }}>
                      Industry: <strong style={{ textTransform: "capitalize" }}>{selectedIndustry}</strong> • File: {file.name}
                    </p>
                  </div>
                  <div style={{ display: "flex", gap: "10px" }}>
                    <button className="btn-secondary" style={{ padding: "8px 16px", fontSize: "13px" }} onClick={handleProcessDocument} disabled={isProcessing}>
                      Re-Process
                    </button>
                    <button 
                      className="btn-primary" 
                      style={{ padding: "8px 16px", fontSize: "13px" }} 
                      onClick={() => { setFile(null); setFileUrl(null); setResult(null); setStep(2); }}
                    >
                      Process Another Document
                    </button>
                  </div>
                </div>

                {/* 50/50 Layout Side-by-Side: PDF Preview left, Validation right */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", alignItems: "start" }}>
                  
                  {/* Left Column: PDF Preview */}
                  <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
                    <h3 style={{ fontSize: "15px", fontWeight: 600, borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "12px" }}>
                      Uploaded Document Preview
                    </h3>
                    <div className="preview-container" style={{ height: "550px", width: "100%", background: "#f8fafc", borderRadius: "8px" }}>
                      {fileUrl ? (
                        <object 
                          key={fileUrl}
                          data={fileUrl} 
                          type="application/pdf"
                          style={{ width: "100%", height: "100%", borderRadius: "8px", border: "none" }}
                        >
                          <div className="preview-placeholder" style={{ padding: "40px", textAlign: "center" }}>
                            <span style={{ fontSize: "13.5px", color: "var(--text-secondary)" }}>PDF preview not supported by browser. <a href={fileUrl} target="_blank" rel="noreferrer" style={{ textDecoration: "underline", color: "var(--accent-color)" }}>Open PDF in new tab</a></span>
                          </div>
                        </object>
                      ) : (
                        <div className="preview-placeholder" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: "10px" }}>
                          <Spinner />
                          <span>Loading preview...</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Column: Validation & Completion Forms */}
                  <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                    
                    <div className="glass-panel" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                      <h3 style={{ fontSize: "16px", fontWeight: 600, borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "12px", marginBottom: "4px" }}>
                        Existing Data Validation Checklist
                      </h3>

                      {result.overall_status === "ready_for_review" ? (
                        <div style={{ background: "rgba(22, 163, 74, 0.08)", border: "1px solid rgba(22, 163, 74, 0.2)", padding: "12px", borderRadius: "8px", color: "#16a34a", fontSize: "13px", fontWeight: 500, display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                          <span>✓</span>
                          <span>All fields validated! You can now download the updated PDF summary below.</span>
                        </div>
                      ) : (
                        <div style={{ background: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.2)", padding: "12px", borderRadius: "8px", color: "#ef4444", fontSize: "13px", fontWeight: 500, display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                          <span>⚠</span>
                          <span>Missing or incorrect fields detected. Please correct them below, click &apos;Save / Update&apos;, and then download the updated PDF.</span>
                        </div>
                      )}

                      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                        {INDUSTRY_FIELDS[selectedIndustry].map((key) => {
                          const val = result.extracted_data[key];
                          
                          const currentPolicyType = manualInputs["policy_type"] || result.extracted_data["policy_type"];
                          const isAccidentPol = currentPolicyType === "Travel Insurance" || currentPolicyType === "Personal Accident Insurance" || currentPolicyType === "Motor/Auto Insurance" || currentPolicyType === "Health Insurance";
                          
                          let displayName = key.replace(/_/g, " ");
                          if (key === "accident_date") {
                            displayName = isAccidentPol ? "Accident Date" : "Incident Date";
                          }
                          
                          const isApplicable = result.extracted_fields?.[key]?.applicable !== false;
                          const isValid = result.validation[key]?.valid !== false;
                          
                          let statusText = "✓ Available / Valid";
                          let statusColor = "#16a34a"; // Green
                          let showInput = false;

                          if (!isApplicable) {
                            statusText = "— Not Applicable";
                            statusColor = "#64748b"; // Slate Gray
                          } else if (val === null || val === undefined || String(val).trim() === "") {
                            statusText = "⚠ Data Missing";
                            statusColor = "#ea580c"; // Orange
                            showInput = true;
                          } else if (!isValid) {
                            statusText = "⚠ Incorrect / Inconsistent";
                            statusColor = "#ef4444"; // Red
                            showInput = true;
                          }

                          // If explicitly toggled to edit mode
                          const isEditing = !!editingFields[key];
                          if (isEditing && isApplicable) {
                            showInput = true;
                          }

                          return (
                            <div key={key} style={{ display: "flex", flexDirection: "column", borderBottom: "1px solid rgba(15,23,42,0.05)", paddingBottom: "16px" }}>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: "10px" }}>
                                <div style={{ display: "flex", flexDirection: "column" }}>
                                  <span style={{ fontSize: "14px", fontWeight: 700, textTransform: "capitalize", color: "var(--text-primary)" }}>
                                    {displayName}
                                  </span>
                                  {val !== null && val !== "" && isApplicable && !showInput && (
                                    <span style={{ fontSize: "13.5px", color: "var(--text-secondary)", marginTop: "4px" }}>
                                      {key === "amount" ? (String(val).startsWith("$") ? String(val) : `$${val}`) : String(val)}
                                    </span>
                                  )}
                                </div>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                  <span style={{ fontSize: "12px", fontWeight: 700, color: statusColor, textTransform: "uppercase" }}>
                                    {statusText}
                                  </span>
                                  {isApplicable && !showInput && (
                                    <button 
                                      style={{ background: "transparent", border: "none", cursor: "pointer", fontSize: "11px", color: "var(--accent-color)", fontWeight: 600, textDecoration: "underline", padding: 0 }}
                                      onClick={() => setEditingFields({ ...editingFields, [key]: true })}
                                    >
                                      Edit
                                    </button>
                                  )}
                                </div>
                              </div>

                              {showInput && (
                                <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "10px", width: "100%", background: "rgba(15, 23, 42, 0.02)", padding: "12px", borderRadius: "8px", border: "1px solid rgba(15, 23, 42, 0.06)" }}>
                                  <span style={{ fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
                                    {val === null || val === "" ? "Provide Missing Value:" : "Correct Value:"}
                                  </span>
                                  {key.toLowerCase().includes("date") || key === "date_of_birth" ? (
                                    <input 
                                      type="date" 
                                      className="form-input" 
                                      style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", color: "var(--text-primary)", outline: "none" }}
                                      value={manualInputs[key] || ""} 
                                      onChange={(e) => {
                                        const nextInputs = { ...manualInputs, [key]: e.target.value };
                                        setManualInputs(nextInputs);
                                        triggerRevalidateWithInputs(nextInputs);
                                      }}
                                    />
                                  ) : key === "policy_type" ? (
                                    <select 
                                      className="form-input" 
                                      style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", color: "var(--text-primary)", outline: "none" }}
                                      value={manualInputs[key] || ""} 
                                      onChange={(e) => {
                                        const nextInputs = { ...manualInputs, [key]: e.target.value };
                                        setManualInputs(nextInputs);
                                        triggerRevalidateWithInputs(nextInputs);
                                      }}
                                    >
                                      <option value="">-- Select Policy Type --</option>
                                      <option value="Health Insurance">Health Insurance</option>
                                      <option value="Life Insurance">Life Insurance</option>
                                      <option value="Motor/Auto Insurance">Motor/Auto Insurance</option>
                                      <option value="Home Insurance">Home Insurance</option>
                                      <option value="Travel Insurance">Travel Insurance</option>
                                      <option value="Personal Accident Insurance">Personal Accident Insurance</option>
                                    </select>
                                  ) : key === "category" ? (
                                    <select 
                                      className="form-input" 
                                      style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", color: "var(--text-primary)", outline: "none" }}
                                      value={manualInputs[key] || ""} 
                                      onChange={(e) => {
                                        const nextInputs = { ...manualInputs, [key]: e.target.value };
                                        setManualInputs(nextInputs);
                                        triggerRevalidateWithInputs(nextInputs);
                                      }}
                                    >
                                      <option value="">-- Select Category --</option>
                                      <option value="Travel">Travel</option>
                                      <option value="Meals">Meals</option>
                                      <option value="Office Supplies">Office Supplies</option>
                                      <option value="Software">Software</option>
                                      <option value="Others">Others</option>
                                    </select>
                                  ) : key === "amount" ? (
                                    <input 
                                      type="number" 
                                      placeholder="Enter amount (e.g. 250.00)"
                                      className="form-input" 
                                      style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", color: "var(--text-primary)", outline: "none" }}
                                      value={manualInputs[key] || ""} 
                                      onChange={(e) => setManualInputs({ ...manualInputs, [key]: e.target.value })}
                                      onBlur={() => triggerRevalidateWithInputs(manualInputs)}
                                    />
                                  ) : (
                                    <input 
                                      type="text" 
                                      placeholder={`Enter ${displayName.replace(/\b\w/g, c => c.toUpperCase())}`}
                                      className="form-input" 
                                      style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", color: "var(--text-primary)", outline: "none" }}
                                      value={manualInputs[key] || ""} 
                                      onChange={(e) => setManualInputs({ ...manualInputs, [key]: e.target.value })}
                                      onBlur={() => triggerRevalidateWithInputs(manualInputs)}
                                    />
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>

                      {/* Save / Update button */}
                      <button 
                        className="btn-primary" 
                        style={{ marginTop: "16px", width: "100%", justifyContent: "center", display: "flex", gap: "8px" }}
                        onClick={() => {
                          handleUpdateAndRevalidate();
                          setEditingFields({});
                        }}
                      >
                        Save/Update
                      </button>
                    </div>

                    {/* Overall Status block and Download Button */}
                    <div className="glass-panel" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(15,23,42,0.05)", paddingBottom: "12px" }}>
                        <div style={{ display: "flex", flexDirection: "column" }}>
                          <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
                            Overall Dataset Status:
                          </span>
                          <span style={{ fontSize: "18px", fontWeight: 800, color: result.overall_status === "ready_for_review" ? "var(--valid-color)" : "var(--invalid-color)", marginTop: "4px" }}>
                            {result.overall_status === "ready_for_review" ? "✓ Complete" : "⚠ Needs Review"}
                          </span>
                        </div>
                      </div>

                      <button
                        className="btn-primary"
                        style={{ 
                          width: "100%", 
                          justifyContent: "center", 
                          padding: "12px", 
                          background: result.overall_status === "ready_for_review" ? "var(--accent-gradient)" : "#cbd5e1",
                          color: result.overall_status === "ready_for_review" ? "#ffffff" : "#94a3b8",
                          border: "none",
                          cursor: result.overall_status === "ready_for_review" ? "pointer" : "not-allowed",
                          opacity: result.overall_status === "ready_for_review" ? 1 : 0.6,
                          pointerEvents: result.overall_status === "ready_for_review" ? "auto" : "none",
                          boxShadow: result.overall_status === "ready_for_review" ? "0 4px 12px rgba(99, 102, 241, 0.2)" : "none"
                        }}
                        disabled={result.overall_status !== "ready_for_review" || isDownloading}
                        onClick={handleDownloadUpdatedPdf}
                      >
                        {isDownloading ? <Spinner /> : "Download Updated PDF"}
                      </button>
                    </div>

                  </div>
                </div>

              </div>
            ) : (
              /* legacy PROCESS NEW DOCUMENT WORKFLOW SCREEN */
              <div style={{ maxWidth: "1200px", width: "100%", margin: "0 auto", display: "flex", flexDirection: "column", gap: "24px" }}>
                
                {/* Header card indicating success */}
                <div className="glass-panel" style={{ padding: "20px", display: "flex", justifyContent: "space-between", alignItems: "center", borderLeft: `4px solid ${result.overall_status === "ready_for_review" ? "var(--valid-color)" : "var(--invalid-color)"}` }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <h3 style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-primary)" }}>✓ Document Processed Successfully</h3>
                      {result.overall_status === "ready_for_review" ? (
                        <div className="status-badge ready">
                          <CheckIcon /> Ready for Review
                        </div>
                      ) : (
                        <div className="status-badge review">
                          <AlertIcon /> Needs Review
                        </div>
                      )}
                    </div>
                    <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "6px" }}>
                      Industry: <strong style={{ textTransform: "capitalize" }}>{selectedIndustry}</strong> • File: {file.name}
                    </p>
                  </div>
                  <div style={{ display: "flex", gap: "10px" }}>
                    {result.overall_status === "ready_for_review" && (
                      <button 
                        className="btn-primary" 
                        style={{ 
                          padding: "8px 16px", 
                          fontSize: "13px", 
                          background: "var(--accent-gradient)",
                          border: "none",
                          boxShadow: "0 4px 12px rgba(99, 102, 241, 0.2)"
                        }} 
                        onClick={handleDownloadUpdatedPdf}
                        disabled={isDownloading}
                      >
                        {isDownloading ? <Spinner /> : "Download PDF"}
                      </button>
                    )}
                    <button className="btn-secondary" style={{ padding: "8px 16px", fontSize: "13px" }} onClick={handleProcessDocument} disabled={isProcessing}>
                      Re-Process
                    </button>
                    <button 
                      className="btn-primary" 
                      style={{ padding: "8px 16px", fontSize: "13px" }} 
                      onClick={() => { setFile(null); setFileUrl(null); setResult(null); setStep(2); }}
                    >
                      Process Another Document
                    </button>
                  </div>
                </div>

                {/* Extraction & Validation detail container (50/50 split side-by-side) */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", alignItems: "start" }}>
                  
                  {/* Section 1: Extracted Information */}
                  <div className="glass-panel" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                    <h3 style={{ fontSize: "16px", fontWeight: 600, borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "12px", marginBottom: "4px" }}>
                      Extracted Information
                    </h3>
                    
                    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                      {INDUSTRY_FIELDS[selectedIndustry].map((key) => {
                        const val = result.extracted_data[key];
                        
                        const currentPolicyType = manualInputs["policy_type"] || result.extracted_data["policy_type"];
                        const isAccidentPol = currentPolicyType === "Travel Insurance" || currentPolicyType === "Personal Accident Insurance" || currentPolicyType === "Motor/Auto Insurance" || currentPolicyType === "Health Insurance";
                        
                        let displayName = key.replace(/_/g, " ");
                        if (key === "accident_date") {
                          displayName = isAccidentPol ? "Accident Date" : "Incident Date";
                        }
                        
                        const isApplicable = result.extracted_fields?.[key]?.applicable !== false;
                        const isValid = result.validation[key]?.valid !== false;
                        
                        // 1. If not applicable, show the field as [Not Applicable]
                        if (!isApplicable) {
                          return (
                            <div key={key} className="data-row" style={{ opacity: 0.5 }}>
                              <span className="data-label" style={{ textTransform: "capitalize" }}>{displayName}</span>
                              <span className="data-value" style={{ fontStyle: "italic", color: "var(--text-muted)", fontSize: "13px" }}>[Not Applicable]</span>
                            </div>
                          );
                        }
                        
                        return (
                          <div key={key} style={{ display: "flex", flexDirection: "column", borderBottom: "1px solid rgba(255,255,255,0.04)", paddingBottom: "12px" }}>
                            <div className="data-row" style={{ borderBottom: "none", paddingBottom: 0 }}>
                              <span className="data-label" style={{ textTransform: "capitalize" }}>{displayName}</span>
                              <span className="data-value">
                                {val === null || val === "" || !isValid ? (
                                  <span style={{ color: "var(--invalid-color)", fontWeight: 600 }}>[Awaiting Input]</span>
                                ) : (
                                  key === "amount" ? (String(val).startsWith("$") ? String(val) : `$${val}`) : String(val)
                                )}
                              </span>
                            </div>
                            
                            {/* Render input form if value is missing/invalid */}
                            {!isValid && (
                              <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "8px", width: "100%", background: "rgba(239, 68, 68, 0.05)", padding: "12px", borderRadius: "8px", border: "1px solid rgba(239, 68, 68, 0.15)" }}>
                                <span style={{ fontSize: "11px", fontWeight: 700, color: "#dc2626", textTransform: "uppercase", display: "flex", alignItems: "center", gap: "4px" }}>
                                  ⚠ Data Missing
                                </span>
                                {key.toLowerCase().includes("date") || key === "date_of_birth" ? (
                                  <input 
                                    type="date" 
                                    className="form-input" 
                                    style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", color: "var(--text-primary)", outline: "none" }}
                                    value={manualInputs[key] || ""} 
                                    onChange={(e) => {
                                      const nextInputs = { ...manualInputs, [key]: e.target.value };
                                      setManualInputs(nextInputs);
                                      triggerRevalidateWithInputs(nextInputs);
                                    }}
                                  />
                                ) : key === "policy_type" ? (
                                  <select 
                                    className="form-input" 
                                    style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", color: "var(--text-primary)", outline: "none" }}
                                    value={manualInputs[key] || ""} 
                                    onChange={(e) => {
                                      const nextInputs = { ...manualInputs, [key]: e.target.value };
                                      setManualInputs(nextInputs);
                                      triggerRevalidateWithInputs(nextInputs);
                                    }}
                                  >
                                    <option value="">-- Select Policy Type --</option>
                                    <option value="Health Insurance">Health Insurance</option>
                                    <option value="Life Insurance">Life Insurance</option>
                                    <option value="Motor/Auto Insurance">Motor/Auto Insurance</option>
                                    <option value="Home Insurance">Home Insurance</option>
                                    <option value="Travel Insurance">Travel Insurance</option>
                                    <option value="Personal Accident Insurance">Personal Accident Insurance</option>
                                  </select>
                                ) : key === "category" ? (
                                  <select 
                                    className="form-input" 
                                    style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", color: "var(--text-primary)", outline: "none" }}
                                    value={manualInputs[key] || ""} 
                                    onChange={(e) => {
                                      const nextInputs = { ...manualInputs, [key]: e.target.value };
                                      setManualInputs(nextInputs);
                                      triggerRevalidateWithInputs(nextInputs);
                                    }}
                                  >
                                    <option value="">-- Select Category --</option>
                                    <option value="Travel">Travel</option>
                                    <option value="Meals">Meals</option>
                                    <option value="Office Supplies">Office Supplies</option>
                                    <option value="Software">Software</option>
                                    <option value="Others">Others</option>
                                  </select>
                                ) : key === "amount" ? (
                                  <input 
                                    type="number" 
                                    placeholder="Enter amount (e.g. 250.00)"
                                    className="form-input" 
                                    style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", color: "var(--text-primary)", outline: "none" }}
                                    value={manualInputs[key] || ""} 
                                    onChange={(e) => setManualInputs({ ...manualInputs, [key]: e.target.value })}
                                    onBlur={() => triggerRevalidateWithInputs(manualInputs)}
                                  />
                                ) : (
                                  <input 
                                    type="text" 
                                    placeholder={`Enter ${displayName.replace(/\b\w/g, c => c.toUpperCase())}`}
                                    className="form-input" 
                                    style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", color: "var(--text-primary)", outline: "none" }}
                                    value={manualInputs[key] || ""} 
                                    onChange={(e) => setManualInputs({ ...manualInputs, [key]: e.target.value })}
                                    onBlur={() => triggerRevalidateWithInputs(manualInputs)}
                                  />
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                      
                      {Object.entries(manualInputs).some(([k, v]) => {
                        const currentVal = result.extracted_data[k];
                        const compVal = v === "" ? null : (k === "amount" ? (isNaN(parseFloat(v)) ? v : parseFloat(v)) : v);
                        return currentVal !== compVal;
                      }) && (
                        <button 
                          className="btn-primary" 
                          style={{ marginTop: "16px", width: "100%", justifyContent: "center", display: "flex", gap: "8px" }}
                          onClick={handleUpdateAndRevalidate}
                        >
                          Save/Update
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Section 2: Validation Status */}
                  <div className="glass-panel" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                    <h3 style={{ fontSize: "16px", fontWeight: 600, borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "12px", marginBottom: "4px" }}>
                      Field Validation Status
                    </h3>
                    
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {Object.entries(result.validation).map(([fieldName, validate]) => (
                        <div 
                          key={fieldName} 
                          className={`validation-item ${validate.valid ? "valid" : "invalid"}`}
                        >
                          <span className="status-icon">
                            {validate.valid ? <CheckIcon /> : "×"}
                          </span>
                          <div style={{ display: "flex", flexDirection: "column" }}>
                            <span style={{ fontSize: "13px", fontWeight: 600, textTransform: "capitalize" }}>
                              {fieldName === "accident_date" ? (
                                (() => {
                                  const currentPolicyType = manualInputs["policy_type"] || result.extracted_data["policy_type"];
                                  const isAccPol = currentPolicyType === "Travel Insurance" || currentPolicyType === "Personal Accident Insurance" || currentPolicyType === "Motor/Auto Insurance" || currentPolicyType === "Health Insurance";
                                  return isAccPol ? "Accident Date" : "Incident Date";
                                })()
                              ) : fieldName.replace(/_/g, " ")}
                            </span>
                            <span style={{ fontSize: "12px", color: validate.valid ? "var(--text-secondary)" : "#fca5a5" }}>
                              {validate.message}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                </div>
              </div>
            )
          )
        )}

        {/* SESSION HISTORY BAR: CURRENT SESSIONS CACHED RESULTS */}
        {history.length > 0 && (
          <div className="glass-panel" style={{ padding: "24px", marginTop: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <h3 style={{ fontSize: "16px", fontWeight: 600 }}>Processed Session Logs</h3>
                <span style={{ fontSize: "12px", background: "rgba(255,255,255,0.08)", padding: "2px 8px", borderRadius: "999px", color: "var(--text-secondary)" }}>
                  {history.length} items
                </span>
              </div>
              <button 
                className="btn-secondary" 
                style={{ 
                  padding: "6px 12px", 
                  fontSize: "12px", 
                  borderColor: "rgba(220, 38, 38, 0.4)", 
                  color: "#b91c1c", 
                  fontWeight: 600,
                  background: "rgba(220, 38, 38, 0.04)" 
                }}
                onClick={handleClearHistory}
              >
                <TrashIcon /> Clear Session
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "16px" }}>
              {history.map((item) => (
                <div 
                  key={item.id}
                  className="glass-panel"
                  style={{ 
                    padding: "16px", 
                    cursor: "pointer", 
                    background: "rgba(255,255,255,0.01)",
                    borderLeft: `4px solid ${item.overall_status === "ready_for_review" ? "var(--valid-color)" : "var(--invalid-color)"}`
                  }}
                  onClick={() => handleSelectHistoryItem(item)}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)" }}>
                      {item.industry}
                    </span>
                    <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{item.timestamp}</span>
                  </div>
                  
                  <h4 style={{ fontSize: "13.5px", fontWeight: 600, marginTop: "6px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {item.file_name}
                  </h4>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "12px" }}>
                    <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                      {item.overall_status === "ready_for_review" ? "✓ Validated" : "⚠ Needs Review"}
                    </span>
                    <span style={{ fontSize: "11px", color: "var(--accent-color)", fontWeight: 600 }}>Inspect &rarr;</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </main>

      {/* Footer credits */}
      <footer style={{ borderTop: "1px solid rgba(255, 255, 255, 0.05)", padding: "20px 32px", textAlign: "center", fontSize: "12px", color: "var(--text-muted)", background: "rgba(2, 6, 23, 0.4)" }}>
        <p>© 2026 AI Document Automation MVP • Session results are stored in-memory only (cleared upon page exit or reload).</p>
      </footer>
    </div>
  );
}
