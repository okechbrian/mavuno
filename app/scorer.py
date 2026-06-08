"""Yield Probability Scorer for Prototype."""
import math
import statistics
from functools import lru_cache
from sqlalchemy import text
from sqlalchemy.orm import Session

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

def score_farm(db: Session, farm_id: str):
    import time
    # We query the unified view or the farmer_profiles table.
    # Fallback to Land Prep if current_stage column is missing/null in older schema.
    try:
        row = db.execute(text("SELECT crop, current_stage, planting_date FROM farmer_profiles WHERE user_id = :id"), {"id": farm_id}).fetchone()
    except:
        row = db.execute(text("SELECT crop FROM farmer_profiles WHERE user_id = :id"), {"id": farm_id}).fetchone()
        if row: row = (row[0], "Land Prep", None)

    if not row: return {"error": "unknown_farm"}
    
    crop = row[0]
    current_stage = row[1] if row[1] else "Land Prep"
    planting_date = row[2]
    
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

    # ML Inference
    model_bundle = _load_model()
    predicted_harvest_days = None
    yps_ml = None

    if model_bundle:
        try:
            clf = model_bundle["classifier"]
            reg_h = model_bundle["harvest_regressor"]
            reg_y = model_bundle["yield_regressor"]
            crop_enc = model_bundle["crop_encoding"]
            
            # Prepare feature vector
            profile = {"sm_ideal": 25.0, "rain_ideal": 100.0} # Fallback defaults
            if crop == "coffee": profile = {"sm_ideal": 28.0, "rain_ideal": 140.0}
            elif crop == "maize": profile = {"sm_ideal": 22.0, "rain_ideal": 110.0}
            elif crop == "beans": profile = {"sm_ideal": 24.0, "rain_ideal": 100.0}
            
            sm_dev = abs(sm_avg - profile["sm_ideal"])
            rain_dev = abs(rain_sum - profile["rain_ideal"] * 7 / 30)
            
            days_since = 0
            if planting_date:
                days_since = int((time.time() - planting_date) / 86400)
            
            # ["sm_avg_7d", "rain_sum_7d", "temp_var_7d", "humidity_avg_7d", "n_avg_7d", "p_avg_7d", "k_avg_7d", "sm_deviation", "rain_deviation", "days_since_planting", "crop_enc"]
            x_input = [
                sm_avg, rain_sum, temp_var, hum_avg, 
                n_avg, p_avg, k_avg,
                sm_dev, rain_dev, days_since, crop_enc.get(crop, 1)
            ]
            
            # Predict Tier
            tier_ml = int(clf.predict([x_input])[0])
            # Predict Harvest
            predicted_harvest_days = int(max(0, reg_h.predict([x_input])[0]))
            # Predict Yield (KG)
            predicted_yield_kg = float(reg_y.predict([x_input])[0])
            
            # Derive YPS from Tier for display consistency
            yps_ml = [300, 550, 850][tier_ml]
        except Exception as e:
            print(f"ML Inference Error: {e}")
            predicted_yield_kg = None

    # Agronomic Feature: Stage-based adjustment (Heuristic Fallback/Adjustment)
    stage_multiplier = 1.0
    if current_stage == "Flowering" and sm_avg < 25:
        stage_multiplier = 0.8
    elif current_stage == "Harvesting":
        if rain_sum > 100: stage_multiplier = 0.85
        else: stage_multiplier = 1.1

    # Final YPS Logic: Hybrid of ML and Heuristics
    expected = ((sm_avg * 10) + (rain_sum * 2) - (temp_var * 5)) * stage_multiplier
    yps_heuristic = 500 + expected
    
    if yps_ml:
        # 70% ML, 30% Heuristic for stability
        yps = int(max(0, min(1000, 0.7 * yps_ml + 0.3 * yps_heuristic)))
    else:
        yps = int(max(0, min(1000, yps_heuristic)))
        predicted_yield_kg = None
    
    # Generate actionable diagnostics based on the 7 crucial signals
    n_avg = statistics.mean(nutrients["n"]) if nutrients["n"] else 0
    p_avg = statistics.mean(nutrients["p"]) if nutrients["p"] else 0
    k_avg = statistics.mean(nutrients["k"]) if nutrients["k"] else 0
    
    diagnostics = []
    if sm_avg < 20:
        diagnostics.append("💧 Moisture deficit. Immediate irrigation required to stabilize YPS.")
    elif sm_avg > 35:
        diagnostics.append("⚠️ Waterlogging risk. Suspend irrigation to prevent root rot.")
        
    if n_avg < 25:
        diagnostics.append("🌿 Severe Nitrogen depletion. Apply Urea/NPK to restore vegetative growth.")
    if p_avg < 12:
        diagnostics.append("🌿 Phosphorus low. Root development is currently stunted.")
    if k_avg < 150:
        diagnostics.append("🛡️ Potassium deficit. Crop drought-resilience is compromised.")
        
    if predicted_harvest_days is not None:
        if predicted_harvest_days <= 14:
            diagnostics.append(f"🌾 Harvest alert: Predicted maturity in {predicted_harvest_days} days. Secure labor and logistics.")
        else:
            diagnostics.append(f"📜 Seasonal update: Estimated {predicted_harvest_days} days until peak maturity.")

    if not diagnostics:
        diagnostics.append("✅ All 7 biological signals are nominal. Maintain current regimen.")
    
    tier = 2 if yps > 700 else 1 if yps > 400 else 0
    health = "Excellent" if yps > 750 else "Good" if yps > 500 else "Fair" if yps > 300 else "Poor"
    
    return {
        "farm_id": farm_id, "yps": yps, "tier": tier, "tier_label": health, "trade_health": health,
        "kg_allocated": [0, 25, 60][tier], "trade_ceiling_ugx": [0, 75000, 200000][tier],
        "nutrients": nutrients,
        "diagnostics": diagnostics,
        "predicted_harvest_days": predicted_harvest_days,
        "predicted_yield_kg": round(predicted_yield_kg, 1) if predicted_yield_kg is not None else None
    }
