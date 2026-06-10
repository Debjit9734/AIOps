import React from "react";

function Stepper({ steps, currentStep }) {
  return (
    <ol className="stepper" aria-label="Deployment wizard steps">
      {steps.map((label, index) => {
        const stepNumber = index + 1;
        const state =
          stepNumber < currentStep ? "done" : stepNumber === currentStep ? "active" : "pending";

        return (
          <li key={label} className={`step-item ${state}`}>
            <div className="step-badge">{stepNumber}</div>
            <div className="step-label">{label}</div>
          </li>
        );
      })}
    </ol>
  );
}

export default Stepper;
