import React from 'react';

interface PipelineStepProps {
  step: any;
  index: number;
  active: boolean;
  onClick: () => void;
  isCollapsed: boolean;
  modelConfig?: any;
  icon: string;
}

export const PipelineStep: React.FC<PipelineStepProps> = ({
  step,
  index,
  active,
  onClick,
  isCollapsed,
  modelConfig,
  icon
}) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✅';
      case 'running': return '⏳';
      case 'error': return '❌';
      default: return '⭕';
    }
  };

  return (
    <div className={`pipeline-step ${active ? 'active' : ''} ${step.status}`}>
      <button className="pipeline-step-button" onClick={onClick}>
        <span className="step-icon">{icon}</span>
        {!isCollapsed && (
          <div className="step-content">
            <span className="step-name">{step.name}</span>
            <div className="step-meta">
              <span className="step-status">{getStatusIcon(step.status)} {step.status}</span>
              {step.percentage > 0 && step.status === 'running' && (
                <span className="step-progress">{step.percentage}%</span>
              )}
            </div>
          </div>
        )}
      </button>
    </div>
  );
};
