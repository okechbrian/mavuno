"""Yield Probability Scorer for Prototype."""
import joblib
import numpy as np
from functools import lru_cache
from .database import get_db

@lru_cache(maxsize=1)
def _load_model():
    from .database import DATA_DIR
    return joblib.load(DATA_DIR / "yps_model.pkl")

def score_farm(farm_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT crop FROM farms WHERE id = ?", (farm_id,))
    row = cur.fetchone()
    if not row: return {"error": "unknown_farm"}
    crop = row['crop']
    
    cur.execute("SELECT soil_moisture, temp_c, rainfall_mm, humidity_pct, n_mg_kg, p_mg_kg, k_mg_kg FROM sensor_history WHERE farm_id = ? ORDER BY timestamp DESC LIMIT 7", (farm_id,))
    window = cur.fetchall()
    conn.close()
    if len(window) < 7: return {"error": "insufficient_data"}

    # NPK Trends for Dashboard
    nutrients = {
        "n": [r['n_mg_kg'] for r in reversed(window)],
        "p": [r['p_mg_kg'] for r in reversed(window)],
        "k": [r['k_mg_kg'] for r in reversed(window)]
    }

    sm_avg = float(np.mean([r['soil_moisture'] for r in window]))
    rain_sum = float(np.sum([r['rainfall_mm'] for r in window]))
    temp_var = float(np.var([r['temp_c'] for r in window]))
    hum_avg = float(np.mean([r['humidity_pct'] for r in window]))

    bundle = _load_model()
    # Simple YPS Logic
    expected = (sm_avg * 10) + (rain_sum * 2) - (temp_var * 5)
    yps = int(max(0, min(1000, 500 + expected)))
    
    # Generate actionable diagnostics based on the 7 crucial signals
    n_avg = np.mean(nutrients["n"]) if nutrients["n"] else 0
    p_avg = np.mean(nutrients["p"]) if nutrients["p"] else 0
    k_avg = np.mean(nutrients["k"]) if nutrients["k"] else 0
    
    diagnostics = []
    if sm_avg < 20:
        diagnostics.append("💧 Moisture deficit. Immediate irrigation required to stabilize YPS.")
    elif sm_avg > 35:
        diagnostics.append("⚠️ Waterlogging risk. Suspend irrigation to prevent root rot.")
        
    if n_avg < 25:
        diagnostics.append("🌱 Severe Nitrogen depletion. Apply Urea/NPK to restore vegetative growth.")
    if p_avg < 12:
        diagnostics.append("🌱 Phosphorus low. Root development is currently stunted.")
    if k_avg < 150:
        diagnostics.append("🛡️ Potassium deficit. Crop drought-resilience is compromised.")
        
    if not diagnostics:
        diagnostics.append("✅ All 7 biological signals are nominal. Maintain current regimen.")
    
    tier = 2 if yps > 700 else 1 if yps > 400 else 0
    health = "Excellent" if yps > 750 else "Good" if yps > 500 else "Fair" if yps > 300 else "Poor"
    
    return {
        "farm_id": farm_id, "yps": yps, "tier": tier, "credit_health": health,
        "kwh_allocated": [0, 25, 60][tier], "credit_ceiling_ugx": [0, 75000, 200000][tier],
        "nutrients": nutrients,
        "diagnostics": diagnostics
    }
