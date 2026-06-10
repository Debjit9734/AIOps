import csv
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
CSV_PATH = DATA_DIR / "training_data.csv"


def ensure_csv_exists():
    """
    Create data/training_data.csv with header if it does not exist.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not CSV_PATH.exists():
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "total_files",
                "total_lines",
                "dependency_count",
                "security_score",
                "cpu",
                "ram",
                "storage"
            ])


def generate_labels(features):
    """
    Rule-based labeling to generate training targets.
    """
    total_lines = features["total_lines"]
    security_score = features["security_score"]

    # Base resource allocation
    if total_lines < 5000:
        cpu, ram, storage = 1, 2, 10
    elif total_lines < 20000:
        cpu, ram, storage = 2, 4, 20
    else:
        cpu, ram, storage = 4, 8, 50

    # Security overhead
    if security_score > 6:
        cpu += 0.5
        ram += 1

    return cpu, ram, storage


def save_training_row(features):
    """
    Save one training row into CSV.
    """
    ensure_csv_exists()

    cpu, ram, storage = generate_labels(features)

    row = [
        features["total_files"],
        features["total_lines"],
        features["dependency_count"],
        features["security_score"],
        cpu,
        ram,
        storage
    ]

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)
