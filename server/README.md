# FastAPI Backend Server

A clean, modular, and production-ready Python FastAPI backend server.

---

## 📁 Project Architecture

```
server/
├── app/
│   ├── __init__.py
│   ├── main.py              # Application factory, lifespan, CORS, route registration
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        # Environment settings (Pydantic Settings)
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py       # API v1 router aggregator
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── health.py# Health check endpoint
│   │           └── items.py # CRUD RESTful endpoints
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py        # Generic API models & health schemas
│   │   └── item.py          # Pydantic request / response validation schemas
│   └── services/
│       ├── __init__.py
│       └── item_service.py  # Business logic & repository layer
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures (async HTTP client)
│   └── test_api.py          # Unit & integration test cases
├── .env.example             # Template environment configuration
├── .env                     # Local environment settings
├── .gitignore               # Git ignore rules for Python / FastAPI
├── requirements.txt         # Pinned production and test dependencies
├── run.py                   # Server entrypoint launcher
└── README.md                # Project documentation
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+ (detected Python 3.11)
- Windows PowerShell / Command Prompt or Bash

### 2. Activate Virtual Environment

A dedicated virtual environment has already been created in `server/venv`.

**On Windows (PowerShell):**
```powershell
cd D:\Pramod\azentio\server
.\venv\Scripts\Activate.ps1
```

*(If script execution is disabled in PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, or use `.\venv\Scripts\activate.bat` in CMD).*

### 3. Install Dependencies (Already Pre-installed)

If you modify or update dependencies in the future:
```powershell
pip install -r requirements.txt
```

### 4. Run the Development Server

You can launch the server using either `run.py` or `uvicorn`:

**Option A (Using run script):**
```powershell
python run.py
```

**Option B (Using uvicorn directly):**
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Server will start at:
- **Base URL:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI Schema:** [http://127.0.0.1:8000/api/v1/openapi.json](http://127.0.0.1:8000/api/v1/openapi.json)

---

## 📡 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root greeting & links to documentation |
| `GET` | `/api/v1/health` | Service health status check |
| `GET` | `/api/v1/items/` | List items (supports `skip`, `limit`, `active_only`) |
| `GET` | `/api/v1/items/{id}` | Get item details by ID |
| `POST` | `/api/v1/items/` | Create a new item (with Pydantic validation) |
| `PUT` | `/api/v1/items/{id}` | Update existing item |
| `DELETE` | `/api/v1/items/{id}` | Delete item by ID |

---

## 🧪 Running Tests

Run the test suite with `pytest`:

```powershell
cd D:\Pramod\azentio\server
.\venv\Scripts\pytest -v
```

---

## ⚙️ Configuration (`.env`)

Configuration is managed via `pydantic-settings` in `app/core/config.py`:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PROJECT_NAME` | `FastAPI Backend Server` | Name of the service |
| `API_V1_STR` | `/api/v1` | URL prefix for version 1 API |
| `DEBUG` | `true` | Enable hot-reloading & debug logs |
| `HOST` | `127.0.0.1` | Host address |
| `PORT` | `8000` | Port number |
| `BACKEND_CORS_ORIGINS` | `["http://localhost:3000", ...]` | Allowed CORS origins (JSON array or comma-separated) |

