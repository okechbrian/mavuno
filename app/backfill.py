"""Backfill script for Mavuno Protocol.

Migrates data from legacy 'farms' and 'buyers' tables to the new 
SQLAlchemy-managed 'users', 'farmer_profiles', and 'buyer_profiles' tables.
"""
import sqlite3
from sqlalchemy.orm import Session
from sqlalchemy import select
from .database import engine, DB_PATH, SessionLocal
from .models import User, FarmerProfile, BuyerProfile
from .config import DATA_DIR
import os

def backfill():
    print(f"Starting backfill from {DB_PATH}...")
    
    # Connect directly via sqlite3 to read legacy tables
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    legacy_cur = conn.cursor()

    db: Session = SessionLocal()
    
    try:
        # 1. Backfill Farmers
        legacy_cur.execute("SELECT * FROM farms")
        farms = legacy_cur.fetchall()
        print(f"Found {len(farms)} legacy farmers.")
        
        for f in farms:
            # Check if user already exists
            existing_user = db.execute(select(User).where(User.id == f["id"])).scalar_one_or_none()
            if not existing_user:
                print(f"  Migrating Farmer: {f['id']} ({f['farmer_name']})")
                # Create User
                user = User(
                    id=f["id"],
                    phone=f["phone"],
                    role="farmer",
                    password_hash="1234", # Default legacy PIN
                    is_active=True
                )
                db.add(user)
                
                # Create Profile
                profile = FarmerProfile(
                    user_id=f["id"],
                    farmer_name=f["farmer_name"],
                    district=f["district"],
                    crop=f["crop"],
                    acres=f["acres"],
                    lat=f["lat"],
                    lng=f["lng"],
                    collection_hub=f["collection_hub"],
                    discipline=f.get("discipline", 1.0),
                    drought_factor=f.get("drought_factor", 1.0)
                )
                db.add(profile)
            else:
                print(f"  Farmer {f['id']} already exists, skipping.")

        # 2. Backfill Buyers
        legacy_cur.execute("SELECT * FROM buyers")
        buyers = legacy_cur.fetchall()
        print(f"Found {len(buyers)} legacy buyers.")
        
        for b in buyers:
            existing_user = db.execute(select(User).where(User.id == b["id"])).scalar_one_or_none()
            if not existing_user:
                print(f"  Migrating Buyer: {b['id']} ({b['name']})")
                # Create User
                user = User(
                    id=b["id"],
                    phone=b["contact"], # Using contact as unique phone identifier
                    role="buyer",
                    password_hash="1234",
                    is_active=True
                )
                db.add(user)
                
                # Create Profile
                profile = BuyerProfile(
                    user_id=b["id"],
                    name=b["name"],
                    region=b["region"],
                    crops_json=b["crops_json"],
                    floor_ugx=b["floor_ugx"],
                    radius_km=b["radius_km"],
                    lat=b["lat"],
                    lng=b["lng"]
                )
                db.add(profile)
            else:
                print(f"  Buyer {b['id']} already exists, skipping.")

        # 3. Create Default Agent
        agent_id = "admin"
        existing_agent = db.execute(select(User).where(User.id == agent_id)).scalar_one_or_none()
        if not existing_agent:
            print("  Creating default SACCO Agent...")
            agent = User(
                id=agent_id,
                phone="+256700000000",
                role="agent",
                password_hash="mavuno2026",
                is_active=True
            )
            db.add(agent)

        db.commit()
        print("Backfill complete successfully.")
        
    except Exception as e:
        print(f"Error during backfill: {e}")
        db.rollback()
    finally:
        db.close()
        conn.close()

if __name__ == "__main__":
    backfill()

