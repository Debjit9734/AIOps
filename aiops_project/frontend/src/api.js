const AUTH_TOKEN_KEY = "aiops_auth_token";

export function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || "";
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
  window.dispatchEvent(new Event("aiops-auth-changed"));
}

function authHeaders() {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function requestJson(endpoint, options = {}) {
  const response = await fetch(endpoint, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...authHeaders(),
      ...(options.headers || {})
    },
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

async function postJson(endpoint, payload) {
  return requestJson(endpoint, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

async function getJson(endpoint) {
  return requestJson(endpoint, { method: "GET" });
}

function persistSession(data) {
  setAuthToken(data.token);
  return data;
}

export async function registerUser({ username, email, password }) {
  return persistSession(await postJson("/api/auth/register/", { username, email, password }));
}

export async function loginUser({ username, password }) {
  return persistSession(await postJson("/api/auth/login/", { username, password }));
}

export async function logoutUser() {
  try {
    await postJson("/api/auth/logout/", {});
  } finally {
    setAuthToken("");
  }
}

export async function getCurrentUser() {
  if (!getAuthToken()) return null;
  return getJson("/api/auth/me/");
}

export async function analyzeRepo(repoUrl) {
  return postJson("/api/analyze/", { repo_url: repoUrl });
}

export async function recommendMl(analysisId, cloud, selectedArchitecture) {
  return postJson("/api/recommend-ml/", {
    analysis_id: analysisId,
    cloud,
    selected_architecture: selectedArchitecture,
  });
}
