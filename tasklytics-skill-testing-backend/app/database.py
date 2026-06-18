from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import os

from dotenv import load_dotenv

# Load .env file locally (not in Docker)
if os.getenv("ENV") != "docker":
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Safety check
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # checks connection before using it
        pool_recycle=300,  # refresh connection every 5 minutes
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# This line is critical
# This initializes the database schema based on defined ORM models
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()