import React from 'react';
import { PipelineStep } from '../../types';
import './ProgressDisplay.css';

interface ProgressDisplayProps {
  step?: PipelineStep | null;
}

export const ProgressDisplay: React.FC<ProgressDisplayProps> = ({ step }) => {
  if (!step || step.status !== 'running') {
    return null;
  }

  return (
    <div className="progress-display">
      <div className="progress-header">
        <h4 className="progress-title">
          Processing: {step.name}
        </h4>
        <span className="progress-percentage">
          {step.percentage}%
        </span>
      </div>
      
      <div className="progress-bar-container">
        <div 
          className="progress-bar-fill"
          style={{ width: `${step.percentage}%` }}
        />
      </div>
      
      {step.data?.message && (
        <div className="progress-message">
          {step.data.message}
        </div>
      )}
    </div>
  );
};
