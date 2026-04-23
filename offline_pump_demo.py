"""
Mavuno - Offline Solar Pump Verification Demo (Future Makers 2026)

This script proves that a remote solar pump can mathematically verify an 
Energy Credit without needing an internet connection to the central database.
This is the core innovation that makes the $500B economy possible in deep rural areas.
"""
import hmac
import hashlib

# 1. The Burned-in Secret (lives on the pump's secure hardware enclave)
PUMP_SECRET = b"future-makers-hackathon-2026-secret-key"

def verify_offline(token_id: str, farm_id: str, kwh: int, timestamp: str, signature: str):
    print("==================================================")
    print("🔌 PUMP NODE TERMINAL (UG-MBL-001)")
    print("📡 Network Status: OFFLINE (No GSM Signal)")
    print("==================================================")
    print(f"Farmer inputs Token: {token_id}")
    print(f"Claiming: {kwh} kWh")
    print("Verifying cryptographic signature locally...\n")
    
    # The pump recreates the cryptographic message
    msg = f"{token_id}:{farm_id}:{kwh}:{timestamp}"
    
    # The pump hashes it using its own offline copy of the secret key
    expected_sig = hmac.new(PUMP_SECRET, msg.encode(), hashlib.sha256).hexdigest()
    
    if hmac.compare_digest(expected_sig, signature):
        print("✅ [SUCCESS] Signature mathematically verified!")
        print("💧 [ACTION] Activating pump. Dispensing water...\n")
    else:
        print("❌ [FAILED] Forged token detected!")
        print("🔒 [ACTION] Water locked.\n")

if __name__ == "__main__":
    print("\n--- MAVUNO JUDGE DEMO: OFFLINE VERIFICATION ---")
    
    # Simulate a token issued by the Cloud
    demo_token = "ECT-A1B2C3"
    demo_farm = "UG-MBL-0001"
    demo_kwh = 60
    demo_ts = "1710000000" # Static timestamp for demo
    
    # The cloud signs it
    cloud_msg = f"{demo_token}:{demo_farm}:{demo_kwh}:{demo_ts}"
    cloud_sig = hmac.new(PUMP_SECRET, cloud_msg.encode(), hashlib.sha256).hexdigest()
    
    # 1. Test Valid Token
    print("\nTest 1: Valid Token presented at offline pump.")
    verify_offline(demo_token, demo_farm, demo_kwh, demo_ts, cloud_sig)
    
    # 2. Test Forged Token (Farmer tries to claim 100 kWh instead of 60)
    print("\nTest 2: Farmer alters SMS to steal 100 kWh.")
    verify_offline(demo_token, demo_farm, 100, demo_ts, cloud_sig)
