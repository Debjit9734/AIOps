import React from "react";

const CLOUD_OPTIONS = ["aws", "gcp", "azure"];

function RecommendPanel({ cloud, setCloud, loading, error, result, onSubmit }) {
  return (
    <section className="panel">
      <h2>ML Recommendation</h2>
      <form onSubmit={onSubmit} className="stack">
        <label htmlFor="cloud">Cloud</label>
        <select id="cloud" value={cloud} onChange={(event) => setCloud(event.target.value)}>
          {CLOUD_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option.toUpperCase()}
            </option>
          ))}
        </select>
        <button type="submit" disabled={loading}>
          {loading ? "Recommending..." : "Run /api/recommend-ml/"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {result && (
        <div className="result">
          <h3>Predicted Resources</h3>
          <pre>{JSON.stringify(result.predicted_resources, null, 2)}</pre>
          <h3>Deployment Files</h3>
          {Object.keys(result.deployment_files || {}).length === 0 ? (
            <p className="muted">No generated deployment files for detected framework.</p>
          ) : (
            Object.entries(result.deployment_files).map(([filename, content]) => (
              <div key={filename}>
                <h4>{filename}</h4>
                <pre>{content}</pre>
              </div>
            ))
          )}
        </div>
      )}
    </section>
  );
}

export default RecommendPanel;
