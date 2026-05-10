"""
models.py — Pydantic schemas for API-Genie
Input: API description or endpoint specs from the user.
Output: Generated mock endpoints, test suites, and documentation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class AuthType(str, Enum):
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer_token"
    BASIC = "basic_auth"

class CodeLanguage(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"


# ─────────────────────────────────────────────
# Input: User-defined endpoint spec (optional)
# ─────────────────────────────────────────────

class EndpointSpec(BaseModel):
    """A single endpoint the user wants mocked."""
    path: str = Field(..., description="API path, e.g. /users/{id}")
    method: HttpMethod = Field(default=HttpMethod.GET)
    description: Optional[str] = Field(default=None, description="What this endpoint does")
    request_body_example: Optional[Dict[str, Any]] = Field(default=None, description="Example request JSON")
    response_example: Optional[Dict[str, Any]] = Field(default=None, description="Example response JSON")


# ─────────────────────────────────────────────
# Master Input Request
# ─────────────────────────────────────────────

class APIGenieRequest(BaseModel):
    """
    The user describes the API they want mocked.
    They can provide a text prompt, structured specs, or both.
    """
    project_name: str = Field(default="My API", description="Name of the API project")
    description: str = Field(..., description="Natural language description of the API (e.g. 'A fintech wallet API with transfers, KYC, and balance')")
    auth_type: AuthType = Field(default=AuthType.BEARER, description="Authentication scheme for the mock API")
    code_language: CodeLanguage = Field(default=CodeLanguage.PYTHON, description="Language for generated code examples")
    endpoints: Optional[List[EndpointSpec]] = Field(default=None, description="Optional: explicitly define some endpoints")
    num_endpoints: int = Field(default=5, ge=1, le=15, description="How many endpoints to generate if none are specified")


# ─────────────────────────────────────────────
# Output: AI-Generated Documentation (LLM structured output target)
# ─────────────────────────────────────────────

class SchemaField(BaseModel):
    name: str
    type: str
    description: str

class EndpointDoc(BaseModel):
    path: str
    method: str
    summary: str
    description: str
    request_schema: List[SchemaField] = []
    response_schema: List[SchemaField] = []
    sample_response: Dict[str, Any] = {}
    code_example: str
    database_code: str
    status_codes: Dict[str, str]

class TestCaseDoc(BaseModel):
    name: str
    endpoint: str
    method: str
    description: str
    expected_status: int
    assertions: List[str]
    code: str

class APIDocumentation(BaseModel):
    project_name: str = "My API"
    base_url: str = "http://localhost:8000"
    auth_type: str = "none"
    auth_instructions: str = ""
    overview: str = Field(default="", description="High-level summary of the API")
    database_setup: str = Field(default="", description="SQL or migration code")
    database_models: str = Field(default="", description="ORM model definitions")
    endpoints: List[EndpointDoc] = []
    test_cases: List[TestCaseDoc] = []
    setup_instructions: str = Field(default="", description="How to run the mock server")


class APIGenieResponse(BaseModel):
    success: bool
    project_name: str
    total_endpoints: int
    documentation: APIDocumentation
    raw_llm_output: str
    generated_at: str
    latency_ms: float = Field(default=0.0, description="End-to-end generation latency in milliseconds")
    llm_provider: str = Field(default="", description="Which LLM provider served this request")
    cached: bool = Field(default=False, description="Whether this response was served from cache")
