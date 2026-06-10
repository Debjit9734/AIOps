import React, { useState } from "react";
import JSZip from "jszip";

function DownloadZipButton({ files, zipName = "deployment-files.zip" }) {
  const [busy, setBusy] = useState(false);
  const entries = Object.entries(files || {}).filter(([name]) => Boolean(name));

  const onDownloadZip = async () => {
    if (!entries.length || busy) return;

    setBusy(true);
    try {
      const zip = new JSZip();
      entries.forEach(([filename, content]) => {
        zip.file(filename, content ?? "");
      });

      const blob = await zip.generateAsync({ type: "blob" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = zipName;
      anchor.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(false);
    }
  };

  return (
    <button type="button" className="btn" disabled={!entries.length || busy} onClick={onDownloadZip}>
      {busy ? "Preparing zip..." : "Download all as .zip"}
    </button>
  );
}

export default DownloadZipButton;
