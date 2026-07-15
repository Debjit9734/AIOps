import React, { useEffect, useMemo, useState } from "react";
import { analyzeRepo, getCurrentUser, recommendMl } from "./api";
import Stepper from "./components/Stepper";
import CodeBlock from "./components/CodeBlock";
import DownloadZipButton from "./components/DownloadZipButton";
import "./DeploymentGuide.css";

const CLOUD_OPTIONS = ["aws", "gcp", "azure"];

const ARCH_MAP = {
  aws: [
    {
      service: "EC2 + Docker",
      when: "Best beginner path because you can see every server, port, and command directly.",
      fit: ["django", "flask", "fastapi", "node/express"],
    },
    {
      service: "ECS Fargate",
      when: "Good next step after the manual EC2 deployment is understood.",
      fit: ["django", "flask", "fastapi", "node/express"],
    },
    {
      service: "App Runner",
      when: "Fast managed runtime for simple web services after the basics are clear.",
      fit: ["flask", "fastapi", "node/express"],
    },
  ],
  gcp: [
    {
      service: "Compute Engine VM",
      when: "Best beginner path for learning server setup, firewall rules, SSH, and app startup.",
      fit: ["django", "flask", "fastapi", "node/express"],
    },
    {
      service: "Cloud Run",
      when: "Good next step for serverless container deployment after Docker is working.",
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
      service: "Azure Virtual Machine",
      when: "Best beginner path for learning VM creation, NSG ports, SSH, and Linux deployment.",
      fit: ["django", "flask", "fastapi", "node/express"],
    },
    {
      service: "Azure App Service",
      when: "Good next step for managed web app hosting once the manual path is clear.",
      fit: ["django", "flask", "fastapi", "node/express"],
    },
    {
      service: "AKS",
      when: "Kubernetes control for advanced networking and workloads.",
      fit: ["django", "flask", "fastapi", "node/express"],
    },
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
      files[fileName] = `# ${fileName}\n# Add your ${fileName} content based on detected stack and cloud.\n`;
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

function titleFromRecommendationStep(step, index) {
  const text = String(step || "").trim();
  if (!text) return `Recommendation step ${index + 1}`;
  return text.replace(/[.!?]\s*$/, "");
}

function normalizeRunbookTitle(title, details, index) {
  const text = String(title || "").trim();
  if (text && !text.toLowerCase().startsWith("recommendation step")) return text;
  return titleFromRecommendationStep(details?.[0], index);
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
  const [authInfo, setAuthInfo] = useState(null);
  const [repoUrl, setRepoUrl] = useState("");
  const [cloud, setCloud] = useState("aws");
  const [detectedStack, setDetectedStack] = useState("");

  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [recommendLoading, setRecommendLoading] = useState(false);
  const [error, setError] = useState("");

  const [analyzeData, setAnalyzeData] = useState(null);
  const [recommendData, setRecommendData] = useState(null);
  const [selectedArchitectureService, setSelectedArchitectureService] = useState("");

  useEffect(() => {
    let active = true;

    getCurrentUser()
      .then((data) => {
        if (active) setAuthInfo(data);
      })
      .catch(() => {
        if (active) setAuthInfo(null);
      });

    return () => {
      active = false;
    };
  }, []);

  const validateRepo = () => {
    if (!authInfo?.user) return "Please login before analyzing a repository.";
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
      if (data?.rate_limit) {
        setAuthInfo((current) => ({
          ...(current || {}),
          rate_limit: data.rate_limit,
        }));
      }
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
      const data = await recommendMl(
        analyzeData.analysis_id,
        cloud,
        selectedArchitecture?.service
      );
      setRecommendData(data);
    } catch (err) {
      setRecommendData(null);
      setError(err.message || "Recommendation failed.");
    } finally {
      setRecommendLoading(false);
    }
  };

  const activeStack = detectedStack;
  const architectureOptions = useMemo(() => {
    if (!activeStack) return [];
    const options = ARCH_MAP[cloud] || [];
    return options.filter((item) => item.fit.includes(activeStack));
  }, [cloud, activeStack]);

  useEffect(() => {
    if (!architectureOptions.length) {
      setSelectedArchitectureService("");
      return;
    }

    const selectedStillAvailable = architectureOptions.some(
      (option) => option.service === selectedArchitectureService
    );

    if (!selectedStillAvailable) {
      setSelectedArchitectureService(architectureOptions[0].service);
    }
  }, [architectureOptions, selectedArchitectureService]);

  const selectedArchitecture =
    architectureOptions.find((option) => option.service === selectedArchitectureService)
    || architectureOptions[0]
    || null;
  const predictedResources = recommendData?.predicted_resources || null;

  const checklist = useMemo(() => {
    if (!recommendData) {
      return [
        {
          title: "Generate the recommendation first",
          details: [
            "Run Analyze Repository to detect the stack, then click Generate Recommendation.",
            "The detailed runbook shown here will come from the ML/API recommendation for this project and selected cloud.",
          ],
        },
      ];
    }

    if (Array.isArray(recommendData.deployment_runbook) && recommendData.deployment_runbook.length) {
      return recommendData.deployment_runbook.map((step, index) => ({
        title: normalizeRunbookTitle(step.title, step.details, index),
        details: Array.isArray(step.details) && step.details.length ? step.details : [String(step)],
        commands: Array.isArray(step.commands) ? step.commands : [],
      }));
    }

    if (Array.isArray(recommendData.deployment_steps) && recommendData.deployment_steps.length) {
      return recommendData.deployment_steps.map((step, index) => ({
        title: titleFromRecommendationStep(step, index),
        details: [step],
        commands: [],
      }));
    }

    return [
      {
        title: "No runbook returned",
        details: [
          "The recommendation API completed, but it did not return deployment_runbook or deployment_steps.",
          "Check the raw recommendation response below for troubleshooting.",
        ],
      },
    ];
  }, [recommendData]);

  const requiredFiles = recommendData?.configuration_files_needed || [];
  const generatedFiles = useMemo(
    () => composeFilesMap(recommendData?.deployment_files, requiredFiles),
    [recommendData, requiredFiles]
  );

  const currentStep = useMemo(() => {
    if (!repoUrl.trim()) return 1;
    if (!analyzeData) return 1;
    if (!recommendData) return 3;
    return 5;
  }, [repoUrl, analyzeData, recommendData]);

  const heroStats = [
    { label: "Selected Cloud", value: formatCloudLabel(cloud) },
    { label: "Detected Stack", value: analyzeData?.insights?.framework || "Waiting" },
    {
      label: "Analyze Quota",
      value: authInfo?.rate_limit?.is_admin
        ? "Admin"
        : `${authInfo?.rate_limit?.remaining ?? 3}/3 left`,
    },
  ];

  return (
    <main className="guide-shell">
      <section className="hero-card">
        <div className="hero-copy">
          <p className="eyebrow">AIOps Deployment Studio</p>
          <h1>From raw repository to a deployment blueprint that actually looks ready.</h1>
          <p className="hero-text">
            Analyze the repo, detect the stack, and generate a beginner-friendly cloud deployment
            path with server choices, ports, SSH steps, commands, and generated files.
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
              "Analyze Stack",
              "Review Architecture",
              "Beginner Runbook",
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
            {authInfo?.user ? `${authInfo.user.username} signed in` : "Login Required"}
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

        {!authInfo?.user && (
          <div className="status-card auth">
            <div>
              <strong>Login required for analysis.</strong>
              <p>Create an account so the app can track your 3 daily analyses.</p>
            </div>
            <a className="btn btn-ghost" href="/login">
              Login
            </a>
          </div>
        )}

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
            Auto-detected stack: <strong>{detectedStack}</strong>.
          </p>
        )}
        {analyzeData && !detectedStack && (
          <p className="hint">
            Analysis finished, but the stack could not be auto-detected from the framework response.
          </p>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      <section className="insight-grid">
        <section className="panel panel-architecture">
          <div className="section-heading">
            <div>
              <p className="section-tag">Architecture Signal</p>
              <h2>Start with the clearest beginner path for this stack.</h2>
            </div>
          </div>

          {!selectedArchitecture && (
            <p className="muted">
              {activeStack
                ? "Run Recommend to load the API architecture recommendation."
                : "Run Analyze to unlock architecture recommendations."}
            </p>
          )}

          {selectedArchitecture && (
            <div className="arch-grid">
              {architectureOptions.map((option, index) => {
                const isSelected = option.service === selectedArchitecture.service;

                return (
                <button
                  type="button"
                  key={option.service}
                  className={`arch-card ${isSelected ? "top" : ""}`}
                  onClick={() => setSelectedArchitectureService(option.service)}
                  aria-pressed={isSelected}
                >
                  <div className="arch-meta">
                    <span className="arch-badge">
                      {isSelected ? "Selected" : index === 0 ? "Primary Fit" : "Alternate"}
                    </span>
                    <h3>{option.service}</h3>
                  </div>
                  <p>{option.when}</p>
                </button>
                );
              })}
            </div>
          )}
        </section>

        <section className="panel panel-metrics">
          <div className="section-heading">
            <div>
              <p className="section-tag">Resource Pulse</p>
              <h2>Beginner server sizing at a glance.</h2>
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
              <p>Run Recommend to estimate CPU, RAM, storage, and starter server size.</p>
            </div>
          )}
        </section>
      </section>

      <section className="panel panel-checklist">
        <div className="section-heading">
          <div>
            <p className="section-tag">Execution Sequence</p>
            <h2>API-generated deployment runbook for {formatCloudLabel(cloud)}.</h2>
          </div>
        </div>
        <ol className="timeline">
          {checklist.map((step, idx) => (
            <li key={`${idx}-${step.title}`} className="timeline-item">
              <span className="timeline-dot">{idx + 1}</span>
              <div className="timeline-content">
                <h3>{step.title}</h3>
                <ul>
                  {step.details.map((detail, detailIndex) => (
                    <li key={`${step.title}-${detailIndex}`}>{detail}</li>
                  ))}
                </ul>
                {step.commands && (
                  <div className="command-list">
                    {step.commands.map((command) => (
                      <code key={command}>{command}</code>
                    ))}
                  </div>
                )}
              </div>
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
              Use these files after the beginner runbook explains where they fit in the cloud setup.
            </p>
          </div>
          <DownloadZipButton files={generatedFiles} zipName="deployment-guide-files.zip" />
        </div>

        <div className="files-grid">
          {Object.entries(generatedFiles).length === 0 && (
            <div className="files-empty">
              <strong>No files generated yet.</strong>
              <p>Run Recommend to produce deployment artifacts for the selected cloud target.</p>
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
