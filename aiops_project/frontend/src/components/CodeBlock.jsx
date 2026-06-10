import React, { useState } from "react";

function downloadTextFile(filename, content) {
  const blob = new Blob([content ?? ""], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function CodeBlock({ title, filename, content }) {
  const [copyState, setCopyState] = useState("");

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(content ?? "");
      setCopyState("copied");
      setTimeout(() => setCopyState(""), 1400);
    } catch {
      setCopyState("failed");
      setTimeout(() => setCopyState(""), 1600);
    }
  };

  return (
    <details className="code-card" open>
      <summary>{title || filename}</summary>
      <div className="code-actions">
        <button type="button" className="btn secondary" onClick={onCopy}>
          {copyState === "copied" ? "Copied" : "Copy"}
        </button>
        <button
          type="button"
          className="btn secondary"
          onClick={() => downloadTextFile(filename, content)}
        >
          Download
        </button>
        {copyState === "failed" && <span className="error-inline">Copy failed</span>}
      </div>
      <pre>{content || ""}</pre>
    </details>
  );
}

export default CodeBlock;
