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
  id: string;
  industry: string;
  document_type: string;
  file_name: string;
  extracted_data: Record<string, any>;
  extracted_fields?: Record<string, any>;
  validation: Record<string, FieldValidation>;
  overall_status: "ready_for_review" | "needs_review";
  ai_provider?: string;
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
  file?: File;
  original_data?: Record<string, any>;
  ai_provider?: string;
}

interface DynamicField {
  id: number;
  name: string;
  label: string;
  industry: string;
  document_type: string;
  field_type: string;
  required: number;
  active: number;
  display_order: number;
  validation_rules: string;
}

type Industry = "insurance" | "finance" | "healthcare";

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
  <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"></polyline>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
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
  </svg>
);

const Spinner = () => (
  <svg className="pulse-animation" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round">
    <circle cx="12" cy="12" r="10" strokeDasharray="32" strokeDashoffset="16" />
  </svg>
);

export default function Home() {
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

  // Authentication State
  const [user, setUser] = useState<{ name: string; email: string; role: string; token: string } | null>(null);
  const [authView, setAuthView] = useState<"login" | "register">("login");
  const [authName, setAuthName] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authConfirmPassword, setAuthConfirmPassword] = useState("");
  const [authSuccessMessage, setAuthSuccessMessage] = useState<string | null>(null);

  // App Navigation States
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [selectedIndustry, setSelectedIndustry] = useState<Industry | null>(null);

  // Dynamic Fields Config
  const [dynamicFields, setDynamicFields] = useState<DynamicField[]>([]);
  const [editingFieldId, setEditingFieldId] = useState<number | null>(null);

  // Inline Field Creation States
  const [showAddFieldForm, setShowAddFieldForm] = useState(false);
  const [newFieldLabel, setNewFieldLabel] = useState("");
  const [newFieldType, setNewFieldType] = useState("text");
  const [newFieldRequired, setNewFieldRequired] = useState(false);
  
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

  // Session Results History
  const [history, setHistory] = useState<SessionResult[]>([]);
  
  // Email Modal States
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [recipientEmail, setRecipientEmail] = useState("");
  const [isSendingEmail, setIsSendingEmail] = useState(false);

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

  // Load session & dynamic fields on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedUser = localStorage.getItem("docauto_user");
      if (savedUser) {
        try {
          const parsed = JSON.parse(savedUser);
          setUser(parsed);
          fetchFields(parsed.token);
          fetchDocuments(parsed.token);
        } catch (e) {
          localStorage.removeItem("docauto_user");
        }
      }
    }
  }, []);

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

  // API Call: Retrieve Dynamic Fields
  const fetchFields = async (token: string) => {
    try {
      const response = await fetch(`${apiUrl}/api/fields`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setDynamicFields(data);
      }
    } catch (e) {
      console.error("Failed to load fields from API", e);
    }
  };

  // API Call: Retrieve Processed Documents History
  const fetchDocuments = async (token: string) => {
    try {
      const response = await fetch(`${apiUrl}/api/documents`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        const formatted = data.map((d: any) => ({
          id: d.id,
          timestamp: new Date(d.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          industry: d.industry,
          document_type: d.document_type,
          file_name: d.file_name,
          extracted_data: d.extracted_data,
          extracted_fields: d.extracted_fields,
          validation: d.validation,
          overall_status: d.overall_status,
          pdfUrl: "",
          original_data: d.original_data,
          ai_provider: d.ai_provider
        }));
        setHistory(formatted);
      }
    } catch (e) {
      console.error("Failed to load document history", e);
    }
  };

  // Auth Operations
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setAuthSuccessMessage(null);
    if (authPassword !== authConfirmPassword) {
      triggerError("Passwords do not match.");
      return;
    }
    try {
      const res = await fetch(`${apiUrl}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: authName,
          email: authEmail,
          password: authPassword,
          confirm_password: authConfirmPassword
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Registration failed.");
      
      setAuthSuccessMessage("Registration successful! Please login.");
      setAuthView("login");
      setAuthName("");
      setAuthPassword("");
      setAuthConfirmPassword("");
    } catch (err: any) {
      triggerError(err.message);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setAuthSuccessMessage(null);
    try {
      const res = await fetch(`${apiUrl}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail, password: authPassword })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Login failed.");
      
      const sessionData = {
        name: data.name,
        email: data.email,
        role: data.role,
        token: data.token
      };
      localStorage.setItem("docauto_user", JSON.stringify(sessionData));
      setUser(sessionData);
      setAuthPassword("");
      fetchFields(data.token);
      fetchDocuments(data.token);
    } catch (err: any) {
      triggerError(err.message);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("docauto_user");
    setUser(null);
    setStep(1);
    setFile(null);
    setFileUrl(null);
    setResult(null);
    setHistory([]);
    setSelectedIndustry(null);
    setErrorMessage(null);
    setAuthSuccessMessage(null);
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
    setFile(null);
    setFileUrl(null);
    setResult(null);
    setOriginalData({});
    setActiveTab("process");
    setErrorMessage(null);
    setStep(1);
  };

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
    setResult(null);
    setErrorMessage(null);
    setStep(3);
  };

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
        throw new Error("Demo file not found. Ensure it was successfully generated.");
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

  const handleProcessDocument = async () => {
    if (!file || !selectedIndustry || !user) {
      triggerError("Missing document file or authenticated context.");
      return;
    }
    setIsProcessing(true);
    setResult(null);
    setErrorMessage(null);
    setManualInputs({});

    const steps = [
      "Extracting plain text from PDF pages...",
      "Submitting text & dynamic database schema to AI...",
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
        headers: { Authorization: `Bearer ${user.token}` },
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

      // Refresh list
      fetchDocuments(user.token);
    } catch (err: any) {
      clearInterval(statusInterval);
      triggerError(err.message || "An unexpected error occurred during processing.");
    } finally {
      setIsProcessing(false);
      setProcessingStatus("");
    }
  };

  const handleSelectHistoryItem = (item: SessionResult) => {
    setSelectedIndustry(item.industry as Industry);
    setFile(new File([], item.file_name, { type: "application/pdf" }));
    setFileUrl("");
    setOriginalData(item.original_data || item.extracted_data);
    setResult({
      success: true,
      id: item.id,
      industry: item.industry,
      document_type: item.document_type,
      file_name: item.file_name,
      extracted_data: item.extracted_data,
      extracted_fields: item.extracted_fields,
      validation: item.validation,
      overall_status: item.overall_status,
      ai_provider: item.ai_provider
    });
    const initialInputs: Record<string, string> = {};
    Object.entries(item.extracted_data).forEach(([k, v]) => {
      initialInputs[k] = v !== null ? String(v) : "";
    });
    setManualInputs(initialInputs);
    setErrorMessage(null);
    setStep(3);
  };

  const handleSaveUpdateDocument = async () => {
    if (!result || !user) return;
    setErrorMessage(null);
    try {
      const response = await fetch(`${apiUrl}/api/documents/update`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user.token}`
        },
        body: JSON.stringify({
          id: result.id,
          extracted_data: manualInputs
        })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Failed to update document.");
      }
      const updatedResult: ProcessResponse = data;
      setResult(updatedResult);
      // Refresh database items
      fetchDocuments(user.token);
    } catch (err: any) {
      triggerError(err.message);
    }
  };

  const [isDownloading, setIsDownloading] = useState(false);
  const handleDownloadUpdatedPdf = async () => {
    if (!result || !selectedIndustry || !user) return;
    setIsDownloading(true);
    try {
      const response = await fetch(`${apiUrl}/api/generate-pdf`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user.token}`
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
      if (!response.ok) throw new Error("Failed to generate updated PDF.");
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      let baseName = result.file_name;
      if (baseName.toLowerCase().endsWith(".pdf")) baseName = baseName.slice(0, -4);
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

  const [isDownloadingAll, setIsDownloadingAll] = useState(false);
  const handleDownloadAllProcessedData = async () => {
    if (history.length === 0 || !user) return;
    setIsDownloadingAll(true);
    try {
      const payloadItems = history.map(item => ({
        file_name: item.file_name,
        industry: item.industry,
        document_type: item.document_type,
        extracted_data: item.extracted_data,
        validation: item.validation,
        overall_status: item.overall_status,
        original_data: item.original_data || item.extracted_data
      }));
      const response = await fetch(`${apiUrl}/api/generate-combined-report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user.token}`
        },
        body: JSON.stringify({ items: payloadItems })
      });
      if (!response.ok) throw new Error("Failed to compile combined PDF summary report.");
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const timestamp = new Date().toISOString().split('T')[0];
      a.download = `processed_documents_report_${timestamp}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      triggerError(err.message || "Failed to download combined report.");
    } finally {
      setIsDownloadingAll(false);
    }
  };

  const handleSendEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recipientEmail || history.length === 0 || !user) return;
    setIsSendingEmail(true);
    setErrorMessage(null);
    try {
      const payloadItems = history.map(item => ({
        file_name: item.file_name,
        industry: item.industry,
        document_type: item.document_type,
        extracted_data: item.extracted_data,
        validation: item.validation,
        overall_status: item.overall_status,
        original_data: item.original_data || item.extracted_data
      }));
      const response = await fetch(`${apiUrl}/api/send-email`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user.token}`
        },
        body: JSON.stringify({
          recipient_email: recipientEmail,
          items: payloadItems
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Email dispatch failed.");
      
      alert("Report emailed successfully!");
      setShowEmailModal(false);
      setRecipientEmail("");
    } catch (err: any) {
      triggerError(err.message);
    } finally {
      setIsSendingEmail(false);
    }
  };

  // Inline Custom Fields Creation
  const handleInlineCreateField = async () => {
    if (!result || !user) return;
    setErrorMessage(null);
    try {
      const cleanName = newFieldLabel.toLowerCase().replace(/[^a-z0-9_]/g, "").replace(/\s+/g, "_");
      if (!cleanName) throw new Error("Please enter a valid field label.");

      const payload = {
        name: cleanName,
        label: newFieldLabel,
        industry: result.industry,
        document_type: result.document_type,
        field_type: newFieldType,
        required: newFieldRequired,
        active: true,
        display_order: dynamicFields.length + 10,
        validation_rules: "{}"
      };

      const response = await fetch(`${apiUrl}/api/fields`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user.token}`
        },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to save dynamic field configuration.");
      
      setShowAddFieldForm(false);
      setNewFieldLabel("");
      setNewFieldType("text");
      setNewFieldRequired(false);
      fetchFields(user.token);
    } catch (err: any) {
      triggerError(err.message);
    }
  };

  const handleToggleFieldActive = async (fieldId: number) => {
    if (!user) return;
    try {
      const response = await fetch(`${apiUrl}/api/fields/${fieldId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${user.token}` }
      });
      if (response.ok) {
        fetchFields(user.token);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Get active fields based on current context
  const getContextFields = () => {
    if (!selectedIndustry) return [];
    const docType = result?.document_type;
    let list = dynamicFields.filter(f => f.industry === selectedIndustry && f.active === 1);
    if (docType) {
      const subset = list.filter(f => f.document_type === docType);
      if (subset.length > 0) list = subset;
    }
    return list.sort((a, b) => a.display_order - b.display_order);
  };

  // Rendering Authentication Screen if not logged in
  if (!user) {
    return (
      <div style={{ position: "relative", zIndex: 1, minHeight: "100vh", display: "flex", justifyContent: "center", alignItems: "center" }}>
        <div className="bg-grid-overlay" />
        <div className="bg-radial-glow" />
        <div className="glass-panel" style={{ padding: "40px", maxWidth: "480px", width: "100%", margin: "20px", display: "flex", flexDirection: "column", gap: "24px" }}>
          <div style={{ textAlign: "center" }}>
            <h2 style={{ fontSize: "28px", fontWeight: 800, letterSpacing: "-0.5px" }}>
              AI Document Automation
            </h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginTop: "8px" }}>
              {authView === "login" ? "Login to access secure dashboard tools" : "Create your account"}
            </p>
          </div>

          {errorMessage && (
            <div style={{ padding: "12px", background: "var(--invalid-glow)", border: "1px solid rgba(220,38,38,0.2)", borderRadius: "8px", color: "var(--invalid-color)", fontSize: "13px" }}>
              {errorMessage}
            </div>
          )}

          {authSuccessMessage && (
            <div style={{ padding: "12px", background: "var(--valid-glow)", border: "1px solid rgba(5,150,105,0.2)", borderRadius: "8px", color: "var(--valid-color)", fontSize: "13px" }}>
              {authSuccessMessage}
            </div>
          )}

          <form onSubmit={authView === "login" ? handleLogin : handleRegister} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {authView === "register" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)" }}>Full Name</label>
                <input 
                  type="text" 
                  required 
                  className="form-input" 
                  style={{ width: "100%", padding: "12px", background: "#ffffff", border: "1px solid var(--panel-border)", borderRadius: "8px", outline: "none" }}
                  value={authName} 
                  onChange={(e) => setAuthName(e.target.value)} 
                />
              </div>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)" }}>Email Address</label>
              <input 
                type="email" 
                required 
                className="form-input" 
                style={{ width: "100%", padding: "12px", background: "#ffffff", border: "1px solid var(--panel-border)", borderRadius: "8px", outline: "none" }}
                value={authEmail} 
                onChange={(e) => setAuthEmail(e.target.value)} 
              />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)" }}>Password</label>
              <input 
                type="password" 
                required 
                className="form-input" 
                style={{ width: "100%", padding: "12px", background: "#ffffff", border: "1px solid var(--panel-border)", borderRadius: "8px", outline: "none" }}
                value={authPassword} 
                onChange={(e) => setAuthPassword(e.target.value)} 
              />
            </div>
            {authView === "register" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-secondary)" }}>Confirm Password</label>
                <input 
                  type="password" 
                  required 
                  className="form-input" 
                  style={{ width: "100%", padding: "12px", background: "#ffffff", border: "1px solid var(--panel-border)", borderRadius: "8px", outline: "none" }}
                  value={authConfirmPassword} 
                  onChange={(e) => setAuthConfirmPassword(e.target.value)} 
                />
              </div>
            )}
            <button type="submit" className="btn-primary" style={{ width: "100%", justifyContent: "center", marginTop: "8px" }}>
              {authView === "login" ? "Login" : "Register"}
            </button>
          </form>

          <div style={{ textAlign: "center", borderTop: "1px solid var(--panel-border)", paddingTop: "16px" }}>
            <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
              {authView === "login" ? "Don't have an account? " : "Already have an account? "}
              <button 
                style={{ background: "transparent", border: "none", cursor: "pointer", color: "var(--accent-color)", fontWeight: 600, textDecoration: "underline", padding: 0 }}
                onClick={() => {
                  setAuthView(authView === "login" ? "register" : "login");
                  setErrorMessage(null);
                  setAuthSuccessMessage(null);
                }}
              >
                {authView === "login" ? "Register" : "Login"}
              </button>
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Rendering dashboard navigation & tabs
  return (
    <div style={{ position: "relative", zIndex: 1, minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <div className="bg-grid-overlay" />
      <div className="bg-radial-glow" />

      {/* Main Header navigation */}
      <header style={{ borderBottom: "1px solid var(--panel-border)", padding: "16px 32px", display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(255, 255, 255, 0.8)", backdropFilter: "blur(12px)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "var(--accent-gradient)", display: "flex", alignItems: "center", justifyItems: "center", justifyContent: "center", fontWeight: 800, color: "#fff" }}>AI</div>
          <span style={{ fontSize: "18px", fontWeight: 700, letterSpacing: "-0.5px" }}>Document Automation</span>
          {step > 1 && (
            <button className="btn-secondary" style={{ padding: "6px 12px", fontSize: "12.5px", marginLeft: "16px", display: "flex", alignItems: "center", gap: "6px" }} onClick={handleBack}>
              <ArrowLeftIcon /> Change Category
            </button>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "13px", fontWeight: 600 }}>{user.name}</span>
            <button className="btn-secondary" style={{ padding: "6px 12px", fontSize: "12px", borderColor: "rgba(220,38,38,0.2)", color: "var(--invalid-color)" }} onClick={handleLogout}>
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Viewport */}
      <main style={{ flex: 1, padding: "40px 32px", maxWidth: "1400px", width: "100%", margin: "0 auto", display: "flex", flexDirection: "column", gap: "32px" }}>
        
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
                Select an industry configuration to apply custom dynamic LLM structured extraction prompt rules and deterministic validators.
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

            {/* Session History Container */}
            {history.length > 0 && (
              <div className="glass-panel" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(15,23,42,0.05)", paddingBottom: "12px" }}>
                  <h3 style={{ fontSize: "15px", fontWeight: 700 }}>Processed Session Documents Logs</h3>
                  <div style={{ display: "flex", gap: "10px" }}>
                    <button className="btn-secondary" style={{ padding: "6px 12px", fontSize: "12px" }} onClick={() => setShowEmailModal(true)}>
                      Send via Email
                    </button>
                    <button className="btn-secondary" style={{ padding: "6px 12px", fontSize: "12px" }} onClick={handleDownloadAllProcessedData} disabled={isDownloadingAll}>
                      {isDownloadingAll ? <Spinner /> : "Download All Processed Data"}
                    </button>
                  </div>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {history.map((item) => (
                    <div key={item.id} className="validation-item" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <span style={{ fontSize: "12px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>{item.timestamp}</span>
                        <span style={{ fontWeight: 700 }}>{item.file_name}</span>
                        <span style={{ fontSize: "11px", textTransform: "capitalize", padding: "2px 6px", borderRadius: "4px", background: "rgba(15,23,42,0.05)" }}>{item.industry}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <span style={{ fontSize: "11px", fontWeight: 700, color: item.overall_status === "ready_for_review" ? "var(--valid-color)" : "var(--invalid-color)" }}>
                          {item.overall_status === "ready_for_review" ? "Complete ✓" : "Needs Review ⚠"}
                        </span>
                        <div style={{ display: "flex", gap: "6px" }}>
                          <button className="btn-secondary" style={{ padding: "4px 8px", fontSize: "12.5px" }} onClick={() => handleSelectHistoryItem(item)}>
                            View
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
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
            /* BEFORE PROCESSING: 50/50 Split */
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

              {/* Right side Extraction Controls */}
              <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                <div className="glass-panel" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <h3 style={{ fontSize: "16px", fontWeight: 600 }}>Processing Controls</h3>
                    <span style={{ fontSize: "11px", padding: "4px 8px", borderRadius: "4px", background: "var(--accent-glow)", color: "var(--accent-color)", fontWeight: 700, textTransform: "uppercase" }}>
                      {selectedIndustry}
                    </span>
                  </div>

                  {!isProcessing ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                      <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                        Document loaded. Click &quot;Process Document&quot; to perform structural extraction and validator checks.
                      </p>
                      <button className="btn-primary" style={{ width: "100%", justifyContent: "center" }} onClick={handleProcessDocument}>
                        Process Document
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "12px", padding: "10px 0" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <span style={{ color: "var(--accent-color)" }}><Spinner /></span>
                        <span style={{ fontWeight: 600, fontSize: "14px" }}>AI Fallback Chain Active</span>
                      </div>
                      <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                        {processingStatus}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            /* AFTER PROCESSING: Results Display and Corrections Form */
            <div style={{ maxWidth: "1200px", width: "100%", margin: "0 auto", display: "flex", flexDirection: "column", gap: "24px" }}>
              
              {/* Header card indicating status */}
              <div className="glass-panel" style={{ padding: "20px", display: "flex", justifyContent: "space-between", alignItems: "center", borderLeft: `4px solid ${result.overall_status === "ready_for_review" ? (result.ai_provider === "Groq" ? "#7d52e9" : result.ai_provider === "Mistral" ? "#2563eb" : "var(--valid-color)") : "var(--invalid-color)"}` }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <h3 style={{ fontSize: "17px", fontWeight: 700, color: "var(--text-primary)" }}>✓ Document Loaded & Validated</h3>
                    {result.overall_status === "ready_for_review" ? (
                      <div className="status-badge ready" style={{ 
                        display: "flex", 
                        alignItems: "center", 
                        gap: "4px", 
                        background: result.ai_provider === "Groq" ? "rgba(139, 92, 246, 0.1)" : result.ai_provider === "Mistral" ? "rgba(37, 99, 235, 0.1)" : "rgba(22, 163, 74, 0.1)", 
                        color: result.ai_provider === "Groq" ? "#7d52e9" : result.ai_provider === "Mistral" ? "#2563eb" : "#16a34a", 
                        border: `1px solid ${result.ai_provider === "Groq" ? "rgba(139, 92, 246, 0.2)" : result.ai_provider === "Mistral" ? "rgba(37, 99, 235, 0.2)" : "rgba(22, 163, 74, 0.2)"}`,
                        padding: "4px 8px", 
                        borderRadius: "4px", 
                        fontSize: "12px", 
                        fontWeight: 700 
                      }}>
                        <CheckIcon /> Ready for Review
                      </div>
                    ) : (
                      <div className="status-badge review" style={{ display: "flex", alignItems: "center", gap: "4px", background: "rgba(239, 68, 68, 0.1)", color: "#ef4444", padding: "4px 8px", borderRadius: "4px", fontSize: "12px", fontWeight: 700 }}>
                        <AlertIcon /> Needs Review
                      </div>
                    )}
                  </div>
                  <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "6px" }}>
                    Industry: <strong style={{ textTransform: "capitalize" }}>{selectedIndustry}</strong> • Document Type: <strong>{result.document_type.replace(/_/g, " ").toUpperCase()}</strong> • File: {file.name}
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
                    Process Another
                  </button>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", alignItems: "start" }}>
                
                {/* Left Column: Document Preview */}
                <div className="glass-panel" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
                  <h3 style={{ fontSize: "15px", fontWeight: 600, borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "12px" }}>
                    Document Preview
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
                      <div className="preview-placeholder" style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
                        <span style={{ fontSize: "13.5px" }}>No PDF source loaded. View extracted metadata logs below.</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Right Column: Dynamic Form Fields and Validation Rules */}
                <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                  <div className="glass-panel" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                    <h3 style={{ fontSize: "16px", fontWeight: 600, borderBottom: "1px solid rgba(15, 23, 42, 0.06)", paddingBottom: "12px", marginBottom: "4px" }}>
                      Data Validation & Completion
                    </h3>

                    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                      {getContextFields().map((f) => {
                        const key = f.name;
                        const val = result.extracted_data[key];
                        const isApplicable = result.extracted_fields?.[key]?.applicable !== false;
                        const isValid = result.validation[key]?.valid !== false;

                        let statusText = "✓ Valid";
                        let statusColor = "var(--valid-color)";
                        let showInput = false;

                        if (!isApplicable) {
                          statusText = "— Not Applicable";
                          statusColor = "#64748b";
                        } else if (val === null || val === undefined || String(val).trim() === "") {
                          statusText = f.required === 1 ? "⚠ Data Missing" : "✓ Empty (Optional)";
                          statusColor = f.required === 1 ? "#ea580c" : "var(--valid-color)";
                          if (f.required === 1) showInput = true;
                        } else if (!isValid) {
                          statusText = "⚠ Incorrect / Inconsistent";
                          statusColor = "var(--invalid-color)";
                          showInput = true;
                        }

                        return (
                          <div key={key} style={{ display: "flex", flexDirection: "column", borderBottom: "1px solid rgba(15,23,42,0.05)", paddingBottom: "16px" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: "10px" }}>
                              <div style={{ display: "flex", flexDirection: "column" }}>
                                <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                                  {f.label}
                                </span>
                                {val !== null && val !== "" && isApplicable && !showInput && (
                                  <span style={{ fontSize: "13.5px", color: "var(--text-secondary)", marginTop: "4px" }}>
                                    {String(val)}
                                  </span>
                                )}
                              </div>
                              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                <span style={{ fontSize: "12px", fontWeight: 700, color: statusColor, textTransform: "uppercase" }}>
                                  {statusText}
                                </span>
                                {isApplicable && !showInput && (
                                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                                    <button 
                                      style={{ background: "transparent", border: "none", cursor: "pointer", fontSize: "11px", color: "var(--accent-color)", fontWeight: 600, textDecoration: "underline", padding: 0 }}
                                      onClick={() => setEditingFieldId(f.id)}
                                    >
                                      Edit
                                    </button>
                                    <button 
                                      style={{ background: "transparent", border: "none", cursor: "pointer", fontSize: "11px", color: "var(--invalid-color)", display: "flex", alignItems: "center" }}
                                      onClick={() => handleToggleFieldActive(f.id)}
                                      title="Delete Field"
                                    >
                                      <TrashIcon />
                                    </button>
                                  </div>
                                )}
                              </div>
                            </div>

                            {(showInput || editingFieldId === f.id) && (
                              <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "10px", width: "100%", background: "rgba(15, 23, 42, 0.02)", padding: "12px", borderRadius: "8px", border: "1px solid rgba(15, 23, 42, 0.06)" }}>
                                <span style={{ fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
                                  Enter Correct Value:
                                </span>
                                
                                {f.field_type === "date" ? (
                                  <input 
                                    type="date" 
                                    className="form-input" 
                                    style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", outline: "none" }}
                                    value={manualInputs[key] || ""} 
                                    onChange={(e) => setManualInputs({ ...manualInputs, [key]: e.target.value })}
                                  />
                                ) : f.field_type === "select" ? (
                                  <select 
                                    className="form-input" 
                                    style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", outline: "none" }}
                                    value={manualInputs[key] || ""} 
                                    onChange={(e) => setManualInputs({ ...manualInputs, [key]: e.target.value })}
                                  >
                                    <option value="">-- Select Option --</option>
                                    {(JSON.parse(f.validation_rules || '{"options":[]}').options || []).map((o: string) => (
                                      <option key={o} value={o}>{o}</option>
                                    ))}
                                  </select>
                                ) : f.field_type === "textarea" ? (
                                  <textarea 
                                    className="form-input" 
                                    style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", outline: "none", height: "60px" }}
                                    value={manualInputs[key] || ""} 
                                    onChange={(e) => setManualInputs({ ...manualInputs, [key]: e.target.value })}
                                  />
                                ) : (
                                  <input 
                                    type="text" 
                                    className="form-input" 
                                    style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", outline: "none" }}
                                    value={manualInputs[key] || ""} 
                                    onChange={(e) => setManualInputs({ ...manualInputs, [key]: e.target.value })}
                                  />
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Inline "+ Add Custom Field" control */}
                    {showAddFieldForm ? (
                      <div className="glass-panel" style={{ padding: "16px", background: "rgba(15, 23, 42, 0.03)", border: "1px solid rgba(15, 23, 42, 0.1)", display: "flex", flexDirection: "column", gap: "12px", marginTop: "12px" }}>
                        <h4 style={{ fontSize: "13.5px", fontWeight: 700 }}>Add Custom Field</h4>
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-secondary)" }}>Field Label</label>
                          <input 
                            type="text"
                            className="form-input"
                            placeholder="e.g. Registration Status"
                            style={{ width: "100%", padding: "8px 12px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", outline: "none", fontSize: "13px" }}
                            value={newFieldLabel}
                            onChange={(e) => setNewFieldLabel(e.target.value)}
                          />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-secondary)" }}>Field Type</label>
                          <select 
                            className="form-input"
                            style={{ width: "100%", padding: "8px 12px", background: "#ffffff", border: "1px solid rgba(15, 23, 42, 0.15)", borderRadius: "8px", outline: "none", fontSize: "13px" }}
                            value={newFieldType}
                            onChange={(e) => setNewFieldType(e.target.value)}
                          >
                            <option value="text">Text</option>
                            <option value="date">Date</option>
                            <option value="number">Number</option>
                            <option value="email">Email</option>
                          </select>
                        </div>
                        <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                          <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}>
                            <input type="checkbox" checked={newFieldRequired} onChange={(e) => setNewFieldRequired(e.target.checked)} />
                            Required Field
                          </label>
                        </div>
                        <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end", marginTop: "4px" }}>
                          <button type="button" className="btn-secondary" style={{ padding: "6px 12px", fontSize: "12px" }} onClick={() => setShowAddFieldForm(false)}>
                            Cancel
                          </button>
                          <button type="button" className="btn-primary" style={{ padding: "6px 12px", fontSize: "12px" }} onClick={handleInlineCreateField}>
                            Save Field
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button 
                        className="btn-secondary"
                        style={{ 
                          marginTop: "12px", 
                          width: "100%", 
                          justifyContent: "center", 
                          borderStyle: "dashed", 
                          borderColor: "var(--accent-color)", 
                          color: "var(--accent-color)",
                          background: "var(--accent-glow)",
                          fontWeight: 600,
                          display: "flex",
                          alignItems: "center",
                          gap: "6px"
                        }}
                        onClick={() => {
                          setNewFieldLabel("");
                          setNewFieldType("text");
                          setNewFieldRequired(false);
                          setShowAddFieldForm(true);
                        }}
                      >
                        <span style={{ fontSize: "16px", fontWeight: "bold" }}>+</span> Add Field
                      </button>
                    )}

                    <button 
                      className="btn-primary" 
                      style={{ marginTop: "16px", width: "100%", justifyContent: "center" }}
                      onClick={handleSaveUpdateDocument}
                    >
                      Save / Update
                    </button>
                  </div>

                  {/* Report Download controls */}
                  <div className="glass-panel" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-muted)" }}>Status Check:</span>
                      <span style={{ fontSize: "16px", fontWeight: 800, color: result.overall_status === "ready_for_review" ? "var(--valid-color)" : "var(--invalid-color)" }}>
                        {result.overall_status === "ready_for_review" ? "Complete ✓" : "Needs Review ⚠"}
                      </span>
                    </div>
                    <button
                      className="btn-primary"
                      style={{ width: "100%", justifyContent: "center" }}
                      disabled={result.overall_status !== "ready_for_review" || isDownloading}
                      onClick={handleDownloadUpdatedPdf}
                    >
                      {isDownloading ? <Spinner /> : "Download Updated PDF Copy"}
                    </button>
                  </div>
                </div>

              </div>
            </div>
          )
        )}
      </main>

      {/* EMAIL RECIPIENT MODAL */}
      {showEmailModal && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", background: "rgba(15,23,42,0.4)", display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000 }}>
          <div className="glass-panel" style={{ padding: "32px", maxWidth: "400px", width: "100%", margin: "20px", display: "flex", flexDirection: "column", gap: "20px" }}>
            <div>
              <h3 style={{ fontSize: "18px", fontWeight: 800 }}>Send processed report via email</h3>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "4px" }}>Generate compiled report and email it securely to the recipient.</p>
            </div>
            <form onSubmit={handleSendEmail} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <label style={{ fontSize: "12px", fontWeight: 700 }}>Recipient Email Address</label>
                <input 
                  type="email" 
                  required 
                  placeholder="e.g. manager@company.com"
                  style={{ width: "100%", padding: "10px", background: "#ffffff", border: "1px solid var(--panel-border)", borderRadius: "8px", outline: "none" }}
                  value={recipientEmail}
                  onChange={(e) => setRecipientEmail(e.target.value)}
                />
              </div>
              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
                <button type="button" className="btn-secondary" style={{ padding: "8px 16px" }} onClick={() => setShowEmailModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" style={{ padding: "8px 16px" }} disabled={isSendingEmail}>
                  {isSendingEmail ? <Spinner /> : "Send"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Footer Branding */}
      <footer style={{ borderTop: "1px solid var(--panel-border)", padding: "20px 32px", textAlign: "center", marginTop: "auto", background: "rgba(255, 255, 255, 0.4)" }}>
        <p style={{ fontSize: "12.5px", color: "#475569", fontWeight: 500 }}>
          © {new Date().getFullYear()} AI Document Automation MVP. All Rights Reserved.
        </p>
      </footer>
    </div>
  );
}
