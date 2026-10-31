import os
import sys
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    Preformatted,
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        if self._pageNumber == 1:
            return  # Suppress footer on cover page
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748b"))
        # Header
        self.drawString(54, letter[1] - 36, "VaaniDesk Banking Assistant — API Documentation")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)
        # Footer
        self.line(54, 45, letter[0] - 54, 45)
        self.drawString(54, 32, "Confidential — Azentio Banking Architecture Team (Member 1)")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 32, page_text)
        self.restoreState()


def build_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=26,
        leading=32,
        textColor=colors.HexColor("#0f172a"),
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#2563eb"),
        alignment=0,
    )
    meta_style = ParagraphStyle(
        "CoverMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#475569"),
    )
    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True,
    )
    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1e40af"),
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True,
    )
    h3_style = ParagraphStyle(
        "Heading3_Custom",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6,
    )
    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f8fafc"),
        borderColor=colors.HexColor("#e2e8f0"),
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=6,
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#1e293b"),
    )
    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#ffffff"),
    )

    story = []

    # ------------------ COVER PAGE ------------------
    story.append(Spacer(1, 40))
    story.append(Paragraph("Azentio Banking System", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("VaaniDesk Banking Assistant", title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Complete Backend API Specification & Frontend Integration Guide", subtitle_style))
    story.append(Spacer(1, 25))

    meta_text = """
    <b>Document Version:</b> 1.0.0<br/>
    <b>Owner / Author:</b> Member 1 — Senior Backend Engineer<br/>
    <b>Target Audience:</b> Member 2 (AI Orchestration), Member 3 (React Frontend)<br/>
    <b>Environment Base URL:</b> http://127.0.0.1:8000<br/>
    <b>API Canonical Prefix:</b> /api/v1<br/>
    <b>OpenAPI Interactive Docs:</b> http://127.0.0.1:8000/docs<br/>
    <b>Date of Issue:</b> October 31, 2026<br/>
    <b>Classification:</b> Internal Engineering Documentation
    """
    story.append(Paragraph(meta_text, meta_style))
    story.append(Spacer(1, 35))

    # Decorative Box
    box_data = [[
        Paragraph(
            "<b>Notice:</b> This document defines the canonical HTTP contract for the VaaniDesk AI-powered voice "
            "banking customer assistant. All voice/chat sessions, customer verification procedures, mock Loan "
            "Origination System (LOS), Loan Management System (LMS), and Core Banking System (CBS) APIs must "
            "conform to the input and output schemas detailed herein.",
            body_style
        )
    ]]
    t_box = Table(box_data, colWidths=[500])
    t_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#93c5fd")),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(t_box)
    story.append(PageBreak())

    # ------------------ TABLE OF CONTENTS ------------------
    story.append(Paragraph("Table of Contents", h1_style))
    story.append(Spacer(1, 8))

    toc_items = [
        "1. Project Overview & System Architecture",
        "2. Environment & Server Setup Instructions",
        "3. Complete API Endpoint Reference (Detailed Input & Output)",
        "   3.1 System Health Probes",
        "   3.2 Customer Voice & Chat Session Management",
        "   3.3 Mock Banking Services (LOS, LMS, CBS)",
        "   3.4 Customer Service Management (CSM Tickets)",
        "   3.5 Operations Dashboard APIs",
        "   3.6 Preserved Customer Web Portal Endpoints",
        "4. API Endpoint Summary Matrix",
        "5. Frontend Developer Integration Guide",
        "6. End-to-End User Journeys & Wireflows",
        "7. Standardized Error Handling & Fault Envelope",
        "8. Data Protection & Security Safeguards",
        "9. Frontend Team Handoff Protocol",
    ]
    for item in toc_items:
        story.append(Paragraph(f"• {item}", body_style))
    story.append(Spacer(1, 15))

    # ------------------ 1. PROJECT OVERVIEW ------------------
    story.append(Paragraph("1. Project Overview & System Architecture", h1_style))
    story.append(Paragraph(
        "VaaniDesk is an enterprise-grade AI-powered voice and digital assistant for retail banking. "
        "It automates customer inquiries regarding loan statuses, monthly EMI repayment schedules, "
        "account balances, transaction disputes, and human escalations. Built with an asynchronous "
        "FastAPI backend and dual-driver SQLite/PostgreSQL architecture, it operates with zero external "
        "database dependencies in local development while maintaining seamless cloud readiness.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Architectural Separation:</b><br/>"
        "• <b>Member 1 (Backend):</b> Core FastAPI engine, SQLite database schema, synthetic data seeding, "
        "server-controlled session state, customer identity verification, mock banking APIs, idempotent ticket creation, "
        "audit logging, and the AI adapter.<br/>"
        "• <b>Member 2 (AI Orchestration):</b> Speech-to-Text, intent classification, multi-turn state machine, "
        "and Text-to-Speech generation via <code>app.integrations.ai_pipeline</code>.<br/>"
        "• <b>Member 3 (Frontend):</b> React/Vite user interface for voice interactions, customer portals, and operations.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # ------------------ 2. ENVIRONMENT SETUP ------------------
    story.append(Paragraph("2. Environment & Server Setup Instructions", h1_style))
    story.append(Paragraph(
        "The backend is self-contained. The local SQLite database is created automatically upon first run.",
        body_style
    ))
    setup_code = (
        "# 1. Activate Virtual Environment\n"
        "cd azentio/server\n"
        ".venv\\Scripts\\activate          # Windows\n"
        "source .venv/bin/activate       # Linux/macOS\n\n"
        "# 2. Populate Repeatable Synthetic Banking Data\n"
        "python -m app.db.seed\n\n"
        "# 3. Run FastAPI Application\n"
        "python run.py                   # Starts server on http://127.0.0.1:8000\n"
        "# Or via uvicorn directly:\n"
        "uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
    )
    story.append(Preformatted(setup_code, code_style))
    story.append(Spacer(1, 10))

    # ------------------ 3. COMPLETE API ENDPOINTS ------------------
    story.append(Paragraph("3. Complete API Endpoint Reference", h1_style))

    # 3.1 Health
    story.append(Paragraph("3.1 System Health Probes", h2_style))
    story.append(Paragraph("<b>GET /health</b> (Canonical Infrastructure Health Probe)", h3_style))
    story.append(Paragraph("• <b>Authentication:</b> Public. No headers or payload required.<br/>"
                           "• <b>Success Response (200 OK):</b>", body_style))
    story.append(Preformatted('{\n  "status": "ok",\n  "service": "vaanidesk-backend"\n}', code_style))

    # 3.2 Sessions
    story.append(Paragraph("3.2 Customer Voice & Chat Session Management", h2_style))
    
    # POST /sessions
    story.append(Paragraph("<b>POST /api/v1/sessions</b> (Initialize Assistant Session)", h3_style))
    story.append(Paragraph(
        "Creates a server-side session and generates a corresponding call audit record. "
        "The session starts in <code>UNVERIFIED</code> state.",
        body_style
    ))
    story.append(Paragraph("<b>INPUT (Optional Body):</b>", body_style))
    story.append(Preformatted('{\n  "customer_id": "C1023",\n  "channel": "voice"\n}', code_style))
    story.append(Paragraph("<b>OUTPUT (201 Created):</b>", body_style))
    story.append(Preformatted('{\n  "session_id": "SES-3f92a10b",\n  "call_id": "CALL-7e81b29c",\n  "customer_id": "C1023",\n  "current_state": "UNVERIFIED",\n  "verified": false,\n  "failed_verification_attempts": 0,\n  "locked": false,\n  "created_at": "2026-10-31T12:00:00Z"\n}', code_style))

    # POST /sessions/{id}/verify
    story.append(Paragraph("<b>POST /api/v1/sessions/{session_id}/verify</b> (Customer Verification)", h3_style))
    story.append(Paragraph(
        "Verifies customer date of birth (DOB) against the synthetic banking database. "
        "Enforces server-side tracking of failed attempts. Exactly three (3) failed attempts lock the session permanently.",
        body_style
    ))
    story.append(Paragraph("<b>INPUT:</b>", body_style))
    story.append(Preformatted('{\n  "customer_id": "C1023",\n  "dob": "1995-03-12"\n}', code_style))
    story.append(Paragraph("<b>OUTPUT (200 OK - Successful Verification):</b>", body_style))
    story.append(Preformatted('{\n  "session_id": "SES-3f92a10b",\n  "verified": true,\n  "customer_id": "C1023",\n  "customer_name": "Alex Mercer",\n  "current_state": "VERIFIED",\n  "message": "Customer identity verified successfully."\n}', code_style))
    story.append(Paragraph("<b>OUTPUT (401 Unauthorized - Mismatch):</b>", body_style))
    story.append(Preformatted('{\n  "error": {\n    "code": "AUTH_MISMATCH",\n    "message": "Date of birth does not match customer record. 2 attempts remaining.",\n    "retryable": true\n  }\n}', code_style))
    story.append(Paragraph("<b>OUTPUT (403 Forbidden - Lockout Triggered):</b>", body_style))
    story.append(Preformatted('{\n  "error": {\n    "code": "LOCKED",\n    "message": "Session locked due to 3 failed verification attempts. Please contact human support.",\n    "retryable": false\n  }\n}', code_style))

    # POST /sessions/{id}/turn
    story.append(Paragraph("<b>POST /api/v1/sessions/{session_id}/turn</b> (Process Conversation Turn)", h3_style))
    story.append(Paragraph(
        "Sends speech transcript or chat message to Member 2's AI orchestration adapter. "
        "Persists the user input, detected intents, assistant reply, and audit events.",
        body_style
    ))
    story.append(Paragraph("<b>INPUT:</b>", body_style))
    story.append(Preformatted('{\n  "text": "What is the status of my loan application?",\n  "input_type": "voice_transcript"\n}', code_style))
    story.append(Paragraph("<b>OUTPUT (200 OK):</b>", body_style))
    story.append(Preformatted('{\n  "turn_id": "TURN-1029",\n  "session_id": "SES-3f92a10b",\n  "call_id": "CALL-7e81b29c",\n  "turn_number": 1,\n  "reply_text": "Your Personal Loan application APP-77 is currently in Document Verification.",\n  "detected_intents": ["los_status_query"],\n  "state": "VERIFIED",\n  "verified": true,\n  "tickets": [],\n  "escalation": null\n}', code_style))

    # POST /sessions/{id}/escalate
    story.append(Paragraph("<b>POST /api/v1/sessions/{session_id}/escalate</b> (Escalate to Human Agent)", h3_style))
    story.append(Paragraph("Transfers call to human support queue and generates an escalation ticket.", body_style))
    story.append(Paragraph("<b>INPUT:</b>", body_style))
    story.append(Preformatted('{\n  "reason": "Customer requested human supervisor regarding disputed transaction",\n  "category": "complaint",\n  "priority": "HIGH"\n}', code_style))
    story.append(Paragraph("<b>OUTPUT (200 OK):</b>", body_style))
    story.append(Preformatted('{\n  "session_id": "SES-3f92a10b",\n  "call_id": "CALL-7e81b29c",\n  "escalated": true,\n  "escalation_id": "ESC-5012",\n  "ticket_id": "SR-9011",\n  "message": "Call successfully transferred to human agent queue."\n}', code_style))

    # POST /sessions/{id}/end
    story.append(Paragraph("<b>POST /api/v1/sessions/{session_id}/end</b> (Close Session)", h3_style))
    story.append(Paragraph("Closes session and updates call outcome to RESOLVED.", body_style))
    story.append(Paragraph("<b>OUTPUT (200 OK):</b>", body_style))
    story.append(Preformatted('{\n  "session_id": "SES-3f92a10b",\n  "call_id": "CALL-7e81b29c",\n  "status": "ENDED",\n  "message": "Session terminated successfully."\n}', code_style))

    # 3.3 Mock Banking APIs
    story.append(PageBreak())
    story.append(Paragraph("3.3 Mock Banking Services (LOS, LMS, CBS)", h2_style))
    
    # LOS
    story.append(Paragraph("<b>GET /api/v1/mock/los/applications?customer_id=C1023</b>", h3_style))
    story.append(Paragraph(
        "Requires verified session header <code>X-Session-ID</code>. Returns loan applications and document checklist.",
        body_style
    ))
    story.append(Paragraph("<b>OUTPUT (200 OK):</b>", body_style))
    story.append(Preformatted('{\n  "customer_id": "C1023",\n  "applications": [\n    {\n      "application_id": "APP-77",\n      "product_type": "personal",\n      "requested_amount": 300000.0,\n      "application_status": "DOC_VERIFICATION",\n      "pending_documents": ["salary_slip"],\n      "created_at": "2026-10-15T09:30:00Z"\n    }\n  ],\n  "source": "LOS-SIMULATED"\n}', code_style))

    # LMS Loan Details
    story.append(Paragraph("<b>GET /api/v1/mock/lms/loans/{loan_id}</b>", h3_style))
    story.append(Paragraph("Returns loan balance, EMI amount, next due date, and overdue amount.", body_style))
    story.append(Paragraph("<b>OUTPUT (200 OK):</b>", body_style))
    story.append(Preformatted('{\n  "loan_id": "LN-9012",\n  "customer_id": "C1023",\n  "application_id": "APP-70",\n  "product_type": "home_loan",\n  "outstanding_amount": 2450000.0,\n  "emi_amount": 28500.0,\n  "next_due_date": "2026-11-05",\n  "overdue_amount": 0.0,\n  "loan_status": "ACTIVE",\n  "source": "LMS-SIMULATED"\n}', code_style))

    # LMS Schedule
    story.append(Paragraph("<b>GET /api/v1/mock/lms/loans/{loan_id}/schedule</b>", h3_style))
    story.append(Paragraph("Returns complete synthetic EMI schedule.", body_style))
    story.append(Paragraph("<b>OUTPUT (200 OK):</b>", body_style))
    story.append(Preformatted('{\n  "loan_id": "LN-9012",\n  "schedule": [\n    {\n      "schedule_id": "SCH-101",\n      "installment_number": 1,\n      "due_date": "2026-10-05",\n      "amount": 28500.0,\n      "payment_status": "PAID"\n    },\n    {\n      "schedule_id": "SCH-102",\n      "installment_number": 2,\n      "due_date": "2026-11-05",\n      "amount": 28500.0,\n      "payment_status": "PENDING"\n    }\n  ],\n  "source": "LMS-SIMULATED"\n}', code_style))

    # CBS Account
    story.append(Paragraph("<b>GET /api/v1/mock/cbs/accounts/{account_id}</b>", h3_style))
    story.append(Paragraph("Returns savings/checking account balance with masked account number.", body_style))
    story.append(Paragraph("<b>OUTPUT (200 OK):</b>", body_style))
    story.append(Preformatted('{\n  "account_id": "ACC-1001",\n  "customer_id": "C1023",\n  "masked_account": "****8821",\n  "account_type": "savings",\n  "balance": 145000.5,\n  "currency": "INR",\n  "account_status": "ACTIVE",\n  "source": "CBS-SIMULATED"\n}', code_style))

    # 3.4 CSM Tickets
    story.append(Paragraph("3.4 Customer Service Management (CSM Tickets)", h2_style))
    story.append(Paragraph("<b>POST /api/v1/mock/csm/tickets</b> (Idempotent Ticket Creation)", h3_style))
    story.append(Paragraph(
        "Enforces database uniqueness on <code>idempotency_key</code>. Retrying with identical key returns "
        "the existing ticket without creating duplicates.",
        body_style
    ))
    story.append(Paragraph("<b>INPUT:</b>", body_style))
    story.append(Preformatted('{\n  "customer_id": "C1023",\n  "type": "service_request",\n  "category": "repayment_schedule",\n  "summary": "Customer requested repayment schedule PDF via email",\n  "priority": "NORMAL",\n  "call_id": "CALL-7e81b29c",\n  "idempotency_key": "SES-3f92a10b-turn2"\n}', code_style))
    story.append(Paragraph("<b>OUTPUT (201 Created or 200 OK on repeat):</b>", body_style))
    story.append(Preformatted('{\n  "ticket_id": "SR-4471",\n  "status": "OPEN",\n  "customer_id": "C1023",\n  "type": "service_request",\n  "category": "repayment_schedule",\n  "summary": "Customer requested repayment schedule PDF via email",\n  "priority": "NORMAL",\n  "idempotency_key": "SES-3f92a10b-turn2",\n  "created_at": "2026-10-31T12:05:00Z"\n}', code_style))

    # 3.5 Operations Dashboard
    story.append(Paragraph("3.5 Operations Dashboard APIs", h2_style))
    story.append(Paragraph(
        "• <b>GET /api/v1/ops/calls</b>: List calls with pagination (<code>limit</code>, <code>offset</code>).<br/>"
        "• <b>GET /api/v1/ops/calls/{call_id}</b>: Complete call audit with conversation turns and trace.<br/>"
        "• <b>GET /api/v1/ops/tickets</b>: List tickets filtered by status, priority, category.<br/>"
        "• <b>GET /api/v1/ops/escalations</b>: List open escalations requiring agent intervention.",
        body_style
    ))

    # ------------------ 4. SUMMARY TABLE ------------------
    story.append(PageBreak())
    story.append(Paragraph("4. API Endpoint Summary Matrix", h1_style))

    table_data = [
        [
            Paragraph("Method", table_header),
            Paragraph("Endpoint", table_header),
            Paragraph("Purpose", table_header),
            Paragraph("Auth", table_header),
            Paragraph("Status", table_header),
        ],
        [Paragraph("GET", table_cell), Paragraph("/health", table_cell), Paragraph("Canary health check", table_cell), Paragraph("None", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("/api/v1/health", table_cell), Paragraph("System health & timestamp", table_cell), Paragraph("None", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("POST", table_cell), Paragraph("/api/v1/sessions", table_cell), Paragraph("Create voice session", table_cell), Paragraph("None", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("POST", table_cell), Paragraph("/api/v1/sessions/{id}/verify", table_cell), Paragraph("Verify DOB / Lockout", table_cell), Paragraph("Session", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("POST", table_cell), Paragraph("/api/v1/sessions/{id}/turn", table_cell), Paragraph("Process speech turn", table_cell), Paragraph("Session", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("POST", table_cell), Paragraph("/api/v1/sessions/{id}/escalate", table_cell), Paragraph("Human agent handoff", table_cell), Paragraph("Session", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("POST", table_cell), Paragraph("/api/v1/sessions/{id}/end", table_cell), Paragraph("End voice call", table_cell), Paragraph("Session", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("/api/v1/mock/los/applications", table_cell), Paragraph("LOS applications", table_cell), Paragraph("Verified", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("/api/v1/mock/lms/loans/{id}", table_cell), Paragraph("LMS loan balance", table_cell), Paragraph("Verified", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("/api/v1/mock/lms/loans/{id}/schedule", table_cell), Paragraph("LMS EMI schedule", table_cell), Paragraph("Verified", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("/api/v1/mock/cbs/accounts/{id}", table_cell), Paragraph("CBS account balance", table_cell), Paragraph("Verified", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("/api/v1/mock/cbs/transactions/{id}", table_cell), Paragraph("CBS transaction info", table_cell), Paragraph("Verified", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("POST", table_cell), Paragraph("/api/v1/mock/csm/tickets", table_cell), Paragraph("Create ticket (idempotent)", table_cell), Paragraph("Verified", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("/api/v1/mock/csm/tickets/{id}", table_cell), Paragraph("Get ticket details", table_cell), Paragraph("Verified", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("/api/v1/ops/calls", table_cell), Paragraph("Ops call history", table_cell), Paragraph("Staff", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("/api/v1/ops/calls/{id}", table_cell), Paragraph("Call trace & turns", table_cell), Paragraph("Staff", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("/api/v1/ops/tickets", table_cell), Paragraph("Ops tickets list", table_cell), Paragraph("Staff", table_cell), Paragraph("Tested", table_cell)],
        [Paragraph("GET", table_cell), Paragraph("/api/v1/ops/escalations", table_cell), Paragraph("Ops active escalations", table_cell), Paragraph("Staff", table_cell), Paragraph("Tested", table_cell)],
    ]

    t_summary = Table(table_data, colWidths=[45, 160, 160, 65, 70])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 15))

    # ------------------ 5. FRONTEND GUIDE ------------------
    story.append(Paragraph("5. Frontend Developer Integration Guide", h1_style))
    story.append(Paragraph(
        "To integrate with React/Vite, make HTTP requests to <code>http://127.0.0.1:8000/api/v1</code>. "
        "Maintain the <code>session_id</code> in React state for the entire voice or chat call.",
        body_style
    ))

    fe_code = (
        "// Sample React Hook for VaaniDesk Assistant Call\n"
        "import { useState } from 'react';\n\n"
        "export function useVaaniSession() {\n"
        "  const [session, setSession] = useState(null);\n\n"
        "  const startSession = async () => {\n"
        "    const res = await fetch('http://127.0.0.1:8000/api/v1/sessions', {\n"
        "      method: 'POST',\n"
        "      headers: { 'Content-Type': 'application/json' },\n"
        "      body: JSON.stringify({ channel: 'web_voice' })\n"
        "    });\n"
        "    const data = await res.json();\n"
        "    setSession(data);\n"
        "    return data;\n"
        "  };\n\n"
        "  const verify = async (customerId, dob) => {\n"
        "    const res = await fetch(`http://127.0.0.1:8000/api/v1/sessions/${session.session_id}/verify`, {\n"
        "      method: 'POST',\n"
        "      headers: { 'Content-Type': 'application/json' },\n"
        "      body: JSON.stringify({ customer_id: customerId, dob })\n"
        "    });\n"
        "    const data = await res.json();\n"
        "    if (res.ok) setSession(prev => ({ ...prev, verified: true, customer_id: customerId }));\n"
        "    return { ok: res.ok, data };\n"
        "  };\n\n"
        "  return { session, startSession, verify };\n"
        "}"
    )
    story.append(Preformatted(fe_code, code_style))
    story.append(Spacer(1, 10))

    # ------------------ 6. ERROR HANDLING ------------------
    story.append(Paragraph("6. Standardized Error Handling & Fault Envelope", h1_style))
    story.append(Paragraph(
        "All error responses adhere to a consistent JSON envelope with actionable error codes:",
        body_style
    ))
    story.append(Preformatted('{\n  "error": {\n    "code": "AUTH_MISMATCH",\n    "message": "Date of birth does not match customer record.",\n    "retryable": true\n  }\n}', code_style))

    # ------------------ 7. DATA PROTECTION ------------------
    story.append(Paragraph("7. Data Protection & Security Safeguards", h1_style))
    story.append(Paragraph(
        "1. <b>Zero Real Customer Data:</b> All customer, loan, and financial records are strictly synthetic.<br/>"
        "2. <b>Server Verification Authority:</b> The backend never trusts client-supplied <code>verified: true</code> flags.<br/>"
        "3. <b>PII Redaction:</b> Full account numbers are automatically masked (e.g. <code>****8821</code>) and credentials/secrets are excluded from audit records.",
        body_style
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF at: {output_path}")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/VAANIDESK_API_DOCUMENTATION.pdf"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    build_pdf(out)

