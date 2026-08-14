# backend/services/email.py

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.encoders import encode_base64
from fastapi import HTTPException, status

logger = logging.getLogger("email")
logger.setLevel(logging.INFO)

def send_combined_report_email(recipient_email: str, pdf_bytes: bytes) -> bool:
    """
    Sends the generated combined PDF report to the specified email recipient.
    Reads credentials and host details from environment variables.
    """
    # 1. Load configuration from environment variables
    host = os.environ.get("EMAIL_HOST")
    port_str = os.environ.get("EMAIL_PORT")
    username = os.environ.get("EMAIL_USERNAME")
    password = os.environ.get("EMAIL_PASSWORD")
    sender_email = os.environ.get("EMAIL_FROM") or username
    
    # 2. Check if configuration exists
    if not all([host, port_str, username, password, sender_email]):
        logger.warning("[Email] SMTP configuration variables are missing or incomplete. Running in Mock/Debug mode.")
        import datetime
        os.makedirs("sent_emails", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = f"sent_emails/email_to_{recipient_email}_{timestamp}.pdf"
        txt_path = f"sent_emails/email_to_{recipient_email}_{timestamp}.txt"
        
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
            
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"To: {recipient_email}\n")
            f.write("Subject: AI Document Automation - Processed Data\n")
            f.write(f"Attachment Saved At: {pdf_path}\n\n")
            f.write(
                "Hello,\n\n"
                "Your processed document data is available.\n\n"
                "Please find the attached PDF report containing all your processed document summaries.\n\n"
                "Regards,\n"
                "AI Document Automation\n"
            )
            
        logger.info(f"[Email] Mock mode: Saved PDF attachment to {pdf_path}")
        return True
        
    try:
        port = int(port_str)
    except ValueError:
        logger.error(f"[Email] Invalid port string configuration: {port_str}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid SMTP server port configured."
        )
        
    logger.info(f"[Email] Preparing email dispatch to: {recipient_email}")
    
    # 3. Construct MIMEMultipart message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = "AI Document Automation - Processed Data"
    
    body = (
        "Hello,\n\n"
        "Your processed document data is available.\n\n"
        "Please find the attached PDF report containing all your processed document summaries.\n\n"
        "Regards,\n"
        "AI Document Automation"
    )
    msg.attach(MIMEText(body, 'plain'))
    
    # 4. Attach PDF bytes
    part = MIMEBase('application', 'pdf')
    part.set_payload(pdf_bytes)
    encode_base64(part)
    part.add_header(
        'Content-Disposition',
        'attachment; filename="processed_documents_report.pdf"'
    )
    msg.attach(part)
    
    # 5. Connect and send
    try:
        # Determine protocol type based on port (e.g. SSL vs STARTTLS)
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            server.ehlo()
            if server.has_extn('STARTTLS'):
                server.starttls()
                server.ehlo()
                
        # Authenticate
        server.login(username, password)
        # Send
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        logger.info("[Email] Message sent successfully")
        return True
        
    except Exception as e:
        err_msg = str(e)
        logger.error(f"[Email] SMTP dispatch connection failed: {err_msg}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SMTP server connection failed: {err_msg}"
        )
