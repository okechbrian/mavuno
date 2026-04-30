"""Production-grade seeding script for Mavuno Yield."""
import os
import sys
import hmac
import hashlib
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal, init_db
from app.models import User, FarmerProfile, BuyerProfile, TrainingModule
from app.config import HMAC_SECRET

def seed():
    # Ensure tables exist
    init_db()
    
    db: Session = SessionLocal()
    try:
        # 1. Seed Training Modules
        modules_data = [
            ("TM-01", "Regenerative Mushroom Cultivation", "Learn high-yield, zero-waste oyster mushroom techniques.", "Mushrooms", 150),
            ("TM-02", "Precision Logistics with Trade Priority", "Optimize your harvest collection using Mavuno's Yield Priorities.", "Logistics", 100),
            ("TM-03", "Marketplace Best Practices", "Build buyer trust through accurate listings and verified harvests.", "Business", 80),
            ("TM-04", "Organic Fertilizer Production", "Turn farm waste into high-quality compost and liquid fertilizer.", "Sustainability", 120),
        ]
        
        for mid, title, desc, cat, xp in modules_data:
            existing = db.query(TrainingModule).filter(TrainingModule.id == mid).first()
            if not existing:
                m = TrainingModule(id=mid, title=title, description=desc, category=cat, xp_reward=xp)
                db.add(m)
        
        # 2. Seed Default Admin/Agent
        # Using the default password hash logic from main.py if needed, 
        # but the agent is handled specially in main.py via comparison.
        # However, for a unified user table, we might want it here.
        admin_id = "admin"
        existing_admin = db.query(User).filter(User.id == admin_id).first()
        if not existing_admin:
            # We don't hash the agent password because main.py compares it directly to env
            # But for other users, we use the PIN as password_hash for the prototype.
            admin = User(id=admin_id, phone="000", role="agent", password_hash="mavuno2026")
            db.add(admin)

        # 3. Seed Demo Buyer
        buyer_id = "BY-MBALE-01"
        existing_buyer = db.query(User).filter(User.id == buyer_id).first()
        if not existing_buyer:
            buyer_user = User(id=buyer_id, phone="256700111222", role="buyer", password_hash="1234")
            db.add(buyer_user)
            
            buyer_profile = BuyerProfile(
                user_id=buyer_id,
                name="Mbale Coffee Cooperative",
                region="Mbale",
                crops_json='["coffee", "beans"]',
                floor_ugx=4500,
                lat=1.08,
                lng=34.18
            )
            db.add(buyer_profile)

        # 4. Seed Demo Farmer
        farmer_id = "UG-MBL-DEMO"
        existing_farmer = db.query(User).filter(User.id == farmer_id).first()
        if not existing_farmer:
            farmer_user = User(id=farmer_id, phone="256777000111", role="farmer", password_hash="1234")
            db.add(farmer_user)
            
            farmer_profile = FarmerProfile(
                user_id=farmer_id,
                farmer_name="Akello Rose",
                district="Mbale",
                crop="coffee",
                acres=2.5,
                lat=1.10,
                lng=34.20,
                collection_hub="Aggregation-Hub-01"
            )
            db.add(farmer_profile)

        db.commit()
        print("✅ Seeding completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
