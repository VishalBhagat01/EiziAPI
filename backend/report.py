"""
report.py — LangChain + Groq API-Genie Generation Engine
Generates mock API specs, sample data, and test cases from a user's description.
"""

import os
import json
import re
from datetime import datetime, timezone
from typing import Tuple

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

from models import APIGenieRequest

load_dotenv()

# ─────────────────────────────────────────────
# LLM Setup
# ─────────────────────────────────────────────

def get_llm() -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set in .env file")
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=api_key,
        temperature=0.3,
        max_tokens=8192,
    )


# ─────────────────────────────────────────────
# Context Builder — converts user input to structured prompt context
# ─────────────────────────────────────────────

def build_context(request: APIGenieRequest) -> str:
    sections = []

    sections.append(f"""
═══ PROJECT OVERVIEW ═══
  Project Name        : {request.project_name}
  API Description     : {request.description}
  Authentication      : {request.auth_type.value}
  Requested Endpoints : {request.num_endpoints}
""")

    if request.endpoints:
        endpoint_text = "═══ USER-DEFINED ENDPOINTS ═══\n"
        for i, ep in enumerate(request.endpoints, 1):
            endpoint_text += f"""
  Endpoint {i}:
    Path              : {ep.path}
    Method            : {ep.method.value}
    Description       : {ep.description or 'Not specified'}
    Request Example   : {json.dumps(ep.request_body_example) if ep.request_body_example else 'None'}
    Response Example  : {json.dumps(ep.response_example) if ep.response_example else 'None'}
"""
        sections.append(endpoint_text)

    return "\n".join(sections)


# ─────────────────────────────────────────────
# API-Genie Master Prompt
# ─────────────────────────────────────────────

API_GENIE_PROMPT = """You are a Senior Backend Architect and API designer. Your task is to design a complete, production-ready REST API specification based on the user's description. Generate realistic mock endpoints with sample data that a Frontend developer could immediately use.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER INPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Design a RESTful API with the following requirements:

1. **Endpoints**: Generate {num_endpoints} well-designed REST endpoints following best practices (proper HTTP verbs, resource naming, pagination, etc.)
2. **Schemas**: For each endpoint, define request and response schemas with realistic field types (string, integer, float, boolean, uuid, datetime, email, url, phone)
3. **Sample Responses**: Generate realistic, domain-specific sample data (not "test123" or "foo" — use real-looking names, emails, amounts, etc.)
4. **Test Cases**: Generate pytest-style test case definitions for each endpoint (at least 1 per endpoint)
5. **Auth**: Include auth instructions for {auth_type}

Return ONLY a valid JSON object in this exact structure:

{{
  "project_name": "{project_name}",
  "base_url": "http://localhost:8000",
  "auth_type": "{auth_type}",
  "auth_instructions": "Describe how to authenticate (e.g., pass Bearer token in Authorization header)",
  "overview": "A 2-3 sentence overview of this API and its purpose",
  "endpoints": [
    {{
      "path": "/resource",
      "method": "GET",
      "summary": "Short summary",
      "description": "Detailed description of what this endpoint does",
      "request_schema": [
        {{"name": "field_name", "type": "string", "description": "What this field is", "example": "example_value"}}
      ],
      "response_schema": [
        {{"name": "field_name", "type": "string", "description": "What this field is", "example": "example_value"}}
      ],
      "sample_response": {{"key": "realistic_value"}},
      "status_codes": {{"200": "Success", "404": "Resource not found"}}
    }}
  ],
  "test_cases": [
    {{
      "name": "test_get_resource_returns_200",
      "endpoint": "/resource",
      "method": "GET",
      "description": "Verify that GET /resource returns a 200 with valid data",
      "expected_status": 200,
      "request_body": null,
      "assertions": ["Response contains 'id' field", "Status code is 200"]
    }}
  ],
  "setup_instructions": "Step-by-step instructions to run the mock server locally"
}}

IMPORTANT RULES:
- request_schema should be null for GET/DELETE endpoints
- Generate realistic, domain-appropriate data (real names, real-looking UUIDs, realistic amounts)
- Follow REST naming conventions (plural nouns, no verbs in paths)
- Include proper error status codes (400, 401, 404, 500) where appropriate
- Generate at least {num_endpoints} endpoints
- Return ONLY the JSON, no extra text"""


# ─────────────────────────────────────────────
# JSON Extractor
# ─────────────────────────────────────────────

def extract_json(text: str) -> dict:
    text = text.strip()
    patterns = [r"```json\s*([\s\S]*?)\s*```", r"```\s*([\s\S]*?)\s*```"]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            text = match.group(1).strip()
            break
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse JSON. Raw response:\n{text[:500]}")


# ─────────────────────────────────────────────
# Main Generator
# ─────────────────────────────────────────────

def generate_api_spec(request: APIGenieRequest) -> Tuple[dict, str]:
    context = build_context(request)

    llm = get_llm()
    prompt = ChatPromptTemplate.from_template(API_GENIE_PROMPT)
    chain = prompt | llm | StrOutputParser()

    raw_response = chain.invoke({
        "context": context,
        "project_name": request.project_name,
        "auth_type": request.auth_type.value,
        "num_endpoints": request.num_endpoints,
    })

    doc_dict = extract_json(raw_response)
    return doc_dict, raw_response