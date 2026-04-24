"""
app.py — API-Genie: AI-Powered API Mock & Documentation Generator
FastAPI application with LangChain + Groq
"""

import io
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from models import APIGenieRequest, APIGenieResponse, APIDocumentation
from report import generate_api_spec
from pdf_generator import generate_pdf


# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────

app = FastAPI(
    title="API-Genie",
    description="""
## ⚡ API-Genie — AI-Powered API Mock & Documentation Generator

Describe the API you need in plain English, and API-Genie will generate:
- **Complete REST API specification** with realistic mock data
- **Professional PDF documentation** (Stripe-style)
- **Pytest test suite** ready to run against your real backend

### How it works
1. Describe your API (e.g., "E-commerce platform with products, orders, and payments")
2. AI generates endpoints, schemas, sample data, and tests
3. Download the docs as PDF or integrate with your CI/CD pipeline

### Powered By
- 🤖 Groq (Llama 3.3 70B)
- 🦜 LangChain
- ⚡ FastAPI
    """,
    version="1.0.0",
    contact={"name": "API-Genie"},
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
        "message": "API-Genie ⚡ — AI-Powered API Mock Generator",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "generate_spec_json": "POST /generate",
            "generate_spec_pdf": "POST /generate/pdf",
            "health": "GET /health",
        },
    }


@app.get("/health", tags=["Health"])
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "API-Genie",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post(
    "/generate",
    response_model=APIGenieResponse,
    tags=["Generation"],
    summary="Generate API Specification (JSON)",
    description="""
Describe your API in plain English and get back a complete specification with:
- Endpoint definitions with request/response schemas
- Realistic sample responses
- Pytest test case definitions
- Authentication setup instructions
    """,
)
async def generate_spec_json(request: APIGenieRequest):
    """Generate API spec and return as structured JSON."""
    try:
        doc_dict, raw_text = generate_api_spec(request)
        return APIGenieResponse(
            success=True,
            project_name=request.project_name,
            total_endpoints=len(doc_dict.get("endpoints", [])),
            documentation=doc_dict,
            raw_llm_output=raw_text,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Generation failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post(
    "/generate/pdf",
    tags=["Generation"],
    summary="Generate API Documentation (PDF)",
    description="""
Same as `/generate` but returns a downloadable **PDF file** with professional API documentation.

The PDF includes:
- Dark-themed professional layout
- Method-colored endpoint badges (GET=green, POST=cyan, etc.)
- Schema tables with field types and descriptions
- Sample response JSON blocks
- Auto-generated test suite
    """,
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF file download",
        }
    },
)
async def generate_spec_pdf(request: APIGenieRequest):
    """Generate API documentation and return as a downloadable PDF."""
    try:
        doc_dict, _ = generate_api_spec(request)
        pdf_bytes = generate_pdf(doc_dict)
        filename = request.project_name.replace(" ", "_")
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="APIGenie_{filename}_Docs.pdf"',
            },
        )
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Generation failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")