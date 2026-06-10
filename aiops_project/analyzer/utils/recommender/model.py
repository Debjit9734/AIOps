from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = PROJECT_ROOT / "trained_model.pkl"


def train_model(X, y):
    model = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        min_samples_leaf=1,
    )
    model.fit(X, y)
    joblib.dump(model, MODEL_PATH)
    return model


def load_model():
    try:
        return joblib.load(MODEL_PATH)
    except Exception:
        return None


def predict_resources(features):
    model = load_model()
    if not model:
        # Default simple mapping if model not trained yet
        return {
            "cpu": round(features["total_lines"] / 5000 + 1, 2),
            "ram": round(features["dependency_count"] / 5 + 1, 2),
            "storage": round(features["total_files"] / 20 + 5, 2),
        }

    X = np.array(
        [[
            features["total_files"],
            features["total_lines"],
            features["dependency_count"],
            features.get("security_score", 0),
        ]]
    )
    y_pred = model.predict(X)[0]
    return {
        "cpu": round(y_pred[0], 2),
        "ram": round(y_pred[1], 2),
        "storage": round(y_pred[2], 2),
    }
