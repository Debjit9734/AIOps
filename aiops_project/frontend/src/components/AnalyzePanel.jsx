import React from "react";

function AnalyzePanel({ loading, error, result, onSubmit }) {
  const dependencies = result?.insights?.dependencies || [];

  return (
    <section className="panel">
      <h2>Analyze Repository</h2>
      <form onSubmit={onSubmit}>
        <button type="submit" disabled={loading}>
          {loading ? "Analyzing..." : "Run /api/analyze/"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      {result && (
        <div className="result">
          <p>
            <strong>Framework:</strong> {result.insights?.framework || "Not detected"}
          </p>
          <div>
            <strong>Dependencies:</strong>
            {dependencies.length === 0 ? (
              <p className="muted">No dependencies detected.</p>
            ) : (
              <ul>
                {dependencies.map((dependency, index) => (
                  <li key={`${dependency}-${index}`}>{dependency}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

export default AnalyzePanel;
