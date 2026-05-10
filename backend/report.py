"""
report.py — LangChain + Groq/Gemini API-Genie Generation Engine

Production-grade LLM orchestration with:
  • Raw text generation for Groq (avoids tool_use_failed on large schemas)
  • Structured output for Gemini (handles complex schemas natively)
  • 2-pass generation pipeline: endpoints → tests (reduces per-call payload)
  • In-memory LRU cache for repeat queries (~0ms latency on cache hit)
  • Dual-provider fallback (Groq → Gemini)
  • Robust JSON extraction from raw LLM responses
"""

import os
import re
import json
import hashlib
import logging
import time
from collections import OrderedDict
from typing import Tuple

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

from models import APIGenieRequest, APIDocumentation

load_dotenv()

logger = logging.getLogger("api_genie.report")


# ─────────────────────────────────────────────
# LRU Cache (thread-safe, bounded)
# ─────────────────────────────────────────────

class LRUCache:
    """Simple bounded LRU cache for prompt→result pairs.

    Evicts least-recently-used entries when capacity is exceeded.
    Thread-safe for single-writer / multi-reader FastAPI async context.
    """

    def __init__(self, max_size: int = 64):
        self._cache: OrderedDict[str, Tuple[dict, str, str]] = OrderedDict()
        self._max_size = max_size
        self.hits = 0
        self.misses = 0

    def _make_key(self, request: APIGenieRequest) -> str:
        """Deterministic cache key from request fields."""
        raw = (
            f"{request.project_name}|{request.description}|"
            f"{request.auth_type.value}|{request.code_language.value}|"
            f"{request.num_endpoints}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, request: APIGenieRequest):
        key = self._make_key(request)
        if key in self._cache:
            self._cache.move_to_end(key)
            self.hits += 1
            return self._cache[key]
        self.misses += 1
        return None

    def put(self, request: APIGenieRequest, doc_dict: dict, raw_text: str, provider: str):
        key = self._make_key(request)
        self._cache[key] = (doc_dict, raw_text, provider)
        self._cache.move_to_end(key)
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "size": self.size,
            "max_size": self._max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{(self.hits / total * 100):.1f}%" if total else "N/A",
        }


# Module-level cache instance
_cache = LRUCache(max_size=64)


def get_cache_stats() -> dict:
    """Expose cache metrics for the /health endpoint."""
    return _cache.stats


# ─────────────────────────────────────────────
# LLM Provider Registry
# ─────────────────────────────────────────────

def _build_groq() -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set in .env file")
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=api_key,
        temperature=0.3,
        max_tokens=4096,
    )


def _build_google() -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY not set in .env file")
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.3,
        max_output_tokens=8192,
    )


# Provider config: (name, factory, supports_structured_output)
# Groq does NOT support structured output for large schemas — use raw text
# Gemini handles structured output natively via function calling
_PROVIDERS = [
    ("groq/llama-3.3-70b", _build_groq, False),
    ("google/gemini-2.5-flash", _build_google, True),
]


