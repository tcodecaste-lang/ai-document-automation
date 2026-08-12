# backend/services/pdf_generator.py

import io
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_validated_summary_pdf(
    original_filename: str,
    industry: str,
    document_type: str,
    extracted_data: dict,
    validation: dict,
    overall_status: str,
    original_data: dict
) -> bytes:
    """
    Generates a beautifully formatted PDF report summarizing the validated results.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )
    
    styles = getSampleStyleSheet()
    
    # Custom, premium styling (slate light mode theme)
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=20
    )
    
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=10,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )
    
    body_bold = ParagraphStyle(
        'BodyTextBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    footer_style = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontSize=8,
        leading=12,
        textColor=colors.HexColor('#94a3b8'),
        alignment=1 # Center aligned
    )
    
    story = []
    
    # Page Header decoration
    story.append(Paragraph("VALIDATED DOCUMENT COPY", title_style))
    story.append(Paragraph("AI-assisted extraction and deterministic validation summary report.", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Metadata block
    story.append(Paragraph("Document Details", section_title))
    
    status_text = "Complete ✓" if overall_status == "ready_for_review" else "Needs Review ⚠"
    status_color = "#16a34a" if overall_status == "ready_for_review" else "#dc2626"
    
    # Human-readable industry mapping
    ind_map = {
        "insurance": "Insurance Claims",
        "finance": "Finance & Expenses",
        "healthcare": "Healthcare Registrations"
    }
    ind_name = ind_map.get(industry.lower(), industry.capitalize())
    doc_name = document_type.replace('_', ' ').replace('-', ' ').title()
    
    meta_rows = [
        [Paragraph("Original File Name", body_bold), Paragraph(original_filename, body_style)],
        [Paragraph("Target Industry", body_bold), Paragraph(ind_name, body_style)],
        [Paragraph("Document Type", body_bold), Paragraph(doc_name, body_style)],
        [Paragraph("Validation Status", body_bold), Paragraph(f"<font color='{status_color}'><b>{status_text}</b></font>", body_bold)],
        [Paragraph("Completion Timestamp", body_bold), Paragraph(datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), body_style)]
    ]
    
    meta_table = Table(meta_rows, colWidths=[150, 370])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#f1f5f9')),
    ]))
    
    story.append(meta_table)
    story.append(Spacer(1, 20))
    
    # Fields table block
    story.append(Paragraph("Extracted & Validated Fields Data", section_title))
    
    fields_header = [
        Paragraph("<b>Field Name</b>", body_bold),
        Paragraph("<b>Value</b>", body_bold),
        Paragraph("<b>Status</b>", body_bold)
    ]
    
    table_data = [fields_header]
    
    for field_name in extracted_data.keys():
        val = extracted_data[field_name]
        val_str = str(val) if val is not None else "[Missing]"
        
        # Calculate dynamic status
        val_is_empty = val is None or str(val).strip() == ""
        
        # Check validation status object
        field_valid = validation.get(field_name, {}).get("valid", True)
        field_msg = validation.get(field_name, {}).get("message", "")
        
        # Check if applicable
        is_not_applicable = "not applicable" in field_msg.lower()
        
        if is_not_applicable:
            status = "Not Applicable"
            status_color = "#64748b" # gray
        elif val_is_empty:
            status = "Missing"
            status_color = "#dc2626" # red
        elif not field_valid:
            status = "Incorrect"
            status_color = "#b91c1c" # dark red
        else:
            # Check if it was added or corrected or original
            orig_val = original_data.get(field_name)
            orig_is_empty = orig_val is None or str(orig_val).strip() == ""
            
            if orig_is_empty:
                status = "Added"
                status_color = "#2563eb" # blue
            elif str(val) != str(orig_val):
                status = "Corrected"
                status_color = "#ea580c" # orange
            else:
                status = "Valid"
                status_color = "#16a34a" # green
        
        status_html = f"<font color='{status_color}'><b>{status}</b></font>"
        
        # Make field name display nicely
        if field_name == "accident_date":
            # Adjust label dynamically based on policy type in the final data
            current_policy_type = extracted_data.get("policy_type")
            is_accident_pol = current_policy_type in ["Travel Insurance", "Personal Accident Insurance", "Motor/Auto Insurance", "Health Insurance"]
            display_name = "Accident Date" if is_accident_pol else "Incident Date"
        else:
            display_name = field_name.replace('_', ' ').title()
            
        table_data.append([
            Paragraph(display_name, body_style),
            Paragraph(val_str, body_style),
            Paragraph(status_html, body_style)
        ])
        
    fields_table = Table(table_data, colWidths=[150, 240, 130])
    fields_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(fields_table)
    story.append(Spacer(1, 35))
    
    # Footer notice
    story.append(Paragraph("This is an automatically compiled report. The original uploaded copy remains unmodified.<br/>Generated by AI Document Automation MVP Service.", footer_style))
    
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def generate_combined_summary_report_pdf(items: list) -> bytes:
    """
    Generates a beautifully compiled PDF report summarizing all processed documents in the session.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )
    
    styles = getSampleStyleSheet()
    
    # Custom, premium styling (slate light mode theme)
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=20
    )
    
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=10,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )
    
    body_bold = ParagraphStyle(
        'BodyTextBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    footer_style = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontSize=8,
        leading=12,
        textColor=colors.HexColor('#94a3b8'),
        alignment=1 # Center aligned
    )
    
    story = []
    
    # 1. Title & Header
    story.append(Paragraph("PROCESSED DOCUMENTS REPORT", title_style))
    story.append(Paragraph(f"AI-assisted batch processed records export • Generated on {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", subtitle_style))
    story.append(Spacer(1, 10))
    
    # 2. Summary Statistics
    story.append(Paragraph("Report Summary", section_title))
    
    total_docs = len(items)
    success_count = sum(1 for item in items if item.overall_status == "ready_for_review")
    failed_count = total_docs - success_count
    
    summary_rows = [
        [Paragraph("Total Documents", body_bold), Paragraph(str(total_docs), body_style)],
        [Paragraph("Successfully Processed (Ready for Review)", body_bold), Paragraph(f"<font color='#16a34a'><b>{success_count}</b></font>", body_style)],
        [Paragraph("Failed (Needs Review)", body_bold), Paragraph(f"<font color='#dc2626'><b>{failed_count}</b></font>", body_style)],
    ]
    
    summary_table = Table(summary_rows, colWidths=[250, 270])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # 3. Documents Iteration
    story.append(Paragraph("Documents Detail", section_title))
    
    for idx, item in enumerate(items):
        file_name = item.file_name
        industry = item.industry
        doc_type = item.document_type
        extracted_data = item.extracted_data
        validation = item.validation
        overall_status = item.overall_status
        original_data = item.original_data
        
        # Divider between items
        if idx > 0:
            divider = Table([[""]], colWidths=[520], rowHeights=[1])
            divider.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#cbd5e1')),
                ('TOPPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(Spacer(1, 15))
            story.append(divider)
            story.append(Spacer(1, 15))
            
        status_text = "Complete ✓" if overall_status == "ready_for_review" else "Needs Review ⚠"
        status_color = "#16a34a" if overall_status == "ready_for_review" else "#dc2626"
        
        ind_map = {
            "insurance": "Insurance Claims",
            "finance": "Finance & Expenses",
            "healthcare": "Healthcare Registrations"
        }
        ind_name = ind_map.get(industry.lower(), industry.capitalize())
        doc_name = doc_type.replace('_', ' ').replace('-', ' ').title()
        
        # Document Sub-card Title
        story.append(Paragraph(f"<b>Document #{idx + 1}: {file_name}</b>", body_bold))
        story.append(Spacer(1, 4))
        
        meta_rows = [
            [Paragraph("Industry", body_bold), Paragraph(ind_name, body_style)],
            [Paragraph("Document Type", body_bold), Paragraph(doc_name, body_style)],
            [Paragraph("Validation Status", body_bold), Paragraph(f"<font color='{status_color}'><b>{status_text}</b></font>", body_bold)]
        ]
        doc_meta_table = Table(meta_rows, colWidths=[150, 370])
        doc_meta_table.setStyle(TableStyle([
            ('PADDING', (0,0), (-1,-1), 4),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(doc_meta_table)
        story.append(Spacer(1, 8))
        
        # Document Fields table
        fields_header = [
            Paragraph("<b>Field Name</b>", body_bold),
            Paragraph("<b>Value</b>", body_bold),
            Paragraph("<b>Status</b>", body_bold)
        ]
        table_data = [fields_header]
        
        for field_name in extracted_data.keys():
            val = extracted_data[field_name]
            val_str = str(val) if val is not None else "[Missing]"
            
            # Calculate dynamic status
            val_is_empty = val is None or str(val).strip() == ""
            field_val_obj = validation.get(field_name)
            field_valid = field_val_obj.valid if field_val_obj else True
            field_msg = field_val_obj.message if field_val_obj else ""
            
            is_not_applicable = "not applicable" in field_msg.lower()
            
            if is_not_applicable:
                status = "Not Applicable"
                status_color = "#64748b"
            elif val_is_empty:
                status = "Missing"
                status_color = "#dc2626"
            elif not field_valid:
                status = "Incorrect"
                status_color = "#b91c1c"
            else:
                orig_val = original_data.get(field_name)
                orig_is_empty = orig_val is None or str(orig_val).strip() == ""
                
                if orig_is_empty:
                    status = "Added"
                    status_color = "#2563eb"
                elif str(val) != str(orig_val):
                    status = "Corrected"
                    status_color = "#ea580c"
                else:
                    status = "Valid"
                    status_color = "#16a34a"
            
            status_html = f"<font color='{status_color}'><b>{status}</b></font>"
            
            if field_name == "accident_date":
                current_policy_type = extracted_data.get("policy_type")
                is_accident_pol = current_policy_type in ["Travel Insurance", "Personal Accident Insurance", "Motor/Auto Insurance", "Health Insurance"]
                display_name = "Accident Date" if is_accident_pol else "Incident Date"
            else:
                display_name = field_name.replace('_', ' ').title()
                
            table_data.append([
                Paragraph(display_name, body_style),
                Paragraph(val_str, body_style),
                Paragraph(status_html, body_style)
            ])
            
        fields_table = Table(table_data, colWidths=[150, 240, 130])
        fields_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(fields_table)
        story.append(Spacer(1, 10))
        
    story.append(Spacer(1, 20))
    story.append(Paragraph("This is an automatically compiled batch report export.<br/>Generated by AI Document Automation MVP Service.", footer_style))
    
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
