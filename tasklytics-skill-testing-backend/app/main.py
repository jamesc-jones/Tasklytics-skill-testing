from dotenv import load_dotenv
from sqlalchemy import text
import time

load_dotenv()

import os
import sentry_sdk

# Inert if SENTRY_DSN is unset/empty - sentry_sdk.init(dsn=None) is a documented
# no-op (no events captured, no network calls), so this is safe to ship before
# a real DSN exists. See docs/PHASE_5_EXECUTION_TRACKER.md for setup steps.
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN") or None,
    traces_sample_rate=0.0,
)

from fastapi import FastAPI
from app.routes import auth, tasks, admin, analytics
from app.database import Base, engine

from app.ai.routes import router as ai_router

from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat

app = FastAPI(
    title="Tasklytics API",
    description="Task management backend with JWT auth",
    version="1.0.0",
    # nginx proxies /api/ -> this app's root, stripping the /api prefix before
    # forwarding (see nginx/default.conf's `location /api/`). This app never
    # sees that prefix in scope["path"], so route matching is unaffected - but
    # without root_path set, FastAPI generates self-referencing URLs (Swagger
    # UI's embedded openapi.json fetch, the OpenAPI schema's `servers` entry)
    # as root-relative, ignoring the proxy prefix. That breaks /api/docs: the
    # page loads, then tries to fetch /openapi.json (no /api prefix), which
    # hits nginx's frontend catch-all instead of this backend. root_path fixes
    # URL *generation* only; it does not change how incoming requests match
    # routes.
    root_path="/api",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tasklytics2ai.com",
        "https://www.tasklytics2ai.com",
        "http://159.203.26.144",
        "http://www.159.203.26.144",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# This creates the tables
Base.metadata.create_all(bind=engine)

# Register routes
app.include_router(auth.router)
app.include_router(tasks.router)

app.include_router(admin.router)

app.include_router(analytics.router)

app.include_router(ai_router)

app.include_router(chat.router)

@app.get("/")
def root():
    return {"message": "Tasklytics Backend API running!"}

@app.get("/health")
def health_check():
    try:
        # Check database connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "service": "tasklytics-backend",
            "database": "connected",
            "timestamp": time.time()
        }

    except Exception as e:
        return {
            "status": "error",
            "service": "tasklytics-backend",
            "database": "disconnected",
            "error": str(e)
        }

# Testing PR Skill