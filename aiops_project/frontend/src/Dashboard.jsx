import React, { useMemo, useState } from "react";
import { analyzeRepo, recommendMl } from "./api";
import "./Dashboard.css";

const CLOUD_OPTIONS = ["aws", "gcp", "azure"];

function JsonSection({ title, data, defaultOpen = true }) {
  if (data === undefined || data === null) return null;

  return (
    <details className="json-section" open={defaultOpen}>
      <summary>{title}</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}

function DeploymentFiles({ files }) {
  const [copied, setCopied] = useState("");

  const entries = useMemo(() => Object.entries(files || {}), [files]);
  if (!entries.length) return <p className="muted">No deployment files returned.</p>;

  const handleCopy = async (filename, content) => {
    try {
      await navigator.clipboard.writeText(content || "");
      setCopied(filename);
      setTimeout(() => setCopied(""), 1400);
    } catch {
      setCopied("copy-failed");
    }
  };

  return (
    <div className="files-list">
      {entries.map(([filename, content]) => (
        <details key={filename} className="json-section" open>
          <summary>{filename}</summary>
          <div className="file-actions">
            <button
              type="button"
              className="secondary"
              onClick={() => handleCopy(filename, content)}
            >
              {copied === filename ? "Copied" : "Copy to clipboard"}
            </button>
            {copied === "copy-failed" && <span className="error-inline">Copy failed</span>}
          </div>
          <pre>{content}</pre>
        </details>
      ))}
    </div>
  );
}

function Dashboard() {
  const [repoUrl, setRepoUrl] = useState("");
  const [cloud, setCloud] = useState("aws");

  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [recommendLoading, setRecommendLoading] = useState(false);
  const [analyzeError, setAnalyzeError] = useState("");
  const [recommendError, setRecommendError] = useState("");
  const [analyzeData, setAnalyzeData] = useState(null);
  const [recommendData, setRecommendData] = useState(null);

  const validate = () => {
    if (!repoUrl.trim()) return "Please enter a repository URL.";
    return "";
  };

  const onAnalyze = async () => {
    const error = validate();
    setAnalyzeError(error);
    if (error) return;

    setAnalyzeLoading(true);
    setAnalyzeError("");
    try {
      const data = await analyzeRepo(repoUrl.trim());
      setAnalyzeData(data);
    } catch (err) {
      setAnalyzeData(null);
      setAnalyzeError(err.message || "Analyze request failed.");
    } finally {
      setAnalyzeLoading(false);
    }
  };

  const onRecommend = async () => {
    const error = validate();
    setRecommendError(error);
    if (error) return;

    setRecommendLoading(true);
    setRecommendError("");
    try {
      if (!analyzeData?.analysis_id) {
        throw new Error("Run Analyze first.");
      }
      const data = await recommendMl(analyzeData.analysis_id, cloud);
      setRecommendData(data);
    } catch (err) {
      setRecommendData(null);
      setRecommendError(err.message || "Recommend request failed.");
    } finally {
      setRecommendLoading(false);
    }
  };

  return (
    <main className="dashboard">
      <section className="card">
        <h1>AIOps Dashboard</h1>
        <p className="muted">Analyze repositories and generate ML-based deployment recommendations.</p>

        <div className="form-grid">
          <label>
            Repo URL
            <input
              type="url"
              placeholder="https://github.com/org/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
            />
          </label>

          <label>
            Cloud
            <select value={cloud} onChange={(e) => setCloud(e.target.value)}>
              {CLOUD_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option.toUpperCase()}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="actions">
          <button type="button" onClick={onAnalyze} disabled={analyzeLoading}>
            {analyzeLoading ? "Analyzing..." : "Analyze"}
          </button>
          <button type="button" onClick={onRecommend} disabled={recommendLoading}>
            {recommendLoading ? "Recommending..." : "Recommend"}
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Analyze Response</h2>
        {analyzeError && <p className="error">{analyzeError}</p>}
        {!analyzeData && !analyzeError && <p className="muted">No analyze response yet.</p>}
        {analyzeData && (
          <>
            <JsonSection title="Insights" data={analyzeData.insights} />
            <JsonSection title="Raw Analyze JSON" data={analyzeData} defaultOpen={false} />
          </>
        )}
      </section>

      <section className="card">
        <h2>Recommendation Response</h2>
        {recommendError && <p className="error">{recommendError}</p>}
        {!recommendData && !recommendError && <p className="muted">No recommendation response yet.</p>}
        {recommendData && (
          <>
            <JsonSection title="Features" data={recommendData.features} />
            <JsonSection title="Predicted Resources" data={recommendData.predicted_resources} />
            <details className="json-section" open>
              <summary>Deployment Files</summary>
              <DeploymentFiles files={recommendData.deployment_files} />
            </details>
            <JsonSection title="Raw Recommendation JSON" data={recommendData} defaultOpen={false} />
          </>
        )}
      </section>
    </main>
  );
}

export default Dashboard;
