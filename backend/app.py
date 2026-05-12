"""
app.py — API-Genie: AI-Powered API Mock & Documentation Generator

Production-grade FastAPI application with:
  • Request timing middleware (X-Response-Time-Ms header)
  • Structured logging with request correlation
  • In-memory rate limiting (10 req/min per IP on /generate)
  • Cache-aware health check with uptime & provider stats
  • Input sanitization (description length cap)
  • LLM provider fallback (Groq → Gemini)
"""

import time
import logging
from datetime import datetime, timezone
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from models import APIGenieRequest, APIGenieResponse
from report import generate_api_spec, get_cache_stats

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("api_genie")

_BOOT_TIME = datetime.now(timezone.utc)


# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────

app = FastAPI(
    title="API-Genie",
    description="""
##  API-Genie — AI-Powered API Mock & Documentation Generator

Describe the API you need in plain English, and API-Genie will generate:
- **Complete REST API specification** with realistic mock data
- **Database-ready code** (SQLAlchemy/Sequelize)
- **Pytest test suite** ready to run against your real backend

### Architecture Highlights
-  **Dual-provider LLM fallback** (Groq → Google Gemini)
-  **In-memory LRU cache** — repeat queries return in <1ms
-  **Per-request latency tracking** via `X-Response-Time-Ms` header
-  **Rate limiting** — 10 requests/min per IP on generation endpoint

### Powered By
-  Groq (Llama 3.3 70B) / Google Gemini 2.5 Flash
-  LangChain (structured output)
-  FastAPI + Pydantic v2
    """,
    version="2.0.0",
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
# Middleware: Request Timing
# ─────────────────────────────────────────────

class TimingMiddleware(BaseHTTPMiddleware):
    """Injects X-Response-Time-Ms header into every response."""

    async def dispatch(self, request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
        logger.info(
            "%s %s → %d (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


app.add_middleware(TimingMiddleware)


# ─────────────────────────────────────────────
# Rate Limiter (in-memory, per-IP)
# ─────────────────────────────────────────────

_rate_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 10          # max requests
_RATE_WINDOW_SEC = 60     # per this many seconds


def _check_rate_limit(client_ip: str) -> bool:
    """Returns True if client is within rate limit, False if exceeded."""
    now = time.time()
    timestamps = _rate_store[client_ip]
    # Prune expired entries
    _rate_store[client_ip] = [t for t in timestamps if now - t < _RATE_WINDOW_SEC]
    if len(_rate_store[client_ip]) >= _RATE_LIMIT:
        return False
    _rate_store[client_ip].append(now)
    return True


# ─────────────────────────────────────────────
# Input Sanitisation
# ─────────────────────────────────────────────

_MAX_DESCRIPTION_LEN = 2000  # chars


def _sanitize_request(request: APIGenieRequest) -> APIGenieRequest:
    """Truncate excessively long descriptions, strip whitespace."""
    request.description = request.description.strip()[:_MAX_DESCRIPTION_LEN]
    request.project_name = request.project_name.strip() or "My API"
    return request


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    """API root — health check."""
    return {
        "message": "API-Genie ⚡ — AI-Powered API Mock Generator",
        "version": "2.0.0",
        "docs": "/docs",
        "endpoints": {
            "generate_spec_json": "POST /generate",
            "health": "GET /health",
        },
    }


@app.get("/health", tags=["Health"])
def health():
    """Health check with uptime, cache stats, and provider info."""
    now = datetime.now(timezone.utc)
    uptime_seconds = (now - _BOOT_TIME).total_seconds()
    return {
        "status": "healthy",
        "service": "API-Genie",
        "version": "2.0.0",
        "timestamp": now.isoformat(),
        "uptime_seconds": round(uptime_seconds, 1),
        "cache": get_cache_stats(),
        "providers": ["groq/llama-3.3-70b", "google/gemini-2.5-flash"],
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

**Performance**: Repeat queries are served from LRU cache (<1ms).
**Fallback**: If the primary LLM provider fails, a secondary provider is tried automatically.
    """,
)


async def generate_spec_json(request: APIGenieRequest, req: Request):
    """Generate API spec and return as structured JSON."""
    # ── Rate limit ──
    client_ip = req.client.host if req.client else "unknown"
    if not _check_rate_limit(client_ip):
        logger.warning("Rate limit exceeded for %s", client_ip)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {_RATE_LIMIT} requests per {_RATE_WINDOW_SEC}s.",
        )

    # ── Sanitize ──
    request = _sanitize_request(request)

    if not request.description:
        raise HTTPException(status_code=422, detail="Description cannot be empty.")

    try:
        doc_dict, raw_text, latency_ms, provider, from_cache = generate_api_spec(request)

        return APIGenieResponse(
            success=True,
            project_name=request.project_name,
            total_endpoints=len(doc_dict.get("endpoints", [])),
            documentation=doc_dict,
            raw_llm_output=raw_text,
            generated_at=datetime.now(timezone.utc).isoformat(),
            latency_ms=round(latency_ms, 2),
            llm_provider=provider,
            cached=from_cache,
        )
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Generation failed: {str(e)}")
    except Exception as e:
        logger.exception("Unhandled error in /generate")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")