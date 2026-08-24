# Forest Guard — Backend

FastAPI + PostgreSQL backend for the Forest Guard / Van-Chetna threat intelligence platform.

## Stack

- **FastAPI** — async REST API + WebSocket
- **PostgreSQL** — event store, alerts, node registry
- **SQLAlchemy 2.0** — async ORM
- **Pydantic v2** — request/response validation

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL running locally (or Docker)

### 2. Setup Database

```bash
# Create the database
createdb forest_guard

# Or with Docker:
docker run -d --name forest-guard-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=forest_guard \
  -p 5432:5432 postgres:16
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env if your Postgres credentials differ
```

### 5. Run the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Tables are auto-created on startup.

### 6. Seed Sample Data (optional)

```bash
python seed.py
```

### 7. Run Event Simulator (optional)

Simulates live sensor events for demo/testing without hardware:

```bash
pip install httpx
python simulate.py
```

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/events` | POST | Gateway posts raw LoRa-payload events |
| `/events` | GET | Dashboard fetches recent events |
| `/alerts` | GET | Dashboard fetches fused/scored alerts |
| `/alerts/{id}/acknowledge` | POST | Officer acknowledges an alert |
| `/nodes/status` | GET | Node health info (battery, online/offline) |
| `/ws/live` | WebSocket | Live alert push to dashboard |
| `/health` | GET | Backend health check |

## API Docs

Once running, visit: http://localhost:8000/docs (Swagger UI)

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment config
│   ├── database.py          # SQLAlchemy async engine + session
│   ├── models.py            # ORM models (Node, AcousticEvent, etc.)
│   ├── schemas.py           # Pydantic request/response models
│   ├── fusion.py            # Rule-based threat fusion engine
│   ├── websocket_manager.py # WebSocket broadcast manager
│   └── routes/
│       ├── events.py        # POST/GET /events
│       ├── alerts.py        # GET /alerts, POST /alerts/{id}/acknowledge
│       ├── nodes.py         # GET /nodes/status
│       ├── websocket.py     # /ws/live WebSocket
│       └── health.py        # GET /health
├── seed.py                  # Database seeder
├── simulate.py              # Event simulator for demos
├── requirements.txt
├── .env.example
└── README.md
```
