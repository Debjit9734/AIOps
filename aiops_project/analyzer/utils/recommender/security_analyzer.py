def analyze_security(dependencies):
    risk_score = 0
    risky_keywords = ["requests<", "django<", "flask<", "cryptography<", "oldlib"]
    
    for dep in dependencies:
        if any(keyword in dep for keyword in risky_keywords):
            risk_score += 2
        elif any(dep.startswith(k) for k in ["django", "flask", "fastapi", "express"]):
            risk_score += 1
    return min(risk_score, 10)  # Cap at 10
