# backend/scripts/generate_demos.py

import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def draw_pdf(filepath: str, title: str, fields: dict, description: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    c = canvas.Canvas(filepath, pagesize=letter)
    
    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, 750, title)
    
    # Divider line
    c.setLineWidth(1)
    c.line(50, 735, 550, 735)
    
    # Fields
    c.setFont("Helvetica", 12)
    y_pos = 700
    for key, val in fields.items():
        # Format field key for user presentation
        formatted_key = key.replace("_", " ").title()
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, f"{formatted_key}:")
        c.setFont("Helvetica", 12)
        c.drawString(180, y_pos, str(val))
        y_pos -= 30
        
    y_pos -= 10
    c.setLineWidth(0.5)
    c.line(50, y_pos, 550, y_pos)
    y_pos -= 30
    
    # Description
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_pos, "Description / Notes:")
    y_pos -= 20
    c.setFont("Helvetica", 10)
    
    # Simple line wrapper for description text
    words = description.split()
    line = []
    for word in words:
        line.append(word)
        if len(" ".join(line)) > 80:
            c.drawString(50, y_pos, " ".join(line[:-1]))
            line = [word]
            y_pos -= 15
    if line:
        c.drawString(50, y_pos, " ".join(line))
        
    c.save()
    print(f"Generated: {filepath}")

def generate_all():
    # Define outputs
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo-pdfs"))
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public", "demo-pdfs"))
    
    demos = [
        {
            "filename": "insurance_demo.pdf",
            "title": "Insurance Claim Form",
            "fields": {
                "customer_name": "John Smith",
                "policy_number": "POL12345",
                "policy_type": "Health Insurance",
                "policy_start_date": "2026-01-01",
                "policy_end_date": "2026-12-31",
                "coverage_amount": "$5000",
                "accident_date": "2026-08-10",
                "claim_type": "Car Accident"
            },
            "description": "The claimant was driving along Main Street when another vehicle collided with the rear of their car. There was minor damage to the bumper."
        },
        {
            "filename": "finance_demo.pdf",
            "title": "Expense Claim Form",
            "fields": {
                "employee_name": "Sarah Jones",
                "merchant_name": "Boston Transit Co",
                "amount": "250.00",
                "date": "2026-08-08",
                "category": "Travel"
            },
            "description": "Train ticket and taxi fares for attending the client meeting in Boston on August 8th."
        },
        {
            "filename": "healthcare_demo.pdf",
            "title": "Patient Registration Form",
            "fields": {
                "patient_name": "David Brown",
                "date_of_birth": "1980-03-12",
                "hospital_name": "General Health Clinic",
                "appointment_type": "General Consultation",
                "appointment_date": "2026-08-15"
            },
            "description": "Routine check-up and renewal of standard prescription."
        },
        {
            "filename": "insurance_negative_demo.pdf",
            "title": "Insurance Claim Form",
            "fields": {
                "customer_name": "John Smith",
                "policy_number": "POL12345",
                "policy_type": "Health Insurance",
                "policy_start_date": "2026-01-01",
                "policy_end_date": "2026-12-31",
                "coverage_amount": "$5000",
                "claim_type": "Car Accident"
                # Missing accident_date
            },
            "description": "The claimant reported a collision on the highway. Note: Accident date was not specified by the claimant."
        }
    ]
    
    for demo in demos:
        # Save to backend folder
        draw_pdf(os.path.join(backend_dir, demo["filename"]), demo["title"], demo["fields"], demo["description"])
        # Save to frontend folder
        draw_pdf(os.path.join(frontend_dir, demo["filename"]), demo["title"], demo["fields"], demo["description"])

if __name__ == "__main__":
    generate_all()
