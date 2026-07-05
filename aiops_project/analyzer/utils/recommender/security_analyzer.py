import re

# Known baseline "safe enough" major versions for a short list of very common
# packages. This is intentionally small and illustrative -- it is NOT a CVE
# database. For real vulnerability coverage, replace/augment this with actual
# `npm audit --json`, `pip-audit`, or an OSV API lookup fed from the repo's
# lockfile (package-lock.json, poetry.lock, etc).
MIN_SAFE_MAJOR = {
    "django": 3,
    "flask": 2,
    "fastapi": 0,
    "requests": 2,
    "express": 4,
    "lodash": 4,
    "axios": 0,
}

UNPINNED_MARKERS = {"*", "latest", "x", ""}

_DEP_PATTERN = re.compile(
    r"^([A-Za-z0-9_\-.]+)\s*(@|==|>=|<=|~=|<|>)?\s*([A-Za-z0-9_.\-^~*]*)$"
)


def _split_name_version(dep):
    """
    Accepts dependency strings in several shapes and returns (name, version)
    with version normalized to a plain numeric-leading string, or None if
    no usable version info is present.

    Supported shapes:
      "express@^4.18.2"   (node, after analyzer_utils.py fix)
      "django==4.2.1"      (python requirements.txt)
      "django>=4.0"
      "django<3.0"
      "express"            (bare name, no version info available)
    """
    dep = (dep or "").strip()
    match = _DEP_PATTERN.match(dep)
    if not match:
        return dep.lower(), None

    name, _operator, version = match.groups()
    version = (version or "").lstrip("^~=v")
    return name.lower(), (version or None)


def _major_version(version_str):
    if not version_str:
        return None
    match = re.match(r"(\d+)", version_str)
    return int(match.group(1)) if match else None


def _is_unpinned(version_str):
    return version_str is None or version_str.strip() in UNPINNED_MARKERS


def analyze_security(dependencies):
    """
    Heuristic dependency risk score, 0-10 (higher = riskier).

    This is a lightweight static check, NOT a vulnerability scan. It flags:
      - dependencies (from our known-package list) with no version info at
        all, or a wildcard version -- meaning we can't verify what's
        actually running
      - dependencies below a known-old major version floor, for a short
        list of common frameworks/libraries

    Packages we don't recognize are skipped rather than penalized, so the
    score only reflects what we can actually check -- it does not claim to
    cover your full dependency tree. For real coverage, wire this up to
    `npm audit` / `pip-audit` output instead.

    Returns a float 0-10. Also returns how many dependencies were actually
    evaluable, via analyze_security_detailed, if that context is useful
    upstream.
    """
    result = analyze_security_detailed(dependencies)
    return result["score"]


def analyze_security_detailed(dependencies):
    if not dependencies:
        return {"score": 0, "checked": 0, "flagged": 0, "flagged_packages": []}

    checked = 0
    flagged = 0
    flagged_packages = []

    for dep in dependencies:
        name, version = _split_name_version(dep)
        floor = MIN_SAFE_MAJOR.get(name)
        if floor is None:
            continue  # not in our known list -- no opinion, don't guess

        checked += 1

        if _is_unpinned(version):
            flagged += 1
            flagged_packages.append(f"{name} (no pinned version)")
            continue

        major = _major_version(version)
        if major is not None and major < floor:
            flagged += 1
            flagged_packages.append(f"{name}@{version} (below major v{floor})")

    if checked == 0:
        # None of the dependencies were in our known-package list, so we
        # have no basis to score risk. Returning 0 here is "unknown", not
        # "verified safe" -- callers that care about the distinction should
        # check `checked` too.
        return {"score": 0, "checked": 0, "flagged": 0, "flagged_packages": []}

    ratio = flagged / checked
    score = round(min(ratio * 10, 10), 1)
    return {
        "score": score,
        "checked": checked,
        "flagged": flagged,
        "flagged_packages": flagged_packages,
    }