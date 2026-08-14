# backend/services/database.py

import sqlite3
import os
import json
import logging
from contextlib import contextmanager

logger = logging.getLogger("database")
logger.setLevel(logging.INFO)

# Store the sqlite DB in the backend directory
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database.db")

@contextmanager
def get_db():
    """Connection helper that yields a Row-mapped connection context."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def seed_fields(conn):
    """Seed default dynamic fields for standard document types."""
    logger.info("[DB] Seeding default dynamic fields...")
    
    # Structure of tuples:
    # (name, label, industry, document_type, field_type, required, active, display_order, validation_rules)
    fields_data = [
        # Legacy static fields for test compatibility
        # Insurance claim/policy
        ("customer_name", "Customer Name", "insurance", "insurance_policy_or_claim", "text", 1, 1, 1, "{}"),
        ("policy_number", "Policy Number", "insurance", "insurance_policy_or_claim", "identifier", 1, 1, 2, "{}"),
        ("policy_type", "Policy Type", "insurance", "insurance_policy_or_claim", "select", 1, 1, 3, json.dumps({"options": ["Health Insurance", "Life Insurance", "Motor/Auto Insurance", "Home Insurance", "Travel Insurance", "Personal Accident Insurance"]})),
        ("policy_start_date", "Policy Start Date", "insurance", "insurance_policy_or_claim", "date", 1, 1, 4, "{}"),
        ("policy_end_date", "Policy End Date", "insurance", "insurance_policy_or_claim", "date", 1, 1, 5, "{}"),
        ("coverage_amount", "Coverage Amount", "insurance", "insurance_policy_or_claim", "currency", 1, 1, 6, "{}"),
        ("accident_date", "Accident Date", "insurance", "insurance_policy_or_claim", "date", 1, 1, 7, "{}"),
        ("claim_type", "Claim Type", "insurance", "insurance_policy_or_claim", "text", 1, 1, 8, "{}"),
        
        # Finance claim
        ("employee_name", "Employee Name", "finance", "expense_claim", "text", 1, 1, 1, "{}"),
        ("merchant_name", "Merchant Name", "finance", "expense_claim", "text", 1, 1, 2, "{}"),
        ("amount", "Amount", "finance", "expense_claim", "currency", 1, 1, 3, "{}"),
        ("date", "Date", "finance", "expense_claim", "date", 1, 1, 4, "{}"),
        ("category", "Category", "finance", "expense_claim", "select", 1, 1, 5, json.dumps({"options": ["Travel", "Meals", "Office Supplies", "Software", "Others"]})),

        # Insurance - Vehicle Insurance Claim
        ("customer_name", "Customer Name", "insurance", "vehicle_insurance_claim", "text", 1, 1, 1, "{}"),
        ("policy_number", "Policy Number", "insurance", "vehicle_insurance_claim", "identifier", 1, 1, 2, "{}"),
        ("accident_date", "Accident Date", "insurance", "vehicle_insurance_claim", "date", 1, 1, 3, "{}"),
        ("claim_type", "Claim Type", "insurance", "vehicle_insurance_claim", "text", 1, 1, 4, "{}"),
        ("incident_location", "Incident Location", "insurance", "vehicle_insurance_claim", "text", 0, 1, 5, "{}"),
        
        # Insurance - Health Insurance Claim
        ("patient_name", "Patient Name", "insurance", "health_insurance_claim", "text", 1, 1, 1, "{}"),
        ("policy_number", "Policy Number", "insurance", "health_insurance_claim", "identifier", 1, 1, 2, "{}"),
        ("hospital_name", "Hospital Name", "insurance", "health_insurance_claim", "text", 1, 1, 3, "{}"),
        ("treatment_date", "Treatment Date", "insurance", "health_insurance_claim", "date", 1, 1, 4, "{}"),
        ("claim_amount", "Claim Amount", "insurance", "health_insurance_claim", "currency", 1, 1, 5, "{}"),
        
        # Finance - Expense Receipt
        ("merchant_name", "Merchant/Vendor Name", "finance", "expense_receipt", "text", 1, 1, 1, "{}"),
        ("expense_date", "Expense Date", "finance", "expense_receipt", "date", 1, 1, 2, "{}"),
        ("amount", "Amount", "finance", "expense_receipt", "currency", 1, 1, 3, "{}"),
        ("tax", "Tax", "finance", "expense_receipt", "currency", 0, 1, 4, "{}"),
        ("category", "Category", "finance", "expense_receipt", "select", 1, 1, 5, json.dumps({"options": ["Travel", "Meals", "Office Supplies", "Software", "Others"]})),
        
        # Finance - Hotel Expense
        ("hotel_name", "Hotel Name", "finance", "hotel_expense", "text", 1, 1, 1, "{}"),
        ("guest_name", "Guest Name", "finance", "hotel_expense", "text", 1, 1, 2, "{}"),
        ("check_in_date", "Check-in Date", "finance", "hotel_expense", "date", 1, 1, 3, "{}"),
        ("check_out_date", "Check-out Date", "finance", "hotel_expense", "date", 1, 1, 4, "{}"),
        ("amount", "Amount", "finance", "hotel_expense", "currency", 1, 1, 5, "{}"),
        
        # Healthcare - Patient Registration Form
        ("patient_name", "Patient Name", "healthcare", "patient_registration", "text", 1, 1, 1, "{}"),
        ("date_of_birth", "Date of Birth", "healthcare", "patient_registration", "date", 1, 1, 2, "{}"),
        ("appointment_type", "Appointment Type", "healthcare", "patient_registration", "text", 1, 1, 3, "{}"),
        ("appointment_date", "Appointment Date", "healthcare", "patient_registration", "date", 1, 1, 4, "{}"),
        ("hospital_name", "Hospital / Healthcare Provider Name", "healthcare", "patient_registration", "text", 1, 1, 5, "{}"),
        
        # Healthcare - Medical Bill
        ("patient_name", "Patient Name", "healthcare", "medical_bill", "text", 1, 1, 1, "{}"),
        ("hospital_name", "Hospital Name", "healthcare", "medical_bill", "text", 1, 1, 2, "{}"),
        ("bill_number", "Bill Number", "healthcare", "medical_bill", "identifier", 1, 1, 3, "{}"),
        ("treatment_date", "Treatment Date", "healthcare", "medical_bill", "date", 1, 1, 4, "{}"),
        ("total_amount", "Total Amount", "healthcare", "medical_bill", "currency", 1, 1, 5, "{}")
    ]
    
    conn.executemany("""
    INSERT INTO fields (name, label, industry, document_type, field_type, required, active, display_order, validation_rules)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, fields_data)

