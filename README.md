# ⚡ API-Genie — AI-Powered API Mock & Documentation Generator

> Describe your API in plain English → get production-ready specs, mock data, DB models, tests, and PDF docs in seconds.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       React + Vite (SPA)                     │
│  Dashboard → Prompt Form → Endpoint Cards → Code Viewer      │
└──────────────────────┬───────────────────────────────────────┘
                       │  POST /generate
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (v2.0)                     │
│                                                              │
│  ┌─────────────┐  ┌────────────┐  ┌──────────────────────┐  │
│  │  Timing MW  │→ │ Rate Limit │→ │  Input Sanitisation  │  │
│  │ (X-Resp-Ms) │  │ 10/min/IP  │  │  (2000 char cap)     │  │
│  └─────────────┘  └────────────┘  └──────────┬───────────┘  │
│                                               │              │
│  ┌────────────────────────────────────────────▼───────────┐  │
│  │              LRU Cache (64 entries)                     │  │
│  │  SHA-256 key = f(description, auth, lang, endpoints)   │  │
│  │  Cache hit → <1ms response                             │  │
│  └───────────┬──────────────────────────┬────────────────┘  │
│              │ miss                      │ hit → return     │
│  ┌───────────▼──────────────────────────────────────────┐   │
│  │     2-Pass Generation Pipeline (per provider)         │   │
│  │                                                       │   │
│  │  Pass 1: Core spec (endpoints + DB models)            │   │
│  │    Groq  → Raw text + JSON extraction                 │   │
│  │    Gemini → Pydantic structured output                │   │
│  │                                                       │   │
│  │  Pass 2: Test cases (lightweight follow-up)           │   │
│  │    Both → Raw text + JSON array extraction             │   │
│  │                                                       │   │
│  │  Fallback: Groq ──fail──→ Gemini (auto)               │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 🚀 Features

| Feature | Implementation |
|---|---|
| **Natural Language → API Spec** | 2-pass pipeline: raw text + JSON extraction (Groq) / Pydantic structured output (Gemini) |
| **Dual-Provider Fallback** | Groq (primary) → Google Gemini (secondary) with automatic failover |
| **In-Memory LRU Cache** | SHA-256 keyed, 64-entry bounded cache — repeat queries return in <1ms |
| **Per-Request Latency Tracking** | `X-Response-Time-Ms` header on every response + `latency_ms` in JSON body |
| **Rate Limiting** | 10 requests/min per IP — prevents abuse without external dependencies |
| **Input Sanitisation** | Description capped at 2000 chars, whitespace stripped |
| **Structured Logging** | Python `logging` with timestamps, severity levels, and request context |
| **Health Endpoint** | `/health` returns uptime, cache hit-rate, and provider availability |
| **Professional PDF Export** | ReportLab-based dark-themed API documentation generator |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19 + Vite 8, React Router v6 |
| **Backend** | FastAPI (Python 3.10+), Starlette Middleware |
| **AI Engine** | Groq (Llama 3.3 70B) + Google Gemini 2.5 Flash via LangChain |
| **Data Validation** | Pydantic v2 (structured output binding) |
| **PDF Engine** | ReportLab |
| **Caching** | Custom in-memory LRU (OrderedDict) |

---

## 📦 Installation

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Configure your `.env`:
```env
GROQ_API_KEY=your_groq_api_key
GOOGLE_API_KEY=your_google_api_key   # optional fallback
```

### Frontend
```bash
cd frontend
npm install
```

---

## 🚀 Running

### Backend (API Server)
```bash
cd backend
uvicorn app:app --reload
```
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health: [http://localhost:8000/health](http://localhost:8000/health)

### Frontend (UI)
```bash
cd frontend
npm run dev
```
- UI: [http://localhost:5173](http://localhost:5173)

---

## 📂 Project Structure

```
API-Genie/
├── backend/
│   ├── app.py              # FastAPI app — middleware, rate limiting, routes
│   ├── report.py           # LLM orchestration — cache, fallback, generation
│   ├── models.py           # Pydantic v2 schemas (input + output)
│   ├── pdf_generator.py    # ReportLab PDF renderer
│   ├── requirements.txt    # Python dependencies
│   └── .env                # API keys (gitignored)
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main generation UI
│   │   ├── Dashboard.jsx   # Landing page
│   │   ├── App.css         # Component styles (dark theme)
│   │   ├── Dashboard.css   # Dashboard styles
│   │   ├── index.css       # Global design tokens
│   │   └── main.jsx        # React Router entry point
│   ├── index.html          # HTML template
│   └── package.json        # Node dependencies
└── README.md
```

---

## 📝 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Root — service info |
| `GET` | `/health` | Health check with uptime, cache stats, provider status |
| `POST` | `/generate` | Generate API specification from natural language prompt |

### Response Metadata
Every `/generate` response includes:
```json
{
  "latency_ms": 4231.07,
  "llm_provider": "groq/llama-3.3-70b",
  "cached": false
}
```