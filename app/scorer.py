"""Yield Probability Scorer for Prototype."""
import math
import statistics
from functools import lru_cache

@lru_cache(maxsize=1)
def _load_model():
    """Optional model loader. Fallback to simple logic if dependencies or file missing."""
    try:
        import joblib
        from .config import DATA_DIR
        path = DATA_DIR / "yps_model.pkl"
        if path.exists():
            return joblib.load(path)
    except ImportError:
        pass
    return None

def score_farm(farm_id: str):
    from sqlalchemy import text
    from .database import SessionLocal
    with SessionLocal() as db:
        # We query the unified view or the farmer_profiles table.
        # Fallback to Land Prep if current_stage column is missing/null in older schema.
        try:
            row = db.execute(text("SELECT crop, current_stage FROM farmer_profiles WHERE user_id = :id"), {"id": farm_id}).fetchone()
        except:
            row = db.execute(text("SELECT crop FROM farmer_profiles WHERE user_id = :id"), {"id": farm_id}).fetchone()
            if row: row = (row[0], "Land Prep")

        if not row: return {"error": "unknown_farm"}
        
        crop = row[0]
        current_stage = row[1] if len(row) > 1 and row[1] else "Land Prep"
        
        window = db.execute(text("SELECT soil_moisture, temp_c, rainfall_mm, humidity_pct, n_mg_kg, p_mg_kg, k_mg_kg FROM soil_telemetry WHERE farm_id = :id ORDER BY timestamp DESC LIMIT 7"), {"id": farm_id}).fetchall()
    
    if len(window) < 7: return {"error": "insufficient_data"}
    window_dicts = [dict(w._mapping) for w in window]

    # NPK Trends for Dashboard
    nutrients = {
        "n": [r['n_mg_kg'] for r in reversed(window_dicts)],
        "p": [r['p_mg_kg'] for r in reversed(window_dicts)],
        "k": [r['k_mg_kg'] for r in reversed(window_dicts)]
    }

    soil_moistures = [r['soil_moisture'] for r in window_dicts]
    rainfalls = [r['rainfall_mm'] for r in window_dicts]
    temps = [r['temp_c'] for r in window_dicts]
    humidities = [r['humidity_pct'] for r in window_dicts]

    sm_avg = statistics.mean(soil_moistures)
    rain_sum = sum(rainfalls)
    # Variance fallback if statistics.variance fails on small data
    try:
        temp_var = statistics.variance(temps)
    except statistics.StatisticsError:
        temp_var = 0
    hum_avg = statistics.mean(humidities)

    # Agronomic Feature: Stage-based adjustment
    # During Flowering/Harvesting, moisture deficit is penalized heavily.
    # During Land Prep/Vegetative, higher baseline expected YPS.
    stage_multiplier = 1.0
    if current_stage == "Flowering" and sm_avg < 25:
        stage_multiplier = 0.8
    elif current_stage == "Harvesting":
        # Less rain needed during harvest
        if rain_sum > 100: stage_multiplier = 0.85
        else: stage_multiplier = 1.1

    # Simple YPS Logic
    expected = ((sm_avg * 10) + (rain_sum * 2) - (temp_var * 5)) * stage_multiplier
    yps = int(max(0, min(1000, 500 + expected)))
    
    # Generate actionable diagnostics based on the 7 crucial signals
    n_avg = statistics.mean(nutrients["n"]) if nutrients["n"] else 0
    p_avg = statistics.mean(nutrients["p"]) if nutrients["p"] else 0
    k_avg = statistics.mean(nutrients["k"]) if nutrients["k"] else 0
    
    diagnostics = []
    if sm_avg < 20:
        diagnostics.append("ðŸ’§ Moisture deficit. Immediate irrigation required to stabilize YPS.")
    elif sm_avg > 35:
        diagnostics.append("âš ï¸ Waterlogging risk. Suspend irrigation to prevent root rot.")
        
    if n_avg < 25:
        diagnostics.append("ðŸŒ± Severe Nitrogen depletion. Apply Urea/NPK to restore vegetative growth.")
    if p_avg < 12:
        diagnostics.append("ðŸŒ± Phosphorus low. Root development is currently stunted.")
    if k_avg < 150:
        diagnostics.append("ðŸ›¡ï¸ Potassium deficit. Crop drought-resilience is compromised.")
        
    if not diagnostics:
        diagnostics.append("âœ… All 7 biological signals are nominal. Maintain current regimen.")
    
    tier = 2 if yps > 700 else 1 if yps > 400 else 0
    health = "Excellent" if yps > 750 else "Good" if yps > 500 else "Fair" if yps > 300 else "Poor"
    
    return {
        "farm_id": farm_id, "yps": yps, "tier": tier, "trade_health": health,
        "kg_allocated": [0, 25, 60][tier], "trade_ceiling_ugx": [0, 75000, 200000][tier],
        "nutrients": nutrients,
        "diagnostics": diagnostics
    }

