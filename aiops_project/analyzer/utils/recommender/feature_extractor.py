import os

def extract_features(repo_path, insights):
    features = {}
    
    # --- Feature 1: Project Size ---
    total_files = 0
    total_lines = 0
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith((".py", ".js", ".java", ".go", ".dart")):
                total_files += 1
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8", errors="ignore") as f:
                        total_lines += len(f.readlines())
                except:
                    pass
    features["total_files"] = total_files
    features["total_lines"] = total_lines

    # --- Feature 2: Dependency count ---
    deps = insights.get("dependencies", [])
    features["dependency_count"] = len(deps)

    return features
