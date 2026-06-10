import io
import json
import os
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import requests


def _as_windows_long_path(path):
    if os.name != "nt":
        return path
    if path.startswith("\\\\?\\"):
        return path
    normalized = os.path.abspath(path)
    return f"\\\\?\\{normalized}"


def _safe_extract_zip(zip_file, target_dir):
    extracted_roots = set()

    for member in zip_file.infolist():
        member_name = member.filename.replace("\\", "/")
        if not member_name or member_name.endswith("/"):
            continue

        safe_parts = [part for part in Path(member_name).parts if part not in {"..", "."}]
        if not safe_parts:
            continue

        destination = os.path.join(target_dir, *safe_parts)
        destination_dir = os.path.dirname(destination)

        try:
            os.makedirs(_as_windows_long_path(destination_dir), exist_ok=True)
            with zip_file.open(member) as source, open(_as_windows_long_path(destination), "wb") as target:
                target.write(source.read())
            extracted_roots.add(safe_parts[0])
        except OSError:
            # Some very large repos have paths that still fail on Windows. Skip those files
            # instead of aborting the whole analysis.
            continue

    return extracted_roots


def download_repo_as_zip(repo_url):
    try:
        if repo_url.endswith("/"):
            repo_url = repo_url[:-1]

        parts = repo_url.split("github.com/")
        if len(parts) < 2:
            return None, "Invalid GitHub URL."

        repo_path = parts[1].removesuffix(".git")

        api_url = f"https://api.github.com/repos/{repo_path}"
        api_response = requests.get(api_url)

        if api_response.status_code != 200:
            return None, "GitHub API error: Repository not found."

        repo_info = api_response.json()
        default_branch = repo_info.get("default_branch", "main")

        zip_url = f"https://github.com/{repo_path}/archive/refs/heads/{default_branch}.zip"
        zip_response = requests.get(zip_url)
        if zip_response.status_code != 200:
            return None, f"Could not download ZIP for branch '{default_branch}'."

        temp_dir = tempfile.mkdtemp()
        zip_file = zipfile.ZipFile(io.BytesIO(zip_response.content))
        extracted_roots = _safe_extract_zip(zip_file, temp_dir)
        if not extracted_roots:
            return None, "Could not extract repository archive."

        extracted_folder = sorted(extracted_roots)[0]
        project_path = os.path.join(temp_dir, extracted_folder)
        return project_path, None

    except Exception as e:
        return None, f"Error: {str(e)}"


