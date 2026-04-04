"""
report.py — LangChain + Google Gemini FIU Official Format Generation Engine
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

from models import FIUReportRequest

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
        temperature=0.2,
        max_tokens=8192,
    )


# ─────────────────────────────────────────────
# Context Builder — converts structured data to natural language
# ─────────────────────────────────────────────

def build_context(request: FIUReportRequest) -> str:
    sections = []

    # ── Transaction Check Data ──
    if request.transaction_data:
        td = request.transaction_data
        graph_info = ""
        if td.graph:
            edge_lines = "\n".join(
                [f"    {e.source} ──[{e.amount}]──▶ {e.target}" for e in td.graph.edges[:15]]
            )
            graph_info = f"""
  Transaction Graph:
    Nodes ({len(td.graph.nodes)}): {', '.join([n.label for n in td.graph.nodes[:10]])}
    Edges ({len(td.graph.edges)}):
{edge_lines}"""

        sections.append(f"""
═══ TRANSACTION RISK ASSESSMENT (POST /check-transaction) ═══
  Primary Account     : {td.account}
  Risk Decision       : {td.decision.value}
  Model Confidence    : {td.confidence:.2%}
  Final Risk Score    : {td.final_score:.6f}
  Patterns Flagged    : {', '.join(td.patterns_detected) if td.patterns_detected else 'None'}
{graph_info}
""")

    # ── Fraud Network ──
    if request.fraud_network:
        fn = request.fraud_network
        node_labels = [n.label for n in fn.graph.nodes[:15]]
        edge_lines = "\n".join(
            [f"    {e.source} ──▶ {e.target}" for e in fn.graph.edges[:15]]
        )
        sections.append(f"""
═══ FRAUD NETWORK TOPOLOGY (GET /detect-fraud-network) ═══
  Status              : {fn.message}
  Total Nodes         : {len(fn.graph.nodes)}
  Total Connections   : {len(fn.graph.edges)}
  Key Accounts        : {', '.join(node_labels)}
  Network Flow:
{edge_lines}
""")

    # ── Pattern Detection Results ──
    if request.patterns:
        pattern_text = "═══ FRAUD PATTERN DETECTION RESULTS ═══\n"
        for pr in request.patterns:
            pattern_text += f"\n  ◆ Pattern: {pr.pattern.upper()}\n"
            for i, result in enumerate(pr.results[:5], 1):
                pattern_text += f"    Instance {i}:\n"
                for k, v in result.items():
                    pattern_text += f"      {k}: {v}\n"
        sections.append(pattern_text)

    # ── Geographic Anomalies ──
    if request.geo_anomalies and request.geo_anomalies.results:
        geo_text = "═══ GEOGRAPHIC ANOMALY ANALYSIS (GET /detect-geo-anomaly) ═══\n"
        for entry in request.geo_anomalies.results:
            geo_text += f"""
  Account             : {entry.account}
  Usual Location      : {entry.usual_location}
  Anomalous Locations : {', '.join(entry.anomalous_locations)}
  Anomaly Count       : {entry.anomaly_count}
"""
        sections.append(geo_text)

    if not sections:
        return "No fraud detection data provided. Please include at least one data source."

    return "\n".join(sections)


# ─────────────────────────────────────────────
# FIU-IND Official Prompt Template
# ─────────────────────────────────────────────

FIU_OFFICIAL_PROMPT = """You are a Senior FIU Analyst specializing in FIU-IND (Financial Intelligence Unit – India) Suspicious Transaction Reports (STRs). Your task is to generate a professional, legally-compliant STR following the official format based on the fraud detection data provided below.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT DATA (Fraud Detection Outputs)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
METADATA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Case ID             : {case_id}
Report Date         : {report_date}
Reporting Entity    : {reporting_entity_name}
Principal Officer   : {principal_officer_name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate a Suspicious Transaction Report (STR) compliant with FIU-IND official guidelines. Ensure the tone is technical, concise, and professional. Use the provided account IDs and risk scores.

Return ONLY a valid JSON object in this exact structure:

{{
  "case_id": "{case_id}",
  "report_date": "{report_date}",
  "report_type": "Suspicious Transaction Report (STR)",
  "risk_level": "CRITICAL/HIGH/MEDIUM/LOW",
  "reporting_entity_details": "Summarize the official reporting entity details (Entity: {reporting_entity_name}). Mention the importance of accurate reporting under PMLA 2002.",
  "principal_officer_details": "Provide details of the Principal Officer managing this filing (Officer: {principal_officer_name}). Mention their role in verifying the suspicion.",
  "reason_for_suspicion": "Official mandatory Section 3: Basis of suspicion. Explain WHY this activity is suspicious using PMLA 2002 definitions (e.g., no economic rationale, unusual complexity).",
  "transaction_details": "Summarize key transactions, amounts, and dates as indicated in the data. Reference specific accounts.",
  "linked_person_details": "Official Section 5: List and describe all linked persons, businesses, and accounts involved in the suspicious chain. Note their roles (e.g., beneficiary, layered account).",
  "pattern_analysis": "Technical breakdown of the fraud patterns detected (e.g., Hub-Relay, SMURFING, Circular, Chain-Laundering). Describe the mechanics based on the provided patterns.",
  "network_analysis": "Describe the network graph topology. Identify the hub/primary suspect accounts and the flow of funds.",
  "geographic_analysis": "Analyze any geographic anomalies (e.g., usual vs anomalous locations) and cross-border transfer risks.",
  "risk_assessment": "Final composite risk assessment. Justify the risk score and the model's confidence in identifying this as money laundering layering.",
  "recommended_actions": "List regulatory actions: filing formal STR with FINGate 2.0, account freeze, enhanced due diligence, law enforcement referral.",
  "regulatory_references": "List applicable PMLA 2002 sections, FATF recommendations (29, 40), and FINnet 2.0 reporting guidelines.",
  "tipping_off_confirmation": "Confirmation statement: 'The reporting entity and the Principal Officer confirm that no tipping-off has occurred. The customer has not been informed about this investigation or the filing of this STR as per Section 3(b) of the PMLA.'"
}}"""

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

def generate_fiu_report(request: FIUReportRequest) -> Tuple[dict, str, str]:
    case_id = request.case_id or f"SAR-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    context = build_context(request)
    
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template(FIU_OFFICIAL_PROMPT)
    chain = prompt | llm | StrOutputParser()

    raw_response = chain.invoke({
        "context": context,
        "case_id": case_id,
        "report_date": report_date,
        "reporting_entity_name": request.reporting_entity_name,
        "principal_officer_name": request.principal_officer_name or "Audit Officer",
    })

    report_dict = extract_json(raw_response)
    return report_dict, raw_response, case_id