# ⚡ API-Genie — AI-Powered API Mock & Documentation Generator

Describe your API in plain English and instantly get:
- **Complete REST API specification** with realistic mock data
- **Professional PDF documentation** (Stripe-style)
- **Pytest test suite** ready to run against your real backend

---

## 🚀 Features

- **Natural Language Input**: Just describe what API you need — no OpenAPI writing required.
- **AI-Generated Specs**: Endpoints, schemas, sample data, and status codes — all production-ready.
- **Professional PDF Docs**: Download a dark-themed, fully-formatted API integration guide.
- **Auto Test Suite**: Get pytest-compatible test definitions generated for every endpoint.
- **Multiple Auth Types**: Bearer Token, API Key, Basic Auth, or No Auth.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React + Vite |
| **Backend** | FastAPI (Python 3.9+) |
| **AI Engine** | Groq (Llama 3.3 70B) + LangChain |
| **PDF Engine** | ReportLab |
| **Data Validation** | Pydantic v2 |

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
│   ├── app.py              # FastAPI application & endpoints
│   ├── report.py           # AI engine (Groq + LangChain)
│   ├── models.py           # Pydantic schemas
│   ├── pdf_generator.py    # ReportLab PDF renderer
│   ├── requirements.txt    # Python dependencies
│   └── .env                # API keys
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main React component
│   │   ├── App.css         # Dark theme styles
│   │   ├── index.css       # Global styles
│   │   └── main.jsx        # Entry point
│   ├── index.html          # HTML template
│   └── package.json        # Node dependencies
└── README.md
```

---

## 📝 API Endpoints

### `POST /generate`
Generates the API specification in JSON format.

### `POST /generate/pdf`
Generates and returns the API documentation as a downloadable PDF.

### `GET /health`
Health check endpoint.
