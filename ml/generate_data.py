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
    {
        "farm_id": "UG-MBL-0001",
        "farmer_name": "Akello Sarah",
        "district": "Mbale",
        "crop": "coffee",
        "gps": {"lat": 1.0754, "lng": 34.1754},
        "acres": 2.0,
        "phone": "+256700000001",
        "pump": {"lat": 1.0980, "lng": 34.1820, "name": "EASP-Mbale-07"},
        "discipline": 0.90,
        "drought_factor": 1.00,
    },
    {
        "farm_id": "UG-GUL-0002",
        "farmer_name": "Okello John",
        "district": "Gulu",
        "crop": "maize",
        "gps": {"lat": 2.7747, "lng": 32.2990},
        "acres": 3.5,
        "phone": "+256700000002",
        "pump": {"lat": 2.7520, "lng": 32.3140, "name": "EASP-Gulu-02"},
        "discipline": 0.45,
        "drought_factor": 0.35,
    },
    {
        "farm_id": "UG-MBR-0003",
        "farmer_name": "Namazzi Grace",
        "district": "Mbarara",
        "crop": "beans",
        "gps": {"lat": -0.6100, "lng": 30.6540},
        "acres": 1.2,
        "phone": "+256700000003",
        "pump": {"lat": -0.6310, "lng": 30.6700, "name": "EASP-Mbarara-11"},
        "discipline": 0.70,
        "drought_factor": 0.95,
    },
]

# Crop-specific baselines (% soil moisture target, ideal temp, rainfall mm/mo)
CROP_PROFILE = {
    "coffee": {"sm_ideal": 28.0, "temp_ideal": 22.0, "rain_ideal": 140.0},
    "maize":  {"sm_ideal": 22.0, "temp_ideal": 25.0, "rain_ideal": 110.0},
    "beans":  {"sm_ideal": 24.0, "temp_ideal": 23.0, "rain_ideal": 100.0},
}


def simulate_farm(farm: dict, days: int = 180) -> list[dict]:
    """Produce daily aggregate readings for a farm (4 readings collapsed to daily avg)."""
    profile = CROP_PROFILE[farm["crop"]]
    start = date.today() - timedelta(days=days)

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

        rows.append({
            "farm_id": farm["farm_id"],
            "crop": farm["crop"],
            "date": d.isoformat(),
            "soil_moisture": round(float(sm), 2),
            "temp_c": round(float(temp), 2),
            "rainfall_mm": round(float(rainfall), 2),
            "humidity_pct": round(float(humidity), 2),
            "discipline": round(discipline, 3),
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
            sm_dev = abs(sm_avg - profile["sm_ideal"])
            rain_dev = abs(rain_sum - profile["rain_ideal"] * 7 / 30)
            # Synthetic "actual yield index" 0-1 from discipline + deviations
            yield_idx = np.clip(
                g.iloc[i]["discipline"]
                - 0.015 * sm_dev
                - 0.008 * rain_dev
                - 0.02 * (temp_var ** 0.5)
                + np.random.normal(0, 0.05),
                0.0, 1.0,
            )
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
                "sm_deviation": round(sm_dev, 3),
                "rain_deviation": round(rain_dev, 3),
                "yield_idx": round(yield_idx, 3),
                "tier": tier,
            })
    return pd.DataFrame(feats)


def main() -> None:
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
