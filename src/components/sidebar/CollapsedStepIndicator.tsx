import React from 'react';

interface CollapsedStepIndicatorProps {
  step: any;
  index: number;
  active: boolean;
  onClick: () => void;
  icon: string;
}

export const CollapsedStepIndicator: React.FC<CollapsedStepIndicatorProps> = ({
  step,
  index,
  active,
  onClick,
  icon
}) => {
  const getStatusIndicator = (status: string) => {
    switch (status) {
      case 'completed': return '✅';
      case 'running': return '⏳';
      case 'error': return '❌';
      default: return '';
    }
  };

  return (
    <div className={`collapsed-step-indicator ${active ? 'active' : ''} ${step.status}`}>
      <button 
        className="collapsed-step-button"
        onClick={onClick}
        title={`${step.name} - ${step.status}`}
        aria-label={`Step ${index + 1}: ${step.name}`}
      >
        <div className="step-icon-container">
          <span className="step-icon">{icon}</span>
          <span className="step-number">{index + 1}</span>
        </div>
        <span className="status-indicator">{getStatusIndicator(step.status)}</span>
      </button>
    </div>
  );
};
