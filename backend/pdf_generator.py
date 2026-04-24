"""
pdf_generator.py — API-Genie Professional API Documentation PDF Generator
Generates a clean, dark-themed technical documentation PDF.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Preformatted
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from io import BytesIO
from datetime import datetime, timezone
import json


# ─────────────────────────────────────────────
# Color Palette (Dark Professional Theme)
# ─────────────────────────────────────────────

BG_DARK      = colors.HexColor("#0F0F0F")
BG_CARD      = colors.HexColor("#1A1A2E")
ACCENT_CYAN  = colors.HexColor("#00D2FF")
ACCENT_GREEN = colors.HexColor("#00E676")
ACCENT_AMBER = colors.HexColor("#FFB300")
ACCENT_RED   = colors.HexColor("#FF5252")
ACCENT_PURPLE = colors.HexColor("#BB86FC")
TEXT_WHITE   = colors.HexColor("#FFFFFF")
TEXT_GRAY    = colors.HexColor("#9E9E9E")
TEXT_LIGHT   = colors.HexColor("#E0E0E0")
BORDER_DARK  = colors.HexColor("#333333")

METHOD_COLORS = {
    "GET":    colors.HexColor("#00E676"),
    "POST":   colors.HexColor("#00D2FF"),
    "PUT":    colors.HexColor("#FFB300"),
    "PATCH":  colors.HexColor("#BB86FC"),
    "DELETE": colors.HexColor("#FF5252"),
}


# ─────────────────────────────────────────────
# Style Factory
# ─────────────────────────────────────────────

def build_styles():
    styles = {}

    styles["title"] = ParagraphStyle(
        "title",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=TEXT_WHITE,
        alignment=TA_CENTER,
        spaceAfter=5,
    )
    styles["subtitle"] = ParagraphStyle(
        "subtitle",
        fontName="Helvetica",
        fontSize=11,
        textColor=ACCENT_CYAN,
        alignment=TA_CENTER,
        spaceAfter=5,
    )
    styles["section_heading"] = ParagraphStyle(
        "section_heading",
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=TEXT_WHITE,
        spaceBefore=12,
        spaceAfter=6,
    )
    styles["body"] = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=10,
        textColor=TEXT_LIGHT,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=5,
    )
    styles["code"] = ParagraphStyle(
        "code",
        fontName="Courier",
        fontSize=9,
        textColor=ACCENT_GREEN,
        leading=12,
        spaceAfter=4,
    )
    styles["label"] = ParagraphStyle(
        "label",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=ACCENT_CYAN,
    )
    styles["method_badge"] = ParagraphStyle(
        "method_badge",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=TEXT_WHITE,
        alignment=TA_CENTER,
    )
    styles["path_text"] = ParagraphStyle(
        "path_text",
        fontName="Courier-Bold",
        fontSize=11,
        textColor=TEXT_WHITE,
    )
    styles["field_name"] = ParagraphStyle(
        "field_name",
        fontName="Courier",
        fontSize=9,
        textColor=ACCENT_CYAN,
    )
    styles["field_type"] = ParagraphStyle(
        "field_type",
        fontName="Helvetica",
        fontSize=9,
        textColor=ACCENT_AMBER,
    )
    styles["field_desc"] = ParagraphStyle(
        "field_desc",
        fontName="Helvetica",
        fontSize=9,
        textColor=TEXT_GRAY,
    )
    styles["footer"] = ParagraphStyle(
        "footer",
        fontName="Helvetica",
        fontSize=8,
        textColor=TEXT_GRAY,
        alignment=TA_CENTER,
    )
    styles["test_name"] = ParagraphStyle(
        "test_name",
        fontName="Courier",
        fontSize=9,
        textColor=ACCENT_GREEN,
    )
    return styles


# ─────────────────────────────────────────────
# Section Header Helper
# ─────────────────────────────────────────────

def section_header(title: str, styles, color=ACCENT_CYAN) -> list:
    header_table = Table(
        [[Paragraph(f"<b>{title}</b>", styles["section_heading"])]],
        colWidths=["100%"],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 2, color),
    ]))
    return [Spacer(1, 12), header_table, Spacer(1, 6)]


# ─────────────────────────────────────────────
# PDF Renderer
# ─────────────────────────────────────────────

def generate_pdf(doc_data: dict) -> bytes:
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

    # ── Title Banner ──
    banner_data = [[Paragraph(f"⚡ {doc_data.get('project_name', 'API-Genie')}", styles["title"])]]
    banner = Table(banner_data, colWidths=[W])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 20),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, -1), 2, ACCENT_CYAN),
    ]))
    story.append(banner)

    sub_data = [[Paragraph("API Documentation &amp; Integration Guide", styles["subtitle"])]]
    sub_banner = Table(sub_data, colWidths=[W])
    sub_banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
    ]))
    story.append(sub_banner)
    story.append(Spacer(1, 10))

    # ── Overview ──
    story += section_header("OVERVIEW", styles)
    overview = doc_data.get("overview", "No overview provided.")
    story.append(Paragraph(overview, styles["body"]))

    # ── Auth Info ──
    story += section_header("AUTHENTICATION", styles, ACCENT_AMBER)
    auth_info = doc_data.get("auth_instructions", "No auth required.")
    auth_table = Table([
        [Paragraph("Type", styles["label"]), Paragraph(doc_data.get("auth_type", "none"), styles["body"])],
        [Paragraph("Instructions", styles["label"]), Paragraph(auth_info, styles["body"])],
    ], colWidths=[4 * cm, W - 4 * cm])
    auth_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_DARK),
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(auth_table)

    # ── Endpoints ──
    endpoints = doc_data.get("endpoints", [])
    story += section_header(f"ENDPOINTS ({len(endpoints)} total)", styles, ACCENT_GREEN)

    for i, ep in enumerate(endpoints, 1):
        method = ep.get("method", "GET").upper()
        method_color = METHOD_COLORS.get(method, ACCENT_CYAN)

        # Method + Path row
        method_cell = Paragraph(f"<b>{method}</b>", styles["method_badge"])
        path_cell = Paragraph(f"<font face='Courier-Bold'>{ep.get('path', '/')}</font>", styles["path_text"])

        ep_header = Table([[method_cell, path_cell]], colWidths=[2.5 * cm, W - 2.5 * cm])
        ep_header.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), method_color),
            ("BACKGROUND", (1, 0), (1, 0), BG_CARD),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(Spacer(1, 8))
        story.append(ep_header)

        # Summary
        summary = ep.get("summary", "")
        desc = ep.get("description", "")
        if summary:
            story.append(Paragraph(f"<b>{summary}</b>", styles["body"]))
        if desc:
            story.append(Paragraph(desc, styles["body"]))

        # Response schema table
        response_schema = ep.get("response_schema", [])
        if response_schema:
            schema_rows = [[
                Paragraph("<b>Field</b>", styles["label"]),
                Paragraph("<b>Type</b>", styles["label"]),
                Paragraph("<b>Description</b>", styles["label"]),
            ]]
            for field in response_schema:
                if isinstance(field, dict):
                    schema_rows.append([
                        Paragraph(field.get("name", ""), styles["field_name"]),
                        Paragraph(field.get("type", ""), styles["field_type"]),
                        Paragraph(field.get("description", ""), styles["field_desc"]),
                    ])

            if len(schema_rows) > 1:
                schema_table = Table(schema_rows, colWidths=[4 * cm, 3 * cm, W - 7 * cm])
                schema_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), BG_CARD),
                    ("BACKGROUND", (0, 1), (-1, -1), BG_DARK),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER_DARK),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(schema_table)

        # Sample Response
        sample = ep.get("sample_response", {})
        if sample:
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>Sample Response:</b>", styles["label"]))
            json_str = json.dumps(sample, indent=2)
            for line in json_str.split("\n"):
                story.append(Paragraph(line.replace(" ", "&nbsp;"), styles["code"]))

        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_DARK))

    # ── Test Cases ──
    test_cases = doc_data.get("test_cases", [])
    if test_cases:
        story += section_header(f"TEST SUITE ({len(test_cases)} tests)", styles, ACCENT_PURPLE)
        for tc in test_cases:
            if isinstance(tc, dict):
                story.append(Paragraph(f"def {tc.get('name', 'test_unnamed')}():", styles["test_name"]))
                story.append(Paragraph(f"  # {tc.get('description', '')}", styles["body"]))
                story.append(Paragraph(
                    f"  {tc.get('method', 'GET')} {tc.get('endpoint', '/')} → expects {tc.get('expected_status', 200)}",
                    styles["code"]
                ))
                assertions = tc.get("assertions", [])
                for a in assertions:
                    story.append(Paragraph(f"  assert {a}", styles["code"]))
                story.append(Spacer(1, 6))

    # ── Setup Instructions ──
    setup = doc_data.get("setup_instructions", "")
    if setup:
        story += section_header("SETUP INSTRUCTIONS", styles, ACCENT_AMBER)
        for line in setup.split("\n"):
            if line.strip():
                story.append(Paragraph(line.strip(), styles["body"]))

    # ── Footer ──
    story.append(Spacer(1, 25))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_DARK))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        f"Generated by API-Genie | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        styles["footer"]
    ))

    doc.build(story)
    return buffer.getvalue()
