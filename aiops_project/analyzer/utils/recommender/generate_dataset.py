import csv
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[3]))

from analyzer.utils.analyzer_utils import analyze_files, download_repo_as_zip
from analyzer.utils.recommender.data_generator import CSV_PATH, save_training_row
from analyzer.utils.recommender.feature_extractor import extract_features
from analyzer.utils.recommender.security_analyzer import analyze_security


def _load_repo_urls(input_path):
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if path.suffix.lower() == ".csv":
        with open(path, "r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if "repo_url" not in (reader.fieldnames or []):
                raise ValueError("CSV input must include a 'repo_url' column.")
            return [row["repo_url"].strip() for row in reader if row.get("repo_url", "").strip()]

    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main():
    if len(sys.argv) != 2:
        print("Usage: python analyzer\\utils\\recommender\\generate_dataset.py <repo-list.txt|repo-list.csv>")
        raise SystemExit(1)

    repo_urls = _load_repo_urls(sys.argv[1])
    if not repo_urls:
        print("No repository URLs found in the input file.")
        raise SystemExit(1)

    success_count = 0
    for repo_url in repo_urls:
        print(f"Analyzing {repo_url}")
        repo_path, error = download_repo_as_zip(repo_url)
        if error:
            print(f"  Skipped: {error}")
            continue

        insights = analyze_files(repo_path)
        features = extract_features(repo_path, insights)
        features["security_score"] = analyze_security(insights.get("dependencies", []))
        if features["total_files"] <= 0 or features["total_lines"] <= 0:
            print("  Skipped: extracted repository did not produce usable source metrics.")
            continue
        save_training_row(features)
        success_count += 1
        print(f"  Added training row with framework={insights.get('framework', 'Unknown')}")

    print(f"Saved {success_count} rows into {CSV_PATH}")


if __name__ == "__main__":
    main()
