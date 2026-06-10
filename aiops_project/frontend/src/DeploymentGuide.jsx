import React, { useMemo, useState } from "react";
import { analyzeRepo, recommendMl } from "./api";
import Stepper from "./components/Stepper";
import CodeBlock from "./components/CodeBlock";
import DownloadZipButton from "./components/DownloadZipButton";
import "./DeploymentGuide.css";

const CLOUD_OPTIONS = ["aws", "gcp", "azure"];
const STACK_OPTIONS = ["django", "flask", "fastapi", "node/express"];

const ARCH_MAP = {
  aws: [
    {
      service: "ECS Fargate",
      when: "Best default for containerized APIs with low ops overhead.",
      fit: ["django", "flask", "fastapi", "node/express"],
    },
    {
      service: "App Runner",
      when: "Fastest managed runtime for simple web services.",
      fit: ["flask", "fastapi", "node/express"],
    },
    {
      service: "EC2 + Docker",
      when: "Custom networking, custom AMI, or long-running worker control.",
      fit: ["django", "flask", "fastapi", "node/express"],
    },
  ],
  gcp: [
    {
      service: "Cloud Run",
      when: "Serverless container deployment with autoscaling.",
      fit: ["django", "flask", "fastapi", "node/express"],
    },
    {
      service: "GKE Autopilot",
      when: "Complex microservices and Kubernetes-native operations.",
      fit: ["django", "flask", "fastapi", "node/express"],
    },
  ],
  azure: [
    {
      service: "Azure App Service",
      when: "Straightforward web app hosting with managed platform features.",
      fit: ["django", "flask", "fastapi", "node/express"],
    },
    {
      service: "AKS",
      when: "Kubernetes control for advanced networking and workloads.",
      fit: ["django", "flask", "fastapi", "node/express"],
    },
  ],
};

const FALLBACK_GUIDES = {
  django: [
    "Create production environment variables and secret management plan.",
    "Build Docker image and run Django migrations.",
    "Collect static assets and validate health endpoint.",
    "Deploy service and configure load balancer or reverse proxy.",
    "Enable monitoring, alerts, and log aggregation.",
  ],
  flask: [
    "Define runtime variables and secrets.",
    "Build container image and run smoke test.",
    "Deploy to managed runtime and expose HTTPS endpoint.",
    "Configure autoscaling and request timeout limits.",
    "Enable observability and access logging.",
  ],
  fastapi: [
    "Prepare environment variables and service account credentials.",
    "Containerize app and run startup checks.",
    "Deploy API service and configure ingress.",
    "Tune concurrency and autoscaling settings.",
    "Add metrics, tracing, and error monitoring.",
  ],
  "node/express": [
    "Set environment variables and secret config.",
    "Build container image and run Node production startup test.",
    "Deploy service and configure domain and TLS.",
    "Apply autoscaling and resource limits.",
    "Configure centralized logs and alerting.",
  ],
};

function normalizeDetectedStack(frameworkText) {
  const f = (frameworkText || "").toLowerCase();
  if (f.includes("django")) return "django";
  if (f.includes("flask")) return "flask";
  if (f.includes("fastapi")) return "fastapi";
  if (f.includes("express") || f.includes("node")) return "node/express";
  return "";
}

function composeFilesMap(deploymentFiles, configList) {
  const files = { ...(deploymentFiles || {}) };
  (configList || []).forEach((fileName) => {
    if (!files[fileName]) {
      files[fileName] = `# ${fileName}\n# Add your ${fileName} content based on selected stack and cloud.\n`;
    }
  });
  return files;
}

