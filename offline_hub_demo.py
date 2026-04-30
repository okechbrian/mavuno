"""
Mavuno - Offline Collection Hub Verification Demo (Mavuno)

This script proves that a remote collection hub can mathematically verify a 
Trade Priority without needing an internet connection to the central database.
This is the core innovation that makes the $500B economy possible in deep rural areas.
"""
import hmac
import hashlib

# 1. The Burned-in Secret (lives on the hub's secure hardware enclave)
HUB_SECRET = b"future-makers-hackathon-2026-secret-key"

def verify_offline(priority_id: str, farm_id: str, kg: int, timestamp: str, signature: str):
    print("==================================================")
    print("🔌 COLLECTION HUB TERMINAL (UG-MBL-001)")
    print("📡 Network Status: OFFLINE (No GSM Signal)")
    print("==================================================")
    print(f"Farmer inputs Priority ID: {priority_id}")
    print(f"Claiming: {kg} KG")
    print("Verifying cryptographic signature locally...\n")
    
    # The hub recreates the cryptographic message
    msg = f"{priority_id}:{farm_id}:{kg}:{timestamp}"
    
    # The hub hashes it using its own offline copy of the secret key
    expected_sig = hmac.new(HUB_SECRET, msg.encode(), hashlib.sha256).hexdigest()
    
    if hmac.compare_digest(expected_sig, signature):
        print("✅ [SUCCESS] Signature mathematically verified!")
        print("🚛 [ACTION] Activating collection sequence. Accepting produce...\n")
    else:
        print("❌ [FAILED] Forged priority detected!")
        print("🔒 [ACTION] Intake locked.\n")

if __name__ == "__main__":
    print("\n--- MAVUNO YIELD: OFFLINE VERIFICATION ---")
    
    # Simulate a priority issued by the Cloud
    demo_priority = "YPS-A1B2C3"
    demo_farm = "UG-MBL-0001"
    demo_kg = 60
    demo_ts = "1710000000" # Static timestamp for demo
    
    # The cloud signs it
    cloud_msg = f"{demo_priority}:{demo_farm}:{demo_kg}:{demo_ts}"
    cloud_sig = hmac.new(HUB_SECRET, cloud_msg.encode(), hashlib.sha256).hexdigest()
    
    # 1. Test Valid Priority
    print("\nTest 1: Valid Priority presented at offline hub.")
    verify_offline(demo_priority, demo_farm, demo_kg, demo_ts, cloud_sig)
    
    # 2. Test Forged Priority (Farmer tries to claim 100 KG instead of 60)
    print("\nTest 2: Farmer alters SMS to steal 100 KG.")
    verify_offline(demo_priority, demo_farm, 100, demo_ts, cloud_sig)
