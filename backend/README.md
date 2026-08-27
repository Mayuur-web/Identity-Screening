# Parakh Seva — Backend

AI-Powered Identity & Document Verification System backend, built with FastAPI.

## Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`.

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/documents/upload` | Upload a document |
| POST | `/api/documents/analyze` | Trigger document analysis |
| POST | `/api/verification/upload` | Upload document + selfie for verification |
| POST | `/api/verification/analyze` | Run full verification analysis pipeline |
| GET | `/api/verification/{id}` | Get verification details |

## Project Structure

```
backend/
├── app/
│   ├── main.py           # FastAPI application entry point
│   ├── api/routes/       # API route handlers
│   ├── services/         # AI service placeholders (OCR, face, tamper, risk)
│   ├── schemas/          # Pydantic request/response models
│   └── core/             # Configuration and security utilities
├── tests/                # Backend tests
├── uploads/              # Uploaded files (gitignored)
├── requirements.txt
└── .env.example
```

## Testing

```bash
pytest
```

## Status

This is the backend foundation. AI services (OCR, face recognition, tamper detection, risk scoring) are placeholder interfaces that will be implemented in the next phase.
