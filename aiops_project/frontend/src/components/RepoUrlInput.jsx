import React from "react";

function RepoUrlInput({ value, onChange }) {
  return (
    <section className="panel">
      <h2>Repository Input</h2>
      <label htmlFor="repoUrl">GitHub Repo URL</label>
      <input
        id="repoUrl"
        type="url"
        placeholder="https://github.com/org/repo"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </section>
  );
}

export default RepoUrlInput;
