"""
Mavuno - IoT Sensor Node Telemetry Simulator (Future Makers 2026)

This script simulates a physical soil sensor deployed in a Ugandan farm.
It captures the 7 crucial biological signals and transmits them over a 
simulated GSM connection to the Mavuno protocol's /sensor/telemetry endpoint.
"""
import time
import random
import requests
import sys

# The 7 Crucial Signals
# 1. Soil Moisture (%)
# 2. Temperature (°C)
# 3. Rainfall (mm)
# 4. Humidity (%)
# 5. Nitrogen (mg/kg)
# 6. Phosphorus (mg/kg)
# 7. Potassium (mg/kg)

# Target endpoint of the Mavuno API
API_URL = "http://localhost:8001/sensor/telemetry"

def generate_telemetry(farm_id: str):
    """Simulates a sensor waking up and capturing the 7 soil signals."""
    print(f"\n[Hardware] Sensor Node waking up... (Farm: {farm_id})")
    
    # Simulate slight environmental stress (e.g. moisture dropping, temp rising)
    payload = {
        "farm_id": farm_id,
        "soil_moisture": round(random.uniform(15.0, 25.0), 2),  # Drought stress threshold
        "temp_c": round(random.uniform(28.0, 34.0), 2),         # High temperature
        "rainfall_mm": round(random.uniform(0.0, 2.0), 2),      # Low rainfall
        "humidity_pct": round(random.uniform(40.0, 60.0), 2),
        "n_mg_kg": round(random.uniform(20.0, 40.0), 2),        # Depleting Nitrogen
        "p_mg_kg": round(random.uniform(10.0, 20.0), 2),
        "k_mg_kg": round(random.uniform(150.0, 250.0), 2),
    }
    
    print("[Sensors] Captured 7 Crucial Signals:")
    print(f"  └ Moisture:   {payload['soil_moisture']}%")
    print(f"  └ Temp:       {payload['temp_c']}°C")
    print(f"  └ Rainfall:   {payload['rainfall_mm']}mm")
    print(f"  └ Humidity:   {payload['humidity_pct']}%")
    print(f"  └ Nitrogen:   {payload['n_mg_kg']} mg/kg")
    print(f"  └ Phosphorus: {payload['p_mg_kg']} mg/kg")
    print(f"  └ Potassium:  {payload['k_mg_kg']} mg/kg")
    
    return payload

def transmit(payload: dict):
    """Simulates GSM transmission to the Mavuno cloud."""
    print("[GSM] Transmitting payload to Mavuno Cloud over 2G...")
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"[Cloud] 200 OK. Telemetry accepted.")
            print(f"[Cloud] Instant Yield Probability Score (YPS) updated to: {data.get('new_yps')}")
        else:
            print(f"[GSM Error] Transmission failed with status: {response.status_code}")
    except Exception as e:
        print(f"[Network Error] Could not reach API. Is the server running? ({e})")
    print("[Hardware] Returning to sleep mode to conserve solar battery.")

if __name__ == "__main__":
    print("--- MAVUNO IoT TELEMETRY DEMO ---")
    
    farm_target = "UG-MBL-0001"
    
    if len(sys.argv) > 1:
        farm_target = sys.argv[1]
        
    data = generate_telemetry(farm_target)
    time.sleep(1) # Simulate hardware processing time
    transmit(data)
