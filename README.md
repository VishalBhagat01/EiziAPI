# 🏦 FIU-IND Report Generator API (Powered by Groq)

An AI-powered system that generates official **Suspicious Transaction Reports (STR)** in compliance with **FIU-IND (Financial Intelligence Unit – India)** standards. This API consumes transaction risk data and uses **Groq (Llama-3.3-70b-versatile)** via **LangChain** to produce professional STR reports.

---

## 🚀 Features

- **Official FIU-IND Format**: Generates reports containing all mandatory sections (Section 1-5) as per PMLA 2002.
- **Powered by Groq**: High-performance reasoning using **Llama 3.3 70B** for lightning-fast report generation.
- **AI-Powered Narrative**: Automatically builds the "Reason for Suspicion" and "Linked Persons" narratives from raw transaction data.
- **Multi-Source Data Ingestion**: Supports outputs from:
    - `/check-transaction`: Patterns, risk scores, and account data.
    - `/detect-fraud-network`: Graph-based network analysis.
    - `/detect-pattern`: Specific patterns like Smurfing, Velocity, and Round-tripping.
    - `/detect-geo-anomaly`: Geographic location risks.
- **Professional PDF Generation**: Renders reports into a courtroom-ready PDF with branding and risk indicators.
- **Privacy & Compliance**: Instructs the AI not to disclose investigations (Tipping-off confirmation).

---

## 🛠️ Tech Stack

- **Framework**: FastAPI (Python 3.9+)
- **GenAI Engine**: Groq (Llama-3.3-70b-versatile) + LangChain
- **PDF Engine**: ReportLab
- **Data Validation**: Pydantic v2

---

## 📦 Installation

1.  **Clone the project** and ensure your virtual environment is active.
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure API Keys**:
    Edit your `.env` file with your Groq API Key:
    ```env
    GROQ_API_KEY=your_groq_api_key
    ```

---

## 🚀 Running the API

Start the server using `uvicorn`:

```bash
uvicorn app:app --reload
```

- **Interactive API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 📝 API Endpoints

### 1. `POST /generate-fiu-report`
Generates the report in a structured JSON format.

### 2. `POST /generate-fiu-report/pdf`
Generates and returns the report as a downloadable **PDF file**.

### 3. `POST /generate-fiu-report/both`
Returns the JSON and a link/instruction to download the PDF.

---

## 📂 Project Structure

```bash
FIU_Report/
├── app.py              # FastAPI application & endpoints
├── report.py           # GenAI logic (Groq + LangChain)
├── models.py           # Pydantic schemas (Official + Intelligence)
├── pdf_generator.py    # ReportLab PDF rendering
├── requirements.txt    # Project dependencies
├── .env                # API configuration (Groq Key)
└── .gitignore          # Python and environment ignores
```

---

## ⚖️ Legal Note

This generator is designed for Internal Compliance Analysts. Ensure all generated reports are reviewed by the **Principal Officer** before submission to the FINGate 2.0 portal.