def _read_text_file(file_path):
    try:
        with open(_as_windows_long_path(file_path), "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return None


def _walk_project_files(repo_path):
    ignored_dirs = {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        "dist",
        "build",
        ".next",
        ".idea",
        ".vscode",
        "coverage",
        ".turbo",
    }

    for root, dirs, files in os.walk(_as_windows_long_path(repo_path)):
        display_root = root[4:] if os.name == "nt" and root.startswith("\\\\?\\") else root
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file_name in files:
            yield display_root, file_name, os.path.join(display_root, file_name)


def _find_first_file(repo_path, target_names):
    for _, file_name, full_path in _walk_project_files(repo_path):
        if file_name in target_names:
            return full_path
    return None


def _find_all_files(repo_path, target_names):
    matches = []
    for _, file_name, full_path in _walk_project_files(repo_path):
        if file_name in target_names:
            matches.append(full_path)
    return matches


def _parse_yaml_dependency_blocks(text, block_names):
    dependencies = []
    lines = text.splitlines()

    for block_name in block_names:
        in_block = False
        block_indent = None

        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            current_indent = len(raw_line) - len(raw_line.lstrip(" "))
            if not in_block and stripped == f"{block_name}:":
                in_block = True
                block_indent = current_indent
                continue

            if in_block:
                if current_indent <= block_indent and not stripped.startswith("#"):
                    in_block = False
                    block_indent = None
                    continue

                if ":" in stripped and not stripped.startswith("-"):
                    name, version = stripped.split(":", 1)
                    dependencies.append(f"{name.strip()}: {version.strip()}")

    return dependencies


def _analyze_flutter(pubspec_path):
    content = _read_text_file(pubspec_path)
    if content is None:
        return None

    return {
        "framework": "Flutter",
        "dependencies": _parse_yaml_dependency_blocks(
            content, ["dependencies", "dev_dependencies"]
        ),
    }


def _analyze_node(package_json_path):
    try:
        with open(_as_windows_long_path(package_json_path), "r", encoding="utf-8", errors="ignore") as f:
            package_data = json.load(f)
    except Exception:
        return None

    dependencies = package_data.get("dependencies") or {}
    dev_dependencies = package_data.get("devDependencies") or {}
    merged_keys = list(dict.fromkeys(list(dependencies.keys()) + list(dev_dependencies.keys())))

    if "next" in dependencies or "next" in dev_dependencies:
        framework = "Next.js"
    elif "react" in dependencies or "react" in dev_dependencies:
        framework = "React"
    elif "express" in dependencies or "express" in dev_dependencies:
        framework = "Express"
    else:
        framework = "Node.js"

    return {
        "framework": framework,
        "dependencies": merged_keys,
    }


def _analyze_java(pom_path):
    try:
        tree = ET.parse(_as_windows_long_path(pom_path))
        root = tree.getroot()
    except Exception:
        return None

    artifact_ids = []
    for element in root.iter():
        if element.tag.endswith("artifactId") and element.text:
            artifact_ids.append(element.text.strip())

    framework = "Spring Boot" if any("spring-boot" in artifact for artifact in artifact_ids) else "Java/Maven"
    return {
        "framework": framework,
        "dependencies": artifact_ids,
    }


def _analyze_go(go_mod_path):
    content = _read_text_file(go_mod_path)
    if content is None:
        return None

    dependencies = []
    in_require_block = False

    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("//"):
            continue

        if stripped.startswith("require ("):
            in_require_block = True
            continue

        if in_require_block:
            if stripped == ")":
                in_require_block = False
                continue
            dependencies.append(stripped)
            continue

        if stripped.startswith("require "):
            dependencies.append(stripped)

    return {
        "framework": "Go",
        "dependencies": dependencies,
    }


def _analyze_php_project(repo_path):
    composer_path = _find_first_file(repo_path, {"composer.json"})
    if not composer_path:
        return None

    try:
        with open(_as_windows_long_path(composer_path), "r", encoding="utf-8", errors="ignore") as f:
            composer_data = json.load(f)
    except Exception:
        return None

    require = composer_data.get("require") or {}
    require_dev = composer_data.get("require-dev") or {}
    dependencies = list(dict.fromkeys(list(require.keys()) + list(require_dev.keys())))

    package_name = (composer_data.get("name") or "").lower()
    extra_text = json.dumps(composer_data).lower()

    if "laravel/framework" in require or "laravel/framework" in require_dev:
        framework = "Laravel"
    elif "laravel" in package_name or "laravel" in extra_text:
        framework = "Laravel"
    else:
        framework = "PHP"

    return {
        "framework": framework,
        "dependencies": dependencies,
    }


def _detect_python_framework_from_text(text):
    lowered = (text or "").lower()
    if "django" in lowered:
        return "Django"
    if "fastapi" in lowered:
        return "FastAPI"
    if "flask" in lowered:
        return "Flask"
    return "Unknown"


def _clean_python_dependencies(lines):
    dependencies = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        dependencies.append(stripped)
    return dependencies


def _analyze_python_manifest(manifest_path):
    content = _read_text_file(manifest_path)
    if content is None:
        return None

    dependencies = _clean_python_dependencies(content.splitlines())
    framework = _detect_python_framework_from_text(content)
    return {
        "framework": framework,
        "dependencies": dependencies,
    }


def _analyze_python_project(repo_path):
    manifest_names = [
        "requirements.txt",
        "requirements-dev.txt",
        "Pipfile",
        "pyproject.toml",
    ]

    dependencies = []
    framework = "Unknown"

    for manifest_path in _find_all_files(repo_path, manifest_names):
        manifest_result = _analyze_python_manifest(manifest_path)
        if manifest_result is None:
            continue

        dependencies.extend(manifest_result["dependencies"])
        if framework == "Unknown" and manifest_result["framework"] != "Unknown":
            framework = manifest_result["framework"]

    unique_dependencies = list(dict.fromkeys(dependencies))

    if framework == "Unknown":
        manage_py = _find_first_file(repo_path, {"manage.py"})
        if manage_py:
            framework = "Django"

    if framework == "Unknown":
        settings_files = _find_all_files(repo_path, {"settings.py"})
        for settings_file in settings_files:
            content = _read_text_file(settings_file) or ""
            if "django" in content.lower():
                framework = "Django"
                break

    if framework == "Unknown" and not unique_dependencies:
        return None

    return {
        "framework": framework,
        "dependencies": unique_dependencies,
    }


def analyze_files(repo_path):
    """
    Analyze the project files to detect framework and dependencies.
    Returns insights: {framework, dependencies}
    """
    prioritized_detectors = [
        _analyze_python_project,
        _analyze_php_project,
        lambda path: _analyze_java(_find_first_file(path, {"pom.xml"})) if _find_first_file(path, {"pom.xml"}) else None,
        lambda path: _analyze_go(_find_first_file(path, {"go.mod"})) if _find_first_file(path, {"go.mod"}) else None,
        lambda path: _analyze_flutter(_find_first_file(path, {"pubspec.yaml"})) if _find_first_file(path, {"pubspec.yaml"}) else None,
        lambda path: _analyze_node(_find_first_file(path, {"package.json"})) if _find_first_file(path, {"package.json"}) else None,
    ]

    for detector in prioritized_detectors:
        result = detector(repo_path)
        if result is not None:
            return result

    return {"framework": "Unknown", "dependencies": []}
