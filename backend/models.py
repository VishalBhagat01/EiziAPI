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
    endpoints: Optional[List[EndpointSpec]] = Field(default=None, description="Optional: explicitly define some endpoints")
    num_endpoints: int = Field(default=5, ge=1, le=15, description="How many endpoints to generate if none are specified")


# ─────────────────────────────────────────────
# Output: AI-Generated Mock Endpoint
# ─────────────────────────────────────────────

class MockField(BaseModel):
    name: str
    type: str = Field(description="e.g. string, integer, float, boolean, uuid, datetime, email")
    description: Optional[str] = None
    example: Any = None


class MockEndpoint(BaseModel):
    path: str
    method: str
    summary: str = ""
    description: str = ""
    request_schema: Optional[Any] = None
    response_schema: Any = []
    sample_response: Any = {}
    status_codes: Any = Field(
        default={"200": "Success"},
        description="Map of status code to description"
    )


class TestCase(BaseModel):
    name: str = Field(default="test_unnamed", description="Test function name, e.g. test_get_users_returns_200")
    endpoint: str = ""
    method: str = "GET"
    description: str = ""
    expected_status: int = 200
    request_body: Optional[Any] = None
    assertions: Any = Field(default=[], description="List of assertion descriptions")


# ─────────────────────────────────────────────
# Master Output: Full API Documentation
# ─────────────────────────────────────────────

class APIDocumentation(BaseModel):
    project_name: str = "My API"
    base_url: str = "http://localhost:8000"
    auth_type: str = "none"
    auth_instructions: str = ""
    overview: str = Field(default="", description="High-level summary of the API")
    endpoints: List[Any] = []
    test_cases: List[Any] = []
    setup_instructions: str = Field(default="", description="How to run the mock server")


class APIGenieResponse(BaseModel):
    success: bool
    project_name: str
    total_endpoints: int
    documentation: APIDocumentation
    raw_llm_output: str
    generated_at: str
