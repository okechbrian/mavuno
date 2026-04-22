"""Load YPS model and score a farm from its recent sensor history."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from .config import DATA_DIR

CROP_PROFILE = {
    "coffee": {"sm_ideal": 28.0, "rain_ideal": 140.0},
    "maize":  {"sm_ideal": 22.0, "rain_ideal": 110.0},
    "beans":  {"sm_ideal": 24.0, "rain_ideal": 100.0},
}


@lru_cache(maxsize=1)
def _load_model():
    bundle = joblib.load(DATA_DIR / "yps_model.pkl")
    return bundle


@lru_cache(maxsize=1)
def _load_sensor_history() -> list[dict]:
    return json.loads((DATA_DIR / "sensor_history.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_farms() -> dict:
    return json.loads((DATA_DIR / "farms.json").read_text(encoding="utf-8"))


def _recent_window(farm_id: str, days: int = 7) -> list[dict]:
    hist = [r for r in _load_sensor_history() if r["farm_id"] == farm_id]
    return hist[-days:]


def score_farm(farm_id: str) -> dict:
    """Return {farm_id, yps, tier, kwh_allocated, credit_ceiling_ugx, reason}."""
    farms = _load_farms()
    if farm_id not in farms:
        return {"error": "unknown_farm", "farm_id": farm_id}

    window = _recent_window(farm_id)
    if len(window) < 7:
        return {"error": "insufficient_data", "farm_id": farm_id}

    crop = farms[farm_id]["crop"]
    profile = CROP_PROFILE[crop]

    sm_avg = float(np.mean([r["soil_moisture"] for r in window]))
    rain_sum = float(np.sum([r["rainfall_mm"] for r in window]))
    temp_var = float(np.var([r["temp_c"] for r in window]))
    humidity_avg = float(np.mean([r["humidity_pct"] for r in window]))
    sm_dev = abs(sm_avg - profile["sm_ideal"])
    rain_dev = abs(rain_sum - profile["rain_ideal"] * 7 / 30)

    bundle = _load_model()
    model = bundle["model"]
    crop_enc = bundle["crop_encoding"][crop]

    X = np.array([[sm_avg, rain_sum, temp_var, humidity_avg, sm_dev, rain_dev, crop_enc]])
    proba = model.predict_proba(X)[0]
    tier = int(np.argmax(proba))
    # Compose YPS 0-1000: weighted expected tier probability
    expected = proba[0] * 200 + proba[1] * 600 + proba[2] * 900
    yps = int(round(float(expected)))
    yps = max(0, min(1000, yps))

    from .config import TIER_KWH, TIER_CEILING_UGX
    return {
        "farm_id": farm_id,
        "crop": crop,
        "yps": yps,
        "tier": tier,
        "tier_label": ["denied", "partial", "full"][tier],
        "kwh_allocated": TIER_KWH[tier],
        "credit_ceiling_ugx": TIER_CEILING_UGX[tier],
        "features": {
            "sm_avg_7d": round(sm_avg, 2),
            "rain_sum_7d": round(rain_sum, 2),
            "temp_var_7d": round(temp_var, 2),
            "humidity_avg_7d": round(humidity_avg, 2),
            "sm_deviation": round(sm_dev, 2),
            "rain_deviation": round(rain_dev, 2),
        },
    }
