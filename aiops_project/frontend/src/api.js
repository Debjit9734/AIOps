async function postJson(endpoint, payload) {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  let data;
  try {
    data = await response.json();
  } catch {
    data = undefined;
  }

  if (!response.ok) {
    const message = data?.error || data?.detail || `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return data ?? {};
}

export async function analyzeRepo(repoUrl) {
  return postJson("/api/analyze/", { repo_url: repoUrl });
}

export async function recommendMl(analysisId, cloud) {
  return postJson("/api/recommend-ml/", { analysis_id: analysisId, cloud });
}
