"""Generate synthetic farm + sensor data for 3 Uganda smallholder farms.

Output:
  app/data/farms.json         - 3 farmer profiles with GPS + crop
  app/data/sensor_history.json - 180 days x 3 farms, 4 sensor readings/day
  app/data/training.csv       - flat features for the YPS model
"""
from __future__ import annotations

import json
import math
import random
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "app" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

FARMS = [
    # MBALE CLUSTER (Coffee)
    {"farm_id": f"UG-MBL-{i:04d}", "farmer_name": f"Farmer Mbale {i}", "district": "Mbale", "crop": "coffee", 
     "gps": {"lat": 1.07 + (random.random()*0.05), "lng": 34.17 + (random.random()*0.05)}, 
     "acres": round(1.0 + random.random()*3, 1), "phone": f"+256700001{i:02d}", 
     "discipline": 0.6 + random.random()*0.3, "drought_factor": 1.0} for i in range(1, 9)
] + [
    # GULU CLUSTER (Maize)
    {"farm_id": f"UG-GUL-{i:04d}", "farmer_name": f"Farmer Gulu {i}", "district": "Gulu", "crop": "maize", 
     "gps": {"lat": 2.77 + (random.random()*0.08), "lng": 32.29 + (random.random()*0.08)}, 
     "acres": round(2.0 + random.random()*5, 1), "phone": f"+256700002{i:02d}", 
     "discipline": 0.4 + random.random()*0.5, "drought_factor": 0.8} for i in range(1, 7)
] + [
    # MBARARA CLUSTER (Beans)
    {"farm_id": f"UG-MBR-{i:04d}", "farmer_name": f"Farmer Mbarara {i}", "district": "Mbarara", "crop": "beans", 
     "gps": {"lat": -0.61 + (random.random()*0.06), "lng": 30.65 + (random.random()*0.06)}, 
     "acres": round(0.5 + random.random()*2, 1), "phone": f"+256700003{i:02d}", 
     "discipline": 0.7 + random.random()*0.2, "drought_factor": 0.95} for i in range(1, 7)
]

# Crop-specific baselines (% soil moisture target, ideal temp, rainfall mm/mo, maturity days, ideal N-P-K)
CROP_PROFILE = {
    "coffee": {"sm_ideal": 28.0, "temp_ideal": 22.0, "rain_ideal": 140.0, "maturity": 240, "n_ideal": 40, "p_ideal": 25, "k_ideal": 220},
    "maize":  {"sm_ideal": 22.0, "temp_ideal": 25.0, "rain_ideal": 110.0, "maturity": 110, "n_ideal": 50, "p_ideal": 20, "k_ideal": 180},
    "beans":  {"sm_ideal": 24.0, "temp_ideal": 23.0, "rain_ideal": 100.0, "maturity": 85, "n_ideal": 30, "p_ideal": 35, "k_ideal": 250},
}


def simulate_farm(farm: dict, days: int = 180) -> list[dict]:
    """Produce daily aggregate readings for a farm (4 readings collapsed to daily avg)."""
    profile = CROP_PROFILE[farm["crop"]]
    start = date.today() - timedelta(days=days)
    farm["planting_date"] = int(time.mktime(start.timetuple()))

    discipline = farm.get("discipline", 0.75)
    drought = farm.get("drought_factor", 1.0)
    rows: list[dict] = []
    for i in range(days):
        d = start + timedelta(days=i)
        # Seasonal swing: two rainy seasons in Uganda (sinusoid approximation)
        season = math.sin((d.timetuple().tm_yday / 365.0) * 2 * math.pi * 2)

        sm = (profile["sm_ideal"] * drought) + season * 4.0 + np.random.normal(0, 3.0) * (1 - discipline)
        temp = profile["temp_ideal"] - season * 2.0 + np.random.normal(0, 1.5)
        rainfall = max(0.0, (profile["rain_ideal"] / 30.0) * drought + season * 3.0 + np.random.normal(0, 2.0))
        humidity = np.clip(55 + season * 10 + np.random.normal(0, 5), 30, 95)
        
        # Simulate NPK (slowly declining without intervention, discipline affects consistency)
        n = profile["n_ideal"] * (0.9 ** (i/30)) + np.random.normal(0, 2.0) * (1-discipline)
        p = profile["p_ideal"] * (0.95 ** (i/30)) + np.random.normal(0, 1.5) * (1-discipline)
        k = profile["k_ideal"] * (0.98 ** (i/30)) + np.random.normal(0, 5.0) * (1-discipline)

        rows.append({
            "farm_id": farm["farm_id"],
            "crop": farm["crop"],
            "date": d.isoformat(),
            "soil_moisture": round(float(sm), 2),
            "temp_c": round(float(temp), 2),
            "rainfall_mm": round(float(rainfall), 2),
            "humidity_pct": round(float(humidity), 2),
            "n_mg_kg": round(max(0, float(n)), 1),
            "p_mg_kg": round(max(0, float(p)), 1),
            "k_mg_kg": round(max(0, float(k)), 1),
            "discipline": round(discipline, 3),
            "days_since_planting": i
        })
    return rows


