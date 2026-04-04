"""
models.py — Pydantic schemas for FIU Report Generator API
Input mirrors the Fraud Detection API output JSON structure.
Output mirrors the official FIU-IND STR format.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class Decision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


# ─────────────────────────────────────────────
# Graph Models
# ─────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str


class GraphEdge(BaseModel):
    source: str
    target: str
    amount: Optional[float] = None


class Graph(BaseModel):
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []


# ─────────────────────────────────────────────
# Transaction Check Result ( POST /check-transaction )
# ─────────────────────────────────────────────

class TransactionCheckResult(BaseModel):
    account: str = Field(..., description="Account identifier being checked")
    decision: Decision = Field(..., description="ALLOW, REVIEW, or BLOCK")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    final_score: float = Field(..., description="Final composite fraud risk score")
    patterns_detected: List[str] = Field(default=[], description="List of fraud patterns flagged")
    graph: Optional[Graph] = Field(default=None, description="Transaction relationship graph")


# ─────────────────────────────────────────────
# Fraud Network ( GET /detect-fraud-network )
# ─────────────────────────────────────────────

class FraudNetworkResult(BaseModel):
    message: str
    graph: Graph


# ─────────────────────────────────────────────
# Generic Pattern Result ( GET /detect-pattern/{pattern_type} )
# ─────────────────────────────────────────────

class PatternResult(BaseModel):
    pattern: str = Field(..., description="Pattern type name")
    results: List[Dict[str, Any]] = Field(default=[], description="Pattern detection results")


# ─────────────────────────────────────────────
# Geographic Anomaly ( GET /detect-geo-anomaly )
# ─────────────────────────────────────────────

class GeoAnomalyEntry(BaseModel):
    account: str
    usual_location: str
    anomalous_locations: List[str] = []
    anomaly_count: int


class GeoAnomalyResult(BaseModel):
    pattern: str = "geographic_anomaly"
    results: List[GeoAnomalyEntry] = []


# ─────────────────────────────────────────────
# Master FIU Report Request (The user's input format)
# ─────────────────────────────────────────────

class FIUReportRequest(BaseModel):
    """
    Input schema directly accepting results from the Fraud Detection API endpoints.
    """
    case_id: Optional[str] = None
    analyst_name: Optional[str] = "AI Auditor"
    
    # Metadata for Official Report
    reporting_entity_name: Optional[str] = Field(default="Financial Institution", description="Name of the bank/entity")
    principal_officer_name: Optional[str] = Field(default="Compliance Officer", description="Name of the PMLA officer")
    
    # Inputs from Fraud Detection API
    transaction_data: Optional[TransactionCheckResult] = None
    fraud_network: Optional[FraudNetworkResult] = None
    patterns: Optional[List[PatternResult]] = None
    geo_anomalies: Optional[GeoAnomalyResult] = None


# ─────────────────────────────────────────────
# FIU-IND Official Output Format
# ─────────────────────────────────────────────

class FIUReport(BaseModel):
    case_id: str
    report_date: str
    report_type: str = "Suspicious Transaction Report (STR)"
    risk_level: str  # CRITICAL, HIGH, MEDIUM, LOW
    
    # Required Sections per FIU-IND
    reporting_entity_details: str    # Section 1
    principal_officer_details: str   # Section 2
    reason_for_suspicion: str        # Section 3 (Crucial Narrative)
    transaction_details: str        # Section 4
    linked_person_details: str      # Section 5
    
    # Supplementary Analysis
    pattern_analysis: str
    network_analysis: str
    geographic_analysis: str
    risk_assessment: str
    recommended_actions: str
    regulatory_references: str
    tipping_off_confirmation: str  # Acknowledging non-disclosure


class FIUReportResponse(BaseModel):
    success: bool
    case_id: str
    report_type: str
    report: FIUReport
    raw_report_text: str
    generated_at: str
