from pathlib import Path

import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

if __package__ in {None, ""}:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[3]))

from analyzer.utils.recommender.model import MODEL_PATH, train_model

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = PROJECT_ROOT / "data" / "training_data.csv"
FEATURE_COLUMNS = ["total_files", "total_lines", "dependency_count", "security_score"]
TARGET_COLUMNS = ["cpu", "ram", "storage"]


def _validate_dataset(df):
    missing = [column for column in FEATURE_COLUMNS + TARGET_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")

    cleaned = df[FEATURE_COLUMNS + TARGET_COLUMNS].dropna()
    if cleaned.shape[0] < 10:
        raise ValueError("Not enough valid training data. Add at least 10 complete rows.")
    return cleaned


def train():
    if not DATA_PATH.exists():
        raise FileNotFoundError("training_data.csv not found. Generate data first.")

    df = pd.read_csv(DATA_PATH)
    df = _validate_dataset(df)

    X = df[FEATURE_COLUMNS].values
    y = df[TARGET_COLUMNS].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = train_model(X_train, y_train)
    predictions = model.predict(X_test)

    r2 = r2_score(y_test, predictions, multioutput="uniform_average")
    mae = mean_absolute_error(y_test, predictions, multioutput="raw_values")

    print(f"Training rows used: {len(df)}")
    print(f"Model R2 score: {round(r2, 3)}")
    print(
        "Mean absolute error -> "
        f"CPU: {mae[0]:.3f}, RAM: {mae[1]:.3f}, Storage: {mae[2]:.3f}"
    )
    print(f"Model saved as {MODEL_PATH}")


if __name__ == "__main__":
    train()
