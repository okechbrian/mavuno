"""Database management for Mavuno Protocol.

This module handles both legacy connections and the new 
SQLAlchemy 2.0 session management with support for PostgreSQL.
"""
import json
import time
import random
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, select
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

def seed_from_json(db: Session):
    """Populates the DB from JSON assets if empty."""
    from .models import User, FarmerProfile, BuyerProfile
    from .config import DATA_DIR
    import json

    # 1. Seed Farmers
    if db.execute(select(User).where(User.role == "farmer")).first() is None:
        path = DATA_DIR / "farms.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                for fid, info in data.items():
                    user = User(id=fid, phone=info["phone"], role="farmer", password_hash="1234")
                    db.add(user)
                    profile = FarmerProfile(
                        user_id=fid, farmer_name=info["farmer_name"], district=info["district"],
                        crop=info["crop"], acres=info["acres"], lat=info["gps"]["lat"], lng=info["gps"]["lng"],
                        discipline=info.get("discipline", 1.0), drought_factor=info.get("drought_factor", 1.0)
                    )
                    db.add(profile)
            print(f"Seeded {len(data)} farmers from JSON.")

    # 2. Seed Buyers
    if db.execute(select(User).where(User.role == "buyer")).first() is None:
        path = DATA_DIR / "buyers.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                for bid, info in data.items():
                    user = User(id=bid, phone=info["contact"], role="buyer", password_hash="1234")
                    db.add(user)
                    profile = BuyerProfile(
                        user_id=bid, name=info["name"], region=info["region"],
                        crops_json=info["crops_json"], floor_ugx=info["floor_ugx"],
                        radius_km=info.get("radius_km", 50.0), lat=info["lat"], lng=info["lng"]
                    )
                    db.add(profile)
            print(f"Seeded {len(data)} buyers from JSON.")
    
    db.commit()


if __name__ == "__main__":
    migrate_seed_data()
