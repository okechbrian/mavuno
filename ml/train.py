"""Train YPS gradient-boosting classifier and save model + metrics."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "app" / "data"
MODEL_PATH = DATA_DIR / "yps_model.pkl"

FEATURES = [
    "sm_avg_7d",
    "rain_sum_7d",
    "temp_var_7d",
    "humidity_avg_7d",
    "sm_deviation",
    "rain_deviation",
    "crop_enc",
]
CROP_ENCODING = {"coffee": 0, "maize": 1, "beans": 2}


def main() -> None:
    df = pd.read_csv(DATA_DIR / "training.csv")
    df["crop_enc"] = df["crop"].map(CROP_ENCODING)
    X = df[FEATURES].values
    y = df["tier"].values

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    clf = GradientBoostingClassifier(
        n_estimators=150, max_depth=3, learning_rate=0.08, random_state=42
    )
    clf.fit(X_tr, y_tr)
    preds = clf.predict(X_te)
    acc = accuracy_score(y_te, preds)
    report = classification_report(y_te, preds, output_dict=True)

    joblib.dump({"model": clf, "features": FEATURES, "crop_encoding": CROP_ENCODING}, MODEL_PATH)
    (DATA_DIR / "train_metrics.json").write_text(
        json.dumps({"accuracy": round(acc, 4), "report": report}, indent=2), encoding="utf-8"
    )
    print(f"trained  accuracy={acc:.3f}  model={MODEL_PATH}")


if __name__ == "__main__":
    main()