def init_db():
    """Initializes tables and configures default seeds."""
    logger.info("[DB] Initializing database tables...")
    
    with get_db() as conn:
        # 1. Users Table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 2. Fields Table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            label TEXT NOT NULL,
            industry TEXT NOT NULL,
            document_type TEXT NOT NULL,
            field_type TEXT NOT NULL,
            required BOOLEAN NOT NULL DEFAULT 0,
            active BOOLEAN NOT NULL DEFAULT 1,
            display_order INTEGER NOT NULL DEFAULT 0,
            validation_rules TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Safely migrate fields schema to support multi-tenant user ownership
        try:
            conn.execute("ALTER TABLE fields ADD COLUMN user_id INTEGER DEFAULT NULL;")
            conn.commit()
        except Exception:
            pass
        
        # 3. Documents Table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            industry TEXT NOT NULL,
            document_type TEXT NOT NULL,
            overall_status TEXT NOT NULL,
            extracted_data TEXT NOT NULL,
            extracted_fields TEXT,
            validation TEXT NOT NULL,
            original_data TEXT NOT NULL,
            ai_provider TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)
        
        # Check if fields table is empty
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM fields")
        if cursor.fetchone()[0] == 0:
            seed_fields(conn)
            
        # Check if there is an admin user. If not, create default admin!
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        if cursor.fetchone()[0] == 0:
            # We import here dynamically to avoid circular references
            from backend.services.auth import hash_password
            conn.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                ("System Admin", "admin@docauto.com", hash_password("AdminPassword123"), "admin")
            )
            logger.info("[DB] Seeded default system admin user.")
            
        conn.commit()
    logger.info("[DB] Database initialization complete.")
