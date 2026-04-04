"""
app.py — FIU Report Generator API
FastAPI application with LangChain + Google Gemini GenAI
"""

import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from models import FIUReportRequest, FIUReportResponse
from report import generate_fiu_report
from pdf_generator import generate_pdf


# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────

app = FastAPI(
    title="FIU Report Generator API",
    description="""
## 🏦 Financial Intelligence Unit (FIU) Report Generator

AI-powered Suspicious Activity Report (SAR) generator that consumes **Fraud Detection API** outputs
and produces professional FIU/SAR reports using **LangChain + Google Gemini**.

### Supported Input Sources
| Endpoint | Description |
|---|---|
| `POST /check-transaction` | Transaction risk assessment with patterns & graph |
| `GET /detect-fraud-network` | Fraud network topology |
| `GET /detect-pattern/{type}` | Specific fraud pattern detection results |
| `GET /detect-geo-anomaly` | Geographic anomaly analysis |

### Report Output
- **JSON** — Structured 15-section FIU SAR report
- **PDF** — Professional printable PDF with colored sections and risk badge

### Powered By
- 🦜 LangChain
- 🤖 Google Gemini 1.5 Flash
- ⚡ FastAPI
    """,
    version="1.0.0",
    contact={"name": "FIU AI System"},
    license_info={"name": "Internal Use Only"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    """API root — health check."""
    return {
        "message": "FIU Report Generator API 🚀",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "generate_report_json": "POST /generate-fiu-report",
            "generate_report_pdf":  "POST /generate-fiu-report/pdf",
            "health":               "GET /health",
        },
    }


@app.get("/health", tags=["Health"])
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "FIU Report Generator",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post(
    "/generate-fiu-report",
    response_model=FIUReportResponse,
    tags=["Report Generation"],
    summary="Generate FIU SAR Report (JSON)",
    description="""
Accepts consolidated fraud detection outputs and generates a detailed FIU Suspicious Activity Report.

**All fields are optional** — include any combination of:
- `transaction_data` from `POST /check-transaction`
- `fraud_network` from `GET /detect-fraud-network`
- `patterns` from `GET /detect-pattern/{pattern_type}`
- `geo_anomalies` from `GET /detect-geo-anomaly`
    """,
)
async def generate_report_json(request: FIUReportRequest):
    """Generate FIU SAR report and return as structured JSON."""
    try:
        report_dict, raw_text, case_id = generate_fiu_report(request)
        return FIUReportResponse(
            success=True,
            case_id=case_id,
            report_type=report_dict.get("report_type", "STR"),
            report=report_dict,
            raw_report_text=raw_text,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Report generation failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post(
    "/generate-fiu-report/pdf",
    tags=["Report Generation"],
    summary="Generate FIU SAR Report (PDF)",
    description="""
Same as `/generate-fiu-report` but returns a downloadable **PDF file**.

The PDF includes:
- Colored header with FIU branding
- Risk level badge (CRITICAL / HIGH / MEDIUM / LOW)
- All 15 report sections with formatted text
- Footer with generation timestamp
    """,
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF file download",
        }
    },
)
async def generate_report_pdf(request: FIUReportRequest):
    """Generate FIU SAR report and return as a downloadable PDF."""
    try:
        report_dict, _, case_id = generate_fiu_report(request)
        pdf_bytes = generate_pdf(report_dict)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="FIU_SAR_{case_id}.pdf"',
                "X-Case-ID": case_id,
            },
        )
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Report generation failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post(
    "/generate-fiu-report/both",
    tags=["Report Generation"],
    summary="Generate FIU SAR Report (JSON + PDF link)",
    description="Generates the report and returns JSON. PDF can be fetched separately.",
)
async def generate_report_both(request: FIUReportRequest):
    """Generate JSON report and include a note about PDF endpoint."""
    try:
        report_dict, raw_text, case_id = generate_fiu_report(request)
        return {
            "success": True,
            "case_id": case_id,
            "report": report_dict,
            "pdf_endpoint": "POST /generate-fiu-report/pdf (same request body)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))