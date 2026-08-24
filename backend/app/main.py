"""
Forest Guard / Van-Chetna Backend
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.database import init_db
from app.routes import events, alerts, nodes, websocket, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables if they don't exist
    await init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Forest Guard Backend",
    description="AI + IoT Forest Threat Intelligence API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(events.router, tags=["Events"])
app.include_router(alerts.router, tags=["Alerts"])
app.include_router(nodes.router, tags=["Nodes"])
app.include_router(websocket.router, tags=["WebSocket"])
app.include_router(health.router, tags=["Health"])