function JsonDetails({ title, value }) {
  if (!value) return null;
  return (
    <details className="json-card">
      <summary>{title}</summary>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}

function formatCloudLabel(cloud) {
  return cloud.toUpperCase();
}

function MetricTile({ label, value, accent }) {
  return (
    <article className={`metric-tile ${accent}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function DeploymentGuide() {
  const [repoUrl, setRepoUrl] = useState("");
  const [cloud, setCloud] = useState("aws");
  const [detectedStack, setDetectedStack] = useState("");
  const [stack, setStack] = useState("");

  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [recommendLoading, setRecommendLoading] = useState(false);
  const [error, setError] = useState("");

  const [analyzeData, setAnalyzeData] = useState(null);
  const [recommendData, setRecommendData] = useState(null);

  const validateRepo = () => {
    if (!repoUrl.trim()) return "Please enter a GitHub repository URL.";
    return "";
  };

  const onAnalyze = async () => {
    const validation = validateRepo();
    if (validation) {
      setError(validation);
      return;
    }

    setAnalyzeLoading(true);
    setError("");
    try {
      const data = await analyzeRepo(repoUrl.trim());
      setAnalyzeData(data);
      setRecommendData(null);
      const autoStack = normalizeDetectedStack(data?.insights?.framework);
      setDetectedStack(autoStack);
      if (!stack && autoStack) setStack(autoStack);
    } catch (err) {
      setAnalyzeData(null);
      setDetectedStack("");
      setError(err.message || "Analyze failed.");
    } finally {
      setAnalyzeLoading(false);
    }
  };

  const onRecommend = async () => {
    const validation = validateRepo() || (!analyzeData?.analysis_id ? "Run Analyze first." : "");
    if (validation) {
      setError(validation);
      return;
    }

    setRecommendLoading(true);
    setError("");
    try {
      const data = await recommendMl(analyzeData.analysis_id, cloud);
      setRecommendData(data);
    } catch (err) {
      setRecommendData(null);
      setError(err.message || "Recommendation failed.");
    } finally {
      setRecommendLoading(false);
    }
  };

  const activeStack = stack || detectedStack;
  const architectureOptions = useMemo(() => {
    if (!activeStack) return [];
    const options = ARCH_MAP[cloud] || [];
    return options.filter((item) => item.fit.includes(activeStack));
  }, [cloud, activeStack]);

  const selectedArchitecture = architectureOptions[0] || null;
  const predictedResources = recommendData?.predicted_resources || null;

  const checklist = useMemo(() => {
    const apiSteps = recommendData?.deployment_steps;
    if (Array.isArray(apiSteps) && apiSteps.length) return apiSteps;

    const local = FALLBACK_GUIDES[activeStack] || [
      "Analyze the repository or select a stack to generate a deployment checklist.",
    ];
    return [
      `Target cloud: ${formatCloudLabel(cloud)}`,
      `Preferred architecture: ${selectedArchitecture?.service || "Choose a stack to see architecture options"}`,
      ...local,
    ];
  }, [recommendData, activeStack, cloud, selectedArchitecture]);

  const requiredFiles = recommendData?.configuration_files_needed || [];
  const generatedFiles = useMemo(
    () => composeFilesMap(recommendData?.deployment_files, requiredFiles),
    [recommendData, requiredFiles]
  );

  const currentStep = useMemo(() => {
    if (!repoUrl.trim()) return 1;
    if (!analyzeData) return 1;
    if (!stack) return 2;
    if (!recommendData) return 3;
    return 5;
  }, [repoUrl, analyzeData, stack, recommendData]);

  const heroStats = [
    { label: "Selected Cloud", value: formatCloudLabel(cloud) },
    { label: "Detected Stack", value: analyzeData?.insights?.framework || "Waiting" },
    { label: "Preferred Runtime", value: selectedArchitecture?.service || "Pending" },
  ];

  return (
    <main className="guide-shell">
      <section className="hero-card">
        <div className="hero-copy">
          <p className="eyebrow">AIOps Deployment Studio</p>
          <h1>From raw repository to a deployment blueprint that actually looks ready.</h1>
          <p className="hero-text">
            Analyze the repo, surface the likely stack, generate an architecture direction, and
            package the files your team needs to ship with more confidence.
          </p>
          <div className="hero-stats">
            {heroStats.map((item) => (
              <div key={item.label} className="hero-stat">
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </div>

        <div className="hero-orbit">
          <div className="orbit-panel">
            <span className="orbit-kicker">Live Route</span>
            <strong>{repoUrl.trim() || "github.com/org/repo"}</strong>
            <p>
              {analyzeData
                ? `Analysis locked with ID ${analyzeData.analysis_id}.`
                : "Point the tool at a repository to begin analysis."}
            </p>
          </div>
          <Stepper
            currentStep={currentStep}
            steps={[
              "Select Cloud",
              "Detect or Override Stack",
              "Review Architecture",
              "Deployment Checklist",
              "Generate Files",
            ]}
          />
        </div>
      </section>

      <section className="panel panel-controls">
        <div className="section-heading">
          <div>
            <p className="section-tag">Control Deck</p>
            <h2>Feed the analyzer and steer the deployment plan.</h2>
          </div>
          <div className="pulse-chip">
            <span className={analyzeData ? "pulse on" : "pulse"} />
            {analyzeData ? "Analysis Ready" : "Awaiting Repo"}
          </div>
        </div>

        <div className="input-grid">
          <label className="field">
            <span>Repository URL</span>
            <input
              type="url"
              placeholder="https://github.com/org/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
            />
          </label>

          <label className="field">
            <span>Cloud</span>
            <select value={cloud} onChange={(e) => setCloud(e.target.value)}>
              {CLOUD_OPTIONS.map((c) => (
                <option value={c} key={c}>
                  {c.toUpperCase()}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Tech Stack</span>
            <select value={stack} onChange={(e) => setStack(e.target.value)}>
              {!stack && <option value="">Auto-detected after Analyze</option>}
              {STACK_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="action-row">
          <button type="button" className="btn btn-primary" onClick={onAnalyze} disabled={analyzeLoading}>
            {analyzeLoading ? "Analyzing..." : "Analyze Repository"}
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onRecommend}
            disabled={recommendLoading || !analyzeData?.analysis_id}
          >
            {recommendLoading ? "Recommending..." : "Generate Recommendation"}
          </button>
        </div>

        {analyzeData && (
          <div className="status-card success">
            <div>
              <strong>Analysis complete.</strong>
              <p>Framework: {analyzeData?.insights?.framework || "Unknown"}</p>
            </div>
            <div>
              <span>Analysis ID</span>
              <code>{analyzeData.analysis_id}</code>
            </div>
          </div>
        )}
        {detectedStack && (
          <p className="hint">
            Auto-detected stack: <strong>{detectedStack}</strong>. You can still override it before
            recommendation.
          </p>
        )}
        {analyzeData && !detectedStack && (
          <p className="hint">
            Analysis finished, but the stack could not be auto-detected. Choose it manually to keep
            going.
          </p>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      <section className="insight-grid">
        <section className="panel panel-architecture">
          <div className="section-heading">
            <div>
              <p className="section-tag">Architecture Signal</p>
              <h2>Pick the lane with the best fit for this stack.</h2>
            </div>
          </div>

          {!selectedArchitecture && (
            <p className="muted">
              {activeStack
                ? "No architecture recommendation yet."
                : "Run Analyze or choose a stack to unlock architecture recommendations."}
            </p>
          )}

          {selectedArchitecture && (
            <div className="arch-grid">
              {architectureOptions.map((option) => (
                <article
                  key={option.service}
                  className={`arch-card ${option.service === selectedArchitecture.service ? "top" : ""}`}
                >
                  <div className="arch-meta">
                    <span className="arch-badge">
                      {option.service === selectedArchitecture.service ? "Primary Fit" : "Alternate"}
                    </span>
                    <h3>{option.service}</h3>
                  </div>
                  <p>{option.when}</p>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="panel panel-metrics">
          <div className="section-heading">
            <div>
              <p className="section-tag">Resource Pulse</p>
              <h2>Infrastructure sizing at a glance.</h2>
            </div>
          </div>

          {predictedResources ? (
            <div className="metric-grid">
              <MetricTile label="CPU" value={predictedResources.cpu} accent="accent-gold" />
              <MetricTile label="RAM" value={predictedResources.ram} accent="accent-cyan" />
              <MetricTile label="Storage" value={predictedResources.storage} accent="accent-rose" />
            </div>
          ) : (
            <div className="metrics-empty">
              <strong>No resource recommendation yet.</strong>
              <p>Run Recommend to generate estimated CPU, RAM, and storage needs.</p>
            </div>
          )}
        </section>
      </section>

      <section className="panel panel-checklist">
        <div className="section-heading">
          <div>
            <p className="section-tag">Execution Sequence</p>
            <h2>Turn the recommendation into a deployment runbook.</h2>
          </div>
        </div>
        <ol className="timeline">
          {checklist.map((step, idx) => (
            <li key={`${idx}-${step}`} className="timeline-item">
              <span className="timeline-dot">{idx + 1}</span>
              <div className="timeline-content">{step}</div>
            </li>
          ))}
        </ol>
      </section>

      <section className="panel panel-files">
        <div className="files-header">
          <div>
            <p className="section-tag">Output Bundle</p>
            <h2>Download and inspect the generated deployment files.</h2>
            <p className="muted">
              Missing files get placeholder content locally so the bundle stays useful even before
              the API returns final content.
            </p>
          </div>
          <DownloadZipButton files={generatedFiles} zipName="deployment-guide-files.zip" />
        </div>

        <div className="files-grid">
          {Object.entries(generatedFiles).length === 0 && (
            <div className="files-empty">
              <strong>No files generated yet.</strong>
              <p>Run Recommend to produce deployment artifacts for the selected target.</p>
            </div>
          )}
          {Object.entries(generatedFiles).map(([filename, content]) => (
            <CodeBlock key={filename} title={filename} filename={filename} content={content} />
          ))}
        </div>
      </section>

      <section className="panel panel-debug">
        <div className="section-heading">
          <div>
            <p className="section-tag">Debug View</p>
            <h2>Raw API responses, kept nearby when you need them.</h2>
          </div>
        </div>
        <JsonDetails title="Analyze Response" value={analyzeData} />
        <JsonDetails title="Recommend Response" value={recommendData} />
      </section>
    </main>
  );
}

export default DeploymentGuide;
