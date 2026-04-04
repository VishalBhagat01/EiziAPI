"""
pdf_generator.py — Official FIU-IND STR format PDF Generator
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from io import BytesIO
from datetime import datetime, timezone


# ─────────────────────────────────────────────
# Color Palette
# ─────────────────────────────────────────────

DARK_NAVY    = colors.HexColor("#0D1B2A")
ACCENT_BLUE  = colors.HexColor("#1B4F8A")
ACCENT_RED   = colors.HexColor("#C0392B")
ACCENT_GREEN = colors.HexColor("#1E8449")
LIGHT_GRAY   = colors.HexColor("#F4F6F8")
MID_GRAY     = colors.HexColor("#BDC3C7")
TEXT_DARK    = colors.HexColor("#1C1C1C")

RISK_COLORS = {
    "CRITICAL": colors.HexColor("#C0392B"),
    "HIGH":     colors.HexColor("#E67E22"),
    "MEDIUM":   colors.HexColor("#F1C40F"),
    "LOW":      colors.HexColor("#27AE60"),
}


# ─────────────────────────────────────────────
# Style Factory
# ─────────────────────────────────────────────

def build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["cover_title"] = ParagraphStyle(
        "cover_title",
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub",
        fontName="Helvetica",
        fontSize=12,
        textColor=colors.HexColor("#AED6F1"),
        alignment=TA_CENTER,
        spaceAfter=5,
    )
    styles["section_heading"] = ParagraphStyle(
        "section_heading",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.white,
        spaceBefore=12,
        spaceAfter=6,
    )
    styles["body"] = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=10,
        textColor=TEXT_DARK,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=5,
    )
    styles["label"] = ParagraphStyle(
        "label",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=ACCENT_BLUE,
    )
    styles["footer"] = ParagraphStyle(
        "footer",
        fontName="Helvetica",
        fontSize=8,
        textColor=MID_GRAY,
        alignment=TA_CENTER,
    )
    return styles


# ─────────────────────────────────────────────
# Header Helper
# ─────────────────────────────────────────────

def section_header(title: str, styles, color=ACCENT_BLUE) -> list:
    header_table = Table(
        [[Paragraph(f"<b>{title}</b>", styles["section_heading"])]],
        colWidths=["100%"],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [Spacer(1, 10), header_table, Spacer(1, 5)]


# ─────────────────────────────────────────────
# Metadata Table
# ─────────────────────────────────────────────

def metadata_table(data: list, styles) -> Table:
    rows = []
    for label, value in data:
        rows.append([
            Paragraph(label, styles["label"]),
            Paragraph(str(value), styles["body"]),
        ])
    t = Table(rows, colWidths=[5 * cm, 12 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ─────────────────────────────────────────────
# PDF Renderer
# ─────────────────────────────────────────────

def generate_pdf(report: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = build_styles()
    story = []
    W = A4[0] - 4 * cm

    risk_level = report.get("risk_level", "HIGH").upper()
    risk_color = RISK_COLORS.get(risk_level, ACCENT_BLUE)

    # ── Header Banner ──
    banner_data = [[Paragraph("FIU-IND OFFICIAL STR REPORT", styles["cover_title"])]]
    banner = Table(banner_data, colWidths=[W])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 15),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
    ]))
    story.append(banner)
    
    sub_banner_data = [[Paragraph("CONFIDENTIAL – FOR REGULATORY USE ONLY", styles["cover_sub"])]]
    sub_banner = Table(sub_banner_data, colWidths=[W])
    sub_banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(sub_banner)
    story.append(Spacer(1, 15))

    # ── Metadata ──
    story += section_header("REPORT METADATA", styles)
    story.append(metadata_table([
        ("Case ID", report.get("case_id")),
        ("Report Date", report.get("report_date")),
        ("Report Type", report.get("report_type")),
        ("Risk Level", f"<b>{risk_level}</b>"),
    ], styles))
    
    # ── Official sections ──
    sections = [
        ("SECTION 1: REPORTING ENTITY DETAILS", "reporting_entity_details", DARK_NAVY),
        ("SECTION 2: PRINCIPAL OFFICER DETAILS", "principal_officer_details", DARK_NAVY),
        ("SECTION 3: BASIS FOR SUSPICION", "reason_for_suspicion", ACCENT_RED),
        ("SECTION 4: TRANSACTION DETAILS", "transaction_details", ACCENT_BLUE),
        ("SECTION 5: LINKED PERSONS / ENTITIES", "linked_person_details", ACCENT_BLUE),
        ("SUPPLEMENTARY: PATTERN ANALYSIS", "pattern_analysis", ACCENT_BLUE),
        ("SUPPLEMENTARY: NETWORK TOPOLOGY", "network_analysis", ACCENT_BLUE),
        ("SUPPLEMENTARY: GEOGRAPHIC ANALYSIS", "geographic_analysis", ACCENT_BLUE),
        ("SUPPLEMENTARY: RISK ASSESSMENT", "risk_assessment", ACCENT_RED),
        ("RECOMMENDED REGULATORY ACTIONS", "recommended_actions", ACCENT_GREEN),
        ("REGULATORY REFERENCES", "regulatory_references", MID_GRAY),
        ("TIPPING-OFF CONFIRMATION", "tipping_off_confirmation", ACCENT_RED),
    ]

    for title, key, color in sections:
        content = report.get(key, "").strip()
        if content:
            story += section_header(title, styles, color=color)
            for paragraph_text in content.split("\n"):
                if paragraph_text.strip():
                    story.append(Paragraph(paragraph_text.strip(), styles["body"]))
            story.append(Spacer(1, 10))

    # ── Footer ──
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        f"Generated by FIU AI Engine | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Confidential",
        styles["footer"]
    ))

    doc.build(story)
    return buffer.getvalue()