# ─────────────────────────────────────────────
# JSON Extraction from Raw LLM Text
# ─────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """Extract a JSON object from raw LLM text output.

    Handles:
      - Clean JSON (starts with {)
      - Markdown code blocks (```json ... ```)
      - Surrounding prose before/after the JSON block
    """
    # Try direct parse first
    text = text.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Try extracting from markdown code block
    md_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding the outermost { ... } pair
    brace_start = text.find("{")
    if brace_start != -1:
        brace_end = text.rfind("}")
        if brace_end > brace_start:
            candidate = text[brace_start:brace_end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

    raise ValueError(f"Could not extract valid JSON from LLM response ({len(text)} chars)")


def _validate_doc(raw: dict) -> dict:
    """Validate and normalise the raw LLM JSON into APIDocumentation shape.

    Fills missing fields with safe defaults so the frontend never crashes.
    """
    doc = {
        "project_name": raw.get("project_name", "My API"),
        "base_url": raw.get("base_url", "http://localhost:8000"),
        "auth_type": raw.get("auth_type", "none"),
        "auth_instructions": raw.get("auth_instructions", ""),
        "overview": raw.get("overview", ""),
        "database_setup": raw.get("database_setup", ""),
        "database_models": raw.get("database_models", ""),
        "endpoints": [],
        "test_cases": [],
        "setup_instructions": raw.get("setup_instructions", ""),
    }

    # Normalise endpoints
    for ep in raw.get("endpoints", []):
        if not isinstance(ep, dict):
            continue
        doc["endpoints"].append({
            "path": ep.get("path", "/"),
            "method": ep.get("method", "GET"),
            "summary": ep.get("summary", ""),
            "description": ep.get("description", ""),
            "request_schema": _normalise_schema_fields(ep.get("request_schema", [])),
            "response_schema": _normalise_schema_fields(ep.get("response_schema", [])),
            "sample_response": ep.get("sample_response", {}),
            "code_example": str(ep.get("code_example", "")),
            "database_code": str(ep.get("database_code", "")),
            "status_codes": ep.get("status_codes", {"200": "Success"}),
        })

    # Normalise test cases
    for tc in raw.get("test_cases", []):
        if not isinstance(tc, dict):
            continue
        doc["test_cases"].append({
            "name": tc.get("name", "test_unnamed"),
            "endpoint": tc.get("endpoint", "/"),
            "method": tc.get("method", "GET"),
            "description": tc.get("description", ""),
            "expected_status": int(tc.get("expected_status", 200)),
            "assertions": tc.get("assertions", []),
            "code": str(tc.get("code", "")),
        })

    return doc


def _normalise_schema_fields(fields) -> list:
    """Ensure schema fields are always a list of {name, type, description} dicts."""
    if not isinstance(fields, list):
        return []
    result = []
    for f in fields:
        if isinstance(f, dict):
            result.append({
                "name": str(f.get("name", "")),
                "type": str(f.get("type", "string")),
                "description": str(f.get("description", "")),
            })
    return result


# ─────────────────────────────────────────────
# Context Builder
# ─────────────────────────────────────────────

def build_context(request: APIGenieRequest) -> str:
    parts = [
        f"Project: {request.project_name}",
        f"Description: {request.description}",
        f"Auth: {request.auth_type.value}",
        f"Language: {request.code_language.value}",
        f"Endpoints: {request.num_endpoints}",
    ]

    if request.endpoints:
        for i, ep in enumerate(request.endpoints, 1):
            parts.append(f"  EP{i}: {ep.method.value} {ep.path} — {ep.description or 'N/A'}")

    return "\n".join(parts)


# ─────────────────────────────────────────────
# Prompts — Compact, split into 2 passes
# ─────────────────────────────────────────────

# Pass 1: Core spec (endpoints + DB models) — this is the heavy lift
PROMPT_CORE = """You are a backend architect. Generate a REST API spec as JSON.

{context}

Return ONLY valid JSON (no markdown, no commentary). Structure:
{{
  "project_name": "{project_name}",
  "base_url": "http://localhost:8000",
  "auth_type": "{auth_type}",
  "auth_instructions": "short auth setup guide",
  "overview": "1-2 sentence architecture overview",
  "database_setup": "SQL CREATE TABLE statements as a string",
  "database_models": "Complete ORM models file as a string",
  "endpoints": [
    {{
      "path": "/resource",
      "method": "GET",
      "summary": "short summary",
      "description": "what it does",
      "request_schema": [{{"name": "field", "type": "string", "description": "..."}}],
      "response_schema": [{{"name": "field", "type": "string", "description": "..."}}],
      "sample_response": {{"example": "data"}},
      "code_example": "frontend fetch function as string",
      "database_code": "backend route handler as string",
      "status_codes": {{"200": "OK", "404": "Not found"}}
    }}
  ],
  "setup_instructions": "how to run the server"
}}

Generate exactly {num_endpoints} endpoints. All code fields must be strings. Return ONLY the JSON object."""

# Pass 2: Test cases — lightweight follow-up
PROMPT_TESTS = """Given these API endpoints, generate test cases as a JSON array.

Endpoints:
{endpoint_summary}

Return ONLY a JSON array (no markdown, no commentary):
[
  {{
    "name": "test_function_name",
    "endpoint": "/path",
    "method": "GET",
    "description": "what the test validates",
    "expected_status": 200,
    "assertions": ["response has correct fields", "status code is 200"],
    "code": "complete runnable {code_language} test function as a string"
  }}
]

Generate one test per endpoint. All code must be strings. Return ONLY the JSON array."""


# ─────────────────────────────────────────────
# Generation Pipeline
# ─────────────────────────────────────────────

def _invoke_raw(llm, prompt_template: str, variables: dict) -> str:
    """Invoke LLM with raw text output (no tool/function calling)."""
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke(variables)


def _invoke_structured(llm, prompt_template: str, variables: dict) -> dict:
    """Invoke LLM with Pydantic structured output (Gemini only)."""
    prompt = ChatPromptTemplate.from_template(prompt_template)
    structured_llm = llm.with_structured_output(APIDocumentation)
    chain = prompt | structured_llm
    result = chain.invoke(variables)
    return result.model_dump()


def _generate_with_provider(
    provider_name: str,
    llm,
    use_structured: bool,
    request: APIGenieRequest,
    context: str,
) -> Tuple[dict, str]:
    """Run the 2-pass generation pipeline for a single provider.

    Pass 1: Generate core spec (endpoints + DB models)
    Pass 2: Generate test cases separately (smaller payload, faster)

    Returns: (doc_dict, raw_json_string)
    """
    variables = {
        "context": context,
        "project_name": request.project_name,
        "auth_type": request.auth_type.value,
        "code_language": request.code_language.value,
        "num_endpoints": request.num_endpoints,
    }

    # ── Pass 1: Core spec ──
    if use_structured:
        # Gemini: structured output works fine
        logger.info("[%s] Pass 1/2: Core spec (structured output)", provider_name)
        doc_dict = _invoke_structured(llm, PROMPT_CORE, variables)
    else:
        # Groq: raw text → manual JSON parse
        logger.info("[%s] Pass 1/2: Core spec (raw text → JSON parse)", provider_name)
        raw_core = _invoke_raw(llm, PROMPT_CORE, variables)
        raw_json = _extract_json(raw_core)
        doc_dict = _validate_doc(raw_json)

    # ── Pass 2: Test cases (always raw text — small payload) ──
    endpoint_summary = "\n".join(
        f"- {ep.get('method', 'GET')} {ep.get('path', '/')} — {ep.get('summary', '')}"
        for ep in doc_dict.get("endpoints", [])
    )

    if endpoint_summary:
        logger.info("[%s] Pass 2/2: Test cases", provider_name)
        try:
            raw_tests = _invoke_raw(llm, PROMPT_TESTS, {
                "endpoint_summary": endpoint_summary,
                "code_language": request.code_language.value,
            })
            test_list = _extract_json_array(raw_tests)
            doc_dict["test_cases"] = _normalise_test_cases(test_list)
        except Exception as e:
            logger.warning("[%s] Test generation failed (non-fatal): %s", provider_name, e)
            # Keep whatever test_cases came from pass 1 (if any)

    raw_response = json.dumps(doc_dict, indent=2)
    return doc_dict, raw_response


def _extract_json_array(text: str) -> list:
    """Extract a JSON array from raw LLM text."""
    text = text.strip()

    # Try direct parse
    if text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Try markdown code block
    md_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Find outermost [ ... ]
    bracket_start = text.find("[")
    if bracket_start != -1:
        bracket_end = text.rfind("]")
        if bracket_end > bracket_start:
            try:
                return json.loads(text[bracket_start:bracket_end + 1])
            except json.JSONDecodeError:
                pass

    logger.warning("Could not extract JSON array from test generation output")
    return []


def _normalise_test_cases(tests: list) -> list:
    """Ensure test cases have all required fields."""
    result = []
    for tc in tests:
        if not isinstance(tc, dict):
            continue
        result.append({
            "name": tc.get("name", "test_unnamed"),
            "endpoint": tc.get("endpoint", "/"),
            "method": tc.get("method", "GET"),
            "description": tc.get("description", ""),
            "expected_status": int(tc.get("expected_status", 200)),
            "assertions": tc.get("assertions", []),
            "code": str(tc.get("code", "")),
        })
    return result


# ─────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────

def generate_api_spec(request: APIGenieRequest) -> Tuple[dict, str, float, str, bool]:
    """Generate API spec from request.

    Returns:
        (doc_dict, raw_json, latency_ms, provider_name, from_cache)
    """
    # ── Cache check ──
    cached = _cache.get(request)
    if cached is not None:
        doc_dict, raw_text, provider = cached
        logger.info("Cache HIT — returning cached result (0ms)")
        return doc_dict, raw_text, 0.0, provider, True

    # ── Build context ──
    context = build_context(request)

    # ── Try providers in order (fallback chain) ──
    last_error = None
    for provider_name, factory, use_structured in _PROVIDERS:
        try:
            logger.info("Trying LLM provider: %s (structured=%s)", provider_name, use_structured)
            t0 = time.perf_counter()

            llm = factory()
            doc_dict, raw_response = _generate_with_provider(
                provider_name, llm, use_structured, request, context
            )

            latency_ms = (time.perf_counter() - t0) * 1000

            # ── Validate result has content ──
            if not doc_dict.get("endpoints"):
                raise ValueError("LLM returned empty endpoints list")

            # ── Populate cache ──
            _cache.put(request, doc_dict, raw_response, provider_name)

            logger.info(
                "Generation complete via %s — %d endpoints, %d tests in %.0fms",
                provider_name,
                len(doc_dict.get("endpoints", [])),
                len(doc_dict.get("test_cases", [])),
                latency_ms,
            )
            return doc_dict, raw_response, latency_ms, provider_name, False

        except EnvironmentError:
            logger.warning("Provider %s unavailable (missing API key), trying fallback", provider_name)
            continue
        except Exception as e:
            logger.error("Provider %s failed: %s", provider_name, str(e))
            last_error = e
            continue

    raise ValueError(f"All LLM providers failed. Last error: {last_error}")