def build_features(all_rows: list[dict]) -> pd.DataFrame:
    """Collapse rolling 7-day windows into feature rows with a synthetic yield label."""
    df = pd.DataFrame(all_rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["farm_id", "date"])

    feats = []
    for farm_id, g in df.groupby("farm_id"):
        g = g.reset_index(drop=True)
        profile = CROP_PROFILE[g.iloc[0]["crop"]]
        for i in range(6, len(g)):
            w = g.iloc[i - 6 : i + 1]
            sm_avg = w["soil_moisture"].mean()
            rain_sum = w["rainfall_mm"].sum()
            temp_var = w["temp_c"].var()
            n_avg = w["n_mg_kg"].mean()
            p_avg = w["p_mg_kg"].mean()
            k_avg = w["k_mg_kg"].mean()

            sm_dev = abs(sm_avg - profile["sm_ideal"])
            rain_dev = abs(rain_sum - profile["rain_ideal"] * 7 / 30)
            
            days_since = g.iloc[i]["days_since_planting"]
            # Environmental stress slows down maturity
            stress_factor = (sm_dev * 0.5 + rain_dev * 0.2 + (temp_var**0.5) * 1.0) / 10.0
            actual_maturity = profile["maturity"] * (1 + stress_factor * 0.1)
            days_to_harvest = max(0, int(actual_maturity - days_since))

            # Nutrient score (0.0 - 1.0)
            n_score = min(1.0, n_avg / profile["n_ideal"])
            p_score = min(1.0, p_avg / profile["p_ideal"])
            k_score = min(1.0, k_avg / profile["k_ideal"])
            nutrient_score = (n_score * 0.4 + p_score * 0.3 + k_score * 0.3)

            # Synthetic "actual yield index" 0-1 from discipline + deviations + nutrients
            yield_idx = np.clip(
                g.iloc[i]["discipline"] * 0.6
                + nutrient_score * 0.4
                - 0.015 * sm_dev
                - 0.008 * rain_dev
                - 0.02 * (temp_var ** 0.5)
                + np.random.normal(0, 0.03),
                0.0, 1.0,
            )
            
            # Yield in kg (acres * baseline_yield * yield_idx)
            # Baseline: Coffee 1000kg/acre, Maize 2000kg/acre, Beans 800kg/acre
            baselines = {"coffee": 1000, "maize": 2000, "beans": 800}
            acres = [f["acres"] for f in FARMS if f["farm_id"] == farm_id][0]
            yield_kg = acres * baselines[g.iloc[0]["crop"]] * yield_idx

            # Tier label: 0=denied, 1=partial, 2=full
            tier = 2 if yield_idx > 0.70 else (1 if yield_idx > 0.40 else 0)
            feats.append({
                "farm_id": farm_id,
                "crop": g.iloc[i]["crop"],
                "date": g.iloc[i]["date"].isoformat(),
                "sm_avg_7d": round(sm_avg, 3),
                "rain_sum_7d": round(rain_sum, 3),
                "temp_var_7d": round(temp_var, 3),
                "humidity_avg_7d": round(w["humidity_pct"].mean(), 3),
                "n_avg_7d": round(n_avg, 1),
                "p_avg_7d": round(p_avg, 1),
                "k_avg_7d": round(k_avg, 1),
                "sm_deviation": round(sm_dev, 3),
                "rain_deviation": round(rain_dev, 3),
                "days_since_planting": days_since,
                "yield_idx": round(yield_idx, 3),
                "yield_kg": round(yield_kg, 1),
                "tier": tier,
                "days_to_harvest": days_to_harvest
            })
    return pd.DataFrame(feats)


def main() -> None:
    import time
    all_rows: list[dict] = []
    for farm in FARMS:
        all_rows.extend(simulate_farm(farm))

    (DATA_DIR / "farms.json").write_text(
        json.dumps({f["farm_id"]: f for f in FARMS}, indent=2), encoding="utf-8"
    )
    (DATA_DIR / "sensor_history.json").write_text(
        json.dumps(all_rows, indent=2), encoding="utf-8"
    )

    feats = build_features(all_rows)
    feats.to_csv(DATA_DIR / "training.csv", index=False)
    print(f"farms={len(FARMS)}  sensor_rows={len(all_rows)}  training_rows={len(feats)}")


if __name__ == "__main__":
    main()
