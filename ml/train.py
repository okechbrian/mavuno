"""Train YPS gradient-boosting classifier and save model + metrics."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import accuracy_score, classification_report, mean_absolute_error
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "app" / "data"
MODEL_PATH = DATA_DIR / "yps_model.pkl"

FEATURES = [
    "sm_avg_7d",
    "rain_sum_7d",
    "temp_var_7d",
    "humidity_avg_7d",
    "n_avg_7d",
    "p_avg_7d",
    "k_avg_7d",
    "sm_deviation",
    "rain_deviation",
    "days_since_planting",
    "crop_enc",
]
CROP_ENCODING = {"coffee": 0, "maize": 1, "beans": 2}


def main() -> None:
    df = pd.read_csv(DATA_DIR / "training.csv")
    df["crop_enc"] = df["crop"].map(CROP_ENCODING)
    X = df[FEATURES].values
    
    # 1. YPS Classifier (Tier)
    y_tier = df["tier"].values
    X_tr, X_te, y_tr, y_te = train_test_split(X, y_tier, test_size=0.2, random_state=42, stratify=y_tier)
    clf = GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=0.08, random_state=42)
    clf.fit(X_tr, y_tr)
    preds = clf.predict(X_te)
    acc = accuracy_score(y_te, preds)

    # 2. Harvest Regressor (Days)
    y_harvest = df["days_to_harvest"].values
    X_tr_h, X_te_h, y_tr_h, y_te_h = train_test_split(X, y_harvest, test_size=0.2, random_state=42)
    reg_h = GradientBoostingRegressor(n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42)
    reg_h.fit(X_tr_h, y_tr_h)
    h_preds = reg_h.predict(X_te_h)
    mae_h = mean_absolute_error(y_te_h, h_preds)

    # 3. Yield Regressor (KG)
    y_yield = df["yield_kg"].values
    X_tr_y, X_te_y, y_tr_y, y_te_y = train_test_split(X, y_yield, test_size=0.2, random_state=42)
    reg_y = GradientBoostingRegressor(n_estimators=250, max_depth=5, learning_rate=0.04, random_state=42)
    reg_y.fit(X_tr_y, y_tr_y)
    y_preds = reg_y.predict(X_te_y)
    mae_y = mean_absolute_error(y_te_y, y_preds)

    joblib.dump({
        "classifier": clf, 
        "harvest_regressor": reg_h,
        "yield_regressor": reg_y,
        "features": FEATURES, 
        "crop_encoding": CROP_ENCODING
    }, MODEL_PATH)
    
    (DATA_DIR / "train_metrics.json").write_text(
        json.dumps({
            "classifier_accuracy": round(acc, 4), 
            "harvest_mae": round(mae_h, 4),
            "yield_mae_kg": round(mae_y, 4)
        }, indent=2), encoding="utf-8"
    )
    print(f"trained  acc={acc:.3f}  h_mae={mae_h:.1f}  y_mae={mae_y:.1f}kg  model={MODEL_PATH}")


if __name__ == "__main__":
    main()
