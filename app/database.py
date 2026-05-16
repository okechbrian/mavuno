"""Database management for Mavuno Protocol.

This module handles both legacy connections and the new 
SQLAlchemy 2.0 session management with support for PostgreSQL.
"""
import json
import time
import random
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .config import DB_PATH, DATABASE_URL
from .models import Base

# SQLAlchemy Setup
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session() -> Generator[Session, None, None]:
    """Modern SQLAlchemy session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initializes the database, creating all tables from SQLAlchemy models."""
    Base.metadata.create_all(bind=engine)

def reset_db():
    """Drops all tables and recreates them. Use with caution!"""
    Base.metadata.drop_all(bind=engine)
    init_db()

def migrate_seed_data():
    """Seeds the database with initial prototype data."""
    init_db()
    # Seeding logic is now delegated to training.seed_training_data or a dedicated script
    print("Database Schema Synchronized.")


if __name__ == "__main__":
    migrate_seed_data()
