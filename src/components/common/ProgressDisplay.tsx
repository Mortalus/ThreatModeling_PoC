import React from 'react';
import { PipelineStep } from '../../types';
import './ProgressDisplay.css';

interface ProgressDisplayProps {
  steps: PipelineStep[];
}

export const ProgressDisplay: React.FC<ProgressDisplayProps> = ({ steps }) => {
  const currentStep = steps.findIndex(s => s.status === 'running');
  
  if (currentStep === -1) {
    return null;
  }

  const step = steps[currentStep];

  return (
    <div className="progress-display">
      <div className="progress-info">
        <span className="progress-step">Step {currentStep + 1} of {steps.length}</span>
        <span className="progress-name">{step.name}</span>
      </div>
      <div className="progress-bar">
        <div 
          className="progress-fill"
          style={{ width: `${step.percentage}%` }}
        />
      </div>
      <div className="progress-percentage">{step.percentage}%</div>
    </div>
  );
};
